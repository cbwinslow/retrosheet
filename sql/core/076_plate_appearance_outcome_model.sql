-- File: sql/core/076_plate_appearance_outcome_model.sql
-- Purpose: Create PA outcome model tables, views, and prediction targets
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS features;
CREATE SCHEMA IF NOT EXISTS predictions;

DROP VIEW IF EXISTS features.pitch_sequence_validation_summary;
DROP MATERIALIZED VIEW IF EXISTS features.pitch_sequence_examples;
DROP VIEW IF EXISTS features.plate_appearance_outcome_validation_summary;
DROP MATERIALIZED VIEW IF EXISTS features.plate_appearance_outcome_examples;

CREATE MATERIALIZED VIEW features.plate_appearance_outcome_examples AS
SELECT
    pa.game_id,
    pa.plate_appearance_id,
    pa.game_pa_number,
    pa.half_inning_pa_number,
    pa.season,
    pa.game_date,
    pa.inning,
    pa.is_bottom_inning,
    pa.outs_before,
    pa.away_score_before,
    pa.home_score_before,
    pa.batting_team_id,
    pa.fielding_team_id,
    pa.home_team_id,
    pa.away_team_id,
    pa.batter_id,
    pa.pitcher_id,
    pa.event_code,
    raw.pitch_seq_tx,
    raw.battedball_cd,
    raw.battedball_loc_tx,
    pa.is_at_bat,
    pa.hit_value,
    pa.is_hit,
    pa.is_walk,
    pa.is_strikeout,
    pa.is_home_run,
    pa.is_hit_by_pitch,
    pa.is_interference,
    pa.is_reach_base,
    pa.is_extra_base_hit,
    pa.runs_on_play,
    pa.rbi,
    pa.final_home_win,
    pa.final_batting_team_win,
    CASE
        WHEN pa.season BETWEEN 2000 AND 2009 THEN '2000_2009'
        WHEN pa.season BETWEEN 2010 AND 2014 THEN '2010_2014'
        WHEN pa.season BETWEEN 2015 AND 2019 THEN '2015_2019'
        WHEN pa.season = 2020 THEN '2020'
        WHEN pa.season BETWEEN 2021 AND 2022 THEN '2021_2022'
        ELSE '2023_plus'
    END AS season_era,
    CASE
        WHEN pa.season = 2020 THEN 'pandemic_2020'
        WHEN pa.season BETWEEN 2021 AND 2022 THEN 'enforcement_transition'
        WHEN pa.season >= 2023 THEN 'post_2023_rules'
        ELSE 'pre_2020_rules'
    END AS rules_context_era,
    COALESCE(pa.start_bases, 0) AS start_bases,
    COALESCE(pa.balls, 0) AS balls,
    COALESCE(pa.strikes, 0) AS strikes,
    pa.home_score_before - pa.away_score_before AS home_score_diff,
    COALESCE(pa.batter_hand::text, 'U') AS batter_hand,
    COALESCE(pa.pitcher_hand::text, 'U') AS pitcher_hand,
    raw.sh_fl = 'T' AS is_sacrifice_hit,
    raw.sf_fl = 'T' AS is_sacrifice_fly,
    CASE
        WHEN raw.sh_fl = 'T' THEN 'sacrifice_hit'
        WHEN raw.sf_fl = 'T' THEN 'sacrifice_fly'
        WHEN pa.event_code = 20 THEN 'single'
        WHEN pa.event_code = 21 THEN 'double'
        WHEN pa.event_code = 22 THEN 'triple'
        WHEN pa.event_code = 23 THEN 'home_run'
        WHEN pa.event_code = 14 THEN 'walk'
        WHEN pa.event_code = 15 THEN 'intentional_walk'
        WHEN pa.event_code = 16 THEN 'hit_by_pitch'
        WHEN pa.event_code = 3 THEN 'strikeout'
        WHEN pa.event_code = 18 THEN 'error_on_batter'
        WHEN pa.event_code = 19 THEN 'fielders_choice'
        WHEN pa.event_code = 17 THEN 'interference'
        WHEN pa.event_code = 2 AND raw.battedball_cd = 'G' THEN 'ground_out'
        WHEN pa.event_code = 2 AND raw.battedball_cd = 'F' THEN 'fly_out'
        WHEN pa.event_code = 2 AND raw.battedball_cd = 'L' THEN 'line_out'
        WHEN pa.event_code = 2 AND raw.battedball_cd = 'P' THEN 'pop_out'
        WHEN pa.event_code = 2 THEN 'generic_out'
        ELSE 'other'
    END AS outcome_class,
    CASE
        WHEN pa.event_code IN (20, 21, 22, 23) THEN 'hit'
        WHEN pa.event_code IN (14, 15) THEN 'walk'
        WHEN pa.event_code IN (16, 17, 18) THEN 'reach_non_hit'
        WHEN pa.event_code IN (2, 3) OR raw.sh_fl = 'T' OR raw.sf_fl = 'T' THEN 'out'
        ELSE 'other'
    END AS outcome_group,
    pa.event_code IN (20, 21, 22, 23, 14, 15, 16) AS on_base_traditional,
    pa.event_code IN (20, 21, 22, 23, 14, 15, 16, 17, 18) AS reach_base_any,
    pa.event_code IN (20, 21, 22, 23) AS is_hit_outcome,
    pa.event_code IN (21, 22, 23) AS is_extra_base_hit_outcome,
    (
        pa.event_code IN (20, 21, 22, 23, 18, 19)
        OR (pa.event_code = 2 AND raw.battedball_cd IN ('G', 'F', 'L', 'P'))
    ) AS is_ball_in_play,
    CASE
        WHEN pa.event_code = 20 THEN 1
        WHEN pa.event_code = 21 THEN 2
        WHEN pa.event_code = 22 THEN 3
        WHEN pa.event_code = 23 THEN 4
        ELSE 0
    END AS outcome_total_bases
