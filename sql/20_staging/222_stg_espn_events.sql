-- File: sql/20_staging/222_stg_espn_events.sql
-- Purpose: Staging table for flattened ESPN events with bridge ID resolution
-- Author: Agent cbwinslow/retrosheet
-- Date: 2026-04-29

-- ============================================================================
-- STAGING TABLE: stg_espn_events
-- ============================================================================
-- Flattened ESPN play-by-play events with all available fields preserved
-- Includes bridge ID resolution for canonical entity mapping
-- ============================================================================

CREATE TABLE IF NOT EXISTS staging.stg_espn_events (
    -- Primary identifiers
    stg_event_id BIGSERIAL PRIMARY KEY,
    espn_game_id TEXT NOT NULL,
    espn_event_id TEXT,
    espn_play_id TEXT,

    -- Event sequencing
    event_sequence INTEGER,
    period INTEGER,                    -- Inning
    period_number INTEGER,             -- Inning number
    clock JSONB,                       -- Pitch count, time remaining, etc.

    -- Team context
    espn_home_team_id TEXT,
    espn_away_team_id TEXT,
    espn_batting_team_id TEXT,
    espn_fielding_team_id TEXT,
    home_team_bridge_id TEXT,          -- Resolved via bridge.team_xref
    away_team_bridge_id TEXT,          -- Resolved via bridge.team_xref
    batting_team_bridge_id TEXT,       -- Resolved via bridge.team_xref

    -- Player context
    espn_batter_id TEXT,
    espn_pitcher_id TEXT,
    batter_bridge_id TEXT,             -- Resolved via bridge.external_player_xref
    pitcher_bridge_id TEXT,            -- Resolved via bridge.external_player_xref
    batter_hand TEXT,                   -- L/R/S
    pitcher_hand TEXT,                -- L/R/S

    -- Game state (count, bases, score)
    balls INTEGER DEFAULT 0,
    strikes INTEGER DEFAULT 0,
    outs INTEGER DEFAULT 0,
    base_state TEXT,                   -- 0-7 representing base occupancy
    start_base_state TEXT,             -- Base state at start of play
    end_base_state TEXT,               -- Base state at end of play
    home_score INTEGER DEFAULT 0,
    away_score INTEGER DEFAULT 0,
    score_diff INTEGER,                -- Home - Away
    batting_team_score INTEGER DEFAULT 0,
    fielding_team_score INTEGER DEFAULT 0,

    -- Play classification
    play_type TEXT,                    -- hit, out, walk, strikeout, etc.
    play_result TEXT,                  -- Detailed result description
    is_hit BOOLEAN DEFAULT FALSE,
    is_out BOOLEAN DEFAULT FALSE,
    is_walk BOOLEAN DEFAULT FALSE,
    is_strikeout BOOLEAN DEFAULT FALSE,
    is_home_run BOOLEAN DEFAULT FALSE,
    is_sacrifice BOOLEAN DEFAULT FALSE,
    is_double_play BOOLEAN DEFAULT FALSE,
    is_triple_play BOOLEAN DEFAULT FALSE,
    is_error BOOLEAN DEFAULT FALSE,
    hit_type TEXT,                     -- single, double, triple, home_run
    hit_location TEXT,                 -- Field location of hit
    trajectory TEXT,                   -- ground_ball, fly_ball, line_drive, popup
    exit_velocity NUMERIC,             -- Statcast exit velocity (if available)
    launch_angle NUMERIC,              -- Statcast launch angle (if available)
    hit_distance NUMERIC,              -- Hit distance in feet

    -- Runs and RBI
    runs_on_play INTEGER DEFAULT 0,
    rbi INTEGER DEFAULT 0,
    is_rbi BOOLEAN DEFAULT FALSE,

    -- Pitch information (if available in ESPN data)
    pitch_type TEXT,                   -- Fastball, Curveball, etc.
    pitch_speed NUMERIC,               -- Pitch velocity
    pitch_zone INTEGER,                -- Strike zone location
    is_pitch_in_zone BOOLEAN,
    pitch_result TEXT,                 -- ball, strike, foul, in_play

    -- Play description
    play_description TEXT,             -- Full text description
    short_description TEXT,            -- Abbreviated description
    alternative_description TEXT,      -- Alternative phrasing

    -- Flags
    is_scoring_play BOOLEAN DEFAULT FALSE,
    is_lead_change BOOLEAN DEFAULT FALSE,
    is_walkoff BOOLEAN DEFAULT FALSE,
    is_pinch_hit BOOLEAN DEFAULT FALSE,
    is_stolen_base BOOLEAN DEFAULT FALSE,
    is_caught_stealing BOOLEAN DEFAULT FALSE,
    is_pickoff BOOLEAN DEFAULT FALSE,
    is_wild_pitch BOOLEAN DEFAULT FALSE,
    is_passed_ball BOOLEAN DEFAULT FALSE,
    is_balk BOOLEAN DEFAULT FALSE,
    is_interference BOOLEAN DEFAULT FALSE,
    is_obstruction BOOLEAN DEFAULT FALSE,

    -- Participants (other than batter/pitcher)
    espn_fielder_id TEXT,              -- Primary fielder
    espn_assist_1_id TEXT,             -- First assist
    espn_assist_2_id TEXT,             -- Second assist
    espn_runner_1_id TEXT,             -- Runner on first
    espn_runner_2_id TEXT,             -- Runner on second
    espn_runner_3_id TEXT,             -- Runner on third

    -- Timing
    game_date DATE,
    game_time TIME,
    season INTEGER,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,

    -- Raw data preservation
    raw_espn_payload JSONB,
    source_snapshot_id BIGINT,         -- Reference to raw_espn.plays_snapshots

    -- Processing metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    bridge_resolution_status TEXT,     -- success, partial, failed
    bridge_resolution_errors TEXT[],     -- Any errors during bridge resolution

    -- Audit trail
    processed_by TEXT DEFAULT current_user,
    processing_batch_id TEXT,          -- For batch processing tracking

    CONSTRAINT stg_espn_events_unique UNIQUE (espn_game_id, espn_event_id, source_snapshot_id)
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_stg_espn_events_game ON staging.stg_espn_events (espn_game_id);
CREATE INDEX IF NOT EXISTS idx_stg_espn_events_event ON staging.stg_espn_events (espn_event_id);
CREATE INDEX IF NOT EXISTS idx_stg_espn_events_batter ON staging.stg_espn_events (espn_batter_id);
CREATE INDEX IF NOT EXISTS idx_stg_espn_events_pitcher ON staging.stg_espn_events (espn_pitcher_id);
CREATE INDEX IF NOT EXISTS idx_stg_espn_events_bridge_batter ON staging.stg_espn_events (batter_bridge_id);
CREATE INDEX IF NOT EXISTS idx_stg_espn_events_bridge_pitcher ON staging.stg_espn_events (pitcher_bridge_id);
CREATE INDEX IF NOT EXISTS idx_stg_espn_events_game_date ON staging.stg_espn_events (game_date);
CREATE INDEX IF NOT EXISTS idx_stg_espn_events_season ON staging.stg_espn_events (season);
CREATE INDEX IF NOT EXISTS idx_stg_espn_events_play_type ON staging.stg_espn_events (play_type);
CREATE INDEX IF NOT EXISTS idx_stg_espn_events_inning ON staging.stg_espn_events (period_number);
CREATE INDEX IF NOT EXISTS idx_stg_espn_events_snapshot ON staging.stg_espn_events (source_snapshot_id);

-- ============================================================================
-- STAGING TABLE: stg_espn_games
-- ============================================================================
-- Flattened ESPN game summary data with bridge ID resolution
-- ============================================================================

CREATE TABLE IF NOT EXISTS staging.stg_espn_games (
    stg_game_id BIGSERIAL PRIMARY KEY,

    -- ESPN identifiers
    espn_game_id TEXT NOT NULL UNIQUE,
    mlb_game_pk INTEGER,               -- MLB Stats API game PK if available

    -- Game context
    game_date DATE,
    game_time TIME,
    season INTEGER,
    game_number INTEGER,               -- 1 or 2 for doubleheaders
    is_doubleheader BOOLEAN DEFAULT FALSE,
    is_spring_training BOOLEAN DEFAULT FALSE,
    is_playoff BOOLEAN DEFAULT FALSE,
    playoff_round TEXT,                -- wild_card, division_series, etc.

    -- Teams
    espn_home_team_id TEXT,
    espn_away_team_id TEXT,
    home_team_name TEXT,
    away_team_name TEXT,
    home_team_bridge_id TEXT,
    away_team_bridge_id TEXT,

    -- Venue
    espn_venue_id TEXT,
    venue_name TEXT,
    venue_city TEXT,
    venue_state TEXT,
    venue_country TEXT,

    -- Scores
    home_score INTEGER DEFAULT 0,
    away_score INTEGER DEFAULT 0,
    home_hits INTEGER DEFAULT 0,
    away_hits INTEGER DEFAULT 0,
    home_errors INTEGER DEFAULT 0,
    away_errors INTEGER DEFAULT 0,
    home_innings JSONB,                -- Score by inning for home team
    away_innings JSONB,                -- Score by inning for away team

    -- Status
    game_status TEXT,                  -- scheduled, in_progress, final, postponed, cancelled
    status_detail TEXT,                -- Detailed status (rain delay, etc.)
    is_complete BOOLEAN DEFAULT FALSE,
    is_final BOOLEAN DEFAULT FALSE,
    current_inning INTEGER,
    is_top_inning BOOLEAN,
    current_outs INTEGER,
    current_balls INTEGER,
    current_strikes INTEGER,

    -- Attendance and conditions
    attendance INTEGER,
    temperature INTEGER,
    weather_condition TEXT,
    wind_speed TEXT,
    wind_direction TEXT,

    -- Officials
    espn_umpire_hp_id TEXT,            -- Home plate umpire
    espn_umpire_1b_id TEXT,            -- First base umpire
    espn_umpire_2b_id TEXT,            -- Second base umpire
    espn_umpire_3b_id TEXT,            -- Third base umpire
    home_plate_umpire_name TEXT,

    -- Winning/losing pitchers
    espn_winning_pitcher_id TEXT,
    espn_losing_pitcher_id TEXT,
    espn_save_pitcher_id TEXT,

    -- Raw data
    raw_espn_payload JSONB,
    source_snapshot_id BIGINT,

    -- Processing metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    bridge_resolution_status TEXT,
    processed_by TEXT DEFAULT current_user
);

-- ============================================================================
-- INDEXES for stg_espn_games
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_stg_espn_games_date ON staging.stg_espn_games (game_date);
CREATE INDEX IF NOT EXISTS idx_stg_espn_games_season ON staging.stg_espn_games (season);
CREATE INDEX IF NOT EXISTS idx_stg_espn_games_home_team ON staging.stg_espn_games (espn_home_team_id);
CREATE INDEX IF NOT EXISTS idx_stg_espn_games_away_team ON staging.stg_espn_games (espn_away_team_id);
CREATE INDEX IF NOT EXISTS idx_stg_espn_games_status ON staging.stg_espn_games (game_status);
CREATE INDEX IF NOT EXISTS idx_stg_espn_games_snapshot ON staging.stg_espn_games (source_snapshot_id);

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE staging.stg_espn_events IS 'Staging table for flattened ESPN play-by-play events with bridge ID resolution';
COMMENT ON TABLE staging.stg_espn_games IS 'Staging table for flattened ESPN game summaries with bridge ID resolution';
