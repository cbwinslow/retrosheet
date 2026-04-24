-- File: sql/bridge/920_game_xref_procedure.sql
-- Purpose: Match Retrosheet games to MLB games by date, teams, and game number
-- Author: Agent Cascade
-- Date: 2026-04-24
DROP PROCEDURE IF EXISTS bridge.populate_game_xref();

-- ============================================================================
-- Procedure: bridge.populate_game_xref()
-- ============================================================================
-- Description: Matches games from core.games (Retrosheet) with core.live_games (MLB)
--              using date, team IDs, and game number to handle doubleheaders.
--              Extracts MLB team IDs and date from raw_payload JSON.
--              Uses DISTINCT ON to pick one match per mlb_game_pk to avoid duplicates.
-- Returns: Number of games matched
-- ============================================================================
CREATE OR REPLACE PROCEDURE bridge.populate_game_xref(
    OUT matched_count INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Match games using date, team IDs, and game number to handle doubleheaders
    -- Extract MLB team IDs, date, and game number from raw_payload JSON
    -- Use DISTINCT ON to pick one match per mlb_game_pk to avoid duplicates
    WITH mlb_games AS (
        SELECT 
            lg.mlb_game_pk,
            (lg.raw_payload->'gameData'->'datetime'->>'originalDate')::date AS game_date,
            (lg.raw_payload->'gameData'->'game'->>'gameNumber')::int AS game_number,
            (lg.raw_payload->'gameData'->'teams'->'home'->>'id')::int AS mlb_home_id,
            (lg.raw_payload->'gameData'->'teams'->'away'->>'id')::int AS mlb_away_id
        FROM core.live_games lg
        WHERE lg.mlb_game_pk IS NOT NULL
        AND lg.raw_payload IS NOT NULL
        AND (lg.raw_payload->'gameData'->'datetime'->>'originalDate') IS NOT NULL
    ),
    matched_games AS (
        SELECT DISTINCT ON (mg.mlb_game_pk)
            rg.game_id AS retrosheet_game_id,
            mg.mlb_game_pk,
            rg.game_date,
            rg.home_team_id AS retrosheet_home_team_id,
            rg.away_team_id AS retrosheet_away_team_id,
            mg.mlb_home_id AS mlb_home_team_id,
            mg.mlb_away_id AS mlb_away_team_id
        FROM core.games rg
        JOIN mlb_games mg ON rg.game_date = mg.game_date
        JOIN bridge.team_xref txh ON mg.mlb_home_id = txh.mlb_team_id AND rg.home_team_id = txh.retrosheet_team_id
        JOIN bridge.team_xref txa ON mg.mlb_away_id = txa.mlb_team_id AND rg.away_team_id = txa.retrosheet_team_id
        ORDER BY mg.mlb_game_pk, COALESCE(rg.game_number, 0) = COALESCE(mg.game_number, 0) DESC
    )
    INSERT INTO bridge.game_xref (
        retrosheet_game_id,
        mlb_game_pk,
        game_date,
        retrosheet_home_team_id,
        retrosheet_away_team_id,
        mlb_home_team_id,
        mlb_away_team_id
    )
    SELECT 
        retrosheet_game_id,
        mlb_game_pk,
        game_date,
        retrosheet_home_team_id,
        retrosheet_away_team_id,
        mlb_home_team_id,
        mlb_away_team_id
    FROM matched_games
    ON CONFLICT (retrosheet_game_id) DO UPDATE SET
        mlb_game_pk = EXCLUDED.mlb_game_pk,
        game_date = EXCLUDED.game_date,
        retrosheet_home_team_id = EXCLUDED.retrosheet_home_team_id,
        retrosheet_away_team_id = EXCLUDED.retrosheet_away_team_id,
        mlb_home_team_id = EXCLUDED.mlb_home_team_id,
        mlb_away_team_id = EXCLUDED.mlb_away_team_id;

    GET DIAGNOSTICS matched_count = ROW_COUNT;
    
    RAISE NOTICE 'Matched and inserted % games in bridge.game_xref', matched_count;
END;
$$;

-- ============================================================================
-- Comment on procedure
-- ============================================================================
COMMENT ON PROCEDURE bridge.populate_game_xref () IS
'Populate bridge.game_xref by matching games between Retrosheet and MLB using date, team IDs, and game number.';

-- ============================================================================
-- Grant execute permission
-- ============================================================================
GRANT EXECUTE ON PROCEDURE bridge.populate_game_xref() TO postgres;

