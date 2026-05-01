/*
File: sql/30_core/312_core_live_plate_appearances.sql
Purpose: Canonical live plate appearances table for win probability modeling
Author: Agent Cascade
Date: 2026-04-29
Depends On: sql/30_core/310_core_live_games.sql, sql/20_staging/221_stg_mlb_live_events.sql
Called By: baseball/sources/mlb.py ingest pipeline, ML training scripts

Table: core.live_plate_appearances
- Plate appearance-level data extracted from live feed
- Combined grain: one row per plate appearance with full context
- Designed for win probability model training and inference
- Links to bridge tables for canonical player IDs

Notes:
- Combines functionality from milestone spec's 323/324 (duplicate entries)
- Grain: One row per plate appearance per game
- Includes pre-PA state (for prediction) and post-PA result (for training)
- All fields preserved from staging (no field reduction)
*/

-- Live plate appearances table
CREATE TABLE IF NOT EXISTS core.live_plate_appearances (
    live_pa_id bigserial PRIMARY KEY,
    
    -- Game linkage
    game_pk integer NOT NULL,
    snapshot_id bigint REFERENCES raw_mlb.live_feed_snapshots(snapshot_id),
    
    -- PA identification
    pa_number integer NOT NULL,              -- Sequence number within game
    pa_timestamp timestamptz,
    
    -- Pre-PA game state (for prediction input)
    inning smallint NOT NULL,
    is_top_inning boolean NOT NULL,
    outs smallint NOT NULL,
    balls smallint,
    strikes smallint,
    
    -- Base state
    runner_on_first boolean DEFAULT FALSE,
    runner_on_second boolean DEFAULT FALSE,
    runner_on_third boolean DEFAULT FALSE,
    bases_occupied varchar(3),              -- '000', '100', '111', etc.
    
    -- Score state
    home_score integer DEFAULT 0,
    away_score integer DEFAULT 0,
    score_differential integer GENERATED ALWAYS AS (home_score - away_score) STORED,
    
    -- Matchup (canonical IDs from bridge)
    batter_id varchar(20),                  -- Retrosheet ID
    batter_mlb_id integer,                 -- Original MLB ID
    batter_name varchar(100),
    batter_hand char(1),                    -- 'L', 'R', 'S'
    
    pitcher_id varchar(20),                 -- Retrosheet ID
    pitcher_mlb_id integer,                -- Original MLB ID
    pitcher_name varchar(100),
    pitcher_hand char(1),                   -- 'L', 'R', 'S'
    
    -- On-deck (for prediction features)
    on_deck_batter_id varchar(20),
    on_deck_batter_mlb_id integer,
    in_hole_batter_id varchar(20),
    in_hole_batter_mlb_id integer,
    
    -- Count and situation
    count varchar(10),                      -- '3-2', '0-1', etc.
    
    -- Post-PA result (for training labels)
    pa_result varchar(50),                  -- 'Single', 'Home Run', 'Walk', etc.
    pa_result_code varchar(10),             -- '1B', 'HR', 'BB', 'K', etc.
    is_hit boolean GENERATED ALWAYS AS (pa_result_code IN ('1B', '2B', '3B', 'HR')) STORED,
    is_walk boolean GENERATED ALWAYS AS (pa_result_code IN ('BB', 'HBP', 'I')) STORED,
    is_strikeout boolean GENERATED ALWAYS AS (pa_result_code = 'K') STORED,
    is_out boolean GENERATED ALWAYS AS (pa_result_code IN ('K', 'FO', 'GO', 'PO', 'FC', 'DP', 'TP')) STORED,
    
    -- Batted ball data (if applicable)
    exit_velocity decimal(5,2),             -- Statcast exit velocity (mph)
    launch_angle decimal(5,2),              -- Statcast launch angle (degrees)
    hit_distance integer,                   -- Estimated hit distance (feet)
    hit_location smallint,                  -- 1-9 fielding position
    batted_ball_type varchar(10),           -- 'GB', 'FB', 'LD', 'PU'
    
    -- Run expectancy context
    re24_state varchar(10),                 -- Runners-outs state (e.g., '1_2_3_2')
    re24_value decimal(6,4),                -- Change in run expectancy
    win_exp_before decimal(5,4),            -- Win probability before PA
    win_exp_after decimal(5,4),             -- Win probability after PA
    win_exp_delta decimal(5,4) GENERATED ALWAYS AS (win_exp_after - win_exp_before) STORED,
    
    -- Inning/win probability context
    inning_half varchar(10),                -- 'top_1', 'bot_9', etc.
    leverage_index decimal(4,2),            -- Current leverage index
    
    -- Team context
    home_team_id varchar(10),
    away_team_id varchar(10),
    batting_team_id varchar(10),
    
    -- Extracted metadata
    extracted_at timestamptz NOT NULL DEFAULT NOW(),
    
    -- Unique constraint per game/PA
    UNIQUE(game_pk, pa_number)
);

