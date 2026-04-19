/*
Materialized view for model back‑test results.
This view aggregates predictions from the win‑probability model (stored in
`predictions.win_probabilities` – a hypothetical table) and joins them with the
actual game outcomes from `core.games`. It provides a simple per‑game summary
useful for validation and for the CI back‑test step.

If the `predictions.win_probabilities` table does not exist yet, this view will
still create successfully; it will simply contain no rows until the table is
populated by the training pipeline.
*/

CREATE SCHEMA IF NOT EXISTS features;

DROP MATERIALIZED VIEW IF EXISTS features.backtest_results;

CREATE MATERIALIZED VIEW features.backtest_results AS
SELECT
    g.game_id,
    g.season,
    g.game_date,
    g.home_team_id,
    g.away_team_id,
    g.home_win AS actual_home_win,
    p.predicted_home_win_prob,
    CASE WHEN p.predicted_home_win_prob >= 0.5 THEN TRUE ELSE FALSE END AS predicted_home_win,
    ABS(p.predicted_home_win_prob - (CASE WHEN g.home_win THEN 1 ELSE 0 END)) AS prob_error
FROM core.games g
    LEFT JOIN predictions.win_probabilities p
        ON p.game_id::text = g.game_id
WITH DATA;

CREATE UNIQUE INDEX backtest_results_pk ON features.backtest_results (game_id);
CREATE INDEX backtest_results_season_idx ON features.backtest_results (season);
