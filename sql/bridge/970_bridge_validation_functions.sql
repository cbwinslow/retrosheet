-- Bridge Table Validation Functions
-- These functions return boolean true/false for use in scripting and validation

-- Function: Check if bridge tables have data
CREATE OR REPLACE FUNCTION bridge.validate_bridge_tables_have_data()
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    table_count INT;
BEGIN
    SELECT COUNT(DISTINCT table_name)
    INTO table_count
    FROM bridge.bridge_table_counts
    WHERE total_rows > 0;
    
    RETURN table_count >= 4; -- At least player_xref, team_xref, park_xref, game_xref
END;
$$;

COMMENT ON FUNCTION bridge.validate_bridge_tables_have_data() IS 'Returns true if all core bridge tables have data';

-- Function: Check for duplicate IDs
CREATE OR REPLACE FUNCTION bridge.validate_no_duplicate_ids()
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    duplicate_count INT;
BEGIN
    SELECT COUNT(*)
    INTO duplicate_count
    FROM bridge.duplicate_id_detection;
    
    RETURN duplicate_count = 0;
END;
$$;

COMMENT ON FUNCTION bridge.validate_no_duplicate_ids() IS 'Returns true if no duplicate IDs exist in bridge tables';

-- Function: Check for orphaned external IDs
CREATE OR REPLACE FUNCTION bridge.validate_no_orphaned_external_ids()
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    orphan_count INT;
BEGIN
    SELECT SUM(orphan_count)
    INTO orphan_count
    FROM bridge.orphaned_external_ids;
    
    RETURN COALESCE(orphan_count, 0) = 0;
END;
$$;

COMMENT ON FUNCTION bridge.validate_no_orphaned_external_ids() IS 'Returns true if no orphaned external IDs exist';

-- Function: Check cross-reference consistency
CREATE OR REPLACE FUNCTION bridge.validate_cross_reference_consistency()
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    inconsistent_count INT;
BEGIN
    SELECT SUM(inconsistent_count)
    INTO inconsistent_count
    FROM bridge.cross_reference_consistency;
    
    RETURN COALESCE(inconsistent_count, 0) = 0;
END;
$$;

COMMENT ON FUNCTION bridge.validate_cross_reference_consistency() IS 'Returns true if cross-references are consistent';

-- Function: Check season coverage gaps
CREATE OR REPLACE FUNCTION bridge.validate_no_season_coverage_gaps()
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    gap_count INT;
BEGIN
    SELECT COUNT(*)
    INTO gap_count
    FROM bridge.season_coverage_gaps;
    
    RETURN gap_count = 0;
END;
$$;

COMMENT ON FUNCTION bridge.validate_no_season_coverage_gaps() IS 'Returns true if no season coverage gaps exist';

-- Function: Check player ID coverage
CREATE OR REPLACE FUNCTION bridge.validate_player_id_coverage(p_minimum_coverage_pct NUMERIC DEFAULT 90.0)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    coverage_pct NUMERIC;
BEGIN
    SELECT mlb_coverage_pct
    INTO coverage_pct
    FROM bridge.mapping_completeness
    WHERE entity_type = 'players';
    
    RETURN COALESCE(coverage_pct, 0) >= p_minimum_coverage_pct;
END;
$$;

COMMENT ON FUNCTION bridge.validate_player_id_coverage(p_minimum_coverage_pct NUMERIC) IS 'Returns true if player ID coverage meets minimum percentage';

-- Function: Check team ID coverage
CREATE OR REPLACE FUNCTION bridge.validate_team_id_coverage(p_minimum_coverage_pct NUMERIC DEFAULT 95.0)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    coverage_pct NUMERIC;
BEGIN
    SELECT mlb_coverage_pct
    INTO coverage_pct
    FROM bridge.mapping_completeness
    WHERE entity_type = 'teams';
    
    RETURN COALESCE(coverage_pct, 0) >= p_minimum_coverage_pct;
END;
$$;

COMMENT ON FUNCTION bridge.validate_team_id_coverage(p_minimum_coverage_pct NUMERIC) IS 'Returns true if team ID coverage meets minimum percentage';

-- Function: Check park ID coverage
CREATE OR REPLACE FUNCTION bridge.validate_park_id_coverage(p_minimum_coverage_pct NUMERIC DEFAULT 90.0)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    coverage_pct NUMERIC;
BEGIN
    SELECT mlb_coverage_pct
    INTO coverage_pct
    FROM bridge.mapping_completeness
    WHERE entity_type = 'parks';
    
    RETURN COALESCE(coverage_pct, 0) >= p_minimum_coverage_pct;
END;
$$;

COMMENT ON FUNCTION bridge.validate_park_id_coverage(p_minimum_coverage_pct NUMERIC) IS 'Returns true if park ID coverage meets minimum percentage';

-- Function: Check data quality (no nulls where required)
CREATE OR REPLACE FUNCTION bridge.validate_data_quality()
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    issue_count INT;
BEGIN
    SELECT SUM(issue_count)
    INTO issue_count
    FROM bridge.bridge_data_quality;
    
    RETURN COALESCE(issue_count, 0) = 0;
