-- File: sql/core/078_plate_appearance_outcome_grouped.sql
-- Purpose: Create grouped PA outcome model views and evaluation tables
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS features;

DROP VIEW IF EXISTS features.plate_appearance_outcome_grouped_validation_summary;
DROP MATERIALIZED VIEW IF EXISTS features.plate_appearance_outcome_grouped_examples;

CREATE MATERIALIZED VIEW features.plate_appearance_outcome_grouped_examples AS
SELECT
    outcome.game_id,
    outcome.plate_appearance_id,
    outcome.game_pa_number,
    outcome.half_inning_pa_number,
    outcome.season,
    outcome.game_date,
    outcome.season_era,
    outcome.rules_context_era,
    outcome.inning,
    outcome.is_bottom_inning,
    outcome.outs_before,
    outcome.start_bases,
    outcome.balls,
    outcome.strikes,
    outcome.home_score_diff,
    outcome.away_score_before,
    outcome.home_score_before,
    outcome.batting_team_id,
    outcome.fielding_team_id,
    outcome.home_team_id,
    outcome.away_team_id,
    outcome.batter_id,
    outcome.batter_hand,
    outcome.pitcher_id,
    outcome.pitcher_hand,
    outcome.event_code,
    outcome.pitch_seq_tx,
    outcome.battedball_cd,
    outcome.battedball_loc_tx,
    outcome.is_sacrifice_hit,
    outcome.is_sacrifice_fly,
    outcome.is_at_bat,
    outcome.hit_value,
    outcome.is_hit,
    outcome.is_walk,
    outcome.is_strikeout,
    outcome.is_home_run,
    outcome.is_hit_by_pitch,
    outcome.is_interference,
    outcome.is_reach_base,
    outcome.is_extra_base_hit,
    outcome.runs_on_play,
    outcome.rbi,
    outcome.outcome_class AS raw_outcome_class,
    outcome.outcome_group AS raw_outcome_group,
    outcome.on_base_traditional,
    outcome.reach_base_any,
    outcome.is_hit_outcome,
    outcome.is_extra_base_hit_outcome,
    outcome.is_ball_in_play,
    outcome.outcome_total_bases,
    outcome.final_home_win,
    outcome.final_batting_team_win,
    CASE
        WHEN outcome.outcome_class IN ('single', 'double', 'triple', 'home_run') THEN outcome.outcome_class
        WHEN outcome.outcome_class IN ('walk', 'intentional_walk') THEN 'walk'
        WHEN outcome.outcome_class = 'hit_by_pitch' THEN 'hit_by_pitch'
        WHEN outcome.outcome_class = 'strikeout' THEN 'strikeout'
        WHEN outcome.outcome_class = 'ground_out' THEN 'ground_out'
        WHEN outcome.outcome_class IN ('fly_out', 'line_out', 'pop_out', 'generic_out') THEN 'air_or_other_out'
        WHEN outcome.outcome_class IN ('error_on_batter', 'fielders_choice') THEN 'reach_on_error_or_fc'
        WHEN outcome.outcome_class IN ('sacrifice_hit', 'sacrifice_fly') THEN 'productive_out'
        ELSE 'other_rare'
    END AS grouped_outcome_class,
    CASE
        WHEN outcome.outcome_class IN ('single', 'double', 'triple', 'home_run') THEN 'hit'
        WHEN outcome.outcome_class IN ('walk', 'intentional_walk', 'hit_by_pitch') THEN 'free_pass'
        WHEN outcome.outcome_class IN ('error_on_batter', 'fielders_choice', 'interference') THEN 'non_hit_reach'
        WHEN outcome.outcome_class IN (
            'strikeout',
            'ground_out',
            'fly_out',
            'line_out',
            'pop_out',
            'generic_out',
            'sacrifice_hit',
            'sacrifice_fly'
        ) THEN 'out'
        ELSE 'other'
    END AS grouped_outcome_family
FROM features.plate_appearance_outcome_examples AS outcome;

CREATE UNIQUE INDEX plate_appearance_outcome_grouped_examples_pk
ON features.plate_appearance_outcome_grouped_examples (game_id, plate_appearance_id);

CREATE INDEX plate_appearance_outcome_grouped_examples_target_idx
ON features.plate_appearance_outcome_grouped_examples (
    season,
    grouped_outcome_class,
    batter_hand,
    pitcher_hand,
    outs_before,
    start_bases,
    balls,
    strikes
);

CREATE INDEX plate_appearance_outcome_grouped_examples_player_idx
ON features.plate_appearance_outcome_grouped_examples (season, batter_id, pitcher_id)
WHERE batter_id IS NOT NULL AND pitcher_id IS NOT NULL;

CREATE OR REPLACE VIEW features.plate_appearance_outcome_grouped_validation_summary AS
SELECT
    'features.plate_appearance_outcome_grouped_examples' AS object_name,
    count(*) AS row_count,
    count(DISTINCT game_id) AS distinct_games,
    count(DISTINCT grouped_outcome_class) AS distinct_grouped_outcomes,
    count(DISTINCT raw_outcome_class) AS distinct_raw_outcomes,
    round(avg((pitch_seq_tx IS NOT NULL AND pitch_seq_tx <> '')::integer)::numeric, 4) AS pitch_sequence_coverage,
    round(avg((battedball_cd IS NOT NULL AND battedball_cd <> '')::integer)::numeric, 4) AS batted_ball_coverage
FROM features.plate_appearance_outcome_grouped_examples;

