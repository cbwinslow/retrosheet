-- File: sql/features/070_stadium_physics_features.sql
-- Purpose: Park factors and per-stadium scoring averages
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE MATERIALIZED VIEW features.stadium_physics_features AS
WITH park_stats AS (
    SELECT
        park_id,
        season,
        COUNT(*) AS total_games,
        AVG(home_score + away_score) AS avg_total_runs_per_game,
        AVG(home_score) AS avg_home_runs,
        AVG(away_score) AS avg_away_runs,
        AVG(away_hits + home_hits) AS avg_total_hits,
        AVG(away_errors + home_errors) AS avg_total_errors,
        -- Park factors
        (AVG(
            home_score + away_score) / (
            SELECT AVG(home_score + away_score) FROM core.games
            WHERE season = g.season
        )) AS park_run_factor
    FROM core.games AS g
    WHERE
        park_id IS NOT NULL
        AND season IS NOT NULL
    GROUP BY park_id, season
)

SELECT
    park_id,
    season,
    total_games,
    season + 1 AS feature_season,
    ROUND(avg_total_runs_per_game::numeric, 2) AS avg_total_runs_per_game,
    ROUND(park_run_factor::numeric, 4) AS park_run_factor,
    -- Park effect flags
    CASE WHEN park_run_factor > 1.05 THEN 1.0 ELSE 0.0 END AS park_hitter_friendly,
    CASE WHEN park_run_factor < 0.95 THEN 1.0 ELSE 0.0 END AS park_pitcher_friendly,
    CASE WHEN park_run_factor > 1.10 THEN 1.0 ELSE 0.0 END AS park_extreme_hitter
FROM park_stats
WITH DATA;

CREATE UNIQUE INDEX idx_stadium_park_season ON features.stadium_physics_features (park_id, feature_season);
CREATE INDEX idx_stadium_season ON features.stadium_physics_features (feature_season);

ANALYZE features.stadium_physics_features;

