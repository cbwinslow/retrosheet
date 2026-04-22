-- Install PL/Python3u extension for Python integration within PostgreSQL
-- This is critical for advanced ML models and external API calls
-- Research-backed: Standard extension for Python integration in PostgreSQL

-- Create extension
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
SELECT extname, extversion FROM pg_extension WHERE extname = 'plpython3u';
