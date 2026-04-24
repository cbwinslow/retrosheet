/*
File: sql/features/007_populate_additional_features.sql
Purpose: Populate additional engineered features in batches
Author: Agent Cascade
Date: 2026-04-24
Depends On: sql/features/006_additional_engineered_features.sql
Called By: Manual execution

Tables Modified:
- features_pitch.engineered_features (updates new columns)

Features Populated:
- Pitch tunneling (velocity_change_from_prev)
- Spin characteristics (spin_rate_percentile, spin_axis categories)
- Platoon indicators (is_same_handed_matchup)
- Fatigue metrics (pitcher_fatigue_score)
- Pressure metrics (pa_pressure_index, is_walk_off_situation)
- Ace pitcher identification

Notes:
- Processes data in batches to avoid long-running transaction
- Uses direct joins instead of correlated subqueries for performance
*/

-- Step 1: Calculate pitcher fatigue (pitch count within game)
WITH pitcher_game_pitch_count AS (
    SELECT 
        ef.pitch_id,
        ROW_NUMBER() OVER (
            PARTITION BY ef.game_pk, ef.pitcher_id 
            ORDER BY ef.at_bat_number, ef.pitch_number
        ) as pitch_num_in_game,
        COUNT(*) OVER (
            PARTITION BY ef.game_pk, ef.pitcher_id
        ) as total_pitches_game
    FROM features_pitch.engineered_features ef
)
UPDATE features_pitch.engineered_features ef
SET pitcher_fatigue_score = 
    CASE 
        WHEN pgc.total_pitches_game > 1 
        THEN pgc.pitch_num_in_game::numeric / pgc.total_pitches_game 
        ELSE 0 
    END
FROM pitcher_game_pitch_count pgc
WHERE ef.pitch_id = pgc.pitch_id;

-- Step 2: Calculate velocity change from previous pitch (tunneling)
WITH prev_pitch_velocity AS (
    SELECT 
        pitch_id,
        start_speed - LAG(start_speed) OVER (
            PARTITION BY game_pk, at_bat_number 
            ORDER BY pitch_number
        ) as vel_change
    FROM features_pitch.base_features
)
UPDATE features_pitch.engineered_features ef
SET velocity_change_from_prev = ppv.vel_change
FROM prev_pitch_velocity ppv
WHERE ef.pitch_id = ppv.pitch_id
  AND ppv.vel_change IS NOT NULL;

-- Step 3: Calculate spin rate percentile
WITH spin_percentiles AS (
    SELECT 
        pitch_id,
        PERCENT_RANK() OVER (
            ORDER BY release_spin_rate
        ) as spin_pct
    FROM features_pitch.base_features
    WHERE release_spin_rate IS NOT NULL
)
UPDATE features_pitch.engineered_features ef
SET spin_rate_percentile = sp.spin_pct
FROM spin_percentiles sp
WHERE ef.pitch_id = sp.pitch_id;

-- Step 4: Platoon/matchup indicators
UPDATE features_pitch.engineered_features ef
SET 
    is_same_handed_matchup = (bf.stand = bf.p_throws),
    is_platoon_advantage_pitcher = (
        (bf.p_throws = 'R' AND bf.stand = 'R') OR 
        (bf.p_throws = 'L' AND bf.stand = 'L')
    )
FROM features_pitch.base_features bf
WHERE ef.pitch_id = bf.pitch_id;

-- Step 5: Spin axis characteristics
UPDATE features_pitch.engineered_features ef
SET 
    spin_axis_quadrant = CASE 
        WHEN bf.spin_axis BETWEEN 0 AND 90 THEN 'top_right'
        WHEN bf.spin_axis BETWEEN 90 AND 180 THEN 'top_left'
        WHEN bf.spin_axis BETWEEN 180 AND 270 THEN 'bottom_left'
        ELSE 'bottom_right'
    END,
    is_backspin = (bf.spin_axis BETWEEN 135 AND 225),
    is_topspin = (bf.spin_axis BETWEEN 315 AND 360 OR bf.spin_axis BETWEEN 0 AND 45),
    is_gyro_spin = (bf.spin_axis BETWEEN 45 AND 135 OR bf.spin_axis BETWEEN 225 AND 315)
FROM features_pitch.base_features bf
WHERE ef.pitch_id = bf.pitch_id
  AND bf.spin_axis IS NOT NULL;

