-- File: sql/maintenance/005_install_pgvector.sql
-- Purpose: Install pgvector extension with similarity search test
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE EXTENSION IF NOT EXISTS vector;

-- Validate installation: Create test embedding table
CREATE TABLE IF NOT EXISTS test_embeddings (
    id SERIAL PRIMARY KEY,
    player_id TEXT,
    embedding VECTOR(3)
);

-- Insert test embeddings
INSERT INTO test_embeddings (player_id, embedding) VALUES
('player1', '[1,2,3]'::VECTOR),
('player2', '[1,2,4]'::VECTOR),
('player3', '[4,5,6]'::VECTOR);

-- Test similarity search
SELECT
    player_id,
    embedding <-> '[1,2,4]'::VECTOR AS distance
FROM test_embeddings
ORDER BY embedding <-> '[1,2,4]'::VECTOR
LIMIT 5;

-- Clean up test table (uncomment after validation)
-- DROP TABLE test_embeddings;

-- Verify extension is installed
SELECT
    extname,
    extversion
FROM pg_extension
WHERE extname = 'vector';

-- Table comments
COMMENT ON TABLE test_embeddings IS 'Test table for pgvector embedding storage';
