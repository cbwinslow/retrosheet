/*
File: sql/602_models_pa_outcome.sql
Purpose: Plate Appearance Outcome Model - Predict single PA result
Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
Depends On: features.matchup_features, features.rolling_form_features
Called By: scripts/models/train_pa_outcome_model.sh

Tables Created:
- models.pa_outcome_training_data: Labeled training examples
- models.pa_outcome_features: Feature vectors
- models.pa_outcome_predictions: Model inference results
*/

-- Ensure models schema exists
CREATE SCHEMA IF NOT EXISTS models;

-- =============================================
-- PA OUTCOME CATEGORIES
-- =============================================

-- Outcome categories for classification:
-- 0: out (in play out, strikeout, etc.)
-- 1: walk (BB, HBP)
-- 2: single
-- 3: double
-- 4: triple
-- 5: home run
-- 6: error/reach (rare, often grouped with single)

CREATE TYPE models.pa_outcome_category AS ENUM (
    'out', 'walk', 'single', 'double', 'triple', 'home_run', 'error'
);

-- =============================================
-- PA OUTCOME TRAINING DATA
-- =============================================

CREATE TABLE IF NOT EXISTS models.pa_outcome_training_data (
    training_id SERIAL PRIMARY KEY,
    game_pk INTEGER NOT NULL,
    season INTEGER NOT NULL,
    
    -- Play identification
    at_bat_index INTEGER NOT NULL,
    play_id VARCHAR(50),  -- External play ID if available
    
    -- Game state
    inning INTEGER NOT NULL,
    is_top BOOLEAN NOT NULL,
    outs INTEGER NOT NULL CHECK (outs IN (0, 1, 2)),
    runner_1b BOOLEAN DEFAULT FALSE,
    runner_2b BOOLEAN DEFAULT FALSE,
    runner_3b BOOLEAN DEFAULT FALSE,
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
        END
    ) STORED,
    
    -- Score context
    score_home INTEGER NOT NULL,
    score_away INTEGER NOT NULL,
    run_diff INTEGER NOT NULL,
    leverage_index NUMERIC(4,2),
    is_high_leverage BOOLEAN,
    
    -- Players
    batter_id INTEGER NOT NULL,
    pitcher_id INTEGER NOT NULL,
    batting_team_id INTEGER,
    pitching_team_id INTEGER,
    
    -- Matchup context
    batter_hand VARCHAR(1),
    pitcher_hand VARCHAR(1),
    is_platoon_advantage BOOLEAN,
    
    -- Target: What happened?
    outcome models.pa_outcome_category NOT NULL,
    outcome_encoded INTEGER GENERATED ALWAYS AS (
        CASE outcome
            WHEN 'out' THEN 0
            WHEN 'walk' THEN 1
            WHEN 'single' THEN 2
            WHEN 'double' THEN 3
            WHEN 'triple' THEN 4
            WHEN 'home_run' THEN 5
            WHEN 'error' THEN 6
        END
    ) STORED,
    
    -- Detailed outcome for reference
    event_type VARCHAR(50),  -- From raw data: 'Strikeout', 'Single', etc.
    detailed_event VARCHAR(100),
    
    -- Run production from PA
    runs_scored INTEGER DEFAULT 0,
    rbi INTEGER DEFAULT 0,
    is_sacrifice BOOLEAN DEFAULT FALSE,
    is_sac_fly BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(game_pk, at_bat_index)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pa_train_game ON models.pa_outcome_training_data(game_pk);
CREATE INDEX IF NOT EXISTS idx_pa_train_season ON models.pa_outcome_training_data(season);
CREATE INDEX IF NOT EXISTS idx_pa_train_outcome ON models.pa_outcome_training_data(outcome);
CREATE INDEX IF NOT EXISTS idx_pa_train_batter ON models.pa_outcome_training_data(batter_id);
CREATE INDEX IF NOT EXISTS idx_pa_train_pitcher ON models.pa_outcome_training_data(pitcher_id);
CREATE INDEX IF NOT EXISTS idx_pa_train_base ON models.pa_outcome_training_data(base_state);

