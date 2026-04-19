j-- =============================================================================
-- Baseball‑Reference Game Log Raw Tables
-- =============================================================================
-- Stores per‑game player statistics exported from Baseball‑Reference.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw_baseball_reference;

CREATE TABLE IF NOT EXISTS raw_baseball_reference.game_logs (
    game_id          TEXT NOT NULL,
    season           INT,
    date             DATE,
    team_id          TEXT,
    opponent_id      TEXT,
    home_away        TEXT,          -- 'home' or 'away'
    player_id        TEXT,
    position         TEXT,
    at_bats          INT,
    runs             INT,
    hits             INT,
    doubles          INT,
    triples          INT,
    home_runs        INT,
    rbi              INT,
    walks            INT,
    strikeouts       INT,
    stolen_bases     INT,
    caught_stealing  INT,
    hit_by_pitch     INT,
    sac_fly          INT,
    sac_bunt         INT,
    plate_appearances INT,
    woba             REAL,
    wrc_plus         INT,
    war              REAL,
    PRIMARY KEY (game_id, player_id)
);