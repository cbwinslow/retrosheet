# Script Consolidation Analysis - REVISED

**Date**: 2026-04-26
**Author**: Agent cbwinslow/retrosheet

## Philosophy Alignment Check

After re-reading major_update.md, the correct approach is:

1. **WRAP** existing scripts through new source adapters - don't blindly merge
2. **Preserve** working logic as compatibility entries
3. **Archive only** when new implementation is verified and materially replaces old
4. **Eliminate** "duplicate orchestration paths" and "orphan scripts"
5. **Target layer model**: raw -> staging -> core -> bridge -> features -> models -> serving

---

## Correct Consolidation Strategy

### What SHOULD Be Consolidated (Orphans & Duplicates)

#### Category 1: Orphan Scripts (No Clear Caller)
| Script | Issue | Action |
|--------|-------|--------|
| `scripts/bridge/investigate_coach_names.py` | One-time investigation | **ARCHIVE** to `scripts/archive/` |
| `scripts/bridge/investigate_umpire_ids.py` | One-time investigation | **ARCHIVE** to `scripts/archive/` |
| `scripts/bridge/replay_live_bridge_backfill.py` | One-time backfill | **ARCHIVE** to `scripts/archive/` |
| `scripts/edgeforge/*.py` | Experimental/unintegrated | **ARCHIVE** per AGENTS.md warning |

#### Category 2: Duplicate Orchestration Paths (Shell Wrappers)
| Script | Issue | Action |
|--------|-------|--------|
| `scripts/complete_mlb_ingestion.sh` | Duplicates Python orchestrator | **REPLACE** with call to `baseball pipeline run mlb_ingest` |
| `scripts/ingest_all_mlb_parallel.sh` | Duplicates complete_mlb_ingestion.py | **REPLACE** with call to `baseball pipeline run mlb_ingest` |
| `scripts/populate_all_missing_data.sh` | Duplicates other orchestrators | **REPLACE** with call to `baseball pipeline run missing_data` |

#### Category 3: Overlapping Header/Comment Scripts
| Script | Issue | Action |
|--------|-------|--------|
| `scripts/add_table_comments.py` | Overlaps with add_sql_headers.py | **MERGE INTO** unified `scripts/utility/sql_maintenance.py` |
| `scripts/apply_accurate_headers.py` | Overlaps with add_sql_headers.py | **MERGE INTO** unified `scripts/utility/sql_maintenance.py` |
| `scripts/fix_sql_headers.py` | Overlaps with add_sql_headers.py | **MERGE INTO** unified `scripts/utility/sql_maintenance.py` |
| `scripts/convert_block_headers.py` | Overlaps with add_sql_headers.py | **MERGE INTO** unified `scripts/utility/sql_maintenance.py` |

### What Should NOT Be Consolidated (Working Assets to WRAP)

Per major_update.md migration_map:

#### MLB Download Scripts - Keep as Compatibility Entries
| Script | Action | Notes |
|--------|--------|-------|
| `scripts/data_ingestion/download_mlb_bulk.py` | **WRAP** → `baseball/sources/mlb.py` | Keep as compatibility entry |
| `scripts/data_ingestion/download_mlb_games.py` | **WRAP** → `baseball/sources/mlb.py` | Keep as compatibility entry |
| `scripts/data_ingestion/download_mlb_schedules.py` | **WRAP** → `baseball/sources/mlb.py` | Keep as compatibility entry |
| `scripts/data_ingestion/fetch_mlb_schedule.py` | **WRAP** → `baseball/sources/mlb.py` | Keep as compatibility entry |

#### Bridge Scripts - Keep as Compatibility Entries
| Script | Action | Notes |
|--------|--------|-------|
| `scripts/bridge/populate_bridge_tables.py` | **WRAP** → `baseball/services/bridge.py` | Preserve as compatibility entry |
| `scripts/bridge/populate_game_xref.py` | **WRAP** → `baseball/services/bridge.py` | Merge into bridge build flow |
| `scripts/bridge/populate_season_aware_team_xref.py` | **WRAP** → `baseball/services/bridge.py` | Keep as compatibility entry |
| `scripts/bridge/populate_coach_umpire_bridge.py` | **WRAP** → `baseball/services/bridge.py` | Keep as compatibility entry |
| `scripts/bridge/populate_external_bridge.py` | **WRAP** → `baseball/services/bridge.py` | Keep as compatibility entry |
| `scripts/bridge/populate_espn_bridge.py` | **WRAP** → `baseball/services/bridge.py` | Keep as compatibility entry |

#### Ingestion Orchestrators - Keep as Compatibility Entries
| Script | Action | Notes |
|--------|--------|-------|
| `scripts/data_ingestion/complete_mlb_ingestion.py` | **WRAP** → `baseball pipeline run` | Keep as compatibility entry |
| `scripts/data_ingestion/ingest_all_mlb_data.py` | **WRAP** → `baseball pipeline run` | Keep as compatibility entry |
| `scripts/data_ingestion/ingest_current_season.py` | **KEEP** | Different use case (current season) |
| `scripts/data_ingestion/ingest_live_games.py` | **KEEP** | Different use case (live games) |

---

## Revised Consolidation Plan

### Phase 1: Archive Orphan Scripts
**Goal**: Clean up one-time use and experimental scripts

Move to `scripts/archive/`:
1. `scripts/bridge/investigate_coach_names.py`
2. `scripts/bridge/investigate_umpire_ids.py`
3. `scripts/bridge/replay_live_bridge_backfill.py`
4. Any EdgeForge experimental scripts not yet integrated

