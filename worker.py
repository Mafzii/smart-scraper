import logging
from playwright.async_api import async_playwright, Playwright

LLM_ENDPOINT = "http://ollama:11434/api/generate"
MODEL = "llama3.2:1b"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

async def run_extraction(prompt: str, url: str) -> dict:
    async with async_playwright() as playwright:
        await fetch_page(url, playwright)

async def fetch_page(url: str, playwright: Playwright) -> str:
    '''
    Fetch accesibility snapshot of the requested url
    '''
    logging.info(f"Fetching playwright accessibility snapshot: {url}")

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
    Recursively convert the accessibility snapshot dict into a readable, ordered string for LLM.
    Each node is serialized with its role, name, and children, preserving order and hierarchy.
    '''
    def serialize_node(node, depth=0, idx_path=None):
        if idx_path is None:
            idx_path = []
        indent = '  ' * depth
        role = node.get('role', 'unknown')
        name = node.get('name', '')
        value = node.get('value', '')
        order_str = '.'.join(str(i) for i in idx_path) if idx_path else 'root'
        line = f"{indent}[{order_str}] role: {role}; name: '{name}'"
        if value:
            line += f"; value: '{value}'"
        lines = [line]
        children = node.get('children', [])
        for i, child in enumerate(children):
            lines.append(serialize_node(child, depth+1, idx_path + [i]))
        return '\n'.join(lines)

    return serialize_node(snapshot)
