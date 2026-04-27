"""
Database Triggers for Model Automation

Phase 3.2: Database Triggers

Provides PostgreSQL triggers and functions for:
- Auto-updating model registry on training completion
- Logging feature changes
- Triggering retraining workflows
- Tracking model performance degradation

Author: Agent Cascade
Date: April 24, 2026
"""

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- ============================================================================
-- SECTION 1: Model Registry Triggers
-- ============================================================================

-- Function to log model registry changes
CREATE OR REPLACE FUNCTION models.log_registry_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO models.model_training_log (
            model_id,
            operation,
            old_values,
            new_values,
            logged_by
        ) VALUES (
            NEW.id,
            'INSERT',
            NULL,
            jsonb_build_object(
                'target_id', NEW.target_id,
                'model_name', NEW.model_name,
                'model_family', NEW.model_family,
                'is_active', NEW.is_active
            ),
            current_user
        );
        RETURN NEW;
        
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO models.model_training_log (
            model_id,
            operation,
            old_values,
            new_values,
            logged_by
        ) VALUES (
            NEW.id,
            'UPDATE',
            jsonb_build_object(
                'is_active', OLD.is_active,
                'metrics', OLD.metrics
            ),
            jsonb_build_object(
                'is_active', NEW.is_active,
                'metrics', NEW.metrics
            ),
            current_user
        );
        
        -- If model activated, deactivate others for same target
        IF NEW.is_active = true AND OLD.is_active = false THEN
            UPDATE models.model_registry
            SET is_active = false,
                updated_at = NOW()
            WHERE target_id = NEW.target_id
              AND id != NEW.id
              AND is_active = true;
        END IF;
        
        RETURN NEW;
        
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO models.model_training_log (
            model_id,
            operation,
            old_values,
            new_values,
            logged_by
        ) VALUES (
            OLD.id,
            'DELETE',
            jsonb_build_object(
                'target_id', OLD.target_id,
                'model_name', OLD.model_name
            ),
            NULL,
            current_user
        );
        RETURN OLD;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create the log table if it doesn't exist
