-- File: sql/core/001_init.sql
-- Purpose: Initialize core database schemas and raw landing tables
-- Author: Agent Cascade
-- Date: 2026-04-24

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
    started_at timestamptz NOT NULL DEFAULT NOW(),
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
    loaded_at timestamptz NOT NULL DEFAULT NOW(),
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
    fetched_at timestamptz NOT NULL DEFAULT NOW(),
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
    updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bridge.team_xref (
    team_xref_id bigserial PRIMARY KEY,
    retrosheet_team_id text UNIQUE,
    mlb_team_id bigint UNIQUE,
    abbreviation text,
    name text,
    updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bridge.park_xref (
    park_xref_id bigserial PRIMARY KEY,
    retrosheet_park_id text UNIQUE,
    mlb_venue_id bigint UNIQUE,
    name text,
    updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bridge.game_xref (
    game_xref_id bigserial PRIMARY KEY,
    retrosheet_game_id text UNIQUE,
    mlb_game_pk bigint UNIQUE,
    game_date date,
    home_team_id text,
    away_team_id text,
    updated_at timestamptz NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE VIEW raw_mlb.latest_live_feed_snapshot AS
SELECT DISTINCT ON (game_pk)
    snapshot_id,
    game_pk,
    fetched_at,
    endpoint,
    payload
FROM raw_mlb.live_feed_snapshots
ORDER BY game_pk ASC, fetched_at DESC;

-- =============================================================================
-- TABLE AND COLUMN COMMENTS
-- =============================================================================

COMMENT ON SCHEMA raw_retrosheet IS 'Landing zone for Retrosheet/Chadwick source data. Source-preserved raw event files and ingest tracking.';
COMMENT ON SCHEMA raw_mlb IS 'Landing zone for MLB Stats API / GUMBO data. Source-preserved JSON snapshots from live feeds.';
COMMENT ON SCHEMA bridge IS 'ID cross-reference tables mapping between Retrosheet, MLB, Lahman, ESPN, and other external ID systems.';
COMMENT ON SCHEMA core IS 'Canonical baseball entities: typed games, events, and plate appearances shared by historical and live sources.';
COMMENT ON SCHEMA features IS 'ML-ready feature marts for model training and inference. Aggregated metrics and engineered features.';
COMMENT ON SCHEMA models IS 'Trained model metadata, hyperparameters, and artifact locations.';
COMMENT ON SCHEMA predictions IS 'Model outputs, backtest results, and live prediction snapshots with confidence scores.';

-- raw_retrosheet.ingest_runs
COMMENT ON TABLE raw_retrosheet.ingest_runs IS 'Tracks data ingestion runs with status, timing, and metadata for reproducibility';
COMMENT ON COLUMN raw_retrosheet.ingest_runs.ingest_run_id IS 'Unique identifier for each ingestion run';
COMMENT ON COLUMN raw_retrosheet.ingest_runs.source_name IS 'Data source name (e.g., chadwick, mlb_api, espn)';
COMMENT ON COLUMN raw_retrosheet.ingest_runs.status IS 'Run status: running, completed, failed';
COMMENT ON COLUMN raw_retrosheet.ingest_runs.details IS 'JSONB metadata about the run (files processed, row counts, errors)';

-- raw_retrosheet.chadwick_event_raw
COMMENT ON TABLE raw_retrosheet.chadwick_event_raw IS 'Source-preserved Chadwick event output. One row per event field (c001-cxxx) from event files.';
COMMENT ON COLUMN raw_retrosheet.chadwick_event_raw.season IS 'Baseball season (year)';
COMMENT ON COLUMN raw_retrosheet.chadwick_event_raw.game_id IS 'Retrosheet game identifier';
COMMENT ON COLUMN raw_retrosheet.chadwick_event_raw.event_id IS 'Event sequence number within game';

-- raw_mlb.live_feed_snapshots
COMMENT ON TABLE raw_mlb.live_feed_snapshots IS 'Source-preserved MLB Stats API live feed JSON snapshots';
COMMENT ON COLUMN raw_mlb.live_feed_snapshots.game_pk IS 'MLB game identifier (primary key from MLB API)';
COMMENT ON COLUMN raw_mlb.live_feed_snapshots.payload IS 'Full JSON response from MLB API /game/{game_pk}/feed/live';

-- bridge.player_xref
COMMENT ON TABLE bridge.player_xref IS 'Player ID crosswalk mapping Retrosheet ID ↔ MLB ID ↔ Baseball-Reference ID';
COMMENT ON COLUMN bridge.player_xref.retrosheet_id IS 'Retrosheet player ID (e.g., ruthb101)';
COMMENT ON COLUMN bridge.player_xref.mlb_id IS 'MLB Stats API player ID (numeric)';
COMMENT ON COLUMN bridge.player_xref.baseball_reference_id IS 'Baseball-Reference player ID (e.g., ruthba01)';
COMMENT ON COLUMN bridge.player_xref.source_notes IS 'JSONB metadata about mapping confidence and sources';

-- bridge.team_xref
COMMENT ON TABLE bridge.team_xref IS 'Team ID crosswalk mapping Retrosheet team ID ↔ MLB team ID';
COMMENT ON COLUMN bridge.team_xref.retrosheet_team_id IS 'Retrosheet 3-character team code (e.g., NYA)';
COMMENT ON COLUMN bridge.team_xref.mlb_team_id IS 'MLB Stats API team ID (numeric)';

-- bridge.park_xref
COMMENT ON TABLE bridge.park_xref IS 'Park/Venue ID crosswalk mapping Retrosheet park ID ↔ MLB venue ID';
COMMENT ON COLUMN bridge.park_xref.retrosheet_park_id IS 'Retrosheet park identifier';
COMMENT ON COLUMN bridge.park_xref.mlb_venue_id IS 'MLB Stats API venue ID (numeric)';

-- bridge.game_xref
COMMENT ON TABLE bridge.game_xref IS 'Game ID crosswalk mapping Retrosheet game ID ↔ MLB game_pk';
COMMENT ON COLUMN bridge.game_xref.retrosheet_game_id IS 'Retrosheet game identifier (e.g., BOS202304150)';
COMMENT ON COLUMN bridge.game_xref.mlb_game_pk IS 'MLB Stats API game primary key (numeric)';
