/*
File: sql/features/008_populate_additional_features_batch.sql
Purpose: Populate additional engineered features in small batches
Author: Agent Cascade
Date: 2026-04-24
Depends On: sql/features/007_populate_additional_features.sql
Called By: Manual execution

Notes:
- Processes 100k rows at a time to avoid long transactions
- Run this script multiple times until all rows are processed
- Check progress with: SELECT COUNT(*) FROM features_pitch.engineered_features WHERE is_same_handed_matchup IS NOT NULL;
*/

-- Process platoon/matchup indicators (batch of 100k unprocessed rows)
WITH unprocessed AS (
    SELECT pitch_id
    FROM features_pitch.engineered_features
    WHERE is_same_handed_matchup IS NULL
    LIMIT 100000
)
UPDATE features_pitch.engineered_features ef
SET 
    is_same_handed_matchup = (bf.stand = bf.p_throws),
    is_platoon_advantage_pitcher = (
        (bf.p_throws = 'R' AND bf.stand = 'R') OR 
        (bf.p_throws = 'L' AND bf.stand = 'L')
    ),
    month_of_season = EXTRACT(MONTH FROM bf.game_date)::integer,
    is_early_season = (EXTRACT(MONTH FROM bf.game_date) IN (3, 4)),
    is_late_season = (EXTRACT(MONTH FROM bf.game_date) IN (8, 9, 10))
FROM features_pitch.base_features bf
WHERE ef.pitch_id = bf.pitch_id
  AND ef.pitch_id IN (SELECT pitch_id FROM unprocessed);

-- Process spin characteristics (batch of 100k unprocessed rows)
WITH unprocessed AS (
    SELECT pitch_id
    FROM features_pitch.engineered_features
    WHERE spin_axis_quadrant IS NULL
    LIMIT 100000
)
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
  AND ef.pitch_id IN (SELECT pitch_id FROM unprocessed)
  AND bf.spin_axis IS NOT NULL;

-- Process pressure and situation indicators (batch of 100k)
WITH unprocessed AS (
    SELECT pitch_id
    FROM features_pitch.engineered_features
    WHERE pa_pressure_index IS NULL
    LIMIT 100000
)
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
    is_run_expectancy_critical = (ef.is_runner_in_scoring_position AND bf.outs_when_up < 2)
FROM features_pitch.base_features bf
WHERE ef.pitch_id = bf.pitch_id
  AND ef.pitch_id IN (SELECT pitch_id FROM unprocessed);

-- Set ace pitcher flag (can do all at once since it's pitcher-level)
WITH pitcher_velocity_rank AS (
    SELECT 
        pitcher_id,
        NTILE(10) OVER (ORDER BY AVG(start_speed) DESC) as velocity_decile
    FROM features_pitch.base_features
    WHERE start_speed IS NOT NULL
    GROUP BY pitcher_id
)
UPDATE features_pitch.engineered_features ef
SET is_ace_pitcher = (pvr.velocity_decile = 1)
FROM pitcher_velocity_rank pvr
WHERE ef.pitcher_id = pvr.pitcher_id
  AND ef.is_ace_pitcher IS NULL;

-- Set closer situation (can do all at once)
UPDATE features_pitch.engineered_features
SET is_closer_situation = (
    inning >= 9 AND 
    absolute_score_diff <= 2 AND 
    is_late_in_pa
)
WHERE is_closer_situation IS NULL;

-- Progress report
SELECT 
    'Batch progress' as status,
    COUNT(*) as total_rows,
    COUNT(is_same_handed_matchup) as with_platoon,
    COUNT(spin_axis_quadrant) as with_spin,
    COUNT(pa_pressure_index) as with_pressure,
    COUNT(is_ace_pitcher) as with_ace,
    ROUND(COUNT(is_same_handed_matchup)::numeric / COUNT(*) * 100, 2) as pct_complete
FROM features_pitch.engineered_features;
