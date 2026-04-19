#!/usr/bin/env python3
"""
Query Performance Benchmark Suite

Compares different query approaches and measures performance improvements
from our inference optimizations.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Any

import psycopg2
import pandas as pd
from psycopg2.pool import SimpleConnectionPool


ROOT = Path(__file__).resolve().parents[1]


class QueryBenchmarker:
    """Comprehensive query performance benchmarking."""

    def __init__(self, max_connections: int = 10):
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

    def benchmark_query(
        self,
        name: str,
        query: str,
        params: tuple = None,
        iterations: int = 5,
        warmup: int = 1,
    ) -> Dict[str, Any]:
        """Benchmark a single query."""
        conn = self.db_pool.getconn()
        times = []

        try:
            # Warmup runs
            for _ in range(warmup):
                with conn.cursor() as cur:
                    cur.execute(query, params or ())
                    cur.fetchall()

            # Benchmark runs
            for _ in range(iterations):
                start_time = time.time()
                with conn.cursor() as cur:
                    cur.execute(query, params or ())
                    results = cur.fetchall()
                end_time = time.time()
                times.append(end_time - start_time)

            result = {
                "name": name,
                "iterations": iterations,
                "warmup_runs": warmup,
                "min_time": min(times),
                "max_time": max(times),
                "avg_time": sum(times) / len(times),
                "total_time": sum(times),
                "result_count": len(results) if results else 0,
                "query": query,
                "params": params,
            }

            self.results[name] = result
            return result

        finally:
            self.db_pool.putconn(conn)


def benchmark_feature_queries(benchmarker: QueryBenchmarker) -> None:
    """Benchmark different approaches to getting plate appearance features."""

    print("Benchmarking Feature Query Approaches...")

    # Test case: Get features for a specific plate appearance
    game_id = "ALS200107100"
    pa_id = 1

    # Approach 1: Complex joins (original approach)
    complex_query = """
        SELECT
            pa.season,
            pa.inning,
            pa.is_bottom_inning,
            pa.outs_before,
            pa.balls,
            pa.strikes,
            pa.start_bases,
            pa.home_score_diff,
            pa.batter_hand,
            pa.pitcher_hand,
            COALESCE(batter.prior_pa, 0) AS batter_prior_pa,
            COALESCE(batter.prior_hit_rate, 0.25) AS batter_prior_hit_rate,
            COALESCE(batter.prior_walk_rate, 0.08) AS batter_prior_walk_rate,
            COALESCE(batter.prior_strikeout_rate, 0.20) AS batter_prior_strikeout_rate,
            COALESCE(pitcher.prior_batters_faced, 0) AS pitcher_prior_batters_faced,
            COALESCE(pitcher.prior_hit_allowed_rate, 0.25) AS pitcher_prior_hit_allowed_rate,
            COALESCE(pitcher.prior_walk_allowed_rate, 0.08) AS pitcher_prior_walk_allowed_rate,
            COALESCE(pitcher.prior_strikeout_rate, 0.20) AS pitcher_prior_strikeout_rate,
            COALESCE(batting_team.prior_win_rate, 0.5) AS batting_team_prior_win_rate,
            COALESCE(fielding_team.prior_win_rate, 0.5) AS fielding_team_prior_win_rate,
            COALESCE(context.prior_hit_rate, 0.25) AS context_prior_hit_rate
        FROM features.plate_appearance_examples pa
        LEFT JOIN features.batter_prior_season_pa_summary batter
          ON batter.feature_season = pa.season AND batter.batter_id = pa.batter_id
        LEFT JOIN features.pitcher_prior_season_pa_summary pitcher
          ON pitcher.feature_season = pa.season AND pitcher.pitcher_id = pa.pitcher_id
        LEFT JOIN features.team_prior_season_summary batting_team
          ON batting_team.feature_season = pa.season AND batting_team.team_id = pa.batting_team_id
        LEFT JOIN features.team_prior_season_summary fielding_team
          ON fielding_team.feature_season = pa.season AND fielding_team.team_id = pa.fielding_team_id
        LEFT JOIN features.pa_context_prior_season_rates context
          ON context.feature_season = pa.season
          AND context.batter_hand = COALESCE(pa.batter_hand::text, 'R')
          AND context.pitcher_hand = COALESCE(pa.pitcher_hand::text, 'R')
          AND context.inning = pa.inning
          AND context.is_bottom_inning = pa.is_bottom_inning
          AND context.outs_before = pa.outs_before
          AND context.start_bases = pa.start_bases
          AND context.balls = pa.balls
          AND context.strikes = pa.strikes
        WHERE pa.game_id = %s AND pa.plate_appearance_id = %s
    """

    # Approach 2: Pre-computed materialized view
    optimized_query = """
        SELECT
            season, inning, is_bottom_inning, outs_before, balls, strikes,
            start_bases, home_score_diff, batter_hand, pitcher_hand,
            batter_prior_pa, batter_prior_hit_rate, batter_prior_walk_rate,
            batter_prior_strikeout_rate, pitcher_prior_batters_faced,
            pitcher_prior_hit_allowed_rate, pitcher_prior_walk_allowed_rate,
            pitcher_prior_strikeout_rate, batting_team_prior_win_rate,
            fielding_team_prior_win_rate, context_prior_hit_rate
        FROM inference.plate_appearance_features
        WHERE game_id = %s AND plate_appearance_id = %s
    """

    # Benchmark each approach
    benchmarker.benchmark_query(
        "complex_feature_joins",
        complex_query,
        (game_id, pa_id)
    )

    benchmarker.benchmark_query(
        "optimized_materialized_view",
        optimized_query,
        (game_id, pa_id)
    )

    # Skip database function test for now due to record variable issues
    print("Note: Skipping database function benchmark due to PostgreSQL function issues")
    """

    # Benchmark each approach
    benchmarker.benchmark_query(
        "complex_feature_joins", complex_query, (game_id, pa_id)
    )

    benchmarker.benchmark_query(
        "optimized_materialized_view", optimized_query, (game_id, pa_id)
    )

    benchmarker.benchmark_query("database_function", function_query)


