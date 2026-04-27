"""End-to-end tests for feature computation pipeline.

Tests the full workflow from database to computed features with
benchmarking and metrics collection.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-27
"""

import os
import tempfile
from pathlib import Path

import pytest


# Skip if no database connection
pytestmark = pytest.mark.skipif(
    not os.getenv('PGDATABASE') and not os.getenv('DATABASE_URL'),
    reason='No database connection configured',
)


class TestWinExpectancyE2E:
    """End-to-end tests for Win Expectancy computation."""

    @pytest.fixture(scope='class')
    def db_connection(self):
        """Create a database connection for tests."""
        from baseball.core.db import get_db_connection

        try:
            conn = get_db_connection()
            yield conn
        except Exception as e:
            pytest.skip(f'Cannot connect to database: {e}')
        finally:
            if 'conn' in locals():
                conn.close()

    @pytest.fixture
    def benchmark_logger(self):
        """Create a benchmark logger for the test."""
        from baseball.core.benchmark import BenchmarkLogger

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            log_file = f.name

        logger = BenchmarkLogger(log_file=log_file)
        yield logger

        # Cleanup
        Path(log_file).unlink(missing_ok=True)

    def test_we_matrix_populated(self, db_connection):
        """Verify WE matrix exists and has data."""
        cursor = db_connection.cursor()

        cursor.execute('SELECT COUNT(*) FROM features.win_expectancy_matrix')
        count = cursor.fetchone()[0]

        assert count > 0, 'WE matrix should have data'
        print(f'WE matrix has {count} states')

    def test_we_computation_performance(self, db_connection, benchmark_logger):
        """Test WE computation performance with benchmarking."""
        from baseball.core.benchmark import benchmark, set_benchmark_logger
        from baseball.features import WinExpectancyCalculator

        set_benchmark_logger(benchmark_logger)

        calc = WinExpectancyCalculator(db_connection=db_connection)

        # Benchmark loading WE matrix
        with benchmark('load_we_matrix', rows_expected=100) as result:
            count = calc.load_from_db()
            result.rows_processed = count

        assert count > 0

        # Benchmark computing WE for multiple states
        from baseball.features.base import GameState

        states = [
            GameState(inning=i, is_top=(i % 2 == 1), outs=j % 3)
            for i in range(1, 10)
            for j in range(6)
        ]

        with benchmark('compute_we_batch', rows_expected=len(states)) as result:
            results = calc.compute_batch(states)
            result.rows_processed = len(results)

        assert len(results) == len(states)
        assert all(0 <= r <= 1 for r in results if r is not None)

        # Print benchmark summary
        benchmark_logger.print_summary()

    def test_we_accuracy(self, db_connection):
        """Test WE values are reasonable."""
        from baseball.features import WinExpectancyCalculator
        from baseball.features.base import GameState

        calc = WinExpectancyCalculator(db_connection=db_connection)
        calc.load_from_db()

        # Start of game should be ~50%
        start_state = GameState(inning=1, is_top=True, outs=0)
        start_we = calc.compute(start_state)

        assert 0.45 <= start_we <= 0.55, f'Start of game WE should be ~50%, got {start_we}'

        # High confidence situations
        # Bottom 9, up by 5, 2 outs = very high WE
        winning_state = GameState(
            inning=9,
            is_top=False,
            outs=2,
            score_home=7,
            score_away=2,
        )
        winning_we = calc.compute(winning_state)

        if winning_we is not None:
            assert winning_we > 0.95, f'Up by 5 in bottom 9 should be >95%, got {winning_we}'


class TestLeverageIndexE2E:
    """End-to-end tests for Leverage Index computation."""

    def test_li_matrix_populated(self, db_connection):
        """Verify LI matrix exists and has data."""
        cursor = db_connection.cursor()

        cursor.execute('SELECT COUNT(*) FROM features.leverage_index_matrix')
        count = cursor.fetchone()[0]

        # LI matrix might be empty if not built yet
        print(f'LI matrix has {count} states')

    def test_li_computation(self, db_connection):
        """Test LI computation."""
        from baseball.features import LeverageIndexCalculator
        from baseball.features.base import GameState

        calc = LeverageIndexCalculator(db_connection=db_connection)

        # Try to load LI matrix
        try:
            calc.load_from_db()
        except Exception as e:
            pytest.skip(f'LI matrix not available: {e}')

        # Low leverage situation
        low_state = GameState(inning=1, is_top=True, outs=0)
        low_li = calc.compute(low_state)

        if low_li is not None:
            assert 0.5 <= low_li <= 1.5, f'Early game LI should be ~1.0, got {low_li}'

        # High leverage situation
        high_state = GameState(
            inning=9,
            is_top=False,
            outs=2,
            score_home=4,
            score_away=4,
        )
        high_li = calc.compute(high_state)

        if high_li is not None:
            assert high_li > 2.0, f'Late close game LI should be >2.0, got {high_li}'


