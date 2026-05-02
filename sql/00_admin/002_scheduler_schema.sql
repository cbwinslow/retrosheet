/*
File: sql/00_admin/002_scheduler_schema.sql
Purpose: Database-driven job scheduling with pg_cron
Author: Agent Cascade
Date: 2026-05-01
Depends On: 000_admin_pipeline_control.sql
Called By: bootstrap_system.py

Overview:
- Uses pg_cron extension for PostgreSQL-native job scheduling
- Config-driven via scheduler.jobs table
- Idempotent ingestion tracking via scheduler.job_runs
- Smart polling adapts to game schedule

Benefits:
- No system crontab modification (container-safe)
- All scheduling logic in database
- Track job history and performance
- Dynamic schedule adjustment
*/

-- Install pg_cron extension (requires PostgreSQL 12+ and admin privileges)
-- Note: This may fail if not superuser - bootstrap script handles gracefully
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS pg_cron;
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE 'pg_cron extension requires superuser. Skipping.';
    WHEN duplicate_object THEN
        -- Already exists, no action needed
        NULL;
END $$;

-- Scheduler schema
CREATE SCHEMA IF NOT EXISTS scheduler;

-- Job configuration table (truth source for scheduled jobs)
CREATE TABLE IF NOT EXISTS scheduler.jobs (
    job_id SERIAL PRIMARY KEY,
    job_name VARCHAR(100) UNIQUE NOT NULL,
    job_type VARCHAR(50) NOT NULL,  -- 'schedule_fetch', 'live_ingestion', 'odds_fetch', etc.
    
    -- Scheduling (cron syntax or 'smart' for dynamic)
    schedule VARCHAR(100) NOT NULL DEFAULT '0 * * * *',  -- cron expression
    schedule_type VARCHAR(20) NOT NULL DEFAULT 'cron',  -- 'cron', 'smart', 'interval'
    
    -- Command to execute
    command TEXT NOT NULL,  -- Shell command or SQL function
    command_type VARCHAR(20) NOT NULL DEFAULT 'shell',  -- 'shell', 'sql', 'python'
    
    -- Execution context
    working_dir VARCHAR(255),
    environment_vars JSONB,  -- env vars as JSON
    
    -- Smart scheduling (for game-aware polling)
    is_game_aware BOOLEAN DEFAULT FALSE,  -- Adjusts polling based on game schedule
    active_during_season_only BOOLEAN DEFAULT FALSE,
    
    -- Status and control
    is_enabled BOOLEAN DEFAULT TRUE,
    is_running BOOLEAN DEFAULT FALSE,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    
    -- Timeouts and limits
    timeout_seconds INTEGER DEFAULT 300,
    max_retries INTEGER DEFAULT 3,
    retry_delay_seconds INTEGER DEFAULT 60,
    
    -- Metadata
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT CURRENT_USER,
    
    -- Constraints
    CONSTRAINT valid_schedule_type 
        CHECK (schedule_type IN ('cron', 'smart', 'interval')),
    CONSTRAINT valid_command_type 
        CHECK (command_type IN ('shell', 'sql', 'python', 'function'))
);

COMMENT ON TABLE scheduler.jobs IS 'Master job configuration table for database-driven scheduling';
COMMENT ON COLUMN scheduler.jobs.job_name IS 'Unique identifier for this job (e.g., mlb_schedule_daily)';
COMMENT ON COLUMN scheduler.jobs.schedule IS 'Cron expression or special value like smart';
COMMENT ON COLUMN scheduler.jobs.schedule_type IS 'cron=fixed schedule, smart=adaptive, interval=every N seconds';
COMMENT ON COLUMN scheduler.jobs.is_game_aware IS 'If true, polling rate changes based on active games';

-- Job run history (for idempotency and tracking)
CREATE TABLE IF NOT EXISTS scheduler.job_runs (
    run_id UUID PRIMARY KEY DEFAULT GEN_RANDOM_UUID(),
    job_id INTEGER NOT NULL REFERENCES scheduler.jobs(job_id) ON DELETE CASCADE,
    
    -- Run details
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'running',  -- 'running', 'success', 'failed', 'timeout', 'skipped'
    
    -- Idempotency tracking
    run_checksum VARCHAR(64),  -- Prevents duplicate runs for same data
    data_checksum VARCHAR(64),  -- Checksum of ingested data (for deduplication)
    
    -- Execution details
    output TEXT,  -- stdout
    error_output TEXT,  -- stderr
    exit_code INTEGER,
    
    -- Performance metrics
    duration_ms INTEGER,
    rows_affected INTEGER,
    
    -- Context
    game_pks INTEGER[],  -- Which games this run processed
    metadata JSONB,
    
    -- Idempotency window
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint for idempotency
    CONSTRAINT unique_recent_run 
        UNIQUE (job_id, run_checksum, created_at)
);

