/*
File: sql/60_models/600_models_registry.sql
Purpose: Model registry for tracking trained ML models
Author: Agent Cascade
Date: 2026-04-28
Depends On: sql/30_core/3001_core_init.sql
Called By: baseball/models/registry.py, training.py, inference.py

Table: models.registry
- Central registry for all trained models
- Versioned model artifacts with lineage tracking
- Performance metrics and metadata
- Supports model promotion (staging -> production -> archived)

Notes:
- model_version uses semantic versioning (e.g., "1.0.0")
- artifact_path should point to persistent storage (S3, local, etc.)
- training_metadata stores hyperparameters and config as JSONB
*/

-- Create models schema if not exists
CREATE SCHEMA IF NOT EXISTS models;

-- Model registry table
CREATE TABLE IF NOT EXISTS models.registry (
    model_id bigserial PRIMARY KEY,
    
    -- Model identification
    model_name varchar(100) NOT NULL,        -- e.g., 'win_probability', 'run_expectancy'
    model_version varchar(20) NOT NULL,        -- e.g., '1.0.0'
    model_type varchar(50) NOT NULL,           -- 'classification', 'regression', 'time_series'
    
    -- Training metadata
    training_date timestamptz NOT NULL DEFAULT NOW(),
    training_dataset varchar(200),             -- Dataset identifier
    training_start_date date,                  -- Data range used
    training_end_date date,
    
    -- Hyperparameters and config
    hyperparameters jsonb,                     -- Model hyperparameters
    feature_set jsonb,                         -- Features used (list)
    training_config jsonb,                     -- Training configuration
    
    -- Performance metrics
    primary_metric varchar(50),                -- e.g., 'log_loss', 'rmse', 'accuracy'
    primary_metric_value decimal(8,6),         -- Metric value
    validation_metrics jsonb,                  -- Full metrics dict
    
    -- Cross-validation results
    cv_folds integer,                          -- Number of CV folds
    cv_mean decimal(8,6),                      -- Mean CV score
    cv_std decimal(8,6),                       -- CV standard deviation
    
    -- Model artifact
    artifact_path varchar(500),                -- Path to serialized model
    artifact_hash varchar(64),                 -- SHA-256 of artifact
    artifact_size_bytes bigint,                -- Size of model file
    
    -- Framework info
    framework varchar(50),                     -- 'sklearn', 'xgboost', 'pytorch', etc.
    framework_version varchar(20),
    
    -- Status and deployment
    status varchar(20) NOT NULL DEFAULT 'staging',  -- 'staging', 'production', 'archived', 'failed'
    promoted_at timestamptz,                   -- When promoted to production
    promoted_by varchar(100),
    
    -- Lineage
    training_run_id bigint,                    -- Link to training run
    
    -- Audit
    created_at timestamptz NOT NULL DEFAULT NOW(),
    updated_at timestamptz NOT NULL DEFAULT NOW(),
    created_by varchar(100) DEFAULT current_user,
    
    -- Unique constraint: name + version
    UNIQUE(model_name, model_version)
);

COMMENT ON TABLE models.registry IS 
    'Central registry for all trained ML models with versioning, lineage, and deployment status';

-- Indexes for model lookups
CREATE INDEX IF NOT EXISTS idx_registry_name ON models.registry(model_name);
CREATE INDEX IF NOT EXISTS idx_registry_status ON models.registry(status) WHERE status = 'production';
CREATE INDEX IF NOT EXISTS idx_registry_type ON models.registry(model_type);
CREATE INDEX IF NOT EXISTS idx_registry_training ON models.registry(training_date);
CREATE INDEX IF NOT EXISTS idx_registry_lookup ON models.registry(model_name, status) WHERE status = 'production';

-- Composite index for latest model query
CREATE INDEX IF NOT EXISTS idx_registry_latest ON models.registry(model_name, training_date DESC);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION models.update_registry_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_registry_updated ON models.registry;
CREATE TRIGGER trg_registry_updated
    BEFORE UPDATE ON models.registry
    FOR EACH ROW
    EXECUTE FUNCTION models.update_registry_timestamp();

-- View: Production models (latest version per model)
CREATE OR REPLACE VIEW models.v_production_models AS
SELECT DISTINCT ON (model_name)
    *
FROM models.registry
WHERE status = 'production'
ORDER BY model_name, training_date DESC;

COMMENT ON VIEW models.v_production_models IS 
    'Latest production model for each model type';

-- View: Model version history
CREATE OR REPLACE VIEW models.v_model_history AS
SELECT 
    model_name,
    model_version,
    model_type,
    status,
    training_date,
    primary_metric,
    primary_metric_value,
    CASE 
        WHEN status = 'production' THEN '✓ Active'
        WHEN status = 'staging' THEN '⚡ Testing'
        WHEN status = 'archived' THEN '✗ Archived'
        ELSE status
    END as status_display
