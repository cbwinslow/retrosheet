/*
File: sql/framework/002_feature_discovery_schema.sql
Purpose: Feature discovery, selection, and dimensionality reduction framework
Author: Agent Cascade
Date: 2026-04-24
Depends On: sql/framework/001_framework_schema.sql
Called By: Feature analysis scripts, automated feature selection

Tables Created:
- framework.feature_importance: Feature importance rankings per model
- framework.feature_correlations: Pairwise feature correlations
- framework.pca_results: PCA components and variance explained
- framework.feature_selection_log: Stepwise selection history
- framework.feature_clusters: Correlated feature groupings
- framework.reduced_features: Optimal feature subsets per use case

Notes:
- Integrates with framework.experiments for tracking
- Supports automated feature selection workflows
- Stores PCA loadings for feature interpretation
- Tracks feature stability across time windows
*/

-- ============================================================================
-- FEATURE IMPORTANCE RANKINGS
-- ============================================================================
-- Stores feature importance from various models and methods

CREATE TABLE IF NOT EXISTS framework.feature_importance (
    importance_id SERIAL PRIMARY KEY,

    -- Experiment/Model reference
    experiment_id INTEGER REFERENCES framework.experiments(experiment_id),
    model_version TEXT NOT NULL,
    analysis_method TEXT NOT NULL CHECK (analysis_method IN (
        'xgboost_gain', 'xgboost_weight', 'xgboost_cover',
        'permutation', 'shap_mean', 'shap_std',
        'lasso', 'ridge', 'elastic_net',
        'mutual_info', 'f_regression', 'chi2'
    )),

    -- Feature identification
    feature_name TEXT NOT NULL,
    feature_category TEXT,  -- velocity, location, count, etc.
    feature_group TEXT,     -- baseline, engineered, context, etc.

    -- Importance metrics
    importance_score NUMERIC(10,8) NOT NULL,  -- 0.0 to 1.0
    rank INTEGER NOT NULL,                   -- 1 = most important
    cumulative_importance NUMERIC(10,8),       -- Sum of top N features

    -- Stability across folds/time
    std_dev NUMERIC(10,8),          -- Std dev across CV folds
    min_importance NUMERIC(10,8),   -- Min across folds
    max_importance NUMERIC(10,8),   -- Max across folds

    -- Metadata
    n_samples INTEGER,              -- Training samples used
    target_variable TEXT,           -- What we predicted
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(model_version, analysis_method, feature_name)
);

