-- Umpire Strike Zone Tendency Features
-- Built from complete Retrosheet data (no Statcast dependency)

CREATE MATERIALIZED VIEW features.umpire_tendency_features AS
WITH umpire_game_stats AS (
    SELECT
        umpire_id,
        game_year AS season,
        COUNT(*) AS total_games,
        SUM(home_score + away_score) AS total_runs,
        SUM(CASE WHEN event_type IN ('K', 'KS') THEN 1 ELSE 0 END) AS strikeouts,
        SUM(CASE WHEN event_type IN ('W', 'IW', 'HP') THEN 1 ELSE 0 END) AS walks,
        SUM(CASE WHEN event_type IN ('HR') THEN 1 ELSE 0 END) AS home_runs
    FROM core.events e
    JOIN core.games g ON e.game_id = g.game_id
    JOIN bridge.umpire_xref ux ON g.home_plate_umpire_id = ux.retrosheet_umpire_id
    WHERE umpire_id IS NOT NULL
    AND game_year IS NOT NULL
    GROUP BY umpire_id, game_year
)
SELECT
    umpire_id,
    season,
    season + 1 AS feature_season,
    total_games,
    -- Umpire tendencies
    ROUND((strikeouts::numeric / NULLIF(total_games, 0))::numeric, 2) AS umpire_strikeouts_per_game,
    ROUND((walks::numeric / NULLIF(total_games, 0))::numeric, 2) AS umpire_walks_per_game,
    ROUND((home_runs::numeric / NULLIF(total_games, 0))::numeric, 2) AS umpire_hr_per_game,
    ROUND((total_runs::numeric / NULLIF(total_games, 0))::numeric, 2) AS umpire_runs_per_game,
    -- Bias flags
    CASE WHEN umpire_strikeouts_per_game > 6.5 THEN 1 ELSE 0 END AS umpire_k_friendly,
    CASE WHEN umpire_walks_per_game > 3.5 THEN 1 ELSE 0 END AS umpire_walk_friendly,
    CASE WHEN umpire_runs_per_game > 9.5 THEN 1 ELSE 0 END AS umpire_hitter_friendly,
    CASE WHEN umpire_runs_per_game < 8.0 THEN 1 ELSE 0 END AS umpire_pitcher_friendly
FROM umpire_game_stats
WHERE total_games >= 10
WITH DATA;

CREATE UNIQUE INDEX idx_umpire_features_season ON features.umpire_tendency_features (umpire_id, feature_season);
CREATE INDEX idx_umpire_features_season_idx ON features.umpire_tendency_features (feature_season);

ANALYZE features.umpire_tendency_features;
