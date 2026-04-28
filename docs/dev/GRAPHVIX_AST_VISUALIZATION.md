--
— File: docs/dev/GRAPHVIZ_AST_VISUALIZATION.md
— Purpose: Guide to using graphviz and AST analysis for codebase visualization
— Author: Agent KiloSwift
— Date: 2026-04-27
—

# Graphviz & AST Visualization Tools

## Overview

We use Graphviz for visualizing:
- **Database schemas** (ERDs showing tables, columns, relationships)
- **Code dependency graphs** (module import relationships)
- **Query execution plans** (EXPLAIN output as interactive diagrams)
- **Pipeline flow diagrams** (data flow through ingestion/feature/model steps)

## Quick Start

### 1. Install Graphviz CLI

```bash
# macOS
brew install graphviz

# Ubuntu/Debian
sudo apt-get install graphviz graphviz-dev

# Check installation
dot -V  # Should print version like "dot - graphviz version 2.50.0"
```

### 2. Install Python Package

```bash
# Already in dev dependencies (add to pyproject.toml if needed)
uv add graphviz
```

### 3. Generate a Diagram

```bash
# Generate core schema ERD
uv run scripts/analysis/generate_schema_diagram.py \
    --schema core \
    --output docs/diagrams/core_schema.png

# Generate combined dependencies graph
uv run scripts/analysis/visualize_dependencies.py \
    --type combined \
    --format pdf
```

---

## Scripts Reference

### 1. Schema Diagram Generator

**File:** `scripts/analysis/generate_schema_diagram.py`

Generates Entity-Relationship Diagrams (ERD) from PostgreSQL schema metadata.

**Usage:**

```bash
# Basic usage
uv run scripts/analysis/generate_schema_diagram.py \
    --schema core \
    --output core_schema.png

# With all options
uv run scripts/analysis/generate_schema_diagram.py \
    --schema features \
    --output docs/diagrams/features_schema.pdf \
    --format pdf \
    --show-sizes \
    --no-types  # hide data types for simpler view
```

**Parameters:**
- `--schema` - Schema name (required): `core`, `bridge`, `features`, `raw_retrosheet`, etc.
- `--output` - Output file path (extension determines format if --format omitted)
- `--format` - Output format: `png`, `pdf`, `svg`
- `--no-columns` - Exclude column details (simpler diagram)
- `--show-sizes` - Include table sizes in labels
- `--help` - Show all options

**Output:**
- PNG file (default) with fully labeled table nodes
- Foreign key relationships shown as directed edges
- Color-coded by table type (VIEW vs TABLE)

**Example Output:** (simplified)
```
┌─────────────────────┐     ┌──────────────────────┐
│   core.games        │     │  core.events         │
│ ─────────────────   │     │ ──────────────────── │
│ • game_id (PK)      │────▶│ • event_id (PK)      │
│ • game_pk (INDEX)   │     │ • game_id (FK →)     │
│ • season            │     │ • batter_id          │
│ • game_date         │     └──────────────────────┘
└─────────────────────┘
```

**Integration:** Generated diagrams are used in:
- `README.md` (architecture section)
- `docs/DATABASE_CATALOG.md`
- `docs/ARCHITECTURE.md`

---

### 2. Dependency Graph Generator

**File:** `scripts/analysis/visualize_dependencies.py`

Creates visual graphs of:
- Python import dependencies across modules
- SQL script execution order
- Combined cross-language dependencies

**Usage:**

```bash
# Python module dependency graph
uv run scripts/analysis/visualize_dependencies.py \
    --type python \
    --output python_deps.svg

# SQL script execution order (by numeric prefix)
uv run scripts/analysis/visualize_dependencies.py \
    --type sql \
    --output docs/diagrams/sql_order.pdf

# Combined view
uv run scripts/analysis/visualize_dependencies.py \
    --type combined \
    --output docs/diagrams/full_dependency_graph.png \
    --format png
```

**Parameters:**
- `--type` - Graph type: `python`, `sql`, `combined`
- `--output` - Output file path
- `--format` - Output format (png, pdf, svg)
- `--show` - Open image after generation (macOS: `open`, Linux: `xdg-open`)

**How it works:**
- Python: AST parsing extracts `import` and `from ... import` statements
- SQL: Sorts `.sql` files by numeric prefix (001_init.sql → 800_*)
- Combined: Overlays Python → SQL usage patterns (e.g., where scripts load SQL files)

**Example output nodes:**
```
baseball.cli           [main CLI entry point]
scripts.warehouse      [orchestration]
baseball.sources.mlb   [MLB API adapter]
sql/010_core_games.sql [schema]
```

---

### 3. Query Plan Visualizer

**File:** `scripts/analysis/analyze_query_plan.py`

Converts PostgreSQL `EXPLAIN (FORMAT JSON)` output into visual tree.

**Usage:**

```bash
# Simple explain
uv run scripts/analysis/analyze_query_plan.py \
    --sql "SELECT * FROM core.games WHERE season = 2024"

# Full analyze with actual stats and buffers
uv run scripts/analysis/analyze_query_plan.py \
    --sql "SELECT g.*, COUNT(*) FROM core.games g JOIN core.events e ON g.game_id = e.game_id GROUP BY g.game_id" \
    --explain --analyze --buffers \
    --output docs/query_plans/complex_join.png

# Save in multiple formats
uv run scripts/analysis/analyze_query_plan.py ... --format pdf
uv run scripts/analysis/analyze_query_plan.py ... --format svg
```

