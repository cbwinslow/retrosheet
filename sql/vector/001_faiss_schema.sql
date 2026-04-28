--
— File: sql/vector/001_faiss_schema.sql
— Purpose: Schema for storing vector embeddings using pgvector extension
— Author: Agent KiloSwift
— Date: 2026-04-27
— Usage: psql -f sql/vector/001_faiss_schema.sql
— Dependencies: pgvector extension must be installed (sql/maintenance/005_install_pgvector.sql)
— Notes: Provides persistent storage for player/pitch embeddings compatible with faiss-cpu
—

-- Create dedicated schema for vector storage
CREATE SCHEMA IF NOT EXISTS embeddings;

-- Table: player_embeddings
-- Stores vector embeddings for players (batters and pitchers)
-- Compatible with faiss-cpu for in-memory indexing
CREATE TABLE IF NOT EXISTS embeddings.player_embeddings (
    player_id TEXT NOT NULL,
    player_type TEXT NOT NULL CHECK (player_type IN ('batter', 'pitcher')),
    season INTEGER NOT NULL,
    embedding vector(128),  -- 128-dimensional normalized embedding
    embedding_source TEXT, -- 'faiss', 'pca', 'manual'
    model_version TEXT,    -- Version of feature set used
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    PRIMARY KEY (player_id, player_type, season)
);

-- Index for similarity search (HNSW for approximate nearest neighbor)
CREATE INDEX IF NOT EXISTS idx_player_embeddings_embedding
    ON embeddings.player_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);  -- Adjust based on row count

-- Alternative: HNSW index for higher recall (requires pgvector >= 0.5)
-- CREATE INDEX idx_player_embeddings_hnsw
--    ON embeddings.player_embeddings
--    USING hnsw (embedding vector_cosine_ops);

