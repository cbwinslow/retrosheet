CREATE SCHEMA IF NOT EXISTS features;

DROP VIEW IF EXISTS features.pitch_sequence_validation_summary;
DROP MATERIALIZED VIEW IF EXISTS features.pitch_sequence_examples;
DROP VIEW IF EXISTS features.pitch_sequence_symbol_reference;

CREATE VIEW features.pitch_sequence_symbol_reference AS
SELECT *
FROM (
    VALUES
        ('+', 'following pickoff throw by catcher', 'marker', false, false, false, false),
        ('*', 'blocked by catcher', 'marker', false, false, false, false),
        ('.', 'play not involving batter', 'marker', false, false, false, false),
        ('1', 'pickoff throw to first', 'pickoff_throw', false, false, false, false),
        ('2', 'pickoff throw to second', 'pickoff_throw', false, false, false, false),
        ('3', 'pickoff throw to third', 'pickoff_throw', false, false, false, false),
        ('>', 'runner going on pitch', 'runner_movement', false, false, false, false),
        ('A', 'automatic strike', 'automatic_strike', true, false, true, false),
        ('B', 'ball', 'ball', true, true, false, false),
        ('C', 'called strike', 'called_strike', true, false, true, false),
        ('F', 'foul', 'foul', true, false, true, false),
        ('H', 'hit batter', 'hit_by_pitch', true, false, false, false),
        ('I', 'intentional ball', 'intentional_ball', true, true, false, false),
        ('K', 'strike unknown type', 'strike_unknown', true, false, true, false),
        ('L', 'foul bunt', 'foul_bunt', true, false, true, false),
        ('M', 'missed bunt attempt', 'missed_bunt', true, false, true, false),
        ('N', 'no pitch', 'no_pitch', true, false, false, false),
        ('O', 'foul tip on bunt', 'foul_tip_bunt', true, false, true, false),
        ('P', 'pitchout', 'pitchout', true, true, false, false),
        ('Q', 'swinging on pitchout', 'swinging_pitchout', true, false, true, false),
        ('R', 'foul ball on pitchout', 'foul_pitchout', true, false, true, false),
        ('S', 'swinging strike', 'swinging_strike', true, false, true, false),
        ('T', 'foul tip', 'foul_tip', true, false, true, false),
        ('U', 'unknown or missed pitch', 'unknown_pitch', true, false, false, false),
        ('V', 'automatic or awarded ball', 'awarded_ball', true, true, false, false),
        ('X', 'ball put into play', 'in_play', true, false, false, true),
        ('Y', 'ball put into play on pitchout', 'in_play_pitchout', true, false, false, true)
) AS t(
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
    FROM features.plate_appearance_outcome_examples pa
    CROSS JOIN LATERAL regexp_split_to_table(pa.pitch_seq_tx, '') WITH ORDINALITY AS token(symbol, ordinality)
    WHERE pa.pitch_seq_tx IS NOT NULL
      AND pa.pitch_seq_tx <> ''
),
annotated AS (
    SELECT
        exploded.*,
        ref.symbol_meaning,
        COALESCE(ref.symbol_group, 'unknown_symbol') AS symbol_group,
        COALESCE(ref.is_pitch_symbol, false) AS is_pitch_symbol,
        COALESCE(ref.counts_toward_ball, false) AS counts_toward_ball,
        COALESCE(ref.counts_toward_strike, false) AS counts_toward_strike,
        COALESCE(ref.is_ball_in_play_symbol, false) AS is_ball_in_play_symbol
    FROM exploded
    LEFT JOIN features.pitch_sequence_symbol_reference ref
      ON ref.symbol = exploded.raw_symbol
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
    char_length(annotated.pitch_seq_tx) AS sequence_length,
    annotated.token_index,
    annotated.raw_symbol,
    annotated.symbol_meaning,
    annotated.symbol_group,
    annotated.is_pitch_symbol,
    annotated.counts_toward_ball,
    annotated.counts_toward_strike,
    annotated.is_ball_in_play_symbol,
    CASE
        WHEN annotated.is_pitch_symbol THEN
            sum(annotated.is_pitch_symbol::integer)
            OVER (
                PARTITION BY annotated.game_id, annotated.plate_appearance_id
                ORDER BY annotated.token_index
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ELSE NULL
    END AS pitch_number_in_pa,
    CASE
        WHEN annotated.is_pitch_symbol THEN
            max(annotated.token_index)
            FILTER (WHERE annotated.is_pitch_symbol)
            OVER (PARTITION BY annotated.game_id, annotated.plate_appearance_id) = annotated.token_index
        ELSE false
    END AS is_terminal_pitch_symbol,
    annotated.battedball_cd,
    annotated.battedball_loc_tx,
    annotated.outcome_class,
    annotated.outcome_group,
    annotated.is_ball_in_play,
    annotated.outcome_total_bases,
    annotated.final_home_win,
    annotated.final_batting_team_win
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
    count(*) AS row_count,
    count(*) FILTER (WHERE is_pitch_symbol) AS pitch_symbol_rows,
    count(DISTINCT (game_id, plate_appearance_id)) AS distinct_plate_appearances,
    round(avg(sequence_length)::numeric, 2) AS avg_sequence_length,
    round(avg((pitch_number_in_pa IS NOT NULL)::integer)::numeric, 4) AS pitch_symbol_share,
    round(avg((is_terminal_pitch_symbol)::integer)::numeric, 4) AS terminal_pitch_symbol_share,
    count(*) FILTER (WHERE symbol_group = 'unknown_symbol') AS unknown_symbol_rows
FROM features.pitch_sequence_examples;
