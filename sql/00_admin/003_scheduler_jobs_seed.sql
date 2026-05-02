/*
File: sql/00_admin/003_scheduler_jobs_seed.sql
Purpose: Seed scheduler with MLB ingestion jobs
Author: Agent Cascade
Date: 2026-05-01
Depends On: 002_scheduler_schema.sql

This creates the actual pg_cron jobs and scheduler.jobs entries
for automated MLB data ingestion.

Note: pg_cron extension must be installed first (requires superuser)
*/

-- Seed jobs into scheduler.jobs table
INSERT INTO scheduler.jobs (
    job_name,
    job_type,
    schedule,
    schedule_type,
    command,
    command_type,
    is_game_aware,
    active_during_season_only,
    timeout_seconds,
    description
) VALUES 
-- Schedule fetch (daily at 6 AM)
(
    'mlb_schedule_daily',
    'schedule_fetch',
    '0 6 * * *',
    'cron',
    'cd /app && python scripts/fetch_mlb_schedule.py --today --populate',
    'shell',
    FALSE,
    TRUE,
    120,
    'Download MLB schedule for today and next 7 days'
),
-- Live game ingestion (smart polling - controlled by get_polling_interval())
(
    'mlb_live_ingestion',
    'live_ingestion',
    '*/5 * * * *',  -- Base schedule, actual rate controlled by smart scheduler
    'smart',
    'cd /app && python scripts/data_ingestion/ingest_live_games.py --active',
    'shell',
    TRUE,
    TRUE,
    300,
    'Ingest live game data with adaptive polling (10s during games, 1hr off-season)'
),
-- Odds data fetch (every 30 min)
(
    'mlb_odds_fetch',
    'odds_fetch',
    '*/30 * * * *',
    'cron',
    'cd /app && python scripts/fetch_espn_mlb.py',
    'shell',
    TRUE,
    TRUE,
    60,
    'Fetch betting odds from ESPN API'
),
-- Materialized view refresh (hourly)
(
    'refresh_materialized_views',
    'maintenance',
    '0 * * * *',
    'cron',
    'SELECT maintenance.refresh_all_materialized_views(TRUE)',
    'sql',
    FALSE,
    FALSE,
    600,
    'Refresh all materialized views with recent data only'
),
-- Cleanup old job runs (daily at 3 AM)
(
    'cleanup_job_history',
    'maintenance',
    '0 3 * * *',
    'cron',
    'DELETE FROM scheduler.job_runs WHERE created_at < NOW() - INTERVAL ''30 days''',
    'sql',
    FALSE,
    FALSE,
    300,
    'Clean up job run history older than 30 days'
),
-- Smart polling interval updater (every 5 minutes)
(
    'update_polling_interval',
    'maintenance',
    '*/5 * * * *',
    'cron',
    'SELECT pg_notify(''scheduler'', ''check_polling'')',
    'sql',
    TRUE,
    TRUE,
    10,
    'Notification trigger for smart polling recalculation'
)
ON CONFLICT (job_name) DO UPDATE SET
    schedule = EXCLUDED.schedule,
    command = EXCLUDED.command,
    is_enabled = TRUE,
    updated_at = NOW();

-- ============================================================================
-- CREATE PG_CRON JOBS (if extension is available)
-- ============================================================================

DO $$
DECLARE
    v_job RECORD;
