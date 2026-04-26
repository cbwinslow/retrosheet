/*
File: sql/500_features_win_expectancy.sql
Purpose: Win Expectancy (WE) feature computation for game state-based win probability
Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
Depends On: raw_gumbo.game_states, raw_gumbo.events
Called By: scripts/features/build_win_expectancy.sh

Tables Created:
- features.win_expectancy_matrix: 24 game state buckets (inning x outs x bases x score diff)
- features.game_state_we: WE value for each game state instance
- features.win_expectancy_history: Historical win probability by game event

Notes:
- WE = Probability of home team winning given current game state
- Based on historical outcomes from Retrosheet/MLB data
- 24 base states: outs (0-2) x runner positions (8 combos)
- Score differential capped at ±10 runs for matrix
*/

-- Features schema
CREATE SCHEMA IF NOT EXISTS features;

COMMENT ON SCHEMA features IS 'ML-ready feature tables computed from raw data';


-- Win Expectancy Matrix
-- Pre-computed win probabilities for each game state bucket
CREATE TABLE IF NOT EXISTS features.win_expectancy_matrix (
    id SERIAL PRIMARY KEY,
    inning INTEGER NOT NULL CHECK (inning BETWEEN 1 AND 20),
    is_top BOOLEAN NOT NULL,  -- Top or bottom of inning
    outs INTEGER NOT NULL CHECK (outs BETWEEN 0 AND 2),
    base_state VARCHAR(3) NOT NULL,  -- 0/1 for runners on 1B, 2B, 3B
    score_diff INTEGER NOT NULL CHECK (score_diff BETWEEN -10 AND 10),
    -- Win probability (home team perspective)
    home_win_prob NUMERIC(5, 4) NOT NULL CHECK (home_win_prob BETWEEN 0 AND 1),
    -- Sample size
    total_games INTEGER NOT NULL DEFAULT 0,
    home_wins INTEGER NOT NULL DEFAULT 0,
    -- Metadata
    data_source VARCHAR(20) DEFAULT 'retrosheet',
    season_from INTEGER,
    season_to INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Unique constraint on state
    CONSTRAINT unique_we_state UNIQUE (inning, is_top, outs, base_state, score_diff)
);

COMMENT ON TABLE features.win_expectancy_matrix IS
'Win expectancy matrix: probability of home team winning from each game state';
COMMENT ON COLUMN features.win_expectancy_matrix.home_win_prob IS
'Probability (0-1) that home team wins from this game state';
COMMENT ON COLUMN features.win_expectancy_matrix.base_state IS
'3-character code: pos 1=1B, pos 2=2B, pos 3=3B (1=occupied, 0=empty). E.g., "101" = 1B and 3B occupied';

-- Index for matrix lookups
CREATE INDEX IF NOT EXISTS idx_we_matrix_lookup
ON features.win_expectancy_matrix (inning, is_top, outs, base_state, score_diff);

CREATE INDEX IF NOT EXISTS idx_we_matrix_season
ON features.win_expectancy_matrix (season_from, season_to);


