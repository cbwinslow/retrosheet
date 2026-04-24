-- File: sql/mlb/145_mlb_historical_schema.sql
-- Purpose: MLB historical data tables complementing Retrosheet
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS mlb;

-- MLB Games (comprehensive game metadata)
CREATE TABLE mlb.games (
    game_pk integer PRIMARY KEY,
    game_date date NOT NULL,
    season integer NOT NULL,
    game_type text,  -- R=Regular, P=Postseason, etc.
    game_number integer,
    day_night text,
    scheduled_innings integer DEFAULT 9,

    -- Teams
    home_team_id integer NOT NULL,
    away_team_id integer NOT NULL,
    home_team_name text,
    away_team_name text,

    -- Venue
    venue_id integer,
    venue_name text,
    field_condition text,
    precipitation text,
    sky_condition text,
    temperature_f integer,
    wind_speed_mph integer,
    wind_direction integer,

    -- Game status
    status_code text,
    status_description text,
    status_abstract text,  -- Live, Final, Scheduled, etc.
    status_detailed text,

    -- Officials
    home_plate_umpire_id integer,
    first_base_umpire_id integer,
    second_base_umpire_id integer,
    third_base_umpire_id integer,

    -- Game results
    home_score integer DEFAULT 0,
    away_score integer DEFAULT 0,
    home_hits integer,
    away_hits integer,
    home_errors integer,
    away_errors integer,
    home_lob integer,
    away_lob integer,
    winning_team_id integer,
    losing_team_id integer,

    -- Timing
    game_start_time timestamptz,
    game_end_time timestamptz,
    game_duration_minutes integer,

    -- Metadata
    api_source text DEFAULT 'mlb_api',
    data_quality_score numeric(3, 2),  -- 0.0 to 1.0
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now(),

    -- Constraints
    CHECK (home_score >= 0),
    CHECK (away_score >= 0),
    CHECK (season >= 2000),
    CHECK (data_quality_score >= 0.0 AND data_quality_score <= 1.0)
);

-- MLB Play Events (play-by-play data)
CREATE TABLE mlb.play_events (
    game_pk integer NOT NULL,
    event_index integer NOT NULL,
    event_type text,  -- pitch, action, pickoff, etc.
    event_description text,
    inning integer NOT NULL,
    is_top_inning boolean NOT NULL,

    -- Count before event
    balls_before integer DEFAULT 0,
    strikes_before integer DEFAULT 0,
    outs_before integer DEFAULT 0,

    -- Players involved
    batter_id integer,
    pitcher_id integer,
    on_deck_batter_id integer,
    in_hole_batter_id integer,

    -- Runners on base
    runner_on_1b_id integer,
    runner_on_2b_id integer,
    runner_on_3b_id integer,

    -- Event result
    event_code text,  -- MLB event code
    event_result text,  -- single, double, home_run, strikeout, etc.
    is_scoring_play boolean DEFAULT false,
    runs_batted_in integer DEFAULT 0,

    -- Game state after event
    balls_after integer,
    strikes_after integer,
    outs_after integer,

    -- Scoring
    home_score_after integer,
    away_score_after integer,

    -- Timing
    event_start_time timestamptz,
    event_end_time timestamptz,

    -- Metadata
    api_source text DEFAULT 'mlb_api',
    data_quality_score numeric(3, 2),
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now(),

    PRIMARY KEY (game_pk, event_index),
    FOREIGN KEY (game_pk) REFERENCES mlb.games (game_pk),

    -- Constraints
    CHECK (inning >= 1 AND inning <= 25),
    CHECK (balls_before >= 0 AND balls_before <= 3),
    CHECK (strikes_before >= 0 AND strikes_before <= 2),
    CHECK (outs_before >= 0 AND outs_before <= 2)
);

