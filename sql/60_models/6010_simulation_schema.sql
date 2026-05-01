-- File: sql/60_models/6010_simulation_schema.sql
-- Purpose: Monte Carlo simulation schema for game state tracking
-- Author: Agent Cascade
-- Date: 2026-04-30
-- Depends On: 6001_models_registry.sql, 6008_inference_functions.sql
-- Called By: baseball/models/simulation.py, baseball models simulate CLI

-- Simulation schema for Monte Carlo game simulation
-- Based on sabermetric Markov chain research (24 base-out states)

CREATE SCHEMA IF NOT EXISTS simulation;

COMMENT ON SCHEMA simulation IS 
'Monte Carlo simulation state tracking and results storage';

-- Simulation runs (top-level tracking)
CREATE TABLE IF NOT EXISTS simulation.runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Model reference
    model_id INTEGER REFERENCES models.registry(id),
    version_id INTEGER REFERENCES models.versions(id),
    
    -- Configuration
    simulation_type VARCHAR(50) NOT NULL 
        CHECK (simulation_type IN ('markov', 'monte_carlo', 'hybrid')),
    num_iterations INTEGER NOT NULL DEFAULT 10000,
    
    -- Game context
    game_id VARCHAR(50),
    season INTEGER,
    starting_inning INTEGER DEFAULT 1,
    starting_is_bottom BOOLEAN DEFAULT FALSE,
    starting_home_score INTEGER DEFAULT 0,
    starting_away_score INTEGER DEFAULT 0,
    starting_outs INTEGER DEFAULT 0,
    starting_bases INTEGER DEFAULT 0,  -- 0-7 bitmask encoding
    
    -- Lineup info (stored as JSON for flexibility)
    home_lineup JSONB,  -- ["player_id_1", "player_id_2", ...]
    away_lineup JSONB,
    starting_pitcher_home VARCHAR(50),
    starting_pitcher_away VARCHAR(50),
    
    -- Weather conditions (affects scoring via run_expectancy_adjustment)
    temperature_f NUMERIC(5,2),           -- Temperature in Fahrenheit
    wind_speed_mph NUMERIC(5,2),            -- Wind speed
    wind_direction VARCHAR(20),           -- in, out, left, right, calm
    humidity_percent NUMERIC(5,2),         -- Relative humidity
    
    -- Park/venue for park factor adjustments
    venue_id VARCHAR(50),
    use_park_factors BOOLEAN DEFAULT TRUE,
    
    -- Execution tracking
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Resource tracking
    duration_seconds INTEGER,
    cpu_time_seconds INTEGER,
    memory_peak_mb INTEGER,
    
    -- Error info
    error_message TEXT,
    
    -- Metadata
    config JSONB,       -- Full simulation configuration
    metadata JSONB      -- User-defined tags, notes, etc.
);

COMMENT ON TABLE simulation.runs IS
'Top-level tracking for each Monte Carlo simulation run';

CREATE INDEX idx_simulation_runs_status ON simulation.runs (status) 
    WHERE status IN ('pending', 'running');
CREATE INDEX idx_simulation_runs_model ON simulation.runs (model_id, created_at DESC);
CREATE INDEX idx_simulation_runs_game ON simulation.runs (game_id, season);

-- Simulation states (per-iteration state tracking)
-- Used for resume/debugging and parallelization
CREATE TABLE IF NOT EXISTS simulation.states (
    state_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES simulation.runs(run_id) ON DELETE CASCADE,
    
    -- Iteration tracking
    iteration INTEGER NOT NULL,
    plate_appearance_number INTEGER DEFAULT 0,
    
    -- Game state (24 base-out state encoding: outs * 8 + base_encoding)
    inning INTEGER NOT NULL,
    is_bottom BOOLEAN NOT NULL DEFAULT FALSE,
    outs INTEGER NOT NULL CHECK (outs >= 0 AND outs <= 3),
    bases INTEGER NOT NULL CHECK (bases >= 0 AND bases <= 7),
    base_out_state INTEGER GENERATED ALWAYS AS (
        outs * 8 + bases
    ) STORED,
    
    -- Score
    home_score INTEGER NOT NULL DEFAULT 0,
    away_score INTEGER NOT NULL DEFAULT 0,
    
    -- Count (for pitch-by-pitch tracking if needed)
    balls INTEGER DEFAULT 0 CHECK (balls >= 0 AND balls <= 4),
    strikes INTEGER DEFAULT 0 CHECK (strikes >= 0 AND strikes <= 3),
    
    -- Current matchup
    batter_id VARCHAR(50),
    pitcher_id VARCHAR(50),
    batter_order_position INTEGER CHECK (batter_order_position BETWEEN 1 AND 9),
    
    -- Team IDs
    batting_team_id VARCHAR(50),
    fielding_team_id VARCHAR(50),
    
    -- Timestamps for replay analysis
    state_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Metadata
    metadata JSONB
);

