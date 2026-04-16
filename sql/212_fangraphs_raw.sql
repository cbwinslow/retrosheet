d-- =============================================================================
-- Fangraphs Player & Team Raw Tables
-- =============================================================================
-- Free CSV exports from Fangraphs (e.g., player season stats, team splits).
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw_fangraphs;

CREATE TABLE IF NOT EXISTS raw_fangraphs.player_season (
    player_id        TEXT NOT NULL,
    season           INT,
    team_id          TEXT,
    age              INT,
    g                INT,
    pa               INT,
    ab               INT,
    r                INT,
    h                INT,
    double           INT,
    triple           INT,
    hr               INT,
    rbi              INT,
    sb               INT,
    cs               INT,
    bb               INT,
    ibb              INT,
    hbp              INT,
    so               INT,
    avg              REAL,
    obp              REAL,
    slg              REAL,
    ops              REAL,
    woba             REAL,
    woba_plus        INT,
    wrc_plus         INT,
    war              REAL,
    PRIMARY KEY (player_id, season)
);

CREATE TABLE IF NOT EXISTS raw_fangraphs.team_season (
    team_id          TEXT NOT NULL,
    season           INT,
    g                INT,
    w                INT,
    l                INT,
    r                INT,
    ra               INT,
    era              REAL,
    woba             REAL,
    woba_plus        INT,
    wrc_plus         INT,
    war              REAL,
    PRIMARY KEY (team_id, season)
);