#!/usr/bin/env python3
"""Run the knowledge-base creation steps in parallel.

The script launches the following tasks concurrently using a ``ProcessPoolExecutor``:
    1. ``scrape_retrosheet_kb.py`` - download Retrosheet publications.
    2. ``download_moneyball.py`` - fetch a public copy of *Moneyball*.
    3. ``web_search_kb.py`` - perform a broad web search for baseball-ML resources.
    4. ``ingest_kb_llamaindex.py`` - optional LlamaIndex ingestion (runs after the
       other three have completed because it depends on the files being present).

Usage::

    python3 scripts/run_kb_parallel.py

The script prints a summary of each task's exit code.  It is safe to run multiple
times - existing files are overwritten only if the source download succeeds.
"""

import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed


SCRIPTS = [
    'scripts/scrape_retrosheet_kb.py',
    'scripts/download_moneyball.py',
    'scripts/web_search_kb.py',
]


def run_script(path: str) -> tuple:
    """Execute a Python script and return (path, returncode)."""
    try:
        result = subprocess.run([sys.executable, path], capture_output=True, text=True)
        print(f'--- {path} finished (code {result.returncode}) ---')
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return (path, result.returncode)
    except Exception as e:
        print(f'Error running {path}: {e}', file=sys.stderr)
        return (path, -1)


def main():
    # Run the three independent scripts in parallel
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(run_script, s): s for s in SCRIPTS}
        for future in as_completed(futures):
            script, rc = future.result()
            if rc != 0:
                print(f'⚠️ {script} exited with code {rc}')

    # After the above finish, run the optional ingestion step (sequential)
    print('=== Running optional LlamaIndex ingestion ===')
    rc = subprocess.run(
        [sys.executable, 'scripts/ingest_kb_llamaindex.py'],
        capture_output=True,
        text=True,
    ).returncode
    print(f'ingest_kb_llamaindex.py finished with code {rc}')


if __name__ == '__main__':
    main()
