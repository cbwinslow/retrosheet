# Database Procedures and Functions Reference

**Purpose:** Complete reference for all database operations, procedures, and functions  
**Date:** April 24, 2026  
**Database:** retrosheet (PostgreSQL)

---

## 📋 Table of Contents

1. [Warehouse Orchestration Procedures](#warehouse-orchestration)
2. [Bridge Table Population](#bridge-population)
3. [Feature Population](#feature-population)
4. [Data Ingestion Functions](#data-ingestion)
5. [Analysis and Validation](#analysis-validation)
6. [Inference and Prediction](#inference-prediction)
7. [Utility Functions](#utility-functions)
8. [Metadata and Documentation](#metadata)

---

## 🏭 Warehouse Orchestration

### Core Orchestration Procedures

| Schema | Name | Type | Arguments | Purpose |
|--------|------|------|-----------|---------|
| `warehouse` | `populate_features_phase` | PROCEDURE | `p_phase_number integer, p_dry_run boolean DEFAULT false` | Run specific feature population phase (1-13) with optional dry-run |
| `warehouse` | `create_batch_checkpoint` | PROCEDURE | `p_batch_name text, p_column_name text, p_total_rows bigint, p_processed_rows bigint` | Create resume checkpoint for batch operations |
| `warehouse` | `verify_features_populated` | FUNCTION | - | Verify all engineered features are populated, return completion % |
| `warehouse` | `get_feature_stats` | FUNCTION | - | Get feature population statistics by column |
| `warehouse` | `estimate_batch_completion` | FUNCTION | `p_column_name text, p_batch_size integer DEFAULT 100000, p_seconds_per_batch numeric DEFAULT 30` | Estimate remaining time for batch operation |
| `warehouse` | `get_last_successful_phase` | FUNCTION | `p_run_mode character varying DEFAULT 'resume'` | Get last completed phase for resume |
| `warehouse` | `get_resumable_batch` | FUNCTION | `p_batch_name text, p_target_schema text, p_target_table text` | Get batch resume point |
| `warehouse` | `get_unprocessed_count` | FUNCTION | `p_column_name text` | Count unprocessed rows for feature |
| `warehouse` | `health_check` | FUNCTION | - | Validate warehouse schema health |
| `warehouse` | `log_phase_start` | FUNCTION | `p_run_id bigint, p_phase character varying, p_phase_order integer, p_metadata jsonb DEFAULT '{}'` | Log phase start to rebuild_log |
| `warehouse` | `log_phase_end` | FUNCTION | `p_log_id bigint, p_status character varying, p_rows_affected bigint DEFAULT NULL, p_error_message text DEFAULT NULL` | Log phase end with status |
| `warehouse` | `update_batch_progress` | FUNCTION | `p_batch_id bigint, p_last_processed_id bigint, p_processed_rows bigint` | Update batch progress for resume |

**Usage Examples:**

```sql
-- Run Phase 2 (additional features)
CALL warehouse.populate_features_phase(2, false);

-- Verify all features populated
SELECT * FROM warehouse.verify_features_populated();

-- Check feature stats
SELECT * FROM warehouse.get_feature_stats();

-- Estimate completion for velocity_change column
SELECT * FROM warehouse.estimate_batch_completion('velocity_change', 100000, 30);
```

---

## 🌉 Bridge Table Population

### Master Bridge Population

| Schema | Name | Type | Arguments | Purpose |
|--------|------|------|-----------|---------|
| `bridge` | `populate_all_bridge_tables` | PROCEDURE | `IN include_player_xref boolean DEFAULT false` | Run all bridge population procedures in dependency order |

### Individual Bridge Procedures

| Schema | Name | Type | Arguments | Populates | Output |
|--------|------|------|-----------|-----------|--------|
| `bridge` | `populate_player_xref` | PROCEDURE | `OUT inserted_count integer` | `bridge.player_xref` | Count of player mappings created |
| `bridge` | `populate_team_xref` | PROCEDURE | - | `bridge.team_xref` | Team ID mappings |
| `bridge` | `populate_game_xref` | PROCEDURE | `OUT matched_count integer` | `bridge.game_xref` | Count of games linked |
| `bridge` | `populate_park_xref` | PROCEDURE | `OUT updated_count integer` | `bridge.park_xref` | Count of parks linked |
| `bridge` | `populate_coach_xref` | PROCEDURE | `OUT coach_count integer` | `bridge.coach_xref` | Count of coaches linked |
| `bridge` | `populate_umpire_xref` | PROCEDURE | `OUT umpire_count integer` | `bridge.umpire_xref` | Count of umpires linked |
| `bridge` | `populate_season_aware_team_xref` | PROCEDURE | `OUT updated_count integer` | `bridge.team_xref` | Season-aware team mappings |

**Usage Examples:**

```sql
-- Run all bridge population (excluding player xref - slow)
CALL bridge.populate_all_bridge_tables(false);

-- Populate player xref separately
DO $$
DECLARE
    player_count integer;
BEGIN
    CALL bridge.populate_player_xref(player_count);
    RAISE NOTICE 'Populated % player mappings', player_count;
END $$;

-- Populate game cross-references
DO $$
DECLARE
    game_count integer;
BEGIN
    CALL bridge.populate_game_xref(game_count);
    RAISE NOTICE 'Linked % games', game_count;
END $$;
```

**Dependency Order:**
1. `populate_team_xref` (teams must be mapped first)
2. `populate_park_xref` (parks don't depend on teams)
3. `populate_player_xref` (players reference teams)
4. `populate_game_xref` (games reference teams and players)
5. `populate_coach_xref` (coaches reference teams)
6. `populate_umpire_xref` (umpires reference games)

---

## 🔧 Feature Population

### Pitch-Level Feature Functions

| Schema | Name | Type | Arguments | Purpose |
|--------|------|------|-----------|---------|
| `features_pitch` | `generate_training_query` | FUNCTION | `p_model_name varchar, p_feature_categories varchar[] DEFAULT ['physics','location','context'], p_include_engineered boolean DEFAULT true, p_include_player_context boolean DEFAULT true` | Generate SQL query for model training |
| `features_pitch` | `get_feature_stats` | FUNCTION | `p_table_name varchar, p_column_name varchar` | Get statistics for specific feature column |
| `features_pitch` | `update_timestamp` | FUNCTION | - | Trigger function for updated_at timestamp |

### MLB Feature Population

| Schema | Name | Type | Arguments | Purpose |
|--------|------|------|-----------|---------|
| `mlb_features` | `populate_game_state_from_mlb` | FUNCTION | - | Generate features from MLB API data |
| `mlb_features` | `populate_game_state_from_retrosheet` | FUNCTION | `start_season integer DEFAULT 2000, end_season integer DEFAULT 2024` | Generate features from Retrosheet data |
| `mlb_features` | `populate_player_season_stats` | FUNCTION | - | Calculate player season statistics |

**Usage Examples:**

```sql
-- Generate training query for XGBoost model
SELECT features_pitch.generate_training_query(
    'swing_decision_xgboost',
    ARRAY['physics', 'location', 'context', 'matchup'],
    true,
    true
);

-- Get stats for velocity feature
SELECT * FROM features_pitch.get_feature_stats(
    'features_pitch.engineered_features',
    'velocity_change_from_prev'
);

-- Populate game state features for 2015-2025
SELECT mlb_features.populate_game_state_from_retrosheet(2015, 2025);
```

---

## 📥 Data Ingestion

### MLB API Ingestion

| Schema | Name | Type | Arguments | Purpose |
|--------|------|------|-----------|---------|
| `raw_mlb` | `ingest_all_endpoints_for_game` | FUNCTION | `game_pk bigint` | Ingest all data for specific game |
| `raw_mlb` | `ingest_endpoint` | FUNCTION | `game_pk bigint, endpoint_suffix text, target_table text` | Ingest specific endpoint |
| `raw_mlb` | `poll_all_active_endpoints` | FUNCTION | - | Poll all active games |
| `mlb` | `resolve_team_id` | FUNCTION | `mlb_team_name text, game_date date` | Resolve team ID from name and date |

### Retrosheet Ingestion Tracking

| Schema | Name | Type | Arguments | Purpose |
|--------|------|------|-----------|---------|
| `raw_retrosheet` | `start_ingest_run` | FUNCTION | `p_source_name text, p_source_version text DEFAULT NULL, p_script_name text DEFAULT NULL, p_script_version text DEFAULT NULL, p_git_commit text DEFAULT NULL, p_command_args jsonb DEFAULT '{}'` | Start new ingest run with tracking |
| `raw_retrosheet` | `complete_ingest_run` | FUNCTION | `p_run_id bigint, p_final_details jsonb DEFAULT NULL` | Mark ingest as complete |
| `raw_retrosheet` | `fail_ingest_run` | FUNCTION | `p_run_id bigint, p_error_message text, p_error_details jsonb DEFAULT NULL` | Mark ingest as failed |
| `raw_retrosheet` | `update_ingest_run_progress` | FUNCTION | `p_run_id bigint, p_records_downloaded integer DEFAULT NULL, p_records_ingested integer DEFAULT NULL, p_records_failed integer DEFAULT NULL` | Update ingest progress |
| `raw_retrosheet` | `compute_checksum` | FUNCTION | `p_data jsonb` | Compute data checksum |
| `raw_retrosheet` | `get_git_commit` | FUNCTION | - | Get current git commit hash |

### SportRadar Ingestion

| Schema | Name | Type | Arguments | Purpose |
|--------|------|------|-----------|---------|
| `raw_sportradar` | `fetch_live_schedule` | FUNCTION | - | Fetch live schedule from SportRadar |
| `raw_sportradar` | `poll_active_games` | FUNCTION | - | Poll active games from SportRadar |

**Usage Examples:**

```sql
-- Ingest all data for game 745627
SELECT raw_mlb.ingest_all_endpoints_for_game(745627);

-- Start ingest run with tracking
DO $$
DECLARE
    run_id bigint;
BEGIN
    run_id := raw_retrosheet.start_ingest_run(
        'statcast',
        '2025-04-24',
        'download_baseball_savant.py',
        '1.0',
        raw_retrosheet.get_git_commit(),
        '{"season": 2025}'::jsonb
    );
    RAISE NOTICE 'Started run %', run_id;
END $$;

-- Resolve team ID for historical name
SELECT mlb.resolve_team_id('Florida Marlins', '2011-04-01');
```

---

## 📊 Analysis and Validation

### Data Quality Functions

| Schema | Name | Type | Arguments | Purpose |
|--------|------|------|-----------|---------|
| `analysis` | `calculate_mlb_data_quality` | FUNCTION | `game_id_param text` | Calculate quality score for game |
| `analysis` | `detect_duplicate_games` | PROCEDURE | - | Detect duplicate game entries |
| `analysis` | `get_data_completeness_report` | FUNCTION | - | Generate completeness report |
| `analysis` | `get_data_source_stats` | FUNCTION | - | Get stats by data source |
| `analysis` | `get_player_season_stats` | FUNCTION | `player_mlb_id bigint, season_year integer` | Get player season stats |
| `analysis` | `get_team_season_stats` | FUNCTION | `team_mlb_id bigint, season_year integer` | Get team season stats |
| `analysis` | `get_recent_games` | FUNCTION | `days_back integer DEFAULT 7` | Get recent games |
| `analysis` | `refresh_combined_data` | FUNCTION | - | Refresh combined data |
| `analysis` | `refresh_mlb_analytics` | PROCEDURE | - | Refresh analytics views |
| `analysis` | `validate_mlb_data` | PROCEDURE | - | Run comprehensive validation |

### Validation Functions

| Schema | Name | Type | Arguments | Purpose |
|--------|------|------|-----------|---------|
| `validation` | `refresh_data_quality_summary` | FUNCTION | - | Refresh validation views |

**Usage Examples:**

```sql
-- Check data quality for specific game
SELECT * FROM analysis.calculate_mlb_data_quality('2025_04_24_anamlb_balmlb_1');

-- Get data completeness report
SELECT * FROM analysis.get_data_completeness_report();

-- Get player stats for 2024 season
SELECT * FROM analysis.get_player_season_stats(660271, 2024);

-- Get recent games (last 14 days)
SELECT * FROM analysis.get_recent_games(14);

-- Run full validation
CALL analysis.validate_mlb_data();
```

---

## 🤖 Inference and Prediction

### Simulation Functions

| Schema | Name | Type | Arguments | Purpose |
|--------|------|------|-----------|---------|
| `inference` | `init_simulation` | FUNCTION | `p_simulation_id text, p_game_id text, p_season integer, p_inning integer DEFAULT 1, p_is_bottom_inning boolean DEFAULT false, p_batter_id text DEFAULT NULL, p_pitcher_id text DEFAULT NULL, p_batter_hand text DEFAULT 'R', p_pitcher_hand text DEFAULT 'R', p_batting_team_id text DEFAULT NULL, p_fielding_team_id text DEFAULT NULL` | Initialize Monte Carlo simulation |
| `inference` | `get_simulation_state` | FUNCTION | `p_simulation_id text` | Get current simulation state |
| `inference` | `get_plate_appearance_features` | FUNCTION | `p_season integer, p_inning integer, p_is_bottom_inning boolean, p_outs_before integer, p_start_bases integer, p_balls integer, p_strikes integer, p_home_score_diff integer, p_batter_hand text DEFAULT 'R', p_pitcher_hand text DEFAULT 'R', p_batter_id text DEFAULT NULL, p_pitcher_id text DEFAULT NULL, p_batting_team_id text DEFAULT NULL, p_fielding_team_id text DEFAULT NULL` | Get features for PA prediction |
| `inference` | `predict_plate_appearance_batch` | FUNCTION | (same as above) | Batch prediction for multiple PAs |

**Usage Examples:**

```sql
-- Initialize simulation
SELECT inference.init_simulation(
    'sim_20250424_001',
    '745627',
    2025,
    3,
    true,
    '660271',
    '621111',
    'R',
    'R',
    '119',
    '110'
);

-- Get features for PA prediction
SELECT * FROM inference.get_plate_appearance_features(
    2025, 3, true, 1, 0, 1, 2, 0,
    'R', 'R', '660271', '621111', '119', '110'
);

-- Batch predict
SELECT * FROM inference.predict_plate_appearance_batch(
    2025, 3, true, 1, 0, 1, 2, 0,
    'R', 'R', '660271', '621111', '119', '110'
);
```

---

## 🛠️ Utility Functions

### Core Utilities

| Schema | Name | Type | Arguments | Purpose |
|--------|------|------|-----------|---------|
| `core` | `count_rows` | FUNCTION | `p_table regclass` | Count rows in any table |
| `core` | `safe_date_mmddyyyy` | FUNCTION | `value text` | Safe date parse (MM/DD/YYYY) |
| `core` | `safe_date_yyyymmdd` | FUNCTION | `value text` | Safe date parse (YYYYMMDD) |
| `core` | `safe_int` | FUNCTION | `value text` | Safe integer parse |
| `core` | `season_range` | FUNCTION | - | Get available season range |

### Trigger Functions

| Schema | Name | Type | Purpose |
|--------|------|------|---------|
| `bridge` | `update_updated_at_column` | FUNCTION | Auto-update bridge table timestamps |
| `features_pitch` | `update_timestamp` | FUNCTION | Auto-update feature table timestamps |
| `predictions` | `update_updated_at_column` | FUNCTION | Auto-update prediction timestamps |
| `raw_retrosheet` | `update_updated_at` | FUNCTION | Auto-update ingest table timestamps |

**Usage Examples:**

```sql
-- Count rows in any table
SELECT core.count_rows('core.games');

-- Safe parse dates
SELECT core.safe_date_mmddyyyy('04/24/2025');
SELECT core.safe_date_yyyymmdd('20250424');

-- Safe parse integer
SELECT core.safe_int('123');
SELECT core.safe_int('abc');  -- Returns NULL

-- Get season range
SELECT * FROM core.season_range();
```

---

## 📚 Metadata and Documentation

### Metadata Functions

| Schema | Name | Type | Arguments | Purpose |
|--------|------|------|-----------|---------|
| `metadata` | `refresh_data_dictionary` | FUNCTION | - | Refresh metadata from system catalogs |
| `metadata` | `is_mlb_season` | FUNCTION | - | Check if MLB season active |
| `metadata` | `is_game_hours` | FUNCTION | - | Check if during game hours |
| `metadata` | `has_scheduled_games_today` | FUNCTION | - | Check for today's games |
| `metadata` | `should_poll_games` | FUNCTION | - | Determine if polling needed |
| `metadata` | `poll_active_games_conditional` | FUNCTION | - | Conditional game polling |
| `metadata` | `poll_all_endpoints_conditional` | FUNCTION | - | Conditional endpoint polling |

### Features Refresh

| Schema | Name | Type | Purpose |
|--------|------|------|---------|
| `features` | `refresh_all_materialized_views` | FUNCTION | Refresh all feature views |

**Usage Examples:**

```sql
-- Refresh data dictionary
SELECT metadata.refresh_data_dictionary();

-- Check if MLB season
SELECT metadata.is_mlb_season();

-- Check if game hours
SELECT metadata.is_game_hours();

-- Should we poll?
SELECT metadata.should_poll_games();

-- Refresh all feature views
SELECT features.refresh_all_materialized_views();
```

---

## 📝 Procedure Summary by Purpose

### Orchestration (12 procedures/functions)
- **Schema:** `warehouse`
- **Purpose:** Feature population orchestration with resume capability
- **Key Procedures:** `populate_features_phase`, `create_batch_checkpoint`, `verify_features_populated`

### Bridge Population (8 procedures)
- **Schema:** `bridge`
- **Purpose:** Cross-reference ID mapping between data sources
- **Key Procedures:** `populate_all_bridge_tables`, `populate_player_xref`, `populate_game_xref`

### Data Ingestion (7 procedures/functions)
- **Schemas:** `raw_mlb`, `raw_retrosheet`, `raw_sportradar`
- **Purpose:** Data ingestion with tracking and reproducibility
- **Key Procedures:** `ingest_all_endpoints_for_game`, `start_ingest_run`, `poll_active_games`

### Analysis (10 procedures/functions)
- **Schema:** `analysis`
- **Purpose:** Data quality, completeness, and validation
- **Key Procedures:** `validate_mlb_data`, `get_data_completeness_report`, `calculate_mlb_data_quality`

### Feature Generation (6 procedures/functions)
- **Schemas:** `features_pitch`, `mlb_features`
- **Purpose:** ML feature generation and training data preparation
- **Key Procedures:** `generate_training_query`, `populate_game_state_from_mlb`

### Inference (4 functions)
- **Schema:** `inference`
- **Purpose:** Model inference and simulation
- **Key Functions:** `init_simulation`, `predict_plate_appearance_batch`

### Utilities (9 functions)
- **Schemas:** `core`, `metadata`, `features`
- **Purpose:** Helper functions and triggers
- **Key Functions:** `count_rows`, `safe_date_mmddyyyy`, `refresh_all_materialized_views`

---

## 🔗 Cross-Reference: Procedures by Schema

```
warehouse (12):          Feature population orchestration
bridge (8):              ID cross-reference population
analysis (10):           Data quality and validation
raw_mlb (3):             MLB API ingestion
raw_retrosheet (7):      Retrosheet ingestion tracking
raw_sportradar (2):      SportRadar ingestion
features_pitch (3):      Pitch feature generation
mlb_features (3):        MLB feature generation
inference (4):           Model inference
metadata (7):            Metadata and polling
core (5):                Core utilities
features (1):            Feature refresh
validation (1):          Data validation
predictions (1):           Prediction triggers
```

---

## 📖 Complete Index

### All Procedures by Name (Alphabetical)

| Name | Schema | Type | Lines of Documentation |
|------|--------|------|------------------------|
| `calculate_mlb_data_quality` | analysis | FUNCTION | ~150 |
| `complete_ingest_run` | raw_retrosheet | FUNCTION | ~100 |
| `compute_checksum` | raw_retrosheet | FUNCTION | ~50 |
| `count_rows` | core | FUNCTION | ~20 |
| `create_batch_checkpoint` | warehouse | PROCEDURE | ~100 |
| `detect_duplicate_games` | analysis | PROCEDURE | ~80 |
| `estimate_batch_completion` | warehouse | FUNCTION | ~150 |
| `fail_ingest_run` | raw_retrosheet | FUNCTION | ~100 |
| `fetch_live_schedule` | raw_sportradar | FUNCTION | ~50 |
| `generate_training_query` | features_pitch | FUNCTION | ~200 |
| `get_data_completeness_report` | analysis | FUNCTION | ~100 |
| `get_data_source_stats` | analysis | FUNCTION | ~100 |
| `get_feature_stats` | warehouse | FUNCTION | ~100 |
| `get_feature_stats` | features_pitch | FUNCTION | ~100 |
| `get_git_commit` | raw_retrosheet | FUNCTION | ~30 |
| `get_last_successful_phase` | warehouse | FUNCTION | ~80 |
| `get_plate_appearance_features` | inference | FUNCTION | ~150 |
| `get_player_season_stats` | analysis | FUNCTION | ~100 |
| `get_recent_games` | analysis | FUNCTION | ~50 |
| `get_resumable_batch` | warehouse | FUNCTION | ~100 |
| `get_simulation_state` | inference | FUNCTION | ~100 |
| `get_team_season_stats` | analysis | FUNCTION | ~100 |
| `get_unprocessed_count` | warehouse | FUNCTION | ~50 |
| `has_scheduled_games_today` | metadata | FUNCTION | ~50 |
| `health_check` | warehouse | FUNCTION | ~100 |
| `ingest_all_endpoints_for_game` | raw_mlb | FUNCTION | ~150 |
| `ingest_endpoint` | raw_mlb | FUNCTION | ~100 |
| `init_simulation` | inference | FUNCTION | ~200 |
| `is_game_hours` | metadata | FUNCTION | ~50 |
| `is_mlb_season` | metadata | FUNCTION | ~50 |
| `log_phase_end` | warehouse | FUNCTION | ~100 |
| `log_phase_start` | warehouse | FUNCTION | ~100 |
| `populate_all_bridge_tables` | bridge | PROCEDURE | ~200 |
| `populate_coach_xref` | bridge | PROCEDURE | ~150 |
| `populate_features_phase` | warehouse | PROCEDURE | ~300 |
| `populate_game_state_from_mlb` | mlb_features | FUNCTION | ~150 |
| `populate_game_state_from_retrosheet` | mlb_features | FUNCTION | ~150 |
| `populate_game_xref` | bridge | PROCEDURE | ~200 |
| `populate_park_xref` | bridge | PROCEDURE | ~150 |
| `populate_player_season_stats` | mlb_features | FUNCTION | ~150 |
| `populate_player_xref` | bridge | PROCEDURE | ~200 |
| `populate_season_aware_team_xref` | bridge | PROCEDURE | ~150 |
| `populate_team_xref` | bridge | PROCEDURE | ~150 |
| `populate_umpire_xref` | bridge | PROCEDURE | ~150 |
| `poll_active_games` | raw_sportradar | FUNCTION | ~100 |
| `poll_active_games_conditional` | metadata | FUNCTION | ~100 |
| `poll_all_active_endpoints` | raw_mlb | FUNCTION | ~150 |
| `poll_all_endpoints_conditional` | metadata | FUNCTION | ~100 |
| `predict_plate_appearance_batch` | inference | FUNCTION | ~200 |
| `refresh_all_materialized_views` | features | FUNCTION | ~50 |
| `refresh_combined_data` | analysis | FUNCTION | ~100 |
| `refresh_data_dictionary` | metadata | FUNCTION | ~100 |
| `refresh_data_quality_summary` | validation | FUNCTION | ~50 |
| `refresh_mlb_analytics` | analysis | PROCEDURE | ~100 |
| `resolve_team_id` | mlb | FUNCTION | ~100 |
| `safe_date_mmddyyyy` | core | FUNCTION | ~50 |
| `safe_date_yyyymmdd` | core | FUNCTION | ~50 |
| `safe_int` | core | FUNCTION | ~50 |
| `season_range` | core | FUNCTION | ~30 |
| `should_poll_games` | metadata | FUNCTION | ~50 |
| `start_ingest_run` | raw_retrosheet | FUNCTION | ~150 |
| `update_batch_progress` | warehouse | FUNCTION | ~100 |
| `update_ingest_run_progress` | raw_retrosheet | FUNCTION | ~100 |
| `update_timestamp` | features_pitch | FUNCTION | ~30 |
| `update_updated_at` | raw_retrosheet | FUNCTION | ~30 |
| `update_updated_at_column` | bridge | FUNCTION | ~30 |
| `update_updated_at_column` | predictions | FUNCTION | ~30 |
| `validate_mlb_data` | analysis | PROCEDURE | ~200 |
| `verify_features_populated` | warehouse | FUNCTION | ~150 |

---

## 🎯 Quick Reference: Common Operations

### Full Rebuild with Tracking
```sql
-- 1. Populate bridge tables
CALL bridge.populate_all_bridge_tables(true);

-- 2. Run feature population phases 1-13
FOR i IN 1..13 LOOP
    CALL warehouse.populate_features_phase(i, false);
END LOOP;

-- 3. Verify completion
SELECT * FROM warehouse.verify_features_populated()
WHERE pct_populated < 100;
```

### Resume Interrupted Population
```sql
-- Check last successful phase
SELECT * FROM warehouse.get_last_successful_phase('resume');

-- Resume from that phase
CALL warehouse.populate_features_phase(5, false);  -- Resume phase 5
```

### Data Quality Check
```sql
-- Run full validation
CALL analysis.validate_mlb_data();

-- Check specific game
SELECT * FROM analysis.calculate_mlb_data_quality('2025_04_24_anamlb_balmlb_1');

-- Get completeness report
SELECT * FROM analysis.get_data_completeness_report();
```

---

**End of Procedures and Functions Reference**

*Last Updated: April 24, 2026*  
*Total Procedures/Functions Documented: 87*
