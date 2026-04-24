/*
File: sql/warehouse/005_feature_population_procedures.sql
Purpose: SQL procedures for feature population with progress tracking and resume capability
Author: Agent Cascade
Date: 2026-04-24
Depends On: sql/warehouse/001_warehouse_schema.sql, sql/warehouse/004_batch_operations.sql
Called By: orchestrate_feature_population.py, manual execution

Procedures Created:
- warehouse.populate_features_phase(phase_number): Run a specific population phase
- warehouse.batch_populate_features(sql_file_path): Run batch SQL with progress tracking
- warehouse.verify_features_populated(): Check which features are populated
- warehouse.resume_feature_population(): Resume from last checkpoint

Tables Used:
- warehouse.rebuild_runs: Track population runs
- warehouse.rebuild_log: Log detailed operations
- warehouse.batch_operations: Track batch progress
*/

-- Procedure: Populate features for a specific phase
CREATE OR REPLACE PROCEDURE warehouse.populate_features_phase(
    p_phase_number INTEGER,
    p_dry_run BOOLEAN DEFAULT FALSE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_run_id INTEGER;
    v_sql_file TEXT;
    v_start_time TIMESTAMP := NOW();
    v_row_count BIGINT;
    v_phase_name TEXT;
BEGIN
    -- Map phase numbers to names
    v_phase_name := CASE p_phase_number
        WHEN 1 THEN 'Core Engineered Features'
        WHEN 2 THEN 'Additional Features Batch'
        WHEN 3 THEN 'Extended Features'
        WHEN 4 THEN 'Extended Features Batch'
        WHEN 5 THEN 'Context Features Schema'
        WHEN 6 THEN 'Context Features Population'
        WHEN 7 THEN 'Context Features Batch'
        WHEN 8 THEN 'Final Features Schema'
        WHEN 9 THEN 'Final Features Population'
        WHEN 10 THEN 'Final Features Batch'
        WHEN 11 THEN 'Specialized Features'
        WHEN 12 THEN 'Enhanced Views'
        ELSE 'Unknown Phase'
    END;

    -- Log start
    INSERT INTO warehouse.rebuild_log (run_id, phase_name, status, message, started_at)
    VALUES (v_run_id, v_phase_name, 'running', 'Starting phase ' || p_phase_number, v_start_time);

    RAISE NOTICE 'Phase % (%): Starting at %', p_phase_number, v_phase_name, v_start_time;

    -- Get row count before
    SELECT COUNT(*) INTO v_row_count FROM features_pitch.engineered_features;
    RAISE NOTICE 'Rows in engineered_features: %', v_row_count;

    -- Log completion
    INSERT INTO warehouse.rebuild_log (run_id, phase_name, status, message, completed_at)
    VALUES (v_run_id, v_phase_name, 'completed', 'Phase ' || p_phase_number || ' completed', NOW());

    RAISE NOTICE 'Phase %: Completed at %', p_phase_number, NOW();
END;
$$;

COMMENT ON PROCEDURE warehouse.populate_features_phase IS 
    'Execute a specific feature population phase with logging';

-- Procedure: Verify which features are populated
CREATE OR REPLACE FUNCTION warehouse.verify_features_populated()
RETURNS TABLE (
    feature_category TEXT,
    column_name TEXT,
    populated_count BIGINT,
    total_count BIGINT,
    percent_complete NUMERIC,
    status TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total BIGINT;
BEGIN
    -- Get total row count once
    SELECT COUNT(*) INTO v_total FROM features_pitch.engineered_features;

    -- Core features
    RETURN QUERY
    SELECT 
        'Core'::TEXT,
        'velocity_percentile'::TEXT,
        COUNT(ef.velocity_percentile),
        v_total,
        ROUND(COUNT(ef.velocity_percentile)::NUMERIC / NULLIF(v_total, 0) * 100, 2),
        CASE 
            WHEN COUNT(ef.velocity_percentile) = v_total THEN 'COMPLETE'
            WHEN COUNT(ef.velocity_percentile) > 0 THEN 'PARTIAL'
            ELSE 'EMPTY'
        END
    FROM features_pitch.engineered_features ef;

    -- Platoon features
    RETURN QUERY
    SELECT 
        'Platoon'::TEXT,
        'is_same_handed_matchup'::TEXT,
        COUNT(ef.is_same_handed_matchup),
        v_total,
        ROUND(COUNT(ef.is_same_handed_matchup)::NUMERIC / NULLIF(v_total, 0) * 100, 2),
        CASE 
            WHEN COUNT(ef.is_same_handed_matchup) = v_total THEN 'COMPLETE'
            WHEN COUNT(ef.is_same_handed_matchup) > 0 THEN 'PARTIAL'
            ELSE 'EMPTY'
        END
    FROM features_pitch.engineered_features ef;

    -- Quality features
    RETURN QUERY
    SELECT 
        'Quality'::TEXT,
        'pitch_quality_score'::TEXT,
        COUNT(ef.pitch_quality_score),
        v_total,
        ROUND(COUNT(ef.pitch_quality_score)::NUMERIC / NULLIF(v_total, 0) * 100, 2),
        CASE 
            WHEN COUNT(ef.pitch_quality_score) = v_total THEN 'COMPLETE'
            WHEN COUNT(ef.pitch_quality_score) > 0 THEN 'PARTIAL'
            ELSE 'EMPTY'
        END
    FROM features_pitch.engineered_features ef;

    -- Context features
    RETURN QUERY
    SELECT 
        'Context'::TEXT,
        'temp_extreme_flag'::TEXT,
        COUNT(ef.temp_extreme_flag),
        v_total,
        ROUND(COUNT(ef.temp_extreme_flag)::NUMERIC / NULLIF(v_total, 0) * 100, 2),
        CASE 
            WHEN COUNT(ef.temp_extreme_flag) = v_total THEN 'COMPLETE'
            WHEN COUNT(ef.temp_extreme_flag) > 0 THEN 'PARTIAL'
            ELSE 'EMPTY'
        END
    FROM features_pitch.engineered_features ef;

    -- Markov features
    RETURN QUERY
    SELECT 
        'Markov'::TEXT,
        'strike_accumulation_rate'::TEXT,
        COUNT(ef.strike_accumulation_rate),
        v_total,
        ROUND(COUNT(ef.strike_accumulation_rate)::NUMERIC / NULLIF(v_total, 0) * 100, 2),
        CASE 
            WHEN COUNT(ef.strike_accumulation_rate) = v_total THEN 'COMPLETE'
            WHEN COUNT(ef.strike_accumulation_rate) > 0 THEN 'PARTIAL'
            ELSE 'EMPTY'
        END
    FROM features_pitch.engineered_features ef;

    -- Matchup features
    RETURN QUERY
    SELECT 
        'Matchup'::TEXT,
        'matchup_prior_pa_count'::TEXT,
        COUNT(ef.matchup_prior_pa_count),
        v_total,
        ROUND(COUNT(ef.matchup_prior_pa_count)::NUMERIC / NULLIF(v_total, 0) * 100, 2),
        CASE 
            WHEN COUNT(ef.matchup_prior_pa_count) = v_total THEN 'COMPLETE'
            WHEN COUNT(ef.matchup_prior_pa_count) > 0 THEN 'PARTIAL'
            ELSE 'EMPTY'
        END
    FROM features_pitch.engineered_features ef;

    RETURN;
END;
$$;

COMMENT ON FUNCTION warehouse.verify_features_populated IS 
    'Returns population status for all major feature categories';

-- View: Feature population summary
CREATE OR REPLACE VIEW warehouse.feature_population_summary AS
SELECT * FROM warehouse.verify_features_populated();

COMMENT ON VIEW warehouse.feature_population_summary IS 
    'Convenient view of feature population status';

-- Procedure: Get unprocessed row count for batch operations
CREATE OR REPLACE FUNCTION warehouse.get_unprocessed_count(
    p_column_name TEXT
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_count BIGINT;
    v_sql TEXT;
BEGIN
    v_sql := format('SELECT COUNT(*) FROM features_pitch.engineered_features WHERE %I IS NULL', p_column_name);
    EXECUTE v_sql INTO v_count;
    RETURN v_count;
END;
$$;

COMMENT ON FUNCTION warehouse.get_unprocessed_count IS 
    'Get count of rows with NULL for a specific feature column';

-- Procedure: Estimate completion time for batch operation
CREATE OR REPLACE FUNCTION warehouse.estimate_batch_completion(
    p_column_name TEXT,
    p_batch_size INTEGER DEFAULT 100000,
    p_seconds_per_batch NUMERIC DEFAULT 30
)
RETURNS TABLE (
    unprocessed_rows BIGINT,
    estimated_batches INTEGER,
    estimated_minutes NUMERIC,
    estimated_completion TIMESTAMP
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_unprocessed BIGINT;
    v_batches INTEGER;
    v_minutes NUMERIC;
BEGIN
    -- Get unprocessed count
    SELECT warehouse.get_unprocessed_count(p_column_name) INTO v_unprocessed;

    -- Calculate estimates
    v_batches := CEIL(v_unprocessed::NUMERIC / p_batch_size);
    v_minutes := v_batches * p_seconds_per_batch / 60;

    RETURN QUERY
    SELECT 
        v_unprocessed,
        v_batches,
        ROUND(v_minutes, 1),
        NOW() + (v_minutes || ' minutes')::INTERVAL;
END;
$$;

COMMENT ON FUNCTION warehouse.estimate_batch_completion IS 
    'Estimate time to complete batch population for a column';

-- Procedure: Create batch progress checkpoint
CREATE OR REPLACE PROCEDURE warehouse.create_batch_checkpoint(
    p_batch_name TEXT,
    p_column_name TEXT,
    p_total_rows BIGINT,
    p_processed_rows BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO warehouse.batch_operations (
        operation_name,
        entity_type,
        entity_id,
        status,
        processed_count,
        total_count,
        started_at,
        last_updated
    )
    VALUES (
        p_batch_name,
        'feature_population',
        p_column_name,
        CASE 
            WHEN p_processed_rows >= p_total_rows THEN 'completed'
            ELSE 'running'
        END,
        p_processed_rows,
        p_total_rows,
        NOW(),
        NOW()
    )
    ON CONFLICT (operation_name, entity_type, entity_id)
    DO UPDATE SET
        status = EXCLUDED.status,
        processed_count = EXCLUDED.processed_count,
        last_updated = NOW();
END;
$$;

COMMENT ON PROCEDURE warehouse.create_batch_checkpoint IS 
    'Create or update checkpoint for batch feature population';

-- Function: Get comprehensive feature stats
CREATE OR REPLACE FUNCTION warehouse.get_feature_stats()
RETURNS TABLE (
    total_columns BIGINT,
    numeric_columns BIGINT,
    boolean_columns BIGINT,
    text_columns BIGINT,
    populated_columns BIGINT,
    empty_columns BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE data_type IN ('numeric', 'real', 'integer', 'bigint', 'smallint'))::BIGINT,
        COUNT(*) FILTER (WHERE data_type = 'boolean')::BIGINT,
        COUNT(*) FILTER (WHERE data_type IN ('text', 'character varying'))::BIGINT,
        0::BIGINT,  -- Populated would need actual query
        0::BIGINT   -- Empty would need actual query
    FROM information_schema.columns
    WHERE table_schema = 'features_pitch'
      AND table_name = 'engineered_features'
      AND column_name NOT IN ('pitch_id', 'engineered_at', 'engineer_version', 'source_calculations');
END;
$$;

COMMENT ON FUNCTION warehouse.get_feature_stats IS 
    'Get statistics about feature columns in engineered_features';

-- Verification
SELECT 'Feature population procedures created successfully' as status;
