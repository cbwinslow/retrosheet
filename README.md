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

# Install Python dependencies
pip install -r requirements.txt

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

2. **Run the initial schema migrations** – the `scripts/warehouse.py init-db` command will apply all SQL files in `sql/` in the correct order.

   ```bash
   python3 scripts/warehouse.py init-db
   ```

3. Verify the connection:

   ```bash
   python3 scripts/check_db_connection.py
   ```

   The script should exit with code `0` and print a success message.

### Running the Warehouse Build

The canonical rebuild order is encapsulated in `scripts/rebuild_warehouse.sh`. For a full historical + live setup:

```bash
YEARS=2000-2025 ./scripts/rebuild_warehouse.sh
```

The script performs the following steps:

1. **Canonical path validation** – Checks for forbidden prototype directories (`EdgeForge`, `mlb_features`, `mlb_models`, `mlb_enhanced`)
2. **Dependency check** – `scripts/warehouse.py check-deps`
3. **Retrosheet fetch** – `scripts/warehouse.py fetch-retrosheet` (skipped by default unless `FETCH_RETROSHEET=1`)
4. **Database initialization** – `scripts/warehouse.py init-db`
5. **Chadwick extraction** – `scripts/warehouse.py extract-chadwick --years $YEARS --outputs all`
6. **Chadwick loading** – `scripts/warehouse.py load-chadwick --years $YEARS --outputs all`
7. **Core schema migrations** – Sequential SQL migrations for games, events, plate appearances
8. **MLB live data schema** – `sql/090_mlb_live_data.sql`, `sql/091_mlb_reference_raw.sql`
9. **MLB reference views** – `sql/095_mlb_reference_views.sql`
10. **Bridge tables** – `sql/100_bridge_tables.sql`
11. **Team resolution** – `sql/085_mlb_team_resolution.sql`
12. **Live core tables** – `sql/110_live_core_tables.sql`
13. **MLB play-by-play** – `sql/080_mlb_pbp.sql`
14. **Reference metadata** – `scripts/load_reference_metadata.py`
15. **Auxiliary metadata** – `scripts/load_auxiliary_retrosheet.py`
16. **Feature marts** – `sql/050_feature_marts.sql`, `sql/060_advanced_feature_marts.sql`, `sql/070_temporal_and_production_marts.sql`
17. **Interface workflows** – `sql/075_interface_workflows.sql`
18. **PA outcome models** – `sql/076_plate_appearance_outcome_model.sql`, `sql/078_plate_appearance_outcome_grouped.sql`
19. **Probability evaluation** – `sql/079_probability_evaluation_reports.sql`, `sql/081_probability_calibration_artifacts.sql`
20. **Count-state features** – `sql/082_count_state_feature_marts.sql`
21. **Live prediction logging** – `sql/083_live_prediction_logging.sql`
22. **Half-inning examples** – `sql/080_half_inning_examples.sql`
23. **Inference optimization** – `sql/120_inference_optimization.sql`, `sql/121_inference_functions.sql`
24. **Live PA feature parity** – `sql/122_live_pa_feature_parity.sql`
25. **Analysis views** – `sql/130_analysis_views.sql`
26. **Query monitor** – Starts FastAPI query monitor on port 8000

**Environment variables:**
- `YEARS` – Year range for historical data (default: `2000-2025`)
- `PGHOST`, `PGPORT`, `PGDATABASE` – PostgreSQL connection (default: `localhost:5432/retrosheet`)
- `FETCH_RETROSHEET` – Set to `1` to force fresh Retrosheet download

---

## Data Ingestion Pipelines

### Historical Retrosheet Data

* **Fetching** – `scripts/warehouse.py fetch-retrosheet` downloads the yearly `.EVN` and `.ROS` archives from the Retrosheet website.
* **Extraction** – `scripts/warehouse.py extract-chadwick --years 2000-2025 --outputs all` runs the Chadwick CLI with `-n` to generate column‑named CSVs stored under `raw_retrosheet/`.
* **Loading** – `scripts/warehouse.py load-chadwick` bulk‑loads the CSVs into the `core` schema using `COPY` for speed.

### Live MLB Data

Live ingestion is split into discovery, download, and transformation:

1. **Schedule discovery** – `python3 scripts/fetch_mlb_schedule.py --yesterday` identifies games that have started/completed.
2. **Game ingestion** – `python3 scripts/warehouse.py fetch-live-game --game-pk <GAME_PK>` stores the raw JSON payload in `raw_mlb.live_feed_snapshots`.
3. **Transformation** – `python3 scripts/transform_live_game.py --game-pk <GAME_PK>` maps the live payload to the canonical `core.live_*` tables, applying bridge‑table ID translation.
4. **Batch processing** – `python3 scripts/ingest_live_games.py --schedule` orchestrates steps 1‑3 for all discovered games, handling duplicates and errors.

All live‑data tables are **additive** – historical rows are never modified.

---

## Bridge Tables & ID Mapping

The bridge layer enables seamless joins between Retrosheet IDs, MLB IDs, and other public identifiers (e.g., Baseball‑Reference).  It is populated by `scripts/populate_bridge_tables.py`, which downloads the **Chadwick Bureau Register** and inserts rows into:

* `bridge.player_xref`
* `bridge.team_xref`

These tables are referenced by the core transformation scripts and by analysis views.

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

The modeling pipeline lives under `scripts/` and is driven by the **feature marts**:

