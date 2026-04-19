CREATE SCHEMA IF NOT EXISTS features;

DROP VIEW IF EXISTS features.advanced_feature_mart_validation_summary;
DROP VIEW IF EXISTS features.game_outcome_advanced_examples;
DROP VIEW IF EXISTS features.plate_appearance_advanced_examples;
DROP MATERIALIZED VIEW IF EXISTS features.team_rolling_30_game_summary;
DROP MATERIALIZED VIEW IF EXISTS features.park_prior_season_run_environment;
DROP MATERIALIZED VIEW IF EXISTS features.batter_pitcher_prior_matchup_summary;
DROP MATERIALIZED VIEW IF EXISTS features.pitcher_career_prior_pa_summary;
DROP MATERIALIZED VIEW IF EXISTS features.batter_career_prior_pa_summary;
DROP MATERIALIZED VIEW IF EXISTS features.pa_context_coarse_prior_season_rates;

CREATE MATERIALIZED VIEW features.pa_context_coarse_prior_season_rates AS
SELECT
    season + 1 AS feature_season,
    batter_hand,
    pitcher_hand,
    outs_before,
    start_bases,
    count(*)::integer AS prior_pa,
    round(avg(is_hit::integer)::numeric, 4) AS prior_hit_rate,
    round(avg(is_walk::integer)::numeric, 4) AS prior_walk_rate,
    round(avg(is_strikeout::integer)::numeric, 4) AS prior_strikeout_rate,
    round(avg(is_home_run::integer)::numeric, 4) AS prior_home_run_rate,
    round(avg(is_reach_base::integer)::numeric, 4) AS prior_reach_base_rate,
    round(avg(is_extra_base_hit::integer)::numeric, 4) AS prior_extra_base_hit_rate,
    round(avg(final_batting_team_win::integer)::numeric, 4) AS prior_batting_team_win_rate
FROM features.plate_appearance_examples
GROUP BY
    season,
    batter_hand,
    pitcher_hand,
    outs_before,
    start_bases
WITH DATA;

CREATE UNIQUE INDEX pa_context_coarse_prior_season_rates_pk
    ON features.pa_context_coarse_prior_season_rates (
        feature_season,
        batter_hand,
        pitcher_hand,
        outs_before,
        start_bases
    );
CREATE INDEX pa_context_coarse_prior_season_rates_volume_idx
    ON features.pa_context_coarse_prior_season_rates (feature_season, prior_pa DESC);

CREATE MATERIALIZED VIEW features.batter_career_prior_pa_summary AS
WITH seasons AS (
    SELECT DISTINCT season AS feature_season
    FROM features.plate_appearance_examples
)
SELECT
    seasons.feature_season,
    examples.batter_id,
    count(*)::integer AS career_prior_pa,
    count(*) FILTER (WHERE examples.is_at_bat)::integer AS career_prior_at_bats,
    count(*) FILTER (WHERE examples.is_hit)::integer AS career_prior_hits,
    count(*) FILTER (WHERE examples.is_walk)::integer AS career_prior_walks,
    count(*) FILTER (WHERE examples.is_strikeout)::integer AS career_prior_strikeouts,
    count(*) FILTER (WHERE examples.is_home_run)::integer AS career_prior_home_runs,
    count(*) FILTER (WHERE examples.is_extra_base_hit)::integer AS career_prior_extra_base_hits,
    round(avg(examples.is_hit::integer)::numeric, 4) AS career_prior_hit_rate,
    round(avg(examples.is_walk::integer)::numeric, 4) AS career_prior_walk_rate,
    round(avg(examples.is_strikeout::integer)::numeric, 4) AS career_prior_strikeout_rate,
    round(avg(examples.is_home_run::integer)::numeric, 4) AS career_prior_home_run_rate,
    round(avg(examples.is_reach_base::integer)::numeric, 4) AS career_prior_reach_base_rate,
    round(avg(examples.is_extra_base_hit::integer)::numeric, 4) AS career_prior_extra_base_hit_rate
FROM seasons
JOIN features.plate_appearance_examples examples
  ON examples.season < seasons.feature_season
WHERE examples.batter_id IS NOT NULL
GROUP BY seasons.feature_season, examples.batter_id
WITH DATA;

CREATE UNIQUE INDEX batter_career_prior_pa_summary_pk
    ON features.batter_career_prior_pa_summary (feature_season, batter_id);
