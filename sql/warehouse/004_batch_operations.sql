/*
File: sql/warehouse/004_batch_operations.sql
Purpose: Track long-running batch operations with resume capability
Author: Agent Cascade
Date: 2026-04-24
Depends On: sql/warehouse/001_warehouse_schema.sql
Called By: Batch processing scripts, feature engineering pipelines

Tables Created:
- warehouse.batch_operations: Resume-capable batch processing tracking

Notes:
- Supports resume from failure for long operations
- Tracks row counts for validation
- Integrates with warehouse.rebuild_runs
*/

-- Batch operations table for resume capability
CREATE TABLE IF NOT EXISTS warehouse.batch_operations (
    batch_id BIGSERIAL PRIMARY KEY,
    batch_name TEXT NOT NULL,
    operation_type TEXT NOT NULL CHECK (operation_type IN (
        'feature_engineering',
        'data_loading',
        'model_training',
        'inference',
        'analysis'
    )),
    
    -- Target table/object being processed
    target_schema TEXT NOT NULL,
    target_table TEXT NOT NULL,
    
    -- Resume tracking
    last_processed_id BIGINT,           -- Last primary key processed
    total_rows BIGINT,                  -- Total rows expected
    processed_rows BIGINT DEFAULT 0,    -- Rows actually processed
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN (
        'running', 'completed', 'failed', 'paused'
    )),
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Error tracking
    error_message TEXT,
    retry_count INT DEFAULT 0,
    
    -- Link to parent run
    run_id BIGINT REFERENCES warehouse.rebuild_runs(run_id) ON DELETE SET NULL,
    
    -- Additional metadata
    batch_params JSONB DEFAULT '{}',
    validation_checksum TEXT
);

-- Indexes for resume queries
CREATE INDEX IF NOT EXISTS idx_batch_operations_status 
ON warehouse.batch_operations(status, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_batch_operations_target 
ON warehouse.batch_operations(target_schema, target_table, status);

CREATE INDEX IF NOT EXISTS idx_batch_operations_resume 
ON warehouse.batch_operations(batch_name, status) 
WHERE status IN ('running', 'failed', 'paused');

-- Comments
COMMENT ON TABLE warehouse.batch_operations IS 
    'Resume-capable batch processing tracking for long-running operations';

COMMENT ON COLUMN warehouse.batch_operations.last_processed_id IS 
    'Primary key of last processed row - used for resume after failure';

COMMENT ON COLUMN warehouse.batch_operations.validation_checksum IS 
    'MD5 or SHA-256 checksum of processed data for integrity validation';

-- Function: Get resumable batch
CREATE OR REPLACE FUNCTION warehouse.get_resumable_batch(
    p_batch_name TEXT,
    p_target_schema TEXT,
    p_target_table TEXT
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_batch_id BIGINT;
BEGIN
    SELECT batch_id INTO v_batch_id
    FROM warehouse.batch_operations
    WHERE batch_name = p_batch_name
      AND target_schema = p_target_schema
      AND target_table = p_target_table
      AND status IN ('running', 'failed', 'paused')
    ORDER BY started_at DESC
    LIMIT 1;
    
    RETURN v_batch_id;
END;
$$;

COMMENT ON FUNCTION warehouse.get_resumable_batch IS 
    'Find the most recent incomplete batch for resume';

-- Function: Update batch progress
CREATE OR REPLACE FUNCTION warehouse.update_batch_progress(
    p_batch_id BIGINT,
    p_last_processed_id BIGINT,
    p_processed_rows BIGINT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE warehouse.batch_operations
    SET last_processed_id = p_last_processed_id,
        processed_rows = p_processed_rows,
        status = CASE 
            WHEN p_processed_rows >= total_rows THEN 'completed'
            ELSE 'running'
        END,
        completed_at = CASE 
            WHEN p_processed_rows >= total_rows THEN NOW()
            ELSE completed_at
        END
    WHERE batch_id = p_batch_id;
END;
$$;

COMMENT ON FUNCTION warehouse.update_batch_progress IS 
    'Update batch progress during processing - call periodically for resume capability';

-- View: Active batches summary
CREATE OR REPLACE VIEW warehouse.active_batches AS
SELECT 
    batch_id,
    batch_name,
    operation_type,
    target_schema || '.' || target_table as target_object,
    status,
    processed_rows,
    total_rows,
    ROUND(100.0 * processed_rows / NULLIF(total_rows, 0), 2) as pct_complete,
    started_at,
    NOW() - started_at as elapsed_time,
    retry_count
FROM warehouse.batch_operations
WHERE status IN ('running', 'paused')
ORDER BY started_at;

COMMENT ON VIEW warehouse.active_batches IS 
    'Currently running or paused batches with progress percentages';