def benchmark_simulation_queries(benchmarker: QueryBenchmarker) -> None:
    """Benchmark queries used in simulation workflows."""

    print("Benchmarking Simulation Query Patterns...")

    # Query 1: Get half-inning state
    hi_query = """
        SELECT start_outs, start_bases, start_balls, start_strikes, start_score_diff,
               batting_team_id, fielding_team_id
        FROM features.half_inning_examples
        WHERE game_id = %s AND inning = %s AND is_bottom_inning = %s
    """

    # Query 2: Batch plate appearance lookups
    batch_pa_query = """
        SELECT game_id, plate_appearance_id, batter_id, pitcher_id,
               batter_hand, pitcher_hand, outs_before, balls, strikes, start_bases
        FROM features.plate_appearance_examples
        WHERE game_id = %s AND inning = %s AND is_bottom_inning = %s
        ORDER BY plate_appearance_id
    """

    # Query 3: Optimized batch features
    optimized_batch_query = """
        SELECT game_id, plate_appearance_id, batter_id, pitcher_id,
               batter_prior_hit_rate, pitcher_prior_strikeout_rate,
               batting_team_prior_win_rate, context_prior_hit_rate
        FROM inference.plate_appearance_features
        WHERE game_id = %s AND inning = %s AND is_bottom_inning = %s
        ORDER BY plate_appearance_id
    """

    params = ("ALS200107100", 1, False)

    benchmarker.benchmark_query("half_inning_state_lookup", hi_query, params)
    benchmarker.benchmark_query("batch_plate_appearances", batch_pa_query, params)
    benchmarker.benchmark_query(
        "optimized_batch_features", optimized_batch_query, params
    )


def benchmark_analytical_queries(benchmarker: QueryBenchmarker) -> None:
    """Benchmark analytical query patterns."""

    print("Benchmarking Analytical Query Patterns...")

    # Query 1: Player season stats
    player_season_query = """
        SELECT batter_id, prior_pa, prior_hit_rate, prior_home_run_rate
        FROM features.batter_prior_season_pa_summary
        WHERE feature_season = 2022 AND prior_pa > 100
        ORDER BY prior_hit_rate DESC
        LIMIT 50
    """

    # Query 2: Team performance trends
    team_trend_query = """
        SELECT team_id, feature_season, prior_win_rate, prior_runs_scored_per_game
        FROM features.team_prior_season_summary
        WHERE feature_season BETWEEN 2015 AND 2022
        ORDER BY feature_season, prior_win_rate DESC
    """

    # Query 3: Game outcome predictions
    game_prediction_query = """
        SELECT game_id, season, home_team_id, away_team_id,
               final_home_win, home_score, away_score
        FROM features.game_outcome_examples
        WHERE season = 2022
        LIMIT 1000
    """

    benchmarker.benchmark_query("player_season_stats", player_season_query)
    benchmarker.benchmark_query("team_performance_trends", team_trend_query)
    benchmarker.benchmark_query("game_outcome_predictions", game_prediction_query)