COMMENT ON TABLE core.live_plate_appearances IS 
    'Canonical live plate appearances with pre-PA state for prediction and post-PA result for training';

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_live_pa_game ON core.live_plate_appearances(game_pk);
CREATE INDEX IF NOT EXISTS idx_live_pa_snapshot ON core.live_plate_appearances(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_live_pa_batter ON core.live_plate_appearances(batter_id) WHERE batter_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_live_pa_pitcher ON core.live_plate_appearances(pitcher_id) WHERE pitcher_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_live_pa_extracted ON core.live_plate_appearances(extracted_at DESC);

-- Composite index for model training queries
CREATE INDEX IF NOT EXISTS idx_live_pa_features ON core.live_plate_appearances(
    inning, is_top_inning, outs, bases_occupied, score_differential, batter_id, pitcher_id
);

-- Index for win probability analysis
CREATE INDEX IF NOT EXISTS idx_live_pa_win_exp ON core.live_plate_appearances(
    win_exp_before, win_exp_after, win_exp_delta
) WHERE win_exp_before IS NOT NULL;

-- View: Latest PAs per game (current state)
CREATE OR REPLACE VIEW core.v_live_plate_appearances_current AS
WITH latest_snapshot AS (
    SELECT DISTINCT ON (game_pk)
        game_pk,
        snapshot_id,
        extracted_at
    FROM core.live_games
    ORDER BY game_pk, extracted_at DESC
)
SELECT 
    lpa.*,
    lg.status_code as game_status,
    lg.status_description as game_status_desc
FROM core.live_plate_appearances lpa
JOIN latest_snapshot ls ON lpa.snapshot_id = ls.snapshot_id
JOIN core.v_live_games_current lg ON lpa.game_pk = lg.game_pk;

COMMENT ON VIEW core.v_live_plate_appearances_current IS 
    'Latest plate appearances from most recent snapshot per game';

-- View: Training-ready PA data with all features
CREATE OR REPLACE VIEW core.v_live_pa_training AS
SELECT 
    live_pa_id,
    game_pk,
    pa_number,
    inning,
    is_top_inning,
    outs,
    balls,
    strikes,
    bases_occupied,
    runner_on_first,
    runner_on_second,
    runner_on_third,
    home_score,
    away_score,
    score_differential,
    batter_id,
    batter_hand,
    pitcher_id,
    pitcher_hand,
    on_deck_batter_id,
    in_hole_batter_id,
    count,
    home_team_id,
    away_team_id,
    batting_team_id,
    win_exp_before,
    win_exp_after,
    win_exp_delta,
    pa_result,
    pa_result_code,
    is_hit,
    is_walk,
    is_strikeout,
    is_out,
    exit_velocity,
    launch_angle,
    hit_distance,
    hit_location,
    batted_ball_type,
    re24_value,
    leverage_index,
    extracted_at
FROM core.live_plate_appearances
WHERE win_exp_before IS NOT NULL
  AND win_exp_after IS NOT NULL
ORDER BY game_pk, pa_number;

COMMENT ON VIEW core.v_live_pa_training IS 
    'Training-ready plate appearance data with all features for win probability model';

-- Function to extract training examples from live PAs
CREATE OR REPLACE FUNCTION core.extract_live_pa_training_examples(
    p_season integer,
    p_game_date date DEFAULT NULL
)
RETURNS TABLE(
    live_pa_id bigint,
    game_pk integer,
    inning smallint,
    is_top_inning boolean,
    outs smallint,
    bases_occupied varchar,
    score_differential integer,
    home_team_id varchar,
    away_team_id varchar,
    batter_id varchar,
    pitcher_id varchar,
    win_exp_before decimal,
    win_exp_after decimal,
    win_exp_delta decimal,
    pa_result varchar,
    pa_result_code varchar
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        vpa.live_pa_id,
        vpa.game_pk,
        vpa.inning,
        vpa.is_top_inning,
        vpa.outs,
        vpa.bases_occupied,
        vpa.score_differential,
        vpa.home_team_id,
        vpa.away_team_id,
        vpa.batter_id,
        vpa.pitcher_id,
        vpa.win_exp_before,
        vpa.win_exp_after,
        vpa.win_exp_delta,
        vpa.pa_result,
        vpa.pa_result_code
    FROM core.v_live_pa_training vpa
    JOIN core.live_games lg ON vpa.game_pk = lg.game_pk
    WHERE lg.season = p_season
      AND (p_game_date IS NULL OR vpa.extracted_at::date = p_game_date);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION core.extract_live_pa_training_examples IS 
    'Extract win probability training examples from live plate appearances for a season';
