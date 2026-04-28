/*
File: sql/30_core/311_core_live_events.sql
Purpose: Canonical live events/plate appearances for real-time prediction
Author: Agent Cascade
Date: 2026-04-28
Depends On: sql/30_core/310_core_live_games.sql
Called By: baseball/sources/mlb.py ingest pipeline, live prediction engine

Table: core.live_events
- Event-level data extracted from live feed (plate appearances, pitch results)
- Snapshot of game state at each event for feature engineering
- Grain: One row per event (PA, pitch, or game state change) per game per snapshot

Notes:
- event_id is synthetic (sequence within game)
- Links to live_games via game_pk and snapshot_id
- Designed for win probability model training and inference
- Event types: 'PA' (plate appearance), 'PITCH', 'GAME_STATE', 'SUBSTITUTION'
*/

-- Live events table for event-level game state tracking
CREATE TABLE IF NOT EXISTS core.live_events (
    live_event_id bigserial PRIMARY KEY,
    
    -- Game linkage
    game_pk integer NOT NULL,
    snapshot_id bigint REFERENCES raw_mlb.live_feed_snapshots(snapshot_id),
    
    -- Event identification
    event_id integer NOT NULL,              -- Sequence number within game
    event_type varchar(20) NOT NULL,          -- 'PA', 'PITCH', 'GAME_STATE', 'SUB'
    event_timestamp timestamptz,            -- When event occurred (if available)
    
    -- Game state at time of event (for model features)
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
    
    -- Matchup
    batter_id varchar(20),                  -- Retrosheet ID
    batter_mlb_id integer,
    batter_name varchar(100),
    batter_hand char(1),                    -- 'L', 'R', 'S'
    
    pitcher_id varchar(20),                 -- Retrosheet ID
    pitcher_mlb_id integer,
    pitcher_name varchar(100),
    pitcher_hand char(1),                   -- 'L', 'R', 'S'
    
    -- Plate appearance details (if event_type = 'PA')
    pa_result varchar(50),                  -- 'Single', 'Home Run', 'Walk', etc.
    pa_result_code varchar(10),             -- '1B', 'HR', 'BB', 'K', etc.
    exit_velocity decimal(5,2),             -- Statcast exit velocity (mph)
    launch_angle decimal(5,2),              -- Statcast launch angle (degrees)
    hit_distance integer,                   -- Estimated hit distance (feet)
    hit_location smallint,                  -- 1-9 fielding position
    
    -- Pitch details (if event_type = 'PITCH')
    pitch_number smallint,                  -- Pitch number within PA
    pitch_type varchar(10),                 -- 'FF', 'SL', 'CH', etc.
    pitch_type_description varchar(50),     -- 'Four-Seam Fastball'
    pitch_speed decimal(4,1),               -- MPH
    pitch_result varchar(50),               -- 'Ball', 'Called Strike', 'Swinging Strike', etc.
    pitch_result_code varchar(10),          -- 'B', 'C', 'S', 'F', 'X', etc.
    zone smallint,                          -- 1-9 strike zone (null = out of zone)
    
    -- Run expectancy context
    re24_state varchar(10),                 -- Runners-outs state (e.g., '1_2_3_2')
    re24_value decimal(6,4),                -- Change in run expectancy
    win_exp_before decimal(5,4),            -- Win probability before event
    win_exp_after decimal(5,4),             -- Win probability after event
    
    -- Inning/win probability context
    inning_half varchar(10),                -- 'top_1', 'bot_9', etc.
    leverage_index decimal(4,2),            -- Current leverage index
    
    -- Extracted metadata
    extracted_at timestamptz NOT NULL DEFAULT NOW(),
    
    -- Unique constraint per game/snapshot/event
    UNIQUE(game_pk, snapshot_id, event_id)
);

