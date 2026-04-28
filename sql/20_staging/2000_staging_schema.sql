/*
File: sql/20_staging/2000_staging_schema.sql
Purpose: Initialize staging schema and base tables for data transformation
Author: Agent Cascade
Date: 2026-04-28
Depends On: sql/30_core/3001_core_init.sql
Called By: scripts/staging/initialize_staging.sh

Creates:
- staging schema
- stg_retrosheet_events: Cleaned event-level data from chadwick_event_raw
- stg_retrosheet_games: Game-level aggregated data
- stg_retrosheet_players: Player reference data

Notes:
- All staging tables preserve source grain
- Adds validation flags (is_valid, validation_errors)
- Adds lineage tracking (source_file, loaded_at, ingest_run_id)
- Types are cast but column names match raw for traceability
*/

-- Create staging schema
CREATE SCHEMA IF NOT EXISTS staging;

-- Staging table for Retrosheet events (from chadwick_event_raw)
CREATE TABLE IF NOT EXISTS staging.stg_retrosheet_events (
    -- Primary key and lineage
    staging_event_id bigserial PRIMARY KEY,
    source_row_id bigint NOT NULL REFERENCES raw_retrosheet.chadwick_event_raw(row_number),
    ingest_run_id bigint REFERENCES raw_retrosheet.ingest_runs(ingest_run_id),
    
    -- Source identification
    season integer NOT NULL,
    game_id varchar(12),
    event_id integer,
    source_type varchar(20),
    source_file varchar(255),
    
    -- Game state
    inning integer,
    batting_team varchar(3),
    outs integer,
    balls integer,
    strikes integer,
    pitch_sequence varchar(50),
    
    -- Runners
    runner_1b varchar(8),
    runner_2b varchar(8),
    runner_3b varchar(8),
    
    -- Event description
    event_type integer,
    event_description varchar(100),
    hit_location integer,
    
    -- Batted ball data
    batted_ball_type varchar(1),
    ab_flag boolean,
    sf_flag boolean,
    sh_flag boolean,
    
    -- Pitcher/Batter
    pitcher_id varchar(8),
    pitcher_hand varchar(1),
    batter_id varchar(8),
    batter_hand varchar(1),
    
    -- Fielding
    pos_1 varchar(8),
    pos_2 varchar(8),
    pos_3 varchar(8),
    pos_4 varchar(8),
    pos_5 varchar(8),
    pos_6 varchar(8),
    pos_7 varchar(8),
    pos_8 varchar(8),
    pos_9 varchar(8),
    
    -- Scoring
    runs_scored integer DEFAULT 0,
    rbi integer DEFAULT 0,
    
    -- Validation and metadata
    is_valid boolean DEFAULT true,
    validation_errors text[],
    loaded_at timestamptz NOT NULL DEFAULT NOW(),
    
    UNIQUE(season, game_id, event_id)
);

COMMENT ON TABLE staging.stg_retrosheet_events IS 'Cleaned and typed Retrosheet event data from chadwick_event_raw';

-- Staging table for games
CREATE TABLE IF NOT EXISTS staging.stg_retrosheet_games (
    staging_game_id bigserial PRIMARY KEY,
    season integer NOT NULL,
    game_id varchar(12) NOT NULL UNIQUE,
    
    -- Game info
    game_date date,
    game_type varchar(1),
    day_of_week varchar(3),
    start_time varchar(4),
    dh_flag boolean,
    
    -- Teams
    home_team_id varchar(3),
    away_team_id varchar(3),
    home_team_league varchar(2),
    away_team_league varchar(2),
    
    -- Managers
    home_manager_id varchar(8),
    away_manager_id varchar(8),
    
    -- Score
    home_score integer,
    away_score integer,
    
    -- Game length
    num_innings integer,
    
    -- Venue
    park_id varchar(5),
    attendance integer,
    duration_minutes integer,
    
    -- Umpires
    umpire_home_id varchar(8),
    umpire_1b_id varchar(8),
    umpire_2b_id varchar(8),
    umpire_3b_id varchar(8),
    umpire_lf_id varchar(8),
    umpire_rf_id varchar(8),
    
    -- Validation
    is_valid boolean DEFAULT true,
    validation_errors text[],
    
    -- Lineage
    source_file varchar(255),
    loaded_at timestamptz NOT NULL DEFAULT NOW(),
    ingest_run_id bigint REFERENCES raw_retrosheet.ingest_runs(ingest_run_id)
);

COMMENT ON TABLE staging.stg_retrosheet_games IS 'Game-level data from Retrosheet game info files';

-- Staging table for player appearances
CREATE TABLE IF NOT EXISTS staging.stg_retrosheet_player_appearances (
    staging_appearance_id bigserial PRIMARY KEY,
    season integer NOT NULL,
    game_id varchar(12) NOT NULL,
    player_id varchar(8) NOT NULL,
    team_id varchar(3),
    
    -- Role
    is_home_team boolean,
    batting_order integer,
    field_position integer,
    
    -- Counts (populated during transformation)
    pa_count integer DEFAULT 0,
    ab_count integer DEFAULT 0,
    
    -- Lineage
    source_file varchar(255),
    loaded_at timestamptz NOT NULL DEFAULT NOW(),
    
    UNIQUE(season, game_id, player_id)
);

COMMENT ON TABLE staging.stg_retrosheet_player_appearances IS 'Player-game appearances extracted from roster files';

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_stg_events_game_id ON staging.stg_retrosheet_events(game_id);
CREATE INDEX IF NOT EXISTS idx_stg_events_season ON staging.stg_retrosheet_events(season);
CREATE INDEX IF NOT EXISTS idx_stg_events_batter ON staging.stg_retrosheet_events(batter_id);
CREATE INDEX IF NOT EXISTS idx_stg_events_pitcher ON staging.stg_retrosheet_events(pitcher_id);
CREATE INDEX IF NOT EXISTS idx_stg_games_date ON staging.stg_retrosheet_games(game_date);
CREATE INDEX IF NOT EXISTS idx_stg_games_season ON staging.stg_retrosheet_games(season);
