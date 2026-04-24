/*
⚠️  DEPRECATED - DO NOT USE ⚠️

This file creates redundant tables that duplicate existing infrastructure:
- framework.log → Use warehouse.rebuild_log instead
- framework.experiments → Use warehouse.rebuild_runs instead  
- framework.plugins → Use Python plugin registry instead
- framework.model_registry → Use models.model_registry instead
- framework.feature_registry → Use features_pitch.feature_registry instead

Only framework.batches has unique value - use warehouse.batch_operations instead.

See: docs/WORKFLOW_VALIDATION_REPORT.md for analysis

File: sql/framework/001_framework_schema.sql
Purpose: [DEPRECATED] Framework extension schema - DO NOT APPLY
Author: Agent Cascade
Date: 2026-04-24
Status: DEPRECATED - DO NOT RUN
Depends On: sql/warehouse/001_warehouse_schema.sql
Called By: [DEPRECATED]

Tables Created:
- framework.log: Structured logging for all framework operations
- framework.experiments: Experiment tracking with config hashes
- framework.plugins: Plugin registry for custom models and features
- framework.batches: Batch processing tracking with resume capability
- framework.model_registry: Model versioning and metadata
- framework.feature_registry: Feature versioning and dependencies

Notes:
- All tables have created_at/updated_at triggers
- Config hashes use MD5 for quick comparison
- Experiment results stored as JSONB for flexibility
- Plugin system supports Python and SQL extensions
- Batch processing supports resume from failure
*/

-- Create framework schema
CREATE SCHEMA IF NOT EXISTS framework;

