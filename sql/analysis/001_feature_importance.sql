/*
File: sql/analysis/001_feature_importance.sql
Purpose: Store feature importance scores from model training
Author: Agent Cascade
Date: 2026-04-24
Depends On: models.model_registry
Called By: scripts/analysis/feature_interaction_explorer.py, training scripts

Tables Created:
- analysis.feature_importance: Feature importance scores by model

Notes:
- Supports XGBoost gain, SHAP values, permutation importance
- Links to models.model_registry for model versioning
- Used by feature interaction explorer and feature selection
*/

-- Feature importance table
CREATE TABLE IF NOT EXISTS analysis.feature_importance (
    importance_id BIGSERIAL PRIMARY KEY,
    model_id BIGINT NOT NULL REFERENCES models.model_registry (model_id),
    feature_name TEXT NOT NULL,
    importance_score NUMERIC NOT NULL,
    importance_rank INT,  -- Rank within model (1 = most important)
    analysis_method TEXT NOT NULL CHECK (analysis_method IN (
        'xgboost_gain',
        'xgboost_weight',
        'xgboost_cover',
        'shap_mean_abs',
        'permutation',
        'correlation'
    )),
    additional_metrics JSONB,  -- Method-specific metrics (e.g., SHAP std)
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_feature_importance_model
ON analysis.feature_importance (model_id, analysis_method);

CREATE INDEX IF NOT EXISTS idx_feature_importance_feature
ON analysis.feature_importance (feature_name, importance_score DESC);

CREATE INDEX IF NOT EXISTS idx_feature_importance_method
ON analysis.feature_importance (analysis_method, computed_at DESC);

-- Comments
COMMENT ON TABLE analysis.feature_importance IS
'Feature importance scores for trained models - used by feature selection and interaction analysis';

COMMENT ON COLUMN analysis.feature_importance.importance_score IS
'Normalized importance score (0-1 range, higher = more important)';

COMMENT ON COLUMN analysis.feature_importance.analysis_method IS
'Method used to compute importance: xgboost_gain (default), shap_mean_abs, permutation';

-- View: Top features by target
CREATE OR REPLACE VIEW analysis.top_features_by_target AS
SELECT
    mr.target_id,
    mr.model_name,
    mr.model_family,
    fi.feature_name,
    fi.importance_score,
    fi.analysis_method,
    fi.computed_at
FROM analysis.feature_importance AS fi
INNER JOIN models.model_registry AS mr ON fi.model_id = mr.model_id
WHERE mr.is_active = TRUE
ORDER BY mr.target_id ASC, fi.importance_score DESC;

COMMENT ON VIEW analysis.top_features_by_target IS
'Top features for each active model - quick reference for feature selection';