COMMENT ON TABLE scheduler.job_runs IS 'History of job executions with idempotency tracking';
COMMENT ON COLUMN scheduler.job_runs.run_checksum IS 'Hash of (job_id, run_time_window) to prevent duplicate runs';
COMMENT ON COLUMN scheduler.job_runs.data_checksum IS 'Hash of actual data ingested - prevents duplicate data';

-- Indexes for performance
CREATE INDEX idx_jobs_enabled ON scheduler.jobs(is_enabled);
CREATE INDEX idx_jobs_type ON scheduler.jobs(job_type);
CREATE INDEX idx_job_runs_job_id ON scheduler.job_runs(job_id);
CREATE INDEX idx_job_runs_status ON scheduler.job_runs(status);
CREATE INDEX idx_job_runs_started_at ON scheduler.job_runs(started_at DESC);
CREATE INDEX idx_job_runs_checksum ON scheduler.job_runs(data_checksum) 
    WHERE data_checksum IS NOT NULL;

-- Function to update timestamps
CREATE OR REPLACE FUNCTION scheduler.update_job_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_jobs_timestamp ON scheduler.jobs;
CREATE TRIGGER update_jobs_timestamp
    BEFORE UPDATE ON scheduler.jobs
    FOR EACH ROW
    EXECUTE FUNCTION scheduler.update_job_timestamp();

-- ============================================================================
-- IDEMPOTENCY FUNCTIONS
-- ============================================================================

-- Check if a data item was already ingested (prevents duplicates)
CREATE OR REPLACE FUNCTION scheduler.is_duplicate_ingestion(
    p_data_checksum VARCHAR(64),
    p_hours_back INTEGER DEFAULT 24
) RETURNS BOOLEAN AS $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM scheduler.job_runs
        WHERE data_checksum = p_data_checksum
        AND created_at > NOW() - INTERVAL '1 hour' * p_hours_back
        AND status IN ('success', 'running')
    ) INTO v_exists;
    
    RETURN v_exists;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION scheduler.is_duplicate_ingestion IS 'Check if data was already ingested (idempotency)';

