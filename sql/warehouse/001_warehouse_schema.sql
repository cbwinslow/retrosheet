/*
File: sql/warehouse/001_warehouse_schema.sql
Purpose: Warehouse rebuild orchestration schema and logging infrastructure
Author: Agent Cascade
Date: 2026-04-24
Depends On: core schema, existing procedure patterns in codebase
Called By: scripts/rebuild_warehouse.sh

Schemas Created:
- warehouse (orchestration and logging tables)

Tables Created:
- warehouse.rebuild_log (per-phase execution log)
- warehouse.rebuild_runs (top-level run tracking)

Functions Created:
- warehouse.log_phase_start()
- warehouse.log_phase_end()
- warehouse.get_last_successful_phase()

Notes:
- All phases are idempotent (can be re-run safely)
- Per-phase commits allow resume from failure
- Supports both full rebuild and resume modes
*/

-- ================================================================================
-- WAREHOUSE ORCHESTRATION SCHEMA
-- ================================================================================

CREATE SCHEMA IF NOT EXISTS warehouse;

COMMENT ON SCHEMA warehouse IS 'Warehouse rebuild orchestration and logging';

-- ================================================================================
-- REBUILD RUN TRACKING (top-level)
-- ================================================================================

CREATE TABLE IF NOT EXISTS warehouse.rebuild_runs (
    run_id BIGSERIAL PRIMARY KEY,
    run_mode VARCHAR(20) NOT NULL DEFAULT 'full',  -- 'full', 'resume', 'quick'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'running',  -- 'running', 'completed', 'failed', 'aborted'
    target_seasons INT[],  -- NULL = all seasons
    error_message TEXT,
    run_metadata JSONB DEFAULT '{}',
    created_by VARCHAR(100) DEFAULT CURRENT_USER
);

COMMENT ON TABLE warehouse.rebuild_runs IS 'Top-level tracking for warehouse rebuild operations';
COMMENT ON COLUMN warehouse.rebuild_runs.run_id IS 'Unique identifier for each rebuild run';
COMMENT ON COLUMN warehouse.rebuild_runs.run_mode IS 'full=all phases, resume=from last failure, quick=skip expensive ops';
COMMENT ON COLUMN warehouse.rebuild_runs.status IS 'Current state of the rebuild run';
COMMENT ON COLUMN warehouse.rebuild_runs.target_seasons IS 'Optional array of specific seasons to rebuild';

-- ================================================================================
-- PER-PHASE EXECUTION LOG
-- ================================================================================

CREATE TABLE IF NOT EXISTS warehouse.rebuild_log (
    log_id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES warehouse.rebuild_runs(run_id),
    phase VARCHAR(50) NOT NULL,  -- 'raw_load', 'core_build', 'bridge_sync', 'feature_build', 'model_prep'
    phase_order INT NOT NULL,
    status VARCHAR(20) DEFAULT 'running',  -- 'running', 'completed', 'failed', 'skipped'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    rows_affected BIGINT,
    execution_time_ms BIGINT,  -- calculated on completion
    error_message TEXT,
    phase_metadata JSONB DEFAULT '{}'
);

COMMENT ON TABLE warehouse.rebuild_log IS 'Per-phase execution log for warehouse rebuilds';
COMMENT ON COLUMN warehouse.rebuild_log.phase IS 'Name of the rebuild phase';
COMMENT ON COLUMN warehouse.rebuild_log.phase_order IS 'Execution order within the run (1, 2, 3, ...)';
COMMENT ON COLUMN warehouse.rebuild_log.rows_affected IS 'Number of rows inserted/updated in this phase';

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_rebuild_log_run_id ON warehouse.rebuild_log(run_id);
CREATE INDEX IF NOT EXISTS idx_rebuild_log_phase ON warehouse.rebuild_log(phase);
CREATE INDEX IF NOT EXISTS idx_rebuild_runs_status ON warehouse.rebuild_runs(status);

-- ================================================================================
-- HELPER FUNCTIONS
-- ================================================================================

-- Log phase start
CREATE OR REPLACE FUNCTION warehouse.log_phase_start(
    p_run_id BIGINT,
    p_phase VARCHAR(50),
    p_phase_order INT,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_log_id BIGINT;
BEGIN
    INSERT INTO warehouse.rebuild_log (run_id, phase, phase_order, status, phase_metadata)
    VALUES (p_run_id, p_phase, p_phase_order, 'running', p_metadata)
    RETURNING log_id INTO v_log_id;
    
    RAISE NOTICE '[Phase %] Started: %', p_phase_order, p_phase;
    
    RETURN v_log_id;
END;
$$;

COMMENT ON FUNCTION warehouse.log_phase_start IS 'Log the start of a rebuild phase';

-- Log phase end
CREATE OR REPLACE FUNCTION warehouse.log_phase_end(
    p_log_id BIGINT,
    p_status VARCHAR(20),
    p_rows_affected BIGINT DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_start_time TIMESTAMP WITH TIME ZONE;
    v_exec_time_ms BIGINT;
BEGIN
    -- Get start time for duration calculation
    SELECT started_at INTO v_start_time 
    FROM warehouse.rebuild_log 
    WHERE log_id = p_log_id;
    
    v_exec_time_ms := EXTRACT(EPOCH FROM (NOW() - v_start_time)) * 1000;
    
    UPDATE warehouse.rebuild_log
    SET status = p_status,
        completed_at = NOW(),
        rows_affected = p_rows_affected,
        execution_time_ms = v_exec_time_ms,
        error_message = p_error_message
    WHERE log_id = p_log_id;
    
    IF p_status = 'completed' THEN
        RAISE NOTICE '[Phase Complete] % rows in % ms', p_rows_affected, v_exec_time_ms;
    ELSIF p_status = 'failed' THEN
        RAISE NOTICE '[Phase Failed] Error: %', p_error_message;
    END IF;
END;
$$;

COMMENT ON FUNCTION warehouse.log_phase_end IS 'Log the completion or failure of a rebuild phase';

-- Get last successful phase for resume mode
CREATE OR REPLACE FUNCTION warehouse.get_last_successful_phase(
    p_run_mode VARCHAR(20) DEFAULT 'resume'
)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    v_last_phase INT;
BEGIN
    IF p_run_mode = 'resume' THEN
        SELECT COALESCE(MAX(phase_order), 0)
        INTO v_last_phase
        FROM warehouse.rebuild_log l
        JOIN warehouse.rebuild_runs r ON l.run_id = r.run_id
        WHERE r.status = 'failed'
          AND l.status = 'completed'
          AND r.run_id = (
              SELECT MAX(run_id) FROM warehouse.rebuild_runs WHERE status = 'failed'
          );
    ELSE
        v_last_phase := 0;  -- Start from beginning for full rebuild
    END IF;
    
    RETURN v_last_phase;
END;
$$;

COMMENT ON FUNCTION warehouse.get_last_successful_phase IS 'Determine where to resume from in resume mode';