CREATE TABLE IF NOT EXISTS models.model_training_log (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models.model_registry(id) ON DELETE SET NULL,
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    logged_by VARCHAR(100),
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE models.model_training_log IS 'Audit log for model registry changes';

-- Create trigger on model_registry
DROP TRIGGER IF EXISTS trg_model_registry_audit ON models.model_registry;
CREATE TRIGGER trg_model_registry_audit
    AFTER INSERT OR UPDATE OR DELETE ON models.model_registry
    FOR EACH ROW
    EXECUTE FUNCTION models.log_registry_change();

-- ============================================================================
-- SECTION 2: Feature Importance Tracking Triggers
-- ============================================================================

-- Table for tracking feature importance over time
CREATE TABLE IF NOT EXISTS models.feature_importance_history (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models.model_registry(id) ON DELETE CASCADE,
    feature_name VARCHAR(100) NOT NULL,
    importance_score DECIMAL(10, 8),
    importance_rank INTEGER,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE models.feature_importance_history IS 'Historical tracking of feature importance by model';

-- Function to capture feature importance on model insert
CREATE OR REPLACE FUNCTION models.capture_feature_importance()
RETURNS TRIGGER AS $$
BEGIN
    -- Only capture if feature_importance is present in metadata
    IF NEW.feature_spec IS NOT NULL AND 
       NEW.feature_spec->'feature_importance' IS NOT NULL THEN
        
        INSERT INTO models.feature_importance_history (
            model_id,
            feature_name,
            importance_score,
            importance_rank
        )
        SELECT 
            NEW.id,
            feat->>'feature_name',
            (feat->>'importance_score')::DECIMAL,
            (feat->>'importance_rank')::INTEGER
        FROM jsonb_array_elements(NEW.feature_spec->'feature_importance') AS feat;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for feature importance capture
DROP TRIGGER IF EXISTS trg_capture_feature_importance ON models.model_registry;
CREATE TRIGGER trg_capture_feature_importance
    AFTER INSERT ON models.model_registry
    FOR EACH ROW
    EXECUTE FUNCTION models.capture_feature_importance();

-- ============================================================================
-- SECTION 3: Model Performance Monitoring
-- ============================================================================

-- Table for model performance snapshots
CREATE TABLE IF NOT EXISTS models.model_performance_snapshots (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models.model_registry(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    metric_name VARCHAR(50) NOT NULL,
    metric_value DECIMAL(10, 8) NOT NULL,
    sample_size INTEGER,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE models.model_performance_snapshots IS 'Periodic snapshots of model performance metrics';

-- Create index for efficient querying
CREATE INDEX IF NOT EXISTS idx_perf_snapshots_model_date 
ON models.model_performance_snapshots(model_id, snapshot_date);

-- Function to detect performance degradation
CREATE OR REPLACE FUNCTION models.check_performance_degradation(
    p_model_id INTEGER,
    p_metric_name VARCHAR(50) DEFAULT 'roc_auc',
    p_threshold DECIMAL(10, 8) DEFAULT 0.05
)
RETURNS TABLE (
    degraded BOOLEAN,
    current_value DECIMAL(10, 8),
    previous_value DECIMAL(10, 8),
    drop_amount DECIMAL(10, 8)
) AS $$
BEGIN
    RETURN QUERY
    WITH current_perf AS (
        SELECT metric_value
        FROM models.model_performance_snapshots
        WHERE model_id = p_model_id
          AND metric_name = p_metric_name
        ORDER BY snapshot_date DESC
        LIMIT 1
    ),
    previous_perf AS (
        SELECT metric_value
        FROM models.model_performance_snapshots
        WHERE model_id = p_model_id
          AND metric_name = p_metric_name
        ORDER BY snapshot_date DESC
        OFFSET 1
        LIMIT 1
    )
    SELECT 
        (prev.metric_value - curr.metric_value) > p_threshold AS degraded,
        curr.metric_value AS current_value,
        prev.metric_value AS previous_value,
        (prev.metric_value - curr.metric_value) AS drop_amount
    FROM current_perf curr
    CROSS JOIN previous_perf prev;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SECTION 4: Auto-Training Triggers
-- ============================================================================

-- Table for training jobs queue
CREATE TABLE IF NOT EXISTS models.training_jobs (
    id SERIAL PRIMARY KEY,
    target_id VARCHAR(50) NOT NULL,
    model_family VARCHAR(50) NOT NULL,
    feature_set VARCHAR(50) DEFAULT 'advanced',
    seasons INTEGER[],
    priority INTEGER DEFAULT 5,
    status VARCHAR(20) DEFAULT 'pending' 
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    config_override JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    model_id INTEGER REFERENCES models.model_registry(id) ON DELETE SET NULL
);

COMMENT ON TABLE models.training_jobs IS 'Queue for automated model training jobs';

-- Create indexes for job queue
CREATE INDEX IF NOT EXISTS idx_training_jobs_status_priority 
ON models.training_jobs(status, priority DESC, created_at);

CREATE INDEX IF NOT EXISTS idx_training_jobs_target 
ON models.training_jobs(target_id, status);

-- Function to queue training job on data update
CREATE OR REPLACE FUNCTION models.queue_retraining_job()
RETURNS TRIGGER AS $$
DECLARE
    v_target_id VARCHAR(50);
    v_model_family VARCHAR(50);
BEGIN
    -- Determine target and model family from context
    -- This would be customized based on which table triggered the update
    v_target_id := COALESCE(
        NEW.target_id,
        TG_ARGV[0],
        'swing_decision'
    );
    
    v_model_family := COALESCE(
        TG_ARGV[1],
        'xgboost'
    );
    
    -- Check if job already pending for this target
    IF EXISTS (
        SELECT 1 FROM models.training_jobs
        WHERE target_id = v_target_id
          AND status = 'pending'
          AND created_at > NOW() - INTERVAL '1 hour'
    ) THEN
        -- Skip if job recently queued
        RETURN NEW;
    END IF;
    
    -- Queue new training job
    INSERT INTO models.training_jobs (
        target_id,
        model_family,
        feature_set,
        priority,
        status
    ) VALUES (
        v_target_id,
        v_model_family,
        'advanced',
        5,
        'pending'
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SECTION 5: Scheduled Maintenance Jobs
-- ============================================================================

-- Function to archive old model versions
CREATE OR REPLACE FUNCTION models.archive_old_models(
    p_days_to_keep INTEGER DEFAULT 90
)
RETURNS INTEGER AS $$
DECLARE
    v_archived_count INTEGER := 0;
BEGIN
    -- Mark old inactive models as archived
    UPDATE models.model_registry
    SET 
        is_active = false,
        notes = COALESCE(notes, '') || ' [Auto-archived on ' || NOW()::date || ']'
    WHERE is_active = false
      AND updated_at < NOW() - (p_days_to_keep || ' days')::INTERVAL
      AND (notes IS NULL OR notes NOT LIKE '%[Auto-archived%');
    
    GET DIAGNOSTICS v_archived_count = ROW_COUNT;
    
    RETURN v_archived_count;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old training logs
CREATE OR REPLACE FUNCTION models.cleanup_old_logs(
    p_days_to_keep INTEGER DEFAULT 30
)
RETURNS INTEGER AS $$
DECLARE
    v_deleted_count INTEGER := 0;
BEGIN
    DELETE FROM models.model_training_log
    WHERE logged_at < NOW() - (p_days_to_keep || ' days')::INTERVAL;
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    
    RETURN v_deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Schedule maintenance jobs (requires pg_cron)
-- Note: Run these manually or schedule via pg_cron if available

-- Example pg_cron schedule (uncomment if pg_cron is installed and configured):
-- SELECT cron.schedule('archive-old-models', '0 2 * * 0', 
--     'SELECT models.archive_old_models(90)');
-- 
-- SELECT cron.schedule('cleanup-old-logs', '0 3 * * 0', 
--     'SELECT models.cleanup_old_logs(30)');

-- ============================================================================
-- SECTION 6: Views for Monitoring
-- ============================================================================

-- View: Active models with performance
CREATE OR REPLACE VIEW models.v_active_models_performance AS
SELECT 
    mr.id,
    mr.target_id,
    mr.model_name,
    mr.model_family,
    mr.created_at,
    mr.metrics->>'roc_auc' as roc_auc,
    mr.metrics->>'accuracy' as accuracy,
    mr.metrics->>'log_loss' as log_loss,
    mr.feature_spec->>'feature_set' as feature_set,
    (SELECT COUNT(*) FROM models.model_performance_snapshots 
     WHERE model_id = mr.id) as snapshot_count,
    (SELECT MAX(snapshot_date) FROM models.model_performance_snapshots 
     WHERE model_id = mr.id) as last_snapshot
FROM models.model_registry mr
WHERE mr.is_active = true
ORDER BY mr.target_id, mr.created_at DESC;

COMMENT ON VIEW models.v_active_models_performance IS 'Overview of active models with latest performance metrics';

-- View: Feature importance trends
CREATE OR REPLACE VIEW models.v_feature_importance_trends AS
WITH ranked_features AS (
    SELECT 
        fih.feature_name,
        fih.importance_score,
        fih.importance_rank,
        fih.recorded_at,
        mr.model_family,
        mr.target_id,
        ROW_NUMBER() OVER (
            PARTITION BY fih.feature_name, mr.target_id 
            ORDER BY fih.recorded_at DESC
        ) as rn
    FROM models.feature_importance_history fih
    JOIN models.model_registry mr ON fih.model_id = mr.id
)
SELECT 
    feature_name,
    target_id,
    model_family,
    importance_score as latest_score,
    importance_rank as latest_rank,
    recorded_at as latest_recorded
FROM ranked_features
WHERE rn = 1
ORDER BY target_id, latest_score DESC;

COMMENT ON VIEW models.v_feature_importance_trends IS 'Latest feature importance across all targets';

-- View: Training job queue status
CREATE OR REPLACE VIEW models.v_training_queue_status AS
SELECT 
    status,
    COUNT(*) as job_count,
    MIN(created_at) as oldest_job,
    MAX(created_at) as newest_job
FROM models.training_jobs
GROUP BY status
ORDER BY 
    CASE status 
        WHEN 'pending' THEN 1 
        WHEN 'running' THEN 2 
        WHEN 'completed' THEN 3 
        WHEN 'failed' THEN 4 
        ELSE 5 
    END;

COMMENT ON VIEW models.v_training_queue_status IS 'Summary of training job queue by status';

-- ============================================================================
-- SECTION 7: Helper Functions
-- ============================================================================

-- Function to get next training job
CREATE OR REPLACE FUNCTION models.get_next_training_job()
RETURNS TABLE (
    job_id INTEGER,
    target_id VARCHAR(50),
    model_family VARCHAR(50),
    feature_set VARCHAR(50),
    seasons INTEGER[],
    config_override JSONB
) AS $$
BEGIN
    RETURN QUERY
    UPDATE models.training_jobs
    SET status = 'running',
        started_at = NOW()
    WHERE id = (
        SELECT id 
        FROM models.training_jobs
        WHERE status = 'pending'
        ORDER BY priority DESC, created_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING 
        models.training_jobs.id,
        models.training_jobs.target_id,
        models.training_jobs.model_family,
        models.training_jobs.feature_set,
        models.training_jobs.seasons,
        models.training_jobs.config_override;
END;
$$ LANGUAGE plpgsql;

-- Function to complete training job
CREATE OR REPLACE FUNCTION models.complete_training_job(
    p_job_id INTEGER,
    p_model_id INTEGER,
    p_success BOOLEAN,
    p_error_message TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    UPDATE models.training_jobs
    SET 
        status = CASE WHEN p_success THEN 'completed' ELSE 'failed' END,
        completed_at = NOW(),
        model_id = p_model_id,
        error_message = p_error_message
    WHERE id = p_job_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SECTION 8: Usage Examples
-- ============================================================================

/*
-- Example 1: Check for performance degradation
SELECT * FROM models.check_performance_degradation(1, 'roc_auc', 0.05);

-- Example 2: Get next training job from queue
SELECT * FROM models.get_next_training_job();

-- Example 3: Complete a training job
SELECT models.complete_training_job(1, 123, true);

-- Example 4: Run maintenance
SELECT models.archive_old_models(90);
SELECT models.cleanup_old_logs(30);

-- Example 5: View active models
SELECT * FROM models.v_active_models_performance;

-- Example 6: Check feature importance trends
SELECT * FROM models.v_feature_importance_trends 
WHERE target_id = 'swing_decision' 
LIMIT 20;
*/

-- ============================================================================
-- DOCUMENTATION
-- ============================================================================

COMMENT ON FUNCTION models.log_registry_change() IS 
'Audit trigger function for model_registry changes. Logs all INSERT/UPDATE/DELETE operations.';

COMMENT ON FUNCTION models.capture_feature_importance() IS 
'Captures feature importance from model registry into history table for trend analysis.';

COMMENT ON FUNCTION models.check_performance_degradation(INTEGER, VARCHAR, DECIMAL) IS 
'Checks if model performance has degraded by comparing latest metrics to previous snapshot.';

COMMENT ON FUNCTION models.queue_retraining_job() IS 
'Trigger function to queue retraining jobs when data updates are detected.';

COMMENT ON FUNCTION models.get_next_training_job() IS 
'Atomically fetches and marks the next pending training job as running.';

COMMENT ON FUNCTION models.complete_training_job(INTEGER, INTEGER, BOOLEAN, TEXT) IS 
'Marks a training job as completed or failed with optional error message.';