CREATE INDEX batter_career_prior_pa_summary_pa_idx
    ON features.batter_career_prior_pa_summary (career_prior_pa DESC);

CREATE MATERIALIZED VIEW features.pitcher_career_prior_pa_summary AS
WITH seasons AS (
    SELECT DISTINCT season AS feature_season
    FROM features.plate_appearance_examples
)
SELECT
    seasons.feature_season,
    examples.pitcher_id,
    count(*)::integer AS career_prior_batters_faced,
    count(*) FILTER (WHERE examples.is_hit)::integer AS career_prior_hits_allowed,
    count(*) FILTER (WHERE examples.is_walk)::integer AS career_prior_walks_allowed,
    count(*) FILTER (WHERE examples.is_strikeout)::integer AS career_prior_strikeouts,
    count(*) FILTER (WHERE examples.is_home_run)::integer AS career_prior_home_runs_allowed,
    count(*) FILTER (WHERE examples.is_extra_base_hit)::integer AS career_prior_extra_base_hits_allowed,
    round(avg(examples.is_hit::integer)::numeric, 4) AS career_prior_hit_allowed_rate,
    round(avg(examples.is_walk::integer)::numeric, 4) AS career_prior_walk_allowed_rate,
    round(avg(examples.is_strikeout::integer)::numeric, 4) AS career_prior_strikeout_rate,
    round(avg(examples.is_home_run::integer)::numeric, 4) AS career_prior_home_run_allowed_rate,
    round(avg(examples.is_reach_base::integer)::numeric, 4) AS career_prior_reach_base_allowed_rate,
    round(avg(examples.is_extra_base_hit::integer)::numeric, 4) AS career_prior_extra_base_hit_allowed_rate
FROM seasons
JOIN features.plate_appearance_examples examples
  ON examples.season < seasons.feature_season
WHERE examples.pitcher_id IS NOT NULL
GROUP BY seasons.feature_season, examples.pitcher_id
WITH DATA;

CREATE UNIQUE INDEX pitcher_career_prior_pa_summary_pk
    ON features.pitcher_career_prior_pa_summary (feature_season, pitcher_id);
CREATE INDEX pitcher_career_prior_pa_summary_bf_idx
    ON features.pitcher_career_prior_pa_summary (career_prior_batters_faced DESC);

CREATE MATERIALIZED VIEW features.batter_pitcher_prior_matchup_summary AS
SELECT
    season + 1 AS feature_season,
    batter_id,
    pitcher_id,
    count(*)::integer AS prior_matchup_pa,
    count(*) FILTER (WHERE is_hit)::integer AS prior_matchup_hits,
    count(*) FILTER (WHERE is_walk)::integer AS prior_matchup_walks,
    count(*) FILTER (WHERE is_strikeout)::integer AS prior_matchup_strikeouts,
    count(*) FILTER (WHERE is_home_run)::integer AS prior_matchup_home_runs,
    round(avg(is_hit::integer)::numeric, 4) AS prior_matchup_hit_rate,
    round(avg(is_walk::integer)::numeric, 4) AS prior_matchup_walk_rate,
    round(avg(is_strikeout::integer)::numeric, 4) AS prior_matchup_strikeout_rate,
    round(avg(is_home_run::integer)::numeric, 4) AS prior_matchup_home_run_rate,
    round(avg(is_reach_base::integer)::numeric, 4) AS prior_matchup_reach_base_rate
FROM features.plate_appearance_examples
WHERE batter_id IS NOT NULL
  AND pitcher_id IS NOT NULL
GROUP BY season, batter_id, pitcher_id
HAVING count(*) >= 2
WITH DATA;

CREATE UNIQUE INDEX batter_pitcher_prior_matchup_summary_pk
    ON features.batter_pitcher_prior_matchup_summary (feature_season, batter_id, pitcher_id);
CREATE INDEX batter_pitcher_prior_matchup_summary_volume_idx
    ON features.batter_pitcher_prior_matchup_summary (feature_season, prior_matchup_pa DESC);

CREATE MATERIALIZED VIEW features.park_prior_season_run_environment AS
SELECT
    games.season + 1 AS feature_season,
    games.park_id,
    count(*)::integer AS prior_games,
    round(avg((games.home_score + games.away_score)::numeric), 3) AS prior_total_runs_per_game,
    round(avg(games.home_score::numeric), 3) AS prior_home_runs_per_game,
    round(avg(games.away_score::numeric), 3) AS prior_away_runs_per_game,
    round(avg(games.home_win::integer)::numeric, 4) AS prior_home_win_rate,
    round(avg(COALESCE(games.temperature_f, 70))::numeric, 2) AS prior_avg_temperature_f
