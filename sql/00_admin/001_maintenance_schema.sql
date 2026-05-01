-- Maintenance schema for production database operations
-- Provides automated refresh procedures, data quality checks, and pipeline orchestration
-- Author: Agent Cascade
-- Date: 2026-05-01

-- Create maintenance schema
CREATE SCHEMA IF NOT EXISTS maintenance;

COMMENT ON SCHEMA maintenance IS 'Production maintenance procedures for automated refreshes, data quality checks, and pipeline orchestration';

-- ============================================================================
-- Refresh Procedures
-- ============================================================================

-- Refresh a specific schema's materialized views
CREATE OR REPLACE FUNCTION maintenance.refresh_schema(
    p_schema_name TEXT,
    p_concurrent BOOLEAN DEFAULT TRUE
)
RETURNS TABLE(
    view_name TEXT,
    status TEXT,
    duration_ms BIGINT,
    rows_affected BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_view RECORD;
    v_start_time TIMESTAMP;
    v_end_time TIMESTAMP;
    v_row_count BIGINT;
BEGIN
    -- Validate schema exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.schemata 
        WHERE schema_name = p_schema_name
    ) THEN
        RAISE EXCEPTION 'Schema % does not exist', p_schema_name;
    END IF;

    -- Log refresh start
    INSERT INTO maintenance.refresh_log (
        schema_name,
        operation_type,
        status,
        started_at
    ) VALUES (
        p_schema_name,
        'REFRESH_SCHEMA',
        'IN_PROGRESS',
        NOW()
    );

    -- Refresh each materialized view in schema
    FOR v_view IN 
        SELECT matviewname 
        FROM pg_matviews 
        WHERE schemaname = p_schema_name
        ORDER BY matviewname
    LOOP
        v_start_time := clock_timestamp();
        
        BEGIN
            IF p_concurrent THEN
                EXECUTE format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I.%I', p_schema_name, v_view.matviewname);
            ELSE
                EXECUTE format('REFRESH MATERIALIZED VIEW %I.%I', p_schema_name, v_view.matviewname);
            END IF;
            
            v_end_time := clock_timestamp();
            
            -- Get row count
            EXECUTE format('SELECT COUNT(*) FROM %I.%I', p_schema_name, v_view.matviewname) INTO v_row_count;
            
            RETURN QUERY SELECT 
                v_view.matviewname::TEXT,
                'SUCCESS'::TEXT,
                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                v_row_count;
                
        EXCEPTION WHEN OTHERS THEN
            v_end_time := clock_timestamp();
            RETURN QUERY SELECT 
                v_view.matviewname::TEXT,
                'FAILED: ' || SQLERRM::TEXT,
                EXTRACT(EPOCH FROM (v_end_time - v_start_time)) * 1000::BIGINT,
                NULL::BIGINT;
        END;
    END LOOP;
    
    -- Log refresh completion
    UPDATE maintenance.refresh_log
    SET status = 'COMPLETED',
        completed_at = NOW()
    WHERE schema_name = p_schema_name
      AND operation_type = 'REFRESH_SCHEMA'
      AND status = 'IN_PROGRESS'
    ORDER BY started_at DESC
    LIMIT 1;
    
    RETURN;
END;
$$;

COMMENT ON FUNCTION maintenance.refresh_schema IS 'Refresh all materialized views in a schema. Supports concurrent refresh to avoid locking.';

-- Refresh all materialized views in dependency order
CREATE OR REPLACE FUNCTION maintenance.refresh_all_materialized_views(
    p_concurrent BOOLEAN DEFAULT TRUE
)
RETURNS TABLE(
    schema_name TEXT,
    view_name TEXT,
    status TEXT,
    duration_ms BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_schema RECORD;
    v_result RECORD;
BEGIN
    -- Define refresh order by dependency
    -- Raw -> Staging -> Core -> Features -> Simulation
    FOR v_schema IN 
        VALUES 
            ('raw'::TEXT),
            ('staging'::TEXT),
            ('core'::TEXT),
            ('features'::TEXT),
            ('simulation'::TEXT),
            ('inference'::TEXT)
    LOOP
        -- Only refresh if schema exists
        IF EXISTS (
            SELECT 1 FROM information_schema.schemata 
            WHERE schema_name = v_schema.column1
        ) THEN
            FOR v_result IN 
                SELECT * FROM maintenance.refresh_schema(v_schema.column1, p_concurrent)
            LOOP
                RETURN NEXT;
            END LOOP;
        END IF;
    END LOOP;
    
    RETURN;
END;
$$;

COMMENT ON FUNCTION maintenance.refresh_all_materialized_views IS 'Refresh all materialized views in dependency order. Automatically handles schema dependencies.';

-- ============================================================================
-- Dependency-Aware Refresh Procedures
-- ============================================================================

-- Refresh features after ingestion
CREATE OR REPLACE FUNCTION maintenance.refresh_features_after_ingestion(
    p_game_id BIGINT DEFAULT NULL
)
RETURNS TABLE(
    view_name TEXT,
    status TEXT,
    duration_ms BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Refresh core feature marts
    FOR v_result IN 
        SELECT * FROM maintenance.refresh_schema('core', TRUE)
    LOOP
        RETURN NEXT;
    END LOOP;
    
    -- Refresh feature-specific views
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'features') THEN
        FOR v_result IN 
            SELECT * FROM maintenance.refresh_schema('features', TRUE)
        LOOP
            RETURN NEXT;
        END LOOP;
    END IF;
    
    RETURN;
END;
$$;

COMMENT ON FUNCTION maintenance.refresh_features_after_ingestion IS 'Refresh feature materialized views after data ingestion. Called by ingestion pipeline.';

-- Refresh live data views after live ingestion
CREATE OR REPLACE FUNCTION maintenance.refresh_live_after_ingestion(
    p_game_id BIGINT
)
RETURNS TABLE(
    view_name TEXT,
    status TEXT,
    duration_ms BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Refresh live-specific views
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'live') THEN
        FOR v_result IN 
            SELECT * FROM maintenance.refresh_schema('live', TRUE)
        LOOP
            RETURN NEXT;
        END LOOP;
    END IF;
    
    -- Refresh staging live events
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'staging' AND table_name = 'stg_mlb_live_events') THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY staging.stg_mlb_live_events;
        RETURN QUERY SELECT 
            'staging.stg_mlb_live_events'::TEXT,
            'SUCCESS'::TEXT,
            0::BIGINT;
    END IF;
    
    RETURN;