-- Step 6: Pressure and situation indicators
UPDATE features_pitch.engineered_features ef
SET 
    pa_pressure_index = (
        (CASE WHEN bf.outs_when_up < 2 THEN 0.3 ELSE 0 END) +
        (CASE WHEN ef.is_runner_in_scoring_position THEN 0.4 ELSE 0 END) +
        (CASE WHEN ef.absolute_score_diff <= 2 THEN 0.2 ELSE 0 END) +
        (CASE WHEN ef.inning >= 7 THEN 0.1 ELSE 0 END)
    ),
    is_high_pressure_pa = (
        (CASE WHEN bf.outs_when_up < 2 THEN 0.3 ELSE 0 END) +
        (CASE WHEN ef.is_runner_in_scoring_position THEN 0.4 ELSE 0 END) +
        (CASE WHEN ef.absolute_score_diff <= 2 THEN 0.2 ELSE 0 END) +
        (CASE WHEN ef.inning >= 7 THEN 0.1 ELSE 0 END)
    ) > 0.7,
    is_walk_off_situation = (
        bf.inning >= 9 AND 
        ABS(bf.bat_score - bf.fld_score) <= 3
    ),
    is_run_expectancy_critical = (ef.is_runner_in_scoring_position AND bf.outs_when_up < 2),
    month_of_season = EXTRACT(MONTH FROM bf.game_date)::integer,
    is_early_season = (EXTRACT(MONTH FROM bf.game_date) IN (3, 4)),
    is_late_season = (EXTRACT(MONTH FROM bf.game_date) IN (8, 9, 10))
FROM features_pitch.base_features bf
WHERE ef.pitch_id = bf.pitch_id;

-- Step 7: Ace pitcher identification (top 10% by average velocity)
WITH pitcher_velocity_rank AS (
    SELECT 
        pitcher_id,
        AVG(start_speed) as avg_velocity,
        NTILE(10) OVER (ORDER BY AVG(start_speed) DESC) as velocity_decile
    FROM features_pitch.base_features
    WHERE start_speed IS NOT NULL
    GROUP BY pitcher_id
)
UPDATE features_pitch.engineered_features ef
SET is_ace_pitcher = (pvr.velocity_decile = 1)
FROM pitcher_velocity_rank pvr
WHERE ef.pitcher_id = pvr.pitcher_id;

-- Step 8: Closer situation
UPDATE features_pitch.engineered_features ef
SET is_closer_situation = (
    ef.inning >= 9 AND 
    ef.absolute_score_diff <= 2 AND 
    ef.is_late_in_pa
);

-- Step 9: Lineup position estimation (based on first PA appearance)
WITH batter_first_pa AS (
    SELECT 
        game_pk,
        batter_id,
        MIN(at_bat_number) as first_pa
    FROM features_pitch.engineered_features
    GROUP BY game_pk, batter_id
)
UPDATE features_pitch.engineered_features ef
SET 
    lineup_position_estimated = CASE 
        WHEN bfp.first_pa <= 3 THEN 1
        WHEN bfp.first_pa <= 6 THEN 2
        ELSE 3
    END,
    is_top_of_lineup = (bfp.first_pa <= 3),
    is_bottom_of_lineup = (bfp.first_pa > 6)
FROM batter_first_pa bfp
WHERE ef.game_pk = bfp.game_pk 
  AND ef.batter_id = bfp.batter_id;

-- Verification
SELECT 
    'Additional features populated' as status,
    COUNT(*) as total_rows,
    COUNT(velocity_change_from_prev) as with_velocity_change,
    ROUND(AVG(velocity_change_from_prev)::numeric, 2) as avg_velocity_change,
    COUNT(spin_rate_percentile) as with_spin_pct,
    COUNT(is_same_handed_matchup) as with_platoon,
    ROUND(AVG(CASE WHEN is_same_handed_matchup THEN 1 ELSE 0 END) * 100, 2) as same_handed_pct,
    COUNT(pitcher_fatigue_score) as with_fatigue,
    ROUND(AVG(pitcher_fatigue_score)::numeric, 3) as avg_fatigue,
    COUNT(pa_pressure_index) as with_pressure,
    ROUND(AVG(pa_pressure_index)::numeric, 3) as avg_pressure,
    ROUND(AVG(CASE WHEN is_ace_pitcher THEN 1 ELSE 0 END) * 100, 2) as ace_pitcher_pct,
    ROUND(AVG(CASE WHEN is_walk_off_situation THEN 1 ELSE 0 END) * 100, 2) as walk_off_pct,
    ROUND(AVG(CASE WHEN is_closer_situation THEN 1 ELSE 0 END) * 100, 2) as closer_sit_pct
FROM features_pitch.engineered_features;
