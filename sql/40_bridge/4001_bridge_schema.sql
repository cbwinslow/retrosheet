/*
File: sql/300_bridge_schema.sql
Purpose: Bridge layer schema for cross-source ID resolution
Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
Depends On: core schema (players, teams, games)
Called By: Scripts that need xref resolution across data sources

Tables Created:
- bridge.player_xref: Player ID mappings across sources
- bridge.team_xref: Team ID mappings across sources
- bridge.game_xref: Game ID mappings across sources
*/

-- Bridge schema
CREATE SCHEMA IF NOT EXISTS bridge;

COMMENT ON SCHEMA bridge IS 'Cross-source ID resolution layer. Maps entity IDs between MLB API, Retrosheet, ESPN, Lahman, etc.';

-- Player cross-reference table
CREATE TABLE IF NOT EXISTS bridge.player_xref (
    canonical_id VARCHAR(50) PRIMARY KEY,
    mlb_id INTEGER,
    retro_id VARCHAR(10),
    espn_id INTEGER,
    lahman_id VARCHAR(20),
    bbref_id VARCHAR(20),
    fg_id INTEGER,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    birth_date DATE,
    bats CHAR(1) CHECK (bats IN ('L', 'R', 'S')),
    throws CHAR(1) CHECK (throws IN ('L', 'R', 'S')),
    debut_date DATE,
    last_game_date DATE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraints for each source ID
    CONSTRAINT unique_mlb_id UNIQUE (mlb_id),
    CONSTRAINT unique_retro_id UNIQUE (retro_id),
    CONSTRAINT unique_espn_id UNIQUE (espn_id),
    CONSTRAINT unique_lahman_id UNIQUE (lahman_id),
    CONSTRAINT unique_bbref_id UNIQUE (bbref_id),
    CONSTRAINT unique_fg_id UNIQUE (fg_id)
);

COMMENT ON TABLE bridge.player_xref IS 'Player ID mappings across all data sources (MLB API, Retrosheet, ESPN, Lahman, etc.)';
COMMENT ON COLUMN bridge.player_xref.canonical_id IS 'Unique canonical player ID used throughout the warehouse';
COMMENT ON COLUMN bridge.player_xref.mlb_id IS 'MLB Stats API player ID';
COMMENT ON COLUMN bridge.player_xref.retro_id IS 'Retrosheet player ID (8-character code)';
COMMENT ON COLUMN bridge.player_xref.espn_id IS 'ESPN player ID';
COMMENT ON COLUMN bridge.player_xref.lahman_id IS 'Lahman database player ID';
COMMENT ON COLUMN bridge.player_xref.bbref_id IS 'Baseball-Reference player ID';
COMMENT ON COLUMN bridge.player_xref.fg_id IS 'FanGraphs player ID';

