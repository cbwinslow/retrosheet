/*
File: sql/metadata/001_add_table_comments.sql
Purpose: Add COMMENT ON statements for all database tables and views
Author: Agent
Date: 2026-04-24
Depends On: All existing schemas and tables
Called By: Manual - run once to populate metadata

Notes:
- Comments follow AGENTS.md documentation standards
- Includes description, purpose, and key statistics where applicable
- Run this after any new table creation to maintain documentation
*/

-- ============================================
-- CORE SCHEMA
-- ============================================

COMMENT ON TABLE core.games IS 'Canonical game records with 62,598 historical games. Primary source for game-level metadata including date, teams, venue, and final score. Links to raw_retrosheet.chadwick_games and raw_mlb.games via bridge.game_xref';

COMMENT ON TABLE core.events IS '4.9 million play-level events from Retrosheet. Contains play-by-play data with event codes, descriptions, base running, and fielding. Parsed from Chadwick output.';

COMMENT ON TABLE core.plate_appearances IS '4.8 million plate appearance outcomes derived from core.events. One row per PA with batter, pitcher, outcome, and base state. Primary training table for PA outcome models.';

COMMENT ON TABLE core.players IS 'Canonical player registry with unique player IDs. Contains biographical information, bats/throws, and debut dates. Links to bridge.player_xref for cross-source lookups.';

COMMENT ON TABLE core.teams IS 'Canonical team registry with franchise information. Links to bridge.team_xref for cross-source lookups.';

COMMENT ON TABLE core.parks IS 'Stadium and ballpark information including capacity, surface type, and dimensions.';

COMMENT ON TABLE core.live_games IS 'Real-time game feeds (16 GB). Stores live game state from MLB API for in-progress games. Updated continuously during games.';

COMMENT ON TABLE core.live_events IS 'Real-time play-by-play events (18 GB). Stores live event stream from MLB API. Updated continuously during games.';

COMMENT ON TABLE core.live_plate_appearances IS 'Live PA tracking for current game state. Tracks current PA in progress with real-time feature updates.';

COMMENT ON TABLE core.mlb_pbp IS 'MLB play-by-play structured data. Alternative to live_events with normalized schema.';

-- ============================================
-- BRIDGE SCHEMA
-- ============================================

COMMENT ON TABLE bridge.player_xref IS 'Cross-reference table mapping player IDs across sources: Retrosheet ID ↔ MLB ID ↔ Lahman ID. Contains 21,000+ player mappings with confidence scores. Size: 47 MB';

COMMENT ON TABLE bridge.team_xref IS 'Cross-reference table mapping team IDs across sources. Links franchise IDs across Retrosheet, MLB API, Lahman, and ESPN.';

COMMENT ON TABLE bridge.game_xref IS 'Cross-reference table linking Retrosheet games to MLB API games. Contains 62,000+ game mappings for historical games 2008-2024.';

COMMENT ON TABLE bridge.park_xref IS 'Stadium/ballpark ID cross-references across sources. Links park IDs from Retrosheet, MLB API, and Lahman.';

COMMENT ON TABLE bridge.coach_xref IS 'Coach and manager ID cross-references. Links coaching staff IDs across sources.';

COMMENT ON TABLE bridge.umpire_xref IS 'Umpire ID cross-references. Links umpire IDs from Retrosheet to other sources.';

COMMENT ON TABLE bridge.external_player_xref IS 'External player ID mappings for non-MLB sources. Size: 14 MB';

COMMENT ON TABLE bridge.external_team_xref IS 'External team ID mappings for non-MLB sources.';

-- ============================================
-- RAW_RETROSHEET SCHEMA
-- ============================================

COMMENT ON TABLE raw_retrosheet.chadwick_events IS 'Parsed Retrosheet event data (4.2 GB). One row per event with 96 fields covering play description, base running, fielding, and scoring. Source-preserved from Chadwick output.';

COMMENT ON TABLE raw_retrosheet.chadwick_games IS 'Parsed Retrosheet game records (124 MB). One row per game with metadata including date, teams, umps, and weather.';

