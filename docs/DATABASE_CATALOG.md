# Retrosheet Database Catalog

**Database:** retrosheet (PostgreSQL)  
**Documentation Date:** April 24, 2026  
**Purpose:** Complete catalog of all database objects, schemas, tables, views, functions, and procedures

---

## 📊 Schema Overview

| Schema | Tables | Views | Functions/Procedures | Purpose |
|--------|--------|-------|---------------------|---------|
| **analysis** | 0 | 5 | 10 | Data quality and analysis utilities |
| **baseball_savant** | 3 | 0 | 0 | Baseball Savant statistics |
| **bridge** | 8 | 9 | 8 | ID cross-references between data sources |
| **chat** | 1 | 0 | 0 | Chatbot query logging |
| **core** | 10 | 19 | 5 | Canonical baseball entities |
| **cron** | 2 | 0 | 5 | pg_cron job scheduling |
| **eda** | 0 | 17 | 0 | Exploratory data analysis views |
| **features** | 1 | 16 | 1 | ML feature engineering |
| **features_pitch** | 13 | 3 | 3 | Pitch-level ML features |
| **inference** | 1 | 0 | 4 | Model inference utilities |
| **lahman** | 19 | 0 | 0 | Lahman baseball database |
| **market_edges** | 2 | 0 | 0 | Prediction market data |
| **metadata** | 2 | 0 | 7 | Data dictionary and metadata |
| **mlb** | 6 | 1 | 1 | MLB API data |
| **mlb_enhanced** | 4 | 0 | 0 | Enhanced MLB statistics |
| **mlb_features** | 6 | 0 | 3 | MLB-derived features |
| **mlb_models** | 2 | 0 | 0 | Model training data |
| **models** | 1 | 0 | 0 | Model registry |
| **predictions** | 10 | 3 | 1 | Prediction storage |
| **raw_baseball_reference** | 2 | 0 | 0 | Baseball Reference raw data |
| **raw_bref** | 2 | 0 | 0 | Baseball Reference staging |
| **raw_espn** | 5 | 0 | 0 | ESPN API raw data |
| **raw_external** | 1 | 0 | 0 | External data sources |
| **raw_lahman** | 10 | 0 | 0 | Lahman raw staging |
| **raw_markets** | 1 | 0 | 0 | Market data raw |
| **raw_mlb** | 10 | 1 | 3 | MLB API raw snapshots |
| **raw_mlb_rosters** | 1 | 0 | 0 | MLB roster snapshots |
| **raw_park_factors** | 1 | 0 | 0 | Park factor data |
| **raw_retrosheet** | 19 | 2 | 7 | Retrosheet raw data |
| **raw_sportradar** | 2 | 0 | 2 | SportRadar data |
| **raw_statcast** | 2 | 0 | 0 | Statcast raw data |
| **test** | 1 | 0 | 0 | Test schema |
| **validation** | 0 | 10 | 1 | Data validation views |
| **warehouse** | 3 | 2 | 12 | Feature population orchestration |

**Total Objects:** 152 tables, 85 views, 87 functions/procedures

---

## 🗄️ Schema Details

---

### `analysis` Schema

**Purpose:** Data quality analysis and validation utilities

#### Functions (10)

| Name | Type | Arguments | Description |
|------|------|-----------|-------------|
| `calculate_mlb_data_quality` | FUNCTION | `game_id_param text` | Calculate data quality score for specific game |
| `detect_duplicate_games` | PROCEDURE | - | Detect and report duplicate game entries |
| `get_data_completeness_report` | FUNCTION | - | Generate overall data completeness report |
| `get_data_source_stats` | FUNCTION | - | Get statistics by data source |
| `get_player_season_stats` | FUNCTION | `player_mlb_id bigint, season_year integer` | Retrieve player statistics for season |
| `get_recent_games` | FUNCTION | `days_back integer DEFAULT 7` | Get games from recent days |
| `get_team_season_stats` | FUNCTION | `team_mlb_id bigint, season_year integer` | Retrieve team statistics for season |
| `refresh_combined_data` | FUNCTION | - | Refresh combined data sources |
| `refresh_mlb_analytics` | PROCEDURE | - | Refresh MLB analytics materialized views |
| `validate_mlb_data` | PROCEDURE | - | Run comprehensive MLB data validation |

