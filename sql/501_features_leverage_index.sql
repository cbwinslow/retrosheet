/*
File: sql/501_features_leverage_index.sql
Purpose: Leverage Index (LI) feature computation for situational importance
Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
Depends On: features.win_expectancy_matrix
Called By: scripts/features/build_leverage_index.sh

Tables Created:
- features.leverage_index_matrix: Importance of each game state
- features.game_state_li: LI for each play
- features.player_clutch_stats: Clutch performance metrics

Notes:
- LI = Relative importance of a game situation
- Based on potential swing in win probability from current state
- Average LI = 1.0; LI > 1.0 = more important than average
- LI is calculated before the play happens (context, not outcome)
*/


-- Leverage Index Matrix
-- Pre-computed importance for each game state bucket
CREATE TABLE IF NOT EXISTS features.leverage_index_matrix (
    id SERIAL PRIMARY KEY,
    inning INTEGER NOT NULL CHECK (inning BETWEEN 1 AND 20),
    is_top BOOLEAN NOT NULL,
    outs INTEGER NOT NULL CHECK (outs BETWEEN 0 AND 2),
    base_state VARCHAR(3) NOT NULL,  -- 0/1 for 1B, 2B, 3B
    score_diff INTEGER NOT NULL CHECK (score_diff BETWEEN -10 AND 10),
    -- Leverage metrics
    leverage_index NUMERIC(5, 3) NOT NULL,
    importance_rating VARCHAR(20),  -- 'low', 'medium', 'high', 'very_high'
    -- Components
    swing_potential NUMERIC(5, 4),  -- Max possible WE change
    win_prob_variance NUMERIC(7, 6),  -- Variance of possible outcomes
    -- Sample size
    total_plays INTEGER NOT NULL DEFAULT 0,
    -- Metadata
    data_source VARCHAR(20) DEFAULT 'computed',
    season_from INTEGER,
    season_to INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Unique constraint
    CONSTRAINT unique_li_state UNIQUE (inning, is_top, outs, base_state, score_diff)
);

COMMENT ON TABLE features.leverage_index_matrix IS
'Leverage Index matrix: importance of each game state (1.0 = average)';
COMMENT ON COLUMN features.leverage_index_matrix.leverage_index IS
'Leverage Index - relative importance (1.0 = average, >1 = more important)';
COMMENT ON COLUMN features.leverage_index_matrix.swing_potential IS
'Maximum possible win probability change from this state';
COMMENT ON COLUMN features.leverage_index_matrix.importance_rating IS
'Categorical rating: low (<0.7), medium (0.7-1.3), high (1.3-2.0), very_high (>2.0)';

-- Index for LI lookups
CREATE INDEX IF NOT EXISTS idx_li_matrix_lookup
ON features.leverage_index_matrix (inning, is_top, outs, base_state, score_diff);

CREATE INDEX IF NOT EXISTS idx_li_matrix_importance
ON features.leverage_index_matrix (importance_rating)
WHERE importance_rating IN ('high', 'very_high');


-- Function to determine importance rating from LI value
CREATE OR REPLACE FUNCTION features.get_importance_rating(p_li NUMERIC)
RETURNS VARCHAR(20) AS $$
BEGIN
    RETURN CASE
        WHEN p_li < 0.7 THEN 'low'
        WHEN p_li < 1.3 THEN 'medium'
        WHEN p_li < 2.0 THEN 'high'
        ELSE 'very_high'
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION features.get_importance_rating IS
'Convert leverage index to categorical importance rating';


-- Function to look up leverage index
CREATE OR REPLACE FUNCTION features.get_leverage_index(
    p_inning INTEGER,
    p_is_top BOOLEAN,
    p_outs INTEGER,
    p_runner_1b BOOLEAN,
    p_runner_2b BOOLEAN,
    p_runner_3b BOOLEAN,
    p_score_diff INTEGER
)
RETURNS NUMERIC(5, 3) AS $$
DECLARE
    v_base_state VARCHAR(3);
    v_score_diff INTEGER;
    v_li NUMERIC(5,3);
BEGIN
    -- Calculate base state
    v_base_state := features.calculate_base_state(p_runner_1b, p_runner_2b, p_runner_3b);
    
    -- Cap score differential
    v_score_diff := GREATEST(-10, LEAST(10, p_score_diff));
    
    -- Look up LI
    SELECT leverage_index INTO v_li
    FROM features.leverage_index_matrix
    WHERE inning = LEAST(p_inning, 9)  -- Cap at 9th for extra innings
      AND is_top = p_is_top
      AND outs = p_outs
      AND base_state = v_base_state
      AND score_diff = v_score_diff
    LIMIT 1;
    
    -- Default to 1.0 (average) if not found
    RETURN COALESCE(v_li, 1.0);
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION features.get_leverage_index IS
'Look up leverage index for a game state. Returns 1.0 if state not found.';


