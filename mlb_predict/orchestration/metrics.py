"""Metrics collection and persistence for pipeline operations.

Tracks timing, success rates, row counts, and data quality metrics over time.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2


@dataclass
class OperationMetrics:
    """Metrics for a single operation run."""

    operation_id: str
    operation_type: str  # chadwick_ingestion, feature_population, etc.
    start_time: datetime
    end_time: datetime | None = None
    success: bool = False

    # Timing
    duration_seconds: float = 0.0
    stage_timings: dict[str, float] = field(default_factory=dict)

    # Row counts
    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_failed: int = 0

    # Data quality
    validation_passed: bool | None = None
    validation_errors: int = 0
    validation_warnings: int = 0

    # Error tracking
    error_count: int = 0
    error_types: list[str] = field(default_factory=list)
    retry_count: int = 0

    # Metadata
    parameters: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'operation_id': self.operation_id,
            'operation_type': self.operation_type,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'success': self.success,
            'duration_seconds': self.duration_seconds,
            'stage_timings': self.stage_timings,
            'records_processed': self.records_processed,
            'records_inserted': self.records_inserted,
            'records_updated': self.records_updated,
            'records_failed': self.records_failed,
            'validation_passed': self.validation_passed,
            'validation_errors': self.validation_errors,
            'validation_warnings': self.validation_warnings,
            'error_count': self.error_count,
            'error_types': self.error_types,
            'retry_count': self.retry_count,
            'parameters': self.parameters,
            'tags': self.tags,
        }


class MetricsCollector:
    """Collects and persists operation metrics."""

    def __init__(self, db_url: str | None = None, metrics_dir: Path | None = None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.metrics_dir = metrics_dir or Path('logs/metrics')
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self._current: OperationMetrics | None = None

    def start_operation(
        self,
        operation_id: str,
        operation_type: str,
        parameters: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> OperationMetrics:
        """Start tracking a new operation."""
        self._current = OperationMetrics(
            operation_id=operation_id,
            operation_type=operation_type,
            start_time=datetime.now(),
            parameters=parameters or {},
            tags=tags or [],
        )
        return self._current

    def record_stage_timing(self, stage_name: str, duration_seconds: float) -> None:
        """Record timing for a stage."""
        if self._current:
            self._current.stage_timings[stage_name] = duration_seconds

    def record_row_counts(
        self,
        processed: int = 0,
        inserted: int = 0,
        updated: int = 0,
        failed: int = 0,
    ) -> None:
        """Record row count metrics."""
        if self._current:
            self._current.records_processed += processed
            self._current.records_inserted += inserted
            self._current.records_updated += updated
            self._current.records_failed += failed

    def record_validation_result(
        self,
        passed: bool,
        errors: int = 0,
        warnings: int = 0,
    ) -> None:
        """Record validation results."""
        if self._current:
            self._current.validation_passed = passed
            self._current.validation_errors = errors
            self._current.validation_warnings = warnings

    def record_error(self, error_type: str) -> None:
        """Record an error occurrence."""
        if self._current:
            self._current.error_count += 1
            if error_type not in self._current.error_types:
                self._current.error_types.append(error_type)

    def record_retry(self) -> None:
        """Record a retry occurrence."""
        if self._current:
            self._current.retry_count += 1

    def finish_operation(self, success: bool) -> OperationMetrics:
        """Finish the current operation and persist metrics."""
        if not self._current:
            raise RuntimeError('No operation in progress')

        self._current.end_time = datetime.now()
        self._current.success = success
        self._current.duration_seconds = (
            self._current.end_time - self._current.start_time
        ).total_seconds()

        # Persist to file
        self._persist_to_file(self._current)

        # Try to persist to database (best effort)
        try:
            self._persist_to_database(self._current)
        except Exception:
            pass  # Don't fail if DB persistence fails

        metrics = self._current
        self._current = None
        return metrics

    def _persist_to_file(self, metrics: OperationMetrics) -> None:
        """Persist metrics to JSON file."""
        timestamp = metrics.start_time.strftime('%Y%m%d_%H%M%S')
        filename = f'{metrics.operation_type}_{timestamp}_{metrics.operation_id}.json'
        filepath = self.metrics_dir / filename

        with open(filepath, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)

    def _persist_to_database(self, metrics: OperationMetrics) -> None:
        """Persist metrics to database (if schema exists)."""
        if not self.db_url:
            return

        conn = psycopg2.connect(self.db_url)
        try:
            with conn.cursor() as cur:
                # Check if table exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'monitoring' 
                        AND table_name = 'operation_metrics'
                    )
                """)
                if not cur.fetchone()[0]:
                    # Table doesn't exist, skip DB persistence
                    return

                # Insert metrics
                cur.execute(
                    """
                    INSERT INTO monitoring.operation_metrics (
                        operation_id, operation_type, start_time, end_time,
                        success, duration_seconds, records_processed,
                        records_inserted, records_updated, records_failed,
                        validation_passed, validation_errors, validation_warnings,
                        error_count, retry_count, parameters
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        metrics.operation_id,
                        metrics.operation_type,
                        metrics.start_time,
                        metrics.end_time,
                        metrics.success,
                        metrics.duration_seconds,
                        metrics.records_processed,
                        metrics.records_inserted,
                        metrics.records_updated,
                        metrics.records_failed,
                        metrics.validation_passed,
                        metrics.validation_errors,
                        metrics.validation_warnings,
                        metrics.error_count,
                        metrics.retry_count,
                        json.dumps(metrics.parameters),
                    ),
                )
            conn.commit()
        finally:
            conn.close()


class MetricsReporter:
    """Generate reports from collected metrics."""

    def __init__(self, metrics_dir: Path | None = None):
        self.metrics_dir = metrics_dir or Path('logs/metrics')

    def load_recent_metrics(
        self,
        operation_type: str | None = None,
        days: int = 7,
    ) -> list[OperationMetrics]:
        """Load metrics from recent runs."""
        metrics = []
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)

        for filepath in self.metrics_dir.glob('*.json'):
            # Check file modification time
            if filepath.stat().st_mtime < cutoff:
                continue

            try:
                with open(filepath) as f:
                    data = json.load(f)

                if operation_type and data.get('operation_type') != operation_type:
                    continue

                metrics.append(self._dict_to_metrics(data))
            except Exception:
                continue

        return sorted(metrics, key=lambda m: m.start_time, reverse=True)

    def generate_summary(self, days: int = 7) -> dict[str, Any]:
        """Generate summary statistics for recent operations."""
        metrics = self.load_recent_metrics(days=days)

        if not metrics:
            return {'message': 'No metrics found for the specified period'}

        # Group by operation type
        by_type: dict[str, list[OperationMetrics]] = {}
        for m in metrics:
            by_type.setdefault(m.operation_type, []).append(m)

        summary = {
            'period_days': days,
            'total_operations': len(metrics),
            'by_operation_type': {},
        }

        for op_type, ops in by_type.items():
            successful = [o for o in ops if o.success]
            failed = [o for o in ops if not o.success]

            summary['by_operation_type'][op_type] = {
                'total_runs': len(ops),
                'successful': len(successful),
                'failed': len(failed),
                'success_rate': len(successful) / len(ops) if ops else 0,
                'avg_duration_seconds': sum(o.duration_seconds for o in ops) / len(ops)
                if ops
                else 0,
                'total_records_processed': sum(o.records_processed for o in ops),
                'total_errors': sum(o.error_count for o in ops),
                'total_retries': sum(o.retry_count for o in ops),
            }

        return summary

    def print_summary(self, days: int = 7) -> None:
        """Print formatted summary to console."""
        summary = self.generate_summary(days)

        print('\n' + '=' * 70)
        print(f'OPERATIONS METRICS SUMMARY (Last {days} days)')
        print('=' * 70)

        if 'message' in summary:
            print(f'\n{summary["message"]}')
            return

        print(f'\nTotal Operations: {summary["total_operations"]}')

        for op_type, stats in summary['by_operation_type'].items():
            print(f'\n📊 {op_type}')
            print(f'  Runs: {stats["total_runs"]} (✓ {stats["successful"]}, ✗ {stats["failed"]})')
            print(f'  Success Rate: {stats["success_rate"] * 100:.1f}%')
            print(f'  Avg Duration: {stats["avg_duration_seconds"]:.1f}s')
            print(f'  Records Processed: {stats["total_records_processed"]:,}')
            print(f'  Errors: {stats["total_errors"]}, Retries: {stats["total_retries"]}')

        print('\n' + '=' * 70)

    def _dict_to_metrics(self, data: dict[str, Any]) -> OperationMetrics:
        """Convert dictionary back to OperationMetrics."""
        return OperationMetrics(
            operation_id=data['operation_id'],
            operation_type=data['operation_type'],
            start_time=datetime.fromisoformat(data['start_time'])
            if data.get('start_time')
            else datetime.now(),
            end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
            success=data.get('success', False),
            duration_seconds=data.get('duration_seconds', 0.0),
            stage_timings=data.get('stage_timings', {}),
            records_processed=data.get('records_processed', 0),
            records_inserted=data.get('records_inserted', 0),
            records_updated=data.get('records_updated', 0),
            records_failed=data.get('records_failed', 0),
            validation_passed=data.get('validation_passed'),
            validation_errors=data.get('validation_errors', 0),
            validation_warnings=data.get('validation_warnings', 0),
            error_count=data.get('error_count', 0),
            error_types=data.get('error_types', []),
            retry_count=data.get('retry_count', 0),
            parameters=data.get('parameters', {}),
            tags=data.get('tags', []),
        )
