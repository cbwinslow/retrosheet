/*
File: sql/warehouse/003_rebuild_orchestrator.sql
Purpose: Main warehouse rebuild orchestration procedure
Author: Agent Cascade
Date: 2026-04-24
Depends On: warehouse schema (001), phase procedures (002)
Called By: scripts/rebuild_warehouse.sh, manual invocation via psql

Procedure Created:
- warehouse.rebuild(run_mode, target_seasons) - Main entry point

Return Codes:
  0 = success
  1 = invalid input
  2 = phase 1 (raw) failed
  3 = phase 2 (core) failed
  4 = phase 3 (bridge) failed
  5 = phase 4 (features) failed
  6 = phase 5 (model_prep) failed

Notes:
- Each phase commits independently (resumable)
- Failed phases can be retried with run_mode='resume'
- All operations are logged to warehouse.rebuild_log
*/

-- ================================================================================
-- MAIN REBUILD ORCHESTRATOR
-- ================================================================================

CREATE OR REPLACE FUNCTION warehouse.rebuild(
    p_run_mode VARCHAR(20) DEFAULT 'full',
    p_target_seasons INT[] DEFAULT NULL
)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    v_run_id BIGINT;
    v_log_id BIGINT;
    v_phase_order INT := 0;
    v_start_phase INT := 0;
    v_rows BIGINT;
    v_return_code INT := 0;
    v_phase_list TEXT[] := ARRAY['raw_load', 'core_build', 'bridge_sync', 'feature_build', 'model_prep'];
    v_current_phase TEXT;
BEGIN
    -- Validate input
    IF p_run_mode NOT IN ('full', 'resume', 'quick') THEN
        RAISE EXCEPTION 'Invalid run_mode: %. Must be full, resume, or quick', p_run_mode;
    END IF;
    
    -- Create run record
    INSERT INTO warehouse.rebuild_runs (run_mode, target_seasons, status, run_metadata)
    VALUES (p_run_mode, p_target_seasons, 'running', 
            jsonb_build_object('server_version', version(), 'database', current_database()))
    RETURNING run_id INTO v_run_id;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'WAREHOUSE REBUILD STARTED';
    RAISE NOTICE 'Run ID: %, Mode: %, Target Seasons: %', v_run_id, p_run_mode, 
        COALESCE(p_target_seasons::TEXT, 'ALL');
    RAISE NOTICE '========================================';
    
    -- Determine starting phase for resume mode
    IF p_run_mode = 'resume' THEN
        v_start_phase := warehouse.get_last_successful_phase('resume');
        RAISE NOTICE 'Resume mode: Starting from phase %', v_start_phase + 1;
    END IF;
    
    -- Skip expensive phases in quick mode (skip feature build and model prep)
    IF p_run_mode = 'quick' THEN
        v_phase_list := ARRAY['raw_load', 'core_build', 'bridge_sync'];
        RAISE NOTICE 'Quick mode: Only running first 3 phases';
    END IF;
    
    -- ========================================================================
    -- PHASE 1: RAW DATA LOAD
    -- ========================================================================
    v_current_phase := 'raw_load';
    v_phase_order := 1;
    
    IF v_phase_order > v_start_phase THEN
        v_log_id := warehouse.log_phase_start(v_run_id, v_current_phase, v_phase_order,
            jsonb_build_object('target_seasons', p_target_seasons));
        
        BEGIN
            v_rows := warehouse.phase_raw_load(p_target_seasons);
            
            IF v_rows < 0 THEN
                warehouse.log_phase_end(v_log_id, 'failed', NULL, 'Phase returned error code');
                v_return_code := 2;
            ELSE
                warehouse.log_phase_end(v_log_id, 'completed', v_rows);
            END IF;
            
        EXCEPTION WHEN OTHERS THEN
            warehouse.log_phase_end(v_log_id, 'failed', NULL, SQLERRM);
            v_return_code := 2;
        END;
        
        IF v_return_code != 0 THEN
            UPDATE warehouse.rebuild_runs 
            SET status = 'failed', completed_at = NOW(), error_message = 'Phase 1 failed'
            WHERE run_id = v_run_id;
            RETURN v_return_code;
        END IF;
    ELSE
        RAISE NOTICE 'Skipping phase 1 (already completed in resumed run)';
    END IF;
    
    -- ========================================================================
    -- PHASE 2: CORE TABLE BUILD
    -- ========================================================================
    v_current_phase := 'core_build';
    v_phase_order := 2;
    
    IF v_phase_order > v_start_phase AND v_return_code = 0 THEN
        v_log_id := warehouse.log_phase_start(v_run_id, v_current_phase, v_phase_order);
        
        BEGIN
            v_rows := warehouse.phase_core_build(p_target_seasons);
            
            IF v_rows < 0 THEN
                warehouse.log_phase_end(v_log_id, 'failed', NULL, 'Phase returned error code');
                v_return_code := 3;
            ELSE
                warehouse.log_phase_end(v_log_id, 'completed', v_rows);
            END IF;
            
        EXCEPTION WHEN OTHERS THEN
            warehouse.log_phase_end(v_log_id, 'failed', NULL, SQLERRM);
            v_return_code := 3;
        END;
        
        IF v_return_code != 0 THEN
            UPDATE warehouse.rebuild_runs 
            SET status = 'failed', completed_at = NOW(), error_message = 'Phase 2 failed'
            WHERE run_id = v_run_id;
            RETURN v_return_code;
        END IF;
    END IF;
    
    -- ========================================================================
    -- PHASE 3: BRIDGE SYNC
    -- ========================================================================
    v_current_phase := 'bridge_sync';
    v_phase_order := 3;
    
    IF v_phase_order > v_start_phase AND v_return_code = 0 THEN
        v_log_id := warehouse.log_phase_start(v_run_id, v_current_phase, v_phase_order);
        
        BEGIN
            v_rows := warehouse.phase_bridge_sync(p_target_seasons);
            
            IF v_rows < 0 THEN
                warehouse.log_phase_end(v_log_id, 'failed', NULL, 'Phase returned error code');
                v_return_code := 4;
            ELSE
                warehouse.log_phase_end(v_log_id, 'completed', v_rows);
            END IF;
            
        EXCEPTION WHEN OTHERS THEN
            warehouse.log_phase_end(v_log_id, 'failed', NULL, SQLERRM);
            v_return_code := 4;
        END;
        
        IF v_return_code != 0 THEN
            UPDATE warehouse.rebuild_runs 
            SET status = 'failed', completed_at = NOW(), error_message = 'Phase 3 failed'
            WHERE run_id = v_run_id;
            RETURN v_return_code;
        END IF;
    END IF;
    
    -- ========================================================================
    -- PHASE 4: FEATURE BUILD
    -- ========================================================================
    v_current_phase := 'feature_build';
    v_phase_order := 4;
    
    IF v_phase_order > v_start_phase AND v_return_code = 0 THEN
        v_log_id := warehouse.log_phase_start(v_run_id, v_current_phase, v_phase_order);
        
        BEGIN
            v_rows := warehouse.phase_feature_build(p_target_seasons);
            
            IF v_rows < 0 THEN
                warehouse.log_phase_end(v_log_id, 'failed', NULL, 'Phase returned error code');
                v_return_code := 5;
            ELSE
                warehouse.log_phase_end(v_log_id, 'completed', v_rows);
            END IF;
            
        EXCEPTION WHEN OTHERS THEN
            warehouse.log_phase_end(v_log_id, 'failed', NULL, SQLERRM);
            v_return_code := 5;
        END;
        
        IF v_return_code != 0 THEN
            UPDATE warehouse.rebuild_runs 
            SET status = 'failed', completed_at = NOW(), error_message = 'Phase 4 failed'
            WHERE run_id = v_run_id;
            RETURN v_return_code;
        END IF;
    END IF;
    
    -- ========================================================================
    -- PHASE 5: MODEL PREP
    -- ========================================================================
    v_current_phase := 'model_prep';
    v_phase_order := 5;
    
    IF v_phase_order > v_start_phase AND v_return_code = 0 THEN
        v_log_id := warehouse.log_phase_start(v_run_id, v_current_phase, v_phase_order);
        
        BEGIN
            v_rows := warehouse.phase_model_prep(p_target_seasons);
            
            IF v_rows < 0 THEN
                warehouse.log_phase_end(v_log_id, 'failed', NULL, 'Phase returned error code');
                v_return_code := 6;
            ELSE
                warehouse.log_phase_end(v_log_id, 'completed', v_rows);
            END IF;
            
        EXCEPTION WHEN OTHERS THEN
            warehouse.log_phase_end(v_log_id, 'failed', NULL, SQLERRM);
            v_return_code := 6;
        END;
        
        IF v_return_code != 0 THEN
            UPDATE warehouse.rebuild_runs 
            SET status = 'failed', completed_at = NOW(), error_message = 'Phase 5 failed'
            WHERE run_id = v_run_id;
            RETURN v_return_code;
        END IF;
    END IF;
    
    -- ========================================================================
    -- COMPLETION
    -- ========================================================================
    UPDATE warehouse.rebuild_runs 
    SET status = 'completed', completed_at = NOW()
    WHERE run_id = v_run_id;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'WAREHOUSE REBUILD COMPLETED SUCCESSFULLY';
    RAISE NOTICE 'Run ID: %', v_run_id;
    RAISE NOTICE '========================================';
    
    RETURN 0;
    
