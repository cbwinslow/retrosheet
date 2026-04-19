-- Coach and Umpire Bridge Tables
-- Cross-reference tables for coaches and umpires across data sources
-- Related to GitHub Issue #43

-- Drop existing tables if they exist (for clean migration)
DROP TABLE IF EXISTS bridge.coach_xref CASCADE;
DROP TABLE IF EXISTS bridge.umpire_xref CASCADE;

-- Coach cross-reference table
CREATE TABLE IF NOT EXISTS bridge.coach_xref (
    retrosheet_coach_id TEXT,
    mlb_coach_id TEXT,
    lahman_coach_id TEXT,
    espn_coach_id TEXT,
    source_system TEXT NOT NULL, -- 'retrosheet', 'mlb', 'lahman', 'espn'
    coach_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Uniqueness constraints
    CONSTRAINT uk_coach_xref_retrosheet UNIQUE (retrosheet_coach_id),
    CONSTRAINT uk_coach_xref_mlb UNIQUE (mlb_coach_id),
    CONSTRAINT uk_coach_xref_lahman UNIQUE (lahman_coach_id),
    CONSTRAINT uk_coach_xref_espn UNIQUE (espn_coach_id)
);

-- Indexes for coach_xref
CREATE INDEX IF NOT EXISTS idx_coach_xref_retrosheet ON bridge.coach_xref(retrosheet_coach_id);
CREATE INDEX IF NOT EXISTS idx_coach_xref_mlb ON bridge.coach_xref(mlb_coach_id);
CREATE INDEX IF NOT EXISTS idx_coach_xref_lahman ON bridge.coach_xref(lahman_coach_id);
CREATE INDEX IF NOT EXISTS idx_coach_xref_espn ON bridge.coach_xref(espn_coach_id);
CREATE INDEX IF NOT EXISTS idx_coach_xref_source ON bridge.coach_xref(source_system);
CREATE INDEX IF NOT EXISTS idx_coach_xref_name ON bridge.coach_xref(coach_name);

-- Umpire cross-reference table
CREATE TABLE IF NOT EXISTS bridge.umpire_xref (
    retrosheet_umpire_id TEXT,
    mlb_umpire_id TEXT,
    lahman_umpire_id TEXT,
    espn_umpire_id TEXT,
    source_system TEXT NOT NULL, -- 'retrosheet', 'mlb', 'lahman', 'espn'
    umpire_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Uniqueness constraints
    CONSTRAINT uk_umpire_xref_retrosheet UNIQUE (retrosheet_umpire_id),
    CONSTRAINT uk_umpire_xref_mlb UNIQUE (mlb_umpire_id),
    CONSTRAINT uk_umpire_xref_lahman UNIQUE (lahman_umpire_id),
    CONSTRAINT uk_umpire_xref_espn UNIQUE (espn_umpire_id)
);

-- Indexes for umpire_xref
CREATE INDEX IF NOT EXISTS idx_umpire_xref_retrosheet ON bridge.umpire_xref(retrosheet_umpire_id);
CREATE INDEX IF NOT EXISTS idx_umpire_xref_mlb ON bridge.umpire_xref(mlb_umpire_id);
CREATE INDEX IF NOT EXISTS idx_umpire_xref_lahman ON bridge.umpire_xref(lahman_umpire_id);
CREATE INDEX IF NOT EXISTS idx_umpire_xref_espn ON bridge.umpire_xref(espn_umpire_id);
CREATE INDEX IF NOT EXISTS idx_umpire_xref_source ON bridge.umpire_xref(source_system);
CREATE INDEX IF NOT EXISTS idx_umpire_xref_name ON bridge.umpire_xref(umpire_name);

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION bridge.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_coach_xref_updated_at ON bridge.coach_xref;
CREATE TRIGGER update_coach_xref_updated_at
    BEFORE UPDATE ON bridge.coach_xref
    FOR EACH ROW
    EXECUTE FUNCTION bridge.update_updated_at_column();

DROP TRIGGER IF EXISTS update_umpire_xref_updated_at ON bridge.umpire_xref;
CREATE TRIGGER update_umpire_xref_updated_at
    BEFORE UPDATE ON bridge.umpire_xref
    FOR EACH ROW
    EXECUTE FUNCTION bridge.update_updated_at_column();

-- Comments
COMMENT ON TABLE bridge.coach_xref IS 'Cross-reference table for coaches across Retrosheet, MLB, Lahman, and ESPN data sources';
COMMENT ON TABLE bridge.umpire_xref IS 'Cross-reference table for umpires across Retrosheet, MLB, Lahman, and ESPN data sources';