FROM models.registry
ORDER BY model_name, training_date DESC;

COMMENT ON VIEW models.v_model_history IS 
    'Complete model version history with status indicators';

-- Function to get latest production model
CREATE OR REPLACE FUNCTION models.get_production_model(p_model_name varchar)
RETURNS TABLE(
    model_id bigint,
    model_version varchar,
    artifact_path varchar,
    primary_metric_value decimal
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.model_id,
        r.model_version,
        r.artifact_path,
        r.primary_metric_value
    FROM models.registry r
    WHERE r.model_name = p_model_name
      AND r.status = 'production'
    ORDER BY r.training_date DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION models.get_production_model IS 
    'Get the latest production model for a given model name';

-- Function to register a new model
CREATE OR REPLACE FUNCTION models.register_model(
    p_model_name varchar,
    p_model_version varchar,
    p_model_type varchar,
    p_artifact_path varchar,
    p_primary_metric varchar,
    p_primary_metric_value decimal,
    p_hyperparameters jsonb DEFAULT '{}',
    p_feature_set jsonb DEFAULT '[]',
    p_training_config jsonb DEFAULT '{}',
    p_validation_metrics jsonb DEFAULT '{}'
)
RETURNS bigint AS $$
DECLARE
    v_model_id bigint;
BEGIN
    INSERT INTO models.registry (
        model_name,
        model_version,
        model_type,
        artifact_path,
        primary_metric,
        primary_metric_value,
        hyperparameters,
        feature_set,
        training_config,
        validation_metrics,
        status
    ) VALUES (
        p_model_name,
        p_model_version,
        p_model_type,
        p_artifact_path,
        p_primary_metric,
        p_primary_metric_value,
        p_hyperparameters,
        p_feature_set,
        p_training_config,
        p_validation_metrics,
        'staging'
    )
    ON CONFLICT (model_name, model_version) DO UPDATE SET
        artifact_path = EXCLUDED.artifact_path,
        primary_metric_value = EXCLUDED.primary_metric_value,
        validation_metrics = EXCLUDED.validation_metrics,
        updated_at = NOW()
    RETURNING model_id INTO v_model_id;
    
    RETURN v_model_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION models.register_model IS 
    'Register a new model or update existing model version';

-- Function to promote model to production
CREATE OR REPLACE FUNCTION models.promote_model(
    p_model_id bigint,
    p_promoted_by varchar DEFAULT current_user
)
RETURNS boolean AS $$
BEGIN
    -- Archive current production model of same type
    UPDATE models.registry
    SET status = 'archived',
        updated_at = NOW()
    WHERE model_name = (SELECT model_name FROM models.registry WHERE model_id = p_model_id)
      AND status = 'production';
    
    -- Promote new model
    UPDATE models.registry
    SET status = 'production',
        promoted_at = NOW(),
        promoted_by = p_promoted_by,
        updated_at = NOW()
    WHERE model_id = p_model_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION models.promote_model IS 
    'Promote a model to production (archives current production model)';

-- Table: Model training runs for detailed lineage
CREATE TABLE IF NOT EXISTS models.training_runs (
    run_id bigserial PRIMARY KEY,
    
    -- Run identification
    model_name varchar(100) NOT NULL,
    model_version varchar(20) NOT NULL,
    
    -- Training execution
    started_at timestamptz NOT NULL DEFAULT NOW(),
    completed_at timestamptz,
    status varchar(20) DEFAULT 'running',       -- 'running', 'completed', 'failed'
    
    -- Configuration
    config jsonb,                              -- Full training configuration
    
    -- Resources
    duration_seconds integer,                  -- Training time
    cpu_hours decimal(6,2),                    -- CPU usage
    memory_gb decimal(6,2),                    -- Peak memory
    
    -- Logs
    log_path varchar(500),                     -- Path to training logs
    error_message text,                        -- If failed
    
    -- Link to registered model
    model_id bigint REFERENCES models.registry(model_id),
    
    created_at timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE models.training_runs IS 
    'Detailed training run logs for model lineage and reproducibility';

CREATE INDEX IF NOT EXISTS idx_training_runs_model ON models.training_runs(model_name, model_version);
CREATE INDEX IF NOT EXISTS idx_training_runs_status ON models.training_runs(status) WHERE status = 'running';

-- View: Active training runs
CREATE OR REPLACE VIEW models.v_active_training_runs AS
SELECT 
    run_id,
    model_name,
    model_version,
    started_at,
    NOW() - started_at as elapsed,
    config->>'feature_set' as features
FROM models.training_runs
WHERE status = 'running'
ORDER BY started_at;

COMMENT ON VIEW models.v_active_training_runs IS 
    'Currently running training jobs';
