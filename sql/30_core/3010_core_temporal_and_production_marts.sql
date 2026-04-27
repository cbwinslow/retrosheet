-- File: sql/core/070_temporal_and_production_marts.sql
-- Purpose: Create team schedule context, player/pitcher production, temporal views
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS features;

DROP VIEW IF EXISTS features.plate_appearance_temporal_examples CASCADE;
DROP VIEW IF EXISTS features.game_outcome_temporal_examples CASCADE;
DROP VIEW IF EXISTS features.temporal_production_validation_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS features.pitcher_production_season CASCADE;
DROP MATERIALIZED VIEW IF EXISTS features.player_production_season CASCADE;
DROP MATERIALIZED VIEW IF EXISTS features.team_game_context CASCADE;

CREATE MATERIALIZED VIEW features.team_game_context AS
WITH team_games AS (
    SELECT
        games.game_id,
        games.season,
        games.game_date,
        games.game_number,
        games.day_of_week,
        games.day_night,
        games.park_id,
        games.home_team_id AS team_id,
        games.away_team_id AS opponent_team_id,
        TRUE AS is_home_team,
        games.home_win AS won,
        games.home_score AS runs_scored,
        games.away_score AS runs_allowed,
        games.home_starting_pitcher_id AS starting_pitcher_id,
        games.attendance,
        games.temperature_f,
        games.wind_speed_mph,
        games.duration_minutes
    FROM core.games AS games
    UNION ALL
    SELECT
        games.game_id,
        games.season,
        games.game_date,
        games.game_number,
        games.day_of_week,
        games.day_night,
        games.park_id,
        games.away_team_id AS team_id,
        games.home_team_id AS opponent_team_id,
        FALSE AS is_home_team,
        NOT games.home_win AS won,
        games.away_score AS runs_scored,
        games.home_score AS runs_allowed,
        games.away_starting_pitcher_id AS starting_pitcher_id,
        games.attendance,
        games.temperature_f,
        games.wind_speed_mph,
        games.duration_minutes
    FROM core.games AS games
),

lagged AS (
    SELECT
        team_games.*,
        ROW_NUMBER() OVER (
            PARTITION BY team_games.team_id, team_games.season
            ORDER BY team_games.game_date, COALESCE(team_games.game_number, 0), team_games.game_id
        )::integer AS team_game_number,
        LAG(team_games.game_date) OVER team_order AS previous_game_date,
        LAG(team_games.park_id) OVER team_order AS previous_park_id,
        LAG(team_games.is_home_team) OVER team_order AS previous_is_home_team,
        LAG(team_games.opponent_team_id) OVER team_order AS previous_opponent_team_id
    FROM team_games
    WINDOW team_order AS (
        PARTITION BY team_id
        ORDER BY game_date, COALESCE(game_number, 0), game_id
    )
)

SELECT
    game_id,
    season,
    game_date,
    game_number,
    team_game_number,
    day_of_week,
    day_night,
    team_id,
    opponent_team_id,
    is_home_team,
    park_id,
    starting_pitcher_id,
    won,
    runs_scored,
    runs_allowed,
    previous_game_date,
    (game_date - previous_game_date)::integer AS days_since_previous_game,
    previous_park_id,
    previous_is_home_team,
    previous_opponent_team_id,
    attendance,
    temperature_f,
    wind_speed_mph,
    duration_minutes,
    ((game_date - previous_game_date) = 1) AS played_yesterday,
    ((game_date - previous_game_date) = 0) AS doubleheader_same_day,
    (previous_park_id = park_id) AS same_park_as_previous_game,
    (
        previous_is_home_team IS NOT NULL
        AND previous_is_home_team IS DISTINCT FROM is_home_team
    ) AS changed_home_road_status,
    (previous_opponent_team_id = opponent_team_id) AS same_opponent_as_previous_game
FROM lagged
WITH DATA;

CREATE UNIQUE INDEX team_game_context_pk
ON features.team_game_context (game_id, team_id);
CREATE INDEX team_game_context_team_date_idx
ON features.team_game_context (team_id, game_date);
CREATE INDEX team_game_context_rest_idx
ON features.team_game_context (season, days_since_previous_game, is_home_team);

