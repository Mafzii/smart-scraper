import asyncio
import json
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from worker import run_extraction

def extract_from_url(url):
    return run_extraction("Find the first match of the new york knicks", url)

# Example usage:
url = 'https://www.espn.com/nba/schedule'
html = asyncio.run(extract_from_url(url))
print(f"Fetched from {url}")
with open("logs/output.json", "w") as f:
    json.dump(html, f)