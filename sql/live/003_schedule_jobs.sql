-- File: sql/live/003_schedule_jobs.sql
-- Purpose: pg_cron jobs for polling active games and endpoints
-- Author: Agent Cascade
-- Date: 2026-04-24
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
SELECT
    jobid,
    schedule,
    command,
    nodename,
    nodeport
FROM cron.job
ORDER BY jobid;

