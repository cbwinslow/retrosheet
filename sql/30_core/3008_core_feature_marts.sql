-- File: sql/core/050_feature_marts.sql
-- Purpose: Create prior-season rate feature marts for batters, pitchers, teams, PA
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS features;

DROP MATERIALIZED VIEW IF EXISTS features.pa_context_prior_season_rates CASCADE;
DROP MATERIALIZED VIEW IF EXISTS features.team_prior_season_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS features.pitcher_prior_season_pa_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS features.batter_prior_season_pa_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS features.half_inning_outcome_summary CASCADE;

CREATE MATERIALIZED VIEW features.batter_prior_season_pa_summary AS
SELECT
    batter_id,
    COUNT(*)::integer AS prior_pa,
    COUNT(*) FILTER (WHERE is_at_bat)::integer AS prior_at_bats,
    COUNT(*) FILTER (WHERE is_hit)::integer AS prior_hits,
    COUNT(*) FILTER (WHERE is_walk)::integer AS prior_walks,
    COUNT(*) FILTER (WHERE is_strikeout)::integer AS prior_strikeouts,
    COUNT(*) FILTER (WHERE is_home_run)::integer AS prior_home_runs,
    COUNT(*) FILTER (WHERE is_extra_base_hit)::integer AS prior_extra_base_hits,
    season + 1 AS feature_season,
    ROUND(AVG(is_hit::integer)::numeric, 4) AS prior_hit_rate,
    ROUND(AVG(is_walk::integer)::numeric, 4) AS prior_walk_rate,
    ROUND(AVG(is_strikeout::integer)::numeric, 4) AS prior_strikeout_rate,
    ROUND(AVG(is_home_run::integer)::numeric, 4) AS prior_home_run_rate,
    ROUND(AVG(is_reach_base::integer)::numeric, 4) AS prior_reach_base_rate,
    ROUND(AVG(is_extra_base_hit::integer)::numeric, 4) AS prior_extra_base_hit_rate
FROM features.plate_appearance_examples
WHERE batter_id IS NOT NULL
GROUP BY season, batter_id
WITH DATA;

CREATE UNIQUE INDEX batter_prior_season_pa_summary_pk
ON features.batter_prior_season_pa_summary (feature_season, batter_id);
CREATE INDEX batter_prior_season_pa_summary_pa_idx
ON features.batter_prior_season_pa_summary (prior_pa DESC);

CREATE MATERIALIZED VIEW features.pitcher_prior_season_pa_summary AS
SELECT
    pitcher_id,
    COUNT(*)::integer AS prior_batters_faced,
    COUNT(*) FILTER (WHERE is_hit)::integer AS prior_hits_allowed,
    COUNT(*) FILTER (WHERE is_walk)::integer AS prior_walks_allowed,
    COUNT(*) FILTER (WHERE is_strikeout)::integer AS prior_strikeouts,
    COUNT(*) FILTER (WHERE is_home_run)::integer AS prior_home_runs_allowed,
    COUNT(*) FILTER (WHERE is_extra_base_hit)::integer AS prior_extra_base_hits_allowed,
    season + 1 AS feature_season,
    ROUND(AVG(is_hit::integer)::numeric, 4) AS prior_hit_allowed_rate,
    ROUND(AVG(is_walk::integer)::numeric, 4) AS prior_walk_allowed_rate,
    ROUND(AVG(is_strikeout::integer)::numeric, 4) AS prior_strikeout_rate,
    ROUND(AVG(is_home_run::integer)::numeric, 4) AS prior_home_run_allowed_rate,
    ROUND(AVG(is_reach_base::integer)::numeric, 4) AS prior_reach_base_allowed_rate,
    ROUND(AVG(is_extra_base_hit::integer)::numeric, 4) AS prior_extra_base_hit_allowed_rate
FROM features.plate_appearance_examples
WHERE pitcher_id IS NOT NULL
GROUP BY season, pitcher_id
WITH DATA;

CREATE UNIQUE INDEX pitcher_prior_season_pa_summary_pk
ON features.pitcher_prior_season_pa_summary (feature_season, pitcher_id);
CREATE INDEX pitcher_prior_season_pa_summary_bf_idx
ON features.pitcher_prior_season_pa_summary (prior_batters_faced DESC);

CREATE MATERIALIZED VIEW features.team_prior_season_summary AS
WITH team_games AS (
    SELECT
        season,
        home_team_id AS team_id,
        COUNT(*)::integer AS games,
        COUNT(*) FILTER (WHERE home_win)::integer AS wins,
        SUM(home_score)::integer AS runs_scored,
        SUM(away_score)::integer AS runs_allowed
    FROM core.games
    GROUP BY season, home_team_id
    UNION ALL
    SELECT
        season,
        away_team_id AS team_id,
        COUNT(*)::integer AS games,
        COUNT(*) FILTER (WHERE NOT home_win)::integer AS wins,
        SUM(away_score)::integer AS runs_scored,
        SUM(home_score)::integer AS runs_allowed
    FROM core.games
    GROUP BY season, away_team_id
)

SELECT
    team_id,
    SUM(games)::integer AS prior_games,
    SUM(wins)::integer AS prior_wins,
    SUM(runs_scored)::integer AS prior_runs_scored,
    SUM(runs_allowed)::integer AS prior_runs_allowed,
    season + 1 AS feature_season,
    ROUND((SUM(wins)::numeric / NULLIF(SUM(games), 0)), 4) AS prior_win_rate,
    ROUND((SUM(runs_scored)::numeric / NULLIF(SUM(games), 0)), 3) AS prior_runs_scored_per_game,
    ROUND((SUM(runs_allowed)::numeric / NULLIF(SUM(games), 0)), 3) AS prior_runs_allowed_per_game
