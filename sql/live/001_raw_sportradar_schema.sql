-- File: sql/live/001_raw_sportradar_schema.sql
-- Purpose: Schema and tables for Sportradar push events and snapshots
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS raw_sportradar;

CREATE TABLE IF NOT EXISTS raw_sportradar.push_events (
    id bigserial PRIMARY KEY,
    event_id text UNIQUE NOT NULL,
    game_pk text NOT NULL,
    raw_payload jsonb NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT NOW(),
    sequence_number integer NOT NULL,
    event_type text NOT NULL,
    sha256_checksum text NOT NULL,
    response_code integer DEFAULT 200,
    ingest_run_id bigint
);

CREATE INDEX IF NOT EXISTS idx_sportradar_push_game_sequence ON raw_sportradar.push_events (game_pk, sequence_number);
CREATE INDEX IF NOT EXISTS idx_sportradar_push_event_type ON raw_sportradar.push_events (event_type);
CREATE INDEX IF NOT EXISTS idx_sportradar_push_fetched_at ON raw_sportradar.push_events (fetched_at);
CREATE INDEX IF NOT EXISTS idx_sportradar_push_event_id ON raw_sportradar.push_events (event_id);

-- Raw game snapshots table
CREATE TABLE IF NOT EXISTS raw_sportradar.game_snapshots (
    id bigserial PRIMARY KEY,
    game_pk text UNIQUE NOT NULL,
    raw_payload jsonb NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT NOW(),
    status_code text NOT NULL,
    sha256_checksum text NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sportradar_game_pk ON raw_sportradar.game_snapshots (game_pk);
CREATE INDEX IF NOT EXISTS idx_sportradar_game_fetched_at ON raw_sportradar.game_snapshots (fetched_at);

-- Table comments
COMMENT ON TABLE raw_sportradar.push_events IS 'Sportradar push event ingestion with payloads';
COMMENT ON TABLE raw_sportradar.game_snapshots IS 'Sportradar game snapshot JSON payloads';
