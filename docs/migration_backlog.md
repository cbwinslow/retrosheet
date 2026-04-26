# Migration Backlog

**Purpose**: Detailed task list for the migration. Track progress here. Each task includes acceptance criteria and estimated effort.

---

## Milestone 0: Planning & Documentation

### Phase 0.1: Create Planning Documents

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 0.1.1 | Create `docs/migration_plan.md` | High | ✅ Done | Document exists with all sections | 2h |
| 0.1.2 | Create `docs/migration_map.md` | High | ✅ Done | File inventory complete | 3h |
| 0.1.3 | Create `docs/migration_backlog.md` | High | ✅ Done | This document | 2h |
| 0.1.4 | Create `docs/architecture.md` | High | 🔄 Pending | Target architecture documented | 4h |
| 0.1.5 | Create `docs/keys_and_grains.md` skeleton | High | 🔄 Pending | Entity keys documented | 3h |
| 0.1.6 | Create `docs/sources.md` | Medium | 🔄 Pending | All sources documented | 3h |
| 0.1.7 | Create `docs/models.md` | Medium | 🔄 Pending | Model strategy documented | 2h |

### Phase 0.2: Update AGENTS Guidance

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 0.2.1 | Update top-level `AGENTS.md` | High | 🔄 Pending | Clean, focused guidance | 2h |
| 0.2.2 | Create `docs/agents/architecture_agent.md` | Medium | 🔄 Pending | Architecture guidance | 1h |
| 0.2.3 | Create `docs/agents/python_agent.md` | Medium | 🔄 Pending | Python coding standards | 1h |
| 0.2.4 | Create `docs/agents/sql_agent.md` | Medium | 🔄 Pending | SQL standards | 1h |
| 0.2.5 | Create `docs/agents/ml_agent.md` | Medium | 🔄 Pending | ML pipeline guidance | 1h |
| 0.2.6 | Create `docs/agents/live_agent.md` | Medium | 🔄 Pending | Live ingestion guidance | 1h |
| 0.2.7 | Create `docs/agents/docs_agent.md` | Low | 🔄 Pending | Documentation standards | 1h |

---

## Milestone 1: Framework Foundation

### Phase 1.1: Package Skeleton

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 1.1.1 | Create `baseball/` directory structure | High | 🔄 Pending | All subdirs exist | 30m |
| 1.1.2 | Create `baseball/__init__.py` with version | High | 🔄 Pending | Package imports work | 15m |
| 1.1.3 | Create `baseball/core/` subdirectory | High | 🔄 Pending | Core module structure | 15m |
| 1.1.4 | Create `baseball/sources/` subdirectory | High | 🔄 Pending | Sources module structure | 15m |
| 1.1.5 | Create `baseball/features/` subdirectory | High | 🔄 Pending | Features module structure | 15m |
| 1.1.6 | Create `baseball/models/` subdirectory | High | 🔄 Pending | Models module structure | 15m |
| 1.1.7 | Create `baseball/services/` subdirectory | High | 🔄 Pending | Services module structure | 15m |

### Phase 1.2: Core Infrastructure

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 1.2.1 | Create `baseball/core/types.py` | High | 🔄 Pending | Type definitions | 1h |
| 1.2.2 | Create `baseball/core/settings.py` | High | 🔄 Pending | Pydantic settings | 2h |
| 1.2.3 | Create `baseball/core/db.py` | High | 🔄 Pending | Database manager | 2h |
| 1.2.4 | Create `baseball/core/sql_runner.py` | High | 🔄 Pending | SQL execution utility | 2h |
| 1.2.5 | Create `baseball/core/checkpoints.py` | High | 🔄 Pending | Pipeline checkpoints | 2h |
| 1.2.6 | Create `baseball/core/filesystem.py` | Medium | 🔄 Pending | File I/O utilities | 1h |
| 1.2.7 | Create `baseball/core/http.py` | Medium | 🔄 Pending | HTTP client | 1h |
| 1.2.8 | Create `baseball/core/registry.py` | Medium | 🔄 Pending | Source/model registry | 2h |
| 1.2.9 | Create `baseball/logging.py` | High | 🔄 Pending | Structured logging | 1h |

