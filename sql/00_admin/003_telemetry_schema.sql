"""
Telemetry Schema - Enterprise Observability Infrastructure

Provides structured logging, metrics collection, and performance monitoring
for all database operations and application events.

Tables:
- telemetry.events: Structured application events (jsonb payload)
- telemetry.metrics: Time-series metrics (counter, gauge, histogram)
- telemetry.query_logs: Database query performance tracking
- telemetry.jobs: Batch job orchestration and tracking
- telemetry.errors: Exception and error tracking
- telemetry.traces: Distributed tracing spans

Usage:
    -- Log an event
    SELECT telemetry.log_event('training.started', '{"model": "xgb"}');
    
    -- Record a metric
    SELECT telemetry.record_metric('query.duration', 150.5, 'milliseconds');
    
    -- Start a job
    SELECT telemetry.start_job('feature_build', '2024-season');
"""

-- Create telemetry schema
CREATE SCHEMA IF NOT EXISTS telemetry;

COMMENT ON SCHEMA telemetry IS 'Enterprise observability: events, metrics, query logs, job tracking';

-- ============================================================
-- 1. EVENTS TABLE - Structured application events
-- ============================================================

CREATE TABLE IF NOT EXISTS telemetry.events (
    event_id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(128) NOT NULL,           -- 'training.started', 'query.completed', etc.
    event_version INTEGER DEFAULT 1,            -- Schema version for event payload
    severity VARCHAR(20) DEFAULT 'INFO',         -- DEBUG, INFO, WARN, ERROR, CRITICAL
    source VARCHAR(128),                        -- Component/module name
    correlation_id UUID,                        -- Trace across distributed operations
    session_id VARCHAR(128),                     -- User session identifier
    payload JSONB,                              -- Structured event data
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Partitioning support
    bucket_date DATE DEFAULT CURRENT_DATE
) PARTITION BY RANGE (bucket_date);

-- Create monthly partitions for events
CREATE TABLE telemetry.events_2025_01 PARTITION OF telemetry.events
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE telemetry.events_2025_02 PARTITION OF telemetry.events
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE telemetry.events_2025_03 PARTITION OF telemetry.events
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE telemetry.events_2025_04 PARTITION OF telemetry.events
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE telemetry.events_2025_05 PARTITION OF telemetry.events
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');

-- Indexes for efficient querying
CREATE INDEX idx_events_type ON telemetry.events(event_type, created_at DESC);
CREATE INDEX idx_events_severity ON telemetry.events(severity, created_at DESC) WHERE severity IN ('ERROR', 'CRITICAL', 'WARN');
CREATE INDEX idx_events_correlation ON telemetry.events(correlation_id, created_at DESC);
CREATE INDEX idx_events_source ON telemetry.events(source, created_at DESC);
CREATE INDEX idx_events_payload ON telemetry.events USING GIN(payload jsonb_path_ops);

COMMENT ON TABLE telemetry.events IS 'Application events with structured jsonb payloads';

-- ============================================================
-- 2. METRICS TABLE - Time-series metrics
-- ============================================================

CREATE TABLE IF NOT EXISTS telemetry.metrics (
    metric_id BIGSERIAL PRIMARY KEY,
    metric_name VARCHAR(256) NOT NULL,          -- 'query.duration', 'rows.processed'
    metric_type VARCHAR(20) NOT NULL,           -- counter, gauge, histogram, timing
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(64),                          -- 'milliseconds', 'rows', 'bytes'
    labels JSONB,                              -- {'table': 'games', 'operation': 'insert'}
    source VARCHAR(128),
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    bucket_date DATE DEFAULT CURRENT_DATE
) PARTITION BY RANGE (bucket_date);

-- Monthly partitions for metrics
CREATE TABLE telemetry.metrics_2025_01 PARTITION OF telemetry.metrics
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE telemetry.metrics_2025_02 PARTITION OF telemetry.metrics
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE telemetry.metrics_2025_03 PARTITION OF telemetry.metrics
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE telemetry.metrics_2025_04 PARTITION OF telemetry.metrics
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE telemetry.metrics_2025_05 PARTITION OF telemetry.metrics
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');

-- Indexes
CREATE INDEX idx_metrics_name_time ON telemetry.metrics(metric_name, recorded_at DESC);
CREATE INDEX idx_metrics_labels ON telemetry.metrics USING GIN(labels);
CREATE INDEX idx_metrics_source ON telemetry.metrics(source, recorded_at DESC);