#### Views (5)

| View | Purpose |
|------|---------|
| `data_quality_summary` | Summary of data quality across sources |
| `missing_data_report` | Report of missing data by table |
| `source_comparison` | Compare data across sources |
| `ingest_status_summary` | Summary of ingestion runs |
| `validation_errors` | Current validation errors |

---

### `baseball_savant` Schema

**Purpose:** Baseball Savant statistics storage

#### Tables (3)

| Table | Size | Description |
|-------|------|-------------|
| `batter_stats` | 1104 kB | Batter statistics from Baseball Savant |
| `pitcher_stats` | 304 kB | Pitcher statistics from Baseball Savant |
| `total_stats` | 5216 kB | Combined batting/pitching totals |

---

### `bridge` Schema

**Purpose:** Cross-reference tables linking IDs across data sources

#### Tables (8)

| Table | Size | Description |
|-------|------|-------------|
| `player_xref` | 47 MB | Maps player IDs: Retrosheet ↔ MLB ↔ Lahman |
| `team_xref` | 216 kB | Maps team IDs across sources |
| `game_xref` | 15 MB | Maps game IDs: Retrosheet ↔ MLB |
| `park_xref` | 320 kB | Stadium/park ID cross-references |
| `coach_xref` | 1840 kB | Coach ID mappings |
| `umpire_xref` | 1480 kB | Umpire ID mappings |
| `external_player_xref` | 14 MB | External player ID mappings |
| `external_team_xref` | 24 kB | External team ID mappings |

#### Procedures (8)

| Name | Type | Purpose |
|------|------|---------|
| `populate_player_xref` | PROCEDURE | Populate player cross-references |
| `populate_team_xref` | PROCEDURE | Populate team cross-references |
| `populate_game_xref` | PROCEDURE | Link Retrosheet and MLB games |
| `populate_park_xref` | PROCEDURE | Link park/stadium IDs |
| `populate_coach_xref` | PROCEDURE | Link coach IDs |
| `populate_umpire_xref` | PROCEDURE | Link umpire IDs |
| `populate_all_bridge_tables` | PROCEDURE | Run all population procedures |
| `populate_season_aware_team_xref` | PROCEDURE | Season-aware team mapping |

#### Views (9)

| View | Purpose |
|------|---------|
| `vw_player_lookup` | Unified player lookup |
| `vw_team_lookup` | Unified team lookup |
| `vw_game_lookup` | Unified game lookup |
| `vw_cross_source_games` | Games with multiple source IDs |
| `vw_unmapped_players` | Players needing ID mapping |
| `vw_unmapped_teams` | Teams needing ID mapping |
| `vw_confident_matches` | High-confidence ID matches |
| `vw_match_summary` | Summary of matching rates |
| `vw_bridge_health` | Overall bridge table health |

---

### `chat` Schema

**Purpose:** Chatbot interaction logging

#### Tables (1)

| Table | Size | Description |
|-------|------|-------------|
| `query_logs` | 72 kB | Log of chatbot queries and responses |

---

### `core` Schema

**Purpose:** Canonical baseball entities and game events

#### Tables (10)

| Table | Size | Description | Key Data |
|-------|------|-------------|----------|
| `games` | 23 MB | Canonical game records | 62,598 historical games |
| `events` | 4491 MB | Play-level events | 4.9M events |
| `plate_appearances` | 3456 MB | PA outcomes | 4.8M plate appearances |
| `players` | 13 MB | Player registry | All MLB players |
| `teams` | 176 kB | Team registry | All MLB teams |
| `parks` | 72 kB | Stadium information | Ballpark data |
| `live_games` | 16 GB | Live game feeds | Real-time data |
| `live_events` | 18 GB | Live play-by-play | Real-time events |
| `live_plate_appearances` | 88 kB | Live PA tracking | Current game state |
| `mlb_pbp` | 136 kB | MLB play-by-play | Structured PBP |

#### Functions (5)

