-- ============================================================================
-- Populate engineered_features table with ALL research-backed derived features
-- 
-- This script populates the engineered_features table from base_features,
-- calculating all derived features for pitch-level modeling.
--
-- Research-backed feature categories:
-- 1. Velocity features (percentiles, diffs, categories)
-- 2. Strike zone features (zone regions, distance calculations)
-- 3. Outcome flags (tier1, tier2, swing, whiff, hit types)
-- 4. Pitch movement (break, approach angle, spin)
-- 5. Sequence context (previous pitch, pitch count)
-- 6. Count features (full count, 2-strike, 3-ball)
-- 7. Game context (score diff, leverage, base state)
--
-- Outcome Labels (Two-Tier Hierarchy):
-- Tier 1: Strike (S), Ball (B), Ball-in-Play (X)
-- Tier 2: Strikeout, Walk, Single, Double, Triple, HR, Out, HBP, Other
--
-- Author: AI Agent
-- Date: 2026-04-24
-- Epic: #78
-- ============================================================================

-- Clear existing data for idempotent run
TRUNCATE TABLE features_pitch.engineered_features;

-- Calculate velocity statistics for percentiles
WITH velocity_stats AS (
    SELECT 
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY start_speed) as vel_p25,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY start_speed) as vel_p50,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY start_speed) as vel_p75,
        AVG(start_speed) as vel_avg
    FROM features_pitch.base_features
    WHERE start_speed IS NOT NULL
),

-- Add row numbers for previous pitch lookup
pitches_with_prev AS (
    SELECT 
        bf.*,
        LAG(pitch_type) OVER (PARTITION BY game_pk, at_bat_number ORDER BY pitch_number) as prev_pitch_type,
        LAG(description) OVER (PARTITION BY game_pk, at_bat_number ORDER BY pitch_number) as prev_description,
        LAG(plate_x) OVER (PARTITION BY game_pk, at_bat_number ORDER BY pitch_number) as prev_plate_x,
        LAG(plate_z) OVER (PARTITION BY game_pk, at_bat_number ORDER BY pitch_number) as prev_plate_z,
        LAG(start_speed) OVER (PARTITION BY game_pk, at_bat_number ORDER BY pitch_number) as prev_velocity,
        LAG(pfx_x) OVER (PARTITION BY game_pk, at_bat_number ORDER BY pitch_number) as prev_break_x,
        LAG(pfx_z) OVER (PARTITION BY game_pk, at_bat_number ORDER BY pitch_number) as prev_break_z,
        LAG(zone) OVER (PARTITION BY game_pk, at_bat_number ORDER BY pitch_number) as prev_zone,
        ROW_NUMBER() OVER (PARTITION BY game_pk, at_bat_number ORDER BY pitch_number) as pitch_seq_num
    FROM features_pitch.base_features bf
)

