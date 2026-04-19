-- Ingest Run Tracking Enhancement
-- Purpose: Add comprehensive run tracking for data ingestion scripts
-- Enables reproducibility, debugging, and audit trail for all data loads

-- Expand ingest_runs table with additional tracking fields
ALTER TABLE raw_retrosheet.ingest_runs
    ADD COLUMN IF NOT EXISTS script_name text,
    ADD COLUMN IF NOT EXISTS script_version text,
    ADD COLUMN IF NOT EXISTS git_commit text,
    ADD COLUMN IF NOT EXISTS command_args jsonb,
    ADD COLUMN IF NOT EXISTS records_downloaded int DEFAULT 0,
    ADD COLUMN IF NOT EXISTS records_ingested int DEFAULT 0,
    ADD COLUMN IF NOT EXISTS records_failed int DEFAULT 0,
    ADD COLUMN IF NOT EXISTS error_message text,
    ADD COLUMN IF NOT EXISTS user_name text DEFAULT current_user,
    ADD COLUMN IF NOT EXISTS hostname text DEFAULT inet_server_addr();

-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_ingest_runs_script_name ON raw_retrosheet.ingest_runs(script_name);
CREATE INDEX IF NOT EXISTS idx_ingest_runs_status ON raw_retrosheet.ingest_runs(status);
CREATE INDEX IF NOT EXISTS idx_ingest_runs_started_at ON raw_retrosheet.ingest_runs(started_at DESC);

-- ============================================
-- Helper Functions for Run Logging
-- ============================================

-- Start a new ingest run
CREATE OR REPLACE FUNCTION raw_retrosheet.start_ingest_run(
    p_source_name text,
    p_source_version text DEFAULT NULL,
    p_script_name text DEFAULT NULL,
    p_script_version text DEFAULT NULL,
    p_git_commit text DEFAULT NULL,
    p_command_args jsonb DEFAULT '{}'::jsonb
)
RETURNS bigint AS $$
DECLARE
    v_run_id bigint;
BEGIN
    INSERT INTO raw_retrosheet.ingest_runs (
        source_name,
        source_version,
        script_name,
        script_version,
        git_commit,
        command_args,
        status,
        started_at,
        details
    ) VALUES (
        p_source_name,
        p_source_version,
        p_script_name,
        p_script_version,
        p_git_commit,
        p_command_args,
        'running',
        now(),
        jsonb_build_object(
            'started_by', current_user,
            'hostname', inet_server_addr()
        )
    ) RETURNING ingest_run_id INTO v_run_id;
    
    RETURN v_run_id;
END;
$$ LANGUAGE plpgsql;