| Name | Type | Purpose |
|------|------|---------|
| `count_rows` | FUNCTION | Count rows in any table |
| `safe_date_mmddyyyy` | FUNCTION | Safe date parsing (MM/DD/YYYY) |
| `safe_date_yyyymmdd` | FUNCTION | Safe date parsing (YYYYMMDD) |
| `safe_int` | FUNCTION | Safe integer parsing |
| `season_range` | FUNCTION | Get available season range |

#### Views (19)

| View | Purpose |
|------|---------|
| `vw_game_summary` | Game-level summary statistics |
| `vw_player_season_stats` | Player statistics by season |
| `vw_team_season_stats` | Team statistics by season |
| `vw_batting_order` | Batting order analysis |
| `vw_pitching_rotation` | Pitching rotation analysis |
| `vw_game_state` | Current game state view |
| `vw_run_expectancy` | Run expectancy by state |
| `vw_win_probability` | Win probability by inning/score |
| `vw_plate_appearance_outcomes` | PA outcome distributions |
| `vw_season_leaders` | Season statistical leaders |
| `vw_career_stats` | Career cumulative statistics |
| `vw_head_to_head` | Batter vs pitcher history |
| `vw_situational_stats` | Stats by situation (men on, etc.) |
| `vw_clutch_performance` | Clutch situation performance |
| `vw_plate_discipline` | Plate discipline metrics |
| `vw_batted_ball_profile` | Batted ball characteristics |
| `vw_defensive_shifts` | Defensive positioning |
| `vw_pace_of_play` | Game duration trends |
| `vw_umpire_consistency` | Umpire call accuracy |

---

### `cron` Schema

**Purpose:** pg_cron job scheduling system

#### Tables (2)

| Table | Size | Description |
|-------|------|-------------|
| `job` | 48 kB | Scheduled job definitions |
| `job_run_details` | 632 kB | Job execution history |

#### Functions (5)

| Name | Type | Purpose |
|------|------|---------|
| `schedule` | FUNCTION | Schedule a new job |
| `unschedule` | FUNCTION | Remove a scheduled job |
| `alter_job` | FUNCTION | Modify existing job |
| `schedule_in_database` | FUNCTION | Schedule job in specific DB |
| `job_cache_invalidate` | FUNCTION | Refresh job cache |

---

### `eda` Schema

**Purpose:** Exploratory data analysis views

#### Views (17)

| View | Purpose |
|------|---------|
| `vw_pitch_distribution` | Pitch type distributions |
| `vw_velocity_by_year` | Velocity trends over time |
| `vw_strike_zone_heatmaps` | Strike zone density maps |
| `vw_spray_charts` | Hit location distributions |
| `vw_outcome_rates` | Outcome rates by situation |
| `vw_platoon_splits` | Left/right matchup stats |
| `vw_park_factors_comparison` | Park effects comparison |
| `vw_season_trends` | Year-over-year trends |
| `vw_player_development` | Career trajectory analysis |
| `vw_team_strength_over_time` | Team performance trends |
| `vw_playoff_performance` | Postseason vs regular season |
| `vw_injury_impact` | Injury effect analysis |
| `vw_rest_days_effect` | Rest day performance impact |
| `vw_travel_fatigue` | Travel distance effects |
| `vw_weather_impact` | Weather condition effects |
| `vw_attendance_correlation` | Attendance vs performance |
| `vw_betting_line_movement` | Odds movement patterns |

---

### `features` Schema

**Purpose:** ML-ready feature engineering tables

#### Tables (1)

| Table | Size | Description |
|-------|------|-------------|
| `play_snapshot` | 24 kB | Play state snapshots for features |

#### Functions (1)

| Name | Type | Purpose |
|------|------|---------|
| `refresh_all_materialized_views` | FUNCTION | Refresh all feature views |

#### Views (16)

