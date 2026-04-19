CREATE SCHEMA IF NOT EXISTS raw_retrosheet;
CREATE SCHEMA IF NOT EXISTS raw_mlb;
CREATE SCHEMA IF NOT EXISTS bridge;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS features;
CREATE SCHEMA IF NOT EXISTS models;
CREATE SCHEMA IF NOT EXISTS predictions;
CREATE SCHEMA IF NOT EXISTS raw_markets;
CREATE SCHEMA IF NOT EXISTS market_edges;
CREATE SCHEMA IF NOT EXISTS chat;

CREATE TABLE IF NOT EXISTS raw_retrosheet.ingest_runs (
    ingest_run_id bigserial PRIMARY KEY,
    source_name text NOT NULL,
    source_version text,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL DEFAULT 'running',
    details jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS raw_retrosheet.chadwick_event_raw (
    season integer NOT NULL,
    source_type text NOT NULL,
    row_number integer NOT NULL,
    game_id text,
    event_id integer,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    c001 text, c002 text, c003 text, c004 text, c005 text, c006 text, c007 text, c008 text, c009 text, c010 text,
    c011 text, c012 text, c013 text, c014 text, c015 text, c016 text, c017 text, c018 text, c019 text, c020 text,
    c021 text, c022 text, c023 text, c024 text, c025 text, c026 text, c027 text, c028 text, c029 text, c030 text,
    c031 text, c032 text, c033 text, c034 text, c035 text, c036 text, c037 text, c038 text, c039 text, c040 text,
    c041 text, c042 text, c043 text, c044 text, c045 text, c046 text, c047 text, c048 text, c049 text, c050 text,
    c051 text, c052 text, c053 text, c054 text, c055 text, c056 text, c057 text, c058 text, c059 text, c060 text,
    c061 text, c062 text, c063 text, c064 text, c065 text, c066 text, c067 text, c068 text, c069 text, c070 text,
    c071 text, c072 text, c073 text, c074 text, c075 text, c076 text, c077 text, c078 text, c079 text, c080 text,
    c081 text, c082 text, c083 text, c084 text, c085 text, c086 text, c087 text, c088 text, c089 text, c090 text,
    c091 text, c092 text, c093 text, c094 text, c095 text, c096 text, c097 text, c098 text, c099 text, c100 text,
    c101 text, c102 text, c103 text, c104 text, c105 text, c106 text, c107 text, c108 text, c109 text, c110 text,
    c111 text, c112 text, c113 text, c114 text, c115 text, c116 text, c117 text, c118 text, c119 text, c120 text,
    c121 text, c122 text, c123 text, c124 text, c125 text, c126 text, c127 text, c128 text, c129 text, c130 text,
    c131 text, c132 text, c133 text, c134 text, c135 text, c136 text, c137 text, c138 text, c139 text, c140 text,
    c141 text, c142 text, c143 text, c144 text, c145 text, c146 text, c147 text, c148 text, c149 text, c150 text,
    c151 text, c152 text, c153 text, c154 text, c155 text, c156 text, c157 text, c158 text, c159 text, c160 text,
    PRIMARY KEY (season, source_type, row_number)
);

ALTER TABLE raw_retrosheet.chadwick_event_raw
    ADD COLUMN IF NOT EXISTS c160 text;

CREATE INDEX IF NOT EXISTS chadwick_event_raw_game_idx
    ON raw_retrosheet.chadwick_event_raw (game_id);

CREATE INDEX IF NOT EXISTS chadwick_event_raw_event_idx
    ON raw_retrosheet.chadwick_event_raw (season, game_id, event_id);

CREATE TABLE IF NOT EXISTS raw_mlb.live_feed_snapshots (
    snapshot_id bigserial PRIMARY KEY,
    game_pk bigint NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT now(),
    endpoint text NOT NULL,
    payload jsonb NOT NULL
);

CREATE INDEX IF NOT EXISTS live_feed_snapshots_game_idx
    ON raw_mlb.live_feed_snapshots (game_pk, fetched_at DESC);

CREATE TABLE IF NOT EXISTS bridge.player_xref (
    player_xref_id bigserial PRIMARY KEY,
    retrosheet_id text UNIQUE,
    mlb_id bigint UNIQUE,
    baseball_reference_id text,
    name_first text,
    name_last text,
    source_notes jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bridge.team_xref (
    team_xref_id bigserial PRIMARY KEY,
    retrosheet_team_id text UNIQUE,
    mlb_team_id bigint UNIQUE,
    abbreviation text,
    name text,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bridge.park_xref (
    park_xref_id bigserial PRIMARY KEY,
    retrosheet_park_id text UNIQUE,
    mlb_venue_id bigint UNIQUE,
    name text,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bridge.game_xref (
    game_xref_id bigserial PRIMARY KEY,
    retrosheet_game_id text UNIQUE,
    mlb_game_pk bigint UNIQUE,
    game_date date,
    home_team_id text,
    away_team_id text,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE VIEW raw_mlb.latest_live_feed_snapshot AS
SELECT DISTINCT ON (game_pk)
    snapshot_id,
    game_pk,
    fetched_at,
    endpoint,
    payload
FROM raw_mlb.live_feed_snapshots
ORDER BY game_pk, fetched_at DESC;