-- MLB Pitches (detailed pitch data)
CREATE TABLE mlb.pitches (
    game_pk integer NOT NULL,
    event_index integer NOT NULL,
    pitch_index integer NOT NULL,  -- Within the at-bat
    pitch_number integer NOT NULL, -- Within the game

    -- Pitch identification
    play_id text,  -- MLB play identifier
    pitch_uid text UNIQUE,  -- Unique pitch identifier

    -- Pitch type and result
    pitch_type_code text,  -- FF, SL, CU, etc.
    pitch_type_description text,
    pitch_type_confidence numeric(4, 3),

    -- Pitch result
    pitch_call_code text,  -- B, S, F, X, etc.
    pitch_call_description text,
    pitch_call_confidence numeric(4, 3),

    -- Pitch location (plate coordinates)
    plate_x numeric(6, 2),  -- Horizontal location (-2 to 2 ft)
    plate_z numeric(6, 2),  -- Vertical location (0 to 4 ft)
    plate_zone integer,    -- Strike zone zone (1-14)

    -- Pitch trajectory
    start_speed numeric(5, 1),  -- Initial velocity (mph)
    end_speed numeric(5, 1),    -- Final velocity (mph)
    extension numeric(5, 3),    -- Release extension (ft)

    -- Pitch physics
    spin_rate integer,         -- RPM
    spin_direction integer,    -- Degrees
    break_angle numeric(4, 1),  -- Degrees
    break_length numeric(4, 1), -- Feet
    break_vertical numeric(5, 1), -- Inches
    break_horizontal numeric(5, 1), -- Inches
    pfx_x numeric(5, 2),        -- Horizontal movement (ft)
    pfx_z numeric(5, 2),        -- Vertical movement (ft)

    -- Pitch timing
    plate_time numeric(6, 4),   -- Time to plate (seconds)
    reaction_time numeric(6, 4), -- Batter reaction time

    -- Contextual data
    batter_id integer,
    pitcher_id integer,
    balls_before integer,
    strikes_before integer,
    outs_before integer,
    inning integer,
    is_top_inning boolean,

    -- Game situation
    runner_on_1b boolean DEFAULT false,
    runner_on_2b boolean DEFAULT false,
    runner_on_3b boolean DEFAULT false,
    home_score integer,
    away_score integer,

    -- Metadata
    api_source text DEFAULT 'mlb_api',
    data_quality_score numeric(3, 2),
    pitch_system text DEFAULT 'statcast',  -- statcast, pitchfx, etc.
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now(),

    PRIMARY KEY (game_pk, event_index, pitch_index),
    FOREIGN KEY (game_pk) REFERENCES mlb.games (game_pk),
    FOREIGN KEY (game_pk, event_index) REFERENCES mlb.play_events (game_pk, event_index)
);

-- MLB Players (comprehensive player data)
CREATE TABLE mlb.players (
    mlb_id integer PRIMARY KEY,
    retrosheet_id text,  -- Link to our bridge table

    -- Biographical
    full_name text NOT NULL,
    first_name text,
    last_name text,
    primary_number text,
    birth_date date,
    birth_city text,
    birth_state_province text,
    birth_country text,
    height text,  -- "6' 2\""
    weight integer,  -- lbs

    -- Physical attributes
    bat_side text,  -- L, R, S
    pitch_hand text,  -- L, R

    -- MLB career
    mlb_debut_date date,
    last_game_date date,
    active boolean DEFAULT true,

    -- Current status
    current_team_id integer,
    position_code text,
    position_name text,
    position_type text,

    -- Advanced metrics (when available)
    bat_speed numeric(6, 1),     -- mph
    swing_speed numeric(6, 1),   -- mph
    sprint_speed numeric(5, 2),  -- seconds for 60ft
    arm_strength text,          -- above/below average

    -- Metadata
    api_source text DEFAULT 'mlb_api',
    data_quality_score numeric(3, 2),
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now(),

    FOREIGN KEY (current_team_id) REFERENCES mlb.teams (mlb_id)
);

-- MLB Teams (must be created before players that reference it)
CREATE TABLE mlb.teams (
    mlb_id integer PRIMARY KEY,
    retrosheet_id text,

    team_name text NOT NULL,
    team_code text,  -- BOS, NYY, etc.
    location_name text,
    league_id integer,
    league_name text,
    division_id integer,
    division_name text,

    venue_id integer,
    venue_name text,

    active boolean DEFAULT true,
    first_year integer,
    last_year integer,

    api_source text DEFAULT 'mlb_api',
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now()
);

-- MLB Venues
CREATE TABLE mlb.venues (
    mlb_id integer PRIMARY KEY,
    retrosheet_id text,

    name text NOT NULL,
    location text,
    time_zone text,

    -- Field dimensions (when available)
    left_field_distance integer,
    center_field_distance integer,
    right_field_distance integer,
    left_center_distance integer,
    right_center_distance integer,

    -- Field surface
    turf_type text,
    roof_type text,

    active boolean DEFAULT true,
    api_source text DEFAULT 'mlb_api',
    last_updated timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now()
);

-- Raw data storage tables (for bulk ingestion)
CREATE TABLE raw_mlb.schedule_snapshots (
    snapshot_id bigserial PRIMARY KEY,
    snapshot_date date NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    endpoint text NOT NULL,
    payload jsonb NOT NULL,
    request_params jsonb,
    http_status integer,
    response_time_ms integer,
    error_text text,
    UNIQUE (snapshot_date, fetched_at)
);

-- Indexes for raw data tables
CREATE INDEX schedule_snapshots_date_idx ON raw_mlb.schedule_snapshots (snapshot_date);
CREATE INDEX schedule_snapshots_fetched_at_idx ON raw_mlb.schedule_snapshots (fetched_at DESC);

-- Comments for documentation
COMMENT ON SCHEMA mlb IS 'MLB historical data from 2000-present, complementing Retrosheet data';
COMMENT ON TABLE mlb.games IS 'Comprehensive MLB game metadata and results';
COMMENT ON TABLE mlb.play_events IS 'Play-by-play events with detailed game state';
COMMENT ON TABLE mlb.pitches IS 'Individual pitch measurements with physics data';
COMMENT ON TABLE mlb.players IS 'MLB player biographical and performance data';
COMMENT ON TABLE mlb.teams IS 'MLB team information and organization';
COMMENT ON TABLE mlb.venues IS 'MLB ballpark information and dimensions';