EXCEPTION WHEN OTHERS THEN
    -- Catch-all for unexpected errors
    UPDATE warehouse.rebuild_runs 
    SET status = 'failed', 
        completed_at = NOW(), 
        error_message = SQLERRM
    WHERE run_id = v_run_id;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'WAREHOUSE REBUILD FAILED';
    RAISE NOTICE 'Error: %', SQLERRM;
    RAISE NOTICE '========================================';
    
    RETURN 99;
END;
$$;

COMMENT ON FUNCTION warehouse.rebuild IS 'Main warehouse rebuild orchestration procedure. Usage: SELECT warehouse.rebuild(''full''); or SELECT warehouse.rebuild(''quick'', ARRAY[2024, 2025]);';

-- ================================================================================
-- UTILITY VIEW: Recent Rebuild Status
-- ================================================================================

CREATE OR REPLACE VIEW warehouse.rebuild_status AS
SELECT 
    r.run_id,
    r.run_mode,
    r.status,
    r.started_at,
    r.completed_at,
    CASE 
        WHEN r.completed_at IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (r.completed_at - r.started_at))::INT 
        ELSE NULL 
    END AS duration_seconds,
    r.error_message,
    r.target_seasons,
    COUNT(l.log_id) FILTER (WHERE l.status = 'completed') AS phases_completed,
    COUNT(l.log_id) FILTER (WHERE l.status = 'failed') AS phases_failed,
    SUM(l.rows_affected) AS total_rows_affected
FROM warehouse.rebuild_runs r
LEFT JOIN warehouse.rebuild_log l ON r.run_id = l.run_id
GROUP BY r.run_id, r.run_mode, r.status, r.started_at, r.completed_at, r.error_message, r.target_seasons
ORDER BY r.run_id DESC;

COMMENT ON VIEW warehouse.rebuild_status IS 'Summary view of recent rebuild runs with phase counts';
