-- File: sql/features/006_additional_engineered_features.sql
-- Purpose: Add additional research-backed engineered features to engineered_features table
-- Author: Agent Cascade
-- Date: 2026-04-24

-- Add new columns to engineered_features table
ALTER TABLE features_pitch.engineered_features 
    ADD COLUMN IF NOT EXISTS velocity_change_from_prev NUMERIC,
    ADD COLUMN IF NOT EXISTS spin_rate_percentile NUMERIC,
    ADD COLUMN IF NOT EXISTS spin_rate_vs_pitchtype_avg NUMERIC,
    ADD COLUMN IF NOT EXISTS is_backspin BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_topspin BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_gyro_spin BOOLEAN,
    ADD COLUMN IF NOT EXISTS spin_axis_quadrant TEXT,
    ADD COLUMN IF NOT EXISTS is_same_handed_matchup BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_platoon_advantage_pitcher BOOLEAN,
    ADD COLUMN IF NOT EXISTS pitcher_fatigue_score NUMERIC,
    ADD COLUMN IF NOT EXISTS inning_normalized NUMERIC,
    ADD COLUMN IF NOT EXISTS score_pressure_ratio NUMERIC,
    ADD COLUMN IF NOT EXISTS is_first_time_through_order BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_second_time_through_order BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_third_plus_time_through_order BOOLEAN,
    ADD COLUMN IF NOT EXISTS pa_pressure_index NUMERIC,
    ADD COLUMN IF NOT EXISTS is_high_pressure_pa BOOLEAN,
    ADD COLUMN IF NOT EXISTS release_point_consistency_5pitch NUMERIC,
    ADD COLUMN IF NOT EXISTS plate_appearance_importance NUMERIC,
    ADD COLUMN IF NOT EXISTS is_walk_off_situation BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_run_expectancy_critical BOOLEAN,
    ADD COLUMN IF NOT EXISTS day_of_week TEXT,
    ADD COLUMN IF NOT EXISTS is_weekend BOOLEAN,
    ADD COLUMN IF NOT EXISTS month_of_season INTEGER,
    ADD COLUMN IF NOT EXISTS is_early_season BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_late_season BOOLEAN,
    ADD COLUMN IF NOT EXISTS pitch_shape_consistency NUMERIC,
    ADD COLUMN IF NOT EXISTS is_ace_pitcher BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_closer_situation BOOLEAN,
    ADD COLUMN IF NOT EXISTS lineup_position_estimated INTEGER,
    ADD COLUMN IF NOT EXISTS is_top_of_lineup BOOLEAN,
    ADD COLUMN IF NOT EXISTS is_bottom_of_lineup BOOLEAN;

-- Update with additional engineered features
WITH spin_stats AS (
    -- Calculate spin rate statistics by pitch type
    SELECT 
        pitch_type,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY release_spin_rate) as spin_p25,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY release_spin_rate) as spin_p50,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY release_spin_rate) as spin_p75,
        AVG(release_spin_rate) as spin_avg,
        STDDEV(release_spin_rate) as spin_std
    FROM features_pitch.base_features
    WHERE release_spin_rate IS NOT NULL
    GROUP BY pitch_type
),
pitcher_game_stats AS (
    -- Calculate pitch count per pitcher per game for fatigue
    SELECT 
        game_pk,
        pitcher_id,
        ROW_NUMBER() OVER (PARTITION BY game_pk, pitcher_id ORDER BY game_date, at_bat_number, pitch_number) as game_pitch_num,
        COUNT(*) OVER (PARTITION BY game_pk, pitcher_id) as total_pitches_in_game
    FROM features_pitch.base_features
),
batter_game_stats AS (
    -- Estimate lineup position based on batting order appearance
    SELECT 
        game_pk,
        batter_id,
        at_bat_number,
        MIN(at_bat_number) OVER (PARTITION BY game_pk, batter_id) as first_pa_num,
        ROW_NUMBER() OVER (PARTITION BY game_pk, batter_id ORDER BY at_bat_number) as pa_num_in_game
    FROM features_pitch.base_features
),
spin_axis_categories AS (
    -- Classify spin axis into meaningful categories
    SELECT 
        pitch_id,
        CASE 
            WHEN spin_axis BETWEEN 0 AND 90 THEN 'top_right'
            WHEN spin_axis BETWEEN 90 AND 180 THEN 'top_left'
            WHEN spin_axis BETWEEN 180 AND 270 THEN 'bottom_left'
            ELSE 'bottom_right'
        END as axis_quadrant,
        CASE 
            WHEN spin_axis BETWEEN 135 AND 225 THEN TRUE  -- Topspin (backspin for RHP)
            ELSE FALSE
        END as is_backspin_flag,
        CASE 
            WHEN spin_axis BETWEEN 315 AND 360 OR spin_axis BETWEEN 0 AND 45 THEN TRUE  -- Topspin
            ELSE FALSE
        END as is_topspin_flag,
        CASE 
            WHEN spin_axis BETWEEN 45 AND 135 OR spin_axis BETWEEN 225 AND 315 THEN TRUE  -- Side spin / gyro
            ELSE FALSE
        END as is_gyro_flag
    FROM features_pitch.base_features
    WHERE spin_axis IS NOT NULL
),
pitcher_arsenal_rank AS (
    -- Identify ace pitchers (top 10% by velocity and usage)
    SELECT 
        pitcher_id,
        AVG(start_speed) as avg_velocity,
        COUNT(DISTINCT pitch_type) as arsenal_depth,
        NTILE(10) OVER (ORDER BY AVG(start_speed) DESC) as velocity_decile
    FROM features_pitch.base_features
    WHERE start_speed IS NOT NULL
    GROUP BY pitcher_id
)

