-- File: sql/bridge/931_lahman_bridge_population.sql
-- Purpose: Populate bridge tables using Lahman database People table for gap-filling
-- Author: Agent Cascade
-- Date: 2026-04-24
-- Depends On: raw_lahman.people, bridge.player_xref
-- Called By: Bridge population orchestration scripts

/*
Lahman Database Bridge Population
=================================

Uses Sean Lahman's Baseball Database People table to fill gaps in player_xref.
The Lahman People table contains:
  - playerid: Lahman ID (primary key)
  - retroid: Retrosheet ID
  - bbrefid: Baseball-Reference ID
  - nameFirst, nameLast: Player names
  - birth/death dates
  - biographical data

This procedure complements Chadwick Register data, particularly for players
who may have missing IDs in one source but present in the other.
*/

-- ============================================================================
-- STAGE 1: Create staging table for Lahman People data
-- ============================================================================

-- Create or recreate staging table
DROP TABLE IF EXISTS bridge._staging_lahman_people CASCADE;

CREATE TABLE bridge._staging_lahman_people (
    lahman_id TEXT PRIMARY KEY,
    retrosheet_id TEXT,
    baseball_reference_id TEXT,
    name_first TEXT,
    name_last TEXT,
    name_given TEXT,
    birth_date DATE,
    birthcountry TEXT,
    birthstate TEXT,
    birthcity TEXT,
    death_date DATE,
    weight INTEGER,
    height INTEGER,
    bats TEXT,
    throws TEXT,
    debut DATE,
    final_game DATE,
    loaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_staging_lahman_retro ON bridge._staging_lahman_people(retrosheet_id);
CREATE INDEX IF NOT EXISTS idx_staging_lahman_bbref ON bridge._staging_lahman_people(baseball_reference_id);

-- ============================================================================
-- STAGE 2: Create procedure to load Lahman data into staging
-- ============================================================================

CREATE OR REPLACE PROCEDURE bridge.load_lahman_to_staging()
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INTEGER := 0;
BEGIN
    -- Clear staging table
    TRUNCATE bridge._staging_lahman_people;
    
    -- Load from raw_lahman.people
    INSERT INTO bridge._staging_lahman_people (
        lahman_id, retrosheet_id, baseball_reference_id,
        name_first, name_last, name_given, birth_date,
        birthcountry, birthstate, birthcity, death_date,
        weight, height, bats, throws, debut, final_game, loaded_at
    )
    SELECT 
        playerid,
        retroid,
        bbrefid,
        namefirst,
        namelast,
        namegiven,
        CASE 
            WHEN birthyear IS NOT NULL 
            THEN MAKE_DATE(birthyear, COALESCE(birthmonth, 1), COALESCE(birthday, 1))
            ELSE NULL 
        END,
        birthcountry,
        birthstate,
        birthcity,
        CASE 
            WHEN deathyear IS NOT NULL 
            THEN MAKE_DATE(deathyear, COALESCE(deathmonth, 1), COALESCE(deathday, 1))
            ELSE NULL 
        END,
        weight,
        height,
        bats,
        throws,
        debut,
        finalgame,
        NOW()
    FROM raw_lahman.people;
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    
    RAISE NOTICE 'Loaded % records from raw_lahman.people to staging', v_count;
END;
$$;

-- ============================================================================
-- STAGE 3: Create procedure for gap-fill using Lahman data
-- ============================================================================

CREATE OR REPLACE PROCEDURE bridge.gap_fill_player_xref_from_lahman()
LANGUAGE plpgsql
AS $$
DECLARE
    v_new_from_lahman INTEGER := 0;
    v_retro_added INTEGER := 0;
    v_bbref_added INTEGER := 0;
    v_name_updated INTEGER := 0;
BEGIN
    RAISE NOTICE 'Starting gap-fill from Lahman People table...';
    
    -- Step 1: Insert players from Lahman who have Retrosheet IDs but aren't in player_xref
    INSERT INTO bridge.player_xref (
        retrosheet_id,
        baseball_reference_id,
        name_first,
        name_last,
        source_notes,
        updated_at,
        confidence_score,
        confidence_source
    )
    SELECT 
        l.retrosheet_id,
        l.baseball_reference_id,
        l.name_first,
        l.name_last,
        jsonb_build_object(
            'lahman_id', l.lahman_id,
            'birth_date', l.birth_date,
            'birth_country', l.birthcountry,
            'birth_state', l.birthstate,
            'birth_city', l.birthcity,
            'death_date', l.death_date,
            'weight', l.weight,
            'height', l.height,
            'bats', l.bats,
            'throws', l.throws,
            'debut', l.debut,
            'final_game', l.final_game,
            'gap_fill_source', 'Lahman People table',
            'gap_fill_date', NOW()
        ),
        NOW(),
        0.85,  -- Good confidence for Lahman
        'Sean Lahman Baseball Database'
    FROM bridge._staging_lahman_people l
    WHERE l.retrosheet_id IS NOT NULL
      AND l.retrosheet_id NOT IN (
          SELECT retrosheet_id 
          FROM bridge.player_xref 
          WHERE retrosheet_id IS NOT NULL
      );
    
    GET DIAGNOSTICS v_new_from_lahman = ROW_COUNT;
    RAISE NOTICE 'Inserted % new players from Lahman with Retrosheet IDs', v_new_from_lahman;
    
    -- Step 2: Add missing Retrosheet IDs to existing MLB players (name match)
    WITH name_matches AS (
        SELECT 
            px.player_xref_id,
            l.retrosheet_id as lahman_retro_id,
            l.name_first,
            l.name_last
        FROM bridge.player_xref px
        JOIN bridge._staging_lahman_people l
            ON px.name_first ILIKE l.name_first
            AND px.name_last ILIKE l.name_last
        WHERE px.retrosheet_id IS NULL
          AND l.retrosheet_id IS NOT NULL
          AND px.mlb_id IS NOT NULL  -- Only match if we have MLB ID
    )
    UPDATE bridge.player_xref px
    SET 
        retrosheet_id = nm.lahman_retro_id,
        source_notes = source_notes || jsonb_build_object(
            'lahman_id', (SELECT lahman_id FROM bridge._staging_lahman_people WHERE retrosheet_id = nm.lahman_retro_id),
            'retrosheet_id_added_via', 'Lahman name match',
            'retrosheet_id_added_date', NOW()
        ),
        updated_at = NOW(),
        confidence_score = 0.75,  -- Slightly lower due to name-based matching
        confidence_source = 'Lahman Database (name match)'
    FROM name_matches nm
    WHERE px.player_xref_id = nm.player_xref_id;
    
    GET DIAGNOSTICS v_retro_added = ROW_COUNT;
    RAISE NOTICE 'Added Retrosheet IDs to % players via name matching', v_retro_added;
    
    -- Step 3: Add missing Baseball-Reference IDs
    UPDATE bridge.player_xref px
    SET 
        baseball_reference_id = l.baseball_reference_id,
        source_notes = source_notes || jsonb_build_object(
            'bbref_id_added_via', 'Lahman match',
            'bbref_id_added_date', NOW()
        ),
        updated_at = NOW()
    FROM bridge._staging_lahman_people l
    WHERE px.retrosheet_id = l.retrosheet_id
      AND px.baseball_reference_id IS NULL
      AND l.baseball_reference_id IS NOT NULL;
    
    GET DIAGNOSTICS v_bbref_added = ROW_COUNT;
    RAISE NOTICE 'Added BBRef IDs to % players', v_bbref_added;
    
    -- Step 4: Update names for players with missing/blank names
    UPDATE bridge.player_xref px
    SET 
        name_first = COALESCE(NULLIF(px.name_first, ''), l.name_first),
        name_last = COALESCE(NULLIF(px.name_last, ''), l.name_last),
        updated_at = NOW()
    FROM bridge._staging_lahman_people l
    WHERE px.retrosheet_id = l.retrosheet_id
      AND (NULLIF(px.name_first, '') IS NULL OR NULLIF(px.name_last, '') IS NULL)
      AND (l.name_first IS NOT NULL OR l.name_last IS NOT NULL);
    
    GET DIAGNOSTICS v_name_updated = ROW_COUNT;
    RAISE NOTICE 'Updated names for % players', v_name_updated;
    
    -- Summary
    RAISE NOTICE 'Lahman gap-fill complete: % new players, % retro added, % bbref added, % names updated',
        v_new_from_lahman, v_retro_added, v_bbref_added, v_name_updated;
END;
$$;

COMMENT ON PROCEDURE bridge.gap_fill_player_xref_from_lahman() IS 'Fills gaps in bridge.player_xref using Lahman People data: new players, missing Retrosheet IDs, missing BBRef IDs, and missing names.';

-- ============================================================================
-- STAGE 4: Create view for Lahman vs Chadwick comparison
-- ============================================================================

CREATE OR REPLACE VIEW bridge.vw_lahman_chadwick_comparison AS
WITH lahman_summary AS (
    SELECT 
        COUNT(*) as total_lahman,
        COUNT(retrosheet_id) as lahman_with_retro,
        COUNT(baseball_reference_id) as lahman_with_bbref
    FROM bridge._staging_lahman_people
),
chadwick_summary AS (
    SELECT 
        COUNT(*) as total_chadwick,
        COUNT(key_retro) as chadwick_with_retro,
        COUNT(key_bbref) as chadwick_with_bbref
    FROM bridge._staging_chadwick_register
),
bridge_summary AS (
    SELECT 
        COUNT(*) as total_bridge,
        COUNT(retrosheet_id) as bridge_with_retro,
        COUNT(mlb_id) as bridge_with_mlb,
        COUNT(baseball_reference_id) as bridge_with_bbref
    FROM bridge.player_xref
)
SELECT 
    'Total Records' as metric,
    l.total_lahman as lahman_count,
    c.total_chadwick as chadwick_count,
    b.total_bridge as bridge_count
FROM lahman_summary l, chadwick_summary c, bridge_summary b
UNION ALL
SELECT 
    'With Retrosheet ID',
    l.lahman_with_retro,
    c.chadwick_with_retro,
    b.bridge_with_retro
FROM lahman_summary l, chadwick_summary c, bridge_summary b
UNION ALL
SELECT 
    'With BBRef ID',
    l.lahman_with_bbref,
    c.chadwick_with_bbref,
    b.bridge_with_bbref
FROM lahman_summary l, chadwick_summary c, bridge_summary b;

COMMENT ON VIEW bridge.vw_lahman_chadwick_comparison IS 'Compares ID coverage across Lahman, Chadwick Register, and bridge.player_xref for gap analysis.';