FROM core.plate_appearances AS pa
INNER JOIN raw_retrosheet.chadwick_events AS raw
    ON
        pa.game_id = raw.game_id
        AND raw.event_id::integer = pa.plate_appearance_id;

CREATE UNIQUE INDEX plate_appearance_outcome_examples_pk
ON features.plate_appearance_outcome_examples (game_id, plate_appearance_id);

CREATE INDEX plate_appearance_outcome_examples_target_idx
ON features.plate_appearance_outcome_examples (
    season,
    outcome_class,
    batter_hand,
    pitcher_hand,
    outs_before,
    start_bases,
    balls,
    strikes
);

CREATE INDEX plate_appearance_outcome_examples_player_idx
ON features.plate_appearance_outcome_examples (season, batter_id, pitcher_id)
WHERE batter_id IS NOT NULL AND pitcher_id IS NOT NULL;

INSERT INTO predictions.prediction_targets (
    target_id, target_name, target_family, description, question_template,
    required_context, training_label_sql, live_resolution_rule, default_model_family
)
VALUES (
    'pa_outcome_distribution',
    'Plate appearance outcome distribution',
    'plate_appearance',
    'Multiclass probability distribution over granular plate-appearance outcomes such as strikeout, walk, single, double, triple, home run, batted-ball out type, error, fielder choice, and sacrifice.',
    'What is the probability distribution over this plate appearance outcome?',
    '["batter_id", "pitcher_id", "batter_hand", "pitcher_hand", "game_state", "count", "park_id"]'::jsonb,
    'features.plate_appearance_outcome_examples.outcome_class',
    'Resolved from completed plate appearance event code plus Chadwick sacrifice and batted-ball fields.',
    'multiclass_gradient_boosted_trees'
)
ON CONFLICT (target_id) DO UPDATE
    SET
        target_name = excluded.target_name,
        target_family = excluded.target_family,
        description = excluded.description,
        question_template = excluded.question_template,
        required_context = excluded.required_context,
        training_label_sql = excluded.training_label_sql,
        live_resolution_rule = excluded.live_resolution_rule,
        default_model_family = excluded.default_model_family,
        is_active = excluded.is_active,
        updated_at = NOW();

CREATE OR REPLACE VIEW features.plate_appearance_outcome_validation_summary AS
SELECT
    'features.plate_appearance_outcome_examples' AS object_name,
    COUNT(*) AS row_count,
    COUNT(DISTINCT game_id) AS distinct_games,
    COUNT(DISTINCT outcome_class) AS distinct_outcome_classes,
    ROUND(AVG((pitch_seq_tx IS NOT NULL AND pitch_seq_tx <> '')::integer)::numeric, 4) AS pitch_sequence_coverage,
    ROUND(AVG((battedball_cd IS NOT NULL AND battedball_cd <> '')::integer)::numeric, 4) AS batted_ball_coverage
FROM features.plate_appearance_outcome_examples;

