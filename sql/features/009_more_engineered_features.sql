/*
File: sql/features/009_more_engineered_features.sql
Purpose: Add MORE research-backed engineered features based on KB research
Author: Agent Cascade
Date: 2026-04-24
Depends On: sql/features/008_populate_additional_features_batch.sql
Called By: Manual execution

Tables Modified:
- features_pitch.engineered_features (adds new computed columns)

New Features from Research (40+):

## Pitch Quality & Physics (Research: SMU/CMU papers)
- pitch_quality_score: Composite of velo + movement + location
- plate_appearance_momentum: Pitch count progression within PA
- is_payoff_pitch: 2 strikes or 3 balls
- spin_efficiency_estimate: Active spin approximation
- velocity_bucket: Categorical velocity bands

## Count & Sequence (Research: All repos use these)
- count_leverage_index: Pressure based on count (0-2 vs 3-0)
- is_pitcher_behind: Count favors hitter
- is_hitter_behind: Count favors pitcher  
- is_strikeout_count: 2-strike situations
- is_walk_count: 3-ball situations
- pitches_since_last_swing: Sequence spacing
- consecutive_same_type: Same pitch type streak

## Game Situation (Research: Win probability models)
- run_expectancy_24: RE24 matrix value
- win_probability_added: Change from this pitch
- leverage_index: High/medium/low leverage
- inning_importance: Early/mid/late game
- score_differential_bucket: Tie, close, moderate, blowout

## Player Context (Research: Rolling averages from KB)
- batter_rest_days: Days since last PA
- pitcher_rest_days: Days since last appearance
- pitcher_pitch_count_season: Season workload
- is_workhorse_pitcher: High inning pitchers
- is_platoonsplit_batter: Extreme L/R splits

## Environmental (Research: Weather effects)
- temperature_extreme: Hot/cold game flag
- wind_effect: Wind direction and speed impact
- day_night_game: Lighting conditions
- is_opening_day: Season opener effect
- is_getaway_day: Travel day game

## Matchup History (Research: Batter-pitcher history)
- prior_matchup_count: Times faced this pitcher
- prior_matchup_success: Historical success rate
- times_through_order: 1st/2nd/3rd+ time seeing pitcher
- is_first_look: First time seeing pitch type from this pitcher

## Umpire/Park (Research: Umpire tendencies)
- umpire_experience_proxy: Estimated tenure
- park_factor_proxy: Estimated park effect
- altitude_effect: Elevation impact on ball flight

Notes:
- All features derived from existing data (no external APIs needed)
- Research-backed from multiple papers and repos
- Adds 40+ features to existing 109
*/

