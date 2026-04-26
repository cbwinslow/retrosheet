-- File: sql/bridge/960_player_xref_procedure.sql
-- Purpose: Populate player cross-reference from Chadwick Bureau Register
-- Author: Agent Cascade
-- Date: 2026-04-24
DROP PROCEDURE IF EXISTS bridge.populate_player_xref();

-- ============================================================================
-- Procedure: bridge.populate_player_xref()
-- ============================================================================
-- Description: Inserts player ID mappings into bridge.player_xref from a
--              temporary table containing parsed Chadwick Bureau Register data.
--              The temp table should be named 'chadwick_player_data' with columns:
--              retrosheet_player_id, mlb_player_id, chadwick_register_id,
--              first_name, last_name, bats, throws, baseball_reference_id
-- Returns: Number of player mappings inserted
-- ============================================================================
CREATE OR REPLACE PROCEDURE bridge.populate_player_xref(
    OUT inserted_count INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    has_canonical_schema BOOLEAN;
BEGIN
    -- Check if canonical schema exists (retrosheet_player_id vs retrosheet_id)
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'bridge' AND table_name = 'player_xref'
        AND column_name = 'retrosheet_player_id'
    ) INTO has_canonical_schema;
    
    IF has_canonical_schema THEN
        -- Canonical schema: use retrosheet_player_id, mlb_player_id, chadwick_register_id
        INSERT INTO bridge.player_xref (
            retrosheet_player_id, mlb_player_id, chadwick_register_id,
            first_name, last_name, bats, throws
        )
        SELECT 
            retrosheet_player_id,
            mlb_player_id,
            chadwick_register_id,
            first_name,
            last_name,
            bats,
            throws
        FROM temp_table.chadwick_player_data
        WHERE retrosheet_player_id IS NOT NULL
        ON CONFLICT (retrosheet_player_id) DO UPDATE
            SET mlb_player_id = EXCLUDED.mlb_player_id,
                chadwick_register_id = EXCLUDED.chadwick_register_id,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                bats = EXCLUDED.bats,
                throws = EXCLUDED.throws,
                updated_at = NOW();
    ELSE
        -- Legacy schema: use retrosheet_id, mlb_id, baseball_reference_id
        INSERT INTO bridge.player_xref (
            retrosheet_id, mlb_id, baseball_reference_id,
            name_first, name_last, source_notes, updated_at
        )
        SELECT 
            retrosheet_player_id as retrosheet_id,
            mlb_player_id as mlb_id,
            baseball_reference_id,
            first_name as name_first,
            last_name as name_last,
            jsonb_build_object(
                'chadwick_register_id', chadwick_register_id,
                'bats', bats,
                'throws', throws
            ) as source_notes,
            NOW()
        FROM temp_table.chadwick_player_data
        WHERE retrosheet_player_id IS NOT NULL
        ON CONFLICT (retrosheet_id) DO UPDATE
            SET mlb_id = EXCLUDED.mlb_id,
                baseball_reference_id = EXCLUDED.baseball_reference_id,
                name_first = EXCLUDED.name_first,
                name_last = EXCLUDED.name_last,
                source_notes = EXCLUDED.source_notes,
                updated_at = NOW();
    END IF;
    
    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RAISE NOTICE 'Total player mappings inserted: %', inserted_count;
END;
$$;

-- ============================================================================
-- Comment on procedure
-- ============================================================================
COMMENT ON PROCEDURE bridge.populate_player_xref () IS
'Populate bridge.player_xref from temp_table.chadwick_player_data containing parsed Chadwick Bureau Register data.';

-- ============================================================================
-- Grant execute permission
-- ============================================================================
GRANT EXECUTE ON PROCEDURE bridge.populate_player_xref() TO postgres;
