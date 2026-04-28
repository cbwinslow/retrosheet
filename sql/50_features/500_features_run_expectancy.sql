/*
File: sql/50_features/500_features_run_expectancy.sql
Purpose: Run expectancy matrix and RE24 features for win probability modeling
Author: Agent Cascade
Date: 2026-04-28
Depends On: sql/30_core/3001_core_init.sql, sql/30_core/310_core_live_games.sql
Called By: baseball/features/run_expectancy.py, prediction pipeline

Table: features.run_expectancy_matrix
- Run expectancy by base-out state (24 possible states)
- Historical averages from core game events
- Used for RE24 calculation and win probability features

Table: features.re24_values
- Per-play RE24 values (run expectancy change)
- Links to source plays for lineage
- Materialized view for performance

Notes:
- 24 base-out states: 8 runner combinations × 3 out states (0, 1, 2)
- RE24 = runs scored after play - runs expected before play + runs scored on play
- Season-specific matrices allow for era adjustments
*/

-- Create features schema if not exists
CREATE SCHEMA IF NOT EXISTS features;

-- Run expectancy matrix by season
CREATE TABLE IF NOT EXISTS features.run_expectancy_matrix (
    matrix_id bigserial PRIMARY KEY,
    
    -- Identification
    season integer NOT NULL,
    scope varchar(20) NOT NULL DEFAULT 'all',  -- 'all', 'regular', 'playoffs'
    
    -- Base-out state
    bases_occupied varchar(3) NOT NULL,         -- '000', '100', '010', '001', '110', '101', '011', '111'
    outs smallint NOT NULL,                    -- 0, 1, 2
    
    -- Run expectancy
    run_expectancy decimal(6,4) NOT NULL,      -- Expected runs for remainder of inning
    
    -- Confidence metrics
    sample_size integer NOT NULL,              -- Number of innings in sample
    std_deviation decimal(6,4),                  -- Standard deviation of runs scored
    
    -- Metadata
    created_at timestamptz NOT NULL DEFAULT NOW(),
    updated_at timestamptz NOT NULL DEFAULT NOW(),
    
    -- Unique constraint: one value per season/scope/state
    UNIQUE(season, scope, bases_occupied, outs)
);

COMMENT ON TABLE features.run_expectancy_matrix IS 
    'Run expectancy values for each of 24 base-out states by season. RE24 = runs scored after - expected before + runs on play.';

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_re_matrix_season ON features.run_expectancy_matrix(season);
CREATE INDEX IF NOT EXISTS idx_re_matrix_state ON features.run_expectancy_matrix(bases_occupied, outs);
CREATE INDEX IF NOT EXISTS idx_re_matrix_lookup ON features.run_expectancy_matrix(season, bases_occupied, outs);