### Phase 1.3: CLI Shell

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 1.3.1 | Add `typer` to dependencies | High | 🔄 Pending | In `pyproject.toml` | 15m |
| 1.3.2 | Create `baseball/cli.py` entry point | High | 🔄 Pending | CLI imports without error | 1h |
| 1.3.3 | Add `[project.scripts]` entry in `pyproject.toml` | High | 🔄 Pending | `baseball` command works | 15m |
| 1.3.4 | Implement `baseball doctor` command stub | High | 🔄 Pending | Returns status | 1h |
| 1.3.5 | Implement `baseball status` command stub | High | 🔄 Pending | Returns status | 1h |
| 1.3.6 | Create CLI command groups structure | Medium | 🔄 Pending | `retrosheet`, `mlb`, etc. groups | 1h |

### Phase 1.4: Admin SQL

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 1.4.1 | Create `sql/00_admin/` directory | High | 🔄 Pending | Directory exists | 15m |
| 1.4.2 | Create `000_admin_pipeline_control.sql` | High | 🔄 Pending | Tables created | 2h |
| 1.4.3 | Define `pipeline_runs` table | High | 🔄 Pending | With all columns | 30m |
| 1.4.4 | Define `pipeline_checkpoints` table | High | 🔄 Pending | With all columns | 30m |
| 1.4.5 | Define `pipeline_errors` table | High | 🔄 Pending | With all columns | 30m |
| 1.4.6 | Add indexes on admin tables | Medium | 🔄 Pending | Performance | 30m |

---

## Milestone 2: Historical Wrapper (Retrosheet)

### Phase 2.1: Source Base Class

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 2.1.1 | Create `baseball/sources/base.py` | High | 🔄 Pending | Abstract base class | 2h |
| 2.1.2 | Define `BaseSource` interface | High | 🔄 Pending | Abstract methods defined | 1h |
| 2.1.3 | Define `SourceResult` dataclass | High | 🔄 Pending | Return type | 30m |
| 2.1.4 | Define `DownloadConfig` dataclass | Medium | 🔄 Pending | Configuration | 30m |

### Phase 2.2: Retrosheet Adapter

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 2.2.1 | Create `baseball/sources/retrosheet.py` | High | 🔄 Pending | Module exists | 30m |
| 2.2.2 | Implement `RetrosheetSource` class | High | 🔄 Pending | Inherits from `BaseSource` | 2h |
| 2.2.3 | Wrap `retrosheet/archive.py` download | High | 🔄 Pending | `download()` method | 2h |
| 2.2.4 | Wrap `retrosheet/event.py` parsing | High | 🔄 Pending | `ingest()` method | 2h |
| 2.2.5 | Implement `validate()` method | High | 🔄 Pending | Row counts, checksums | 2h |
| 2.2.6 | Add checkpoint integration | Medium | 🔄 Pending | Resume capability | 2h |

### Phase 2.3: CLI Commands

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 2.3.1 | Implement `baseball retrosheet download` | High | 🔄 Pending | Working download | 1h |
| 2.3.2 | Implement `baseball retrosheet ingest` | High | 🔄 Pending | Working ingest | 1h |
| 2.3.3 | Implement `baseball retrosheet validate` | High | 🔄 Pending | Working validate | 1h |
| 2.3.4 | Add `--year` parameter | High | 🔄 Pending | Single year support | 30m |
| 2.3.5 | Add `--start-year`/`--end-year` parameters | Medium | 🔄 Pending | Range support | 30m |

### Phase 2.4: SQL Migration

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 2.4.1 | Create `sql/10_raw/` directory | High | 🔄 Pending | For raw Retrosheet | 15m |
| 2.4.2 | Create `sql/20_staging/` directory | High | 🔄 Pending | For staging | 15m |
| 2.4.3 | Move core Retrosheet SQL to `sql/30_core/` | High | 🔄 Pending | Renumber files | 2h |
| 2.4.4 | Create raw landing table SQL | High | 🔄 Pending | `raw_retrosheet.*` | 2h |
| 2.4.5 | Create staging table SQL | Medium | 🔄 Pending | `stg_retrosheet.*` | 2h |
| 2.4.6 | Update foreign key references | Medium | 🔄 Pending | Consistency | 1h |

---

## Milestone 3: MLB Live Vertical Slice

