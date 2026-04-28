# Database Schema Reference for Codex

## Overview

This document provides a high-level overview of the baseball prediction warehouse database schema. 

**Full Schema Dump**: `docs/schema_dump.sql` (23,000+ lines - contains complete DDL)

**Database**: PostgreSQL retrosheet database
**Size**: ~45M rows, 100+ tables across 20+ schemas

---

## Schema Organization

| Schema | Purpose | Table Count |
|--------|---------|-------------|
| **raw_*** | Raw data from external sources | 50+ tables |
| **core** | Canonical tables (games, events, players) | 15 tables |
| **bridge** | ID cross-reference mappings | 10 tables |
| **features** | ML feature tables | 20+ tables |
| **features_pitch** | Pitch-level features | 10+ tables |
| **models** | Model registry and training runs | 5 tables |
| **serving** | Low-latency serving views/tables | 10+ views |
| **admin** | Pipeline runs, checkpoints | 5 tables |
| **mlb** | MLB-specific data | 20+ tables |

---

## Key Tables by Layer

### Raw Layer (10_raw)

| Table | Source | Purpose |
|-------|--------|---------|
| raw_mlb.live_feed_snapshots | MLB Stats API | Real-time game JSON |
| raw_mlb.schedule_snapshots | MLB Stats API | Daily schedules |
| raw_mlb.reference_snapshots | MLB Stats API | Teams, rosters, venues |
| raw_mlb.statcast | Baseball Savant | Pitch-level data |
| raw_espn.game_snapshots | ESPN API | Game data |
| raw_espn.schedule_snapshots | ESPN API | Schedule |
| raw_retrosheet.event_files | Retrosheet | Historical events |
| raw_lahman.* | Lahman DB | Historical stats |

### Core Layer (30_core)

| Table | Grain | Key Columns |
|-------|-------|-------------|
| core.games | One per game | game_id, season, game_date, home_team_id, away_team_id, home_score, away_score |
| core.events | One per play | event_id, game_id, inning, outs, base_state, event_type, batter_id, pitcher_id |
| core.plate_appearances | One per PA | pa_id, game_id, batter_id, pitcher_id, at_bat_result, exit_velocity, launch_angle |
| core.players | One per player | player_id, name_first, name_last, birth_date, bats, throws |
| core.teams | One per team | team_id, team_name, league, division, franchise_id |
| core.parks | One per park | park_id, park_name, city, state |
| core.live_games | One per live game | game_pk, status, home_team, away_team, current_inning, outs, base_state |

### Bridge Layer (40_bridge)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| bridge.player_xref | Player ID mapping | player_id, retrosheet_id, mlb_id, espn_id, statcast_id, confidence |
| bridge.team_xref | Team ID mapping | team_id, retrosheet_id, mlb_id, espn_id |
| bridge.game_xref | Game ID mapping | game_id, retrosheet_id, mlb_id |
| bridge.park_xref | Park ID mapping | park_id, retrosheet_id, mlb_id |
| bridge.umpire_xref | Umpire ID mapping | umpire_id, retrosheet_id, mlb_id |

### Features Layer (50_features)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| features.win_expectancy_matrix | 24-state WE lookup | inning, is_top_inning, score_diff, base_state, outs, win_probability |
| features.leverage_index_matrix | LI lookup | inning, is_top_inning, score_diff, base_state, outs, leverage_index |
| features.run_expectancy_matrix | RE 24-state matrix | base_state, outs, expected_runs, season |
| features.matchup_features | Batter-pitcher history | batter_id, pitcher_id, pa_count, batter_avg, pitcher_era_vs_batter |
| features.rolling_form | 30-day player stats | player_id, season, game_date, avg_30d, ops_30d, form_trend |
| features.bullpen_stress | Bullpen fatigue | team_id, game_date, stress_index, available_pitchers |

### Models Layer (60_models)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| models.registry | Model metadata | model_id, model_name, model_type, version, status, created_at |
| models.training_runs | Training history | run_id, model_id, season, started_at, completed_at, metrics |
| models.artifacts | Model binaries | artifact_id, model_id, file_path, checksum, size_bytes |
| models.evaluations | Model performance | eval_id, model_id, metric_name, metric_value, evaluated_at |

### Serving Layer (70_serving)

| View/Table | Purpose | Key Columns |
|-------------|---------|-------------|
| serving.mv_current_standings | Team standings | team_id, wins, losses, win_pct, runs_scored, runs_allowed, gb |
| serving.mv_player_form_30d | Recent player stats | player_id, role, pa_last_30d, avg_last_30d, form_trend |
| serving.mv_we_lookup | Fast WE lookup | inning, is_top, score_diff, base_state, outs, win_probability |
| serving.mv_li_lookup | Fast LI lookup | inning, is_top, score_diff, base_state, outs, leverage_index |
| serving.mv_pitcher_arsenal | Pitcher pitch types | pitcher_id, pitch_type, avg_velocity, avg_spin, whiff_rate |
| serving.win_prob_predictions | WP predictions | game_pk, at_bat_index, home_win_probability, confidence |

### Admin Layer (00_admin)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| admin.pipeline_runs | Pipeline tracking | run_id, pipeline_name, status, started_at, completed_at |
| admin.pipeline_checkpoints | Resume state | checkpoint_id, run_id, step_name, status, completed_at |
| admin.pipeline_errors | Error logging | error_id, run_id, step_name, error_message, stack_trace |
| admin.system_metadata | System info | key, value, updated_at |

---

## Important SQL Files for Codex

