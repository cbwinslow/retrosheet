-- Phase 2 Feature Mart: Momentum & Streak Features
-- Rolling window metrics for team and player recent performance

CREATE MATERIALIZED VIEW features.team_momentum_features AS
WITH team_game_results AS (
    SELECT
        game_id,
        game_date,
        home_team_id AS team_id,
        CASE WHEN home_score > away_score THEN 1 ELSE 0 END AS win,
        home_score AS runs_scored,
        away_score AS runs_allowed
    FROM core.games
    UNION ALL
    SELECT
        game_id,
        game_date,
        away_team_id AS team_id,
        CASE WHEN away_score > home_score THEN 1 ELSE 0 END AS win,
        away_score AS runs_scored,
        home_score AS runs_allowed
    FROM core.games
),
team_rolling_stats AS (
    SELECT
        game_id,
        team_id,
        game_date,
        -- Rolling window metrics
        AVG(win) OVER last_5 AS team_last_5_win_rate,
        AVG(win) OVER last_10 AS team_last_10_win_rate,
        AVG(runs_scored) OVER last_3 AS team_last_3_runs_scored_avg,
        AVG(runs_allowed) OVER last_3 AS team_last_3_runs_allowed_avg,
        -- Streak calculation
        SUM(win) OVER last_30 AS last_30_wins,
        ROW_NUMBER() OVER (PARTITION BY team_id ORDER BY game_date DESC) AS game_rank
    FROM team_game_results
    WINDOW
        last_3 AS (PARTITION BY team_id ORDER BY game_date ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING),
        last_5 AS (PARTITION BY team_id ORDER BY game_date ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING),
        last_10 AS (PARTITION BY team_id ORDER BY game_date ROWS BETWEEN 10 PRECEDING AND 1 PRECEDING),
        last_30 AS (PARTITION BY team_id ORDER BY game_date ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING)
)
SELECT
    game_id,
    team_id,
    ROUND(team_last_5_win_rate::numeric, 4) AS team_last_5_win_rate,
    ROUND(team_last_10_win_rate::numeric, 4) AS team_last_10_win_rate,
    ROUND(team_last_3_runs_scored_avg::numeric, 2) AS team_last_3_runs_scored_avg,
    ROUND(team_last_3_runs_allowed_avg::numeric, 2) AS team_last_3_runs_allowed_avg,
    ROUND((team_last_10_win_rate - AVG(team_last_10_win_rate) OVER (PARTITION BY team_id ORDER BY game_date ROWS BETWEEN 30 PRECEDING AND 10 PRECEDING))::numeric, 4) AS team_momentum_delta
FROM team_rolling_stats
WITH DATA;

CREATE UNIQUE INDEX idx_team_momentum_game_team ON features.team_momentum_features (game_id, team_id);
CREATE INDEX idx_team_momentum_game ON features.team_momentum_features (game_id);

ANALYZE features.team_momentum_features;
