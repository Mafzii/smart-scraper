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
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "div", "section", "table"]):
        desc = tag.name
        if tag.get("id"):
            desc += f"#{tag.get('id')}"
        if tag.get("class"):
            desc += f".{'.'.join(tag.get('class'))}"
        text = tag.get_text(strip=True)[:50]
        if text:
            desc += f" → {text}"
        outline.append(desc)
    
    with open('logs/step1_outline.txt', 'w') as f:
        f.write("\n".join(outline))
    return "\n".join(outline)

def extract_subtree(soup: BeautifulSoup, hint: str) -> str:
    """
    Deep search: find all tags where id/class/text matches hint, collect their text.
    """
    matches = []
    logging.info(f"Extracting subtree with hint: {hint[:100]}...")
    logging.info(f"Soup length: {len(soup.prettify())}")

    # Search by id
    for tag in soup.find_all(attrs={"id": lambda v: v and hint.lower() in v.lower()}):
        text = tag.get_text(" ", strip=True)
        matches.append(text)

    # Search by class (can be multiple classes per tag)
    for tag in soup.find_all(class_=lambda v: v and any(hint.lower() in c.lower() for c in v)):
        text = tag.get_text(" ", strip=True)
        matches.append(text)

    # Search by tag name
    for tag in soup.find_all(hint.lower()):
        text = tag.get_text(" ", strip=True)
        matches.append(text)

    # Search by text content
    for tag in soup.find_all(string=lambda t: hint.lower() in t.lower()):
        text = tag.parent.get_text(" ", strip=True)
        matches.append(text)

    # Remove duplicates and empty strings
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
    html = asyncio.run(fetch_page(url, True))
    with open('logs/page_content.txt', 'w') as f:
        f.write(html)
    soup = BeautifulSoup(html, "html.parser")

    # Step 0: Extract structured content for LLM
    structured_content = extract_structured_content(soup)
    with open('logs/page_structured_content.json', 'w') as f:
        json.dump(structured_content, f, indent=2)

    # Step 1: Build outline & ask LLM for best section
    outline = make_outline(soup)
    section_hint = call_llm(f"""
    User wants: {prompt}.
    Here is a page outline:
    {outline}

    Which section (heading, div id, class, or table) seems most relevant?
    Reply with a comma-separated string.
    No extra information please.
    """)
    with open('logs/step1_llm_section_hint.txt', 'w') as f:
        f.write(section_hint)

    # Step 2: Extract candidate snippets for each identifier
    identifiers = [i.strip() for i in section_hint.replace(',', '\n').split('\n') if i.strip()]
    logging.info(f"Identifiers from LLM: {identifiers}")
    candidates = []
    for ident in identifiers:
        subtree = extract_subtree(soup, ident)
        if subtree:
            candidates.append(subtree)

    combined_candidate = '\n---\n'.join(candidates)

    # Step 3: Ask LLM to extract JSON from combined candidate text and structured content
    structured = call_llm(f"""
    Task: {prompt}.
    Here is the candidate text:
    {combined_candidate}

    Here is the page structured content (list of dicts with id, href, text):
    {json.dumps(structured_content, ensure_ascii=False)}

    Extract according to the task, no explanation.
    """)
    with open('logs/step3_llm_structured_response.txt', 'w') as f:
        f.write(structured)

    try:
        return json.loads(structured)
    except Exception:
        return {"raw": structured}