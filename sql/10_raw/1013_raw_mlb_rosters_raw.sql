-- File: sql/external/214_mlb_rosters_raw.sql
-- Purpose: Create MLB roster snapshots raw table with JSON payloads
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS raw_mlb_rosters;

CREATE TABLE IF NOT EXISTS raw_mlb_rosters.roster_snapshots (
    snapshot_date DATE NOT NULL,
    team_id TEXT NOT NULL,
    json_payload JSONB,
    PRIMARY KEY (snapshot_date, team_id)
);

-- Table comments
COMMENT ON TABLE raw_mlb_rosters.roster_snapshots IS 'MLB roster snapshots with JSON payload data';
