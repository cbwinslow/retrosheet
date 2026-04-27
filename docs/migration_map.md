# Migration Map

**Purpose**: This document maps current files to their new destinations in the target architecture. Use this as the source of truth for file moves, renames, and wrapping decisions.

---

## Legend

| Action | Meaning |
|--------|---------|
| **KEEP** | File stays in current location, no changes |
| **MOVE** | File relocated to new path |
| **WRAP** | Keep original, create adapter/wrapper in new location |
| **SPLIT** | File functionality split across multiple new files |
| **MERGE** | File merged with other files into new location |
| **ARCHIVE** | Move to `scripts_legacy/` or delete after migration |

---

## Python Package: `retrosheet/` → `baseball/`

### Core Package Migration

| Current File | New Location | Action | Notes |
|--------------|--------------|--------|-------|
| `retrosheet/__init__.py` | `baseball/__init__.py` | MOVE | Package entry point |
| `retrosheet/archive.py` | `baseball/sources/retrosheet.py` | WRAP | Create `RetrosheetSource` adapter wrapping `archive.py` |
| `retrosheet/event.py` | `baseball/sources/retrosheet.py` | WRAP | Parser logic wrapped in adapter |
| `retrosheet/game.py` | `baseball/sources/retrosheet.py` | WRAP | Game-level logic wrapped in adapter |
| `retrosheet/parser.py` | `baseball/sources/retrosheet.py` | WRAP | Orchestration wrapped in adapter |

### New Core Infrastructure

| Current File | New Location | Action | Notes |
|--------------|--------------|--------|-------|
| *new* | `baseball/cli.py` | CREATE | Typer CLI entry point |
| *new* | `baseball/app.py` | CREATE | Application container |
| *new* | `baseball/settings.py` | CREATE | Pydantic settings management |
| *new* | `baseball/logging.py` | CREATE | Structured logging setup |
| *new* | `baseball/core/db.py` | CREATE | Database connection manager |
| *new* | `baseball/core/sql_runner.py` | CREATE | SQL file execution utility |
| *new* | `baseball/core/checkpoints.py` | CREATE | Pipeline checkpoint logic |
| *new* | `baseball/core/filesystem.py` | CREATE | File I/O utilities |
| *new* | `baseball/core/http.py` | CREATE | HTTP client with retry/backoff |
| *new* | `baseball/core/registry.py` | CREATE | Source/feature/model registry |
| *new* | `baseball/core/types.py` | CREATE | Shared type definitions |

---

## Scripts: `scripts/` → Organized Structure

### Ingestion Scripts

| Current Path | New Location | Action | Notes |
|--------------|--------------|--------|-------|
| `scripts/data_ingestion/fetch_espn_complete.py` | `baseball/sources/espn.py` | WRAP | Create `EspnSource` adapter |
| `scripts/data_ingestion/fetch_mlb_schedule.py` | `baseball/sources/mlb.py` | WRAP | Merge into `MlbSource` |
| `scripts/data_ingestion/complete_mlb_ingestion.py` | `baseball/sources/mlb.py` | WRAP | Orchestration logic in `MlbSource` |
| `scripts/data_ingestion/download_baseball_savant.py` | `baseball/sources/statcast.py` | WRAP | Create `StatcastSource` adapter |
| `scripts/data_ingestion/create_live_plate_appearances.py` | `baseball/features/live_state.py` | MOVE | Feature engineering logic |
| `scripts/data_ingestion/ingest_all_external.sh` | `baseball/cli.py` (command) | WRAP | Shell → Python CLI command |
| `scripts/data_ingestion/ingest_all_mlb_parallel.sh` | `baseball/cli.py` (command) | WRAP | Shell → Python CLI command |

### Bridge Scripts

| Current Path | New Location | Action | Notes |
|--------------|--------------|--------|-------|
| `scripts/bridge/populate_mlb_players_venues_complete.py` | `baseball/services/bridge.py` | WRAP | Bridge service layer |
| `scripts/bridge/populate_bridge_tables.py` | `baseball/services/bridge.py` | WRAP | Xref population logic |
| `scripts/bridge/ingest_chadwick_register.py` | `baseball/services/bridge.py` | WRAP | Chadwick register integration |
| `scripts/bridge/complete_game_xref.py` | `baseball/services/bridge.py` | WRAP | Game xref logic |
| `scripts/bridge/investigate_coach_names.py` | `scripts_legacy/bridge/` | ARCHIVE | One-off investigation script |

### Transform Scripts

| Current Path | New Location | Action | Notes |
|--------------|--------------|--------|-------|
| `scripts/transform_live_game.py` | `baseball/sources/mlb.py` | WRAP | Live transform logic in `MlbSource` |
| `scripts/ingest_live_games.py` | `baseball/sources/mlb.py` | WRAP | Ingest logic in `MlbSource` |

