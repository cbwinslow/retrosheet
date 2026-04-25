/*
File: sql/features/013b_refresh_context_features_procedure.sql
Purpose: Stored procedure for refreshing context features via materialized views
Author: Agent Cascade
Date: 2026-04-25
Depends On: sql/features/013a_optimized_context_features_mv.sql
Called By: orchestration layer, pg_cron scheduled jobs, manual refresh

Strategy:
- REFRESH CONCURRENTLY allows reads during refresh
- Batched refresh via partial refresh (not implemented here but possible)
- Audit logging for tracking refresh times

Usage:
  CALL features_pitch.refresh_context_features(FALSE);  -- Full refresh
  CALL features_pitch.refresh_context_features(TRUE);   -- Concurrent refresh (allows reads)
*/

-- Create schema for procedure
CREATE SCHEMA IF NOT EXISTS features_pitch;

-- Drop existing procedure
DROP PROCEDURE IF EXISTS features_pitch.refresh_context_features(boolean);

-- Create optimized refresh procedure
CREATE OR REPLACE PROCEDURE features_pitch.refresh_context_features(
    concurrent boolean DEFAULT TRUE,
    OUT refresh_status text,
    OUT duration_seconds numeric
)
LANGUAGE plpgsql
AS $$
DECLARE
    start_time timestamp;
    step_start timestamp;
    step_name text;
BEGIN
    start_time := clock_timestamp();
    
    -- =========================================================================
    -- STEP 1: Refresh game context MV
    -- =========================================================================
    step_name := 'mv_game_context';
    step_start := clock_timestamp();
    
    IF concurrent THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY features_pitch.mv_game_context;
    ELSE
        REFRESH MATERIALIZED VIEW features_pitch.mv_game_context;
    END IF;
    
    RAISE NOTICE 'Step % completed in % seconds', 
        step_name, 
        EXTRACT(EPOCH FROM (clock_timestamp() - step_start));
    
    -- =========================================================================
    -- STEP 2: Refresh park context MV
    -- =========================================================================
    step_name := 'mv_park_context';
    step_start := clock_timestamp();
    
    IF concurrent THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY features_pitch.mv_park_context;
    ELSE
        REFRESH MATERIALIZED VIEW features_pitch.mv_park_context;
    END IF;
    
    RAISE NOTICE 'Step % completed in % seconds', 
        step_name, 
        EXTRACT(EPOCH FROM (clock_timestamp() - step_start));
    
    -- =========================================================================
    -- STEP 3: Refresh team momentum MV
    -- =========================================================================
    step_name := 'mv_team_momentum';
    step_start := clock_timestamp();
    
    IF concurrent THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY features_pitch.mv_team_momentum;
    ELSE
        REFRESH MATERIALIZED VIEW features_pitch.mv_team_momentum;
    END IF;
    
    RAISE NOTICE 'Step % completed in % seconds', 
        step_name, 
        EXTRACT(EPOCH FROM (clock_timestamp() - step_start));
    
    -- =========================================================================
    -- STEP 4: Refresh pitcher fatigue MV
    -- =========================================================================
    step_name := 'mv_pitcher_fatigue';
    step_start := clock_timestamp();
    
    IF concurrent THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY features_pitch.mv_pitcher_fatigue;
    ELSE
        REFRESH MATERIALIZED VIEW features_pitch.mv_pitcher_fatigue;
    END IF;
    
    RAISE NOTICE 'Step % completed in % seconds', 
        step_name, 
        EXTRACT(EPOCH FROM (clock_timestamp() - step_start));
    
    -- =========================================================================
    -- STEP 5: Refresh unified feature view
    -- =========================================================================
    step_name := 'mv_all_context_features';
    step_start := clock_timestamp();
    
    IF concurrent THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY features_pitch.mv_all_context_features;
    ELSE
        REFRESH MATERIALIZED VIEW features_pitch.mv_all_context_features;
    END IF;
    
    RAISE NOTICE 'Step % completed in % seconds', 
        step_name, 
        EXTRACT(EPOCH FROM (clock_timestamp() - step_start));
    
    -- =========================================================================
    -- Final status
    -- =========================================================================
    duration_seconds := EXTRACT(EPOCH FROM (clock_timestamp() - start_time));
    refresh_status := format('SUCCESS: All materialized views refreshed in %s seconds', duration_seconds);
    
    RAISE NOTICE '%', refresh_status;
    
