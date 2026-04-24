/*
File: sql/metadata/002_add_procedure_comments.sql
Purpose: Add COMMENT ON statements for all database functions and procedures
Author: Agent
Date: 2026-04-24
Depends On: All existing schemas with functions/procedures
Called By: Manual - run once to populate metadata

Notes:
- Documents all warehouse orchestration procedures
- Documents all bridge population procedures
- Documents all analysis and utility functions
*/

-- ============================================
-- WAREHOUSE SCHEMA PROCEDURES
-- ============================================

COMMENT ON PROCEDURE warehouse.populate_features_phase IS 'Orchestrates phased feature population. Runs a specific phase (1-13) with optional dry-run mode. Logs progress to warehouse.rebuild_log. Supports resume from checkpoints.';

COMMENT ON PROCEDURE warehouse.create_batch_checkpoint IS 'Creates a resume checkpoint for batch operations. Stores batch name, column, total rows, and processed rows for resumable processing.';

COMMENT ON FUNCTION warehouse.verify_features_populated IS 'Verifies that all engineered features have been populated. Returns completion percentage by column. Used for post-population validation.';

COMMENT ON FUNCTION warehouse.get_feature_stats IS 'Returns feature population statistics. Shows populated vs unpopulated rows for all feature columns.';

COMMENT ON FUNCTION warehouse.estimate_batch_completion IS 'Estimates completion time for batch operations. Calculates remaining time based on batch size and processing speed.';

COMMENT ON FUNCTION warehouse.get_last_successful_phase IS 'Returns the last successfully completed feature population phase. Used for resume functionality.';

COMMENT ON FUNCTION warehouse.get_resumable_batch IS 'Retrieves batch resume point. Returns last processed ID for continuing interrupted batches.';

COMMENT ON FUNCTION warehouse.get_unprocessed_count IS 'Counts unprocessed rows for a feature column. Useful for estimating remaining work.';

COMMENT ON FUNCTION warehouse.health_check IS 'Performs warehouse schema health check. Validates tables, indexes, and procedure availability.';

COMMENT ON FUNCTION warehouse.log_phase_start IS 'Logs start of a feature population phase. Creates entry in warehouse.rebuild_log with metadata.';

COMMENT ON FUNCTION warehouse.log_phase_end IS 'Logs end of a feature population phase. Updates rebuild_log with status, rows affected, and any errors.';

COMMENT ON FUNCTION warehouse.update_batch_progress IS 'Updates batch operation progress. Records last processed ID and row count for resume capability.';

-- ============================================
-- BRIDGE SCHEMA PROCEDURES
-- ============================================

COMMENT ON PROCEDURE bridge.populate_player_xref IS 'Populates player cross-reference table. Links Retrosheet player IDs to MLB and Lahman IDs. Returns count of inserted records.';

COMMENT ON PROCEDURE bridge.populate_team_xref IS 'Populates team cross-reference table. Links team IDs across Retrosheet, MLB, Lahman, and ESPN sources.';

COMMENT ON PROCEDURE bridge.populate_game_xref IS 'Populates game cross-reference table. Links Retrosheet games to MLB API games by date and teams. Returns matched count.';

COMMENT ON PROCEDURE bridge.populate_park_xref IS 'Populates park cross-reference table. Links stadium IDs across sources. Returns updated count.';

COMMENT ON PROCEDURE bridge.populate_coach_xref IS 'Populates coach cross-reference table. Links coaching staff IDs across sources. Returns coach count.';

COMMENT ON PROCEDURE bridge.populate_umpire_xref IS 'Populates umpire cross-reference table. Links umpire IDs across sources. Returns umpire count.';

COMMENT ON PROCEDURE bridge.populate_all_bridge_tables IS 'Runs all bridge table population procedures. Orchestrates full bridge refresh with optional player xref exclusion.';

COMMENT ON PROCEDURE bridge.populate_season_aware_team_xref IS 'Populates season-aware team cross-references. Handles franchise relocations and name changes over time.';

COMMENT ON FUNCTION bridge.update_updated_at_column IS 'Trigger function to auto-update updated_at timestamp. Used on bridge tables for change tracking.';

-- ============================================
-- CORE SCHEMA FUNCTIONS
-- ============================================