### Phase 3.1: MLB Source Adapter

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 3.1.1 | Create `baseball/sources/mlb.py` | High | 🔄 Pending | Module exists | 30m |
| 3.1.2 | Implement `MlbSource` class | High | 🔄 Pending | Inherits from `BaseSource` | 2h |
| 3.1.3 | Implement `download()` for schedule | High | 🔄 Pending | MLB Stats API schedule | 2h |
| 3.1.4 | Implement `download()` for games | High | 🔄 Pending | MLB Stats API games | 2h |
| 3.1.5 | Implement `ingest()` for raw → core | High | 🔄 Pending | Transformation logic | 3h |
| 3.1.6 | Implement `validate()` | High | 🔄 Pending | Data validation | 2h |
| 3.1.7 | Add checkpoint integration | Medium | 🔄 Pending | Resume capability | 2h |

### Phase 3.2: Raw Live Persistence

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 3.2.1 | Create `sql/10_raw/101_raw_mlb_live_feed.sql` | High | 🔄 Pending | Table definition | 1h |
| 3.2.2 | Define `raw_mlb.live_feed_snapshots` | High | 🔄 Pending | With JSONB payload | 1h |
| 3.2.3 | Add deduplication logic | High | 🔄 Pending | Checksum-based | 1h |
| 3.2.4 | Add indexes on raw table | Medium | 🔄 Pending | Performance | 30m |
| 3.2.5 | Implement raw persistence in adapter | High | 🔄 Pending | `save_raw()` method | 2h |

### Phase 3.3: Canonical Live Tables

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 3.3.1 | Create `sql/30_core/310_core_live_games.sql` | High | 🔄 Pending | Live games table | 2h |
| 3.3.2 | Create `sql/30_core/311_core_live_events.sql` | High | 🔄 Pending | Live events table | 2h |
| 3.3.3 | Define event-state snapshot schema | High | 🔄 Pending | Base-out, score, inning | 2h |
| 3.3.4 | Add foreign keys to core tables | Medium | 🔄 Pending | Referential integrity | 1h |
| 3.3.5 | Create live game state view | Medium | 🔄 Pending | Unified view | 2h |

### Phase 3.4: CLI Commands

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 3.4.1 | Implement `baseball mlb download` | High | 🔄 Pending | Working download | 1h |
| 3.4.2 | Implement `baseball mlb ingest` | High | 🔄 Pending | Working ingest | 1h |
| 3.4.3 | Implement `baseball mlb stream` | High | 🔄 Pending | Continuous poll | 2h |
| 3.4.4 | Implement `baseball mlb validate` | High | 🔄 Pending | Working validate | 1h |
| 3.4.5 | Add `--date` parameter | High | 🔄 Pending | Date filtering | 30m |
| 3.4.6 | Add `--team` parameter | Medium | 🔄 Pending | Team filtering | 30m |
| 3.4.7 | Add `--game-pk` parameter | Medium | 🔄 Pending | Single game | 30m |

### Phase 3.5: Feature Foundation

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 3.5.1 | Create `sql/50_features/500_features_run_expectancy.sql` | High | 🔄 Pending | RE table | 2h |
| 3.5.2 | Create `sql/50_features/501_features_live_game_state.sql` | High | 🔄 Pending | Live state table | 2h |
| 3.5.3 | Create `baseball/features/base.py` | High | 🔄 Pending | Base feature class | 2h |
| 3.5.4 | Create `baseball/features/run_expectancy.py` | High | 🔄 Pending | RE calculation | 2h |
| 3.5.5 | Create `baseball/features/live_state.py` | High | 🔄 Pending | Live state features | 2h |
| 3.5.6 | Implement `baseball features build` | High | 🔄 Pending | CLI command | 1h |
| 3.5.7 | Add `--scope` parameter | High | 🔄 Pending | `historical`/`live` | 30m |

