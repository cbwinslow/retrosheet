/*
File: sql/30_core/313_core_live_pitch_events.sql
Purpose: Canonical live pitch events table for pitch-level analysis
Author: Agent Cascade
Date: 2026-04-29
Depends On: sql/30_core/312_core_live_plate_appearances.sql, sql/20_staging/221_stg_mlb_live_events.sql
Called By: baseball/sources/mlb.py ingest pipeline, pitch modeling scripts

Table: core.live_pitch_events
- Pitch-level data extracted from live feed
- Grain: One row per pitch within plate appearance
- Designed for pitch outcome modeling and analysis
- Links to live_plate_appearances for PA context

Notes:
- ALL pitch fields preserved from staging (no field reduction)
- Includes pitch-by-pitch sequence for PA reconstruction
- Supports pitch-level win probability and outcome modeling
*/

-- Live pitch events table
CREATE TABLE IF NOT EXISTS core.live_pitch_events (
    live_pitch_id bigserial PRIMARY KEY,
    
    -- Game linkage
    game_pk integer NOT NULL,
    snapshot_id bigint REFERENCES raw_mlb.live_feed_snapshots(snapshot_id),
    
    -- PA linkage
    live_pa_id bigint REFERENCES core.live_plate_appearances(live_pa_id),
    pa_number integer NOT NULL,              -- PA sequence number
    
    -- Pitch identification
    pitch_number smallint NOT NULL,          -- Pitch number within PA
    pitch_timestamp timestamptz,
    
    -- Pre-pitch game state
    inning smallint NOT NULL,
    is_top_inning boolean NOT NULL,
    outs smallint NOT NULL,
    balls smallint,
    strikes smallint,
    
    -- Base state
    runner_on_first boolean DEFAULT FALSE,
    runner_on_second boolean DEFAULT FALSE,
    runner_on_third boolean DEFAULT FALSE,
    bases_occupied varchar(3),
    
    -- Score state
    home_score integer DEFAULT 0,
    away_score integer DEFAULT 0,
    score_differential integer GENERATED ALWAYS AS (home_score - away_score) STORED,
    
    -- Matchup
    batter_id varchar(20),
    batter_mlb_id integer,
    batter_name varchar(100),
    batter_hand char(1),
    
    pitcher_id varchar(20),
    pitcher_mlb_id integer,
    pitcher_name varchar(100),
    pitcher_hand char(1),
    
    -- Pitch characteristics
    pitch_type varchar(10),                 -- 'FF', 'SL', 'CH', 'CU', 'KC', etc.
    pitch_type_description varchar(50),     -- 'Four-Seam Fastball', 'Slider', etc.
    pitch_speed decimal(4,1),               -- Release speed (mph)
    pitch_spin_rate decimal(5,1),           -- Spin rate (rpm)
    pitch_spin_axis decimal(5,1),           -- Spin axis (degrees)
    pitch_release_x decimal(5,2),           -- Release position X (feet)
    pitch_release_z decimal(5,2),           -- Release position Z (feet)
    pitch_extension decimal(4,2),          -- Extension (feet)
    
    -- Pitch result
    pitch_result varchar(50),               -- 'Ball', 'Called Strike', 'Swinging Strike', etc.
    pitch_result_code varchar(10),          -- 'B', 'C', 'S', 'F', 'X', etc.
    is_ball boolean GENERATED ALWAYS AS (pitch_result_code = 'B') STORED,
    is_strike boolean GENERATED ALWAYS AS (pitch_result_code IN ('C', 'S', 'F', 'X')) STORED,
    is_called_strike boolean GENERATED ALWAYS AS (pitch_result_code = 'C') STORED,
    is_swinging_strike boolean GENERATED ALWAYS AS (pitch_result_code = 'S') STORED,
    is_foul_ball boolean GENERATED ALWAYS AS (pitch_result_code = 'F') STORED,
    is_in_play boolean GENERATED ALWAYS AS (pitch_result_code = 'X') STORED,
    
    -- Zone location
    zone smallint,                          -- 1-9 strike zone (null = out of zone)
    plate_x decimal(5,2),                   -- Horizontal plate location
    plate_z decimal(5,2),                   -- Vertical plate location
    
    -- Batted ball data (if in play)
    exit_velocity decimal(5,2),             -- Exit velocity (mph)
    launch_angle decimal(5,2),              -- Launch angle (degrees)
    hit_distance integer,                   -- Hit distance (feet)
    hit_location smallint,                  -- 1-9 fielding position
    batted_ball_type varchar(10),           -- 'GB', 'FB', 'LD', 'PU'
    hang_time decimal(4,2),                 -- Hang time (seconds)
    
    -- Run expectancy context
    re24_state varchar(10),
    re24_value decimal(6,4),
    win_exp_before decimal(5,4),
    win_exp_after decimal(5,4),
    win_exp_delta decimal(5,4) GENERATED ALWAYS AS (win_exp_after - win_exp_before) STORED,
    
    -- Leverage
    leverage_index decimal(4,2),
    
    -- Team context
    home_team_id varchar(10),
    away_team_id varchar(10),
    batting_team_id varchar(10),
    
    -- Extracted metadata
    extracted_at timestamptz NOT NULL DEFAULT NOW(),
    
    -- Unique constraint per game/PA/pitch
    UNIQUE(game_pk, pa_number, pitch_number)
);

