-- File: sql/bridge/940_bridge_validation_tests.sql
-- Purpose: Validation tests and coverage checks for bridge tables
-- Author: Agent Cascade
-- Date: 2026-04-24
-- Depends On: bridge.player_xref, bridge.game_xref, bridge.team_xref, bridge.park_xref
-- Called By: Test runners, validation scripts, CI/CD pipelines

/*
Bridge Table Validation Tests
==============================

This file contains comprehensive tests for bridge table data quality:
1. ID coverage tests (MLB, Retrosheet, BBRef)
2. Uniqueness constraints
3. Referential integrity
4. Cross-table consistency
5. Pitch data linkage coverage

All tests return BOOLEAN (true = pass, false = fail) and log details.
*/

-- ============================================================================
-- TEST 1: Player Xref - MLB ID Coverage
-- ============================================================================

CREATE OR REPLACE FUNCTION bridge.test_player_xref_mlb_coverage(
    p_min_pct NUMERIC DEFAULT 95.0
)
RETURNS TABLE (
    test_name TEXT,
    passed BOOLEAN,
    actual_value TEXT,
    expected_value TEXT,
    details TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total INTEGER;
    v_with_mlb INTEGER;
    v_pct NUMERIC;
BEGIN
    test_name := 'player_xref_mlb_coverage';
    expected_value := format('>=%s%%', p_min_pct);
    
    SELECT COUNT(*), COUNT(mlb_id)
    INTO v_total, v_with_mlb
    FROM bridge.player_xref;
    
    v_pct := ROUND(v_with_mlb::numeric / NULLIF(v_total, 0) * 100, 2);
    
    passed := v_pct >= p_min_pct;
    actual_value := format('%s%% (%s/%s)', v_pct, v_with_mlb, v_total);
    details := CASE 
        WHEN passed THEN format('MLB ID coverage meets minimum %s%%', p_min_pct)
        ELSE format('MLB ID coverage %s%% below minimum %s%%', v_pct, p_min_pct)
    END;
    
    RETURN NEXT;
END;
$$;

COMMENT ON FUNCTION bridge.test_player_xref_mlb_coverage(NUMERIC) IS 'Validates that at least p_min_pct of player_xref records have MLB IDs.';

-- ============================================================================
-- TEST 2: Player Xref - Retrosheet ID Coverage
-- ============================================================================

CREATE OR REPLACE FUNCTION bridge.test_player_xref_retrosheet_coverage(
    p_min_pct NUMERIC DEFAULT 20.0
)
RETURNS TABLE (
    test_name TEXT,
    passed BOOLEAN,
    actual_value TEXT,
    expected_value TEXT,
    details TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total INTEGER;
    v_with_retro INTEGER;
    v_pct NUMERIC;
BEGIN
    test_name := 'player_xref_retrosheet_coverage';
    expected_value := format('>=%s%%', p_min_pct);
    
    SELECT COUNT(*), COUNT(retrosheet_id)
    INTO v_total, v_with_retro
    FROM bridge.player_xref;
    
    v_pct := ROUND(v_with_retro::numeric / NULLIF(v_total, 0) * 100, 2);
    
    passed := v_pct >= p_min_pct;
    actual_value := format('%s%% (%s/%s)', v_pct, v_with_retro, v_total);
    details := CASE 
        WHEN passed THEN format('Retrosheet ID coverage meets minimum %s%%', p_min_pct)
        ELSE format('Retrosheet ID coverage %s%% below minimum %s%%', v_pct, p_min_pct)
    END;
    
    RETURN NEXT;
END;
$$;

COMMENT ON FUNCTION bridge.test_player_xref_retrosheet_coverage(NUMERIC) IS 'Validates that at least p_min_pct of player_xref records have Retrosheet IDs.';

-- ============================================================================
-- TEST 3: Player Xref - Uniqueness of MLB IDs
-- ============================================================================

CREATE OR REPLACE FUNCTION bridge.test_player_xref_mlb_id_unique()
RETURNS TABLE (
    test_name TEXT,
    passed BOOLEAN,
    actual_value TEXT,
    expected_value TEXT,
    details TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total_with_mlb INTEGER;
    v_unique_mlb INTEGER;
    v_duplicates INTEGER;
BEGIN
    test_name := 'player_xref_mlb_id_unique';
    expected_value := '0 duplicates';
    
    SELECT 
        COUNT(mlb_id),
        COUNT(DISTINCT mlb_id)
    INTO v_total_with_mlb, v_unique_mlb
    FROM bridge.player_xref
    WHERE mlb_id IS NOT NULL;
    
    v_duplicates := v_total_with_mlb - v_unique_mlb;
    
    passed := v_duplicates = 0;
    actual_value := format('%s duplicates', v_duplicates);
    details := CASE 
        WHEN passed THEN 'All MLB IDs are unique'
        ELSE format('Found %s duplicate MLB IDs', v_duplicates)
    END;
    
    RETURN NEXT;
END;
$$;

COMMENT ON FUNCTION bridge.test_player_xref_mlb_id_unique() IS 'Validates that MLB IDs in player_xref are unique (no duplicates).';

-- ============================================================================
-- TEST 4: Player Xref - Uniqueness of Retrosheet IDs
-- ============================================================================

CREATE OR REPLACE FUNCTION bridge.test_player_xref_retrosheet_id_unique()
RETURNS TABLE (
    test_name TEXT,
    passed BOOLEAN,
    actual_value TEXT,
    expected_value TEXT,
    details TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total_with_retro INTEGER;
    v_unique_retro INTEGER;
    v_duplicates INTEGER;
BEGIN
    test_name := 'player_xref_retrosheet_id_unique';
    expected_value := '0 duplicates';
    
    SELECT 
        COUNT(retrosheet_id),
        COUNT(DISTINCT retrosheet_id)
    INTO v_total_with_retro, v_unique_retro
    FROM bridge.player_xref
    WHERE retrosheet_id IS NOT NULL;
    
    v_duplicates := v_total_with_retro - v_unique_retro;
    
    passed := v_duplicates = 0;
    actual_value := format('%s duplicates', v_duplicates);
    details := CASE 
        WHEN passed THEN 'All Retrosheet IDs are unique'
        ELSE format('Found %s duplicate Retrosheet IDs', v_duplicates)
    END;
    
    RETURN NEXT;
END;
$$;

COMMENT ON FUNCTION bridge.test_player_xref_retrosheet_id_unique() IS 'Validates that Retrosheet IDs in player_xref are unique (no duplicates).';

-- ============================================================================
-- TEST 5: Game Xref - Complete ID Coverage
-- ============================================================================

CREATE OR REPLACE FUNCTION bridge.test_game_xref_complete_coverage()
RETURNS TABLE (
    test_name TEXT,
    passed BOOLEAN,
    actual_value TEXT,
    expected_value TEXT,
    details TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total INTEGER;
    v_with_mlb INTEGER;
    v_with_retro INTEGER;
    v_pct_mlb NUMERIC;
    v_pct_retro NUMERIC;
BEGIN
    test_name := 'game_xref_complete_coverage';
    expected_value := '100% for both IDs';
    
    SELECT 
        COUNT(*),
        COUNT(mlb_game_pk),
        COUNT(retrosheet_game_id)
    INTO v_total, v_with_mlb, v_with_retro
    FROM bridge.game_xref;
    
    v_pct_mlb := ROUND(v_with_mlb::numeric / NULLIF(v_total, 0) * 100, 2);
    v_pct_retro := ROUND(v_with_retro::numeric / NULLIF(v_total, 0) * 100, 2);
    
    passed := v_pct_mlb = 100 AND v_pct_retro = 100;
    actual_value := format('MLB: %s%%, Retro: %s%%', v_pct_mlb, v_pct_retro);
    details := format('Total games: %s, MLB coverage: %s%%, Retrosheet coverage: %s%%', 
                      v_total, v_pct_mlb, v_pct_retro);
    
    RETURN NEXT;
END;
$$;

COMMENT ON FUNCTION bridge.test_game_xref_complete_coverage() IS 'Validates that all game_xref records have both MLB and Retrosheet IDs.';

-- ============================================================================
-- TEST 6: Pitch Data Player Coverage
-- ============================================================================

CREATE OR REPLACE FUNCTION bridge.test_pitch_data_player_coverage(
    p_min_pct NUMERIC DEFAULT 100.0
)
RETURNS TABLE (
    test_name TEXT,
    passed BOOLEAN,
    actual_value TEXT,
    expected_value TEXT,
    details TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total_players INTEGER;
    v_linked_players INTEGER;
    v_pct NUMERIC;
BEGIN
    test_name := 'pitch_data_player_coverage';
    expected_value := format('>=%s%%', p_min_pct);
    
    WITH all_pitch_players AS (
        SELECT DISTINCT pitcher_id as player_id FROM features_pitch.base_features
        UNION
        SELECT DISTINCT batter_id as player_id FROM features_pitch.base_features
    )
    SELECT 
        COUNT(*),
        COUNT(*) FILTER (WHERE px.player_xref_id IS NOT NULL)
    INTO v_total_players, v_linked_players
    FROM all_pitch_players app
    LEFT JOIN bridge.player_xref px 
        ON app.player_id::text = px.mlb_id::text;
    
    v_pct := ROUND(v_linked_players::numeric / NULLIF(v_total_players, 0) * 100, 2);
    
    passed := v_pct >= p_min_pct;
    actual_value := format('%s%% (%s/%s)', v_pct, v_linked_players, v_total_players);
    details := CASE 
        WHEN passed THEN format('All %s pitch data players linked to bridge', v_total_players)
        ELSE format('Only %s%% of %s pitch data players linked', v_pct, v_total_players)
    END;
    
    RETURN NEXT;
END;
$$;

COMMENT ON FUNCTION bridge.test_pitch_data_player_coverage(NUMERIC) IS 'Validates that pitch data players (batters and pitchers) are linked to bridge.player_xref.';

-- ============================================================================
-- TEST 7: Team Xref - Retrosheet Coverage
-- ============================================================================

CREATE OR REPLACE FUNCTION bridge.test_team_xref_retrosheet_coverage(
    p_min_pct NUMERIC DEFAULT 100.0
)
RETURNS TABLE (
    test_name TEXT,
    passed BOOLEAN,
    actual_value TEXT,
    expected_value TEXT,
    details TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total INTEGER;
    v_with_retro INTEGER;
    v_pct NUMERIC;
BEGIN
    test_name := 'team_xref_retrosheet_coverage';
    expected_value := format('>=%s%%', p_min_pct);
    
    SELECT COUNT(*), COUNT(retrosheet_team_id)
    INTO v_total, v_with_retro
    FROM bridge.team_xref;
    
    v_pct := ROUND(v_with_retro::numeric / NULLIF(v_total, 0) * 100, 2);
    
    passed := v_pct >= p_min_pct;
    actual_value := format('%s%% (%s/%s)', v_pct, v_with_retro, v_total);
    details := format('Team xref: %s total, %s with Retrosheet ID (%s%%)', 
                      v_total, v_with_retro, v_pct);
    
    RETURN NEXT;
END;
$$;

COMMENT ON FUNCTION bridge.test_team_xref_retrosheet_coverage(NUMERIC) IS 'Validates team_xref Retrosheet ID coverage.';

-- ============================================================================
-- TEST 8: Park Xref - Retrosheet Coverage
-- ============================================================================

CREATE OR REPLACE FUNCTION bridge.test_park_xref_retrosheet_coverage(
    p_min_pct NUMERIC DEFAULT 100.0
)
RETURNS TABLE (
    test_name TEXT,
    passed BOOLEAN,
    actual_value TEXT,
    expected_value TEXT,
    details TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total INTEGER;
    v_with_retro INTEGER;
    v_pct NUMERIC;
BEGIN
    test_name := 'park_xref_retrosheet_coverage';
    expected_value := format('>=%s%%', p_min_pct);
    
    SELECT COUNT(*), COUNT(retrosheet_park_id)
    INTO v_total, v_with_retro
    FROM bridge.park_xref;
    
    v_pct := ROUND(v_with_retro::numeric / NULLIF(v_total, 0) * 100, 2);
    
    passed := v_pct >= p_min_pct;
    actual_value := format('%s%% (%s/%s)', v_pct, v_with_retro, v_total);
    details := format('Park xref: %s total, %s with Retrosheet ID (%s%%)', 
                      v_total, v_with_retro, v_pct);
    
    RETURN NEXT;
END;
$$;

COMMENT ON FUNCTION bridge.test_park_xref_retrosheet_coverage(NUMERIC) IS 'Validates park_xref Retrosheet ID coverage.';

-- ============================================================================
-- MASTER TEST RUNNER - Run all bridge tests
-- ============================================================================

CREATE OR REPLACE FUNCTION bridge.run_all_bridge_tests(
    p_verbose BOOLEAN DEFAULT TRUE
)
RETURNS TABLE (
    test_name TEXT,
    passed BOOLEAN,
    actual_value TEXT,
    expected_value TEXT,
    details TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Run all individual tests
    RETURN QUERY SELECT * FROM bridge.test_player_xref_mlb_coverage(95.0);
    RETURN QUERY SELECT * FROM bridge.test_player_xref_retrosheet_coverage(20.0);
    RETURN QUERY SELECT * FROM bridge.test_player_xref_mlb_id_unique();
    RETURN QUERY SELECT * FROM bridge.test_player_xref_retrosheet_id_unique();
    RETURN QUERY SELECT * FROM bridge.test_game_xref_complete_coverage();
    RETURN QUERY SELECT * FROM bridge.test_pitch_data_player_coverage(100.0);
    RETURN QUERY SELECT * FROM bridge.test_team_xref_retrosheet_coverage(100.0);
    RETURN QUERY SELECT * FROM bridge.test_park_xref_retrosheet_coverage(100.0);
END;
$$;

COMMENT ON FUNCTION bridge.run_all_bridge_tests(BOOLEAN) IS 'Runs all bridge table validation tests and returns consolidated results.';

-- ============================================================================
-- TEST RESULT SUMMARY FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION bridge.get_bridge_test_summary()
RETURNS TABLE (
    total_tests INTEGER,
    passed_tests INTEGER,
    failed_tests INTEGER,
    pass_rate NUMERIC,
    status TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total INTEGER;
    v_passed INTEGER;
    v_rate NUMERIC;
BEGIN
    SELECT 
        COUNT(*),
        COUNT(*) FILTER (WHERE t.passed = true)
    INTO v_total, v_passed
    FROM bridge.run_all_bridge_tests(false) t;
    
    v_rate := ROUND(v_passed::numeric / NULLIF(v_total, 0) * 100, 2);
    
    total_tests := v_total;
    passed_tests := v_passed;
    failed_tests := v_total - v_passed;
    pass_rate := v_rate;
    status := CASE 
        WHEN v_rate = 100 THEN 'ALL TESTS PASSED'
        WHEN v_rate >= 80 THEN 'ACCEPTABLE'
        ELSE 'NEEDS ATTENTION'
    END;
    
    RETURN NEXT;
END;
$$;

COMMENT ON FUNCTION bridge.get_bridge_test_summary() IS 'Returns a summary of all bridge validation tests with pass/fail counts.';

-- ============================================================================
-- GAP ANALYSIS VIEW
-- ============================================================================

CREATE OR REPLACE VIEW bridge.vw_bridge_coverage_gap_analysis AS
WITH player_gaps AS (
    SELECT
        'player_xref' AS table_name,
        'mlb_id' AS id_type,
        COUNT(*) FILTER (WHERE mlb_id IS NULL) AS null_count,
        COUNT(*) AS total_count,
        ROUND(
            COUNT(*) FILTER (WHERE mlb_id IS NULL)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 2
        ) AS gap_pct
    FROM bridge.player_xref
    UNION ALL
    SELECT
        'player_xref',
        'retrosheet_id',
        COUNT(*) FILTER (WHERE retrosheet_id IS NULL),
        COUNT(*),
        ROUND(
            COUNT(*) FILTER (WHERE retrosheet_id IS NULL)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 2
        )
    FROM bridge.player_xref
    UNION ALL
    SELECT
        'player_xref',
        'baseball_reference_id',
        COUNT(*) FILTER (WHERE baseball_reference_id IS NULL),
        COUNT(*),
        ROUND(
            COUNT(*) FILTER (WHERE baseball_reference_id IS NULL)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 2
        )
    FROM bridge.player_xref
),

pitch_data_gaps AS (
    SELECT
        'pitch_data_players' AS table_name,
        'linked_to_bridge' AS id_type,
        COUNT(DISTINCT p.player_id) FILTER (WHERE px.player_xref_id IS NULL),
        COUNT(DISTINCT p.player_id),
        ROUND(
            COUNT(DISTINCT p.player_id) FILTER (WHERE px.player_xref_id IS NULL)::NUMERIC
            / NULLIF(COUNT(DISTINCT p.player_id), 0) * 100, 2
        )
    FROM (
        SELECT pitcher_id AS player_id FROM features_pitch.base_features
        UNION
        SELECT batter_id AS player_id FROM features_pitch.base_features
    ) AS p
    LEFT JOIN bridge.player_xref AS px ON p.player_id::TEXT = px.mlb_id::TEXT
)

SELECT * FROM player_gaps
UNION ALL
SELECT * FROM pitch_data_gaps
ORDER BY gap_pct DESC;

COMMENT ON VIEW bridge.vw_bridge_coverage_gap_analysis IS 'Identifies gaps in bridge table ID coverage, ordered by severity (highest gap % first).';
