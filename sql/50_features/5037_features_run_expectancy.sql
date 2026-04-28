/*
File: sql/50_features/5037_features_run_expectancy.sql
Purpose: Run Expectancy matrix storage
Author: Agent cbwinslow/retrosheet
Date: 2026-04-28
Depends On: core.events
Called By: baseball/features/run_expectancy.py

Tables Created:
- features.run_expectancy_matrix (24 base-out states with expected runs)

Notes:
- 24 base-out states = 8 base states × 3 out states
- Season-specific matrices supported (NULL season = all-time average)
- Used by WinExpectancyCalculator and LeverageIndexCalculator
*/

-- Create RE matrix table
CREATE TABLE IF NOT EXISTS features.run_expectancy_matrix (
    id SERIAL PRIMARY KEY,
    base_state SMALLINT NOT NULL CHECK (base_state BETWEEN 0 AND 7),
    outs SMALLINT NOT NULL CHECK (outs BETWEEN 0 AND 2),
    expected_runs NUMERIC(5,3) NOT NULL,
    occurrences INTEGER DEFAULT 0,
    season SMALLINT,  -- NULL = all-time average
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(base_state, outs, season)
);

COMMENT ON TABLE features.run_expectancy_matrix IS 
    'Run expectancy matrix: expected runs from each of 24 base-out states';

COMMENT ON COLUMN features.run_expectancy_matrix.base_state IS 
    'Base state: 0=empty, 1=1st, 2=2nd, 3=3rd, 4=1st+2nd, 5=1st+3rd, 6=2nd+3rd, 7=loaded';

COMMENT ON COLUMN features.run_expectancy_matrix.expected_runs IS 
    'Expected runs for remainder of inning from this state';

COMMENT ON COLUMN features.run_expectancy_matrix.occurrences IS 
    'Number of times this state occurred in historical data';

-- Index for fast lookup
CREATE INDEX IF NOT EXISTS idx_re_matrix_lookup 
    ON features.run_expectancy_matrix(base_state, outs, season);

-- Insert default MLB-average values (approximate)
INSERT INTO features.run_expectancy_matrix (base_state, outs, expected_runs, season, occurrences)
VALUES 
    (0, 0, 0.461, NULL, 0),  -- Bases empty, 0 outs
    (0, 1, 0.243, NULL, 0),  -- Bases empty, 1 out
    (0, 2, 0.095, NULL, 0),  -- Bases empty, 2 outs
    (1, 0, 0.831, NULL, 0),  -- Runner on 1st, 0 outs
    (1, 1, 0.489, NULL, 0),  -- Runner on 1st, 1 out
    (1, 2, 0.214, NULL, 0),  -- Runner on 1st, 2 outs
    (2, 0, 1.068, NULL, 0),  -- Runner on 2nd, 0 outs
    (2, 1, 0.644, NULL, 0),  -- Runner on 2nd, 1 out
    (2, 2, 0.305, NULL, 0),  -- Runner on 2nd, 2 outs
    (3, 0, 1.426, NULL, 0),  -- Runner on 3rd, 0 outs
    (3, 1, 0.864, NULL, 0),  -- Runner on 3rd, 1 out
    (3, 2, 0.413, NULL, 0),  -- Runner on 3rd, 2 outs
    (4, 0, 1.313, NULL, 0),  -- 1st & 2nd, 0 outs
    (4, 1, 0.814, NULL, 0),  -- 1st & 2nd, 1 out
    (4, 2, 0.400, NULL, 0),  -- 1st & 2nd, 2 outs
    (5, 0, 1.741, NULL, 0),  -- 1st & 3rd, 0 outs
    (5, 1, 1.118, NULL, 0),  -- 1st & 3rd, 1 out
    (5, 2, 0.510, NULL, 0),  -- 1st & 3rd, 2 outs
    (6, 0, 1.844, NULL, 0),  -- 2nd & 3rd, 0 outs
    (6, 1, 1.152, NULL, 0),  -- 2nd & 3rd, 1 out
    (6, 2, 0.494, NULL, 0),  -- 2nd & 3rd, 2 outs
    (7, 0, 2.292, NULL, 0),  -- Bases loaded, 0 outs
    (7, 1, 1.542, NULL, 0),  -- Bases loaded, 1 out
    (7, 2, 0.747, NULL, 0)   -- Bases loaded, 2 outs
ON CONFLICT (base_state, outs, season) DO UPDATE SET
    expected_runs = EXCLUDED.expected_runs,
    computed_at = CURRENT_TIMESTAMP;