COMMENT ON TABLE telemetry.metrics IS 'Time-series metrics for performance monitoring';

-- ============================================================
-- 3. QUERY LOGS TABLE - Database query performance
-- ============================================================

CREATE TABLE IF NOT EXISTS telemetry.query_logs (
    query_id BIGSERIAL PRIMARY KEY,
    query_hash VARCHAR(64),                     -- MD5 hash of normalized query
    query_text TEXT,                           -- Full query (truncated if needed)
    query_normalized TEXT,                     -- Query with literals replaced
    duration_ms DOUBLE PRECISION,              -- Execution time
    rows_affected BIGINT,
    rows_returned BIGINT,
    db_user VARCHAR(128),
    db_name VARCHAR(128),
    client_addr INET,
    application_name VARCHAR(128),
    was_slow BOOLEAN DEFAULT FALSE,           -- Flag if exceeds threshold
    plan_hash VARCHAR(64),                     -- Execution plan hash
    -- Wait event information
    wait_event_type VARCHAR(64),
    wait_event VARCHAR(64),
    waited_ms DOUBLE PRECISION,
    -- Context
    correlation_id UUID,
    session_id VARCHAR(128),
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    bucket_date DATE DEFAULT CURRENT_DATE
) PARTITION BY RANGE (bucket_date);

-- Monthly partitions for query logs
CREATE TABLE telemetry.query_logs_2025_01 PARTITION OF telemetry.query_logs
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE telemetry.query_logs_2025_02 PARTITION OF telemetry.query_logs
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE telemetry.query_logs_2025_03 PARTITION OF telemetry.query_logs
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE telemetry.query_logs_2025_04 PARTITION OF telemetry.query_logs
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE telemetry.query_logs_2025_05 PARTITION OF telemetry.query_logs
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');

-- Indexes for query analysis
CREATE INDEX idx_query_logs_slow ON telemetry.query_logs(was_slow, recorded_at DESC) WHERE was_slow = TRUE;
CREATE INDEX idx_query_logs_hash ON telemetry.query_logs(query_hash, recorded_at DESC);
CREATE INDEX idx_query_logs_duration ON telemetry.query_logs(duration_ms DESC) WHERE duration_ms > 1000;
CREATE INDEX idx_query_logs_correlation ON telemetry.query_logs(correlation_id, recorded_at DESC);

COMMENT ON TABLE telemetry.query_logs IS 'Database query performance logs for bottleneck analysis';

-- ============================================================
-- 4. JOBS TABLE - Batch job orchestration
-- ============================================================

CREATE TYPE telemetry.job_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');

CREATE TABLE IF NOT EXISTS telemetry.jobs (
    job_id BIGSERIAL PRIMARY KEY,
    job_name VARCHAR(256) NOT NULL,             -- 'feature_build', 'model_training'
    job_type VARCHAR(128),                      -- 'batch', 'scheduled', 'ad_hoc'
    job_group VARCHAR(128),                     -- 'ingestion', 'features', 'models'
    status telemetry.job_status DEFAULT 'pending',
    payload JSONB,                             -- Job parameters
    
    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms DOUBLE PRECISION GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000
    ) STORED,
    
    -- Progress tracking
    total_steps INTEGER DEFAULT 1,
    completed_steps INTEGER DEFAULT 0,
    progress_pct DOUBLE PRECISION GENERATED ALWAYS AS (
        CASE WHEN total_steps > 0 
            THEN (completed_steps::DOUBLE PRECISION / total_steps) * 100 
            ELSE 0 
        END
    ) STORED,
    
    -- Results and errors
    result_summary JSONB,                      -- High-level results
    error_message TEXT,
    error_stacktrace TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Resource tracking
    memory_mb_peak DOUBLE PRECISION,
    cpu_seconds DOUBLE PRECISION,
    rows_processed BIGINT,
    
    -- Attribution
    correlation_id UUID,
    triggered_by VARCHAR(128),                  -- User, scheduler, webhook
    
    -- Constraints
    CONSTRAINT valid_progress CHECK (completed_steps <= total_steps)
);

-- Indexes
CREATE INDEX idx_jobs_status ON telemetry.jobs(status, created_at DESC);
CREATE INDEX idx_jobs_name ON telemetry.jobs(job_name, created_at DESC);
CREATE INDEX idx_jobs_correlation ON telemetry.jobs(correlation_id);
CREATE INDEX idx_jobs_active ON telemetry.jobs(status, started_at) WHERE status = 'running';