-- Comments
COMMENT ON TABLE models.pa_outcome_training_data IS 'Training data for Plate Appearance Outcome Model';
COMMENT ON COLUMN models.pa_outcome_training_data.outcome IS 'Target: PA result category (out/walk/single/double/triple/home_run)';
COMMENT ON TYPE models.pa_outcome_category IS 'PA outcome categories for multi-class classification';

-- =============================================
-- PA OUTCOME FEATURE VECTORS
-- =============================================

CREATE TABLE IF NOT EXISTS models.pa_outcome_features (
    feature_id SERIAL PRIMARY KEY,
    training_id INTEGER REFERENCES models.pa_outcome_training_data(training_id),
    game_pk INTEGER NOT NULL,
    season INTEGER NOT NULL,
    
    -- Game state features
    inning_normalized NUMERIC(4,2),
    is_top_half BOOLEAN,
    outs INTEGER,
    base_state INTEGER,
    run_diff_normalized NUMERIC(4,2),
    leverage_index NUMERIC(4,2),
    is_high_leverage BOOLEAN,
    
    -- Matchup features
    matchup_score NUMERIC(3,2),  -- 0-1, higher = better for batter
    career_matchup_pa INTEGER,
    career_matchup_avg NUMERIC(4,3),
    is_platoon_advantage BOOLEAN,
    
    -- Batter form features
    batter_l7_ops NUMERIC(4,3),
    batter_l14_ops NUMERIC(4,3),
    batter_l30_ops NUMERIC(4,3),
    batter_trend VARCHAR(10),
    batter_is_hot BOOLEAN,
    
    -- Batter platoon
    batter_vs_hand_ops NUMERIC(4,3),  -- OPS vs this pitcher's hand
    batter_season_avg NUMERIC(4,3),
    batter_season_obp NUMERIC(4,3),
    batter_season_slg NUMERIC(4,3),
    
    -- Pitcher form features
    pitcher_l7_era NUMERIC(5,2),
    pitcher_l14_era NUMERIC(5,2),
    pitcher_l30_era NUMERIC(5,2),
    pitcher_l7_whip NUMERIC(4,2),
    pitcher_l30_k_9 NUMERIC(4,1),
    pitcher_trend VARCHAR(10),
    pitcher_is_hot BOOLEAN,
    
    -- Pitcher platoon
    pitcher_vs_hand_avg NUMERIC(4,3),  -- Avg allowed vs this batter's hand
    pitcher_vs_hand_ops_allowed NUMERIC(4,3),
    pitcher_season_era NUMERIC(5,2),
    pitcher_season_whip NUMERIC(4,2),
    pitcher_season_k_9 NUMERIC(4,1),
    
    -- Historical rates (for this matchup profile)
    historical_out_rate NUMERIC(4,3),
    historical_walk_rate NUMERIC(4,3),
    historical_hit_rate NUMERIC(4,3),
    historical_xbh_rate NUMERIC(4,3),  -- extra base hit rate
    historical_hr_rate NUMERIC(4,3),
    
    -- Feature vector as JSON
    feature_vector JSONB,
    
    -- Metadata
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(training_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pa_feat_train ON models.pa_outcome_features(training_id);
CREATE INDEX IF NOT EXISTS idx_pa_feat_game ON models.pa_outcome_features(game_pk);
CREATE INDEX IF NOT EXISTS idx_pa_feat_matchup ON models.pa_outcome_features(matchup_score);
CREATE INDEX IF NOT EXISTS idx_pa_feat_vector ON models.pa_outcome_features USING GIN(feature_vector);

-- Comments
COMMENT ON TABLE models.pa_outcome_features IS 'Feature vectors for PA Outcome Model';
COMMENT ON COLUMN models.pa_outcome_features.matchup_score IS '0-1 score, higher = better matchup for batter';

-- =============================================
-- PA OUTCOME PREDICTIONS
-- =============================================

CREATE TABLE IF NOT EXISTS models.pa_outcome_predictions (
    prediction_id SERIAL PRIMARY KEY,
    model_version VARCHAR(20) NOT NULL,
    game_pk INTEGER NOT NULL,
    season INTEGER NOT NULL,
    
    -- Observation point
    at_bat_index INTEGER NOT NULL,
    inning INTEGER NOT NULL,
    is_top BOOLEAN NOT NULL,
    
    -- Batter/Pitcher
    batter_id INTEGER NOT NULL,
    pitcher_id INTEGER NOT NULL,
    
    -- Predicted probabilities (sum to 1.0)
    prob_out NUMERIC(4,3) NOT NULL,
    prob_walk NUMERIC(4,3) NOT NULL,
    prob_single NUMERIC(4,3) NOT NULL,
    prob_double NUMERIC(4,3) NOT NULL,
    prob_triple NUMERIC(4,3) NOT NULL,
    prob_home_run NUMERIC(4,3) NOT NULL,
    
    -- Prediction
    predicted_outcome models.pa_outcome_category GENERATED ALWAYS AS (
        CASE GREATEST(prob_out, prob_walk, prob_single, prob_double, prob_triple, prob_home_run)
            WHEN prob_out THEN 'out'::models.pa_outcome_category
            WHEN prob_walk THEN 'walk'::models.pa_outcome_category
            WHEN prob_single THEN 'single'::models.pa_outcome_category
            WHEN prob_double THEN 'double'::models.pa_outcome_category
            WHEN prob_triple THEN 'triple'::models.pa_outcome_category
            ELSE 'home_run'::models.pa_outcome_category
        END
    ) STORED,
    
    predicted_outcome_encoded INTEGER GENERATED ALWAYS AS (
        CASE GREATEST(prob_out, prob_walk, prob_single, prob_double, prob_triple, prob_home_run)
            WHEN prob_out THEN 0
            WHEN prob_walk THEN 1
            WHEN prob_single THEN 2
            WHEN prob_double THEN 3
            WHEN prob_triple THEN 4
            ELSE 5
        END
    ) STORED,
    
    -- Confidence and metadata
    confidence NUMERIC(4,3),  -- Probability of predicted class
    entropy NUMERIC(5,3),  -- Uncertainty measure (higher = more uncertain)
    
    -- Feature snapshot
    feature_snapshot JSONB,
    
    -- Actual outcome (filled after PA completes)
    actual_outcome models.pa_outcome_category,
    actual_outcome_encoded INTEGER,
    
    -- Evaluation
    is_correct BOOLEAN,
    log_loss NUMERIC(6,4),  -- Multi-class log loss
    
    -- Derived predictions
    prob_hit NUMERIC(4,3) GENERATED ALWAYS AS (
        prob_single + prob_double + prob_triple + prob_home_run
    ) STORED,
    prob_on_base NUMERIC(4,3) GENERATED ALWAYS AS (
        prob_walk + prob_single + prob_double + prob_triple + prob_home_run
    ) STORED,
    prob_xbh NUMERIC(4,3) GENERATED ALWAYS AS (
        prob_double + prob_triple + prob_home_run
    ) STORED,
    
    -- Expected value metrics
    expected_bases NUMERIC(3,2) GENERATED ALWAYS AS (
        prob_walk + prob_single + 2*prob_double + 3*prob_triple + 4*prob_home_run
    ) STORED,
    expected_runs NUMERIC(4,3),  -- Expected runs from this PA (context-dependent)
    
    -- Timestamps
    predicted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    outcome_recorded_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(model_version, game_pk, at_bat_index)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pa_pred_model ON models.pa_outcome_predictions(model_version);
CREATE INDEX IF NOT EXISTS idx_pa_pred_game ON models.pa_outcome_predictions(game_pk);
CREATE INDEX IF NOT EXISTS idx_pa_pred_batter ON models.pa_outcome_predictions(batter_id);
CREATE INDEX IF NOT EXISTS idx_pa_pred_pitcher ON models.pa_outcome_predictions(pitcher_id);
CREATE INDEX IF NOT EXISTS idx_pa_pred_outcome ON models.pa_outcome_predictions(predicted_outcome);
CREATE INDEX IF NOT EXISTS idx_pa_pred_correct ON models.pa_outcome_predictions(is_correct) WHERE is_correct IS NOT NULL;

-- Comments
COMMENT ON TABLE models.pa_outcome_predictions IS 'PA Outcome Model predictions with class probabilities';
COMMENT ON COLUMN models.pa_outcome_predictions.prob_hit IS 'Sum of single/double/triple/home_run probabilities';
COMMENT ON COLUMN models.pa_outcome_predictions.prob_on_base IS 'Probability of reaching base (walk or hit)';
COMMENT ON COLUMN models.pa_outcome_predictions.expected_bases IS 'Expected total bases from PA';

-- =============================================
-- FUNCTIONS
-- =============================================

-- Function: Populate PA training data
CREATE OR REPLACE FUNCTION models.populate_pa_outcome_training(
    p_season INTEGER,
    p_sample_rate NUMERIC DEFAULT 1.0
) RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER := 0;
BEGIN
    INSERT INTO models.pa_outcome_training_data (
        game_pk, season, at_bat_index,
        inning, is_top, outs,
        runner_1b, runner_2b, runner_3b,
        score_home, score_away, run_diff,
        leverage_index, is_high_leverage,
        batter_id, pitcher_id,
        batting_team_id, pitching_team_id,
        batter_hand, pitcher_hand, is_platoon_advantage,
        outcome,
        event_type, detailed_event,
        runs_scored, rbi,
        is_sacrifice, is_sac_fly
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
        COALESCE(li.li, 1.0),
        COALESCE(li.li, 1.0) >= 1.5,
        p.batter_id,
        p.pitcher_id,
        CASE WHEN p.is_top THEN p.away_team_id ELSE p.home_team_id END,
        CASE WHEN p.is_top THEN p.home_team_id ELSE p.away_team_id END,
        NULL,  -- batter_hand (from player table)
        NULL,  -- pitcher_hand (from player table)
        NULL,  -- is_platoon_advantage (compute from hands)
        -- Map event to outcome category
        CASE 
            WHEN p.event IN ('Walk', 'Intent Walk') THEN 'walk'::models.pa_outcome_category
            WHEN p.event IN ('Hit By Pitch') THEN 'walk'::models.pa_outcome_category
            WHEN p.event = 'Single' THEN 'single'::models.pa_outcome_category
            WHEN p.event = 'Double' THEN 'double'::models.pa_outcome_category
            WHEN p.event = 'Triple' THEN 'triple'::models.pa_outcome_category
            WHEN p.event = 'Home Run' THEN 'home_run'::models.pa_outcome_category
            WHEN p.event IN ('Field Error', 'Catcher Interference') THEN 'error'::models.pa_outcome_category
            ELSE 'out'::models.pa_outcome_category
        END,
        p.event,
        p.description,
        p.rbi,  -- runs scored from this play
        p.rbi,
        p.is_sacrifice_hit,
        p.is_sacrifice_fly
    FROM raw_gumbo.plays p
    LEFT JOIN features.game_state_li li ON li.game_pk = p.game_pk AND li.at_bat_index = p.at_bat_index
    WHERE p.season = p_season
      AND p.outcome_type IS NOT NULL  -- Completed PA
      AND (p_sample_rate >= 1.0 OR random() < p_sample_rate)
    ON CONFLICT (game_pk, at_bat_index) DO NOTHING;
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- Function: Compute PA features
CREATE OR REPLACE FUNCTION models.compute_pa_outcome_features(
    p_training_id INTEGER
) RETURNS VOID AS $$
DECLARE
    v_train models.pa_outcome_training_data%ROWTYPE;
    v_matchup features.matchup_features%ROWTYPE;
    v_form features.rolling_form_features%ROWTYPE;
BEGIN
    SELECT * INTO v_train
    FROM models.pa_outcome_training_data
    WHERE training_id = p_training_id;
    
    IF NOT FOUND THEN
        RETURN;
    END IF;
    
    -- Get matchup features
    SELECT * INTO v_matchup
    FROM features.matchup_features
    WHERE game_pk = v_train.game_pk AND at_bat_index = v_train.at_bat_index;
    
    -- Get form features
    SELECT * INTO v_form
    FROM features.rolling_form_features
    WHERE game_pk = v_train.game_pk 
      AND batter_id = v_train.batter_id
      AND pitcher_id = v_train.pitcher_id;
    
    -- Calculate historical rates (from same season or prior)
    INSERT INTO models.pa_outcome_features (
        training_id, game_pk, season,
        inning_normalized, is_top_half, outs, base_state, run_diff_normalized,
        leverage_index, is_high_leverage,
        matchup_score, is_platoon_advantage,
        batter_l14_ops, batter_is_hot,
        pitcher_l14_era, pitcher_is_hot,
        historical_out_rate, historical_walk_rate,
        historical_hit_rate, historical_hr_rate,
        feature_vector
    )
    SELECT 
        p_training_id,
        v_train.game_pk,
        v_train.season,
        LEAST(v_train.inning, 12) / 9.0,
        v_train.is_top,
        v_train.outs,
        v_train.base_state,
        GREATEST(-10, LEAST(10, v_train.run_diff)) / 10.0,
        v_train.leverage_index,
        v_train.is_high_leverage,
        COALESCE(v_matchup.matchup_score, 0.5),
        v_matchup.is_platoon_advantage,
        v_form.batter_l14_ops,
        v_form.batter_is_hot,
        v_form.pitcher_l14_era,
        v_form.pitcher_is_hot,
        -- Historical rates (placeholders - would compute from data)
        0.68,  -- out rate
        0.09,  -- walk rate
        0.23,  -- hit rate
        0.035, -- HR rate
        jsonb_build_object(
            'inning', v_train.inning,
            'outs', v_train.outs,
            'base_state', v_train.base_state,
            'matchup_score', v_matchup.matchup_score,
            'batter_l14_ops', v_form.batter_l14_ops,
            'pitcher_l14_era', v_form.pitcher_l14_era
        )
    ON CONFLICT (training_id) DO UPDATE SET
        matchup_score = EXCLUDED.matchup_score,
        batter_l14_ops = EXCLUDED.batter_l14_ops,
        pitcher_l14_era = EXCLUDED.pitcher_l14_era,
        feature_vector = EXCLUDED.feature_vector,
        computed_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Function: Record PA outcome and evaluate
CREATE OR REPLACE FUNCTION models.record_pa_outcome(
    p_prediction_id INTEGER,
    p_actual_outcome models.pa_outcome_category
) RETURNS VOID AS $$
DECLARE
    v_pred models.pa_outcome_predictions%ROWTYPE;
    v_actual_enc INTEGER;
    v_log_loss NUMERIC;
    v_prob_actual NUMERIC;
BEGIN
    SELECT * INTO v_pred
    FROM models.pa_outcome_predictions
    WHERE prediction_id = p_prediction_id;
    
    IF NOT FOUND THEN
        RETURN;
    END IF;
    
    -- Get probability of actual outcome
    v_actual_enc := CASE p_actual_outcome
        WHEN 'out' THEN 0
        WHEN 'walk' THEN 1
        WHEN 'single' THEN 2
        WHEN 'double' THEN 3
        WHEN 'triple' THEN 4
        WHEN 'home_run' THEN 5
        ELSE 6
    END;
    
    v_prob_actual := CASE v_actual_enc
        WHEN 0 THEN v_pred.prob_out
        WHEN 1 THEN v_pred.prob_walk
        WHEN 2 THEN v_pred.prob_single
        WHEN 3 THEN v_pred.prob_double
        WHEN 4 THEN v_pred.prob_triple
        WHEN 5 THEN v_pred.prob_home_run
        ELSE 0.001
    END;
    
    -- Log loss
    v_log_loss := -LN(GREATEST(0.0001, v_prob_actual));
    
    UPDATE models.pa_outcome_predictions
    SET actual_outcome = p_actual_outcome,
        actual_outcome_encoded = v_actual_enc,
        is_correct = (v_pred.predicted_outcome = p_actual_outcome),
        log_loss = v_log_loss,
        outcome_recorded_at = NOW()
    WHERE prediction_id = p_prediction_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- VIEWS
-- =============================================

-- View: Model accuracy by outcome type
CREATE OR REPLACE VIEW models.pa_outcome_accuracy AS
SELECT 
    model_version,
    predicted_outcome,
    COUNT(*) as n_predictions,
    SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)::NUMERIC / COUNT(*) as accuracy,
    AVG(log_loss) as mean_log_loss,
    AVG(confidence) as avg_confidence
FROM models.pa_outcome_predictions
WHERE actual_outcome IS NOT NULL
GROUP BY model_version, predicted_outcome;

-- View: Calibration by predicted class probability
CREATE OR REPLACE VIEW models.pa_outcome_calibration AS
WITH binned AS (
    SELECT 
        model_version,
        predicted_outcome,
        CASE 
            WHEN confidence < 0.2 THEN '0.0-0.2'
            WHEN confidence < 0.4 THEN '0.2-0.4'
            WHEN confidence < 0.6 THEN '0.4-0.6'
            WHEN confidence < 0.8 THEN '0.6-0.8'
            ELSE '0.8-1.0'
        END as confidence_bin,
        confidence as predicted_prob,
        CASE WHEN is_correct THEN 1 ELSE 0 END as is_correct_int
    FROM models.pa_outcome_predictions
    WHERE actual_outcome IS NOT NULL
)
SELECT 
    model_version,
    predicted_outcome,
    confidence_bin,
    COUNT(*) as n,
    AVG(predicted_prob) as avg_predicted,
    AVG(is_correct_int) as actual_rate,
    AVG(predicted_prob) - AVG(is_correct_int) as calibration_error
FROM binned
GROUP BY model_version, predicted_outcome, confidence_bin
ORDER BY model_version, predicted_outcome, confidence_bin;

-- View: Batter prediction summary
CREATE OR REPLACE VIEW models.batter_prediction_summary AS
SELECT 
    model_version,
    batter_id,
    COUNT(*) as total_pa,
    AVG(prob_hit) as avg_predicted_hit_prob,
    AVG(CASE WHEN actual_outcome IN ('single', 'double', 'triple', 'home_run') THEN 1 ELSE 0 END) as actual_hit_rate,
    AVG(prob_home_run) as avg_predicted_hr_prob,
    AVG(CASE WHEN actual_outcome = 'home_run' THEN 1 ELSE 0 END) as actual_hr_rate,
    AVG(CASE WHEN is_correct THEN 1 ELSE 0 END) as model_accuracy
FROM models.pa_outcome_predictions
WHERE actual_outcome IS NOT NULL
GROUP BY model_version, batter_id;

-- View: Pitcher prediction summary
CREATE OR REPLACE VIEW models.pitcher_prediction_summary AS
SELECT 
    model_version,
    pitcher_id,
    COUNT(*) as total_bf,
    AVG(prob_out) as avg_predicted_out_prob,
    AVG(CASE WHEN actual_outcome = 'out' THEN 1 ELSE 0 END) as actual_out_rate,
    AVG(prob_on_base) as avg_predicted_obp,
    AVG(CASE WHEN actual_outcome IN ('walk', 'single', 'double', 'triple', 'home_run') THEN 1 ELSE 0 END) as actual_obp,
    AVG(CASE WHEN is_correct THEN 1 ELSE 0 END) as model_accuracy
FROM models.pa_outcome_predictions
WHERE actual_outcome IS NOT NULL
GROUP BY model_version, pitcher_id;

-- View: High confidence predictions (for monitoring)
CREATE OR REPLACE VIEW models.high_confidence_pa AS
SELECT 
    model_version,
    game_pk,
    at_bat_index,
    batter_id,
    pitcher_id,
    predicted_outcome,
    confidence,
    prob_hit,
    prob_home_run,
    expected_bases,
    CASE 
        WHEN confidence > 0.7 AND predicted_outcome = 'home_run' THEN 'Very confident HR'
        WHEN confidence > 0.7 AND predicted_outcome = 'out' THEN 'Very confident out'
        WHEN prob_hit > 0.5 THEN 'Likely hit'
        WHEN prob_home_run > 0.2 THEN 'HR threat'
        ELSE 'Uncertain'
    END as narrative
FROM models.pa_outcome_predictions
WHERE confidence > 0.6 OR prob_home_run > 0.15
ORDER BY confidence DESC;

COMMENT ON VIEW models.pa_outcome_accuracy IS 'Model accuracy by predicted outcome type';
COMMENT ON VIEW models.pa_outcome_calibration IS 'Calibration analysis by confidence bin';
COMMENT ON VIEW models.batter_prediction_summary IS 'Prediction summary per batter';
COMMENT ON VIEW models.pitcher_prediction_summary IS 'Prediction summary per pitcher';
COMMENT ON VIEW models.high_confidence_pa IS 'High confidence predictions for monitoring';