CREATE MATERIALIZED VIEW features.player_production_season AS
SELECT
    plate_appearances.season,
    plate_appearances.batter_id AS player_id,
    COUNT(*)::integer AS plate_appearances,
    COUNT(*) FILTER (WHERE plate_appearances.is_at_bat)::integer AS at_bats,
    COUNT(*) FILTER (WHERE plate_appearances.is_hit)::integer AS hits,
    COUNT(*) FILTER (WHERE plate_appearances.is_walk)::integer AS walks,
    COUNT(*) FILTER (WHERE plate_appearances.is_strikeout)::integer AS strikeouts,
    COUNT(*) FILTER (WHERE plate_appearances.is_home_run)::integer AS home_runs,
    COUNT(*) FILTER (WHERE plate_appearances.is_extra_base_hit)::integer AS extra_base_hits,
    COUNT(*) FILTER (WHERE plate_appearances.is_hit_by_pitch)::integer AS hit_by_pitch,
    SUM(plate_appearances.hit_value)::integer AS total_bases,
    SUM(plate_appearances.rbi)::integer AS rbi,
    MAX(players.player_name) AS player_name,
    ROUND(
        COUNT(*) FILTER (WHERE plate_appearances.is_hit)::numeric
        / NULLIF(COUNT(*) FILTER (WHERE plate_appearances.is_at_bat), 0),
        4
    ) AS batting_average,
    ROUND(
        (
            COUNT(*) FILTER (WHERE plate_appearances.is_hit)
            + COUNT(*) FILTER (WHERE plate_appearances.is_walk)
            + COUNT(*) FILTER (WHERE plate_appearances.is_hit_by_pitch)
        )::numeric
        / NULLIF(
            COUNT(*)
            FILTER (
                WHERE plate_appearances.is_at_bat
                OR plate_appearances.is_walk
                OR plate_appearances.is_hit_by_pitch
            ),
            0
        ),
        4
    ) AS on_base_percentage_proxy,
    ROUND(
        SUM(plate_appearances.hit_value)::numeric
        / NULLIF(COUNT(*) FILTER (WHERE plate_appearances.is_at_bat), 0),
        4
    ) AS slugging_percentage,
    ROUND(AVG(plate_appearances.is_hit::integer)::numeric, 4) AS hit_rate,
    ROUND(AVG(plate_appearances.is_walk::integer)::numeric, 4) AS walk_rate,
    ROUND(AVG(plate_appearances.is_strikeout::integer)::numeric, 4) AS strikeout_rate,
    ROUND(AVG(plate_appearances.is_home_run::integer)::numeric, 4) AS home_run_rate,
    ROUND(AVG(plate_appearances.is_reach_base::integer)::numeric, 4) AS reach_base_rate
FROM core.plate_appearances AS plate_appearances
LEFT JOIN core.players AS players
    ON plate_appearances.batter_id = players.retrosheet_player_id
WHERE plate_appearances.batter_id IS NOT NULL
GROUP BY plate_appearances.season, plate_appearances.batter_id
WITH DATA;

CREATE UNIQUE INDEX player_production_season_pk
ON features.player_production_season (season, player_id);
CREATE INDEX player_production_season_ops_proxy_idx
ON features.player_production_season (
    season,
    (COALESCE(on_base_percentage_proxy, 0) + COALESCE(slugging_percentage, 0)) DESC
);

CREATE MATERIALIZED VIEW features.pitcher_production_season AS
SELECT
    plate_appearances.season,
    plate_appearances.pitcher_id AS player_id,
    COUNT(*)::integer AS batters_faced,
    COUNT(*) FILTER (WHERE plate_appearances.is_at_bat)::integer AS at_bats_against,
    COUNT(*) FILTER (WHERE plate_appearances.is_hit)::integer AS hits_allowed,
    COUNT(*) FILTER (WHERE plate_appearances.is_walk)::integer AS walks_allowed,
    COUNT(*) FILTER (WHERE plate_appearances.is_strikeout)::integer AS strikeouts,
    COUNT(*) FILTER (WHERE plate_appearances.is_home_run)::integer AS home_runs_allowed,
    COUNT(*) FILTER (WHERE plate_appearances.is_extra_base_hit)::integer AS extra_base_hits_allowed,
    SUM(plate_appearances.runs_on_play)::integer AS runs_allowed_on_pa,
    SUM(plate_appearances.hit_value)::integer AS total_bases_allowed,
    MAX(players.player_name) AS player_name,
    ROUND(AVG(plate_appearances.is_hit::integer)::numeric, 4) AS hit_allowed_rate,
    ROUND(AVG(plate_appearances.is_walk::integer)::numeric, 4) AS walk_allowed_rate,
    ROUND(AVG(plate_appearances.is_strikeout::integer)::numeric, 4) AS strikeout_rate,
    ROUND(AVG(plate_appearances.is_home_run::integer)::numeric, 4) AS home_run_allowed_rate,
    ROUND(AVG(plate_appearances.is_reach_base::integer)::numeric, 4) AS reach_base_allowed_rate,
    ROUND(
        SUM(plate_appearances.hit_value)::numeric
        / NULLIF(COUNT(*) FILTER (WHERE plate_appearances.is_at_bat), 0),
        4
    ) AS slugging_allowed,
    ROUND(
        COUNT(*) FILTER (WHERE plate_appearances.is_strikeout)::numeric
        - COUNT(*) FILTER (WHERE plate_appearances.is_walk)::numeric
        - COUNT(*) FILTER (WHERE plate_appearances.is_home_run)::numeric,
        4
    ) AS command_power_score_proxy
