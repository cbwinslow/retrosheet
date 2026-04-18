-- ESPN MLB Data Schema
-- Purpose: Store source-preserved ESPN API data for MLB games, schedules, and statistics
-- Integration: Part of external data layer alongside raw_retrosheet and raw_mlb
-- Data Flow: raw_espn -> bridge -> core (if needed for canonical shapes)

CREATE SCHEMA IF NOT EXISTS raw_espn;

-- ESPN Game Snapshots
-- Stores raw JSON responses from ESPN scoreboard API
CREATE TABLE IF NOT EXISTS raw_espn.game_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    game_id TEXT NOT NULL,  -- ESPN game ID
    endpoint TEXT NOT NULL,  -- API endpoint used
    http_status INTEGER,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    response_time_ms NUMERIC,
    raw_payload JSONB,
    checksum TEXT,
    game_date DATE,
    season INTEGER,
    CONSTRAINT raw_espn_game_snapshots_unique UNIQUE (game_id, fetched_at)
);

-- ESPN Schedule Snapshots
-- Stores raw JSON responses from ESPN schedule API
CREATE TABLE IF NOT EXISTS raw_espn.schedule_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    endpoint TEXT NOT NULL,
    http_status INTEGER,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    response_time_ms NUMERIC,
    raw_payload JSONB,
    checksum TEXT,
    season INTEGER,
    CONSTRAINT raw_espn_schedule_snapshots_unique UNIQUE (date, fetched_at)
);

-- ESPN Player Stats Snapshots
-- Stores raw JSON responses from ESPN player statistics API
CREATE TABLE IF NOT EXISTS raw_espn.player_stats_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    player_id TEXT NOT NULL,  -- ESPN player ID
    season INTEGER NOT NULL,
    stat_type TEXT NOT NULL,  -- 'batting', 'pitching', 'fielding'
    endpoint TEXT NOT NULL,
    http_status INTEGER,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    response_time_ms NUMERIC,
    raw_payload JSONB,
    checksum TEXT,
    CONSTRAINT raw_espn_player_stats_snapshots_unique UNIQUE (player_id, season, stat_type, fetched_at)
);

-- ESPN Team Stats Snapshots
-- Stores raw JSON responses from ESPN team statistics API
CREATE TABLE IF NOT EXISTS raw_espn.team_stats_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    team_id TEXT NOT NULL,  -- ESPN team ID
    season INTEGER NOT NULL,
    stat_type TEXT NOT NULL,  -- 'batting', 'pitching', 'fielding'
    endpoint TEXT NOT NULL,
    http_status INTEGER,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    response_time_ms NUMERIC,
    raw_payload JSONB,
    checksum TEXT,
    CONSTRAINT raw_espn_team_stats_snapshots_unique UNIQUE (team_id, season, stat_type, fetched_at)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_raw_espn_game_snapshots_game_id ON raw_espn.game_snapshots(game_id);
CREATE INDEX IF NOT EXISTS idx_raw_espn_game_snapshots_game_date ON raw_espn.game_snapshots(game_date);
CREATE INDEX IF NOT EXISTS idx_raw_espn_game_snapshots_season ON raw_espn.game_snapshots(season);
CREATE INDEX IF NOT EXISTS idx_raw_espn_schedule_snapshots_date ON raw_espn.schedule_snapshots(date);
CREATE INDEX IF NOT EXISTS idx_raw_espn_schedule_snapshots_season ON raw_espn.schedule_snapshots(season);
CREATE INDEX IF NOT EXISTS idx_raw_espn_player_stats_snapshots_player_id ON raw_espn.player_stats_snapshots(player_id);
CREATE INDEX IF NOT EXISTS idx_raw_espn_player_stats_snapshots_season ON raw_espn.player_stats_snapshots(season);
CREATE INDEX IF NOT EXISTS idx_raw_espn_team_stats_snapshots_team_id ON raw_espn.team_stats_snapshots(team_id);
CREATE INDEX IF NOT EXISTS idx_raw_espn_team_stats_snapshots_season ON raw_espn.team_stats_snapshots(season);

-- Add comments
COMMENT ON SCHEMA raw_espn IS 'Source-preserved ESPN API data for MLB games, schedules, and statistics';
COMMENT ON TABLE raw_espn.game_snapshots IS 'Raw ESPN game data with fetch provenance';
COMMENT ON TABLE raw_espn.schedule_snapshots IS 'Raw ESPN schedule data with fetch provenance';
COMMENT ON TABLE raw_espn.player_stats_snapshots IS 'Raw ESPN player statistics with fetch provenance';
COMMENT ON TABLE raw_espn.team_stats_snapshots IS 'Raw ESPN team statistics with fetch provenance';
