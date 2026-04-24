-- File: sql/maintenance/021_update_cron_game_hours.sql
-- Purpose: Update cron jobs for season-aware MLB polling schedule
-- Author: Agent Cascade
-- Date: 2026-04-24
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

