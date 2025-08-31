import asyncio
import json
import logging
from playwright.async_api import async_playwright
import httpx
import requests
from bs4 import BeautifulSoup


LLM_ENDPOINT = "http://ollama:11434/api/generate"  # talk to Ollama container

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


async def fetch_page(url: str, render_js: bool = True) -> str:
    logging.info(f"Fetching page: {url} | render_js={render_js}")
    if render_js:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            content = await page.content()
            await browser.close()
        logging.info(f"Fetched JS-rendered content from {url} (length={len(content)})")
        return content
    else:
        resp = httpx.get(url, timeout=30)
        resp.raise_for_status()
        logging.info(f"Fetched static content from {url} (length={len(resp.text)})")
        return resp.text


def query_llm(prompt: str, context: str) -> str:
    logging.info(f"Querying LLM with prompt: {prompt[:60]}... and context length: {len(context)}")
    payload = {
        "model": "llama3.2:1b",   # must match pulled Ollama model
        "stream": False,
        "prompt": f"You are a web extraction assistant.\n\n"
                  f"Prompt: {prompt}\n\n"
                  f"Website content:\n{context[:10000]}\n\n"
                  f"Return the answer in JSON with root property field 'answer'."
                  f"Give a brief explanation for your answer."
                  f"Use only the website content to determine your answer."
    }
    resp = requests.post(LLM_ENDPOINT, json=payload)
    resp.raise_for_status()
    data = resp.json()
    logging.info(f"LLM response received (length={len(data)})")
    return data.get("response", "")


async def run_extraction(prompt: str, url: str) -> dict:
    logging.info(f"Starting extraction for URL: {url} with prompt: {prompt}")
    raw_html = await fetch_page(url, render_js=True)
    html = clean_html(raw_html)
    result = query_llm(prompt, html)

    try:
        parsed = json.loads(result)
        logging.info(f"Parsed LLM result as JSON: {parsed}")
    except Exception as e:
        raise ValueError(f"Failed to parse LLM result: {e}")

    output = {
        "prompt": prompt,
        "url": url,
        "result": parsed
    }
    logging.info(f"Extraction complete for {url}")
    return output

def clean_html(raw_html):
    logging.info(f"Cleaning html input for LLM")
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    content = []
    for tag in soup.find_all(["h1","h2","h3","p","li","table","tr","td"]):
        content.append(tag.get_text(" ", strip=True))

    return "\n".join(content)
