# Retrosheet Prediction Warehouse

A reproducible, end-to-end baseball data platform with unified CLI, layered SQL architecture, and real-time prediction support.

## Project Overview

This project refactors cbwinslow/retrosheet into a clean, extensible baseball data platform with:

- **Unified CLI** - Single `baseball` command for all operations
- **Layered SQL** - Raw → Staging → Core → Bridge → Features → Models → Serving
- **Source adapters** - MLB Stats API, Retrosheet, Statcast, ESPN, Lahman
- **Bridge/xref resolution** - Cross-reference tables for entity ID mapping
- **Sabermetric features** - ML-ready feature marts (run expectancy, win expectancy, leverage)
- **ML modeling** - Reproducible model registry with training and inference
- **Real-time prediction** - Live game tracking and win probability models

## Architecture

The system follows a layered SQL architecture:

| Layer | Schema | Purpose |
|-------|--------|---------|
| `00_admin` | `admin.*` | Pipeline control, checkpoints, errors |
| `10_raw` | `raw_*.*` | Source-preserved payloads (MLB, ESPN, Statcast, etc.) |
| `20_staging` | `stg_*.*` | Flattened source data with deterministic uniqueness |
| `30_core` | `core.*` | Canonical baseball entities (games, events, players, parks) |
| `40_bridge` | `bridge.*` | Cross-reference tables (player_xref, team_xref, game_xref) |
| `50_features` | `features.*` | ML-ready feature marts (run_expectancy, live_game_state) |
| `60_models` | `models.*` | Model registry, training runs, artifacts |
| `70_serving` | `predictions.*` | Live prediction outputs and serving tables |
| `80_quality` | `quality.*` | Data quality checks and validation |

See [docs/architecture.md](docs/architecture.md) for detailed architecture specifications.

## Getting Started

### Prerequisites

- **Python ≥3.10**
- **PostgreSQL 14+** (default: `retrosheet` database on port 5432)
- **Chadwick** command-line tools (`cwevent`, `cwgame`, `cwdaily`, `cwsub`, `cwcomment`)

### Installation

```bash
# Clone and navigate
cd retrosheet

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
# Or with uv (recommended):
# uv pip install -r requirements.txt

# Create database
createdb retrosheet
```

### Initialize Database

```bash
# Run all SQL migrations in order
baseball admin init

# Verify connection
baseball doctor
```

## CLI Commands

The `baseball` CLI provides unified access to all operations:

### Source Adapters

```bash
# Retrosheet (historical)
baseball retrosheet download --years 2000-2024
baseball retrosheet ingest --years 2000-2024
baseball retrosheet validate --years 2000-2024

# MLB Stats API
baseball mlb download --seasons 2024
baseball mlb ingest --seasons 2024
baseball mlb validate --seasons 2024
baseball mlb today

# Statcast
baseball statcast download --seasons 2024
baseball statcast ingest --seasons 2024

# ESPN
baseball espn download --seasons 2024
baseball espn ingest --seasons 2024

# Lahman
baseball lahman download --tables teams batting
baseball lahman ingest --tables teams batting
```

### Live Data

```bash
# Watch live games
baseball live watch --game-pk 12345

# Poll live games
baseball live poll --date 2026-04-27

# Stream live feed
baseball mlb stream --interval 10
```

### Bridge/Xref

```bash
# Build bridge tables
baseball bridge build

# Resolve entity IDs
baseball bridge resolve --entity-type player --canonical-id 12345
baseball bridge lookup --source mlb --source-id 547043

# Validate bridge data
baseball bridge validate
```

### Features

```bash
# Build features
baseball features build --scope historical --season 2024
baseball features build --scope live

# Validate features
baseball features validate
```

### Models

```bash
# Train model
baseball models train --model-type win_probability --season 2024

# List models
baseball models list

# Predict
baseball predict game --game-pk 12345
baseball predict today
baseball predict batch --date 2026-04-27

# Backtest
baseball models backtest --model-type win_probability --season 2024
```

### Pipelines

```bash
# Run pipeline
baseball pipeline run --pipeline historical --year 2024
baseball pipeline run --pipeline live --date 2026-04-27
baseball pipeline run --pipeline feature_building

# List pipelines
baseball pipeline list

# Check status
baseball status
```

## Documentation

### Key Documents

| Document | Purpose |
|----------|---------|
| [AGENTS.md](AGENTS.md) | Project mission and agent guidelines |
| [docs/architecture.md](docs/architecture.md) | Layered architecture specification |
| [docs/migration_backlog.md](docs/migration_backlog.md) | Migration tasks and milestones (Milestones 0-13) |
| [docs/migration_map.md](docs/migration_map.md) | File mapping from old to new structure |
| [docs/keys_and_grains.md](docs/keys_and_grains.md) | Table grains, keys, and uniqueness strategies |
| [docs/ARCHIVED_DOCUMENTATION.md](docs/ARCHIVED_DOCUMENTATION.md) | List of archived outdated documentation |

### Agent-Specific Documentation

| Document | Purpose |
|----------|---------|
| [docs/agents/architecture_agent.md](docs/agents/architecture_agent.md) | Architecture rules and package structure |
| [docs/agents/python_agent.md](docs/agents/python_agent.md) | Python coding standards and patterns |
| [docs/agents/sql_agent.md](docs/agents/sql_agent.md) | SQL layer rules and naming conventions |
| [docs/agents/ml_agent.md](docs/agents/ml_agent.md) | ML modeling guidelines and feature rules |
| [docs/agents/live_agent.md](docs/agents/live_agent.md) | Live ingestion rules and performance guidelines |
| [docs/agents/docs_agent.md](docs/agents/docs_agent.md) | Documentation standards and update procedures |

### Additional Documentation

- [docs/agents/PROCEDURES.md](docs/agents/PROCEDURES.md) - Canonical workflows and procedures
- [docs/agents/FILE_INVENTORY.md](docs/agents/FILE_INVENTORY.md) - File inventory and organization
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Operational troubleshooting guide

## Migration Status

This project is undergoing a phased migration to the new `baseball` CLI architecture. See [docs/migration_backlog.md](docs/migration_backlog.md) for detailed task tracking across Milestones 0-13.

**Completed Milestones:**
- Milestone 0: Planning and contracts
- Milestone 1: Package and CLI foundation
- Milestone 2: Shared core services
- Milestone 3: Administrative SQL and control plane
- Milestone 4: Retrosheet historical adapter
- Milestone 5: MLB live source vertical slice
- Milestone 6: ESPN secondary live source
- Milestone 7: SQL reorganization
- Milestone 8: Bridge consolidation
- Milestone 9: External and enrichment sources
- Milestone 10: Sabermetric feature layer
- Milestone 11: ML model layer
- Milestone 12: Serving and performance layer
- Milestone 13: Documentation and cleanup

## Contributing

This repository follows the conventions described in [AGENTS.md](AGENTS.md) and the detailed agent documentation in [docs/agents/](docs/agents/).

Key principles:
- Preserve working logic before rewriting
- Do not create orphan scripts
- Reuse existing repo code whenever possible
- Keep Python modular and class-based
- Keep SQL layered and purpose-specific
- Document file moves in docs/migration_map.md
- Document table grains and keys in docs/keys_and_grains.md

## License

See LICENSE file for details.
