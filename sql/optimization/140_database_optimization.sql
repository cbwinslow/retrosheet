-- Database Optimization: Indexes, Constraints, and Performance Improvements

-- 1. OPTIMIZE DATA TYPES (keeping text dates as requested)
-- Add season as integer for better indexing where appropriate

-- Add season as integer for better indexing (live_games already has text dates)
ALTER TABLE core.live_games ADD COLUMN IF NOT EXISTS season_int integer;
UPDATE core.live_games SET season_int = season::integer
WHERE season_int IS NULL AND season IS NOT NULL;
CREATE INDEX CONCURRENTLY IF NOT EXISTS live_games_season_int_idx ON core.live_games (season_int);

-- 2. CORE TABLE INDEXES
-- Add essential indexes to core tables for common query patterns

-- Games table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS games_season_idx ON core.games (season);
CREATE INDEX CONCURRENTLY IF NOT EXISTS games_date_idx ON core.games (game_date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS games_season_date_idx ON core.games (season, game_date);
CREATE INDEX CONCURRENTLY IF NOT EXISTS games_home_team_idx ON core.games (home_team_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS games_away_team_idx ON core.games (away_team_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS games_source_type_idx ON core.games (source_type);

-- Events table indexes (most critical for performance)
CREATE INDEX CONCURRENTLY IF NOT EXISTS events_game_id_idx ON core.events (game_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS events_season_idx ON core.events (season);
CREATE INDEX CONCURRENTLY IF NOT EXISTS events_batter_idx ON core.events (batter_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS events_pitcher_idx ON core.events (pitcher_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS events_game_event_idx ON core.events (game_id, event_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS events_season_batter_idx ON core.events (season, batter_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS events_season_pitcher_idx ON core.events (season, pitcher_id);

-- Live events table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS live_events_game_id_idx ON core.live_events (game_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS live_events_season_idx ON core.live_events (season);
CREATE INDEX CONCURRENTLY IF NOT EXISTS live_events_batter_idx ON core.live_events (batter_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS live_events_pitcher_idx ON core.live_events (pitcher_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS live_events_game_event_idx ON core.live_events (game_id, event_id);

-- Plate appearances table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS plate_appearances_game_id_idx ON core.plate_appearances (game_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS plate_appearances_season_idx ON core.plate_appearances (season);
CREATE INDEX CONCURRENTLY IF NOT EXISTS plate_appearances_batter_idx ON core.plate_appearances (batter_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS plate_appearances_pitcher_idx ON core.plate_appearances (pitcher_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS plate_appearances_season_batter_idx ON core.plate_appearances (season, batter_id);

-- Players table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS players_retrosheet_id_idx ON core.players (retrosheet_player_id);

-- Teams table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS teams_retrosheet_id_idx ON core.teams (retrosheet_team_id);

-- 3. FOREIGN KEY CONSTRAINTS
-- Add referential integrity constraints where appropriate

-- Games table foreign keys
ALTER TABLE core.games ADD CONSTRAINT games_home_team_fk
FOREIGN KEY (home_team_id) REFERENCES core.teams (retrosheet_team_id);
ALTER TABLE core.games ADD CONSTRAINT games_away_team_fk
FOREIGN KEY (away_team_id) REFERENCES core.teams (retrosheet_team_id);
ALTER TABLE core.games ADD CONSTRAINT games_park_fk
FOREIGN KEY (park_id) REFERENCES core.parks (retrosheet_park_id);

-- Events table foreign keys (careful - these can be expensive to add)
-- Consider adding these after initial load
-- ALTER TABLE core.events ADD CONSTRAINT events_batter_fk
--     FOREIGN KEY (batter_id) REFERENCES core.players (retrosheet_player_id);
-- ALTER TABLE core.events ADD CONSTRAINT events_pitcher_fk
--     FOREIGN KEY (pitcher_id) REFERENCES core.players (retrosheet_player_id);

-- 4. CHECK CONSTRAINTS
-- Add data validation constraints

ALTER TABLE core.games ADD CONSTRAINT games_scores_positive
CHECK (home_score >= 0 AND away_score >= 0);
ALTER TABLE core.games ADD CONSTRAINT games_season_valid
CHECK (season ~ '^[0-9]{4}$');

ALTER TABLE core.live_games ADD CONSTRAINT live_games_scores_positive
CHECK (home_score >= 0 AND away_score >= 0);

ALTER TABLE core.events ADD CONSTRAINT events_inning_valid
CHECK (inning >= 1 AND inning <= 25);
ALTER TABLE core.events ADD CONSTRAINT events_event_sequence_positive
CHECK (event_sequence > 0);

-- 5. OPTIMIZE MATERIALIZED VIEWS
-- Add more comprehensive indexes to existing materialized views

-- Refresh existing materialized view with better indexing
DROP MATERIALIZED VIEW IF EXISTS analysis.combined_plate_appearances;
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
    created_at
FROM core.plate_appearances

UNION ALL

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
    created_at
FROM core.live_events
WHERE is_plate_appearance = TRUE;

-- Better indexes on the materialized view
CREATE INDEX combined_pa_season_idx ON analysis.combined_plate_appearances (season);
CREATE INDEX combined_pa_batter_idx ON analysis.combined_plate_appearances (batter_id);
CREATE INDEX combined_pa_pitcher_idx ON analysis.combined_plate_appearances (pitcher_id);
CREATE INDEX combined_pa_game_season_batter_idx ON analysis.combined_plate_appearances (game_id, season, batter_id);

-- 6. QUERY OPTIMIZATION FUNCTIONS
-- Add functions for common optimized queries

CREATE OR REPLACE FUNCTION analysis.get_player_game_stats(
    player_id text,
    start_date date DEFAULT CURRENT_DATE - interval '30 days',
    end_date date DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    game_date date,
    game_id text,
    is_home boolean,
    team_id text,
    opponent_id text,
    plate_appearances bigint,
    hits bigint,
    home_runs bigint,
    rbi bigint,
    walks bigint,
    strikeouts bigint
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        g.game_date,
        g.game_id,
        CASE WHEN g.home_team_id = p.team_id THEN true ELSE false END as is_home,
        p.team_id,
        CASE WHEN g.home_team_id = p.team_id THEN g.away_team_id ELSE g.home_team_id END as opponent_id,
        COUNT(*) as plate_appearances,
        COUNT(*) FILTER (WHERE pa.is_hit) as hits,
        COUNT(*) FILTER (WHERE pa.is_home_run) as home_runs,
        SUM(pa.rbi) as rbi,
        COUNT(*) FILTER (WHERE pa.is_walk) as walks,
        COUNT(*) FILTER (WHERE pa.is_strikeout) as strikeouts
    FROM analysis.combined_plate_appearances pa
    JOIN analysis.combined_games g ON pa.game_id = g.game_id
    JOIN (
        SELECT game_id, batter_id, CASE WHEN home_team_id = away_team_id THEN home_team_id ELSE
            CASE WHEN batter_id IN (
                SELECT DISTINCT batter_id FROM core.events e
                JOIN core.games g2 ON e.game_id = g2.game_id
                WHERE g2.home_team_id = g.home_team_id
            ) THEN g.home_team_id ELSE g.away_team_id END
        END as team_id
        FROM analysis.combined_games g
        CROSS JOIN (SELECT DISTINCT batter_id FROM analysis.combined_plate_appearances WHERE batter_id = $1) b
    ) p ON pa.game_id = p.game_id AND pa.batter_id = p.batter_id
    WHERE pa.batter_id = $1
    AND g.game_date BETWEEN $2 AND $3
    GROUP BY g.game_date, g.game_id, p.team_id, g.home_team_id, g.away_team_id
    ORDER BY g.game_date DESC;
$$;

-- 7. PARTITIONING (for very large tables - optional)
-- Consider partitioning events table by season if it becomes extremely large

-- CREATE TABLE core.events_y2024 PARTITION OF core.events
--     FOR VALUES FROM ('2024') TO ('2025');
-- CREATE TABLE core.events_y2025 PARTITION OF core.events
--     FOR VALUES FROM ('2025') TO ('2026');

-- 8. STATISTICS AND ANALYZE
-- Update table statistics for better query planning

ANALYZE core.games;
ANALYZE core.events;
ANALYZE core.live_games;
ANALYZE core.live_events;
ANALYZE core.plate_appearances;
ANALYZE analysis.combined_games;
ANALYZE analysis.combined_events;
ANALYZE analysis.combined_plate_appearances;

-- 9. OPTIMIZE VIEW DEFINITIONS
-- Create optimized versions of analysis views

-- Optimized combined_games view with explicit column ordering (keeping text dates)
CREATE OR REPLACE VIEW analysis.combined_games_optimized AS
SELECT
    game_id,
    season,
    source_type,
    game_date,
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
    season,
    source_type,
    game_date,
    NULL::smallint AS game_number,
    NULL::text AS day_of_week,
    NULL::text AS start_time,
    NULL::text AS doubleheader_flag,
    NULL::text AS day_night,
    away_team_id,
    home_team_id,
    park_id,
    NULL::text AS away_starting_pitcher_id,
    NULL::text AS home_starting_pitcher_id,
    NULL::integer AS attendance,
    NULL::integer AS temperature_f,
    NULL::text AS wind_direction,
    NULL::integer AS wind_speed_mph,
    NULL::text AS field_condition,
    NULL::text AS precipitation,
    NULL::text AS sky_condition,
    NULL::integer AS duration_minutes,
    NULL::integer AS innings,
    away_score,
    home_score,
    NULL::integer AS away_hits,
    NULL::integer AS home_hits,
    NULL::integer AS away_errors,
    NULL::integer AS home_errors,
    NULL::integer AS away_lob,
    NULL::integer AS home_lob,
    NULL::text AS winning_team_id,
    (home_score > away_score) AS home_win,
    NULL::text AS win_pitcher_id,
    NULL::text AS loss_pitcher_id,
    NULL::text AS save_pitcher_id,
    NULL::timestamptz AS raw_loaded_at,
    created_at,
    updated_at
FROM core.live_games;

-- 10. MONITORING AND MAINTENANCE
-- Add maintenance functions

CREATE OR REPLACE FUNCTION maintenance.reindex_slow_tables()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    table_record record;
BEGIN
    -- Reindex tables that might have fragmented indexes
    FOR table_record IN
        SELECT schemaname, tablename
        FROM pg_stat_user_tables
        WHERE schemaname IN ('core', 'analysis')
        ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC
        LIMIT 5
    LOOP
        EXECUTE format('REINDEX TABLE CONCURRENTLY %I.%I', table_record.schemaname, table_record.tablename);
        RAISE NOTICE 'Reindexed %.%', table_record.schemaname, table_record.tablename;
    END LOOP;
END;
$$;

-- Vacuum analyze for maintenance
CREATE OR REPLACE FUNCTION maintenance.vacuum_analyze_all()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    table_record record;
BEGIN
    FOR table_record IN
        SELECT schemaname, tablename
        FROM pg_tables
        WHERE schemaname IN ('core', 'analysis', 'features')
        AND tablename NOT LIKE 'pg_%'
    LOOP
        EXECUTE format('VACUUM ANALYZE %I.%I', table_record.schemaname, table_record.tablename);
        RAISE NOTICE 'Vacuum analyzed %.%', table_record.schemaname, table_record.tablename;
    END LOOP;
END;
$$;
