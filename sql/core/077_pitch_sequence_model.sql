-- File: sql/core/077_pitch_sequence_model.sql
-- Purpose: Create pitch sequence model tables, views, and Markov state features
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS features;

DROP VIEW IF EXISTS features.pitch_sequence_validation_summary;
DROP MATERIALIZED VIEW IF EXISTS features.pitch_sequence_examples;
DROP VIEW IF EXISTS features.pitch_sequence_symbol_reference;

CREATE VIEW features.pitch_sequence_symbol_reference AS
SELECT *
FROM (
    VALUES
    ('+', 'following pickoff throw by catcher', 'marker', FALSE, FALSE, FALSE, FALSE),
    ('*', 'blocked by catcher', 'marker', FALSE, FALSE, FALSE, FALSE),
    ('.', 'play not involving batter', 'marker', FALSE, FALSE, FALSE, FALSE),
    ('1', 'pickoff throw to first', 'pickoff_throw', FALSE, FALSE, FALSE, FALSE),
    ('2', 'pickoff throw to second', 'pickoff_throw', FALSE, FALSE, FALSE, FALSE),
    ('3', 'pickoff throw to third', 'pickoff_throw', FALSE, FALSE, FALSE, FALSE),
    ('>', 'runner going on pitch', 'runner_movement', FALSE, FALSE, FALSE, FALSE),
    ('A', 'automatic strike', 'automatic_strike', TRUE, FALSE, TRUE, FALSE),
    ('B', 'ball', 'ball', TRUE, TRUE, FALSE, FALSE),
    ('C', 'called strike', 'called_strike', TRUE, FALSE, TRUE, FALSE),
    ('F', 'foul', 'foul', TRUE, FALSE, TRUE, FALSE),
    ('H', 'hit batter', 'hit_by_pitch', TRUE, FALSE, FALSE, FALSE),
    ('I', 'intentional ball', 'intentional_ball', TRUE, TRUE, FALSE, FALSE),
    ('K', 'strike unknown type', 'strike_unknown', TRUE, FALSE, TRUE, FALSE),
    ('L', 'foul bunt', 'foul_bunt', TRUE, FALSE, TRUE, FALSE),
    ('M', 'missed bunt attempt', 'missed_bunt', TRUE, FALSE, TRUE, FALSE),
    ('N', 'no pitch', 'no_pitch', TRUE, FALSE, FALSE, FALSE),
    ('O', 'foul tip on bunt', 'foul_tip_bunt', TRUE, FALSE, TRUE, FALSE),
    ('P', 'pitchout', 'pitchout', TRUE, TRUE, FALSE, FALSE),
    ('Q', 'swinging on pitchout', 'swinging_pitchout', TRUE, FALSE, TRUE, FALSE),
    ('R', 'foul ball on pitchout', 'foul_pitchout', TRUE, FALSE, TRUE, FALSE),
    ('S', 'swinging strike', 'swinging_strike', TRUE, FALSE, TRUE, FALSE),
    ('T', 'foul tip', 'foul_tip', TRUE, FALSE, TRUE, FALSE),
    ('U', 'unknown or missed pitch', 'unknown_pitch', TRUE, FALSE, FALSE, FALSE),
    ('V', 'automatic or awarded ball', 'awarded_ball', TRUE, TRUE, FALSE, FALSE),
    ('X', 'ball put into play', 'in_play', TRUE, FALSE, FALSE, TRUE),
    ('Y', 'ball put into play on pitchout', 'in_play_pitchout', TRUE, FALSE, FALSE, TRUE)
) AS t (
    symbol,
    symbol_meaning,
    symbol_group,
    is_pitch_symbol,
    counts_toward_ball,
    counts_toward_strike,
    is_ball_in_play_symbol
);

CREATE MATERIALIZED VIEW features.pitch_sequence_examples AS
WITH exploded AS (
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
        pa.start_bases,
        pa.balls AS balls_at_pa_end,
        pa.strikes AS strikes_at_pa_end,
        pa.home_score_diff,
        pa.away_score_before,
        pa.home_score_before,
        pa.batting_team_id,
        pa.fielding_team_id,
        pa.home_team_id,
        pa.away_team_id,
        pa.batter_id,
        pa.batter_hand,
        pa.pitcher_id,
        pa.pitcher_hand,
        pa.event_code,
        pa.pitch_seq_tx,
        pa.battedball_cd,
        pa.battedball_loc_tx,
        pa.outcome_class,
        pa.outcome_group,
        pa.is_ball_in_play,
        pa.outcome_total_bases,
        pa.final_home_win,
        pa.final_batting_team_win,
        ordinality::integer AS token_index,
        token.symbol AS raw_symbol
    FROM features.plate_appearance_outcome_examples AS pa
    CROSS JOIN LATERAL REGEXP_SPLIT_TO_TABLE(pa.pitch_seq_tx, '') WITH ORDINALITY AS token (symbol, ordinality)
    WHERE
        pa.pitch_seq_tx IS NOT NULL
        AND pa.pitch_seq_tx <> ''
),