-- Table: pitch_embeddings
-- Stores vector embeddings for pitch sequences or individual pitches
CREATE TABLE IF NOT EXISTS embeddings.pitch_embeddings (
    pitch_id BIGSERIAL PRIMARY KEY,
    game_pk BIGINT,
    pitcher_id INTEGER,
    batter_id INTEGER,
    pitch_number INTEGER,
    pitch_sequence TEXT,  -- Encoded pitch sequence (e.g., "FF-SL-CH")
    embedding vector(128),
    embedding_model TEXT, -- Architecture used (LSTM, Transformer, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Index for pitch similarity search
CREATE INDEX IF NOT EXISTS idx_pitch_embeddings_pitcher
    ON embeddings.pitch_embeddings (pitcher_id);

CREATE INDEX IF NOT EXISTS idx_pitch_embeddings_embedding
    ON embeddings.pitch_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 1000);

-- Table: team_embeddings
-- Stores team performance embeddings
CREATE TABLE IF NOT EXISTS embeddings.team_embeddings (
    team_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    embedding vector(64),  -- Smaller dimension for teams
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    PRIMARY KEY (team_id, season)
);

-- Comments
COMMENT ON TABLE embeddings.player_embeddings IS 'Player similarity embeddings computed from performance features. Used with FAISS for fast nearest-neighbor search.';
COMMENT ON COLUMN embeddings.player_embeddings.player_id IS 'Canonical player ID (matches bridge.player_xref)';
COMMENT ON COLUMN embeddings.player_embeddings.player_type IS 'Either batter or pitcher - embeddings are type-specific';
COMMENT ON COLUMN embeddings.player_embeddings.embedding IS '128-dimensional normalized vector (L2 norm = 1). Use <=> operator for cosine similarity';
COMMENT ON COLUMN embeddings.player_embeddings.embedding_source IS 'Source system: faiss, pca, manual (indicates how vector was generated)';

-- Upsert function for batch loading
CREATE OR REPLACE FUNCTION embeddings.upsert_player_embedding(
    p_player_id TEXT,
    p_player_type TEXT,
    p_season INTEGER,
    p_embedding vector(128),
    p_model_version TEXT DEFAULT 'v1.0'
) RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO embeddings.player_embeddings
        (player_id, player_type, season, embedding, model_version, updated_at)
    VALUES
        (p_player_id, p_player_type, p_season, p_embedding, p_model_version, now())
    ON CONFLICT (player_id, player_type, season)
    DO UPDATE SET
        embedding = EXCLUDED.embedding,
        model_version = EXCLUDED.model_version,
        updated_at = EXCLUDED.updated_at;
END;
$$;

COMMENT ON FUNCTION embeddings.upsert_player_embedding IS 'Upsert a single player embedding. Called by batch loaders and real-time inference.';

-- Batch upsert from staging table (for bulk loading)
CREATE OR REPLACE FUNCTION embeddings.bulk_upsert_from_staging()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    WITH merged AS (
        INSERT INTO embeddings.player_embeddings AS target
        SELECT
            s.player_id,
            s.player_type,
            s.season,
            s.embedding,
            s.model_version,
            now() as created_at,
            now() as updated_at
        FROM embeddings.player_embeddings_staging s
        ON CONFLICT (player_id, player_type, season)
        DO UPDATE SET
            embedding = EXCLUDED.embedding,
            model_version = EXCLUDED.model_version,
            updated_at = EXCLUDED.updated_at
        RETURNING 1
    )
    SELECT COUNT(*) INTO v_count FROM merged;

    -- Clear staging table
    TRUNCATE embeddings.player_embeddings_staging;

    RETURN v_count;
END;
$$;

COMMENT ON FUNCTION embeddings.bulk_upsert_from_staging IS 'Bulk upsert from staging table. Returns number of rows inserted/updated. Called by ETL pipelines.';

-- Similarity search function
CREATE OR REPLACE FUNCTION embeddings.find_similar_players(
    p_player_id TEXT,
    p_player_type TEXT,
    p_season INTEGER,
    p_limit INTEGER DEFAULT 10,
    p_min_similarity REAL DEFAULT 0.5
)
RETURNS TABLE (
    similar_player_id TEXT,
    similarity REAL,
    player_type TEXT,
    season INTEGER
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        pe.player_id AS similar_player_id,
        1 - (pe.embedding <=> q.embedding) AS similarity,
        pe.player_type,
        pe.season
    FROM
        embeddings.player_embeddings pe,
        (SELECT embedding FROM embeddings.player_embeddings
         WHERE player_id = p_player_id AND player_type = p_player_type AND season = p_season) q
    WHERE
        pe.player_id != p_player_id
        AND pe.player_type = p_player_type
        AND 1 - (pe.embedding <=> q.embedding) >= p_min_similarity
    ORDER BY
        pe.embedding <=> q.embedding  -- Order by distance (ascending = similar)
    LIMIT p_limit;
$$;

COMMENT ON FUNCTION embeddings.find_similar_players IS 'Find similar players using cosine similarity on embeddings. Returns players with similarity >= min_similarity, ordered by most similar.';

-- Stats function
CREATE OR REPLACE FUNCTION embeddings.get_embedding_stats(p_season INTEGER DEFAULT NULL)
RETURNS TABLE (
    player_type TEXT,
    total_embeddings BIGINT,
    avg_embedding_norm REAL,
    min_season INTEGER,
    max_season INTEGER
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        player_type,
        COUNT(*) AS total_embeddings,
        AVG(embedding <-> ARRAY[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]::vector) AS avg_norm,
        MIN(season) AS min_season,
        MAX(season) AS max_season
    FROM
        embeddings.player_embeddings
    WHERE
        p_season IS NULL OR season = p_season
    GROUP BY player_type;
$$;

-- Note: pgvector provides the <=> (L2 distance), <-> (cosine distance), <#> (inner product) operators
-- For normalized vectors, cosine distance = 1 - cosine_similarity
