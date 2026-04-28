/*
File: sql/20_staging/2002_staging_checkpoints.sql
Purpose: Checkpoint table for source adapter resume capability
Author: Agent Cascade
Date: 2026-04-28
Depends On: sql/20_staging/2000_staging_schema.sql
Called By: scripts/staging/initialize_staging.sh, baseball.sources module

Tables:
- staging.source_checkpoints: Tracks granular progress for resumable downloads

Notes:
- Checkpoint key format: {source_type}/{season}/{entity_type}
- Position tracking for partial file downloads
- status: 'pending' | 'in_progress' | 'completed' | 'failed'
- last_attempt tracks retry history
- Metadata stores JSON with detailed position info (offset, chunks, etc.)
*/

-- Checkpoint table for granular download progress tracking
CREATE TABLE IF NOT EXISTS staging.source_checkpoints (
    checkpoint_id bigserial PRIMARY KEY,
    
    -- Identification
    source_type varchar(50) NOT NULL,      -- 'retrosheet', 'mlb', 'statcast', etc.
    season integer,                          -- Year/season identifier
    entity_type varchar(50) NOT NULL,      -- 'events', 'games', 'rosters', 'schedule'
    entity_key varchar(255) NOT NULL,      -- Specific file/URL/key
    
    -- Status
    status varchar(20) NOT NULL DEFAULT 'pending',  -- pending/in_progress/completed/failed
    
    -- Progress tracking
    file_path text,                        -- Local path if downloaded
    file_size_bytes bigint,                -- Total expected size
    bytes_processed bigint DEFAULT 0,      -- For partial resume
    records_total integer,                   -- Expected record count
    records_processed integer DEFAULT 0,     -- Records successfully handled
    
    -- Attempt tracking
    attempt_count integer DEFAULT 0,
    first_attempt_at timestamptz,
    last_attempt_at timestamptz,
    completed_at timestamptz,
    
    -- Error tracking
    last_error text,
    last_error_code varchar(50),
    
    -- Metadata for resumption
    metadata jsonb DEFAULT '{}'::jsonb,      -- Source-specific checkpoint data
    
    -- Foreign key to ingest run for lineage
    ingest_run_id bigint REFERENCES raw_retrosheet.ingest_runs(ingest_run_id),
    
    -- Timestamps
    created_at timestamptz NOT NULL DEFAULT NOW(),
    updated_at timestamptz NOT NULL DEFAULT NOW(),
    
    -- Unique constraint: one checkpoint per source/season/entity
    UNIQUE(source_type, season, entity_type, entity_key)
);

COMMENT ON TABLE staging.source_checkpoints IS 
    'Granular checkpoint tracking for resumable source adapter downloads';

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_checkpoints_source ON staging.source_checkpoints(source_type, status);
CREATE INDEX IF NOT EXISTS idx_checkpoints_season ON staging.source_checkpoints(season, status);
CREATE INDEX IF NOT EXISTS idx_checkpoints_status ON staging.source_checkpoints(status, updated_at);
CREATE INDEX IF NOT EXISTS idx_checkpoints_run ON staging.source_checkpoints(ingest_run_id);

-- Function to update checkpoint timestamp
CREATE OR REPLACE FUNCTION staging.update_checkpoint_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_update_checkpoint_timestamp
    BEFORE UPDATE ON staging.source_checkpoints
    FOR EACH ROW
    EXECUTE FUNCTION staging.update_checkpoint_timestamp();