COMMENT ON TABLE telemetry.jobs IS 'Batch job orchestration and execution tracking';

-- ============================================================
-- 5. ERRORS TABLE - Exception tracking
-- ============================================================

CREATE TABLE IF NOT EXISTS telemetry.errors (
    error_id BIGSERIAL PRIMARY KEY,
    error_type VARCHAR(256) NOT NULL,           -- Exception class name
    error_message TEXT NOT NULL,
    error_stacktrace TEXT,
    error_hash VARCHAR(64),                     -- Hash for grouping similar errors
    
    -- Context
    source VARCHAR(128),                        -- Component where error occurred
    operation VARCHAR(256),                     -- What operation was being performed
    correlation_id UUID,
    session_id VARCHAR(128),
    
    -- Environment
    environment VARCHAR(64) DEFAULT 'development', -- prod, staging, dev
    release_version VARCHAR(64),
    
    -- Resolution tracking
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    occurrence_count INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'open',         -- open, resolved, ignored
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(128),
    
    -- Additional context
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    bucket_date DATE DEFAULT CURRENT_DATE
) PARTITION BY RANGE (bucket_date);

-- Monthly partitions for errors
CREATE TABLE telemetry.errors_2025_01 PARTITION OF telemetry.errors
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE telemetry.errors_2025_02 PARTITION OF telemetry.errors
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE telemetry.errors_2025_03 PARTITION OF telemetry.errors
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE telemetry.errors_2025_04 PARTITION OF telemetry.errors
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE telemetry.errors_2025_05 PARTITION OF telemetry.errors
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');

-- Indexes
CREATE INDEX idx_errors_hash ON telemetry.errors(error_hash, last_seen_at DESC);
CREATE INDEX idx_errors_status ON telemetry.errors(status, created_at DESC);
CREATE INDEX idx_errors_type ON telemetry.errors(error_type, created_at DESC);
CREATE INDEX idx_errors_correlation ON telemetry.errors(correlation_id);

COMMENT ON TABLE telemetry.errors IS 'Exception and error tracking with grouping';

-- ============================================================
-- 6. TRACES TABLE - Distributed tracing
-- ============================================================

