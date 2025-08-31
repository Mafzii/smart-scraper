

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from workers.worker import fetch_page
from workers.agentic_worker import agentic_scrape, make_outline
import asyncio

def extract_from_url(url):
    return agentic_scrape("Find the first match of the new york knicks on October the 2nd", url)

# Example usage:
url = 'https://www.espn.com/nba/schedule'
html = extract_from_url(url)
print(f"Fetched from {url}")
with open('test/output.html', 'w') as f:
    f.write(html.__str__())