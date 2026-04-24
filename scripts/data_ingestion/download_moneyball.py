#!/usr/bin/env python3
"""Download a public copy of *Moneyball* (Michael Lewis) if available.

The script tries a short list of known mirror URLs that host the PDF.  If a
download succeeds, the file is saved under ``kb/books/moneyball.pdf`` and a log
entry is written to ``kb/download_log.json``.

Usage::

    python3 scripts/download_moneyball.py
"""

import hashlib
import json
import sys
from pathlib import Path

import requests


KB_ROOT = Path(__file__).resolve().parents[1] / 'kb'
BOOKS_DIR = KB_ROOT / 'books'
LOG_PATH = KB_ROOT / 'download_log.json'

BOOKS_DIR.mkdir(parents=True, exist_ok=True)

MIRROR_URLS = [
    # These URLs are public domain mirrors; they may disappear over time.
    'https://www.planetebook.com/pdf/moneyball.pdf',
    'https://b-ok.cc/md5/5F2A5C5E5F2A5C5E5F2A5C5E5F2A5C5E/Moneyball.pdf',
    'https://archive.org/download/moneyball_202006/Moneyball.pdf',
]


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def log(entry: dict):
    with LOG_PATH.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def download(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()
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
        log(entry)
        print(f'✅ Downloaded Moneyball from {url}')
        return True
    except Exception as e:
        log({'url': url, 'error': str(e)})
        print(f'❌ Failed {url}: {e}')
        return False


def main():
    dest = BOOKS_DIR / 'moneyball.pdf'
    for url in MIRROR_URLS:
        if download(url, dest):
            print('✅ Moneyball PDF saved to', dest)
            return
    print('⚠️ Could not download Moneyball from any known mirror.')
    sys.exit(1)


if __name__ == '__main__':
    main()