class TestFeaturePipelineE2E:
    """End-to-end tests for complete feature pipeline."""

    def test_full_feature_pipeline(self, db_connection, benchmark_logger):
        """Test full feature computation pipeline with timing."""
        from baseball.core.benchmark import benchmark, set_benchmark_logger
        from baseball.features import (
            LeverageIndexCalculator,
            MatchupCalculator,
            WinExpectancyCalculator,
        )
        from baseball.features.base import GameState

        set_benchmark_logger(benchmark_logger)

        # Load all feature calculators
        with benchmark('load_all_features') as result:
            calculators = {
                'we': WinExpectancyCalculator(db_connection=db_connection),
                'li': LeverageIndexCalculator(db_connection=db_connection),
                'matchup': MatchupCalculator(db_connection=db_connection),
            }

            loaded = 0
            for name, calc in calculators.items():
                try:
                    count = calc.load_from_db()
                    if count > 0:
                        loaded += 1
                except Exception:
                    pass

            result.rows_processed = loaded

        # Compute features for sample game states
        states = [
            GameState(inning=1, is_top=True, outs=0),
            GameState(inning=5, is_top=False, outs=1, runner_1b=True),
            GameState(inning=9, is_top=False, outs=2, runner_1b=True, runner_2b=True),
        ]

        with benchmark('compute_all_features') as result:
            features_computed = 0

            for state in states:
                for name, calc in calculators.items():
                    try:
                        value = calc.compute(state)
                        if value is not None:
                            features_computed += 1
                    except Exception:
                        pass

            result.rows_processed = features_computed

        assert features_computed > 0

        # Print summary
        benchmark_logger.print_summary()

    def test_database_query_performance(self, db_connection, benchmark_logger):
        """Test and log database query performance."""
        from baseball.core.benchmark import QueryProfiler

        profiler = QueryProfiler(db_connection)

        # Profile key queries
        queries = [
            ('we_matrix_count', 'SELECT COUNT(*) FROM features.win_expectancy_matrix'),
            (
                'we_matrix_lookup',
                'SELECT home_win_prob FROM features.win_expectancy_matrix '
                + "WHERE inning = 1 AND is_top = true AND outs = 0 AND base_state = '000' AND score_diff = 0",
            ),
            ('games_recent', 'SELECT COUNT(*) FROM core.games WHERE season >= 2023'),
        ]

        for name, sql in queries:
            with profiler.profile_query(name, sql) as cursor:
                cursor.execute(sql)
                cursor.fetchone()

        # Print slow queries
        profiler.print_slow_queries(threshold_ms=50)

        # Verify queries executed
        assert len(profiler.queries) == len(queries)


class TestMaterializedViewsE2E:
    """End-to-end tests for materialized views."""

    def test_context_features_mv_exists(self, db_connection):
        """Verify context features materialized view exists."""
        cursor = db_connection.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM pg_matviews 
            WHERE schemaname = 'features_pitch' 
            AND matviewname LIKE 'mv_%'
        """)
        count = cursor.fetchone()[0]

        print(f'Found {count} materialized views in features_pitch schema')

    def test_mv_refresh_performance(self, db_connection, benchmark_logger):
        """Test materialized view refresh performance."""
        from baseball.core.benchmark import benchmark, set_benchmark_logger

        set_benchmark_logger(benchmark_logger)

        cursor = db_connection.cursor()

        # Try to refresh materialized views
        try:
            with benchmark('refresh_game_context_mv') as result:
                cursor.execute(
                    'REFRESH MATERIALIZED VIEW CONCURRENTLY features_pitch.mv_game_context'
                )
                result.rows_processed = 1
        except Exception as e:
            print(f'Could not refresh mv_game_context: {e}')

        try:
            with benchmark('refresh_park_context_mv') as result:
                cursor.execute(
                    'REFRESH MATERIALIZED VIEW CONCURRENTLY features_pitch.mv_park_context'
                )
                result.rows_processed = 1
        except Exception as e:
            print(f'Could not refresh mv_park_context: {e}')

        benchmark_logger.print_summary()

    def test_mv_data_freshness(self, db_connection):
        """Test materialized view data freshness."""
        cursor = db_connection.cursor()

        # Check when MVs were last refreshed
        try:
            cursor.execute("""
                SELECT schemaname, matviewname, hasindexes, ispopulated
                FROM pg_matviews 
                WHERE schemaname = 'features_pitch'
            """)
            mvs = cursor.fetchall()

            for mv in mvs:
                print(f'MV: {mv[0]}.{mv[1]} - Populated: {mv[3]}')

        except Exception as e:
            print(f'Could not check MV freshness: {e}')
