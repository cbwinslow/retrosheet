-- File: sql/features/010_pitcher_arsenal_features.sql
-- Purpose: Create pitcher arsenal features materialized view
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE MATERIALIZED VIEW features.pitcher_arsenal_features AS
WITH pitch_stats AS (
    SELECT
        pitcher,
        game_year AS season,
        COUNT(*) AS total_pitches,
        -- Pitch type distribution
        COUNT(CASE WHEN pitch_type IN ('FF', 'FT', 'FC', 'SI', 'FS') THEN 1 END) AS fastball_count,
        COUNT(CASE WHEN pitch_type IN ('SL', 'CU', 'KC', 'SC') THEN 1 END) AS breaking_count,
        COUNT(CASE WHEN pitch_type IN ('CH', 'FS', 'FO') THEN 1 END) AS offspeed_count,
        -- Velocity metrics
        PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY release_speed) AS fb_velocity_90th,
        AVG(release_speed) AS avg_release_speed,
        STDDEV(release_speed) AS velocity_stddev,
        -- Spin metrics
        AVG(release_spin_rate) AS avg_spin_rate,
        AVG(spin_axis) AS avg_spin_axis,
        -- Release point
        AVG(release_extension) AS avg_release_extension,
        AVG(release_pos_x) AS avg_release_x,
        AVG(release_pos_z) AS avg_release_z
    FROM raw_mlb.statcast
    WHERE
        pitcher IS NOT NULL
        AND game_date IS NOT NULL
        AND pitch_type IS NOT NULL
    GROUP BY pitcher, game_year
)

SELECT
    pitcher AS pitcher_id,
    season,
    total_pitches AS pitcher_sample_pitches,
    -- Arsenal distribution percentages
    season + 1 AS feature_season,
    ROUND((fastball_count::numeric / NULLIF(total_pitches, 0))::numeric, 4) AS pitcher_fastball_pct,
    ROUND((breaking_count::numeric / NULLIF(total_pitches, 0))::numeric, 4) AS pitcher_breaking_pct,
    -- Velocity metrics
    ROUND((offspeed_count::numeric / NULLIF(total_pitches, 0))::numeric, 4) AS pitcher_offspeed_pct,
    ROUND(fb_velocity_90th::numeric, 2) AS pitcher_fb_velocity_90th,
    ROUND(avg_release_speed::numeric, 2) AS pitcher_avg_velocity,
    -- Spin metrics
    ROUND(velocity_stddev::numeric, 3) AS pitcher_velocity_consistency,
    ROUND(avg_spin_rate::numeric, 1) AS pitcher_spin_rate_avg,
    -- Release point
    ROUND(avg_spin_axis::numeric, 1) AS pitcher_spin_axis_avg,
    ROUND(avg_release_extension::numeric, 2) AS pitcher_release_extension,
    ROUND(avg_release_x::numeric, 3) AS pitcher_release_x,
    -- Sample size
    ROUND(avg_release_z::numeric, 3) AS pitcher_release_z
FROM pitch_stats
WHERE total_pitches >= 100
WITH DATA;

CREATE UNIQUE INDEX idx_pitcher_arsenal_season ON features.pitcher_arsenal_features (pitcher_id, feature_season);
CREATE INDEX idx_pitcher_arsenal_season_feature ON features.pitcher_arsenal_features (feature_season);

ANALYZE features.pitcher_arsenal_features;