1. **Feature extraction** – `scripts/train_models.py --feature-set enriched` reads from `features.*` and writes model artifacts to `data/models/`.
2. **Model registry** – `models.model_registry` tracks versions, hyper‑parameters, and an `is_active` flag.
3. **Promotion** – `scripts/promote_best_models.py` flips the `is_active` flag after validation.
4. **Live inference** – the Next.js API routes in `baseball-chatbot-ui/app/api/` query `core.live_*` and the active model to return win probabilities.

All model training is reproducible via the `scripts/cross_validate_models.py` and `scripts/sweep_hyperparameters.py` utilities.

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `warehouse.py` | High‑level orchestration (check‑deps, fetch‑retrosheet, extract‑chadwick, load‑chadwick, fetch‑live‑game). |
| `populate_bridge_tables.py` | Populate `bridge.*` mappings. |
| `load_reference_metadata.py` | Back‑fill player handedness, update reference tables. |
| `load_auxiliary_retrosheet.py` | Load rosters, All‑Star games, umpires, coaches, ejections, relatives. |
| `transform_live_game.py` | Convert raw MLB JSON to canonical live schema. |
| `ingest_live_games.py` | Batch discovery + ingestion of live games. |
| `train_models.py` | Train ML models on feature marts. |
| `auto_promote_models.py` | Auto‑promote best performing model. |
| `benchmark_queries.py` | Run performance benchmarks on analysis views. |
| `analyze_pa_models.py` | Evaluate plate‑appearance outcome models. |
| `complete_mlb_ingestion.sh` | End‑to‑end script for a single day of live ingestion. |

Each script prints usage information when invoked with `-h`.

---

## Testing

The project includes comprehensive test coverage for core functionality:

### Unit Tests
- Baseball state transition logic (`retrosheet/simulation/test_baseball_state.py`)
- PA prediction service (`retrosheet/prediction/test_pa_service.py`)
- Calibration logic (`retrosheet/prediction/test_calibration.py`)
- Feature engineering (`retrosheet/prediction/test_feature_engineering.py`)
- Data transformation (`retrosheet/prediction/test_data_transformation.py`)

Run unit tests:
```bash
pytest retrosheet/prediction/test_*.py -v
pytest retrosheet/simulation/test_*.py -v
```

### Integration Tests
- Prediction serving workflows (`scripts/test_integration_prediction.py`)

Run integration tests:
```bash
pytest scripts/test_integration_prediction.py -v
```

### Validation Tests
- Model predictions against historical data (`scripts/test_validation_model_predictions.py`)
- Simulation outputs against historical distributions (`scripts/test_validation_simulation.py`)

Run validation tests:
```bash
pytest scripts/test_validation_*.py -v
```

### Data Quality Validation
- Schema validation, null rate monitoring, value range validation
- Referential integrity checks, temporal consistency validation

Run data quality validation:
```bash
python3 scripts/validate_data_quality.py
```

## Training & Onboarding

Comprehensive training materials are available for new contributors:

- **Warehouse Rebuild**: `docs/TRAINING_WAREHOUSE_REBUILD.md` - Step-by-step warehouse rebuild guide
- **Model Training**: `docs/TRAINING_MODEL_TRAINING.md` - Model training and evaluation guide
- **Prediction Serving**: `docs/TRAINING_PREDICTION_SERVING.md` - Prediction serving guide
- **Troubleshooting**: `docs/TROUBLESHOOTING.md` - Common issues and solutions
- **FAQ**: `docs/FAQ.md` - Frequently asked questions
- **Contributor Onboarding**: `docs/CONTRIBUTOR_ONBOARDING.md` - New contributor guide

## Quality & Monitoring

### Data Quality SLAs
- Schema validation SLAs defined in `docs/DATA_QUALITY_SLAs.md`
- Null rate SLAs: 5% for non-critical, 0% for critical fields
- Value range SLAs: 0 out-of-range values
- Referential integrity SLAs: 0% orphan rate

### Reliability Dashboard
- Model calibration metrics (ECE, confidence gaps)
- Feature null rates monitoring
- Prediction latency tracking
- Drift detection (feature drift, prediction drift)
- Design documented in `docs/RELIABILITY_DASHBOARD.md`

### Performance Optimization
- Model loading optimization (caching, lazy loading)
- Database query optimization (indexes, connection pooling)
- Prediction inference optimization (batch processing, vectorization)
- Calibration optimization (lookup tables, pre-computation)
- Documented in `docs/PERFORMANCE_OPTIMIZATION.md`

## Simulation

The project includes a baseball state transition engine for simulation and odds calculation:

- State machine in `retrosheet/simulation/baseball_state.py`
- Handles base occupancy, out count, run scoring, lineup progression
- Documented in `docs/MLB_SIMULATION.md`

Usage:
```python
from retrosheet.simulation.baseball_state import BaseballState, apply_event

state = BaseballState(bases=0, outs=0, home_score=0, away_score=0, inning=1)
new_state = apply_event(state, event_type='single')
```

## Market Integration (Design)

Market comparison layer design for comparing model predictions with public prediction markets:

- Market snapshot tables (`sql/125_market_snapshot_tables.sql`)
- Model edge comparison views (`sql/126_model_edge_comparison.sql`)
- Architecture documented in `docs/MARKET_INTEGRATION.md`

Note: This is currently in design phase; requires market data ingestion for implementation.

## Testing

Unit and integration tests live under `tests/`.  Run them with:

```bash
pytest
```

The test suite covers:

* Data loading correctness (`tests/test_loaders.py`).
* Bridge‑table integrity (`tests/test_bridge.py`).
* Feature‑mart calculations (`tests/test_features.py`).
* Model training pipelines (`tests/test_training.py`).

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
