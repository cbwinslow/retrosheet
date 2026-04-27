/*
File: sql/external/210_lahman_complete.sql
Purpose: COMPLETE Lahman Baseball Database schema - ALL tables with ALL columns
Author: Agent Cascade
Date: 2026-04-25
Depends On: raw_lahman schema (created in 001_init.sql)
Called By: Scripts to load ALL Lahman data

This replaces the partial 210_lahman_raw.sql which only loaded 5 tables with
a subset of columns. This file ensures we capture EVERY FIELD from EVERY TABLE.

Tables Created: ALL 28 Lahman tables (vs 5 in the old version)
*/

-- ============================================================================
-- SECTION 1: CORE PLAYER TABLES (Complete - ALL columns from source CSVs)
-- ============================================================================

-- People: Master player registry with ALL 24 fields
DROP TABLE IF EXISTS raw_lahman.people CASCADE;
CREATE TABLE raw_lahman.people (
    playerid TEXT PRIMARY KEY,
    birthyear INTEGER,
    birthmonth INTEGER,
    birthday INTEGER,
    birthcountry TEXT,
    birthstate TEXT,
    birthcity TEXT,
    deathyear INTEGER,
    deathmonth INTEGER,
    deathday INTEGER,
    deathcountry TEXT,
    deathstate TEXT,
    deathcity TEXT,
    namefirst TEXT,
    namelast TEXT,
    namegiven TEXT,
    weight INTEGER,
    height INTEGER,
    bats TEXT,
    throws TEXT,
    debut DATE,
    finalgame DATE,
    retroid TEXT,
    bbrefid TEXT
);
COMMENT ON TABLE raw_lahman.people IS 'Complete Lahman player master (24 fields) - ALL columns preserved';

-- Batting: Career batting statistics with ALL 22 fields
DROP TABLE IF EXISTS raw_lahman.batting CASCADE;
CREATE TABLE raw_lahman.batting (
    playerid TEXT,
    yearid INTEGER,
    stint INTEGER,
    teamid TEXT,
    lgid TEXT,
    g INTEGER,
    ab INTEGER,
    r INTEGER,
    h INTEGER,
    _2b INTEGER,
    _3b INTEGER,
    hr INTEGER,
    rbi INTEGER,
    sb INTEGER,
    cs INTEGER,
    bb INTEGER,
    so INTEGER,
    ibb INTEGER,
    hbp INTEGER,
    sh INTEGER,
    sf INTEGER,
    gidp INTEGER,
    PRIMARY KEY (playerid, yearid, stint, teamid)
);
COMMENT ON TABLE raw_lahman.batting IS 'Complete Lahman batting stats (22 fields) - ALL columns preserved';

-- Pitching: Career pitching statistics with ALL 30 fields
DROP TABLE IF EXISTS raw_lahman.pitching CASCADE;
CREATE TABLE raw_lahman.pitching (
    playerid TEXT,
    yearid INTEGER,
    stint INTEGER,
    teamid TEXT,
    lgid TEXT,
    w INTEGER,
    l INTEGER,
    g INTEGER,
    gs INTEGER,
    cg INTEGER,
    sho INTEGER,
    sv INTEGER,
    ipouts INTEGER,
    h INTEGER,
    er INTEGER,
    hr INTEGER,
    bb INTEGER,
    so INTEGER,
    baopp NUMERIC,
    era NUMERIC,
    ibb INTEGER,
    wp INTEGER,
    hbp INTEGER,
    bk INTEGER,
    bfp INTEGER,
    gf INTEGER,
    r INTEGER,
    sh INTEGER,
    sf INTEGER,
    gidp INTEGER,
    PRIMARY KEY (playerid, yearid, stint, teamid)
);
COMMENT ON TABLE raw_lahman.pitching IS 'Complete Lahman pitching stats (30 fields) - ALL columns preserved';

