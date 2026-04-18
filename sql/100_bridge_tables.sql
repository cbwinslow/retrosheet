CREATE SCHEMA IF NOT EXISTS bridge;

-- Player ID cross-references between Retrosheet and MLB
CREATE TABLE bridge.player_xref (
    retrosheet_player_id TEXT PRIMARY KEY,
    mlb_player_id INTEGER UNIQUE,
    chadwick_register_id TEXT UNIQUE,
    first_name TEXT,
    last_name TEXT,
    bats TEXT CHECK (bats IN ('L', 'R', 'B', 'U')),
    throws TEXT CHECK (throws IN ('L', 'R', 'U')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX player_xref_mlb_id_idx ON bridge.player_xref (mlb_player_id);
CREATE INDEX player_xref_chadwick_idx ON bridge.player_xref (chadwick_register_id);

-- Team ID cross-references between Retrosheet and MLB
CREATE TABLE bridge.team_xref (
    retrosheet_team_id TEXT PRIMARY KEY,
    mlb_team_id INTEGER UNIQUE,
    team_name TEXT,
    league TEXT,
    division TEXT,
    season_start INTEGER DEFAULT 1876,  -- First season this team ID is valid
    season_end INTEGER DEFAULT 9999,    -- Last season this team ID is valid
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX team_xref_mlb_id_idx ON bridge.team_xref (mlb_team_id);

-- Park/venue ID cross-references between Retrosheet and MLB
CREATE TABLE bridge.park_xref (
    retrosheet_park_id TEXT PRIMARY KEY,
    mlb_venue_id INTEGER UNIQUE,
    park_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Game ID cross-references between Retrosheet and MLB
CREATE TABLE bridge.game_xref (
    retrosheet_game_id TEXT PRIMARY KEY,
    mlb_game_pk INTEGER UNIQUE,
    game_date DATE,
    retrosheet_home_team_id TEXT,
    retrosheet_away_team_id TEXT,
    mlb_home_team_id INTEGER,
    mlb_away_team_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX game_xref_mlb_pk_idx ON bridge.game_xref (mlb_game_pk);
CREATE INDEX game_xref_date_idx ON bridge.game_xref (game_date);

COMMENT ON SCHEMA bridge IS 'Cross-reference tables connecting Retrosheet and MLB identifiers';
COMMENT ON TABLE bridge.player_xref IS 'Player ID mapping between Retrosheet, MLB, and Chadwick Register';
COMMENT ON TABLE bridge.team_xref IS 'Team ID mapping between Retrosheet and MLB';
COMMENT ON TABLE bridge.park_xref IS 'Park/venue ID mapping between Retrosheet and MLB';
COMMENT ON TABLE bridge.game_xref IS 'Game ID mapping between Retrosheet and MLB';