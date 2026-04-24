-- File: sql/optimization/143_advanced_optimizations.sql
-- Purpose: Advanced optimizations: partitioning, clustering, monitoring
-- Author: Agent Cascade
-- Date: 2026-04-24
CREATE TABLE core.events_partitioned (
    game_id text NOT NULL,
    event_id integer NOT NULL,
    season text NOT NULL,
    source_type text NOT NULL,
    event_sequence integer,
    inning integer,
    is_bottom_inning boolean,
    outs_before integer,
    balls integer,
    strikes integer,
    away_score_before integer,
    home_score_before integer,
    batting_team_id text,
    fielding_team_id text,
    batter_id text,
    batter_hand text,
    pitcher_id text,
    pitcher_hand text,
    event_code text,
    event_text text,
    is_plate_appearance boolean,
    is_at_bat boolean,
    hit_value integer,
    is_hit boolean,
    is_walk boolean,
    is_strikeout boolean,
    is_home_run boolean,
    outs_on_play integer,
    runs_on_play integer,
    rbi integer,
    start_bases integer,
    end_bases integer,
    away_score_after integer,
    home_score_after integer,
    game_pa_count integer,
    half_inning_pa_count integer,
    is_new_plate_appearance boolean,
    is_inning_start boolean,
    is_inning_end boolean,
    is_game_end boolean,
    raw_loaded_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
) PARTITION BY LIST (season);

-- Create partitions for recent seasons (adjust as needed)
CREATE TABLE core.events_2020 PARTITION OF core.events_partitioned FOR VALUES IN ('2020');
CREATE TABLE core.events_2021 PARTITION OF core.events_partitioned FOR VALUES IN ('2021');
CREATE TABLE core.events_2022 PARTITION OF core.events_partitioned FOR VALUES IN ('2022');
CREATE TABLE core.events_2023 PARTITION OF core.events_partitioned FOR VALUES IN ('2023');
CREATE TABLE core.events_2024 PARTITION OF core.events_partitioned FOR VALUES IN ('2024');
CREATE TABLE core.events_2025 PARTITION OF core.events_partitioned FOR VALUES IN ('2025');

-- Create a default partition for any other seasons
CREATE TABLE core.events_default PARTITION OF core.events_partitioned DEFAULT;

-- Add indexes to partitioned table (these will automatically apply to partitions)
CREATE INDEX events_partitioned_game_id_idx ON core.events_partitioned (game_id);
CREATE INDEX events_partitioned_season_batter_idx ON core.events_partitioned (season, batter_id);
CREATE INDEX events_partitioned_season_pitcher_idx ON core.events_partitioned (season, pitcher_id);
CREATE INDEX events_partitioned_created_at_idx ON core.events_partitioned (created_at);

-- To migrate existing data (run this after creating partitions):
-- INSERT INTO core.events_partitioned SELECT * FROM core.events;

-- =============================================================================
-- 2. TABLE CLUSTERING (Physical Data Organization)
-- =============================================================================

-- Cluster tables by their most commonly used indexes for better performance
-- This physically reorders the table data to match index order

-- Cluster games table by season+date (most common query pattern)
ALTER TABLE core.games CLUSTER ON games_season_date_idx;

-- Cluster events table by game_id (most common join)
ALTER TABLE core.events CLUSTER ON events_game_id_idx;

-- Cluster live_games by date for time-based queries
ALTER TABLE core.live_games CLUSTER ON live_games_date_parsed_idx;

-- =============================================================================
-- 3. MATERIALIZED VIEWS FOR COMMON AGGREGATIONS
-- =============================================================================

-- Materialized view for player career stats (refreshed daily)
CREATE MATERIALIZED VIEW analysis.player_career_stats AS
SELECT
    batter_id,
    count(*) AS plate_appearances,
    count(*) FILTER (WHERE is_hit) AS hits,
    count(*) FILTER (WHERE is_home_run) AS home_runs,
    sum(rbi) AS rbi,
    count(*) FILTER (WHERE is_walk) AS walks,
    count(*) FILTER (WHERE is_strikeout) AS strikeouts,
    round(avg(is_hit::numeric), 3) AS batting_average,
    sum(runs_on_play) AS runs_created,
    count(DISTINCT game_id) AS games_played,
    min(season) AS first_season,
    max(season) AS last_season
FROM analysis.combined_plate_appearances
WHERE is_plate_appearance = true
GROUP BY batter_id
HAVING count(*) >= 100; -- Only include players with significant plate appearances

