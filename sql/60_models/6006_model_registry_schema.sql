-- ============================================================
-- Model Registry Schema for Model Zoo Architecture
-- MLflow-style model registry in PostgreSQL
-- ============================================================
-- Author: Agent Cascade
-- Date: 2026-05-01
-- Purpose: Store, version, and serve 110+ trained models
-- ============================================================

CREATE SCHEMA IF NOT EXISTS models;

COMMENT ON SCHEMA models IS 
'MLflow-style model registry for the Model Zoo Architecture. Stores 110+ models across 8 abstraction layers.';

-- ============================================================
-- CORE MODEL REGISTRY TABLE
-- ============================================================

CREATE TABLE models.registry (
    model_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    
    -- Classification
    abstraction_layer VARCHAR(20) NOT NULL,  -- 'league', 'team', 'game', 'inning', 'pa', 'count', 'pitch', 'player'
    prediction_target VARCHAR(50) NOT NULL,  -- 'swing', 'outcome', 'winner', 'hr', 'k', 'bb', 'pitch_type', etc
    architecture VARCHAR(50) NOT NULL,  -- 'xgboost', 'random_forest', 'neural_net', 'lstm', 'markov', 'prophet', 'survival'
    model_type VARCHAR(20) NOT NULL,  -- 'classification', 'regression', 'multi_class', 'sequence', 'time_series'
    
    -- Scope (generic vs specific)
    is_generic BOOLEAN NOT NULL DEFAULT TRUE,
    player_id VARCHAR(20),  -- NULL if generic model
    team_id VARCHAR(20),  -- NULL if generic model
    
    -- Performance metrics (from validation set)
    accuracy DECIMAL(5,4),  -- Classification
    precision DECIMAL(5,4),
    recall DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    auc_roc DECIMAL(5,4),
    
    rmse DECIMAL(8,4),  -- Regression
    mae DECIMAL(8,4),
    r_squared DECIMAL(5,4),
    mape DECIMAL(5,2),  -- Mean absolute % error
    
    log_loss DECIMAL(8,4),  -- Classification
    calibration_error DECIMAL(5,4),  -- Brier score / expected calibration error
    
    -- Training info
    training_data_start DATE,
    training_data_end DATE,
    training_samples INTEGER,
    training_duration_seconds INTEGER,
    
    -- Features
    feature_count INTEGER,
    feature_list TEXT[],  -- Array of feature column names
    feature_importance JSONB,  -- {feature_name: importance_score}
    feature_selection_method VARCHAR(50),  -- 'all', 'top_k', 'recursive', 'lasso'
    
    -- Model artifact
    model_binary BYTEA,  -- Serialized model bytes
    model_framework VARCHAR(20) NOT NULL,  -- 'sklearn', 'xgboost', 'pytorch', 'tensorflow', 'statsmodels', 'custom'
    model_format VARCHAR(20),  -- 'pickle', 'joblib', 'onnx', 'torch', 'json'
    model_size_bytes INTEGER,
    model_hash VARCHAR(64),  -- SHA-256 hash for integrity
    
    -- Hyperparameters
    hyperparameters JSONB,  -- Full hyperparameter config
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'training',  -- 'training', 'active', 'deprecated', 'failed', 'archived'
    is_production BOOLEAN NOT NULL DEFAULT FALSE,
    production_date TIMESTAMP,
    
    -- Overfitting protection
    train_accuracy DECIMAL(5,4),  -- Training set performance
    validation_accuracy DECIMAL(5,4),  -- Validation set
    test_accuracy DECIMAL(5,4),  -- Hold-out test set
    overfit_gap DECIMAL(5,4),  -- train_accuracy - test_accuracy
    overfit_check_passed BOOLEAN,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    trained_by VARCHAR(50),
    training_config JSONB,  -- Full training configuration
    training_notes TEXT,
    
    -- Tags for searching
    tags TEXT[],
    
    -- Constraints
    CONSTRAINT unique_model_version UNIQUE (model_name, model_version),
    CONSTRAINT valid_layer CHECK (abstraction_layer IN ('league', 'team', 'game', 'inning', 'pa', 'count', 'pitch', 'player', 'historical')),
    CONSTRAINT valid_architecture CHECK (architecture IN ('xgboost', 'random_forest', 'neural_net', 'lstm', 'gru', 'markov', 'prophet', 'arima', 'survival', 'ensemble', 'logistic', 'linear')),
    CONSTRAINT valid_framework CHECK (model_framework IN ('sklearn', 'xgboost', 'pytorch', 'tensorflow', 'statsmodels', 'custom')),
    CONSTRAINT valid_status CHECK (status IN ('training', 'active', 'deprecated', 'failed', 'archived'))
);

