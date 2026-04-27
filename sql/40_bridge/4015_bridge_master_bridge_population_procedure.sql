-- File: sql/bridge/999_master_bridge_population_procedure.sql
-- Purpose: Master procedure to populate all bridge tables in sequence
-- Author: Agent Cascade
-- Date: 2026-04-24
DROP PROCEDURE IF EXISTS bridge.populate_all_bridge_tables();

-- ============================================================================
-- Procedure: bridge.populate_all_bridge_tables()
-- ============================================================================
-- Description: Master orchestrator that calls all bridge table population
--              procedures in the correct dependency order.
--              Order:
--                1. Season-aware team_xref (establishes team mappings)
--                2. Park_xref (establishes park mappings)
--                3. Game_xref (depends on team_xref)
--                4. Coach_xref (independent)
--                5. Umpire_xref (independent)
--                6. Player_xref (requires external data download first)
-- Parameters:
--   include_player_xref: Whether to include player_xref (downloads Chadwick data)
-- Returns: Summary of all operations
-- ============================================================================
CREATE OR REPLACE PROCEDURE bridge.populate_all_bridge_tables(
    include_player_xref BOOLEAN DEFAULT TRUE
)
LANGUAGE plpgsql
AS $$
DECLARE
    game_xref_count INTEGER;
    team_xref_count INTEGER;
    coach_xref_count INTEGER;
    umpire_xref_count INTEGER;
    park_xref_count INTEGER;
    player_xref_count INTEGER := 0;
    start_time TIMESTAMP;
    end_time TIMESTAMP;
BEGIN
    start_time := NOW();
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Starting Bridge Table Population';
    RAISE NOTICE '========================================';
    
    -- Step 1: Populate season-aware team_xref
    RAISE NOTICE '';
    RAISE NOTICE '[1/6] Populating season-aware team_xref...';
    CALL bridge.populate_season_aware_team_xref(team_xref_count);
    RAISE NOTICE '  Teams updated: %', team_xref_count;
    
    -- Step 2: Populate park_xref
    RAISE NOTICE '';
    RAISE NOTICE '[2/6] Populating park_xref...';
    CALL bridge.populate_park_xref(park_xref_count);
    RAISE NOTICE '  Parks updated: %', park_xref_count;
    
    -- Step 3: Populate game_xref (depends on team_xref)
    RAISE NOTICE '';
    RAISE NOTICE '[3/6] Populating game_xref...';
    CALL bridge.populate_game_xref(game_xref_count);
    RAISE NOTICE '  Games matched: %', game_xref_count;
    
    -- Step 4: Populate coach_xref
    RAISE NOTICE '';
    RAISE NOTICE '[4/6] Populating coach_xref...';
    CALL bridge.populate_coach_xref(coach_xref_count);
    RAISE NOTICE '  Coaches populated: %', coach_xref_count;
    
    -- Step 5: Populate umpire_xref
    RAISE NOTICE '';
    RAISE NOTICE '[5/6] Populating umpire_xref...';
    CALL bridge.populate_umpire_xref(umpire_xref_count);
    RAISE NOTICE '  Umpires populated: %', umpire_xref_count;
    
    -- Step 6: Populate player_xref (optional, downloads Chadwick data via SQL)
    IF include_player_xref THEN
        RAISE NOTICE '';
        RAISE NOTICE '[6/6] Populating player_xref from Chadwick Bureau Register...';
        CALL bridge.populate_player_xref_full();
        -- Get count after population
        SELECT COUNT(*) INTO player_xref_count FROM bridge.player_xref;
        RAISE NOTICE '  Players inserted: %', player_xref_count;
    ELSE
        RAISE NOTICE '';
        RAISE NOTICE '[6/6] Skipping player_xref (downloads Chadwick data)';
        RAISE NOTICE '      Call bridge.populate_player_xref_full() separately if needed';
    END IF;
    
    end_time := NOW();
    
    -- Print summary
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Bridge Table Population Summary';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Season-aware team_xref: %', team_xref_count;
    RAISE NOTICE 'Park_xref: %', park_xref_count;
    RAISE NOTICE 'Game_xref: %', game_xref_count;
    RAISE NOTICE 'Coach_xref: %', coach_xref_count;
    RAISE NOTICE 'Umpire_xref: %', umpire_xref_count;
    IF include_player_xref THEN
        RAISE NOTICE 'Player_xref: %', player_xref_count;
    END IF;
    RAISE NOTICE 'Total time: %', end_time - start_time;
    RAISE NOTICE '========================================';
END;
$$;

-- ============================================================================
-- Comment on procedure
-- ============================================================================
COMMENT ON PROCEDURE bridge.populate_all_bridge_tables (BOOLEAN) IS
'Master orchestrator that calls all bridge table population procedures in the correct dependency order.';

-- ============================================================================
-- Grant execute permission
-- ============================================================================
GRANT EXECUTE ON PROCEDURE bridge.populate_all_bridge_tables(BOOLEAN) TO postgres;
