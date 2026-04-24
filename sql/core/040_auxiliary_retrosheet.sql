-- File: sql/core/040_auxiliary_retrosheet.sql
-- Purpose: Load auxiliary tables, create roster/allstar/ejection/umpire/coach views
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS raw_retrosheet;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS bridge;

CREATE TABLE IF NOT EXISTS raw_retrosheet.biofile_legacy (
    player_id text PRIMARY KEY,
    last_name text,
    use_name text,
    full_name text,
    birthdate text,
    birth_city text,
    birth_state text,
    birth_country text,
    deathdate text,
    death_city text,
    death_state text,
    death_country text,
    cemetery text,
    cemetery_city text,
    cemetery_state text,
    cemetery_country text,
    cemetery_note text,
    birth_name text,
    alt_name text,
    play_debut text,
    play_lastgame text,
    coach_debut text,
    coach_lastgame text,
    manager_debut text,
    manager_lastgame text,
    umpire_debut text,
    umpire_lastgame text,
    bats text,
    throws text,
    height text,
    weight text,
    hall_of_fame text,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_retrosheet.coaches (
    source_row_number integer PRIMARY KEY,
    coach_id text NOT NULL,
    season integer NOT NULL,
    team_id text NOT NULL,
    role text,
    start_date text,
    end_date text,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_retrosheet.ejections (
    source_row_number integer PRIMARY KEY,
    game_id text,
    game_date text,
    doubleheader_flag text,
    ejectee_id text,
    ejectee_name text,
    team_id text,
    job text,
    umpire_id text,
    umpire_name text,
    inning text,
    reason text,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_retrosheet.relatives (
    source_row_number integer PRIMARY KEY,
    player_id_1 text NOT NULL,
    relationship text NOT NULL,
    player_id_2 text NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_retrosheet.season_rosters (
    source_file text NOT NULL,
    source_row_number integer NOT NULL,
    season integer NOT NULL,
    roster_team_id text NOT NULL,
    player_id text NOT NULL,
    last_name text,
    first_name text,
    bats text,
    throws text,
    team_id text,
    position text,
    is_allstar boolean NOT NULL DEFAULT false,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_file, source_row_number)
);

CREATE TABLE IF NOT EXISTS raw_retrosheet.season_teams (
    source_file text NOT NULL,
    source_row_number integer NOT NULL,
    season integer NOT NULL,
    team_id text NOT NULL,
    league text,
    city text,
    nickname text,
    is_allstar boolean NOT NULL DEFAULT false,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_file, source_row_number)
);

CREATE TABLE IF NOT EXISTS raw_retrosheet.season_schedules (
    source_file text NOT NULL,
    source_row_number integer NOT NULL,
    season integer NOT NULL,
    game_date text,
    game_number text,
    day_of_week text,
    visitor_team_id text,
    visitor_league text,
    visitor_game_number text,
    home_team_id text,
    home_league text,
    home_game_number text,
    day_night text,
    park_id text,
    postponed text,
    makeup text,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_file, source_row_number)
);

CREATE TABLE IF NOT EXISTS raw_retrosheet.season_umpires (
    source_file text NOT NULL,
    source_row_number integer NOT NULL,
    season integer NOT NULL,
    umpire_id text NOT NULL,
    last_name text,
    first_name text,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_file, source_row_number)
);

CREATE TABLE IF NOT EXISTS raw_retrosheet.special_gamelog_lines (
    source_file text NOT NULL,
    source_row_number integer NOT NULL,
    game_type text NOT NULL,
    row_text text NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_file, source_row_number)
);

CREATE INDEX IF NOT EXISTS season_rosters_player_idx
ON raw_retrosheet.season_rosters (player_id, season);
CREATE INDEX IF NOT EXISTS season_rosters_team_idx
ON raw_retrosheet.season_rosters (roster_team_id, season);
CREATE INDEX IF NOT EXISTS season_rosters_allstar_idx
ON raw_retrosheet.season_rosters (season, is_allstar);
CREATE INDEX IF NOT EXISTS season_teams_team_idx
ON raw_retrosheet.season_teams (team_id, season);
CREATE INDEX IF NOT EXISTS season_schedules_date_idx
ON raw_retrosheet.season_schedules (season, game_date);
CREATE INDEX IF NOT EXISTS ejections_game_idx
ON raw_retrosheet.ejections (game_id);
CREATE INDEX IF NOT EXISTS coaches_coach_idx
ON raw_retrosheet.coaches (coach_id, season);

ALTER TABLE core.players
ADD COLUMN IF NOT EXISTS name_first text,
ADD COLUMN IF NOT EXISTS name_last text,
ADD COLUMN IF NOT EXISTS nickname text;

