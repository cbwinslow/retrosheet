-- File: sql/mlb/151_register_model.sql
-- Purpose: Register a trained model artifact in the model registry
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE OR REPLACE FUNCTION models.register_model(
    p_target_id TEXT,
    p_model_name TEXT,
    p_model_family TEXT,
    p_artifact_uri TEXT,
    p_feature_spec JSONB,
    p_metrics JSONB DEFAULT NULL,
    p_training_window DATERANGE DEFAULT NULL,
    p_is_active BOOLEAN DEFAULT FALSE
)
RETURNS BIGINT AS $$
DECLARE
    v_model_id BIGINT;
    v_version_suffix TEXT;
BEGIN
    -- Generate version suffix from artifact filename timestamp
    v_version_suffix := SUBSTRING(p_artifact_uri FROM '(\d{8}T\d{6}Z)'); 
    
    INSERT INTO models.model_registry (
        target_id,
        model_name,
        model_family,
        model_version,
        artifact_uri,
        training_window,
        feature_spec,
        metrics,
        is_active,
        created_at
    )
    VALUES (
        p_target_id,
        p_model_name,
        p_model_family,
        v_version_suffix,
        p_artifact_uri,
        p_training_window,
        p_feature_spec,
        p_metrics,
        p_is_active,
        NOW()
    )
    RETURNING model_id INTO v_model_id;
    
    RETURN v_model_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION models.register_model IS
'Register a trained model artifact. Usage: SELECT models.register_model(
    target_id := ''pa_outcome_distribution'',
    model_name := ''hist_gradient_boosting_multiclass'',
    model_family := ''hist_gradient_boosting'',
    artifact_uri := ''data/models/pa_outcome_distribution_hist_gradient_boosting_multiclass_20260412T045759Z.joblib'',
    feature_spec := ''{"feature_set": "advanced_count"}''::jsonb,
    metrics := ''{"log_loss": 1.5089, "accuracy": 0.413}''::jsonb,
    is_active := TRUE
);';

-- Function to promote (activate) a model - deactivates others for same target
CREATE OR REPLACE FUNCTION models.promote_model(
    p_model_id BIGINT
)
RETURNS VOID AS $$
BEGIN
    -- First deactivate all models for this target
    UPDATE models.model_registry
    SET is_active = FALSE
    WHERE target_id = (SELECT target_id FROM models.model_registry WHERE model_id = p_model_id)
      AND is_active = TRUE;
    
    -- Then activate the specified model
    UPDATE models.model_registry
    SET is_active = TRUE
    WHERE model_id = p_model_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION models.promote_model IS
'Promote a model to active status (auto-deactivates others for same target). Usage: SELECT models.promote_model(1);';

-- View to see active models
CREATE OR REPLACE VIEW models.v_active_models AS
SELECT
    mr.model_id,
    mr.target_id,
    mr.model_name,
    mr.model_family,
    mr.model_version,
    mr.artifact_uri,
    mr.feature_spec,
    mr.metrics,
    mr.created_at,
    pt.description AS target_description,
    pt.question_template
FROM models.model_registry AS mr
INNER JOIN predictions.prediction_targets AS pt ON mr.target_id = pt.target_id
WHERE mr.is_active = TRUE
ORDER BY pt.target_id ASC, mr.created_at DESC;

COMMENT ON VIEW models.v_active_models IS 'Currently active models with target info.';