FROM core.games games
WHERE games.park_id IS NOT NULL
GROUP BY games.season, games.park_id
WITH DATA;

CREATE UNIQUE INDEX park_prior_season_run_environment_pk
    ON features.park_prior_season_run_environment (feature_season, park_id);
CREATE INDEX park_prior_season_run_environment_runs_idx
    ON features.park_prior_season_run_environment (feature_season, prior_total_runs_per_game DESC);

CREATE MATERIALIZED VIEW features.team_rolling_30_game_summary AS
WITH team_games AS (
    SELECT
        game_id,
        season,
        game_date,
        home_team_id AS team_id,
        away_team_id AS opponent_team_id,
        true AS is_home_team,
        home_win AS won,
        home_score AS runs_scored,
        away_score AS runs_allowed
    FROM core.games
    UNION ALL
    SELECT
        game_id,
        season,
        game_date,
        away_team_id AS team_id,
        home_team_id AS opponent_team_id,
        false AS is_home_team,
        NOT home_win AS won,
        away_score AS runs_scored,
        home_score AS runs_allowed
    FROM core.games
),
rolling AS (
    SELECT
        team_games.*,
        count(*) OVER prior_games AS rolling_30_games,
        sum(won::integer) OVER prior_games AS rolling_30_wins,
        avg(won::integer) OVER prior_games AS rolling_30_win_rate,
        avg(runs_scored) OVER prior_games AS rolling_30_runs_scored_per_game,
        avg(runs_allowed) OVER prior_games AS rolling_30_runs_allowed_per_game
    FROM team_games
    WINDOW prior_games AS (
        PARTITION BY team_id
        ORDER BY game_date, game_id
        ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
    )
)
SELECT
    game_id,
    season,
    game_date,
    team_id,
    opponent_team_id,
    is_home_team,
    COALESCE(rolling_30_games, 0)::integer AS rolling_30_games,
    COALESCE(rolling_30_wins, 0)::integer AS rolling_30_wins,
    round(rolling_30_win_rate::numeric, 4) AS rolling_30_win_rate,
    round(rolling_30_runs_scored_per_game::numeric, 3) AS rolling_30_runs_scored_per_game,
    round(rolling_30_runs_allowed_per_game::numeric, 3) AS rolling_30_runs_allowed_per_game
FROM rolling
WITH DATA;

CREATE UNIQUE INDEX team_rolling_30_game_summary_pk
    ON features.team_rolling_30_game_summary (game_id, team_id);
CREATE INDEX team_rolling_30_game_summary_team_date_idx
    ON features.team_rolling_30_game_summary (team_id, game_date);