END;
$$;

COMMENT ON PROCEDURE features_pitch.refresh_context_features(boolean) IS 
    'Refreshes all context feature materialized views. Use concurrent=TRUE for production (allows reads during refresh).';

-- ============================================================================
-- Create audit logging table for refresh tracking
-- ============================================================================

DROP TABLE IF EXISTS features_pitch.refresh_audit_log;

CREATE TABLE features_pitch.refresh_audit_log (
    log_id serial PRIMARY KEY,
    refresh_type text NOT NULL,
    started_at timestamp NOT NULL DEFAULT clock_timestamp(),
    completed_at timestamp,
    duration_seconds numeric,
    rows_affected bigint,
    status text,
    error_message text,
    concurrent_mode boolean DEFAULT FALSE
);

CREATE INDEX idx_refresh_log_type ON features_pitch.refresh_audit_log(refresh_type, started_at DESC);

COMMENT ON TABLE features_pitch.refresh_audit_log IS 
    'Audit trail for materialized view refresh operations. Query to track performance over time.';

-- ============================================================================
-- Create wrapper procedure with audit logging
-- ============================================================================

CREATE OR REPLACE PROCEDURE features_pitch.refresh_context_features_with_audit(
    concurrent boolean DEFAULT TRUE,
    OUT log_id integer,
    OUT final_status text
)
LANGUAGE plpgsql
AS $$
DECLARE
    log_record_id integer;
    start_time timestamp;
    status_msg text;
    duration numeric;
    row_count bigint;
BEGIN
    start_time := clock_timestamp();
    
    -- Insert audit record
    INSERT INTO features_pitch.refresh_audit_log (
        refresh_type, 
        started_at, 
        concurrent_mode
    ) VALUES (
        'context_features',
        start_time,
        concurrent
    ) RETURNING log_id INTO log_record_id;
    
    log_id := log_record_id;
    
    BEGIN
        -- Call main refresh procedure
        CALL features_pitch.refresh_context_features(concurrent, status_msg, duration);
        
        -- Get row count
        SELECT COUNT(*) INTO row_count FROM features_pitch.mv_all_context_features;
        
        -- Update audit record with success
        UPDATE features_pitch.refresh_audit_log
        SET 
            completed_at = clock_timestamp(),
            duration_seconds = duration,
            rows_affected = row_count,
            status = 'SUCCESS'
        WHERE log_id = log_record_id;
        
        final_status := status_msg;
        
    EXCEPTION WHEN OTHERS THEN
        -- Update audit record with failure
        UPDATE features_pitch.refresh_audit_log
        SET 
            completed_at = clock_timestamp(),
            duration_seconds = EXTRACT(EPOCH FROM (clock_timestamp() - start_time)),
            status = 'FAILED',
            error_message = SQLERRM
        WHERE log_id = log_record_id;
        
        final_status := format('FAILED: %s', SQLERRM);
        RAISE;
    END;
END;
$$;

COMMENT ON PROCEDURE features_pitch.refresh_context_features_with_audit(boolean) IS 
    'Refreshes context features with full audit logging. Use for scheduled jobs and tracking performance.';

-- ============================================================================
-- Create pg_cron scheduled job (if pg_cron is installed)
-- ============================================================================

-- Check if pg_cron is available and create scheduled refresh
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        -- Schedule daily refresh at 3 AM
        PERFORM cron.schedule(
            'refresh-context-features',
            '0 3 * * *',
            'CALL features_pitch.refresh_context_features_with_audit(TRUE)'
        );
        RAISE NOTICE 'Created pg_cron job for daily context features refresh at 3 AM';
    ELSE
        RAISE NOTICE 'pg_cron not available. Manual refresh required or add to external scheduler.';
    END IF;
END;
$$;

-- ============================================================================
-- Verification query
-- ============================================================================

SELECT 
    'Procedures Created' as status,
    'features_pitch.refresh_context_features(concurrent BOOLEAN)' as procedure_1,
    'features_pitch.refresh_context_features_with_audit(concurrent BOOLEAN)' as procedure_2,
    'features_pitch.refresh_audit_log' as audit_table;
