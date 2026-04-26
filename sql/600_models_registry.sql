/*
File: sql/600_models_registry.sql
Purpose: Model Registry schema for tracking ML models, versions, and training runs
Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
Depends On: features schema
Called By: scripts/models/register_model.sh, baseball models CLI

Tables Created:
- models.registry: Model definitions and metadata
- models.versions: Model versions with metrics
- models.training_runs: Training job tracking
- models.artifacts: Model file/storage references
- models.predictions: Prediction output storage

Notes:
- Each model has a canonical name (e.g., 'win_probability_v1')
- Versions are immutable once registered
- Training runs link to specific data versions
*/

-- Models schema
CREATE SCHEMA IF NOT EXISTS models;

COMMENT ON SCHEMA models IS 'ML model registry and prediction storage';


-- Model Registry
-- Central registry of all ML models
CREATE TABLE IF NOT EXISTS models.registry (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL UNIQUE,
    model_type VARCHAR(50) NOT NULL,  -- 'classification', 'regression', 'time_series'
    task VARCHAR(100) NOT NULL,  -- 'win_probability', 'run_expectancy', 'plate_appearance'
    description TEXT,
    -- Model characteristics
    features JSONB,  -- List of feature names used
    target_variable VARCHAR(100),
    output_type VARCHAR(50),  -- 'probability', 'count', 'binary'
    -- Versioning
    current_version VARCHAR(20),
    total_versions INTEGER DEFAULT 0,
    -- Metadata
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

COMMENT ON TABLE models.registry IS
'Central registry of all ML models in the system';
COMMENT ON COLUMN models.registry.features IS
'JSON array of feature names this model expects';

CREATE INDEX IF NOT EXISTS idx_registry_task
ON models.registry (task) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_registry_type
ON models.registry (model_type);


-- Model Versions
-- Individual model versions with full metadata
CREATE TABLE IF NOT EXISTS models.versions (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL REFERENCES models.registry (id),
    version VARCHAR(20) NOT NULL,
    version_tag VARCHAR(50),  -- e.g., 'production', 'staging', 'experimental'
    -- Version metadata
    git_commit VARCHAR(40),
    code_version VARCHAR(20),
    -- Training info
    training_run_id INTEGER,
    training_data_start DATE,
    training_data_end DATE,
    training_data_rows INTEGER,
    -- Performance metrics (JSON for flexibility)
    metrics JSONB,  -- e.g., {"accuracy": 0.85, "f1": 0.83, "auc": 0.91}
    validation_metrics JSONB,
    test_metrics JSONB,
    -- Model characteristics
    algorithm VARCHAR(50),  -- 'xgboost', 'lightgbm', 'neural_net', etc.
    hyperparameters JSONB,
    feature_importance JSONB,  -- Feature importance scores
    -- Status
    status VARCHAR(20) DEFAULT 'pending'
    CHECK (status IN ('pending', 'training', 'ready', 'validated', 'failed', 'archived')),
    is_production BOOLEAN DEFAULT FALSE,
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deployed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (model_id, version)
);

COMMENT ON TABLE models.versions IS
'Individual model versions with training metadata and performance metrics';
COMMENT ON COLUMN models.versions.metrics IS
'JSON object with model performance metrics';
COMMENT ON COLUMN models.versions.feature_importance IS
'JSON object mapping feature names to importance scores';

CREATE INDEX IF NOT EXISTS idx_versions_model
ON models.versions (model_id, version);

CREATE INDEX IF NOT EXISTS idx_versions_status
ON models.versions (status) WHERE status IN ('ready', 'validated');

CREATE INDEX IF NOT EXISTS idx_versions_production
ON models.versions (model_id) WHERE is_production = TRUE;


-- Training Runs
-- Track individual training jobs
CREATE TABLE IF NOT EXISTS models.training_runs (
    id SERIAL PRIMARY KEY,
    run_name VARCHAR(100),
    model_id INTEGER REFERENCES models.registry (id),
    -- Training configuration
    algorithm VARCHAR(50) NOT NULL,
    hyperparameters JSONB,
    feature_list JSONB,
    -- Data info
    data_source VARCHAR(100),
    data_query TEXT,
    training_start_date DATE,
    training_end_date DATE,
    training_rows INTEGER,
    validation_rows INTEGER,
    test_rows INTEGER,
    -- Execution
    status VARCHAR(20) DEFAULT 'pending'
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    -- Resources
    machine_type VARCHAR(50),
    cpu_count INTEGER,
    memory_gb NUMERIC(6, 2),
    -- Error info
    error_message TEXT,
    -- Artifacts
    artifact_path VARCHAR(500),
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE models.training_runs IS
'Training job tracking with configuration and execution metadata';

CREATE INDEX IF NOT EXISTS idx_training_model
ON models.training_runs (model_id, status);

CREATE INDEX IF NOT EXISTS idx_training_status
ON models.training_runs (status, started_at)
WHERE status IN ('pending', 'running');


-- Model Artifacts
-- Storage references for model files
CREATE TABLE IF NOT EXISTS models.artifacts (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES models.versions (id),
    artifact_type VARCHAR(50) NOT NULL,  -- 'model', 'preprocessor', 'config', 'log'
    storage_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,
    checksum VARCHAR(64),
    -- Metadata
    format VARCHAR(20),  -- 'pickle', 'joblib', 'onnx', 'json'
    compression VARCHAR(20),  -- 'none', 'gzip', 'bz2'
    -- Status
    is_primary BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE models.artifacts IS
'Storage locations for model files and related artifacts';

CREATE INDEX IF NOT EXISTS idx_artifacts_version
ON models.artifacts (version_id, artifact_type);


-- Predictions Storage
-- Store model predictions for analysis and serving
CREATE TABLE IF NOT EXISTS models.predictions (
    id SERIAL PRIMARY KEY,
    -- Model reference
    model_id INTEGER NOT NULL REFERENCES models.registry (id),
    version_id INTEGER REFERENCES models.versions (id),
    -- Prediction context
    game_pk INTEGER,
    play_id VARCHAR(20),
    at_bat_index INTEGER,
    pitch_index INTEGER,
    -- Input features (as of prediction time)
    features_hash VARCHAR(64),  -- Hash of input features
    -- Output
    prediction_type VARCHAR(50),  -- 'win_probability', 'run_expectancy', 'outcome'
    predicted_value NUMERIC,
    predicted_class VARCHAR(50),
    -- Probabilities for classification
    probabilities JSONB,  -- e.g., {"home_win": 0.65, "away_win": 0.35}
    confidence NUMERIC(5, 4),  -- Model confidence score
    -- Actual outcome (for validation)
    actual_value NUMERIC,
    actual_class VARCHAR(50),
    is_correct BOOLEAN,
    -- Metadata
    prediction_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    inference_time_ms INTEGER,  -- Performance metric
    -- Query optimization
    prediction_date DATE GENERATED ALWAYS AS (DATE(prediction_time)) STORED
);

COMMENT ON TABLE models.predictions IS
'Stored predictions for validation, analysis, and serving';
COMMENT ON COLUMN models.predictions.probabilities IS
'JSON object with class probabilities for classification models';
COMMENT ON COLUMN models.predictions.confidence IS
'Model confidence in prediction (0-1)';

-- Partitioning would be recommended for large prediction tables
CREATE INDEX IF NOT EXISTS idx_predictions_model
ON models.predictions (model_id, prediction_date);

CREATE INDEX IF NOT EXISTS idx_predictions_game
ON models.predictions (game_pk, prediction_type);

CREATE INDEX IF NOT EXISTS idx_predictions_time
ON models.predictions (prediction_time);


-- View: Production Models
CREATE OR REPLACE VIEW models.production_models AS
SELECT
    r.id AS model_id,
    r.model_name,
    r.task,
    r.model_type,
    v.id AS version_id,
    v.version,
    v.algorithm,
    v.metrics,
    v.deployed_at,
    a.storage_path AS model_path
FROM models.registry AS r
INNER JOIN models.versions AS v ON r.id = v.model_id
LEFT JOIN models.artifacts AS a ON v.id = a.version_id AND a.is_primary = TRUE
WHERE
    v.is_production = TRUE
    AND v.status = 'validated'
    AND r.is_active = TRUE;

COMMENT ON VIEW models.production_models IS
'Currently deployed production models with their paths';


-- View: Model Performance History
CREATE OR REPLACE VIEW models.model_performance AS
SELECT
    r.model_name,
    r.task,
    v.version,
    v.version_tag,
    v.metrics ->> 'accuracy' AS accuracy,
    v.metrics ->> 'f1' AS f1_score,
    v.metrics ->> 'auc' AS auc_roc,
    v.metrics ->> 'mae' AS mean_abs_error,
    v.metrics ->> 'rmse' AS rmse,
    v.training_data_rows,
    v.created_at AS trained_at,
    v.is_production
FROM models.registry AS r
INNER JOIN models.versions AS v ON r.id = v.model_id
WHERE v.status IN ('ready', 'validated')
ORDER BY r.model_name ASC, v.created_at DESC;

COMMENT ON VIEW models.model_performance IS
'Model performance metrics across all versions';


-- Function: Register Model
CREATE OR REPLACE FUNCTION models.register_model(
    p_model_name VARCHAR(100),
    p_model_type VARCHAR(50),
    p_task VARCHAR(100),
    p_description TEXT DEFAULT NULL,
    p_features JSONB DEFAULT NULL,
    p_target VARCHAR(100) DEFAULT NULL,
    p_output_type VARCHAR(50) DEFAULT 'probability'
)
RETURNS INTEGER AS $$
DECLARE
    v_model_id INTEGER;
BEGIN
    INSERT INTO models.registry (
        model_name, model_type, task, description,
        features, target_variable, output_type,
        created_by, created_at, is_active
    )
    VALUES (
        p_model_name, p_model_type, p_task, p_description,
        p_features, p_target, p_output_type,
        CURRENT_USER, NOW(), TRUE
    )
    ON CONFLICT (model_name) 
    DO UPDATE SET
        description = EXCLUDED.description,
        features = EXCLUDED.features,
        target_variable = EXCLUDED.target_variable,
        output_type = EXCLUDED.output_type,
        updated_at = NOW()
    RETURNING id INTO v_model_id;
    
    RETURN v_model_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION models.register_model IS
'Register a new model in the registry';


-- Function: Create Model Version
CREATE OR REPLACE FUNCTION models.create_version(
    p_model_id INTEGER,
    p_version VARCHAR(20),
    p_algorithm VARCHAR(50),
    p_hyperparameters JSONB DEFAULT NULL,
    p_metrics JSONB DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_version_id INTEGER;
    v_current VARCHAR(20);
BEGIN
    -- Get current version number
    SELECT current_version INTO v_current
    FROM models.registry WHERE id = p_model_id;
    
    -- Insert version
    INSERT INTO models.versions (
        model_id, version, algorithm, hyperparameters, metrics,
        status, is_production, created_at
    )
    VALUES (
        p_model_id, p_version, p_algorithm, p_hyperparameters, p_metrics,
        'ready', FALSE, NOW()
    )
    RETURNING id INTO v_version_id;
    
    -- Update registry
    UPDATE models.registry
    SET current_version = p_version,
        total_versions = total_versions + 1,
        updated_at = NOW()
    WHERE id = p_model_id;
    
    RETURN v_version_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION models.create_version IS
'Create a new version for an existing model';


-- Function: Promote to Production
CREATE OR REPLACE FUNCTION models.promote_to_production(
    p_version_id INTEGER
)
RETURNS BOOLEAN AS $$
DECLARE
    v_model_id INTEGER;
BEGIN
    -- Get model_id
    SELECT model_id INTO v_model_id
    FROM models.versions WHERE id = p_version_id;
    
    IF v_model_id IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Demote current production version
    UPDATE models.versions
    SET is_production = FALSE
    WHERE model_id = v_model_id AND is_production = TRUE;
    
    -- Promote new version
    UPDATE models.versions
    SET is_production = TRUE,
        status = 'validated',
        deployed_at = NOW()
    WHERE id = p_version_id;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION models.promote_to_production IS
'Promote a model version to production (demotes current production)';


-- Function: Log Prediction
CREATE OR REPLACE FUNCTION models.log_prediction(
    p_model_id INTEGER,
    p_version_id INTEGER,
    p_game_pk INTEGER,
    p_prediction_type VARCHAR(50),
    p_predicted_value NUMERIC,
    p_probabilities JSONB DEFAULT NULL,
    p_features_hash VARCHAR(64) DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_prediction_id BIGINT;
BEGIN
    INSERT INTO models.predictions (
        model_id, version_id, game_pk, prediction_type,
        predicted_value, probabilities, features_hash,
        prediction_time
    )
    VALUES (
        p_model_id, p_version_id, p_game_pk, p_prediction_type,
        p_predicted_value, p_probabilities, p_features_hash,
        NOW()
    )
    RETURNING id INTO v_prediction_id;
    
    RETURN v_prediction_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION models.log_prediction IS
'Log a model prediction for tracking and validation';