COMMENT ON TABLE raw_retrosheet.chadwick_event_raw IS 'Raw event strings from Chadwick output before parsing (3.2 GB). Preserved for re-parsing if needed.';

COMMENT ON TABLE raw_retrosheet.chadwick_daily IS 'Daily player statistics from Retrosheet (946 MB). Aggregated by player-date for quick lookups.';

COMMENT ON TABLE raw_retrosheet.chadwick_substitutions IS 'Substitution records from Retrosheet (206 MB). Tracks player replacements during games.';

COMMENT ON TABLE raw_retrosheet.chadwick_comments IS 'Event comments and annotations from Retrosheet (27 MB). Contains additional context for plays.';

COMMENT ON TABLE raw_retrosheet.biofile IS 'Player biographical information from Retrosheet (5.7 MB). Contains birth date, birthplace, bats/throws.';

COMMENT ON TABLE raw_retrosheet.season_rosters IS 'Season roster data from Retrosheet (36 MB). Team rosters by season with player assignments.';

COMMENT ON TABLE raw_retrosheet.season_schedules IS 'Season schedules from Retrosheet (57 MB). Game dates and matchups by season.';

COMMENT ON TABLE raw_retrosheet.season_teams IS 'Team season records from Retrosheet (920 kB). Season-level team statistics.';

COMMENT ON TABLE raw_retrosheet.season_umpires IS 'Umpire assignments by season (2.4 MB). Tracks which umps worked which games.';

COMMENT ON TABLE raw_retrosheet.coaches IS 'Coach records from Retrosheet (1.7 MB). Coaching staff by team and season.';

COMMENT ON TABLE raw_retrosheet.ejections IS 'Ejection records from Retrosheet (4.7 MB). Tracks player/manager ejections with reasons.';

COMMENT ON TABLE raw_retrosheet.ingest_runs IS 'Ingestion run tracking with git commit hashes, timestamps, and record counts. Supports reproducibility tracking.';

COMMENT ON TABLE raw_retrosheet.ballparks_reference IS 'Ballpark reference data from Retrosheet (104 kB). Stadium IDs and basic info.';

COMMENT ON TABLE raw_retrosheet.teams_reference IS 'Team reference data from Retrosheet (48 kB). Team IDs and franchise info.';

COMMENT ON TABLE raw_retrosheet.biofile_legacy IS 'Legacy biofile format for backward compatibility (5.7 MB).';

COMMENT ON TABLE raw_retrosheet.relatives IS 'Player relationship data from Retrosheet (184 kB). Family connections between players.';

COMMENT ON TABLE raw_retrosheet.special_gamelog_lines IS 'Special game log events (2.8 MB). Records of unusual game events.';

-- ============================================
-- RAW_MLB SCHEMA
-- ============================================

COMMENT ON TABLE raw_mlb.statcast IS 'Source-preserved Statcast pitch-level data from Baseball Savant (3.9 GB). 7.8M pitches with 118 columns including pitch physics, location, and batted ball data. 2015-2025 seasons.';

COMMENT ON TABLE raw_mlb.stg_statcast IS 'Staging table for Statcast data ingestion (510 MB). Temporary holding before validation.';

COMMENT ON TABLE raw_mlb.live_feed_snapshots IS 'Live game feed JSON snapshots from MLB Stats API (16 GB). Captured during games for real-time analysis.';

COMMENT ON TABLE raw_mlb.boxscore_snapshots IS 'Game boxscore JSON from MLB API (40 kB). Structured game summary data.';

COMMENT ON TABLE raw_mlb.schedule_snapshots IS 'Game schedule JSON from MLB API (36 MB). Daily schedule with game times and matchups.';

COMMENT ON TABLE raw_mlb.reference_snapshots IS 'Reference data JSON from MLB API (14 MB). Teams, players, venues reference data.';

COMMENT ON TABLE raw_mlb.play_by_play_snapshots IS 'Play-by-play JSON from MLB API (40 kB). Structured PBP data.';

COMMENT ON TABLE raw_mlb.pitch_metrics_snapshots IS 'Pitch metrics JSON from MLB API (40 kB). Detailed pitch-level metrics.';

