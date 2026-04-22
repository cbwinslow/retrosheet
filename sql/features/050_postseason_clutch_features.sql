-- Phase 2 Feature Mart: Postseason & Clutch Metrics
-- Postseason, elimination game, and high leverage situation flags

CREATE MATERIALIZED VIEW features.postseason_clutch_features AS
SELECT
    game_id,
    home_team_id,
    away_team_id,
    season,
    -- Game type flags
    CASE WHEN source_type = 'postseason' THEN 1 ELSE 0 END AS is_postseason,
    CASE WHEN source_type = 'spring' THEN 1 ELSE 0 END AS is_spring_training,
    -- In-game leverage context
    CASE 
        WHEN innings >= 7 AND ABS(home_score - away_score) <= 3 THEN 1 
        ELSE 0 
    END AS is_high_leverage_situation,
    -- Game context flags
    CASE WHEN day_of_week IN ('5', '6', '7') THEN 1 ELSE 0 END AS is_weekend_game,
    CASE WHEN doubleheader_flag != '0' THEN 1 ELSE 0 END AS is_doubleheader
FROM core.games
WITH DATA;

CREATE UNIQUE INDEX idx_postseason_game ON features.postseason_clutch_features (game_id);

ANALYZE features.postseason_clutch_features;