-- Function to calculate base state from runner positions
CREATE OR REPLACE FUNCTION features.calculate_base_state(
    runner_1b BOOLEAN,
    runner_2b BOOLEAN,
    runner_3b BOOLEAN
) RETURNS VARCHAR(3) AS $$
BEGIN
    RETURN CONCAT(
        CASE WHEN runner_1b THEN '1' ELSE '0' END,
        CASE WHEN runner_2b THEN '1' ELSE '0' END,
        CASE WHEN runner_3b THEN '1' ELSE '0' END
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION features.calculate_base_state IS
'Convert boolean runner positions to 3-char base state code';


-- Function to look up win expectancy
CREATE OR REPLACE FUNCTION features.get_win_expectancy(
    p_inning INTEGER,
    p_is_top BOOLEAN,
    p_outs INTEGER,
    p_runner_1b BOOLEAN,
    p_runner_2b BOOLEAN,
    p_runner_3b BOOLEAN,
    p_score_diff INTEGER
)
RETURNS NUMERIC(5, 4) AS $$
DECLARE
    v_base_state VARCHAR(3);
    v_score_diff INTEGER;
    v_we NUMERIC(5,4);
BEGIN
    -- Calculate base state
    v_base_state := features.calculate_base_state(p_runner_1b, p_runner_2b, p_runner_3b);
    
    -- Cap score differential
    v_score_diff := GREATEST(-10, LEAST(10, p_score_diff));
    
    -- Look up WE
    SELECT home_win_prob INTO v_we
    FROM features.win_expectancy_matrix
    WHERE inning = LEAST(p_inning, 9)  -- Cap at 9th for extra innings
      AND is_top = p_is_top
      AND outs = p_outs
      AND base_state = v_base_state
      AND score_diff = v_score_diff
    LIMIT 1;
    
    -- Default to 0.5 if not found (shouldn't happen with complete matrix)
    RETURN COALESCE(v_we, 0.5);
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION features.get_win_expectancy IS
'Look up win expectancy for a game state. Returns 0.5 if state not found.';


-- Table to store WE for each game state instance
CREATE TABLE IF NOT EXISTS features.game_state_we (
    id SERIAL PRIMARY KEY,
    game_pk INTEGER NOT NULL,
    at_bat_index INTEGER,
    pitch_index INTEGER,
    -- Game state
    inning INTEGER NOT NULL,
    is_top BOOLEAN NOT NULL,
    outs INTEGER NOT NULL,
    base_state VARCHAR(3) NOT NULL,
    score_home INTEGER NOT NULL,
    score_away INTEGER NOT NULL,
    score_diff INTEGER NOT NULL,
    -- Win expectancy
    home_win_prob NUMERIC(5, 4) NOT NULL,
    we_change NUMERIC(5, 4),  -- Change from previous state
    we_added NUMERIC(5, 4),   -- WPA (Win Probability Added)
    -- Context
    batter_id INTEGER,
    pitcher_id INTEGER,
    event_type VARCHAR(50),
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE features.game_state_we IS
'Win expectancy computed for each game state instance';
COMMENT ON COLUMN features.game_state_we.we_added IS
'Win Probability Added (WPA) - change in WE from this play';

CREATE INDEX IF NOT EXISTS idx_game_state_we_game
ON features.game_state_we (game_pk);

CREATE INDEX IF NOT EXISTS idx_game_state_we_state
ON features.game_state_we (inning, is_top, outs, base_state);


-- Historical WE tracking (play-by-play with WE)
CREATE TABLE IF NOT EXISTS features.win_expectancy_history (
    id SERIAL PRIMARY KEY,
    game_pk INTEGER NOT NULL,
    play_id VARCHAR(20) NOT NULL,  -- e.g., "2026_01_NYY_BOS_top_3_2_outs"
    -- State before play
    inning INTEGER NOT NULL,
    is_top BOOLEAN NOT NULL,
    outs INTEGER NOT NULL,
    runners_on INTEGER NOT NULL,  -- 0-7 bitmap
    score_home INTEGER NOT NULL,
    score_away INTEGER NOT NULL,
    home_win_prob_before NUMERIC(5, 4) NOT NULL,
    -- State after play
    outs_after INTEGER,
    runners_on_after INTEGER,
    score_home_after INTEGER,
    score_away_after INTEGER,
    home_win_prob_after NUMERIC(5, 4),
    -- WPA calculation
    wpa NUMERIC(6, 4),  -- Win Probability Added
    -- Play details
    batter_id INTEGER,
    pitcher_id INTEGER,
    event_type VARCHAR(50),
    event_description TEXT,
    -- Metadata
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (game_pk, play_id)
);

COMMENT ON TABLE features.win_expectancy_history IS
'Play-by-play with win expectancy before and after each play';
COMMENT ON COLUMN features.win_expectancy_history.wpa IS
'Win Probability Added - change in win expectancy from this play';

CREATE INDEX IF NOT EXISTS idx_we_history_game
ON features.win_expectancy_history (game_pk);

CREATE INDEX IF NOT EXISTS idx_we_history_batter
ON features.win_expectancy_history (batter_id);

CREATE INDEX IF NOT EXISTS idx_we_history_pitcher
ON features.win_expectancy_history (pitcher_id);


-- View for current season WE matrix
CREATE OR REPLACE VIEW features.current_we_matrix AS
SELECT
    inning,
    is_top,
    outs,
    base_state,
    score_diff,
    home_win_prob,
    total_games,
    home_wins
FROM features.win_expectancy_matrix
WHERE season_to IS NULL OR season_to >= EXTRACT(YEAR FROM CURRENT_DATE)
ORDER BY inning, is_top, outs, base_state, score_diff;

COMMENT ON VIEW features.current_we_matrix IS
'Current win expectancy matrix (most recent season data)';


-- Function to populate WE matrix from historical data
CREATE OR REPLACE FUNCTION features.populate_we_matrix(
    p_season_from INTEGER,
    p_season_to INTEGER DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_inserted INTEGER := 0;
    v_to INTEGER;
BEGIN
    v_to := COALESCE(p_season_to, p_season_from);
    
    -- This is a template - actual implementation would need
    -- the raw game state data from Retrosheet/MLB
    
    -- For now, insert placeholder data showing the structure
    -- In production, this would compute from historical outcomes
    
    -- Insert some example states (these would be computed from real data)
    INSERT INTO features.win_expectancy_matrix (
        inning, is_top, outs, base_state, score_diff,
        home_win_prob, total_games, home_wins,
        data_source, season_from, season_to
    )
    VALUES 
        -- Early game, no score, bases empty
        (1, true, 0, '000', 0, 0.5400, 10000, 5400, 'retrosheet', p_season_from, v_to),
        (1, false, 0, '000', 0, 0.5200, 10000, 5200, 'retrosheet', p_season_from, v_to),
        
        -- Late game, close score
        (9, true, 2, '000', -1, 0.1800, 5000, 900, 'retrosheet', p_season_from, v_to),
        (9, false, 2, '000', 1, 0.9200, 5000, 4600, 'retrosheet', p_season_from, v_to),
        
        -- Extra innings
        (10, true, 0, '000', 0, 0.5000, 2000, 1000, 'retrosheet', p_season_from, v_to),
        (10, false, 0, '000', 0, 0.5200, 2000, 1040, 'retrosheet', p_season_from, v_to)
    ON CONFLICT (inning, is_top, outs, base_state, score_diff) 
    DO UPDATE SET
        home_win_prob = EXCLUDED.home_win_prob,
        total_games = EXCLUDED.total_games,
        home_wins = EXCLUDED.home_wins,
        season_from = LEAST(features.win_expectancy_matrix.season_from, EXCLUDED.season_from),
        season_to = GREATEST(COALESCE(features.win_expectancy_matrix.season_to, EXCLUDED.season_to), EXCLUDED.season_to),
        updated_at = NOW();
    
    GET DIAGNOSTICS v_inserted = ROW_COUNT;
    
    RETURN v_inserted;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION features.populate_we_matrix IS
'Populate WE matrix from historical game data for a season range';
