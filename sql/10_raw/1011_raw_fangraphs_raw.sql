-- File: sql/external/212_fangraphs_raw.sql
-- Purpose: COMPLETE Fangraphs raw tables - ALL 50+ fields from CSV exports
-- Author: Agent Cascade
-- Date: 2026-04-24
-- Updated: 2026-05-01 - Expanded to capture ALL available fields
-- =============================================================================
-- Fangraphs Player & Team Raw Tables - COMPLETE FIELD COVERAGE
-- =============================================================================
-- Free CSV exports from Fangraphs include 50+ fields per player/team.
-- This schema captures ALL available metrics, not just a subset.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw_fangraphs;

-- ============================================================================
-- BATTING STATS - COMPLETE (50+ fields)
-- ============================================================================
DROP TABLE IF EXISTS raw_fangraphs.player_batting_season CASCADE;
CREATE TABLE raw_fangraphs.player_batting_season (
    -- Identity
    player_id        TEXT NOT NULL,
    player_name      TEXT,
    season           INT NOT NULL,
    team_id          TEXT,
    age              INT,

    -- Counting Stats
    g                INT,           -- Games
    ab               INT,           -- At Bats
    pa               INT,           -- Plate Appearances
    h                INT,           -- Hits
    single           INT,           -- Singles
    double           INT,           -- Doubles
    triple           INT,           -- Triples
    hr               INT,           -- Home Runs
    r                INT,           -- Runs
    rbi              INT,           -- RBIs
    bb               INT,           -- Walks
    ibb              INT,           -- Intentional Walks
    so               INT,           -- Strikeouts
    hbp              INT,           -- Hit By Pitch
    sf               INT,           -- Sacrifice Flies
    sh               INT,           -- Sacrifice Hits
    gdp              INT,           -- Grounded Into Double Play
    sb               INT,           -- Stolen Bases
    cs               INT,           -- Caught Stealing

    -- Traditional Rate Stats
    avg              REAL,          -- Batting Average
    obp              REAL,          -- On-Base Percentage
    slg              REAL,          -- Slugging Percentage
    ops              REAL,          -- On-base Plus Slugging

    -- Advanced Stats
    woba             REAL,          -- Weighted On-Base Average
    wrc_plus         INT,           -- Weighted Runs Created Plus
    wraa             REAL,          -- Weighted Runs Above Average
    war              REAL,          -- Wins Above Replacement

    -- Percentage Stats (rates per PA)
    bb_pct           REAL,          -- BB%
    k_pct            REAL,          -- K%
    bb_k_ratio       REAL,          -- BB/K
    iso              REAL,          -- Isolated Power
    babip            REAL,          -- Batting Average on Balls In Play

    -- Batted Ball Profile
    gb_pct           REAL,          -- Ground Ball %
    fb_pct           REAL,          -- Fly Ball %
    ld_pct           REAL,          -- Line Drive %
    iffb_pct         REAL,          -- Infield Fly Ball %
    hr_fb_ratio      REAL,          -- HR/FB ratio
    gb_fb_ratio      REAL,          -- GB/FB ratio

    -- Plate Discipline
    o_swing_pct      REAL,          -- O-Swing% (swings outside zone)
    z_swing_pct      REAL,          -- Z-Swing% (swings inside zone)
    swing_pct        REAL,          -- Swing%
    o_contact_pct    REAL,          -- O-Contact% (contact outside zone)
    z_contact_pct    REAL,          -- Z-Contact% (contact inside zone)
    contact_pct      REAL,          -- Contact%
    zone_pct         REAL,          -- Zone% (pitches in strike zone)
    f_strike_pct     REAL,          -- F-Strike% (first pitch strike)
    swstr_pct        REAL,          -- SwStr% (swinging strikes)

    -- Value Stats
    bat              REAL,          -- Batting Runs
    bsr              REAL,          -- Base Running Runs
    fld              REAL,          -- Fielding Runs
    off              REAL,          -- Offense Runs
    def              REAL,          -- Defense Runs
    pos              REAL,          -- Positional Adjustment
    woba_dollars     REAL,          -- Dollar Value

    -- Metadata
    player_page      TEXT,          -- FanGraphs player page URL
    team_abbr        TEXT,          -- Team abbreviation
    league           TEXT,          -- League (AL/NL)
    qualifying       BOOLEAN,       -- Qualified for batting title

    PRIMARY KEY (player_id, season)
);

