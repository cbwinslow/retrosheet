-- File: sql/core/081_probability_calibration_artifacts.sql
-- Purpose: Create calibration artifact tables and model reliability views
-- Author: Agent Cascade
-- Date: 2026-04-24
ALTER TABLE predictions.calibration_reports
ADD COLUMN IF NOT EXISTS artifact_uri text;

CREATE INDEX IF NOT EXISTS calibration_reports_artifact_created_idx
ON predictions.calibration_reports (model_id, created_at DESC)
WHERE artifact_uri IS NOT NULL;

DROP VIEW IF EXISTS predictions.recent_calibration_reports;

CREATE VIEW predictions.recent_calibration_reports AS
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
    artifact_uri,
    summary
FROM predictions.calibration_reports
ORDER BY created_at DESC;