COMMENT ON FUNCTION core.count_rows IS 'Counts rows in any table safely. Takes regclass parameter for dynamic table counting.';

COMMENT ON FUNCTION core.safe_date_mmddyyyy IS 'Safely parses dates in MM/DD/YYYY format. Returns NULL for invalid dates instead of error.';

COMMENT ON FUNCTION core.safe_date_yyyymmdd IS 'Safely parses dates in YYYYMMDD format. Returns NULL for invalid dates instead of error.';

COMMENT ON FUNCTION core.safe_int IS 'Safely parses integers from text. Returns NULL for non-numeric values instead of error.';

COMMENT ON FUNCTION core.season_range IS 'Returns available season range in database. Returns min and max seasons with game data.';

-- ============================================
-- ANALYSIS SCHEMA FUNCTIONS
-- ============================================

COMMENT ON FUNCTION analysis.calculate_mlb_data_quality IS 'Calculates data quality score for a specific game. Returns completeness percentage across all data sources.';

COMMENT ON PROCEDURE analysis.detect_duplicate_games IS 'Detects and reports duplicate game entries. Identifies games with multiple records that should be merged.';

COMMENT ON FUNCTION analysis.get_data_completeness_report IS 'Generates overall data completeness report. Aggregates completeness metrics across all tables.';

COMMENT ON FUNCTION analysis.get_data_source_stats IS 'Returns statistics by data source. Shows record counts and coverage for each source.';

COMMENT ON FUNCTION analysis.get_player_season_stats IS 'Retrieves player statistics for a season. Takes MLB player ID and season year as parameters.';

COMMENT ON FUNCTION analysis.get_recent_games IS 'Returns games from recent days. Default 7 days, configurable parameter.';

COMMENT ON FUNCTION analysis.get_team_season_stats IS 'Retrieves team statistics for a season. Takes MLB team ID and season year as parameters.';

COMMENT ON FUNCTION analysis.refresh_combined_data IS 'Refreshes combined data sources. Updates materialized views and caches for analysis queries.';

COMMENT ON PROCEDURE analysis.refresh_mlb_analytics IS 'Refreshes MLB analytics materialized views. Updates all analysis views with latest data.';

COMMENT ON PROCEDURE analysis.validate_mlb_data IS 'Runs comprehensive MLB data validation. Checks consistency across sources and reports issues.';

-- ============================================
-- FEATURES_PITCH SCHEMA FUNCTIONS
-- ============================================

COMMENT ON FUNCTION features_pitch.generate_training_query IS 'Generates SQL query for model training. Creates SELECT statement with specified feature categories for given model type.';

COMMENT ON FUNCTION features_pitch.get_feature_stats IS 'Returns statistics for a specific feature column. Shows min, max, avg, null count, and distribution.';

COMMENT ON FUNCTION features_pitch.update_timestamp IS 'Trigger function to auto-update modified_at timestamp. Applied to feature tables for change tracking.';

-- ============================================
-- INFERENCE SCHEMA FUNCTIONS
-- ============================================

COMMENT ON FUNCTION inference.init_simulation IS 'Initializes new Monte Carlo simulation. Creates simulation state record with game parameters.';

COMMENT ON FUNCTION inference.get_simulation_state IS 'Retrieves current simulation state. Returns all parameters and current progress for a simulation ID.';

COMMENT ON FUNCTION inference.get_plate_appearance_features IS 'Returns features for a plate appearance prediction. Takes game state parameters and returns feature vector.';

COMMENT ON FUNCTION inference.predict_plate_appearance_batch IS 'Batch prediction function for plate appearances. Scores multiple PAs in single call for efficiency.';

-- ============================================
-- METADATA SCHEMA FUNCTIONS
-- ============================================

COMMENT ON FUNCTION metadata.refresh_data_dictionary IS 'Refreshes data dictionary from system catalogs. Populates metadata.table_dictionary and column_dictionary.';

COMMENT ON FUNCTION metadata.is_mlb_season IS 'Checks if MLB season is currently active. Returns boolean based on current date vs season calendar.';

COMMENT ON FUNCTION metadata.is_game_hours IS 'Checks if games are currently being played. Returns boolean based on typical game times.';

COMMENT ON FUNCTION metadata.has_scheduled_games_today IS 'Checks for scheduled games today. Returns boolean if any games on current date.';