COMMENT ON TABLE core.live_events IS 
    'Event-level data from live feed for win probability prediction. One row per event with full game state snapshot.';

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_live_events_game ON core.live_events(game_pk);
CREATE INDEX IF NOT EXISTS idx_live_events_snapshot ON core.live_events(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_live_events_type ON core.live_events(event_type);
CREATE INDEX IF NOT EXISTS idx_live_events_batter ON core.live_events(batter_id) WHERE batter_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_live_events_pitcher ON core.live_events(pitcher_id) WHERE pitcher_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_live_events_extracted ON core.live_events(extracted_at DESC);

-- Composite index for model training queries
CREATE INDEX IF NOT EXISTS idx_live_events_features ON core.live_events(
    inning, is_top_inning, outs, bases_occupied, score_differential
) WHERE event_type = 'PA';

-- View: Latest events per game (current state)
CREATE OR REPLACE VIEW core.v_live_events_current AS
WITH latest_snapshot AS (
    SELECT DISTINCT ON (game_pk)
        game_pk,
        snapshot_id,
        extracted_at
    FROM core.live_games
    ORDER BY game_pk, extracted_at DESC
)
SELECT 
    le.*,
    lg.status_code as game_status,
    lg.status_description as game_status_desc
FROM core.live_events le
JOIN latest_snapshot ls ON le.snapshot_id = ls.snapshot_id
JOIN core.v_live_games_current lg ON le.game_pk = lg.game_pk;

COMMENT ON VIEW core.v_live_events_current IS 
    'Latest events from most recent snapshot per game';

-- View: Plate appearances with full context (for model training)
CREATE OR REPLACE VIEW core.v_live_plate_appearances AS
SELECT 
    le.live_event_id,
    le.game_pk,
    le.season,
    le.event_id as pa_number,
    le.inning,
    le.is_top_inning,
    le.outs,
    le.balls,
    le.strikes,
    le.bases_occupied,
    le.runner_on_first,
    le.runner_on_second,
    le.runner_on_third,
    le.home_score,
    le.away_score,
    le.score_differential,
    le.batter_id,
    le.batter_hand,
    le.pitcher_id,
    le.pitcher_hand,
    le.pa_result,
    le.pa_result_code,
    le.exit_velocity,
    le.launch_angle,
    le.hit_distance,
    le.re24_value,
    le.win_exp_before,
    le.win_exp_after,
    le.leverage_index,
    lg.home_team_id,
    lg.away_team_id,
    le.extracted_at
FROM core.live_events le
JOIN core.live_games lg ON le.snapshot_id = lg.snapshot_id
WHERE le.event_type = 'PA'
ORDER BY le.game_pk, le.event_id;

COMMENT ON VIEW core.v_live_plate_appearances IS 
    'Clean plate appearance data with full context for win probability model training';

-- View: Game state sequence for replay/simulation
CREATE OR REPLACE VIEW core.v_live_game_state_sequence AS
SELECT 
    game_pk,
    snapshot_id,
    event_id,
    inning,
    is_top_inning,
    outs,
    bases_occupied,
    home_score,
    away_score,
    score_differential,
    batter_id,
    pitcher_id,
    win_exp_before,
    win_exp_after,
    LAG(win_exp_after) OVER (PARTITION BY game_pk ORDER BY event_id) as prev_win_exp,
    win_exp_after - COALESCE(LAG(win_exp_after) OVER (PARTITION BY game_pk ORDER BY event_id), 0.5) as win_exp_delta
FROM core.live_events
WHERE event_type = 'PA'
ORDER BY game_pk, event_id;

COMMENT ON VIEW core.v_live_game_state_sequence IS 
    'Sequential game states with win probability deltas for analysis';

-- Function to extract training examples from live events
CREATE OR REPLACE FUNCTION core.extract_live_training_examples(
    p_season integer,
    p_game_date date DEFAULT NULL
)
RETURNS TABLE(
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
    pa_result varchar
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        vlp.game_pk,
        vlp.inning,
        vlp.is_top_inning,
        vlp.outs,
        vlp.bases_occupied,
        vlp.score_differential,
        vlp.home_team_id,
        vlp.away_team_id,
        vlp.batter_id,
        vlp.pitcher_id,
        vlp.win_exp_before,
        vlp.win_exp_after,
        vlp.pa_result
    FROM core.v_live_plate_appearances vlp
    WHERE vlp.season = p_season
      AND (p_game_date IS NULL OR vlp.extracted_at::date = p_game_date)
      AND vlp.win_exp_before IS NOT NULL
      AND vlp.win_exp_after IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION core.extract_live_training_examples IS 
    'Extract win probability training examples from live game data for a season';
