-- File: sql/75_scheduler/7501_ingestion_scheduler.sql
-- Purpose: Database-driven cron job scheduler for data ingestion
-- Author: Agent Cascade
-- Date: 2026-04-30
-- Depends On: betting.market_odds, live.game_events
-- Called By: ingestion scheduler service

-- Scheduler schema for automated data ingestion
-- Uses PostgreSQL + pg_cron for job execution

CREATE SCHEMA IF NOT EXISTS scheduler;

COMMENT ON SCHEMA scheduler IS 
'Database-driven cron job scheduler for live data and odds ingestion';

-- ============================================================================
-- Job Definitions
-- ============================================================================

CREATE TABLE IF NOT EXISTS scheduler.jobs (
    job_id BIGSERIAL PRIMARY KEY,
    
    -- Identity
    job_name VARCHAR(100) NOT NULL UNIQUE,
    job_type VARCHAR(50) NOT NULL,  -- 'live_feed', 'odds_fetch', 'data_sync', 'analysis'
    
    -- Source configuration
    source_type VARCHAR(50) NOT NULL,  -- 'mlb_api', 'espn', 'the_odds_api', 'pinnacle', 'draftkings'
    source_config JSONB DEFAULT '{}',  -- API keys, endpoints, rate limits
    
    -- Scheduling (cron format or interval)
    schedule_type VARCHAR(20) NOT NULL DEFAULT 'cron',  -- 'cron', 'interval', 'event'
    schedule_expression VARCHAR(100) NOT NULL,  -- '* * * * *' for every minute, '5 minutes'
    
    -- What to fetch
    sport VARCHAR(20) DEFAULT 'mlb',
    data_types VARCHAR[] DEFAULT ARRAY['odds'],  -- ['odds', 'scores', 'stats', 'lineups']
    
    -- Execution config
    enabled BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 5,  -- 1=high, 10=low
    timeout_seconds INTEGER DEFAULT 60,
    retry_count INTEGER DEFAULT 3,
    retry_delay_seconds INTEGER DEFAULT 5,
    
    -- Rate limiting
    rate_limit_per_minute INTEGER DEFAULT 60,
    concurrent_jobs_allowed INTEGER DEFAULT 1,
    
    -- WebSocket config (for live feeds)
    websocket_url VARCHAR(500),
    websocket_enabled BOOLEAN DEFAULT FALSE,
    
    -- Event hooks (JSON array of event names)
    pre_hooks JSONB DEFAULT '[]',
    post_hooks JSONB DEFAULT '[]',
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'system',
    description TEXT
);

COMMENT ON TABLE scheduler.jobs IS
'Registered ingestion jobs with scheduling configuration';

CREATE INDEX idx_jobs_enabled ON scheduler.jobs (enabled, job_type);
CREATE INDEX idx_jobs_schedule ON scheduler.jobs (schedule_type, enabled);

-- ============================================================================
-- Job Execution Log
-- ============================================================================

CREATE TABLE IF NOT EXISTS scheduler.job_runs (
    run_id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES scheduler.jobs(job_id) ON DELETE CASCADE,
    
    -- Execution details
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'running',  -- 'running', 'success', 'failed', 'timeout'
    
    -- Results
    records_fetched INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    
    -- Error tracking
    error_message TEXT,
    error_details JSONB,
    
    -- Performance metrics
    duration_ms INTEGER,
    api_calls_made INTEGER DEFAULT 0,
    api_rate_limit_hits INTEGER DEFAULT 0,
    
    -- Raw data snapshot (optional, for debugging)
    sample_data JSONB,
    
    -- WebSocket specific
    websocket_connected_at TIMESTAMP WITH TIME ZONE,
    websocket_disconnected_at TIMESTAMP WITH TIME ZONE,
    messages_received INTEGER DEFAULT 0
);

COMMENT ON TABLE scheduler.job_runs IS
'Execution history for all ingestion jobs';

CREATE INDEX idx_job_runs_job ON scheduler.job_runs (job_id, started_at DESC);
CREATE INDEX idx_job_runs_status ON scheduler.job_runs (status, started_at DESC);
CREATE INDEX idx_job_runs_recent ON scheduler.job_runs (started_at DESC) WHERE status = 'running';