### Phase 3.6: First Model (Win Probability)

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 3.6.1 | Create `sql/60_models/600_models_registry.sql` | High | 🔄 Pending | Model registry table | 1h |
| 3.6.2 | Create `sql/70_serving/700_serving_predictions.sql` | High | 🔄 Pending | Predictions table | 1h |
| 3.6.3 | Create `baseball/models/base.py` | High | 🔄 Pending | Base model class | 2h |
| 3.6.4 | Create `baseball/models/registry.py` | High | 🔄 Pending | Model registry | 2h |
| 3.6.5 | Create `baseball/models/training.py` | High | 🔄 Pending | Training pipeline | 3h |
| 3.6.6 | Create `baseball/models/inference.py` | High | 🔄 Pending | Inference pipeline | 3h |
| 3.6.7 | Implement `win_probability` model | High | 🔄 Pending | Working model | 4h |
| 3.6.8 | Implement `baseball models train` | High | 🔄 Pending | CLI command | 1h |
| 3.6.9 | Implement `baseball models predict` | High | 🔄 Pending | CLI command | 1h |
| 3.6.10 | Add `--model` parameter | High | 🔄 Pending | Model selection | 30m |
| 3.6.11 | Add `--game-pk` parameter | High | 🔄 Pending | Game prediction | 30m |

---

## Milestone 4: ESPN + Statcast

### Phase 4.1: ESPN Source

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 4.1.1 | Create `baseball/sources/espn.py` | High | 🔄 Pending | Module exists | 30m |
| 4.1.2 | Implement `EspnSource` class | High | 🔄 Pending | Inherits from `BaseSource` | 2h |
| 4.1.3 | Implement ESPN API client | High | 🔄 Pending | HTTP wrapper | 2h |
| 4.1.4 | Implement `download()` | High | 🔄 Pending | Schedule/scores | 2h |
| 4.1.5 | Implement `ingest()` | High | 🔄 Pending | Transform logic | 2h |
| 4.1.6 | Implement `validate()` | Medium | 🔄 Pending | Data validation | 1h |
| 4.1.7 | Create `baseball espn` CLI commands | High | 🔄 Pending | download/ingest | 1h |

### Phase 4.2: Statcast Source

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 4.2.1 | Create `baseball/sources/statcast.py` | High | 🔄 Pending | Module exists | 30m |
| 4.2.2 | Implement `StatcastSource` class | High | 🔄 Pending | Inherits from `BaseSource` | 2h |
| 4.2.3 | Integrate pybaseball library | High | 🔄 Pending | Dependency | 30m |
| 4.2.4 | Implement `download()` | High | 🔄 Pending | Statcast data | 2h |
| 4.2.5 | Implement `ingest()` | High | 🔄 Pending | Transform logic | 2h |
| 4.2.6 | Implement `validate()` | Medium | 🔄 Pending | Data validation | 1h |
| 4.2.7 | Create `baseball statcast` CLI commands | High | 🔄 Pending | download/ingest | 1h |
| 4.2.8 | Add date range parameters | Medium | 🔄 Pending | --start-date/--end-date | 30m |

### Phase 4.3: Bridge Integration

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 4.3.1 | Update bridge for ESPN IDs | Medium | 🔄 Pending | Xref table update | 2h |
| 4.3.2 | Update bridge for Statcast IDs | Medium | 🔄 Pending | Xref table update | 2h |
| 4.3.3 | Add ESPN/Statcast to confidence scoring | Low | 🔄 Pending | Validation logic | 2h |

---

## Milestone 5: Bridge Consolidation

### Phase 5.1: Bridge Service ✅ COMPLETE

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 5.1.1 | Create `baseball/bridge/` module | High | ✅ Done | Module exists | 30m |
| 5.1.2 | Implement `XrefManager` class | High | ✅ Done | Business logic | 3h |
| 5.1.3 | Create `player_xref.py` | High | ✅ Done | `PlayerXrefService` | 2h |
| 5.1.4 | Create `team_xref.py` | High | ✅ Done | `TeamXrefService` | 2h |
| 5.1.5 | Create `game_xref.py` | Medium | ✅ Done | `GameXrefService` | 2h |
| 5.1.6 | Create SQL schema | Medium | ✅ Done | `300_bridge_schema.sql` | 2h |

### Phase 5.2: SQL Migration

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 5.2.1 | Move `sql/bridge/` → `sql/40_bridge/` | High | 🔄 Pending | Renumber files | 2h |
| 5.2.2 | Rename files with layer prefix | High | 🔄 Pending | `40x_*.sql` format | 1h |
| 5.2.3 | Update SQL file references | Medium | 🔄 Pending | Documentation | 1h |
| 5.2.4 | Add COMMENT ON statements | Medium | 🔄 Pending | Table documentation | 1h |