CREATE OR REPLACE VIEW features.plate_appearance_advanced_examples AS
SELECT
    examples.*,
    games.park_id,
    batter_career.career_prior_pa AS batter_career_prior_pa,
    batter_career.career_prior_hit_rate AS batter_career_prior_hit_rate,
    batter_career.career_prior_walk_rate AS batter_career_prior_walk_rate,
    batter_career.career_prior_strikeout_rate AS batter_career_prior_strikeout_rate,
    batter_career.career_prior_home_run_rate AS batter_career_prior_home_run_rate,
    batter_career.career_prior_reach_base_rate AS batter_career_prior_reach_base_rate,
    pitcher_career.career_prior_batters_faced AS pitcher_career_prior_batters_faced,
    pitcher_career.career_prior_hit_allowed_rate AS pitcher_career_prior_hit_allowed_rate,
    pitcher_career.career_prior_walk_allowed_rate AS pitcher_career_prior_walk_allowed_rate,
    pitcher_career.career_prior_strikeout_rate AS pitcher_career_prior_strikeout_rate,
    pitcher_career.career_prior_home_run_allowed_rate AS pitcher_career_prior_home_run_allowed_rate,
    pitcher_career.career_prior_reach_base_allowed_rate AS pitcher_career_prior_reach_base_allowed_rate,
    matchup.prior_matchup_pa,
    matchup.prior_matchup_hit_rate,
    matchup.prior_matchup_walk_rate,
    matchup.prior_matchup_strikeout_rate,
    matchup.prior_matchup_home_run_rate,
    matchup.prior_matchup_reach_base_rate,
    coarse_context.prior_pa AS coarse_context_prior_pa,
    coarse_context.prior_hit_rate AS coarse_context_prior_hit_rate,
    coarse_context.prior_walk_rate AS coarse_context_prior_walk_rate,
    coarse_context.prior_strikeout_rate AS coarse_context_prior_strikeout_rate,
    coarse_context.prior_home_run_rate AS coarse_context_prior_home_run_rate,
    coarse_context.prior_reach_base_rate AS coarse_context_prior_reach_base_rate,
    coarse_context.prior_extra_base_hit_rate AS coarse_context_prior_extra_base_hit_rate,
    park.prior_total_runs_per_game AS park_prior_total_runs_per_game,
    park.prior_home_win_rate AS park_prior_home_win_rate,
    batting_form.rolling_30_games AS batting_team_rolling_30_games,
    batting_form.rolling_30_win_rate AS batting_team_rolling_30_win_rate,
    batting_form.rolling_30_runs_scored_per_game AS batting_team_rolling_30_runs_scored_per_game,
    batting_form.rolling_30_runs_allowed_per_game AS batting_team_rolling_30_runs_allowed_per_game,
    fielding_form.rolling_30_games AS fielding_team_rolling_30_games,
    fielding_form.rolling_30_win_rate AS fielding_team_rolling_30_win_rate,
    fielding_form.rolling_30_runs_scored_per_game AS fielding_team_rolling_30_runs_scored_per_game,
    fielding_form.rolling_30_runs_allowed_per_game AS fielding_team_rolling_30_runs_allowed_per_game
FROM features.plate_appearance_examples examples
JOIN core.games games
  ON games.game_id = examples.game_id
LEFT JOIN features.batter_career_prior_pa_summary batter_career
  ON batter_career.feature_season = examples.season
 AND batter_career.batter_id = examples.batter_id
LEFT JOIN features.pitcher_career_prior_pa_summary pitcher_career
  ON pitcher_career.feature_season = examples.season
 AND pitcher_career.pitcher_id = examples.pitcher_id
LEFT JOIN features.batter_pitcher_prior_matchup_summary matchup
  ON matchup.feature_season = examples.season
 AND matchup.batter_id = examples.batter_id
 AND matchup.pitcher_id = examples.pitcher_id
LEFT JOIN features.pa_context_coarse_prior_season_rates coarse_context
  ON coarse_context.feature_season = examples.season
 AND coarse_context.batter_hand = examples.batter_hand
 AND coarse_context.pitcher_hand = examples.pitcher_hand
 AND coarse_context.outs_before = examples.outs_before
 AND coarse_context.start_bases = examples.start_bases
LEFT JOIN features.park_prior_season_run_environment park
  ON park.feature_season = examples.season
 AND park.park_id = games.park_id
LEFT JOIN features.team_rolling_30_game_summary batting_form
  ON batting_form.game_id = examples.game_id
 AND batting_form.team_id = examples.batting_team_id
LEFT JOIN features.team_rolling_30_game_summary fielding_form
  ON fielding_form.game_id = examples.game_id
 AND fielding_form.team_id = examples.fielding_team_id;

