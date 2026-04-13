-- Analysis views for combining historical Retrosheet and live MLB data
-- These views provide unified access to both data sources while maintaining separation

CREATE SCHEMA IF NOT EXISTS analysis;

-- Combined games view - unions historical and live games
CREATE OR REPLACE VIEW analysis.combined_games AS
SELECT
    game_id,
    season::integer,
    source_type,
    game_date::date,
    game_number,
    day_of_week,
    start_time,
    doubleheader_flag,
    day_night,
    away_team_id,
    home_team_id,
    park_id,
    away_starting_pitcher_id,
    home_starting_pitcher_id,
    attendance,
    temperature_f,
    wind_direction,
    wind_speed_mph,
    field_condition,
    precipitation,
    sky_condition,
    duration_minutes,
    innings,
    away_score,
    home_score,
    away_hits,
    home_hits,
    away_errors,
    home_errors,
    away_lob,
    home_lob,
    winning_team_id,
    home_win,
    win_pitcher_id,
    loss_pitcher_id,
    save_pitcher_id,
    raw_loaded_at,
    created_at,
    updated_at
FROM core.games

UNION ALL

SELECT
    game_id,
    season::integer,
    source_type,
    game_date::date,
    NULL::smallint as game_number,
    NULL::text as day_of_week,
    NULL::text as start_time,
    NULL::text as doubleheader_flag,
    NULL::text as day_night,
    away_team_id,
    home_team_id,
    park_id,
    NULL::text as away_starting_pitcher_id,
    NULL::text as home_starting_pitcher_id,
    NULL::integer as attendance,
    NULL::integer as temperature_f,
    NULL::text as wind_direction,
    NULL::integer as wind_speed_mph,
    NULL::text as field_condition,
    NULL::text as precipitation,
    NULL::text as sky_condition,
    NULL::integer as duration_minutes,
    NULL::integer as innings,
    away_score,
    home_score,
    NULL::integer as away_hits,
    NULL::integer as home_hits,
    NULL::integer as away_errors,
    NULL::integer as home_errors,
    NULL::integer as away_lob,
    NULL::integer as home_lob,
    NULL::text as winning_team_id,
    (home_score > away_score) as home_win,
    NULL::text as win_pitcher_id,
    NULL::text as loss_pitcher_id,
    NULL::text as save_pitcher_id,
    NULL::timestamptz as raw_loaded_at,
    now()::timestamptz as created_at,
    now()::timestamptz as updated_at
FROM core.live_games;

-- Combined events view - unions historical and live events
CREATE OR REPLACE VIEW analysis.combined_events AS
SELECT
    game_id,
    event_id,
    season,
    inning,
    is_bottom_inning,
    event_sequence,
    batter_id,
    pitcher_id,
    batter_hand,
    pitcher_hand,
    outs_before,
    balls,
    strikes,
    start_bases,
    event_code,
    event_text,
    is_at_bat,
    is_plate_appearance,
    hit_value,
    is_hit,
    is_walk,
    is_strikeout,
    is_home_run,
    runs_on_play,
    rbi,
    source_type,
    created_at,
    created_at as updated_at
FROM core.events

UNION ALL

SELECT
    game_id,
    event_id,
    season::integer,
    inning,
    is_bottom_inning,
    event_sequence,
    batter_id,
    pitcher_id,
    batter_hand,
    pitcher_hand,
    outs_before,
    balls,
    strikes,
    start_bases,
    event_code,
    event_text,
    is_at_bat,
    is_plate_appearance,
    hit_value,
    is_hit,
    is_walk,
    is_strikeout,
    is_home_run,
    runs_on_play,
    rbi,
    source_type,
    now()::timestamptz as created_at,
    now()::timestamptz as updated_at
FROM core.live_events;