COMMENT ON TABLE raw_mlb.win_probability_snapshots IS 'Win probability JSON from MLB API (40 kB). WP changes by play.';

COMMENT ON TABLE raw_mlb.gameday_xml IS 'Gameday XML data from MLB (16 kB). Legacy XML format feeds.';

-- ============================================
-- RAW_ESPN SCHEMA
-- ============================================

COMMENT ON TABLE raw_espn.game_snapshots IS 'ESPN API game data JSON (9.8 GB). Game summaries and box scores from ESPN.';

COMMENT ON TABLE raw_espn.schedule_snapshots IS 'ESPN API schedule JSON (341 MB). Game schedules with TV broadcast info.';

COMMENT ON TABLE raw_espn.plays_snapshots IS 'ESPN API play-by-play JSON (103 MB). Structured PBP from ESPN.';

COMMENT ON TABLE raw_espn.team_stats_snapshots IS 'ESPN API team statistics JSON (40 kB). Team-level stats.';

COMMENT ON TABLE raw_espn.player_stats_snapshots IS 'ESPN API player statistics JSON (40 kB). Player-level stats.';

-- ============================================
-- LAHMAN SCHEMA
-- ============================================

COMMENT ON TABLE lahman.people IS 'Player biographical data from Lahman database (3.6 MB). Names, birth dates, debut dates.';

COMMENT ON TABLE lahman.batting IS 'Season-level batting statistics from Lahman (12 MB). Standard batting stats by player-season.';

COMMENT ON TABLE lahman.pitching IS 'Season-level pitching statistics from Lahman (6.4 MB). Standard pitching stats by player-season.';

COMMENT ON TABLE lahman.fielding IS 'Season-level fielding statistics from Lahman (13 MB). Fielding stats by player-season-position.';

COMMENT ON TABLE lahman.teams IS 'Team season records from Lahman (768 kB). Team standings and totals by season.';

COMMENT ON TABLE lahman.managers IS 'Manager records from Lahman (288 kB). Manager assignments and records.';

COMMENT ON TABLE lahman.appearances IS 'Player game appearances from Lahman (11 MB). Games played by position.';

COMMENT ON TABLE lahman.battingpost IS 'Postseason batting statistics from Lahman (1.6 MB). Playoff batting stats.';

COMMENT ON TABLE lahman.pitchingpost IS 'Postseason pitching statistics from Lahman (864 kB). Playoff pitching stats.';

COMMENT ON TABLE lahman.fieldingpost IS 'Postseason fielding statistics from Lahman (1.3 MB). Playoff fielding stats.';

COMMENT ON TABLE lahman.fieldingof IS 'Outfield fielding statistics from Lahman (752 kB). OF positional stats.';

COMMENT ON TABLE lahman.fieldingofsplit IS 'Outfield split position stats from Lahman (2.9 MB). Detailed OF positioning.';

COMMENT ON TABLE lahman.allstarfull IS 'All-Star game rosters from Lahman (424 kB). ASG appearances by player.';

COMMENT ON TABLE lahman.homegames IS 'Home game attendance from Lahman (304 kB). Games and attendance by team-park-season.';

COMMENT ON TABLE lahman.seriespost IS 'Postseason series results from Lahman (56 kB). Playoff series outcomes.';

COMMENT ON TABLE lahman.managershalf IS 'Mid-season manager changes from Lahman (16 kB). Manager transitions.';

COMMENT ON TABLE lahman.teamsfranchises IS 'Franchise information from Lahman (16 kB). Franchise IDs and current teams.';

COMMENT ON TABLE lahman.teamshalf IS 'Team half-season records from Lahman (16 kB). First/second half splits.';

COMMENT ON TABLE lahman.parks IS 'Ballpark information from Lahman (56 kB). Park names and locations.';

-- ============================================
-- FEATURES_PITCH SCHEMA
-- ============================================

COMMENT ON TABLE features_pitch.locations IS 'PostGIS-enabled pitch location table (13 GB). 7.66M pitches 2015-2025 with spatial geometry column for GIS analysis. Includes plate_x, plate_z coordinates and calculated geometry.';

