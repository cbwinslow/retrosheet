-- File: sql/core/080_half_inning_examples.sql
-- Purpose: Create half-inning run expectancy examples and feature views
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS features;

DROP MATERIALIZED VIEW IF EXISTS features.half_inning_examples;

CREATE MATERIALIZED VIEW features.half_inning_examples AS
SELECT
    -- Half-inning identity
    pa.game_id,
    pa.season,
    pa.game_date,
    pa.inning,
    pa.is_bottom_inning,
    pa.home_team_id,
    pa.away_team_id,
    first_pa.outs_before AS start_outs,
    first_pa.balls AS start_balls,

    -- State at start of half-inning (first plate appearance)
    first_pa.strikes AS start_strikes,
    first_pa.start_bases,
    first_pa.home_score_before AS start_home_score,
    first_pa.away_score_before AS start_away_score,
    count(*)::integer AS total_plate_appearances,
    count(*) FILTER (WHERE pa.is_hit)::integer AS total_hits,
    count(*) FILTER (WHERE pa.is_walk)::integer AS total_walks,

    -- Half-inning outcomes (aggregated from all plate appearances)
    count(*) FILTER (WHERE pa.is_strikeout)::integer AS total_strikeouts,
    count(*) FILTER (WHERE pa.is_home_run)::integer AS total_home_runs,
    sum(pa.runs_on_play)::integer AS total_runs_scored,
    (sum(pa.runs_on_play) > 0)::integer AS any_run_scored,
    bool_or(pa.is_hit AND pa.batter_hand = 'L')::integer AS any_left_handed_hit,
    bool_or(pa.is_hit AND pa.batter_hand = 'R')::integer AS any_right_handed_hit,

    -- Specific scenario targets
    count(*) FILTER (WHERE pa.batter_hand = 'L')::integer AS left_handed_pa_count,
    count(*) FILTER (WHERE pa.batter_hand = 'L' AND pa.is_hit)::integer AS left_handed_hits,
    (
        count(*) FILTER (WHERE pa.batter_hand = 'L') > 0
        AND count(*) FILTER (WHERE pa.batter_hand = 'L')
        = count(*) FILTER (WHERE pa.batter_hand = 'L' AND pa.is_hit)
    )::integer AS all_left_handed_batters_hit,

    -- Left-handed batter scenario context
    bool_or(pa.final_home_win)::integer AS final_home_win,
    bool_or(pa.final_batting_team_win)::integer AS final_batting_team_win,
    CASE WHEN pa.is_bottom_inning THEN pa.home_team_id ELSE pa.away_team_id END AS batting_team_id,

    -- Final game outcome (for potential win probability context)
    CASE WHEN pa.is_bottom_inning THEN pa.away_team_id ELSE pa.home_team_id END AS fielding_team_id,
    first_pa.home_score_before - first_pa.away_score_before AS start_score_diff

FROM core.plate_appearances AS pa
INNER JOIN core.plate_appearances AS first_pa
    ON (
        pa.game_id = first_pa.game_id
        AND pa.inning = first_pa.inning
        AND pa.is_bottom_inning = first_pa.is_bottom_inning
        AND first_pa.half_inning_pa_number = 1
    )
WHERE pa.half_inning_pa_number >= 1
GROUP BY
    pa.game_id,
    pa.season,
    pa.game_date,
    pa.inning,
    pa.is_bottom_inning,
    pa.home_team_id,
    pa.away_team_id,
    first_pa.outs_before,
    first_pa.balls,
    first_pa.strikes,
    first_pa.start_bases,
    first_pa.home_score_before,
    first_pa.away_score_before
WITH DATA;

CREATE UNIQUE INDEX half_inning_examples_pk
ON features.half_inning_examples (game_id, inning, is_bottom_inning);

CREATE INDEX half_inning_examples_season_idx
ON features.half_inning_examples (season);

CREATE INDEX half_inning_examples_team_context_idx
ON features.half_inning_examples (season, batting_team_id, fielding_team_id);

CREATE INDEX half_inning_examples_state_idx
ON features.half_inning_examples (season, start_outs, start_bases, start_score_diff);

