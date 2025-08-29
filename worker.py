import asyncio
import json
from playwright.async_api import async_playwright
import httpx
import requests

LLM_ENDPOINT = "http://ollama:11434/api/generate"  # talk to Ollama container


async def fetch_page(url: str, render_js: bool = True) -> str:
    if render_js:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            content = await page.content()
            await browser.close()
        return content
    else:
        resp = httpx.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text


def query_llm(prompt: str, context: str) -> str:
    payload = {
        "model": "llama3",   # must match pulled Ollama model
        "prompt": f"You are a web extraction assistant.\n\n"
                  f"Prompt: {prompt}\n\n"
                  f"Website content:\n{context[:5000]}\n\n"
                  f"Return the answer in JSON with fields 'answer' and 'confidence'."
    }
    resp = requests.post(LLM_ENDPOINT, json=payload)
    resp.raise_for_status()
    return resp.json().get("response", "")


async def run_extraction(prompt: str, url: str) -> dict:
    html = await fetch_page(url, render_js=True)
    result = query_llm(prompt, html)

    try:
        parsed = json.loads(result)
    except Exception:
        parsed = {"answer": result.strip(), "confidence": 0.5}

    return {
        "prompt": prompt,
        "url": url,
        "result": parsed
    }