FROM team_games
GROUP BY season, team_id
WITH DATA;

CREATE UNIQUE INDEX team_prior_season_summary_pk
ON features.team_prior_season_summary (feature_season, team_id);

CREATE MATERIALIZED VIEW features.pa_context_prior_season_rates AS
SELECT
    batter_hand,
    pitcher_hand,
    inning,
    is_bottom_inning,
    outs_before,
    start_bases,
    balls,
    strikes,
    COUNT(*)::integer AS prior_pa,
    season + 1 AS feature_season,
    ROUND(AVG(is_hit::integer)::numeric, 4) AS prior_hit_rate,
    ROUND(AVG(is_walk::integer)::numeric, 4) AS prior_walk_rate,
    ROUND(AVG(is_strikeout::integer)::numeric, 4) AS prior_strikeout_rate,
    ROUND(AVG(is_home_run::integer)::numeric, 4) AS prior_home_run_rate,
    ROUND(AVG(is_reach_base::integer)::numeric, 4) AS prior_reach_base_rate,
    ROUND(AVG(is_extra_base_hit::integer)::numeric, 4) AS prior_extra_base_hit_rate,
    ROUND(AVG(final_batting_team_win::integer)::numeric, 4) AS prior_batting_team_win_rate
FROM features.plate_appearance_examples
GROUP BY
    season,
    batter_hand,
    pitcher_hand,
    inning,
    is_bottom_inning,
    outs_before,
    start_bases,
    balls,
    strikes
WITH DATA;

CREATE UNIQUE INDEX pa_context_prior_season_rates_pk
ON features.pa_context_prior_season_rates (
    feature_season,
    batter_hand,
    pitcher_hand,
    inning,
    is_bottom_inning,
    outs_before,
    start_bases,
    balls,
    strikes
);
CREATE INDEX pa_context_prior_season_rates_volume_idx
ON features.pa_context_prior_season_rates (feature_season, prior_pa DESC);

CREATE MATERIALIZED VIEW features.half_inning_outcome_summary AS
SELECT
    game_id,
    season,
    game_date,
    inning,
    is_bottom_inning,
    COUNT(*)::integer AS plate_appearances,
    COUNT(*) FILTER (WHERE is_hit)::integer AS hits,
    COUNT(*) FILTER (WHERE is_walk)::integer AS walks,
    COUNT(*) FILTER (WHERE is_strikeout)::integer AS strikeouts,
    COUNT(*) FILTER (WHERE is_home_run)::integer AS home_runs,
    SUM(runs_on_play)::integer AS runs_scored,
    COUNT(*) FILTER (WHERE batter_hand = 'L')::integer AS left_handed_pa,
    COUNT(*) FILTER (WHERE batter_hand = 'L' AND is_hit)::integer AS left_handed_hits,
    CASE WHEN is_bottom_inning THEN home_team_id ELSE away_team_id END AS batting_team_id,
    CASE WHEN is_bottom_inning THEN away_team_id ELSE home_team_id END AS fielding_team_id,
    BOOL_OR(is_hit AND batter_hand = 'L') AS any_left_handed_hit,
    (
        COUNT(*) FILTER (WHERE batter_hand = 'L') > 0
        AND COUNT(*) FILTER (WHERE batter_hand = 'L')
        = COUNT(*) FILTER (WHERE batter_hand = 'L' AND is_hit)
    ) AS all_left_handed_batters_hit
FROM core.plate_appearances
GROUP BY
    game_id,
    season,
    game_date,
    inning,
    is_bottom_inning,
    home_team_id,
    away_team_id
WITH DATA;

CREATE UNIQUE INDEX half_inning_outcome_summary_pk
ON features.half_inning_outcome_summary (game_id, inning, is_bottom_inning);
CREATE INDEX half_inning_outcome_summary_scenario_idx
ON features.half_inning_outcome_summary (
    season,
    batting_team_id,
    fielding_team_id,
    all_left_handed_batters_hit
);

CREATE INDEX IF NOT EXISTS season_schedules_matchup_idx
ON raw_retrosheet.season_schedules (season, visitor_team_id, home_team_id);
CREATE INDEX IF NOT EXISTS season_schedules_park_idx
ON raw_retrosheet.season_schedules (park_id, season) WHERE park_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ejections_ejectee_idx
ON raw_retrosheet.ejections (ejectee_id) WHERE ejectee_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ejections_umpire_idx
ON raw_retrosheet.ejections (umpire_id) WHERE umpire_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS season_umpires_umpire_idx
ON raw_retrosheet.season_umpires (umpire_id, season);

CREATE OR REPLACE VIEW features.feature_mart_validation_summary AS
SELECT
    'features.batter_prior_season_pa_summary' AS object_name,
    COUNT(*) AS row_count
FROM features.batter_prior_season_pa_summary
UNION ALL
SELECT
    'features.pitcher_prior_season_pa_summary',
    COUNT(*)
FROM features.pitcher_prior_season_pa_summary
UNION ALL
SELECT
    'features.team_prior_season_summary',
    COUNT(*)
FROM features.team_prior_season_summary
UNION ALL
SELECT
    'features.pa_context_prior_season_rates',
    COUNT(*)
FROM features.pa_context_prior_season_rates
UNION ALL
SELECT
    'features.half_inning_outcome_summary',
    COUNT(*)
FROM features.half_inning_outcome_summary;