-- Record job start with idempotency check
CREATE OR REPLACE FUNCTION scheduler.record_job_start(
    p_job_name VARCHAR,
    p_run_checksum VARCHAR DEFAULT NULL,
    p_data_checksum VARCHAR DEFAULT NULL,
    p_game_pks INTEGER[] DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_job_id INTEGER;
    v_run_id UUID;
    v_is_duplicate BOOLEAN;
BEGIN
    -- Get job_id
    SELECT job_id INTO v_job_id
    FROM scheduler.jobs
    WHERE job_name = p_job_name;
    
    IF v_job_id IS NULL THEN
        RAISE EXCEPTION 'Job not found: %', p_job_name;
    END IF;
    
    -- Check for duplicate
    IF p_data_checksum IS NOT NULL THEN
        v_is_duplicate := scheduler.is_duplicate_ingestion(p_data_checksum);
        IF v_is_duplicate THEN
            RAISE NOTICE 'Duplicate ingestion skipped for checksum: %', p_data_checksum;
            RETURN NULL;
        END IF;
    END IF;
    
    -- Insert run record
    INSERT INTO scheduler.job_runs (
        job_id, run_checksum, data_checksum, game_pks, status
    ) VALUES (
        v_job_id, p_run_checksum, p_data_checksum, p_game_pks, 'running'
    ) RETURNING run_id INTO v_run_id;
    
    -- Update job status
    UPDATE scheduler.jobs
    SET is_running = TRUE, last_run_at = NOW()
    WHERE job_id = v_job_id;
    
    RETURN v_run_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION scheduler.record_job_start IS 'Start job tracking with duplicate check';

-- Record job completion
CREATE OR REPLACE FUNCTION scheduler.record_job_complete(
    p_run_id UUID,
    p_status VARCHAR,
    p_output TEXT DEFAULT NULL,
    p_error_output TEXT DEFAULT NULL,
    p_exit_code INTEGER DEFAULT NULL,
    p_rows_affected INTEGER DEFAULT NULL,
    p_metadata JSONB DEFAULT NULL
) RETURNS VOID AS $$
DECLARE
    v_job_id INTEGER;
BEGIN
    -- Update run record
    UPDATE scheduler.job_runs
    SET 
        status = p_status,
        completed_at = NOW(),
        output = p_output,
        error_output = p_error_output,
        exit_code = p_exit_code,
        duration_ms = EXTRACT(EPOCH FROM (NOW() - started_at))::INTEGER * 1000,
        rows_affected = p_rows_affected,
        metadata = p_metadata
    WHERE run_id = p_run_id
    RETURNING job_id INTO v_job_id;
    
    -- Update job status
    UPDATE scheduler.jobs
    SET is_running = FALSE
    WHERE job_id = v_job_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION scheduler.record_job_complete IS 'Mark job as completed';

-- ============================================================================
-- SMART SCHEDULING FUNCTIONS
-- ============================================================================

-- Get optimal polling interval based on game schedule
CREATE OR REPLACE FUNCTION scheduler.get_polling_interval()
RETURNS INTEGER AS $$
DECLARE
    v_now TIMESTAMP WITH TIME ZONE := NOW();
    v_today DATE := CURRENT_DATE;
    v_active_games INTEGER;
    v_pre_game_games INTEGER;
    v_today_games INTEGER;
    v_is_season BOOLEAN;
BEGIN
    -- Check if during season (Mar 15 - Oct 15)
    v_is_season := (EXTRACT(MONTH FROM v_now) BETWEEN 3 AND 10);
    
    IF NOT v_is_season THEN
        RETURN 3600;  -- 1 hour off-season
    END IF;
    
    -- Count active games (in progress)
    SELECT COUNT(*) INTO v_active_games
    FROM core.games
    WHERE game_date = v_today
    AND status_code = 'L';  -- Live
    
    IF v_active_games > 0 THEN
        RETURN 10;  -- 10 seconds during games
    END IF;
    
    -- Count pre-game (within 60 min of start)
    SELECT COUNT(*) INTO v_pre_game_games
    FROM core.games
    WHERE game_date = v_today
    AND status_code IN ('S', 'P')  -- Scheduled, Preview
    AND game_time BETWEEN v_now AND v_now + INTERVAL '60 minutes';
    
    IF v_pre_game_games > 0 THEN
        RETURN 60;  -- 1 minute pre-game
    END IF;
    
    -- Count today's games
    SELECT COUNT(*) INTO v_today_games
    FROM core.games
    WHERE game_date = v_today;
    
    IF v_today_games > 0 THEN
        RETURN 300;  -- 5 minutes on game day
    END IF;
    
    -- Default off-hours
    RETURN 3600;  -- 1 hour
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION scheduler.get_polling_interval IS 'Returns optimal polling interval in seconds based on game schedule';

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Active jobs view
CREATE OR REPLACE VIEW scheduler.v_active_jobs AS
SELECT 
    j.job_id,
    j.job_name,
    j.job_type,
    j.schedule,
    j.schedule_type,
    j.is_game_aware,
    j.is_enabled,
    j.is_running,
    j.last_run_at,
    j.description,
    -- Last run info
    jr.status AS last_status,
    jr.duration_ms AS last_duration_ms,
    jr.created_at AS last_run_created_at
FROM scheduler.jobs j
LEFT JOIN LATERAL (
    SELECT status, duration_ms, created_at
    FROM scheduler.job_runs
    WHERE job_id = j.job_id
    ORDER BY started_at DESC
    LIMIT 1
) jr ON true
WHERE j.is_enabled = TRUE
ORDER BY j.job_name;

COMMENT ON VIEW scheduler.v_active_jobs IS 'Overview of active jobs with last run status';

-- Job performance summary
CREATE OR REPLACE VIEW scheduler.v_job_performance AS
SELECT 
    j.job_name,
    j.job_type,
    COUNT(jr.run_id) AS total_runs,
    COUNT(*) FILTER (WHERE jr.status = 'success') AS success_count,
    COUNT(*) FILTER (WHERE jr.status = 'failed') AS failure_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE jr.status = 'success') / COUNT(*), 
        1
    ) AS success_rate,
    AVG(jr.duration_ms) FILTER (WHERE jr.status = 'success') AS avg_duration_ms,
    MAX(jr.started_at) AS last_run_at
FROM scheduler.jobs j
LEFT JOIN scheduler.job_runs jr ON j.job_id = jr.job_id
WHERE jr.started_at > NOW() - INTERVAL '7 days'
GROUP BY j.job_id, j.job_name, j.job_type
ORDER BY j.job_name;

COMMENT ON VIEW scheduler.v_job_performance IS '7-day job performance summary';

-- Recent duplicates (for monitoring)
CREATE OR REPLACE VIEW scheduler.v_recent_duplicates AS
SELECT 
    jr.run_id,
    j.job_name,
    jr.data_checksum,
    jr.started_at,
    jr.status
FROM scheduler.job_runs jr
JOIN scheduler.jobs j ON jr.job_id = j.job_id
WHERE jr.data_checksum IS NOT NULL
AND jr.created_at > NOW() - INTERVAL '24 hours'
AND jr.status = 'skipped'
ORDER BY jr.started_at DESC;

COMMENT ON VIEW scheduler.v_recent_duplicates IS 'Recently skipped duplicate ingestions';
