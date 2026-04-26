/*
File: sql/00_admin/000_admin_pipeline_control.sql
Purpose: Create admin tables for pipeline control and monitoring
Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
Depends On: None (creates schema)
Called By: Scripts/pipelines that need checkpoint tracking

Tables Created:
- admin.pipeline_runs: Track pipeline executions
- admin.pipeline_checkpoints: Resume capability
- admin.pipeline_errors: Error logging

Notes:
- All tables include created_at timestamps
- Checkpoints allow pipeline resume after interruption
- Error logging includes stack traces for debugging
*/

-- Create admin schema if not exists
CREATE SCHEMA IF NOT EXISTS admin;

-- Pipeline runs tracking
CREATE TABLE IF NOT EXISTS admin.pipeline_runs (
    run_id UUID PRIMARY KEY DEFAULT GEN_RANDOM_UUID(),
    command VARCHAR(255) NOT NULL,
    source_system VARCHAR(50),
    parameters JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    rows_processed INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE admin.pipeline_runs IS 'Tracks all pipeline executions with status and timing';
COMMENT ON COLUMN admin.pipeline_runs.run_id IS 'Unique identifier for this pipeline run';
COMMENT ON COLUMN admin.pipeline_runs.command IS 'CLI command that was executed';
COMMENT ON COLUMN admin.pipeline_runs.source_system IS 'Data source being processed (retrosheet, mlb, espn, statcast)';
COMMENT ON COLUMN admin.pipeline_runs.parameters IS 'JSON parameters passed to the command';
COMMENT ON COLUMN admin.pipeline_runs.status IS 'Current status: running, completed, failed, cancelled';
COMMENT ON COLUMN admin.pipeline_runs.started_at IS 'When the pipeline started';
COMMENT ON COLUMN admin.pipeline_runs.completed_at IS 'When the pipeline finished (NULL if running)';
COMMENT ON COLUMN admin.pipeline_runs.error_message IS 'Error details if status is failed';
COMMENT ON COLUMN admin.pipeline_runs.rows_processed IS 'Number of rows processed in this run';
COMMENT ON COLUMN admin.pipeline_runs.metadata IS 'Additional run metadata as JSON';

-- Pipeline checkpoints for resume capability
CREATE TABLE IF NOT EXISTS admin.pipeline_checkpoints (
    checkpoint_id UUID PRIMARY KEY DEFAULT GEN_RANDOM_UUID(),
    run_id UUID NOT NULL REFERENCES admin.pipeline_runs (run_id) ON DELETE CASCADE,
    phase VARCHAR(100) NOT NULL,
    position JSONB NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE admin.pipeline_checkpoints IS 'Checkpoints for pipeline resume capability';
COMMENT ON COLUMN admin.pipeline_checkpoints.checkpoint_id IS 'Unique checkpoint identifier';
COMMENT ON COLUMN admin.pipeline_checkpoints.run_id IS 'Reference to parent pipeline run';
COMMENT ON COLUMN admin.pipeline_checkpoints.phase IS 'Pipeline phase that completed (download, ingest, validate, etc.)';
COMMENT ON COLUMN admin.pipeline_checkpoints.position IS 'JSON state needed to resume from this point';
COMMENT ON COLUMN admin.pipeline_checkpoints.completed_at IS 'When this checkpoint was created';

-- Pipeline error logging
CREATE TABLE IF NOT EXISTS admin.pipeline_errors (
    error_id UUID PRIMARY KEY DEFAULT GEN_RANDOM_UUID(),
    run_id UUID NOT NULL REFERENCES admin.pipeline_runs (run_id) ON DELETE CASCADE,
    phase VARCHAR(100) NOT NULL,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    context JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE admin.pipeline_errors IS 'Detailed error logging for failed pipeline operations';
COMMENT ON COLUMN admin.pipeline_errors.error_id IS 'Unique error identifier';
COMMENT ON COLUMN admin.pipeline_errors.run_id IS 'Reference to pipeline run where error occurred';
COMMENT ON COLUMN admin.pipeline_errors.phase IS 'Pipeline phase when error occurred';
COMMENT ON COLUMN admin.pipeline_errors.error_type IS 'Exception type or error category';
COMMENT ON COLUMN admin.pipeline_errors.error_message IS 'Human-readable error message';
COMMENT ON COLUMN admin.pipeline_errors.stack_trace IS 'Full stack trace for debugging';
COMMENT ON COLUMN admin.pipeline_errors.context IS 'Additional context as JSON';

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON admin.pipeline_runs (status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON admin.pipeline_runs (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_source ON admin.pipeline_runs (source_system);
CREATE INDEX IF NOT EXISTS idx_pipeline_checkpoints_run_id ON admin.pipeline_checkpoints (run_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_errors_run_id ON admin.pipeline_errors (run_id);

-- Trigger to update updated_at on pipeline_runs
CREATE OR REPLACE FUNCTION admin.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_pipeline_runs_updated_at ON admin.pipeline_runs;
CREATE TRIGGER update_pipeline_runs_updated_at
BEFORE UPDATE ON admin.pipeline_runs
FOR EACH ROW
EXECUTE FUNCTION admin.update_updated_at_column();

-- View for recent pipeline runs summary
CREATE OR REPLACE VIEW admin.v_recent_pipeline_runs AS
SELECT
    run_id,
    command,
    source_system,
    status,
    started_at,
    completed_at,
    CASE
        WHEN completed_at IS NOT NULL
            THEN
                EXTRACT(EPOCH FROM (completed_at - started_at))::INTEGER
        ELSE
            EXTRACT(EPOCH FROM (NOW() - started_at))::INTEGER
    END AS duration_seconds,
    rows_processed,
    error_message
FROM admin.pipeline_runs
ORDER BY started_at DESC;

COMMENT ON VIEW admin.v_recent_pipeline_runs IS 'Summary view of recent pipeline runs with duration calculation';
