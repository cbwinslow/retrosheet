-- Install pg_cron extension for job scheduling
-- This is critical for automated pipeline (live game discovery, MV refresh)
-- Research-backed: Standard extension for scheduled tasks in PostgreSQL

-- Create extension
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Validate installation: Create test job
-- This job runs every minute and logs a simple message
SELECT cron.schedule(
    'test-job',
    '* * * * *',
    $$SELECT current_timestamp as test_timestamp;$$
);

-- Check if job was scheduled
SELECT * FROM cron.job;

-- Clean up test job (uncomment after validation)
-- SELECT cron.unschedule('test-job');

-- Verify extension is installed
SELECT extname, extversion FROM pg_extension WHERE extname = 'cron';