### Phase 2: Create Unified SQL Maintenance Script
**Goal**: Merge overlapping header/comment scripts

Create `scripts/utility/sql_maintenance.py`:
- Merge functionality from: add_sql_headers.py, add_table_comments.py, apply_accurate_headers.py, fix_sql_headers.py, convert_block_headers.py
- Add subcommands: add-headers, add-comments, fix-headers, convert-headers
- Archive merged scripts after verification

### Phase 3: Replace Shell Wrapper Duplicates
**Goal**: Eliminate duplicate orchestration paths

Update shell scripts to call new CLI:
1. `scripts/complete_mlb_ingestion.sh` → call `baseball pipeline run mlb_ingest`
2. `scripts/ingest_all_mlb_parallel.sh` → call `baseball pipeline run mlb_ingest --parallel`
3. `scripts/populate_all_missing_data.sh` → call `baseball pipeline run missing_data`

### Phase 4: Build Source Adapters (WRAP Pattern)
**Goal**: Create new baseball/sources/ adapters that WRAP existing scripts

Create `baseball/sources/mlb.py`:
- Methods call existing scripts (download_mlb_bulk.py, etc.)
- Preserves working logic
- Adds new CLI interface

Create `baseball/services/bridge.py`:
- Methods call existing bridge scripts
- Preserves working logic
- Adds new CLI interface

### Phase 5: E2E Testing
**Goal**: Verify new adapters work before any archiving

- Test that `baseball mlb download` calls download_mlb_bulk.py correctly
- Test that `baseball bridge populate` calls populate_bridge_tables.py correctly
- Only archive after verification passes

---

## Post-Consolidation Structure (Correct)

```
scripts/
├── data_ingestion/           # Keep existing scripts as compatibility entries
│   ├── download_mlb_bulk.py      # WRAPPED by baseball/sources/mlb.py
│   ├── download_mlb_games.py     # WRAPPED by baseball/sources/mlb.py
│   ├── download_mlb_schedules.py # WRAPPED by baseball/sources/mlb.py
│   ├── fetch_mlb_schedule.py     # WRAPPED by baseball/sources/mlb.py
│   ├── complete_mlb_ingestion.py # WRAPPED by baseball pipeline
│   ├── ingest_all_mlb_data.py    # WRAPPED by baseball pipeline
│   ├── ingest_current_season.py  # KEPT (different use case)
│   ├── ingest_live_games.py      # KEPT (different use case)
│   └── ...
├── bridge/                   # Keep existing scripts as compatibility entries
│   ├── populate_bridge_tables.py      # WRAPPED by baseball/services/bridge.py
│   ├── populate_game_xref.py        # WRAPPED by baseball/services/bridge.py
│   ├── populate_season_aware_team_xref.py # WRAPPED
│   └── ...
├── utility/                  # Consolidated utilities
│   └── sql_maintenance.py    # Merged from 4 header/comment scripts
├── archive/                  # Archived one-time scripts
│   ├── investigate_coach_names.py
│   ├── investigate_umpire_ids.py
│   └── replay_live_bridge_backfill.py
└── rebuild_warehouse.sh      # UPDATED to call baseball pipeline

baseball/                     # NEW package with WRAPPERS
├── sources/
│   ├── base.py               # BaseSource adapter interface
│   ├── mlb.py                # WRAPS download_mlb_*.py scripts
│   ├── espn.py               # WRAPS fetch_espn_mlb.py
│   ├── statcast.py           # WRAPS download_statcast.py
│   ├── lahman.py             # WRAPS download_lahman_data.py
│   └── retrosheet.py         # WRAPS retrosheet/ package
├── services/
│   └── bridge.py             # WRAPS bridge/ scripts
└── cli.py                    # Calls new adapters
```

---

## Scripts to Archive (Orphans Only)

1. `scripts/bridge/investigate_coach_names.py` - One-time investigation
2. `scripts/bridge/investigate_umpire_ids.py` - One-time investigation
3. `scripts/bridge/replay_live_bridge_backfill.py` - One-time backfill
4. EdgeForge experimental files (per AGENTS.md warning)

---

## Scripts to Merge (Only Overlapping Utilities)

1. `scripts/add_table_comments.py` → merge into sql_maintenance.py
2. `scripts/apply_accurate_headers.py` → merge into sql_maintenance.py
3. `scripts/fix_sql_headers.py` → merge into sql_maintenance.py
4. `scripts/convert_block_headers.py` → merge into sql_maintenance.py

---

## Scripts to WRAP (Preserve as Compatibility Entries)

Per major_update.md, these are working assets that get WRAPPED, not merged:

- All `scripts/data_ingestion/*.py` download/ingest scripts
- All `scripts/bridge/*.py` population scripts
- All `scripts/external_data/*.py` load scripts

---

## Success Criteria (Aligned with major_update.md)

1. ✅ **No orphan scripts** - All scripts have clear purpose or archived
2. ✅ **No duplicate orchestration paths** - Shell wrappers call new CLI
3. ✅ **Working logic preserved** - Existing scripts remain as compatibility entries
4. ✅ **New adapters wrap old scripts** - baseball/sources/ calls existing scripts
5. ✅ **Migration map updated** - Every move documented
6. ✅ **E2E tests pass** - Before any archiving

---

## Key Difference from Original Analysis

**Original (Wrong)**: Merge 14+ scripts into fewer files, archive originals
**Revised (Correct)**: WRAP existing scripts through new adapters, only archive true orphans

The major_update.md is clear: "Wrap and reorganize these. Do not discard them casually."
