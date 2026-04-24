-- ============================================================================
-- Bridge: Season-Aware Team Cross-Reference Population Procedure
-- ============================================================================
-- Purpose: Populate bridge.team_xref with valid_from_season and valid_to_season
-- Dependencies: core.games, bridge.team_xref
-- Created: 2026-04-21
-- ============================================================================

-- Drop procedure if exists
DROP PROCEDURE IF EXISTS bridge.populate_season_aware_team_xref();

-- ============================================================================
-- Procedure: bridge.populate_season_aware_team_xref()
-- ============================================================================
-- Description: Populates valid_from_season and valid_to_season for all teams
--              based on core.games data. Handles franchise moves by creating
--              separate entries for each franchise period.
-- Returns: Number of teams updated
-- ============================================================================
CREATE OR REPLACE PROCEDURE bridge.populate_season_aware_team_xref(
    OUT updated_count INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- First, populate basic season ranges for all teams from core.games
    UPDATE bridge.team_xref tx
    SET 
        valid_from_season = g.first_season,
        valid_to_season = CASE WHEN g.last_season >= 2025 THEN NULL ELSE g.last_season END
    FROM (
        SELECT 
            team_id,
            MIN(season) as first_season,
            MAX(season) as last_season
        FROM (
            SELECT home_team_id as team_id, season FROM core.games
            UNION ALL
            SELECT away_team_id as team_id, season FROM core.games
        ) all_games
        GROUP BY team_id
    ) g
    WHERE tx.retrosheet_team_id = g.team_id;

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % teams with basic season ranges', updated_count;

    -- Handle franchise moves by inserting new entries for historical teams
    -- Montreal Expos -> Washington Nationals
    INSERT INTO bridge.team_xref (retrosheet_team_id, mlb_team_id, abbreviation, name, valid_from_season, valid_to_season)
    VALUES ('MON', 120, 'MON', 'Montreal Expos', 1969, 2004)
    ON CONFLICT (retrosheet_team_id) DO UPDATE SET
        valid_from_season = EXCLUDED.valid_from_season,
        valid_to_season = EXCLUDED.valid_to_season;

    -- Florida Marlins -> Miami Marlins
    INSERT INTO bridge.team_xref (retrosheet_team_id, mlb_team_id, abbreviation, name, valid_from_season, valid_to_season)
    VALUES ('FLO', 146, 'FLO', 'Florida Marlins', 1993, 2011)
    ON CONFLICT (retrosheet_team_id) DO UPDATE SET
        valid_from_season = EXCLUDED.valid_from_season,
        valid_to_season = EXCLUDED.valid_to_season;

    -- Update Washington Nationals to show it started in 2005
    UPDATE bridge.team_xref
    SET valid_from_season = 2005
    WHERE retrosheet_team_id = 'WAS';

    -- Update Miami Marlins to show it started in 2012
    UPDATE bridge.team_xref
    SET valid_from_season = 2012
    WHERE retrosheet_team_id = 'MIA';

    RAISE NOTICE 'Added franchise move entries for MON->WAS and FLO->MIA';
END;
$$;

-- ============================================================================
-- Comment on procedure
-- ============================================================================
COMMENT ON PROCEDURE bridge.populate_season_aware_team_xref () IS
'Populate bridge.team_xref with valid_from_season and valid_to_season based on core.games data, including franchise move handling.';

-- ============================================================================
-- Grant execute permission
-- ============================================================================
GRANT EXECUTE ON PROCEDURE bridge.populate_season_aware_team_xref() TO postgres;