COMMENT ON TABLE simulation.states IS
'Per-iteration game state snapshots for resume and debugging';
COMMENT ON COLUMN simulation.states.base_out_state IS
'Integer 0-23 encoding: outs * 8 + base_encoding (0=empty, 1=1B, 2=2B, etc.)';

CREATE INDEX idx_simulation_states_run ON simulation.states (run_id, iteration);
CREATE INDEX idx_simulation_states_base_out ON simulation.states (base_out_state);

-- Simulation results (aggregated per iteration)
CREATE TABLE IF NOT EXISTS simulation.results (
    result_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES simulation.runs(run_id) ON DELETE CASCADE,
    
    -- Iteration tracking
    iteration INTEGER NOT NULL,
    
    -- Final state
    final_inning INTEGER,
    final_is_bottom BOOLEAN,
    final_home_score INTEGER,
    final_away_score INTEGER,
    
    -- Outcome
    home_won BOOLEAN,
    is_tie BOOLEAN DEFAULT FALSE,
    is_extra_innings BOOLEAN DEFAULT FALSE,
    
    -- Statistics
    total_plate_appearances INTEGER,
    total_hits INTEGER,
    total_walks INTEGER,
    total_strikeouts INTEGER,
    total_home_runs INTEGER,
    total_runs_scored INTEGER,
    
    -- Pitching
    total_pitches INTEGER,
    
    -- Duration
    duration_ms INTEGER,
    
    UNIQUE (run_id, iteration)
);

COMMENT ON TABLE simulation.results IS
'Final results for each simulation iteration';

CREATE INDEX idx_simulation_results_run ON simulation.results (run_id, iteration);
CREATE INDEX idx_simulation_results_outcome ON simulation.results (run_id, home_won);

