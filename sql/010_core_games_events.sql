CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS features;
CREATE SCHEMA IF NOT EXISTS models;
CREATE SCHEMA IF NOT EXISTS predictions;
CREATE SCHEMA IF NOT EXISTS raw_markets;
CREATE SCHEMA IF NOT EXISTS market_edges;
CREATE SCHEMA IF NOT EXISTS chat;

CREATE OR REPLACE FUNCTION core.safe_int(value text)
RETURNS integer
LANGUAGE sql
IMMUTABLE
RETURNS NULL ON NULL INPUT
AS $$
    SELECT CASE WHEN btrim(value) ~ '^-?[0-9]+$' THEN btrim(value)::integer END
$$;

CREATE OR REPLACE FUNCTION core.safe_date_yyyymmdd(value text)
RETURNS date
LANGUAGE sql
IMMUTABLE
RETURNS NULL ON NULL INPUT
AS $$
    SELECT CASE
        WHEN btrim(value) ~ '^[0-9]{8}$'
        THEN to_date(btrim(value), 'YYYYMMDD')
    END
$$;

CREATE TABLE IF NOT EXISTS core.teams (
    retrosheet_team_id text PRIMARY KEY,
    first_season integer,
    last_season integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO core.teams (retrosheet_team_id, first_season, last_season)
SELECT team_id, min(season), max(season)
FROM (
    SELECT away_team_id AS team_id, season FROM raw_retrosheet.chadwick_games WHERE away_team_id <> ''
    UNION ALL
    SELECT home_team_id AS team_id, season FROM raw_retrosheet.chadwick_games WHERE home_team_id <> ''
    UNION ALL
    SELECT bat_team_id AS team_id, season FROM raw_retrosheet.chadwick_events WHERE bat_team_id <> ''
    UNION ALL
    SELECT fld_team_id AS team_id, season FROM raw_retrosheet.chadwick_events WHERE fld_team_id <> ''
) teams
WHERE team_id IS NOT NULL
GROUP BY team_id
ON CONFLICT (retrosheet_team_id) DO UPDATE
SET first_season = LEAST(core.teams.first_season, EXCLUDED.first_season),
    last_season = GREATEST(core.teams.last_season, EXCLUDED.last_season),
    updated_at = now();

CREATE TABLE IF NOT EXISTS core.parks (
    retrosheet_park_id text PRIMARY KEY,
    first_season integer,
    last_season integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO core.parks (retrosheet_park_id, first_season, last_season)
SELECT park_id, min(season), max(season)
FROM raw_retrosheet.chadwick_games
WHERE park_id IS NOT NULL AND park_id <> ''
GROUP BY park_id
ON CONFLICT (retrosheet_park_id) DO UPDATE
SET first_season = LEAST(core.parks.first_season, EXCLUDED.first_season),
    last_season = GREATEST(core.parks.last_season, EXCLUDED.last_season),
    updated_at = now();

CREATE TABLE IF NOT EXISTS core.players (
    retrosheet_player_id text PRIMARY KEY,
    player_name text,
    bats char(1),
    throws char(1),
    first_season integer,
    last_season integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT players_bats_check CHECK (bats IS NULL OR bats IN ('L', 'R', 'B')),
    CONSTRAINT players_throws_check CHECK (throws IS NULL OR throws IN ('L', 'R'))
);

WITH player_id_observations AS (
    SELECT bat_id AS player_id, season, bat_hand_cd AS bats, NULL::text AS throws FROM raw_retrosheet.chadwick_events WHERE bat_id <> ''
    UNION ALL SELECT resp_bat_id, season, resp_bat_hand_cd, NULL FROM raw_retrosheet.chadwick_events WHERE resp_bat_id <> ''
    UNION ALL SELECT pit_id, season, NULL, pit_hand_cd FROM raw_retrosheet.chadwick_events WHERE pit_id <> ''
    UNION ALL SELECT resp_pit_id, season, NULL, resp_pit_hand_cd FROM raw_retrosheet.chadwick_events WHERE resp_pit_id <> ''
    UNION ALL SELECT base1_run_id, season, NULL, NULL FROM raw_retrosheet.chadwick_events WHERE base1_run_id <> ''
    UNION ALL SELECT base2_run_id, season, NULL, NULL FROM raw_retrosheet.chadwick_events WHERE base2_run_id <> ''
    UNION ALL SELECT base3_run_id, season, NULL, NULL FROM raw_retrosheet.chadwick_events WHERE base3_run_id <> ''
    UNION ALL SELECT pos2_fld_id, season, NULL, NULL FROM raw_retrosheet.chadwick_events WHERE pos2_fld_id <> ''
    UNION ALL SELECT pos3_fld_id, season, NULL, NULL FROM raw_retrosheet.chadwick_events WHERE pos3_fld_id <> ''
    UNION ALL SELECT pos4_fld_id, season, NULL, NULL FROM raw_retrosheet.chadwick_events WHERE pos4_fld_id <> ''
    UNION ALL SELECT pos5_fld_id, season, NULL, NULL FROM raw_retrosheet.chadwick_events WHERE pos5_fld_id <> ''
    UNION ALL SELECT pos6_fld_id, season, NULL, NULL FROM raw_retrosheet.chadwick_events WHERE pos6_fld_id <> ''
    UNION ALL SELECT pos7_fld_id, season, NULL, NULL FROM raw_retrosheet.chadwick_events WHERE pos7_fld_id <> ''
    UNION ALL SELECT pos8_fld_id, season, NULL, NULL FROM raw_retrosheet.chadwick_events WHERE pos8_fld_id <> ''
    UNION ALL SELECT pos9_fld_id, season, NULL, NULL FROM raw_retrosheet.chadwick_events WHERE pos9_fld_id <> ''
),
player_names AS (
    SELECT away_lineup1_bat_id AS player_id, away_lineup1_bat_name_tx AS player_name FROM raw_retrosheet.chadwick_games WHERE away_lineup1_bat_id <> ''
    UNION ALL SELECT away_lineup2_bat_id, away_lineup2_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE away_lineup2_bat_id <> ''
    UNION ALL SELECT away_lineup3_bat_id, away_lineup3_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE away_lineup3_bat_id <> ''
    UNION ALL SELECT away_lineup4_bat_id, away_lineup4_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE away_lineup4_bat_id <> ''
    UNION ALL SELECT away_lineup5_bat_id, away_lineup5_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE away_lineup5_bat_id <> ''
    UNION ALL SELECT away_lineup6_bat_id, away_lineup6_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE away_lineup6_bat_id <> ''
    UNION ALL SELECT away_lineup7_bat_id, away_lineup7_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE away_lineup7_bat_id <> ''
    UNION ALL SELECT away_lineup8_bat_id, away_lineup8_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE away_lineup8_bat_id <> ''
    UNION ALL SELECT away_lineup9_bat_id, away_lineup9_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE away_lineup9_bat_id <> ''
    UNION ALL SELECT home_lineup1_bat_id, home_lineup1_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE home_lineup1_bat_id <> ''
    UNION ALL SELECT home_lineup2_bat_id, home_lineup2_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE home_lineup2_bat_id <> ''
    UNION ALL SELECT home_lineup3_bat_id, home_lineup3_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE home_lineup3_bat_id <> ''
    UNION ALL SELECT home_lineup4_bat_id, home_lineup4_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE home_lineup4_bat_id <> ''
    UNION ALL SELECT home_lineup5_bat_id, home_lineup5_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE home_lineup5_bat_id <> ''
    UNION ALL SELECT home_lineup6_bat_id, home_lineup6_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE home_lineup6_bat_id <> ''
    UNION ALL SELECT home_lineup7_bat_id, home_lineup7_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE home_lineup7_bat_id <> ''
    UNION ALL SELECT home_lineup8_bat_id, home_lineup8_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE home_lineup8_bat_id <> ''
    UNION ALL SELECT home_lineup9_bat_id, home_lineup9_bat_name_tx FROM raw_retrosheet.chadwick_games WHERE home_lineup9_bat_id <> ''
),
player_rollup AS (
    SELECT
        player_id,
        min(season) AS first_season,
        max(season) AS last_season,
        mode() WITHIN GROUP (ORDER BY NULLIF(bats, '')) AS bats,
        mode() WITHIN GROUP (ORDER BY NULLIF(throws, '')) AS throws
    FROM player_id_observations
    WHERE player_id IS NOT NULL
    GROUP BY player_id
),
name_rollup AS (
    SELECT DISTINCT ON (player_id)
        player_id,
        NULLIF(player_name, '') AS player_name
    FROM player_names
    WHERE player_id IS NOT NULL AND player_name IS NOT NULL AND player_name <> ''
    ORDER BY player_id, length(player_name) DESC
)
INSERT INTO core.players (retrosheet_player_id, player_name, bats, throws, first_season, last_season)
SELECT
    player_rollup.player_id,
    name_rollup.player_name,
    CASE WHEN player_rollup.bats IN ('L', 'R', 'B') THEN player_rollup.bats::char(1) END,
    CASE WHEN player_rollup.throws IN ('L', 'R') THEN player_rollup.throws::char(1) END,
    player_rollup.first_season,
    player_rollup.last_season
FROM player_rollup
LEFT JOIN name_rollup USING (player_id)
ON CONFLICT (retrosheet_player_id) DO UPDATE
SET player_name = COALESCE(EXCLUDED.player_name, core.players.player_name),
    bats = COALESCE(EXCLUDED.bats, core.players.bats),
    throws = COALESCE(EXCLUDED.throws, core.players.throws),
    first_season = LEAST(core.players.first_season, EXCLUDED.first_season),
    last_season = GREATEST(core.players.last_season, EXCLUDED.last_season),
    updated_at = now();

DROP MATERIALIZED VIEW IF EXISTS features.game_outcome_examples;
DROP VIEW IF EXISTS core.validation_summary;
DROP VIEW IF EXISTS core.game_states;
DROP TABLE IF EXISTS core.events CASCADE;
DROP TABLE IF EXISTS core.games CASCADE;

CREATE TABLE core.games (
    game_id text PRIMARY KEY,
    season integer NOT NULL,
    source_type text NOT NULL,
    game_date date NOT NULL,
    game_number smallint,
    day_of_week text,
    start_time text,
    doubleheader_flag text,
    day_night text,
    away_team_id text NOT NULL REFERENCES core.teams (retrosheet_team_id),
    home_team_id text NOT NULL REFERENCES core.teams (retrosheet_team_id),
    park_id text REFERENCES core.parks (retrosheet_park_id),
    away_starting_pitcher_id text REFERENCES core.players (retrosheet_player_id),
    home_starting_pitcher_id text REFERENCES core.players (retrosheet_player_id),
    attendance integer,
    temperature_f integer,
    wind_direction text,
    wind_speed_mph integer,
    field_condition text,
    precipitation text,
    sky_condition text,
    duration_minutes integer,
    innings integer,
    away_score integer NOT NULL,
    home_score integer NOT NULL,
    away_hits integer,
    home_hits integer,
    away_errors integer,
    home_errors integer,
    away_lob integer,
    home_lob integer,
    winning_team_id text REFERENCES core.teams (retrosheet_team_id),
    home_win boolean,
    win_pitcher_id text REFERENCES core.players (retrosheet_player_id),
    loss_pitcher_id text REFERENCES core.players (retrosheet_player_id),
    save_pitcher_id text REFERENCES core.players (retrosheet_player_id),
    raw_loaded_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT games_score_check CHECK (away_score >= 0 AND home_score >= 0)
);

INSERT INTO core.games (
    game_id, season, source_type, game_date, game_number, day_of_week, start_time,
    doubleheader_flag, day_night, away_team_id, home_team_id, park_id,
    away_starting_pitcher_id, home_starting_pitcher_id, attendance, temperature_f,
    wind_direction, wind_speed_mph, field_condition, precipitation, sky_condition,
    duration_minutes, innings, away_score, home_score, away_hits, home_hits,
    away_errors, home_errors, away_lob, home_lob, winning_team_id, home_win,
    win_pitcher_id, loss_pitcher_id, save_pitcher_id, raw_loaded_at
)
SELECT
    game_id,
    season,
    source_type,
    core.safe_date_yyyymmdd(game_dt) AS game_date,
    core.safe_int(game_ct)::smallint AS game_number,
    NULLIF(game_dy, '') AS day_of_week,
    NULLIF(start_game_tm, '') AS start_time,
    NULLIF(dh_fl, '') AS doubleheader_flag,
    NULLIF(daynight_park_cd, '') AS day_night,
    away_team_id,
    home_team_id,
    NULLIF(park_id, '') AS park_id,
    NULLIF(away_start_pit_id, '') AS away_starting_pitcher_id,
    NULLIF(home_start_pit_id, '') AS home_starting_pitcher_id,
    core.safe_int(attend_park_ct) AS attendance,
    core.safe_int(temp_park_ct) AS temperature_f,
    NULLIF(wind_direction_park_cd, '') AS wind_direction,
    core.safe_int(wind_speed_park_ct) AS wind_speed_mph,
    NULLIF(field_park_cd, '') AS field_condition,
    NULLIF(precip_park_cd, '') AS precipitation,
    NULLIF(sky_park_cd, '') AS sky_condition,
    core.safe_int(minutes_game_ct) AS duration_minutes,
    core.safe_int(inn_ct) AS innings,
    core.safe_int(away_score_ct) AS away_score,
    core.safe_int(home_score_ct) AS home_score,
    core.safe_int(away_hits_ct) AS away_hits,
    core.safe_int(home_hits_ct) AS home_hits,
    core.safe_int(away_err_ct) AS away_errors,
    core.safe_int(home_err_ct) AS home_errors,
    core.safe_int(away_lob_ct) AS away_lob,
    core.safe_int(home_lob_ct) AS home_lob,
    CASE
        WHEN core.safe_int(home_score_ct) > core.safe_int(away_score_ct) THEN home_team_id
        WHEN core.safe_int(away_score_ct) > core.safe_int(home_score_ct) THEN away_team_id
    END AS winning_team_id,
    CASE
        WHEN core.safe_int(home_score_ct) > core.safe_int(away_score_ct) THEN true
        WHEN core.safe_int(away_score_ct) > core.safe_int(home_score_ct) THEN false
    END AS home_win,
    NULLIF(win_pit_id, '') AS win_pitcher_id,
    NULLIF(lose_pit_id, '') AS loss_pitcher_id,
    NULLIF(save_pit_id, '') AS save_pitcher_id,
    loaded_at
FROM raw_retrosheet.chadwick_games
WHERE game_id IS NOT NULL
  AND game_id <> ''
  AND core.safe_date_yyyymmdd(game_dt) IS NOT NULL
  AND away_team_id <> ''
  AND home_team_id <> ''
  AND core.safe_int(away_score_ct) IS NOT NULL
  AND core.safe_int(home_score_ct) IS NOT NULL;

CREATE INDEX IF NOT EXISTS games_season_date_idx ON core.games (season, game_date);
CREATE INDEX IF NOT EXISTS games_home_team_date_idx ON core.games (home_team_id, game_date);
CREATE INDEX IF NOT EXISTS games_away_team_date_idx ON core.games (away_team_id, game_date);
CREATE INDEX IF NOT EXISTS games_park_date_idx ON core.games (park_id, game_date);

CREATE UNLOGGED TABLE core.events AS
SELECT
    events.game_id,
    NULLIF(events.event_id, '')::integer AS event_id,
    events.season,
    events.source_type,
    events.row_number AS event_sequence,
    NULLIF(events.inn_ct, '')::integer AS inning,
    events.bat_home_id = '1' AS is_bottom_inning,
    NULLIF(events.outs_ct, '')::integer AS outs_before,
    NULLIF(events.balls_ct, '')::integer AS balls,
    NULLIF(events.strikes_ct, '')::integer AS strikes,
    NULLIF(events.away_score_ct, '')::integer AS away_score_before,
    NULLIF(events.home_score_ct, '')::integer AS home_score_before,
    events.bat_team_id AS batting_team_id,
    events.fld_team_id AS fielding_team_id,
    NULLIF(events.bat_id, '') AS batter_id,
    CASE WHEN events.bat_hand_cd IN ('L', 'R', 'B') THEN events.bat_hand_cd::char(1) END AS batter_hand,
    NULLIF(events.pit_id, '') AS pitcher_id,
    CASE WHEN events.pit_hand_cd IN ('L', 'R') THEN events.pit_hand_cd::char(1) END AS pitcher_hand,
    NULLIF(events.event_cd, '')::integer AS event_code,
    NULLIF(events.event_tx, '') AS event_text,
    events.bat_event_fl = 'T' AS is_plate_appearance,
    events.ab_fl = 'T' AS is_at_bat,
    COALESCE(NULLIF(events.h_cd, '')::integer, 0) AS hit_value,
    COALESCE(NULLIF(events.h_cd, '')::integer, 0) > 0 AS is_hit,
    NULLIF(events.event_cd, '')::integer IN (14, 15) AS is_walk,
    NULLIF(events.event_cd, '')::integer = 3 AS is_strikeout,
    COALESCE(NULLIF(events.h_cd, '')::integer, 0) = 4 AS is_home_run,
    COALESCE(NULLIF(events.event_outs_ct, '')::integer, 0) AS outs_on_play,
    COALESCE(NULLIF(events.event_runs_ct, '')::integer, 0) AS runs_on_play,
    COALESCE(NULLIF(events.rbi_ct, '')::integer, 0) AS rbi,
    NULLIF(events.start_bases_cd, '')::integer AS start_bases,
    NULLIF(events.end_bases_cd, '')::integer AS end_bases,
    NULLIF(events.away_score_ct, '')::integer + CASE WHEN events.bat_home_id = '0' THEN COALESCE(NULLIF(events.event_runs_ct, '')::integer, 0) ELSE 0 END AS away_score_after,
    NULLIF(events.home_score_ct, '')::integer + CASE WHEN events.bat_home_id = '1' THEN COALESCE(NULLIF(events.event_runs_ct, '')::integer, 0) ELSE 0 END AS home_score_after,
    NULLIF(events.game_pa_ct, '')::integer AS game_pa_count,
    NULLIF(events.inn_pa_ct, '')::integer AS inning_pa_count,
    events.pa_new_fl = 'T' AS is_new_plate_appearance,
    events.inn_new_fl = 'T' AS is_inning_start,
    events.inn_end_fl = 'T' AS is_inning_end,
    events.game_end_fl = 'T' AS is_game_end,
    events.loaded_at AS raw_loaded_at,
    now() AS created_at
FROM raw_retrosheet.chadwick_events events
JOIN core.games games ON games.game_id = events.game_id
WHERE events.game_id IS NOT NULL
  AND events.game_id <> ''
  AND NULLIF(events.event_id, '') IS NOT NULL
  AND NULLIF(events.inn_ct, '') IS NOT NULL
  AND events.bat_home_id IN ('0', '1')
  AND NULLIF(events.outs_ct, '')::integer BETWEEN 0 AND 2
  AND NULLIF(events.away_score_ct, '') IS NOT NULL
  AND NULLIF(events.home_score_ct, '') IS NOT NULL
  AND events.bat_team_id <> ''
  AND events.fld_team_id <> '';

ALTER TABLE core.events
    ALTER COLUMN game_id SET NOT NULL,
    ALTER COLUMN event_id SET NOT NULL,
    ALTER COLUMN season SET NOT NULL,
    ALTER COLUMN source_type SET NOT NULL,
    ALTER COLUMN event_sequence SET NOT NULL,
    ALTER COLUMN inning SET NOT NULL,
    ALTER COLUMN is_bottom_inning SET NOT NULL,
    ALTER COLUMN outs_before SET NOT NULL,
    ALTER COLUMN away_score_before SET NOT NULL,
    ALTER COLUMN home_score_before SET NOT NULL,
    ALTER COLUMN batting_team_id SET NOT NULL,
    ALTER COLUMN fielding_team_id SET NOT NULL,
    ALTER COLUMN is_plate_appearance SET NOT NULL,
    ALTER COLUMN is_at_bat SET NOT NULL,
    ALTER COLUMN hit_value SET NOT NULL,
    ALTER COLUMN is_hit SET NOT NULL,
    ALTER COLUMN is_walk SET NOT NULL,
    ALTER COLUMN is_strikeout SET NOT NULL,
    ALTER COLUMN is_home_run SET NOT NULL,
    ALTER COLUMN outs_on_play SET NOT NULL,
    ALTER COLUMN runs_on_play SET NOT NULL,
    ALTER COLUMN rbi SET NOT NULL,
    ALTER COLUMN away_score_after SET NOT NULL,
    ALTER COLUMN home_score_after SET NOT NULL,
    ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE core.events
    ADD CONSTRAINT events_pk PRIMARY KEY (game_id, event_id),
    ADD CONSTRAINT events_outs_before_check CHECK (outs_before BETWEEN 0 AND 2),
    ADD CONSTRAINT events_inning_check CHECK (inning > 0),
    ADD CONSTRAINT events_count_check CHECK ((balls IS NULL OR balls BETWEEN 0 AND 4) AND (strikes IS NULL OR strikes BETWEEN 0 AND 3)),
    ADD CONSTRAINT events_hit_value_check CHECK (hit_value BETWEEN 0 AND 4),
    ADD CONSTRAINT events_hands_check CHECK (
        (batter_hand IS NULL OR batter_hand IN ('L', 'R', 'B'))
        AND (pitcher_hand IS NULL OR pitcher_hand IN ('L', 'R'))
    );

CREATE INDEX IF NOT EXISTS events_game_sequence_idx ON core.events (game_id, event_sequence);
CREATE INDEX IF NOT EXISTS events_season_game_idx ON core.events (season, game_id);
CREATE INDEX IF NOT EXISTS events_state_idx ON core.events (inning, is_bottom_inning, outs_before, start_bases);
CREATE INDEX IF NOT EXISTS events_batter_idx ON core.events (batter_id, season) WHERE batter_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS events_pitcher_idx ON core.events (pitcher_id, season) WHERE pitcher_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS events_pa_idx ON core.events (season, is_plate_appearance, batter_id, pitcher_id) WHERE is_plate_appearance;

ALTER TABLE core.events
    ADD CONSTRAINT events_game_fk
    FOREIGN KEY (game_id) REFERENCES core.games (game_id) ON DELETE CASCADE NOT VALID;

ALTER TABLE core.events
    ADD CONSTRAINT events_batting_team_fk
    FOREIGN KEY (batting_team_id) REFERENCES core.teams (retrosheet_team_id) NOT VALID;

ALTER TABLE core.events
    ADD CONSTRAINT events_fielding_team_fk
    FOREIGN KEY (fielding_team_id) REFERENCES core.teams (retrosheet_team_id) NOT VALID;

ALTER TABLE core.events
    ADD CONSTRAINT events_batter_fk
    FOREIGN KEY (batter_id) REFERENCES core.players (retrosheet_player_id) NOT VALID;

ALTER TABLE core.events
    ADD CONSTRAINT events_pitcher_fk
    FOREIGN KEY (pitcher_id) REFERENCES core.players (retrosheet_player_id) NOT VALID;

ALTER TABLE core.events SET LOGGED;

CREATE OR REPLACE VIEW core.game_states AS
SELECT
    events.game_id,
    events.event_id,
    events.season,
    games.game_date,
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
    CASE
        WHEN events.is_bottom_inning THEN events.home_score_before - events.away_score_before
        ELSE events.away_score_before - events.home_score_before
    END AS batting_team_score_diff,
    CASE
        WHEN events.is_bottom_inning THEN events.home_score_before - events.away_score_before
        ELSE events.away_score_before - events.home_score_before
    END AS score_diff_for_batting_team,
    events.batting_team_id,
    events.fielding_team_id,
    games.home_team_id,
    games.away_team_id,
    events.batter_id,
    events.batter_hand,
    events.pitcher_id,
    events.pitcher_hand,
    events.event_code,
    events.is_plate_appearance,
    events.is_at_bat,
    events.hit_value,
    events.is_hit,
    events.is_walk,
    events.is_strikeout,
    events.is_home_run,
    events.runs_on_play,
    games.home_win AS final_home_win,
    games.winning_team_id,
    events.batting_team_id = games.winning_team_id AS final_batting_team_win
FROM core.events events
JOIN core.games games ON games.game_id = events.game_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS features.game_outcome_examples AS
SELECT
    game_id,
    event_id,
    season,
    game_date,
    inning,
    is_bottom_inning,
    outs_before,
    COALESCE(start_bases, 0) AS start_bases,
    COALESCE(balls, 0) AS balls,
    COALESCE(strikes, 0) AS strikes,
    home_score_before - away_score_before AS home_score_diff,
    away_score_before,
    home_score_before,
    batting_team_id,
    fielding_team_id,
    home_team_id,
    away_team_id,
    batter_id,
    batter_hand,
    pitcher_id,
    pitcher_hand,
    final_home_win
FROM core.game_states
WHERE is_plate_appearance
  AND final_home_win IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS game_outcome_examples_pk
    ON features.game_outcome_examples (game_id, event_id);

CREATE INDEX IF NOT EXISTS game_outcome_examples_state_idx
    ON features.game_outcome_examples (season, inning, is_bottom_inning, outs_before, start_bases, home_score_diff);

REFRESH MATERIALIZED VIEW features.game_outcome_examples;

CREATE TABLE IF NOT EXISTS predictions.prediction_targets (
    target_id text PRIMARY KEY,
    target_name text NOT NULL,
    target_family text NOT NULL,
    description text NOT NULL,
    question_template text,
    required_context jsonb NOT NULL DEFAULT '[]'::jsonb,
    training_label_sql text,
    live_resolution_rule text,
    default_model_family text NOT NULL DEFAULT 'baseline',
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO predictions.prediction_targets (
    target_id, target_name, target_family, description, question_template,
    required_context, training_label_sql, live_resolution_rule, default_model_family
)
VALUES
    (
        'game_home_win',
        'Home team wins',
        'game_outcome',
        'Probability that the home team wins from a given game state.',
        'What is the probability the home team wins this game?',
        '["game_id", "inning", "is_bottom_inning", "outs_before", "base_state", "score"]'::jsonb,
        'features.game_outcome_examples.final_home_win',
        'Resolved from final game score.',
        'logistic_regression'
    ),
    (
        'pa_batter_hit',
        'Batter gets a hit',
        'plate_appearance',
        'Probability that the batter records a hit in a plate appearance.',
        'What is the probability this batter gets a hit?',
        '["batter_id", "pitcher_id", "batter_hand", "pitcher_hand", "game_state"]'::jsonb,
        'core.events.is_hit where core.events.is_plate_appearance',
        'Resolved from the completed plate appearance.',
        'gradient_boosted_trees'
    ),
    (
        'pa_pitcher_strikeout',
        'Pitcher records a strikeout',
        'plate_appearance',
        'Probability that the pitcher records a strikeout in a plate appearance.',
        'What is the probability this pitcher records a strikeout?',
        '["batter_id", "pitcher_id", "batter_hand", "pitcher_hand", "game_state"]'::jsonb,
        'core.events.is_strikeout where core.events.is_plate_appearance',
        'Resolved from the completed plate appearance.',
        'gradient_boosted_trees'
    ),
    (
        'half_inning_any_run',
        'Half-inning has any run',
        'half_inning',
        'Probability that at least one run scores in the current half-inning.',
        'What is the probability this half-inning has at least one run?',
        '["game_id", "inning", "is_bottom_inning", "base_state", "lineup_context"]'::jsonb,
        'Derived from future core.events.runs_on_play within same half-inning.',
        'Resolved when the half-inning ends.',
        'monte_carlo'
    ),
    (
        'half_inning_lhb_any_hit',
        'Left-handed batter gets any hit this half-inning',
        'half_inning',
        'Probability that at least one left-handed batter records a hit in the current half-inning.',
        'What is the probability a left-handed batter gets a hit this inning?',
        '["game_id", "inning", "is_bottom_inning", "batter_handedness", "lineup_context"]'::jsonb,
        'Derived from future core.events where batter_hand = L and is_hit in same half-inning.',
        'Resolved when the half-inning ends.',
        'monte_carlo'
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

CREATE TABLE IF NOT EXISTS models.model_registry (
    model_id bigserial PRIMARY KEY,
    target_id text NOT NULL REFERENCES predictions.prediction_targets (target_id),
    model_name text NOT NULL,
    model_family text NOT NULL,
    model_version text NOT NULL,
    artifact_uri text,
    training_window daterange,
    feature_spec jsonb NOT NULL DEFAULT '{}'::jsonb,
    metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
    is_active boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (target_id, model_name, model_version)
);

CREATE TABLE IF NOT EXISTS predictions.prediction_runs (
    prediction_run_id bigserial PRIMARY KEY,
    target_id text NOT NULL REFERENCES predictions.prediction_targets (target_id),
    model_id bigint REFERENCES models.model_registry (model_id),
    run_context text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL DEFAULT 'running',
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS predictions.target_probabilities (
    prediction_id bigserial PRIMARY KEY,
    prediction_run_id bigint REFERENCES predictions.prediction_runs (prediction_run_id),
    target_id text NOT NULL REFERENCES predictions.prediction_targets (target_id),
    model_id bigint REFERENCES models.model_registry (model_id),
    game_id text REFERENCES core.games (game_id),
    event_id integer,
    predicted_at timestamptz NOT NULL DEFAULT now(),
    probability numeric(8,7) NOT NULL,
    input_features jsonb NOT NULL DEFAULT '{}'::jsonb,
    explanation jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT target_probabilities_probability_check CHECK (probability >= 0 AND probability <= 1),
    CONSTRAINT target_probabilities_event_fk FOREIGN KEY (game_id, event_id)
        REFERENCES core.events (game_id, event_id)
        DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS target_probabilities_target_time_idx
    ON predictions.target_probabilities (target_id, predicted_at DESC);

CREATE INDEX IF NOT EXISTS target_probabilities_game_event_idx
    ON predictions.target_probabilities (game_id, event_id);

CREATE TABLE IF NOT EXISTS raw_markets.market_snapshots (
    market_snapshot_id bigserial PRIMARY KEY,
    venue text NOT NULL,
    market_id text NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL,
    UNIQUE (venue, market_id, fetched_at)
);

CREATE TABLE IF NOT EXISTS market_edges.market_prices (
    market_price_id bigserial PRIMARY KEY,
    venue text NOT NULL,
    market_id text NOT NULL,
    target_id text REFERENCES predictions.prediction_targets (target_id),
    observed_at timestamptz NOT NULL DEFAULT now(),
    side text NOT NULL,
    bid_price numeric(10,6),
    ask_price numeric(10,6),
    implied_probability numeric(8,7),
    liquidity jsonb NOT NULL DEFAULT '{}'::jsonb,
    settlement_rules text,
    raw_snapshot_id bigint REFERENCES raw_markets.market_snapshots (market_snapshot_id),
    CONSTRAINT market_prices_probability_check CHECK (implied_probability IS NULL OR (implied_probability >= 0 AND implied_probability <= 1))
);

CREATE INDEX IF NOT EXISTS market_prices_target_time_idx
    ON market_edges.market_prices (target_id, observed_at DESC);

CREATE TABLE IF NOT EXISTS market_edges.detected_edges (
    detected_edge_id bigserial PRIMARY KEY,
    prediction_id bigint NOT NULL REFERENCES predictions.target_probabilities (prediction_id),
    market_price_id bigint NOT NULL REFERENCES market_edges.market_prices (market_price_id),
    detected_at timestamptz NOT NULL DEFAULT now(),
    model_probability numeric(8,7) NOT NULL,
    market_implied_probability numeric(8,7) NOT NULL,
    edge numeric(9,7) NOT NULL,
    expected_value numeric(12,6),
    assumptions jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS chat.query_logs (
    query_log_id bigserial PRIMARY KEY,
    asked_at timestamptz NOT NULL DEFAULT now(),
    user_question text NOT NULL,
    parsed_intent jsonb NOT NULL DEFAULT '{}'::jsonb,
    response_summary text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE OR REPLACE VIEW core.validation_summary AS
SELECT 'core.games' AS object_name, count(*) AS row_count, count(DISTINCT game_id) AS distinct_games
FROM core.games
UNION ALL
SELECT 'core.events', count(*), count(DISTINCT game_id)
FROM core.events
UNION ALL
SELECT 'features.game_outcome_examples', count(*), count(DISTINCT game_id)
FROM features.game_outcome_examples;
