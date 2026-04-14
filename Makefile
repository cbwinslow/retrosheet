# Makefile for EdgeForge project

PYTHON=python3

## Knowledge‑base creation
kb:
	@echo "=== Scraping Retrosheet publications ==="
	$(PYTHON) scripts/scrape_retrosheet_kb.py
	@echo "=== Downloading Moneyball PDF ==="
	$(PYTHON) scripts/download_moneyball.py
	@echo "=== Performing web search for baseball‑ML resources ==="
	$(PYTHON) scripts/web_search_kb.py
	@echo "=== Building LlamaIndex vector store (optional) ==="
	$(PYTHON) scripts/ingest_kb_llamaindex.py

## Convenience shortcuts
run:
	$(PYTHON) main.py

.PHONY: kb run

# -------------------------------------------------------------------
# Feature marts
# -------------------------------------------------------------------
feature-marts:
	@echo "Running feature‑mart migrations..."
	python scripts/migrate_feature_marts.py

## Run KB pipeline in parallel (scrape, download, search) then ingest
kb_parallel:
	@echo "=== Running KB pipeline in parallel ==="
	$(PYTHON) scripts/run_kb_parallel.py