ALTER TABLE core.teams
ADD COLUMN IF NOT EXISTS league text,
ADD COLUMN IF NOT EXISTS city text,
ADD COLUMN IF NOT EXISTS nickname text,
ADD COLUMN IF NOT EXISTS team_name text;

INSERT INTO core.teams (
    retrosheet_team_id,
    league,
    city,
    nickname,
    team_name,
    first_season,
    last_season,
    updated_at
)
SELECT
    team_id,
    max(nullif(league, '')),
    max(nullif(city, '')),
    max(nullif(nickname, '')),
    max(nullif(trim(coalesce(city, '') || ' ' || coalesce(nickname, '')), '')),
    min(season),
    max(season),
    now()
FROM raw_retrosheet.season_teams
WHERE team_id <> ''
GROUP BY team_id
ON CONFLICT (retrosheet_team_id) DO UPDATE
    SET
        league = coalesce(core.teams.league, excluded.league),
        city = coalesce(core.teams.city, excluded.city),
        nickname = coalesce(core.teams.nickname, excluded.nickname),
        team_name = coalesce(core.teams.team_name, excluded.team_name),
        first_season = least(coalesce(core.teams.first_season, excluded.first_season), excluded.first_season),
        last_season = greatest(coalesce(core.teams.last_season, excluded.last_season), excluded.last_season),
        updated_at = now();

INSERT INTO core.players (
    retrosheet_player_id,
    player_name,
    name_first,
    name_last,
    bats,
    throws,
    first_season,
    last_season,
    updated_at
)
SELECT
    player_id,
    max(nullif(trim(coalesce(first_name, '') || ' ' || coalesce(last_name, '')), '')),
    max(nullif(first_name, '')),
    max(nullif(last_name, '')),
    CASE WHEN max(nullif(bats, '')) IN ('L', 'R', 'B') THEN max(nullif(bats, ''))::char(1) END,
    CASE WHEN max(nullif(throws, '')) IN ('L', 'R') THEN max(nullif(throws, ''))::char(1) END,
    min(season),
    max(season),
    now()
FROM raw_retrosheet.season_rosters
WHERE player_id <> ''
GROUP BY player_id
ON CONFLICT (retrosheet_player_id) DO UPDATE
    SET
        player_name = coalesce(core.players.player_name, excluded.player_name),
        name_first = coalesce(core.players.name_first, excluded.name_first),
        name_last = coalesce(core.players.name_last, excluded.name_last),
        bats = coalesce(core.players.bats, excluded.bats),
        throws = coalesce(core.players.throws, excluded.throws),
        first_season = least(coalesce(core.players.first_season, excluded.first_season), excluded.first_season),
        last_season = greatest(coalesce(core.players.last_season, excluded.last_season), excluded.last_season),
        updated_at = now();

INSERT INTO bridge.player_xref (
    retrosheet_id,
    name_first,
    name_last,
    source_notes,
    updated_at
)
SELECT
    player_id,
    max(nullif(first_name, '')),
    max(nullif(last_name, '')),
    jsonb_build_object(
        'source', 'retrosheet.season_rosters',
        'first_season', min(season),
        'last_season', max(season),
        'positions', jsonb_agg(DISTINCT nullif(position, '')) FILTER (WHERE nullif(position, '') IS NOT null)
    ),
    now()
FROM raw_retrosheet.season_rosters
WHERE player_id <> ''
GROUP BY player_id
ON CONFLICT (retrosheet_id) DO UPDATE
    SET
        name_first = coalesce(bridge.player_xref.name_first, excluded.name_first),
        name_last = coalesce(bridge.player_xref.name_last, excluded.name_last),
        source_notes = bridge.player_xref.source_notes || excluded.source_notes,
        updated_at = now();

CREATE OR REPLACE VIEW core.roster_entries AS
SELECT
    rosters.season,
    rosters.roster_team_id,
    rosters.player_id,
    players.player_name,
    rosters.first_name,
    rosters.last_name,
    rosters.bats,
    rosters.throws,
    rosters.position,
    rosters.is_allstar,
    teams.league,
    teams.city AS team_city,
    teams.nickname AS team_nickname,
    rosters.source_file
FROM raw_retrosheet.season_rosters AS rosters
LEFT JOIN core.players AS players
    ON rosters.player_id = players.retrosheet_player_id
LEFT JOIN core.teams AS teams
    ON rosters.roster_team_id = teams.retrosheet_team_id;

CREATE OR REPLACE VIEW core.allstar_roster_entries AS
SELECT *
FROM core.roster_entries
WHERE is_allstar;

CREATE OR REPLACE VIEW core.allstar_games AS
SELECT *
FROM core.games
WHERE source_type = 'allstar';

