/*
File: sql/features/010_populate_more_features.sql
Purpose: Populate additional research-backed features from KB
Author: Agent Cascade
Date: 2026-04-24
Depends On: sql/features/009_more_engineered_features.sql
Called By: Manual execution

Tables Modified:
- features_pitch.engineered_features (populates new columns)

Features Populated:
- Pitch quality metrics
- Count leverage indices
- Times Through Order Penalty (TTOP)
- Game situation enhancements
- Environmental factors
- Run expectancy

Notes:
- Batched processing for performance
- Uses existing data only (no external APIs)
- Research-backed from FEATURE_ENGINEERING_PLAN.md
*/

-- Step 1: Pitch Quality Score (composite metric)
WITH velocity_stats AS (
    SELECT 
        pitcher_id,
        game_year,
        AVG(start_speed) as pitcher_avg_velocity,
        STDDEV(start_speed) as pitcher_velo_std
    FROM features_pitch.base_features
    WHERE start_speed IS NOT NULL
    GROUP BY pitcher_id, game_year
)
UPDATE features_pitch.engineered_features ef
SET 
    pitch_quality_score = (
        -- Velocity component (normalized)
        (bf.start_speed - 85) / 20 * 30 +
        -- Movement component
        (SQRT(POWER(bf.pfx_x, 2) + POWER(bf.pfx_z, 2)) / 15 * 25) +
        -- Location quality (closer to center = worse, on edge = better for deception)
        (1 - ABS(bf.plate_x) / 20) * 20 +
        -- Spin component
        (bf.release_spin_rate - 2000) / 1000 * 15 +
        -- Extension component
        (bf.release_extension / 7 * 10)
    ),
    velocity_bucket = CASE 
        WHEN bf.start_speed >= 95 THEN 'elite'
        WHEN bf.start_speed >= 90 THEN 'above_avg'
        WHEN bf.start_speed >= 85 THEN 'avg'
        WHEN bf.start_speed >= 80 THEN 'below_avg'
        ELSE 'slow'
    END,
    velocity_diff_from_pitcher_avg = bf.start_speed - vs.pitcher_avg_velocity
FROM features_pitch.base_features bf
LEFT JOIN velocity_stats vs ON bf.pitcher_id = vs.pitcher_id 
    AND bf.game_year = vs.game_year
WHERE ef.pitch_id = bf.pitch_id
  AND ef.pitch_quality_score IS NULL
  AND bf.start_speed IS NOT NULL;

-- Step 2: Payoff pitch and count leverage
UPDATE features_pitch.engineered_features ef
SET 
    is_payoff_pitch = (
        bf.strikes = 2 OR bf.balls = 3
    ),
    count_leverage_index = (
        -- Positive = pitcher advantage, negative = hitter advantage
        (bf.strikes * 0.5) - (bf.balls * 0.4) +
        CASE WHEN bf.strikes = 2 THEN 0.5 ELSE 0 END +
        CASE WHEN bf.balls = 3 THEN -0.5 ELSE 0 END
    ),
    is_pitcher_ahead = (
        (bf.strikes = 2 AND bf.balls < 3) OR
        (bf.strikes = 1 AND bf.balls = 0) OR
        (bf.strikes = 0 AND bf.balls = 0)
    ),
    is_hitter_ahead = (
        (bf.balls = 3 AND bf.strikes < 2) OR
        (bf.balls = 2 AND bf.strikes = 0) OR
        (bf.balls = 3 AND bf.strikes = 1)
    ),
    is_strikeout_count = (bf.strikes = 2),
    is_walk_count = (bf.balls = 3),
    is_2_strike_approach = (bf.strikes = 2),
    is_3_ball_approach = (bf.balls = 3)
FROM features_pitch.base_features bf
WHERE ef.pitch_id = bf.pitch_id
  AND ef.is_payoff_pitch IS NULL;

-- Step 3: Times Through Order (detailed TTOP)
WITH pitch_order_sequence AS (
    SELECT 
        pitch_id,
        game_pk,
        batter_id,
        pitcher_id,
        at_bat_number,
        -- Count how many times this batter has faced this pitcher
        ROW_NUMBER() OVER (
            PARTITION BY game_pk, batter_id, pitcher_id 
            ORDER BY at_bat_number
        ) as tto
    FROM features_pitch.base_features
)
UPDATE features_pitch.engineered_features ef
SET 
    times_through_order_detailed = pos.tto,
    is_first_time_seeing_pitcher = (pos.tto = 1),
    is_second_time_seeing_pitcher = (pos.tto = 2),
    is_third_plus_time_seeing_pitcher = (pos.tto >= 3),
    ttop_penalty_applies = (pos.tto >= 3)
FROM pitch_order_sequence pos
WHERE ef.pitch_id = pos.pitch_id
  AND ef.times_through_order_detailed IS NULL;

-- Step 4: Game situation enhancements
UPDATE features_pitch.engineered_features ef
SET 
    inning_phase = CASE 
        WHEN ef.inning <= 3 THEN 'early'
        WHEN ef.inning <= 6 THEN 'middle'
        WHEN ef.inning <= 8 THEN 'late'
        ELSE 'extra'
    END,
    score_differential_bucket = CASE 
        WHEN ef.score_diff = 0 THEN 'tie'
        WHEN ABS(ef.score_diff) = 1 THEN 'close'
        WHEN ABS(ef.score_diff) BETWEEN 2 AND 3 THEN 'moderate'
        ELSE 'blowout'
    END,
    is_one_run_game = (ABS(ef.score_diff) <= 1),
    is_save_situation = (
        ef.inning >= 9 AND 
        ef.absolute_score_diff <= 3 AND
        ef.is_late_in_pa
    ),
    leverage_index_bracket = CASE 
        WHEN ef.pa_pressure_index > 0.8 THEN 'high'
        WHEN ef.pa_pressure_index > 0.5 THEN 'medium'
        ELSE 'low'
    END