COMMENT ON TABLE features_pitch.base_features IS 'Complete Statcast feature table (4 GB). 7.66M pitches with all 118 Statcast columns. Mirror of raw_mlb.statcast with computed game_year.';

COMMENT ON TABLE features_pitch.engineered_features IS 'ML-ready engineered features (4 GB). 7.66M pitches with 220+ derived features including velocity differential, spin efficiency, count leverage, run expectancy, and matchup history.';

COMMENT ON TABLE features_pitch.pitcher_arsenals IS 'Pitcher pitch type arsenal breakdowns. Aggregated pitch usage and effectiveness by pitcher-pitch type combination.';

COMMENT ON TABLE features_pitch.batter_zone_profiles IS 'Batter zone swing rates by zone. Historical swing decision patterns for each batter in each strike zone region.';

COMMENT ON TABLE features_pitch.count_performance IS 'Count-specific performance statistics. Batter and pitcher stats broken down by ball-strike count.';

COMMENT ON TABLE features_pitch.batter_pitch_type_performance IS 'Batter performance against each pitch type. Aggregated outcomes for batter-pitch_type combinations.';

COMMENT ON TABLE features_pitch.matchup_history IS 'Batter-pitcher matchup history. Historical PA outcomes between specific batter-pitcher pairs.';

COMMENT ON TABLE features_pitch.feature_registry IS 'Feature metadata catalog. Documents all features with descriptions, data types, sources, and population status.';

COMMENT ON TABLE features_pitch.sequential_features IS 'LSTM sequence features. Pitch sequences within plate appearances for sequence modeling.';

COMMENT ON TABLE features_pitch.player_context IS 'Player rolling context. 30/60/90-day rolling statistics for batters and pitchers.';

COMMENT ON TABLE features_pitch.pitch_sequences IS 'PA-level pitch arrays. Array of all pitches within each plate appearance for sequence analysis.';

COMMENT ON TABLE features_pitch.model_training_set IS 'Versioned model training data. Snapshots of training data with version labels for reproducibility.';

-- ============================================
-- MLB SCHEMA
-- ============================================

COMMENT ON TABLE mlb.games IS 'MLB API game records (12 MB). Games from MLB Stats API with metadata and outcomes.';

COMMENT ON TABLE mlb.pitches IS 'MLB API pitch-level data (7.1 GB). Pitch records from MLB API.';

COMMENT ON TABLE mlb.play_events IS 'MLB API play events (1.3 GB). Play-level data from MLB API.';

COMMENT ON TABLE mlb.players IS 'MLB API player records (80 kB). Player data from MLB API.';

COMMENT ON TABLE mlb.teams IS 'MLB API team records (72 kB). Team data from MLB API.';

COMMENT ON TABLE mlb.venues IS 'MLB API venue records (16 kB). Stadium data from MLB API.';

-- ============================================
-- MLB_FEATURES SCHEMA
-- ============================================

COMMENT ON TABLE mlb_features.game_state_features IS 'Game situation features for modeling (125 MB). Features derived from game state: inning, score, bases, outs.';

COMMENT ON TABLE mlb_features.win_probability_training IS 'Win probability model training data (200 MB). Historical game states with WP labels for training.';

COMMENT ON TABLE mlb_features.player_season_stats IS 'Player season statistics (7.1 MB). Aggregated season-level stats for feature generation.';

COMMENT ON TABLE mlb_features.team_season_stats IS 'Team season statistics (16 kB). Aggregated team-level stats for feature generation.';

COMMENT ON TABLE mlb_features.park_factors IS 'Park effect factors (16 kB). Calculated park effects for run scoring and other outcomes.';

COMMENT ON TABLE mlb_features.batter_pitcher_matchups IS 'Batter-pitcher matchup stats (16 kB). Historical PA outcomes for specific matchups.';

-- ============================================
-- MLB_MODELS SCHEMA
-- ============================================

COMMENT ON TABLE mlb_models.win_probability_training IS 'WP model training dataset (40 MB). Curated training data for win probability models.';

COMMENT ON TABLE mlb_models.win_probability_training_enhanced IS 'Enhanced WP training dataset (61 MB). WP training data with additional engineered features.';

-- ============================================
-- MLB_ENHANCED SCHEMA
-- ============================================

