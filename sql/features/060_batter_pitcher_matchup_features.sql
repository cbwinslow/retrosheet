-- File: sql/features/060_batter_pitcher_matchup_features.sql
-- Purpose: Batter-pitcher matchup rates and contact quality features
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE MATERIALIZED VIEW features.batter_pitcher_matchup_features AS
WITH historical_matchups AS (
    SELECT
        batter AS batter_id,
        pitcher AS pitcher_id,
        EXTRACT(YEAR FROM game_date::date) AS season,
        COUNT(*) AS total_matchup_pa,
        -- Outcome rates
        COUNT(CASE WHEN events LIKE '%hit%' OR events LIKE '%single%' OR events LIKE '%double%' OR events LIKE '%triple%' OR events LIKE '%home_run%' THEN 1 END) AS hits,
        COUNT(CASE WHEN events IN ('strikeout', 'strikeout_double_play') THEN 1 END) AS strikeouts,
        COUNT(CASE WHEN events IN ('walk', 'intent_walk', 'hit_by_pitch') THEN 1 END) AS walks,
        COUNT(CASE WHEN events = 'home_run' THEN 1 END) AS home_runs,
        -- Quality of contact
        AVG(launch_speed) FILTER (WHERE launch_speed IS NOT NULL) AS avg_launch_speed,
        AVG(launch_angle) FILTER (WHERE launch_angle IS NOT NULL) AS avg_launch_angle,
        AVG(estimated_ba_using_speedangle) FILTER (WHERE estimated_ba_using_speedangle IS NOT NULL) AS avg_expected_ba
    FROM raw_mlb.statcast
    WHERE
        batter IS NOT NULL
        AND pitcher IS NOT NULL
        AND game_date IS NOT NULL
    GROUP BY batter, pitcher, EXTRACT(YEAR FROM game_date::date)
)

SELECT
    batter_id,
    pitcher_id,
    season,
    total_matchup_pa,
    season + 1 AS feature_season,
    -- Calculated rates
    ROUND((hits::numeric / NULLIF(total_matchup_pa, 0))::numeric, 4) AS matchup_hit_rate,
    ROUND((strikeouts::numeric / NULLIF(total_matchup_pa, 0))::numeric, 4) AS matchup_strikeout_rate,
    ROUND((walks::numeric / NULLIF(total_matchup_pa, 0))::numeric, 4) AS matchup_walk_rate,
    ROUND((home_runs::numeric / NULLIF(total_matchup_pa, 0))::numeric, 4) AS matchup_home_run_rate,
    -- Contact quality
    ROUND(avg_launch_speed::numeric, 1) AS matchup_avg_launch_speed,
    ROUND(avg_launch_angle::numeric, 1) AS matchup_avg_launch_angle,
    ROUND(avg_expected_ba::numeric, 4) AS matchup_expected_ba
FROM historical_matchups
WHERE total_matchup_pa >= 5
WITH DATA;

CREATE UNIQUE INDEX idx_matchup_batter_pitcher_season ON features.batter_pitcher_matchup_features (batter_id, pitcher_id, feature_season);
CREATE INDEX idx_matchup_pitcher_season ON features.batter_pitcher_matchup_features (pitcher_id, feature_season);
CREATE INDEX idx_matchup_batter_season ON features.batter_pitcher_matchup_features (batter_id, feature_season);

ANALYZE features.batter_pitcher_matchup_features;

