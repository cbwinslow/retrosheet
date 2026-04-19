CREATE SCHEMA IF NOT EXISTS features;

DROP VIEW IF EXISTS features.live_plate_appearance_advanced_count_examples;

CREATE OR REPLACE VIEW features.live_plate_appearance_advanced_count_examples AS
WITH live_pa AS (
    SELECT
        ev.game_id,
        ev.event_id AS plate_appearance_id,
        COALESCE(gm.season_int, NULLIF(ev.season, '')::integer) AS season,
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
        CASE
            WHEN ev.is_bottom_inning THEN gm.home_team_id
            ELSE gm.away_team_id
        END AS batting_team_id,
        CASE
            WHEN ev.is_bottom_inning THEN gm.away_team_id
            ELSE gm.home_team_id
        END AS fielding_team_id,
        gm.home_team_id,
        gm.away_team_id,
        ev.batter_id,
        COALESCE(ev.batter_hand::text, 'U') AS batter_hand,
        ev.pitcher_id,
        COALESCE(ev.pitcher_hand::text, 'U') AS pitcher_hand,
        COALESCE(gm.park_id, 'UNK') AS park_id,
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
    FROM core.live_events ev
    JOIN core.live_games gm
      ON gm.game_id = ev.game_id
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
LEFT JOIN features.batter_career_prior_pa_summary batter_career
  ON batter_career.feature_season = live_pa.season
 AND batter_career.batter_id = live_pa.batter_id
LEFT JOIN features.pitcher_career_prior_pa_summary pitcher_career
  ON pitcher_career.feature_season = live_pa.season
 AND pitcher_career.pitcher_id = live_pa.pitcher_id
LEFT JOIN features.batter_pitcher_prior_matchup_summary matchup
  ON matchup.feature_season = live_pa.season
 AND matchup.batter_id = live_pa.batter_id
 AND matchup.pitcher_id = live_pa.pitcher_id
LEFT JOIN features.pa_context_coarse_prior_season_rates coarse_context
  ON coarse_context.feature_season = live_pa.season
 AND coarse_context.batter_hand = live_pa.batter_hand
 AND coarse_context.pitcher_hand = live_pa.pitcher_hand
 AND coarse_context.outs_before = live_pa.outs_before
 AND coarse_context.start_bases = live_pa.start_bases
LEFT JOIN features.park_prior_season_run_environment park
  ON park.feature_season = live_pa.season
 AND park.park_id = live_pa.park_id
LEFT JOIN features.team_rolling_30_game_summary batting_form
  ON batting_form.game_id = live_pa.game_id
 AND batting_form.team_id = live_pa.batting_team_id
LEFT JOIN features.team_rolling_30_game_summary fielding_form
  ON fielding_form.game_id = live_pa.game_id
 AND fielding_form.team_id = live_pa.fielding_team_id
LEFT JOIN features.batter_count_state_prior_pa_summary batter_count
  ON batter_count.feature_season = live_pa.season
 AND batter_count.batter_id = live_pa.batter_id
 AND batter_count.balls = live_pa.balls
 AND batter_count.strikes = live_pa.strikes
LEFT JOIN features.pitcher_count_state_prior_pa_summary pitcher_count
  ON pitcher_count.feature_season = live_pa.season
 AND pitcher_count.pitcher_id = live_pa.pitcher_id
 AND pitcher_count.balls = live_pa.balls
 AND pitcher_count.strikes = live_pa.strikes
LEFT JOIN features.pa_count_state_context_prior_season_rates context_count
  ON context_count.feature_season = live_pa.season
 AND context_count.batter_hand = live_pa.batter_hand
 AND context_count.pitcher_hand = live_pa.pitcher_hand
 AND context_count.outs_before = live_pa.outs_before
 AND context_count.start_bases = live_pa.start_bases
 AND context_count.balls = live_pa.balls
 AND context_count.strikes = live_pa.strikes;
