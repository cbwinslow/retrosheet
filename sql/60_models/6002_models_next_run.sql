/*
File: sql/601_models_next_run.sql
Purpose: Next-Run Probability Model - Predict if a run scores in remainder of inning
Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
Depends On: features.win_expectancy_matrix, features.leverage_index_matrix
Called By: scripts/models/train_next_run_model.sh

Tables Created:
- models.next_run_training_data: Labeled training examples
- models.next_run_features: Feature vectors for model input
- models.next_run_predictions: Model inference results
*/

-- Ensure models schema exists
CREATE SCHEMA IF NOT EXISTS models;

-- =============================================
-- NEXT-RUN TRAINING DATA
-- =============================================

CREATE TABLE IF NOT EXISTS models.next_run_training_data (
    training_id SERIAL PRIMARY KEY,
    game_pk INTEGER NOT NULL,
    season INTEGER NOT NULL,
    
    -- Game state at observation point
    observation_at_bat_index INTEGER NOT NULL,
    inning INTEGER NOT NULL,
    is_top BOOLEAN NOT NULL,
    outs INTEGER NOT NULL CHECK (outs IN (0, 1, 2)),
    runner_1b BOOLEAN DEFAULT FALSE,
    runner_2b BOOLEAN DEFAULT FALSE,
    runner_3b BOOLEAN DEFAULT FALSE,
    score_home INTEGER NOT NULL,
    score_away INTEGER NOT NULL,
    run_diff INTEGER NOT NULL,  -- Home minus away (can be negative)
    
    -- Base state encoding (0-23)
    base_state INTEGER GENERATED ALWAYS AS (
        CASE 
            WHEN runner_1b AND runner_2b AND runner_3b THEN 7
            WHEN runner_2b AND runner_3b THEN 6
            WHEN runner_1b AND runner_3b THEN 5
            WHEN runner_3b THEN 4
            WHEN runner_1b AND runner_2b THEN 3
            WHEN runner_2b THEN 2
            WHEN runner_1b THEN 1
            ELSE 0
        END * 3 + outs
    ) STORED,
    
    -- Team/batter context
    batting_team_id INTEGER,
    pitching_team_id INTEGER,
    batter_id INTEGER,
    pitcher_id INTEGER,
    batter_hand VARCHAR(1),
    pitcher_hand VARCHAR(1),
    
    -- Target: Did a run score before inning ended?
    runs_scored_before_inning_end INTEGER NOT NULL,
    did_run_score BOOLEAN GENERATED ALWAYS AS (runs_scored_before_inning_end > 0) STORED,
    
    -- Additional outcome info
    total_runs_in_inning INTEGER,
    final_outs_in_inning INTEGER,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(game_pk, observation_at_bat_index)
);

-- Indexes for training queries
CREATE INDEX IF NOT EXISTS idx_next_run_train_game ON models.next_run_training_data(game_pk);
CREATE INDEX IF NOT EXISTS idx_next_run_train_season ON models.next_run_training_data(season);
CREATE INDEX IF NOT EXISTS idx_next_run_train_base ON models.next_run_training_data(base_state);
CREATE INDEX IF NOT EXISTS idx_next_run_train_target ON models.next_run_training_data(did_run_score);
CREATE INDEX IF NOT EXISTS idx_next_run_train_inning ON models.next_run_training_data(inning, is_top);

-- Comments
COMMENT ON TABLE models.next_run_training_data IS 'Training data for Next-Run Probability Model';
COMMENT ON COLUMN models.next_run_training_data.did_run_score IS 'Target label: TRUE if any run scored before inning end';
COMMENT ON COLUMN models.next_run_training_data.base_state IS 'Encoded base state (0-23): runners * 3 + outs';

-- =============================================
-- NEXT-RUN FEATURE VECTORS
-- =============================================

