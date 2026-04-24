-- File: sql/maintenance/001_check_extensions.sql
-- Purpose: List installed and available PostgreSQL extensions
-- Author: Agent Cascade
-- Date: 2026-04-24
SELECT
    name,
    default_version,
    installed_version,
    CASE
        WHEN installed_version IS NOT NULL THEN 'INSTALLED'
        ELSE 'AVAILABLE'
    END AS status
FROM pg_available_extensions
ORDER BY name;