### Utility Scripts

| Current Path | New Location | Action | Notes |
|--------------|--------------|--------|-------|
| `scripts/install_chadwick.sh` | `scripts_legacy/` | KEEP | Keep for reference, document in README |
| `scripts/warehouse.py` | `baseball/cli.py` | WRAP | CLI commands replace warehouse.py |
| `scripts/rebuild_warehouse.sh` | `baseball/cli.py` (pipeline command) | WRAP | Pipeline orchestration |
| `scripts/monitor_mlb_ingestion.sh` | `baseball/cli.py` (status command) | WRAP | Monitoring → `baseball status` |
| `scripts/add_sql_headers.py` | `scripts_legacy/` | ARCHIVE | One-time utility |
| `scripts/add_table_comments.py` | `scripts_legacy/` | ARCHIVE | One-time utility |
| `scripts/apply_accurate_headers.py` | `scripts_legacy/` | ARCHIVE | One-time utility |
| `scripts/benchmark_queries.py` | `baseball/services/validation.py` | WRAP | Query performance validation |

### Analysis Scripts

| Current Path | New Location | Action | Notes |
|--------------|--------------|--------|-------|
| `scripts/analysis/analyze_pa_models.py` | `baseball/models/backtest.py` | WRAP | Model analysis in backtest module |
| `scripts/analysis/analyze_pa_outcome_calibration.py` | `baseball/models/backtest.py` | WRAP | Calibration analysis |
| `scripts/analysis/feature_discovery_master.py` | `baseball/features/base.py` | WRAP | Feature discovery framework |

---

## SQL: `sql/` → Layered Structure

### Current → New Mapping

| Current Path | New Location | Action | Notes |
|--------------|--------------|--------|-------|
| `sql/core/` | `sql/30_core/` | MOVE | Core tables |
| `sql/bridge/` | `sql/40_bridge/` | MOVE | Bridge/xref tables |
| `sql/live/` | `sql/10_raw/` + `sql/30_core/` | SPLIT | Raw live → raw layer, canonical → core layer |
| `sql/external/` | `sql/10_raw/` + `sql/20_staging/` | SPLIT | External sources to raw/staging |
| `sql/features/` | `sql/50_features/` | MOVE | Feature marts |
| `sql/analysis/` | `sql/80_quality/` + `docs/analysis/` | SPLIT | Quality checks → 80_quality/, ad-hoc → docs |
| `sql/warehouse/` | `sql/70_serving/` | MOVE | Serving layer |
| `sql/eda/` | `docs/analysis/` | MOVE | Exploratory analysis documentation |
| `sql/maintenance/` | `sql/00_admin/` | MOVE | Admin/maintenance scripts |

### New Admin SQL

| New Location | Purpose |
|--------------|---------|
| `sql/00_admin/001_pipeline_control_tables.sql` | Create `pipeline_runs`, `pipeline_checkpoints`, `pipeline_errors` |
| `sql/00_admin/002_source_registry.sql` | Source configuration and metadata |

### SQL Naming Convention

| Old Pattern | New Pattern | Example |
|-------------|-------------|---------|
| `001_init.sql` | `001_admin_database_init.sql` | With layer prefix |
| `010_core_games_events.sql` | `301_core_games.sql` | Layer 30, sequence 01 |
| `900_bridge_monitoring_views.sql` | `440_bridge_monitoring_views.sql` | Layer 40, sequence 40 |

---

## ✅ Milestone 7: SQL Layer Reorganization (COMPLETED 2026-04-27)

### Completed Actions

| Layer | Old Location | New Location | Files | Status |
|-------|--------------|--------------|-------|--------|
| 00_admin | `sql/maintenance/` + `sql/00_admin/` | `sql/00_admin/` | 1 | ✅ Consolidated |
| 10_raw | `sql/live/` + `sql/external/` | `sql/10_raw/` | 19 | ✅ Merged & renamed |
| 20_staging | *new* | `sql/20_staging/` | 0 | ✅ Created (ready) |
| 30_core | `sql/core/` | `sql/30_core/` | 23 | ✅ Renamed to 30XX pattern |
| 40_bridge | `sql/bridge/` | `sql/40_bridge/` | 15 | ✅ Renamed to 40XX pattern |
| 50_features | `sql/features/` | `sql/50_features/` | 36 | ✅ Renamed to 50XX pattern |
| 60_models | `sql/models/` + root `sql/600_*.sql` | `sql/60_models/` | 4 | ✅ Consolidated & renamed |
| 70_serving | *new* | `sql/70_serving/` | 0 | ✅ Created (ready) |
| 80_quality | *new* | `sql/80_quality/` | 0 | ✅ Created (ready) |