-- Indexes for player lookups
CREATE INDEX IF NOT EXISTS idx_player_xref_name ON bridge.player_xref (last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_player_xref_active ON bridge.player_xref (active) WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_player_xref_birth ON bridge.player_xref (birth_date);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION bridge.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_player_xref_updated_at ON bridge.player_xref;
CREATE TRIGGER update_player_xref_updated_at
BEFORE UPDATE ON bridge.player_xref
FOR EACH ROW
EXECUTE FUNCTION bridge.update_updated_at_column();


-- Team cross-reference table
CREATE TABLE IF NOT EXISTS bridge.team_xref (
    canonical_id INTEGER PRIMARY KEY,
    mlb_id INTEGER,
    mlb_code VARCHAR(3),
    retro_id VARCHAR(3),
    retro_code VARCHAR(3),
    espn_id INTEGER,
    lahman_id VARCHAR(10),
    lahman_code VARCHAR(3),
    name VARCHAR(100),
    city VARCHAR(100),
    nickname VARCHAR(100),
    league CHAR(2) CHECK (league IN ('AL', 'NL')),
    division VARCHAR(20),
    first_year INTEGER,
    last_year INTEGER,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_team_mlb_id UNIQUE (mlb_id),
    CONSTRAINT unique_team_mlb_code UNIQUE (mlb_code),
    CONSTRAINT unique_team_espn_id UNIQUE (espn_id)
);

COMMENT ON TABLE bridge.team_xref IS 'Team ID mappings across all data sources';
COMMENT ON COLUMN bridge.team_xref.canonical_id IS 'Canonical team ID (typically MLB ID)';
COMMENT ON COLUMN bridge.team_xref.mlb_id IS 'MLB Stats API team ID';
COMMENT ON COLUMN bridge.team_xref.mlb_code IS 'MLB team code (2-3 letters, e.g., NYY, LAD)';
COMMENT ON COLUMN bridge.team_xref.retro_id IS 'Retrosheet team ID';
COMMENT ON COLUMN bridge.team_xref.espn_id IS 'ESPN team ID';
COMMENT ON COLUMN bridge.team_xref.lahman_id IS 'Lahman database team ID';

-- Indexes for team lookups
CREATE INDEX IF NOT EXISTS idx_team_xref_code ON bridge.team_xref (mlb_code);
CREATE INDEX IF NOT EXISTS idx_team_xref_league ON bridge.team_xref (league) WHERE active = TRUE;
CREATE INDEX IF NOT EXISTS idx_team_xref_active ON bridge.team_xref (active);

DROP TRIGGER IF EXISTS update_team_xref_updated_at ON bridge.team_xref;
CREATE TRIGGER update_team_xref_updated_at
BEFORE UPDATE ON bridge.team_xref
FOR EACH ROW
EXECUTE FUNCTION bridge.update_updated_at_column();


-- Game cross-reference table
CREATE TABLE IF NOT EXISTS bridge.game_xref (
    canonical_id INTEGER PRIMARY KEY,
    mlb_id INTEGER,
    retro_id VARCHAR(12),
    espn_id INTEGER,
    game_date DATE NOT NULL,
    game_type CHAR(1) CHECK (game_type IN ('R', 'P', 'S', 'E', 'A')),
    home_team_id INTEGER,
    away_team_id INTEGER,
    home_team_code VARCHAR(3),
    away_team_code VARCHAR(3),
    year INTEGER,
    doubleheader INTEGER DEFAULT 0 CHECK (doubleheader IN (0, 1, 2)),
    season INTEGER,
    status VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_game_mlb_id UNIQUE (mlb_id),
    CONSTRAINT unique_game_retro_id UNIQUE (retro_id),
    CONSTRAINT unique_game_espn_id UNIQUE (espn_id),
    CONSTRAINT fk_home_team FOREIGN KEY (home_team_id) REFERENCES bridge.team_xref (canonical_id),
    CONSTRAINT fk_away_team FOREIGN KEY (away_team_id) REFERENCES bridge.team_xref (canonical_id)
);

COMMENT ON TABLE bridge.game_xref IS 'Game ID mappings across all data sources';
COMMENT ON COLUMN bridge.game_xref.canonical_id IS 'Canonical game ID (typically MLB game_pk)';
COMMENT ON COLUMN bridge.game_xref.mlb_id IS 'MLB Stats API game ID (game_pk)';
COMMENT ON COLUMN bridge.game_xref.retro_id IS 'Retrosheet game ID (YYYYMMDDTHH)';
COMMENT ON COLUMN bridge.game_xref.espn_id IS 'ESPN game ID';
COMMENT ON COLUMN bridge.game_xref.game_type IS 'R=Regular, P=Postseason, S=Spring, E=Exhibition, A=All-Star';
COMMENT ON COLUMN bridge.game_xref.doubleheader IS '0=single, 1=first game, 2=second game';

-- Indexes for game lookups
CREATE INDEX IF NOT EXISTS idx_game_xref_date ON bridge.game_xref (game_date);
CREATE INDEX IF NOT EXISTS idx_game_xref_season ON bridge.game_xref (season);
CREATE INDEX IF NOT EXISTS idx_game_xref_teams ON bridge.game_xref (home_team_id, away_team_id);
CREATE INDEX IF NOT EXISTS idx_game_xref_matchup ON bridge.game_xref (home_team_code, away_team_code, game_date);

DROP TRIGGER IF EXISTS update_game_xref_updated_at ON bridge.game_xref;
CREATE TRIGGER update_game_xref_updated_at
BEFORE UPDATE ON bridge.game_xref
FOR EACH ROW
EXECUTE FUNCTION bridge.update_updated_at_column();


-- View for active players with all source IDs
CREATE OR REPLACE VIEW bridge.active_players AS
SELECT
    canonical_id,
    mlb_id,
    retro_id,
    espn_id,
    lahman_id,
    bbref_id,
    fg_id,
    first_name,
    last_name,
    birth_date,
    bats,
    throws,
    debut_date
FROM bridge.player_xref
WHERE active = TRUE
ORDER BY last_name, first_name;

COMMENT ON VIEW bridge.active_players IS 'Active players with all source system IDs';


-- View for current teams
CREATE OR REPLACE VIEW bridge.current_teams AS
SELECT
    canonical_id,
    mlb_id,
    mlb_code,
    retro_id,
    name,
    city,
    nickname,
    league,
    division
FROM bridge.team_xref
WHERE active = TRUE
ORDER BY league, division, city;

COMMENT ON VIEW bridge.current_teams IS 'Current MLB teams with all source system IDs';


-- Function to find player by name
CREATE OR REPLACE FUNCTION bridge.find_player_by_name(
    p_first_name VARCHAR(100),
    p_last_name VARCHAR(100),
    p_birth_date DATE DEFAULT NULL
)
RETURNS TABLE (
    canonical_id VARCHAR(50),
    mlb_id INTEGER,
    retro_id VARCHAR(10),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    birth_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        px.canonical_id,
        px.mlb_id,
        px.retro_id,
        px.first_name,
        px.last_name,
        px.birth_date
    FROM bridge.player_xref px
    WHERE px.last_name = p_last_name
      AND px.first_name = p_first_name
      AND (p_birth_date IS NULL OR px.birth_date = p_birth_date)
    ORDER BY px.active DESC, px.last_game_date DESC NULLS LAST;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION bridge.find_player_by_name IS 'Find players by name with optional birth date matching';


-- Function to find games by date range
CREATE OR REPLACE FUNCTION bridge.find_games_by_date_range(
    p_start_date DATE,
    p_end_date DATE
)
RETURNS TABLE (
    canonical_id INTEGER,
    mlb_id INTEGER,
    retro_id VARCHAR(12),
    game_date DATE,
    home_team_code VARCHAR(3),
    away_team_code VARCHAR(3)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gx.canonical_id,
        gx.mlb_id,
        gx.retro_id,
        gx.game_date,
        gx.home_team_code,
        gx.away_team_code
    FROM bridge.game_xref gx
    WHERE gx.game_date BETWEEN p_start_date AND p_end_date
    ORDER BY gx.game_date, gx.home_team_code;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION bridge.find_games_by_date_range IS 'Find games within a date range';
