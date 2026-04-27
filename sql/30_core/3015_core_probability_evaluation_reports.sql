-- File: sql/core/079_probability_evaluation_reports.sql
-- Purpose: Create probability evaluation report tables and model comparison views
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS predictions;

CREATE TABLE IF NOT EXISTS predictions.calibration_reports (
    calibration_report_id bigserial PRIMARY KEY,
    target_id text NOT NULL REFERENCES predictions.prediction_targets (target_id),
    model_id bigint NOT NULL REFERENCES models.model_registry (model_id),
    prediction_run_id bigint REFERENCES predictions.prediction_runs (prediction_run_id),
    report_name text NOT NULL,
    report_scope text NOT NULL,
    calibration_method text NOT NULL,
    calibration_window daterange,
    evaluation_window daterange,
    summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    per_class_summary jsonb NOT NULL DEFAULT '[]'::jsonb,
    subgroup_summary jsonb NOT NULL DEFAULT '[]'::jsonb,
    notes text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS calibration_reports_target_created_idx
ON predictions.calibration_reports (target_id, created_at DESC);

CREATE INDEX IF NOT EXISTS calibration_reports_model_created_idx
ON predictions.calibration_reports (model_id, created_at DESC);

CREATE INDEX IF NOT EXISTS calibration_reports_summary_gin_idx
ON predictions.calibration_reports USING gin (summary);

CREATE TABLE IF NOT EXISTS predictions.bootstrap_reports (
    bootstrap_report_id bigserial PRIMARY KEY,
    target_id text NOT NULL REFERENCES predictions.prediction_targets (target_id),
    model_id bigint NOT NULL REFERENCES models.model_registry (model_id),
    prediction_run_id bigint REFERENCES predictions.prediction_runs (prediction_run_id),
    report_name text NOT NULL,
    resampling_method text NOT NULL,
    replicates integer NOT NULL,
    seed integer,
    evaluation_window daterange,
    summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    notes text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS bootstrap_reports_target_created_idx
ON predictions.bootstrap_reports (target_id, created_at DESC);

CREATE INDEX IF NOT EXISTS bootstrap_reports_model_created_idx
ON predictions.bootstrap_reports (model_id, created_at DESC);

CREATE INDEX IF NOT EXISTS bootstrap_reports_summary_gin_idx
ON predictions.bootstrap_reports USING gin (summary);

CREATE OR REPLACE VIEW predictions.recent_calibration_reports AS
SELECT
    calibration_report_id,
    created_at,
    target_id,
    model_id,
    prediction_run_id,
    report_name,
    report_scope,
    calibration_method,
    calibration_window,
    evaluation_window,
    summary
FROM predictions.calibration_reports
ORDER BY created_at DESC;

CREATE OR REPLACE VIEW predictions.recent_bootstrap_reports AS
SELECT
    bootstrap_report_id,
    created_at,
    target_id,
    model_id,
    prediction_run_id,
    report_name,
    resampling_method,
    replicates,
    seed,
    evaluation_window,
    summary
FROM predictions.bootstrap_reports
ORDER BY created_at DESC;

-- Table comments
COMMENT ON TABLE predictions.calibration_reports IS 'calibration reports data table';
COMMENT ON TABLE predictions.bootstrap_reports IS 'bootstrap reports data table';