### Phase 5.3: CLI Commands

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 5.3.1 | Implement `baseball bridge build` | High | 🔄 Pending | Working build | 1h |
| 5.3.2 | Implement `baseball bridge validate` | High | 🔄 Pending | Working validate | 1h |
| 5.3.3 | Add progress reporting | Medium | 🔄 Pending | User feedback | 1h |

---

## Milestone 6: Feature + Model Expansion

### Phase 6.1: Win Expectancy ✅ COMPLETE

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 6.1.1 | Create `sql/500_features_win_expectancy.sql` | Medium | ✅ Done | WE tables, functions, views | 2h |
| 6.1.2 | Create `baseball/features/win_expectancy.py` | Medium | ✅ Done | `WinExpectancyCalculator` with WPA | 2h |

### Phase 6.2: Leverage Index ✅ COMPLETE

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 6.2.1 | Create `sql/501_features_leverage_index.sql` | Medium | ✅ Done | LI tables, functions, views | 2h |
| 6.2.2 | Create `baseball/features/leverage_index.py` | Medium | ✅ Done | `LeverageIndexCalculator` with clutch | 2h |

### Phase 6.3: Matchup/Rolling/Bullpen

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 6.3.1 | Create `sql/50_features/520_features_matchup.sql` | Medium | 🔄 Pending | Matchup features | 3h |
| 6.3.2 | Create `sql/50_features/521_features_rolling_form.sql` | Medium | 🔄 Pending | Rolling features | 3h |
| 6.3.3 | Create `sql/50_features/522_features_bullpen.sql` | Medium | 🔄 Pending | Bullpen features | 3h |
| 6.3.4 | Create `baseball/features/matchup.py` | Medium | 🔄 Pending | Matchup logic | 2h |
| 6.3.5 | Create `baseball/features/rolling_form.py` | Medium | 🔄 Pending | Rolling logic | 2h |
| 6.3.6 | Create `baseball/features/bullpen.py` | Medium | 🔄 Pending | Bullpen logic | 2h |

### Phase 6.4: Next-Run Model

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 6.4.1 | Create `baseball/models/next_run_probability.py` | Medium | 🔄 Pending | Model implementation | 4h |
| 6.4.2 | Add to model registry | Medium | 🔄 Pending | Registration | 30m |
| 6.4.3 | Implement training pipeline | Medium | 🔄 Pending | Training script | 2h |

### Phase 6.5: Plate Appearance Model

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 6.5.1 | Create `baseball/models/plate_appearance_outcome.py` | Medium | 🔄 Pending | Model implementation | 4h |
| 6.5.2 | Add to model registry | Medium | 🔄 Pending | Registration | 30m |
| 6.5.3 | Implement training pipeline | Medium | 🔄 Pending | Training script | 2h |

### Phase 6.6: Training + Backtesting

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 6.6.1 | Create `baseball/models/backtest.py` | Medium | 🔄 Pending | Backtest framework | 3h |
| 6.6.2 | Create `sql/600_models_registry.sql` | Medium | ✅ Done | Full registry: models, versions, runs, artifacts, predictions | 2h |
| 6.6.3 | Add production deployment functions | Medium | ✅ Done | `promote_to_production()`, `log_prediction()` | 1h |
| 6.6.4 | Implement `baseball models backtest` | Medium | 🔄 Pending | CLI command | 1h |
| 6.6.5 | Add `--season` parameter | Medium | 🔄 Pending | Season filtering | 30m |

---

## Milestone 7: Serving + Interfaces

### Phase 7.1: Serving Tables

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 7.1.1 | Create `sql/70_serving/710_serving_game_predictions.sql` | Low | 🔄 Pending | Game predictions | 2h |
| 7.1.2 | Create `sql/70_serving/711_serving_pa_predictions.sql` | Low | 🔄 Pending | PA predictions | 2h |
| 7.1.3 | Create `sql/70_serving/712_serving_pitch_predictions.sql` | Low | 🔄 Pending | Pitch predictions | 2h |
| 7.1.4 | Add indexes for low-latency reads | Low | 🔄 Pending | Performance | 1h |
| 7.1.5 | Create materialized views where appropriate | Low | 🔄 Pending | Read optimization | 2h |

