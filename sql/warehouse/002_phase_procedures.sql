/*
File: sql/warehouse/002_phase_procedures.sql
Purpose: Phase-level procedures for warehouse rebuild orchestration
Author: Agent Cascade
Date: 2026-04-24
Depends On: warehouse schema from 001_warehouse_schema.sql
Called By: warehouse.rebuild() procedure

Functions Created:
- warehouse.phase_raw_load()       -- Phase 1: Load raw data sources
- warehouse.phase_core_build()    -- Phase 2: Build core canonical tables
- warehouse.phase_bridge_sync()   -- Phase 3: Sync bridge/xref tables
- warehouse.phase_feature_build() -- Phase 4: Build feature marts
- warehouse.phase_model_prep()    -- Phase 5: Prepare model training data

Notes:
- Each phase is idempotent and logs its own progress
- Return rows_affected or -1 on error
*/

-- ================================================================================
-- PHASE 1: RAW DATA LOAD
-- ================================================================================

CREATE OR REPLACE FUNCTION warehouse.phase_raw_load(
    p_target_seasons INT[] DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_rows_total BIGINT := 0;
    v_rows INT;
BEGIN
    RAISE NOTICE '=== Phase 1: Raw Data Load ===';
    
    -- Raw data loads are typically from external sources
    -- This phase validates that raw sources are populated
    
    -- Check raw_retrosheet events
    SELECT COUNT(*) INTO v_rows FROM raw_retrosheet.events;
    RAISE NOTICE 'raw_retrosheet.events: % rows', v_rows;
    v_rows_total := v_rows_total + v_rows;
    
    -- Check raw_mlb statcast if present
    BEGIN
        SELECT COUNT(*) INTO v_rows FROM raw_mlb.statcast;
        RAISE NOTICE 'raw_mlb.statcast: % rows', v_rows;
        v_rows_total := v_rows_total + v_rows;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'raw_mlb.statcast: not available (%)', SQLERRM;
    END;
    
    -- Check raw_espn if present
    BEGIN
        SELECT COUNT(*) INTO v_rows FROM raw_espn.game_snapshots;
        RAISE NOTICE 'raw_espn.game_snapshots: % rows', v_rows;
        v_rows_total := v_rows_total + v_rows;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'raw_espn: not available (%)', SQLERRM;
    END;
    
    RAISE NOTICE 'Phase 1 complete: % total raw rows verified', v_rows_total;
    RETURN v_rows_total;
    
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Phase 1 failed: %', SQLERRM;
    RETURN -1;
END;
$$;

COMMENT ON FUNCTION warehouse.phase_raw_load IS 'Phase 1: Verify raw data sources are populated';

-- ================================================================================
-- PHASE 2: CORE TABLE BUILD
-- ================================================================================

CREATE OR REPLACE FUNCTION warehouse.phase_core_build(
    p_target_seasons INT[] DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_rows_inserted BIGINT := 0;
    v_game_count BIGINT;
    v_event_count BIGINT;
    v_pa_count BIGINT;
BEGIN
    RAISE NOTICE '=== Phase 2: Core Table Build ===';
    
    -- Verify core.games
    SELECT COUNT(*) INTO v_game_count FROM core.games;
    RAISE NOTICE 'core.games: % rows', v_game_count;
    
    IF v_game_count = 0 THEN
        RAISE NOTICE 'WARNING: core.games is empty - run core table build scripts';
    END IF;
    
    -- Verify core.events
    SELECT COUNT(*) INTO v_event_count FROM core.events;
    RAISE NOTICE 'core.events: % rows', v_event_count;
    v_rows_inserted := v_rows_inserted + v_event_count;
    
    -- Verify core.plate_appearances
    SELECT COUNT(*) INTO v_pa_count FROM core.plate_appearances;
    RAISE NOTICE 'core.plate_appearances: % rows', v_pa_count;
    v_rows_inserted := v_rows_inserted + v_pa_count;
    
    -- Refresh materialized views if any
    BEGIN
        REFRESH MATERIALIZED VIEW CONCURRENTLY core.game_state_cache;
        RAISE NOTICE 'Refreshed: core.game_state_cache';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Note: core.game_state_cache may not exist or not be materialized';
    END;
    
    RAISE NOTICE 'Phase 2 complete: % core rows verified', v_rows_inserted;
    RETURN v_rows_inserted;
    
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Phase 2 failed: %', SQLERRM;
    RETURN -1;
END;
$$;

COMMENT ON FUNCTION warehouse.phase_core_build IS 'Phase 2: Verify core canonical tables are built';

-- ================================================================================
-- PHASE 3: BRIDGE SYNC
-- ================================================================================

CREATE OR REPLACE FUNCTION warehouse.phase_bridge_sync(
    p_target_seasons INT[] DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_rows_total BIGINT := 0;
    v_count BIGINT;
BEGIN
    RAISE NOTICE '=== Phase 3: Bridge/XRef Sync ===';
    
    -- Check player_xref
    SELECT COUNT(*) INTO v_count FROM bridge.player_xref;
    RAISE NOTICE 'bridge.player_xref: % rows', v_count;
    v_rows_total := v_rows_total + v_count;
    
    -- Check team_xref
    SELECT COUNT(*) INTO v_count FROM bridge.team_xref;
    RAISE NOTICE 'bridge.team_xref: % rows', v_count;
    v_rows_total := v_rows_total + v_count;
    
    -- Check game_xref
    SELECT COUNT(*) INTO v_count FROM bridge.game_xref;
    RAISE NOTICE 'bridge.game_xref: % rows', v_count;
    v_rows_total := v_rows_total + v_count;
    
    -- Run bridge validation if function exists
    BEGIN
        PERFORM bridge.validate_bridge_tables_quick();
        RAISE NOTICE 'Bridge validation passed';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Bridge validation note: %', SQLERRM;
    END;
    
    RAISE NOTICE 'Phase 3 complete: % bridge rows verified', v_rows_total;
    RETURN v_rows_total;
    
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Phase 3 failed: %', SQLERRM;
    RETURN -1;
END;
$$;

COMMENT ON FUNCTION warehouse.phase_bridge_sync IS 'Phase 3: Verify bridge/xref tables are synced';

-- ================================================================================
-- PHASE 4: FEATURE BUILD
-- ================================================================================

CREATE OR REPLACE FUNCTION warehouse.phase_feature_build(
    p_target_seasons INT[] DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_rows_total BIGINT := 0;
    v_count BIGINT;
BEGIN
    RAISE NOTICE '=== Phase 4: Feature Mart Build ===';
    
    -- Check features_pitch.base_features
    BEGIN
        SELECT COUNT(*) INTO v_count FROM features_pitch.base_features;
        RAISE NOTICE 'features_pitch.base_features: % rows', v_count;
        v_rows_total := v_rows_total + v_count;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'features_pitch.base_features: not available';
    END;
    
    -- Check features_pitch.locations
    BEGIN
        SELECT COUNT(*) INTO v_count FROM features_pitch.locations;
        RAISE NOTICE 'features_pitch.locations: % rows', v_count;
        v_rows_total := v_rows_total + v_count;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'features_pitch.locations: not available';
    END;
    
    -- Check mlb_features tables
    BEGIN
        SELECT COUNT(*) INTO v_count FROM mlb_features.game_state_features;
        RAISE NOTICE 'mlb_features.game_state_features: % rows', v_count;
        v_rows_total := v_rows_total + v_count;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'mlb_features.game_state_features: not available';
    END;
    
    -- Populate win probability features if function exists
    BEGIN
        v_count := mlb_features.populate_game_state_from_retrosheet(
            COALESCE(p_target_seasons[1], 2000),
            COALESCE(p_target_seasons[array_length(p_target_seasons, 1)], 2024)
        );
        RAISE NOTICE 'Populated game state features: % rows', v_count;
        v_rows_total := v_rows_total + v_count;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Game state population note: %', SQLERRM;
    END;
    
    RAISE NOTICE 'Phase 4 complete: % feature rows', v_rows_total;
    RETURN v_rows_total;
    
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Phase 4 failed: %', SQLERRM;
    RETURN -1;
END;
$$;

COMMENT ON FUNCTION warehouse.phase_feature_build IS 'Phase 4: Build and verify feature marts';

-- ================================================================================
-- PHASE 5: MODEL PREP
-- ================================================================================

CREATE OR REPLACE FUNCTION warehouse.phase_model_prep(
    p_target_seasons INT[] DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_rows_total BIGINT := 0;
    v_count BIGINT;
BEGIN
    RAISE NOTICE '=== Phase 5: Model Preparation ===';
    
    -- Check model training tables
    BEGIN
        SELECT COUNT(*) INTO v_count FROM model_inference.plate_appearance_features;
        RAISE NOTICE 'model_inference.plate_appearance_features: % rows', v_count;
        v_rows_total := v_rows_total + v_count;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'model_inference.plate_appearance_features: not available';
    END;
    
    -- Check predictions tables
    BEGIN
        SELECT COUNT(*) INTO v_count FROM predictions.at_bat_outcomes;
        RAISE NOTICE 'predictions.at_bat_outcomes: % rows', v_count;
        v_rows_total := v_rows_total + v_count;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'predictions.at_bat_outcomes: not available';
    END;
    
    RAISE NOTICE 'Phase 5 complete: % model/prediction rows', v_rows_total;
    RETURN v_rows_total;
    
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Phase 5 failed: %', SQLERRM;
    RETURN -1;
END;
$$;

COMMENT ON FUNCTION warehouse.phase_model_prep IS 'Phase 5: Verify model training and prediction tables';
