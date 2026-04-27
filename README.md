# Retrosheet Prediction Warehouse

**Table of Contents**
1. [Project Overview](#project-overview)
2. [Architecture & Data Layers](#architecture--data-layers)
3. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Installation](#installation)
   - [Database Setup](#database-setup)
   - [Running the Warehouse Build](#running-the-warehouse-build)
4. [Data Ingestion Pipelines](#data-ingestion-pipelines)
   - [Historical Retrosheet Data](#historical-retrosheet-data)
   - [Live MLB Data](#live-mlb-data)
5. [Bridge Tables & ID Mapping](#bridge-tables--id-mapping)
6. [Core & Feature Schemas](#core--feature-schemas)
7. [Analysis Views](#analysis-views)
8. [Modeling & Prediction Engine](#modeling--prediction-engine)
9. [Scripts Reference](#scripts-reference)
10. [Testing](#testing)
11. [Deployment & Interface](#deployment--interface)
12. [Contributing](#contributing)
13. [License](#license)

---

## Project Overview

The **Retrosheet Prediction Warehouse** is a reproducible, end‑to‑end data platform that ingests **historical baseball event data** from the open‑source **Retrosheet** project (via the **Chadwick** parsing tools) and **live game data** from the **MLB Stats API / GUMBO**.  It normalises, enriches, and stores the data in a PostgreSQL warehouse, exposing **ML‑ready feature marts** and **prediction tables** that can be used to train and serve win‑probability models.

Key goals:

* Preserve raw source payloads (no destructive overwrites).
* Provide a clean separation between historical and live data sources.
* Offer a set of **canonical core tables** (`core.*`) that present a unified view of game state.
* Build **feature marts** (`features.*`) for model training and inference.
* Enable **back‑testing** and **live‑prediction** pipelines.
* Keep the entire workflow reproducible from a clean checkout.

The repository follows the conventions described in `docs/agents/AGENTS.md` and the detailed design documents under `docs/`.

---

## Architecture & Data Layers

| Layer | Description | Primary Schemas |
|-------|-------------|-----------------|
| `raw_retrosheet` | Source‑preserved Chadwick extracts and reference tables from the Retrosheet archive. | `raw_retrosheet.*` |
| `raw_mlb` | Source‑preserved JSON snapshots from the MLB Stats API (schedule, live feeds, reference endpoints). | `raw_mlb.*` |
| `bridge` | Cross‑reference tables that map Retrosheet IDs ↔ MLB IDs ↔ other public identifiers. | `bridge.player_xref`, `bridge.team_xref` |
| `core` | Canonical, typed entities (games, events, plate appearances) shared by both historical and live sources. | `core.games`, `core.events`, `core.plate_appearances`, `core.live_games`, `core.live_events` |
| `features` | ML‑ready feature marts, materialised views, and training tables. | `features.*` |
| `predictions` | Model output tables, back‑test results, and live prediction snapshots. | `predictions.*` |
| `analysis` | Union views that combine historical and live data for ad‑hoc querying. | `analysis.combined_*` |

The separation ensures that raw payloads are never overwritten and that any schema changes are additive (migrations, not destructive ALTERs).

---

## Getting Started

### Prerequisites

* **Python ≥3.10** (managed via the repository's virtual environment – see `scripts/agent_adapter.py`).
* **PostgreSQL 14+** – default local database name is `retrosheet` on port `5432`. Override with `DATABASE_URL` or standard `PG*` env vars.
* **Node.js ≥18** (for the Next.js UI in `baseball-chatbot-ui`).
* **Chadwick** command‑line tools (`cwevent`, `cwgame`, `cwdaily`, `cwsub`, `cwcomment`). Install via `conda`/`brew` or from source – see `docs/agents/PROCEDURES.md`.
* **Git LFS** is **not** required – large binary assets are stored outside the repo.

### Installation

```bash
# Clone the repo (already done) and cd into it
cd /home/cbwinslow/workspace/retrosheet

# Create and activate the Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies (including the baseball CLI)
pip install -r requirements.txt
# Or with uv (recommended):
# uv pip install -r requirements.txt

# Install Node dependencies for the UI
cd baseball-chatbot-ui
npm install
cd ..
```

### Database Setup

1. **Create the database** (if it does not exist):

   ```bash
   createdb retrosheet
   ```

2. **Run the initial schema migrations** – the `baseball admin init` command will apply all SQL files in `sql/` in the correct order.

   ```bash
   baseball admin init
   ```

3. Verify the connection:

   ```bash
   baseball doctor
   ```

   The script should exit with code `0` and print a success message.

### Running the Warehouse Build

The canonical rebuild order is encapsulated in the `baseball` CLI.  For a full historical + live setup:

```bash
# Run the complete historical pipeline
baseball pipeline run --pipeline historical --year 2024

# Or run individual source adapters
baseball retrosheet download --years 2000-2024
baseball retrosheet ingest --years 2000-2024

# For live data ingestion
baseball live watch
```

**Pipeline commands available:**

| Pipeline | Description | Command |
|----------|-------------|---------|
| `daily` | Daily data ingestion and feature updates | `baseball pipeline run --pipeline daily` |
| `historical` | Historical data for a specific season | `baseball pipeline run --pipeline historical --year 2024` |
| `live` | Live game tracking and predictions | `baseball pipeline run --pipeline live --date 2026-04-27` |
| `feature_building` | Build all ML features | `baseball pipeline run --pipeline feature_building` |

**Individual source adapters:**

| Source | Commands |
|--------|----------|
| Retrosheet | `baseball retrosheet download/ingest/validate` |
| MLB Stats API | `baseball mlb download/ingest/validate/today` |
| Statcast | `baseball statcast download/ingest/validate` |
| ESPN | `baseball espn download/ingest/validate` |
| Lahman | `baseball lahman download/ingest/validate` |

---

## Data Ingestion Pipelines

### Historical Retrosheet Data

* **Fetching** – `baseball retrosheet download --years 2000-2024` downloads the yearly `.EVN` and `.ROS` archives from the Retrosheet website.
* **Extraction** – Automatically handled by the `RetrosheetSource` adapter.
* **Loading** – `baseball retrosheet ingest --years 2000-2024` bulk‑loads the data into the `core` schema using `COPY` for speed.

### Live MLB Data

Live ingestion is handled by the `LiveMlbSource` adapter:

1. **Schedule discovery** – `baseball mlb today` identifies games happening today.
2. **Game ingestion** – `baseball live watch` polls live games and stores raw JSON in `raw_mlb.live_feed_snapshots`.
3. **Transformation** – Automatically maps live payloads to `core.live_*` tables.
4. **Batch processing** – `baseball live poll` orchestrates discovery and ingestion for all active games.

All live‑data tables are **additive** – historical rows are never modified.

---

## Bridge Tables & ID Mapping

The bridge layer enables seamless joins between Retrosheet IDs, MLB IDs, and other public identifiers (e.g., Baseball‑Reference).  It is populated by the `baseball bridge` commands, which download the **Chadwick Bureau Register** and insert rows into:

* `bridge.player_xref`
* `bridge.team_xref`
* `bridge.game_xref`

**Bridge CLI commands:**

```bash
# Resolve an entity ID across sources
baseball bridge resolve --entity-type player --canonical-id 12345

# Populate bridge tables from Chadwick register
baseball bridge populate --source chadwick
```

---

## Core & Feature Schemas

### Core Tables (`core.*`)

| Table | Description |
|-------|-------------|
| `games` | One row per game (historical). |
| `events` | Play‑by‑play rows from Chadwick (`cwevent`). |
| `plate_appearances` | Batter‑level rows derived from events. |
| `live_games` | Canonical live‑game rows (MLB API). |
| `live_events` | Live play‑by‑play rows, mirroring `events`. |

All core tables include **foreign‑key constraints** to the bridge tables and **typed columns** (dates, integers, enums) as defined in `docs/CORE_SCHEMA.md`.

### Feature Marts (`features.*`)

Feature marts are materialised views that aggregate historical statistics, rolling averages, and contextual signals.  They are defined in:

* `sql/050_feature_marts.sql` – baseline features (season‑to‑date stats, park factors, etc.)
* `sql/060_advanced_feature_marts.sql` – career‑level, matchup, and temporal features.
* `sql/070_temporal_and_production_marts.sql` – team rest, travel, and production windows.

Each mart follows the **no‑leakage rule**: the feature for a given game uses data from **prior seasons** (`feature_season = game_season + 1`).

---

## Analysis Views

Unified views live under the `analysis` schema and are intended for ad‑hoc querying, back‑testing, and reporting:

* `analysis.combined_games` – `UNION ALL` of `core.games` and `core.live_games`.
* `analysis.combined_events` – same for events.
* `analysis.combined_plate_appearances` – same for plate appearances.
* Helper functions such as `analysis.get_data_source_stats()` and `analysis.get_recent_games(days_back)` provide quick diagnostics.

---

## Modeling & Prediction Engine

The modeling pipeline is driven by the **feature marts** and managed via the `baseball` CLI:

1. **Feature extraction** – `baseball features compute --season 2024` builds features from `features.*` tables.
2. **Model training** – `baseball models train --model-type win_probability` trains models and writes artifacts to `data/models/`.
3. **Model registry** – `models.model_registry` tracks versions, hyper‑parameters, and an `is_active` flag.
4. **Live predictions** – `baseball live predict --game-pk 12345` queries `core.live_*` and the active model to return win probabilities.
5. **Chatbot UI** – The Next.js app in `baseball-chatbot-ui/` provides a chat interface and real‑time visualisation.

**Model CLI commands:**

```bash
# List available models
baseball models list

# Train a model (dry-run to preview)
baseball models train --model-type win_probability --dry-run

# Predict a single game
baseball predict game --game-pk 12345

# Predict today's games
baseball predict today
```

---

## CLI Reference

The unified `baseball` CLI replaces the individual scripts.  All commands support `--help`.

### Top-level Commands

| Command | Purpose |
|---------|---------|
| `baseball doctor` | Check system health and dependencies |
| `baseball status` | Show recent activity and pipeline runs |

### Source Adapters

| Command | Purpose |
|---------|---------|
| `baseball retrosheet download --years 2000-2024` | Download Retrosheet event files |
| `baseball retrosheet ingest --years 2000-2024` | Ingest into core schema |
| `baseball mlb today` | List today's MLB games |
| `baseball mlb download --date 2026-04-27` | Download MLB data |
| `baseball statcast download --start 2026-04-01 --end 2026-04-27` | Download Statcast data |
| `baseball espn download --seasons 2024` | Download ESPN data |
| `baseball lahman download` | Download Lahman database |

### Pipeline Commands

| Command | Purpose |
|---------|---------|
| `baseball pipeline list` | Show available pipelines |
| `baseball pipeline run --pipeline daily` | Run a pipeline |
| `baseball pipeline run --pipeline historical --year 2024` | Run historical backfill |
| `baseball pipeline status` | Show recent pipeline runs |

### Bridge Commands

| Command | Purpose |
|---------|---------|
| `baseball bridge resolve --entity-type player --canonical-id 12345` | Resolve ID across sources |
| `baseball bridge populate --source chadwick` | Populate bridge tables |

### Feature Commands

| Command | Purpose |
|---------|---------|
| `baseball features list` | List feature calculators |
| `baseball features compute --season 2024` | Compute features for season |
| `baseball features show --game-pk 12345` | Display features for game |

### Model Commands

| Command | Purpose |
|---------|---------|
| `baseball models list` | List available models |
| `baseball models train --model-type win_probability` | Train a model |

### Live Commands

| Command | Purpose |
|---------|---------|
| `baseball live games` | Show live games |
| `baseball live watch` | Watch live games in real-time |
| `baseball live poll` | Poll for game updates |
| `baseball live predict --game-pk 12345` | Generate prediction for game |
| `baseball live server` | Start WebSocket prediction server |

### Legacy Scripts

Original scripts have been moved to `scripts_legacy/` and are preserved for reference.  They are **not** actively maintained.  Use the CLI commands above for all new work.

---

## Testing

The project has a comprehensive test suite with 160+ tests covering unit, integration, E2E, compatibility, and functionality testing.

### Running Tests

```bash
# Run all tests
uv run python -m pytest tests/ -v

# Run specific test categories
uv run python -m pytest tests/unit/ -v
uv run python -m pytest tests/integration/ -v
uv run python -m pytest tests/e2e/ -v

# Run with markers
uv run python -m pytest -m unit -v
uv run python -m pytest -m integration -v
uv run python -m pytest -m e2e -v

# Run the comprehensive test runner
uv run python tests/run_tests.py --all --verbose
```

### Test Categories

| Category | Location | Count | Coverage |
|----------|----------|-------|----------|
| **Unit Tests** | `tests/unit/` | 100+ | Core classes, feature calculators, pipeline service |
| **Integration Tests** | `tests/integration/` | 20+ | Component integration, data flow |
| **E2E Tests** | `tests/e2e/` | 15+ | Full pipelines with database |
| **Compatibility** | `tests/unit/test_compatibility.py` | 15 | Python/OS/DB compatibility |
| **Scripts** | `tests/unit/test_scripts.py` | 20 | Script validation |
| **Functionality** | `tests/integration/test_functionality.py` | 25 | Comprehensive workflows |

### Key Test Files

- `tests/unit/test_features_base.py` – FeatureConfig, GameState, FeatureResult
- `tests/unit/test_win_expectancy.py` – WinExpectancyCalculator
- `tests/unit/test_leverage_index.py` – LeverageIndexCalculator
- `tests/unit/test_pipeline.py` – Pipeline service
- `tests/e2e/test_features_e2e.py` – End-to-end feature pipeline

### Benchmarking

Performance tests with timing and memory profiling:

```bash
# Run benchmarks
uv run python -m pytest tests/unit/test_compatibility.py::TestPerformanceBenchmarks -v
```

Benchmark results are logged to `logs/benchmarks/` in JSONL format.

---

## Deployment & Interface

The user‑facing chatbot UI is a **Next.js** application located in `baseball-chatbot-ui/`.  It provides:

* A chat interface that queries the warehouse via API routes.
* Real‑time win‑probability visualisation for live games.
* Historical query tools for back‑testing.

To run the UI locally:

```bash
cd baseball-chatbot-ui
npm run dev
```

For production, the recommended deployment target is **Vercel** (see `docs/agents/PROJECT_OBJECTIVES.md` for a Vercel‑specific guide).  Environment variables required by the API routes:

* `DATABASE_URL` – PostgreSQL connection string.
* `MODEL_REGISTRY_PATH` – Path to the active model artifact.
* `MLB_API_KEY` – Secret for MLB Stats API access (stored in Vercel env).

---

## Contributing

Please read the following before contributing:

* **Documentation** – Keep `README.md`, `docs/agents/*.md`, and `AGENTS.md` up‑to‑date.
* **SQL migrations** – Add new tables via additive `CREATE TABLE` statements; avoid destructive `DROP/ALTER` unless absolutely necessary and documented in `docs/agents/FILE_INVENTORY.md`.
* **Code style** – Follow the project's `flake8` and `black` configuration (`pyproject.toml`).
* **Issue workflow** – Every new issue must contain a detailed description and link to relevant docs.  Use the **Issue Linking Policy** described in `AGENTS.md`.
* **Pull‑request process** – Open a PR against `master`, run the CI pipeline, and address all review comments before merging.

---

## License

This project is licensed under the **MIT License** – see the `LICENSE` file for details.

---

*Generated on $(date '+%Y-%m-%d') by the Retrosheet Prediction Warehouse documentation generator.*
