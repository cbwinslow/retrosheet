-- Optimized inference views for fast prediction lookups
-- These views pre-compute and index the most common prediction scenarios

CREATE SCHEMA IF NOT EXISTS inference;

CREATE MATERIALIZED VIEW inference.plate_appearance_features AS
SELECT
    -- Primary identifiers
    pa.game_id,
    pa.plate_appearance_id,
    pa.season,
    pa.inning,
    pa.is_bottom_inning,

    -- Basic state features
    pa.outs_before,
    pa.balls,
    pa.strikes,
    pa.start_bases,
    pa.home_score_diff,

    -- Batter/pitcher info
    pa.batter_id,
    pa.pitcher_id,
    pa.batter_hand,
    pa.pitcher_hand,

    -- Enriched features (pre-joined)
    pa.is_hit,
    pa.is_walk,
    pa.is_strikeout,
    pa.is_home_run,
    pa.is_reach_base,
    pa.is_extra_base_hit,
    COALESCE(batter.prior_pa, 0) AS batter_prior_pa,

    COALESCE(batter.prior_hit_rate, 0.25) AS batter_prior_hit_rate,
    COALESCE(batter.prior_walk_rate, 0.08) AS batter_prior_walk_rate,
    COALESCE(batter.prior_strikeout_rate, 0.20) AS batter_prior_strikeout_rate,
    COALESCE(batter.prior_home_run_rate, 0.03) AS batter_prior_home_run_rate,
    COALESCE(batter.prior_reach_base_rate, 0.32) AS batter_prior_reach_base_rate,
    COALESCE(batter.prior_extra_base_hit_rate, 0.07) AS batter_prior_extra_base_hit_rate,
    COALESCE(pitcher.prior_batters_faced, 0) AS pitcher_prior_batters_faced,

    COALESCE(pitcher.prior_hit_allowed_rate, 0.25) AS pitcher_prior_hit_allowed_rate,
    COALESCE(pitcher.prior_walk_allowed_rate, 0.08) AS pitcher_prior_walk_allowed_rate,
    COALESCE(pitcher.prior_strikeout_rate, 0.20) AS pitcher_prior_strikeout_rate,

    COALESCE(pitcher.prior_home_run_allowed_rate, 0.03) AS pitcher_prior_home_run_allowed_rate,
    COALESCE(pitcher.prior_reach_base_allowed_rate, 0.32) AS pitcher_prior_reach_base_allowed_rate,
    COALESCE(pitcher.prior_extra_base_hit_allowed_rate, 0.07) AS pitcher_prior_extra_base_hit_allowed_rate,

    COALESCE(batting_team.prior_win_rate, 0.5) AS batting_team_prior_win_rate,
    COALESCE(batting_team.prior_runs_scored_per_game, 4.5) AS batting_team_prior_runs_scored_per_game,
    COALESCE(batting_team.prior_runs_allowed_per_game, 4.5) AS batting_team_prior_runs_allowed_per_game,
    COALESCE(fielding_team.prior_win_rate, 0.5) AS fielding_team_prior_win_rate,
    COALESCE(fielding_team.prior_runs_scored_per_game, 4.5) AS fielding_team_prior_runs_scored_per_game,
    COALESCE(fielding_team.prior_runs_allowed_per_game, 4.5) AS fielding_team_prior_runs_allowed_per_game,
    COALESCE(context.prior_pa, 0) AS context_prior_pa,
    COALESCE(context.prior_hit_rate, 0.25) AS context_prior_hit_rate,

    -- Target outcomes (for training/validation)
    COALESCE(context.prior_walk_rate, 0.08) AS context_prior_walk_rate,
    COALESCE(context.prior_strikeout_rate, 0.20) AS context_prior_strikeout_rate,
    COALESCE(context.prior_home_run_rate, 0.03) AS context_prior_home_run_rate,
    COALESCE(context.prior_reach_base_rate, 0.32) AS context_prior_reach_base_rate,
    COALESCE(context.prior_extra_base_hit_rate, 0.07) AS context_prior_extra_base_hit_rate,
    COALESCE(context.prior_batting_team_win_rate, 0.5) AS context_prior_batting_team_win_rate

FROM features.plate_appearance_examples AS pa
LEFT JOIN features.batter_prior_season_pa_summary AS batter
    ON pa.season = batter.feature_season AND pa.batter_id = batter.batter_id
LEFT JOIN features.pitcher_prior_season_pa_summary AS pitcher
    ON pa.season = pitcher.feature_season AND pa.pitcher_id = pitcher.pitcher_id
LEFT JOIN features.team_prior_season_summary AS batting_team
    ON pa.season = batting_team.feature_season AND pa.batting_team_id = batting_team.team_id
LEFT JOIN features.team_prior_season_summary AS fielding_team
    ON pa.season = fielding_team.feature_season AND pa.fielding_team_id = fielding_team.team_id
LEFT JOIN features.pa_context_prior_season_rates AS context
    ON
        pa.season = context.feature_season
        AND context.batter_hand = COALESCE(pa.batter_hand::text, 'U')
        AND context.pitcher_hand = COALESCE(pa.pitcher_hand::text, 'U')
        AND pa.inning = context.inning
        AND pa.is_bottom_inning = context.is_bottom_inning
        AND pa.outs_before = context.outs_before
        AND pa.start_bases = context.start_bases
        AND pa.balls = context.balls
        AND pa.strikes = context.strikes
WITH DATA;

-- Optimized indexes for fast lookups
CREATE UNIQUE INDEX plate_appearance_features_pk
ON inference.plate_appearance_features (game_id, plate_appearance_id);

CREATE INDEX plate_appearance_features_state_idx
ON inference.plate_appearance_features (
    season, inning, is_bottom_inning, outs_before, start_bases, balls, strikes
);

CREATE INDEX plate_appearance_features_batter_idx
ON inference.plate_appearance_features (batter_id, season);

CREATE INDEX plate_appearance_features_pitcher_idx
ON inference.plate_appearance_features (pitcher_id, season);
