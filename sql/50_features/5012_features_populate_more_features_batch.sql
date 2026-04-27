/*
File: sql/features/011_populate_more_features_batch.sql
Purpose: Batched population of more research-backed features
Author: Agent Cascade
Date: 2026-04-24
Depends On: sql/features/010_populate_more_features.sql
Called By: Manual execution in batches

Notes:
- Processes 100k rows at a time
- Run multiple times until complete
- Check progress with verification query at end
*/

-- Step 1: Pitch Quality Score (batch of 100k)
WITH unprocessed AS (
    SELECT pitch_id
    FROM features_pitch.engineered_features
    WHERE pitch_quality_score IS NULL
    LIMIT 100000
),
velocity_stats AS (
    SELECT 
        pitcher_id,
        game_year,
        AVG(start_speed) as pitcher_avg_velocity
    FROM features_pitch.base_features
    WHERE start_speed IS NOT NULL
    GROUP BY pitcher_id, game_year
)
UPDATE features_pitch.engineered_features ef
SET 
    pitch_quality_score = (
        (bf.start_speed - 85) / 20 * 30 +
        (SQRT(POWER(bf.pfx_x, 2) + POWER(bf.pfx_z, 2)) / 15 * 25) +
        (1 - ABS(bf.plate_x) / 20) * 20 +
        (bf.release_spin_rate - 2000) / 1000 * 15 +
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
FROM unprocessed u
JOIN features_pitch.base_features bf ON u.pitch_id = bf.pitch_id
LEFT JOIN velocity_stats vs ON bf.pitcher_id = vs.pitcher_id 
    AND bf.game_year = vs.game_year
WHERE ef.pitch_id = u.pitch_id;

-- Step 2: Count leverage (batch of 100k)
WITH unprocessed AS (
    SELECT pitch_id
    FROM features_pitch.engineered_features
    WHERE is_payoff_pitch IS NULL
    LIMIT 100000
)
UPDATE features_pitch.engineered_features ef
SET 
    is_payoff_pitch = (bf.strikes = 2 OR bf.balls = 3),
    count_leverage_index = ((bf.strikes * 0.5) - (bf.balls * 0.4) +
        CASE WHEN bf.strikes = 2 THEN 0.5 ELSE 0 END +
        CASE WHEN bf.balls = 3 THEN -0.5 ELSE 0 END
    ),
    is_pitcher_ahead = ((bf.strikes = 2 AND bf.balls < 3) OR
        (bf.strikes = 1 AND bf.balls = 0) OR
        (bf.strikes = 0 AND bf.balls = 0)),
    is_hitter_ahead = ((bf.balls = 3 AND bf.strikes < 2) OR
        (bf.balls = 2 AND bf.strikes = 0) OR
        (bf.balls = 3 AND bf.strikes = 1)),
    is_strikeout_count = (bf.strikes = 2),
    is_walk_count = (bf.balls = 3),
    is_2_strike_approach = (bf.strikes = 2),
    is_3_ball_approach = (bf.balls = 3)
FROM unprocessed u
JOIN features_pitch.base_features bf ON u.pitch_id = bf.pitch_id
WHERE ef.pitch_id = u.pitch_id;

-- Step 3: Times Through Order (batch of 100k)
WITH unprocessed AS (
    SELECT pitch_id
    FROM features_pitch.engineered_features
    WHERE times_through_order_detailed IS NULL
    LIMIT 100000
),
pitch_order_sequence AS (
    SELECT 
        pitch_id,
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
FROM unprocessed u
JOIN pitch_order_sequence pos ON u.pitch_id = pos.pitch_id
WHERE ef.pitch_id = u.pitch_id;

-- Step 4: Game situation (batch of 100k)
WITH unprocessed AS (
    SELECT pitch_id
    FROM features_pitch.engineered_features
    WHERE inning_phase IS NULL
    LIMIT 100000
)
UPDATE features_pitch.engineered_features ef
SET 
    inning_phase = CASE 
        WHEN inning <= 3 THEN 'early'
        WHEN inning <= 6 THEN 'middle'
        WHEN inning <= 8 THEN 'late'
        ELSE 'extra'
    END,
    score_differential_bucket = CASE 
        WHEN score_diff = 0 THEN 'tie'
        WHEN ABS(score_diff) = 1 THEN 'close'
        WHEN ABS(score_diff) BETWEEN 2 AND 3 THEN 'moderate'
        ELSE 'blowout'
    END,
    is_one_run_game = (ABS(score_diff) <= 1),
    is_save_situation = (
        inning >= 9 AND 
        absolute_score_diff <= 3 AND
        is_late_in_pa
    ),
    leverage_index_bracket = CASE 
        WHEN pa_pressure_index > 0.8 THEN 'high'
        WHEN pa_pressure_index > 0.5 THEN 'medium'
        ELSE 'low'
    END
FROM unprocessed u
WHERE ef.pitch_id = u.pitch_id;

-- Step 5: Run Expectancy (batch of 100k)
WITH unprocessed AS (
    SELECT pitch_id, outs_when_up, base_state
    FROM features_pitch.engineered_features
    WHERE run_expectancy_24 IS NULL
    LIMIT 100000
),
re_values AS (
    SELECT 
        pitch_id,
        CASE outs_when_up
            WHEN 0 THEN 
                CASE base_state
                    WHEN 0 THEN 0.461 WHEN 1 THEN 0.831 WHEN 2 THEN 1.068
                    WHEN 3 THEN 1.211 WHEN 4 THEN 1.331 WHEN 5 THEN 1.448
                    WHEN 6 THEN 1.550 WHEN 7 THEN 1.842 ELSE 0.461
                END
            WHEN 1 THEN
                CASE base_state
                    WHEN 0 THEN 0.243 WHEN 1 THEN 0.489 WHEN 2 THEN 0.644
                    WHEN 3 THEN 0.706 WHEN 4 THEN 0.797 WHEN 5 THEN 0.857
                    WHEN 6 THEN 0.920 WHEN 7 THEN 1.089 ELSE 0.243
                END
            WHEN 2 THEN
                CASE base_state
                    WHEN 0 THEN 0.095 WHEN 1 THEN 0.214 WHEN 2 THEN 0.297
                    WHEN 3 THEN 0.323 WHEN 4 THEN 0.368 WHEN 5 THEN 0.394
                    WHEN 6 THEN 0.423 WHEN 7 THEN 0.504 ELSE 0.095
                END
            ELSE 0.461
        END as re24
    FROM unprocessed
)
UPDATE features_pitch.engineered_features ef
SET run_expectancy_24 = rv.re24
FROM re_values rv
WHERE ef.pitch_id = rv.pitch_id;

-- Step 6: WPA and environmental (batch of 100k)
WITH unprocessed AS (
    SELECT pitch_id
    FROM features_pitch.engineered_features
    WHERE win_probability_added IS NULL
    LIMIT 100000
)
UPDATE features_pitch.engineered_features ef
SET 
    win_probability_added = (delta_home_win_exp * 100),
    pitch_type_family = CASE 
        WHEN is_fastball THEN 'fastball'
        WHEN is_breaking THEN 'breaking'
        WHEN is_offspeed THEN 'offspeed'
        ELSE 'other'
    END
FROM unprocessed u
WHERE ef.pitch_id = u.pitch_id;

-- Step 7: Environmental factors (batch of 100k)
WITH unprocessed AS (
    SELECT ef.pitch_id, bf.game_date, bf.game_pk
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    WHERE ef.is_day_game IS NULL
    LIMIT 100000
)
UPDATE features_pitch.engineered_features ef
SET 
    is_day_game = (EXTRACT(HOUR FROM u.game_date) BETWEEN 12 AND 17),
    game_month = TO_CHAR(u.game_date, 'Month'),
    is_opening_series = (
        EXTRACT(MONTH FROM u.game_date) = 3 OR 
        (EXTRACT(MONTH FROM u.game_date) = 4 AND EXTRACT(DAY FROM u.game_date) <= 7)
    ),
    is_getaway_day = FALSE
FROM unprocessed u
WHERE ef.pitch_id = u.pitch_id;

-- Progress report
SELECT 
    'Batch progress - More Features' as status,
    COUNT(*) as total_rows,
    COUNT(pitch_quality_score) as with_quality,
    COUNT(is_payoff_pitch) as with_payoff,
    COUNT(times_through_order_detailed) as with_ttop,
    COUNT(run_expectancy_24) as with_re24,
    COUNT(win_probability_added) as with_wpa,
    COUNT(is_day_game) as with_daynight,
    ROUND(COUNT(pitch_quality_score)::numeric / COUNT(*) * 100, 2) as pct_complete
FROM features_pitch.engineered_features;