-- Transition log (for Markov chain analysis)
CREATE TABLE IF NOT EXISTS simulation.transitions (
    log_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES simulation.runs(run_id) ON DELETE CASCADE,
    
    -- Iteration and PA number
    iteration INTEGER NOT NULL,
    plate_appearance_number INTEGER NOT NULL,
    
    -- States
    from_base_out_state INTEGER NOT NULL CHECK (from_base_out_state BETWEEN 0 AND 23),
    to_base_out_state INTEGER NOT NULL CHECK (to_base_out_state BETWEEN 0 AND 23),
    
    -- Event details
    event_type VARCHAR(50) NOT NULL 
        CHECK (event_type IN ('out', 'walk', 'single', 'double', 'triple', 'home_run', 
                             'error', 'fielders_choice', 'double_play', 'triple_play',
                             'stolen_base', 'caught_stealing', 'passed_ball', 'wild_pitch')),
    
    -- Runs scored on this event
    runs_scored INTEGER NOT NULL DEFAULT 0,
    
    -- Players involved
    batter_id VARCHAR(50),
    pitcher_id VARCHAR(50),
    
    -- Context (from PA features)
    inning INTEGER,
    is_bottom BOOLEAN,
    outs INTEGER,
    bases INTEGER,
    
    -- Timestamp for replay
    event_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE simulation.transitions IS
'Detailed transition log for Markov chain analysis and replay';

CREATE INDEX idx_simulation_transitions_run ON simulation.transitions (run_id, iteration);
CREATE INDEX idx_simulation_transitions_event ON simulation.transitions (event_type);

-- Aggregated results view (for quick queries)
CREATE OR REPLACE VIEW simulation.summary AS
SELECT 
    r.run_id,
    r.simulation_type,
    r.num_iterations,
    r.status,
    r.game_id,
    r.season,
    
    -- Aggregated outcomes
    COUNT(DISTINCT res.iteration) AS completed_iterations,
    SUM(CASE WHEN res.home_won THEN 1 ELSE 0 END) AS home_wins,
    SUM(CASE WHEN NOT res.home_won THEN 1 ELSE 0 END) AS away_wins,
    SUM(CASE WHEN res.is_tie THEN 1 ELSE 0 END) AS ties,
    
    -- Win probability
    ROUND(
        SUM(CASE WHEN res.home_won THEN 1 ELSE 0 END)::numeric / 
        NULLIF(COUNT(*), 0), 
        4
    ) AS home_win_probability,
    
    -- Score statistics
    ROUND(AVG(res.final_home_score), 2) AS mean_home_score,
    ROUND(AVG(res.final_away_score), 2) AS mean_away_score,
    ROUND(STDDEV(res.final_home_score), 2) AS std_home_score,
    ROUND(STDDEV(res.final_away_score), 2) AS std_away_score,
    
    -- Game length
    ROUND(AVG(res.total_plate_appearances), 1) AS mean_total_pas,
    
    -- Duration
    r.duration_seconds

FROM simulation.runs r
LEFT JOIN simulation.results res ON r.run_id = res.run_id
WHERE r.status = 'completed'
GROUP BY r.run_id;

COMMENT ON VIEW simulation.summary IS
'Quick summary of completed simulation runs with aggregated statistics';

-- Function: Initialize simulation
CREATE OR REPLACE FUNCTION simulation.init_run(
    p_model_id INTEGER,
    p_simulation_type VARCHAR(50),
    p_num_iterations INTEGER,
    p_game_id VARCHAR(50) DEFAULT NULL,
    p_season INTEGER DEFAULT NULL,
    p_starting_inning INTEGER DEFAULT 1,
    p_starting_is_bottom BOOLEAN DEFAULT FALSE,
    p_starting_home_score INTEGER DEFAULT 0,
    p_starting_away_score INTEGER DEFAULT 0,
    p_starting_outs INTEGER DEFAULT 0,
    p_starting_bases INTEGER DEFAULT 0,
    p_home_lineup JSONB DEFAULT NULL,
    p_away_lineup JSONB DEFAULT NULL,
    p_config JSONB DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_run_id UUID;
BEGIN
    INSERT INTO simulation.runs (
        model_id,
        simulation_type,
        num_iterations,
        game_id,
        season,
        starting_inning,
        starting_is_bottom,
        starting_home_score,
        starting_away_score,
        starting_outs,
        starting_bases,
        home_lineup,
        away_lineup,
        status,
        started_at,
        config
    ) VALUES (
        p_model_id,
        p_simulation_type,
        p_num_iterations,
        p_game_id,
        p_season,
        p_starting_inning,
        p_starting_is_bottom,
        p_starting_home_score,
        p_starting_away_score,
        p_starting_outs,
        p_starting_bases,
        p_home_lineup,
        p_away_lineup,
        'running',
        NOW(),
        p_config
    )
    RETURNING run_id INTO v_run_id;
    
    RETURN v_run_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Record simulation state
CREATE OR REPLACE FUNCTION simulation.record_state(
    p_run_id UUID,
    p_iteration INTEGER,
    p_plate_appearance_number INTEGER,
    p_inning INTEGER,
    p_is_bottom BOOLEAN,
    p_outs INTEGER,
    p_bases INTEGER,
    p_home_score INTEGER,
    p_away_score INTEGER,
    p_batter_id VARCHAR(50) DEFAULT NULL,
    p_pitcher_id VARCHAR(50) DEFAULT NULL,
    p_batter_order_position INTEGER DEFAULT NULL,
    p_batting_team_id VARCHAR(50) DEFAULT NULL,
    p_fielding_team_id VARCHAR(50) DEFAULT NULL,
    p_metadata JSONB DEFAULT NULL
) RETURNS BIGINT AS $$
DECLARE
    v_state_id BIGINT;
BEGIN
    INSERT INTO simulation.states (
        run_id,
        iteration,
        plate_appearance_number,
        inning,
        is_bottom,
        outs,
        bases,
        home_score,
        away_score,
        batter_id,
        pitcher_id,
        batter_order_position,
        batting_team_id,
        fielding_team_id,
        metadata
    ) VALUES (
        p_run_id, p_iteration, p_plate_appearance_number,
        p_inning, p_is_bottom, p_outs, p_bases,
        p_home_score, p_away_score,
        p_batter_id, p_pitcher_id, p_batter_order_position,
        p_batting_team_id, p_fielding_team_id,
        p_metadata
    )
    RETURNING state_id INTO v_state_id;
    
    RETURN v_state_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Record transition
CREATE OR REPLACE FUNCTION simulation.record_transition(
    p_run_id UUID,
    p_iteration INTEGER,
    p_plate_appearance_number INTEGER,
    p_from_state INTEGER,
    p_to_state INTEGER,
    p_event_type VARCHAR(50),
    p_runs_scored INTEGER DEFAULT 0,
    p_batter_id VARCHAR(50) DEFAULT NULL,
    p_pitcher_id VARCHAR(50) DEFAULT NULL,
    p_inning INTEGER DEFAULT NULL,
    p_is_bottom BOOLEAN DEFAULT NULL,
    p_outs INTEGER DEFAULT NULL,
    p_bases INTEGER DEFAULT NULL
) RETURNS BIGINT AS $$
DECLARE
    v_log_id BIGINT;
BEGIN
    INSERT INTO simulation.transitions (
        run_id,
        iteration,
        plate_appearance_number,
        from_base_out_state,
        to_base_out_state,
        event_type,
        runs_scored,
        batter_id,
        pitcher_id,
        inning,
        is_bottom,
        outs,
        bases
    ) VALUES (
        p_run_id, p_iteration, p_plate_appearance_number,
        p_from_state, p_to_state, p_event_type, p_runs_scored,
        p_batter_id, p_pitcher_id,
        p_inning, p_is_bottom, p_outs, p_bases
    )
    RETURNING log_id INTO v_log_id;
    
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Finalize simulation iteration
CREATE OR REPLACE FUNCTION simulation.finalize_iteration(
    p_run_id UUID,
    p_iteration INTEGER,
    p_final_inning INTEGER,
    p_final_is_bottom BOOLEAN,
    p_final_home_score INTEGER,
    p_final_away_score INTEGER,
    p_total_pas INTEGER DEFAULT NULL,
    p_total_hits INTEGER DEFAULT NULL,
    p_total_walks INTEGER DEFAULT NULL,
    p_duration_ms INTEGER DEFAULT NULL
) RETURNS VOID AS $$
DECLARE
    v_home_won BOOLEAN;
    v_is_tie BOOLEAN;
BEGIN
    v_home_won := p_final_home_score > p_final_away_score;
    v_is_tie := p_final_home_score = p_final_away_score;
    
    INSERT INTO simulation.results (
        run_id,
        iteration,
        final_inning,
        final_is_bottom,
        final_home_score,
        final_away_score,
        home_won,
        is_tie,
        total_plate_appearances,
        total_hits,
        total_walks,
        duration_ms
    ) VALUES (
        p_run_id, p_iteration,
        p_final_inning, p_final_is_bottom,
        p_final_home_score, p_final_away_score,
        v_home_won, v_is_tie,
        p_total_pas, p_total_hits, p_total_walks,
        p_duration_ms
    );
END;
$$ LANGUAGE plpgsql;

-- Function: Complete simulation run
CREATE OR REPLACE FUNCTION simulation.complete_run(
    p_run_id UUID,
    p_duration_seconds INTEGER DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    IF p_error_message IS NOT NULL THEN
        UPDATE simulation.runs
        SET status = 'failed',
            completed_at = NOW(),
            duration_seconds = p_duration_seconds,
            error_message = p_error_message
        WHERE run_id = p_run_id;
    ELSE
        UPDATE simulation.runs
        SET status = 'completed',
            completed_at = NOW(),
            duration_seconds = p_duration_seconds
        WHERE run_id = p_run_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function: Cancel simulation
CREATE OR REPLACE FUNCTION simulation.cancel_run(
    p_run_id UUID,
    p_reason TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    UPDATE simulation.runs
    SET status = 'cancelled',
        completed_at = NOW(),
        error_message = COALESCE(p_reason, 'Cancelled by user')
    WHERE run_id = p_run_id;
END;
$$ LANGUAGE plpgsql;

-- Transition matrix table (for Markov chain simulator)
CREATE TABLE IF NOT EXISTS simulation.transition_matrix (
    matrix_id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models.registry(id),
    
    -- State transition
    from_base_out_state INTEGER NOT NULL CHECK (from_base_out_state BETWEEN 0 AND 23),
    to_base_out_state INTEGER NOT NULL CHECK (to_base_out_state BETWEEN 0 AND 24),
    -- Note: to_state = 24 represents "3 outs, inning over"
    
    -- Event details
    event_type VARCHAR(50) NOT NULL 
        CHECK (event_type IN ('out', 'walk', 'single', 'double', 'triple', 'home_run',
                             'double_play', 'triple_play', 'error')),
    
    -- Probability (from historical data)
    probability NUMERIC(8, 6) NOT NULL CHECK (probability >= 0 AND probability <= 1),
    
    -- Runs scored on this transition
    runs_scored INTEGER NOT NULL DEFAULT 0,
    
    -- Context (for conditional probabilities)
    batter_hand CHAR(1) CHECK (batter_hand IN ('L', 'R', 'S')),
    pitcher_hand CHAR(1) CHECK (pitcher_hand IN ('L', 'R')),
    
    -- Source
    data_source VARCHAR(100),  -- e.g., 're24_2020_2024', 'statcast'
    
    -- Metadata
    total_observations INTEGER,  -- Number of historical observations
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE (model_id, from_base_out_state, to_base_out_state, event_type, 
            batter_hand, pitcher_hand)
);

COMMENT ON TABLE simulation.transition_matrix IS
'Transition probabilities for Markov chain simulation';

CREATE INDEX idx_transition_matrix_lookup 
ON simulation.transition_matrix (model_id, from_base_out_state, batter_hand, pitcher_hand);

-- View: Current transition matrix (most recent for each model)
CREATE OR REPLACE VIEW simulation.current_transition_matrix AS
SELECT DISTINCT ON (model_id, from_base_out_state, to_base_out_state, event_type)
    *
FROM simulation.transition_matrix
ORDER BY model_id, from_base_out_state, to_base_out_state, event_type, created_at DESC;

-- Materialized view: Run expectancy by state (RE24)
CREATE MATERIALIZED VIEW IF NOT EXISTS simulation.re24 AS
WITH base_out_states AS (
    SELECT generate_series(0, 23) AS base_out_state
),
run_expectancies AS (
    SELECT 
        base_out_state,
        AVG(runs_scored) AS expected_runs,
        COUNT(*) AS sample_size
    FROM (
        SELECT 
            outs_before * 8 + start_bases AS base_out_state,
            runs_scored_in_inning AS runs_scored
        FROM features.plate_appearance_examples
        WHERE runs_scored_in_inning IS NOT NULL
    ) sub
    GROUP BY base_out_state
)
SELECT 
    b.base_out_state,
    COALESCE(r.expected_runs, 0.5) AS expected_runs,
    COALESCE(r.sample_size, 0) AS sample_size,
    -- Decode for readability
    (b.base_out_state / 8) AS outs,
    (b.base_out_state % 8) AS base_encoding,
    CASE (b.base_out_state % 8)
        WHEN 0 THEN '___'
        WHEN 1 THEN '1__'
        WHEN 2 THEN '_2_'
        WHEN 3 THEN '12_'
        WHEN 4 THEN '__3'
        WHEN 5 THEN '1_3'
        WHEN 6 THEN '_23'
        WHEN 7 THEN '123'
    END AS bases_loaded
FROM base_out_states b
LEFT JOIN run_expectancies r ON b.base_out_state = r.base_out_state;

CREATE UNIQUE INDEX idx_re24_state ON simulation.re24 (base_out_state);

COMMENT ON MATERIALIZED VIEW simulation.re24 IS
'Run expectancy by base-out state (RE24 matrix). Refresh after new data ingest.';

-- Refresh function for RE24
CREATE OR REPLACE FUNCTION simulation.refresh_re24()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY simulation.re24;
END;
$$ LANGUAGE plpgsql;
