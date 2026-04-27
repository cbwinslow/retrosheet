"""Benchmarking and performance monitoring utilities.

Provides timing, metrics collection, and bottleneck identification
for database operations and feature computation.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-27
"""

import json
import logging
import os
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any

import psutil


logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a benchmarked operation."""

    name: str
    duration_ms: float
    rows_processed: int = 0
    memory_mb_start: float = 0.0
    memory_mb_end: float = 0.0
    memory_mb_peak: float = 0.0
    cpu_percent: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def throughput_rows_per_sec(self) -> float:
        """Calculate rows processed per second."""
        if self.duration_ms > 0:
            return (self.rows_processed / self.duration_ms) * 1000
        return 0.0

    @property
    def memory_delta_mb(self) -> float:
        """Memory change during operation."""
        return self.memory_mb_end - self.memory_mb_start


class BenchmarkLogger:
    """Logger for benchmark results with persistence."""

    def __init__(self, log_file: str | None = None):
        self.results: list[BenchmarkResult] = []
        self.log_file = log_file or f'benchmarks_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl'

    def log(self, result: BenchmarkResult) -> None:
        """Log a benchmark result."""
        self.results.append(result)

        # Write to file immediately for durability
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(asdict(result), default=str) + '\n')

        # Log to console/logger
        status = '✅' if not result.error else '❌'
        logger.info(
            f'{status} {result.name}: {result.duration_ms:.2f}ms | '
            f'{result.rows_processed:,} rows | '
            f'{result.throughput_rows_per_sec:.0f} rows/sec',
        )

    def get_summary(self) -> dict[str, Any]:
        """Get summary statistics of all benchmarks."""
        if not self.results:
            return {}

        durations = [r.duration_ms for r in self.results if not r.error]
        rows = [r.rows_processed for r in self.results if not r.error]

        return {
            'total_operations': len(self.results),
            'successful_operations': len([r for r in self.results if not r.error]),
            'failed_operations': len([r for r in self.results if r.error]),
            'total_duration_ms': sum(durations),
            'avg_duration_ms': sum(durations) / len(durations) if durations else 0,
            'max_duration_ms': max(durations) if durations else 0,
            'min_duration_ms': min(durations) if durations else 0,
            'total_rows_processed': sum(rows),
            'avg_throughput_rows_per_sec': sum(r.throughput_rows_per_sec for r in self.results)
            / len(self.results)
            if self.results
            else 0,
        }

    def print_summary(self) -> None:
        """Print benchmark summary to console."""
        summary = self.get_summary()
        if not summary:
            print('No benchmarks recorded')
            return

        print('\n' + '=' * 60)
        print('BENCHMARK SUMMARY')
        print('=' * 60)
        print(f'Total operations: {summary["total_operations"]}')
        print(
            f'Successful: {summary["successful_operations"]} | Failed: {summary["failed_operations"]}'
        )
        print(f'Total duration: {summary["total_duration_ms"]:.2f}ms')
        print(f'Avg duration: {summary["avg_duration_ms"]:.2f}ms')
        print(f'Min/Max: {summary["min_duration_ms"]:.2f}ms / {summary["max_duration_ms"]:.2f}ms')
        print(f'Total rows: {summary["total_rows_processed"]:,}')
        print(f'Avg throughput: {summary["avg_throughput_rows_per_sec"]:.0f} rows/sec')
        print('=' * 60 + '\n')


# Global benchmark logger
_default_logger: BenchmarkLogger | None = None


def get_benchmark_logger() -> BenchmarkLogger:
    """Get or create the global benchmark logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = BenchmarkLogger()
    return _default_logger


def set_benchmark_logger(logger: BenchmarkLogger) -> None:
    """Set the global benchmark logger."""
    global _default_logger
    _default_logger = logger