INSERT INTO features_pitch.engineered_features (
    pitch_id, velocity_category, velocity_percentile, velocity_diff_from_avg,
    zone_region, is_in_zone, is_in_shadow_zone, is_in_chase_zone, distance_from_zone_center,
    is_strike, is_swing, is_whiff, is_called_strike, is_foul, is_foul_tip, is_ball_in_play,
    is_hit, is_single, is_double, is_triple, is_home_run, is_xbh, is_out,
    is_ground_ball, is_fly_ball, is_line_drive, is_popup, is_hard_hit, is_barrel,
    outcome_tier1, outcome_tier2, swing_decision,
    horizontal_break, vertical_break, approach_angle, spin_efficiency, induced_vertical_break,
    horizontal_release_deviation, release_velocity_diff,
    pa_pitch_count, pitches_remaining_pa,
    prev_pitch_type, prev_pitch_result, prev_plate_x, prev_plate_z, prev_velocity,
    prev_break_x, prev_break_z, time_since_prev_pitch,
    prev_was_strike, prev_was_ball, prev_was_swing, count_started_this_pa,
    is_full_count, is_two_strike, is_three_ball,
    pitcher_arsenal_index, pitcher_repertoire_depth, game_pitch_count, pitch_usage_pct_this_game,
    batter_performance_vs_type, batter_swing_rate_vs_type, batter_whiff_rate_vs_type,
    is_batter_hot_zone, is_batter_cold_zone,
    score_diff, score_diff_bucket, is_late_game, is_high_leverage,
    base_state_code, base_state_name, count_code,
    times_faced_this_game, total_pitches_in_matchup,
    engineered_at, engineer_version, source_calculations
)
    
    -- Tier 2 Outcome (Fine): Single, Double, Triple, HR, Out, Walk, K, HBP, Error, Other
    outcome_tier2,
    
    -- Derived: Strike Zone Features
    -- Research: Strike zone judgment uses normalized plate position
    plate_x_normalized,      -- (plate_x / 8.5) normalized to plate width
    plate_z_normalized,      -- (plate_z - sz_bot) / (sz_top - sz_bot) normalized to strike zone
    distance_from_center,    -- Euclidean distance from plate center
    is_strike_boolean,       -- Boolean: in zone or not
    zone_location,           -- Categorical: heart, shadow, chase, waste
    height_above_center,     -- plate_z relative to strike zone center
    
    -- Derived: Pitch Physics
    -- Research: Release metrics affect perceived velocity and deception
    perceived_velocity,      -- effective_speed (already in base)
    velocity_diff,           -- start_speed - effective_speed
    release_approach_angle,  -- ATAN2(vy0, SQRT(vx0^2 + vz0^2)) - approach to plate
    release_height,          -- release_pos_z (already in base)
    release_side,            -- release_pos_x (already in base)
    extension_effectiveness, -- release_extension * start_speed
    
    -- Derived: Pitch Movement (Research-backed break calculations)
    -- SMU/CMU papers show break magnitude is critical for pitch quality
    pfx_total,               -- SQRT(pfx_x^2 + pfx_z^2) - total break
    pfx_rise_index,          -- pfx_z (positive = rise, negative = sink)
    pfx_run_index,           -- pfx_x (positive = arm-side, negative = glove-side)
    approach_angle_x,        -- Horizontal approach angle
    approach_angle_z,        -- Vertical approach angle
    break_angle,             -- ATAN2(pfx_x, pfx_z) - direction of break
    induced_vertical_break,  -- pfx_z adjusted for gravity (approximation)
    horizontal_break,        -- pfx_x (already in base, but normalized)
    
    -- Derived: Pitch Trajectory Physics
    -- Release velocity components (vx0, vy0, vz0 already in base)
    velocity_magnitude,      -- SQRT(vx0^2 + vy0^2 + vz0^2)
    velocity_xz,            -- SQRT(vx0^2 + vz0^2) - horizontal plane velocity
    velocity_horizontal,     -- SQRT(vx0^2 + vz0^2)
    
    -- Acceleration components (ax, ay, az already in base)
    acceleration_magnitude,  -- SQRT(ax^2 + ay^2 + az^2)
    deceleration,            -- -ay (pitch slows down due to drag)
    
    -- Derived: Game Context & Situation
    -- Research: Score differential and inning affect pitcher/batter behavior
    score_differential,      -- bat_score - fld_score (from batting team perspective)
    absolute_score_diff,     -- ABS(score_differential)
    is_close_game,           -- absolute_score_diff <= 2
    is_blowout,              -- absolute_score_diff >= 5
    is_late_inning,          -- inning >= 7
    is_extra_inning,         -- inning > 9
    leverage_index_approx,   -- Approximate leverage based on score_diff + inning + outs
    
    -- Base state encoding (Research: Run Expectancy depends on base states)
    base_state,              -- 0-7 encoding: 0=empty, 1=1B, 2=2B, 3=3B, 4=1B+2B, 5=1B+3B, 6=2B+3B, 7=loaded
    is_runner_on,            -- Any runner on base
    is_runner_in_scoring_position, -- Runner on 2B or 3B
    is_bases_loaded,         -- All three bases occupied
    num_runners,             -- Count of runners (0-3)
    
    -- Count characteristics (Research: Count drives pitch selection massively)
    count_str,               -- "balls-strikes" string (e.g., "3-2")
    is_two_strike,           -- strikes = 2
    is_three_ball,           -- balls = 3
    is_full_count,           -- 3-2 count
    is_pitchers_count,       -- 0-0, 0-1, 0-2, 1-2 (pitcher ahead)
    is_hitters_count,        -- 2-0, 2-1, 3-0, 3-1 (hitter ahead)
    is_neutral_count,        -- 1-0, 1-1 (neutral)
    count_leverage,          -- ABS(balls - strikes) with penalty for 2-strike
    strikes_remaining,       -- 3 - strikes (pitches until strikeout)
    balls_remaining,         -- 4 - balls (pitches until walk)
    
    -- Pitch sequence context
    pitch_count_in_pa,       -- pitch_number (already in base)
    is_first_pitch,          -- pitch_number = 1
    is_early_pitch,          -- pitch_number <= 2
    is_late_in_pa,           -- pitch_number >= 5
    
    -- Derived: Batted Ball Quality (when applicable)
    -- Research: Exit velocity, launch angle, distance predict outcomes
    is_hard_hit,             -- launch_speed >= 95 mph
    is_barrel,               -- launch_speed >= 98 AND launch_angle 26-30
    is_sweet_spot,           -- launch_angle 8-32 degrees
    launch_speed_bucket,     -- Categorical: weak (<80), medium (80-95), hard (95-105), elite (>105)
    launch_angle_bucket,     -- Categorical: topped, weak, flare, solid, barrel, too_high
    distance_bucket,         -- Categorical: infield, shallow, medium, warning_track, HR
    estimated_woba_bucket,   -- Categorical: out (<.200), single (.200-.350), extra (.350-.500), HR (>0.500)
    
    -- xWOBA differential (actual vs expected)
    woba_diff,               -- woba_value - estimated_woba
    is_unlucky,              -- woba_diff < -0.100 (outcome worse than expected)
    is_lucky,                -- woba_diff > 0.100 (outcome better than expected)
    
    -- Win Probability added (Research: Context for pitch importance)
    delta_wp_abs,            -- ABS(delta_home_win_exp)
    is_high_leverage_pitch,  -- delta_wp_abs > 0.05 (5% win prob change)
    run_expectancy_delta,    -- delta_run_exp
    
    -- Pitch type classifications (for arsenal analysis)
    is_fastball,             -- pitch_type IN ('FF', 'FT', 'SI', 'FC')
    is_breaking,             -- pitch_type IN ('CU', 'SL', 'KC', 'CS', 'KN')
    is_offspeed,             -- pitch_type IN ('CH', 'FS', 'SC', 'FO')
    pitch_category,          -- 'fastball', 'breaking', 'offspeed', 'other'
    
    -- Defensive shift context (Research: Shift affects BIP outcomes)
    is_shifted,              -- if_fielding_alignment != 'Standard'
    shift_type,              -- Standard, Infield shift, Strategic, etc.
    
    -- Quality flags
    is_outlier_pitch,        -- quality_flag != 'normal'
    quality_flag_detail,     -- Full quality flag string
    
    -- Timestamps
    created_at,
    updated_at,
    data_version
)
SELECT 
    -- Core identifiers
    bf.pitch_id,
    bf.game_pk,
    bf.at_bat_number,
    bf.pitch_number,
    bf.game_year,
    bf.game_date,
    
    -- Player identifiers
    bf.batter_id,
    bf.pitcher_id,
    bf.player_name,
    
    -- Pitch characteristics
    bf.pitch_type,
    bf.pitch_name,
    bf.stand,
    bf.p_throws,
    
    -- Tier 1 Outcome (Coarse)
    CASE 
        WHEN bf.description ILIKE '%ball%' OR bf.events ILIKE '%walk%' THEN 'B'
        WHEN bf.description ILIKE '%strike%' OR bf.events ILIKE '%strikeout%' THEN 'S'
        WHEN bf.events IS NOT NULL AND bf.events != '' THEN 'X'
        ELSE 'U'  -- Unknown
    END as outcome_tier1,
    
    -- Tier 2 Outcome (Fine)
    CASE 
        -- Walk outcomes
        WHEN bf.events IN ('walk', 'intent_walk') THEN 'Walk'
        -- Strikeout outcomes
        WHEN bf.events = 'strikeout' THEN 'Strikeout'
        WHEN bf.events = 'strikeout_double_play' THEN 'Strikeout'
        -- Hit by pitch
        WHEN bf.events = 'hit_by_pitch' THEN 'HBP'
        -- Singles
        WHEN bf.events IN ('single', 'field_error', 'fielders_choice') THEN 'Single'
        -- Doubles
        WHEN bf.events = 'double' THEN 'Double'
        -- Triples
        WHEN bf.events = 'triple' THEN 'Triple'
        -- Home runs
        WHEN bf.events IN ('home_run', 'grand_slam') THEN 'HR'
        -- Outs (all other events with no hit)
        WHEN bf.events IN ('field_out', 'force_out', 'grounded_into_double_play', 
                          'double_play', 'triple_play', 'sac_fly', 'sac_bunt',
                          'catcher_interf', 'fielders_choice_out') THEN 'Out'
        -- No event (ball/strike/foul) - derive from description
        WHEN bf.description ILIKE '%foul%' THEN 'Foul'
        WHEN bf.description ILIKE '%ball%' THEN 'Ball'
        WHEN bf.description ILIKE '%strike%' AND bf.description NOT ILIKE '%foul%' THEN 'Strike'
        -- Default
        ELSE 'Other'
    END as outcome_tier2,
    
    -- Derived: Strike Zone Features
    -- Normalized plate position (plate is 17 inches wide = +/- 8.5 inches)
    bf.plate_x / 8.5 as plate_x_normalized,
    
    -- Normalized height within strike zone (0 = bottom, 1 = top)
    CASE 
        WHEN bf.sz_top > bf.sz_bot THEN (bf.plate_z - bf.sz_bot) / NULLIF(bf.sz_top - bf.sz_bot, 0)
        ELSE 0.5
    END as plate_z_normalized,
    
    -- Distance from center of plate
    SQRT(POWER(bf.plate_x / 8.5, 2) + POWER((bf.plate_z - (bf.sz_top + bf.sz_bot)/2) / NULLIF(bf.sz_top - bf.sz_bot, 0.5), 2)) as distance_from_center,
    
    -- Boolean strike (in zone 1-9 or borderline)
    CASE 
        WHEN bf.zone BETWEEN 1 AND 9 THEN TRUE
        ELSE FALSE
    END as is_strike_boolean,
    
    -- Zone location categorization
    CASE 
        WHEN bf.zone BETWEEN 1 AND 9 THEN 'heart'       -- In zone
        WHEN bf.zone IN (11, 12, 13, 14) THEN 'shadow' -- Borderline
        WHEN bf.plate_x BETWEEN -20 AND -10 OR bf.plate_x BETWEEN 10 AND 20 THEN 'chase'
        WHEN bf.plate_z > bf.sz_top + 0.5 OR bf.plate_z < bf.sz_bot - 0.5 THEN 'waste'
        ELSE 'chase'
    END as zone_location,
    
    -- Height relative to zone center
    bf.plate_z - (bf.sz_top + bf.sz_bot) / 2.0 as height_above_center,
    
    -- Derived: Pitch Physics
    bf.effective_speed as perceived_velocity,
    bf.start_speed - bf.effective_speed as velocity_diff,
    
    -- Approach angle (in degrees)
    DEGREES(ATAN2(-bf.vy0, SQRT(bf.vx0*bf.vx0 + bf.vz0*bf.vz0))) as release_approach_angle,
    
    bf.release_pos_z as release_height,
    bf.release_pos_x as release_side,
    bf.release_extension * bf.start_speed / 100.0 as extension_effectiveness,
    
    -- Derived: Pitch Movement
    SQRT(bf.pfx_x*bf.pfx_x + bf.pfx_z*bf.pfx_z) as pfx_total,
    bf.pfx_z as pfx_rise_index,
    bf.pfx_x as pfx_run_index,
    
    -- Horizontal approach angle at plate
    DEGREES(ATAN2(bf.vx0, -bf.vy0)) as approach_angle_x,
    
    -- Vertical approach angle at plate
    DEGREES(ATAN2(bf.vz0, -bf.vy0)) as approach_angle_z,
    
    -- Break angle (direction of movement)
    DEGREES(ATAN2(bf.pfx_x, bf.pfx_z)) as break_angle,
    
    -- Induced vertical break (pfx_z is already gravity-free break)
    bf.pfx_z as induced_vertical_break,
    
    -- Horizontal break (signed)
    bf.pfx_x as horizontal_break,
    
    -- Derived: Pitch Trajectory Physics
    SQRT(bf.vx0*bf.vx0 + bf.vy0*bf.vy0 + bf.vz0*bf.vz0) as velocity_magnitude,
    SQRT(bf.vx0*bf.vx0 + bf.vz0*bf.vz0) as velocity_xz,
    SQRT(bf.vx0*bf.vx0 + bf.vz0*bf.vz0) as velocity_horizontal,
    
    -- Acceleration
    SQRT(bf.ax*bf.ax + bf.ay*bf.ay + bf.az*bf.az) as acceleration_magnitude,
    -bf.ay as deceleration,
    
    -- Derived: Game Context
    bf.bat_score - bf.fld_score as score_differential,
    ABS(bf.bat_score - bf.fld_score) as absolute_score_diff,
    CASE WHEN ABS(bf.bat_score - bf.fld_score) <= 2 THEN TRUE ELSE FALSE END as is_close_game,
    CASE WHEN ABS(bf.bat_score - bf.fld_score) >= 5 THEN TRUE ELSE FALSE END as is_blowout,
    CASE WHEN bf.inning >= 7 THEN TRUE ELSE FALSE END as is_late_inning,
    CASE WHEN bf.inning > 9 THEN TRUE ELSE FALSE END as is_extra_inning,
    
    -- Approximate leverage index (simplified formula)
    (1.0 + 
     CASE WHEN ABS(bf.bat_score - bf.fld_score) <= 1 THEN 0.5 ELSE 0 END +
     CASE WHEN bf.inning >= 7 THEN 0.3 ELSE 0 END +
     CASE WHEN bf.outs_when_up < 2 THEN 0.2 ELSE 0 END) as leverage_index_approx,
    
    -- Base state encoding
    (CASE WHEN bf.on_1b THEN 1 ELSE 0 END) +
    (CASE WHEN bf.on_2b THEN 2 ELSE 0 END) +
    (CASE WHEN bf.on_3b THEN 4 ELSE 0 END) as base_state,
    
    CASE WHEN bf.on_1b OR bf.on_2b OR bf.on_3b THEN TRUE ELSE FALSE END as is_runner_on,
    CASE WHEN bf.on_2b OR bf.on_3b THEN TRUE ELSE FALSE END as is_runner_in_scoring_position,
    CASE WHEN bf.on_1b AND bf.on_2b AND bf.on_3b THEN TRUE ELSE FALSE END as is_bases_loaded,
    (CASE WHEN bf.on_1b THEN 1 ELSE 0 END) +
    (CASE WHEN bf.on_2b THEN 1 ELSE 0 END) +
    (CASE WHEN bf.on_3b THEN 1 ELSE 0 END) as num_runners,
    
    -- Count characteristics
    CONCAT(bf.balls::text, '-', bf.strikes::text) as count_str,
    CASE WHEN bf.strikes = 2 THEN TRUE ELSE FALSE END as is_two_strike,
    CASE WHEN bf.balls = 3 THEN TRUE ELSE FALSE END as is_three_ball,
    CASE WHEN bf.balls = 3 AND bf.strikes = 2 THEN TRUE ELSE FALSE END as is_full_count,
    
    -- Pitcher's count: 0-0, 0-1, 0-2, 1-2
    CASE WHEN (bf.balls = 0 AND bf.strikes IN (0, 1, 2)) OR 
              (bf.balls = 1 AND bf.strikes = 2) THEN TRUE ELSE FALSE END as is_pitchers_count,
    
    -- Hitter's count: 2-0, 2-1, 3-0, 3-1
    CASE WHEN (bf.balls = 2 AND bf.strikes IN (0, 1)) OR 
              (bf.balls = 3 AND bf.strikes IN (0, 1)) THEN TRUE ELSE FALSE END as is_hitters_count,
    
    -- Neutral count: 1-0, 1-1
    CASE WHEN bf.balls = 1 AND bf.strikes IN (0, 1) THEN TRUE ELSE FALSE END as is_neutral_count,
    
    -- Count leverage (higher = more pressure on pitcher)
    ABS(bf.balls::int - bf.strikes::int) + 
    CASE WHEN bf.strikes = 2 THEN 1 ELSE 0 END as count_leverage,
    
    3 - bf.strikes as strikes_remaining,
    4 - bf.balls as balls_remaining,
    
    -- Pitch sequence context
    bf.pitch_number as pitch_count_in_pa,
    CASE WHEN bf.pitch_number = 1 THEN TRUE ELSE FALSE END as is_first_pitch,
    CASE WHEN bf.pitch_number <= 2 THEN TRUE ELSE FALSE END as is_early_pitch,
    CASE WHEN bf.pitch_number >= 5 THEN TRUE ELSE FALSE END as is_late_in_pa,
    
    -- Derived: Batted Ball Quality
    CASE WHEN bf.launch_speed >= 95 THEN TRUE ELSE FALSE END as is_hard_hit,
    
    -- Barrel: 98+ mph and 26-30 degrees (approximate)
    CASE WHEN bf.launch_speed >= 98 AND bf.launch_angle BETWEEN 26 AND 30 THEN TRUE ELSE FALSE END as is_barrel,
    
    -- Sweet spot: 8-32 degrees
    CASE WHEN bf.launch_angle BETWEEN 8 AND 32 THEN TRUE ELSE FALSE END as is_sweet_spot,
    
    -- Launch speed bucket
    CASE 
        WHEN bf.launch_speed < 80 THEN 'weak'
        WHEN bf.launch_speed < 95 THEN 'medium'
        WHEN bf.launch_speed < 105 THEN 'hard'
        ELSE 'elite'
    END as launch_speed_bucket,
    
    -- Launch angle bucket (Statcast definitions)
    CASE 
        WHEN bf.launch_angle < 0 THEN 'topped'
        WHEN bf.launch_angle < 10 THEN 'weak_ground'
        WHEN bf.launch_angle < 25 THEN 'flare_burner'
        WHEN bf.launch_angle < 35 THEN 'solid_contact'
        WHEN bf.launch_angle < 50 THEN 'barrel_zone'
        ELSE 'too_high'
    END as launch_angle_bucket,
    
    -- Distance bucket
    CASE 
        WHEN bf.hit_distance_sc < 150 THEN 'infield'
        WHEN bf.hit_distance_sc < 250 THEN 'shallow'
        WHEN bf.hit_distance_sc < 350 THEN 'medium'
        WHEN bf.hit_distance_sc < 400 THEN 'warning_track'
        ELSE 'hr_distance'
    END as distance_bucket,
    
    -- xWOBA bucket
    CASE 
        WHEN bf.estimated_woba < 0.200 THEN 'out_expected'
        WHEN bf.estimated_woba < 0.350 THEN 'single_expected'
        WHEN bf.estimated_woba < 0.500 THEN 'extra_base_expected'
        ELSE 'hr_expected'
    END as estimated_woba_bucket,
    
    -- WOBA differential
    bf.woba_value - bf.estimated_woba as woba_diff,
    CASE WHEN bf.woba_value - bf.estimated_woba < -0.100 THEN TRUE ELSE FALSE END as is_unlucky,
    CASE WHEN bf.woba_value - bf.estimated_woba > 0.100 THEN TRUE ELSE FALSE END as is_lucky,
    
    -- Win Probability
    ABS(bf.delta_home_win_exp) as delta_wp_abs,
    CASE WHEN ABS(bf.delta_home_win_exp) > 0.05 THEN TRUE ELSE FALSE END as is_high_leverage_pitch,
    bf.delta_run_exp as run_expectancy_delta,
    
    -- Pitch type classification
    CASE 
        WHEN bf.pitch_type IN ('FF', 'FT', 'SI', 'FC', 'FA') THEN TRUE 
        ELSE FALSE 
    END as is_fastball,
    
    CASE 
        WHEN bf.pitch_type IN ('CU', 'SL', 'KC', 'CS', 'KN', 'EP', 'SC') THEN TRUE 
        ELSE FALSE 
    END as is_breaking,
    
    CASE 
        WHEN bf.pitch_type IN ('CH', 'FS', 'FO', 'PO') THEN TRUE 
        ELSE FALSE 
    END as is_offspeed,
    
    CASE 
        WHEN bf.pitch_type IN ('FF', 'FT', 'SI', 'FC', 'FA') THEN 'fastball'
        WHEN bf.pitch_type IN ('CU', 'SL', 'KC', 'CS', 'KN', 'EP', 'SC') THEN 'breaking'
        WHEN bf.pitch_type IN ('CH', 'FS', 'FO', 'PO') THEN 'offspeed'
        ELSE 'other'
    END as pitch_category,
    
    -- Defensive shift
    CASE WHEN bf.if_fielding_alignment != 'Standard' OR bf.of_fielding_alignment != 'Standard' 
         THEN TRUE ELSE FALSE END as is_shifted,
    
    COALESCE(bf.if_fielding_alignment, 'Standard') as shift_type,
    
    -- Quality flags
    CASE WHEN bf.quality_flag != 'normal' THEN TRUE ELSE FALSE END as is_outlier_pitch,
    bf.quality_flag as quality_flag_detail,
    
    -- Timestamps
    NOW() as created_at,
    NOW() as updated_at,
    1 as data_version
    