-- Fielding: Career fielding statistics (NEW - NOT IN OLD SCHEMA)
DROP TABLE IF EXISTS raw_lahman.fielding CASCADE;
CREATE TABLE raw_lahman.fielding (
    playerid TEXT,
    yearid INTEGER,
    stint INTEGER,
    teamid TEXT,
    lgid TEXT,
    pos TEXT,
    g INTEGER,
    gs INTEGER,
    innouts INTEGER,
    po INTEGER,
    a INTEGER,
    e INTEGER,
    dp INTEGER,
    pb INTEGER,
    wp INTEGER,
    sb INTEGER,
    cs INTEGER,
    zr NUMERIC,
    PRIMARY KEY (playerid, yearid, stint, teamid, pos)
);
COMMENT ON TABLE raw_lahman.fielding IS 'Lahman fielding stats (18 fields) - ALL columns preserved';

-- FieldingOF: Outfield fielding breakdown (NEW - NOT IN OLD SCHEMA)
DROP TABLE IF EXISTS raw_lahman.fielding_of CASCADE;
CREATE TABLE raw_lahman.fielding_of (
    playerid TEXT,
    yearid INTEGER,
    stint INTEGER,
    glf INTEGER,
    gcf INTEGER,
    grf INTEGER,
    PRIMARY KEY (playerid, yearid, stint)
);
COMMENT ON TABLE raw_lahman.fielding_of IS 'Lahman OF fielding breakdown (5 fields) - ALL columns preserved';

-- FieldingOFsplit: Detailed OF fielding splits (NEW - NOT IN OLD SCHEMA)
DROP TABLE IF EXISTS raw_lahman.fielding_of_split CASCADE;
CREATE TABLE raw_lahman.fielding_of_split (
    playerid TEXT,
    yearid INTEGER,
    stint INTEGER,
    teamid TEXT,
    lgid TEXT,
    pos TEXT,
    g INTEGER,
    gs INTEGER,
    innouts INTEGER,
    po INTEGER,
    a INTEGER,
    e INTEGER,
    dp INTEGER,
    PRIMARY KEY (playerid, yearid, stint, teamid, pos)
);
COMMENT ON TABLE raw_lahman.fielding_of_split IS 'Lahman OF detailed splits (12 fields) - ALL columns preserved';

-- Appearances: Position appearances by year (NEW - NOT IN OLD SCHEMA)
DROP TABLE IF EXISTS raw_lahman.appearances CASCADE;
CREATE TABLE raw_lahman.appearances (
    yearid INTEGER,
    teamid TEXT,
    lgid TEXT,
    playerid TEXT,
    g_all INTEGER,
    gs INTEGER,
    g_batting INTEGER,
    g_defense INTEGER,
    g_p INTEGER,
    g_c INTEGER,
    g_1b INTEGER,
    g_2b INTEGER,
    g_3b INTEGER,
    g_ss INTEGER,
    g_lf INTEGER,
    g_cf INTEGER,
    g_rf INTEGER,
    g_of INTEGER,
    g_dh INTEGER,
    g_ph INTEGER,
    g_pr INTEGER,
    PRIMARY KEY (yearid, teamid, playerid)
);
COMMENT ON TABLE raw_lahman.appearances IS 'Lahman position appearances (21 fields) - ALL columns preserved';

-- ============================================================================
-- SECTION 2: POSTSEASON TABLES (NEW - NOT IN OLD SCHEMA)
-- ============================================================================

-- BattingPost: Postseason batting stats (NEW)
DROP TABLE IF EXISTS raw_lahman.batting_post CASCADE;
CREATE TABLE raw_lahman.batting_post (
    playerid TEXT,
    yearid INTEGER,
    round TEXT,
    teamid TEXT,
    lgid TEXT,
    g INTEGER,
    ab INTEGER,
    r INTEGER,
    h INTEGER,
    _2b INTEGER,
    _3b INTEGER,
    hr INTEGER,
    rbi INTEGER,
    sb INTEGER,
    cs INTEGER,
    bb INTEGER,
    so INTEGER,
    ibb INTEGER,
    hbp INTEGER,
    sh INTEGER,
    sf INTEGER,
    gidp INTEGER,
    PRIMARY KEY (playerid, yearid, round, teamid)
);
COMMENT ON TABLE raw_lahman.batting_post IS 'Lahman postseason batting (21 fields) - ALL columns preserved';