BEGIN
    -- Check if pg_cron is available
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        RAISE NOTICE 'pg_cron extension not available. Cron jobs not created.';
        RAISE NOTICE 'To enable: CREATE EXTENSION pg_cron;';
        RETURN;
    END IF;
    
    -- Create pg_cron jobs for each enabled scheduler job
    FOR v_job IN 
        SELECT job_name, schedule, command
        FROM scheduler.jobs
        WHERE is_enabled = TRUE
        AND command_type = 'shell'
    LOOP
        -- Unschedule existing to avoid duplicates
        BEGIN
            PERFORM cron.unschedule(v_job.job_name);
        EXCEPTION
            WHEN OTHERS THEN
                NULL;  -- Job may not exist
        END;
        
        -- Schedule new job
        BEGIN
            PERFORM cron.schedule(
                v_job.job_name,
                v_job.schedule,
                v_job.command
            );
            RAISE NOTICE 'Created cron job: %', v_job.job_name;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Failed to create job %: %', v_job.job_name, SQLERRM;
        END;
    END LOOP;
    
    -- Create SQL-based cron jobs separately (using different syntax)
    FOR v_job IN 
        SELECT job_name, schedule, command
        FROM scheduler.jobs
        WHERE is_enabled = TRUE
        AND command_type = 'sql'
    LOOP
        BEGIN
            PERFORM cron.unschedule(v_job.job_name);
        EXCEPTION
            WHEN OTHERS THEN
                NULL;
        END;
        
        BEGIN
            -- For SQL commands, wrap in anonymous block
            PERFORM cron.schedule(
                v_job.job_name,
                v_job.schedule,
                format('DO $$ BEGIN %s; END $$;', v_job.command)
            );
            RAISE NOTICE 'Created SQL cron job: %', v_job.job_name;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Failed to create SQL job %: %', v_job.job_name, SQLERRM;
        END;
    END LOOP;
END $$;

-- ============================================================================
-- FUNCTION: Initialize pg_cron jobs after extension is installed
-- ============================================================================

CREATE OR REPLACE FUNCTION scheduler.initialize_pg_cron_jobs()
RETURNS TABLE (
    job_name VARCHAR,
    status TEXT
) AS $$
DECLARE
    v_job RECORD;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        RAISE EXCEPTION 'pg_cron extension not installed';
    END IF;
    
    FOR v_job IN 
        SELECT j.job_name, j.schedule, j.command, j.command_type
        FROM scheduler.jobs j
        WHERE j.is_enabled = TRUE
    LOOP
        -- Unschedule existing
        BEGIN
            PERFORM cron.unschedule(v_job.job_name);
        EXCEPTION
            WHEN OTHERS THEN
                NULL;
        END;
        
        -- Schedule based on command type
        BEGIN
            IF v_job.command_type = 'sql' THEN
                PERFORM cron.schedule(
                    v_job.job_name,
                    v_job.schedule,
                    format('DO $$ BEGIN %s; END $$;', v_job.command)
                );
            ELSE
                PERFORM cron.schedule(
                    v_job.job_name,
                    v_job.schedule,
                    v_job.command
                );
            END IF;
            
            job_name := v_job.job_name;
            status := 'created';
            RETURN NEXT;
            
        EXCEPTION
            WHEN OTHERS THEN
                job_name := v_job.job_name;
                status := 'failed: ' || SQLERRM;
                RETURN NEXT;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION scheduler.initialize_pg_cron_jobs IS 'Create pg_cron jobs from scheduler.jobs table. Call after pg_cron extension is installed.';

-- ============================================================================
-- FUNCTION: Check and create pg_cron jobs if extension available
-- ============================================================================

CREATE OR REPLACE FUNCTION scheduler.try_initialize_scheduler()
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        SELECT jsonb_agg(
            jsonb_build_object('job', job_name, 'status', status)
        ) INTO v_result
        FROM scheduler.initialize_pg_cron_jobs();
        
        RETURN jsonb_build_object(
            'success', TRUE,
            'message', 'pg_cron jobs initialized',
            'jobs', COALESCE(v_result, '[]'::jsonb)
        );
    ELSE
        RETURN jsonb_build_object(
            'success', FALSE,
            'message', 'pg_cron extension not available',
            'hint', 'Run: CREATE EXTENSION pg_cron; (requires superuser)'
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION scheduler.try_initialize_scheduler IS 'Attempt to initialize pg_cron jobs, returns status JSON';
