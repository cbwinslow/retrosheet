/*
File: sql/core/998_table_comments_batch2.sql
Purpose: Add COMMENT ON for remaining undocumented tables (batch 2)
Author: Agent Cascade
Date: 2026-04-24
Depends On: All tables must exist
Called By: Manual execution after new tables created

Tables Documented: 24 tables across raw_mlb, raw_retrosheet, features_pitch
*/

-- features_pitch schema
COMMENT ON TABLE features_pitch.locations IS 'PostGIS-enabled pitch location data with 118 Statcast fields (7.66M pitches 2015-2025)';

-- raw_mlb schema
COMMENT ON TABLE raw_mlb.pitch_metrics_snapshots IS 'Source-preserved MLB pitch metrics API snapshots';
COMMENT ON TABLE raw_mlb.play_by_play_snapshots IS 'Source-preserved MLB play-by-play API snapshots';
COMMENT ON TABLE raw_mlb.statcast IS 'Source-preserved Statcast data from Baseball Savant (7.8M pitches 2015-2025)';
COMMENT ON TABLE raw_mlb.stg_statcast IS 'Staging table for Statcast data ingestion before deduplication';
COMMENT ON TABLE raw_mlb.win_probability_snapshots IS 'Source-preserved MLB win probability API snapshots';

-- raw_retrosheet reference tables
COMMENT ON TABLE raw_retrosheet.ballparks_reference IS 'Retrosheet ballpark reference data (park IDs, names, locations)';
COMMENT ON TABLE raw_retrosheet.biofile IS 'Player biographical data from Retrosheet (current format)';
COMMENT ON TABLE raw_retrosheet.biofile_legacy IS 'Legacy player biographical data format';
COMMENT ON TABLE raw_retrosheet.chadwick_comments IS 'Event-level comments and notes from Chadwick parsing';
COMMENT ON TABLE raw_retrosheet.chadwick_daily IS 'Daily player statistics from Chadwick cwevent output';
COMMENT ON TABLE raw_retrosheet.chadwick_event_raw IS 'Raw Chadwick event file output (c001-cxxx columns, source-preserved)';
COMMENT ON TABLE raw_retrosheet.chadwick_events IS 'Processed Chadwick event data with typed columns';
COMMENT ON TABLE raw_retrosheet.chadwick_games IS 'Processed Chadwick game data with typed columns';
COMMENT ON TABLE raw_retrosheet.chadwick_substitutions IS 'Substitution events from Chadwick parsing';
COMMENT ON TABLE raw_retrosheet.coaches IS 'Team coaching staff data by season';
COMMENT ON TABLE raw_retrosheet.ejections IS 'Player/umpire ejection records';
COMMENT ON TABLE raw_retrosheet.relatives IS 'Player family relationships';
COMMENT ON TABLE raw_retrosheet.season_rosters IS 'Team rosters by season';
COMMENT ON TABLE raw_retrosheet.season_schedules IS 'Game schedules by season';
COMMENT ON TABLE raw_retrosheet.season_teams IS 'Team records and standings by season';
COMMENT ON TABLE raw_retrosheet.season_umpires IS 'Umpire assignments by season';
COMMENT ON TABLE raw_retrosheet.special_gamelog_lines IS 'Special game log entries (forfeits, suspensions, etc.)';
COMMENT ON TABLE raw_retrosheet.teams_reference IS 'Team reference data (franchise IDs, locations, names)';
