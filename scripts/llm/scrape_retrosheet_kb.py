#!/usr/bin/env python3
"""Scrape Retrosheet.org for publicly available articles, PDFs and reports.

The script crawls the main publications page, follows each link that points to a
PDF or an HTML article, downloads the content, and stores it under the ``kb``
directory created in the repository root.

Usage::

    python3 scripts/scrape_retrosheet_kb.py

The script is deliberately lightweight – it uses only the standard library and
``requests``/``beautifulsoup4`` which are already declared in ``requirements.txt``.
It writes a JSON log (``kb/download_log.json``) that records the source URL,
local path, HTTP status and any error messages.
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_URL = 'https://www.retrosheet.org/'
PUBLICATIONS_PAGE = urljoin(BASE_URL, 'publications.htm')
KB_ROOT = Path(__file__).resolve().parents[1] / 'kb'
ARTICLES_DIR = KB_ROOT / 'articles'
LOG_PATH = KB_ROOT / 'download_log.json'

ARTICLES_DIR.mkdir(parents=True, exist_ok=True)


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def log_entry(entry: dict):
    # Append a JSON line to the log file
    with LOG_PATH.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def download_file(url: str, dest: Path) -> dict:
    try:
        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        entry = {
            'url': url,
            'local_path': str(dest),
            'status': resp.status_code,
            'sha256': sha256_of_file(dest),
        }
        log_entry(entry)
        print(f'✅ Downloaded {url} → {dest}')
        return entry
    except Exception as e:
        entry = {'url': url, 'error': str(e)}
        log_entry(entry)
        print(f'❌ Failed {url}: {e}')
        return entry


def is_valid_link(href: str) -> bool:
    # Accept absolute URLs or relative URLs that stay on retrosheet.org
    if not href:
        return False
    parsed = urlparse(href)
    if parsed.scheme and parsed.netloc:
        return parsed.netloc.endswith('retrosheet.org')
    return True


def main():
    print(f'🔎 Crawling {PUBLICATIONS_PAGE}')
    try:
        page = requests.get(PUBLICATIONS_PAGE, timeout=30)
        page.raise_for_status()
    except Exception as exc:
        print(f'❌ Could not fetch publications page: {exc}')
        sys.exit(1)

    soup = BeautifulSoup(page.text, 'html.parser')
    # Find all anchor tags that look like documents
    links = soup.find_all('a', href=True)
    for a in links:
        href = a['href']
        if not is_valid_link(href):
            continue
        full_url = urljoin(PUBLICATIONS_PAGE, href)
        # Determine file type by extension
        path = urlparse(full_url).path
        filename = os.path.basename(path)
        if not filename:
            continue
        lower = filename.lower()
        if lower.endswith('.pdf'):
            dest = ARTICLES_DIR / filename
            download_file(full_url, dest)
        elif lower.endswith('.htm') or lower.endswith('.html'):
            # Save raw HTML and also extract text version
            dest_html = ARTICLES_DIR / filename
            entry = download_file(full_url, dest_html)
            # Extract readable text if download succeeded
            if entry.get('status') == 200:
                try:
                    html_resp = requests.get(full_url, timeout=30)
                    html_resp.raise_for_status()
                    article_soup = BeautifulSoup(html_resp.text, 'html.parser')
                    # Simple heuristic: grab <article> or main <div>
                    article = article_soup.find('article') or article_soup.find(
                        'div', {'class': 'content'},
                    )
                    text = (
                        article.get_text(separator='\n', strip=True)
                        if article
                        else article_soup.get_text(separator='\n', strip=True)
                    )
                    txt_path = ARTICLES_DIR / (filename.rsplit('.', 1)[0] + '.txt')
                    txt_path.write_text(text, encoding='utf-8')
                    print(f'📝 Extracted text to {txt_path}')
                except Exception as e:
                    print(f'⚠️ Could not extract text from {full_url}: {e}')
        else:
            # Skip other file types (e.g., .zip, .doc) for now
            continue

    print('✅ Scraping complete. Log written to', LOG_PATH)


if __name__ == '__main__':
    main()