CREATE OR REPLACE VIEW features.game_outcome_advanced_examples AS
SELECT
    examples.*,
    games.park_id,
    batter_career.career_prior_pa AS batter_career_prior_pa,
    batter_career.career_prior_hit_rate AS batter_career_prior_hit_rate,
    batter_career.career_prior_walk_rate AS batter_career_prior_walk_rate,
    batter_career.career_prior_strikeout_rate AS batter_career_prior_strikeout_rate,
    batter_career.career_prior_home_run_rate AS batter_career_prior_home_run_rate,
    batter_career.career_prior_reach_base_rate AS batter_career_prior_reach_base_rate,
    pitcher_career.career_prior_batters_faced AS pitcher_career_prior_batters_faced,
    pitcher_career.career_prior_hit_allowed_rate AS pitcher_career_prior_hit_allowed_rate,
    pitcher_career.career_prior_walk_allowed_rate AS pitcher_career_prior_walk_allowed_rate,
    pitcher_career.career_prior_strikeout_rate AS pitcher_career_prior_strikeout_rate,
    pitcher_career.career_prior_home_run_allowed_rate AS pitcher_career_prior_home_run_allowed_rate,
    pitcher_career.career_prior_reach_base_allowed_rate AS pitcher_career_prior_reach_base_allowed_rate,
    matchup.prior_matchup_pa,
    matchup.prior_matchup_hit_rate,
    matchup.prior_matchup_walk_rate,
    matchup.prior_matchup_strikeout_rate,
    matchup.prior_matchup_home_run_rate,
    matchup.prior_matchup_reach_base_rate,
    coarse_context.prior_pa AS coarse_context_prior_pa,
    coarse_context.prior_hit_rate AS coarse_context_prior_hit_rate,
    coarse_context.prior_walk_rate AS coarse_context_prior_walk_rate,
    coarse_context.prior_strikeout_rate AS coarse_context_prior_strikeout_rate,
    coarse_context.prior_home_run_rate AS coarse_context_prior_home_run_rate,
    coarse_context.prior_reach_base_rate AS coarse_context_prior_reach_base_rate,
    coarse_context.prior_extra_base_hit_rate AS coarse_context_prior_extra_base_hit_rate,
    park.prior_total_runs_per_game AS park_prior_total_runs_per_game,
    park.prior_home_win_rate AS park_prior_home_win_rate,
    home_form.rolling_30_games AS home_team_rolling_30_games,
    home_form.rolling_30_win_rate AS home_team_rolling_30_win_rate,
    home_form.rolling_30_runs_scored_per_game AS home_team_rolling_30_runs_scored_per_game,
    home_form.rolling_30_runs_allowed_per_game AS home_team_rolling_30_runs_allowed_per_game,
    away_form.rolling_30_games AS away_team_rolling_30_games,
    away_form.rolling_30_win_rate AS away_team_rolling_30_win_rate,
    away_form.rolling_30_runs_scored_per_game AS away_team_rolling_30_runs_scored_per_game,
    away_form.rolling_30_runs_allowed_per_game AS away_team_rolling_30_runs_allowed_per_game
FROM features.game_outcome_examples examples
JOIN core.games games
  ON games.game_id = examples.game_id
LEFT JOIN features.batter_career_prior_pa_summary batter_career
  ON batter_career.feature_season = examples.season
 AND batter_career.batter_id = examples.batter_id
LEFT JOIN features.pitcher_career_prior_pa_summary pitcher_career
  ON pitcher_career.feature_season = examples.season
 AND pitcher_career.pitcher_id = examples.pitcher_id
LEFT JOIN features.batter_pitcher_prior_matchup_summary matchup
  ON matchup.feature_season = examples.season
 AND matchup.batter_id = examples.batter_id
 AND matchup.pitcher_id = examples.pitcher_id
LEFT JOIN features.pa_context_coarse_prior_season_rates coarse_context
  ON coarse_context.feature_season = examples.season
 AND coarse_context.batter_hand = examples.batter_hand
 AND coarse_context.pitcher_hand = examples.pitcher_hand
 AND coarse_context.outs_before = examples.outs_before
 AND coarse_context.start_bases = examples.start_bases
LEFT JOIN features.park_prior_season_run_environment park
  ON park.feature_season = examples.season
 AND park.park_id = games.park_id
LEFT JOIN features.team_rolling_30_game_summary home_form
  ON home_form.game_id = examples.game_id
 AND home_form.team_id = examples.home_team_id
LEFT JOIN features.team_rolling_30_game_summary away_form
  ON away_form.game_id = examples.game_id
 AND away_form.team_id = examples.away_team_id;

CREATE OR REPLACE VIEW features.advanced_feature_mart_validation_summary AS
SELECT 'features.pa_context_coarse_prior_season_rates' AS object_name, count(*) AS row_count
FROM features.pa_context_coarse_prior_season_rates
UNION ALL
SELECT 'features.batter_career_prior_pa_summary', count(*)
FROM features.batter_career_prior_pa_summary
UNION ALL
SELECT 'features.pitcher_career_prior_pa_summary', count(*)
FROM features.pitcher_career_prior_pa_summary
UNION ALL
SELECT 'features.batter_pitcher_prior_matchup_summary', count(*)
FROM features.batter_pitcher_prior_matchup_summary
UNION ALL
SELECT 'features.park_prior_season_run_environment', count(*)
FROM features.park_prior_season_run_environment
UNION ALL
SELECT 'features.team_rolling_30_game_summary', count(*)
FROM features.team_rolling_30_game_summary;
