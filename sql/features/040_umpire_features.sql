-- Phase 2 Feature Mart: Umpire Strike Zone Tendency Features
-- Umpire specific strike zone characteristics and consistency metrics

CREATE MATERIALIZED VIEW features.umpire_strike_zone_features AS
WITH umpire_stats AS (
    SELECT
        umpire,
        game_year AS season,
        COUNT(*) AS total_pitches,
        -- Strike zone characteristics
        COUNT(CASE WHEN description LIKE '%called strike%' THEN 1 END) AS called_strike_count,
        COUNT(CASE WHEN description LIKE '%ball%' THEN 1 END) AS called_ball_count,
        -- Call rates
        ROUND(COUNT(CASE WHEN description LIKE '%called strike%' THEN 1 END)::numeric / NULLIF(COUNT(CASE WHEN description IN ('ball', 'called_strike') THEN 1 END), 0)::numeric, 4) AS called_strike_rate,
        -- Zone location metrics
        AVG(sz_top) AS avg_strike_zone_top,
        AVG(sz_bot) AS avg_strike_zone_bottom,
        STDDEV(sz_top) AS strike_zone_variance_top,
        STDDEV(sz_bot) AS strike_zone_variance_bottom,
        -- Consistency score
        1.0 - (STDDEV(sz_top) + STDDEV(sz_bot)) / 2.0 AS umpire_consistency_score,
        -- Strikeout / walk tendencies
        COUNT(CASE WHEN events = 'strikeout' THEN 1 END) AS strikeout_count,
        COUNT(CASE WHEN events = 'walk' THEN 1 END) AS walk_count,
        ROUND(COUNT(CASE WHEN events = 'strikeout' THEN 1 END)::numeric / NULLIF(COUNT(DISTINCT game_pk), 0)::numeric, 2) AS strikeouts_per_game,
        ROUND(COUNT(CASE WHEN events = 'walk' THEN 1 END)::numeric / NULLIF(COUNT(DISTINCT game_pk), 0)::numeric, 2) AS walks_per_game
    FROM raw_mlb.statcast
    WHERE
        umpire IS NOT NULL
        AND description IS NOT NULL
        AND game_year IS NOT NULL
    GROUP BY umpire, game_year
)

SELECT
    umpire AS umpire_id,
    season,
    total_pitches,
    called_strike_rate,
    avg_strike_zone_top,
    avg_strike_zone_bottom,
    strike_zone_variance_top,
    strike_zone_variance_bottom,
    strikeouts_per_game,
    walks_per_game,
    season + 1 AS feature_season,
    ROUND(umpire_consistency_score::numeric, 4) AS umpire_consistency_score,
    -- Umpire bias flags
    CASE WHEN strikeouts_per_game > 6.5 THEN 1 ELSE 0 END AS umpire_k_friendly,
    CASE WHEN walks_per_game > 3.5 THEN 1 ELSE 0 END AS umpire_walk_friendly,
    CASE WHEN called_strike_rate > 0.34 THEN 1 ELSE 0 END AS umpire_pitcher_favored,
    CASE WHEN called_strike_rate < 0.30 THEN 1 ELSE 0 END AS umpire_hitter_favored
FROM umpire_stats
WHERE total_pitches >= 1000
WITH DATA;

CREATE UNIQUE INDEX idx_umpire_features_season ON features.umpire_strike_zone_features (umpire_id, feature_season);
CREATE INDEX idx_umpire_features_season ON features.umpire_strike_zone_features (feature_season);

ANALYZE features.umpire_strike_zone_features;
