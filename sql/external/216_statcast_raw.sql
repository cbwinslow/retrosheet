-- =============================================================================
-- Statcast Raw Table
-- =============================================================================
-- Stores the full Statcast CSV for a given season.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw_statcast;

CREATE TABLE IF NOT EXISTS raw_statcast.events (
    game_pk            BIGINT,
    at_bat_number      INT,
    pitch_number       INT,
    pitcher_mlb_id     INT,
    batter_mlb_id      INT,
    release_speed      REAL,
    release_spin_rate  REAL,
    launch_angle       REAL,
    launch_speed       REAL,
    hit_distance       REAL,
    events             TEXT,
    pitch_type         TEXT,
    PRIMARY KEY (game_pk, at_bat_number, pitch_number)
);