#!/usr/bin/env python3
"""
Database Optimization Script - Apply Advanced Performance Improvements

This script applies various database optimizations including:
- Materialized view creation and refresh
- Table clustering
- Performance monitoring setup
- Query optimization validation
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import psycopg2


ROOT = Path(__file__).resolve().parents[1]


def database_kwargs() -> dict[str, str]:
    return {
        'host': 'localhost',
        'port': '5432',
        'dbname': 'retrosheet',
        'user': 'postgres',
        'password': '',
    }


def run_sql_file(file_path: Path, description: str) -> bool:
    """Run a SQL file and report results."""
    print(f'\n🔧 {description}')
    print(f'Running {file_path.name}...')

    try:
        conn = psycopg2.connect(**database_kwargs())
        with conn.cursor() as cur:
            with file_path.open('r') as f:
                sql = f.read()
            cur.execute(sql)
        conn.commit()
        print(f'✅ {description} completed successfully')
        return True
    except Exception as e:
        print(f'❌ Error in {description}: {e}')
        return False
    finally:
        if 'conn' in locals():
            conn.close()


def test_query_performance(query: str, description: str) -> float:
    """Test query performance and return execution time."""
    print(f'\n⚡ Testing: {description}')

    try:
        conn = psycopg2.connect(**database_kwargs())
        with conn.cursor() as cur:
            start_time = time.time()
            cur.execute(query)
            result = cur.fetchall()
            end_time = time.time()

            execution_time = end_time - start_time
            print(f'   Query returned {len(result)} rows in {execution_time:.3f} seconds')
            return execution_time
    except Exception as e:
        print(f'   Error: {e}')
        return float('inf')
    finally:
        if 'conn' in locals():
            conn.close()


def run_performance_tests() -> None:
    """Run performance tests before and after optimizations."""
    print('🧪 RUNNING PERFORMANCE TESTS')

    test_queries = [
        (
            "SELECT COUNT(*) FROM analysis.combined_games WHERE game_date >= '2024-01-01'",
            'Combined games date filter',
        ),
        (
            "SELECT COUNT(*) FROM core.events WHERE season = '2024' AND batter_id LIKE 'trou%'",
            'Events with season + batter filter',
        ),
        (
            "SELECT batter_id, COUNT(*) as pa FROM analysis.combined_plate_appearances WHERE season = '2024' GROUP BY batter_id ORDER BY pa DESC LIMIT 10",
            'Top batters by plate appearances',
        ),
        (
            'SELECT * FROM analysis.get_data_source_stats()',
            'Data source statistics function',
        ),
        (
            'SELECT game_id, COUNT(*) as events FROM analysis.combined_events GROUP BY game_id ORDER BY events DESC LIMIT 5',
            'Games with most events',
        ),
    ]

    for query, description in test_queries:
        execution_time = test_query_performance(query, description)
        if execution_time < 1.0:
            status = '🚀'
        elif execution_time < 5.0:
            status = '✅'
        else:
            status = '⚠️'

        print(f'   {status} {execution_time:.3f}s')


def apply_materialized_views() -> bool:
    """Apply materialized view optimizations."""
    # Simplified materialized view without problematic casting
    mv_sql = """
-- Materialized view for player career stats (simplified)
CREATE MATERIALIZED VIEW IF NOT EXISTS analysis.player_career_stats AS
SELECT
    batter_id,
    COUNT(*) as plate_appearances,
    COUNT(*) FILTER (WHERE is_hit) as hits,
    COUNT(*) FILTER (WHERE is_home_run) as home_runs,
    SUM(rbi) as rbi,
    COUNT(*) FILTER (WHERE is_walk) as walks,
    COUNT(*) FILTER (WHERE is_strikeout) as strikeouts,
    COUNT(DISTINCT game_id) as games_played,
    MIN(season) as first_season,
    MAX(season) as last_season
FROM analysis.combined_plate_appearances
WHERE is_plate_appearance = true
GROUP BY batter_id
HAVING COUNT(*) >= 100;

-- Indexes for player career stats
CREATE INDEX IF NOT EXISTS player_career_stats_batter_idx ON analysis.player_career_stats (batter_id);
CREATE INDEX IF NOT EXISTS player_career_stats_pa_idx ON analysis.player_career_stats (plate_appearances DESC);
"""

    try:
        conn = psycopg2.connect(**database_kwargs())
        with conn.cursor() as cur:
            cur.execute(mv_sql)
        conn.commit()
        print('✅ Materialized views created successfully')
        return True
    except Exception as e:
        print(f'❌ Error creating materialized views: {e}')
        return False
    finally:
        if 'conn' in locals():
            conn.close()


def apply_table_clustering() -> bool:
    """Apply table clustering optimizations."""
    cluster_sql = """
-- Cluster tables by most commonly used indexes
ALTER TABLE core.games CLUSTER ON games_season_date_idx;
ALTER TABLE core.events CLUSTER ON events_game_id_idx;
ALTER TABLE core.live_games CLUSTER ON live_games_date_parsed_idx;
"""

    try:
        conn = psycopg2.connect(**database_kwargs())
        with conn.cursor() as cur:
            cur.execute(cluster_sql)
        conn.commit()
        print('✅ Table clustering applied successfully')
        return True
    except Exception as e:
        print(f'❌ Error applying table clustering: {e}')
        return False
    finally:
        if 'conn' in locals():
            conn.close()


def apply_monitoring_setup() -> bool:
    """Apply monitoring and maintenance functions."""
    monitoring_sql = """
