/*
File: sql/50_features/501_features_live_game_state.sql
Purpose: Live game state features for real-time win probability prediction
Author: Agent Cascade
Date: 2026-04-28
Depends On: sql/30_core/310_core_live_games.sql, sql/50_features/500_features_run_expectancy.sql
Called By: baseball/features/live_state.py, prediction pipeline

Table: features.live_game_state_features
- Materialized view of current game states formatted for model input
- Pre-calculated RE24, leverage index, and win probability inputs
- Grain: One row per game per snapshot

Table: features.win_probability_inputs
- Normalized game states for win probability model
- Historical training data + live inference inputs

Notes:
- Materialized view refreshes on-demand for performance
- Links to raw snapshots for full lineage
- Designed for fast inference (pre-aggregated features)
*/

-- Live game state features (materialized for performance)
CREATE TABLE IF NOT EXISTS features.live_game_state_features (
    feature_id bigserial PRIMARY KEY,
    
    -- Game identification
    game_pk integer NOT NULL,
    season integer NOT NULL,
    snapshot_id bigint REFERENCES raw_mlb.live_feed_snapshots(snapshot_id),
    
    -- Time context
    game_date date,
    extracted_at timestamptz NOT NULL,
    
    -- Game state
    inning smallint NOT NULL,
    is_top_inning boolean NOT NULL,
    outs smallint NOT NULL,
    
    -- Score state
    home_score integer DEFAULT 0,
    away_score integer DEFAULT 0,
    score_differential integer,                -- home - away
    run_diff_bucket varchar(10),               -- 'tied', '1_run', '2_run', '3_plus'
    
    -- Base state
    runner_on_first boolean DEFAULT FALSE,
    runner_on_second boolean DEFAULT FALSE,
    runner_on_third boolean DEFAULT FALSE,
    bases_occupied varchar(3),                 -- '000', '100', etc.
    
    -- Base-out state features
    base_out_state varchar(10),                -- '1_2_3_2' = runners on 1st, 2nd, 3rd, 2 outs
    
    -- Run expectancy
    run_expectancy decimal(6,4),               -- From RE matrix
    
    -- Inning features
    inning_normalized decimal(4,2),            -- inning / 9 (for extra innings > 1.0)
    is_late_game boolean,                      -- inning >= 7
    is_extra_innings boolean,                  -- inning > 9
    
    -- Team context
    home_team_id varchar(10),
    away_team_id varchar(10),
    batting_team_id varchar(10),               -- Who's batting now
    fielding_team_id varchar(10),              -- Who's fielding now
    
    -- Current matchup
    current_pitcher_id varchar(20),
    current_batter_id varchar(20),
    
    -- Game status
    game_status varchar(20),                   -- 'In Progress', 'Final', etc.
    outs_remaining smallint,                   -- 3 - outs (for bottom of 9th+)
    
    -- Win probability inputs (pre-calculated)
    inning_half_score_diff varchar(50),        -- Composite feature: inning_half + score_diff
    base_out_score_state varchar(50),          -- Composite: bases + outs + score_diff
    
    -- Feature vector (for direct model input)
    feature_vector_24 jsonb,                   -- 24-state one-hot + continuous features
    
    -- Metadata
    created_at timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE features.live_game_state_features IS 
    'Pre-calculated live game state features optimized for win probability model input';

-- Indexes for fast inference lookups
CREATE INDEX IF NOT EXISTS idx_live_features_game ON features.live_game_state_features(game_pk);
CREATE INDEX IF NOT EXISTS idx_live_features_snapshot ON features.live_game_state_features(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_live_features_state ON features.live_game_state_features(bases_occupied, outs, score_differential);
CREATE INDEX IF NOT EXISTS idx_live_features_extracted ON features.live_game_state_features(extracted_at DESC);

-- Win probability training/inference inputs
CREATE TABLE IF NOT EXISTS features.win_probability_inputs (
    input_id bigserial PRIMARY KEY,
    
    -- Source identification
    game_pk integer NOT NULL,
    season integer NOT NULL,
    event_id integer,                          -- If from a specific play
    
    -- Game state features
    inning smallint NOT NULL,
    is_top_inning boolean NOT NULL,
    outs smallint NOT NULL,
    
    -- Score features
    home_score integer DEFAULT 0,
    away_score integer DEFAULT 0,
    score_differential integer,
    abs_score_diff integer,                    -- Absolute value for tied/close games
    
    -- Base state (one-hot encoded)
    runner_1b boolean DEFAULT FALSE,
    runner_2b boolean DEFAULT FALSE,
    runner_3b boolean DEFAULT FALSE,
    
    -- Run expectancy
    run_expectancy decimal(6,4),
    
    -- Normalized features (for neural networks)
    inning_norm decimal(4,2),                  -- inning / 9
    outs_norm decimal(3,2),                    -- outs / 3
    score_diff_norm decimal(5,2),              -- score_diff / 10 (clipped)
    
    -- Context features
    batting_team_home boolean,                 -- Is batting team the home team?
    is_final_inning boolean,                   -- 9th inning or later
    outs_remaining smallint,                   -- 3 - outs
    
    -- Outcome (for training data)
    home_won boolean,                          -- Target variable for training
    final_home_score integer,
    final_away_score integer,
    
    -- Source lineage
    source_type varchar(20) DEFAULT 'retrosheet',  -- 'retrosheet' or 'live'
    source_event_id bigint,                    -- Link to original event
    
    created_at timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE features.win_probability_inputs IS 
    'Normalized game states for win probability model training and inference';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_wp_inputs_game ON features.win_probability_inputs(game_pk);
CREATE INDEX IF NOT EXISTS idx_wp_inputs_season ON features.win_probability_inputs(season);
CREATE INDEX IF NOT EXISTS idx_wp_inputs_state ON features.win_probability_inputs(inning, is_top_inning, outs, score_differential);

-- Materialized view: Current game states for fast inference
CREATE MATERIALIZED VIEW IF NOT EXISTS features.mv_current_game_states AS
SELECT 
    lgf.*,
    lg.status_code,
    lg.status_description,
    lg.current_pitcher_name,
    lg.current_batter_name
FROM features.live_game_state_features lgf
JOIN core.live_games lg ON lgf.snapshot_id = lg.snapshot_id
WHERE lgf.extracted_at >= NOW() - INTERVAL '1 day'
ORDER BY lgf.game_pk, lgf.extracted_at DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_current_game ON features.mv_current_game_states(feature_id);

COMMENT ON MATERIALIZED VIEW features.mv_current_game_states IS 
    'Recent game states materialized for fast win probability lookups';

-- Function to extract game state features from live feed
CREATE OR REPLACE FUNCTION features.extract_live_game_state(p_game_pk integer)
RETURNS TABLE(
    game_pk integer,
    inning smallint,
    is_top_inning boolean,
    outs smallint,
    bases_occupied varchar(3),
    run_expectancy decimal(6,4),
    score_differential integer,
    feature_vector jsonb
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        lg.game_pk,
        lg.inning,
        lg.is_top_inning,
        lg.outs,
        CASE 
            WHEN lg.runner_on_first AND lg.runner_on_second AND lg.runner_on_third THEN '111'
            WHEN lg.runner_on_first AND lg.runner_on_second THEN '110'
            WHEN lg.runner_on_first AND lg.runner_on_third THEN '101'
            WHEN lg.runner_on_second AND lg.runner_on_third THEN '011'
            WHEN lg.runner_on_first THEN '100'
            WHEN lg.runner_on_second THEN '010'
            WHEN lg.runner_on_third THEN '001'
            ELSE '000'
        END as bases_occ,
        features.get_run_expectancy(lg.season, 
            CASE 
                WHEN lg.runner_on_first AND lg.runner_on_second AND lg.runner_on_third THEN '111'
                WHEN lg.runner_on_first AND lg.runner_on_second THEN '110'
                WHEN lg.runner_on_first AND lg.runner_on_third THEN '101'
                WHEN lg.runner_on_second AND lg.runner_on_third THEN '011'
                WHEN lg.runner_on_first THEN '100'
                WHEN lg.runner_on_second THEN '010'
                WHEN lg.runner_on_third THEN '001'
                ELSE '000'
            END,
            lg.outs,
            'all'
        ) as re,
        (lg.home_score - lg.away_score) as diff,
        jsonb_build_object(
            'inning', lg.inning,
            'is_top', lg.is_top_inning,
            'outs', lg.outs,
            'runners_1b', lg.runner_on_first,
            'runners_2b', lg.runner_on_second,
            'runners_3b', lg.runner_on_third,
            'home_score', lg.home_score,
            'away_score', lg.away_score
        ) as fv
    FROM core.v_live_games_current lg
    WHERE lg.game_pk = p_game_pk
      AND lg.status_code = 'I';  -- In Progress
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION features.extract_live_game_state IS 
    'Extract normalized game state features for a live game';

-- Function to prepare training data from historical games
CREATE OR REPLACE FUNCTION features.prepare_wp_training_data(
    p_season integer,
    p_sample_limit integer DEFAULT NULL
)
RETURNS TABLE(
    game_pk integer,
    inning smallint,
    is_top_inning boolean,
    outs smallint,
    score_differential integer,
    bases_occupied varchar(3),
    run_expectancy decimal(6,4),
    home_won boolean
) AS $$
BEGIN
    RETURN QUERY
    WITH game_outcomes AS (
        SELECT DISTINCT ON (game_pk)
            game_pk,
            CASE WHEN home_score > away_score THEN TRUE ELSE FALSE END as home_win
        FROM core.live_games
        WHERE season = p_season
          AND status_code = 'F'  -- Final
        ORDER BY game_pk, extracted_at DESC
    )
    SELECT 
        re.game_pk,
        re.inning,
        re.is_top_inning,
        re.outs,
        (re.home_score - re.away_score) as diff,
        re.bases_before,
        features.get_run_expectancy(p_season, re.bases_before, re.outs, 'all'),
        go.home_win
    FROM features.re24_values re
    JOIN game_outcomes go ON re.game_pk = go.game_pk
    WHERE re.season = p_season
      AND re.inning <= 9  -- Regular innings only for training base model
    ORDER BY re.game_pk, re.event_id
    LIMIT COALESCE(p_sample_limit, 100000);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION features.prepare_wp_training_data IS 
    'Prepare historical game states with outcomes for win probability model training';

-- View: Feature summary statistics
CREATE OR REPLACE VIEW features.v_feature_summary AS
SELECT 
    'live_game_state' as feature_set,
    COUNT(*) as total_records,
    COUNT(DISTINCT game_pk) as unique_games,
    MIN(extracted_at) as earliest,
    MAX(extracted_at) as latest
FROM features.live_game_state_features

UNION ALL

SELECT 
    'win_probability_inputs' as feature_set,
    COUNT(*) as total_records,
    COUNT(DISTINCT game_pk) as unique_games,
    MIN(created_at) as earliest,
    MAX(created_at) as latest
FROM features.win_probability_inputs;

COMMENT ON VIEW features.v_feature_summary IS 
    'Summary statistics for feature tables';