COMMENT ON TABLE mlb_enhanced.statcast_pitches IS 'Enhanced Statcast data (633 MB). Statcast with derived metrics and classifications.';

COMMENT ON TABLE mlb_enhanced.betting_features IS 'Features for betting models (55 MB). Features specifically engineered for prediction market models.';

COMMENT ON TABLE mlb_enhanced.batter_pitcher_history IS 'Historical matchup data (8.3 MB). Comprehensive batter-pitcher history for matchup models.';

COMMENT ON TABLE mlb_enhanced.player_advanced_stats IS 'Advanced player metrics (16 kB). Calculated advanced statistics beyond standard stats.';

-- ============================================
-- PREDICTIONS SCHEMA
-- ============================================

COMMENT ON TABLE predictions.pa_predictions IS 'Plate appearance predictions. Outcome probabilities for each PA scored by models.';

COMMENT ON TABLE predictions.live_pa_predictions IS 'Live game predictions (144 kB). Real-time predictions for in-progress PAs.';

COMMENT ON TABLE predictions.win_probabilities IS 'Win probability estimates. WP for each game state scored by models.';

COMMENT ON TABLE predictions.target_probabilities IS 'Target variable probabilities. Probabilities for specific prediction targets.';

COMMENT ON TABLE predictions.prediction_runs IS 'Prediction batch runs. Metadata for each prediction batch execution.';

COMMENT ON TABLE predictions.api_prediction_requests IS 'API prediction log (64 kB). Log of all API prediction requests.';

COMMENT ON TABLE predictions.simulation_runs IS 'Monte Carlo simulation runs (88 kB). MC simulation metadata and results.';

COMMENT ON TABLE predictions.calibration_reports IS 'Model calibration data (152 kB). Calibration curves and metrics.';

COMMENT ON TABLE predictions.bootstrap_reports IS 'Bootstrap confidence intervals (88 kB). Uncertainty estimates from bootstrap sampling.';

COMMENT ON TABLE predictions.prediction_targets IS 'Prediction target definitions (72 kB). Configuration for prediction targets.';

-- ============================================
-- MODELS SCHEMA
-- ============================================

COMMENT ON TABLE models.model_registry IS 'Model registry with metadata (488 kB). Registered models with version, metrics, and deployment status.';

-- ============================================
-- WAREHOUSE SCHEMA
-- ============================================

COMMENT ON TABLE warehouse.rebuild_runs IS 'Feature population run tracking. Orchestrates phased feature generation with status tracking.';

COMMENT ON TABLE warehouse.rebuild_log IS 'Detailed phase logging. Logs each phase execution with timing and row counts.';

COMMENT ON TABLE warehouse.batch_operations IS 'Batch progress tracking. Tracks batch operations for resumable feature population.';

-- ============================================
-- METADATA SCHEMA
-- ============================================

COMMENT ON TABLE metadata.table_dictionary IS 'Table metadata and descriptions (144 kB). Documents all tables with descriptions and purposes.';

COMMENT ON TABLE metadata.column_dictionary IS 'Column metadata and definitions (1.5 MB). Documents all columns with data types and descriptions.';

-- ============================================
-- ANALYSIS SCHEMA
-- ============================================

COMMENT ON TABLE analysis.data_quality_summary IS 'Summary of data quality across all sources. Aggregated quality metrics by table.';

-- ============================================
-- EDA SCHEMA
-- ============================================

COMMENT ON TABLE eda.pitch_distribution IS 'Pitch type distribution analysis view. Aggregated pitch type frequencies.';

COMMENT ON TABLE eda.velocity_by_year IS 'Velocity trends by year view. Year-over-year velocity changes.';

-- ============================================
-- VALIDATION SCHEMA
-- ============================================

COMMENT ON TABLE validation.null_counts IS 'NULL value counts by column. Data completeness validation.';

COMMENT ON TABLE validation.data_quality_score IS 'Overall data quality score. Aggregated quality metrics.';

-- ============================================
-- CRON SCHEMA (pg_cron)
-- ============================================

COMMENT ON TABLE cron.job IS 'Scheduled job definitions. pg_cron job configuration.';