COMMENT ON TABLE models.registry IS 
'Master registry for all trained models. Stores serialized models, performance metrics, and metadata. 110+ models expected.';

-- Indexes for common queries
CREATE INDEX idx_registry_layer ON models.registry(abstraction_layer);
CREATE INDEX idx_registry_target ON models.registry(prediction_target);
CREATE INDEX idx_registry_architecture ON models.registry(architecture);
CREATE INDEX idx_registry_status ON models.registry(status, is_production);
CREATE INDEX idx_registry_generic ON models.registry(is_generic, abstraction_layer, prediction_target);
CREATE INDEX idx_registry_player ON models.registry(player_id) WHERE player_id IS NOT NULL;
CREATE INDEX idx_registry_team ON models.registry(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX idx_registry_performance ON models.registry(test_accuracy DESC, f1_score DESC) WHERE status = 'active';
CREATE INDEX idx_registry_tags ON models.registry USING GIN(tags);
CREATE INDEX idx_registry_overfit ON models.registry(overfit_gap) WHERE overfit_check_passed = TRUE;

-- ============================================================
-- MODEL PERFORMANCE HISTORY
-- ============================================================

CREATE TABLE models.performance_history (
    history_id BIGSERIAL PRIMARY KEY,
    model_id UUID NOT NULL REFERENCES models.registry(model_id) ON DELETE CASCADE,
    
    -- Evaluation context
    evaluation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    evaluation_type VARCHAR(20) NOT NULL DEFAULT 'validation',  -- 'validation', 'test', 'backtest', 'live'
    
    -- Dataset info
    dataset_start DATE,
    dataset_end DATE,
    sample_count INTEGER NOT NULL,
    
    -- Classification metrics
    accuracy DECIMAL(5,4),
    precision DECIMAL(5,4),
    recall DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    auc_roc DECIMAL(5,4),
    log_loss DECIMAL(8,4),
    
    -- Per-class metrics (for multi-class)
    class_metrics JSONB,  -- {"K": {"precision": 0.82, "recall": 0.78}, "BB": {...}}
    confusion_matrix JSONB,  -- [[TN, FP], [FN, TP]] or multi-class matrix
    
    -- Regression metrics
    rmse DECIMAL(8,4),
    mae DECIMAL(8,4),
    r_squared DECIMAL(5,4),
    mape DECIMAL(5,2),
    
    -- Calibration
    calibration_error DECIMAL(5,4),
    reliability_diagram JSONB,  -- Binned accuracy vs confidence
    
    -- Comparison to baseline
    baseline_accuracy DECIMAL(5,4),  -- e.g., majority class classifier
    improvement_over_baseline DECIMAL(5,4),
    
    -- Statistical significance
    p_value DECIMAL(8,6),  -- vs baseline
    confidence_interval JSONB,  -- {"accuracy": {"lower": 0.72, "upper": 0.78}}
    
    -- Notes
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE models.performance_history IS 
'Historical performance tracking for all models. Enables drift detection and model selection.';

CREATE INDEX idx_perf_history_model ON models.performance_history(model_id, evaluation_date DESC);
CREATE INDEX idx_perf_history_date ON models.performance_history(evaluation_date);
CREATE INDEX idx_perf_history_accuracy ON models.performance_history(accuracy DESC);

-- ============================================================
-- MODEL PREDICTION LOG (for tracking live predictions)
-- ============================================================

CREATE TABLE models.prediction_log (
    log_id BIGSERIAL PRIMARY KEY,
    model_id UUID NOT NULL REFERENCES models.registry(model_id),
    
    -- Input
    input_features JSONB NOT NULL,
    input_hash VARCHAR(64) NOT NULL,  -- SHA-256 for deduplication
    input_signature TEXT,  -- Human-readable feature summary
    
    -- Prediction
    prediction JSONB NOT NULL,  -- Scalar, vector, or distribution
    prediction_type VARCHAR(20) NOT NULL,  -- 'probability', 'class', 'regression', 'distribution', 'sequence'
    confidence DECIMAL(5,4),  -- Model confidence
    
    -- Timing
    prediction_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    inference_latency_ms INTEGER,  -- Time to generate prediction
    
    -- Context
    game_pk INTEGER,
    season INTEGER,
    pa_id VARCHAR,
    pitch_id BIGINT,
    inning INTEGER,
    count VARCHAR(5),
    
    player_id VARCHAR(20),  -- If player-specific prediction
    team_id VARCHAR(20),  -- If team-specific prediction
    
    -- Actual outcome (populated later)
    actual_outcome JSONB,
    outcome_timestamp TIMESTAMP,
    outcome_correct BOOLEAN,
    prediction_error DECIMAL(8,4),  -- For regression
    
    -- Performance on this specific prediction
    log_likelihood DECIMAL(8,4),  -- For probabilistic predictions
    brier_score DECIMAL(5,4),  -- For binary predictions
    
    -- Feature drift detection
    feature_drift_detected BOOLEAN DEFAULT FALSE,
    drift_score DECIMAL(5,4),
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE models.prediction_log IS 
'Log of all model predictions for accuracy tracking and drift detection. Partitioned by date recommended for production.';

CREATE INDEX idx_pred_log_model ON models.prediction_log(model_id, prediction_timestamp DESC);
CREATE INDEX idx_pred_log_game ON models.prediction_log(game_pk);
CREATE INDEX idx_pred_log_player ON models.prediction_log(player_id);
CREATE INDEX idx_pred_log_timestamp ON models.prediction_log(prediction_timestamp);
CREATE INDEX idx_pred_log_hash ON models.prediction_log(input_hash);  -- For deduplication

-- ============================================================
-- MODEL SELECTION RULES (for NL query routing)
-- ============================================================

CREATE TABLE models.selection_rules (
    rule_id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL UNIQUE,
    rule_description TEXT,
    
    -- Matching criteria
    query_pattern_regex VARCHAR(200),  -- Regex pattern on natural language query
    required_layer VARCHAR(20),  -- Must match this layer
    required_target VARCHAR(50),  -- Must match this prediction target
    required_context JSONB,  -- Required context features present: {"count": true, "bases": true}
    
    -- Model selection
    primary_model_id UUID REFERENCES models.registry(model_id),
    fallback_model_id UUID REFERENCES models.registry(model_id),
    
    -- Ensemble selection
    ensemble_model_ids UUID[],  -- Multiple models to ensemble
    ensemble_weights DECIMAL(5,4)[],  -- Must match length of ensemble_model_ids
    ensemble_method VARCHAR(20) DEFAULT 'average',  -- 'average', 'weighted_average', 'voting', 'stacking'
    
    -- Performance criteria
    min_accuracy DECIMAL(5,4) DEFAULT 0.60,
    min_f1_score DECIMAL(5,4) DEFAULT 0.50,
    max_latency_ms INTEGER DEFAULT 5000,
    max_overfit_gap DECIMAL(5,4) DEFAULT 0.05,
    
    -- Prioritization
    priority INTEGER NOT NULL DEFAULT 100,  -- Lower = higher priority
    
    -- Scope
    active BOOLEAN NOT NULL DEFAULT TRUE,
    valid_from DATE,
    valid_until DATE,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(50)
);

COMMENT ON TABLE models.selection_rules IS 
'Rules for routing natural language queries to appropriate models. Supports single model, fallback, or ensemble selection.';

CREATE INDEX idx_selection_rules_layer ON models.selection_rules(required_layer, priority);
CREATE INDEX idx_selection_rules_active ON models.selection_rules(active, priority) WHERE active = TRUE;

-- ============================================================
-- FEATURE SCHEMA (for feature validation)
-- ============================================================

CREATE TABLE models.feature_schema (
    feature_id SERIAL PRIMARY KEY,
    feature_name VARCHAR(100) NOT NULL UNIQUE,
    
    -- Metadata
    feature_type VARCHAR(20) NOT NULL,  -- 'numeric', 'categorical', 'boolean', 'json', 'embedding'
    feature_layer VARCHAR(20) NOT NULL,  -- Which abstraction layer
    data_type VARCHAR(20),  -- PostgreSQL type: 'INTEGER', 'DECIMAL', 'VARCHAR', 'JSONB', etc
    
    -- Description
    description TEXT,
    source_table VARCHAR(100),  -- Where this feature comes from
    source_column VARCHAR(100),
    
    -- Statistics (updated periodically)
    mean_value DECIMAL(12,6),
    std_value DECIMAL(12,6),
    min_value DECIMAL(12,6),
    max_value DECIMAL(12,6),
    null_rate DECIMAL(5,4),
    
    -- Usage
    used_by_models INTEGER[],  -- Array of model_ids using this feature
    
    -- Validation
    validation_rules JSONB,  -- {"min": 0, "max": 1, "allowed_values": [...]}
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE models.feature_schema IS 
'Schema registry for all features used by models. Enables feature validation and drift detection.';

CREATE INDEX idx_feature_layer ON models.feature_schema(feature_layer);
CREATE INDEX idx_feature_type ON models.feature_schema(feature_type);

-- ============================================================
-- MODEL COMPARISON VIEW (for selecting best model)
-- ============================================================

CREATE VIEW models.v_model_comparison AS
SELECT 
    r.model_id,
    r.model_name,
    r.model_version,
    r.abstraction_layer,
    r.prediction_target,
    r.architecture,
    r.model_type,
    r.is_generic,
    r.player_id,
    r.team_id,
    
    -- Performance
    r.accuracy,
    r.f1_score,
    r.auc_roc,
    r.rmse,
    r.mae,
    r.log_loss,
    
    -- Overfitting
    r.train_accuracy,
    r.test_accuracy,
    r.overfit_gap,
    r.overfit_check_passed,
    
    -- Status
    r.status,
    r.is_production,
    r.training_data_end,
    
    -- Recent performance (last 30 days)
    h.accuracy as recent_accuracy,
    h.f1_score as recent_f1,
    
    -- Ranking (within layer/target)
    RANK() OVER (
        PARTITION BY r.abstraction_layer, r.prediction_target, r.is_generic 
        ORDER BY r.test_accuracy DESC NULLS LAST
    ) as accuracy_rank

FROM models.registry r
LEFT JOIN LATERAL (
    SELECT accuracy, f1_score
    FROM models.performance_history
    WHERE model_id = r.model_id
    ORDER BY evaluation_date DESC
    LIMIT 1
) h ON true
WHERE r.status = 'active'
ORDER BY r.abstraction_layer, r.prediction_target, accuracy_rank;

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Function: Get best model for a query
CREATE OR REPLACE FUNCTION models.get_best_model(
    p_layer VARCHAR,
    p_target VARCHAR,
    p_is_generic BOOLEAN DEFAULT TRUE,
    p_player_id VARCHAR DEFAULT NULL,
    p_team_id VARCHAR DEFAULT NULL
)
RETURNS TABLE(
    model_id UUID,
    model_name VARCHAR,
    architecture VARCHAR,
    accuracy DECIMAL,
    model_binary BYTEA
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.model_id,
        r.model_name,
        r.architecture,
        r.accuracy,
        r.model_binary
    FROM models.registry r
    WHERE r.abstraction_layer = p_layer
      AND r.prediction_target = p_target
      AND r.is_generic = p_is_generic
      AND r.status = 'active'
      AND (p_player_id IS NULL OR r.player_id = p_player_id)
      AND (p_team_id IS NULL OR r.team_id = p_team_id)
      AND r.overfit_check_passed = TRUE
    ORDER BY 
        r.is_production DESC,  -- Prefer production models
        r.test_accuracy DESC NULLS LAST,  -- Then by accuracy
        r.f1_score DESC NULLS LAST
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION models.get_best_model IS 
'Returns the best available model for a given layer, target, and scope (generic or player-specific).';

-- Function: Log a prediction
CREATE OR REPLACE FUNCTION models.log_prediction(
    p_model_id UUID,
    p_input_features JSONB,
    p_prediction JSONB,
    p_prediction_type VARCHAR,
    p_game_pk INTEGER DEFAULT NULL,
    p_pa_id VARCHAR DEFAULT NULL,
    p_pitch_id BIGINT DEFAULT NULL,
    p_latency_ms INTEGER DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_log_id BIGINT;
    v_input_hash VARCHAR(64);
BEGIN
    -- Compute hash for deduplication
    v_input_hash := encode(digest(p_input_features::text, 'sha256'), 'hex');
    
    INSERT INTO models.prediction_log (
        model_id,
        input_features,
        input_hash,
        prediction,
        prediction_type,
        game_pk,
        pa_id,
        pitch_id,
        inference_latency_ms
    ) VALUES (
        p_model_id,
        p_input_features,
        v_input_hash,
        p_prediction,
        p_prediction_type,
        p_game_pk,
        p_pa_id,
        p_pitch_id,
        p_latency_ms
    )
    RETURNING log_id INTO v_log_id;
    
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION models.log_prediction IS 
'Logs a model prediction and returns the log_id for later outcome updates.';

-- Function: Update prediction outcome
CREATE OR REPLACE FUNCTION models.update_prediction_outcome(
    p_log_id BIGINT,
    p_actual_outcome JSONB,
    p_outcome_correct BOOLEAN DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    UPDATE models.prediction_log
    SET 
        actual_outcome = p_actual_outcome,
        outcome_timestamp = NOW(),
        outcome_correct = COALESCE(
            p_outcome_correct,
            -- Auto-compute for simple cases
            CASE 
                WHEN prediction::text = p_actual_outcome::text THEN TRUE
                ELSE FALSE
            END
        )
    WHERE log_id = p_log_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION models.update_prediction_outcome IS 
'Updates a logged prediction with the actual outcome for accuracy tracking.';

-- Function: Get model accuracy over time
CREATE OR REPLACE FUNCTION models.get_model_accuracy_trend(
    p_model_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE(
    eval_date DATE,
    accuracy DECIMAL,
    sample_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        evaluation_date,
        accuracy,
        sample_count
    FROM models.performance_history
    WHERE model_id = p_model_id
      AND evaluation_date >= CURRENT_DATE - p_days
    ORDER BY evaluation_date;
END;
$$ LANGUAGE plpgsql;

-- Function: Detect model drift
CREATE OR REPLACE FUNCTION models.detect_drift(
    p_model_id UUID,
    p_baseline_window_days INTEGER DEFAULT 30,
    p_current_window_days INTEGER DEFAULT 7
)
RETURNS TABLE(
    drift_detected BOOLEAN,
    accuracy_drop DECIMAL,
    p_value DECIMAL
) AS $$
DECLARE
    v_baseline_accuracy DECIMAL;
    v_current_accuracy DECIMAL;
    v_baseline_std DECIMAL;
BEGIN
    -- Get baseline accuracy
    SELECT AVG(accuracy), STDDEV(accuracy)
    INTO v_baseline_accuracy, v_baseline_std
    FROM models.performance_history
    WHERE model_id = p_model_id
      AND evaluation_date BETWEEN 
          CURRENT_DATE - p_baseline_window_days - p_current_window_days 
          AND CURRENT_DATE - p_current_window_days;
    
    -- Get current accuracy
    SELECT AVG(accuracy)
    INTO v_current_accuracy
    FROM models.performance_history
    WHERE model_id = p_model_id
      AND evaluation_date >= CURRENT_DATE - p_current_window_days;
    
    -- Detect drift (simple z-test approximation)
    RETURN QUERY SELECT 
        (v_baseline_accuracy - v_current_accuracy) > (2 * COALESCE(v_baseline_std, 0.05)),
        v_baseline_accuracy - v_current_accuracy,
        0.05  -- Placeholder p-value
    WHERE v_baseline_accuracy IS NOT NULL AND v_current_accuracy IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Trigger: Auto-update updated_at
CREATE OR REPLACE FUNCTION models.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER registry_update_timestamp
    BEFORE UPDATE ON models.registry
    FOR EACH ROW EXECUTE FUNCTION models.update_timestamp();

CREATE TRIGGER selection_rules_update_timestamp
    BEFORE UPDATE ON models.selection_rules
    FOR EACH ROW EXECUTE FUNCTION models.update_timestamp();

-- Trigger: Auto-update production flag
CREATE OR REPLACE FUNCTION models.update_production_flag()
RETURNS TRIGGER AS $$
BEGIN
    -- If this model is being set to production, demote others
    IF NEW.is_production = TRUE AND (OLD.is_production = FALSE OR OLD.is_production IS NULL) THEN
        UPDATE models.registry
        SET is_production = FALSE
        WHERE abstraction_layer = NEW.abstraction_layer
          AND prediction_target = NEW.prediction_target
          AND is_generic = NEW.is_generic
          AND model_id != NEW.model_id;
        
        NEW.production_date = NOW();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER production_flag_trigger
    BEFORE UPDATE ON models.registry
    FOR EACH ROW EXECUTE FUNCTION models.update_production_flag();

-- ============================================================
-- GRANTS
-- ============================================================

GRANT USAGE ON SCHEMA models TO readonly;
GRANT USAGE ON SCHEMA models TO readwrite;

GRANT SELECT ON ALL TABLES IN SCHEMA models TO readonly;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA models TO readwrite;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA models TO readwrite;

-- ============================================================
-- SEED DATA: Example Models
-- ============================================================

-- Insert placeholder models to demonstrate structure
-- Real models will be inserted by training pipeline

INSERT INTO models.registry (
    model_name,
    model_version,
    abstraction_layer,
    prediction_target,
    architecture,
    model_type,
    is_generic,
    accuracy,
    f1_score,
    rmse,
    model_framework,
    status,
    is_production,
    hyperparameters,
    feature_count,
    tags
) VALUES 
(
    'pitch_swing_probability',
    '1.0.0',
    'pitch',
    'swing',
    'xgboost',
    'classification',
    TRUE,
    0.72,
    0.68,
    NULL,
    'xgboost',
    'active',
    TRUE,
    '{"max_depth": 6, "learning_rate": 0.1, "n_estimators": 200}',
    45,
    ARRAY['pitch', 'swing', 'real-time']
),
(
    'pa_is_home_run',
    '1.0.0',
    'pa',
    'hr',
    'xgboost',
    'classification',
    TRUE,
    0.68,
    0.42,
    NULL,
    'xgboost',
    'active',
    TRUE,
    '{"max_depth": 8, "learning_rate": 0.05, "scale_pos_weight": 10}',
    60,
    ARRAY['pa', 'home_run', 'power']
),
(
    'game_winner_monte_carlo',
    '1.0.0',
    'game',
    'winner',
    'ensemble',
    'classification',
    TRUE,
    0.58,
    0.58,
    NULL,
    'custom',
    'active',
    FALSE,
    '{"simulations": 10000, "method": "monte_carlo"}',
    25,
    ARRAY['game', 'simulation', 'win_probability']
),
(
    'harper_next_pa_hr',
    '1.0.0',
    'pa',
    'hr',
    'xgboost',
    'classification',
    FALSE,
    0.74,
    0.45,
    NULL,
    'xgboost',
    'active',
    TRUE,
    '{"max_depth": 6}',
    55,
    ARRAY['player-specific', 'harper', 'power']
)
ON CONFLICT (model_name, model_version) DO NOTHING;

-- ============================================================
-- DOCUMENTATION
-- ============================================================

COMMENT ON SCHEMA models IS 
'Model Zoo Registry: Stores 110+ trained models for baseball predictions across 8 abstraction layers.
Key tables:
- registry: Main model storage with serialized binaries
- performance_history: Historical accuracy tracking
- prediction_log: Live prediction tracking
- selection_rules: NL query routing

Usage:
1. Train models → INSERT into registry
2. Query models → SELECT using get_best_model()
3. Log predictions → CALL log_prediction()
4. Update outcomes → CALL update_prediction_outcome()
5. Monitor drift → CALL detect_drift()
';

-- End of model registry schema