-- Indexes for the materialized view
CREATE INDEX player_career_stats_batter_idx ON analysis.player_career_stats (batter_id);
CREATE INDEX player_career_stats_pa_idx ON analysis.player_career_stats (plate_appearances DESC);

-- Materialized view for team season stats
CREATE MATERIALIZED VIEW analysis.team_season_stats AS
SELECT
    season,
    home_team_id AS team_id,
    count(*) AS games_played,
    count(*) FILTER (WHERE home_win) AS wins,
    count(*) FILTER (WHERE NOT home_win) AS losses,
    round(avg(home_win::numeric), 3) AS win_percentage,
    sum(home_score) AS runs_scored,
    sum(away_score) AS runs_allowed,
    round(avg(home_score::numeric), 1) AS avg_runs_scored,
    round(avg(away_score::numeric), 1) AS avg_runs_allowed
FROM analysis.combined_games
GROUP BY season, home_team_id

UNION ALL

SELECT
    season,
    away_team_id AS team_id,
    count(*) AS games_played,
    count(*) FILTER (WHERE NOT home_win) AS wins,
    count(*) FILTER (WHERE home_win) AS losses,
    round(avg((NOT home_win)::numeric), 3) AS win_percentage,
    sum(away_score) AS runs_scored,
    sum(home_score) AS runs_allowed,
    round(avg(away_score::numeric), 1) AS avg_runs_scored,
    round(avg(home_score::numeric), 1) AS avg_runs_allowed
FROM analysis.combined_games
GROUP BY season, away_team_id;

-- Indexes for team stats
CREATE INDEX team_season_stats_season_team_idx ON analysis.team_season_stats (season, team_id);
CREATE INDEX team_season_stats_win_pct_idx ON analysis.team_season_stats (win_percentage DESC);

-- =============================================================================
-- 4. ADVANCED QUERY OPTIMIZATION FUNCTIONS
-- =============================================================================

