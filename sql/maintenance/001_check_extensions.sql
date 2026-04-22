-- Check currently installed PostgreSQL extensions
SELECT 
    name,
    default_version,
    installed_version,
    CASE 
        WHEN installed_version IS NOT NULL THEN 'INSTALLED'
        ELSE 'AVAILABLE'
    END as status
FROM pg_available_extensions
ORDER BY name;