-- ============================================================================
-- Active WebSocket Connections
-- ============================================================================

CREATE TABLE IF NOT EXISTS scheduler.websocket_connections (
    connection_id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES scheduler.jobs(job_id) ON DELETE CASCADE,
    
    -- Connection state
    status VARCHAR(20) NOT NULL DEFAULT 'connecting',  -- 'connecting', 'connected', 'disconnected', 'error'
    connected_at TIMESTAMP WITH TIME ZONE,
    disconnected_at TIMESTAMP WITH TIME ZONE,
    last_ping_at TIMESTAMP WITH TIME ZONE,
    
    -- Metrics
    messages_received BIGINT DEFAULT 0,
    messages_processed BIGINT DEFAULT 0,
    messages_failed BIGINT DEFAULT 0,
    bytes_received BIGINT DEFAULT 0,
    
    -- Error tracking
    error_count INTEGER DEFAULT 0,
    last_error_at TIMESTAMP WITH TIME ZONE,
    last_error_message TEXT,
    
    -- Reconnection tracking
    reconnect_attempts INTEGER DEFAULT 0,
    next_reconnect_at TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE scheduler.websocket_connections IS
'Active WebSocket connection tracking for live feeds';

CREATE INDEX idx_ws_connections_job ON scheduler.websocket_connections (job_id, status);
CREATE INDEX idx_ws_connections_active ON scheduler.websocket_connections (status) WHERE status = 'connected';

-- ============================================================================
-- Functions
-- ============================================================================

-- Get jobs ready to run
CREATE OR REPLACE FUNCTION scheduler.get_due_jobs()
RETURNS TABLE (
    job_id BIGINT,
    job_name VARCHAR,
    job_type VARCHAR,
    source_type VARCHAR,
    source_config JSONB,
    sport VARCHAR,
    data_types VARCHAR[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        j.job_id,
        j.job_name,
        j.job_type,
        j.source_type,
        j.source_config,
        j.sport,
        j.data_types
    FROM scheduler.jobs j
    WHERE j.enabled = TRUE
    AND NOT EXISTS (
        -- Check if job is already running
        SELECT 1 FROM scheduler.job_runs jr
        WHERE jr.job_id = j.job_id
        AND jr.status = 'running'
        AND jr.started_at > NOW() - INTERVAL '1 minute'
    )
    AND (
        -- Check if enough time has passed since last run
        j.schedule_type = 'interval' AND (
            SELECT MAX(jr.started_at) 
            FROM scheduler.job_runs jr 
            WHERE jr.job_id = j.job_id
        ) IS NULL 
        OR (
            SELECT MAX(jr.started_at) 
            FROM scheduler.job_runs jr 
            WHERE jr.job_id = j.job_id
        ) < NOW() - (j.schedule_expression::INTERVAL)
    );
END;
$$ LANGUAGE plpgsql;

-- Log job start
CREATE OR REPLACE FUNCTION scheduler.log_job_start(p_job_id BIGINT)
RETURNS BIGINT AS $$
DECLARE
    v_run_id BIGINT;
BEGIN
    INSERT INTO scheduler.job_runs (job_id, status, started_at)
    VALUES (p_job_id, 'running', NOW())
    RETURNING run_id INTO v_run_id;
    
    RETURN v_run_id;
END;
$$ LANGUAGE plpgsql;

-- Log job completion
CREATE OR REPLACE FUNCTION scheduler.log_job_complete(
    p_run_id BIGINT,
    p_status VARCHAR,
    p_records_fetched INTEGER DEFAULT 0,
    p_records_inserted INTEGER DEFAULT 0,
    p_error_message TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    UPDATE scheduler.job_runs
    SET 
        status = p_status,
        completed_at = NOW(),
        duration_ms = EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000,
        records_fetched = p_records_fetched,
        records_inserted = p_records_inserted,
        error_message = p_error_message
    WHERE run_id = p_run_id;
END;
$$ LANGUAGE plpgsql;

-- Update WebSocket connection status
CREATE OR REPLACE FUNCTION scheduler.update_ws_connection(
    p_job_id BIGINT,
    p_status VARCHAR,
    p_messages_received INTEGER DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO scheduler.websocket_connections (
        job_id, status, connected_at, messages_received, last_error_message
    )
    VALUES (
        p_job_id, 
        p_status, 
        CASE WHEN p_status = 'connected' THEN NOW() ELSE NULL END,
        COALESCE(p_messages_received, 0),
        p_error_message
    )
    ON CONFLICT (job_id) WHERE status IN ('connecting', 'connected')
    DO UPDATE SET
        status = p_status,
        messages_received = scheduler.websocket_connections.messages_received + COALESCE(p_messages_received, 0),
        last_error_message = p_error_message,
        last_error_at = CASE WHEN p_error_message IS NOT NULL THEN NOW() ELSE scheduler.websocket_connections.last_error_at END,
        disconnected_at = CASE WHEN p_status = 'disconnected' THEN NOW() ELSE scheduler.websocket_connections.disconnected_at END;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Views
-- ============================================================================

-- Job status overview
CREATE OR REPLACE VIEW scheduler.job_status AS
SELECT 
    j.job_id,
    j.job_name,
    j.job_type,
    j.source_type,
    j.enabled,
    j.schedule_expression,
    (
        SELECT jr.status
        FROM scheduler.job_runs jr
        WHERE jr.job_id = j.job_id
        ORDER BY jr.started_at DESC
        LIMIT 1
    ) as last_run_status,
    (
        SELECT jr.started_at
        FROM scheduler.job_runs jr
        WHERE jr.job_id = j.job_id
        ORDER BY jr.started_at DESC
        LIMIT 1
    ) as last_run_at,
    (
        SELECT COUNT(*)
        FROM scheduler.job_runs jr
        WHERE jr.job_id = j.job_id
        AND jr.status = 'success'
        AND jr.started_at > NOW() - INTERVAL '24 hours'
    ) as successful_runs_24h,
    (
        SELECT COUNT(*)
        FROM scheduler.job_runs jr
        WHERE jr.job_id = j.job_id
        AND jr.status = 'failed'
        AND jr.started_at > NOW() - INTERVAL '24 hours'
    ) as failed_runs_24h
FROM scheduler.jobs j;

-- Active WebSocket feeds
CREATE OR REPLACE VIEW scheduler.active_websockets AS
SELECT 
    j.job_id,
    j.job_name,
    j.source_type,
    j.sport,
    wc.connected_at,
    wc.messages_received,
    wc.messages_processed,
    EXTRACT(EPOCH FROM (NOW() - wc.last_ping_at)) as seconds_since_last_ping
FROM scheduler.websocket_connections wc
JOIN scheduler.jobs j ON wc.job_id = j.job_id
WHERE wc.status = 'connected';

-- ============================================================================
-- Default Jobs (Seed Data)
-- ============================================================================

-- Live MLB feed (WebSocket)
INSERT INTO scheduler.jobs (
    job_name, job_type, source_type, schedule_type, schedule_expression,
    sport, data_types, websocket_enabled, priority, description
) VALUES (
    'mlb_live_feed',
    'live_feed',
    'mlb_api',
    'event',
    'continuous',
    'mlb',
    ARRAY['scores', 'plays', 'lineups'],
    TRUE,
    1,
    'Live MLB game data via WebSocket'
) ON CONFLICT (job_name) DO NOTHING;

-- Odds fetch every minute
INSERT INTO scheduler.jobs (
    job_name, job_type, source_type, schedule_type, schedule_expression,
    sport, data_types, priority, description
) VALUES (
    'odds_minute_fetch',
    'odds_fetch',
    'the_odds_api',
    'interval',
    '1 minute',
    'mlb',
    ARRAY['odds'],
    2,
    'Fetch latest odds from The Odds API'
) ON CONFLICT (job_name) DO NOTHING;

-- Hourly analysis job
INSERT INTO scheduler.jobs (
    job_name, job_type, source_type, schedule_type, schedule_expression,
    sport, data_types, priority, description
) VALUES (
    'hourly_bet_analysis',
    'analysis',
    'internal',
    'cron',
    '0 * * * *',
    'mlb',
    ARRAY['opportunities'],
    5,
    'Run betting analysis on all upcoming games'
) ON CONFLICT (job_name) DO NOTHING;

COMMENT ON TABLE scheduler.jobs IS 'Default ingestion jobs are seeded automatically';
