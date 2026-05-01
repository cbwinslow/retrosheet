/*
File: sql/30_core/314_core_game_state_snapshots.sql
Purpose: Canonical game state snapshots for replay and simulation
Author: Agent Cascade
Date: 2026-04-29
Depends On: sql/30_core/310_core_live_games.sql, sql/30_core/312_core_live_plate_appearances.sql
Called By: baseball/sources/mlb.py ingest pipeline, simulation/replay scripts

Table: core.game_state_snapshots
- Complete game state at each snapshot timestamp
- Grain: One row per game per snapshot (append-only)
- Designed for game replay, simulation, and historical analysis
- Links to raw snapshots for full API response

Notes:
- Preserves complete game state for each snapshot
- Supports time-series analysis of game progression
- Enables reconstruction of game timeline
- All fields preserved from live_games (no reduction)
*/

-- Game state snapshots table
CREATE TABLE IF NOT EXISTS core.game_state_snapshots (
    snapshot_id bigserial PRIMARY KEY,
    
    -- Raw linkage
    raw_snapshot_id bigint REFERENCES raw_mlb.live_feed_snapshots(snapshot_id),
    
    -- Game identification
    game_pk integer NOT NULL,
    game_guid uuid,
    season integer NOT NULL,
    game_date date NOT NULL,
    game_number smallint DEFAULT 1,
    
    -- Teams
    home_team_id varchar(10) NOT NULL,
    away_team_id varchar(10) NOT NULL,
    home_team_name varchar(100),
    away_team_name varchar(100),
    
    -- Game status
    status_code varchar(20) NOT NULL,
    status_description varchar(50),
    detailed_state varchar(50),
    
    -- Current game state
    inning smallint,
    is_top_inning boolean,
    outs smallint,
    balls smallint,
    strikes smallint,
    
    -- Base state
    runner_on_first boolean DEFAULT FALSE,
    runner_on_second boolean DEFAULT FALSE,
    runner_on_third boolean DEFAULT FALSE,
    bases_occupied varchar(3),
    
    -- Score
    home_score integer DEFAULT 0,
    away_score integer DEFAULT 0,
    score_differential integer GENERATED ALWAYS AS (home_score - away_score) STORED,
    
    -- Pitching
    current_pitcher_id varchar(20),
    current_pitcher_name varchar(100),
    current_pitcher_mlb_id integer,
    
    -- Batting
    current_batter_id varchar(20),
    current_batter_name varchar(100),
    current_batter_mlb_id integer,
    
    -- On-deck
    on_deck_batter_id varchar(20),
    in_hole_batter_id varchar(20),
    
    -- Count and situation
    count varchar(10),
    
    -- Game timing
    scheduled_start timestamptz,
    actual_start timestamptz,
    game_duration_minutes integer,
    
    -- Weather/conditions
    temperature_fahrenheit smallint,
    weather_condition varchar(50),
    wind_speed_mph smallint,
    wind_direction varchar(20),
    
    -- Venue
    venue_id varchar(10),
    venue_name varchar(100),
    
    -- Umpires
    home_plate_umpire_id varchar(20),
    first_base_umpire_id varchar(20),
    second_base_umpire_id varchar(20),
    third_base_umpire_id varchar(20),
    
    -- Broadcast info
    national_broadcast varchar(100),
    home_broadcast varchar(100),
    away_broadcast varchar(100),
    
    -- Win probability context
    win_exp_home decimal(5,4),
    win_exp_away decimal(5,4),
    leverage_index decimal(4,2),
    
    -- Extracted metadata
    extracted_at timestamptz NOT NULL DEFAULT NOW(),
    
    -- Unique constraint per game/snapshot
    UNIQUE(game_pk, raw_snapshot_id)
);

COMMENT ON TABLE core.game_state_snapshots IS 
    'Complete game state snapshots for replay, simulation, and historical analysis';

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_game_snapshots_game ON core.game_state_snapshots(game_pk);
CREATE INDEX IF NOT EXISTS idx_game_snapshots_raw ON core.game_state_snapshots(raw_snapshot_id);
CREATE INDEX IF NOT EXISTS idx_game_snapshots_season ON core.game_state_snapshots(season);
CREATE INDEX IF NOT EXISTS idx_game_snapshots_date ON core.game_state_snapshots(game_date);
CREATE INDEX IF NOT EXISTS idx_game_snapshots_status ON core.game_state_snapshots(status_code) WHERE status_code IN ('I', 'P', 'S');
CREATE INDEX IF NOT EXISTS idx_game_snapshots_extracted ON core.game_state_snapshots(extracted_at DESC);

-- Composite index for time-series queries
CREATE INDEX IF NOT EXISTS idx_game_snapshots_timeline ON core.game_state_snapshots(
    game_pk, extracted_at
);

-- View: Latest snapshot per game
CREATE OR REPLACE VIEW core.v_game_state_latest AS
WITH ranked_snapshots AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY game_pk ORDER BY extracted_at DESC) as rn
    FROM core.game_state_snapshots
)
SELECT * FROM ranked_snapshots WHERE rn = 1;

COMMENT ON VIEW core.v_game_state_latest IS 
    'Latest game state snapshot for each game';