**Parameters:**
- `--sql` - SQL query to analyze (required)
- `--output` - Output image file (default: `query_plan.png`)
- `--analyze` - Include actual execution statistics (slower, but real data)
- `--buffers` - Include buffer hit/miss data
- `--format` - Output format

**Output:**
- Color-coded node boxes:
  - 🔴 **Red** - Seq Scan (may need index)
  - 🟢 **Green** - Index Scan (good)
  - **Blue** - Hash/Merge Join
  - **Purple** - Nested Loop
  - **Yellow** - Bitmap Scan
- Each node shows:
  - Estimated vs actual rows (check for estimation errors)
  - Total cost
  - Table/index names
  - Filter conditions

**When to use:**
- After adding a new index — verify it's used
- Diagnosing slow queries
- Understanding join order
- Teaching team about query optimization

**Example finding:**
```
⚠️  Actual Rows: 150,000 | Estimated: 5,000
→ Cardinality estimation mismatch; consider ANALYZE or extended statistics
```

---

## AST Analysis

### What is AST?

**Abstract Syntax Tree (AST)** is a tree representation of code structure.
Python's `ast` module parses source code into a tree of node objects.

Our AST scripts:
- Parse Python files to extract imports, function definitions, class hierarchies
- Build import dependency graphs
- Detect circular dependencies
- Calculate module complexity metrics

### AST-based Analysis Scripts

#### Dependency Analysis

**Script:** `scripts/analysis/visualize_dependencies.py`

Uses `ast.parse()` to extract import statements without executing code:

```python
import ast

with open('scripts/warehouse.py') as f:
    tree = ast.parse(f.read())

for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        print(f"Import: {node.names[0].name}")
    elif isinstance(node, ast.ImportFrom):
        print(f"From {node.module}: {[a.name for a in node.names]}")
```

This builds a directed acyclic graph (DAG) of dependencies.

#### Complexity Metrics

Add to `visualize_dependencies.py` or create new script:

```python
import ast

def get_complexity(filename: str) -> int:
    with open(filename) as f:
        tree = ast.parse(f.read())
    # Cyclomatic complexity ≈ # of branching nodes + 1
    return sum(1 for node in ast.walk(tree)
               if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler))) + 1
```

---

## Generating All Documentation Diagrams

Run this single command to update all schema diagrams in documentation:

```bash
#!/usr/bin/env bash
# scripts/update_documentation_diagrams.sh

SCHEMAS=("core" "bridge" "features" "raw_retrosheet" "raw_mlb")

for SCHEMA in "${SCHEMAS[@]}"; do
    echo "Generating diagram for $SCHEMA..."
    uv run scripts/analysis/generate_schema_diagram.py \
        --schema "$SCHEMA" \
        --output "docs/diagrams/${SCHEMA}_schema.png"
done

echo "✅ All diagrams updated"
```

---

## Troubleshooting

### Graphviz "dot not found"

```bash
# Verify dot is in PATH
which dot

# If not found, install:
brew install graphviz   # macOS
# or
sudo apt-get install graphviz  # Ubuntu/Debian

# Ensure Python can find it
export PATH="/usr/local/bin:$PATH"  # Add to ~/.bashrc or ~/.zshrc
```

### "No module named 'faiss'"

```bash
uv add faiss-cpu
# or if GPU available:
uv add faiss-gpu
```

### "Error: relationship 'xxx' does not exist" in schema diagram

This means the table or FK doesn't exist in the database yet. Run schema migrations first:

```bash
psql -d retrosheet -f sql/010_core_games_events.sql
```

### pgTAP tests failing

Make sure pgTAP is installed:

```bash
psql -d retrosheet -f sql/test/003_install_pgtap.sql
```

Then re-run:

```bash
./scripts/test/run_pgtap.sh --verbose
```

### Query plan visualization shows "Unknown node type"

Update Graphviz to latest version. Some node types (e.g., `Parallel Seq Scan`) require newer versions.

---

## Related Documentation

- `docs/POSTGRESQL_EXTENSIONS_RESEARCH.md` - Extension research
- `docs/agents/PROCEDURES.md` - Database procedures (some use pgTAP)
- `docs/agents/FILE_INVENTORY.md` - Inventory of all SQL test files
- `docs/dev/TOOL_SETUP_GUIDE.md` (this document) - Tool installation

---

## Maintenance

### Keep Tools Updated

```bash
# Update graphviz (system)
brew upgrade graphviz   # macOS
sudo apt-get upgrade graphviz  # Ubuntu

# Update Python packages
uv sync --all-extras --upgrade

# Check for new CodeQL queries
# CodeQL auto-updates via GitHub Actions
```

### Check Installation Status

```bash
# Check all PostgreSQL extensions (we provide helper)
uv run python scripts/check_extensions.py

# Check faiss
uv run python scripts/vector/install_faiss_check.py

# Check pytest coverage
uv run pytest --cov --cov-report=term-missing
```

---

## Contributing

When adding new visualization scripts:
1. Follow naming convention: `scripts/analysis/<purpose>_visualization.py`
2. Add proper shebang and docstring
3. Include `--help` documentation
4. Add entry to this guide
5. Add to `FILE_INVENTORY.md`
6. Mark as executable: `chmod +x`

When writing pgTAP tests:
1. Place in `sql/test/` with 3-digit prefix for ordering
2. Follow TAP convention: `SELECT plan(N);` and `SELECT * FROM finish();`
3. Comment each test clearly
4. Add to `PROCEDURES.md` section on testing
5. Document in `PROJECT_LOG.md`

---

**Last Updated:** 2026-04-27  
**Maintainer:** Agent KiloSwift  
**Status:** Initial setup complete; pytest & CodeQL CI integrated; FAISS & visualization ready for use