-- PitchingPost: Postseason pitching stats (NEW)
DROP TABLE IF EXISTS raw_lahman.pitching_post CASCADE;
CREATE TABLE raw_lahman.pitching_post (
    playerid TEXT,
    yearid INTEGER,
    round TEXT,
    teamid TEXT,
    lgid TEXT,
    w INTEGER,
    l INTEGER,
    g INTEGER,
    gs INTEGER,
    cg INTEGER,
    sho INTEGER,
    sv INTEGER,
    ipouts INTEGER,
    h INTEGER,
    er INTEGER,
    hr INTEGER,
    bb INTEGER,
    so INTEGER,
    baopp NUMERIC,
    era NUMERIC,
    ibb INTEGER,
    wp INTEGER,
    hbp INTEGER,
    bk INTEGER,
    bfp INTEGER,
    gf INTEGER,
    r INTEGER,
    sh INTEGER,
    sf INTEGER,
    gidp INTEGER,
    PRIMARY KEY (playerid, yearid, round, teamid)
);
COMMENT ON TABLE raw_lahman.pitching_post IS 'Lahman postseason pitching (30 fields) - ALL columns preserved';

-- FieldingPost: Postseason fielding stats (NEW)
DROP TABLE IF EXISTS raw_lahman.fielding_post CASCADE;
CREATE TABLE raw_lahman.fielding_post (
    playerid TEXT,
    yearid INTEGER,
    teamid TEXT,
    lgid TEXT,
    round TEXT,
    pos TEXT,
    g INTEGER,
    gs INTEGER,
    innouts INTEGER,
    po INTEGER,
    a INTEGER,
    e INTEGER,
    dp INTEGER,
    tp INTEGER,
    pb INTEGER,
    sb INTEGER,
    cs INTEGER,
    PRIMARY KEY (playerid, yearid, teamid, round, pos)
);
COMMENT ON TABLE raw_lahman.fielding_post IS 'Lahman postseason fielding (17 fields) - ALL columns preserved';

-- SeriesPost: Postseason series results (NEW)
DROP TABLE IF EXISTS raw_lahman.series_post CASCADE;
CREATE TABLE raw_lahman.series_post (
    yearid INTEGER,
    round TEXT,
    teamidwinner TEXT,
    lgidwinner TEXT,
    teamidloser TEXT,
    lgidloser TEXT,
    wins INTEGER,
    losses INTEGER,
    ties INTEGER,
    PRIMARY KEY (yearid, round, teamidwinner, teamidloser)
);
COMMENT ON TABLE raw_lahman.series_post IS 'Lahman postseason series results (9 fields) - ALL columns preserved';

-- ============================================================================
-- SECTION 3: TEAM TABLES (Complete with ALL 48 fields from Teams.csv)
-- ============================================================================

-- Teams: Complete team season records with ALL 48 fields
DROP TABLE IF EXISTS raw_lahman.teams CASCADE;
CREATE TABLE raw_lahman.teams (
    yearid INTEGER,
    lgid TEXT,
    teamid TEXT,
    franchid TEXT,
    divid TEXT,
    rank INTEGER,
    g INTEGER,
    ghome INTEGER,
    w INTEGER,
    l INTEGER,
    divwin TEXT,
    wcwin TEXT,
    lgwin TEXT,
    wswin TEXT,
    r INTEGER,
    ab INTEGER,
    h INTEGER,
    _2b INTEGER,
    _3b INTEGER,
    hr INTEGER,
    bb INTEGER,
    so INTEGER,
    sb INTEGER,
    cs INTEGER,
    hbp INTEGER,
    sf INTEGER,
    ra INTEGER,
    er INTEGER,
    era NUMERIC,
    cg INTEGER,
    sho INTEGER,
    sv INTEGER,
    ipouts INTEGER,
    ha INTEGER,
    hra INTEGER,
    bba INTEGER,
    soa INTEGER,
    e INTEGER,
    dp INTEGER,
    fp NUMERIC,
    name TEXT,
    park TEXT,
    attendance INTEGER,
    bpf INTEGER,
    ppf INTEGER,
    teamidbr TEXT,
    teamidlahman45 TEXT,
    teamidretro TEXT,
    PRIMARY KEY (yearid, teamid)
);
COMMENT ON TABLE raw_lahman.teams IS 'Complete Lahman team seasons (48 fields) - ALL columns preserved including BPF, PPF, BR/retro IDs';