### Naming Convention Applied

All files now follow: `{layer}{sequence}_{layer_name}_{description}.sql`

Examples:
- `1001_raw_mlb_api_complete.sql` (layer 10, sequence 01)
- `3001_core_init.sql` (layer 30, sequence 01)
- `4001_bridge_schema.sql` (layer 40, sequence 01)
- `5001_features_pitch_data_quality.sql` (layer 50, sequence 01)
- `6001_models_registry.sql` (layer 60, sequence 01)

### Deleted Directories

- `sql/live/` → merged into `sql/10_raw/`
- `sql/external/` → merged into `sql/10_raw/`
- `sql/core/` → moved to `sql/30_core/`
- `sql/bridge/` → moved to `sql/40_bridge/`
- `sql/features/` → moved to `sql/50_features/`
- `sql/models/` → moved to `sql/60_models/`

### Remaining (Non-Layered)

- `sql/analysis/` → analysis queries (future: review for 80_quality/)
- `sql/eda/` → exploratory analysis (future: move to docs/)
- `sql/framework/` → framework utilities
- `sql/maintenance/` → maintenance utilities
- `sql/metadata/` → metadata queries
- `sql/mlb/` → MLB-specific queries (future: review)
- `sql/optimization/` → optimization scripts
- `sql/test/` → test fixtures
- `sql/utility/` → utility functions
- `sql/warehouse/` → warehouse views (future: move to 70_serving/)

---

## Configuration: New `config/` Directory

| New Location | Purpose | Source |
|--------------|---------|--------|
| `config/sources.yml` | Source configuration (URLs, credentials, schedules) | Extract from scattered config |
| `config/pipelines.yml` | Pipeline definitions and dependencies | Extract from shell scripts |
| `config/models.yml` | Model configuration (hyperparameters, features) | Extract from model training scripts |

---

## Documentation: `docs/` Structure

| Current | New Location | Action |
|---------|--------------|--------|
| `README.md` | `README.md` | KEEP (update) |
| `AGENTS.md` | `AGENTS.md` | UPDATE (split guidance) |
| `docs/agents/FILE_INVENTORY.md` | `docs/agents/FILE_INVENTORY.md` | KEEP (maintain) |
| `docs/agents/PROCEDURES.md` | `docs/agents/PROCEDURES.md` | KEEP (maintain) |
| `docs/PROJECT_LOG.md` | `docs/PROJECT_LOG.md` | KEEP (append) |
| *new* | `docs/architecture.md` | CREATE |
| *new* | `docs/sources.md` | CREATE |
| *new* | `docs/keys_and_grains.md` | CREATE |
| *new* | `docs/models.md` | CREATE |
| *new* | `docs/agents/architecture_agent.md` | CREATE |
| *new* | `docs/agents/python_agent.md` | CREATE |
| *new* | `docs/agents/sql_agent.md` | CREATE |
| *new* | `docs/agents/ml_agent.md` | CREATE |
| *new* | `docs/agents/live_agent.md` | CREATE |
| *new* | `docs/agents/docs_agent.md` | CREATE |

---

## Package Configuration: `pyproject.toml`

### Required Changes

```toml
[project.scripts]
baseball = "baseball.cli:main"

[project.optional-dependencies]
ml = ["scikit-learn", "xgboost", "lightgbm", "pandas", "numpy"]
live = ["websockets", "asyncio-mqtt"]
dev = ["pytest", "ruff", "mypy", "pre-commit"]
```

### New Dependencies

| Package | Purpose |
|---------|---------|
| `typer` | CLI framework |
| `pydantic` | Settings validation |
| `pydantic-settings` | Configuration management |
| `structlog` | Structured logging |
| `tenacity` | HTTP retry logic |
| `aiohttp` | Async HTTP client |

---

## Migration Order

### Phase 1: Foundation (Week 1)

1. Create `baseball/` package skeleton
2. Create core infrastructure modules
3. Update `pyproject.toml` with CLI entry
4. Create `docs/migration_map.md` (this document)
5. Create `docs/migration_backlog.md`

### Phase 2: Retrosheet Adapter (Week 2)

1. Create `baseball/sources/retrosheet.py` wrapping existing `retrosheet/` package
2. Move `retrosheet/` → `retrosheet_legacy/` (temporary)
3. Update imports and tests
4. Create `baseball/sources/base.py` with `BaseSource` abstract class

### Phase 3: MLB Live Adapter (Week 3)

1. Create `baseball/sources/mlb.py`
2. Migrate SQL from `sql/live/` → `sql/10_raw/` + `sql/30_core/`
3. Create admin SQL tables
4. Implement `baseball mlb` CLI commands

### Phase 4: Bridge Consolidation (Week 4)

