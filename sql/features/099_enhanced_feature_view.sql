-- Enhanced Feature View
-- Combines all new Phase 1 features into the existing training set

CREATE OR REPLACE VIEW features.plate_appearance_enhanced_examples AS
SELECT
    pa.*,
    -- Pitcher arsenal features
    ars.pitcher_fastball_pct,
    ars.pitcher_breaking_pct,
    ars.pitcher_offspeed_pct,
    ars.pitcher_fb_velocity_90th,
    ars.pitcher_avg_velocity,
    ars.pitcher_velocity_consistency,
    ars.pitcher_spin_rate_avg,
    ars.pitcher_spin_axis_avg,
    ars.pitcher_release_extension,
    -- Attendance and weather features
    att.temp_extreme_flag,
    att.wind_blowing_out_flag,
    att.wind_blowing_in_flag,
    att.wind_out_speed,
    att.is_night_game,
    att.field_dry_flag,
    att.sky_clear_flag,
    att.sky_cloudy_flag
FROM features.plate_appearance_advanced_examples pa
LEFT JOIN features.pitcher_arsenal_features ars
    ON pa.pitcher_id::bigint = ars.pitcher_id
    AND pa.season = ars.feature_season
LEFT JOIN features.game_attendance_features att
    ON pa.game_id = att.game_pk;
