-- Install pg_stat_statements extension for query performance monitoring
-- This is critical for identifying slow queries and optimizing performance
-- Research-backed: Standard extension for query performance monitoring in PostgreSQL

-- Create extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Validate installation: Check if extension is installed
SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_stat_statements';

-- Validate: Check query stats (should be empty initially)
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;

-- Note: Requires shared_preload_libraries = 'pg_stat_statements' in postgresql.conf
-- and PostgreSQL restart to take effect