-- Update run progress (records downloaded/ingested/failed)
CREATE OR REPLACE FUNCTION raw_retrosheet.update_ingest_run_progress(
    p_run_id bigint,
    p_records_downloaded int DEFAULT NULL,
    p_records_ingested int DEFAULT NULL,
    p_records_failed int DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    UPDATE raw_retrosheet.ingest_runs
    SET 
        records_downloaded = COALESCE(p_records_downloaded, records_downloaded),
        records_ingested = COALESCE(p_records_ingested, records_ingested),
        records_failed = COALESCE(p_records_failed, records_failed)
    WHERE ingest_run_id = p_run_id;
END;
$$ LANGUAGE plpgsql;

-- Complete a run successfully
CREATE OR REPLACE FUNCTION raw_retrosheet.complete_ingest_run(
    p_run_id bigint,
    p_final_details jsonb DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    UPDATE raw_retrosheet.ingest_runs
    SET 
        status = 'completed',
        finished_at = now(),
        details = CASE 
            WHEN p_final_details IS NOT NULL THEN details || p_final_details
            ELSE details
        END
    WHERE ingest_run_id = p_run_id;
END;
$$ LANGUAGE plpgsql;

-- Fail a run with error message
CREATE OR REPLACE FUNCTION raw_retrosheet.fail_ingest_run(
    p_run_id bigint,
    p_error_message text,
    p_error_details jsonb DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    UPDATE raw_retrosheet.ingest_runs
    SET 
        status = 'failed',
        finished_at = now(),
        error_message = p_error_message,
        details = CASE 
            WHEN p_error_details IS NOT NULL THEN details || p_error_details
            ELSE details
        END
    WHERE ingest_run_id = p_run_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Utility Functions
-- ============================================

-- Get git commit hash from system (requires git command available)
CREATE OR REPLACE FUNCTION raw_retrosheet.get_git_commit()
RETURNS text AS $$
BEGIN
    -- This requires the script to be run from within a git repository
    -- If not available, returns NULL
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Compute SHA256 checksum for deduplication
CREATE OR REPLACE FUNCTION raw_retrosheet.compute_checksum(p_data jsonb)
RETURNS text AS $$
BEGIN
    RETURN encode(digest(p_data::text, 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Triggers for Auto-Timestamp Updates
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION raw_retrosheet.update_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to bridge tables
CREATE TRIGGER bridge_player_xref_updated_at
    BEFORE UPDATE ON bridge.player_xref
    FOR EACH ROW EXECUTE FUNCTION raw_retrosheet.update_updated_at();

CREATE TRIGGER bridge_team_xref_updated_at
    BEFORE UPDATE ON bridge.team_xref
    FOR EACH ROW EXECUTE FUNCTION raw_retrosheet.update_updated_at();

CREATE TRIGGER bridge_park_xref_updated_at
    BEFORE UPDATE ON bridge.park_xref
    FOR EACH ROW EXECUTE FUNCTION raw_retrosheet.update_updated_at();

CREATE TRIGGER bridge_game_xref_updated_at
    BEFORE UPDATE ON bridge.game_xref
    FOR EACH ROW EXECUTE FUNCTION raw_retrosheet.update_updated_at();

-- ============================================
-- Views for Run Monitoring
-- ============================================

-- Recent ingest runs summary
CREATE OR REPLACE VIEW raw_retrosheet.recent_ingest_runs AS
SELECT 
    ingest_run_id,
    source_name,
    script_name,
    status,
    started_at,
    finished_at,
    EXTRACT(EPOCH FROM (COALESCE(finished_at, now()) - started_at)) AS duration_seconds,
    records_downloaded,
    records_ingested,
    records_failed,
    error_message
FROM raw_retrosheet.ingest_runs
ORDER BY started_at DESC
LIMIT 100;

-- Run statistics by script
CREATE OR REPLACE VIEW raw_retrosheet.ingest_run_stats_by_script AS
SELECT 
    script_name,
    COUNT(*) AS total_runs,
    COUNT(*) FILTER (WHERE status = 'completed') AS successful_runs,
    COUNT(*) FILTER (WHERE status = 'failed') AS failed_runs,
    SUM(records_downloaded) AS total_records_downloaded,
    SUM(records_ingested) AS total_records_ingested,
    AVG(EXTRACT(EPOCH FROM (COALESCE(finished_at, now()) - started_at))) FILTER (WHERE finished_at IS NOT NULL) AS avg_duration_seconds
FROM raw_retrosheet.ingest_runs
WHERE script_name IS NOT NULL
GROUP BY script_name
ORDER BY total_runs DESC;

-- Comments
COMMENT ON TABLE raw_retrosheet.ingest_runs IS 'Tracks all data ingestion runs with script metadata, progress, and error tracking';
COMMENT ON FUNCTION raw_retrosheet.start_ingest_run IS 'Start a new ingest run and return run_id';
COMMENT ON FUNCTION raw_retrosheet.update_ingest_run_progress IS 'Update progress counters for an ingest run';
COMMENT ON FUNCTION raw_retrosheet.complete_ingest_run IS 'Mark an ingest run as completed';
COMMENT ON FUNCTION raw_retrosheet.fail_ingest_run IS 'Mark an ingest run as failed with error message';
COMMENT ON FUNCTION raw_retrosheet.compute_checksum IS 'Compute SHA256 checksum for JSON data';
COMMENT ON VIEW raw_retrosheet.recent_ingest_runs IS 'Summary of recent 100 ingest runs';
COMMENT ON VIEW raw_retrosheet.ingest_run_stats_by_script IS 'Statistics grouped by script name';