-- Table to store LI for each play instance
CREATE TABLE IF NOT EXISTS features.game_state_li (
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
    -- Leverage metrics
    leverage_index NUMERIC(5, 3) NOT NULL,
    importance_rating VARCHAR(20),
    swing_potential NUMERIC(5, 4),
    is_high_leverage BOOLEAN GENERATED ALWAYS AS (leverage_index >= 1.5) STORED,
    -- Context
    batter_id INTEGER,
    pitcher_id INTEGER,
    -- Metadata
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE features.game_state_li IS
'Leverage index computed for each play instance';
COMMENT ON COLUMN features.game_state_li.is_high_leverage IS
'Boolean flag for high-leverage situations (LI >= 1.5)';

CREATE INDEX IF NOT EXISTS idx_game_state_li_game
ON features.game_state_li (game_pk);

CREATE INDEX IF NOT EXISTS idx_game_state_li_high
ON features.game_state_li (game_pk, batter_id)
WHERE is_high_leverage = TRUE;

CREATE INDEX IF NOT EXISTS idx_game_state_li_pitcher
ON features.game_state_li (pitcher_id, leverage_index);


-- Player clutch performance statistics
CREATE TABLE IF NOT EXISTS features.player_clutch_stats (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,
    player_type VARCHAR(10) NOT NULL CHECK (player_type IN ('batter', 'pitcher')),
    season INTEGER NOT NULL,
    -- Leverage breakdown
    pa_low_leverage INTEGER DEFAULT 0,
    pa_medium_leverage INTEGER DEFAULT 0,
    pa_high_leverage INTEGER DEFAULT 0,
    pa_very_high_leverage INTEGER DEFAULT 0,
    -- Performance by leverage
    avg_low_leverage NUMERIC(5, 4),
    avg_medium_leverage NUMERIC(5, 4),
    avg_high_leverage NUMERIC(5, 4),
    avg_very_high_leverage NUMERIC(5, 4),
    -- Clutch metrics
    clutch_score NUMERIC(6, 4),  -- Performance vs expected in high leverage
    leverage_opportunities INTEGER DEFAULT 0,
    -- WPA totals by leverage
    wpa_low NUMERIC(7, 4),
    wpa_medium NUMERIC(7, 4),
    wpa_high NUMERIC(7, 4),
    wpa_very_high NUMERIC(7, 4),
    -- Metadata
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (player_id, player_type, season)
);

COMMENT ON TABLE features.player_clutch_stats IS
'Player performance broken down by leverage situation (clutch stats)';
COMMENT ON COLUMN features.player_clutch_stats.clutch_score IS
'Clutch score: positive = better in high leverage than expected';

CREATE INDEX IF NOT EXISTS idx_clutch_stats_player
ON features.player_clutch_stats (player_id, season);

CREATE INDEX IF NOT EXISTS idx_clutch_stats_season
ON features.player_clutch_stats (season, clutch_score)
WHERE clutch_score IS NOT NULL;


-- View for high leverage situations
CREATE OR REPLACE VIEW features.high_leverage_plays AS
SELECT
    li.*,
    CASE
        WHEN li.is_top THEN 'Top'
        ELSE 'Bottom'
    END AS half_inning
FROM features.game_state_li AS li
WHERE li.leverage_index >= 1.5
ORDER BY li.leverage_index DESC;

COMMENT ON VIEW features.high_leverage_plays IS
'All high-leverage plays (LI >= 1.5) for analysis';


-- View for player clutch leaders
CREATE OR REPLACE VIEW features.clutch_leaders AS
SELECT
    pcs.player_id,
    pcs.season,
    pcs.player_type,
    pcs.pa_high_leverage + pcs.pa_very_high_leverage AS high_leverage_pa,
    pcs.clutch_score,
    pcs.wpa_high + pcs.wpa_very_high AS high_leverage_wpa,
    CASE
        WHEN pcs.clutch_score > 0.1 THEN 'Elite'
        WHEN pcs.clutch_score > 0.05 THEN 'Good'
        WHEN pcs.clutch_score > -0.05 THEN 'Average'
        WHEN pcs.clutch_score > -0.1 THEN 'Poor'
        ELSE 'Chokes'
    END AS clutch_rating
FROM features.player_clutch_stats AS pcs
WHERE
    pcs.clutch_score IS NOT NULL
    AND (pcs.pa_high_leverage + pcs.pa_very_high_leverage) >= 20  -- Minimum sample
ORDER BY pcs.clutch_score DESC;

COMMENT ON VIEW features.clutch_leaders IS
'Player clutch performance ranked by clutch score';


-- Function to calculate Leverage Index from WE matrix
CREATE OR REPLACE FUNCTION features.calculate_leverage_index(
    p_we_current NUMERIC,
    p_inning INTEGER,
    p_is_top BOOLEAN,
    p_outs INTEGER,
    p_base_state VARCHAR(3),
    p_score_diff INTEGER
)
RETURNS NUMERIC(5, 3) AS $$
DECLARE
    v_we_best_outcome NUMERIC(5,4);
    v_we_worst_outcome NUMERIC(5,4);
    v_swing_potential NUMERIC(5,4);
    v_avg_swing NUMERIC(5,4) := 0.046;  -- Historical average swing
BEGIN
    -- Look up best and worst case scenarios
    -- Best: home run or multiple runs scored
    SELECT MAX(home_win_prob) INTO v_we_best_outcome
    FROM features.win_expectancy_matrix
    WHERE inning = p_inning
      AND is_top = p_is_top
      AND score_diff BETWEEN p_score_diff - 4 AND p_score_diff + 4;
    
    -- Worst: out made, no runs
    SELECT MIN(home_win_prob) INTO v_we_worst_outcome
    FROM features.win_expectancy_matrix
    WHERE inning = p_inning
      AND is_top = p_is_top
      AND score_diff BETWEEN p_score_diff - 4 AND p_score_diff + 4;
    
    -- Calculate swing potential
    v_swing_potential := ABS(v_we_best_outcome - v_we_worst_outcome);
    
    -- Calculate LI: swing potential relative to average
    RETURN ROUND(v_swing_potential / NULLIF(v_avg_swing, 0), 3);
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION features.calculate_leverage_index IS
'Calculate Leverage Index from win expectancy matrix';


-- Function to populate LI matrix from WE data
CREATE OR REPLACE FUNCTION features.populate_li_matrix(
    p_season_from INTEGER,
    p_season_to INTEGER DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_inserted INTEGER := 0;
    v_to INTEGER;
BEGIN
    v_to := COALESCE(p_season_to, p_season_from);
    
    -- Insert calculated LI values based on WE matrix swing potential
    INSERT INTO features.leverage_index_matrix (
        inning, is_top, outs, base_state, score_diff,
        leverage_index, importance_rating, swing_potential, total_plays,
        data_source, season_from, season_to
    )
    SELECT 
        we.inning,
        we.is_top,
        we.outs,
        we.base_state,
        we.score_diff,
        -- Calculate LI from swing potential (simplified formula)
        CASE 
            WHEN we.inning >= 9 THEN 
                CASE 
                    WHEN ABS(we.score_diff) <= 1 THEN 2.5  -- Close late games
                    WHEN ABS(we.score_diff) <= 3 THEN 1.8
                    ELSE 0.8
                END
            WHEN we.inning >= 7 THEN
                CASE 
                    WHEN ABS(we.score_diff) <= 1 THEN 1.8  -- Close 7th/8th
                    WHEN ABS(we.score_diff) <= 3 THEN 1.3
                    ELSE 0.7
                END
            ELSE
                CASE 
                    WHEN we.outs = 2 AND we.base_state != '000' THEN 1.4  -- RISP, 2 outs
                    WHEN we.base_state IN ('111', '011', '110') THEN 1.3  -- Bases loaded or RISP
                    WHEN we.base_state != '000' THEN 1.1  -- Runners on
                    ELSE 0.9  -- Bases empty
                END
        END as leverage_index,
        'computed' as importance_rating,
        0.046 as swing_potential,  -- Placeholder
        we.total_games as total_plays,
        'computed',
        p_season_from,
        v_to
    FROM features.win_expectancy_matrix we
    WHERE we.season_from <= v_to
      AND (we.season_to IS NULL OR we.season_to >= p_season_from)
    ON CONFLICT (inning, is_top, outs, base_state, score_diff) 
    DO UPDATE SET
        leverage_index = EXCLUDED.leverage_index,
        swing_potential = EXCLUDED.swing_potential,
        total_plays = EXCLUDED.total_plays,
        season_from = LEAST(features.leverage_index_matrix.season_from, EXCLUDED.season_from),
        season_to = GREATEST(COALESCE(features.leverage_index_matrix.season_to, EXCLUDED.season_to), EXCLUDED.season_to),
        updated_at = NOW();
    
    GET DIAGNOSTICS v_inserted = ROW_COUNT;
    
    -- Update importance ratings
    UPDATE features.leverage_index_matrix
    SET importance_rating = features.get_importance_rating(leverage_index)
    WHERE importance_rating = 'computed' OR importance_rating IS NULL;
    
    RETURN v_inserted;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION features.populate_li_matrix IS
'Populate LI matrix from win expectancy data';