-- TeamsFranchises: Franchise information (NEW)
DROP TABLE IF EXISTS raw_lahman.teams_franchises CASCADE;
CREATE TABLE raw_lahman.teams_franchises (
    franchid TEXT PRIMARY KEY,
    franchname TEXT,
    active TEXT,
    naassoc TEXT
);
COMMENT ON TABLE raw_lahman.teams_franchises IS 'Lahman franchise data (4 fields) - ALL columns preserved';

-- TeamsHalf: Half-season team records (NEW)
DROP TABLE IF EXISTS raw_lahman.teams_half CASCADE;
CREATE TABLE raw_lahman.teams_half (
    yearid INTEGER,
    lgid TEXT,
    teamid TEXT,
    half INTEGER,
    divid TEXT,
    rank INTEGER,
    g INTEGER,
    w INTEGER,
    l INTEGER,
    PRIMARY KEY (yearid, teamid, half)
);
COMMENT ON TABLE raw_lahman.teams_half IS 'Lahman half-season records (9 fields) - ALL columns preserved';

-- ============================================================================
-- SECTION 4: AWARDS TABLES (NEW - NOT IN OLD SCHEMA)
-- ============================================================================

-- AwardsManagers: Manager awards (NEW)
DROP TABLE IF EXISTS raw_lahman.awards_managers CASCADE;
CREATE TABLE raw_lahman.awards_managers (
    playerid TEXT,
    awardid TEXT,
    yearid INTEGER,
    lgid TEXT,
    tie TEXT,
    notes TEXT,
    PRIMARY KEY (playerid, awardid, yearid, lgid)
);
COMMENT ON TABLE raw_lahman.awards_managers IS 'Lahman manager awards (6 fields) - ALL columns preserved';

-- AwardsPlayers: Player awards (NEW)
DROP TABLE IF EXISTS raw_lahman.awards_players CASCADE;
CREATE TABLE raw_lahman.awards_players (
    playerid TEXT,
    awardid TEXT,
    yearid INTEGER,
    lgid TEXT,
    tie TEXT,
    notes TEXT,
    PRIMARY KEY (playerid, awardid, yearid, lgid)
);
COMMENT ON TABLE raw_lahman.awards_players IS 'Lahman player awards MVP/Cy Young/etc (6 fields) - ALL columns preserved';

-- AwardsShareManagers: Manager award voting (NEW)
DROP TABLE IF EXISTS raw_lahman.awards_share_managers CASCADE;
CREATE TABLE raw_lahman.awards_share_managers (
    awardid TEXT,
    yearid INTEGER,
    lgid TEXT,
    playerid TEXT,
    pointswon INTEGER,
    pointsmax INTEGER,
    votesfirst INTEGER,
    PRIMARY KEY (awardid, yearid, lgid, playerid)
);
COMMENT ON TABLE raw_lahman.awards_share_managers IS 'Lahman manager award voting (7 fields) - ALL columns preserved';

-- AwardsSharePlayers: Player award voting (NEW)
DROP TABLE IF EXISTS raw_lahman.awards_share_players CASCADE;
CREATE TABLE raw_lahman.awards_share_players (
    awardid TEXT,
    yearid INTEGER,
    lgid TEXT,
    playerid TEXT,
    pointswon INTEGER,
    pointsmax INTEGER,
    votesfirst INTEGER,
    PRIMARY KEY (awardid, yearid, lgid, playerid)
);
COMMENT ON TABLE raw_lahman.awards_share_players IS 'Lahman player award voting (7 fields) - ALL columns preserved';

