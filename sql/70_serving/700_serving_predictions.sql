/*
File: sql/70_serving/700_serving_predictions.sql
Purpose: Prediction storage for model inference results
Author: Agent Cascade
Date: 2026-04-28
Depends On: sql/60_models/600_models_registry.sql, sql/30_core/310_core_live_games.sql
Called By: baseball/models/inference.py, prediction pipeline

Table: predictions.inference_results
- Stores all model predictions with full context
- Links to model registry and input features for lineage
- Supports both batch historical and live real-time predictions
- Calibration and evaluation metrics

Notes:
- prediction_id is unique per inference call
- confidence interval fields for probabilistic predictions
- evaluation columns for post-hoc accuracy assessment
- TTL/index strategy for efficient queries
*/

-- Create predictions schema if not exists
CREATE SCHEMA IF NOT EXISTS predictions;

-- Prediction results table
CREATE TABLE IF NOT EXISTS predictions.inference_results (
    prediction_id bigserial PRIMARY KEY,
    
    -- Prediction identification
    prediction_type varchar(50) NOT NULL,      -- 'win_probability', 'run_expectancy', etc.
    prediction_timestamp timestamptz NOT NULL DEFAULT NOW(),
    
    -- Model linkage
    model_id bigint NOT NULL REFERENCES models.registry(model_id),
    model_version varchar(20) NOT NULL,        -- Denormalized for performance
    
    -- Game context (for live predictions)
    game_pk integer,
    season integer,
    inning smallint,
    is_top_inning boolean,
    outs smallint,
    
    -- Score state
    home_score integer,
    away_score integer,
    score_differential integer,
    
    -- Base state
    bases_occupied varchar(3),
    
    -- The prediction
    predicted_value decimal(8,6) NOT NULL,     -- Primary prediction (probability or value)
    predicted_class varchar(20),                 -- For classification
    
    -- Confidence
    confidence_lower decimal(8,6),             -- Lower bound of confidence interval
    confidence_upper decimal(8,6),             -- Upper bound of confidence interval
    confidence_width decimal(8,6) GENERATED ALWAYS AS (
        confidence_upper - confidence_lower
    ) STORED,
    
    -- Full probability distribution (for classification)
    probability_distribution jsonb,            -- {class: probability}
    
    -- Input features snapshot
    feature_vector jsonb,                      -- Features at time of prediction
    feature_hash varchar(64),                  -- Hash of features for deduplication
    
    -- Prediction request source
    request_source varchar(50),                -- 'live_api', 'batch_pipeline', 'cli', 'web'
    request_id varchar(100),                   -- Correlation ID for tracing
    
    -- Evaluation (filled in post-game)
    actual_outcome decimal(8,6),               -- What actually happened
    prediction_error decimal(8,6) GENERATED ALWAYS AS (
        CASE WHEN actual_outcome IS NOT NULL 
             THEN predicted_value - actual_outcome 
             ELSE NULL END
    ) STORED,
    was_correct boolean,                       -- For binary predictions
    
    -- Calibration metrics (post-hoc)
    calibration_error decimal(8,6),            -- |predicted - actual| for calibration
    
    -- Metadata
    inference_time_ms integer,                 -- How long prediction took
    inference_batch_size integer DEFAULT 1,    -- Single vs batch
    
    -- Lineage
    input_features_id bigint,                  -- Link to features.win_probability_inputs
    snapshot_id bigint REFERENCES raw_mlb.live_feed_snapshots(snapshot_id),
    
    -- Audit
    created_at timestamptz NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE predictions.inference_results IS 
    'All model predictions with full context, confidence intervals, and evaluation metrics';

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_predictions_game ON predictions.inference_results(game_pk);
CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions.inference_results(prediction_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_model ON predictions.inference_results(model_id);
CREATE INDEX IF NOT EXISTS idx_predictions_type ON predictions.inference_results(prediction_type);
CREATE INDEX IF NOT EXISTS idx_predictions_season ON predictions.inference_results(season);
CREATE INDEX IF NOT EXISTS idx_predictions_request ON predictions.inference_results(request_id) WHERE request_id IS NOT NULL;

-- Partial index for un-evaluated predictions (for batch evaluation)
CREATE INDEX IF NOT EXISTS idx_predictions_pending_eval ON predictions.inference_results(prediction_id) 
    WHERE actual_outcome IS NULL AND game_pk IS NOT NULL;

-- Composite index for game state predictions
CREATE INDEX IF NOT EXISTS idx_predictions_state ON predictions.inference_results(
    game_pk, inning, is_top_inning, outs, bases_occupied
);

-- Trigger function to auto-calculate confidence width
CREATE OR REPLACE FUNCTION predictions.set_confidence_width()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.confidence_lower IS NOT NULL AND NEW.confidence_upper IS NOT NULL THEN
        NEW.confidence_width := NEW.confidence_upper - NEW.confidence_lower;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- View: Latest predictions per game (current state)
CREATE OR REPLACE VIEW predictions.v_latest_predictions AS
SELECT DISTINCT ON (game_pk, prediction_type)
    *
FROM predictions.inference_results
ORDER BY game_pk, prediction_type, prediction_timestamp DESC;

COMMENT ON VIEW predictions.v_latest_predictions IS 
    'Most recent prediction for each game and prediction type';

-- View: Win probability timeline for a game
CREATE OR REPLACE VIEW predictions.v_wp_timeline AS
SELECT 
    prediction_id,
    game_pk,
    prediction_timestamp,
    inning,
    is_top_inning,
    outs,
    bases_occupied,
    home_score,
    away_score,
    predicted_value as home_win_probability,
    (1 - predicted_value) as away_win_probability,
    confidence_lower,
    confidence_upper,
    actual_outcome,
    was_correct
FROM predictions.inference_results
WHERE prediction_type = 'win_probability'
ORDER BY game_pk, prediction_timestamp;

COMMENT ON VIEW predictions.v_wp_timeline IS 
    'Win probability evolution throughout a game';

-- View: Model performance summary
CREATE OR REPLACE VIEW predictions.v_model_performance AS
SELECT 
    model_id,
    prediction_type,
    COUNT(*) as total_predictions,
    COUNT(actual_outcome) as evaluated_predictions,
    ROUND(AVG(CASE WHEN actual_outcome IS NOT NULL 
                     THEN ABS(predicted_value - actual_outcome) END), 6) as mae,
    ROUND(AVG(CASE WHEN was_correct THEN 1.0 ELSE 0.0 END), 4) as accuracy,
    ROUND(AVG(confidence_width), 6) as avg_confidence_width,
    ROUND(AVG(inference_time_ms), 2) as avg_inference_ms
FROM predictions.inference_results
GROUP BY model_id, prediction_type;

COMMENT ON VIEW predictions.v_model_performance IS 
    'Performance metrics per model from prediction history';

-- View: Calibration analysis
CREATE OR REPLACE VIEW predictions.v_calibration_analysis AS
SELECT 
    model_id,
    prediction_type,
    CASE 
        WHEN predicted_value BETWEEN 0 AND 0.1 THEN '0-10%'
        WHEN predicted_value BETWEEN 0.1 AND 0.2 THEN '10-20%'
        WHEN predicted_value BETWEEN 0.2 AND 0.3 THEN '20-30%'
        WHEN predicted_value BETWEEN 0.3 AND 0.4 THEN '30-40%'
        WHEN predicted_value BETWEEN 0.4 AND 0.5 THEN '40-50%'
        WHEN predicted_value BETWEEN 0.5 AND 0.6 THEN '50-60%'
        WHEN predicted_value BETWEEN 0.6 AND 0.7 THEN '60-70%'
        WHEN predicted_value BETWEEN 0.7 AND 0.8 THEN '70-80%'
        WHEN predicted_value BETWEEN 0.8 AND 0.9 THEN '80-90%'
        ELSE '90-100%'
    END as probability_bin,
    COUNT(*) as n_predictions,
    ROUND(AVG(predicted_value), 4) as avg_predicted,
    ROUND(AVG(actual_outcome), 4) as avg_actual,
    ROUND(AVG(predicted_value) - AVG(actual_outcome), 4) as calibration_error
FROM predictions.inference_results
WHERE actual_outcome IS NOT NULL
GROUP BY model_id, prediction_type, probability_bin
ORDER BY model_id, prediction_type, probability_bin;

COMMENT ON VIEW predictions.v_calibration_analysis IS 
    'Calibration analysis: predicted vs actual by probability bin';

-- Function to store a prediction
CREATE OR REPLACE FUNCTION predictions.store_prediction(
    p_prediction_type varchar,
    p_model_id bigint,
    p_predicted_value decimal,
    p_game_pk integer DEFAULT NULL,
    p_feature_vector jsonb DEFAULT '{}',
    p_probability_distribution jsonb DEFAULT NULL,
    p_confidence_lower decimal DEFAULT NULL,
    p_confidence_upper decimal DEFAULT NULL,
    p_request_source varchar DEFAULT 'api',
    p_request_id varchar DEFAULT NULL,
    p_inference_time_ms integer DEFAULT NULL
)
RETURNS bigint AS $$
DECLARE
    v_prediction_id bigint;
    v_model_version varchar;
BEGIN
    -- Get model version
    SELECT model_version INTO v_model_version
    FROM models.registry WHERE model_id = p_model_id;
    
    INSERT INTO predictions.inference_results (
        prediction_type,
        model_id,
        model_version,
        predicted_value,
        game_pk,
        feature_vector,
        feature_hash,
        probability_distribution,
        confidence_lower,
        confidence_upper,
        request_source,
        request_id,
        inference_time_ms
    ) VALUES (
        p_prediction_type,
        p_model_id,
        v_model_version,
        p_predicted_value,
        p_game_pk,
        p_feature_vector,
        encode(digest(p_feature_vector::text, 'sha256'), 'hex'),
        p_probability_distribution,
        p_confidence_lower,
        p_confidence_upper,
        p_request_source,
        p_request_id,
        p_inference_time_ms
    )
    RETURNING prediction_id INTO v_prediction_id;
    
    RETURN v_prediction_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION predictions.store_prediction IS 
    'Store a single prediction with all metadata';

-- Function to evaluate predictions post-game
CREATE OR REPLACE FUNCTION predictions.evaluate_predictions(
    p_game_pk integer,
    p_actual_home_win boolean,
    p_final_home_score integer DEFAULT NULL,
    p_final_away_score integer DEFAULT NULL
)
RETURNS integer AS $$
DECLARE
    v_updated integer;
BEGIN
    UPDATE predictions.inference_results
    SET 
        actual_outcome = CASE WHEN p_actual_home_win THEN 1.0 ELSE 0.0 END,
        was_correct = CASE 
            WHEN predicted_value > 0.5 AND p_actual_home_win THEN TRUE
            WHEN predicted_value < 0.5 AND NOT p_actual_home_win THEN TRUE
            ELSE FALSE
        END
    WHERE game_pk = p_game_pk
      AND prediction_type = 'win_probability'
      AND actual_outcome IS NULL;
    
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RETURN v_updated;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION predictions.evaluate_predictions IS 
    'Update predictions with actual outcomes after game completion';

-- Function to get prediction history for a game
CREATE OR REPLACE FUNCTION predictions.get_game_predictions(p_game_pk integer)
RETURNS TABLE(
    prediction_timestamp timestamptz,
    prediction_type varchar,
    model_version varchar,
    inning smallint,
    is_top_inning boolean,
    home_win_probability decimal,
    confidence_lower decimal,
    confidence_upper decimal,
    was_correct boolean
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ir.prediction_timestamp,
        ir.prediction_type,
        ir.model_version,
        ir.inning,
        ir.is_top_inning,
        ir.predicted_value as home_win_probability,
        ir.confidence_lower,
        ir.confidence_upper,
        ir.was_correct
    FROM predictions.inference_results ir
    WHERE ir.game_pk = p_game_pk
    ORDER BY ir.prediction_timestamp;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION predictions.get_game_predictions IS 
    'Get all predictions for a specific game';
