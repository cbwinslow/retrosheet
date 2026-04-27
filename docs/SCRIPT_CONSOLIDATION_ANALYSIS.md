# Script Consolidation Analysis

**Date**: 2026-04-26
**Author**: Agent cbwinslow/retrosheet

## Executive Summary

This document identifies opportunities to consolidate the scripts directory by:
1. Merging duplicate/overlapping functionality
2. Eliminating orphan scripts
3. Creating wrapper scripts that call consolidated functions
4. Aligning with the new `baseball` CLI architecture

---

## Current Script Inventory by Category

### 1. Data Ingestion Scripts (31 files)

#### MLB Data Download (Duplication Detected)
| Script | Purpose | Lines | Consolidation Action |
|--------|---------|-------|---------------------|
| `download_mlb_bulk.py` | Bulk download with parallel workers | 435 | **KEEP** - Most comprehensive |
| `download_mlb_games.py` | Download specific games | 7283 bytes | **MERGE INTO** download_mlb_bulk.py |
| `download_mlb_schedules.py` | Download schedules only | 6400 bytes | **MERGE INTO** download_mlb_bulk.py |
| `fetch_mlb_schedule.py` | Fetch schedule (different impl) | 4235 bytes | **MERGE INTO** download_mlb_bulk.py |
| `fetch_mlb_stats_api_complete.py` | Complete stats API fetch | 17300 bytes | **MERGE INTO** download_mlb_bulk.py |
| `fetch_mlb_rosters.py` | Fetch rosters | 2251 bytes | **MERGE INTO** download_mlb_bulk.py |

**Consolidation Plan**: Create unified `scripts/data_ingestion/mlb_downloader.py` with subcommands:
- `mlb_downloader.py schedules --season 2025`
- `mlb_downloader.py games --season 2025`
- `mlb_downloader.py rosters --season 2025`
- `mlb_downloader.py bulk --start-season 2020 --end-season 2025`

#### ESPN Data (Multiple Implementations)
| Script | Purpose | Consolidation Action |
|--------|---------|---------------------|
| `fetch_espn_mlb.py` | Generalized ESPN fetcher | **KEEP** - Most comprehensive |
| `fetch_espn_complete.py` | Complete ESPN fetcher | **MERGE INTO** fetch_espn_mlb.py |
| `ingest_espn_plays.py` | ESPN plays ingestion | **MERGE INTO** fetch_espn_mlb.py |
| `populate_espn_bridge.py` | ESPN bridge population | **MERGE INTO** bridge/populate_bridge_tables.py |

#### Statcast Data
| Script | Purpose | Consolidation Action |
|--------|---------|---------------------|
| `download_statcast.py` | Download Statcast | **KEEP** |
| `download_statcast_pitch_level.py` | Pitch-level data | **MERGE INTO** download_statcast.py |
| `download_baseball_savant.py` | Baseball Savant data | **MERGE INTO** download_statcast.py |

#### Orchestration Scripts (Multiple Similar)
| Script | Purpose | Consolidation Action |
|--------|---------|---------------------|
| `complete_mlb_ingestion.py` | Complete ingestion orchestrator | **KEEP** - Most comprehensive |
| `ingest_all_mlb_data.py` | All MLB data ingestion | **MERGE INTO** complete_mlb_ingestion.py |
| `ingest_current_season.py` | Current season pipeline | **KEEP** (different use case) |
| `ingest_live_games.py` | Live games ingestion | **KEEP** (different use case) |
| `ingest_mlb_pbp.py` | MLB play-by-play | **MERGE INTO** complete_mlb_ingestion.py |

### 2. Bridge Scripts (17 files)

#### Bridge Population (Many Similar Scripts)
| Script | Purpose | Consolidation Action |
|--------|---------|---------------------|
| `populate_bridge_tables.py` | Main bridge population | **KEEP** - Most comprehensive |
| `populate_game_xref.py` | Game xref only | **MERGE INTO** populate_bridge_tables.py |
| `populate_external_bridge.py` | External bridge | **MERGE INTO** populate_bridge_tables.py |
| `populate_espn_bridge.py` | ESPN bridge | **MERGE INTO** populate_bridge_tables.py |
| `populate_coach_umpire_bridge.py` | Coach/umpire bridge | **MERGE INTO** populate_bridge_tables.py |
| `populate_season_aware_team_xref.py` | Team xref | **MERGE INTO** populate_bridge_tables.py |
| `run_bridge_ingestion.py` | Bridge orchestrator | **MERGE INTO** populate_bridge_tables.py |
| `populate_all_bridge_tables.sh` | Shell wrapper | **REPLACE** with Python wrapper |
| `complete_game_xref.py` | Game xref completion | **MERGE INTO** populate_bridge_tables.py |