| View | Purpose |
|------|---------|
| `vw_plate_appearance_examples` | PA-level training examples |
| `vw_game_outcome_examples` | Game-level training examples |
| `vw_half_inning_examples` | Half-inning training examples |
| `vw_pitch_examples` | Pitch-level training examples |
| `vw_batter_features` | Batter-derived features |
| `vw_pitcher_features` | Pitcher-derived features |
| `vw_matchup_features` | Batter-pitcher matchup features |
| `vw_situational_features` | Game situation features |
| `vw_historical_context` | Historical performance context |
| `vw_rolling_averages` | Rolling performance windows |
| `vw_season_totals` | Season-to-date statistics |
| `vw_career_stats` | Career cumulative features |
| `vw_recent_form` | Recent performance (7/14/30 day) |
| `vw_head_to_head_history` | Historical matchup data |
| `vw_clutch_features` | High-leverage performance |
| `vw_momentum_features` | Team/player momentum |

---

### `features_pitch` Schema

**Purpose:** Pitch-level feature engineering (Statcast)

#### Tables (13)

| Table | Size | Description | Rows |
|-------|------|-------------|------|
| `locations` | 13 GB | Pitch locations with PostGIS | 7.66M |
| `base_features` | 4038 MB | All 118 Statcast fields | 7.66M |
| `engineered_features` | 4090 MB | 220+ ML features | 7.66M |
| `pitcher_arsenals` | 528 kB | Pitcher pitch type breakdowns | - |
| `batter_zone_profiles` | 16 kB | Batter zone swing rates | - |
| `matchup_history` | 40 kB | Batter-pitcher history | - |
| `count_performance` | 16 kB | Count-specific stats | - |
| `batter_pitch_type_performance` | 736 kB | Batter vs pitch type | - |
| `feature_registry` | 88 kB | Feature metadata catalog | - |
| `sequential_features` | 56 kB | LSTM sequence features | - |
| `player_context` | 40 kB | Player rolling context | - |
| `pitch_sequences` | 40 kB | PA-level pitch arrays | - |
| `model_training_set` | 48 kB | Versioned training data | - |

#### Functions (3)

| Name | Type | Purpose |
|------|------|---------|
| `generate_training_query` | FUNCTION | Generate SQL for model training |
| `get_feature_stats` | FUNCTION | Get statistics for feature column |
| `update_timestamp` | FUNCTION | Auto-update modified timestamp |

#### Views (3)

| View | Purpose |
|------|---------|
| `vw_xgboost_base` | XGBoost-compatible feature view |
| `vw_clean_pitch_data` | Data quality filtered pitches |
| `vw_strict_pitch_data` | Strict quality filter |

---

### `inference` Schema

**Purpose:** Model inference and simulation state management

#### Tables (1)

| Table | Size | Description |
|-------|------|-------------|
| `simulation_states` | 24 kB | Monte Carlo simulation states |

#### Functions (4)

| Name | Type | Purpose |
|------|------|---------|
| `init_simulation` | FUNCTION | Initialize new simulation |
| `get_simulation_state` | FUNCTION | Retrieve current simulation state |
| `get_plate_appearance_features` | FUNCTION | Get features for PA prediction |
| `predict_plate_appearance_batch` | FUNCTION | Batch prediction function |

---

### `lahman` Schema

**Purpose:** Lahman baseball database tables

#### Tables (19)

| Table | Size | Description |
|-------|------|-------------|
| `people` | 3656 kB | Player biographical information |
| `batting` | 12 MB | Batting statistics by season |
| `pitching` | 6392 kB | Pitching statistics by season |
| `fielding` | 13 MB | Fielding statistics |
| `fieldingof` | 752 kB | Outfield fielding stats |
| `fieldingofsplit` | 2928 kB | Outfield split positions |
| `appearances` | 11 MB | Player game appearances |
| `teams` | 768 kB | Team season records |
| `managers` | 288 kB | Manager records |
| `allstarfull` | 424 kB | All-Star game rosters |
| `battingpost` | 1624 kB | Postseason batting |
| `pitchingpost` | 864 kB | Postseason pitching |
| `fieldingpost` | 1312 kB | Postseason fielding |
| `homegames` | 304 kB | Home game records |
| `managershalf` | 16 kB | Mid-season manager changes |
| `seriespost` | 56 kB | Postseason series results |
| `teamsfranchises` | 16 kB | Franchise information |
| `teamshalf` | 16 kB | Team half-season records |
| `parks` | 56 kB | Ballpark information |