When working on features/models, read these SQL files:

### Feature SQL Files
```
sql/50_features/5032_features_win_expectancy.sql       - WE matrix
sql/50_features/5033_features_leverage_index.sql       - LI matrix
sql/50_features/5034_features_matchup.sql              - Matchup features
sql/50_features/5035_features_rolling_form.sql         - Rolling form
sql/50_features/5036_features_bullpen.sql              - Bullpen stress
```

### Model SQL Files
```
sql/60_models/600_models_registry.sql                  - Model registry
sql/60_models/601_models_training_runs.sql             - Training tracking
sql/60_models/602_models_artifacts.sql                 - Model storage
```

### Serving SQL Files
```
sql/70_serving/701_serving_views.sql                   - Serving layer
```

---

## Table Grain Reference

Always check table grain before writing queries:

| Table | Grain | Natural Key | Notes |
|-------|-------|-------------|-------|
| core.games | One per game | (game_date, home_team, away_team) | game_id = surrogate |
| core.events | One per play | (game_id, event_id) | event_id = sequence in game |
| core.plate_appearances | One per PA | (game_id, at_bat_index) | at_bat_index = PA sequence |
| bridge.player_xref | One per player | player_id | Maps multiple source IDs |
| features.win_expectancy_matrix | One per state | (inning, is_top, score_diff, base_state, outs) | 24 * innings * score_diffs |
| models.registry | One per model version | (model_name, version) | status = active/archived |
| serving.win_prob_predictions | One per prediction | (game_pk, at_bat_index, model_version) | Mutable - can have multiple versions |

---

## Key Relationships

```
raw_mlb.live_feed_snapshots 
    → core.live_games (via game_pk)
    → core.live_events
    → features.* (via transformation)

core.games
    → core.events (game_id)
    → core.plate_appearances (game_id)
    → models.training_data (game features)

core.players
    → bridge.player_xref (player_id)
    → features.rolling_form (player_id)
    → models.features (batter/pitcher IDs)

models.registry
    → models.training_runs (model_id)
    → models.artifacts (model_id)
    → serving.win_prob_predictions (model_name/version)
```

---

## Indexes for Performance

Key indexes to know about:

```sql
-- Game lookups
CREATE INDEX idx_games_date ON core.games(game_date, season);
CREATE INDEX idx_games_teams ON core.games(home_team_id, away_team_id);

-- Event lookups
CREATE INDEX idx_events_game ON core.events(game_id, event_id);
CREATE INDEX idx_events_batter ON core.events(batter_id, game_date);

-- Feature lookups
CREATE INDEX idx_we_lookup ON features.win_expectancy_matrix(
    inning, is_top_inning, score_diff, base_state, outs
);
CREATE INDEX idx_li_lookup ON features.leverage_index_matrix(
    inning, is_top_inning, score_diff, base_state, outs
);

-- Bridge lookups
CREATE INDEX idx_player_xref_mlb ON bridge.player_xref(mlb_id);
CREATE INDEX idx_player_xref_retro ON bridge.player_xref(retrosheet_id);
```

---

## Common Query Patterns

### Get Current Game State
```sql
SELECT 
    g.game_pk, g.status, g.current_inning, g.is_top_inning,
    g.home_score, g.away_score, g.base_state, g.outs,
    g.batter_id, g.pitcher_id
FROM core.live_games g
WHERE g.game_pk = ?;
```

### Get Win Expectancy
```sql
SELECT win_probability 
FROM features.win_expectancy_matrix
WHERE inning = ?
  AND is_top_inning = ?
  AND score_diff = ?
  AND base_state = ?
  AND outs = ?;
```

### Get Batter Form
```sql
SELECT avg_30d, ops_30d, form_trend
FROM features.rolling_form
WHERE player_id = ?
  AND season = ?
  AND game_date <= ?
ORDER BY game_date DESC
LIMIT 1;
```

### Get Player Canonical ID
```sql
SELECT player_id, confidence
FROM bridge.player_xref
WHERE mlb_id = ?;
```

---

## Data Volumes (Approximate)

| Table | Rows | Size |
|-------|------|------|
| core.games | ~62,000 | ~50MB |
| core.events | ~7.6M | ~2GB |
| core.plate_appearances | ~1.8M | ~500MB |
| raw_mlb.statcast | ~7.6M | ~5GB |
| bridge.player_xref | ~25,000 | ~5MB |
| features.* | Varies | ~1GB total |

---

## For Codex: What to Read

When implementing new features/models:

1. **Always read the SQL files** for the layer you're working in:
   - Features → Read `sql/50_features/50*.sql`
   - Models → Read `sql/60_models/*.sql`
   - Serving → Read `sql/70_serving/*.sql`

2. **Check existing patterns**:
   - How do existing calculators query the DB?
   - What table/column naming conventions are used?
   - How are indexes defined?

3. **Match the grain**:
   - What makes a row unique?
   - What are the foreign key relationships?
   - What columns are required vs nullable?

4. **Test with real schema**:
   - Use `docs/schema_dump.sql` as reference
   - Verify column types match
   - Check for existing tables before creating new ones

---

## Full Schema Dump Location

```
/home/cbwinslow/workspace/retrosheet/docs/schema_dump.sql
```

This file contains complete DDL:
- All CREATE SCHEMA statements
- All CREATE TABLE statements
- All CREATE INDEX statements
- All CREATE FUNCTION/PROCEDURE statements
- All COMMENT ON statements

Use this when you need precise column types, constraints, or relationships.