UPDATE features_pitch.engineered_features ef
SET
    -- Pitch tunneling: velocity change from previous pitch in same PA
    velocity_change_from_prev = (
        SELECT ef2.start_speed - LAG(ef2.start_speed) OVER (
            PARTITION BY ef2.game_pk, ef2.at_bat_number 
            ORDER BY ef2.pitch_number
        )
        FROM features_pitch.engineered_features ef2
        WHERE ef2.pitch_id = ef.pitch_id
    ),
    
    -- Spin rate percentile (relative to all pitches)
    spin_rate_percentile = (
        SELECT PERCENT_RANK() OVER (ORDER BY release_spin_rate)
        FROM features_pitch.base_features bf
        WHERE bf.pitch_id = ef.pitch_id
    ),
    
    -- Spin rate vs pitch type average
    spin_rate_vs_pitchtype_avg = bf.release_spin_rate - ss.spin_avg,
    
    -- Spin characteristics based on axis
    is_backspin = COALESCE(sac.is_backspin_flag, FALSE),
    is_topspin = COALESCE(sac.is_topspin_flag, FALSE),
    is_gyro_spin = COALESCE(sac.is_gyro_flag, FALSE),
    spin_axis_quadrant = COALESCE(sac.axis_quadrant, 'unknown'),
    
    -- Matchup handedness
    is_same_handed_matchup = (bf.stand = bf.p_throws),
    is_platoon_advantage_pitcher = (
        (bf.p_throws = 'R' AND bf.stand = 'R') OR 
        (bf.p_throws = 'L' AND bf.stand = 'L')
    ),
    
    -- Pitcher fatigue (normalized pitch count in game)
    pitcher_fatigue_score = pgs.game_pitch_num::numeric / NULLIF(pgs.total_pitches_in_game, 0),
    
    -- Inning normalized (0-1 scale, extra innings > 1)
    inning_normalized = bf.inning::numeric / 9.0,
    
    -- Score pressure (ratio of current diff to potential max change)
    score_pressure_ratio = ABS(bf.bat_score - bf.fld_score)::numeric / 
        GREATEST(ABS(bf.bat_score - bf.fld_score) + 4, 1),
    
    -- Times through order (estimated)
    is_first_time_through_order = (bgs.pa_num_in_game = 1),
    is_second_time_through_order = (bgs.pa_num_in_game = 2),
    is_third_plus_time_through_order = (bgs.pa_num_in_game >= 3),
    
    -- Plate appearance pressure index
    pa_pressure_index = (
        (CASE WHEN bf.outs_when_up < 2 THEN 0.3 ELSE 0 END) +
        (CASE WHEN ef.is_runner_in_scoring_position THEN 0.4 ELSE 0 END) +
        (CASE WHEN ef.is_close_game THEN 0.2 ELSE 0 END) +
        (CASE WHEN ef.is_late_inning THEN 0.1 ELSE 0 END)
    ),
    is_high_pressure_pa = (
        (CASE WHEN bf.outs_when_up < 2 THEN 0.3 ELSE 0 END) +
        (CASE WHEN ef.is_runner_in_scoring_position THEN 0.4 ELSE 0 END) +
        (CASE WHEN ef.is_close_game THEN 0.2 ELSE 0 END) +
        (CASE WHEN ef.is_late_inning THEN 0.1 ELSE 0 END)
    ) > 0.7,
    
    -- Walk-off situation
    is_walk_off_situation = (
        bf.inning >= 9 AND 
        ABS(bf.bat_score - bf.fld_score) <= 3 AND
        ef.is_late_in_pa
    ),
    
    -- Run expectancy critical (high leverage on runs)
    is_run_expectancy_critical = (ef.is_runner_in_scoring_position AND bf.outs_when_up < 2),
    
    -- Season timing
    month_of_season = EXTRACT(MONTH FROM bf.game_date),
    is_early_season = (EXTRACT(MONTH FROM bf.game_date) IN (3, 4)),
    is_late_season = (EXTRACT(MONTH FROM bf.game_date) IN (8, 9, 10)),
    
    -- Ace pitcher identification (top velocity decile)
    is_ace_pitcher = (par.velocity_decile = 1),
    
    -- Closer situation (9th inning or later, close game, late in PA)
    is_closer_situation = (
        bf.inning >= 9 AND 
        ef.is_close_game AND 
        ef.is_late_in_pa
    ),
    
    -- Estimated lineup position
    lineup_position_estimated = 
        CASE 
            WHEN bgs.first_pa_num <= 3 THEN 1
            WHEN bgs.first_pa_num <= 6 THEN 2
            ELSE 3
        END,
    is_top_of_lineup = (bgs.first_pa_num <= 3),
    is_bottom_of_lineup = (bgs.first_pa_num > 6)