COMMENT ON TABLE cron.job_run_details IS 'Job execution history. Log of cron job runs with timing and status.';

-- ============================================
-- CHAT SCHEMA
-- ============================================

COMMENT ON TABLE chat.query_logs IS 'Chatbot query and response log (72 kB). Tracks all chatbot interactions.';

-- ============================================
-- MARKET_EDGES SCHEMA
-- ============================================

COMMENT ON TABLE market_edges.market_prices IS 'Prediction market odds and prices. Market data for comparison with model predictions.';

COMMENT ON TABLE market_edges.detected_edges IS 'Detected value opportunities. Cases where model differs significantly from market.';

-- ============================================
-- BASEBALL_SAVANT SCHEMA
-- ============================================

COMMENT ON TABLE baseball_savant.batter_stats IS 'Batter statistics from Baseball Savant (1.1 MB). Savant-specific batting metrics.';

COMMENT ON TABLE baseball_savant.pitcher_stats IS 'Pitcher statistics from Baseball Savant (304 kB). Savant-specific pitching metrics.';

COMMENT ON TABLE baseball_savant.total_stats IS 'Combined batting/pitching totals (5.2 MB). Aggregate statistics from Savant.';

-- ============================================
-- RAW_* STAGING SCHEMAS
-- ============================================

COMMENT ON TABLE raw_lahman.stg_batting IS 'Lahman batting staging table. Temporary holding during Lahman ingestion.';

COMMENT ON TABLE raw_lahman.stg_pitching IS 'Lahman pitching staging table. Temporary holding during Lahman ingestion.';

COMMENT ON TABLE raw_lahman.stg_people IS 'Lahman people staging table. Temporary holding during Lahman ingestion.';

COMMENT ON TABLE raw_lahman.stg_teams IS 'Lahman teams staging table. Temporary holding during Lahman ingestion.';

COMMENT ON TABLE raw_lahman.stg_salaries IS 'Lahman salaries staging table. Temporary holding during Lahman ingestion.';

COMMENT ON TABLE raw_bref.batting_stats IS 'Baseball Reference batting statistics (16 MB). Bref batting data.';

COMMENT ON TABLE raw_bref.pitching_stats IS 'Baseball Reference pitching statistics (3.2 MB). Bref pitching data.';

COMMENT ON TABLE raw_baseball_reference.game_logs IS 'Baseball Reference game logs (16 kB). Historical game records.';

COMMENT ON TABLE raw_baseball_reference.stg_game_logs IS 'BRef game logs staging. Temporary holding during ingestion.';

COMMENT ON TABLE raw_statcast.stg_events IS 'Statcast events staging (4.8 MB). Temporary holding during Statcast ingestion.';

COMMENT ON TABLE raw_statcast.events IS 'Statcast events (1 MB). Parsed Statcast events.';

COMMENT ON TABLE raw_sportradar.game_snapshots IS 'SportRadar game snapshots (40 kB). SportRadar API game data.';

COMMENT ON TABLE raw_sportradar.push_events IS 'SportRadar push events (56 kB). Real-time push events from SportRadar.';

COMMENT ON TABLE raw_park_factors.factors IS 'Park factors data (32 kB). Calculated park effect factors.';

COMMENT ON TABLE raw_mlb_rosters.roster_snapshots IS 'MLB roster snapshots (208 kB). Team roster data by date.';

COMMENT ON TABLE raw_markets.market_snapshots IS 'Market data snapshots (24 kB). Historical market prices.';

COMMENT ON TABLE raw_external.baseball_data_com IS 'Baseball-data.com external data (16 kB). Third party data source.';

COMMENT ON TABLE test.runs IS 'Test schema table. Used for testing database operations.';

-- ============================================
-- INFERENCE SCHEMA
-- ============================================

COMMENT ON TABLE inference.simulation_states IS 'Monte Carlo simulation state storage (24 kB). Tracks simulation progress and results.';

-- ============================================
-- FEATURES SCHEMA
-- ============================================

COMMENT ON TABLE features.play_snapshot IS 'Play state snapshots for feature generation (24 kB). Captures game state at each play.';

COMMIT;
