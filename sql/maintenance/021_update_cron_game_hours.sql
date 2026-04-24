-- Update cron jobs to use game-hours-aware scheduling
-- This applies conditional polling using the metadata wrapper functions

-- Option 1: Use conditional polling functions (recommended)
-- These check season and game hours before executing

-- Update live game poll to use conditional wrapper
-- This will only poll during MLB season and game hours
SELECT cron.unschedule('live-game-poll-10s');

-- Use conditional wrapper - polls every 10s but only executes if conditions met
SELECT cron.schedule(
    'live-game-poll-10s-conditional',
    '*/10 * * * * *',
    'SELECT metadata.poll_active_games_conditional();'
);

-- Update all endpoints poll to use conditional wrapper
SELECT cron.unschedule('all-endpoints-poll-15s');

-- Use conditional wrapper - polls every 15s but only executes if conditions met  
SELECT cron.schedule(
    'all-endpoints-poll-15s-conditional',
    '*/15 * * * * *',
    'SELECT metadata.poll_all_endpoints_conditional();'
);

-- Keep the daily schedule refresh (runs year-round at midnight)
-- No change needed: '0 0 * * *' - raw_sportradar.fetch_live_schedule();

-- Keep the data dictionary refresh (runs year-round at 1am)
-- No change needed: '0 1 * * *' - metadata.refresh_data_dictionary();

-- Verify updated jobs
SELECT
    jobid,
    jobname,
    schedule,
    active
FROM cron.job
ORDER BY jobid;