FROM features_pitch.base_features bf
LEFT JOIN spin_stats ss ON bf.pitch_type = ss.pitch_type
LEFT JOIN pitcher_game_stats pgs ON bf.pitch_id = pgs.pitch_id
LEFT JOIN batter_game_stats bgs ON bf.pitch_id = bgs.pitch_id
LEFT JOIN spin_axis_categories sac ON bf.pitch_id = sac.pitch_id
LEFT JOIN pitcher_arsenal_rank par ON bf.pitcher_id = par.pitcher_id
WHERE ef.pitch_id = bf.pitch_id;

-- Create additional indexes for new features
CREATE INDEX IF NOT EXISTS idx_eng_feat_spin_bucket 
ON features_pitch.engineered_features(spin_rate_percentile) 
WHERE spin_rate_percentile IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_eng_feat_pressure 
ON features_pitch.engineered_features(pa_pressure_index) 
WHERE is_high_pressure_pa = TRUE;

CREATE INDEX IF NOT EXISTS idx_eng_feat_platoon 
ON features_pitch.engineered_features(is_same_handed_matchup, is_platoon_advantage_pitcher);

-- Add table comments
COMMENT ON COLUMN features_pitch.engineered_features.velocity_change_from_prev IS 
    'Velocity difference from previous pitch in same PA (tunneling metric)';
COMMENT ON COLUMN features_pitch.engineered_features.spin_rate_percentile IS 
    'Percentile ranking of spin rate relative to all pitches';
COMMENT ON COLUMN features_pitch.engineered_features.is_same_handed_matchup IS 
    'True if batter and pitcher have same handedness (R vs R or L vs L)';
COMMENT ON COLUMN features_pitch.engineered_features.pitcher_fatigue_score IS 
    'Normalized pitch count in game (0=first pitch, 1=last pitch)';
COMMENT ON COLUMN features_pitch.engineered_features.pa_pressure_index IS 
    'Composite pressure metric (runners + outs + score + inning)';
COMMENT ON COLUMN features_pitch.engineered_features.is_walk_off_situation IS 
    'True if potential walk-off scenario (9th+, close, late in PA)';

-- Verify new features
SELECT 
    'Additional features added successfully' as status,
    COUNT(*) as total_rows,
    COUNT(velocity_change_from_prev) as with_velocity_change,
    COUNT(spin_rate_percentile) as with_spin_percentile,
    COUNT(is_same_handed_matchup) as with_platoon_data,
    COUNT(pitcher_fatigue_score) as with_fatigue,
    COUNT(pa_pressure_index) as with_pressure_index,
    ROUND(AVG(CASE WHEN is_ace_pitcher THEN 1 ELSE 0 END) * 100, 2) as ace_pitcher_pct
FROM features_pitch.engineered_features;
