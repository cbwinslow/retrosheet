-- pg_cron Scheduled Jobs
-- Run automatically inside PostgreSQL

-- Poll all active games EVERY 10 SECONDS
SELECT cron.schedule(
    'live-game-poll-10s',
    '*/10 * * * * *',
    $$ SELECT raw_sportradar.poll_active_games(); $$
);

-- Refresh schedule DAILY at 00:00 UTC
SELECT cron.schedule(
    'daily-schedule-refresh',
    '0 0 * * *',
    $$ SELECT raw_sportradar.fetch_live_schedule(); $$
);

-- Verify scheduled jobs
SELECT jobid, schedule, command, nodename, nodeport
FROM cron.job
ORDER BY jobid;
