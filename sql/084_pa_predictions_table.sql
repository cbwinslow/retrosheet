-- Create predictions.pa_predictions table for historical PA outcome predictions
-- This table stores predictions generated on historical plate appearances
-- Similar structure to live_pa_predictions but for historical data

CREATE TABLE IF NOT EXISTS predictions.pa_predictions (
    pa_prediction_id BIGSERIAL PRIMARY KEY,
    game_id TEXT NOT NULL,
    plate_appearance_id INTEGER NOT NULL,
    target_id TEXT NOT NULL,
    model_id BIGINT NOT NULL,
    prediction_run_id BIGINT,
    feature_snapshot JSONB NOT NULL DEFAULT '{}',
    state_snapshot JSONB NOT NULL DEFAULT '{}',
    missing_features TEXT[] NOT NULL DEFAULT '{}',
    predicted_outcome TEXT NOT NULL,
    predicted_probabilities JSONB NOT NULL DEFAULT '{}',
    aggregated_metrics JSONB NOT NULL DEFAULT '{}',
    prediction_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_calibrated BOOLEAN NOT NULL DEFAULT FALSE,
    calibration_artifact_uri TEXT,
    actual_outcome TEXT,
    outcome_timestamp TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_pa_predictions_game_id ON predictions.pa_predictions(game_id);
CREATE INDEX IF NOT EXISTS idx_pa_predictions_plate_appearance_id ON predictions.pa_predictions(plate_appearance_id);
CREATE INDEX IF NOT EXISTS idx_pa_predictions_model_id ON predictions.pa_predictions(model_id);
CREATE INDEX IF NOT EXISTS idx_pa_predictions_prediction_run_id ON predictions.pa_predictions(prediction_run_id);
CREATE INDEX IF NOT EXISTS idx_pa_predictions_prediction_timestamp ON predictions.pa_predictions(prediction_timestamp);
CREATE INDEX IF NOT EXISTS idx_pa_predictions_actual_outcome ON predictions.pa_predictions(actual_outcome) WHERE actual_outcome IS NOT NULL;

-- Comment
COMMENT ON TABLE predictions.pa_predictions IS 'Historical plate appearance outcome predictions for model evaluation and backtesting';