#### Investigation Scripts (Temporary/One-time)
| Script | Purpose | Consolidation Action |
|--------|---------|---------------------|
| `investigate_coach_names.py` | Investigation script | **ARCHIVE** - One-time use |
| `investigate_umpire_ids.py` | Investigation script | **ARCHIVE** - One-time use |
| `view_metrics.py` | Metrics viewer | **KEEP** but move to `utility/` |

### 3. Utility Scripts (13 files)

#### Header/Comment Scripts (Multiple Similar)
| Script | Purpose | Consolidation Action |
|--------|---------|---------------------|
| `add_sql_headers.py` | Add SQL headers | **KEEP** |
| `add_table_comments.py` | Add table comments | **MERGE INTO** add_sql_headers.py |
| `apply_accurate_headers.py` | Apply headers | **MERGE INTO** add_sql_headers.py |
| `fix_sql_headers.py` | Fix headers | **MERGE INTO** add_sql_headers.py |
| `convert_block_headers.py` | Convert headers | **MERGE INTO** add_sql_headers.py |

### 4. Model Training Scripts (18 files)

#### Duplicate Training Scripts
| Script | Purpose | Consolidation Action |
|--------|---------|---------------------|
| `train_sample_models.py` | Train sample models | **MERGE INTO** demo_advanced_modeling.py |
| `demo_advanced_modeling.py` | Demo modeling | **KEEP** - Most comprehensive |

### 5. Shell Scripts (Multiple Wrappers)

| Script | Purpose | Consolidation Action |
|--------|---------|---------------------|
| `complete_mlb_ingestion.sh` | Shell wrapper for Python | **CONSOLIDATE** with Python script |
| `ingest_all_mlb_parallel.sh` | Parallel ingestion wrapper | **CONSOLIDATE** with complete_mlb_ingestion.py |
| `populate_all_missing_data.sh` | Missing data wrapper | **CONSOLIDATE** with complete_mlb_ingestion.py |
| `rebuild_warehouse.sh` | Warehouse rebuild | **KEEP** - High-level orchestrator |
| `backup_procedures.sh` | Backup procedures | **KEEP** |

---

## Consolidation Plan Summary

### Phase 1: Merge Download Scripts
**Goal**: Create unified MLB downloader

1. Create `scripts/data_ingestion/mlb_downloader.py`:
   - Merge: download_mlb_bulk.py, download_mlb_games.py, download_mlb_schedules.py
   - Add subcommands: schedules, games, rosters, bulk
   - Use download_mlb_bulk.py as base (most comprehensive)

2. Archive merged scripts:
   - download_mlb_games.py → archive/
   - download_mlb_schedules.py → archive/
   - fetch_mlb_schedule.py → archive/

### Phase 2: Merge Bridge Scripts
**Goal**: Single bridge population script

1. Enhance `scripts/bridge/populate_bridge_tables.py`:
   - Add functions from: populate_game_xref.py, populate_external_bridge.py
   - Add ESPN bridge population from: populate_espn_bridge.py
   - Add coach/umpire from: populate_coach_umpire_bridge.py

2. Archive merged scripts:
   - populate_game_xref.py → archive/
   - populate_external_bridge.py → archive/
   - populate_espn_bridge.py → archive/
   - populate_coach_umpire_bridge.py → archive/
   - populate_season_aware_team_xref.py → archive/

### Phase 3: Merge Ingestion Orchestrators
**Goal**: Single comprehensive ingestion script

1. Create `scripts/data_ingestion/ingest_mlb.py`:
   - Merge: complete_mlb_ingestion.py, ingest_all_mlb_data.py
   - Keep: ingest_current_season.py (different use case)
   - Keep: ingest_live_games.py (different use case)

2. Archive:
   - ingest_all_mlb_data.py → archive/

### Phase 4: Merge Header/Comment Scripts
**Goal**: Single SQL maintenance script

1. Create `scripts/utility/sql_maintenance.py`:
   - Merge: add_sql_headers.py, add_table_comments.py
   - Add subcommands: add-headers, add-comments, fix-headers

2. Archive:
   - add_table_comments.py → archive/
   - apply_accurate_headers.py → archive/
   - fix_sql_headers.py → archive/
   - convert_block_headers.py → archive/

### Phase 5: Archive Investigation Scripts
**Goal**: Clean up one-time scripts

