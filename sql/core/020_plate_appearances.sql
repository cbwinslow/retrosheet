CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS features;
CREATE SCHEMA IF NOT EXISTS predictions;

-- Drop dependent view that references the materialized view
DROP VIEW IF EXISTS core.plate_appearance_validation_summary;
-- Use CASCADE to ensure any lingering dependents are removed safely
DROP MATERIALIZED VIEW IF EXISTS features.plate_appearance_examples CASCADE;
DROP TABLE IF EXISTS core.plate_appearances CASCADE;

CREATE TABLE core.plate_appearances AS
SELECT
    events.game_id,
    events.event_id AS plate_appearance_id,
    row_number() OVER (PARTITION BY events.game_id ORDER BY events.event_sequence)::integer AS game_pa_number,
    row_number() OVER (
        PARTITION BY events.game_id, events.inning, events.is_bottom_inning
        ORDER BY events.event_sequence
    )::integer AS half_inning_pa_number,
    events.season,
    games.game_date,
    events.source_type,
    events.event_sequence,
    events.inning,
    events.is_bottom_inning,
    events.outs_before,
    events.balls,
    events.strikes,
    events.start_bases,
    events.end_bases,
    events.away_score_before,
    events.home_score_before,
    events.away_score_after,
    events.home_score_after,
    games.home_team_id,
    games.away_team_id,
    events.batting_team_id,
    events.fielding_team_id,
    events.batter_id,
    events.batter_hand,
    events.pitcher_id,
    events.pitcher_hand,
    events.event_code,
    events.event_text,
    events.is_at_bat,
    events.hit_value,
    events.is_hit,
    events.is_walk,
    events.is_strikeout,
    events.is_home_run,
    events.runs_on_play,
    events.rbi,
    games.home_win AS final_home_win,
    events.raw_loaded_at,
    events.event_code = 16 AS is_hit_by_pitch,
    events.event_code = 17 AS is_interference,
    (events.is_hit OR events.is_walk OR events.event_code IN (16, 17)) AS is_reach_base,
    events.hit_value >= 2 AS is_extra_base_hit,
    events.batting_team_id = games.winning_team_id AS final_batting_team_win,
    now() AS created_at
FROM core.events AS events
INNER JOIN core.games AS games ON events.game_id = games.game_id
WHERE events.is_plate_appearance;

ALTER TABLE core.plate_appearances
ALTER COLUMN game_id SET NOT NULL,
ALTER COLUMN plate_appearance_id SET NOT NULL,
ALTER COLUMN game_pa_number SET NOT NULL,
ALTER COLUMN half_inning_pa_number SET NOT NULL,
ALTER COLUMN season SET NOT NULL,
ALTER COLUMN game_date SET NOT NULL,
ALTER COLUMN source_type SET NOT NULL,
ALTER COLUMN event_sequence SET NOT NULL,
ALTER COLUMN inning SET NOT NULL,
ALTER COLUMN is_bottom_inning SET NOT NULL,
ALTER COLUMN outs_before SET NOT NULL,
ALTER COLUMN away_score_before SET NOT NULL,
ALTER COLUMN home_score_before SET NOT NULL,
ALTER COLUMN away_score_after SET NOT NULL,
ALTER COLUMN home_score_after SET NOT NULL,
ALTER COLUMN home_team_id SET NOT NULL,
ALTER COLUMN away_team_id SET NOT NULL,
ALTER COLUMN batting_team_id SET NOT NULL,
ALTER COLUMN fielding_team_id SET NOT NULL,
ALTER COLUMN is_at_bat SET NOT NULL,
ALTER COLUMN hit_value SET NOT NULL,
ALTER COLUMN is_hit SET NOT NULL,
ALTER COLUMN is_walk SET NOT NULL,
ALTER COLUMN is_strikeout SET NOT NULL,
ALTER COLUMN is_home_run SET NOT NULL,
ALTER COLUMN is_hit_by_pitch SET NOT NULL,
ALTER COLUMN is_interference SET NOT NULL,
ALTER COLUMN is_reach_base SET NOT NULL,
ALTER COLUMN is_extra_base_hit SET NOT NULL,
ALTER COLUMN runs_on_play SET NOT NULL,
ALTER COLUMN rbi SET NOT NULL,
ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE core.plate_appearances
ADD CONSTRAINT plate_appearances_pk PRIMARY KEY (game_id, plate_appearance_id),
ADD CONSTRAINT plate_appearances_event_fk
FOREIGN KEY (game_id, plate_appearance_id) REFERENCES core.events (game_id, event_id) ON DELETE CASCADE,
ADD CONSTRAINT plate_appearances_game_fk
FOREIGN KEY (game_id) REFERENCES core.games (game_id) ON DELETE CASCADE,
ADD CONSTRAINT plate_appearances_batting_team_fk
FOREIGN KEY (batting_team_id) REFERENCES core.teams (retrosheet_team_id),
ADD CONSTRAINT plate_appearances_fielding_team_fk
FOREIGN KEY (fielding_team_id) REFERENCES core.teams (retrosheet_team_id),
ADD CONSTRAINT plate_appearances_batter_fk
FOREIGN KEY (batter_id) REFERENCES core.players (retrosheet_player_id),
ADD CONSTRAINT plate_appearances_pitcher_fk
FOREIGN KEY (pitcher_id) REFERENCES core.players (retrosheet_player_id),
ADD CONSTRAINT plate_appearances_count_check CHECK (
    (balls IS NULL OR balls BETWEEN 0 AND 4)
    AND (strikes IS NULL OR strikes BETWEEN 0 AND 3)
),
ADD CONSTRAINT plate_appearances_hit_value_check CHECK (hit_value BETWEEN 0 AND 4);

