-- File: sql/mlb/122_live_pa_feature_parity.sql
-- Purpose: Live plate appearance features matching historical schema
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS features;

DROP VIEW IF EXISTS features.live_plate_appearance_advanced_count_examples;

CREATE OR REPLACE VIEW features.live_plate_appearance_advanced_count_examples AS
WITH live_pa AS (
    SELECT
        ev.game_id,
        ev.event_id AS plate_appearance_id,
        gm.game_date_parsed AS game_date,
        ev.inning::integer AS inning,
        ev.is_bottom_inning,
        ev.outs_before::integer AS outs_before,
        COALESCE(ev.start_bases, 0)::integer AS start_bases,
        COALESCE(ev.balls, 0)::integer AS balls,
        COALESCE(ev.strikes, 0)::integer AS strikes,
        (
            (COALESCE(ev.home_score_after, 0) - CASE WHEN ev.is_bottom_inning THEN COALESCE(ev.runs_on_play, 0) ELSE 0 END)
            -
            (COALESCE(ev.away_score_after, 0) - CASE WHEN ev.is_bottom_inning THEN 0 ELSE COALESCE(ev.runs_on_play, 0) END)
        )::integer AS home_score_diff,
        gm.home_team_id,
        gm.away_team_id,
        ev.batter_id,
        ev.pitcher_id,
        ev.mlb_game_pk,
        ev.snapshot_id,
        ev.plate_appearance_index,
        ev.event_text,
        ev.event_code,
        ev.is_at_bat,
        ev.is_plate_appearance,
        ev.hit_value,
        ev.is_hit,
        ev.is_walk,
        ev.is_strikeout,
        ev.is_home_run,
        ev.runs_on_play,
        ev.rbi,
        COALESCE(gm.season_int, NULLIF(ev.season, '')::integer) AS season,
        CASE
            WHEN ev.is_bottom_inning THEN gm.home_team_id
            ELSE gm.away_team_id
        END AS batting_team_id,
        CASE
            WHEN ev.is_bottom_inning THEN gm.away_team_id
            ELSE gm.home_team_id
        END AS fielding_team_id,
        COALESCE(ev.batter_hand::text, 'U') AS batter_hand,
        COALESCE(ev.pitcher_hand::text, 'U') AS pitcher_hand,
        COALESCE(gm.park_id, 'UNK') AS park_id,
        CASE
            WHEN COALESCE(gm.season_int, NULLIF(ev.season, '')::integer) BETWEEN 2000 AND 2009 THEN '2000_2009'
            WHEN COALESCE(gm.season_int, NULLIF(ev.season, '')::integer) BETWEEN 2010 AND 2014 THEN '2010_2014'
            WHEN COALESCE(gm.season_int, NULLIF(ev.season, '')::integer) BETWEEN 2015 AND 2019 THEN '2015_2019'
            WHEN COALESCE(gm.season_int, NULLIF(ev.season, '')::integer) = 2020 THEN '2020'
            WHEN COALESCE(gm.season_int, NULLIF(ev.season, '')::integer) BETWEEN 2021 AND 2022 THEN '2021_2022'
            ELSE '2023_plus'
        END AS season_era,
        CASE
            WHEN COALESCE(gm.season_int, NULLIF(ev.season, '')::integer) = 2020 THEN 'pandemic_2020'
            WHEN COALESCE(gm.season_int, NULLIF(ev.season, '')::integer) BETWEEN 2021 AND 2022 THEN 'enforcement_transition'
            WHEN COALESCE(gm.season_int, NULLIF(ev.season, '')::integer) >= 2023 THEN 'post_2023_rules'
            ELSE 'pre_2020_rules'
        END AS rules_context_era
    FROM core.live_events AS ev
    INNER JOIN core.live_games AS gm
        ON ev.game_id = gm.game_id
    WHERE ev.is_plate_appearance = true
)

