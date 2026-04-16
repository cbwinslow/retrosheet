-- =============================================================================
-- Lahman Baseball Database Raw Tables
-- =============================================================================
-- This migration creates a separate schema for the free Lahman CSV data.
-- The tables are kept raw‑preserved; downstream feature views will join to
-- the canonical `core` entities via bridge tables.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw_lahman;

-- People (players) basic biographical data
CREATE TABLE IF NOT EXISTS raw_lahman.people (
    playerID        TEXT PRIMARY KEY,
    birthYear       INT,
    birthMonth      INT,
    birthDay        INT,
    birthCountry    TEXT,
    birthState      TEXT,
    birthCity       TEXT,
    deathYear       INT,
    deathMonth      INT,
    deathDay        INT,
    deathCountry    TEXT,
    deathState      TEXT,
    deathCity       TEXT,
    nameFirst       TEXT,
    nameLast        TEXT,
    nameGiven       TEXT,
    weight          INT,
    height          INT,
    bats            TEXT,
    throws          TEXT,
    debut           DATE,
    finalGame       DATE,
    retroID         TEXT,
    bbrefID         TEXT
);

-- Teams (season‑by‑season franchise data)
CREATE TABLE IF NOT EXISTS raw_lahman.teams (
    yearID          INT,
    lgID            TEXT,
    teamID          TEXT,
    franchID        TEXT,
    divID           TEXT,
    Rank            INT,
    G               INT,
    Ghome           INT,
    W               INT,
    L               INT,
    DivWin          TEXT,
    WCWin           TEXT,
    LgWin           TEXT,
    WSWin           TEXT,
    R               INT,
    AB              INT,
    H               INT,
    _2B             INT,
    _3B             INT,
    HR              INT,
    BB              INT,
    SO              INT,
    SB              INT,
    CS              INT,
    HBP             INT,
    SF              INT,
    RA              INT,
    ER              INT,
    ERA             REAL,
    CG              INT,
    SHO             INT,
    SV              INT,
    IPouts          INT,
    HAA             INT,
    HA              INT,
    BAA             REAL,
    OAA             INT,
    OBA             REAL,
    leagueID        TEXT,
    parkID          TEXT,
    attendance      INT,
    teamIDBR        TEXT,
    teamIDlahman45  TEXT,
    teamIDretro     TEXT,
    PRIMARY KEY (yearID, teamID)
);

-- Salaries (player‑season salary data)
CREATE TABLE IF NOT EXISTS raw_lahman.salaries (
    yearID          INT,
    teamID          TEXT,
    playerID        TEXT,
    salary          BIGINT,
    PRIMARY KEY (yearID, teamID, playerID)
);

-- Pitching stats (season aggregates)
CREATE TABLE IF NOT EXISTS raw_lahman.pitching (
    yearID          INT,
    lgID            TEXT,
    teamID          TEXT,
    playerID        TEXT,
    W               INT,
    L               INT,
    G               INT,
    GS              INT,
    CG              INT,
    SHO             INT,
    SV              INT,
    IPouts          INT,
    H               INT,
    ER              INT,
    HR              INT,
    BB              INT,
    SO              INT,
    BAOpp           REAL,
    ERA             REAL,
    IBB             INT,
    WP              INT,
    HBP             INT,
    BK              INT,
    BFP             INT,
    GF              INT,
    R               INT,
    SH              INT,
    SF              INT,
    GIDP            INT,
    PRIMARY KEY (yearID, playerID, teamID)
);

-- Batting stats (season aggregates)
CREATE TABLE IF NOT EXISTS raw_lahman.batting (
    yearID          INT,
    lgID            TEXT,
    teamID          TEXT,
    playerID        TEXT,
    G               INT,
    AB              INT,
    R               INT,
    H               INT,
    _2B             INT,
    _3B             INT,
    HR              INT,
    RBI             INT,
    SB              INT,
    CS              INT,
    BB              INT,
    SO              INT,
    IBB             INT,
    HBP             INT,
    SH              INT,
    SF              INT,
    GIDP            INT,
    PRIMARY KEY (yearID, playerID, teamID)
);