COMMENT ON TABLE core.live_pitch_events IS 
    'Canonical live pitch events with complete pitch characteristics and results';

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_live_pitch_game ON core.live_pitch_events(game_pk);
CREATE INDEX IF NOT EXISTS idx_live_pitch_snapshot ON core.live_pitch_events(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_live_pitch_pa ON core.live_pitch_events(live_pa_id);
CREATE INDEX IF NOT EXISTS idx_live_pitch_batter ON core.live_pitch_events(batter_id) WHERE batter_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_live_pitch_pitcher ON core.live_pitch_events(pitcher_id) WHERE pitcher_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_live_pitch_extracted ON core.live_pitch_events(extracted_at DESC);

-- Composite index for pitch sequence queries
CREATE INDEX IF NOT EXISTS idx_live_pitch_sequence ON core.live_pitch_events(
    game_pk, pa_number, pitch_number
);

-- Index for pitch type analysis
CREATE INDEX IF NOT EXISTS idx_live_pitch_type ON core.live_pitch_events(
    pitch_type, pitch_result_code
);

-- View: Latest pitches per game (current state)
CREATE OR REPLACE VIEW core.v_live_pitch_events_current AS
WITH latest_snapshot AS (
    SELECT DISTINCT ON (game_pk)
        game_pk,
        snapshot_id,
        extracted_at
    FROM core.live_games
    ORDER BY game_pk, extracted_at DESC
)
SELECT 
    lpe.*,
    lg.status_code as game_status
FROM core.live_pitch_events lpe
JOIN latest_snapshot ls ON lpe.snapshot_id = ls.snapshot_id
JOIN core.v_live_games_current lg ON lpe.game_pk = lg.game_pk;

COMMENT ON VIEW core.v_live_pitch_events_current IS 
    'Latest pitch events from most recent snapshot per game';

-- View: Pitch sequence within PA
CREATE OR REPLACE VIEW core.v_live_pitch_sequence AS
SELECT 
    lpe.*,
    LAG(lpe.pitch_result_code) OVER (PARTITION BY lpe.game_pk, lpe.pa_number ORDER BY lpe.pitch_number) as prev_pitch_result,
    LAG(lpe.pitch_type) OVER (PARTITION BY lpe.game_pk, lpe.pa_number ORDER BY lpe.pitch_number) as prev_pitch_type,
    SUM(CASE WHEN lpe.is_strike THEN 1 ELSE 0 END) OVER (PARTITION BY lpe.game_pk, lpe.pa_number ORDER BY lpe.pitch_number) as strike_count,
    SUM(CASE WHEN lpe.is_ball THEN 1 ELSE 0 END) OVER (PARTITION BY lpe.game_pk, lpe.pa_number ORDER BY lpe.pitch_number) as ball_count
FROM core.live_pitch_events lpe
ORDER BY lpe.game_pk, lpe.pa_number, lpe.pitch_number;

COMMENT ON VIEW core.v_live_pitch_sequence IS 
    'Pitch sequence with context for pitch-by-pitch analysis';

-- View: Training-ready pitch data
CREATE OR REPLACE VIEW core.v_live_pitch_training AS
SELECT 
    live_pitch_id,
    game_pk,
    pa_number,
    pitch_number,
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
    pitch_type,
    pitch_speed,
    pitch_spin_rate,
    pitch_result,
    pitch_result_code,
    is_ball,
    is_strike,
    is_called_strike,
    is_swinging_strike,
    is_foul_ball,
    is_in_play,
    zone,
    plate_x,
    plate_z,
    exit_velocity,
    launch_angle,
    hit_distance,
    hit_location,
    batted_ball_type,
    win_exp_before,
    win_exp_after,
    win_exp_delta,
    leverage_index,
    home_team_id,
    away_team_id,
    batting_team_id,
    extracted_at
FROM core.live_pitch_events
WHERE win_exp_before IS NOT NULL
  AND win_exp_after IS NOT NULL
ORDER BY game_pk, pa_number, pitch_number;

COMMENT ON VIEW core.v_live_pitch_training IS 
    'Training-ready pitch data with all features for pitch outcome modeling';

-- Function to extract pitch training examples
CREATE OR REPLACE FUNCTION core.extract_live_pitch_training_examples(
    p_season integer,
    p_game_date date DEFAULT NULL
)
RETURNS TABLE(
    live_pitch_id bigint,
    game_pk integer,
    pa_number integer,
    pitch_number smallint,
    pitch_type varchar,
    pitch_speed decimal,
    pitch_result_code varchar,
    is_strike boolean,
    win_exp_before decimal,
    win_exp_after decimal,
    win_exp_delta decimal
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        vpt.live_pitch_id,
        vpt.game_pk,
        vpt.pa_number,
        vpt.pitch_number,
        vpt.pitch_type,
        vpt.pitch_speed,
        vpt.pitch_result_code,
        vpt.is_strike,
        vpt.win_exp_before,
        vpt.win_exp_after,
        vpt.win_exp_delta
    FROM core.v_live_pitch_training vpt
    JOIN core.live_games lg ON vpt.game_pk = lg.game_pk
    WHERE lg.season = p_season
      AND (p_game_date IS NULL OR vpt.extracted_at::date = p_game_date);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION core.extract_live_pitch_training_examples IS 
    'Extract pitch outcome training examples from live pitch events for a season';