CREATE INDEX IF NOT EXISTS idx_feature_importance_model ON framework.feature_importance(model_version, rank);
CREATE INDEX IF NOT EXISTS idx_feature_importance_feature ON framework.feature_importance(feature_name, importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_feature_importance_category ON framework.feature_importance(feature_category, importance_score DESC);

COMMENT ON TABLE framework.feature_importance IS 'Feature importance rankings from various methods (XGBoost, SHAP, permutation, etc.)';

-- ============================================================================
-- FEATURE CORRELATIONS
-- ============================================================================
-- Pairwise feature correlations for multicollinearity detection

CREATE TABLE IF NOT EXISTS framework.feature_correlations (
    correlation_id SERIAL PRIMARY KEY,

    dataset_version TEXT NOT NULL,  -- Which data snapshot

    feature_1 TEXT NOT NULL,
    feature_2 TEXT NOT NULL,

    -- Correlation metrics
    pearson_r NUMERIC(5,4),
    spearman_r NUMERIC(5,4),
    mutual_info NUMERIC(6,4),       -- Non-linear dependency

    -- Categorization
    correlation_strength TEXT CHECK (correlation_strength IN ('weak', 'moderate', 'strong', 'very_strong')),
    is_redundant BOOLEAN GENERATED ALWAYS AS (
        correlation_strength IN ('strong', 'very_strong')
    ) STORED,

    -- Recommendation
    keep_feature TEXT,              -- Which to keep if redundant
    drop_reason TEXT,               -- Why the other should drop

    sample_size INTEGER,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(dataset_version, feature_1, feature_2)
);

CREATE INDEX IF NOT EXISTS idx_feature_corr_f1 ON framework.feature_correlations(feature_1, pearson_r DESC);
CREATE INDEX IF NOT EXISTS idx_feature_corr_redundant ON framework.feature_correlations(is_redundant, pearson_r DESC) WHERE is_redundant;

COMMENT ON TABLE framework.feature_correlations IS 'Pairwise feature correlations for detecting multicollinearity and redundancy';

-- ============================================================================
-- PCA RESULTS
-- ============================================================================
-- Principal Component Analysis results for dimensionality reduction

CREATE TABLE IF NOT EXISTS framework.pca_results (
    pca_id SERIAL PRIMARY KEY,

    experiment_id INTEGER REFERENCES framework.experiments(experiment_id),
    analysis_name TEXT NOT NULL,      -- e.g., "pitch_features_2025"

    -- Dataset info
    n_samples INTEGER NOT NULL,
    n_features_original INTEGER NOT NULL,
    features_used TEXT[],             -- List of original features

    -- Component info
    component_number INTEGER NOT NULL,  -- 1, 2, 3, ...
    explained_variance_ratio NUMERIC(6,4),  -- % variance this component
    cumulative_variance NUMERIC(6,4),       -- Running total

    -- Loadings (feature weights for this component)
    top_positive_features JSONB,      -- {feature: weight, ...}
    top_negative_features JSONB,      -- {feature: weight, ...}

    -- Interpretation
    component_label TEXT,             -- Human-readable label
    interpretation_notes TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(analysis_name, component_number)
);

CREATE INDEX IF NOT EXISTS idx_pca_analysis ON framework.pca_results(analysis_name, component_number);
CREATE INDEX IF NOT EXISTS idx_pca_variance ON framework.pca_results(cumulative_variance);

COMMENT ON TABLE framework.pca_results IS 'PCA component analysis with loadings and variance explained';

-- ============================================================================
-- FEATURE SELECTION LOG (Stepwise/Recursive)
-- ============================================================================
-- Tracks stepwise feature selection process

CREATE TABLE IF NOT EXISTS framework.feature_selection_log (
    selection_id SERIAL PRIMARY KEY,

    experiment_id INTEGER REFERENCES framework.experiments(experiment_id),
    selection_method TEXT NOT NULL CHECK (selection_method IN (
        'forward_stepwise', 'backward_stepwise', 'recursive_elimination',
        'lasso', 'elastic_net', 'genetic_algorithm', 'boruta'
    )),

    -- Step info
    step_number INTEGER NOT NULL,
    total_steps INTEGER,

    -- Action taken
    action TEXT NOT NULL CHECK (action IN ('add', 'remove', 'keep')),
    feature_name TEXT NOT NULL,

    -- Performance at this step
    n_features_selected INTEGER,
    validation_score NUMERIC(8,6),      -- e.g., AUC or accuracy
    training_score NUMERIC(8,6),
    score_improvement NUMERIC(8,6),     -- Delta from previous step

    -- Selection criteria
    selection_criterion NUMERIC(10,8),  -- p-value, importance, etc.
    p_value NUMERIC(8,6),              -- For statistical tests

    -- Current feature set snapshot
    selected_features TEXT[],
    rejected_features TEXT[],

    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(experiment_id, step_number, feature_name)
);

CREATE INDEX IF NOT EXISTS idx_feature_sel_exp ON framework.feature_selection_log(experiment_id, step_number);
CREATE INDEX IF NOT EXISTS idx_feature_sel_method ON framework.feature_selection_log(selection_method, validation_score DESC);

COMMENT ON TABLE framework.feature_selection_log IS 'Step-by-step log of feature selection process with performance at each step';

-- ============================================================================
-- FEATURE CLUSTERS (Correlated Groups)
-- ============================================================================
-- Groups of highly correlated features for representative selection

CREATE TABLE IF NOT EXISTS framework.feature_clusters (
    cluster_id SERIAL PRIMARY KEY,

    dataset_version TEXT NOT NULL,
    clustering_method TEXT NOT NULL CHECK (clustering_method IN (
        'correlation', 'hierarchical', 'kmeans', 'dbscan', 'domain_expert'
    )),

    cluster_number INTEGER NOT NULL,
    cluster_name TEXT,              -- e.g., "velocity_metrics", "weather_factors"

    -- Features in cluster
    features TEXT[] NOT NULL,
    n_features INTEGER,

    -- Representative selection
    representative_feature TEXT,      -- Best feature to keep from cluster
    selection_rationale TEXT,       -- Why this one

    -- Cluster characteristics
    avg_correlation NUMERIC(5,4),     -- Mean |r| within cluster
    variance_explained NUMERIC(6,4), -- If PCA on just this cluster

    -- Domain tagging
    domain_category TEXT,           -- physics, context, sequence, etc.

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(dataset_version, clustering_method, cluster_number)
);

CREATE INDEX IF NOT EXISTS idx_feature_clusters_dataset ON framework.feature_clusters(dataset_version, cluster_number);
CREATE INDEX IF NOT EXISTS idx_feature_clusters_domain ON framework.feature_clusters(domain_category);

COMMENT ON TABLE framework.feature_clusters IS 'Groups of correlated features with recommended representative for each group';

-- ============================================================================
-- REDUCED FEATURE SETS (Optimal Subsets)
-- ============================================================================
-- Pre-computed optimal feature sets for different use cases

CREATE TABLE IF NOT EXISTS framework.reduced_features (
    reduction_id SERIAL PRIMARY KEY,

    reduction_name TEXT NOT NULL UNIQUE,  -- e.g., "minimal_50", "optimal_100"
    use_case TEXT NOT NULL,               -- "production", "experiment", "baseline"

    -- Selection criteria
    selection_method TEXT NOT NULL,
    target_n_features INTEGER,
    actual_n_features INTEGER,

    -- Features included
    features TEXT[] NOT NULL,
    feature_categories TEXT[],           -- Which domains are covered

    -- Performance vs full set
    baseline_score NUMERIC(8,6),       -- Full feature set score
    reduced_score NUMERIC(8,6),        -- This subset score
    score_retention NUMERIC(5,4),        -- reduced / baseline

    -- Efficiency metrics
    training_time_reduction NUMERIC(5,2),  -- % faster
    inference_time_reduction NUMERIC(5,2),
    memory_reduction NUMERIC(5,2),           -- % less RAM

    -- Validation
    validation_method TEXT,              -- CV, holdout, temporal
    stability_score NUMERIC(5,4),        -- Across folds/time

    -- Metadata
    source_experiment_id INTEGER REFERENCES framework.experiments(experiment_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by TEXT DEFAULT CURRENT_USER
);

CREATE INDEX IF NOT EXISTS idx_reduced_features_use_case ON framework.reduced_features(use_case, score_retention DESC);
CREATE INDEX IF NOT EXISTS idx_reduced_features_n ON framework.reduced_features(actual_n_features, score_retention DESC);

COMMENT ON TABLE framework.reduced_features IS 'Pre-computed optimal feature subsets for different use cases with performance retention metrics';

-- ============================================================================
-- VIEWS FOR ANALYSIS
-- ============================================================================

-- Top features by multiple methods (consensus ranking)
CREATE OR REPLACE VIEW framework.feature_consensus_ranking AS
WITH method_ranks AS (
    SELECT
        feature_name,
        analysis_method,
        rank,
        importance_score
    FROM framework.feature_importance
    WHERE rank <= 50  -- Top 50 per method
),
consensus AS (
    SELECT
        feature_name,
        COUNT(DISTINCT analysis_method) as n_methods,
        AVG(rank) as avg_rank,
        AVG(importance_score) as avg_importance,
        STDDEV(importance_score) as stability  -- Lower = more consistent
    FROM method_ranks
    GROUP BY feature_name
)
SELECT
    feature_name,
    n_methods,
    ROUND(avg_rank::numeric, 2) as avg_rank,
    ROUND(avg_importance::numeric, 6) as avg_importance,
    ROUND(stability::numeric, 6) as stability_score,
    RANK() OVER (ORDER BY avg_importance DESC, stability ASC) as consensus_rank
FROM consensus
WHERE n_methods >= 2  -- Appears in at least 2 methods
ORDER BY consensus_rank;

COMMENT ON VIEW framework.feature_consensus_ranking IS 'Consensus feature ranking across multiple importance methods';

-- Redundant feature pairs (candidates for removal)
CREATE OR REPLACE VIEW framework.redundant_features AS
SELECT
    feature_1,
    feature_2,
    pearson_r,
    ABS(pearson_r) as abs_correlation,
    CASE
        WHEN ABS(pearson_r) >= 0.95 THEN 'very_strong'
        WHEN ABS(pearson_r) >= 0.85 THEN 'strong'
        WHEN ABS(pearson_r) >= 0.70 THEN 'moderate'
        ELSE 'weak'
    END as strength,
    keep_feature,
    drop_reason
FROM framework.feature_correlations
WHERE ABS(pearson_r) >= 0.70  -- Threshold for redundancy
ORDER BY ABS(pearson_r) DESC;

COMMENT ON VIEW framework.redundant_features IS 'Highly correlated feature pairs with recommendations for which to keep/drop';

-- Feature coverage by domain
CREATE OR REPLACE VIEW framework.feature_domain_coverage AS
SELECT
    feature_category,
    COUNT(*) as n_features,
    COUNT(CASE WHEN rank <= 50 THEN 1 END) as top_50_count,
    ROUND(AVG(importance_score)::numeric, 6) as avg_importance,
    ROUND(STDDEV(importance_score)::numeric, 6) as stability
FROM framework.feature_importance
WHERE analysis_method = 'xgboost_gain'  -- Use one method for consistency
GROUP BY feature_category
ORDER BY avg_importance DESC;

COMMENT ON VIEW framework.feature_domain_coverage IS 'Feature importance statistics by domain category';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SELECT 'Feature discovery schema created successfully' as status;

SELECT COUNT(*) as table_count
FROM information_schema.tables
WHERE table_schema = 'framework'
AND table_name IN (
    'feature_importance', 'feature_correlations', 'pca_results',
    'feature_selection_log', 'feature_clusters', 'reduced_features'
);
