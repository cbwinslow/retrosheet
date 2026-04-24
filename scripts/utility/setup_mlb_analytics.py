# MLB Analytical Pipeline
# Views, materialized views, and procedures for MLB data analysis

import os

import psycopg2


def database_kwargs():
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def create_analytical_views():
    """Create analytical views combining MLB and Retrosheet data."""

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Combined games view
            cur.execute("""
                CREATE OR REPLACE VIEW analysis.mlb_combined_games AS
                SELECT
                    lg.game_id,
                    lg.season,
                    lg.game_date,
                    lg.home_team_id,
                    lg.away_team_id,
                    lg.home_team_name,
                    lg.away_team_name,
                    lg.home_score,
                    lg.away_score,
                    lg.is_complete,
                    lg.status_code,
                    lg.detailed_state,
                    lg.venue_name,
                    lg.source_type,
                    lg.mlb_game_pk,
                    -- Link to Retrosheet games via bridge tables
                    rt.game_id as retrosheet_game_id,
                    rt.game_date as retrosheet_date,
                    rt.home_team_id as retrosheet_home_team,
                    rt.away_team_id as retrosheet_away_team
                FROM core.live_games lg
                LEFT JOIN bridge.game_xref gx ON lg.mlb_game_pk = gx.mlb_game_pk
                LEFT JOIN core.games rt ON gx.retrosheet_game_id = rt.game_id;
            """)

            # Combined events view
            cur.execute("""
                CREATE OR REPLACE VIEW analysis.mlb_combined_events AS
                SELECT
                    le.game_id,
                    le.event_sequence,
                    le.mlb_event_type as event_type,
                    le.event_text as event_description,
                    le.inning,
                    le.is_bottom_inning,
                    le.batter_id,
                    le.pitcher_id,
                    le.hit_value,
                    le.runs_on_play as runs_scored,
                    le.rbi as runs_batted_in,
                    le.home_score_after,
                    le.away_score_after,
                    le.is_at_bat,
                    le.is_plate_appearance,
                    le.is_home_run,
                    le.source_type,
                    -- Basic game info
                    g.season,
                    g.home_team_name,
                    g.away_team_name
                FROM core.live_events le
                JOIN core.live_games g ON le.game_id = g.game_id;
            """)

            # Player performance view (MLB data only for now)
            cur.execute("""
                CREATE OR REPLACE VIEW analysis.mlb_player_performance AS
                SELECT
                    p.mlb_id,
                    p.full_name,
                    p.bat_side,
                    p.pitch_hand,
                    -- MLB batting stats
                    COALESCE(mlb_stats.avg, 0) as batting_avg,
                    COALESCE(mlb_stats.hits, 0) as hits,
                    COALESCE(mlb_stats.homers, 0) as home_runs,
                    COALESCE(mlb_stats.rbi, 0) as rbi,
                    COALESCE(mlb_stats.games, 0) as games_played,
                    COALESCE(mlb_stats.plate_appearances, 0) as plate_appearances
                FROM mlb.players p
                LEFT JOIN (
                    SELECT
                        batter_id::bigint,
                        COUNT(DISTINCT game_id) as games,
                        COUNT(CASE WHEN is_plate_appearance THEN 1 END) as plate_appearances,
                        AVG(CASE WHEN is_hit THEN 1.0 ELSE 0.0 END) as avg,
                        COUNT(CASE WHEN is_hit THEN 1 END) as hits,
                        COUNT(CASE WHEN is_home_run THEN 1 END) as homers,
                        SUM(rbi) as rbi
                    FROM core.live_events
                    WHERE batter_id IS NOT NULL
                    GROUP BY batter_id
                ) mlb_stats ON p.mlb_id = mlb_stats.batter_id;
            """)

            # Pitch analysis view
            cur.execute("""
                CREATE OR REPLACE VIEW analysis.mlb_pitch_analysis AS
                SELECT
                    p.game_pk,
                    p.event_index,
                    p.pitch_index,
                    p.pitch_type_code,
                    p.pitch_type_description,
                    p.start_speed,
                    p.spin_rate,
                    p.plate_x,
                    p.plate_z,
                    p.pitch_call_code,
                    -- Player info
                    bat.full_name as batter_name,
                    pit.full_name as pitcher_name,
                    -- Game context
                    g.home_team_name,
                    g.away_team_name,
                    g.game_date,
                    -- Advanced metrics
                    CASE WHEN p.plate_x BETWEEN -0.83 AND 0.83 AND p.plate_z BETWEEN 1.5 AND 3.5 THEN 1 ELSE 0 END as in_zone,
                    CASE WHEN p.pitch_call_code = 'S' THEN 1 ELSE 0 END as swing,
                    CASE WHEN p.pitch_call_code IN ('S', 'F', 'B') THEN 1 ELSE 0 END as decision_pitch
                FROM mlb.pitches p
                JOIN mlb.players bat ON p.batter_id = bat.mlb_id
                JOIN mlb.players pit ON p.pitcher_id = pit.mlb_id
                JOIN core.live_games g ON p.game_pk = g.mlb_game_pk::bigint;
            """)

        conn.commit()
        print('✅ Analytical views created successfully')

    finally:
        conn.close()