CREATE TABLE IF NOT EXISTS telemetry.traces (
    trace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_span_id UUID,                      -- NULL for root spans
    span_id UUID DEFAULT gen_random_uuid(),
    operation_name VARCHAR(256) NOT NULL,      -- 'train_model', 'fetch_features'
    service_name VARCHAR(128) NOT NULL,        -- 'training', 'ingestion'
    
    -- Timing
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    duration_ms DOUBLE PRECISION,
    
    -- Status
    status VARCHAR(20) DEFAULT 'ok',         -- ok, error, cancelled
    error_message TEXT,
    
    -- Context
    tags JSONB,
    logs JSONB,                                -- Array of log events during span
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_traces_parent ON telemetry.traces(parent_span_id);
CREATE INDEX idx_traces_operation ON telemetry.traces(service_name, operation_name, started_at DESC);
CREATE INDEX idx_traces_time ON telemetry.traces(started_at DESC);

COMMENT ON TABLE telemetry.traces IS 'Distributed tracing spans for request flow analysis';

-- ============================================================
-- HELPER FUNCTIONS
-- ============================================================

-- Log an event
CREATE OR REPLACE FUNCTION telemetry.log_event(
    p_event_type VARCHAR,
    p_payload JSONB DEFAULT NULL,
    p_severity VARCHAR DEFAULT 'INFO',
    p_source VARCHAR DEFAULT NULL,
    p_correlation_id UUID DEFAULT NULL
) RETURNS BIGINT AS $$
DECLARE
    v_event_id BIGINT;
BEGIN
    INSERT INTO telemetry.events (event_type, payload, severity, source, correlation_id)
    VALUES (p_event_type, p_payload, p_severity, p_source, p_correlation_id)
    RETURNING event_id INTO v_event_id;
    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

-- Record a metric
CREATE OR REPLACE FUNCTION telemetry.record_metric(
    p_metric_name VARCHAR,
    p_value DOUBLE PRECISION,
    p_unit VARCHAR DEFAULT NULL,
    p_labels JSONB DEFAULT NULL,
    p_source VARCHAR DEFAULT NULL
) RETURNS BIGINT AS $$
DECLARE
    v_metric_id BIGINT;
    v_type VARCHAR;
BEGIN
    -- Infer metric type from name patterns
    v_type := CASE
        WHEN p_metric_name LIKE '%.count' THEN 'counter'
        WHEN p_metric_name LIKE '%.duration' OR p_metric_name LIKE '%.time' THEN 'timing'
        WHEN p_metric_name LIKE '%.bytes' OR p_metric_name LIKE '%.rows' THEN 'gauge'
        ELSE 'gauge'
    END;
    
    INSERT INTO telemetry.metrics (metric_name, metric_type, value, unit, labels, source)
    VALUES (p_metric_name, v_type, p_value, p_unit, p_labels, p_source)
    RETURNING metric_id INTO v_metric_id;
    RETURN v_metric_id;
END;
$$ LANGUAGE plpgsql;

-- Start a job
CREATE OR REPLACE FUNCTION telemetry.start_job(
    p_job_name VARCHAR,
    p_payload JSONB DEFAULT NULL,
    p_job_type VARCHAR DEFAULT 'batch',
    p_job_group VARCHAR DEFAULT NULL,
    p_total_steps INTEGER DEFAULT 1,
    p_triggered_by VARCHAR DEFAULT NULL
) RETURNS BIGINT AS $$
DECLARE
    v_job_id BIGINT;
    v_correlation UUID := gen_random_uuid();
BEGIN
    INSERT INTO telemetry.jobs (
        job_name, job_type, job_group, payload, 
        total_steps, triggered_by, correlation_id, status, started_at
    ) VALUES (
        p_job_name, p_job_type, p_job_group, p_payload,
        p_total_steps, p_triggered_by, v_correlation, 'running', NOW()
    )
    RETURNING job_id INTO v_job_id;
    
    -- Log the job start event
    PERFORM telemetry.log_event(
        'job.started',
        jsonb_build_object('job_id', v_job_id, 'job_name', p_job_name),
        'INFO',
        p_job_group,
        v_correlation
    );
    
    RETURN v_job_id;
END;
$$ LANGUAGE plpgsql;

-- Update job progress
CREATE OR REPLACE FUNCTION telemetry.update_job_progress(
    p_job_id BIGINT,
    p_completed_steps INTEGER,
    p_result_summary JSONB DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    UPDATE telemetry.jobs
    SET completed_steps = p_completed_steps,
        result_summary = COALESCE(p_result_summary, result_summary)
    WHERE job_id = p_job_id;
END;
$$ LANGUAGE plpgsql;

-- Complete a job
CREATE OR REPLACE FUNCTION telemetry.complete_job(
    p_job_id BIGINT,
    p_status VARCHAR DEFAULT 'completed',
    p_result_summary JSONB DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL
) RETURNS VOID AS $$
DECLARE
    v_job RECORD;
BEGIN
    SELECT * INTO v_job FROM telemetry.jobs WHERE job_id = p_job_id;
    
    UPDATE telemetry.jobs
    SET status = p_status::telemetry.job_status,
        completed_at = NOW(),
        result_summary = p_result_summary,
        error_message = p_error_message
    WHERE job_id = p_job_id;
    
    -- Log completion event
    PERFORM telemetry.log_event(
        'job.' || p_status,
        jsonb_build_object(
            'job_id', p_job_id,
            'job_name', v_job.job_name,
            'duration_ms', EXTRACT(EPOCH FROM (NOW() - v_job.started_at)) * 1000
        ),
        CASE WHEN p_status = 'failed' THEN 'ERROR' ELSE 'INFO' END,
        v_job.job_group,
        v_job.correlation_id
    );
END;
$$ LANGUAGE plpgsql;

-- Log an error with deduplication
CREATE OR REPLACE FUNCTION telemetry.log_error(
    p_error_type VARCHAR,
    p_error_message TEXT,
    p_error_stacktrace TEXT DEFAULT NULL,
    p_source VARCHAR DEFAULT NULL,
    p_operation VARCHAR DEFAULT NULL,
    p_correlation_id UUID DEFAULT NULL,
    p_payload JSONB DEFAULT NULL
) RETURNS BIGINT AS $$
DECLARE
    v_error_id BIGINT;
    v_error_hash VARCHAR(64);
    v_existing_id BIGINT;
BEGIN
    -- Generate hash for deduplication
    v_error_hash := MD5(p_error_type || ':' || LEFT(p_error_message, 200));
    
    -- Try to update existing error (within 1 hour window for grouping)
    SELECT error_id INTO v_existing_id
    FROM telemetry.errors
    WHERE error_hash = v_error_hash
      AND last_seen_at > NOW() - INTERVAL '1 hour'
      AND status = 'open'
    ORDER BY last_seen_at DESC
    LIMIT 1;
    
    IF v_existing_id IS NOT NULL THEN
        UPDATE telemetry.errors
        SET occurrence_count = occurrence_count + 1,
            last_seen_at = NOW()
        WHERE error_id = v_existing_id;
        RETURN v_existing_id;
    END IF;
    
    -- Insert new error
    INSERT INTO telemetry.errors (
        error_type, error_message, error_stacktrace, error_hash,
        source, operation, correlation_id, payload
    ) VALUES (
        p_error_type, p_error_message, p_error_stacktrace, v_error_hash,
        p_source, p_operation, p_correlation_id, p_payload
    )
    RETURNING error_id INTO v_error_id;
    
    RETURN v_error_id;
END;
$$ LANGUAGE plpgsql;

-- Get slow queries summary
CREATE OR REPLACE VIEW telemetry.slow_queries_summary AS
SELECT 
    query_hash,
    LEFT(query_normalized, 100) as query_preview,
    COUNT(*) as execution_count,
    AVG(duration_ms) as avg_duration_ms,
    MAX(duration_ms) as max_duration_ms,
    MIN(duration_ms) as min_duration_ms,
    SUM(rows_returned) as total_rows_returned,
    MAX(recorded_at) as last_seen
FROM telemetry.query_logs
WHERE was_slow = TRUE
GROUP BY query_hash, query_normalized
ORDER BY avg_duration_ms DESC;

COMMENT ON VIEW telemetry.slow_queries_summary IS 'Aggregated slow query analysis';

-- Get job statistics
CREATE OR REPLACE VIEW telemetry.job_statistics AS
SELECT 
    job_name,
    job_group,
    COUNT(*) as total_runs,
    COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_runs,
    AVG(duration_ms) FILTER (WHERE status = 'completed') as avg_duration_ms,
    MAX(duration_ms) as max_duration_ms,
    SUM(rows_processed) as total_rows_processed
FROM telemetry.jobs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY job_name, job_group;

COMMENT ON VIEW telemetry.job_statistics IS 'Weekly job execution statistics';

-- Get error summary
CREATE OR REPLACE VIEW telemetry.error_summary AS
SELECT 
    error_type,
    error_hash,
    LEFT(error_message, 100) as message_preview,
    COUNT(*) as total_occurrences,
    MIN(first_seen_at) as first_seen,
    MAX(last_seen_at) as last_seen,
    status
FROM telemetry.errors
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY error_type, error_hash, LEFT(error_message, 100), status
ORDER BY COUNT(*) DESC;

COMMENT ON VIEW telemetry.error_summary IS 'Weekly error occurrence summary';

-- ============================================================
-- AUTO-MAINTENANCE: Partition management
-- ============================================================

CREATE OR REPLACE FUNCTION telemetry.create_monthly_partitions()
RETURNS VOID AS $$
DECLARE
    v_next_month DATE := DATE_TRUNC('month', NOW() + INTERVAL '1 month');
    v_table_name TEXT;
    v_start DATE;
    v_end DATE;
BEGIN
    -- Events
    v_table_name := 'telemetry.events_' || TO_CHAR(v_next_month, 'YYYY_MM');
    v_start := v_next_month;
    v_end := v_next_month + INTERVAL '1 month';
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF telemetry.events FOR VALUES FROM (%L) TO (%L)',
        v_table_name, v_start, v_end);
    
    -- Metrics
    v_table_name := 'telemetry.metrics_' || TO_CHAR(v_next_month, 'YYYY_MM');
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF telemetry.metrics FOR VALUES FROM (%L) TO (%L)',
        v_table_name, v_start, v_end);
    
    -- Query logs
    v_table_name := 'telemetry.query_logs_' || TO_CHAR(v_next_month, 'YYYY_MM');
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF telemetry.query_logs FOR VALUES FROM (%L) TO (%L)',
        v_table_name, v_start, v_end);
    
    -- Errors
    v_table_name := 'telemetry.errors_' || TO_CHAR(v_next_month, 'YYYY_MM');
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF telemetry.errors FOR VALUES FROM (%L) TO (%L)',
        v_table_name, v_start, v_end);
END;
$$ LANGUAGE plpgsql;

-- Schedule monthly partition creation (requires pg_cron)
-- SELECT cron.schedule('create-telemetry-partitions', '0 0 1 * *', 'SELECT telemetry.create_monthly_partitions()');