COMMENT ON FUNCTION metadata.should_poll_games IS 'Determines if game polling is needed. Combines season active, game hours, and scheduled games checks.';

COMMENT ON FUNCTION metadata.poll_active_games_conditional IS 'Conditionally polls active games. Only polls if should_poll_games returns true.';

COMMENT ON FUNCTION metadata.poll_all_endpoints_conditional IS 'Conditionally polls all endpoints. Respects polling rules to avoid unnecessary API calls.';

-- ============================================
-- MLB SCHEMA FUNCTIONS
-- ============================================

COMMENT ON FUNCTION mlb.resolve_team_id IS 'Resolves team ID from name and date. Handles team relocations and name changes over time.';

-- ============================================
-- MLB_FEATURES SCHEMA FUNCTIONS
-- ============================================

COMMENT ON FUNCTION mlb_features.populate_game_state_from_mlb IS 'Generates game state features from MLB data. Processes raw_mlb tables into mlb_features.';

COMMENT ON FUNCTION mlb_features.populate_game_state_from_retrosheet IS 'Generates game state features from Retrosheet data. Processes core tables into mlb_features with year range parameters.';

COMMENT ON FUNCTION mlb_features.populate_player_season_stats IS 'Calculates player season statistics. Aggregates from raw data into season-level features.';

-- ============================================
-- RAW_MLB SCHEMA FUNCTIONS
-- ============================================

COMMENT ON FUNCTION raw_mlb.ingest_all_endpoints_for_game IS 'Ingests all endpoint data for a specific game. Fetches live feed, boxscore, PBP, and metrics for game_pk.';

COMMENT ON FUNCTION raw_mlb.ingest_endpoint IS 'Ingests specific endpoint for a game. Takes game_pk, endpoint suffix, and target table parameters.';

COMMENT ON FUNCTION raw_mlb.poll_all_active_endpoints IS 'Polls all active game endpoints. Discovers and fetches data for currently active games.';

-- ============================================
-- RAW_RETROSHEET SCHEMA FUNCTIONS
-- ============================================

COMMENT ON FUNCTION raw_retrosheet.start_ingest_run IS 'Starts new ingestion run with tracking. Records git commit, script version, and parameters for reproducibility.';

COMMENT ON FUNCTION raw_retrosheet.complete_ingest_run IS 'Marks ingestion run as complete. Records final record counts and details.';

COMMENT ON FUNCTION raw_retrosheet.fail_ingest_run IS 'Marks ingestion run as failed. Records error message and details for debugging.';

COMMENT ON FUNCTION raw_retrosheet.update_ingest_run_progress IS 'Updates ingestion run progress. Records downloaded, ingested, and failed record counts.';

COMMENT ON FUNCTION raw_retrosheet.compute_checksum IS 'Computes checksum for data validation. Creates hash for verifying data integrity.';

COMMENT ON FUNCTION raw_retrosheet.get_git_commit IS 'Returns current git commit hash. Used for reproducibility tracking in ingestion runs.';

COMMENT ON FUNCTION raw_retrosheet.update_updated_at IS 'Trigger function for updated_at timestamp. Auto-updates modification time on ingestion tables.';

-- ============================================
-- RAW_SPORTRADAR SCHEMA FUNCTIONS
-- ============================================

COMMENT ON FUNCTION raw_sportradar.fetch_live_schedule IS 'Fetches live game schedule from SportRadar. Returns current day schedule.';

COMMENT ON FUNCTION raw_sportradar.poll_active_games IS 'Polls active games from SportRadar. Fetches real-time data for in-progress games.';

-- ============================================
-- VALIDATION SCHEMA FUNCTIONS
-- ============================================

COMMENT ON FUNCTION validation.refresh_data_quality_summary IS 'Refreshes data quality summary views. Updates all validation materialized views.';

-- ============================================
-- FEATURES SCHEMA FUNCTIONS
-- ============================================

COMMENT ON FUNCTION features.refresh_all_materialized_views IS 'Refreshes all feature materialized views. Updates all views in features schema with latest data.';

-- ============================================
-- PREDICTIONS SCHEMA FUNCTIONS
-- ============================================

COMMENT ON FUNCTION predictions.update_updated_at_column IS 'Trigger function for updated_at on prediction tables. Auto-updates modification timestamp.';

COMMIT;
