# Makefile for retrosheet baseball prediction platform

PYTHON=python3
PIP=pip3

## Run the CLI
run:
	$(PYTHON) -m baseball.cli

## Install dependencies
install:
	$(PIP) install -e .

## Install dev dependencies
install-dev:
	$(PIP) install -e ".[dev]"
	$(PIP) install ruff pytest pytest-asyncio

.PHONY: run install install-dev

# -------------------------------------------------------------------
# Code Quality & Linting (Ruff)
# -------------------------------------------------------------------
lint:
	@echo "=== Running Ruff linter ==="
	uv run ruff check baseball/ tests/ scripts/

lint-fix:
	@echo "=== Auto-fixing issues with Ruff ==="
	uv run ruff check --fix baseball/ tests/ scripts/

lint-fix-unsafe:
	@echo "=== Auto-fixing issues with Ruff (unsafe) ==="
	uv run ruff check --fix --unsafe-fixes baseball/ tests/ scripts/

format:
	@echo "=== Formatting code with Ruff ==="
	uv run ruff format baseball/ tests/ scripts/

imports:
	@echo "=== Organizing imports with Ruff ==="
	uv run ruff check --select I --fix baseball/ tests/ scripts/

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
	pytest tests/integration/ -v --tb=short

test-betting:
	@echo "=== Running betting tests ==="
	pytest tests/betting/ -v --tb=short

test-ingestion:
	@echo "=== Running ingestion tests ==="
	pytest tests/ingestion/ -v --tb=short

test-live:
	@echo "=== Running live MLB API tests ==="
	python scripts/test_live_ingestion.py

coverage:
	@echo "=== Running tests with coverage ==="
	pytest tests/ --cov=baseball --cov-report=html --cov-report=term

# -------------------------------------------------------------------
# Cleanup
# -------------------------------------------------------------------
clean:
	@echo "=== Cleaning up ==="
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf htmlcov/ .pytest_cache/ .ruff_cache/ 2>/dev/null || true
	@echo "=== Cleanup complete ==="

# -------------------------------------------------------------------
# Feature marts
# -------------------------------------------------------------------
feature-marts:
	@echo "Running feature‑mart migrations..."
	$(PYTHON) scripts/migrate_feature_marts.py

# -------------------------------------------------------------------
# Database
# -------------------------------------------------------------------
db-migrate:
	@echo "=== Running database migrations ==="
	$(PYTHON) scripts/migrate.py

db-refresh:
	@echo "=== Refreshing materialized views ==="
	psql -d retrosheet -f sql/maintenance/refresh_all_views.sql

.PHONY: lint lint-fix format imports quality test test-unit test-integration test-betting test-ingestion test-live coverage clean feature-marts db-migrate db-refresh