---

### `market_edges` Schema

**Purpose:** Prediction market data and edge detection

#### Tables (2)

| Table | Size | Description |
|-------|------|-------------|
| `market_prices` | 24 kB | Market odds and prices |
| `detected_edges` | 16 kB | Detected value opportunities |

---

### `metadata` Schema

**Purpose:** Data dictionary and metadata management

#### Tables (2)

| Table | Size | Description |
|-------|------|-------------|
| `table_dictionary` | 144 kB | Table metadata and descriptions |
| `column_dictionary` | 1568 kB | Column metadata and definitions |

#### Functions (7)

| Name | Type | Purpose |
|------|------|---------|
| `refresh_data_dictionary` | FUNCTION | Refresh dictionary from system catalogs |
| `is_mlb_season` | FUNCTION | Check if MLB season is active |
| `is_game_hours` | FUNCTION | Check if games are being played |
| `has_scheduled_games_today` | FUNCTION | Check for today's games |
| `should_poll_games` | FUNCTION | Determine if polling needed |
| `poll_active_games_conditional` | FUNCTION | Conditional game polling |
| `poll_all_endpoints_conditional` | FUNCTION | Conditional endpoint polling |

---

### `mlb` Schema

**Purpose:** MLB Stats API data

#### Tables (6)

| Table | Size | Description |
|-------|------|-------------|
| `games` | 12 MB | MLB game records |
| `pitches` | 7172 MB | Pitch-level data |
| `play_events` | 1341 MB | Play events |
| `players` | 80 kB | Player records |
| `teams` | 72 kB | Team records |
| `venues` | 16 kB | Stadium records |

#### Functions (1)

| Name | Type | Purpose |
|------|------|---------|
| `resolve_team_id` | FUNCTION | Resolve team ID from name and date |

---

### `mlb_enhanced` Schema

**Purpose:** Enhanced MLB statistics

#### Tables (4)

| Table | Size | Description |
|-------|------|-------------|
| `statcast_pitches` | 633 MB | Enhanced Statcast data |
| `betting_features` | 55 MB | Features for betting models |
| `batter_pitcher_history` | 8304 kB | Historical matchup data |
| `player_advanced_stats` | 16 kB | Advanced player metrics |

---

### `mlb_features` Schema

**Purpose:** MLB-derived features for modeling

#### Tables (6)

| Table | Size | Description |
|-------|------|-------------|
| `game_state_features` | 125 MB | Game situation features |
| `win_probability_training` | 200 MB | WP model training data |
| `player_season_stats` | 7112 kB | Player season statistics |
| `team_season_stats` | 16 kB | Team season statistics |
| `park_factors` | 16 kB | Park effect factors |
| `batter_pitcher_matchups` | 16 kB | Matchup statistics |

#### Functions (3)

| Name | Type | Purpose |
|------|------|---------|
| `populate_game_state_from_mlb` | FUNCTION | Generate features from MLB data |
| `populate_game_state_from_retrosheet` | FUNCTION | Generate features from Retrosheet |
| `populate_player_season_stats` | FUNCTION | Calculate player season stats |

---

### `mlb_models` Schema

**Purpose:** Model training datasets

#### Tables (2)

| Table | Size | Description |
|-------|------|-------------|
| `win_probability_training` | 40 MB | WP model dataset |
| `win_probability_training_enhanced` | 61 MB | Enhanced WP dataset |

---

### `models` Schema

**Purpose:** Model registry and management

#### Tables (1)

| Table | Size | Description |
|-------|------|-------------|
| `model_registry` | 488 kB | Registered models with metadata |

---

### `predictions` Schema

**Purpose:** Store model predictions

#### Tables (10)

