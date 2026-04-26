# Migration Plan

**Purpose**

This document defines the phased migration plan for refactoring the cbwinslow/retrosheet repository into a clean, extensible baseball data platform centered around a unified `baseball` CLI, layered SQL architecture, reusable source adapters, and a reproducible feature/model pipeline.

The current repository already contains substantial working logic for Retrosheet parsing, multi-source ingestion, bridge/xref workflows, and SQL-based warehouse operations. The goal is to **preserve and reorganize** those assets rather than rewrite them from scratch.

---

## Goals

The migration should produce a platform that:

1. **Ingests historical baseball data, live MLB event data, and multiple enrichment sources** through a common interface
2. **Supports bridge/xref resolution** between source systems for players, teams, games, parks, umpires, coaches, and external IDs
3. **Builds canonical baseball entities and event-state tables** suitable for sabermetric analysis and predictive ML
4. **Supports real-time model inference** during active MLB games using live event data, with MLB live feed as primary source and ESPN as secondary/fallback
5. **Exposes an installable CLI** so users can run ingestion, validation, feature builds, and model workflows predictably
6. **Leaves room for future websocket delivery** and natural-language/chatbot interfaces over the baseball warehouse

---

## Non-Goals

This migration is **not** intended to:

- Rewrite working logic purely for stylistic reasons
- Solve every source, feature, and model in the first milestone
- Build the future chatbot interface now
- Introduce heavy orchestration frameworks prematurely
- Replace MLB live feeds with ESPN as the primary real-time engine

---

## Current State Summary

The repository currently contains:

- **`retrosheet/`** Python package with archive download, parsing, event/game logic, and helper modules — **core historical ingestion assets**
- **`scripts/`** tree with ingestion, bridge, external-data, and operational scripts for MLB live, ESPN, Statcast, Lahman, FanGraphs, Baseball Reference, weather, park factors, and bridge/xref workflows
- **`sql/`** tree with bridge, live, external, core, features, warehouse, analysis directories — partially staged warehouse architecture
- Operational artifacts: `README.md`, `Makefile`, `schema.prisma`, multiple planning documents

**Major weakness**: Implementation is spread across too many public entry points. Not lack of functionality — lack of a single clear architectural contract.

---

## Target Architecture

```
raw -> staging -> core -> bridge -> features -> models -> serving -> interfaces
```

**Layer Definitions:**

| Layer | Purpose |
|-------|---------|
| `raw` | Source-preserved payloads and source-native extracts |
| `staging` | Flattened, source-specific cleaned tables for deterministic transformation |
| `core` | Canonical baseball entities and event-state representations |
| `bridge` | Cross-source entity resolution and xref logic |
| `features` | Sabermetric and ML-ready feature tables |
| `models` | Model registry, training metadata, training data definitions, artifacts |
| `serving` | Low-latency outputs, denormalized read models, prediction tables |
| `interfaces` | CLI, future API, future websocket, future chatbot |

---

## Target Repository Layout

```
retrosheet/
  baseball/                    # NEW: Main package
    __init__.py
    cli.py                     # Typer CLI entry point
    app.py                     # Application container
    settings.py                # Configuration management
    logging.py                 # Structured logging
    core/                      # Shared infrastructure
      db.py
      sql_runner.py
      checkpoints.py
      filesystem.py
      http.py
      registry.py
      types.py
    sources/                   # Source adapters
      base.py
      retrosheet.py
      mlb.py
      espn.py
      statcast.py
      lahman.py
      fangraphs.py
      bref.py
      weather.py
      park_factors.py
    features/                  # Feature engineering
      base.py
      run_expectancy.py
      win_expectancy.py
      leverage.py
      matchup.py
      rolling_form.py
      bullpen.py
      live_state.py
    models/                    # ML pipeline
      base.py
      registry.py
      training.py
      inference.py
      backtest.py
    services/                  # Business logic layer
      bridge.py
      validation.py
      marts.py
      scheduler.py
      serving.py
      chatbot.py
  config/                      # Configuration files
    sources.yml
    pipelines.yml
    models.yml
  sql/                         # REORGANIZED SQL
    00_admin/
    10_raw/
    20_staging/
    30_core/
    40_bridge/
    50_features/
    60_models/
    70_serving/
    80_quality/
  docs/
    architecture.md
    sources.md
    keys_and_grains.md
    migration_map.md
    migration_backlog.md
    models.md
    agents/
  scripts_legacy/              # MOVED: Old scripts preserved
  tests/
```

---

## Public CLI Contract

**Target public interface**: Typer-based installable CLI named `baseball`, exposed through `pyproject.toml` using `[project.scripts]`.

### Required Command Family

