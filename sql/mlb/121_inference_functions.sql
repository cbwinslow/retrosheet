-- File: sql/mlb/121_inference_functions.sql
-- Purpose: Functions for model inference and prediction scoring
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE TYPE inference.game_state AS (
    inning integer,
    is_bottom_inning boolean,
    outs_before integer,
    start_bases integer,
    balls integer,
    strikes integer,
    home_score_diff integer,
    batter_hand text,
    pitcher_hand text,
    batter_prior_pa integer,
    batter_prior_hit_rate numeric,
    batter_prior_walk_rate numeric,
    batter_prior_strikeout_rate numeric,
    pitcher_prior_batters_faced integer,
    pitcher_prior_hit_allowed_rate numeric,
    pitcher_prior_walk_allowed_rate numeric,
    pitcher_prior_strikeout_rate numeric,
    batting_team_prior_win_rate numeric,
    fielding_team_prior_win_rate numeric
);

-- Function to get pre-computed features for a game state
CREATE OR REPLACE FUNCTION inference.get_plate_appearance_features(
    p_season integer,
    p_inning integer,
    p_is_bottom_inning boolean,
    p_outs_before integer,
    p_start_bases integer,
    p_balls integer,
    p_strikes integer,
    p_home_score_diff integer,
    p_batter_hand text DEFAULT 'R',
    p_pitcher_hand text DEFAULT 'R',
    p_batter_id text DEFAULT NULL,
    p_pitcher_id text DEFAULT NULL,
    p_batting_team_id text DEFAULT NULL,
    p_fielding_team_id text DEFAULT NULL
) RETURNS TABLE (
    batter_prior_pa integer,
    batter_prior_hit_rate numeric,
    batter_prior_walk_rate numeric,
    batter_prior_strikeout_rate numeric,
    batter_prior_home_run_rate numeric,
    batter_prior_reach_base_rate numeric,
    batter_prior_extra_base_hit_rate numeric,
    pitcher_prior_batters_faced integer,
    pitcher_prior_hit_allowed_rate numeric,
    pitcher_prior_walk_allowed_rate numeric,
    pitcher_prior_strikeout_rate numeric,
    pitcher_prior_home_run_allowed_rate numeric,
    pitcher_prior_reach_base_allowed_rate numeric,
    pitcher_prior_extra_base_hit_allowed_rate numeric,
    batting_team_prior_win_rate numeric,
    batting_team_prior_runs_scored_per_game numeric,
    batting_team_prior_runs_allowed_per_game numeric,
    fielding_team_prior_win_rate numeric,
    fielding_team_prior_runs_scored_per_game numeric,
    fielding_team_prior_runs_allowed_per_game numeric,
    context_prior_pa integer,
    context_prior_hit_rate numeric,
    context_prior_walk_rate numeric,
    context_prior_strikeout_rate numeric,
    context_prior_home_run_rate numeric,
    context_prior_reach_base_rate numeric,
    context_prior_extra_base_hit_rate numeric,
    context_prior_batting_team_win_rate numeric
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        -- Batter stats with defaults
        COALESCE(batter.prior_pa, 0)::integer,
        COALESCE(batter.prior_hit_rate, 0.25)::numeric,
        COALESCE(batter.prior_walk_rate, 0.08)::numeric,
        COALESCE(batter.prior_strikeout_rate, 0.20)::numeric,
        COALESCE(batter.prior_home_run_rate, 0.03)::numeric,
        COALESCE(batter.prior_reach_base_rate, 0.32)::numeric,
        COALESCE(batter.prior_extra_base_hit_rate, 0.07)::numeric,

        -- Pitcher stats with defaults
        COALESCE(pitcher.prior_batters_faced, 0)::integer,
        COALESCE(pitcher.prior_hit_allowed_rate, 0.25)::numeric,
        COALESCE(pitcher.prior_walk_allowed_rate, 0.08)::numeric,
        COALESCE(pitcher.prior_strikeout_rate, 0.20)::numeric,
        COALESCE(pitcher.prior_home_run_allowed_rate, 0.03)::numeric,
        COALESCE(pitcher.prior_reach_base_allowed_rate, 0.32)::numeric,
        COALESCE(pitcher.prior_extra_base_hit_allowed_rate, 0.07)::numeric,

        -- Batting team stats with defaults
        COALESCE(batting_team.prior_win_rate, 0.5)::numeric,
        COALESCE(batting_team.prior_runs_scored_per_game, 4.5)::numeric,
        COALESCE(batting_team.prior_runs_allowed_per_game, 4.5)::numeric,

        -- Fielding team stats with defaults
        COALESCE(fielding_team.prior_win_rate, 0.5)::numeric,
        COALESCE(fielding_team.prior_runs_scored_per_game, 4.5)::numeric,
        COALESCE(fielding_team.prior_runs_allowed_per_game, 4.5)::numeric,

        -- Context stats with defaults
        COALESCE(context.prior_pa, 0)::integer,
        COALESCE(context.prior_hit_rate, 0.25)::numeric,
        COALESCE(context.prior_walk_rate, 0.08)::numeric,
        COALESCE(context.prior_strikeout_rate, 0.20)::numeric,
        COALESCE(context.prior_home_run_rate, 0.03)::numeric,
        COALESCE(context.prior_reach_base_rate, 0.32)::numeric,
        COALESCE(context.prior_extra_base_hit_rate, 0.07)::numeric,
        COALESCE(context.prior_batting_team_win_rate, 0.5)::numeric

    FROM (SELECT 1 as dummy) base
    LEFT JOIN features.batter_prior_season_pa_summary batter
      ON batter.feature_season = p_season AND batter.batter_id = p_batter_id
    LEFT JOIN features.pitcher_prior_season_pa_summary pitcher
      ON pitcher.feature_season = p_season AND pitcher.pitcher_id = p_pitcher_id
    LEFT JOIN features.team_prior_season_summary batting_team
      ON batting_team.feature_season = p_season AND batting_team.team_id = p_batting_team_id
    LEFT JOIN features.team_prior_season_summary fielding_team
      ON fielding_team.feature_season = p_season AND fielding_team.team_id = p_fielding_team_id
    LEFT JOIN features.pa_context_prior_season_rates context
      ON context.feature_season = p_season
      AND context.batter_hand = COALESCE(p_batter_hand, 'R')
      AND context.pitcher_hand = COALESCE(p_pitcher_hand, 'R')
      AND context.inning = p_inning
      AND context.is_bottom_inning = p_is_bottom_inning
      AND context.outs_before = p_outs_before
      AND context.start_bases = p_start_bases
      AND context.balls = p_balls
      AND context.strikes = p_strikes;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function for fast batch predictions (returns probabilities for all targets)
CREATE OR REPLACE FUNCTION inference.predict_plate_appearance_batch(
    p_season integer,
    p_inning integer,
    p_is_bottom_inning boolean,
    p_outs_before integer,
    p_start_bases integer,
    p_balls integer,
    p_strikes integer,
    p_home_score_diff integer,
    p_batter_hand text DEFAULT 'R',
    p_pitcher_hand text DEFAULT 'R',
    p_batter_id text DEFAULT NULL,
    p_pitcher_id text DEFAULT NULL,
    p_batting_team_id text DEFAULT NULL,
    p_fielding_team_id text DEFAULT NULL
) RETURNS TABLE (
    target_id text,
    probability numeric
) AS $$
BEGIN
    -- This would interface with Python models, but for now return mock data
    -- In production, this would call out to the Python prediction service
    RETURN QUERY VALUES
        ('pa_batter_hit', 0.250::numeric),
        ('pa_batter_walk', 0.080::numeric),
        ('pa_batter_strikeout', 0.200::numeric),
        ('pa_batter_home_run', 0.030::numeric),
        ('pa_batter_reach_base', 0.320::numeric),
        ('pa_batter_extra_base_hit', 0.070::numeric);
END;
$$ LANGUAGE plpgsql STABLE;

-- Simulation state table for maintaining simulation state in database
CREATE TABLE inference.simulation_states (
    simulation_id text PRIMARY KEY,
    game_id text,
    season integer,
    inning integer,
    is_bottom_inning boolean,
    outs integer,
    bases integer,
    balls integer,
    strikes integer,
    home_score integer,
    away_score integer,
    batter_id text,
    pitcher_id text,
    batter_hand text,
    pitcher_hand text,
    batting_team_id text,
    fielding_team_id text,
    plate_appearances_completed integer DEFAULT 0,
    runs_scored integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

CREATE INDEX simulation_states_game_idx ON inference.simulation_states (game_id);
CREATE INDEX simulation_states_active_idx ON inference.simulation_states (created_at DESC);

-- Function to initialize simulation state
CREATE OR REPLACE FUNCTION inference.init_simulation(
    p_simulation_id text,
    p_game_id text,
    p_season integer,
    p_inning integer DEFAULT 1,
    p_is_bottom_inning boolean DEFAULT FALSE,
    p_batter_id text DEFAULT NULL,
    p_pitcher_id text DEFAULT NULL,
    p_batter_hand text DEFAULT 'R',
    p_pitcher_hand text DEFAULT 'R',
    p_batting_team_id text DEFAULT NULL,
    p_fielding_team_id text DEFAULT NULL
) RETURNS void AS $$
BEGIN
    INSERT INTO inference.simulation_states (
        simulation_id, game_id, season, inning, is_bottom_inning,
        outs, bases, balls, strikes, home_score, away_score,
        batter_id, pitcher_id, batter_hand, pitcher_hand,
        batting_team_id, fielding_team_id
    ) VALUES (
        p_simulation_id, p_game_id, p_season, p_inning, p_is_bottom_inning,
        0, 0, 0, 0, 0, 0,
        p_batter_id, p_pitcher_id, p_batter_hand, p_pitcher_hand,
        p_batting_team_id, p_fielding_team_id
    )
    ON CONFLICT (simulation_id) DO UPDATE SET
        outs = 0, bases = 0, balls = 0, strikes = 0,
        home_score = 0, away_score = 0,
        plate_appearances_completed = 0, runs_scored = 0,
        updated_at = now();
END;
$$ LANGUAGE plpgsql;

-- Function to get current simulation state
CREATE OR REPLACE FUNCTION inference.get_simulation_state(p_simulation_id text)
RETURNS TABLE (
    simulation_id text,
    game_id text,
    season integer,
    inning integer,
    is_bottom_inning boolean,
    outs integer,
    bases integer,
    balls integer,
    strikes integer,
    home_score integer,
    away_score integer,
    batter_id text,
    pitcher_id text,
    batter_hand text,
    pitcher_hand text,
    batting_team_id text,
    fielding_team_id text,
    plate_appearances_completed integer,
    runs_scored integer
) AS $$
BEGIN
    RETURN QUERY SELECT
        s.simulation_id, s.game_id, s.season, s.inning, s.is_bottom_inning,
        s.outs, s.bases, s.balls, s.strikes, s.home_score, s.away_score,
        s.batter_id, s.pitcher_id, s.batter_hand, s.pitcher_hand,
        s.batting_team_id, s.fielding_team_id,
        s.plate_appearances_completed, s.runs_scored
    FROM inference.simulation_states s
    WHERE s.simulation_id = p_simulation_id;
END;
$$ LANGUAGE plpgsql STABLE;

-- Table comments
COMMENT ON TABLE inference.simulation_states IS 'simulation states data table';