1. Move to archive/:
   - investigate_coach_names.py
   - investigate_umpire_ids.py
   - replay_live_bridge_backfill.py

---

## Post-Consolidation Structure

```
scripts/
├── data_ingestion/
│   ├── mlb_downloader.py          (consolidated - replaces 6 scripts)
│   ├── ingest_mlb.py              (consolidated - replaces 2 scripts)
│   ├── ingest_current_season.py   (kept - specific use case)
│   ├── ingest_live_games.py       (kept - specific use case)
│   ├── download_statcast.py       (enhanced - merged 3 scripts)
│   ├── fetch_espn_mlb.py          (enhanced - merged 3 scripts)
│   ├── download_lahman_data.py    (kept)
│   └── fetch_weather.py           (kept)
├── bridge/
│   ├── populate_bridge_tables.py  (enhanced - merged 7 scripts)
│   ├── ingest_chadwick_register.py (kept)
│   └── run_bridge_ingestion.py    (kept as wrapper)
├── utility/
│   ├── sql_maintenance.py       (consolidated - replaces 4 scripts)
│   ├── backup_procedures.sh       (kept)
│   ├── check_extensions.py        (kept)
│   └── view_metrics.py            (moved from bridge/)
├── analysis/
│   └── (keep all - different purposes)
├── model_training/
│   └── (keep all - different purposes)
└── archive/
    └── (merged scripts moved here)
```

---

## Scripts to Remove (Orphans/Duplicates)

### Directly Merge and Remove (14 scripts):
1. `scripts/data_ingestion/download_mlb_games.py`
2. `scripts/data_ingestion/download_mlb_schedules.py`
3. `scripts/data_ingestion/fetch_mlb_schedule.py`
4. `scripts/data_ingestion/fetch_mlb_rosters.py`
5. `scripts/bridge/populate_game_xref.py`
6. `scripts/bridge/populate_external_bridge.py`
7. `scripts/bridge/populate_espn_bridge.py`
8. `scripts/bridge/populate_coach_umpire_bridge.py`
9. `scripts/bridge/populate_season_aware_team_xref.py`
10. `scripts/bridge/complete_game_xref.py`
11. `scripts/bridge/investigate_coach_names.py` (archive)
12. `scripts/bridge/investigate_umpire_ids.py` (archive)
13. `scripts/add_table_comments.py`
14. `scripts/apply_accurate_headers.py`

### Shell Scripts to Consolidate (3 scripts):
1. `scripts/complete_mlb_ingestion.sh` → merge into Python script
2. `scripts/ingest_all_mlb_parallel.sh` → merge into complete_mlb_ingestion.py
3. `scripts/populate_all_missing_data.sh` → merge into complete_mlb_ingestion.py

---

## E2E Test Coverage Plan

### Tier 1: Core CLI Commands
- [ ] `baseball doctor` - System health check
- [ ] `baseball status` - Pipeline status display
- [ ] `baseball version` - Version information

### Tier 2: Source Adapters
- [ ] `baseball mlb download --season 2025` - MLB download
- [ ] `baseball mlb ingest` - MLB ingestion
- [ ] `baseball mlb validate` - MLB validation
- [ ] `baseball retrosheet download --year 2024` - Retrosheet download
- [ ] `baseball espn download --season 2025` - ESPN download
- [ ] `baseball statcast download --season 2025` - Statcast download
- [ ] `baseball lahman download` - Lahman download

### Tier 3: Bridge Commands
- [ ] `baseball bridge resolve --source mlb --id 12345` - ID resolution
- [ ] `baseball bridge match --type player --source-a mlb --source-b espn` - Match
- [ ] `baseball bridge lookup --id canonical_123` - Lookup

### Tier 4: Pipeline Commands
- [ ] `baseball pipeline list` - List pipelines
- [ ] `baseball pipeline run --pipeline retrosheet_ingest` - Run pipeline
- [ ] `baseball pipeline status` - Pipeline status

### Tier 5: Integration Tests
- [ ] Full flow: download → ingest → validate (single game)
- [ ] Full flow: download → ingest → bridge → features (single season)

---

## Success Criteria

1. **Script count reduced by 30%** (from ~150+ to ~100)
2. **All E2E tests pass**
3. **No orphan scripts** (all scripts called by workflows or CLI)
4. **Documentation updated** (AGENTS.md, FILE_INVENTORY.md)
5. **Wrapper scripts functional** (rebuild_warehouse.sh, etc.)

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Execute Phase 1** (Download consolidation)
3. **Run E2E tests** after each phase
4. **Execute Phase 2-5** sequentially
5. **Final validation** with full test suite