```bash
# Diagnostics
baseball doctor
baseball status

# Retrosheet historical
baseball retrosheet download --year 2024
baseball retrosheet ingest --year 2024
baseball retrosheet validate --year 2024

# MLB live
baseball mlb download --date 2026-04-25 --team ATL
baseball mlb ingest --date 2026-04-25 --team ATL
baseball mlb stream --date 2026-04-25
baseball mlb validate --date 2026-04-25

# ESPN enrichment
baseball espn download --date 2026-04-25
baseball espn ingest --date 2026-04-25

# Statcast
baseball statcast download --start-date 2026-04-01 --end-date 2026-04-25
baseball statcast ingest --start-date 2026-04-01 --end-date 2026-04-25

# Bridge
baseball bridge build
baseball bridge validate

# Features
baseball features build --scope historical
baseball features build --scope live

# Models
baseball models train --model win_probability
baseball models predict --model win_probability --game-pk 777777
baseball models backtest --model win_probability --season 2025

# Pipelines
baseball pipeline run daily
baseball pipeline run historical --year 2024
baseball pipeline run live --date 2026-04-25
```

---

## Source Strategy

### Historical Primary
- **Retrosheet** for event/game history
- **Lahman/reference data** for enrichment

### Live Primary
- **MLB Stats API live feed** for active games and canonical current game state

### Live Secondary/Fallback
- **ESPN** public/hidden endpoints as enrichment and fallback layer

### Enrichment
- Statcast / Baseball Savant
- FanGraphs
- Baseball Reference
- Weather, park factors, rosters, and similar external data

---

## Real-Time Prediction Requirement

The architecture must support **low-latency in-game prediction loops**:

1. Poll live games from MLB
2. Persist raw live payloads
3. Process only changed events where possible
4. Update canonical game-state snapshots
5. Recompute affected live features
6. Score active models
7. Store predictions in serving tables

Design for later websocket or event-driven delivery, even if not implemented in first milestone.

---

## Database and SQL Strategy

### SQL Foldering

All SQL organized into numbered layers:

| Folder | Layer | Purpose |
|--------|-------|---------|
| `00_admin/` | Admin | Pipeline control, checkpoints, errors |
| `10_raw/` | Raw | Source-preserved payloads |
| `20_staging/` | Staging | Source-specific cleaned tables |
| `30_core/` | Core | Canonical baseball entities |
| `40_bridge/` | Bridge | Cross-source xref tables |
| `50_features/` | Features | ML-ready feature tables |
| `60_models/` | Models | Model registry, training metadata |
| `70_serving/` | Serving | Low-latency read models |
| `80_quality/` | Quality | Data quality checks |

### SQL Naming Convention

```
101_raw_mlb_live_feed.sql
202_stg_mlb_live_events.sql
303_core_game_state_snapshots.sql
405_bridge_players.sql
501_features_run_expectancy.sql
601_models_registry.sql
701_serving_live_predictions.sql
801_quality_rowcount_checks.sql
```

**Pattern**: `{layer_number}{sequence}_{layer}_{description}.sql`

### Materialized View Guidance

- Use PostgreSQL materialized views only where read-heavy workloads justify them
- Ensure unique indexes exist before using `REFRESH MATERIALIZED VIEW CONCURRENTLY`
- Prefer targeted summary tables or well-indexed serving tables over excessive MV usage when low-latency incremental updates needed

### Database Control and Idempotency

Create these administrative tables in `sql/00_admin/`:

- `pipeline_runs`
- `pipeline_checkpoints`
- `pipeline_errors`

Every ingest path must:
- Be safe to rerun
- Store checkpoints
- Deduplicate raw/staged data
- Use deterministic merge/upsert logic

---

## Sabermetric Feature Strategy

First feature layer must support:

- Run expectancy
- Win expectancy
- Leverage index
- Base-out state
- Inning and score differential
- Platoon state
- Park effects
- Rolling player form
- Bullpen usage/fatigue
- Times-through-order context

### Required Initial Feature Tables

- `features.run_expectancy_state`
- `features.win_expectancy_state`
- `features.leverage_index_state`
- `features.matchup_features`
- `features.live_game_state`

---

## Modeling Strategy

Add minimal but real model layer with:

- `models.registry`
- `models.training_runs`
- `models.artifacts`
- `predictions.game_live`
- `predictions.plate_appearance_live`
- `predictions.pitch_live`

### Initial Model Priorities

1. `win_probability`
2. `next_run_probability`
3. `plate_appearance_outcome`
4. Later: `pitch_outcome`

All models must be:
- Versioned
- Reproducible
- Backtestable on historical event-state data
- Protected against future-leakage in training and live scoring

---

## Migration Principles

1. **Preserve working code first**
2. **Wrap before rewriting**
3. **Move toward adapters and shared services**
4. **Avoid orphan scripts**
5. **Avoid duplicate downloader/parser/DB/SQL-runner logic**
6. **Leave a migration trail for every moved file**
7. **Keep changes incremental and reviewable**

---

## Required Documentation Deliverables

This migration must produce:

- `docs/architecture.md`
- `docs/sources.md`
- `docs/keys_and_grains.md`
- `docs/migration_map.md`
- `docs/migration_backlog.md`
- `docs/models.md`

Plus clean agent guidance:

