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
    max(NULLIF(league, '')),
    max(NULLIF(city, '')),
    max(NULLIF(nickname, '')),
    max(NULLIF(trim(COALESCE(city, '') || ' ' || COALESCE(nickname, '')), '')),
    min(season),
    max(season),
    now()
FROM raw_retrosheet.season_teams
WHERE team_id <> ''
GROUP BY team_id
ON CONFLICT (retrosheet_team_id) DO UPDATE
SET league = COALESCE(core.teams.league, EXCLUDED.league),
    city = COALESCE(core.teams.city, EXCLUDED.city),
    nickname = COALESCE(core.teams.nickname, EXCLUDED.nickname),
    team_name = COALESCE(core.teams.team_name, EXCLUDED.team_name),
    first_season = LEAST(COALESCE(core.teams.first_season, EXCLUDED.first_season), EXCLUDED.first_season),
    last_season = GREATEST(COALESCE(core.teams.last_season, EXCLUDED.last_season), EXCLUDED.last_season),
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
    max(NULLIF(trim(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')), '')),
    max(NULLIF(first_name, '')),
    max(NULLIF(last_name, '')),
    CASE WHEN max(NULLIF(bats, '')) IN ('L', 'R', 'B') THEN max(NULLIF(bats, ''))::char(1) END,
    CASE WHEN max(NULLIF(throws, '')) IN ('L', 'R') THEN max(NULLIF(throws, ''))::char(1) END,
    min(season),
    max(season),
    now()
FROM raw_retrosheet.season_rosters
WHERE player_id <> ''
GROUP BY player_id
ON CONFLICT (retrosheet_player_id) DO UPDATE
SET player_name = COALESCE(core.players.player_name, EXCLUDED.player_name),
    name_first = COALESCE(core.players.name_first, EXCLUDED.name_first),
    name_last = COALESCE(core.players.name_last, EXCLUDED.name_last),
    bats = COALESCE(core.players.bats, EXCLUDED.bats),
    throws = COALESCE(core.players.throws, EXCLUDED.throws),
    first_season = LEAST(COALESCE(core.players.first_season, EXCLUDED.first_season), EXCLUDED.first_season),
    last_season = GREATEST(COALESCE(core.players.last_season, EXCLUDED.last_season), EXCLUDED.last_season),
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
    max(NULLIF(first_name, '')),
    max(NULLIF(last_name, '')),
    jsonb_build_object(
        'source', 'retrosheet.season_rosters',
        'first_season', min(season),
        'last_season', max(season),
        'positions', jsonb_agg(DISTINCT NULLIF(position, '')) FILTER (WHERE NULLIF(position, '') IS NOT NULL)
    ),
    now()
FROM raw_retrosheet.season_rosters
WHERE player_id <> ''
GROUP BY player_id
ON CONFLICT (retrosheet_id) DO UPDATE
SET name_first = COALESCE(bridge.player_xref.name_first, EXCLUDED.name_first),
    name_last = COALESCE(bridge.player_xref.name_last, EXCLUDED.name_last),
    source_notes = bridge.player_xref.source_notes || EXCLUDED.source_notes,
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
FROM raw_retrosheet.season_rosters rosters
LEFT JOIN core.players players
    ON players.retrosheet_player_id = rosters.player_id
LEFT JOIN core.teams teams
    ON teams.retrosheet_team_id = rosters.roster_team_id;

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
    core.safe_date_yyyymmdd(game_date) AS game_date,
    core.safe_int(game_number) AS game_number,
    day_of_week,
    visitor_team_id AS away_team_id,
    visitor_league AS away_league,
    core.safe_int(visitor_game_number) AS away_game_number,
    home_team_id,
    home_league,
    core.safe_int(home_game_number) AS home_game_number,
    day_night,
    park_id,
    NULLIF(postponed, '') AS postponed,
    NULLIF(makeup, '') AS makeup,
    source_file
FROM raw_retrosheet.season_schedules;

CREATE OR REPLACE VIEW core.umpires AS
SELECT
    umpire_id,
    max(NULLIF(first_name, '')) AS first_name,
    max(NULLIF(last_name, '')) AS last_name,
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
FROM raw_retrosheet.coaches coaches
LEFT JOIN core.players players
    ON players.retrosheet_player_id = coaches.coach_id;

CREATE OR REPLACE VIEW core.ejections AS
SELECT
    game_id,
    core.safe_date_yyyymmdd(game_date) AS game_date,
    doubleheader_flag,
    ejectee_id,
    ejectee_name,
    team_id,
    job,
    umpire_id,
    umpire_name,
    core.safe_int(inning) AS inning,
    reason
FROM raw_retrosheet.ejections;

CREATE OR REPLACE VIEW core.player_relatives AS
SELECT
    relatives.player_id_1,
    player_1.player_name AS player_1_name,
    relatives.relationship,
    relatives.player_id_2,
    player_2.player_name AS player_2_name
FROM raw_retrosheet.relatives relatives
LEFT JOIN core.players player_1
    ON player_1.retrosheet_player_id = relatives.player_id_1
LEFT JOIN core.players player_2
    ON player_2.retrosheet_player_id = relatives.player_id_2;

CREATE OR REPLACE VIEW core.auxiliary_validation_summary AS
SELECT 'raw_retrosheet.biofile_legacy' AS object_name, count(*) AS row_count FROM raw_retrosheet.biofile_legacy
UNION ALL SELECT 'raw_retrosheet.coaches', count(*) FROM raw_retrosheet.coaches
UNION ALL SELECT 'raw_retrosheet.ejections', count(*) FROM raw_retrosheet.ejections
UNION ALL SELECT 'raw_retrosheet.relatives', count(*) FROM raw_retrosheet.relatives
UNION ALL SELECT 'raw_retrosheet.season_rosters', count(*) FROM raw_retrosheet.season_rosters
UNION ALL SELECT 'raw_retrosheet.allstar_rosters', count(*) FROM raw_retrosheet.season_rosters WHERE is_allstar
UNION ALL SELECT 'raw_retrosheet.season_teams', count(*) FROM raw_retrosheet.season_teams
UNION ALL SELECT 'raw_retrosheet.season_schedules', count(*) FROM raw_retrosheet.season_schedules
UNION ALL SELECT 'raw_retrosheet.season_umpires', count(*) FROM raw_retrosheet.season_umpires
UNION ALL SELECT 'raw_retrosheet.special_gamelog_lines', count(*) FROM raw_retrosheet.special_gamelog_lines
UNION ALL SELECT 'core.roster_entries', count(*) FROM core.roster_entries
UNION ALL SELECT 'core.allstar_games', count(*) FROM core.allstar_games;