1. Create `baseball/services/bridge.py`
2. Migrate bridge scripts
3. Move `sql/bridge/` → `sql/40_bridge/`
4. Implement `baseball bridge` CLI commands

### Phase 5: ESPN + Statcast (Week 5)

1. Create `baseball/sources/espn.py`
2. Create `baseball/sources/statcast.py`
3. Implement `baseball espn` and `baseball statcast` commands

### Phase 6: Features + Models (Week 6-7)

1. Create feature framework in `baseball/features/`
2. Create model framework in `baseball/models/`
3. Migrate SQL from `sql/features/` → `sql/50_features/`
4. Implement `baseball features` and `baseball models` commands

### Phase 7: Cleanup (Week 8)

1. Move remaining scripts to `scripts_legacy/`
2. Archive one-time utilities
3. Finalize documentation
4. Run full pipeline validation

---

## Rollback Plan

If migration issues arise:

1. **Phase 1-2**: Can revert by removing `baseball/` directory, restoring imports
2. **Phase 3-4**: Keep `scripts_legacy/` intact for rollback
3. **Phase 5+**: Database migrations are additive, can coexist with old scripts
4. **Emergency**: `git checkout` to pre-migration branch, database unchanged

---

## Validation Checklist

After each phase, verify:

- [ ] All tests pass
- [ ] `baseball doctor` reports healthy status
- [ ] At least one source adapter works end-to-end
- [ ] No orphan scripts created
- [ ] SQL files follow naming convention
- [ ] Documentation updated

---

## Script Consolidation (April 26, 2026)

Consolidation effort following major_update.md principles: preserve working logic, wrap existing scripts, archive true orphans only.

### Archived Scripts (True Orphans)

| File | Destination | Reason |
|------|-------------|--------|
| `scripts/bridge/investigate_coach_names.py` | `scripts/archive/bridge_investigations/` | One-time investigation |
| `scripts/bridge/investigate_umpire_ids.py` | `scripts/archive/bridge_investigations/` | One-time investigation |
| `scripts/bridge/replay_live_bridge_backfill.py` | `scripts/archive/one_time_backfills/` | One-time backfill |
| `scripts/add_table_comments.py` | `scripts/archive/deprecated_sql_tools/` | Superseded by sql_maintenance.py |
| `scripts/apply_accurate_headers.py` | `scripts/archive/deprecated_sql_tools/` | Superseded by sql_maintenance.py |
| `scripts/fix_sql_headers.py` | `scripts/archive/deprecated_sql_tools/` | Superseded by sql_maintenance.py |
| `scripts/convert_block_headers.py` | `scripts/archive/deprecated_sql_tools/` | Superseded by sql_maintenance.py |

### Unified Scripts (Merged Functionality)

| Previous Files | New File | Purpose |
|----------------|----------|---------|
| `add_sql_headers.py`, `add_table_comments.py`, `apply_accurate_headers.py`, `fix_sql_headers.py` | `scripts/utility/sql_maintenance.py` | Unified SQL header/comment management tool |

### Shell Wrappers Updated

| File | Change | New Behavior |
|------|--------|--------------|
| `scripts/complete_mlb_ingestion.sh` | Updated | Calls `baseball mlb download/ingest` |
| `scripts/ingest_all_mlb_parallel.sh` | Updated | Calls `baseball mlb download/ingest` |

### Source Adapters Created (WRAP Pattern)

| Adapter | Wraps | Location |
|-----------|-------|----------|
| `MlbSource` | `download_mlb_bulk.py`, `ingest_all_mlb_data.py` | `baseball/sources/mlb.py` |
| `EspnSource` | `fetch_espn_mlb.py` | `baseball/sources/espn.py` |
| `StatcastSource` | `download_statcast.py`, `load_statcast.py` | `baseball/sources/statcast.py` |
| `LahmanSource` | `download_lahman_data.py`, `load_lahman.py` | `baseball/sources/lahman.py` |
| `RetrosheetSource` | `retrosheet/archive.py`, `retrosheet/parser.py` | `baseball/sources/retrosheet.py` |

### Bridge Service Created

| Service | Wraps | Location |
|---------|-------|----------|
| `BridgeService` | `populate_bridge_tables.py`, `ingest_chadwick_register.py`, `populate_game_xref.py`, `populate_season_aware_team_xref.py` | `baseball/services/bridge.py` |

### E2E Test Framework Created

| Test File | Coverage | Status |
|-----------|----------|--------|
| `tests/e2e/test_source_adapters.py` | All 5 source adapters | 12 passed |
| `tests/e2e/test_bridge_service.py` | Bridge service | 4 passed, 1 skipped |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Migration Agent | Initial file inventory and mapping |
| 1.1 | 2026-04-26 | Migration Agent | Added Script Consolidation section |
