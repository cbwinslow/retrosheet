-- Phase 1 Feature Mart: Attendance, Crowd, and Weather Features

CREATE MATERIALIZED VIEW features.game_attendance_features AS
WITH game_attendance AS (
    SELECT
        game_id AS game_pk,
        home_team_id,
        season,
        attendance,
        temperature_f,
        wind_speed_mph,
        wind_direction,
        day_night,
        field_condition,
        sky_condition
    FROM core.games
    WHERE attendance IS NOT NULL
)
SELECT
    game_pk,
    home_team_id,
    season,
    season + 1 AS feature_season,
    -- Attendance metrics
    attendance AS game_attendance,
    -- Temperature effects
    CASE
        WHEN temperature_f >= 90 THEN 1.0
        WHEN temperature_f <= 50 THEN 1.0
        ELSE 0.0
    END AS temp_extreme_flag,
    -- Wind direction effects
    CASE
        WHEN wind_direction IN ('Out To Center', 'Out To LF', 'Out To RF') THEN 1.0
        ELSE 0.0
    END AS wind_blowing_out_flag,
    CASE
        WHEN wind_direction IN ('In From Center', 'In From LF', 'In From RF') THEN 1.0
        ELSE 0.0
    END AS wind_blowing_in_flag,
    -- Wind speed interaction
    wind_speed_mph * CASE WHEN wind_direction IN ('Out To Center', 'Out To LF', 'Out To RF') THEN 1.0 ELSE 0.0 END AS wind_out_speed,
    -- Game context
    CASE WHEN day_night = 'N' THEN 1 ELSE 0 END AS is_night_game,
    -- Field and sky conditions
    CASE WHEN field_condition = 'Dry' THEN 1 ELSE 0 END AS field_dry_flag,
    CASE WHEN sky_condition = 'Clear' THEN 1 ELSE 0 END AS sky_clear_flag,
    CASE WHEN sky_condition = 'Cloudy' THEN 1 ELSE 0 END AS sky_cloudy_flag
FROM game_attendance
WITH DATA;

CREATE UNIQUE INDEX idx_game_attendance_pk ON features.game_attendance_features (game_pk);
CREATE INDEX idx_game_attendance_season ON features.game_attendance_features (season);

ANALYZE features.game_attendance_features;