@contextmanager
def benchmark(
    name: str,
    rows_expected: int = 0,
    metadata: dict[str, Any] | None = None,
):
    """Context manager for benchmarking a code block.

    Usage:
        with benchmark('load_we_matrix', rows_expected=1000) as result:
            matrix = load_matrix()
            result.rows_processed = len(matrix)
    """
    logger = get_benchmark_logger()
    result = BenchmarkResult(
        name=name,
        rows_processed=rows_expected,
        metadata=metadata or {},
    )

    # Get initial metrics
    process = psutil.Process(os.getpid())
    mem_start = process.memory_info().rss / 1024 / 1024
    result.memory_mb_start = mem_start

    start_time = time.perf_counter()

    try:
        yield result
    except Exception as e:
        result.error = str(e)
        raise
    finally:
        end_time = time.perf_counter()
        result.duration_ms = (end_time - start_time) * 1000

        # Get final metrics
        mem_end = process.memory_info().rss / 1024 / 1024
        result.memory_mb_end = mem_end
        result.memory_mb_peak = max(mem_start, mem_end)  # Simplified - could track peak during

        logger.log(result)


def benchmark_fn(name: str | None = None):
    """Decorator for benchmarking functions.

    Usage:
        @benchmark_fn('compute_we')
        def compute_win_expectancy(game_state):
            # ... computation ...
            return result
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            bench_name = name or func.__name__
            with benchmark(bench_name) as result:
                retval = func(*args, **kwargs)
                # Try to infer rows processed from return value
                if hasattr(retval, '__len__') and not isinstance(retval, (str, bytes)):
                    result.rows_processed = len(retval)
                return retval

        return wrapper

    return decorator


class QueryProfiler:
    """Profile PostgreSQL query execution."""

    def __init__(self, connection):
        self.conn = connection
        self.queries: list[dict[str, Any]] = []

    @contextmanager
    def profile_query(self, query_name: str, sql: str, params: tuple | None = None):
        """Profile a single query execution."""
        cursor = self.conn.cursor()

        # Enable query timing
        cursor.execute('SET log_min_duration_statement = 0;')

        start = time.perf_counter()
        try:
            yield cursor
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
        finally:
            duration = (time.perf_counter() - start) * 1000

            # Get row count if available
            row_count = cursor.rowcount if cursor.description else 0

            query_info = {
                'name': query_name,
                'sql': sql[:200],  # Truncate for logging
                'duration_ms': duration,
                'row_count': row_count,
                'timestamp': datetime.now().isoformat(),
            }
            self.queries.append(query_info)

            logger.info(
                f'Query {query_name}: {duration:.2f}ms | {row_count} rows | SQL: {sql[:100]}...',
            )

    def get_slow_queries(self, threshold_ms: float = 100.0) -> list[dict[str, Any]]:
        """Get queries slower than threshold."""
        return [q for q in self.queries if q['duration_ms'] > threshold_ms]

    def print_slow_queries(self, threshold_ms: float = 100.0) -> None:
        """Print slow queries for optimization."""
        slow = self.get_slow_queries(threshold_ms)
        if slow:
            print(f'\n⚠️  Slow queries (>{threshold_ms}ms):')
            for q in slow:
                print(f'  {q["name"]}: {q["duration_ms"]:.2f}ms')
                print(f'    SQL: {q["sql"]}')


class PerformanceMonitor:
    """Monitor system performance during operations."""

    def __init__(self, interval_seconds: float = 1.0):
        self.interval = interval_seconds
        self.running = False
        self.samples: list[dict[str, Any]] = []

    def start(self) -> None:
        """Start monitoring in background."""
        self.running = True
        self._sample()

    def stop(self) -> None:
        """Stop monitoring."""
        self.running = False

    def _sample(self) -> None:
        """Take a performance sample."""
        if not self.running:
            return

        sample = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': psutil.cpu_percent(interval=None),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_available_mb': psutil.virtual_memory().available / 1024 / 1024,
            'disk_io': psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
        }
        self.samples.append(sample)

    def get_peak_memory_percent(self) -> float:
        """Get peak memory usage during monitoring."""
        if not self.samples:
            return 0.0
        return max(s['memory_percent'] for s in self.samples)

    def get_avg_cpu_percent(self) -> float:
        """Get average CPU usage during monitoring."""
        if not self.samples:
            return 0.0
        return sum(s['cpu_percent'] for s in self.samples) / len(self.samples)