| Table | Size | Description |
|-------|------|-------------|
| `pa_predictions` | 64 kB | Plate appearance predictions |
| `live_pa_predictions` | 144 kB | Live game predictions |
| `win_probabilities` | 8192 bytes | Win probability estimates |
| `target_probabilities` | 32 kB | Target variable probabilities |
| `prediction_runs` | 32 kB | Prediction batch runs |
| `api_prediction_requests` | 64 kB | API prediction log |
| `simulation_runs` | 88 kB | Monte Carlo simulations |
| `calibration_reports` | 152 kB | Model calibration data |
| `bootstrap_reports` | 88 kB | Bootstrap confidence intervals |
| `prediction_targets` | 72 kB | Prediction target definitions |

#### Functions (1)

| Name | Type | Purpose |
|------|------|---------|
| `update_updated_at_column` | FUNCTION | Auto-update modified timestamp |

#### Views (3)

| View | Purpose |
|------|---------|
| `vw_prediction_accuracy` | Prediction accuracy by model |
| `vw_calibration_summary` | Calibration curve data |
| `vw_recent_predictions` | Recent prediction results |

---

### `raw_*` Schemas

**Purpose:** Source-preserved raw data from external APIs

#### `raw_mlb` (MLB Stats API)
| Table | Size | Description |
|-------|------|-------------|
| `statcast` | 3920 MB | Statcast pitch-level data (7.8M rows) |
| `live_feed_snapshots` | 16 GB | Live game feed JSON |
| `boxscore_snapshots` | 40 kB | Game boxscore JSON |
| `schedule_snapshots` | 36 MB | Game schedule JSON |
| `reference_snapshots` | 14 MB | Reference data JSON |
| `play_by_play_snapshots` | 40 kB | PBP JSON |
| `pitch_metrics_snapshots` | 40 kB | Pitch metrics JSON |
| `gameday_xml` | 16 kB | Gameday XML data |
| `win_probability_snapshots` | 40 kB | WP JSON |
| `stg_statcast` | 510 MB | Staging table |

#### Functions (3)
- `ingest_all_endpoints_for_game()` - Ingest all data for game
- `ingest_endpoint()` - Ingest specific endpoint
- `poll_all_active_endpoints()` - Poll all active games

#### `raw_retrosheet` (Chadwick/Retrosheet)
| Table | Size | Description |
|-------|------|-------------|
| `chadwick_events` | 4263 MB | Parsed event data |
| `chadwick_games` | 124 MB | Game records |
| `chadwick_event_raw` | 3258 MB | Raw event strings |
| `chadwick_daily` | 946 MB | Daily player stats |
| `chadwick_substitutions` | 206 MB | Substitution records |
| `chadwick_comments` | 27 MB | Event comments |
| `biofile` | 5784 kB | Player bios |
| `biofile_legacy` | 5752 kB | Legacy bios |
| `season_rosters` | 36 MB | Season rosters |
| `season_schedules` | 57 MB | Season schedules |
| `season_teams` | 920 kB | Team season records |
| `season_umpires` | 2400 kB | Umpire assignments |
| `coaches` | 1768 kB | Coach records |
| `ejections` | 4768 kB | Ejection records |
| `relatives` | 184 kB | Player relationships |
| `special_gamelog_lines` | 2816 kB | Special game events |
| `ballparks_reference` | 104 kB | Ballpark reference |
| `teams_reference` | 48 kB | Team reference |
| `ingest_runs` | 128 kB | Ingestion tracking |

#### Functions (7)
- `start_ingest_run()` - Begin ingestion tracking
- `complete_ingest_run()` - Mark ingest complete
- `fail_ingest_run()` - Mark ingest failure
- `update_ingest_run_progress()` - Update progress
- `compute_checksum()` - Compute data checksum
- `get_git_commit()` - Get git commit hash
- `update_updated_at()` - Update timestamp

#### `raw_espn` (ESPN API)
| Table | Size | Description |
|-------|------|-------------|
| `game_snapshots` | 9894 MB | Game data JSON |
| `schedule_snapshots` | 341 MB | Schedule JSON |
| `plays_snapshots` | 103 MB | Play-by-play JSON |
| `team_stats_snapshots` | 40 kB | Team stats JSON |
| `player_stats_snapshots` | 40 kB | Player stats JSON |

