# MLB Play-by-Play Data Pipeline

**Status**: Partially Implemented  
**Last Updated**: 2026-04-16  
**Priority**: High - Bridge population blocking pitch-level analysis

---

## Overview

This document defines the canonical workflow for ingesting, transforming, and linking MLB Stats API play-by-play data with Retrosheet historical data. The goal is to create pitch-level granularity that supplements Retrosheet's event-level data.

## Data Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SOURCE LAYER (Raw)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  raw_mlb.schedule_snapshots        - MLB schedule API responses             │
│  raw_mlb.live_feed_snapshots       - Full game feed JSON (72,830 games)     │
│  raw_retrosheet.*                  - Chadwick/Retrosheet historical           │
└─────────────────────────────────────────────────────────────────────────────┘
                                       ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      TRANSFORMATION LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  OPTION A: mlb_pbp_collector.py → CSV → ingest_mlb_pbp.py → core.mlb_pbp   │
│  OPTION B: transform_live_comprehensive.py → core.live_games/events         │
│  FUTURE: Direct raw→mlb.pitches extraction (not yet implemented)            │
└─────────────────────────────────────────────────────────────────────────────┘
                                       ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      BRIDGE LAYER (Crosswalk)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  bridge.game_xref       - MLB game_pk ↔ Retrosheet game_id                  │
│  bridge.player_xref     - MLB player_id ↔ Retrosheet player_id               │
│  bridge.team_xref       - MLB team_id ↔ Retrosheet team_code                 │
│  bridge.park_xref       - MLB venue_id ↔ Retrosheet park_id                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CANONICAL LAYER (Typed)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  core.games               - Unified game dimension                           │
│  core.events              - Retrosheet event-level data                      │
│  core.mlb_pbp             - MLB play-by-play (at-bat level)                  │
│  mlb.pitches              - Pitch-level data (one row per pitch)             │
│  mlb.play_events          - Play events from live feed                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                       ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ANALYSIS LAYER (Combined)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  analysis.combined_games         - Historical + live games                   │
│  analysis.combined_events        - Retrosheet + MLB events                   │
│  analysis.mlb_retrosheet_pbp_join - Pitch data linked to Retrosheet         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Current Implementation Status

| Component | Status | Rows/Details | Blocker |
|-----------|--------|--------------|---------|
| `raw_mlb.schedule_snapshots` | ✅ Complete | 9,561 rows | - |
| `raw_mlb.live_feed_snapshots` | ✅ Complete | 72,830 rows (25 failed with HTTP 500) | - |
| `bridge.game_xref` | ❌ **EMPTY** | 0 rows | **BLOCKING** - Need to populate |
| `bridge.player_xref` | ❌ **EMPTY** | 0 rows | **BLOCKING** - Need to populate |
| `bridge.team_xref` | ❌ **EMPTY** | 0 rows | **BLOCKING** - Need to populate |
| `core.mlb_pbp` | ⚠️ Minimal | 76 rows | Needs bulk ingestion |
| `mlb.pitches` | ❌ **EMPTY** | 0 rows | Needs extraction from live_feed_snapshots |
| `mlb.play_events` | ❌ **EMPTY** | 0 rows | Needs extraction |
| `core.live_games` | ⚠️ Partial | 67,913 rows | Some games not yet transformed |
| `core.live_events` | ⚠️ Partial | 5,172,275 rows | Some events not yet transformed |

---

## Canonical Workflows

### Phase 1: Bridge Population (REQUIRED FIRST)

**Purpose**: Create crosswalk tables linking MLB and Retrosheet identifiers.

**Command**:
```bash
python3 scripts/populate_bridge_tables.py
```

**What it does**:
1. Downloads Chadwick Bureau Register CSV (player/team/park ID mappings)
2. Populates `bridge.player_xref` with MLB ↔ Retrosheet player mappings
3. Populates `bridge.team_xref` with MLB team ↔ Retrosheet team code mappings
4. Populates `bridge.park_xref` with MLB venue ↔ Retrosheet park mappings
5. Populates `bridge.game_xref` by matching game dates + teams

**Verification**:
```sql
-- Check bridge population
SELECT 
    (SELECT COUNT(*) FROM bridge.game_xref) as games_mapped,
    (SELECT COUNT(*) FROM bridge.player_xref) as players_mapped,
    (SELECT COUNT(*) FROM bridge.team_xref) as teams_mapped,
    (SELECT COUNT(*) FROM bridge.park_xref) as parks_mapped;
```

**Blocking Status**: ⚠️ **MUST COMPLETE BEFORE Phase 2** - Without bridge tables, MLB data cannot be linked to Retrosheet events.

---

### Phase 2A: Historical MLB PBP via CSV (Current Working Path)

**Purpose**: Extract play-by-play data using pybaseball + MLB Stats API.

