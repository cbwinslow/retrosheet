-- =============================================================================
-- External Data Mart Definitions
-- =============================================================================
-- This file defines schemas and tables for supplemental free data sources that
-- are ingested into their own data marts. The tables are kept separate from
-- the core Retrosheet warehouse and later joined via bridge tables or view
-- definitions.
-- =============================================================================

-- 1. Statcast raw data (pitch‑level metrics)
CREATE SCHEMA IF NOT EXISTS raw_mlb;
CREATE TABLE IF NOT EXISTS raw_mlb.statcast (
    game_pk            BIGINT      NOT NULL,
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
    -- additional columns can be added as needed
    PRIMARY KEY (game_pk, at_bat_number, pitch_number)
);

-- 2. Baseball‑Data.com play‑by‑play (historical)
CREATE SCHEMA IF NOT EXISTS raw_external;
CREATE TABLE IF NOT EXISTS raw_external.baseball_data_com (
    event_id           BIGINT      NOT NULL,
    game_id            BIGINT,
    inning             INT,
    half               TEXT,       -- \"top\" or \"bottom\"
    batter_id          INT,
    pitcher_id         INT,
    event_type         TEXT,
    description        TEXT,
    -- keep columns generic; mapping to core schema is done in a view
    PRIMARY KEY (event_id)
);

-- 3. Gameday XML raw snapshots (near‑real‑time)
CREATE TABLE IF NOT EXISTS raw_mlb.gameday_xml (
    game_date          DATE        NOT NULL,
    game_pk            BIGINT,
    xml_payload        TEXT,       -- raw XML string
    fetched_at         TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (game_date, game_pk)
);

-- 4. Bridge tables for external IDs (if not already present)
-- These tables map external player/team IDs to the canonical Retrosheet IDs.
CREATE TABLE IF NOT EXISTS bridge.external_player_xref (
    external_source     TEXT        NOT NULL,   -- e.g., ''statcast'', ''baseball_data_com''
    external_player_id  INT         NOT NULL,
    retrosheet_player_id INT        NOT NULL,
    PRIMARY KEY (external_source, external_player_id)
);

CREATE TABLE IF NOT EXISTS bridge.external_team_xref (
    external_source     TEXT        NOT NULL,
    external_team_id    INT         NOT NULL,
    retrosheet_team_id  INT         NOT NULL,
    PRIMARY KEY (external_source, external_team_id)
);