def create_materialized_views():
    """Create materialized views for performance-critical queries."""

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Season batting leaders (simplified)
            cur.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS analysis.mlb_season_batting_leaders AS
                SELECT
                    season,
                    batter_id,
                    player_name,
                    team_name,
                    games_played,
                    hits,
                    homers,
                    rbi,
                    batting_avg,
                    ROW_NUMBER() OVER (PARTITION BY season ORDER BY hits DESC) as hits_rank,
                    ROW_NUMBER() OVER (PARTITION BY season ORDER BY homers DESC) as hr_rank,
                    ROW_NUMBER() OVER (PARTITION BY season ORDER BY rbi DESC) as rbi_rank
                FROM (
                    SELECT
                        EXTRACT(YEAR FROM g.game_date::date)::int as season,
                        e.batter_id::bigint as batter_id,
                        p.full_name as player_name,
                        g.home_team_name as team_name,
                        COUNT(DISTINCT g.game_id) as games_played,
                        COUNT(CASE WHEN e.is_hit THEN 1 END) as hits,
                        COUNT(CASE WHEN e.is_home_run THEN 1 END) as homers,
                        COALESCE(SUM(e.rbi), 0) as rbi,
                        ROUND(
                            COUNT(CASE WHEN e.is_hit THEN 1 END)::numeric
                            / NULLIF(COUNT(CASE WHEN e.is_at_bat THEN 1 END), 0),
                            3
                        ) as batting_avg
                    FROM core.live_events e
                    JOIN core.live_games g ON e.game_id = g.game_id
                    JOIN mlb.players p ON e.batter_id::bigint = p.mlb_id
                    WHERE e.batter_id IS NOT NULL
                    GROUP BY EXTRACT(YEAR FROM g.game_date::date)::int, e.batter_id::bigint, p.full_name, g.home_team_name
                    HAVING COUNT(CASE WHEN e.is_at_bat THEN 1 END) >= 50 -- Basic qualification
                ) stats
                ORDER BY season, hits DESC;

                CREATE INDEX IF NOT EXISTS idx_mlb_batting_leaders_season ON analysis.mlb_season_batting_leaders (season);
                CREATE INDEX IF NOT EXISTS idx_mlb_batting_leaders_player ON analysis.mlb_season_batting_leaders (batter_id);
            """)

            # Season pitching leaders (simplified)
            cur.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS analysis.mlb_season_pitching_leaders AS
                SELECT
                    season,
                    pitcher_id,
                    player_name,
                    team_name,
                    games_pitched,
                    hits_allowed,
                    runs_allowed,
                    home_runs_allowed,
                    ROW_NUMBER() OVER (PARTITION BY season ORDER BY games_pitched DESC) as games_rank
                FROM (
                    SELECT
                        EXTRACT(YEAR FROM g.game_date::date)::int as season,
                        e.pitcher_id::bigint as pitcher_id,
                        p.full_name as player_name,
                        g.home_team_name as team_name,
                        COUNT(DISTINCT g.game_id) as games_pitched,
                        COUNT(CASE WHEN e.is_hit THEN 1 END) as hits_allowed,
                        SUM(e.home_score_after - e.away_score_after) as runs_allowed,
                        COUNT(CASE WHEN e.is_home_run THEN 1 END) as home_runs_allowed
                    FROM core.live_events e
                    JOIN core.live_games g ON e.game_id = g.game_id
                    JOIN mlb.players p ON e.pitcher_id::bigint = p.mlb_id
                    WHERE e.pitcher_id IS NOT NULL
                    GROUP BY EXTRACT(YEAR FROM g.game_date::date)::int, e.pitcher_id::bigint, p.full_name, g.home_team_name
                ) stats
                ORDER BY season, games_pitched DESC;

                CREATE INDEX IF NOT EXISTS idx_mlb_pitching_leaders_season ON analysis.mlb_season_pitching_leaders (season);
                CREATE INDEX IF NOT EXISTS idx_mlb_pitching_leaders_player ON analysis.mlb_season_pitching_leaders (pitcher_id);
            """)

            # Team season stats (simplified)
            cur.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS analysis.mlb_team_season_stats AS
                SELECT
                    season,
                    team_name,
                    games_played,
                    wins,
                    losses,
                    win_pct,
                    runs_scored,
                    runs_allowed,
                    ROW_NUMBER() OVER (PARTITION BY season ORDER BY wins DESC) as wins_rank
                FROM (
                    SELECT
                        EXTRACT(YEAR FROM g.game_date::date)::int as season,
                        g.home_team_name as team_name,
                        COUNT(*) as games_played,
                        COUNT(CASE WHEN g.home_score > g.away_score THEN 1 END) as wins,
                        COUNT(CASE WHEN g.home_score < g.away_score THEN 1 END) as losses,
                        ROUND(COUNT(CASE WHEN g.home_score > g.away_score THEN 1 END)::numeric / COUNT(*), 3) as win_pct,
                        SUM(g.home_score) as runs_scored,
                        SUM(g.away_score) as runs_allowed
                    FROM core.live_games g
                    GROUP BY EXTRACT(YEAR FROM g.game_date::date)::int, g.home_team_name
                ) home_stats
                ORDER BY season, wins DESC;

                CREATE INDEX IF NOT EXISTS idx_mlb_team_stats_season ON analysis.mlb_team_season_stats (season);
            """)

        conn.commit()
        print('✅ Materialized views created successfully')

    finally:
        conn.close()


def create_analytical_procedures():
    """Create stored procedures for data analysis and validation."""

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Procedure to refresh materialized views
            cur.execute("""
                CREATE OR REPLACE PROCEDURE analysis.refresh_mlb_analytics()
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    REFRESH MATERIALIZED VIEW analysis.mlb_season_batting_leaders;
                    REFRESH MATERIALIZED VIEW analysis.mlb_season_pitching_leaders;
                    REFRESH MATERIALIZED VIEW analysis.mlb_team_season_stats;

                    RAISE NOTICE 'MLB analytical materialized views refreshed';
                END;
                $$;
            """)

            # Procedure to validate MLB data integrity
            cur.execute("""
                CREATE OR REPLACE PROCEDURE analysis.validate_mlb_data()
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    invalid_games int;
                    missing_players int;
                    orphan_events int;
                BEGIN
                    -- Check for games with invalid scores
                    SELECT COUNT(*) INTO invalid_games
                    FROM core.live_games
                    WHERE home_score < 0 OR away_score < 0;

                    IF invalid_games > 0 THEN
                        RAISE WARNING '% games have invalid scores', invalid_games;
                    END IF;

                    -- Check for events without corresponding games
                    SELECT COUNT(*) INTO orphan_events
                    FROM core.live_events e
                    LEFT JOIN core.live_games g ON e.game_id = g.game_id
                    WHERE g.game_id IS NULL;

                    IF orphan_events > 0 THEN
                        RAISE WARNING '% events have no corresponding game', orphan_events;
                    END IF;

                    -- Check for players referenced but not in player table
                    SELECT COUNT(DISTINCT e.batter_id) INTO missing_players
                    FROM core.live_events e
                    LEFT JOIN mlb.players p ON e.batter_id = p.mlb_id
                    WHERE p.mlb_id IS NULL AND e.batter_id IS NOT NULL;

                    IF missing_players > 0 THEN
                        RAISE WARNING '% players referenced in events but missing from player table', missing_players;
                    END IF;

                    RAISE NOTICE 'MLB data validation complete. Games: %, Orphan events: %, Missing players: %',
                        invalid_games, orphan_events, missing_players;
                END;
                $$;
            """)

            # Function to get player season stats
            cur.execute("""
                CREATE OR REPLACE FUNCTION analysis.get_player_season_stats(
                    player_mlb_id bigint,
                    season_year int
                )
                RETURNS TABLE (
                    games_played int,
                    plate_appearances int,
                    at_bats int,
                    hits int,
                    doubles int,
                    triples int,
                    homers int,
                    rbi int,
                    runs int,
                    batting_avg numeric,
                    slugging_pct numeric,
                    on_base_pct numeric
                )
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    RETURN QUERY
                    SELECT
                        COUNT(DISTINCT g.game_id)::int as games_played,
                        COUNT(CASE WHEN e.is_plate_appearance THEN 1 END)::int as plate_appearances,
                        COUNT(CASE WHEN e.is_at_bat THEN 1 END)::int as at_bats,
                        COUNT(CASE WHEN e.event_result = 'single' THEN 1 END)::int as hits,
                        COUNT(CASE WHEN e.event_result = 'double' THEN 1 END)::int as doubles,
                        COUNT(CASE WHEN e.event_result = 'triple' THEN 1 END)::int as triples,
                        COUNT(CASE WHEN e.event_result = 'home_run' THEN 1 END)::int as homers,
                        COALESCE(SUM(e.runs_batted_in), 0)::int as rbi,
                        COUNT(CASE WHEN e.event_result IN ('single', 'double', 'triple', 'home_run') AND e.is_scoring_play THEN 1 END)::int as runs,
                        ROUND(
                            COUNT(CASE WHEN e.event_result IN ('single', 'double', 'triple', 'home_run') THEN 1 END)::numeric
                            / NULLIF(COUNT(CASE WHEN e.is_at_bat THEN 1 END), 0),
                            3
                        ) as batting_avg,
                        ROUND(
                            (COUNT(CASE WHEN e.event_result IN ('single', 'double', 'triple', 'home_run') THEN 1 END)
                           + COUNT(CASE WHEN e.event_result = 'double' THEN 1 END)
                           + 2 * COUNT(CASE WHEN e.event_result = 'triple' THEN 1 END)
                           + 3 * COUNT(CASE WHEN e.event_result = 'home_run' THEN 1 END))::numeric
                            / NULLIF(COUNT(CASE WHEN e.is_at_bat THEN 1 END), 0),
                            3
                        ) as slugging_pct,
                        ROUND(
                            (COUNT(CASE WHEN e.event_result IN ('single', 'double', 'triple', 'home_run') THEN 1 END))::numeric
                            / NULLIF(COUNT(CASE WHEN e.is_plate_appearance THEN 1 END), 0),
                            3
                        ) as on_base_pct
                    FROM core.live_games g
                    JOIN core.live_events e ON g.game_id = e.game_id
                    WHERE e.batter_id = player_mlb_id
                      AND EXTRACT(YEAR FROM g.game_date::date) = season_year
                      AND e.is_plate_appearance = true;
                END;
                $$;
            """)

            # Function to get team season stats
            cur.execute("""
                CREATE OR REPLACE FUNCTION analysis.get_team_season_stats(
                    team_mlb_id bigint,
                    season_year int
                )
                RETURNS TABLE (
                    games_played int,
                    wins int,
                    losses int,
                    win_pct numeric,
                    runs_scored int,
                    runs_allowed int,
                    run_differential int
                )
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    RETURN QUERY
                    SELECT
                        COUNT(*)::int as games_played,
                        COUNT(CASE WHEN
                            ((g.home_team_id = team_mlb_id AND g.home_score > g.away_score) OR
                             (g.away_team_id = team_mlb_id AND g.away_score > g.home_score))
                            THEN 1 END)::int as wins,
                        COUNT(CASE WHEN
                            ((g.home_team_id = team_mlb_id AND g.home_score < g.away_score) OR
                             (g.away_team_id = team_mlb_id AND g.away_score < g.home_score))
                            THEN 1 END)::int as losses,
                        ROUND(
                            COUNT(CASE WHEN
                                ((g.home_team_id = team_mlb_id AND g.home_score > g.away_score) OR
                                 (g.away_team_id = team_mlb_id AND g.away_score > g.home_score))
                                THEN 1 END)::numeric / COUNT(*),
                            3
                        ) as win_pct,
                        SUM(CASE WHEN g.home_team_id = team_mlb_id THEN g.home_score ELSE g.away_score END)::int as runs_scored,
                        SUM(CASE WHEN g.home_team_id = team_mlb_id THEN g.away_score ELSE g.home_score END)::int as runs_allowed,
                        (SUM(CASE WHEN g.home_team_id = team_mlb_id THEN g.home_score ELSE g.away_score END) -
                         SUM(CASE WHEN g.home_team_id = team_mlb_id THEN g.away_score ELSE g.home_score END))::int as run_differential
                    FROM core.live_games g
                    WHERE (g.home_team_id = team_mlb_id OR g.away_team_id = team_mlb_id)
                      AND EXTRACT(YEAR FROM g.game_date::date) = season_year;
                END;
                $$;
            """)

        conn.commit()
        print('✅ Analytical procedures created successfully')

    finally:
        conn.close()


def create_data_quality_procedures():
    """Create procedures for data quality monitoring and cleanup."""

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Data quality scoring function
            cur.execute("""
                CREATE OR REPLACE FUNCTION analysis.calculate_mlb_data_quality(
                    game_id_param text
                )
                RETURNS numeric(3,2)
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    total_events int;
                    events_with_players int;
                    events_with_results int;
                    score numeric(3,2) := 0.0;
                BEGIN
                    -- Get total events
                    SELECT COUNT(*) INTO total_events
                    FROM core.live_events
                    WHERE game_id = game_id_param;

                    IF total_events = 0 THEN
                        RETURN 0.0;
                    END IF;

                    -- Check events with player data
                    SELECT COUNT(*) INTO events_with_players
                    FROM core.live_events
                    WHERE game_id = game_id_param
                      AND batter_id IS NOT NULL;

                    -- Check events with result data
                    SELECT COUNT(*) INTO events_with_results
                    FROM core.live_events
                    WHERE game_id = game_id_param
                      AND event_result IS NOT NULL;

                    -- Calculate score based on completeness
                    score := score + (events_with_players::numeric / total_events) * 0.5;
                    score := score + (events_with_results::numeric / total_events) * 0.5;

                    RETURN ROUND(score, 2);
                END;
                $$;
            """)

            # Duplicate detection procedure
            cur.execute("""
                CREATE OR REPLACE PROCEDURE analysis.detect_duplicate_games()
                LANGUAGE plpgsql
                AS $$
                DECLARE
                    dup_record record;
                BEGIN
                    RAISE NOTICE 'Checking for duplicate games...';

                    FOR dup_record IN
                        SELECT
                            game_date,
                            home_team_id,
                            away_team_id,
                            COUNT(*) as game_count,
                            array_agg(game_id) as game_ids
                        FROM core.live_games
                        GROUP BY game_date, home_team_id, away_team_id
                        HAVING COUNT(*) > 1
                    LOOP
                        RAISE WARNING 'Duplicate games found on % between teams % and %: % games (%)',
                            dup_record.game_date,
                            dup_record.home_team_id,
                            dup_record.away_team_id,
                            dup_record.game_count,
                            dup_record.game_ids;
                    END LOOP;

                    RAISE NOTICE 'Duplicate detection complete';
                END;
                $$;
            """)

            # Data completeness report
            cur.execute("""
                CREATE OR REPLACE FUNCTION analysis.get_data_completeness_report()
                RETURNS TABLE (
                    data_type text,
                    total_records bigint,
                    complete_records bigint,
                    completeness_pct numeric
                )
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    -- Games completeness
                    RETURN QUERY
                    SELECT
                        'Games'::text as data_type,
                        COUNT(*)::bigint as total_records,
                        COUNT(CASE WHEN home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 END)::bigint as complete_records,
                        ROUND(
                            COUNT(CASE WHEN home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 END)::numeric
                            / NULLIF(COUNT(*), 0) * 100,
                            1
                        ) as completeness_pct
                    FROM core.live_games;

                    -- Events completeness
                    RETURN QUERY
                    SELECT
                        'Events'::text as data_type,
                        COUNT(*)::bigint as total_records,
                        COUNT(CASE WHEN batter_id IS NOT NULL AND event_result IS NOT NULL THEN 1 END)::bigint as complete_records,
                        ROUND(
                            COUNT(CASE WHEN batter_id IS NOT NULL AND event_result IS NOT NULL THEN 1 END)::numeric
                            / NULLIF(COUNT(*), 0) * 100,
                            1
                        ) as completeness_pct
                    FROM core.live_events;

                    -- Players completeness
                    RETURN QUERY
                    SELECT
                        'Players'::text as data_type,
                        COUNT(*)::bigint as total_records,
                        COUNT(CASE WHEN full_name IS NOT NULL AND primary_position IS NOT NULL THEN 1 END)::bigint as complete_records,
                        ROUND(
                            COUNT(CASE WHEN full_name IS NOT NULL AND primary_position IS NOT NULL THEN 1 END)::numeric
                            / NULLIF(COUNT(*), 0) * 100,
                            1
                        ) as completeness_pct
                    FROM mlb.players;
                END;
                $$;
            """)

        conn.commit()
        print('✅ Data quality procedures created successfully')

    finally:
        conn.close()


if __name__ == '__main__':
    print('🚀 Setting up MLB analytical pipeline...')

    create_analytical_views()
    create_materialized_views()
    create_analytical_procedures()
    create_data_quality_procedures()

    print('🎉 MLB analytical pipeline setup complete!')
    print('\nAvailable views:')
    print('- analysis.mlb_combined_games')
    print('- analysis.mlb_combined_events')
    print('- analysis.mlb_player_performance')
    print('- analysis.mlb_pitch_analysis')
    print('\nAvailable materialized views:')
    print('- analysis.mlb_season_batting_leaders')
    print('- analysis.mlb_season_pitching_leaders')
    print('- analysis.mlb_team_season_stats')
    print('\nAvailable procedures:')
    print('- analysis.refresh_mlb_analytics()')
    print('- analysis.validate_mlb_data()')
    print('- analysis.detect_duplicate_games()')
    print('\nAvailable functions:')
    print('- analysis.get_player_season_stats(player_id, season)')
    print('- analysis.get_team_season_stats(team_id, season)')
    print('- analysis.calculate_mlb_data_quality(game_id)')
    print('- analysis.get_data_completeness_report()')