-- Framework log table (structured logging)
CREATE TABLE IF NOT EXISTS framework.log (
    log_id SERIAL PRIMARY KEY,
    log_level TEXT NOT NULL CHECK (log_level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    component TEXT NOT NULL,  -- e.g., 'model', 'feature', 'data_loader', 'experiment'
    operation TEXT NOT NULL,  -- e.g., 'train', 'predict', 'transform', 'load'
    message TEXT NOT NULL,
    details JSONB,  -- Structured data: params, metrics, row counts, etc.
    run_id INTEGER REFERENCES warehouse.rebuild_runs(run_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_file TEXT,  -- Python file or SQL file generating the log
    line_number INTEGER
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_framework_log_component ON framework.log(component, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_framework_log_level ON framework.log(log_level, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_framework_log_run ON framework.log(run_id) WHERE run_id IS NOT NULL;

COMMENT ON TABLE framework.log IS 'Structured logging for all framework operations - queryable, persistent, auditable';

-- Experiment tracking table
CREATE TABLE IF NOT EXISTS framework.experiments (
    experiment_id SERIAL PRIMARY KEY,
    experiment_name TEXT NOT NULL,
    experiment_type TEXT NOT NULL CHECK (experiment_type IN ('training', 'inference', 'evaluation', 'feature_engineering', 'data_processing')),
    config_hash TEXT NOT NULL,  -- MD5 hash of config for reproducibility
    config JSONB NOT NULL,  -- Full configuration
    data_version TEXT,  -- Git commit or data timestamp
    model_version TEXT,  -- Model identifier
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds NUMERIC,
    results JSONB,  -- Metrics, predictions, artifacts
    error_message TEXT,
    git_commit TEXT,  -- Repository state
    created_by TEXT DEFAULT CURRENT_USER,
    tags TEXT[]  -- For filtering: ['pitch_model', 'xgboost', '2025_season']
);

CREATE INDEX IF NOT EXISTS idx_framework_experiments_name ON framework.experiments(experiment_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_framework_experiments_hash ON framework.experiments(config_hash);
CREATE INDEX IF NOT EXISTS idx_framework_experiments_tags ON framework.experiments USING GIN(tags);

COMMENT ON TABLE framework.experiments IS 'Experiment tracking with full config, results, and reproducibility info';

-- Plugin registry
CREATE TABLE IF NOT EXISTS framework.plugins (
    plugin_id SERIAL PRIMARY KEY,
    plugin_name TEXT NOT NULL UNIQUE,
    plugin_type TEXT NOT NULL CHECK (plugin_type IN ('model', 'feature', 'data_loader', 'transformer', 'metric')),
    plugin_class TEXT NOT NULL,  -- Python class path: 'my_plugin.MyModel'
    plugin_file TEXT,  -- Path to plugin file
    version TEXT DEFAULT '1.0.0',
    description TEXT,
    config_schema JSONB,  -- JSONSchema for config validation
    dependencies TEXT[],  -- Other plugins or packages required
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    registered_by TEXT DEFAULT CURRENT_USER
);

CREATE INDEX IF NOT EXISTS idx_framework_plugins_type ON framework.plugins(plugin_type, is_active);

COMMENT ON TABLE framework.plugins IS 'Plugin registry for custom models, features, and extensions';

-- Batch processing tracking
CREATE TABLE IF NOT EXISTS framework.batches (
    batch_id SERIAL PRIMARY KEY,
    batch_name TEXT NOT NULL,
    operation TEXT NOT NULL,  -- e.g., 'load_statcast', 'compute_features'
    total_items INTEGER NOT NULL,
    processed_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'paused')),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    last_processed_id TEXT,  -- For resume: last primary key processed
    checkpoint_data JSONB,  -- Arbitrary resume state
    experiment_id INTEGER REFERENCES framework.experiments(experiment_id) ON DELETE SET NULL,
    error_log TEXT[]  -- Array of error messages
);

CREATE INDEX IF NOT EXISTS idx_framework_batches_status ON framework.batches(status, started_at);
CREATE INDEX IF NOT EXISTS idx_framework_batches_exp ON framework.batches(experiment_id);

COMMENT ON TABLE framework.batches IS 'Batch processing with resume capability and progress tracking';

-- Model registry
CREATE TABLE IF NOT EXISTS framework.model_registry (
    model_id SERIAL PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    model_type TEXT NOT NULL CHECK (model_type IN ('sklearn', 'xgboost', 'pytorch', 'tensorflow', 'custom')),
    training_experiment_id INTEGER REFERENCES framework.experiments(experiment_id),
    artifact_path TEXT,  -- Path to saved model file
    hyperparameters JSONB,
    feature_set TEXT[],  -- List of features used
    metrics JSONB,  -- Training/validation metrics
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(model_name, model_version)
);

CREATE INDEX IF NOT EXISTS idx_framework_models_name ON framework.model_registry(model_name, is_active);

COMMENT ON TABLE framework.model_registry IS 'Model versioning with full metadata and lineage';

-- Feature registry
CREATE TABLE IF NOT EXISTS framework.feature_registry (
    feature_id SERIAL PRIMARY KEY,
    feature_name TEXT NOT NULL UNIQUE,
    feature_type TEXT NOT NULL CHECK (feature_type IN ('sql', 'python', 'hybrid')),
    source_table TEXT,  -- e.g., 'features_pitch.engineered_features'
    computation_method TEXT,  -- SQL expression or Python function
    dependencies TEXT[],  -- Other features this depends on
    data_type TEXT,  -- 'numeric', 'categorical', 'boolean', 'text'
    is_nullable BOOLEAN DEFAULT true,
    description TEXT,
    category TEXT,  -- e.g., 'weather', 'momentum', 'umpire', 'pitch_physics'
    version TEXT DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_framework_features_category ON framework.feature_registry(category, is_active);
CREATE INDEX IF NOT EXISTS idx_framework_features_deps ON framework.feature_registry USING GIN(dependencies);

COMMENT ON TABLE framework.feature_registry IS 'Feature catalog with dependencies, types, and computation methods';

-- Views for common queries
CREATE OR REPLACE VIEW framework.active_plugins AS
SELECT * FROM framework.plugins WHERE is_active = true;

CREATE OR REPLACE VIEW framework.active_models AS
SELECT * FROM framework.model_registry WHERE is_active = true;

CREATE OR REPLACE VIEW framework.active_features AS
SELECT * FROM framework.feature_registry WHERE is_active = true;

CREATE OR REPLACE VIEW framework.recent_experiments AS
SELECT 
    e.*,
    CASE 
        WHEN e.status = 'running' THEN EXTRACT(EPOCH FROM (NOW() - e.started_at))::INTEGER
        ELSE e.duration_seconds
    END as current_duration
FROM framework.experiments e
ORDER BY e.started_at DESC
LIMIT 100;

-- Helper functions
CREATE OR REPLACE FUNCTION framework.log_message(
    p_level TEXT,
    p_component TEXT,
    p_operation TEXT,
    p_message TEXT,
    p_details JSONB DEFAULT NULL,
    p_run_id INTEGER DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_log_id INTEGER;
BEGIN
    INSERT INTO framework.log (log_level, component, operation, message, details, run_id)
    VALUES (p_level, p_component, p_operation, p_message, p_details, p_run_id)
    RETURNING log_id INTO v_log_id;
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION framework.log_message IS 'Log a message to the framework log table';

CREATE OR REPLACE FUNCTION framework.start_experiment(
    p_name TEXT,
    p_type TEXT,
    p_config JSONB,
    p_tags TEXT[] DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_exp_id INTEGER;
    v_config_hash TEXT;
    v_git_commit TEXT;
BEGIN
    -- Compute config hash
    v_config_hash := MD5(p_config::TEXT);
    
    -- Try to get git commit (may fail in some environments)
    BEGIN
        v_git_commit := trim(both from (pg_read_file('.git/HEAD', 0, 100)));
    EXCEPTION WHEN OTHERS THEN
        v_git_commit := 'unknown';
    END;
    
    INSERT INTO framework.experiments (
        experiment_name, experiment_type, config_hash, config, tags, git_commit
    ) VALUES (p_name, p_type, v_config_hash, p_config, p_tags, v_git_commit)
    RETURNING experiment_id INTO v_exp_id;
    
    RETURN v_exp_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION framework.start_experiment IS 'Start tracking a new experiment, returns experiment_id';

CREATE OR REPLACE FUNCTION framework.complete_experiment(
    p_experiment_id INTEGER,
    p_status TEXT,
    p_results JSONB DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    UPDATE framework.experiments
    SET status = p_status,
        completed_at = NOW(),
        duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at)),
        results = p_results,
        error_message = p_error_message
    WHERE experiment_id = p_experiment_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION framework.complete_experiment IS 'Mark experiment as completed/failed with results';

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION framework.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_plugins_updated ON framework.plugins;
CREATE TRIGGER trg_plugins_updated
    BEFORE UPDATE ON framework.plugins
    FOR EACH ROW EXECUTE FUNCTION framework.update_timestamp();

DROP TRIGGER IF EXISTS trg_features_updated ON framework.feature_registry;
CREATE TRIGGER trg_features_updated
    BEFORE UPDATE ON framework.feature_registry
    FOR EACH ROW EXECUTE FUNCTION framework.update_timestamp();

-- Initial verification
SELECT 
    'Framework schema created' as status,
    (SELECT COUNT(*) FROM framework.plugins) as plugin_count,
    (SELECT COUNT(*) FROM framework.feature_registry) as feature_count;
