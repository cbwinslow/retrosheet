-- Confidence Scoring Framework for Bridge Tables
-- Adds confidence scores to track mapping quality and reliability

-- Confidence Score Levels:
-- 1.0 - Direct mapping from authoritative source (Chadwick Register, MLB API)
-- 0.9 - High-confidence cross-reference (name + ID match)
-- 0.8 - Medium-confidence cross-reference (ID match only)
-- 0.7 - Low-confidence cross-reference (name match only)
-- 0.5 - Fuzzy match (similar names, approximate dates)
-- 0.3 - Placeholder or inferred mapping
-- 0.1 - Unverified or uncertain mapping

-- Add confidence_score column to bridge.player_xref
ALTER TABLE bridge.player_xref 
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3,2) DEFAULT 0.8,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'chadwick_register';

-- Add confidence_score column to bridge.team_xref
ALTER TABLE bridge.team_xref 
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3,2) DEFAULT 0.8,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'chadwick_register';

-- Add confidence_score column to bridge.park_xref
ALTER TABLE bridge.park_xref 
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3,2) DEFAULT 0.8,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'chadwick_register';

-- Add confidence_score column to bridge.game_xref
ALTER TABLE bridge.game_xref 
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3,2) DEFAULT 0.8,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'automated_match';

-- Add confidence_score column to bridge.coach_xref
ALTER TABLE bridge.coach_xref 
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3,2) DEFAULT 0.3,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'retrosheet_id_only';

-- Add confidence_score column to bridge.umpire_xref
ALTER TABLE bridge.umpire_xref 
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3,2) DEFAULT 0.7,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'retrosheet_name_match';

-- Add confidence_score column to bridge.external_player_xref
ALTER TABLE bridge.external_player_xref 
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3,2) DEFAULT 0.8,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'id_cross_reference';

-- Add confidence_score column to bridge.external_team_xref
ALTER TABLE bridge.external_team_xref 
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3,2) DEFAULT 0.8,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'id_cross_reference';

-- Add indexes for confidence-based queries
CREATE INDEX IF NOT EXISTS idx_player_xref_confidence ON bridge.player_xref(confidence_score);
CREATE INDEX IF NOT EXISTS idx_team_xref_confidence ON bridge.team_xref(confidence_score);
CREATE INDEX IF NOT EXISTS idx_park_xref_confidence ON bridge.park_xref(confidence_score);
CREATE INDEX IF NOT EXISTS idx_game_xref_confidence ON bridge.game_xref(confidence_score);
CREATE INDEX IF NOT EXISTS idx_coach_xref_confidence ON bridge.coach_xref(confidence_score);
CREATE INDEX IF NOT EXISTS idx_umpire_xref_confidence ON bridge.umpire_xref(confidence_score);
CREATE INDEX IF NOT EXISTS idx_external_player_xref_confidence ON bridge.external_player_xref(confidence_score);
CREATE INDEX IF NOT EXISTS idx_external_team_xref_confidence ON bridge.external_team_xref(confidence_score);

