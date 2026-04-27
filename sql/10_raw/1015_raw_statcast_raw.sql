-- File: sql/external/216_statcast_raw.sql
-- Purpose: Create Statcast raw events table with pitch physics data
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS raw_statcast;

CREATE TABLE IF NOT EXISTS raw_statcast.events (
    game_pk BIGINT,
    at_bat_number INT,
    pitch_number INT,
    pitcher_mlb_id INT,
    batter_mlb_id INT,
    release_speed REAL,
    release_spin_rate REAL,
    launch_angle REAL,
    launch_speed REAL,
    hit_distance REAL,
    events TEXT,
    pitch_type TEXT,
    PRIMARY KEY (game_pk, at_bat_number, pitch_number)
);

-- Table comments
COMMENT ON TABLE raw_statcast.events IS 'Statcast pitch-level events with physics and outcome data';
