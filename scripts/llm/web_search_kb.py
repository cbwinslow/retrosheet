#!/usr/bin/env python3
"""Perform a broad web search for baseball-ML literature and store results.

The script uses the SerpAPI (https://serpapi.com) if the environment variable
``SERPAPI_KEY`` is present.  If no key is available, it falls back to a simple
Bing HTML scrape (limited and may be blocked).  Results are saved as JSON lines
in ``kb/search_results.json`` and any downloadable PDFs are fetched into the
``kb/articles`` directory.

The list of queries is defined in ``QUERIES`` - it covers the topics you asked
for (Moneyball, Markov chains, Bayesian inference, WAR, betting markets, etc.).
"""

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


KB_ROOT = Path(__file__).resolve().parents[1] / 'kb'
ARTICLES_DIR = KB_ROOT / 'articles'
RESULTS_PATH = KB_ROOT / 'search_results.json'

ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

QUERIES = [
    'Moneyball baseball analytics PDF',
    'Markov chain baseball model',
    'Bayesian inference baseball',
    'Random forest baseball prediction',
    'WAR calculation baseball',
    'Baseball betting markets Kalshi',
    'ML models for baseball plate appearance',
    'Retrosheet data analysis tutorial',
    'Baseball regression analysis',
    'Supervised learning baseball',
    'Unsupervised clustering baseball',
    'Feature engineering baseball analytics',
]


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def log_result(entry: dict):
    with RESULTS_PATH.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def download_pdf(url: str, dest: Path) -> None:
    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        with dest.open('wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f'✅ PDF saved: {dest}')
    except Exception as e:
        print(f'⚠️ Failed to download PDF {url}: {e}')


def serpapi_search(query: str, api_key: str):
    params = {
        'engine': 'google',
        'q': query,
        'api_key': api_key,
        'num': '10',
    }
    resp = requests.get('https://serpapi.com/search', params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get('organic_results', [])


def bing_html_search(query: str):
    # Very simple Bing search - may be throttled.
    url = f'https://www.bing.com/search?q={requests.utils.quote(query)}'
    page = requests.get(url, timeout=30)
    page.raise_for_status()
    soup = BeautifulSoup(page.text, 'html.parser')
    results = []
    for li in soup.select('li.b_algo')[:10]:
        a = li.find('a')
        if a and a.get('href'):
            results.append({'title': a.get_text(), 'link': a['href']})
    return results


def process_query(query: str, api_key: str | None = None):
    print(f'🔎 Searching for: {query}')
    try:
        raw_results = serpapi_search(query, api_key) if api_key else bing_html_search(query)
    except Exception as e:
        print(f"❌ Search failed for '{query}': {e}")
        return

    for res in raw_results:
        link = res.get('link') or res.get('url')
        title = res.get('title', '')
        entry = {'query': query, 'title': title, 'url': link}
        log_result(entry)
        # If the link ends with .pdf, download it
        if link and link.lower().endswith('.pdf'):
            filename = os.path.basename(urlparse(link).path)
            dest = ARTICLES_DIR / filename
            download_pdf(link, dest)


def main():
    api_key = os.getenv('SERPAPI_KEY')
    for q in QUERIES:
        process_query(q, api_key)
    print('✅ Search complete. Results stored in', RESULTS_PATH)


if __name__ == '__main__':
    main()
