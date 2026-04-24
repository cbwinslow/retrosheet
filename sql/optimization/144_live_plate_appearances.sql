-- File: sql/optimization/144_live_plate_appearances.sql
-- Purpose: Live plate appearances table with indexes for MLB data
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE TABLE IF NOT EXISTS core.live_plate_appearances (
    game_id text NOT NULL,
    plate_appearance_id integer NOT NULL,
    game_pa_number integer NOT NULL,
    half_inning_pa_number integer NOT NULL,
    season integer NOT NULL,
    game_date date NOT NULL,
    source_type text NOT NULL DEFAULT 'mlb_live',
    event_sequence integer NOT NULL,
    inning integer NOT NULL,
    is_bottom_inning boolean NOT NULL,
    outs_before integer NOT NULL,
    balls integer,
    strikes integer,
    start_bases integer,
    end_bases integer,
    away_score_before integer NOT NULL,
    home_score_before integer NOT NULL,
    away_score_after integer,
    home_score_after integer,
    home_team_id text,
    away_team_id text,
    batting_team_id text,
    fielding_team_id text,
    batter_id text,
    batter_hand text,
    pitcher_id text,
    pitcher_hand text,
    event_code integer,
    event_text text,
    is_at_bat boolean,
    hit_value integer DEFAULT 0,
    is_hit boolean DEFAULT false,
    is_walk boolean DEFAULT false,
    is_strikeout boolean DEFAULT false,
    is_home_run boolean DEFAULT false,
    is_hit_by_pitch boolean DEFAULT false,
    is_interference boolean DEFAULT false,
    is_reach_base boolean,
    outs_on_play integer DEFAULT 0,
    runs_on_play integer DEFAULT 0,
    rbi integer DEFAULT 0,
    is_new_pa boolean DEFAULT true,
    pa_index integer,
    batter_is_starter boolean,
    pitcher_is_starter boolean,
    park_id text,
    park_name text,
    temperature_f integer,
    wind_speed_mph integer,
    wind_direction text,
    precipitation text,
    sky_condition text,
    game_pa_count integer,
    inning_pa_count integer,
    is_inning_start boolean DEFAULT false,
    is_inning_end boolean DEFAULT false,
    is_game_end boolean DEFAULT false,
    mlb_game_pk integer,
    snapshot_id integer,
    snapshot_fetched_at timestamptz,
    raw_play jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (game_id, plate_appearance_id)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS live_pa_game_id_idx ON core.live_plate_appearances (game_id);
CREATE INDEX IF NOT EXISTS live_pa_season_idx ON core.live_plate_appearances (season);
CREATE INDEX IF NOT EXISTS live_pa_batter_idx ON core.live_plate_appearances (batter_id);
CREATE INDEX IF NOT EXISTS live_pa_pitcher_idx ON core.live_plate_appearances (pitcher_id);
CREATE INDEX IF NOT EXISTS live_pa_game_pa_idx ON core.live_plate_appearances (game_id, game_pa_number);
CREATE INDEX IF NOT EXISTS live_pa_season_batter_idx ON core.live_plate_appearances (season, batter_id);
CREATE INDEX IF NOT EXISTS live_pa_season_pitcher_idx ON core.live_plate_appearances (season, pitcher_id);
CREATE INDEX IF NOT EXISTS live_pa_mlb_game_pk_idx ON core.live_plate_appearances (mlb_game_pk);
CREATE INDEX IF NOT EXISTS live_pa_snapshot_idx ON core.live_plate_appearances (snapshot_id);

-- Add comments
COMMENT ON TABLE core.live_plate_appearances IS 'Live MLB plate appearances transformed to match core.plate_appearances schema';
COMMENT ON COLUMN core.live_plate_appearances.plate_appearance_id IS 'Sequential PA ID within the game (matches event_id from live_events)';
COMMENT ON COLUMN core.live_plate_appearances.game_pa_number IS 'Sequential PA number within the entire game';
COMMENT ON COLUMN core.live_plate_appearances.half_inning_pa_number IS 'Sequential PA number within the half-inning';

