-- Error logging and monitoring schema for baseball multi-model ensemble system
-- Provides comprehensive error tracking, stack traces, and runtime metrics

-- Error logs table for detailed error tracking
CREATE TABLE IF NOT EXISTS admin.error_logs (
    error_id BIGSERIAL PRIMARY KEY,
    error_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    error_level VARCHAR(20) NOT NULL, -- ERROR, WARNING, INFO, DEBUG
    error_category VARCHAR(50) NOT NULL, -- INGESTION, MODELING, INFERENCE, SYSTEM
    error_source VARCHAR(100) NOT NULL, -- retrosheet, mlb, statcast, espn, etc.
    error_code VARCHAR(50),
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    context_data JSONB, -- Additional context like command parameters, data size, etc.
    user_id VARCHAR(100),
    command_name VARCHAR(100),
    function_name VARCHAR(100),
    file_path VARCHAR(500),
    line_number INTEGER,
    column_name VARCHAR(100),
    table_name VARCHAR(100),
    sql_query TEXT,
    execution_time_ms INTEGER,
    memory_usage_mb FLOAT,
    cpu_usage_percent FLOAT,
    affected_rows INTEGER,
    recovery_attempted BOOLEAN DEFAULT FALSE,
    recovery_successful BOOLEAN,
    recovery_message TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(100),
    resolution_method VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for error query performance
CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON admin.error_logs(error_timestamp);
CREATE INDEX IF NOT EXISTS idx_error_logs_level ON admin.error_logs(error_level);
CREATE INDEX IF NOT EXISTS idx_error_logs_category ON admin.error_logs(error_category);
CREATE INDEX IF NOT EXISTS idx_error_logs_source ON admin.error_logs(error_source);
CREATE INDEX IF NOT EXISTS idx_error_logs_resolved ON admin.error_logs(resolved_at) WHERE resolved_at IS NOT NULL;

-- Pipeline runs table for tracking execution
CREATE TABLE IF NOT EXISTS admin.pipeline_runs (
    run_id BIGSERIAL PRIMARY KEY,
    command_name VARCHAR(100) NOT NULL,
    subcommand VARCHAR(100),
    parameters JSONB,
    status VARCHAR(20) NOT NULL, -- RUNNING, COMPLETED, FAILED, CANCELLED
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    rows_processed INTEGER,
    rows_inserted INTEGER,
    rows_updated INTEGER,
    rows_failed INTEGER,
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    memory_peak_mb FLOAT,
    cpu_avg_percent FLOAT,
    disk_io_mb FLOAT,
    network_io_mb FLOAT,
    success_rate FLOAT,
    performance_score FLOAT, -- 0-100 based on success rate and performance
    logs_location VARCHAR(500),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for pipeline run queries
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_command ON admin.pipeline_runs(command_name);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON admin.pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started ON admin.pipeline_runs(started_at);

-- Runtime metrics table for performance monitoring
CREATE TABLE IF NOT EXISTS admin.runtime_metrics (
    metric_id BIGSERIAL PRIMARY KEY,
    metric_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metric_type VARCHAR(50) NOT NULL, -- MODEL_INFERENCE, DATA_INGESTION, SYSTEM_HEALTH
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_unit VARCHAR(20), -- ms, mb, percent, count, etc.
    model_name VARCHAR(100),
    data_source VARCHAR(100),
    operation_name VARCHAR(100),
    batch_size INTEGER,
    throughput_per_second FLOAT,
    latency_p50_ms FLOAT,
    latency_p95_ms FLOAT,
    latency_p99_ms FLOAT,
    error_rate_percent FLOAT,
    memory_usage_mb FLOAT,
    cpu_usage_percent FLOAT,
    disk_usage_mb FLOAT,
    network_io_mb FLOAT,
    custom_tags JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for metrics queries
CREATE INDEX IF NOT EXISTS idx_runtime_metrics_timestamp ON admin.runtime_metrics(metric_timestamp);
CREATE INDEX IF NOT EXISTS idx_runtime_metrics_type ON admin.runtime_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_runtime_metrics_name ON admin.runtime_metrics(metric_name);

-- Error patterns table for common error analysis
CREATE TABLE IF NOT EXISTS admin.error_patterns (
    pattern_id BIGSERIAL PRIMARY KEY,
    pattern_name VARCHAR(100) NOT NULL,
    pattern_regex VARCHAR(500),
    error_category VARCHAR(50),
    severity VARCHAR(20), -- LOW, MEDIUM, HIGH, CRITICAL
    description TEXT,
    suggested_resolution TEXT,
    auto_resolve BOOLEAN DEFAULT FALSE,
    resolve_script TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Error resolution tracking
CREATE TABLE IF NOT EXISTS admin.error_resolutions (
    resolution_id BIGSERIAL PRIMARY KEY,
    error_id BIGINT REFERENCES admin.error_logs(error_id),
    resolution_type VARCHAR(50), -- AUTOMATIC, MANUAL, IGNORED
    resolution_method VARCHAR(100),
    resolution_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_by VARCHAR(100),
    resolution_notes TEXT,
    success BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- System health snapshots
CREATE TABLE IF NOT EXISTS admin.system_health (
    health_id BIGSERIAL PRIMARY KEY,
    health_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    component_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL, -- HEALTHY, DEGRADED, UNHEALTHY
    cpu_usage_percent FLOAT,
    memory_usage_percent FLOAT,
    disk_usage_percent FLOAT,
    network_latency_ms FLOAT,
    database_connections INTEGER,
    active_models INTEGER,
    queue_depth INTEGER,
    error_rate FLOAT,
    uptime_seconds FLOAT,
    health_score FLOAT, -- 0-100 overall health score
    alerts JSONB, -- Active alerts
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for health queries
CREATE INDEX IF NOT EXISTS idx_system_health_timestamp ON admin.system_health(health_timestamp);
CREATE INDEX IF NOT EXISTS idx_system_health_component ON admin.system_health(component_name);
CREATE INDEX IF NOT EXISTS idx_system_health_status ON admin.system_health(status);

-- Views for common queries
CREATE OR REPLACE VIEW admin.error_summary AS
SELECT 
    error_level,
    error_category,
    error_source,
    COUNT(*) as error_count,
    COUNT(DISTINCT error_code) as unique_errors,
    MIN(error_timestamp) as first_occurrence,
    MAX(error_timestamp) as last_occurrence,
    AVG(execution_time_ms) as avg_execution_time,
    SUM(CASE WHEN recovery_successful = TRUE THEN 1 ELSE 0 END) as resolved_count,
    ROUND(
        SUM(CASE WHEN recovery_successful = TRUE THEN 1 ELSE 0 END) * 100.0 / 
        COUNT(*), 2
    ) as resolution_rate_percent
FROM admin.error_logs
WHERE error_timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY error_level, error_category, error_source;

CREATE OR REPLACE VIEW admin.pipeline_performance AS
SELECT 
    command_name,
    COUNT(*) as total_runs,
    COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as successful_runs,
    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_runs,
    ROUND(
        COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) * 100.0 / 
        COUNT(*), 2
    ) as success_rate_percent,
    AVG(duration_seconds) as avg_duration_seconds,
    AVG(rows_processed) as avg_rows_processed,
    AVG(success_rate) as avg_success_rate,
    AVG(performance_score) as avg_performance_score,
    MAX(started_at) as last_run
FROM admin.pipeline_runs
WHERE started_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY command_name;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON admin.error_logs TO baseball_user;
GRANT SELECT, INSERT, UPDATE ON admin.pipeline_runs TO baseball_user;
GRANT SELECT, INSERT, UPDATE ON admin.runtime_metrics TO baseball_user;
GRANT SELECT, INSERT, UPDATE ON admin.error_patterns TO baseball_user;
GRANT SELECT, INSERT, UPDATE ON admin.error_resolutions TO baseball_user;
GRANT SELECT ON admin.error_summary TO baseball_user;
GRANT SELECT ON admin.pipeline_performance TO baseball_user;

-- Comments
COMMENT ON TABLE admin.error_logs IS 'Comprehensive error logging with stack traces and context';
COMMENT ON TABLE admin.pipeline_runs IS 'Pipeline execution tracking with performance metrics';
COMMENT ON TABLE admin.runtime_metrics IS 'Runtime metrics for monitoring and alerting';
COMMENT ON TABLE admin.error_patterns IS 'Common error patterns for automatic resolution';
COMMENT ON TABLE admin.error_resolutions IS 'Error resolution tracking';
COMMENT ON TABLE admin.system_health IS 'System health monitoring snapshots';