def benchmark_index_effectiveness(benchmarker: QueryBenchmarker) -> None:
    """Test how well our indexes perform."""

    print("Benchmarking Index Effectiveness...")

    # Test indexed vs non-indexed queries
    indexed_query = """
        SELECT COUNT(*) FROM core.games
        WHERE season = 2022 AND home_team_id = 'LAN'
    """

    non_indexed_query = """
        SELECT COUNT(*) FROM core.games
        WHERE home_score > away_score AND inning > 5
    """

    benchmarker.benchmark_query("indexed_season_team_query", indexed_query)
    benchmarker.benchmark_query("non_indexed_complex_query", non_indexed_query)


def generate_performance_report(benchmarker: QueryBenchmarker) -> None:
    """Generate a comprehensive performance report."""

    print("\n" + "=" * 80)
    print("QUERY PERFORMANCE BENCHMARK REPORT")
    print("=" * 80)

    # Group results by category
    categories = {
        "Feature Queries": [
            r for r in benchmarker.results.items() if "feature" in r[0].lower()
        ],
        "Simulation Queries": [
            r
            for r in benchmarker.results.items()
            if "simulation" in r[0].lower() or "batch" in r[0].lower()
        ],
        "Analytical Queries": [
            r
            for r in benchmarker.results.items()
            if "analytical" in r[0].lower()
            or "stats" in r[0].lower()
            or "trend" in r[0].lower()
        ],
        "Index Tests": [
            r for r in benchmarker.results.items() if "index" in r[0].lower()
        ],
        "Other": [
            r
            for r in benchmarker.results.items()
            if not any(
                cat in r[0].lower()
                for cat in ["feature", "simulation", "analytical", "index"]
            )
        ],
    }

    for category_name, results in categories.items():
        if not results:
            continue

        print(f"\n{category_name}:")
        print("-" * len(category_name))

        # Sort by average time
        results.sort(key=lambda x: x[1]["avg_time"])

        for name, result in results:
            avg_time = result["avg_time"]
            result_count = result.get("result_count", 0)
            print(f".4f({result_count} rows returned)")

        # Show performance ratios for feature queries
        if category_name == "Feature Queries" and len(results) > 1:
            fastest = min(results, key=lambda x: x[1]["avg_time"])
            slowest = max(results, key=lambda x: x[1]["avg_time"])

            if fastest[1]["avg_time"] > 0:
                speedup = slowest[1]["avg_time"] / fastest[1]["avg_time"]
                print(".1f")

    # Overall statistics
    all_times = [r["avg_time"] for r in benchmarker.results.values()]
    print("\n📊 OVERALL STATISTICS:")
    print(f"  Total queries benchmarked: {len(benchmarker.results)}")
    print(".4f")
    print(".4f")
    print(".4f")

    # Performance recommendations
    print("\n💡 PERFORMANCE RECOMMENDATIONS:")
    slow_queries = [
        (n, r) for n, r in benchmarker.results.items() if r["avg_time"] > 0.1
    ]
    if slow_queries:
        print("  Queries taking >100ms that may need optimization:")
        for name, result in sorted(
            slow_queries, key=lambda x: x[1]["avg_time"], reverse=True
        )[:5]:
            print(".4f")

    # Save detailed results
    with open("benchmark_results.json", "w") as f:
        json.dump(benchmarker.results, f, indent=2, default=str)

    print("\n📄 Detailed results saved to benchmark_results.json")


def main():
    parser = argparse.ArgumentParser(description="Query Performance Benchmark Suite")
    parser.add_argument(
        "--benchmark-type",
        choices=["all", "features", "simulation", "analytical", "indexes"],
        default="all",
        help="Type of benchmarks to run",
    )
    parser.add_argument(
        "--iterations", type=int, default=5, help="Number of iterations per benchmark"
    )
    parser.add_argument("--output-json", type=str, help="Save results to JSON file")

    args = parser.parse_args()

    benchmarker = QueryBenchmarker(max_connections=5)

    # Run selected benchmarks
    if args.benchmark_type in ["all", "features"]:
        benchmark_feature_queries(benchmarker)

    if args.benchmark_type in ["all", "simulation"]:
        benchmark_simulation_queries(benchmarker)

    if args.benchmark_type in ["all", "analytical"]:
        benchmark_analytical_queries(benchmarker)

    if args.benchmark_type in ["all", "indexes"]:
        benchmark_index_effectiveness(benchmarker)

    # Generate report
    generate_performance_report(benchmarker)

    # Save to custom file if requested
    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(benchmarker.results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
