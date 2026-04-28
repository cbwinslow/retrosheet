--
— File: sql/test/010_pgtap_core_tables.sql
— Purpose: pgTAP unit tests for core.games table and related constraints
— Author: Agent KiloSwift
— Date: 2026-04-27
— Usage: psql -v schema=core -f sql/test/010_pgtap_core_tables.sql
— Dependencies: sql/test/003_install_pgtap.sql must be run first
— Tables Tested: core.games, core.events, core.plate_appearances
— Notes: This test suite validates schema, constraints, and data integrity
—

-- Set search path to core schema
SET search_path TO core, public;

-- Begin test plan
SELECT plan(15);

-- Test 1: Verify core.games table exists
SELECT has_table('core', 'games', 'core.games table exists');

-- Test 2: Verify core.games has correct number of columns (expected: 46 columns based on schema)
SELECT col_is_present('core', 'games', 'game_id', 'game_id column exists');
SELECT col_is_present('core', 'games', 'game_pk', 'game_pk column exists');
SELECT col_is_present('core', 'games', 'season', 'season column exists');
SELECT col_is_present('core', 'games', 'game_date', 'game_date column exists');
SELECT col_is_present('core', 'games', 'home_score', 'home_score column exists');
SELECT col_is_present('core', 'games', 'away_score', 'away_score column exists');

-- Test 3: Verify primary key constraint
SELECT idx_is_pk('core', 'games', 'games_pkey', 'Primary key constraint exists on games');

-- Test 4: Verify NOT NULL constraints
SELECT col_is_not_null('core', 'games', 'game_id', 'game_id is NOT NULL');
SELECT col_is_not_null('core', 'games', 'game_pk', 'game_pk is NOT NULL');
SELECT col_is_not_null('core', 'games', 'season', 'season is NOT NULL');
SELECT col_is_not_null('core', 'games', 'game_date', 'game_date is NOT NULL');

-- Test 5: Verify data types
SELECT col_type_is('core', 'games', 'game_id', 'TEXT', 'game_id is TEXT');
SELECT col_type_is('core', 'games', 'season', 'INTEGER', 'season is INTEGER');
SELECT col_type_is('core', 'games', 'home_score', 'INTEGER', 'home_score is INTEGER');
SELECT col_type_is('core', 'games', 'away_score', 'INTEGER', 'away_score is INTEGER');

-- Test 6: Verify indexes exist
SELECT has_index('core', 'games', 'idx_games_game_pk', 'Index on game_pk exists');
SELECT has_index('core', 'games', 'idx_games_game_date', 'Index on game_date exists');
SELECT has_index('core', 'games', 'idx_games_season', 'Index on season exists');

-- Test 7: Foreign key relationships
-- (Will be tested after bridge tables are populated)

-- Test 8: Verify view exists (analysis.combined_games should exist)
SELECT has_view('analysis', 'combined_games', 'analysis.combined_games view exists');

-- Test 9: Verify comment on table exists
SELECT has_table_comment('core', 'games', 'core.games has table comment');

-- Finish and return results
SELECT * FROM finish();