CREATE OR REPLACE VIEW core.scheduled_games AS
SELECT
    season,
    day_of_week,
    visitor_team_id AS away_team_id,
    visitor_league AS away_league,
    home_team_id,
    home_league,
    day_night,
    park_id,
    source_file,
    core.safe_date_yyyymmdd(game_date) AS game_date,
    core.safe_int(game_number) AS game_number,
    core.safe_int(visitor_game_number) AS away_game_number,
    core.safe_int(home_game_number) AS home_game_number,
    nullif(postponed, '') AS postponed,
    nullif(makeup, '') AS makeup
FROM raw_retrosheet.season_schedules;

CREATE OR REPLACE VIEW core.umpires AS
SELECT
    umpire_id,
    max(nullif(first_name, '')) AS first_name,
    max(nullif(last_name, '')) AS last_name,
    min(season) AS first_season,
    max(season) AS last_season
FROM raw_retrosheet.season_umpires
GROUP BY umpire_id;

CREATE OR REPLACE VIEW core.coach_assignments AS
SELECT
    coaches.coach_id,
    players.player_name AS coach_name,
    coaches.season,
    coaches.team_id,
    coaches.role,
    core.safe_date_mmddyyyy(coaches.start_date) AS start_date,
    core.safe_date_mmddyyyy(coaches.end_date) AS end_date
FROM raw_retrosheet.coaches AS coaches
LEFT JOIN core.players AS players
    ON coaches.coach_id = players.retrosheet_player_id;

CREATE OR REPLACE VIEW core.ejections AS
SELECT
    game_id,
    doubleheader_flag,
    ejectee_id,
    ejectee_name,
    team_id,
    job,
    umpire_id,
    umpire_name,
    reason,
    core.safe_date_yyyymmdd(game_date) AS game_date,
    core.safe_int(inning) AS inning
FROM raw_retrosheet.ejections;

CREATE OR REPLACE VIEW core.player_relatives AS
SELECT
    relatives.player_id_1,
    player_1.player_name AS player_1_name,
    relatives.relationship,
    relatives.player_id_2,
    player_2.player_name AS player_2_name
FROM raw_retrosheet.relatives AS relatives
LEFT JOIN core.players AS player_1
    ON relatives.player_id_1 = player_1.retrosheet_player_id
LEFT JOIN core.players AS player_2
    ON relatives.player_id_2 = player_2.retrosheet_player_id;

CREATE OR REPLACE VIEW core.auxiliary_validation_summary AS
SELECT
    'raw_retrosheet.biofile_legacy' AS object_name,
    count(*) AS row_count
FROM raw_retrosheet.biofile_legacy
UNION ALL
SELECT
    'raw_retrosheet.coaches',
    count(*)
FROM raw_retrosheet.coaches
UNION ALL
SELECT
    'raw_retrosheet.ejections',
    count(*)
FROM raw_retrosheet.ejections
UNION ALL
SELECT
    'raw_retrosheet.relatives',
    count(*)
FROM raw_retrosheet.relatives
UNION ALL
SELECT
    'raw_retrosheet.season_rosters',
    count(*)
FROM raw_retrosheet.season_rosters
UNION ALL
SELECT
    'raw_retrosheet.allstar_rosters',
    count(*)
FROM raw_retrosheet.season_rosters
WHERE is_allstar
UNION ALL
SELECT
    'raw_retrosheet.season_teams',
    count(*)
FROM raw_retrosheet.season_teams
UNION ALL
SELECT
    'raw_retrosheet.season_schedules',
    count(*)
FROM raw_retrosheet.season_schedules
UNION ALL
SELECT
    'raw_retrosheet.season_umpires',
    count(*)
FROM raw_retrosheet.season_umpires
UNION ALL
SELECT
    'raw_retrosheet.special_gamelog_lines',
    count(*)
FROM raw_retrosheet.special_gamelog_lines
UNION ALL
SELECT
    'core.roster_entries',
    count(*)
FROM core.roster_entries
UNION ALL
SELECT
    'core.allstar_games',
    count(*)
FROM core.allstar_games;

-- Table comments
COMMENT ON TABLE raw_retrosheet.biofile_legacy IS 'Legacy-format player biographical data from Retrosheet';
COMMENT ON TABLE raw_retrosheet.coaches IS 'Coaching assignments by season, team, and role';
COMMENT ON TABLE raw_retrosheet.ejections IS 'Game ejection records with ejectee, umpire, and reason';
COMMENT ON TABLE raw_retrosheet.relatives IS 'Player relationship records';
COMMENT ON TABLE raw_retrosheet.season_rosters IS 'season rosters data table';
COMMENT ON TABLE raw_retrosheet.season_teams IS 'season teams data table';
COMMENT ON TABLE raw_retrosheet.season_schedules IS 'season schedules data table';
COMMENT ON TABLE raw_retrosheet.season_umpires IS 'season umpires data table';
COMMENT ON TABLE raw_retrosheet.special_gamelog_lines IS 'special gamelog lines data table';