**Command**:
```bash
# Step 1: Collect PBP data to CSV
python3 scripts/mlb_pbp_collector.py --season 2024 --output-csv data/mlb_pbp/mlb_pbp_2024.csv

# Step 2: Ingest CSV to database
python3 scripts/ingest_mlb_pbp.py --csv data/mlb_pbp/mlb_pbp_2024.csv
```

**What it does**:
1. Uses `statsapi` (MLB-StatsAPI package) to fetch play-by-play
2. Uses `pybaseball` to fetch Statcast pitch-level data
3. Merges data on game_pk + at_bat_number + pitch_number
4. Outputs CSV with columns: game_pk, pitch_type, release_speed, spin_rate, plate_x, plate_z, etc.
5. `ingest_mlb_pbp.py` loads CSV into `core.mlb_pbp`

**Data Destination**: `core.mlb_pbp` (at-bat level, not individual pitches)

**Limitations**:
- One row per plate appearance, not per pitch
- Pitch sequence stored as string (e.g., "CBSBFC")
- Limited pitch-level metrics (only last pitch of PA)

---

### Phase 2B: Direct Live Feed Extraction (Future Enhancement)

**Purpose**: Extract individual pitch rows from the 72,830 stored live feed snapshots.

**Status**: ⚠️ **NOT YET IMPLEMENTED** - Script needed

**Proposed Implementation**:
```bash
# Future command
python3 scripts/extract_pitches_from_snapshots.py --season 2000-2025
```

**What it should do**:
1. Query `raw_mlb.live_feed_snapshots` for games without pitch extraction
2. Parse JSON payload: `liveData.plays.allPlays[].playEvents[]`
3. Filter `isPitch = true` events
4. Extract per-pitch fields:
   - `index` → pitch_number
   - `pitchData.startSpeed` → release_speed
   - `pitchData.spinRate` → spin_rate
   - `pitchData.coordinates.pX/pZ` → plate_x/plate_z
   - `pitchData.breaks.*` → break_angle, break_length
   - `details.type.code` → pitch_type_code
   - `details.call.code` → pitch_call_code
5. Insert into `mlb.pitches` with foreign key to `mlb.play_events`

**Data Destination**: `mlb.pitches` (one row per pitch)

**Schema Alignment**:
The extracted data should match the user's pitch-by-pitch architecture spec:
- `game_pk` (from payload.gameData.game.pk)
- `at_bat_number` (from play.atBatIndex)
- `pitch_number` (from playEvents.index)
- `batter_id`, `pitcher_id` (from play.matchup)
- `inning`, `inning_half`, `outs_before`
- `balls_before`, `strikes_before`
- `pitch_type_code`, `pitch_type_name`
- `release_speed`, `spin_rate`, `plate_x`, `plate_z`
- `pfx_x`, `pfx_z`, `break_angle`, `break_length`
- `zone`, `type_confidence`

---

### Phase 3: Linking MLB Pitches to Retrosheet Events

**Purpose**: Join pitch-level data with Retrosheet event-level data via bridge tables.

**Prerequisites**: 
- ✅ Bridge tables populated (Phase 1)
- ✅ Pitch data extracted (Phase 2A or 2B)

**Query Pattern**:
```sql
-- Link MLB pitches to Retrosheet events
SELECT 
    r.game_id as retrosheet_game_id,
    r.event_id as retrosheet_event_id,
    r.bat_id,
    r.pit_id,
    r.inning,
    r.event_cd,
    p.pitch_number,
    p.pitch_type_code,
    p.release_speed,
    p.spin_rate,
    p.plate_x,
    p.plate_z
FROM core.events r
JOIN bridge.game_xref gx ON r.game_id = gx.retrosheet_game_id
JOIN mlb.pitches p ON gx.mlb_game_pk = p.game_pk
WHERE r.bat_id = p.batter_id  -- Same batter
  AND r.pit_id = p.pitcher_id  -- Same pitcher
  AND r.inning = p.inning      -- Same inning
ORDER BY r.game_id, r.event_id, p.pitch_number;
```

**Join Strategy**:
1. Match games via `bridge.game_xref`
2. Match batters via `bridge.player_xref`
3. Match pitchers via `bridge.player_xref`
4. Match context: inning, base state, count
5. Validate: temporal sequence alignment

---

## Data Quality & Validation

### Row Count Validation

```sql
-- Validate data completeness by season
SELECT 
    season,
    COUNT(DISTINCT game_pk) as games_in_raw,
    (SELECT COUNT(DISTINCT mlb_game_pk) FROM bridge.game_xref WHERE season = lfs.season) as games_mapped,
    (SELECT COUNT(DISTINCT game_pk) FROM mlb.pitches p WHERE p.season = lfs.season) as games_with_pitches
FROM raw_mlb.live_feed_snapshots lfs
WHERE http_status = 200
GROUP BY season
ORDER BY season;
```

### Bridge Mapping Validation

```sql
-- Check unmapped games
SELECT season, COUNT(*) as unmapped_games
FROM raw_mlb.live_feed_snapshots lfs
WHERE http_status = 200
  AND NOT EXISTS (
    SELECT 1 FROM bridge.game_xref gx 
    WHERE gx.mlb_game_pk = lfs.game_pk
  )
GROUP BY season;
```

