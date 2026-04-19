CREATE SCHEMA IF NOT EXISTS raw_retrosheet;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS bridge;

CREATE OR REPLACE FUNCTION core.safe_int(value text)
RETURNS integer
LANGUAGE sql
IMMUTABLE
RETURNS NULL ON NULL INPUT
AS $$
    SELECT CASE WHEN btrim(value) ~ '^-?[0-9]+$' THEN btrim(value)::integer END
$$;

CREATE OR REPLACE FUNCTION core.safe_date_mmddyyyy(value text)
RETURNS date
LANGUAGE sql
IMMUTABLE
RETURNS NULL ON NULL INPUT
AS $$
    SELECT CASE
        WHEN btrim(value) ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$'
        THEN to_date(btrim(value), 'MM/DD/YYYY')
    END
$$;

CREATE TABLE IF NOT EXISTS raw_retrosheet.biofile (
    player_id text PRIMARY KEY,
    last_name text,
    first_name text,
    nickname text,
    birthdate text,
    birth_city text,
    birth_state text,
    birth_country text,
    play_debut text,
    play_lastgame text,
    mgr_debut text,
    mgr_lastgame text,
    coach_debut text,
    coach_lastgame text,
    ump_debut text,
    ump_lastgame text,
    deathdate text,
    death_city text,
    death_state text,
    death_country text,
    bats text,
    throws text,
    height text,
    weight text,
    cemetery text,
    cemetery_city text,
    cemetery_state text,
    cemetery_country text,
    cemetery_note text,
    birth_name text,
    name_change text,
    bat_change text,
    hall_of_fame text,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_retrosheet.teams_reference (
    retrosheet_team_id text PRIMARY KEY,
    league text,
    city text,
    nickname text,
    first_season integer,
    last_season integer,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_retrosheet.ballparks_reference (
    retrosheet_park_id text PRIMARY KEY,
    name text,
    aka text,
    city text,
    state text,
    start_date text,
    end_date text,
    league text,
    notes text,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE core.players
    ADD COLUMN IF NOT EXISTS name_first text,
    ADD COLUMN IF NOT EXISTS name_last text,
    ADD COLUMN IF NOT EXISTS nickname text,
    ADD COLUMN IF NOT EXISTS play_debut date,
    ADD COLUMN IF NOT EXISTS play_lastgame date,
    ADD COLUMN IF NOT EXISTS height text,
    ADD COLUMN IF NOT EXISTS weight integer,
    ADD COLUMN IF NOT EXISTS hall_of_fame boolean;

UPDATE core.players players
SET
    player_name = COALESCE(NULLIF(bio.first_name || ' ' || bio.last_name, ' '), players.player_name),
    name_first = NULLIF(bio.first_name, ''),
    name_last = NULLIF(bio.last_name, ''),
    nickname = NULLIF(bio.nickname, ''),
    bats = CASE WHEN bio.bats IN ('L', 'R', 'B') THEN bio.bats::char(1) ELSE players.bats END,
    throws = CASE WHEN bio.throws IN ('L', 'R') THEN bio.throws::char(1) ELSE players.throws END,
    play_debut = core.safe_date_mmddyyyy(bio.play_debut),
    play_lastgame = core.safe_date_mmddyyyy(bio.play_lastgame),
    height = NULLIF(bio.height, ''),
    weight = core.safe_int(bio.weight),
    hall_of_fame = NULLIF(bio.hall_of_fame, '') IS NOT NULL,
    updated_at = now()
FROM raw_retrosheet.biofile bio
WHERE bio.player_id = players.retrosheet_player_id;

ALTER TABLE core.teams
    ADD COLUMN IF NOT EXISTS league text,
    ADD COLUMN IF NOT EXISTS city text,
    ADD COLUMN IF NOT EXISTS nickname text,
    ADD COLUMN IF NOT EXISTS team_name text;

UPDATE core.teams teams
SET
    league = NULLIF(ref.league, ''),
    city = NULLIF(ref.city, ''),
    nickname = NULLIF(ref.nickname, ''),
    team_name = NULLIF(trim(COALESCE(ref.city, '') || ' ' || COALESCE(ref.nickname, '')), ''),
    first_season = COALESCE(ref.first_season, teams.first_season),
    last_season = COALESCE(ref.last_season, teams.last_season),
    updated_at = now()
FROM raw_retrosheet.teams_reference ref
WHERE ref.retrosheet_team_id = teams.retrosheet_team_id;

ALTER TABLE core.parks
    ADD COLUMN IF NOT EXISTS name text,
    ADD COLUMN IF NOT EXISTS aka text,
    ADD COLUMN IF NOT EXISTS city text,
    ADD COLUMN IF NOT EXISTS state text,
    ADD COLUMN IF NOT EXISTS start_date date,
    ADD COLUMN IF NOT EXISTS end_date date,
    ADD COLUMN IF NOT EXISTS league text,
    ADD COLUMN IF NOT EXISTS notes text;

UPDATE core.parks parks
SET
    name = NULLIF(ref.name, ''),
    aka = NULLIF(ref.aka, ''),
    city = NULLIF(ref.city, ''),
    state = NULLIF(ref.state, ''),
    start_date = core.safe_date_mmddyyyy(ref.start_date),
    end_date = core.safe_date_mmddyyyy(ref.end_date),
    league = NULLIF(ref.league, ''),
    notes = NULLIF(ref.notes, ''),
    updated_at = now()
FROM raw_retrosheet.ballparks_reference ref
WHERE ref.retrosheet_park_id = parks.retrosheet_park_id;

INSERT INTO bridge.player_xref (
    retrosheet_id,
    name_first,
    name_last,
    source_notes,
    updated_at
)
SELECT
    player_id,
    NULLIF(first_name, ''),
    NULLIF(last_name, ''),
    jsonb_build_object(
        'source', 'retrosheet.biofile',
        'bats', NULLIF(bats, ''),
        'throws', NULLIF(throws, ''),
        'play_debut', NULLIF(play_debut, ''),
        'play_lastgame', NULLIF(play_lastgame, '')
    ),
    now()
FROM raw_retrosheet.biofile
ON CONFLICT (retrosheet_id) DO UPDATE
SET name_first = EXCLUDED.name_first,
    name_last = EXCLUDED.name_last,
    source_notes = bridge.player_xref.source_notes || EXCLUDED.source_notes,
    updated_at = now();

INSERT INTO bridge.team_xref (
    retrosheet_team_id,
    abbreviation,
    name,
    updated_at
)
SELECT
    retrosheet_team_id,
    retrosheet_team_id,
    NULLIF(trim(COALESCE(city, '') || ' ' || COALESCE(nickname, '')), ''),
    now()
FROM raw_retrosheet.teams_reference
ON CONFLICT (retrosheet_team_id) DO UPDATE
SET abbreviation = EXCLUDED.abbreviation,
    name = EXCLUDED.name,
    updated_at = now();

INSERT INTO bridge.park_xref (
    retrosheet_park_id,
    name,
    updated_at
)
SELECT
    retrosheet_park_id,
    NULLIF(name, ''),
    now()
FROM raw_retrosheet.ballparks_reference
ON CONFLICT (retrosheet_park_id) DO UPDATE
SET name = EXCLUDED.name,
    updated_at = now();

UPDATE core.events events
SET batter_hand = players.bats
FROM core.players players
WHERE events.batter_id = players.retrosheet_player_id
  AND events.batter_hand IS NULL
  AND players.bats IS NOT NULL;

UPDATE core.events events
SET pitcher_hand = players.throws
FROM core.players players
WHERE events.pitcher_id = players.retrosheet_player_id
  AND events.pitcher_hand IS NULL
  AND players.throws IS NOT NULL;

UPDATE core.plate_appearances plate_appearances
SET batter_hand = events.batter_hand,
    pitcher_hand = events.pitcher_hand
FROM core.events events
WHERE plate_appearances.game_id = events.game_id
  AND plate_appearances.plate_appearance_id = events.event_id
  AND (
      plate_appearances.batter_hand IS DISTINCT FROM events.batter_hand
      OR plate_appearances.pitcher_hand IS DISTINCT FROM events.pitcher_hand
  );

REFRESH MATERIALIZED VIEW features.game_outcome_examples;
REFRESH MATERIALIZED VIEW features.plate_appearance_examples;

CREATE OR REPLACE VIEW core.metadata_validation_summary AS
SELECT
    'core.players' AS object_name,
    count(*) AS row_count,
    count(*) FILTER (WHERE bats IS NOT NULL) AS populated_bats,
    count(*) FILTER (WHERE throws IS NOT NULL) AS populated_throws
FROM core.players
UNION ALL
SELECT
    'features.plate_appearance_examples',
    count(*),
    count(*) FILTER (WHERE batter_hand <> 'U'),
    count(*) FILTER (WHERE pitcher_hand <> 'U')
FROM features.plate_appearance_examples;
