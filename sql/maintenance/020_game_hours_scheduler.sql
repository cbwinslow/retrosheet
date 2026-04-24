-- File: sql/maintenance/020_game_hours_scheduler.sql
-- Purpose: Functions to conditionally poll MLB data during season hours
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE OR REPLACE FUNCTION metadata.has_scheduled_games_today()
RETURNS boolean AS $$
DECLARE
    has_games boolean;
    today date;
BEGIN
    today := CURRENT_DATE;
    
    -- Check if there are any games scheduled for today
    -- Based on raw_mlb.schedule_snapshots payload
    SELECT EXISTS (
        SELECT 1 FROM raw_mlb.schedule_snapshots s
        WHERE s.snapshot_date = today
          AND s.payload->>'totalGames' IS NOT NULL
          AND (s.payload->>'totalGames')::int > 0
    ) INTO has_games;
    
    RETURN has_games;
END;
$$ LANGUAGE plpgsql;

-- Function to check if we're in MLB season (March-October, plus February spring training)
CREATE OR REPLACE FUNCTION metadata.is_mlb_season()
RETURNS boolean AS $$
DECLARE
    current_month int;
BEGIN
    current_month := EXTRACT(MONTH FROM CURRENT_DATE);
    -- MLB season: February (spring training) through October (postseason)
    -- Offseason: November, December, January
    RETURN current_month BETWEEN 2 AND 10;
END;
$$ LANGUAGE plpgsql;

-- Function to check if current time is within game hours
-- MLB games typically: 1pm - 11pm ET (can go later for extra innings)
CREATE OR REPLACE FUNCTION metadata.is_game_hours()
RETURNS boolean AS $$
DECLARE
    current_hour int;
    current_dow int;
BEGIN
    current_hour := EXTRACT(HOUR FROM CURRENT_TIMESTAMP AT TIME ZONE 'America/New_York');
    current_dow := EXTRACT(DOW FROM CURRENT_DATE);
    
    -- Game hours: 11am - 1am ET (covers pre-game prep through extra innings)
    -- Sunday night baseball starts later
    -- Monday games often start later (7pm+)
    
    -- Regular game window: 11am - 1am
    IF current_hour BETWEEN 11 AND 23 THEN
        RETURN true;
    END IF;
    
    -- Late games/Extra innings: midnight - 1am
    IF current_hour = 0 THEN
        RETURN true;
    END IF;
    
    RETURN false;
END;
$$ LANGUAGE plpgsql;

-- Smart polling function that checks season, hours, and schedule
CREATE OR REPLACE FUNCTION metadata.should_poll_games()
RETURNS boolean AS $$
BEGIN
    -- Only poll during MLB season
    IF NOT metadata.is_mlb_season() THEN
        RETURN false;
    END IF;
    
    -- Only poll during game hours
    IF NOT metadata.is_game_hours() THEN
        RETURN false;
    END IF;
    
    -- Check if games are scheduled today (optional - requires recent schedule fetch)
    -- Comment this out if you want to poll even without confirmed schedule
    -- IF NOT metadata.has_scheduled_games_today() THEN
    --     RETURN false;
    -- END IF;
    
    RETURN true;
END;
$$ LANGUAGE plpgsql;

-- Create wrapper functions for the polling that check conditions

-- Wrapper for live game polling
CREATE OR REPLACE FUNCTION metadata.poll_active_games_conditional()
RETURNS void AS $$
BEGIN
    IF metadata.should_poll_games() THEN
        PERFORM raw_sportradar.poll_active_games();
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Wrapper for all endpoints polling
CREATE OR REPLACE FUNCTION metadata.poll_all_endpoints_conditional()
RETURNS void AS $$
BEGIN
    IF metadata.should_poll_games() THEN
        PERFORM raw_mlb.poll_all_active_endpoints();
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Schedule refresh should run daily year-round
-- No wrapper needed - already scheduled as 0 0 * * *

COMMENT ON FUNCTION metadata.is_mlb_season() IS 'Returns true during MLB season (Feb-Oct)';
COMMENT ON FUNCTION metadata.is_game_hours() IS 'Returns true during typical game hours (11am-1am ET)';
COMMENT ON FUNCTION metadata.should_poll_games() IS 'Returns true if season + game hours conditions are met';

