-- Knowledge Base Vector Schema for RAG
-- Creates schema, tables, and indexes for storing document chunks with pgvector embeddings
-- Depends on: pgvector extension (see 005_install_pgvector.sql)
-- Run after: pgvector is installed and verified

-- Create KB schema
CREATE SCHEMA IF NOT EXISTS kb;

-- Document chunks table with vector embeddings
CREATE TABLE IF NOT EXISTS kb.document_chunks (
    id BIGSERIAL PRIMARY KEY,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI text-embedding-3-small dimensions
    metadata JSONB DEFAULT '{}',
    source_url TEXT,
    source_title TEXT,
    source_type TEXT,  -- paper | article | book | reference
    topic TEXT,        -- fundamentals | hitting_metrics | pitching_metrics | etc.
    chunk_index INTEGER,
    total_chunks INTEGER,
    source_file TEXT,
    date_ingested TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Comments for documentation
COMMENT ON TABLE kb.document_chunks IS 'Chunked sabermetrics source documents with vector embeddings for RAG retrieval';
COMMENT ON COLUMN kb.document_chunks.embedding IS 'Vector embedding for semantic similarity search (1536-dim for OpenAI text-embedding-3-small)';
COMMENT ON COLUMN kb.document_chunks.metadata IS 'JSONB metadata including source info, chunk position, topic';
COMMENT ON COLUMN kb.document_chunks.topic IS 'Categorized topic for filtered retrieval: fundamentals, hitting_metrics, pitching_metrics, fielding_metrics, advanced_metrics, statcast, park_factors, modeling, steroid_era, strategy, injury, retrosheet';

-- Vector similarity index using ivfflat
-- ivfflat is good for <1M vectors; hnsw for >1M or higher recall requirements
CREATE INDEX IF NOT EXISTS idx_kb_chunks_embedding_ivfflat
ON kb.document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- B-tree indexes for filtering
CREATE INDEX IF NOT EXISTS idx_kb_chunks_topic ON kb.document_chunks (topic);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_source_type ON kb.document_chunks (source_type);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_source_title ON kb.document_chunks (source_title);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_date_ingested ON kb.document_chunks (date_ingested);

-- Composite index for common filtered queries
CREATE INDEX IF NOT EXISTS idx_kb_chunks_topic_source ON kb.document_chunks (topic, source_type);

-- GIN index on metadata for flexible JSONB queries
CREATE INDEX IF NOT EXISTS idx_kb_chunks_metadata_gin ON kb.document_chunks USING gin (metadata);

-- Ingestion tracking table
CREATE TABLE IF NOT EXISTS kb.ingestion_runs (
    id SERIAL PRIMARY KEY,
    run_name TEXT NOT NULL,
    source_count INTEGER,
    chunk_count INTEGER,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running',  -- running | completed | failed
    error_message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Validation: count chunks by topic
CREATE OR REPLACE VIEW kb.chunk_summary AS
SELECT
    topic,
    source_type,
    COUNT(*) AS chunk_count,
    MIN(created_at) AS first_chunk,
    MAX(created_at) AS last_chunk
FROM kb.document_chunks
GROUP BY topic, source_type
ORDER BY chunk_count DESC;

-- Validation: check for empty embeddings
CREATE OR REPLACE VIEW kb.empty_embeddings AS
SELECT
    id,
    source_title,
    chunk_index
FROM kb.document_chunks
WHERE embedding IS NULL;

-- Function: semantic search with topic filter
CREATE OR REPLACE FUNCTION kb.similar_chunks(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5,
    filter_topic TEXT DEFAULT NULL
)
RETURNS TABLE (
    id BIGINT,
    chunk_text TEXT,
    source_title TEXT,
    source_url TEXT,
    topic TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.chunk_text,
        dc.source_title,
        dc.source_url,
        dc.topic,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM kb.document_chunks dc
    WHERE dc.embedding IS NOT NULL
      AND 1 - (dc.embedding <=> query_embedding) > match_threshold
      AND (filter_topic IS NULL OR dc.topic = filter_topic)
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Function: keyword search fallback (for when embeddings aren't available)
CREATE OR REPLACE FUNCTION kb.keyword_search(
    query_text TEXT,
    match_count INT DEFAULT 5,
    filter_topic TEXT DEFAULT NULL
)
RETURNS TABLE (
    id BIGINT,
    chunk_text TEXT,
    source_title TEXT,
    source_url TEXT,
    topic TEXT,
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.chunk_text,
        dc.source_title,
        dc.source_url,
        dc.topic,
        ts_rank(dc.chunk_text::tsvector, plainto_tsquery('english', query_text)) AS rank
    FROM kb.document_chunks dc
    WHERE dc.chunk_text::tsvector @@ plainto_tsquery('english', query_text)
      AND (filter_topic IS NULL OR dc.topic = filter_topic)
    ORDER BY rank DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Example usage:
-- INSERT INTO kb.document_chunks (chunk_text, embedding, metadata, source_url, source_title, source_type, topic, chunk_index, total_chunks, source_file, date_ingested)
-- VALUES ('...', '[...]'::vector, '{"key": "value"}', 'https://...', 'Title', 'article', 'fundamentals', 0, 10, 'file.txt', NOW());
--
-- SELECT * FROM kb.similar_chunks('[...]'::vector, 0.7, 5, 'modeling');
-- SELECT * FROM kb.chunk_summary;
