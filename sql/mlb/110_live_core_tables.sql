-- Live game and event tables for real-time MLB data
-- These mirror the structure of core.games and core.events but for live data

CREATE TABLE IF NOT EXISTS core.live_games (
    game_id TEXT PRIMARY KEY,
    season INTEGER,
    game_date DATE,
    home_team_id TEXT,
    away_team_id TEXT,
    home_team_name TEXT,
    away_team_name TEXT,
    park_id TEXT,
    home_score INTEGER DEFAULT 0,
    away_score INTEGER DEFAULT 0,
    is_complete BOOLEAN DEFAULT FALSE,
    source_type TEXT DEFAULT 'mlb_live',
    raw_payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

ALTER TABLE core.live_games
ADD COLUMN IF NOT EXISTS raw_payload JSONB,
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
ADD COLUMN IF NOT EXISTS mlb_game_pk INTEGER,
ADD COLUMN IF NOT EXISTS snapshot_id INTEGER,
ADD COLUMN IF NOT EXISTS snapshot_fetched_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS status_code TEXT,
ADD COLUMN IF NOT EXISTS detailed_state TEXT,
ADD COLUMN IF NOT EXISTS venue_name TEXT;

CREATE TABLE IF NOT EXISTS core.live_events (
    game_id TEXT REFERENCES core.live_games (game_id),
    event_id INTEGER,
    season INTEGER,
    inning INTEGER,
    is_bottom_inning BOOLEAN,
    event_sequence INTEGER,
    batter_id TEXT,
    pitcher_id TEXT,
    batter_hand TEXT,
    pitcher_hand TEXT,
    outs_before INTEGER,
    balls INTEGER,
    strikes INTEGER,
    start_bases INTEGER,
    event_code INTEGER,
    event_text TEXT,
    is_at_bat BOOLEAN,
    is_plate_appearance BOOLEAN,
    hit_value INTEGER,
    is_hit BOOLEAN,
    is_walk BOOLEAN,
    is_strikeout BOOLEAN,
    is_home_run BOOLEAN,
    runs_on_play INTEGER,
    rbi INTEGER,
    source_type TEXT DEFAULT 'mlb_live',
    raw_play JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    PRIMARY KEY (game_id, event_id)
);

ALTER TABLE core.live_events
ADD COLUMN IF NOT EXISTS raw_play JSONB,
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
ADD COLUMN IF NOT EXISTS mlb_game_pk INTEGER,
ADD COLUMN IF NOT EXISTS snapshot_id INTEGER,
ADD COLUMN IF NOT EXISTS plate_appearance_index INTEGER,
ADD COLUMN IF NOT EXISTS mlb_event_type TEXT,
ADD COLUMN IF NOT EXISTS event_type_description TEXT,
ADD COLUMN IF NOT EXISTS trajectory TEXT,
ADD COLUMN IF NOT EXISTS home_score_after INTEGER,
ADD COLUMN IF NOT EXISTS away_score_after INTEGER,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT now();

CREATE INDEX IF NOT EXISTS live_games_mlb_game_pk_idx ON core.live_games (mlb_game_pk);
CREATE INDEX IF NOT EXISTS live_games_snapshot_idx ON core.live_games (snapshot_id);
CREATE UNIQUE INDEX IF NOT EXISTS live_games_game_id_uidx ON core.live_games (game_id);
CREATE INDEX IF NOT EXISTS live_events_game_inning_idx ON core.live_events (game_id, inning, is_bottom_inning);
CREATE INDEX IF NOT EXISTS live_events_batter_idx ON core.live_events (batter_id);
CREATE INDEX IF NOT EXISTS live_events_pitcher_idx ON core.live_events (pitcher_id);
CREATE INDEX IF NOT EXISTS live_events_mlb_game_pk_idx ON core.live_events (mlb_game_pk);
CREATE INDEX IF NOT EXISTS live_events_snapshot_idx ON core.live_events (snapshot_id);
CREATE UNIQUE INDEX IF NOT EXISTS live_events_game_event_uidx ON core.live_events (game_id, event_id);

COMMENT ON TABLE core.live_games IS 'Live MLB game data transformed into core schema';
COMMENT ON TABLE core.live_events IS 'Live MLB play-by-play data transformed into core schema';