annotated AS (
    SELECT
        exploded.*,
        ref.symbol_meaning,
        COALESCE(ref.symbol_group, 'unknown_symbol') AS symbol_group,
        COALESCE(ref.is_pitch_symbol, FALSE) AS is_pitch_symbol,
        COALESCE(ref.counts_toward_ball, FALSE) AS counts_toward_ball,
        COALESCE(ref.counts_toward_strike, FALSE) AS counts_toward_strike,
        COALESCE(ref.is_ball_in_play_symbol, FALSE) AS is_ball_in_play_symbol
    FROM exploded
    LEFT JOIN features.pitch_sequence_symbol_reference AS ref
        ON exploded.raw_symbol = ref.symbol
)

SELECT
    annotated.game_id,
    annotated.plate_appearance_id,
    annotated.game_pa_number,
    annotated.half_inning_pa_number,
    annotated.season,
    annotated.game_date,
    annotated.inning,
    annotated.is_bottom_inning,
    annotated.outs_before,
    annotated.start_bases,
    annotated.balls_at_pa_end,
    annotated.strikes_at_pa_end,
    annotated.home_score_diff,
    annotated.away_score_before,
    annotated.home_score_before,
    annotated.batting_team_id,
    annotated.fielding_team_id,
    annotated.home_team_id,
    annotated.away_team_id,
    annotated.batter_id,
    annotated.batter_hand,
    annotated.pitcher_id,
    annotated.pitcher_hand,
    annotated.event_code,
    annotated.pitch_seq_tx,
    annotated.token_index,
    annotated.raw_symbol,
    annotated.symbol_meaning,
    annotated.symbol_group,
    annotated.is_pitch_symbol,
    annotated.counts_toward_ball,
    annotated.counts_toward_strike,
    annotated.is_ball_in_play_symbol,
    annotated.battedball_cd,
    annotated.battedball_loc_tx,
    annotated.outcome_class,
    annotated.outcome_group,
    annotated.is_ball_in_play,
    annotated.outcome_total_bases,
    annotated.final_home_win,
    annotated.final_batting_team_win,
    CHAR_LENGTH(annotated.pitch_seq_tx) AS sequence_length,
    CASE
        WHEN annotated.is_pitch_symbol
            THEN
                SUM(annotated.is_pitch_symbol::integer)
                    OVER (
                        PARTITION BY annotated.game_id, annotated.plate_appearance_id
                        ORDER BY annotated.token_index
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    )
    END AS pitch_number_in_pa,
    CASE
        WHEN annotated.is_pitch_symbol
            THEN
                MAX(annotated.token_index)
                FILTER (WHERE annotated.is_pitch_symbol)
                    OVER (PARTITION BY annotated.game_id, annotated.plate_appearance_id)
                = annotated.token_index
        ELSE FALSE
    END AS is_terminal_pitch_symbol
FROM annotated;

CREATE UNIQUE INDEX pitch_sequence_examples_pk
ON features.pitch_sequence_examples (game_id, plate_appearance_id, token_index);

CREATE INDEX pitch_sequence_examples_pitch_idx
ON features.pitch_sequence_examples (season, symbol_group, outcome_class, pitch_number_in_pa)
WHERE is_pitch_symbol;

CREATE INDEX pitch_sequence_examples_player_idx
ON features.pitch_sequence_examples (season, batter_id, pitcher_id)
WHERE batter_id IS NOT NULL AND pitcher_id IS NOT NULL;

CREATE OR REPLACE VIEW features.pitch_sequence_validation_summary AS
SELECT
    'features.pitch_sequence_examples' AS object_name,
    COUNT(*) AS row_count,
    COUNT(*) FILTER (WHERE is_pitch_symbol) AS pitch_symbol_rows,
    COUNT(DISTINCT game_id, plate_appearance_id) AS distinct_plate_appearances,
    ROUND(AVG(sequence_length)::numeric, 2) AS avg_sequence_length,
    ROUND(AVG((pitch_number_in_pa IS NOT NULL)::integer)::numeric, 4) AS pitch_symbol_share,
    ROUND(AVG((is_terminal_pitch_symbol)::integer)::numeric, 4) AS terminal_pitch_symbol_share,
    COUNT(*) FILTER (WHERE symbol_group = 'unknown_symbol') AS unknown_symbol_rows
FROM features.pitch_sequence_examples;
