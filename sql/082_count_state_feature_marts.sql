CREATE SCHEMA IF NOT EXISTS features;

DROP VIEW IF EXISTS features.count_state_feature_mart_validation_summary;
DROP VIEW IF EXISTS features.plate_appearance_count_state_advanced_examples;
DROP MATERIALIZED VIEW IF EXISTS features.pa_count_state_context_prior_season_rates;
DROP MATERIALIZED VIEW IF EXISTS features.pitcher_count_state_prior_pa_summary;
DROP MATERIALIZED VIEW IF EXISTS features.batter_count_state_prior_pa_summary;

CREATE MATERIALIZED VIEW features.batter_count_state_prior_pa_summary AS
SELECT
    season + 1 AS feature_season,
    batter_id,
    balls,
    strikes,
    count(*)::integer AS prior_pa,
    round(avg(is_hit::integer)::numeric, 4) AS prior_hit_rate,
    round(avg(is_walk::integer)::numeric, 4) AS prior_walk_rate,
    round(avg(is_strikeout::integer)::numeric, 4) AS prior_strikeout_rate,
    round(avg(is_home_run::integer)::numeric, 4) AS prior_home_run_rate,
    round(avg(is_reach_base::integer)::numeric, 4) AS prior_reach_base_rate,
    round(avg(is_extra_base_hit::integer)::numeric, 4) AS prior_extra_base_hit_rate
FROM features.plate_appearance_examples
WHERE batter_id IS NOT NULL
GROUP BY season, batter_id, balls, strikes
WITH DATA;

CREATE UNIQUE INDEX batter_count_state_prior_pa_summary_pk
    ON features.batter_count_state_prior_pa_summary (feature_season, batter_id, balls, strikes);

CREATE INDEX batter_count_state_prior_pa_summary_pa_idx
    ON features.batter_count_state_prior_pa_summary (feature_season, balls, strikes, prior_pa DESC);

CREATE MATERIALIZED VIEW features.pitcher_count_state_prior_pa_summary AS
SELECT
    season + 1 AS feature_season,
    pitcher_id,
    balls,
    strikes,
    count(*)::integer AS prior_batters_faced,
    round(avg(is_hit::integer)::numeric, 4) AS prior_hit_allowed_rate,
    round(avg(is_walk::integer)::numeric, 4) AS prior_walk_allowed_rate,
    round(avg(is_strikeout::integer)::numeric, 4) AS prior_strikeout_rate,
    round(avg(is_home_run::integer)::numeric, 4) AS prior_home_run_allowed_rate,
    round(avg(is_reach_base::integer)::numeric, 4) AS prior_reach_base_allowed_rate,
    round(avg(is_extra_base_hit::integer)::numeric, 4) AS prior_extra_base_hit_allowed_rate
FROM features.plate_appearance_examples
WHERE pitcher_id IS NOT NULL
GROUP BY season, pitcher_id, balls, strikes
WITH DATA;

CREATE UNIQUE INDEX pitcher_count_state_prior_pa_summary_pk
    ON features.pitcher_count_state_prior_pa_summary (feature_season, pitcher_id, balls, strikes);

CREATE INDEX pitcher_count_state_prior_pa_summary_bf_idx
    ON features.pitcher_count_state_prior_pa_summary (feature_season, balls, strikes, prior_batters_faced DESC);

CREATE MATERIALIZED VIEW features.pa_count_state_context_prior_season_rates AS
SELECT
    season + 1 AS feature_season,
    batter_hand,
    pitcher_hand,
    outs_before,
    start_bases,
    balls,
    strikes,
    count(*)::integer AS prior_pa,
    round(avg(is_hit::integer)::numeric, 4) AS prior_hit_rate,
    round(avg(is_walk::integer)::numeric, 4) AS prior_walk_rate,
    round(avg(is_strikeout::integer)::numeric, 4) AS prior_strikeout_rate,
    round(avg(is_home_run::integer)::numeric, 4) AS prior_home_run_rate,
    round(avg(is_reach_base::integer)::numeric, 4) AS prior_reach_base_rate,
    round(avg(is_extra_base_hit::integer)::numeric, 4) AS prior_extra_base_hit_rate
FROM features.plate_appearance_examples
GROUP BY season, batter_hand, pitcher_hand, outs_before, start_bases, balls, strikes
WITH DATA;

CREATE UNIQUE INDEX pa_count_state_context_prior_season_rates_pk
    ON features.pa_count_state_context_prior_season_rates (
        feature_season,
        batter_hand,
        pitcher_hand,
        outs_before,
        start_bases,
        balls,
        strikes
    );

CREATE INDEX pa_count_state_context_prior_season_rates_pa_idx
    ON features.pa_count_state_context_prior_season_rates (feature_season, balls, strikes, prior_pa DESC);

CREATE OR REPLACE VIEW features.plate_appearance_count_state_advanced_examples AS
SELECT
    advanced.*,
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
FROM features.plate_appearance_advanced_examples advanced
LEFT JOIN features.batter_count_state_prior_pa_summary batter_count
  ON batter_count.feature_season = advanced.season
 AND batter_count.batter_id = advanced.batter_id
 AND batter_count.balls = advanced.balls
 AND batter_count.strikes = advanced.strikes
LEFT JOIN features.pitcher_count_state_prior_pa_summary pitcher_count
  ON pitcher_count.feature_season = advanced.season
 AND pitcher_count.pitcher_id = advanced.pitcher_id
 AND pitcher_count.balls = advanced.balls
 AND pitcher_count.strikes = advanced.strikes
LEFT JOIN features.pa_count_state_context_prior_season_rates context_count
  ON context_count.feature_season = advanced.season
 AND context_count.batter_hand = advanced.batter_hand
 AND context_count.pitcher_hand = advanced.pitcher_hand
 AND context_count.outs_before = advanced.outs_before
 AND context_count.start_bases = advanced.start_bases
 AND context_count.balls = advanced.balls
 AND context_count.strikes = advanced.strikes;

CREATE OR REPLACE VIEW features.count_state_feature_mart_validation_summary AS
SELECT 'features.batter_count_state_prior_pa_summary' AS object_name, count(*) AS row_count
FROM features.batter_count_state_prior_pa_summary
UNION ALL
SELECT 'features.pitcher_count_state_prior_pa_summary', count(*)
FROM features.pitcher_count_state_prior_pa_summary
UNION ALL
SELECT 'features.pa_count_state_context_prior_season_rates', count(*)
FROM features.pa_count_state_context_prior_season_rates
UNION ALL
SELECT 'features.plate_appearance_count_state_advanced_examples', count(*)
FROM features.plate_appearance_count_state_advanced_examples;