FROM core.plate_appearances AS plate_appearances
LEFT JOIN core.players AS players
    ON plate_appearances.pitcher_id = players.retrosheet_player_id
WHERE plate_appearances.pitcher_id IS NOT NULL
GROUP BY plate_appearances.season, plate_appearances.pitcher_id
WITH DATA;

CREATE UNIQUE INDEX pitcher_production_season_pk
ON features.pitcher_production_season (season, player_id);
CREATE INDEX pitcher_production_season_power_idx
ON features.pitcher_production_season (season, command_power_score_proxy DESC);

CREATE OR REPLACE VIEW features.game_outcome_temporal_examples AS
SELECT
    advanced.*,
    home_context.days_since_previous_game AS home_days_since_previous_game,
    home_context.played_yesterday AS home_played_yesterday,
    home_context.doubleheader_same_day AS home_doubleheader_same_day,
    home_context.same_park_as_previous_game AS home_same_park_as_previous_game,
    home_context.changed_home_road_status AS home_changed_home_road_status,
    away_context.days_since_previous_game AS away_days_since_previous_game,
    away_context.played_yesterday AS away_played_yesterday,
    away_context.doubleheader_same_day AS away_doubleheader_same_day,
    away_context.same_park_as_previous_game AS away_same_park_as_previous_game,
    away_context.changed_home_road_status AS away_changed_home_road_status
FROM features.game_outcome_advanced_examples AS advanced
LEFT JOIN features.team_game_context AS home_context
    ON
        advanced.game_id = home_context.game_id
        AND advanced.home_team_id = home_context.team_id
LEFT JOIN features.team_game_context AS away_context
    ON
        advanced.game_id = away_context.game_id
        AND advanced.away_team_id = away_context.team_id;

CREATE OR REPLACE VIEW features.plate_appearance_temporal_examples AS
SELECT
    advanced.*,
    batting_context.days_since_previous_game AS batting_team_days_since_previous_game,
    batting_context.played_yesterday AS batting_team_played_yesterday,
    batting_context.doubleheader_same_day AS batting_team_doubleheader_same_day,
    batting_context.same_park_as_previous_game AS batting_team_same_park_as_previous_game,
    batting_context.changed_home_road_status AS batting_team_changed_home_road_status,
    fielding_context.days_since_previous_game AS fielding_team_days_since_previous_game,
    fielding_context.played_yesterday AS fielding_team_played_yesterday,
    fielding_context.doubleheader_same_day AS fielding_team_doubleheader_same_day,
    fielding_context.same_park_as_previous_game AS fielding_team_same_park_as_previous_game,
    fielding_context.changed_home_road_status AS fielding_team_changed_home_road_status
FROM features.plate_appearance_advanced_examples AS advanced
LEFT JOIN features.team_game_context AS batting_context
    ON
        advanced.game_id = batting_context.game_id
        AND advanced.batting_team_id = batting_context.team_id
LEFT JOIN features.team_game_context AS fielding_context
    ON
        advanced.game_id = fielding_context.game_id
        AND advanced.fielding_team_id = fielding_context.team_id;

CREATE OR REPLACE VIEW features.temporal_production_validation_summary AS
SELECT
    'features.team_game_context' AS object_name,
    COUNT(*) AS row_count
FROM features.team_game_context
UNION ALL
SELECT
    'features.player_production_season',
    COUNT(*)
FROM features.player_production_season
UNION ALL
SELECT
    'features.pitcher_production_season',
    COUNT(*)
FROM features.pitcher_production_season
UNION ALL
SELECT
    'features.game_outcome_temporal_examples_2025',
    COUNT(*)
FROM features.game_outcome_temporal_examples
WHERE season = 2025
UNION ALL
SELECT
    'features.plate_appearance_temporal_examples_2025',
    COUNT(*)
FROM features.plate_appearance_temporal_examples
WHERE season = 2025;
