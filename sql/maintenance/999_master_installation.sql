-- Master PostgreSQL Extensions and Features Installation Script
-- Research-backed implementation of PostgreSQL extensions and advanced features
-- This script orchestrates the installation of all recommended extensions and features

-- ============================================================================
-- PHASE 1: Check Current State
-- ============================================================================
\echo 'Checking current PostgreSQL extensions...'
\i sql/maintenance/001_check_extensions.sql

-- ============================================================================
-- PHASE 2: Install Core Extensions
-- ============================================================================
\echo 'Installing pg_cron extension for job scheduling...'
\i sql/maintenance/002_install_pg_cron.sql

\echo 'Installing pg_stat_statements extension for query monitoring...'
\i sql/maintenance/003_install_pg_stat_statements.sql

\echo 'Installing PL/Python3u extension for Python integration...'
\i sql/maintenance/004_install_pl_python3u.sql

-- ============================================================================
-- PHASE 3: Install Analytics Extensions
-- ============================================================================
\echo 'Installing pgvector extension for vector similarity search...'
\i sql/maintenance/005_install_pgvector.sql

-- ============================================================================
-- PHASE 4: Implement Advanced Features
-- ============================================================================
\echo 'Implementing array types for multi-value features...'
\i sql/maintenance/010_array_types.sql

\echo 'Implementing custom types (domains) for data validation...'
\i sql/maintenance/011_custom_types.sql

\echo 'Implementing partial indexes for query optimization...'
\i sql/maintenance/012_partial_indexes.sql

-- ============================================================================
-- PHASE 5: Final Validation
-- ============================================================================
\echo 'Final validation: Checking installed extensions...'
SELECT 
    name,
    default_version,
    installed_version,
    CASE 
        WHEN installed_version IS NOT NULL THEN 'INSTALLED'
        ELSE 'AVAILABLE'
    END as status
FROM pg_available_extensions
WHERE name IN ('cron', 'pg_stat_statements', 'plpython3u', 'vector')
ORDER BY name;

\echo 'Installation complete!'