CREATE TABLE IF NOT EXISTS models.next_run_features (
    feature_id SERIAL PRIMARY KEY,
    training_id INTEGER REFERENCES models.next_run_training_data(training_id),
    game_pk INTEGER NOT NULL,
    season INTEGER NOT NULL,
    
    -- Game state features (raw)
    inning_normalized NUMERIC(4,2),  -- inning / 9 (to handle extras)
    is_top_half BOOLEAN,
    outs INTEGER,
    base_state INTEGER,
    runners_on INTEGER,  -- Count of runners
    run_diff_normalized NUMERIC(4,2),  -- run_diff / 10 (clipped)
    
    -- Win Expectancy features
    current_we NUMERIC(4,3),  -- Win expectancy at this state
    we_with_run NUMERIC(4,3),  -- WE if a run scores
    we_delta_on_run NUMERIC(4,3),  -- WE gain from scoring
    
    -- Leverage Index features
    current_li NUMERIC(3,2),
    li_rating VARCHAR(10),
    is_high_leverage BOOLEAN,
    
    -- Run expectancy features
    expected_runs NUMERIC(3,2),  -- Expected runs remainder of inning
    run_probability NUMERIC(4,3),  -- Historical P(run scores) from this state
    
    -- Matchup features (if available)
    matchup_score NUMERIC(3,2),
    is_platoon_advantage BOOLEAN,
    batter_l14_ops NUMERIC(4,3),
    pitcher_l14_era NUMERIC(4,2),
    
    -- Bullpen features (if late inning)
    batting_team_bullpen_fatigue NUMERIC(3,2),
    pitching_team_bullpen_fatigue NUMERIC(3,2),
    bullpen_advantage_diff NUMERIC(4,2),
    
    -- Historical state-based probability (from WE matrix)
    historical_run_rate NUMERIC(4,3),
    
    -- Feature vector as JSON (for flexible model inputs)
    feature_vector JSONB,
    
    -- Metadata
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(training_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_next_run_feat_train ON models.next_run_features(training_id);
CREATE INDEX IF NOT EXISTS idx_next_run_feat_game ON models.next_run_features(game_pk);
CREATE INDEX IF NOT EXISTS idx_next_run_feat_we ON models.next_run_features(current_we);
CREATE INDEX IF NOT EXISTS idx_next_run_feat_li ON models.next_run_features(current_li);
CREATE INDEX IF NOT EXISTS idx_next_run_feat_vector ON models.next_run_features USING GIN(feature_vector);

-- Comments
COMMENT ON TABLE models.next_run_features IS 'Feature vectors for Next-Run Probability Model';
COMMENT ON COLUMN models.next_run_features.feature_vector IS 'Complete feature vector as JSON for model input';

-- =============================================
-- NEXT-RUN PREDICTIONS
-- =============================================

CREATE TABLE IF NOT EXISTS models.next_run_predictions (
    prediction_id SERIAL PRIMARY KEY,
    model_version VARCHAR(20) NOT NULL,
    game_pk INTEGER NOT NULL,
    season INTEGER NOT NULL,
    
    -- Observation point
    observation_at_bat_index INTEGER NOT NULL,
    inning INTEGER NOT NULL,
    is_top BOOLEAN NOT NULL,
    
    -- Prediction
    run_probability NUMERIC(4,3) NOT NULL,  -- 0.0 to 1.0
    confidence NUMERIC(4,3),  -- Model confidence
    prediction_label BOOLEAN GENERATED ALWAYS AS (run_probability > 0.5) STORED,
    
    -- Calibration bins
    probability_bin VARCHAR(10) GENERATED ALWAYS AS (
        CASE 
            WHEN run_probability < 0.10 THEN '0-10%'
            WHEN run_probability < 0.20 THEN '10-20%'
            WHEN run_probability < 0.30 THEN '20-30%'
            WHEN run_probability < 0.40 THEN '30-40%'
            WHEN run_probability < 0.50 THEN '40-50%'
            WHEN run_probability < 0.60 THEN '50-60%'
            WHEN run_probability < 0.70 THEN '60-70%'
            WHEN run_probability < 0.80 THEN '70-80%'
            WHEN run_probability < 0.90 THEN '80-90%'
            ELSE '90-100%'
        END
    ) STORED,
    
    -- Feature values at prediction time (for debugging)
    feature_snapshot JSONB,
    
    -- Actual outcome (filled in after inning ends)
    actual_outcome BOOLEAN,
    runs_scored INTEGER,
    
    -- Evaluation metrics (filled after outcome known)
    is_correct BOOLEAN,
    log_loss NUMERIC(6,4),
    brier_score NUMERIC(6,4),
    
    -- Timestamps
    predicted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    outcome_recorded_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(model_version, game_pk, observation_at_bat_index)
);

-- Indexes for prediction queries
CREATE INDEX IF NOT EXISTS idx_next_run_pred_model ON models.next_run_predictions(model_version);
CREATE INDEX IF NOT EXISTS idx_next_run_pred_game ON models.next_run_predictions(game_pk);
CREATE INDEX IF NOT EXISTS idx_next_run_pred_prob ON models.next_run_predictions(run_probability);
CREATE INDEX IF NOT EXISTS idx_next_run_pred_bin ON models.next_run_predictions(probability_bin);
CREATE INDEX IF NOT EXISTS idx_next_run_pred_correct ON models.next_run_predictions(is_correct) WHERE is_correct IS NOT NULL;

-- Comments
COMMENT ON TABLE models.next_run_predictions IS 'Next-Run Probability Model predictions';
COMMENT ON COLUMN models.next_run_predictions.run_probability IS 'Predicted probability that a run will score';
COMMENT ON COLUMN models.next_run_predictions.brier_score IS 'Squared difference between prediction and outcome';

-- =============================================
-- FUNCTIONS
-- =============================================

-- Function: Populate training data from plays
CREATE OR REPLACE FUNCTION models.populate_next_run_training(
    p_season INTEGER,
    p_sample_rate NUMERIC DEFAULT 1.0  -- 1.0 = all, 0.1 = 10% sample
) RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 0;
BEGIN
    INSERT INTO models.next_run_training_data (
        game_pk, season, observation_at_bat_index,
        inning, is_top, outs,
        runner_1b, runner_2b, runner_3b,
        score_home, score_away, run_diff,
        batting_team_id, pitching_team_id,
        batter_id, pitcher_id,
        -- Target will be updated by trigger or separate process
        runs_scored_before_inning_end
    )
    SELECT 
        p.game_pk,
        p.season,
        p.at_bat_index,
        p.inning,
        p.is_top,
        p.outs,
        p.runner_on_1b_id IS NOT NULL,
        p.runner_on_2b_id IS NOT NULL,
        p.runner_on_3b_id IS NOT NULL,
        p.score_home,
        p.score_away,
        p.score_home - p.score_away,
        CASE WHEN p.is_top THEN p.away_team_id ELSE p.home_team_id END,
        CASE WHEN p.is_top THEN p.home_team_id ELSE p.away_team_id END,
        p.batter_id,
        p.pitcher_id,
        0  -- Will be updated with actual runs scored
    FROM raw_gumbo.plays p
    WHERE p.season = p_season
      AND p.outs < 3  -- Only valid states
      AND (p_sample_rate >= 1.0 OR random() < p_sample_rate)
    ON CONFLICT (game_pk, observation_at_bat_index) DO NOTHING;
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Compute features for a training example
CREATE OR REPLACE FUNCTION models.compute_next_run_features(
    p_training_id INTEGER
) RETURNS VOID AS $$
DECLARE
    v_training models.next_run_training_data%ROWTYPE;
    v_we NUMERIC;
    v_li NUMERIC;
    v_expected_runs NUMERIC;
    v_historical_rate NUMERIC;
BEGIN
    -- Get training record
    SELECT * INTO v_training
    FROM models.next_run_training_data
    WHERE training_id = p_training_id;
    
    IF NOT FOUND THEN
        RETURN;
    END IF;
    
    -- Get WE for current state
    SELECT we INTO v_we
    FROM features.win_expectancy_matrix
    WHERE inning = LEAST(v_training.inning, 9)
      AND is_top = v_training.is_top
      AND outs = v_training.outs
      AND base_state = v_training.base_state
      AND run_diff = v_training.run_diff
    LIMIT 1;
    
    -- Get LI
    SELECT li INTO v_li
    FROM features.leverage_index_matrix
    WHERE inning = LEAST(v_training.inning, 9)
      AND is_top = v_training.is_top
      AND outs = v_training.outs
      AND base_state = v_training.base_state
      AND run_diff = v_training.run_diff
    LIMIT 1;
    
    -- Historical run rate from this state
    SELECT AVG(CASE WHEN did_run_score THEN 1.0 ELSE 0.0 END)
    INTO v_historical_rate
    FROM models.next_run_training_data
    WHERE season < v_training.season  -- Prior seasons only
      AND outs = v_training.outs
      AND base_state = v_training.base_state
      AND inning = v_training.inning;
    
    -- Get matchup features if available
    INSERT INTO models.next_run_features (
        training_id, game_pk, season,
        inning_normalized, is_top_half, outs, base_state,
        runners_on, run_diff_normalized,
        current_we, we_delta_on_run,
        current_li, li_rating, is_high_leverage,
        run_probability, historical_run_rate,
        feature_vector
    )
    SELECT 
        p_training_id,
        v_training.game_pk,
        v_training.season,
        LEAST(v_training.inning, 12) / 9.0,
        v_training.is_top,
        v_training.outs,
        v_training.base_state,
        (CASE WHEN v_training.runner_1b THEN 1 ELSE 0 END +
         CASE WHEN v_training.runner_2b THEN 1 ELSE 0 END +
         CASE WHEN v_training.runner_3b THEN 1 ELSE 0 END),
        GREATEST(-10, LEAST(10, v_training.run_diff)) / 10.0,
        COALESCE(v_we, 0.5),
        0.05,  -- Approximate WE delta for a run
        COALESCE(v_li, 1.0),
        CASE 
            WHEN v_li >= 2.5 THEN 'very_high'
            WHEN v_li >= 1.5 THEN 'high'
            WHEN v_li >= 0.8 THEN 'medium'
            ELSE 'low'
        END,
        v_li >= 1.5,
        COALESCE(v_historical_rate, 
            -- Default by base state
            CASE v_training.base_state / 3  -- runners only
                WHEN 0 THEN 0.15  -- Empty bases
                WHEN 1 THEN 0.28  -- Runner on
                WHEN 2 THEN 0.35  -- Two on
                WHEN 3 THEN 0.42  -- Bases loaded
                ELSE 0.25
            END * (1 + 0.1 * (2 - v_training.outs))  -- Boost for fewer outs
        ),
        COALESCE(v_historical_rate, 0.25),
        jsonb_build_object(
            'inning', v_training.inning,
            'outs', v_training.outs,
            'base_state', v_training.base_state,
            'run_diff', v_training.run_diff,
            'we', v_we,
            'li', v_li,
            'historical_rate', v_historical_rate
        )
    ON CONFLICT (training_id) DO UPDATE SET
        current_we = EXCLUDED.current_we,
        current_li = EXCLUDED.current_li,
        run_probability = EXCLUDED.run_probability,
        feature_vector = EXCLUDED.feature_vector,
        computed_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Function: Record prediction outcome
CREATE OR REPLACE FUNCTION models.record_next_run_outcome(
    p_prediction_id INTEGER,
    p_actual_outcome BOOLEAN,
    p_runs_scored INTEGER
) RETURNS VOID AS $$
DECLARE
    v_pred models.next_run_predictions%ROWTYPE;
    v_log_loss NUMERIC;
    v_brier NUMERIC;
BEGIN
    -- Get prediction
    SELECT * INTO v_pred
    FROM models.next_run_predictions
    WHERE prediction_id = p_prediction_id;
    
    IF NOT FOUND THEN
        RETURN;
    END IF;
    
    -- Calculate metrics
    -- Log loss: -[y*log(p) + (1-y)*log(1-p)]
    v_log_loss := CASE 
        WHEN p_actual_outcome THEN -LN(GREATEST(0.0001, v_pred.run_probability))
        ELSE -LN(GREATEST(0.0001, 1 - v_pred.run_probability))
    END;
    
    -- Brier score: (p - y)^2
    v_brier := POWER(v_pred.run_probability - CASE WHEN p_actual_outcome THEN 1 ELSE 0 END, 2);
    
    -- Update
    UPDATE models.next_run_predictions
    SET actual_outcome = p_actual_outcome,
        runs_scored = p_runs_scored,
        is_correct = (v_pred.prediction_label = p_actual_outcome),
        log_loss = v_log_loss,
        brier_score = v_brier,
        outcome_recorded_at = NOW()
    WHERE prediction_id = p_prediction_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- VIEWS
-- =============================================

-- View: Model calibration by probability bin
CREATE OR REPLACE VIEW models.next_run_calibration AS
SELECT 
    model_version,
    probability_bin,
    COUNT(*) as n_predictions,
    AVG(run_probability) as avg_predicted_prob,
    AVG(CASE WHEN actual_outcome THEN 1.0 ELSE 0.0 END) as actual_rate,
    AVG(run_probability) - AVG(CASE WHEN actual_outcome THEN 1.0 ELSE 0.0 END) as calibration_error,
    AVG(brier_score) as avg_brier_score,
    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)::NUMERIC / COUNT(*) as accuracy
FROM models.next_run_predictions
WHERE actual_outcome IS NOT NULL
GROUP BY model_version, probability_bin
ORDER BY model_version, 
    CASE probability_bin
        WHEN '0-10%' THEN 1
        WHEN '10-20%' THEN 2
        WHEN '20-30%' THEN 3
        WHEN '30-40%' THEN 4
        WHEN '40-50%' THEN 5
        WHEN '50-60%' THEN 6
        WHEN '60-70%' THEN 7
        WHEN '70-80%' THEN 8
        WHEN '80-90%' THEN 9
        ELSE 10
    END;

-- View: Model performance summary
CREATE OR REPLACE VIEW models.next_run_performance AS
SELECT 
    model_version,
    COUNT(*) as total_predictions,
    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)::NUMERIC / COUNT(*) as accuracy,
    AVG(brier_score) as mean_brier_score,
    AVG(log_loss) as mean_log_loss,
    -- Brier skill score vs baseline (0.25 for always predicting 0.5)
    1 - (AVG(brier_score) / 0.25) as brier_skill_score,
    -- By leverage
    AVG(CASE WHEN (feature_snapshot->>'li')::NUMERIC >= 1.5 THEN brier_score END) as high_leverage_brier,
    AVG(CASE WHEN (feature_snapshot->>'li')::NUMERIC < 1.5 THEN brier_score END) as low_leverage_brier
FROM models.next_run_predictions
WHERE actual_outcome IS NOT NULL
GROUP BY model_version;

-- View: High-confidence predictions
CREATE OR REPLACE VIEW models.high_confidence_next_run AS
SELECT 
    model_version,
    game_pk,
    observation_at_bat_index,
    inning,
    is_top,
    run_probability,
    prediction_label,
    probability_bin,
    feature_snapshot
FROM models.next_run_predictions
WHERE run_probability > 0.8 OR run_probability < 0.2
ORDER BY ABS(run_probability - 0.5) DESC;

COMMENT ON VIEW models.next_run_calibration IS 'Calibration analysis by probability bin';
COMMENT ON VIEW models.next_run_performance IS 'Overall model performance metrics by version';
COMMENT ON VIEW models.high_confidence_next_run IS 'Predictions with high confidence (p > 0.8 or p < 0.2)';