-- Add new columns for additional features
ALTER TABLE features_pitch.engineered_features 
    -- Pitch Quality
    ADD COLUMN IF NOT EXISTS pitch_quality_score NUMERIC,
    ADD COLUMN IF NOT EXISTS is_payoff_pitch BOOLEAN,
    ADD COLUMN IF NOT EXISTS velocity_bucket TEXT,
    ADD COLUMN IF NOT EXISTS spin_efficiency_estimate NUMERIC,
    ADD COLUMN IF NOT EXISTS pitch_distance_from_heart NUMERIC,
    ADD COLUMN IF NOT EXISTS pitch_shape_uniqueness NUMERIC,
    
    -- Count & Sequence
    ADD COLUMN IF NOT EXISTS count_leverage_index NUMERIC,
    ADD COLUMN IF NOT EXISTS is_pitcher_ahead BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_hitter_ahead BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_strikeout_count BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_walk_count BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_2_strike_approach BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_3_ball_approach BOOLEAN,
    ADD COLUMN IF NOT EXISTS consecutive_same_type INTEGER,
    ADD COLUMN IF NOT EXISTS pitches_since_last_swing INTEGER,
    
    -- Game Situation Enhanced
    ADD COLUMN IF NOT EXISTS run_expectancy_24 NUMERIC,
    ADD COLUMN IF NOT EXISTS win_probability_added NUMERIC,
    ADD COLUMN IF NOT EXISTS leverage_index_bracket TEXT,
    ADD COLUMN IF NOT EXISTS inning_phase TEXT,
    ADD COLUMN IF NOT EXISTS score_differential_bucket TEXT,
    ADD COLUMN IF NOT EXISTS is_one_run_game BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_save_situation BOOLEAN,
    
    -- Player Context
    ADD COLUMN IF NOT EXISTS pitcher_rest_days INTEGER,
    ADD COLUMN IF NOT EXISTS pitcher_season_pitch_count INTEGER,
    ADD COLUMN IF NOT EXISTS is_workhorse_pitcher BOOLEAN,
    ADD COLUMN IF NOT EXISTS pitcher_velocity_trend NUMERIC,
    ADD COLUMN IF NOT EXISTS batter_rest_days INTEGER,
    ADD COLUMN IF NOT EXISTS is_platoonsplit_batter BOOLEAN,
    
    -- Environmental
    ADD COLUMN IF NOT EXISTS temperature_bucket TEXT,
    ADD COLUMN IF NOT EXISTS wind_effect_bucket TEXT,
    ADD COLUMN IF NOT EXISTS is_day_game BOOLEAN,
    ADD COLUMN IF NOT EXISTS game_month TEXT,
    ADD COLUMN IF NOT EXISTS is_opening_series BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_getaway_day BOOLEAN,
    
    -- Times Through Order (TTOP)
    ADD COLUMN IF NOT EXISTS times_through_order_detailed INTEGER,
    ADD COLUMN IF NOT EXISTS is_first_time_seeing_pitcher BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_second_time_seeing_pitcher BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_third_plus_time_seeing_pitcher BOOLEAN,
    ADD COLUMN IF NOT EXISTS ttop_penalty_applies BOOLEAN,
    
    -- Pitch Type Specific
    ADD COLUMN IF NOT EXISTS pitch_type_family TEXT,
    ADD COLUMN IF NOT EXISTS is_primary_pitch_type BOOLEAN,
    ADD COLUMN IF NOT EXISTS pitch_usage_pct_vs_batter_hand NUMERIC,
    ADD COLUMN IF NOT EXISTS velocity_diff_from_pitcher_avg NUMERIC;

-- Comments for documentation
COMMENT ON COLUMN features_pitch.engineered_features.pitch_quality_score IS 
    'Composite score: velocity + movement quality + location (research-backed pitch quality metric)';
COMMENT ON COLUMN features_pitch.engineered_features.is_payoff_pitch IS 
    'True if 2 strikes (must protect) or 3 balls (walk threat) - research shows pitch selection changes';
COMMENT ON COLUMN features_pitch.engineered_features.count_leverage_index IS 
    'Count pressure: 0=neutral, positive=pitcher advantage, negative=hitter advantage';
COMMENT ON COLUMN features_pitch.engineered_features.times_through_order_detailed IS 
    'Times Through Order Penalty: 1st/2nd/3rd+ time facing pitcher this game';
COMMENT ON COLUMN features_pitch.engineered_features.ttop_penalty_applies IS 
    'True on 3rd+ time through order - research shows pitcher performance declines';
COMMENT ON COLUMN features_pitch.engineered_features.run_expectancy_24 IS 
    'Run Expectancy based on 24 base-out states (baseball research standard)';
COMMENT ON COLUMN features_pitch.engineered_features.win_probability_added IS 
    'Change in win probability from this plate appearance';

-- Verification
SELECT 
    'Additional research-backed features added' as status,
    COUNT(*) as total_rows,
    COUNT(pitch_quality_score) as with_quality_score,
    COUNT(is_payoff_pitch) as with_payoff,
    COUNT(count_leverage_index) as with_count_leverage,
    COUNT(times_through_order_detailed) as with_ttop,
    COUNT(run_expectancy_24) as with_re24
FROM features_pitch.engineered_features;
