/*
File: sql/30_core/310_core_live_games.sql
Purpose: Canonical live games table for real-time game state
Author: Agent Cascade
Date: 2026-04-28
Depends On: sql/30_core/3001_core_init.sql (core schema)
Called By: baseball/sources/mlb.py ingest pipeline

Table: core.live_games
- Canonical representation of live game state from MLB Stats API
- Updated in real-time as game progresses
- Links to raw_mlb.live_feed_snapshots via snapshot_id
- Grain: One row per game per snapshot (append-only, latest wins via view)

Notes:
- Use v_live_games_current view to get latest state per game
- snapshot_id provides full lineage to raw API response
- Game status tracks: preview, live, final, postponed, etc.
- All timestamps in UTC
*/

-- Live games table for real-time game state tracking
CREATE TABLE IF NOT EXISTS core.live_games (
    live_game_id bigserial PRIMARY KEY,
    
    -- Game identification
    game_pk integer NOT NULL,
    game_guid uuid,                        -- MLB's game GUID if available
    season integer NOT NULL,
    game_date date NOT NULL,
    game_number smallint DEFAULT 1,        -- 1 or 2 for doubleheaders
    
    -- Teams (using canonical team IDs, not source-specific)
    home_team_id varchar(10) NOT NULL,     -- Reference to core.teams
    away_team_id varchar(10) NOT NULL,
    home_team_name varchar(100),
    away_team_name varchar(100),
    
    -- Game status
    status_code varchar(20) NOT NULL,       -- 'S', 'P', 'I', 'F', 'D', 'C', 'O'
    status_description varchar(50),         -- 'Scheduled', 'Preview', 'Live', 'Final', etc.
    detailed_state varchar(50),             -- 'Pre-Game', 'Warmup', 'In Progress', 'Game Over'
    
    -- Current game state (for live games)
    inning smallint,                        -- Current inning (null if not started)
    is_top_inning boolean,                  -- true = top, false = bottom
    outs smallint,                          -- 0-2
    balls smallint,                         -- 0-4
    strikes smallint,                       -- 0-2
    
    -- Base state (runner occupancy)
    runner_on_first boolean DEFAULT FALSE,
    runner_on_second boolean DEFAULT FALSE,
    runner_on_third boolean DEFAULT FALSE,
    
    -- Score
    home_score integer DEFAULT 0,
    away_score integer DEFAULT 0,
    
    -- Pitching
    current_pitcher_id varchar(20),         -- Retrosheet player ID
    current_pitcher_name varchar(100),
    current_pitcher_mlb_id integer,         -- MLB ID for bridge lookup
    
    -- Batting
    current_batter_id varchar(20),            -- Retrosheet player ID
    current_batter_name varchar(100),
    current_batter_mlb_id integer,
    
    -- On-deck (for prediction features)
    on_deck_batter_id varchar(20),
    in_hole_batter_id varchar(20),
    
    -- Count and situation
    count varchar(10),                      -- '3-2', '0-1', etc.
    bases_occupied varchar(3),              -- '111' = loaded, '100' = first only, etc.
    
    -- Game timing
    scheduled_start timestamptz,
    actual_start timestamptz,
    game_duration_minutes integer,
    
    -- Weather/conditions (if available)
    temperature_fahrenheit smallint,
    weather_condition varchar(50),
    wind_speed_mph smallint,
    wind_direction varchar(20),
    
    -- Venue
    venue_id varchar(10),                   -- Reference to core.parks
    venue_name varchar(100),
    
    -- Umpires (if assigned)
    home_plate_umpire_id varchar(20),
    first_base_umpire_id varchar(20),
    second_base_umpire_id varchar(20),
    third_base_umpire_id varchar(20),
    
    -- Broadcast info
    national_broadcast varchar(100),        -- Comma-separated networks
    home_broadcast varchar(100),
    away_broadcast varchar(100),
    
    -- Lineage
    snapshot_id bigint REFERENCES raw_mlb.live_feed_snapshots(snapshot_id),
    extracted_at timestamptz NOT NULL DEFAULT NOW(),
    
    -- Unique constraint: one canonical record per snapshot
    UNIQUE(snapshot_id)
);

