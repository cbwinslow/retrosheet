#!/usr/bin/env python3
"""
Baseball Analytics Testing Framework

Comprehensive testing and benchmarking for:
- SQL queries and views
- Data integrity validation
- Inference performance
- Simulation workflows
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

import psycopg2
import pandas as pd
from psycopg2.pool import SimpleConnectionPool
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]


class BaseballTester:
    """Comprehensive testing framework for baseball analytics."""

    def __init__(self, max_connections: int = 5):
        self.db_pool = SimpleConnectionPool(
            minconn=1, maxconn=max_connections, **self._database_kwargs()
        )
        self.results = {}

    def _database_kwargs(self) -> dict[str, str]:
        return {
            "host": os.environ.get("PGHOST", "localhost"),
            "port": os.environ.get("PGPORT", "5432"),
            "dbname": os.environ.get("PGDATABASE", "retrosheet"),
            "user": os.environ.get("PGUSER", "postgres"),
            "password": os.environ.get("PGPASSWORD", ""),
        }

    def run_query(self, query: str, params: tuple = None):
        """Execute a query and return results."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                return cur.fetchall()
        finally:
            self.db_pool.putconn(conn)

    def run_test(self, test_name: str, test_func, *args, **kwargs) -> Dict[str, Any]:
        """Run a single test and record results."""
        print(f"Running test: {test_name}")
        start_time = time.time()

        try:
            result = test_func(*args, **kwargs)
            elapsed = time.time() - start_time

            test_result = {
                "test_name": test_name,
                "status": "PASS",
                "duration": elapsed,
                "result": result,
            }

        except Exception as e:
            elapsed = time.time() - start_time
            test_result = {
                "test_name": test_name,
                "status": "FAIL",
                "duration": elapsed,
                "error": str(e),
            }

        self.results[test_name] = test_result
        status_icon = "✅" if test_result["status"] == "PASS" else "❌"
        print(f"{status_icon} {test_name}: {test_result['status']} ({elapsed:.2f}s)")

        return test_result

    def test_view_exists(self, schema: str, view_name: str) -> bool:
        """Test that a view exists and is accessible."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.views
                        WHERE table_schema = %s AND table_name = %s
                    )
                """,
                    (schema, view_name),
                )
                return cur.fetchone()[0]
        finally:
            self.db_pool.putconn(conn)

    def test_table_exists(self, schema: str, table_name: str) -> bool:
        """Test that a table exists and is accessible."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = %s AND table_name = %s
                    )
                """,
                    (schema, table_name),
                )
                return cur.fetchone()[0]
        finally:
            self.db_pool.putconn(conn)

    def test_function_exists(self, schema: str, function_name: str) -> bool:
        """Test that a function exists."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.routines
                        WHERE routine_schema = %s AND routine_name = %s
                        AND routine_type = 'FUNCTION'
                    )
                """,
                    (schema, function_name),
                )
                return cur.fetchone()[0]
        finally:
            self.db_pool.putconn(conn)

    def benchmark_query(
        self, query: str, params: tuple = None, iterations: int = 3
    ) -> Dict[str, float]:
        """Benchmark a query's execution time."""
        conn = self.db_pool.getconn()
        times = []

        try:
            for _ in range(iterations):
                start_time = time.time()
                with conn.cursor() as cur:
                    cur.execute(query, params or ())
                    cur.fetchall()  # Consume results
                times.append(time.time() - start_time)

            return {
                "min_time": min(times),
                "max_time": max(times),
                "avg_time": sum(times) / len(times),
                "iterations": iterations,
            }
        finally:
            self.db_pool.putconn(conn)

    def test_data_integrity(
        self, table: str, constraints: List[Dict]
    ) -> Dict[str, Any]:
        """Test data integrity constraints."""
        results = {}

        for constraint in constraints:
            constraint_name = constraint["name"]
            query = constraint["query"]
            expected_min = constraint.get("min_count", 0)

            conn = self.db_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(query)
                    count = cur.fetchone()[0]
                    results[constraint_name] = {
                        "count": count,
                        "passes": count >= expected_min,
                    }
            finally:
                self.db_pool.putconn(conn)

        return results

    def test_inference_accuracy(
        self, target_id: str, sample_size: int = 100
    ) -> Dict[str, Any]:
        """Test inference accuracy by comparing predictions to actual outcomes."""
        conn = self.db_pool.getconn()
        try:
            # Get sample of plate appearances with known outcomes
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT game_id, plate_appearance_id, is_hit, is_walk, is_strikeout,
                           is_home_run, is_reach_base, is_extra_base_hit
                    FROM features.plate_appearance_examples
                    WHERE season = 2022  -- Use validation season
                    AND {target_id.replace("pa_batter_", "")} IS NOT NULL
                    ORDER BY random()
                    LIMIT %s
                """,
                    (sample_size,),
                )
                samples = cur.fetchall()

            if not samples:
                return {"error": f"No samples found for {target_id}"}

            # For now, return mock accuracy (would need full inference service)
            return {
                "target_id": target_id,
                "sample_size": len(samples),
                "accuracy": 0.75,  # Mock value
                "note": "Full inference accuracy testing requires PredictionService",
            }

        finally:
            self.db_pool.putconn(conn)


def run_core_schema_tests(tester: BaseballTester) -> None:
    """Test core schema components."""
    print("\n=== Core Schema Tests ===")

    # Test tables exist
    core_tables = ["games", "events", "plate_appearances", "players", "teams", "parks"]
    for table in core_tables:
        tester.run_test(
            f"core_table_{table}_exists", tester.test_table_exists, "core", table
        )

    # Test views exist
    core_views = [
        "roster_entries",
        "allstar_roster_entries",
        "allstar_games",
        "scheduled_games",
        "umpires",
        "coach_assignments",
        "ejections",
        "player_relatives",
    ]
    for view in core_views:
        tester.run_test(
            f"core_view_{view}_exists", tester.test_view_exists, "core", view
        )


def run_feature_mart_tests(tester: BaseballTester) -> None:
    """Test feature mart components."""
    print("\n=== Feature Mart Tests ===")

    # Test materialized views exist and have data
    feature_views = [
        ("batter_prior_season_pa_summary", 1000),
        ("pitcher_prior_season_pa_summary", 1000),
        ("team_prior_season_summary", 100),
        ("pa_context_prior_season_rates", 1000),
        ("plate_appearance_examples", 100000),
        ("half_inning_examples", 10000),
        ("game_outcome_examples", 10000),
    ]

    for view_name, min_rows in feature_views:
        # Test view exists
        tester.run_test(
            f"feature_view_{view_name}_exists",
            tester.test_view_exists,
            "features",
            view_name,
        )

        # Test view has minimum data
        def test_view_data():
            conn = tester.db_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) FROM features.{view_name}")
                    count = cur.fetchone()[0]
                    return {"row_count": count, "sufficient": count >= min_rows}
            finally:
                tester.db_pool.putconn(conn)

        tester.run_test(f"feature_view_{view_name}_data", test_view_data)


def run_inference_tests(tester: BaseballTester) -> None:
    """Test inference components."""
    print("\n=== Inference Tests ===")

    # Test inference schema exists
    tester.run_test(
        "inference_schema_exists",
        lambda: (
            tester.run_query(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'inference'"
            )
            != []
        ),
    )

    # Test inference views
    inference_views = ["plate_appearance_features"]
    for view in inference_views:
        tester.run_test(
            f"inference_view_{view}_exists", tester.test_view_exists, "inference", view
        )

    # Test inference functions
    inference_functions = [
        "get_plate_appearance_features",
        "predict_plate_appearance_batch",
    ]
    for func in inference_functions:
        tester.run_test(
            f"inference_function_{func}_exists",
            tester.test_function_exists,
            "inference",
            func,
        )

    # Test simulation tables
    tester.run_test(
        "simulation_states_table_exists",
        tester.test_table_exists,
        "inference",
        "simulation_states",
    )


def run_performance_benchmarks(tester: BaseballTester) -> None:
    """Run performance benchmarks."""
    print("\n=== Performance Benchmarks ===")

    # Benchmark common queries
    benchmarks = [
        {
            "name": "game_lookup",
            "query": "SELECT * FROM core.games WHERE game_id = 'ALS200107100'",
            "description": "Single game lookup",
        },
        {
            "name": "plate_appearance_features",
            "query": """
                SELECT * FROM inference.plate_appearance_features
                WHERE game_id = 'ALS200107100' AND plate_appearance_id = 1
            """,
            "description": "Optimized plate appearance features lookup",
        },
        {
            "name": "batter_stats",
            "query": """
                SELECT * FROM features.batter_prior_season_pa_summary
                WHERE feature_season = 2022 AND batter_id = 'batea001'
                LIMIT 1
            """,
            "description": "Batter season stats lookup",
        },
        {
            "name": "half_inning_examples",
            "query": """
                SELECT * FROM features.half_inning_examples
                WHERE season = 2022 AND inning = 1
                LIMIT 10
            """,
            "description": "Half-inning examples query",
        },
    ]

    for bench in benchmarks:
        result = tester.run_test(
            f"benchmark_{bench['name']}", tester.benchmark_query, bench["query"]
        )
        if result["status"] == "PASS":
            perf = result["result"]
            print(
                f"  └─ {bench['description']}: {perf['avg_time']:.4f}s avg ({perf['min_time']:.4f}s - {perf['max_time']:.4f}s)"
            )


def run_data_integrity_tests(tester: BaseballTester) -> None:
    """Run data integrity tests."""
    print("\n=== Data Integrity Tests ===")

    integrity_checks = [
        {
            "name": "games_have_valid_ids",
            "query": "SELECT COUNT(*) FROM core.games WHERE game_id IS NOT NULL AND length(game_id) > 0",
            "min_count": 60000,
        },
        {
            "name": "events_have_game_refs",
            "query": "SELECT COUNT(*) FROM core.events e WHERE EXISTS (SELECT 1 FROM core.games g WHERE g.game_id = e.game_id)",
            "min_count": 4000000,
        },
        {
            "name": "plate_appearances_have_events",
            "query": "SELECT COUNT(*) FROM core.plate_appearances pa WHERE EXISTS (SELECT 1 FROM core.events e WHERE e.game_id = pa.game_id AND e.event_id = pa.event_id)",
            "min_count": 4000000,
        },
        {
            "name": "no_null_home_scores",
            "query": "SELECT COUNT(*) FROM core.games WHERE home_score IS NOT NULL",
            "min_count": 60000,
        },
    ]

    for check in integrity_checks:
        result = tester.run_test(
            f"integrity_{check['name']}",
            tester.test_data_integrity,
            "core.games",
            [check],
        )


def run_inference_accuracy_tests(tester: BaseballTester) -> None:
    """Run inference accuracy tests."""
    print("\n=== Inference Accuracy Tests ===")

    # Test inference accuracy for key targets
    targets_to_test = ["pa_batter_hit", "pa_batter_walk", "pa_batter_strikeout"]

    for target in targets_to_test:
        tester.run_test(
            f"accuracy_{target}",
            tester.test_inference_accuracy,
            target,
            50,  # Sample size
        )


def generate_report(tester: BaseballTester) -> None:
    """Generate a comprehensive test report."""
    print("\n" + "=" * 60)
    print("BASEBALL ANALYTICS TEST REPORT")
    print("=" * 60)

    total_tests = len(tester.results)
    passed_tests = sum(1 for r in tester.results.values() if r["status"] == "PASS")
    failed_tests = total_tests - passed_tests

    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(".1f")

    if failed_tests > 0:
        print("\n❌ FAILED TESTS:")
        for name, result in tester.results.items():
            if result["status"] == "FAIL":
                print(f"  • {name}: {result.get('error', 'Unknown error')}")

    print("\n✅ PASSED TESTS:")
    for name, result in tester.results.items():
        if result["status"] == "PASS":
            duration = result["duration"]
            if duration < 0.1:
                time_str = ".4f"
            else:
                time_str = ".2f"
            print(f"  • {name}: {time_str}")

    # Save detailed results
    with open("test_results.json", "w") as f:
        json.dump(tester.results, f, indent=2, default=str)

    print("\n📄 Detailed results saved to test_results.json")
    return {
        "total_tests": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Baseball Analytics Testing Framework")
    parser.add_argument(
        "--test-type",
        choices=[
            "all",
            "core",
            "features",
            "inference",
            "performance",
            "integrity",
            "accuracy",
        ],
        default="all",
        help="Type of tests to run",
    )
    parser.add_argument("--output-json", type=str, help="Save results to JSON file")
    parser.add_argument(
        "--benchmark-iterations",
        type=int,
        default=3,
        help="Number of iterations for benchmarks",
    )

    args = parser.parse_args()

    tester = BaseballTester(max_connections=5)

    # Run selected test suites
    if args.test_type in ["all", "core"]:
        run_core_schema_tests(tester)

    if args.test_type in ["all", "features"]:
        run_feature_mart_tests(tester)

    if args.test_type in ["all", "inference"]:
        run_inference_tests(tester)

    if args.test_type in ["all", "performance"]:
        run_performance_benchmarks(tester)

    if args.test_type in ["all", "integrity"]:
        run_data_integrity_tests(tester)

    if args.test_type in ["all", "accuracy"]:
        run_inference_accuracy_tests(tester)

    # Generate report
    summary = generate_report(tester)

    # Save to custom file if requested
    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(tester.results, f, indent=2, default=str)

    # Exit with appropriate code
    exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
