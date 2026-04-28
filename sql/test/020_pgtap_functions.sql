--
— File: sql/test/020_pgtap_functions.sql
— Purpose: pgTAP tests for database functions and procedures
— Author: Agent KiloSwift
— Date: 2026-04-27
— Usage: psql -v schema=bridge -f sql/test/020_pgtap_functions.sql
— Dependencies: sql/test/003_install_pgtap.sql, bridge population procedures
— Notes: Tests validation functions and bridge procedures
—

-- Set search path
SET search_path TO bridge, public;

-- Begin test plan (24 tests)
SELECT plan(24);

-- Test bridge validation functions
SELECT has_function('bridge', 'validate_bridge_tables_have_data', ARRAY[]::text[], 'validate_bridge_tables_have_data function exists');
SELECT has_function('bridge', 'validate_no_duplicate_ids', ARRAY[]::text[], 'validate_no_duplicate_ids function exists');
SELECT has_function('bridge', 'validate_no_orphaned_external_ids', ARRAY[]::text[], 'validate_no_orphaned_external_ids function exists');
SELECT has_function('bridge', 'validate_cross_reference_consistency', ARRAY[]::text[], 'validate_cross_reference_consistency function exists');
SELECT has_function('bridge', 'validate_no_season_coverage_gaps', ARRAY[]::text[], 'validate_no_season_coverage_gaps function exists');

-- Test that validation functions return boolean
SELECT function_returns('bridge', 'validate_bridge_tables_have_data', 'boolean', 'validate_bridge_tables_have_data returns boolean');
SELECT function_returns('bridge', 'validate_no_duplicate_ids', 'boolean', 'validate_no_duplicate_ids returns boolean');

-- Test bridge population procedures exist
SELECT has_function('bridge', 'populate_player_xref', ARRAY['boolean', 'boolean', 'boolean'], 'populate_player_xref procedure exists');
SELECT has_function('bridge', 'populate_team_xref', ARRAY[]::text[], 'populate_team_xref procedure exists');
SELECT has_function('bridge', 'populate_game_xref', ARRAY[]::text[], 'populate_game_xref procedure exists');
SELECT has_function('bridge', 'populate_park_xref', ARRAY[]::text[], 'populate_park_xref procedure exists');

-- Test master bridge population orchestrator
SELECT has_function('bridge', 'populate_all_bridge_tables', ARRAY[]::text[], 'populate_all_bridge_tables orchestrator exists');

-- Test procedure arguments (check signature)
SELECT function_arguments('bridge', 'populate_team_xref') LIKE '%boolean%' OR function_arguments('bridge', 'populate_team_xref') IS NULL
    AS 'populate_team_xref has optional dry_run parameter or no args';

-- Test confidence scoring function
SELECT has_function('bridge', 'update_confidence_scores', ARRAY['text', 'numeric', 'text'], 'update_confidence_scores function exists');

-- Test feature population procedures
SELECT has_function('features', 'populate_features_phase', ARRAY['text'], 'populate_features_phase exists');
SELECT has_function('features', 'verify_features_populated', ARRAY[]::text[], 'verify_features_populated exists');
SELECT has_function('features', 'get_feature_stats', ARRAY[]::text[], 'get_feature_stats exists');

-- Test win expectancy calculation function
SELECT has_function('core', 'get_win_expectancy', ARRAY['integer', 'integer', 'integer', 'integer', 'integer'], 'get_win_expectancy exists');

-- Test analysis functions
SELECT has_function('analysis', 'get_data_source_stats', ARRAY[]::text[], 'get_data_source_stats exists');
SELECT has_function('analysis', 'get_recent_games', ARRAY['integer'], 'get_recent_games exists');

-- Test inference functions
SELECT has_function('models', 'register_model', ARRAY['text', 'text', 'text', 'jsonb'], 'register_model exists');
SELECT has_function('models', 'get_active_model', ARRAY['text'], 'get_active_model exists');

-- Verify function returns correct types where documented
SELECT function_returns('core', 'get_win_expectancy', 'numeric', 'get_win_expectancy returns numeric');

-- Check function comments exist (documentation)
SELECT has_description('pg_proc', 'regprocedure', 'bridge.populate_player_xref', 'populate_player_xref has description');

-- Finish
SELECT * FROM finish();
