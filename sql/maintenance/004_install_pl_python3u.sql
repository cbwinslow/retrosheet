-- File: sql/maintenance/004_install_pl_python3u.sql
-- Purpose: Install PL/Python3u extension with test function
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE EXTENSION IF NOT EXISTS plpython3u;

-- Validate installation: Create test function
CREATE OR REPLACE FUNCTION test_python_function()
RETURNS INTEGER
AS $$
    return 42
$$ LANGUAGE plpython3u;

-- Test the function
SELECT test_python_function();

-- Clean up test function (uncomment after validation)
-- DROP FUNCTION test_python_function();

-- Verify extension is installed
SELECT
    extname,
    extversion
FROM pg_extension
WHERE extname = 'plpython3u';