WHERE ef.inning_phase IS NULL;

-- Step 5: Run Expectancy (simplified RE24)
WITH base_out_state AS (
    SELECT 
        pitch_id,
        -- Calculate expected runs based on base-out state
        -- Standard RE24 values (approximate)
        CASE ef.outs_when_up
            WHEN 0 THEN 
                CASE ef.base_state
                    WHEN 0 THEN 0.461  -- bases empty
                    WHEN 1 THEN 0.831  -- 1B
                    WHEN 2 THEN 1.068  -- 2B
                    WHEN 3 THEN 1.211  -- 3B
                    WHEN 4 THEN 1.331  -- 1B+2B
                    WHEN 5 THEN 1.448  -- 1B+3B
                    WHEN 6 THEN 1.550  -- 2B+3B
                    WHEN 7 THEN 1.842  -- loaded
                    ELSE 0.461
                END
            WHEN 1 THEN
                CASE ef.base_state
                    WHEN 0 THEN 0.243
                    WHEN 1 THEN 0.489
                    WHEN 2 THEN 0.644
                    WHEN 3 THEN 0.706
                    WHEN 4 THEN 0.797
                    WHEN 5 THEN 0.857
                    WHEN 6 THEN 0.920
                    WHEN 7 THEN 1.089
                    ELSE 0.243
                END
            WHEN 2 THEN
                CASE ef.base_state
                    WHEN 0 THEN 0.095
                    WHEN 1 THEN 0.214
                    WHEN 2 THEN 0.297
                    WHEN 3 THEN 0.323
                    WHEN 4 THEN 0.368
                    WHEN 5 THEN 0.394
                    WHEN 6 THEN 0.423
                    WHEN 7 THEN 0.504
                    ELSE 0.095
                END
            ELSE 0.461
        END as run_expectancy
    FROM features_pitch.engineered_features ef
)
UPDATE features_pitch.engineered_features ef
SET run_expectancy_24 = bos.run_expectancy
FROM base_out_state bos
WHERE ef.pitch_id = bos.pitch_id
  AND ef.run_expectancy_24 IS NULL;

-- Step 6: Win Probability Added (simplified)
UPDATE features_pitch.engineered_features ef
SET win_probability_added = (
    ef.delta_home_win_exp * 100  -- Convert to percentage points
)
WHERE ef.win_probability_added IS NULL
  AND ef.delta_home_win_exp IS NOT NULL;

-- Step 7: Pitch type family and usage
UPDATE features_pitch.engineered_features ef
SET 
    pitch_type_family = CASE 
        WHEN ef.is_fastball THEN 'fastball'
        WHEN ef.is_breaking THEN 'breaking'
        WHEN ef.is_offspeed THEN 'offspeed'
        ELSE 'other'
    END,
    is_primary_pitch_type = FALSE  -- Will be updated based on pitcher arsenal
WHERE ef.pitch_type_family IS NULL;

-- Step 8: Environmental factors
UPDATE features_pitch.engineered_features ef
SET 
    is_day_game = (EXTRACT(HOUR FROM bf.game_date) BETWEEN 12 AND 17),
    game_month = TO_CHAR(bf.game_date, 'Month'),
    is_opening_series = (
        EXTRACT(MONTH FROM bf.game_date) = 3 OR 
        (EXTRACT(MONTH FROM bf.game_date) = 4 AND EXTRACT(DAY FROM bf.game_date) <= 7)
    ),
    is_getaway_day = FALSE  -- Would need travel schedule data
FROM features_pitch.base_features bf
WHERE ef.pitch_id = bf.pitch_id
  AND ef.is_day_game IS NULL;

-- Step 9: Mark primary pitch types per pitcher
WITH pitcher_primary_pitches AS (
    SELECT 
        pitcher_id,
        pitch_type,
        COUNT(*) as pitch_count,
        ROW_NUMBER() OVER (
            PARTITION BY pitcher_id 
            ORDER BY COUNT(*) DESC
        ) as rank
    FROM features_pitch.base_features
    WHERE pitch_type IS NOT NULL
    GROUP BY pitcher_id, pitch_type
)
UPDATE features_pitch.engineered_features ef
SET is_primary_pitch_type = TRUE
FROM pitcher_primary_pitches ppp
JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
WHERE bf.pitcher_id = ppp.pitcher_id
  AND bf.pitch_type = ppp.pitch_type
  AND ppp.rank = 1
  AND ef.is_primary_pitch_type = FALSE;

-- Verification
SELECT 
    'More features populated' as status,
    COUNT(*) as total_rows,
    COUNT(pitch_quality_score) as with_quality,
    COUNT(is_payoff_pitch) as with_payoff,
    COUNT(times_through_order_detailed) as with_ttop,
    COUNT(run_expectancy_24) as with_re24,
    COUNT(win_probability_added) as with_wpa,
    ROUND(AVG(run_expectancy_24)::numeric, 3) as avg_re24,
    ROUND(AVG(win_probability_added)::numeric, 4) as avg_wpa,
    ROUND(AVG(CASE WHEN ttop_penalty_applies THEN 1 ELSE 0 END) * 100, 2) as ttop_pct
FROM features_pitch.engineered_features;