COMMENT ON TABLE core.live_games IS 
    'Canonical live game state extracted from raw_mlb.live_feed_snapshots. Append-only with v_live_games_current view for latest state.';

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_live_games_game_pk ON core.live_games(game_pk);
CREATE INDEX IF NOT EXISTS idx_live_games_season ON core.live_games(season);
CREATE INDEX IF NOT EXISTS idx_live_games_date ON core.live_games(game_date);
CREATE INDEX IF NOT EXISTS idx_live_games_status ON core.live_games(status_code) WHERE status_code IN ('I', 'P', 'S');
CREATE INDEX IF NOT EXISTS idx_live_games_teams ON core.live_games(home_team_id, away_team_id);
CREATE INDEX IF NOT EXISTS idx_live_games_extracted ON core.live_games(extracted_at DESC);

-- Foreign key constraints (soft references - may not exist yet in core)
-- ALTER TABLE core.live_games ADD CONSTRAINT fk_live_games_home_team 
--     FOREIGN KEY (home_team_id) REFERENCES core.teams(team_id);
-- ALTER TABLE core.live_games ADD CONSTRAINT fk_live_games_away_team 
--     FOREIGN KEY (away_team_id) REFERENCES core.teams(team_id);

-- View: Latest state per game (current live view)
CREATE OR REPLACE VIEW core.v_live_games_current AS
WITH ranked_games AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (PARTITION BY game_pk ORDER BY extracted_at DESC) as rn
    FROM core.live_games
)
SELECT * FROM ranked_games WHERE rn = 1;

COMMENT ON VIEW core.v_live_games_current IS 
    'Latest live game state for each game (deduplicated from append-only table)';

-- View: Games currently in progress
CREATE OR REPLACE VIEW core.v_live_games_in_progress AS
SELECT *
FROM core.v_live_games_current
WHERE status_code = 'I'  -- In Progress
ORDER BY game_date, game_pk;

COMMENT ON VIEW core.v_live_games_in_progress IS 
    'Games currently being played (for live prediction pipeline)';

-- View: Today's games summary
CREATE OR REPLACE VIEW core.v_todays_games AS
SELECT 
    game_pk,
    game_date,
    season,
    home_team_id,
    away_team_id,
    home_team_name,
    away_team_name,
    status_description,
    detailed_state,
    inning,
    is_top_inning,
    outs,
    home_score,
    away_score,
    current_pitcher_name,
    current_batter_name,
    count,
    extracted_at
FROM core.v_live_games_current
WHERE game_date = CURRENT_DATE
   OR (game_date = CURRENT_DATE - 1 AND status_code NOT IN ('F', 'D', 'C'))
ORDER BY 
    CASE status_code 
        WHEN 'I' THEN 1  -- In Progress first
        WHEN 'P' THEN 2  -- Preview
        WHEN 'S' THEN 3  -- Scheduled
        ELSE 4
    END,
    scheduled_start;

COMMENT ON VIEW core.v_todays_games IS 
    'Summary view of today''s games with current status and score';

-- Function to get game state for prediction input
CREATE OR REPLACE FUNCTION core.get_game_state_for_prediction(p_game_pk integer)
RETURNS TABLE(
    game_pk integer,
    inning smallint,
    is_top_inning boolean,
    outs smallint,
    balls smallint,
    strikes smallint,
    home_score integer,
    away_score integer,
    runner_on_first boolean,
    runner_on_second boolean,
    runner_on_third boolean,
    current_pitcher_id varchar,
    current_batter_id varchar,
    home_team_id varchar,
    away_team_id varchar,
    status_code varchar
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        lg.game_pk,
        lg.inning,
        lg.is_top_inning,
        lg.outs,
        lg.balls,
        lg.strikes,
        lg.home_score,
        lg.away_score,
        lg.runner_on_first,
        lg.runner_on_second,
        lg.runner_on_third,
        lg.current_pitcher_id,
        lg.current_batter_id,
        lg.home_team_id,
        lg.away_team_id,
        lg.status_code
    FROM core.v_live_games_current lg
    WHERE lg.game_pk = p_game_pk;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION core.get_game_state_for_prediction IS 
    'Extract current game state formatted for win probability prediction input';
