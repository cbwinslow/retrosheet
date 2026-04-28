--
— File: sql/test/003_install_pgtap.sql
— Purpose: Install pgTAP extension for PostgreSQL unit testing
— Author: Agent KiloSwift
— Date: 2026-04-27
— Usage: psql -f sql/test/003_install_pgtap.sql
— Notes: pgTAP provides TAP-compliant unit testing for PostgreSQL databases
—

-- Check if pgTAP is already installed
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pgtap' AND installed_version IS NOT NULL) THEN
        RAISE NOTICE 'pgTAP is already installed (version: %)', (
            SELECT installed_version FROM pg_available_extensions
            WHERE name = 'pgtap' AND installed_version IS NOT NULL
        );
    ELSE
        RAISE NOTICE 'Installing pgTAP extension...';
        CREATE EXTENSION IF NOT EXISTS pgtap;
        RAISE NOTICE 'pgTAP installed successfully.';
    END IF;
END $$;

-- Verify installation by checking key functions
SELECT
    proname,
    prosrc,
    pg_get_function_identity_arguments(oid) as args
FROM pg_proc
WHERE proname LIKE '%tap%'
ORDER BY proname
LIMIT 10;

-- Comment on extension
COMMENT ON EXTENSION pgtap IS 'TAP-compliant unit testing framework for PostgreSQL. Enables automated testing of database objects (tables, functions, procedures, triggers) with ok(), is(), isnt(), like(), etc. Used for regression testing of warehouse schema and procedures.';

-- Create helper function to run all pgTAP tests for a schema
CREATE OR REPLACE FUNCTION public.run_schema_tests(p_schema_name TEXT)
RETURNS TABLE (
    test_name TEXT,
    passed BOOLEAN,
    error_message TEXT
) LANGUAGE plpgsql AS $$
DECLARE
    v_sql TEXT;
    v_result RECORD;
BEGIN
    RAISE NOTICE 'Running all pgTAP tests in schema: %', p_schema_name;

    -- Query all test functions and execute them
    FOR v_result IN
        SELECT
            n.nspname as schema_name,
            p.proname as function_name,
            pg_get_function_identity_arguments(p.oid) as args
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = p_schema_name
          AND p.proname LIKE 'test_%'
          AND pg_function_is_visible(p.oid)
    LOOP
        BEGIN
            v_sql := format('SELECT * FROM %I.%I()', v_result.schema_name, v_result.function_name);
            RETURN QUERY EXECUTE v_sql;
            RETURN NEXT;
        EXCEPTION WHEN OTHERS THEN
            test_name := v_result.function_name;
            passed := FALSE;
            error_message := SQLERRM;
            RETURN NEXT;
        END;
    END LOOP;
END;
$$;

COMMENT ON FUNCTION public.run_schema_tests(TEXT) IS 'Run all pgTAP test functions in a given schema. Returns test results with pass/fail status and error messages. Use: SELECT * FROM public.run_schema_tests(''test'');';

-- Create a convenience function to check if test exists
CREATE OR REPLACE FUNCTION public.has_pgtap_tests(p_schema_name TEXT DEFAULT 'public')
RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = p_schema_name
          AND p.proname LIKE 'test_%'
    );
$$;

COMMENT ON FUNCTION public.has_pgtap_tests(TEXT) IS 'Check if a schema contains any pgTAP test functions. Returns TRUE if test_* functions exist.';

-- Setup完成验证
SELECT '✅ pgTAP installation complete. Key functions: plan(), ok(), is(), isnt(), like(), throws_ok().' AS status;
