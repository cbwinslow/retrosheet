-- Live Prediction Logging Migration
-- Purpose: Durable storage for live plate appearance predictions and API request tracking
-- Phase: 3.1 - Standardize PA Serving

CREATE SCHEMA IF NOT EXISTS predictions;

-- Table for storing live plate appearance predictions
CREATE TABLE IF NOT EXISTS predictions.live_pa_predictions (
    live_pa_prediction_id bigserial PRIMARY KEY,
    game_id text NOT NULL,
    plate_appearance_id integer NOT NULL,
    target_id text NOT NULL REFERENCES predictions.prediction_targets (target_id),
    model_id bigint NOT NULL REFERENCES models.model_registry (model_id),
    prediction_run_id bigint REFERENCES predictions.prediction_runs (prediction_run_id),
    
    -- Input feature snapshot (for reproducibility and debugging)
    feature_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
    state_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
    missing_features text[] NOT NULL DEFAULT '{}'::text[],
    
    -- Prediction outputs
    predicted_outcome text NOT NULL,
    predicted_probabilities jsonb NOT NULL DEFAULT '{}'::jsonb,
    aggregated_metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
    
    -- Provenance and context
    request_context jsonb NOT NULL DEFAULT '{}'::jsonb,
    prediction_timestamp timestamptz NOT NULL DEFAULT now(),
    is_calibrated boolean NOT NULL DEFAULT false,
    calibration_artifact_uri text,
    
    -- Actual outcome (filled in after the PA completes)
    actual_outcome text,
    outcome_timestamp timestamptz,
    
    -- Metadata
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS live_pa_predictions_game_pa_idx
    ON predictions.live_pa_predictions (game_id, plate_appearance_id);

CREATE INDEX IF NOT EXISTS live_pa_predictions_target_created_idx
    ON predictions.live_pa_predictions (target_id, prediction_timestamp DESC);

CREATE INDEX IF NOT EXISTS live_pa_predictions_model_created_idx
    ON predictions.live_pa_predictions (model_id, prediction_timestamp DESC);

CREATE INDEX IF NOT EXISTS live_pa_predictions_timestamp_idx
    ON predictions.live_pa_predictions (prediction_timestamp DESC);

CREATE INDEX IF NOT EXISTS live_pa_predictions_feature_snapshot_gin_idx
    ON predictions.live_pa_predictions USING gin (feature_snapshot);

CREATE INDEX IF NOT EXISTS live_pa_predictions_state_snapshot_gin_idx
    ON predictions.live_pa_predictions USING gin (state_snapshot);

-- Table for tracking API prediction requests
CREATE TABLE IF NOT EXISTS predictions.api_prediction_requests (
    api_request_id bigserial PRIMARY KEY,
    request_id text NOT NULL UNIQUE,
    target_id text NOT NULL REFERENCES predictions.prediction_targets (target_id),
    model_id bigint REFERENCES models.model_registry (model_id),
    
    -- Request parameters
    request_params jsonb NOT NULL DEFAULT '{}'::jsonb,
    request_context jsonb NOT NULL DEFAULT '{}'::jsonb,
    
    -- Response data
    response_status text NOT NULL,
    response_data jsonb NOT NULL DEFAULT '{}'::jsonb,
    error_message text,
    
    -- Performance metrics
    request_timestamp timestamptz NOT NULL DEFAULT now(),
    response_timestamp timestamptz,
    latency_ms numeric,
    
    -- Metadata
    client_ip text,
    user_agent text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS api_prediction_requests_request_id_idx
    ON predictions.api_prediction_requests (request_id);

CREATE INDEX IF NOT EXISTS api_prediction_requests_target_created_idx
    ON predictions.api_prediction_requests (target_id, request_timestamp DESC);

CREATE INDEX IF NOT EXISTS api_prediction_requests_model_created_idx
    ON predictions.api_prediction_requests (model_id, request_timestamp DESC);

CREATE INDEX IF NOT EXISTS api_prediction_requests_timestamp_idx
    ON predictions.api_prediction_requests (request_timestamp DESC);

CREATE INDEX IF NOT EXISTS api_prediction_requests_status_idx
    ON predictions.api_prediction_requests (response_status);

-- View: Latest live PA prediction per game/PA
CREATE OR REPLACE VIEW analysis.live_pa_prediction_latest AS
SELECT DISTINCT ON (game_id, plate_appearance_id)
    live_pa_prediction_id,
    game_id,
    plate_appearance_id,
    target_id,
    model_id,
    prediction_run_id,
    feature_snapshot,
    state_snapshot,
    missing_features,
    predicted_outcome,
    predicted_probabilities,
    aggregated_metrics,
    request_context,
    prediction_timestamp,
    is_calibrated,
    calibration_artifact_uri,
    actual_outcome,
    outcome_timestamp,
    created_at,
    updated_at
FROM predictions.live_pa_predictions
ORDER BY game_id, plate_appearance_id, prediction_timestamp DESC;

-- View: Live PA prediction cards (for UI display)
CREATE OR REPLACE VIEW analysis.live_pa_prediction_cards AS
SELECT
    l.live_pa_prediction_id,
    l.game_id,
    l.plate_appearance_id,
    l.target_id,
    m.model_name,
    m.model_version,
    l.predicted_outcome,
    l.predicted_probabilities,
    l.aggregated_metrics,
    l.state_snapshot,
    l.missing_features,
    l.prediction_timestamp,
    l.actual_outcome,
    l.outcome_timestamp,
    CASE
        WHEN l.actual_outcome IS NOT NULL THEN 'settled'
        ELSE 'pending'
    END AS settlement_status,
    CASE
        WHEN l.actual_outcome IS NOT NULL THEN
            (l.predicted_probabilities->>l.actual_outcome)::numeric
        ELSE NULL
    END AS assigned_probability
FROM predictions.live_pa_predictions l
LEFT JOIN models.model_registry m ON l.model_id = m.model_id
ORDER BY l.prediction_timestamp DESC;

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION predictions.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_live_pa_predictions_updated_at
    BEFORE UPDATE ON predictions.live_pa_predictions
    FOR EACH ROW
    EXECUTE FUNCTION predictions.update_updated_at_column();
