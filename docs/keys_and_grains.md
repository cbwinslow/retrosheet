# Keys and Grains

**Purpose**: This document defines the entity keys (primary, foreign, natural) and table grains (what makes a row unique) for the baseball data warehouse. Essential for join logic, data quality checks, and ML feature engineering.

---

## Terminology

| Term | Definition |
|------|------------|
| **Surrogate Key** | System-generated unique identifier (UUID or SERIAL) |
| **Natural Key** | Business identifier from source system |
| **Grain** | Level of uniqueness (what makes a row distinct) |
| **Cardinality** | Relationship type (1:1, 1:N, M:N) |
| **Temporal Key** | Date/time component for time-series data |

---

## Core Entities

### Teams

**Table**: `core.teams`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `team_id` (UUID) | Internal reference |
| **Natural Key** | `franchise_id` + `season` | Retrosheet franchise + year |
| **Alternate NK** | `mlb_org_id` + `season` | MLB org ID + year |
| **Grain** | One row per franchise per season | Team relocations = new row |

**Bridge Mapping**: `bridge.team_xref` links `source_id` (per source) to `team_id`

---

### Players

**Table**: `core.players`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `player_id` (UUID) | Internal reference |
| **Natural Key** | `retrosheet_id` | Retrosheet player code (8 chars) |
| **Alternate NK** | `mlb_person_id` | MLB API person ID |
| **Alternate NK** | `espn_id` | ESPN player ID |
| **Grain** | One row per player career | Single record per person |

**Bridge Mapping**: `bridge.player_xref` links multiple source IDs to `player_id`

---

### Parks

**Table**: `core.parks`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `park_id` (UUID) | Internal reference |
| **Natural Key** | `retrosheet_park_id` | Retrosheet park code |
| **Alternate NK** | `mlb_venue_id` | MLB API venue ID |
| **Grain** | One row per physical park | Park renovations = same park |

---

### Games

**Table**: `core.games`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `game_id` (UUID) | Internal reference |
| **Natural Key** | `retrosheet_game_id` | Retrosheet game ID (12 chars) |
| **Alternate NK** | `mlb_game_pk` | MLB API gamePk |
| **Alternate NK** | `espn_game_id` | ESPN game ID |
| **Temporal** | `game_date` | ISO date (YYYY-MM-DD) |
| **Grain** | One row per game | Historical game record |

**Foreign Keys**:
- `home_team_id` → `core.teams.team_id`
- `away_team_id` → `core.teams.team_id`
- `park_id` → `core.parks.park_id`

---

### Events (Play-by-Play)

**Table**: `core.events`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `event_id` (UUID) | Internal reference |
| **Natural Key** | `game_id` + `event_seq` | Game + sequence number |
| **Alternate NK** | `retrosheet_event_id` | Retrosheet event key |
| **Temporal** | `game_date` + `inning` + `event_seq` | Time within game |
| **Grain** | One row per play event | Individual pitch or play |

**Foreign Keys**:
- `game_id` → `core.games.game_id`
- `batter_id` → `core.players.player_id`
- `pitcher_id` → `core.players.player_id`

---

### Plate Appearances

**Table**: `core.plate_appearances`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `pa_id` (UUID) | Internal reference |
| **Natural Key** | `game_id` + `pa_seq` | Game + PA sequence |
| **Temporal** | `game_date` | For partitioning |
| **Grain** | One row per plate appearance | Aggregated from events |

**Foreign Keys**:
- `game_id` → `core.games.game_id`
- `batter_id` → `core.players.player_id`
- `pitcher_id` → `core.players.player_id`

---

## Live Entities

### Live Games

**Table**: `core.live_games`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `live_game_id` (UUID) | Internal reference |
| **Natural Key** | `mlb_game_pk` | MLB API gamePk |
| **Temporal** | `last_updated_at` | Timestamp of last change |
| **Grain** | One row per live game | Mutable (updated in real-time) |

**Key Difference from `core.games`**: Live table is mutable; updates in real-time. Historical `core.games` is immutable after initial load.

---

### Live Events

**Table**: `core.live_events`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `live_event_id` (UUID) | Internal reference |
| **Natural Key** | `mlb_game_pk` + `play_id` | MLB API play ID |
| **Temporal** | `wall_clock_time` | Actual event time |
| **Grain** | One row per live event | Individual play/pitch |

---

## Bridge/Xref Tables

### Player Xref

**Table**: `bridge.player_xref`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `xref_id` (UUID) | Internal reference |
| **Composite Key** | `source_system` + `source_id` | Unique per source |
| **Grain** | One row per source player ID | Multiple rows per canonical player |

**Foreign Keys**:
- `player_id` → `core.players.player_id`

**Example Data**:

| source_system | source_id | player_id | confidence_score |
|---------------|-----------|-----------|------------------|
| retrosheet | 'aaroh101' | <uuid> | 1.0 |
| mlb | 605141 | <uuid> | 1.0 |
| espn | 32610 | <uuid> | 0.95 |
| statcast | 605141 | <uuid> | 1.0 |