CREATE INDEX plate_appearances_game_order_idx
ON core.plate_appearances (game_id, game_pa_number);

CREATE INDEX plate_appearances_half_inning_idx
ON core.plate_appearances (game_id, inning, is_bottom_inning, half_inning_pa_number);

CREATE INDEX plate_appearances_batter_season_idx
ON core.plate_appearances (batter_id, season) WHERE batter_id IS NOT NULL;

CREATE INDEX plate_appearances_pitcher_season_idx
ON core.plate_appearances (pitcher_id, season) WHERE pitcher_id IS NOT NULL;

CREATE INDEX plate_appearances_matchup_idx
ON core.plate_appearances (season, batter_hand, pitcher_hand, outs_before, start_bases);

CREATE MATERIALIZED VIEW features.plate_appearance_examples AS
SELECT
    game_id,
    plate_appearance_id,
    season,
    game_date,
    inning,
    is_bottom_inning,
    outs_before,
    batting_team_id,
    fielding_team_id,
    home_team_id,
    away_team_id,
    batter_id,
    pitcher_id,
    is_at_bat,
    is_hit,
    is_walk,
    is_strikeout,
    is_home_run,
    is_hit_by_pitch,
    is_reach_base,
    is_extra_base_hit,
    hit_value,
    runs_on_play,
    rbi,
    final_home_win,
    final_batting_team_win,
    coalesce(start_bases, 0) AS start_bases,
    coalesce(balls, 0) AS balls,
    coalesce(strikes, 0) AS strikes,
    home_score_before - away_score_before AS home_score_diff,
    coalesce(batter_hand::text, 'U') AS batter_hand,
    coalesce(pitcher_hand::text, 'U') AS pitcher_hand
FROM core.plate_appearances;

CREATE UNIQUE INDEX plate_appearance_examples_pk
ON features.plate_appearance_examples (game_id, plate_appearance_id);

CREATE INDEX plate_appearance_examples_target_idx
ON features.plate_appearance_examples (season, batter_hand, pitcher_hand, outs_before, start_bases);

INSERT INTO predictions.prediction_targets (
    target_id, target_name, target_family, description, question_template,
    required_context, training_label_sql, live_resolution_rule, default_model_family
)
VALUES
(
    'pa_batter_hit',
    'Batter gets a hit',
    'plate_appearance',
    'Probability that the batter records a hit.',
    'What is the probability this batter gets a hit?',
    '["batter_id", "pitcher_id", "batter_hand", "pitcher_hand", "game_state"]'::jsonb,
    'features.plate_appearance_examples.is_hit',
    'Resolved from the completed plate appearance.',
    'gradient_boosted_trees'
),
(
    'pa_batter_walk',
    'Batter draws a walk',
    'plate_appearance',
    'Probability that the batter draws a walk.',
    'What is the probability this batter draws a walk?',
    '["batter_id", "pitcher_id", "batter_hand", "pitcher_hand", "game_state"]'::jsonb,
    'features.plate_appearance_examples.is_walk',
    'Resolved from the completed plate appearance.',
    'gradient_boosted_trees'
),
(
    'pa_batter_strikeout',
    'Batter strikes out',
    'plate_appearance',
    'Probability that the batter strikes out.',
    'What is the probability this batter strikes out?',
    '["batter_id", "pitcher_id", "batter_hand", "pitcher_hand", "game_state"]'::jsonb,
    'features.plate_appearance_examples.is_strikeout',
    'Resolved from the completed plate appearance.',
    'gradient_boosted_trees'
),
(
    'pa_batter_home_run',
    'Batter hits a home run',
    'plate_appearance',
    'Probability that the batter hits a home run.',
    'What is the probability this batter hits a home run?',
    '["batter_id", "pitcher_id", "batter_hand", "pitcher_hand", "game_state"]'::jsonb,
    'features.plate_appearance_examples.is_home_run',
    'Resolved from the completed plate appearance.',
    'gradient_boosted_trees'
),
(
    'pa_batter_reach_base',
    'Batter reaches base',
    'plate_appearance',
    'Probability that the batter reaches base by hit, walk, hit-by-pitch, or interference.',
    'What is the probability this batter reaches base?',
    '["batter_id", "pitcher_id", "batter_hand", "pitcher_hand", "game_state"]'::jsonb,
    'features.plate_appearance_examples.is_reach_base',
    'Resolved from the completed plate appearance.',
    'gradient_boosted_trees'
),
(
    'pa_batter_extra_base_hit',
    'Batter gets an extra-base hit',
    'plate_appearance',
    'Probability that the batter records a double, triple, or home run.',
    'What is the probability this batter gets an extra-base hit?',
    '["batter_id", "pitcher_id", "batter_hand", "pitcher_hand", "game_state"]'::jsonb,
    'features.plate_appearance_examples.is_extra_base_hit',
    'Resolved from the completed plate appearance.',
    'gradient_boosted_trees'
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
        updated_at = now();

CREATE OR REPLACE VIEW core.plate_appearance_validation_summary AS
SELECT
    'core.plate_appearances' AS object_name,
    count(*) AS row_count,
    count(DISTINCT game_id) AS distinct_games
FROM core.plate_appearances
UNION ALL
SELECT
    'features.plate_appearance_examples',
    count(*),
    count(DISTINCT game_id)
FROM features.plate_appearance_examples;
