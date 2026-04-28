--
— File: docs/dev/TOOL_SETUP_GUIDE.md
— Purpose: Comprehensive guide for installing and configuring development tools
— Author: Agent KiloSwift
— Date: 2026-04-27
—

# Development Tools Setup Guide

This guide covers installation and configuration of all development,
testing, and analysis tools for the Retrosheet prediction warehouse.

## Table of Contents

1. [PostgreSQL Extensions](#postgresql-extensions)
2. [Testing Frameworks](#testing-frameworks)
3. [Code Quality & Security](#code-quality--security)
4. [Vector Similarity Search](#vector-similarity-search)
5. [Code Search & Navigation](#code-search--navigation)
6. [Visualization & Analysis](#visualization--analysis)

---

## PostgreSQL Extensions

### Overview

Our warehouse uses PostgreSQL extensions to enhance performance and capabilities.
We recommend installing core extensions first, then optional ones as needed.

### Installation Methods

#### Method A: SQL Scripts (Automated)

We provide SQL installation scripts in `sql/maintenance/`:

```bash
# Install all extensions via master script
psql -f sql/maintenance/999_master_installation.sql

# Or install individually:
psql -f sql/maintenance/002_install_pg_cron.sql
psql -f sql/maintenance/003_install_pg_stat_statements.sql
psql -f sql/maintenance/004_install_pl_python3u.sql
psql -f sql/maintenance/005_install_pgvector.sql
```

#### Method B: psql Direct Commands

```sql
-- Connect to your database
psql -d retrosheet

-- Install extensions
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS plpython3u;
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify
SELECT * FROM pg_extension WHERE extname IN ('pg_cron', 'pg_stat_statements', 'plpython3u', 'vector');
```

#### Method C: Check & Install Script

Use the Python helper to check installation status:

```bash
uv run python scripts/check_extensions.py
```

### Extension Reference

| Extension | Priority | Purpose | Installation Command |
|-----------|----------|---------|---------------------|
| pg_cron | HIGH | Job scheduling within PostgreSQL | `CREATE EXTENSION pg_cron;` |
| pg_stat_statements | HIGH | Query performance monitoring | `CREATE EXTENSION pg_stat_statements;` |
| plpython3u | MEDIUM | Python functions within SQL | `CREATE EXTENSION plpython3u;` |
| pgvector | HIGH | Vector similarity search | `CREATE EXTENSION vector;` |
| postgis | LOW | Geospatial queries | `CREATE EXTENSION postgis;` |
| timescaledb | LOW | Time-series optimizations | `CREATE EXTENSION timescaledb;` |

See detailed research in `docs/POSTGRESQL_EXTENSIONS_RESEARCH.md`.

---

## Testing Frameworks

### pgTAP (Database Unit Testing)

**[Status: Initial Setup Complete]**

pgTAP provides TAP-compliant unit testing for PostgreSQL. We use it to test:
- Table schemas, constraints, and indexes
- Stored procedures and functions
- Triggers and views
- Data integrity constraints

#### Installation

```bash
# Install pgTAP extension
psql -d retrosheet -f sql/test/003_install_pgtap.sql
```

This installs pgTAP and creates helper functions:
- `public.run_schema_tests(schema_name)` - Run all tests in a schema
- `public.has_pgtap_tests(schema_name)` - Check if tests exist

#### Writing pgTAP Tests

Create SQL test files in `sql/test/` following conventions:

```sql
--
— File: sql/test/030_pgtap_my_feature.sql
— Purpose: Test my feature tables and functions
—

SET search_path TO my_schema, public;

SELECT plan(10);  -- Declare we expect 10 tests

-- Test table exists
SELECT has_table('my_schema', 'my_table', 'my_table exists');

-- Test column exists with correct type
SELECT col_is_present('my_schema', 'my_table', 'my_column', 'my_column column exists');
SELECT col_type_is('my_schema', 'my_table', 'my_column', 'INTEGER', 'my_column is INTEGER');

-- Test NOT NULL constraint
SELECT col_is_not_null('my_schema', 'my_table', 'my_column', 'my_column is NOT NULL');

-- Test foreign key
SELECT fk_is_not_null('my_schema', 'my_table', 'other_table', 'foreign key is valid');

-- Finish and return results
SELECT * FROM finish();
```

#### Running pgTAP Tests

```bash
# Run all pgTAP tests (discovered automatically)
./scripts/test/run_pgtap.sh

# Run tests for specific schema
./scripts/test/run_pgtap.sh --schema core --verbose

# Run directly via psql
psql -d retrosheet -f sql/test/010_pgtap_core_tables.sql
psql -d retrosheet -f sql/test/020_pgtap_functions.sql

# Integration with pytest (runs automatically)
pytest tests/unit/test_pgtap_integration.py -v
```

#### pgTAP in CI

GitHub Actions workflow `.github/workflows/ci.yml` runs pgTAP tests on every push:

```yaml
- name: Run pgTAP tests
  run: |
    psql -f sql/test/003_install_pgtap.sql
    ./scripts/test/run_pgtap.sh --verbose
```

### pytest (Python Testing)

**[Status: Fully Configured]**

pytest is configured with `pytest.ini` and provides:
- 160+ unit, integration, and E2E tests
- Test coverage reporting
- Markers for test categorization
- Database fixtures

#### Running pytest

```bash
# All tests
uv run pytest tests/ -v

# By category
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
uv run pytest tests/e2e/ -v

# By marker
uv run pytest -m "unit and database" -v

# Coverage
uv run pytest --cov --cov-report=html
```

#### Adding Tests

Place tests in appropriate directory:
- `tests/unit/` - Isolated unit tests (mocked dependencies)
- `tests/integration/` - Tests with database integration
- `tests/e2e/` - Full pipeline tests (slower, more comprehensive)

See existing test files for patterns.

---

## Code Quality & Security

### CodeQL Security Analysis

**[Status: Initial Setup Complete]**

CodeQL is GitHub's code scanning tool that identifies security vulnerabilities
and quality issues.

#### What CodeQL Scans

- **Python**: SQL injection, XSS, path traversal, hardcoded secrets
- **JavaScript/TypeScript**: XSS, prototype pollution, regex DoS
- **SQL**: SQL injection patterns
- **Generic**: Credential leakage, weak cryptography

#### Running CodeQL

**Automatically via CI** (push/PR to main branch):

The workflow `.github/workflows/codeql-analysis.yml` runs on:
- Every push to `main`/`master`/`setup-complete`
- Every pull request to those branches
- Weekly scheduled scan (Monday 00:00 UTC)

Results appear in GitHub Security tab as "Code scanning alerts".

**Locally** (requires GitHub CLI and CodeQL CLI):

```bash
# Install CodeQL CLI
wget https://github.com/github/codeql-cli-binaries/releases/download/v2.14.0/codeql-linux64.zip
unzip codeql-linux64.zip
export PATH="$PWD/codeql/bin:$PATH"

# Clone CodeQL queries
git clone https://github.com/github/codeql.git

# Create database from code
codeql database create retrosheet-db --language=python --source-root=.

# Run analysis
codeql query run codeql/python/ql/src/Security/CWE-089.ql \
  --database=retrosheet-db --output=results.bqrs

# View results
codeql bqrs decode --format=csv --output=results.csv results.bqrs
```

**Via Docker** (easiest local):

```bash
docker run --rm -v $(pwd):/code -w /code \
  github/codeql-cli analyze /code --language=python --format=csv --output=results.csv
```

#### Customizing CodeQL

Configuration file: `.github/codeql/codeql-config.yml`

You can:
- Exclude specific queries
- Ignore certain paths (data/, tests/, .venv/)
- Adjust query packs

Additional Python-specific queries are in `.github/workflows/codeql-analysis.yml`.

### Bandit (Python Security Scanner)

Already integrated via CI workflow:

```bash
# Run locally
pip install bandit
bandit -r . -f html -o bandit-report.html
```

Configuration: via command line args or `.bandit` config file.

### pip-audit (Vulnerability Scanning)

```bash
pip install pip-audit
pip-audit --desc --format json
```

See `pyproject.toml` for dependency pinning strategy.

---

## Vector Similarity Search

### faiss-cpu

**[Status: Installation Helper Created]**

FAISS (Facebook AI Similarity Search) provides efficient vector similarity
search. Used for player similarity, pitch sequence search, clustering.

#### Installation

```bash
# CPU-only (simpler, works everywhere)
uv add faiss-cpu

# GPU-accelerated (requires CUDA)
uv add faiss-gpu
```

Verify installation:

```bash
uv run scripts/vector/install_faiss_check.py
```

#### Usage

```python
import faiss
import numpy as np

# Create index
dimension = 128
index = faiss.IndexFlatIP(dimension)  # Inner product = cosine for normalized vectors

# Add vectors (normalized unit vectors)
vectors = np.random.randn(1000, dimension).astype('float32')
faiss.normalize_L2(vectors)  # normalize to unit length
index.add(vectors)

# Search
query = np.random.randn(1, dimension).astype('float32')
faiss.normalize_L2(query)
distances, indices = index.search(query, k=10)

print("Top 10 similar players:")
for i, (idx, dist) in enumerate(zip(indices[0], distances[0]), 1):
    print(f"  {i}. player_id={idx} similarity={dist:.3f}")
```

#### Integration Scripts

- `scripts/vector/build_player_embeddings.py` - Build player embeddings from features
- `scripts/vector/similarity_search.py` - CLI for finding similar players/pitches
- `sql/vector/001_faiss_schema.sql` - pgvector table for persistent storage

See `docs/vector/FAISS_INTEGRATION.md` for full documentation.

### pgvector (PostgreSQL Extension)

Already covered in [PostgreSQL Extensions](#postgresql-extensions).

Use pgvector when:
- Embeddings should be persisted in the warehouse
- Search needs to operate on the latest data (no index reload)
- Dataset is too large to fit in app memory

Use FAISS when:
- Real-time inference with precomputed embeddings
- Need to run specialized index types (HNSW, PQ)
- Large-scale similarity search (>100K vectors)

---

## Code Search & Navigation

### Sourcegraph

**[Status: Local Setup Available]**

Sourcegraph provides powerful code search, reference finding, and code intelligence.

#### Quick Start

Start local Sourcegraph instance:

```bash
docker-compose -f docker-compose.sourcegraph.yml up -d
```

Access at http://localhost:7080 (admin/admin).

#### Configure Repository

1. Login as admin
2. Site admin → Add code host → GitHub
3. Enter: `github.com/cbwinslow/retrosheet`
4. Click "Sync now"
5. Wait for indexing (2-5 min)

#### Code Intelligence Upload

Every push to main triggers the GitHub Actions workflow
`.github/workflows/sourcegraph-code-intel.yml` that uploads LSIF data
to `sourcegraph.com` (requires `SOURCGRAPH_TOKEN` secret).

For local Sourcegraph, code intelligence is computed automatically.

#### Search Examples

```
# Find all calls to get_win_expectancy
repo:^github\.com/cbwinslow/retrosheet$ symbol:get_win_expectancy

# Find SQL queries in tests
repo:^github\.com/cbwinslow/retrosheet$ file:\.py$ pattern:SELECT.*FROM core

# Find all pytest fixtures
repo:github.com/cbwinslow/retrosheet type:function @pytest.fixture

# Use Cody (AI) for natural language search
"show me where we load Statcast data"
```

#### When to Use Sourcegraph

- Exploring unfamiliar codebase
- Finding all callers of a function
- Cross-repo reference finding (when we add more repos)
- Code review depth analysis

#### Alternatives

- **GitHub Search**: Basic search at github.com
- **Livegrep**: Faster grep-style searching, simpler
- **OpenGrok**: Self-hosted, less overhead
- **Sourcegraph Cloud**: Hosted SaaS at sourcegraph.com

---

## Visualization & Analysis

### Graphviz

**[Status: Integration Complete]**

Graphviz is used to generate diagrams of:
- Database schemas (ERDs)
- Code dependency graphs
- Query execution plans

#### Installation

```bash
# macOS
brew install graphviz

# Ubuntu/Debian
sudo apt-get install graphviz graphviz-dev

# Fedora
sudo dnf install graphviz graphviz-devel

# Windows
choco install graphviz
```

Python package:

```bash
uv add graphviz
```

#### Scripts

**1. Schema Diagram Generator**

```bash
# Generate ERD for core schema
uv run scripts/analysis/generate_schema_diagram.py \
    --schema core \
    --output docs/diagrams/core_schema.png

# Generate for multiple schemas
uv run scripts/analysis/generate_schema_diagram.py --schema bridge --format pdf
uv run scripts/analysis/generate_schema_diagram.py --schema features --show-sizes
```

Options:
- `--schema` - Schema name (required)
- `--output` - Output file path
- `--format` - png/pdf/svg (default: png)
- `--no-columns` - Exclude column details
- `--show-sizes` - Include table sizes

**2. Dependency Graph Generator**

```bash
# Python module dependency graph
uv run scripts/analysis/visualize_dependencies.py --type python --output python_deps.png

# SQL execution order graph
uv run scripts/analysis/visualize_dependencies.py --type sql --output sql_order.pdf

# Combined graph
uv run scripts/analysis/visualize_dependencies.py --type combined --output combined_deps.svg
```

**3. Query Plan Visualizer**

```bash
# Generate query plan diagram
uv run scripts/analysis/analyze_query_plan.py \
    --sql "SELECT * FROM core.games WHERE season=2024" \
    --explain --analyze \
    --output query_plan.png

# With buffer statistics
uv run scripts/analysis/analyze_query_plan.py \
    --sql "SELECT g.*, e.* FROM core.games g JOIN core.events e ON g.game_id = e.game_id" \
    --explain --analyze --buffers
```

Output shows:
- Node types (Seq Scan, Index Scan, Hash Join, etc.)
- Estimated vs actual rows (key for cardinality estimation issues)
- Total cost
- Buffer hits/misses

#### Integration with Documentation

Generated diagrams are automatically included in:
- `docs/DATABASE_CATALOG.md` (schema diagrams)
- `docs/ARCHITECTURE.md` (component diagrams)
- README.md (architecture section)

---

## Summary Table

| Tool | Purpose | Status | Primary Scripts |
|------|---------|--------|-----------------|
| pgTAP | Database unit testing | ✅ Installed | `sql/test/003_install_pgtap.sql`, `scripts/test/run_pgtap.sh` |
| pytest | Python testing | ✅ Configured | `pytest.ini`, `tests/` |
| CodeQL | Security scanning | ✅ CI Configured | `.github/workflows/codeql-analysis.yml` |
| Bandit | Python security | ✅ CI | (part of workflow) |
| pip-audit | Dependency vulns | ✅ CI | (part of workflow) |
| faiss-cpu | Vector similarity | ⏳ Setup | `scripts/vector/build_player_embeddings.py` |
| Sourcegraph | Code search | 📦 Local | `docker-compose.sourcegraph.yml` |
| Graphviz | Visualization | ✅ Scripts | `scripts/analysis/generate_schema_diagram.py` |

Legend:
- ✅ Complete
- 🚧 In Progress
- 📦 Available (ready to use)
- ⏳ Setup Pending

---

## Next Steps

1. Install all **required PostgreSQL extensions**:
   ```bash
   psql -f sql/maintenance/999_master_installation.sql
   ```

2. Run **pgTAP tests** to validate database state:
   ```bash
   ./scripts/test/run_pgtap.sh --verbose
   ```

3. Set up **Sourcegraph** locally (optional):
   ```bash
   docker-compose -f docker-compose.sourcegraph.yml up -d
   ```

4. Build **player embeddings** with FAISS:
   ```bash
   uv add faiss-cpu
   uv run scripts/vector/build_player_embeddings.py --season 2024 --output faiss
   ```

5. Generate **schema diagrams** for documentation:
   ```bash
   uv run scripts/analysis/generate_schema_diagram.py --schema core --output docs/diagrams/core.png
   ```