#### `raw_espn` (ESPN API)
| Table | Size | Description |
|-------|------|-------------|
| `game_snapshots` | 9894 MB | Game data JSON |
| `schedule_snapshots` | 341 MB | Schedule JSON |
| `plays_snapshots` | 103 MB | Play-by-play JSON |
| `team_stats_snapshots` | 40 kB | Team stats JSON |
| `player_stats_snapshots` | 40 kB | Player stats JSON |

#### `raw_lahman` (Lahman Database)
| Table | Size | Description |
|-------|------|-------------|
| `stg_batting` | 8192 bytes | Staging |
| `stg_pitching` | 8192 bytes | Staging |
| `stg_people` | 16 kB | Staging |
| `stg_teams` | 8192 bytes | Staging |
| `stg_salaries` | 8192 bytes | Staging |
| `batting` | 16 kB | Raw batting |
| `pitching` | 16 kB | Raw pitching |
| `people` | 32 kB | Raw people |
| `teams` | 16 kB | Raw teams |
| `salaries` | 16 kB | Raw salaries |

#### `raw_bref` (Baseball Reference)
| Table | Size | Description |
|-------|------|-------------|
| `batting_stats` | 16 MB | Batting stats |
| `pitching_stats` | 3200 kB | Pitching stats |

#### `raw_baseball_reference`
| Table | Size | Description |
|-------|------|-------------|
| `game_logs` | 16 kB | Game logs |
| `stg_game_logs` | 8192 bytes | Staging |

#### `raw_statcast` (Baseball Savant)
| Table | Size | Description |
|-------|------|-------------|
| `stg_events` | 4816 kB | Staging |
| `events` | 1072 kB | Events |

#### `raw_sportradar` (SportRadar)
| Table | Size | Description |
|-------|------|-------------|
| `game_snapshots` | 40 kB | Game data |
| `push_events` | 56 kB | Push events |

#### Functions (2)
- `fetch_live_schedule()` - Get live schedule
- `poll_active_games()` - Poll active games

#### `raw_park_factors`
| Table | Size | Description |
|-------|------|-------------|
| `factors` | 32 kB | Park factors |

#### `raw_mlb_rosters`
| Table | Size | Description |
|-------|------|-------------|
| `roster_snapshots` | 208 kB | Roster data |

#### `raw_markets`
| Table | Size | Description |
|-------|------|-------------|
| `market_snapshots` | 24 kB | Market data |

#### `raw_external`
| Table | Size | Description |
|-------|------|-------------|
| `baseball_data_com` | 16 kB | External data |

---

### `validation` Schema

**Purpose:** Data quality validation views

#### Functions (1)

| Name | Type | Purpose |
|------|------|---------|
| `refresh_data_quality_summary` | FUNCTION | Refresh validation summaries |

#### Views (10)

| View | Purpose |
|------|---------|
| `vw_null_counts` | NULL value counts by column |
| `vw_duplicate_check` | Duplicate row detection |
| `vw_foreign_key_validation` | FK constraint validation |
| `vw_range_validation` | Value range checks |
| `vw_data_type_validation` | Type consistency |
| `vw_completeness_report` | Completeness by table |
| `vw_freshness_report` | Data freshness checks |
| `vw_schema_drift` | Schema change detection |
| `vw_data_quality_score` | Overall quality score |
| `vw_validation_summary` | All validations summary |

---

### `warehouse` Schema

**Purpose:** Feature population orchestration and tracking

#### Tables (3)

| Table | Size | Description |
|-------|------|-------------|
| `rebuild_runs` | 24 kB | Feature population runs |
| `rebuild_log` | 32 kB | Detailed phase logging |
| `batch_operations` | 40 kB | Batch progress tracking |

#### Procedures (12)