-- Add comments
COMMENT ON COLUMN bridge.player_xref.confidence_score IS 'Confidence score (0.0-1.0) for mapping quality';
COMMENT ON COLUMN bridge.player_xref.confidence_source IS 'Source of confidence assessment';
COMMENT ON COLUMN bridge.team_xref.confidence_score IS 'Confidence score (0.0-1.0) for mapping quality';
COMMENT ON COLUMN bridge.team_xref.confidence_source IS 'Source of confidence assessment';
COMMENT ON COLUMN bridge.park_xref.confidence_score IS 'Confidence score (0.0-1.0) for mapping quality';
COMMENT ON COLUMN bridge.park_xref.confidence_source IS 'Source of confidence assessment';
COMMENT ON COLUMN bridge.game_xref.confidence_score IS 'Confidence score (0.0-1.0) for mapping quality';
COMMENT ON COLUMN bridge.game_xref.confidence_source IS 'Source of confidence assessment';
COMMENT ON COLUMN bridge.coach_xref.confidence_score IS 'Confidence score (0.0-1.0) for mapping quality';
COMMENT ON COLUMN bridge.coach_xref.confidence_source IS 'Source of confidence assessment';
COMMENT ON COLUMN bridge.umpire_xref.confidence_score IS 'Confidence score (0.0-1.0) for mapping quality';
COMMENT ON COLUMN bridge.umpire_xref.confidence_source IS 'Source of confidence assessment';
COMMENT ON COLUMN bridge.external_player_xref.confidence_score IS 'Confidence score (0.0-1.0) for mapping quality';
COMMENT ON COLUMN bridge.external_player_xref.confidence_source IS 'Source of confidence assessment';
COMMENT ON COLUMN bridge.external_team_xref.confidence_score IS 'Confidence score (0.0-1.0) for mapping quality';
COMMENT ON COLUMN bridge.external_team_xref.confidence_source IS 'Source of confidence assessment';

-- View: Confidence score distribution
CREATE OR REPLACE VIEW bridge.confidence_score_distribution AS
SELECT 
    'player_xref' as table_name,
    confidence_score,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY 'player_xref'), 2) as percentage
FROM bridge.player_xref
GROUP BY confidence_score
UNION ALL
SELECT 
    'team_xref' as table_name,
    confidence_score,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY 'team_xref'), 2) as percentage
FROM bridge.team_xref
GROUP BY confidence_score
UNION ALL
SELECT 
    'game_xref' as table_name,
    confidence_score,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY 'game_xref'), 2) as percentage
FROM bridge.game_xref
GROUP BY confidence_score
ORDER BY table_name, confidence_score DESC;

COMMENT ON VIEW bridge.confidence_score_distribution IS 'Distribution of confidence scores across bridge tables';

-- View: Low-confidence mappings requiring review
CREATE OR REPLACE VIEW bridge.low_confidence_mappings AS
SELECT 
    'player_xref' as table_name,
    retrosheet_id as entity_id,
    confidence_score,
    confidence_source,
    name_first,
    name_last
FROM bridge.player_xref
WHERE confidence_score < 0.7
UNION ALL
SELECT 
    'team_xref' as table_name,
    retrosheet_team_id as entity_id,
    confidence_score,
    confidence_source,
    NULL as name_first,
    name as name_last
FROM bridge.team_xref
WHERE confidence_score < 0.7
UNION ALL
SELECT 
    'game_xref' as table_name,
    retrosheet_game_id as entity_id,
    confidence_score,
    confidence_source,
    NULL as name_first,
    NULL as name_last
FROM bridge.game_xref
WHERE confidence_score < 0.7
ORDER BY confidence_score ASC, table_name;

COMMENT ON VIEW bridge.low_confidence_mappings IS 'Mappings with confidence scores below 0.7 requiring manual review';

-- View: Confidence summary by source
CREATE OR REPLACE VIEW bridge.confidence_summary_by_source AS
SELECT 
    table_name,
    confidence_source,
    COUNT(*) as total_mappings,
    AVG(confidence_score) as avg_confidence,
    MIN(confidence_score) as min_confidence,
    MAX(confidence_score) as max_confidence,
    COUNT(*) FILTER (WHERE confidence_score >= 0.9) as high_confidence_count,
    COUNT(*) FILTER (WHERE confidence_score < 0.7) as low_confidence_count
FROM (
    SELECT 'player_xref' as table_name, confidence_source, confidence_score FROM bridge.player_xref
    UNION ALL
    SELECT 'team_xref' as table_name, confidence_source, confidence_score FROM bridge.team_xref
    UNION ALL
    SELECT 'game_xref' as table_name, confidence_source, confidence_score FROM bridge.game_xref
) combined
GROUP BY table_name, confidence_source
ORDER BY table_name, avg_confidence DESC;

COMMENT ON VIEW bridge.confidence_summary_by_source IS 'Summary statistics of confidence scores by table and source';
