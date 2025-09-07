import logging
import requests
from playwright.async_api import async_playwright, Playwright

OLLAMA = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"
NOTFOUND = "Information not found in URL"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

async def run_extraction(user_input: str, url: str) -> dict:
    '''
    Main driver function
    '''
    async with async_playwright() as playwright:
        logging.info(f"Fetching playwright accessibility snapshot: {url}")
        url_snapshot = await fetch_page(url, playwright)

    print(len(url_snapshot))
    url_snapshot = url_snapshot[6000:12000]
    with open("logs/smol_snapshot.txt", "w") as f:
        f.write(url_snapshot)
    
    if url_snapshot.strip() != "":
        while True:
            logging.info(f"Prompting Ollama for response: {url}")
            slm_resp, state = query_slm(user_input, url_snapshot)
            if state == "DONE":
                logging.info(f"Completed task for: {url}")
                return slm_resp
            if state == "NOTFOUND":
                raise Exception(NOTFOUND)
            if state == "SEARCH":
                break # todo: implement search subpages

async def fetch_page(url: str, playwright: Playwright) -> str:
    '''
    Fetch accesibility snapshot of the requested url
    '''
    chromium = playwright.chromium # or "firefox" or "webkit".
    browser = await chromium.launch()
    page = await browser.new_page()
    await page.goto(url)
    
    snapshot = await page.accessibility.snapshot()
    converted_snapshot = convert_snapshot(snapshot)
    with open("logs/snapshot_str.txt", "w") as f:
        f.write(converted_snapshot)

    await browser.close()
    return converted_snapshot

def convert_snapshot(snapshot: dict) -> str:
    '''
    Recursively convert the accessibility snapshot dict into a readable, ordered string for SLM.
    Each node is serialized with its role, name, and children, preserving order and hierarchy.
    '''
    def serialize_node(node, depth=0, idx_path=None):
        if idx_path is None:
            idx_path = []
        indent = f'depth:{depth}'
        role = node.get('role', 'unknown')
        name = node.get('name', '')
        value = node.get('value', '')
        order_str = '.'.join(str(i) for i in idx_path) if idx_path else 'root'
        line = f"[{indent}][{order_str}] type: {role}; text: '{name}'"
        if value:
            line += f"; value: '{value}'"
        lines = [line]
        children = node.get('children', [])
        for i, child in enumerate(children):
            lines.append(serialize_node(child, depth+1, idx_path + [i]))
        return '\n'.join(lines)

    return serialize_node(snapshot)

def query_slm(user_input: str, url_snapshot: str):
    prompt = f"""
USER_INPUT: {{{user_input}}}
Your job is to answer the USER_INPUT by extracting and reasoning over the provided CONTEXT

- The CONTEXT uses a hierarchy of nodes with types, text, values, and depth.
- The structure may contain lists, tables, buttons, links, divs, spans, and other semantic elements.
- You should parse, interpret, and map these nodes to fulfill the user request.
- Always keep responses concise and machine-readable.

CONTEXT: {{{url_snapshot}}}

Respond strictly in JSON format with the following schema:
{{
  "input": "<the user input exactly as given>",
  "output": "<the extracted or inferred answer to the user_input, in as less words as possible>"
}}
"""

    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    resp = requests.post(OLLAMA, json=payload)
    resp.raise_for_status()

    state = "DONE" # todo: update it for multi page searching
    return resp.json()["response"], state