END;
$$;

COMMENT ON FUNCTION bridge.validate_data_quality() IS 'Returns true if no data quality issues exist';

-- Function: Master validation function (runs all checks)
CREATE OR REPLACE FUNCTION bridge.validate_all_bridge_tables()
RETURNS TABLE(
    check_name TEXT,
    passed BOOLEAN,
    details TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    checks RECORD;
BEGIN
    -- Check 1: Tables have data
    SELECT 'bridge_tables_have_data' as check_name,
           bridge.validate_bridge_tables_have_data() as passed,
           CASE 
               WHEN bridge.validate_bridge_tables_have_data() THEN 'All core bridge tables have data'
               ELSE 'Some bridge tables are empty'
           END as details
    INTO checks;
    RETURN QUERY SELECT checks.check_name, checks.passed, checks.details;
    
    -- Check 2: No duplicate IDs
    SELECT 'no_duplicate_ids' as check_name,
           bridge.validate_no_duplicate_ids() as passed,
           CASE 
               WHEN bridge.validate_no_duplicate_ids() THEN 'No duplicate IDs found'
               ELSE 'Duplicate IDs exist in bridge tables'
           END as details
    INTO checks;
    RETURN QUERY SELECT checks.check_name, checks.passed, checks.details;
    
    -- Check 3: No orphaned external IDs
    SELECT 'no_orphaned_external_ids' as check_name,
           bridge.validate_no_orphaned_external_ids() as passed,
           CASE 
               WHEN bridge.validate_no_orphaned_external_ids() THEN 'No orphaned external IDs'
               ELSE 'Orphaned external IDs found'
           END as details
    INTO checks;
    RETURN QUERY SELECT checks.check_name, checks.passed, checks.details;
    
    -- Check 4: Cross-reference consistency
    SELECT 'cross_reference_consistency' as check_name,
           bridge.validate_cross_reference_consistency() as passed,
           CASE 
               WHEN bridge.validate_cross_reference_consistency() THEN 'Cross-references are consistent'
               ELSE 'Cross-reference inconsistencies found'
           END as details
    INTO checks;
    RETURN QUERY SELECT checks.check_name, checks.passed, checks.details;
    
    -- Check 5: No season coverage gaps
    SELECT 'no_season_coverage_gaps' as check_name,
           bridge.validate_no_season_coverage_gaps() as passed,
           CASE 
               WHEN bridge.validate_no_season_coverage_gaps() THEN 'No season coverage gaps'
               ELSE 'Season coverage gaps found'
           END as details
    INTO checks;
    RETURN QUERY SELECT checks.check_name, checks.passed, checks.details;
    
    -- Check 6: Player ID coverage
    SELECT 'player_id_coverage' as check_name,
           bridge.validate_player_id_coverage(90.0) as passed,
           CASE 
               WHEN bridge.validate_player_id_coverage(90.0) THEN 'Player ID coverage >= 90%'
               ELSE 'Player ID coverage below 90%'
           END as details
    INTO checks;
    RETURN QUERY SELECT checks.check_name, checks.passed, checks.details;
    
    -- Check 7: Team ID coverage
    SELECT 'team_id_coverage' as check_name,
           bridge.validate_team_id_coverage(95.0) as passed,
           CASE 
               WHEN bridge.validate_team_id_coverage(95.0) THEN 'Team ID coverage >= 95%'
               ELSE 'Team ID coverage below 95%'
           END as details
    INTO checks;
    RETURN QUERY SELECT checks.check_name, checks.passed, checks.details;
    
    -- Check 8: Park ID coverage
    SELECT 'park_id_coverage' as check_name,
           bridge.validate_park_id_coverage(90.0) as passed,
           CASE 
               WHEN bridge.validate_park_id_coverage(90.0) THEN 'Park ID coverage >= 90%'
               ELSE 'Park ID coverage below 90%'
           END as details
    INTO checks;
    RETURN QUERY SELECT checks.check_name, checks.passed, checks.details;
    
    -- Check 9: Data quality
    SELECT 'data_quality' as check_name,
           bridge.validate_data_quality() as passed,
           CASE 
               WHEN bridge.validate_data_quality() THEN 'No data quality issues'
               ELSE 'Data quality issues found'
           END as details
    INTO checks;
    RETURN QUERY SELECT checks.check_name, checks.passed, checks.details;
END;
$$;

COMMENT ON FUNCTION bridge.validate_all_bridge_tables() IS 'Runs all bridge table validation checks and returns results';

-- Function: Quick validation (returns single boolean)
CREATE OR REPLACE FUNCTION bridge.validate_bridge_tables_quick()
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    all_passed BOOLEAN;
BEGIN
    SELECT NOT EXISTS (
        SELECT 1 FROM bridge.validate_all_bridge_tables() WHERE passed = false
    )
    INTO all_passed;
    
    RETURN COALESCE(all_passed, false);
END;
$$;

COMMENT ON FUNCTION bridge.validate_bridge_tables_quick() IS 'Returns true if all bridge table validation checks pass';
