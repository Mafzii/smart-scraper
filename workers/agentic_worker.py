import asyncio
import logging
import requests
from bs4 import BeautifulSoup
import json

from workers.worker import fetch_page

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"   # or any model you pulled into Ollama

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def call_llm(prompt: str) -> str:
    """
    Call local Ollama model and return plain text response.
    """
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    resp = requests.post(OLLAMA_API, json=payload)
    resp.raise_for_status()
    return resp.json()["response"]

def make_outline(soup: BeautifulSoup) -> str:
    """
    Create a rough outline of the page structure.
    Only grabs some headings, div ids/classes, and table hints.
    """
    outline = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "div", "section", "table"]):
        desc = tag.name
        if tag.get("id"):
            desc += f"#{tag.get('id')}"
        if tag.get("class"):
            desc += f".{'.'.join(tag.get('class'))}"
        text = tag.get_text(strip=True)
        if text:
            desc += f" → {text}"
        outline.append(desc)
    
    with open('logs/step1_outline.txt', 'w') as f:
        f.write("\n".join(outline))
    return "\n".join(outline)

def extract_subtree(soup: BeautifulSoup, hint: str) -> str:
    """
    Extract subtree based on structured identifier dict from LLM.
    """
    tag = hint.get("tag")
    tag_id = hint.get("id")
    tag_class = hint.get("class")
    tag_text = hint.get("text")
    tag_href = hint.get("href")
    matches = []
    search_kwargs = {}
    if tag_id:
        search_kwargs["id"] = tag_id
    if tag_class:
        search_kwargs["class_"] = tag_class.split() if isinstance(tag_class, str) else tag_class
    found = soup.find_all(tag, **search_kwargs)
    for t in found:
        if tag_text and tag_text not in t.get_text(" ", strip=True):
            continue
        if tag_href and t.get("href") != tag_href:
            continue
        matches.append(t.get_text(" ", strip=True))
    results = [text for text in set(matches) if text]
    with open('logs/step2_extracted_subtree.txt', 'w') as f:
        f.write("\n---\n".join(results))
    return "\n---\n".join(results)



def extract_structured_content(soup: BeautifulSoup):
    """
    Extracts all tags with id, href, and text into a structured list.
    Returns a list of dicts: {id, href, text}
    """
    elements = []
    for tag in soup.find_all(True):
        tag_id = tag.get('id')
        tag_href = tag.get('href')
        tag_text = tag.get_text(' ', strip=True)
        if tag_id or tag_href or tag_text:
            elements.append({
                "id": tag_id,
                "href": tag_href,
                "text": tag_text
            })
    return elements

def agentic_scrape(prompt: str, url: str) -> dict:
    """
    Two-pass agentic scraping:
    1. Ask LLM where to look.
    2. Ask LLM to extract structured JSON.
    """
    page_content = asyncio.run(fetch_page(url, True))
    with open('logs/page_content.txt', 'w') as f:
        f.write(page_content)
    soup = BeautifulSoup(page_content, "html.parser")
    outline = make_outline(soup)

    # Step 1: Build outline & ask LLM for best section
    section_hint = call_llm(f"""
        USER_REQUEST: {prompt}
        PAGE_STRUCTURE: {outline}

        TASK: From the PAGE_STRUCTURE, identify only the sections, elements, or text that are most relevant to fulfilling the USER_REQUEST. 
        - Ignore navigation menus, ads, boilerplate text, and unrelated content.
        - Preserve concise, context-rich snippets (e.g. headings, table rows, labeled divs).
        - Keep order if it helps understanding.

        REPLY STRICTLY with a list of JSON objects, each with keys:
        "tag": the tag name (e.g. "h2", "div", "table", "tr", "td", "a"),
        "id": the id attribute if present, else null,
        "class": the class attribute if present, else null,
        "text": the text content (short, max 100 chars),
        "href": the href attribute if present, else null.
        Example:
        "tag": "h2", "id": "schedule", "class": "main-title", "text": "NBA Schedule", "href": null
        "tag": "a", "id": null, "class": "link", "text": "Thunder vs Lakers", "href": "/nba/game/123"
        DO NOT explain or add extra text.
    """)
    with open('logs/step1_llm_section_hint.txt', 'w') as f:
        f.write(section_hint)

    # Step 2: Extract identifiers from JSON array in section_hint
    identifiers = []
    try:
        # Find the first JSON array in the string
        start = section_hint.find('[')
        end = section_hint.rfind(']') + 1
        if start != -1 and end != -1:
            json_str = section_hint[start:end]
            identifiers = json.loads(json_str)
    except Exception as e:
        raise Exception(f"Failed to parse identifiers JSON: {e}")
    logging.info(f"Identifiers from LLM: {identifiers}")
    candidates = []
    for ident in identifiers:
        subtree = extract_subtree(soup, ident)
        if subtree:
            candidates.append(subtree)

    combined_candidate = '\n---\n'.join(candidates)

    # Step 3: Ask LLM to extract JSON from combined candidate text and structured content
    structured = call_llm(f"""
        You are a web extraction assistant.\n\n
        USER_INPUT: {prompt}.
        CONTEXT: {combined_candidate}

        TASK: Complete the user input to the best of your ability using the context.
        Respond in JSON format with the answer in the output property 
        and the user input in the input property.
    """)
    with open('logs/step3_llm_structured_response.json', 'w') as f:
        f.write(structured)

    try:
        return json.loads(structured)
    except Exception:
        return {"raw": structured}