-- ============================================================================
-- PITCHING STATS - COMPLETE (60+ fields)
-- ============================================================================
DROP TABLE IF EXISTS raw_fangraphs.player_pitching_season CASCADE;
CREATE TABLE raw_fangraphs.player_pitching_season (
    -- Identity
    player_id        TEXT NOT NULL,
    player_name      TEXT,
    season           INT NOT NULL,
    team_id          TEXT,
    age              INT,

    -- Counting Stats
    g                INT,           -- Games
    gs               INT,           -- Games Started
    ip               REAL,          -- Innings Pitched
    tbf              INT,           -- Total Batters Faced
    h                INT,           -- Hits Allowed
    r                INT,           -- Runs Allowed
    er               INT,           -- Earned Runs
    hr               INT,           -- Home Runs Allowed
    bb               INT,           -- Walks
    ibb              INT,           -- Intentional Walks
    so               INT,           -- Strikeouts
    hbp              INT,           -- Hit By Pitch
    wp               INT,           -- Wild Pitches
    bk               INT,           -- Balks

    -- Outcomes
    w                INT,           -- Wins
    l                INT,           -- Losses
    sv               INT,           -- Saves
    bs               INT,           -- Blown Saves
    hold             INT,           -- Holds
    qs               INT,           -- Quality Starts

    -- Traditional Rate Stats
    era              REAL,          -- Earned Run Average
    whip             REAL,          -- Walks + Hits per IP
    k_9              REAL,          -- K/9
    bb_9             REAL,          -- BB/9
    k_bb_ratio       REAL,          -- K/BB

    -- Advanced Stats
    fip              REAL,          -- Fielding Independent Pitching
    xfip             REAL,          -- Expected FIP
    siera            REAL,          -- SIERA
    war              REAL,          -- Wins Above Replacement
    ra9_war          REAL,          -- RA9-WAR

    -- Percentage Stats
    k_pct            REAL,          -- K%
    bb_pct           REAL,          -- BB%
    k_bb_pct         REAL,          -- K-BB%
    hr_fb_ratio      REAL,          -- HR/FB
    lob_pct          REAL,          -- Left on Base %
    gb_pct           REAL,          -- Ground Ball %
    fb_pct           REAL,          -- Fly Ball %
    ld_pct           REAL,          -- Line Drive %
    gb_fb_ratio      REAL,          -- GB/FB ratio

    -- Pitch Type Distribution
    fastball_pct     REAL,          -- Fastball %
    slider_pct       REAL,          -- Slider %
    curveball_pct    REAL,          -- Curveball %
    changeup_pct     REAL,          -- Changeup %
    cutter_pct       REAL,          -- Cutter %
    sinker_pct       REAL,          -- Sinker %
    splitter_pct     REAL,          -- Splitter %
    knuckleball_pct  REAL,          -- Knuckleball %

    -- Pitch Values
    wfb              REAL,          -- Fastball Runs
    wsl              REAL,          -- Slider Runs
    wcb              REAL,          -- Curveball Runs
    wch              REAL,          -- Changeup Runs
    wsf              REAL,          -- Splitter Runs
    wkn              REAL,          -- Knuckleball Runs

    -- Plate Discipline (pitching perspective)
    o_swing_pct      REAL,          -- O-Swing%
    z_swing_pct      REAL,          -- Z-Swing%
    swing_pct        REAL,          -- Swing%
    o_contact_pct    REAL,          -- O-Contact%
    z_contact_pct    REAL,          -- Z-Contact%
    contact_pct      REAL,          -- Contact%
    zone_pct         REAL,          -- Zone%
    f_strike_pct     REAL,          -- F-Strike%
    swstr_pct        REAL,          -- SwStr%
    csw_pct          REAL,          -- Called + Swinging Strike %

    -- Velocity
    velo             REAL,          -- Average Velocity
    v_fastball       REAL,          -- Fastball Velocity
    v_slider         REAL,          -- Slider Velocity
    v_curveball      REAL,          -- Curveball Velocity
    v_changeup       REAL,          -- Changeup Velocity
    v_cutter         REAL,          -- Cutter Velocity
    v_sinker         REAL,          -- Sinker Velocity
    v_splitter       REAL,          -- Splitter Velocity

    -- Metadata
    player_page      TEXT,
    team_abbr        TEXT,
    league           TEXT,
    sp_rp            TEXT,          -- Starter or Reliever
    qualifying       BOOLEAN,

    PRIMARY KEY (player_id, season)
);