-- Create monitoring schema
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Function to get index usage statistics (works without pg_stat_statements)
CREATE OR REPLACE FUNCTION monitoring.get_index_usage()
RETURNS TABLE (
    schemaname text,
    tablename text,
    indexname text,
    idx_scan bigint,
    idx_tup_read bigint,
    idx_tup_fetch bigint
)
LANGUAGE sql
AS $$
    SELECT
        ps.schemaname,
        ps.tablename,
        ps.indexname,
        ps.idx_scan,
        ps.idx_tup_read,
        ps.idx_tup_fetch
    FROM pg_stat_user_indexes ps
    WHERE ps.schemaname IN ('core', 'analysis', 'features')
    ORDER BY ps.idx_scan DESC;
$$;

-- Function to get table size information
CREATE OR REPLACE FUNCTION monitoring.get_table_sizes()
RETURNS TABLE (
    schemaname text,
    tablename text,
    table_size text,
    index_size text,
    total_size text
)
LANGUAGE sql
AS $$
    SELECT
        schemaname,
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as table_size,
        pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as index_size,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size
    FROM pg_tables
    WHERE schemaname IN ('core', 'analysis', 'features')
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
$$;
"""

    try:
        conn = psycopg2.connect(**database_kwargs())
        with conn.cursor() as cur:
            cur.execute(monitoring_sql)
        conn.commit()
        print('✅ Monitoring functions created successfully')
        return True
    except Exception as e:
        print(f'❌ Error creating monitoring functions: {e}')
        return False
    finally:
        if 'conn' in locals():
            conn.close()


def run_vacuum_analyze() -> bool:
    """Run VACUUM ANALYZE on all tables for better query planning."""
    print('\n🧹 Running VACUUM ANALYZE on all tables...')

    # VACUUM can't run in transactions, so we'll run individual commands
    vacuum_commands = [
        'VACUUM ANALYZE core.games;',
        'VACUUM ANALYZE core.events;',
        'VACUUM ANALYZE core.live_games;',
        'VACUUM ANALYZE core.live_events;',
        'VACUUM ANALYZE core.plate_appearances;',
        'VACUUM ANALYZE analysis.combined_games;',
        'VACUUM ANALYZE analysis.combined_events;',
        'VACUUM ANALYZE analysis.combined_plate_appearances;',
    ]

    success_count = 0
    for cmd in vacuum_commands:
        try:
            conn = psycopg2.connect(**database_kwargs())
            conn.autocommit = True  # VACUUM must be autocommit
            with conn.cursor() as cur:
                cur.execute(cmd)
            success_count += 1
        except Exception as e:
            print(f'   Warning: Failed to VACUUM {cmd.split()[2]}: {e}')
        finally:
            if 'conn' in locals():
                conn.close()

    if success_count > 0:
        print(f'✅ VACUUM ANALYZE completed on {success_count}/{len(vacuum_commands)} tables')
        return True
    print('❌ VACUUM ANALYZE failed on all tables')
    return False


def main():
    parser = argparse.ArgumentParser(description='Apply advanced database optimizations')
    parser.add_argument('--all', action='store_true', help='Apply all optimizations')
    parser.add_argument(
        '--materialized-views', action='store_true', help='Create materialized views',
    )
    parser.add_argument('--clustering', action='store_true', help='Apply table clustering')
    parser.add_argument('--monitoring', action='store_true', help='Set up monitoring functions')
    parser.add_argument('--vacuum', action='store_true', help='Run VACUUM ANALYZE')
    parser.add_argument('--test-performance', action='store_true', help='Run performance tests')

    args = parser.parse_args()

    if not any(
        [
            args.all,
            args.materialized_views,
            args.clustering,
            args.monitoring,
            args.vacuum,
            args.test_performance,
        ],
    ):
        parser.print_help()
        return

    print('🚀 ADVANCED DATABASE OPTIMIZATION SCRIPT')
    print('=' * 50)

    # Run performance tests first (baseline)
    if args.test_performance or args.all:
        print('\n📊 BASELINE PERFORMANCE TESTS')
        run_performance_tests()

    # Apply optimizations
    success_count = 0
    total_count = 0

    if args.materialized_views or args.all:
        total_count += 1
        if apply_materialized_views():
            success_count += 1

    if args.clustering or args.all:
        total_count += 1
        if apply_table_clustering():
            success_count += 1

    if args.monitoring or args.all:
        total_count += 1
        if apply_monitoring_setup():
            success_count += 1

    if args.vacuum or args.all:
        total_count += 1
        if run_vacuum_analyze():
            success_count += 1

    # Run performance tests again (after optimizations)
    if args.test_performance or args.all:
        print('\n📊 POST-OPTIMIZATION PERFORMANCE TESTS')
        run_performance_tests()

    print('\n' + '=' * 50)
    print(
        f'🎯 OPTIMIZATION COMPLETE: {success_count}/{total_count} optimizations applied successfully',
    )

    if success_count == total_count:
        print('✅ All optimizations completed successfully!')
    else:
        print(f'⚠️  {total_count - success_count} optimizations failed - check logs above')

    print('\n💡 Next Steps:')
    print('• Monitor query performance with: SELECT * FROM monitoring.get_index_usage();')
    print('• Check for slow queries with: SELECT * FROM monitoring.get_slow_queries();')
    print(
        '• Refresh materialized views periodically: SELECT maintenance.refresh_all_materialized_views();',
    )


if __name__ == '__main__':
    main()