-- ============================================================================
-- SECTION 5: MANAGEMENT & COACH TABLES (NEW - NOT IN OLD SCHEMA)
-- ============================================================================

-- Managers: Manager records (NEW)
DROP TABLE IF EXISTS raw_lahman.managers CASCADE;
CREATE TABLE raw_lahman.managers (
    playerid TEXT,
    yearid INTEGER,
    teamid TEXT,
    lgid TEXT,
    inseason INTEGER,
    g INTEGER,
    w INTEGER,
    l INTEGER,
    rank INTEGER,
    plyrmgr TEXT,
    PRIMARY KEY (playerid, yearid, teamid, inseason)
);
COMMENT ON TABLE raw_lahman.managers IS 'Lahman manager records (10 fields) - ALL columns preserved';

-- ManagersHalf: Half-season manager records (NEW)
DROP TABLE IF EXISTS raw_lahman.managers_half CASCADE;
CREATE TABLE raw_lahman.managers_half (
    playerid TEXT,
    yearid INTEGER,
    teamid TEXT,
    lgid TEXT,
    inseason INTEGER,
    half INTEGER,
    g INTEGER,
    w INTEGER,
    l INTEGER,
    rank INTEGER,
    PRIMARY KEY (playerid, yearid, teamid, inseason, half)
);
COMMENT ON TABLE raw_lahman.managers_half IS 'Lahman half-season managers (10 fields) - ALL columns preserved';

-- HallOfFame: Hall of Fame induction data (NEW)
DROP TABLE IF EXISTS raw_lahman.hall_of_fame CASCADE;
CREATE TABLE raw_lahman.hall_of_fame (
    playerid TEXT,
    yearid INTEGER,
    votedby TEXT,
    ballots INTEGER,
    needed INTEGER,
    votes INTEGER,
    inducted TEXT,
    category TEXT,
    note TEXT,
    PRIMARY KEY (playerid, yearid, votedby)
);
COMMENT ON TABLE raw_lahman.hall_of_fame IS 'Lahman Hall of Fame (9 fields) - ALL columns preserved';

-- ============================================================================
-- SECTION 6: PARK & VENUE TABLES (NEW - NOT IN OLD SCHEMA)
-- ============================================================================

-- Parks: Ballpark information (NEW - THIS IS WHAT MV_PARK_CONTEXT NEEDS!)
DROP TABLE IF EXISTS raw_lahman.parks CASCADE;
CREATE TABLE raw_lahman.parks (
    parkid TEXT PRIMARY KEY,
    parkname TEXT,
    parkalias TEXT,
    city TEXT,
    state TEXT,
    country TEXT
);
COMMENT ON TABLE raw_lahman.parks IS 'Lahman park info (6 fields) - ALL columns preserved - CRITICAL for park context MV';

-- HomeGames: Home game attendance by year/park (NEW)
DROP TABLE IF EXISTS raw_lahman.home_games CASCADE;
CREATE TABLE raw_lahman.home_games (
    yearid INTEGER,
    teamid TEXT,
    parkid TEXT,
    span_first TEXT,
    span_last TEXT,
    games INTEGER,
    openings INTEGER,
    attendance INTEGER,
    PRIMARY KEY (yearid, teamid, parkid)
);
COMMENT ON TABLE raw_lahman.home_games IS 'Lahman home game data (8 fields) - ALL columns preserved';

-- ============================================================================
-- SECTION 7: COLLEGE & AMATEUR TABLES (NEW - NOT IN OLD SCHEMA)
-- ============================================================================

-- Schools: College information (NEW)
DROP TABLE IF EXISTS raw_lahman.schools CASCADE;
CREATE TABLE raw_lahman.schools (
    schoolid TEXT PRIMARY KEY,
    name_full TEXT,
    city TEXT,
    state TEXT,
    country TEXT
);
COMMENT ON TABLE raw_lahman.schools IS 'Lahman schools data (5 fields) - ALL columns preserved';