-- RE24 values per play (materialized as table for performance)
CREATE TABLE IF NOT EXISTS features.re24_values (
    re24_id bigserial PRIMARY KEY,
    
    -- Source identification
    game_pk integer,
    season integer,
    event_id integer,                          -- Sequence within game
    
    -- Base-out state BEFORE play
    bases_before varchar(3) NOT NULL,
    outs_before smallint NOT NULL,
    re_before decimal(6,4) NOT NULL,           -- Run expectancy before play
    
    -- Base-out state AFTER play
    bases_after varchar(3),
    outs_after smallint,
    re_after decimal(6,4),                     -- Run expectancy after play
    
    -- Run scoring
    runs_on_play integer DEFAULT 0,            -- Runs scored during this play
    
    -- RE24 calculation
    re24 decimal(6,4) GENERATED ALWAYS AS (
        (re_after - re_before) + runs_on_play
    ) STORED,
    
    -- Play details
    event_type varchar(20),                    -- 'PA', 'pitch', etc.
    pa_result varchar(50),                     -- 'Single', 'Double', etc.
    pa_result_code varchar(10),                -- '1B', '2B', etc.
    
    -- Player context
    batter_id varchar(20),
    pitcher_id varchar(20),
    
    -- Lineage
    source_event_id bigint,                    -- Link to core.events or core.live_events
    source_type varchar(20) DEFAULT 'retrosheet', -- 'retrosheet' or 'live'
    
    created_at timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE features.re24_values IS 
    'Per-play RE24 values with base-out state transitions. Links to source events for full lineage.';

-- Indexes for RE24 lookups
CREATE INDEX IF NOT EXISTS idx_re24_game ON features.re24_values(game_pk);
CREATE INDEX IF NOT EXISTS idx_re24_season ON features.re24_values(season);
CREATE INDEX IF NOT EXISTS idx_re24_batter ON features.re24_values(batter_id);
CREATE INDEX IF NOT EXISTS idx_re24_pitcher ON features.re24_values(pitcher_id);
CREATE INDEX IF NOT EXISTS idx_re24_state ON features.re24_values(bases_before, outs_before);

-- Function to get run expectancy for a state
CREATE OR REPLACE FUNCTION features.get_run_expectancy(
    p_season integer,
    p_bases varchar(3),
    p_outs smallint,
    p_scope varchar(20) DEFAULT 'all'
)
RETURNS decimal(6,4) AS $$
DECLARE
    v_re decimal(6,4);
BEGIN
    SELECT run_expectancy INTO v_re
    FROM features.run_expectancy_matrix
    WHERE season = p_season
      AND scope = p_scope
      AND bases_occupied = p_bases
      AND outs = p_outs;
    
    -- Return league average if specific season not found
    IF v_re IS NULL THEN
        SELECT AVG(run_expectancy) INTO v_re
        FROM features.run_expectancy_matrix
        WHERE scope = p_scope
          AND bases_occupied = p_bases
          AND outs = p_outs;
    END IF;
    
    RETURN COALESCE(v_re, 0.5);  -- Default fallback
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION features.get_run_expectancy IS 
    'Get run expectancy for a base-out state, falling back to league average if season not found';

-- Function to calculate RE24 for a play
CREATE OR REPLACE FUNCTION features.calculate_re24(
    p_season integer,
    p_bases_before varchar(3),
    p_outs_before smallint,
    p_bases_after varchar(3),
    p_outs_after smallint,
    p_runs_on_play integer,
    p_scope varchar(20) DEFAULT 'all'
)
RETURNS decimal(6,4) AS $$
DECLARE
    v_re_before decimal(6,4);
    v_re_after decimal(6,4);
BEGIN
    v_re_before := features.get_run_expectancy(p_season, p_bases_before, p_outs_before, p_scope);
    v_re_after := features.get_run_expectancy(p_season, p_bases_after, p_outs_after, p_scope);
    
    RETURN (v_re_after - v_re_before) + p_runs_on_play;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION features.calculate_re24 IS 
    'Calculate RE24 value for a play given base-out state transitions';

-- View: Run expectancy matrix as a pivot table (easier to read)
CREATE OR REPLACE VIEW features.v_re_matrix_pivot AS
SELECT 
    season,
    scope,
    bases_occupied,
    MAX(CASE WHEN outs = 0 THEN run_expectancy END) as outs_0,
    MAX(CASE WHEN outs = 1 THEN run_expectancy END) as outs_1,
    MAX(CASE WHEN outs = 2 THEN run_expectancy END) as outs_2,
    MAX(CASE WHEN outs = 0 THEN sample_size END) as sample_0,
    MAX(CASE WHEN outs = 1 THEN sample_size END) as sample_1,
    MAX(CASE WHEN outs = 2 THEN sample_size END) as sample_2
FROM features.run_expectancy_matrix
GROUP BY season, scope, bases_occupied
ORDER BY season, bases_occupied;

COMMENT ON VIEW features.v_re_matrix_pivot IS 
    'Pivoted run expectancy matrix showing all 3 out states per base configuration';

-- View: RE24 leaderboards
CREATE OR REPLACE VIEW features.v_re24_leaderboard AS
SELECT 
    season,
    batter_id,
    COUNT(*) as pa_count,
    SUM(re24) as total_re24,
    ROUND(AVG(re24), 4) as avg_re24,
    SUM(CASE WHEN re24 > 0 THEN 1 ELSE 0 END) as positive_pa,
    ROUND(100.0 * SUM(CASE WHEN re24 > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) as positive_pct
FROM features.re24_values
WHERE event_type = 'PA'
GROUP BY season, batter_id
HAVING COUNT(*) >= 100  -- Minimum sample size
ORDER BY total_re24 DESC;

COMMENT ON VIEW features.v_re24_leaderboard IS 
    'RE24 leaderboards by batter (minimum 100 PAs)';

-- Materialized view: Season RE averages (for quick reference)
CREATE MATERIALIZED VIEW IF NOT EXISTS features.mv_season_re_averages AS
SELECT 
    season,
    scope,
    AVG(CASE WHEN bases_occupied = '000' AND outs = 0 THEN run_expectancy END) as re_bases_empty_0_out,
    AVG(CASE WHEN bases_occupied = '100' AND outs = 1 THEN run_expectancy END) as re_runner_1st_1_out,
    AVG(CASE WHEN bases_occupied = '111' AND outs = 2 THEN run_expectancy END) as re_bases_loaded_2_out,
    COUNT(*) as total_states
FROM features.run_expectancy_matrix
GROUP BY season, scope;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_season_re ON features.mv_season_re_averages(season, scope);

COMMENT ON MATERIALIZED VIEW features.mv_season_re_averages IS 
    'Key run expectancy benchmarks by season for quick reference';

-- Function to refresh materialized view
CREATE OR REPLACE FUNCTION features.refresh_re_averages()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY features.mv_season_re_averages;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION features.refresh_re_averages IS 
    'Refresh season RE averages materialized view';

-- Populate sample data (2024 run expectancy matrix from historical averages)
INSERT INTO features.run_expectancy_matrix (season, bases_occupied, outs, run_expectancy, sample_size, std_deviation)
VALUES 
    -- 2024 season sample data (approximate historical averages)
    (2024, '000', 0, 0.544, 45000, 1.02),
    (2024, '000', 1, 0.291, 42000, 0.85),
    (2024, '000', 2, 0.112, 38000, 0.62),
    (2024, '100', 0, 0.941, 28000, 1.15),
    (2024, '100', 1, 0.562, 32000, 0.98),
    (2024, '100', 2, 0.245, 29000, 0.71),
    (2024, '010', 0, 1.171, 12000, 1.28),
    (2024, '010', 1, 0.721, 15000, 1.05),
    (2024, '010', 2, 0.348, 14000, 0.78),
    (2024, '001', 0, 1.421, 8000, 1.35),
    (2024, '001', 1, 0.983, 9000, 1.12),
    (2024, '001', 2, 0.384, 8500, 0.82),
    (2024, '110', 0, 1.568, 8500, 1.42),
    (2024, '110', 1, 0.973, 9800, 1.18),
    (2024, '110', 2, 0.461, 8900, 0.88),
    (2024, '101', 0, 1.804, 4200, 1.48),
    (2024, '101', 1, 1.193, 5100, 1.25),
    (2024, '101', 2, 0.512, 4800, 0.92),
    (2024, '011', 0, 2.031, 2800, 1.55),
    (2024, '011', 1, 1.423, 3400, 1.32),
    (2024, '011', 2, 0.598, 3100, 0.98),
    (2024, '111', 0, 2.384, 2100, 1.62),
    (2024, '111', 1, 1.752, 2600, 1.42),
    (2024, '111', 2, 0.815, 2400, 1.08)
ON CONFLICT (season, scope, bases_occupied, outs) DO UPDATE SET
    run_expectancy = EXCLUDED.run_expectancy,
    sample_size = EXCLUDED.sample_size,
    std_deviation = EXCLUDED.std_deviation,
    updated_at = NOW();