| Name | Type | Arguments | Description |
|------|------|-----------|-------------|
| `populate_features_phase` | PROCEDURE | `p_phase_number integer, p_dry_run boolean DEFAULT false` | Run specific population phase |
| `create_batch_checkpoint` | PROCEDURE | `p_batch_name text, p_column_name text, p_total_rows bigint, p_processed_rows bigint` | Create resume checkpoint |
| `verify_features_populated` | FUNCTION | - | Verify all features complete |
| `get_feature_stats` | FUNCTION | - | Get feature population stats |
| `estimate_batch_completion` | FUNCTION | `p_column_name text, p_batch_size integer DEFAULT 100000, p_seconds_per_batch numeric DEFAULT 30` | Estimate completion time |
| `get_last_successful_phase` | FUNCTION | `p_run_mode character varying DEFAULT 'resume'::character varying` | Get last completed phase |
| `get_resumable_batch` | FUNCTION | `p_batch_name text, p_target_schema text, p_target_table text` | Get batch resume point |
| `get_unprocessed_count` | FUNCTION | `p_column_name text` | Count unprocessed rows |
| `health_check` | FUNCTION | - | Warehouse health check |
| `log_phase_start` | FUNCTION | `p_run_id bigint, p_phase character varying, p_phase_order integer, p_metadata jsonb DEFAULT '{}'::jsonb` | Log phase start |
| `log_phase_end` | FUNCTION | `p_log_id bigint, p_status character varying, p_rows_affected bigint DEFAULT NULL::bigint, p_error_message text DEFAULT NULL::text` | Log phase end |
| `update_batch_progress` | FUNCTION | `p_batch_id bigint, p_last_processed_id bigint, p_processed_rows bigint` | Update batch progress |

#### Views (2)

| View | Purpose |
|------|---------|
| `vw_rebuild_status` | Current rebuild status |
| `vw_batch_progress` | Batch operation progress |

---

## 📈 Key Statistics

### Largest Tables by Size

| Table | Schema | Size | Description |
|-------|--------|------|-------------|
| `live_events` | core | 18 GB | Real-time play-by-play |
| `live_games` | core | 16 GB | Real-time game data |
| `locations` | features_pitch | 13 GB | Pitch locations (PostGIS) |
| `game_snapshots` | raw_espn | 9894 MB | ESPN game JSON |
| `live_feed_snapshots` | raw_mlb | 16 GB | MLB live feeds |
| `engineered_features` | features_pitch | 4090 MB | 220+ ML features |
| `base_features` | features_pitch | 4038 MB | 118 Statcast fields |
| `statcast` | raw_mlb | 3920 MB | Source Statcast |
| `events` | core | 4491 MB | Retrosheet events |
| `plate_appearances` | core | 3456 MB | PA outcomes |

### Row Counts (Major Tables)

| Table | Schema | Approx Rows |
|-------|--------|-------------|
| `locations` | features_pitch | 7,661,992 |
| `base_features` | features_pitch | 7,661,992 |
| `engineered_features` | features_pitch | 7,661,992 |
| `statcast` | raw_mlb | 7,797,034 |
| `events` | core | 4,900,000 |
| `plate_appearances` | core | 4,800,000 |
| `games` | core | 62,598 |

---

## 🔗 Key Relationships

### Data Flow Architecture

```
raw_* schemas (source data)
    ↓
bridge schema (ID mapping)
    ↓
core schema (canonical entities)
    ↓
features_* schemas (ML features)
    ↓
models schema (model registry)
    ↓
predictions schema (inference results)
```

### Critical Join Paths

1. **Game Linking:**
   - `core.games` ↔ `bridge.game_xref` ↔ `raw_mlb.statcast`

2. **Player Linking:**
   - `core.players` ↔ `bridge.player_xref` ↔ `raw_mlb.*`

3. **Pitch-to-Event:**
   - `features_pitch.locations` ↔ `core.events` (via bridge)

4. **Feature-to-Training:**
   - `features_pitch.engineered_features` → `mlb_models.*`

---

## 📝 Maintenance Notes

### Regular Maintenance Tasks
1. **Update bridge tables** after new data ingestion
2. **Refresh materialized views** in `features` schema
3. **Archive old raw data** (>2 years) to cold storage
4. **Update data dictionary** when schema changes
5. **Validate data quality** using `validation` schema

### Performance Considerations
1. **PostGIS indexes** on `features_pitch.locations`
2. **Partitioning** on large tables (events, pitches)
3. **Materialized views** for complex aggregations
4. **Batch operations** for large updates

---

**End of Database Catalog**

*Last Updated: April 24, 2026*
