-- ============================================================================
-- Bridge: Park Cross-Reference Population Procedure
-- ============================================================================
-- Purpose: Populate bridge.park_xref with MLB venue id mappings
-- Dependencies: core.mlb_api_teams, bridge.park_xref
-- Created: 2026-04-21
-- ============================================================================

-- Drop procedure if exists
DROP PROCEDURE IF EXISTS bridge.populate_park_xref();

-- ============================================================================
-- Procedure: bridge.populate_park_xref()
-- ============================================================================
-- Description: Populates bridge.park_xref with MLB venue id mappings for
--              2000-2025 venues using a static mapping table.
-- Returns: Number of parks updated
-- ============================================================================
CREATE OR REPLACE PROCEDURE bridge.populate_park_xref(
    OUT updated_count INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    venue_record RECORD;
    mapped_park_id TEXT;
    skipped_count INTEGER := 0;
    updated_count INTEGER := 0;
BEGIN
    -- Create temporary table with static MLB venue ID to Retrosheet park ID mappings
    -- These mappings prioritize stable venue ids over name-alias drift
    CREATE TEMP TABLE venue_mapping (
        mlb_venue_id INTEGER PRIMARY KEY,
        retrosheet_park_id TEXT
    ) ON COMMIT DROP;
    
    INSERT INTO venue_mapping (mlb_venue_id, retrosheet_park_id) VALUES
        (1, 'ANA01'),
        (2, 'BAL12'),
        (3, 'BOS07'),
        (4, 'CHI12'),
        (5, 'CLE08'),
        (7, 'KAN06'),
        (8, 'MIN03'),
        (9, 'NYC16'),
        (10, 'OAK01'),
        (12, 'STP01'),
        (13, 'ARL02'),
        (14, 'TOR02'),
        (15, 'PHO01'),
        (16, 'ATL02'),
        (17, 'CHI11'),
        (18, 'CIN08'),
        (19, 'DEN02'),
        (20, 'MIA01'),
        (22, 'LOS03'),
        (23, 'MIL05'),
        (24, 'MON02'),
        (25, 'NYC17'),
        (26, 'PHI12'),
        (27, 'PIT07'),
        (28, 'SAN01'),
        (30, 'STL09'),
        (31, 'PIT08'),
        (32, 'MIL06'),
        (680, 'SEA03'),
        (2392, 'HOU03'),
        (2394, 'DET05'),
        (2395, 'SFO03'),
        (2523, 'TAM02'),
        (2602, 'CIN09'),
        (2680, 'SAN02'),
        (2681, 'PHI13'),
        (2721, 'WAS10'),
        (2889, 'STL10'),
        (3289, 'NYC20'),
        (3309, 'WAS11'),
        (3312, 'MIN04'),
        (3313, 'NYC21'),
        (4169, 'MIA02'),
        (4705, 'ATL03'),
        (5325, 'ARL03');

    -- Get distinct venues from MLB API teams data
    FOR venue_record IN
        SELECT DISTINCT ON (venue_id)
            venue_id,
            venue_name,
            season
        FROM core.mlb_api_teams
        WHERE venue_id IS NOT NULL
        ORDER BY venue_id, season DESC
    LOOP
        -- Look up Retrosheet park ID from mapping table
        SELECT venue_mapping.retrosheet_park_id INTO mapped_park_id
        FROM venue_mapping
        WHERE mlb_venue_id = venue_record.venue_id;
        
        IF mapped_park_id IS NOT NULL THEN
            -- Update existing bridge.park_xref row
            UPDATE bridge.park_xref
            SET mlb_venue_id = venue_record.venue_id,
                updated_at = NOW()
            WHERE bridge.park_xref.retrosheet_park_id = mapped_park_id;
            
            IF FOUND THEN
                updated_count := updated_count + 1;
            ELSE
                skipped_count := skipped_count + 1;
                RAISE NOTICE 'Skipped venue_id % (%): missing bridge.park_xref row for %',
                    venue_record.venue_id, venue_record.venue_name, mapped_park_id;
            END IF;
        ELSE
            skipped_count := skipped_count + 1;
            RAISE NOTICE 'Skipped venue_id % (%): no canonical venue mapping',
                venue_record.venue_id, venue_record.venue_name;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'Total park mappings updated: %', updated_count;
    RAISE NOTICE 'Total park mappings skipped: %', skipped_count;
END;
$$;

-- ============================================================================
-- Comment on procedure
-- ============================================================================
COMMENT ON PROCEDURE bridge.populate_park_xref() IS 
'Populate bridge.park_xref with MLB venue id mappings using static mapping table for 2000-2025 venues.';

-- ============================================================================
-- Grant execute permission
-- ============================================================================
GRANT EXECUTE ON PROCEDURE bridge.populate_park_xref() TO postgres;
