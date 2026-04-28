/*
File: sql/10_raw/1020_raw_mlb_live_feed.sql
Purpose: Raw landing table for MLB Stats API live feed data
Author: Agent Cascade
Date: 2026-04-28
Depends On: sql/10_raw/1001_raw_sportradar_schema.sql (schema pattern)
Called By: scripts/live_ingestion/mlb_live_feed.sh, baseball/sources/mlb.py

Table: raw_mlb.live_feed_snapshots
- Stores raw JSON responses from MLB Stats API
- Checksum-based deduplication to avoid storing identical snapshots
- Indexed for efficient querying by game and timestamp
- Supports live game state tracking and replay

Notes:
- JSONB payload preserves complete API response
- request_url captures exact endpoint for reproducibility
- status_code tracks API availability
- response_time_ms helps monitor API performance
- Use v_live_feed_dedup view to get only unique snapshots
*/

-- Create raw_mlb schema if not exists
CREATE SCHEMA IF NOT EXISTS raw_mlb;

-- Live feed snapshots table for MLB Stats API
CREATE TABLE IF NOT EXISTS raw_mlb.live_feed_snapshots (
    snapshot_id bigserial PRIMARY KEY,
    
    -- Game identification
    game_pk integer NOT NULL,
    game_date date,
    season integer,
    
    -- Request metadata
    request_url text NOT NULL,
    request_timestamp timestamptz NOT NULL DEFAULT NOW(),
    request_type varchar(50) DEFAULT 'live_feed',  -- 'live_feed', 'schedule', 'boxscore', etc.
    
    -- Response metadata
    status_code integer NOT NULL,
    response_time_ms integer,              -- API latency measurement
    response_hash varchar(64) NOT NULL,   -- SHA-256 hash for deduplication
    
    -- Raw payload
    payload_json jsonb NOT NULL,
    payload_size_bytes integer,             -- For monitoring data volume
    
    -- Ingestion metadata
    fetched_by varchar(100) DEFAULT current_user,
    ingest_run_id bigint REFERENCES raw_retrosheet.ingest_runs(ingest_run_id),
    
    -- Deduplication: prevent storing identical snapshots
    UNIQUE(game_pk, response_hash),
    
    -- Indexing strategy
    CONSTRAINT valid_status_code CHECK (status_code BETWEEN 100 AND 599)
);

COMMENT ON TABLE raw_mlb.live_feed_snapshots IS 
    'Raw MLB Stats API live feed responses with checksum-based deduplication';

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_live_feed_game_pk ON raw_mlb.live_feed_snapshots(game_pk);
CREATE INDEX IF NOT EXISTS idx_live_feed_timestamp ON raw_mlb.live_feed_snapshots(request_timestamp);
CREATE INDEX IF NOT EXISTS idx_live_feed_season ON raw_mlb.live_feed_snapshots(season);
CREATE INDEX IF NOT EXISTS idx_live_feed_type ON raw_mlb.live_feed_snapshots(request_type);
CREATE INDEX IF NOT EXISTS idx_live_feed_status ON raw_mlb.live_feed_snapshots(status_code) WHERE status_code != 200;

-- Partial index for latest snapshot per game (for efficient "current state" queries)
CREATE INDEX IF NOT EXISTS idx_live_feed_latest 
    ON raw_mlb.live_feed_snapshots(game_pk, request_timestamp DESC);

-- View to get deduplicated feed with deduplication statistics
CREATE OR REPLACE VIEW raw_mlb.v_live_feed_dedup AS
SELECT 
    game_pk,
    game_date,
    season,
    request_type,
    request_timestamp,
    status_code,
    response_time_ms,
    payload_json,
    response_hash,
    snapshot_id,
    fetched_by
FROM raw_mlb.live_feed_snapshots
WHERE status_code = 200  -- Only successful responses
ORDER BY game_pk, request_timestamp DESC;

COMMENT ON VIEW raw_mlb.v_live_feed_dedup IS 
    'Deduplicated live feed view showing only unique snapshots with latest first';

-- Function to insert live feed snapshot with automatic deduplication
CREATE OR REPLACE FUNCTION raw_mlb.upsert_live_feed_snapshot(
    p_game_pk integer,
    p_game_date date,
    p_season integer,
    p_request_url text,
    p_status_code integer,
    p_response_time_ms integer,
    p_payload_json jsonb,
    p_request_type varchar(50) DEFAULT 'live_feed'
)
RETURNS bigint AS $$
DECLARE
    v_hash varchar(64);
    v_snapshot_id bigint;
    v_payload_size integer;
BEGIN
    -- Calculate hash for deduplication
    v_hash := encode(digest(p_payload_json::text, 'sha256'), 'hex');
    v_payload_size := octet_length(p_payload_json::text);
    
    -- Insert with conflict handling (deduplication)
    INSERT INTO raw_mlb.live_feed_snapshots (
        game_pk,
        game_date,
        season,
        request_url,
        request_timestamp,
        request_type,
        status_code,
        response_time_ms,
        response_hash,
        payload_json,
        payload_size_bytes
    ) VALUES (
        p_game_pk,
        p_game_date,
        p_season,
        p_request_url,
        NOW(),
        p_request_type,
        p_status_code,
        p_response_time_ms,
        v_hash,
        p_payload_json,
        v_payload_size
    )
    ON CONFLICT (game_pk, response_hash) DO UPDATE SET
        request_timestamp = EXCLUDED.request_timestamp,
        fetched_by = EXCLUDED.fetched_by
    RETURNING snapshot_id INTO v_snapshot_id;
    
    RETURN v_snapshot_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION raw_mlb.upsert_live_feed_snapshot IS 
    'Insert or update live feed snapshot with automatic SHA-256 deduplication';

-- View for snapshot frequency analysis
CREATE OR REPLACE VIEW raw_mlb.v_snapshot_frequency AS
SELECT
    game_pk,
    season,
    game_date,
    COUNT(*) as total_snapshots,
    COUNT(DISTINCT response_hash) as unique_snapshots,
    MIN(request_timestamp) as first_snapshot,
    MAX(request_timestamp) as last_snapshot,
    ROUND(AVG(response_time_ms), 2) as avg_response_time_ms
FROM raw_mlb.live_feed_snapshots
WHERE status_code = 200
GROUP BY game_pk, season, game_date
ORDER BY game_date DESC, game_pk;

COMMENT ON VIEW raw_mlb.v_snapshot_frequency IS 
    'Analysis of snapshot frequency per game - useful for understanding data volume';
