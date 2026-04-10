CREATE SCHEMA IF NOT EXISTS features;
CREATE SCHEMA IF NOT EXISTS predictions;

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
    COALESCE(pa.start_bases, 0) AS start_bases,
    COALESCE(pa.balls, 0) AS balls,
    COALESCE(pa.strikes, 0) AS strikes,
    pa.home_score_before - pa.away_score_before AS home_score_diff,
    pa.away_score_before,
    pa.home_score_before,
    pa.batting_team_id,
    pa.fielding_team_id,
    pa.home_team_id,
    pa.away_team_id,
    pa.batter_id,
    COALESCE(pa.batter_hand::text, 'U') AS batter_hand,
    pa.pitcher_id,
    COALESCE(pa.pitcher_hand::text, 'U') AS pitcher_hand,
    pa.event_code,
    raw.pitch_seq_tx,
    raw.battedball_cd,
    raw.battedball_loc_tx,
    raw.sh_fl = 'T' AS is_sacrifice_hit,
    raw.sf_fl = 'T' AS is_sacrifice_fly,
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
    END AS outcome_total_bases,
    pa.final_home_win,
    pa.final_batting_team_win
FROM core.plate_appearances pa
JOIN raw_retrosheet.chadwick_events raw
  ON raw.game_id = pa.game_id
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
SET target_name = EXCLUDED.target_name,
    target_family = EXCLUDED.target_family,
    description = EXCLUDED.description,
    question_template = EXCLUDED.question_template,
    required_context = EXCLUDED.required_context,
    training_label_sql = EXCLUDED.training_label_sql,
    live_resolution_rule = EXCLUDED.live_resolution_rule,
    default_model_family = EXCLUDED.default_model_family,
    is_active = EXCLUDED.is_active,
    updated_at = now();

CREATE OR REPLACE VIEW features.plate_appearance_outcome_validation_summary AS
SELECT
    'features.plate_appearance_outcome_examples' AS object_name,
    count(*) AS row_count,
    count(DISTINCT game_id) AS distinct_games,
    count(DISTINCT outcome_class) AS distinct_outcome_classes,
    round(avg((pitch_seq_tx IS NOT NULL AND pitch_seq_tx <> '')::integer)::numeric, 4) AS pitch_sequence_coverage,
    round(avg((battedball_cd IS NOT NULL AND battedball_cd <> '')::integer)::numeric, 4) AS batted_ball_coverage
FROM features.plate_appearance_outcome_examples;