### Pitch Data Validation

```sql
-- Validate pitch extraction completeness
SELECT 
    game_pk,
    COUNT(*) as pitch_count,
    COUNT(DISTINCT at_bat_number) as pa_count,
    AVG(release_speed) as avg_speed,
    COUNT(CASE WHEN pitch_type_code IS NULL THEN 1 END) as missing_pitch_type
FROM mlb.pitches
GROUP BY game_pk
ORDER BY pitch_count DESC
LIMIT 10;
```

---

## Troubleshooting

### Issue: Bridge tables empty after populate_bridge_tables.py

**Symptoms**: 
```sql
SELECT COUNT(*) FROM bridge.game_xref;  -- Returns 0
```

**Diagnosis**:
1. Check if Chadwick Register files downloaded:
   ```bash
   ls -la data/raw/chadwick/register/
   ```
2. Check for errors in script output:
   ```bash
   python3 scripts/populate_bridge_tables.py 2>&1 | tee /tmp/bridge_population.log
   ```

**Resolution**:
- Ensure `data/raw/chadwick/register/` exists with CSV files
- Check network connectivity to Chadwick Bureau
- Verify `core.games` has Retrosheet data to match against

---

### Issue: core.mlb_pbp has only 76 rows

**Symptoms**: 
```sql
SELECT COUNT(*) FROM core.mlb_pbp;  -- Returns 76
```

**Cause**: CSV files not ingested after collection.

**Resolution**:
```bash
# Check for CSV files
ls -la data/mlb_pbp/*.csv

# Ingest all CSV files
python3 scripts/ingest_mlb_pbp.py --dir data/mlb_pbp/
```

---

### Issue: mlb.pitches is empty

**Symptoms**:
```sql
SELECT COUNT(*) FROM mlb.pitches;  -- Returns 0
```

**Cause**: No script has extracted pitch-level data from live_feed_snapshots yet.

**Resolution**: 
- Phase 2B (direct extraction) needs to be implemented
- OR use Phase 2A (CSV via mlb_pbp_collector) which populates core.mlb_pbp instead

---

## Next Steps (Priority Order)

1. **🔴 CRITICAL**: Run `populate_bridge_tables.py` to enable cross-source linking
2. **🟡 HIGH**: Implement `extract_pitches_from_snapshots.py` for pitch-level granularity
3. **🟡 HIGH**: Create `analysis.mlb_retrosheet_pitch_join` view for unified querying
4. **🟢 MEDIUM**: Backfill missing games (25 HTTP 500 errors from bulk download)
5. **🟢 MEDIUM**: Validate pitch data quality and coverage
6. **🔵 LOW**: Document edge cases (exhibition games, All-Star games, etc.)

---

## Related Documentation

- `docs/agents/PROCEDURES.md` - Canonical warehouse workflows
- `docs/MLB_API_INTEGRATION_GUIDE.md` - MLB Stats API endpoint details
- `docs/LIVE_DATA_ARCHITECTURE.md` - Real-time data flow design
- `scripts/mlb_pbp_collector.py` - PBP data collection (CSV path)
- `scripts/ingest_mlb_pbp.py` - CSV to database ingestion
- `scripts/transform_live_comprehensive.py` - Live feed transformation
- `scripts/populate_bridge_tables.py` - Crosswalk table population

---

## Schema Reference

### Key Join Columns

| Table | Key Column | Description | Joins To |
|-------|------------|-------------|----------|
| raw_mlb.live_feed_snapshots | game_pk | MLB game identifier | bridge.game_xref.mlb_game_pk |
| bridge.game_xref | mlb_game_pk | MLB side of bridge | raw_mlb.live_feed_snapshots |
| bridge.game_xref | retrosheet_game_id | Retrosheet side | core.games.game_id |
| core.events | game_id | Retrosheet game key | bridge.game_xref.retrosheet_game_id |
| mlb.pitches | game_pk | MLB game key | bridge.game_xref.mlb_game_pk |
| mlb.pitches | batter_id | MLB batter ID | bridge.player_xref.mlb_player_id |
| mlb.pitches | pitcher_id | MLB pitcher ID | bridge.player_xref.mlb_player_id |

### Play-by-Play Grain

| Table | Grain | Primary Key | Notes |
|-------|-------|-------------|-------|
| core.events | Event/PA | game_id, event_id | Retrosheet events |
| core.mlb_pbp | At-bat | game_pk, event_sequence | One row per PA |
| mlb.pitches | Pitch | game_pk, at_bat_number, pitch_number | One row per pitch |
| mlb.play_events | Play event | game_pk, play_id, event_index | All play events |

---

**Document Owner**: Data Engineering  
**Review Cycle**: Monthly or when pipeline changes  
**Questions**: Check `docs/agents/PROCEDURES.md` or create GitHub issue