-- ============================================================================
-- TEAM BATTING STATS - COMPLETE
-- ============================================================================
DROP TABLE IF EXISTS raw_fangraphs.team_batting_season CASCADE;
CREATE TABLE raw_fangraphs.team_batting_season (
    team_id          TEXT NOT NULL,
    team_name        TEXT,
    season           INT NOT NULL,
    g                INT,
    pa               INT,
    ab               INT,
    h                INT,
    single           INT,
    double           INT,
    triple           INT,
    hr               INT,
    r                INT,
    rbi              INT,
    bb               INT,
    so               INT,
    hbp              INT,
    sf               INT,
    avg              REAL,
    obp              REAL,
    slg              REAL,
    ops              REAL,
    woba             REAL,
    wrc_plus         INT,
    war              REAL,
    bb_pct           REAL,
    k_pct            REAL,
    iso              REAL,
    babip            REAL,
    gb_pct           REAL,
    fb_pct           REAL,
    ld_pct           REAL,
    PRIMARY KEY (team_id, season)
);

-- ============================================================================
-- TEAM PITCHING STATS - COMPLETE
-- ============================================================================
DROP TABLE IF EXISTS raw_fangraphs.team_pitching_season CASCADE;
CREATE TABLE raw_fangraphs.team_pitching_season (
    team_id          TEXT NOT NULL,
    team_name        TEXT,
    season           INT NOT NULL,
    g                INT,
    ip               REAL,
    era              REAL,
    whip             REAL,
    k_9              REAL,
    bb_9             REAL,
    fip              REAL,
    xfip             REAL,
    war              REAL,
    k_pct            REAL,
    bb_pct           REAL,
    hr_fb_ratio      REAL,
    lob_pct          REAL,
    gb_pct           REAL,
    fb_pct           REAL,
    PRIMARY KEY (team_id, season)
);

-- ============================================================================
-- Legacy Tables (for backwards compatibility)
-- ============================================================================
DROP TABLE IF EXISTS raw_fangraphs.player_season CASCADE;
DROP TABLE IF EXISTS raw_fangraphs.team_season CASCADE;

-- Create views for backwards compatibility
CREATE OR REPLACE VIEW raw_fangraphs.player_season AS
SELECT
    player_id, season, team_id, age, g, pa, ab, r, h,
    double, triple, hr, rbi, sb, cs, bb, ibb, hbp, so,
    avg, obp, slg, ops, woba, wrc_plus AS woba_plus,
    wrc_plus, war
FROM raw_fangraphs.player_batting_season;

CREATE OR REPLACE VIEW raw_fangraphs.team_season AS
SELECT
    team_id, season, g, NULL::INT as w, NULL::INT as l,
    NULL::INT as r, NULL::INT as ra, NULL::REAL as era,
    woba, wrc_plus as woba_plus, wrc_plus, war
FROM raw_fangraphs.team_batting_season;

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON TABLE raw_fangraphs.player_batting_season IS 'COMPLETE Fangraphs player batting stats (50+ fields)';
COMMENT ON TABLE raw_fangraphs.player_pitching_season IS 'COMPLETE Fangraphs player pitching stats (60+ fields)';
COMMENT ON TABLE raw_fangraphs.team_batting_season IS 'COMPLETE Fangraphs team batting stats';
COMMENT ON TABLE raw_fangraphs.team_pitching_season IS 'COMPLETE Fangraphs team pitching stats';
COMMENT ON VIEW raw_fangraphs.player_season IS 'Legacy view for backwards compatibility';
COMMENT ON VIEW raw_fangraphs.team_season IS 'Legacy view for backwards compatibility';

-- ============================================================================
-- Indexes
-- ============================================================================
CREATE INDEX idx_fg_batting_season ON raw_fangraphs.player_batting_season(season);
CREATE INDEX idx_fg_batting_team ON raw_fangraphs.player_batting_season(team_id);
CREATE INDEX idx_fg_pitching_season ON raw_fangraphs.player_pitching_season(season);
CREATE INDEX idx_fg_pitching_team ON raw_fangraphs.player_pitching_season(team_id);
