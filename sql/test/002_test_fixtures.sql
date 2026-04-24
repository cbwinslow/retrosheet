-- File: sql/test/002_test_fixtures.sql
-- Purpose: Create minimal test data for E2E validation
-- Author: Agent Cascade
-- Date: 2026-04-24

-- Create test game data (subset of real data)
CREATE TABLE test.sample_games AS
SELECT * FROM core.games
WHERE game_date >= '2024-01-01'
LIMIT 100;

-- Create test events data
CREATE TABLE test.sample_events AS
SELECT e.*
FROM core.events AS e
INNER JOIN test.sample_games AS g ON e.game_id = g.game_id;

-- Add comments
COMMENT ON TABLE test.sample_games IS 'Test fixture: 100 games from 2024';
COMMENT ON TABLE test.sample_events IS 'Test fixture: Events for sample games';

-- Log what we created
SELECT
    'test.sample_games' AS table_name,
    COUNT(*) AS row_count
FROM test.sample_games
UNION ALL
SELECT
    'test.sample_events' AS table_name,
    COUNT(*) AS row_count
FROM test.sample_events;
