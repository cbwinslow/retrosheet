/*
File: sql/features/018_swing_model_schema.sql
Purpose: Create schema for Swing Probability Model predictions and analysis
Author: Agent Cascade
Date: 2026-04-24
Depends On: features_pitch.engineered_features
Called By: Swing probability model training and inference

Tables Created:
- features_pitch.swing_predictions: Model predictions for each pitch
- features_pitch.swing_feature_importance: SHAP/feature importance tracking
- features_pitch.swing_model_performance: Per-game/day performance metrics

Notes:
- Predictions stored for backtesting and calibration analysis
- Includes actual outcome for validation
- Designed for real-time inference with pre-computed features
*/

-- ============================================================================
-- SWING PROBABILITY PREDICTIONS TABLE
-- ============================================================================
-- Stores model predictions for every pitch with swing/take outcome

CREATE TABLE IF NOT EXISTS features_pitch.swing_predictions (
    -- Primary Key & Identifiers
    pitch_id BIGINT PRIMARY KEY REFERENCES features_pitch.engineered_features(pitch_id),
    game_pk INTEGER NOT NULL,
    at_bat_number INTEGER NOT NULL,
    pitch_number INTEGER NOT NULL,

    -- Model Prediction
    swing_probability NUMERIC(6,5) NOT NULL,  -- P(swing), 0.0 to 1.0
    swing_predicted BOOLEAN NOT NULL,         -- Threshold at 0.5

    -- Prediction Confidence
    confidence_bucket TEXT,  -- 'high' (>0.8), 'med' (0.5-0.8), 'low' (<0.5)

    -- Actual Outcome (for validation)
    actual_swing BOOLEAN,  -- Did batter actually swing?
    correct_prediction BOOLEAN,  -- Was model correct?

    -- Context for Analysis
    pitch_type VARCHAR(2),
    count_code VARCHAR(5),  -- e.g., "1-2", "3-0"
    is_in_zone BOOLEAN,
    is_two_strike BOOLEAN,

    -- Model Metadata
    model_version TEXT,  -- e.g., "swing_xgboost_20260424_120000"
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- SHAP values for top features (stored as JSONB for flexibility)
    shap_values JSONB
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_swing_pred_game ON features_pitch.swing_predictions(game_pk);
CREATE INDEX IF NOT EXISTS idx_swing_pred_prob ON features_pitch.swing_predictions(swing_probability);
CREATE INDEX IF NOT EXISTS idx_swing_pred_correct ON features_pitch.swing_predictions(correct_prediction);
CREATE INDEX IF NOT EXISTS idx_swing_pred_confidence ON features_pitch.swing_predictions(confidence_bucket);

COMMENT ON TABLE features_pitch.swing_predictions IS 'Swing probability model predictions with actual outcomes for validation and calibration analysis';
COMMENT ON COLUMN features_pitch.swing_predictions.swing_probability IS 'Model predicted probability of batter swinging (0.0-1.0)';
COMMENT ON COLUMN features_pitch.swing_predictions.confidence_bucket IS 'Categorical confidence: high (>0.8), med (0.5-0.8), low (<0.5 for takes, >0.5 for swings)';
COMMENT ON COLUMN features_pitch.swing_predictions.shap_values IS 'SHAP feature attributions as JSONB for interpretability';

-- ============================================================================
-- SWING MODEL PERFORMANCE METRICS
-- ============================================================================
-- Aggregated performance by game, date, or other dimensions

CREATE TABLE IF NOT EXISTS features_pitch.swing_model_performance (
    id SERIAL PRIMARY KEY,

    -- Aggregation Level
    aggregation_level TEXT NOT NULL,  -- 'daily', 'game', 'monthly', 'overall'
    aggregation_key TEXT NOT NULL,    -- date, game_pk, or 'all'

    -- Sample Size
    n_pitches INTEGER NOT NULL,
    n_swings INTEGER NOT NULL,
    swing_rate_actual NUMERIC(5,4),   -- Actual swing rate in sample

    -- Calibration Metrics
    calibration_error NUMERIC(6,5),   -- Mean absolute calibration error
    brier_score NUMERIC(6,5),           -- Brier score (lower is better)

    -- Classification Metrics
    accuracy NUMERIC(5,4),
    precision_swing NUMERIC(5,4),       -- Precision for swing class
    recall_swing NUMERIC(5,4),          -- Recall for swing class (sensitivity)
    f1_score NUMERIC(5,4),
    roc_auc NUMERIC(5,4),

    -- Calibration by Buckets
    pct_high_conf_correct NUMERIC(5,4),  -- Accuracy on high confidence predictions
    pct_low_conf_correct NUMERIC(5,4),   -- Accuracy on low confidence predictions

    -- Model Version
    model_version TEXT NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(aggregation_level, aggregation_key, model_version)
);

COMMENT ON TABLE features_pitch.swing_model_performance IS 'Aggregated swing model performance metrics for monitoring and drift detection';

-- Index for time-series performance tracking
CREATE INDEX IF NOT EXISTS idx_swing_perf_date ON features_pitch.swing_model_performance(aggregation_key, calculated_at);

-- ============================================================================
-- SWING FEATURE IMPORTANCE TRACKING
-- ============================================================================
-- Global and per-prediction feature importance

CREATE TABLE IF NOT EXISTS features_pitch.swing_feature_importance (
    id SERIAL PRIMARY KEY,

    model_version TEXT NOT NULL,
    feature_name TEXT NOT NULL,

    -- Importance Metrics
    global_importance NUMERIC(8,6),      -- XGBoost feature importance
    mean_shap_value NUMERIC(10,8),         -- Mean absolute SHAP
    shap_std NUMERIC(10,8),                -- Std dev of SHAP values

    -- Directionality (does feature increase or decrease swing prob?)
    correlation_with_target NUMERIC(5,4),  -- Correlation with actual swings

    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(model_version, feature_name)
);

COMMENT ON TABLE features_pitch.swing_feature_importance IS 'Feature importance tracking for model interpretability and feature selection';

-- ============================================================================
-- SWING CALIBRATION CURVE (for visualization)
-- ============================================================================

CREATE TABLE IF NOT EXISTS features_pitch.swing_calibration_curve (
    id SERIAL PRIMARY KEY,

    model_version TEXT NOT NULL,
    probability_bin NUMERIC(3,2) NOT NULL,  -- 0.00, 0.05, 0.10, etc.

    -- Bin statistics
    n_samples INTEGER NOT NULL,
    mean_predicted_prob NUMERIC(6,5),
    mean_actual_rate NUMERIC(6,5),
    bin_error NUMERIC(6,5),  -- |predicted - actual|

    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE features_pitch.swing_calibration_curve IS 'Calibration curve data for reliability diagrams';

-- ============================================================================
-- VIEW: SWING ANALYSIS BY CONTEXT
-- ============================================================================

CREATE OR REPLACE VIEW features_pitch.swing_analysis_by_context AS
SELECT
    sp.count_code,
    sp.is_in_zone,
    sp.is_two_strike,
    sp.pitch_type,
    COUNT(*) as n_pitches,
    ROUND(AVG(sp.swing_probability)::numeric, 4) as avg_predicted_prob,
    ROUND(AVG(CASE WHEN sp.actual_swing THEN 1 ELSE 0 END)::numeric, 4) as actual_swing_rate,
    ROUND(AVG(CASE WHEN sp.correct_prediction THEN 1 ELSE 0 END)::numeric, 4) as accuracy,
    ROUND(AVG(ABS(sp.swing_probability - CASE WHEN sp.actual_swing THEN 1 ELSE 0 END))::numeric, 4) as mean_abs_error
FROM features_pitch.swing_predictions sp
WHERE sp.actual_swing IS NOT NULL  -- Has ground truth
GROUP BY sp.count_code, sp.is_in_zone, sp.is_two_strike, sp.pitch_type;

COMMENT ON VIEW features_pitch.swing_analysis_by_context IS 'Swing prediction accuracy broken down by baseball context for validation';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SELECT 'Swing model schema created successfully' as status;
SELECT COUNT(*) as table_count FROM information_schema.tables
WHERE table_schema = 'features_pitch'
AND table_name IN ('swing_predictions', 'swing_model_performance', 'swing_feature_importance', 'swing_calibration_curve');