### Phase 7.2: Serving Service

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 7.2.1 | Create `baseball/services/serving.py` | Low | 🔄 Pending | Serving layer | 2h |
| 7.2.2 | Implement prediction caching | Low | 🔄 Pending | Cache layer | 2h |
| 7.2.3 | Add websocket-ready hooks | Low | 🔄 Pending | Future support | 2h |

### Phase 7.3: Chatbot-Ready Design

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 7.3.1 | Create `baseball/services/chatbot.py` | Low | 🔄 Pending | Query interface | 2h |
| 7.3.2 | Design query-safe views | Low | 🔄 Pending | Read-only views | 2h |
| 7.3.3 | Document query patterns | Low | 🔄 Pending | For chatbot | 1h |

---

## Milestone 8: Pipeline Orchestration

### Phase 8.1: Pipeline Commands

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 8.1.1 | Implement `baseball pipeline run daily` | Medium | 🔄 Pending | Daily pipeline | 2h |
| 8.1.2 | Implement `baseball pipeline run historical` | Medium | 🔄 Pending | Historical pipeline | 2h |
| 8.1.3 | Implement `baseball pipeline run live` | High | 🔄 Pending | Live pipeline | 2h |
| 8.1.4 | Add `--year` parameter for historical | Medium | 🔄 Pending | Year selection | 30m |
| 8.1.5 | Add `--date` parameter for live | High | 🔄 Pending | Date selection | 30m |

### Phase 8.2: Configuration

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 8.2.1 | Create `config/sources.yml` | Medium | 🔄 Pending | Source config | 1h |
| 8.2.2 | Create `config/pipelines.yml` | Medium | 🔄 Pending | Pipeline config | 1h |
| 8.2.3 | Create `config/models.yml` | Medium | 🔄 Pending | Model config | 1h |
| 8.2.4 | Implement config loading in `settings.py` | Medium | 🔄 Pending | Integration | 1h |

---

## Milestone 9: Cleanup + Validation

### Phase 9.1: Legacy Script Migration

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 9.1.1 | Create `scripts_legacy/` directory | High | 🔄 Pending | Archive location | 15m |
| 9.1.2 | Move wrapped scripts to `scripts_legacy/` | High | 🔄 Pending | Preserve originals | 2h |
| 9.1.3 | Document moved scripts in `docs/migration_map.md` | High | 🔄 Pending | Cross-reference | 1h |
| 9.1.4 | Archive one-time utilities | Medium | 🔄 Pending | Cleanup | 1h |

### Phase 9.2: Testing

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 9.2.1 | Create `tests/unit/test_sources.py` | High | 🔄 Pending | Unit tests | 3h |
| 9.2.2 | Create `tests/unit/test_features.py` | Medium | 🔄 Pending | Feature tests | 2h |
| 9.2.3 | Create `tests/integration/test_pipeline.py` | High | 🔄 Pending | Integration tests | 3h |
| 9.2.4 | Create `tests/e2e/test_cli.py` | Medium | 🔄 Pending | CLI tests | 2h |

### Phase 9.3: Documentation Finalization

| ID | Task | Priority | Status | AC | Effort |
|----|------|----------|--------|-----|--------|
| 9.3.1 | Update `README.md` | High | 🔄 Pending | New CLI instructions | 2h |
| 9.3.2 | Update `docs/PROJECT_LOG.md` | High | 🔄 Pending | Migration complete | 1h |
| 9.3.3 | Update `docs/agents/FILE_INVENTORY.md` | High | 🔄 Pending | New files | 1h |
| 9.3.4 | Final review of all agent docs | Medium | 🔄 Pending | Consistency | 1h |

---

## Progress Summary

| Milestone | Tasks | Complete | % Done |
|-----------|-------|----------|--------|
| 0: Planning | 13 | 3 | 23% |
| 1: Foundation | 21 | 0 | 0% |
| 2: Retrosheet | 15 | 0 | 0% |
| 3: MLB Live | 31 | 0 | 0% |
| 4: ESPN/Statcast | 15 | 0 | 0% |
| 5: Bridge | 11 | 0 | 0% |
| 6: Features/Models | 24 | 0 | 0% |
| 7: Serving | 11 | 0 | 0% |
| 8: Pipeline | 8 | 0 | 0% |
| 9: Cleanup | 13 | 0 | 0% |
| **TOTAL** | **162** | **3** | **2%** |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Migration Agent | Initial comprehensive backlog |
