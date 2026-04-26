-- File: sql/bridge/910_confidence_scoring.sql
-- Purpose: Add confidence scoring columns and views to all bridge mapping tables
-- Author: Agent Cascade
-- Date: 2026-04-24
ALTER TABLE bridge.player_xref
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3, 2) DEFAULT 0.8,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'chadwick_register';

-- Add confidence_score column to bridge.team_xref
ALTER TABLE bridge.team_xref
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3, 2) DEFAULT 0.8,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'chadwick_register';

-- Add confidence_score column to bridge.park_xref
ALTER TABLE bridge.park_xref
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3, 2) DEFAULT 0.8,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'chadwick_register';

-- Add confidence_score column to bridge.game_xref
ALTER TABLE bridge.game_xref
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3, 2) DEFAULT 0.8,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'automated_match';

-- Add confidence_score column to bridge.coach_xref
ALTER TABLE bridge.coach_xref
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3, 2) DEFAULT 0.3,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'retrosheet_id_only';

-- Add confidence_score column to bridge.umpire_xref
ALTER TABLE bridge.umpire_xref
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3, 2) DEFAULT 0.7,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'retrosheet_name_match';

-- Add confidence_score column to bridge.external_player_xref
ALTER TABLE bridge.external_player_xref
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3, 2) DEFAULT 0.8,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'id_cross_reference';

-- Add confidence_score column to bridge.external_team_xref
ALTER TABLE bridge.external_team_xref
ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3, 2) DEFAULT 0.8,
ADD COLUMN IF NOT EXISTS confidence_source TEXT DEFAULT 'id_cross_reference';

-- Add indexes for confidence-based queries
CREATE INDEX IF NOT EXISTS idx_player_xref_confidence ON bridge.player_xref (confidence_score);
CREATE INDEX IF NOT EXISTS idx_team_xref_confidence ON bridge.team_xref (confidence_score);
CREATE INDEX IF NOT EXISTS idx_park_xref_confidence ON bridge.park_xref (confidence_score);
CREATE INDEX IF NOT EXISTS idx_game_xref_confidence ON bridge.game_xref (confidence_score);
CREATE INDEX IF NOT EXISTS idx_coach_xref_confidence ON bridge.coach_xref (confidence_score);
CREATE INDEX IF NOT EXISTS idx_umpire_xref_confidence ON bridge.umpire_xref (confidence_score);
CREATE INDEX IF NOT EXISTS idx_external_player_xref_confidence ON bridge.external_player_xref (confidence_score);
CREATE INDEX IF NOT EXISTS idx_external_team_xref_confidence ON bridge.external_team_xref (confidence_score);

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
    'player_xref' AS table_name,
    confidence_score,
    COUNT(*) AS count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY 'player_xref'), 2) AS percentage
FROM bridge.player_xref
GROUP BY confidence_score
UNION ALL
SELECT
    'team_xref' AS table_name,
    confidence_score,
    COUNT(*) AS count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY 'team_xref'), 2) AS percentage
FROM bridge.team_xref
GROUP BY confidence_score
UNION ALL
SELECT
    'game_xref' AS table_name,
    confidence_score,
    COUNT(*) AS count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY 'game_xref'), 2) AS percentage
FROM bridge.game_xref
GROUP BY confidence_score
ORDER BY table_name ASC, confidence_score DESC;

COMMENT ON VIEW bridge.confidence_score_distribution IS 'Distribution of confidence scores across bridge tables';

-- View: Low-confidence mappings requiring review
CREATE OR REPLACE VIEW bridge.low_confidence_mappings AS
SELECT
    'player_xref' AS table_name,
    retrosheet_id AS entity_id,
    confidence_score,
    confidence_source,
    name_first,
    name_last
FROM bridge.player_xref
WHERE confidence_score < 0.7
UNION ALL
SELECT
    'team_xref' AS table_name,
    retrosheet_team_id AS entity_id,
    confidence_score,
    confidence_source,
    NULL AS name_first,
    name AS name_last
FROM bridge.team_xref
WHERE confidence_score < 0.7
UNION ALL
SELECT
    'game_xref' AS table_name,
    retrosheet_game_id AS entity_id,
    confidence_score,
    confidence_source,
    NULL AS name_first,
    NULL AS name_last
FROM bridge.game_xref
WHERE confidence_score < 0.7
ORDER BY confidence_score ASC, table_name ASC;

COMMENT ON VIEW bridge.low_confidence_mappings IS 'Mappings with confidence scores below 0.7 requiring manual review';

-- View: Confidence summary by source
CREATE OR REPLACE VIEW bridge.confidence_summary_by_source AS
SELECT
    table_name,
    confidence_source,
    COUNT(*) AS total_mappings,
    AVG(confidence_score) AS avg_confidence,
    MIN(confidence_score) AS min_confidence,
    MAX(confidence_score) AS max_confidence,
    COUNT(*) FILTER (WHERE confidence_score >= 0.9) AS high_confidence_count,
    COUNT(*) FILTER (WHERE confidence_score < 0.7) AS low_confidence_count
FROM (
    SELECT
        'player_xref' AS table_name,
        confidence_source,
        confidence_score
    FROM bridge.player_xref
    UNION ALL
    SELECT
        'team_xref' AS table_name,
        confidence_source,
        confidence_score
    FROM bridge.team_xref
    UNION ALL
    SELECT
        'game_xref' AS table_name,
        confidence_source,
        confidence_score
    FROM bridge.game_xref
) AS combined
GROUP BY table_name, confidence_source
ORDER BY table_name ASC, avg_confidence DESC;

COMMENT ON VIEW bridge.confidence_summary_by_source IS 'Summary statistics of confidence scores by table and source';