SELECT
    live_pa.*,
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
    fielding_form.rolling_30_runs_allowed_per_game AS fielding_team_rolling_30_runs_allowed_per_game,
    batter_count.prior_pa AS batter_count_state_prior_pa,
    batter_count.prior_hit_rate AS batter_count_state_prior_hit_rate,
    batter_count.prior_walk_rate AS batter_count_state_prior_walk_rate,
    batter_count.prior_strikeout_rate AS batter_count_state_prior_strikeout_rate,
    batter_count.prior_home_run_rate AS batter_count_state_prior_home_run_rate,
    batter_count.prior_reach_base_rate AS batter_count_state_prior_reach_base_rate,
    batter_count.prior_extra_base_hit_rate AS batter_count_state_prior_extra_base_hit_rate,
    pitcher_count.prior_batters_faced AS pitcher_count_state_prior_batters_faced,
    pitcher_count.prior_hit_allowed_rate AS pitcher_count_state_prior_hit_allowed_rate,
    pitcher_count.prior_walk_allowed_rate AS pitcher_count_state_prior_walk_allowed_rate,
    pitcher_count.prior_strikeout_rate AS pitcher_count_state_prior_strikeout_rate,
    pitcher_count.prior_home_run_allowed_rate AS pitcher_count_state_prior_home_run_allowed_rate,
    pitcher_count.prior_reach_base_allowed_rate AS pitcher_count_state_prior_reach_base_allowed_rate,
    pitcher_count.prior_extra_base_hit_allowed_rate AS pitcher_count_state_prior_extra_base_hit_allowed_rate,
    context_count.prior_pa AS count_state_context_prior_pa,
    context_count.prior_hit_rate AS count_state_context_prior_hit_rate,
    context_count.prior_walk_rate AS count_state_context_prior_walk_rate,
    context_count.prior_strikeout_rate AS count_state_context_prior_strikeout_rate,
    context_count.prior_home_run_rate AS count_state_context_prior_home_run_rate,
    context_count.prior_reach_base_rate AS count_state_context_prior_reach_base_rate,
    context_count.prior_extra_base_hit_rate AS count_state_context_prior_extra_base_hit_rate
FROM live_pa
LEFT JOIN features.batter_career_prior_pa_summary AS batter_career
    ON
        live_pa.season = batter_career.feature_season
        AND live_pa.batter_id = batter_career.batter_id
LEFT JOIN features.pitcher_career_prior_pa_summary AS pitcher_career
    ON
        live_pa.season = pitcher_career.feature_season
        AND live_pa.pitcher_id = pitcher_career.pitcher_id
LEFT JOIN features.batter_pitcher_prior_matchup_summary AS matchup
    ON
        live_pa.season = matchup.feature_season
        AND live_pa.batter_id = matchup.batter_id
        AND live_pa.pitcher_id = matchup.pitcher_id
LEFT JOIN features.pa_context_coarse_prior_season_rates AS coarse_context
    ON
        live_pa.season = coarse_context.feature_season
        AND live_pa.batter_hand = coarse_context.batter_hand
        AND live_pa.pitcher_hand = coarse_context.pitcher_hand
        AND live_pa.outs_before = coarse_context.outs_before
        AND live_pa.start_bases = coarse_context.start_bases
LEFT JOIN features.park_prior_season_run_environment AS park
    ON
        live_pa.season = park.feature_season
        AND live_pa.park_id = park.park_id
LEFT JOIN features.team_rolling_30_game_summary AS batting_form
    ON
        live_pa.game_id = batting_form.game_id
        AND live_pa.batting_team_id = batting_form.team_id
LEFT JOIN features.team_rolling_30_game_summary AS fielding_form
    ON
        live_pa.game_id = fielding_form.game_id
        AND live_pa.fielding_team_id = fielding_form.team_id
LEFT JOIN features.batter_count_state_prior_pa_summary AS batter_count
    ON
        live_pa.season = batter_count.feature_season
        AND live_pa.batter_id = batter_count.batter_id
        AND live_pa.balls = batter_count.balls
        AND live_pa.strikes = batter_count.strikes
LEFT JOIN features.pitcher_count_state_prior_pa_summary AS pitcher_count
    ON
        live_pa.season = pitcher_count.feature_season
        AND live_pa.pitcher_id = pitcher_count.pitcher_id
        AND live_pa.balls = pitcher_count.balls
        AND live_pa.strikes = pitcher_count.strikes
LEFT JOIN features.pa_count_state_context_prior_season_rates AS context_count
    ON
        live_pa.season = context_count.feature_season
        AND live_pa.batter_hand = context_count.batter_hand
        AND live_pa.pitcher_hand = context_count.pitcher_hand
        AND live_pa.outs_before = context_count.outs_before
        AND live_pa.start_bases = context_count.start_bases
        AND live_pa.balls = context_count.balls
        AND live_pa.strikes = context_count.strikes;