-- View: Game timeline (all snapshots for a game)
CREATE OR REPLACE VIEW core.v_game_timeline AS
SELECT 
    game_pk,
    season,
    game_date,
    home_team_id,
    away_team_id,
    status_code,
    status_description,
    inning,
    is_top_inning,
    outs,
    balls,
    strikes,
    bases_occupied,
    home_score,
    away_score,
    score_differential,
    current_pitcher_name,
    current_batter_name,
    count,
    win_exp_home,
    win_exp_away,
    leverage_index,
    extracted_at
FROM core.game_state_snapshots
ORDER BY game_pk, extracted_at;

COMMENT ON VIEW core.v_game_timeline IS 
    'Complete game timeline with all snapshots for time-series analysis';

-- View: Game state changes (delta between snapshots)
CREATE OR REPLACE VIEW core.v_game_state_changes AS
WITH ordered_snapshots AS (
    SELECT 
        *,
        LAG(extracted_at) OVER (PARTITION BY game_pk ORDER BY extracted_at) as prev_extracted_at,
        LAG(inning) OVER (PARTITION BY game_pk ORDER BY extracted_at) as prev_inning,
        LAG(is_top_inning) OVER (PARTITION BY game_pk ORDER BY extracted_at) as prev_is_top_inning,
        LAG(outs) OVER (PARTITION BY game_pk ORDER BY extracted_at) as prev_outs,
        LAG(balls) OVER (PARTITION BY game_pk ORDER BY extracted_at) as prev_balls,
        LAG(strikes) OVER (PARTITION BY game_pk ORDER BY extracted_at) as prev_strikes,
        LAG(bases_occupied) OVER (PARTITION BY game_pk ORDER BY extracted_at) as prev_bases_occupied,
        LAG(home_score) OVER (PARTITION BY game_pk ORDER BY extracted_at) as prev_home_score,
        LAG(away_score) OVER (PARTITION BY game_pk ORDER BY extracted_at) as prev_away_score,
        LAG(status_code) OVER (PARTITION BY game_pk ORDER BY extracted_at) as prev_status_code
    FROM core.game_state_snapshots
)
SELECT 
    game_pk,
    season,
    game_date,
    home_team_id,
    away_team_id,
    extracted_at,
    prev_extracted_at,
    EXTRACT(EPOCH FROM (extracted_at - prev_extracted_at)) as seconds_since_prev,
    inning,
    is_top_inning,
    outs,
    balls,
    strikes,
    bases_occupied,
    home_score,
    away_score,
    score_differential,
    current_pitcher_name,
    current_batter_name,
    count,
    status_code,
    prev_status_code,
    CASE 
        WHEN inning != prev_inning THEN 'inning_change'
        WHEN is_top_inning != prev_is_top_inning THEN 'half_inning_change'
        WHEN outs != prev_outs THEN 'out_change'
        WHEN balls != prev_balls OR strikes != prev_strikes THEN 'count_change'
        WHEN bases_occupied != prev_bases_occupied THEN 'runner_change'
        WHEN home_score != prev_home_score OR away_score != prev_away_score THEN 'score_change'
        WHEN status_code != prev_status_code THEN 'status_change'
        ELSE 'other'
    END as change_type,
    win_exp_home,
    win_exp_away,
    leverage_index
FROM ordered_snapshots
WHERE prev_extracted_at IS NOT NULL
ORDER BY game_pk, extracted_at;

COMMENT ON VIEW core.v_game_state_changes IS 
    'Game state changes between snapshots for event detection and analysis';

-- Function to get game timeline for replay
CREATE OR REPLACE FUNCTION core.get_game_timeline(p_game_pk integer)
RETURNS TABLE(
    extracted_at timestamptz,
    inning smallint,
    is_top_inning boolean,
    outs smallint,
    balls smallint,
    strikes smallint,
    bases_occupied varchar,
    home_score integer,
    away_score integer,
    score_differential integer,
    current_pitcher_name varchar,
    current_batter_name varchar,
    count varchar,
    status_code varchar,
    win_exp_home decimal,
    win_exp_away decimal
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        extracted_at,
        inning,
        is_top_inning,
        outs,
        balls,
        strikes,
        bases_occupied,
        home_score,
        away_score,
        score_differential,
        current_pitcher_name,
        current_batter_name,
        count,
        status_code,
        win_exp_home,
        win_exp_away
    FROM core.game_state_snapshots
    WHERE game_pk = p_game_pk
    ORDER BY extracted_at;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION core.get_game_timeline IS 
    'Get complete game timeline for replay or simulation';

-- Function to get game state at specific timestamp
CREATE OR REPLACE FUNCTION core.get_game_state_at_time(
    p_game_pk integer,
    p_timestamp timestamptz
)
RETURNS TABLE(
    game_pk integer,
    inning smallint,
    is_top_inning boolean,
    outs smallint,
    balls smallint,
    strikes smallint,
    bases_occupied varchar,
    home_score integer,
    away_score integer,
    score_differential integer,
    current_pitcher_id varchar,
    current_batter_id varchar,
    status_code varchar
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        game_pk,
        inning,
        is_top_inning,
        outs,
        balls,
        strikes,
        bases_occupied,
        home_score,
        away_score,
        score_differential,
        current_pitcher_id,
        current_batter_id,
        status_code
    FROM core.game_state_snapshots
    WHERE game_pk = p_game_pk
      AND extracted_at <= p_timestamp
    ORDER BY extracted_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION core.get_game_state_at_time IS 
    'Get game state at a specific timestamp for historical queries';