---

### Team Xref

**Table**: `bridge.team_xref`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `xref_id` (UUID) | Internal reference |
| **Composite Key** | `source_system` + `source_id` + `season` | Unique per source per year |
| **Grain** | One row per source team ID per season | Team IDs can change year-to-year |

---

### Game Xref

**Table**: `bridge.game_xref`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `xref_id` (UUID) | Internal reference |
| **Composite Key** | `source_system` + `source_id` | Unique per source |
| **Grain** | One row per source game ID | Links multiple sources to canonical game |

---

## Feature Tables

### Run Expectancy State

**Table**: `features.run_expectancy_state`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `re_state_id` (UUID) | Internal reference |
| **Natural Key** | `outs` + `runner_on_1b` + `runner_on_2b` + `runner_on_3b` + `season` | Base-out state + year |
| **Grain** | One row per base-out state per season | 24 states × seasons |

**Dimensions**:
- `outs`: 0, 1, 2
- `runners`: Boolean for 1B, 2B, 3B occupancy
- `season`: Year (RE changes over time)

---

### Win Expectancy State

**Table**: `features.win_expectancy_state`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `we_state_id` (UUID) | Internal reference |
| **Natural Key** | `inning` + `top_bottom` + `score_diff` + `outs` + `runners` + `season` | Game state + year |
| **Grain** | One row per game state per season | Many combinations |

---

### Live Game State

**Table**: `features.live_game_state`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `state_id` (UUID) | Internal reference |
| **Natural Key** | `mlb_game_pk` + `play_id` | Game + play |
| **Temporal** | `wall_clock_time` | For ordering |
| **Grain** | One row per play | Features for each play |

---

## Model Tables

### Model Registry

**Table**: `models.registry`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `model_id` (UUID) | Internal reference |
| **Natural Key** | `model_name` + `version` | Semantic version |
| **Grain** | One row per model version | Immutable after registration |

---

### Training Runs

**Table**: `models.training_runs`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `run_id` (UUID) | Internal reference |
| **Natural Key** | `model_id` + `run_timestamp` | Model + when trained |
| **Grain** | One row per training run | Includes metrics, config |

---

### Predictions

**Table**: `serving.game_predictions`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `prediction_id` (UUID) | Internal reference |
| **Natural Key** | `model_id` + `game_id` + `prediction_timestamp` | Who, what, when |
| **Grain** | One row per prediction | Immutable record |

---

## Admin Tables

### Pipeline Runs

**Table**: `admin.pipeline_runs`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `run_id` (UUID) | Internal reference |
| **Natural Key** | `pipeline_name` + `started_at` | Pipeline + start time |
| **Grain** | One row per pipeline execution | Tracks status, duration |

---

### Pipeline Checkpoints

**Table**: `admin.pipeline_checkpoints`

| Key Type | Column(s) | Notes |
|----------|-----------|-------|
| **Surrogate PK** | `checkpoint_id` (UUID) | Internal reference |
| **Composite Key** | `pipeline_name` + `checkpoint_key` | Pipeline + identifier |
| **Grain** | One row per checkpoint | Resume capability |

---

## Join Patterns

### Historical Game + Events

```sql
SELECT g.game_date, e.inning, e.event_text
FROM core.games g
JOIN core.events e ON e.game_id = g.game_id
WHERE g.game_date = '2024-04-01';
```

### Player with All IDs

```sql
SELECT p.player_id, p.name,
       px_mlb.source_id AS mlb_id,
       px_espn.source_id AS espn_id
FROM core.players p
LEFT JOIN bridge.player_xref px_mlb 
    ON px_mlb.player_id = p.player_id AND px_mlb.source_system = 'mlb'
LEFT JOIN bridge.player_xref px_espn 
    ON px_espn.player_id = p.player_id AND px_espn.source_system = 'espn';
```

### Live Game State with Predictions

```sql
SELECT lg.mlb_game_pk, lgs.state_features,
       pred.home_win_probability
FROM core.live_games lg
JOIN features.live_game_state lgs ON lgs.mlb_game_pk = lg.mlb_game_pk
JOIN serving.game_predictions pred 
    ON pred.game_id = lg.live_game_id
WHERE pred.model_id = '<win_prob_model_uuid>';
```

---

## Data Quality Checks

### Key Uniqueness

```sql
-- Check for duplicate natural keys
SELECT retrosheet_game_id, COUNT(*)
FROM core.games
GROUP BY retrosheet_game_id
HAVING COUNT(*) > 1;
```

### Orphaned Records

```sql
-- Check for events without valid games
SELECT e.event_id
FROM core.events e
LEFT JOIN core.games g ON g.game_id = e.game_id
WHERE g.game_id IS NULL;
```

### Bridge Completeness

```sql
-- Check for players without MLB mapping
SELECT p.player_id, p.name
FROM core.players p
LEFT JOIN bridge.player_xref px 
    ON px.player_id = p.player_id AND px.source_system = 'mlb'
WHERE px.xref_id IS NULL;
```

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Migration Agent | Initial keys and grains specification |