-- Materialized view for combined plate appearances (refreshed periodically)
-- This combines historical plate appearances with live events converted to PA format
CREATE MATERIALIZED VIEW analysis.combined_plate_appearances AS
SELECT
    game_id,
    season,
    inning,
    is_bottom_inning,
    batter_id,
    pitcher_id,
    batter_hand,
    pitcher_hand,
    outs_before,
    balls,
    strikes,
    start_bases,
    event_code,
    event_text,
    is_at_bat,
    hit_value,
    is_hit,
    is_walk,
    is_strikeout,
    is_home_run,
    runs_on_play,
    rbi,
    source_type,
    now()::timestamptz as created_at,
    now()::timestamptz as updated_at
FROM core.plate_appearances

UNION ALL

-- Convert live events to plate appearance format
SELECT
    game_id,
    season::integer,
    inning,
    is_bottom_inning,
    batter_id,
    pitcher_id,
    batter_hand,
    pitcher_hand,
    outs_before,
    balls,
    strikes,
    start_bases,
    event_code,
    event_text,
    is_at_bat,
    hit_value,
    is_hit,
    is_walk,
    is_strikeout,
    is_home_run,
    runs_on_play,
    rbi,
    source_type,
    now()::timestamptz as created_at,
    now()::timestamptz as updated_at
FROM core.live_events
WHERE is_plate_appearance = true;

-- Create indexes on the materialized view
CREATE INDEX combined_plate_appearances_season_idx
    ON analysis.combined_plate_appearances (season);
CREATE INDEX combined_plate_appearances_batter_idx
    ON analysis.combined_plate_appearances (batter_id);
CREATE INDEX combined_plate_appearances_game_idx
    ON analysis.combined_plate_appearances (game_id);

-- Function to refresh combined data views
CREATE OR REPLACE FUNCTION analysis.refresh_combined_data()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    -- Refresh materialized views
    REFRESH MATERIALIZED VIEW analysis.combined_plate_appearances;

    -- Log the refresh
    INSERT INTO ingest_runs (script_name, status, message, completed_at)
    VALUES ('analysis.refresh_combined_data', 'success',
            'Refreshed combined analysis views', now());
END;
$$;

-- Function to get data source statistics
CREATE OR REPLACE FUNCTION analysis.get_data_source_stats()
RETURNS TABLE (
    data_source text,
    games_count bigint,
    events_count bigint,
    plate_appearances_count bigint,
    latest_game_date text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM (
        SELECT
            'historical'::text as data_source,
            COUNT(*)::bigint as games_count,
            (SELECT COUNT(*) FROM core.events)::bigint as events_count,
            (SELECT COUNT(*) FROM core.plate_appearances)::bigint as plate_appearances_count,
            MAX(game_date)::text as latest_game_date
        FROM core.games

        UNION ALL

        SELECT
            'live'::text as data_source,
            COUNT(*)::bigint as games_count,
            (SELECT COUNT(*) FROM core.live_events)::bigint as events_count,
            (SELECT COUNT(*) FROM core.live_events WHERE is_plate_appearance = true)::bigint as plate_appearances_count,
            MAX(game_date)::text as latest_game_date
        FROM core.live_games

        UNION ALL

        SELECT
            'combined'::text as data_source,
            COUNT(*)::bigint as games_count,
            (SELECT COUNT(*) FROM analysis.combined_events)::bigint as events_count,
            (SELECT COUNT(*) FROM analysis.combined_plate_appearances)::bigint as plate_appearances_count,
            MAX(game_date)::text as latest_game_date
        FROM analysis.combined_games
    ) stats
    ORDER BY data_source;
END;
$$;

-- Function to get recent games from both sources
CREATE OR REPLACE FUNCTION analysis.get_recent_games(days_back integer DEFAULT 7)
RETURNS TABLE (
    game_id text,
    game_date date,
    season integer,
    source_type text,
    home_team_id text,
    away_team_id text,
    home_score integer,
    away_score integer,
    home_win boolean
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        cg.game_id,
        cg.game_date,
        cg.season,
        cg.source_type,
        cg.home_team_id,
        cg.away_team_id,
        cg.home_score,
        cg.away_score,
        cg.home_win
    FROM analysis.combined_games cg
    WHERE cg.game_date >= CURRENT_DATE - INTERVAL '1 day' * days_back
    ORDER BY cg.game_date DESC, cg.game_id;
END;
$$;