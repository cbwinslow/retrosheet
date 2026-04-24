-- File: sql/external/210_lahman_raw.sql
-- Purpose: Create Lahman raw tables for players, teams, salaries, pitching, batting
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE SCHEMA IF NOT EXISTS raw_lahman;

-- People (players) basic biographical data
CREATE TABLE IF NOT EXISTS raw_lahman.people (
    playerid TEXT PRIMARY KEY,
    birthyear INT,
    birthmonth INT,
    birthday INT,
    birthcountry TEXT,
    birthstate TEXT,
    birthcity TEXT,
    deathyear INT,
    deathmonth INT,
    deathday INT,
    deathcountry TEXT,
    deathstate TEXT,
    deathcity TEXT,
    namefirst TEXT,
    namelast TEXT,
    namegiven TEXT,
    weight INT,
    height INT,
    bats TEXT,
    throws TEXT,
    debut DATE,
    finalgame DATE,
    retroid TEXT,
    bbrefid TEXT
);

-- Teams (season‑by‑season franchise data)
CREATE TABLE IF NOT EXISTS raw_lahman.teams (
    yearid INT,
    lgid TEXT,
    teamid TEXT,
    franchid TEXT,
    divid TEXT,
    rank INT,
    g INT,
    ghome INT,
    w INT,
    l INT,
    divwin TEXT,
    wcwin TEXT,
    lgwin TEXT,
    wswin TEXT,
    r INT,
    ab INT,
    h INT,
    _2b INT,
    _3b INT,
    hr INT,
    bb INT,
    so INT,
    sb INT,
    cs INT,
    hbp INT,
    sf INT,
    ra INT,
    er INT,
    era REAL,
    cg INT,
    sho INT,
    sv INT,
    ipouts INT,
    haa INT,
    ha INT,
    baa REAL,
    oaa INT,
    oba REAL,
    leagueid TEXT,
    parkid TEXT,
    attendance INT,
    teamidbr TEXT,
    teamidlahman45 TEXT,
    teamidretro TEXT,
    PRIMARY KEY (yearid, teamid)
);

-- Salaries (player‑season salary data)
CREATE TABLE IF NOT EXISTS raw_lahman.salaries (
    yearid INT,
    teamid TEXT,
    playerid TEXT,
    salary BIGINT,
    PRIMARY KEY (yearid, teamid, playerid)
);

-- Pitching stats (season aggregates)
CREATE TABLE IF NOT EXISTS raw_lahman.pitching (
    yearid INT,
    lgid TEXT,
    teamid TEXT,
    playerid TEXT,
    w INT,
    l INT,
    g INT,
    gs INT,
    cg INT,
    sho INT,
    sv INT,
    ipouts INT,
    h INT,
    er INT,
    hr INT,
    bb INT,
    so INT,
    baopp REAL,
    era REAL,
    ibb INT,
    wp INT,
    hbp INT,
    bk INT,
    bfp INT,
    gf INT,
    r INT,
    sh INT,
    sf INT,
    gidp INT,
    PRIMARY KEY (yearid, playerid, teamid)
);

-- Batting stats (season aggregates)
CREATE TABLE IF NOT EXISTS raw_lahman.batting (
    yearid INT,
    lgid TEXT,
    teamid TEXT,
    playerid TEXT,
    g INT,
    ab INT,
    r INT,
    h INT,
    _2b INT,
    _3b INT,
    hr INT,
    rbi INT,
    sb INT,
    cs INT,
    bb INT,
    so INT,
    ibb INT,
    hbp INT,
    sh INT,
    sf INT,
    gidp INT,
    PRIMARY KEY (yearid, playerid, teamid)
);

-- Table comments
COMMENT ON TABLE raw_lahman.people IS 'people data table';
COMMENT ON TABLE raw_lahman.teams IS 'Lahman database team information';
COMMENT ON TABLE raw_lahman.salaries IS 'Lahman database player salary data';
COMMENT ON TABLE raw_lahman.pitching IS 'Lahman database pitching statistics';
COMMENT ON TABLE raw_lahman.batting IS 'Lahman database batting statistics';
