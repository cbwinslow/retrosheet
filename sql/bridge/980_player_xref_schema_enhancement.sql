-- File: sql/bridge/980_player_xref_schema_enhancement.sql
-- Purpose: Enhance player_xref with Baseball Reference IDs and indexes
-- Author: Agent Cascade
-- Date: 2026-04-24
ALTER TABLE bridge.player_xref
ADD COLUMN IF NOT EXISTS bbref_id TEXT;

-- Add FanGraphs ID column
ALTER TABLE bridge.player_xref
ADD COLUMN IF NOT EXISTS fangraphs_id INTEGER;

-- Add MLB debut year column
ALTER TABLE bridge.player_xref
ADD COLUMN IF NOT EXISTS mlb_played_first INTEGER;

-- Add birth year column
ALTER TABLE bridge.player_xref
ADD COLUMN IF NOT EXISTS birth_year INTEGER;

-- Add unique constraint for bbref_id
ALTER TABLE bridge.player_xref
ADD CONSTRAINT player_xref_bbref_id_unique UNIQUE (bbref_id);

-- Add unique constraint for fangraphs_id
ALTER TABLE bridge.player_xref
ADD CONSTRAINT player_xref_fangraphs_id_unique UNIQUE (fangraphs_id);

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS player_xref_bbref_id_idx ON bridge.player_xref (bbref_id);
CREATE INDEX IF NOT EXISTS player_xref_fangraphs_id_idx ON bridge.player_xref (fangraphs_id);

-- Add comments
COMMENT ON COLUMN bridge.player_xref.bbref_id IS 'Baseball Reference player ID from Chadwick Bureau Register';
COMMENT ON COLUMN bridge.player_xref.fangraphs_id IS 'FanGraphs player ID from Chadwick Bureau Register';
COMMENT ON COLUMN bridge.player_xref.mlb_played_first IS 'MLB debut year from Chadwick Bureau Register';
COMMENT ON COLUMN bridge.player_xref.birth_year IS 'Player birth year from Chadwick Bureau Register';