-- Function to get optimized player vs pitcher matchups
CREATE OR REPLACE FUNCTION analysis.get_pitcher_vs_batter_stats(
    pitcher_id text,
    batter_id text,
    min_plate_appearances integer DEFAULT 5
)
RETURNS TABLE (
    plate_appearances integer,
    hits integer,
    home_runs integer,
    walks integer,
    strikeouts integer,
    avg numeric,
    obp numeric,
    slg numeric,
    last_faced_date text
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        COUNT(*) as plate_appearances,
        COUNT(*) FILTER (WHERE is_hit) as hits,
        COUNT(*) FILTER (WHERE is_home_run) as home_runs,
        COUNT(*) FILTER (WHERE is_walk) as walks,
        COUNT(*) FILTER (WHERE is_strikeout) as strikeouts,
        ROUND(AVG(is_hit::numeric), 3) as avg,
        ROUND(AVG((is_hit::integer + is_walk::integer)::numeric), 3) as obp,
        ROUND(AVG(is_hit::numeric), 3) as slg, -- Simplified SLG
        MAX(game_date) as last_faced_date
    FROM analysis.combined_plate_appearances
    WHERE pitcher_id = $1 AND batter_id = $2 AND is_plate_appearance = true
    GROUP BY pitcher_id, batter_id
    HAVING COUNT(*) >= $3;
$$;

-- Function for real-time game state queries (optimized for live scoring)
CREATE OR REPLACE FUNCTION analysis.get_live_game_state(game_id_param text)
RETURNS TABLE (
    inning integer,
    is_bottom_inning boolean,
    home_score integer,
    away_score integer,
    outs integer,
    runners_on_base integer,
    current_batter text,
    current_pitcher text,
    last_play text,
    game_status text
)
LANGUAGE sql
STABLE
AS $$
    WITH latest_event AS (
        SELECT * FROM analysis.combined_events
        WHERE game_id = game_id_param
        ORDER BY event_id DESC
        LIMIT 1
    ),
    game_info AS (
        SELECT * FROM analysis.combined_games
        WHERE game_id = game_id_param
    )
    SELECT
        le.inning,
        le.is_bottom_inning,
        g.home_score,
        g.away_score,
        le.outs_before,
        le.start_bases as runners_on_base,
        le.batter_id as current_batter,
        le.pitcher_id as current_pitcher,
        le.event_text as last_play,
        CASE
            WHEN g.home_score > g.away_score THEN 'Home team winning'
            WHEN g.away_score > g.home_score THEN 'Away team winning'
            ELSE 'Tied'
        END as game_status
    FROM latest_event le
    CROSS JOIN game_info g;
$$;

-- =============================================================================
-- 5. DATABASE MAINTENANCE FUNCTIONS
-- =============================================================================

-- Function to refresh all materialized views
CREATE OR REPLACE FUNCTION maintenance.refresh_all_materialized_views()
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    mv_record record;
BEGIN
    FOR mv_record IN
        SELECT schemaname, matviewname
        FROM pg_matviews
        WHERE schemaname IN ('analysis')
    LOOP
        EXECUTE format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I.%I', mv_record.schemaname, mv_record.matviewname);
        RAISE NOTICE 'Refreshed materialized view %.%', mv_record.schemaname, mv_record.matviewname;
    END LOOP;
END;
$$;

-- Function to analyze table bloat and suggest optimizations
CREATE OR REPLACE FUNCTION maintenance.analyze_table_bloat()
RETURNS TABLE (
    schemaname text,
    tablename text,
    estimated_bloat_mb numeric,
    fill_factor integer,
    last_vacuum timestamptz,
    last_analyze timestamptz
)
LANGUAGE sql
AS $$
    SELECT
        ps.schemaname,
        ps.tablename,
        ROUND(ps.n_dead_tup * 8 / 1024.0 / 1024.0, 2) as estimated_bloat_mb,
        ps.fillfactor as fill_factor,
        ps.last_vacuum,
        ps.last_analyze
    FROM pg_stat_user_tables ps
    WHERE ps.schemaname IN ('core', 'analysis', 'features')
    ORDER BY estimated_bloat_mb DESC;
$$;

-- =============================================================================
-- 6. PERFORMANCE MONITORING FUNCTIONS
-- =============================================================================

-- Function to get slow query insights
CREATE OR REPLACE FUNCTION monitoring.get_slow_queries(
    min_duration_seconds numeric DEFAULT 1.0,
    limit_rows integer DEFAULT 10
)
RETURNS TABLE (
    query text,
    calls bigint,
    total_time numeric,
    mean_time numeric,
    rows_affected bigint
)
LANGUAGE sql
AS $$
    SELECT
        LEFT(query, 100) as query,
        calls,
        ROUND(total_time::numeric, 2) as total_time,
        ROUND(mean_time::numeric, 2) as mean_time,
        rows as rows_affected
    FROM pg_stat_statements
    WHERE mean_time > $1 * 1000  -- Convert to milliseconds
    ORDER BY mean_time DESC
    LIMIT $2;
$$;

-- Function to get index usage statistics
CREATE OR REPLACE FUNCTION monitoring.get_index_usage()
RETURNS TABLE (
    schemaname text,
    tablename text,
    indexname text,
    idx_scan bigint,
    idx_tup_read bigint,
    idx_tup_fetch bigint,
    last_used timestamptz
)
LANGUAGE sql
AS $$
    SELECT
        ps.schemaname,
        ps.tablename,
        ps.indexname,
        ps.idx_scan,
        ps.idx_tup_read,
        ps.idx_tup_fetch,
        CASE
            WHEN ps.idx_scan > 0 THEN now() - interval '1 second' * extract(epoch from (now() - ps.last_idx_scan))
            ELSE NULL
        END as last_used
    FROM pg_stat_user_indexes ps
    WHERE ps.schemaname IN ('core', 'analysis', 'features')
    ORDER BY ps.idx_scan DESC;
$$;

-- =============================================================================
-- 7. ARCHIVAL STRATEGY (For Historical Data Management)
-- =============================================================================

-- Function to archive old seasons to separate tables
CREATE OR REPLACE FUNCTION maintenance.archive_old_season(
    target_season text
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    archive_table_name text := 'archive.games_' || target_season;
    archive_events_name text := 'archive.events_' || target_season;
BEGIN
    -- Create archive schema if it doesn't exist
    CREATE SCHEMA IF NOT EXISTS archive;

    -- Create archive tables
    EXECUTE format('CREATE TABLE %I (LIKE core.games INCLUDING ALL)', archive_table_name);
    EXECUTE format('CREATE TABLE %I (LIKE core.events INCLUDING ALL)', archive_events_name);

    -- Move data
    EXECUTE format('INSERT INTO %I SELECT * FROM core.games WHERE season = %L', archive_table_name, target_season);
    EXECUTE format('INSERT INTO %I SELECT * FROM core.events WHERE season = %L', archive_events_name, target_season);

    -- Remove from main tables
    EXECUTE format('DELETE FROM core.events WHERE season = %L', target_season);
    EXECUTE format('DELETE FROM core.games WHERE season = %L', target_season);

    -- Add indexes to archive tables
    EXECUTE format('CREATE INDEX ON %I (game_id)', archive_table_name);
    EXECUTE format('CREATE INDEX ON %I (game_id)', archive_events_name);

    RAISE NOTICE 'Archived season % to tables %.%', target_season, archive_table_name, archive_events_name;
END;
$$;

-- =============================================================================
-- 8. CONNECTION POOLING CONFIGURATION (pgBouncer example)
-- =============================================================================

/*
For high-concurrency applications, consider using pgBouncer for connection pooling:

pgbouncer.ini configuration:

[databases]
retrosheet = host=localhost port=5432 dbname=retrosheet

[pgbouncer]
listen_port = 6432
listen_addr = localhost
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
reserve_pool_size = 5
*/

-- =============================================================================
-- 9. POSTGRESQL CONFIGURATION OPTIMIZATIONS
-- =============================================================================

/*
Add to postgresql.conf for better performance:

# Memory Configuration
shared_buffers = 256MB                    # 25% of RAM
effective_cache_size = 1GB               # 75% of RAM
work_mem = 4MB                           # Per-connection working memory
maintenance_work_mem = 64MB              # For VACUUM, etc.

# Checkpoint Configuration
checkpoint_completion_target = 0.9
wal_buffers = 16MB
max_wal_size = 1GB
min_wal_size = 80MB

# Query Planning
random_page_cost = 1.1                   # For SSD storage
effective_io_concurrency = 200           # For SSD storage

# Logging (for monitoring)
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_statement = 'ddl'
log_duration = on
log_min_duration_statement = 1000        # Log queries > 1 second
*/

-- =============================================================================
-- 10. APPLICATION-LEVEL CACHING STRATEGY
-- =============================================================================

/*
For frequently accessed data, consider Redis caching:

1. Player stats cache (TTL: 1 hour)
   Key: player:{player_id}:stats:{season}
   Value: JSON of player statistics

2. Game state cache (TTL: 5 minutes)
   Key: game:{game_id}:state
   Value: Current game state JSON

3. Team standings cache (TTL: 15 minutes)
   Key: standings:{season}
   Value: Current standings JSON

Example Redis commands:
SET player:aaronha01:stats:2024 '{"avg": 0.305, "hr": 45, ...}' EX 3600
GET game:123456:state
*/

-- =============================================================================
-- 11. MONITORING DASHBOARD QUERIES
-- =============================================================================

-- System health monitoring
CREATE OR REPLACE FUNCTION monitoring.get_system_health()
RETURNS TABLE (
    metric text,
    value text,
    status text
)
LANGUAGE sql
AS $$
    SELECT 'Database Size'::text, pg_size_pretty(pg_database_size(current_database()))::text, 'info'::text
    UNION ALL
    SELECT 'Active Connections'::text, count(*)::text, CASE WHEN count(*) > 50 THEN 'warning' ELSE 'ok' END
    FROM pg_stat_activity
    UNION ALL
    SELECT 'Cache Hit Ratio'::text,
           ROUND((sum(blks_hit) * 100.0 / (sum(blks_hit) + sum(blks_read))), 1)::text || '%',
           CASE WHEN (sum(blks_hit) * 100.0 / (sum(blks_hit) + sum(blks_read))) > 95 THEN 'good'
                WHEN (sum(blks_hit) * 100.0 / (sum(blks_hit) + sum(blks_read))) > 90 THEN 'ok'
                ELSE 'warning' END
    FROM pg_stat_database
    UNION ALL
    SELECT 'Long Running Queries'::text, count(*)::text,
           CASE WHEN count(*) > 5 THEN 'warning' ELSE 'ok' END
    FROM pg_stat_activity
    WHERE state = 'active' AND now() - query_start > interval '30 seconds';
$$;

-- Table comments
COMMENT ON TABLE core.events_partitioned IS 'events partitioned data table';
COMMENT ON TABLE core.events_2020 IS 'events 2020 data table';
COMMENT ON TABLE core.events_2021 IS 'events 2021 data table';
COMMENT ON TABLE core.events_2022 IS 'events 2022 data table';
COMMENT ON TABLE core.events_2023 IS 'events 2023 data table';
COMMENT ON TABLE core.events_2024 IS 'events 2024 data table';
COMMENT ON TABLE core.events_2025 IS 'events 2025 data table';
COMMENT ON TABLE core.events_default IS 'events default data table';
