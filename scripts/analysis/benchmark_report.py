def generate_performance_report(benchmarker: QueryBenchmarker) -> None:
    """Generate a comprehensive performance report."""

    print("\n" + "="*80)
    print("QUERY PERFORMANCE BENCHMARK REPORT")
    print("="*80)

    # Group results by category
    categories = {
        "Feature Queries": [r for r in benchmarker.results.items() if "feature" in r[0].lower()],
        "Simulation Queries": [r for r in benchmarker.results.items() if "simulation" in r[0].lower() or "batch" in r[0].lower()],
        "Analytical Queries": [r for r in benchmarker.results.items() if "analytical" in r[0].lower() or "stats" in r[0].lower() or "trend" in r[0].lower()],
        "Index Tests": [r for r in benchmarker.results.items() if "index" in r[0].lower()],
        "Other": [r for r in benchmarker.results.items() if not any(cat in r[0].lower() for cat in ["feature", "simulation", "analytical", "index"])]
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
            print(".4f"
                  f"({result_count} rows returned)")

        # Show performance ratios for feature queries
        if category_name == "Feature Queries" and len(results) > 1:
            fastest = min(results, key=lambda x: x[1]["avg_time"])
            slowest = max(results, key=lambda x: x[1]["avg_time"])

            if fastest[1]["avg_time"] > 0:
                speedup = slowest[1]["avg_time"] / fastest[1]["avg_time"]
                print(".1f"
    # Overall statistics
    all_times = [r["avg_time"] for r in benchmarker.results.values()]
    print("
📊 OVERALL STATISTICS:"    print(f"  Total queries benchmarked: {len(benchmarker.results)}")
    print(".4f"    print(".4f"    print(".4f"
    # Save detailed results
    with open("benchmark_results.json", "w") as f:
        json.dump(benchmarker.results, f, indent=2, default=str)

    print("
📄 Detailed results saved to benchmark_results.json"