-- Function to get resumable work for a source
CREATE OR REPLACE FUNCTION staging.get_resumable_checkpoints(
    p_source_type varchar(50),
    p_season integer,
    p_entity_type varchar(50) DEFAULT NULL
)
RETURNS TABLE(
    entity_key varchar,
    status varchar,
    bytes_processed bigint,
    records_processed integer,
    metadata jsonb,
    attempt_count integer
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sc.entity_key,
        sc.status,
        sc.bytes_processed,
        sc.records_processed,
        sc.metadata,
        sc.attempt_count
    FROM staging.source_checkpoints sc
    WHERE sc.source_type = p_source_type
      AND sc.season = p_season
      AND (p_entity_type IS NULL OR sc.entity_type = p_entity_type)
      AND sc.status IN ('pending', 'in_progress', 'failed')
    ORDER BY sc.entity_key;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION staging.get_resumable_checkpoints IS 
    'Returns incomplete checkpoints for resuming a download operation';

-- Function to mark checkpoint started
CREATE OR REPLACE FUNCTION staging.start_checkpoint(
    p_source_type varchar(50),
    p_season integer,
    p_entity_type varchar(50),
    p_entity_key varchar,
    p_ingest_run_id bigint,
    p_metadata jsonb DEFAULT '{}'::jsonb
)
RETURNS bigint AS $$
DECLARE
    v_checkpoint_id bigint;
BEGIN
    INSERT INTO staging.source_checkpoints (
        source_type,
        season,
        entity_type,
        entity_key,
        ingest_run_id,
        status,
        metadata,
        attempt_count,
        first_attempt_at,
        last_attempt_at
    ) VALUES (
        p_source_type,
        p_season,
        p_entity_type,
        p_entity_key,
        p_ingest_run_id,
        'in_progress',
        p_metadata,
        1,
        NOW(),
        NOW()
    )
    ON CONFLICT (source_type, season, entity_type, entity_key) DO UPDATE SET
        status = 'in_progress',
        attempt_count = staging.source_checkpoints.attempt_count + 1,
        last_attempt_at = NOW(),
        last_error = NULL,
        metadata = COALESCE(EXCLUDED.metadata, staging.source_checkpoints.metadata)
    RETURNING checkpoint_id INTO v_checkpoint_id;
    
    RETURN v_checkpoint_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION staging.start_checkpoint IS 
    'Creates or updates a checkpoint when starting work on an entity';

-- Function to mark checkpoint complete
CREATE OR REPLACE FUNCTION staging.complete_checkpoint(
    p_checkpoint_id bigint,
    p_file_path text DEFAULT NULL,
    p_records_processed integer DEFAULT NULL,
    p_metadata jsonb DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    UPDATE staging.source_checkpoints
    SET status = 'completed',
        completed_at = NOW(),
        file_path = COALESCE(p_file_path, file_path),
        records_processed = COALESCE(p_records_processed, records_processed),
        metadata = COALESCE(p_metadata, metadata),
        updated_at = NOW()
    WHERE checkpoint_id = p_checkpoint_id;
END;
$$ LANGUAGE plpgsql;

-- Function to mark checkpoint failed
CREATE OR REPLACE FUNCTION staging.fail_checkpoint(
    p_checkpoint_id bigint,
    p_error_message text,
    p_error_code varchar(50) DEFAULT NULL,
    p_records_processed integer DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    UPDATE staging.source_checkpoints
    SET status = 'failed',
        last_error = p_error_message,
        last_error_code = p_error_code,
        records_processed = COALESCE(p_records_processed, records_processed),
        updated_at = NOW()
    WHERE checkpoint_id = p_checkpoint_id;
END;
$$ LANGUAGE plpgsql;

-- View for checkpoint summary
CREATE OR REPLACE VIEW staging.v_checkpoint_summary AS
SELECT
    source_type,
    season,
    entity_type,
    COUNT(*) as total_entities,
    COUNT(*) FILTER (WHERE status = 'completed') as completed,
    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
    COUNT(*) FILTER (WHERE status = 'pending') as pending,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    SUM(records_processed) as total_records_processed,
    MAX(completed_at) as last_completion
FROM staging.source_checkpoints
GROUP BY source_type, season, entity_type
ORDER BY source_type, season, entity_type;

COMMENT ON VIEW staging.v_checkpoint_summary IS 
    'Summary of checkpoint status across all source adapters';