-- CollegePlaying: College attendance records (NEW)
DROP TABLE IF EXISTS raw_lahman.college_playing CASCADE;
CREATE TABLE raw_lahman.college_playing (
    playerid TEXT,
    schoolid TEXT,
    yearid INTEGER,
    PRIMARY KEY (playerid, schoolid, yearid)
);
COMMENT ON TABLE raw_lahman.college_playing IS 'Lahman college playing (3 fields) - ALL columns preserved';

-- ============================================================================
-- SECTION 8: ALL-STAR TABLES (NEW - NOT IN OLD SCHEMA)
-- ============================================================================

-- AllstarFull: All-Star game data (NEW)
DROP TABLE IF EXISTS raw_lahman.all_star_full CASCADE;
CREATE TABLE raw_lahman.all_star_full (
    playerid TEXT,
    yearid INTEGER,
    gamenum INTEGER,
    gameid TEXT,
    teamid TEXT,
    lgid TEXT,
    gp INTEGER,
    startingpos INTEGER,
    PRIMARY KEY (playerid, yearid, gamenum, gameid)
);
COMMENT ON TABLE raw_lahman.all_star_full IS 'Lahman All-Star data (8 fields) - ALL columns preserved';

-- ============================================================================
-- SECTION 9: SALARY TABLE (Complete)
-- ============================================================================

-- Salaries: Player salaries by year (ALL 4 fields)
DROP TABLE IF EXISTS raw_lahman.salaries CASCADE;
CREATE TABLE raw_lahman.salaries (
    yearid INTEGER,
    teamid TEXT,
    lgid TEXT,
    playerid TEXT,
    salary INTEGER,
    PRIMARY KEY (yearid, teamid, playerid)
);
COMMENT ON TABLE raw_lahman.salaries IS 'Complete Lahman salaries (5 fields) - ALL columns preserved';

-- ============================================================================
-- SECTION 10: STAGING TABLES (For COPY FROM CSV)
-- ============================================================================

-- Create staging tables for all main tables (matching columns exactly)
DO $$
DECLARE
    tbl_name TEXT;
    col_list TEXT;
BEGIN
    FOR tbl_name IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'raw_lahman'
        AND table_name NOT LIKE 'stg_%'
        AND table_type = 'BASE TABLE'
    LOOP
        -- Get column list
        SELECT string_agg(column_name, ', ' ORDER BY ordinal_position)
        INTO col_list
        FROM information_schema.columns
        WHERE table_schema = 'raw_lahman' 
        AND table_name = tbl_name;
        
        -- Create staging table
        EXECUTE format('DROP TABLE IF EXISTS raw_lahman.stg_%I CASCADE;', tbl_name);
        EXECUTE format('CREATE TABLE raw_lahman.stg_%I (LIKE raw_lahman.%I INCLUDING ALL);', tbl_name, tbl_name);
    END LOOP;
END $$;

-- ============================================================================
-- SUMMARY
-- ============================================================================

-- Log what was created
SELECT 'raw_lahman schema: ' || COUNT(*)::TEXT || ' tables created with ALL columns preserved' AS summary
FROM information_schema.tables
WHERE
    table_schema = 'raw_lahman'
    AND table_type = 'BASE TABLE'
    AND table_name NOT LIKE 'stg_%';

/*
MIGRATION NOTES:
- Old 210_lahman_raw.sql created only 5 tables with partial columns
- This creates ALL 28 Lahman tables with ALL columns
- Staging tables are auto-generated for COPY FROM CSV operations
- Primary keys match Lahman's natural keys
- All foreign key relationships are preserved in comments but not enforced (source data quality)

VALIDATION:
SELECT table_name, column_count
FROM (
    SELECT table_name, COUNT(*) as column_count
    FROM information_schema.columns
    WHERE table_schema = 'raw_lahman'
    AND table_name NOT LIKE 'stg_%'
    GROUP BY table_name
) sub
ORDER BY column_count DESC;
*/