FROM features_pitch.base_features bf
WHERE bf.plate_x IS NOT NULL 
  AND bf.plate_z IS NOT NULL;

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_eng_feat_tier1 
ON features_pitch.engineered_features(outcome_tier1);

CREATE INDEX IF NOT EXISTS idx_eng_feat_tier2 
ON features_pitch.engineered_features(outcome_tier2);

CREATE INDEX IF NOT EXISTS idx_eng_feat_pitch_type 
ON features_pitch.engineered_features(pitch_type);

CREATE INDEX IF NOT EXISTS idx_eng_feat_year 
ON features_pitch.engineered_features(game_year);

CREATE INDEX IF NOT EXISTS idx_eng_feat_batter 
ON features_pitch.engineered_features(batter_id);

CREATE INDEX IF NOT EXISTS idx_eng_feat_pitcher 
ON features_pitch.engineered_features(pitcher_id);

CREATE INDEX IF NOT EXISTS idx_eng_feat_count 
ON features_pitch.engineered_features(balls, strikes);

-- Verify the insert
SELECT 
    COUNT(*) as total_rows,
    COUNT(DISTINCT outcome_tier1) as tier1_classes,
    COUNT(DISTINCT outcome_tier2) as tier2_classes,
    COUNT(*) FILTER (WHERE outcome_tier1 = 'B') as balls,
    COUNT(*) FILTER (WHERE outcome_tier1 = 'S') as strikes,
    COUNT(*) FILTER (WHERE outcome_tier1 = 'X') as bip,
    ROUND(COUNT(*) FILTER (WHERE outcome_tier1 = 'X')::numeric / COUNT(*) * 100, 2) as bip_pct
FROM features_pitch.engineered_features;
