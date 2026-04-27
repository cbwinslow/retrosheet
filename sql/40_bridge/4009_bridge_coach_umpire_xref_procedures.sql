-- File: sql/bridge/940_coach_umpire_xref_procedures.sql
-- Purpose: Populate coach and umpire cross-reference tables from Retrosheet
-- Author: Agent Cascade
-- Date: 2026-04-24
DROP PROCEDURE IF EXISTS bridge.populate_coach_xref();
DROP PROCEDURE IF EXISTS bridge.populate_umpire_xref();

-- ============================================================================
-- Procedure: bridge.populate_coach_xref()
-- ============================================================================
-- Description: Populates bridge.coach_xref from raw_retrosheet.coaches with
--              names from biofile_legacy (coach_id matches player_id).
-- Returns: Number of coaches populated
-- ============================================================================
CREATE OR REPLACE PROCEDURE bridge.populate_coach_xref(
    OUT coach_count INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Extract unique coaches from raw_retrosheet.coaches
    -- Join with biofile_legacy to get coach names (coach_id matches player_id)
    INSERT INTO bridge.coach_xref (retrosheet_coach_id, source_system, coach_name, confidence_score, confidence_source)
    SELECT DISTINCT 
        c.coach_id,
        'retrosheet' as source_system,
        COALESCE(b.use_name, b.full_name, b.last_name, c.coach_id) as coach_name,
        0.9 as confidence_score,
        'biofile_legacy_name_match' as confidence_source
    FROM raw_retrosheet.coaches c
    LEFT JOIN raw_retrosheet.biofile_legacy b ON c.coach_id = b.player_id
    WHERE c.coach_id IS NOT NULL
    ON CONFLICT (retrosheet_coach_id) DO UPDATE SET
        coach_name = EXCLUDED.coach_name,
        confidence_score = EXCLUDED.confidence_score,
        confidence_source = EXCLUDED.confidence_source,
        updated_at = NOW();

    GET DIAGNOSTICS coach_count = ROW_COUNT;
    RAISE NOTICE 'Populated % coaches in bridge.coach_xref with names from biofile_legacy', coach_count;
END;
$$;

-- ============================================================================
-- Procedure: bridge.populate_umpire_xref()
-- ============================================================================
-- Description: Populates bridge.umpire_xref from raw_retrosheet.season_umpires
--              with biofile_legacy cross-reference for players who became umpires.
-- Returns: Number of umpires populated
-- ============================================================================
CREATE OR REPLACE PROCEDURE bridge.populate_umpire_xref(
    OUT umpire_count INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Extract unique umpires from raw_retrosheet.season_umpires
    -- Cross-reference with biofile_legacy for players who became umpires
    -- Use DISTINCT ON to handle duplicates properly
    INSERT INTO bridge.umpire_xref (retrosheet_umpire_id, source_system, umpire_name, confidence_score, confidence_source)
    SELECT DISTINCT ON (u.umpire_id)
        u.umpire_id,
        'retrosheet' as source_system,
        COALESCE(
            CASE WHEN b.player_id IS NOT NULL THEN b.use_name || ' (former player)' END,
            u.first_name || ' ' || u.last_name
        ) as umpire_name,
        CASE WHEN b.player_id IS NOT NULL THEN 0.9 ELSE 0.7 END as confidence_score,
        CASE WHEN b.player_id IS NOT NULL THEN 'biofile_legacy_player_match' ELSE 'retrosheet_name_only' END as confidence_source
    FROM raw_retrosheet.season_umpires u
    LEFT JOIN raw_retrosheet.biofile_legacy b ON 
        (u.last_name = b.last_name OR u.last_name = b.use_name)
        AND b.umpire_debut IS NOT NULL
    WHERE u.umpire_id IS NOT NULL
    ORDER BY u.umpire_id, u.season
    ON CONFLICT (retrosheet_umpire_id) DO UPDATE SET
        umpire_name = EXCLUDED.umpire_name,
        confidence_score = EXCLUDED.confidence_score,
        confidence_source = EXCLUDED.confidence_source,
        updated_at = NOW();

    GET DIAGNOSTICS umpire_count = ROW_COUNT;
    RAISE NOTICE 'Populated % umpires in bridge.umpire_xref with biofile_legacy cross-reference', umpire_count;
END;
$$;

-- ============================================================================
-- Comments on procedures
-- ============================================================================
COMMENT ON PROCEDURE bridge.populate_coach_xref () IS
'Populate bridge.coach_xref from raw_retrosheet.coaches with names from biofile_legacy.';

COMMENT ON PROCEDURE bridge.populate_umpire_xref () IS
'Populate bridge.umpire_xref from raw_retrosheet.season_umpires with biofile_legacy cross-reference.';

-- ============================================================================
-- Grant execute permissions
-- ============================================================================
GRANT EXECUTE ON PROCEDURE bridge.populate_coach_xref() TO postgres;
GRANT EXECUTE ON PROCEDURE bridge.populate_umpire_xref() TO postgres;