- Top-level `AGENTS.md`
- `docs/agents/architecture_agent.md`
- `docs/agents/python_agent.md`
- `docs/agents/sql_agent.md`
- `docs/agents/ml_agent.md`
- `docs/agents/live_agent.md`
- `docs/agents/docs_agent.md`

---

## Migration Phases

### Phase 0 — Planning and Inventory

**Deliver:**
- `docs/migration_plan.md` (this document)
- `docs/migration_map.md`
- `docs/migration_backlog.md`
- `docs/architecture.md`
- `docs/keys_and_grains.md` skeleton

**No major code moves yet.**

### Phase 1 — Framework Foundation

**Deliver:**
- `baseball/` package skeleton
- Typer CLI shell in `baseball/cli.py`
- `pyproject.toml` console script entry for `baseball` CLI
- Shared core modules: `db.py`, `sql_runner.py`, `settings.py`, `logging.py`, `types.py`
- Admin SQL tables: `pipeline_runs`, `pipeline_checkpoints`, `pipeline_errors`
- `doctor` and `status` command stubs

### Phase 2 — Historical Wrapper

**Deliver:**
- `RetrosheetSource` adapter in `baseball/sources/retrosheet.py`
- Wrapping of existing `retrosheet/` package logic
- Migration of historical-related SQL into layer folders (`10_raw/`, `20_staging/`, `30_core/`)
- Compatibility wrappers for still-used legacy scripts
- CLI commands: `baseball retrosheet download/ingest/validate`

### Phase 3 — MLB Live Vertical Slice

**Deliver:**
- `MlbSource` adapter in `baseball/sources/mlb.py`
- Raw live feed persistence in `raw_mlb.live_feed_snapshots`
- Canonical live tables: `core.live_games`, `core.live_events`
- Event-state snapshots table
- `features.run_expectancy_state`
- `features.live_game_state`
- First live prediction path for `win_probability`
- CLI commands: `baseball mlb download/ingest/stream/validate`

### Phase 4 — ESPN + Statcast

**Deliver:**
- `EspnSource` adapter in `baseball/sources/espn.py`
- `StatcastSource` adapter in `baseball/sources/statcast.py`
- Bridge integration for ESPN/Statcast IDs
- Enrichment workflows
- Validation commands
- CLI commands: `baseball espn` and `baseball statcast`

### Phase 5 — Bridge Consolidation

**Deliver:**
- Bridge service layer in `baseball/services/bridge.py`
- Bridge SQL migration to `40_bridge/` folder
- Xref confidence and validation workflows
- Consistent bridge documentation
- CLI commands: `baseball bridge build/validate`

### Phase 6 — Feature and Model Expansion

**Deliver:**
- Win expectancy features: `features.win_expectancy_state`
- Leverage index features: `features.leverage_index_state`
- Matchup/rolling/bullpen features: `features.matchup_features`
- Next-run model: `models.next_run_probability`
- Plate-appearance model: `models.plate_appearance_outcome`
- Training-run tracking and backtesting framework
- CLI commands: `baseball features build` and `baseball models train/predict/backtest`

### Phase 7 — Serving and Interfaces

**Deliver:**
- Serving tables/views in `70_serving/`
- Low-latency read models
- Websocket-ready hooks for future implementation
- Chatbot-compatible query-safe design

---

## First Vertical Slice

The first end-to-end vertical slice to ship:

```bash
baseball mlb download --date TODAY
baseball mlb ingest --date TODAY
baseball features build --scope live
baseball models predict --model win_probability --game-pk <id>
```

This slice validates the architecture and unlocks the project's primary differentiator: **real-time baseball prediction from live game state**.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Accidental rewrite of working repo logic | Preserve existing scripts in `scripts_legacy/`; wrap before deleting; document old→new mappings in `docs/migration_map.md` |
| Source proliferation and duplicated paths | Canonical source adapter per source; prohibit new orphan scripts; centralize DB/HTTP/SQL execution |
| Live latency vs warehouse complexity | Separate raw/core/features/serving layers; use targeted serving tables and selective materialized views |
| Feature leakage in ML | Document offline vs online features; require backtesting; version training runs and feature sets |

---

## Success Criteria

The migration is successful when:

- [ ] The project installs and exposes a `baseball` CLI
- [ ] The repo is easier to navigate than before
- [ ] Working Retrosheet logic remains intact and wrapped
- [ ] Live MLB ingest works via a canonical path
- [ ] ESPN enrichment exists as a secondary layer
- [ ] Bridge workflows still function
- [ ] At least one sabermetric feature path is productionized
- [ ] At least one live model produces persisted predictions
- [ ] Docs and AGENTS guidance are clean and usable
- [ ] No new orphan scripts are introduced

---

## Immediate Next Step

Before coding major refactors, produce and review:

1. `docs/migration_map.md`
2. `docs/migration_backlog.md`
3. `docs/architecture.md`
4. `docs/keys_and_grains.md` skeleton

**Then begin Phase 1 only.**

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Migration Agent | Initial migration plan from conversation synthesis |