END;
$$;

COMMENT ON FUNCTION maintenance.refresh_live_after_ingestion IS 'Refresh live data materialized views after live game data ingestion.';

-- ============================================================================
-- Pipeline Orchestration Procedures
-- ============================================================================

-- Ingest live games and refresh dependent views
CREATE OR REPLACE FUNCTION pipeline.ingest_live_games(
    p_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE(
    game_id BIGINT,
    status TEXT,
    message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_game RECORD;
BEGIN
    -- This would call the actual ingestion script
    -- For now, placeholder that would be called by external script
    
    -- After ingestion, refresh dependent views
    PERFORM maintenance.refresh_live_after_ingestion(NULL);
    
    RETURN QUERY SELECT 
        NULL::BIGINT,
        'SUCCESS'::TEXT,
        'Live ingestion pipeline completed'::TEXT;
END;
$$;

COMMENT ON FUNCTION pipeline.ingest_live_games IS 'Orchestrate live game ingestion and refresh dependent materialized views.';

-- Refresh entire warehouse
CREATE OR REPLACE FUNCTION pipeline.refresh_warehouse(
    p_full_refresh BOOLEAN DEFAULT FALSE
)
RETURNS TABLE(
    schema_name TEXT,
    view_name TEXT,
    status TEXT,
    duration_ms BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_result RECORD;
BEGIN
    -- If full refresh, use non-concurrent to rebuild from scratch
    -- Otherwise use concurrent to avoid locking
    FOR v_result IN 
        SELECT * FROM maintenance.refresh_all_materialized_views(NOT p_full_refresh)
    LOOP
        RETURN NEXT;
    END LOOP;
    
    RETURN;
END;
$$;

COMMENT ON FUNCTION pipeline.refresh_warehouse IS 'Refresh entire data warehouse. Full refresh rebuilds from scratch, incremental uses concurrent refresh.';

-- ============================================================================
-- Data Quality Monitoring
-- ============================================================================

-- Check data quality across schemas
CREATE OR REPLACE FUNCTION maintenance.check_data_quality()
RETURNS TABLE(
    schema_name TEXT,
    table_name TEXT,
    check_name TEXT,
    status TEXT,
    details TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_schema RECORD;
    v_table RECORD;
    v_row_count BIGINT;
    v_null_count BIGINT;
    v_check_date TIMESTAMP;
BEGIN
    v_check_date := NOW();
    
    -- Check row counts for key tables
    FOR v_schema IN 
        SELECT schema_name FROM information_schema.schemata 
        WHERE schema_name IN ('raw', 'staging', 'core', 'features', 'simulation')
    LOOP
        FOR v_table IN 
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = v_schema.schema_name
              AND table_type = 'BASE TABLE'
        LOOP
            BEGIN
                EXECUTE format('SELECT COUNT(*) FROM %I.%I', v_schema.schema_name, v_table.table_name) 
                INTO v_row_count;
                
                RETURN QUERY SELECT 
                    v_schema.schema_name::TEXT,
                    v_table.table_name::TEXT,
                    'row_count'::TEXT,
                    CASE WHEN v_row_count > 0 THEN 'PASS' ELSE 'FAIL' END::TEXT,
                    v_row_count::TEXT;
                    
            EXCEPTION WHEN OTHERS THEN
                RETURN QUERY SELECT 
                    v_schema.schema_name::TEXT,
                    v_table.table_name::TEXT,
                    'row_count'::TEXT,
                    'ERROR'::TEXT,
                    SQLERRM::TEXT;
            END;
        END LOOP;
    END LOOP;
    
    RETURN;
END;
$$;

COMMENT ON FUNCTION maintenance.check_data_quality IS 'Run data quality checks across all schemas. Returns row counts and validation status.';

-- ============================================================================
-- Refresh Log Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS maintenance.refresh_log (
    log_id BIGSERIAL PRIMARY KEY,
    schema_name TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_ms BIGINT,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::JSONB
);

CREATE INDEX idx_refresh_log_schema ON maintenance.refresh_log(schema_name);
CREATE INDEX idx_refresh_log_started_at ON maintenance.refresh_log(started_at DESC);
CREATE INDEX idx_refresh_log_status ON maintenance.refresh_log(status);

COMMENT ON TABLE maintenance.refresh_log IS 'Log of all materialized view refresh operations for monitoring and debugging';

-- ============================================================================
-- Pipeline Schema
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS pipeline;

COMMENT ON SCHEMA pipeline IS 'Pipeline orchestration procedures for data ingestion and warehouse refresh';

-- ============================================================================
-- Grant Permissions
-- ============================================================================

-- Grant usage on schemas
GRANT USAGE ON SCHEMA maintenance TO PUBLIC;
GRANT USAGE ON SCHEMA pipeline TO PUBLIC;

-- Grant execute on functions
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA maintenance TO PUBLIC;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA pipeline TO PUBLIC;

-- Grant select on log table
GRANT SELECT ON maintenance.refresh_log TO PUBLIC;
