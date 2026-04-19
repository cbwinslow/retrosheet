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
    CASE WHEN pa.is_bottom_inning THEN pa.home_team_id ELSE pa.away_team_id END AS batting_team_id,
    CASE WHEN pa.is_bottom_inning THEN pa.away_team_id ELSE pa.home_team_id END AS fielding_team_id,

    -- State at start of half-inning (first plate appearance)
    first_pa.outs_before AS start_outs,
    first_pa.balls AS start_balls,
    first_pa.strikes AS start_strikes,
    first_pa.start_bases AS start_bases,
    first_pa.home_score_before AS start_home_score,
    first_pa.away_score_before AS start_away_score,
    first_pa.home_score_before - first_pa.away_score_before AS start_score_diff,

    -- Half-inning outcomes (aggregated from all plate appearances)
    count(*)::integer AS total_plate_appearances,
    count(*) FILTER (WHERE pa.is_hit)::integer AS total_hits,
    count(*) FILTER (WHERE pa.is_walk)::integer AS total_walks,
    count(*) FILTER (WHERE pa.is_strikeout)::integer AS total_strikeouts,
    count(*) FILTER (WHERE pa.is_home_run)::integer AS total_home_runs,
    sum(pa.runs_on_play)::integer AS total_runs_scored,

    -- Specific scenario targets
    (sum(pa.runs_on_play) > 0)::integer AS any_run_scored,
    bool_or(pa.is_hit AND pa.batter_hand = 'L')::integer AS any_left_handed_hit,
    bool_or(pa.is_hit AND pa.batter_hand = 'R')::integer AS any_right_handed_hit,

    -- Left-handed batter scenario context
    count(*) FILTER (WHERE pa.batter_hand = 'L')::integer AS left_handed_pa_count,
    count(*) FILTER (WHERE pa.batter_hand = 'L' AND pa.is_hit)::integer AS left_handed_hits,
    (count(*) FILTER (WHERE pa.batter_hand = 'L') > 0
     AND count(*) FILTER (WHERE pa.batter_hand = 'L')
         = count(*) FILTER (WHERE pa.batter_hand = 'L' AND pa.is_hit))::integer AS all_left_handed_batters_hit,

    -- Final game outcome (for potential win probability context)
    bool_or(pa.final_home_win)::integer AS final_home_win,
    bool_or(pa.final_batting_team_win)::integer AS final_batting_team_win

FROM core.plate_appearances pa
JOIN core.plate_appearances first_pa ON (
    first_pa.game_id = pa.game_id
    AND first_pa.inning = pa.inning
    AND first_pa.is_bottom_inning = pa.is_bottom_inning
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