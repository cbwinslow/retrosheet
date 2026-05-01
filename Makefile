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
# Code Quality & Linting (Ruff)
# -------------------------------------------------------------------
lint:
	@echo "=== Running Ruff linter ==="
	ruff check baseball/ tests/ scripts/

lint-fix:
	@echo "=== Auto-fixing issues with Ruff ==="
	ruff check --fix baseball/ tests/ scripts/

format:
	@echo "=== Formatting code with Ruff ==="
	ruff format baseball/ tests/ scripts/

imports:
	@echo "=== Organizing imports with Ruff ==="
	ruff check --select I --fix baseball/ tests/ scripts/

# Run all quality checks
quality: format imports lint
	@echo "=== All quality checks passed ==="

# -------------------------------------------------------------------
# Testing
# -------------------------------------------------------------------
test:
	@echo "=== Running all tests ==="
	pytest tests/ -v --tb=short

test-unit:
	@echo "=== Running unit tests ==="
	pytest tests/unit/ -v --tb=short

test-integration:
	@echo "=== Running integration tests ==="
	pytest tests/integration/ -v --tb=short -m integration

test-betting:
	@echo "=== Running betting tests ==="
	pytest tests/betting/ -v --tb=short

test-ingestion:
	@echo "=== Running ingestion tests ==="
	pytest tests/ingestion/ -v --tb=short

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