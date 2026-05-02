"""
Telemetry Collector - Core Implementation

Provides the main TelemetryCollector class with decorators and context managers
for comprehensive observability.
"""

import functools
import hashlib
import inspect
import uuid
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from baseball.core.db import get_db_connection
from baseball.telemetry.models import (
    TelemetryEvent,
    TelemetryMetric,
    TelemetryQuery,
    TelemetryJob,
    TelemetryError,
    TelemetrySpan,
    Severity,
    MetricType,
    JobStatus,
)

F = TypeVar('F', bound=Callable[..., Any])


@dataclass
class TelemetryConfig:
    """Configuration for telemetry collection."""
    enabled: bool = True
    log_events: bool = True
    log_metrics: bool = True
    log_queries: bool = True
    log_slow_queries_only: bool = False
    slow_query_threshold_ms: float = 1000.0
    source: str = "baseball"
    environment: str = "development"
    release_version: Optional[str] = None
    sentry_dsn: Optional[str] = None  # Optional external integration
    
    def __post_init__(self):
        """Load from environment if available."""
        import os
        if os.getenv('TELEMETRY_ENABLED') == 'false':
            self.enabled = False
        if os.getenv('SENTRY_DSN'):
            self.sentry_dsn = os.getenv('SENTRY_DSN')
        if os.getenv('RELEASE_VERSION'):
            self.release_version = os.getenv('RELEASE_VERSION')


class TelemetryCollector:
    """
    Main telemetry collection interface.
    
    Provides methods for:
    - Logging events
    - Recording metrics
    - Tracking queries
    - Managing jobs
    - Capturing errors
    - Distributed tracing
    
    Usage:
        telemetry = TelemetryCollector(source='training')
        
        # Simple event
        telemetry.log_event('model.loaded', {'model_id': '123'})
        
        # With context manager
        with telemetry.operation_scope('train_model'):
            train()
        
        # Decorator
        @telemetry.timed
        def my_func():
            pass
    """
    
    _instance: Optional['TelemetryCollector'] = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern for default instance."""
        if cls._instance is None or args or kwargs:
            instance = super().__new__(cls)
            if not args and not kwargs and cls._instance is None:
                cls._instance = instance
            return instance
        return cls._instance
    
    def __init__(
        self,
        source: Optional[str] = None,
        config: Optional[TelemetryConfig] = None,
        correlation_id: Optional[uuid.UUID] = None
    ):
        """Initialize the collector."""
        if hasattr(self, '_initialized'):
            return
        
        self.config = config or TelemetryConfig()
        self.source = source or self.config.source
        self.correlation_id = correlation_id or uuid.uuid4()
        self._active_spans: Dict[uuid.UUID, TelemetrySpan] = {}
        self._active_jobs: Dict[int, TelemetryJob] = {}
        self._initialized = True
        
        # Optional Sentry integration
        if self.config.sentry_dsn:
            self._init_sentry()
    
    def _init_sentry(self):
        """Initialize Sentry integration if configured."""
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=self.config.sentry_dsn,
                release=self.config.release_version,
                environment=self.config.environment,
            )
        except ImportError:
            pass
    
    def _get_connection(self):
        """Get database connection."""
        return get_db_connection()
    
    def log_event(
        self,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        severity: Union[Severity, str] = Severity.INFO,
        correlation_id: Optional[uuid.UUID] = None
    ) -> Optional[int]:
        """
        Log a structured event.
        
        Args:
            event_type: Event identifier (e.g., 'training.started')
            payload: Structured event data
            severity: Event severity level
            correlation_id: Optional correlation ID for distributed tracing
        
        Returns:
            Event ID if logged, None if disabled
        """
        if not self.config.enabled or not self.config.log_events:
            return None
        
        if isinstance(severity, str):
            severity = Severity(severity.upper())
        
        event = TelemetryEvent(
            event_type=event_type,
            payload=payload or {},
            severity=severity,
            source=self.source,
            correlation_id=correlation_id or self.correlation_id,
        )
        
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT telemetry.log_event(%s, %s, %s, %s, %s)
                """,
                (
                    event.event_type,
                    event.payload,
                    event.severity.value,
                    event.source,
                    event.correlation_id,
                )
            )
            event_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            return event_id
        except Exception:
            # Don't fail the application if telemetry fails
            return None
    
    def record_metric(
        self,
        metric_name: str,
        value: float,
        unit: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Optional[int]:
        """
        Record a metric measurement.
        
        Args:
            metric_name: Metric identifier
            value: Numeric value
            unit: Unit of measurement (e.g., 'ms', 'rows')
            labels: Additional labels for aggregation
        
        Returns:
            Metric ID if recorded, None if disabled
        """
        if not self.config.enabled or not self.config.log_metrics:
            return None
        
        metric = TelemetryMetric(
            metric_name=metric_name,
            value=value,
            unit=unit,
            labels=labels or {},
            source=self.source,
        )
        
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT telemetry.record_metric(%s, %s, %s, %s, %s)
                """,
                (
                    metric.metric_name,
                    metric.value,
                    metric.unit,
                    metric.labels,
                    metric.source,
                )
            )
            metric_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            return metric_id
        except Exception:
            return None
    
    def log_query(
        self,
        query_text: str,
        duration_ms: float,
        rows_affected: Optional[int] = None,
        rows_returned: Optional[int] = None,
        query_normalized: Optional[str] = None,
    ) -> Optional[int]:
        """
        Log a database query execution.
        
        Args:
            query_text: The actual SQL query
            duration_ms: Execution time in milliseconds
            rows_affected: Number of rows modified
            rows_returned: Number of rows returned
            query_normalized: Query with literals replaced
        """
        if not self.config.enabled or not self.config.log_queries:
            return None
        
        was_slow = duration_ms > self.config.slow_query_threshold_ms
        if self.config.log_slow_queries_only and not was_slow:
            return None
        
        query = TelemetryQuery(
            query_text=query_text,
            duration_ms=duration_ms,
            query_normalized=query_normalized,
            rows_affected=rows_affected,
            rows_returned=rows_returned,
            was_slow=was_slow,
            correlation_id=self.correlation_id,
        )
        
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO telemetry.query_logs (
                    query_hash, query_text, query_normalized, duration_ms,
                    rows_affected, rows_returned, was_slow, correlation_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING query_id
                """,
                (
                    query.query_hash,
                    query.query_text,
                    query.query_normalized,
                    query.duration_ms,
                    query.rows_affected,
                    query.rows_returned,
                    query.was_slow,
                    query.correlation_id,
                )
            )
            query_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            return query_id
        except Exception:
            return None
    
    def start_job(
        self,
        job_name: str,
        job_type: str = "batch",
        job_group: Optional[str] = None,
        total_steps: int = 1,
        payload: Optional[Dict[str, Any]] = None
    ) -> TelemetryJob:
        """
        Start tracking a batch job.
        
        Args:
            job_name: Job identifier
            job_type: Type of job (batch, scheduled, ad_hoc)
            job_group: Logical grouping (e.g., 'training', 'ingestion')
            total_steps: Total steps for progress tracking
            payload: Job parameters
        
        Returns:
            TelemetryJob instance for updating progress
        """
        job = TelemetryJob(
            job_name=job_name,
            job_type=job_type,
            job_group=job_group or self.source,
            total_steps=total_steps,
            payload=payload or {},
            correlation_id=self.correlation_id,
        )
        
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT telemetry.start_job(%s, %s, %s, %s, %s, %s)
                """,
                (
                    job.job_name,
                    job.payload,
                    job.job_type,
                    job.job_group,
                    job.total_steps,
                    None,  # triggered_by
                )
            )
            job.job_id = cur.fetchone()[0]
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            conn.commit()
            cur.close()
            conn.close()
            
            self._active_jobs[job.job_id] = job
        except Exception:
            pass
        
        return job
    
    def update_job_progress(
        self,
        job: TelemetryJob,
        completed_steps: int,
        result_summary: Optional[Dict[str, Any]] = None
    ):
        """Update job progress."""
        if job.job_id is None:
            return
        
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT telemetry.update_job_progress(%s, %s, %s)",
                (job.job_id, completed_steps, result_summary)
            )
            conn.commit()
            cur.close()
            conn.close()
            
            job.completed_steps = completed_steps
            if result_summary:
                job.result_summary.update(result_summary)
        except Exception:
            pass
    
    def complete_job(
        self,
        job: TelemetryJob,
        status: str = "completed",
        result_summary: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ):
        """Mark a job as completed or failed."""
        if job.job_id is None:
            return
        
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT telemetry.complete_job(%s, %s, %s, %s)",
                (job.job_id, status, result_summary, error_message)
            )
            conn.commit()
            cur.close()
            conn.close()
            
            job.status = JobStatus(status)
            job.completed_at = datetime.now()
            if result_summary:
                job.result_summary.update(result_summary)
            if error_message:
                job.error_message = error_message
            
            self._active_jobs.pop(job.job_id, None)
        except Exception:
            pass
    
    def log_error(
        self,
        error: Exception,
        operation: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Log an exception/error.
        
        Args:
            error: The exception that occurred
            operation: What operation was being performed
            payload: Additional context
        
        Returns:
            Error ID if logged
        """
        if not self.config.enabled:
            return None
        
        error_type = error.__class__.__name__
        error_message = str(error)
        error_stacktrace = traceback.format_exc()
        
        # Also send to Sentry if configured
        if self.config.sentry_dsn:
            try:
                import sentry_sdk
                sentry_sdk.capture_exception(error)
            except ImportError:
                pass
        
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT telemetry.log_error(%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    error_type,
                    error_message,
                    error_stacktrace,
                    self.source,
                    operation,
                    self.correlation_id,
                    payload,
                )
            )
            error_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            return error_id
        except Exception:
            return None
    
    @contextmanager
    def operation_scope(
        self,
        operation_name: str,
        payload: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for timing and logging an operation.
        
        Usage:
            with telemetry.operation_scope('train_model'):
                model.fit(X, y)
        """
        start_time = time.time()
        span = self.start_span(operation_name)
        
        try:
            self.log_event(
                f"{operation_name}.started",
                payload,
                Severity.INFO
            )
            yield span
            duration_ms = (time.time() - start_time) * 1000
            self.log_event(
                f"{operation_name}.completed",
                {**(payload or {}), 'duration_ms': duration_ms},
                Severity.INFO
            )
            self.record_metric(f"{operation_name}.duration", duration_ms, 'ms')
            self.finish_span(span, status='ok')
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.log_error(e, operation=operation_name, payload=payload)
            self.log_event(
                f"{operation_name}.failed",
                {**(payload or {}), 'duration_ms': duration_ms, 'error': str(e)},
                Severity.ERROR
            )
            self.finish_span(span, status='error', error_message=str(e))
            raise
    
    @contextmanager
    def job_scope(
        self,
        job_name: str,
        job_type: str = "batch",
        job_group: Optional[str] = None,
        total_steps: int = 1,
        payload: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for batch job execution.
        
        Usage:
            with telemetry.job_scope('feature_build', total_steps=100) as job:
                for i, batch in enumerate(batches):
                    process(batch)
                    job.update_progress(i + 1)
        """
        job = self.start_job(job_name, job_type, job_group, total_steps, payload)
        
        try:
            yield job
            self.complete_job(job, status='completed')
        except Exception as e:
            self.complete_job(job, status='failed', error_message=str(e))
            self.log_error(e, operation=job_name)
            raise
    
    def start_span(
        self,
        operation_name: str,
        parent_span_id: Optional[uuid.UUID] = None
    ) -> TelemetrySpan:
        """Start a distributed tracing span."""
        span = TelemetrySpan(
            operation_name=operation_name,
            service_name=self.source,
            parent_span_id=parent_span_id,
            trace_id=self.correlation_id if parent_span_id else uuid.uuid4(),
        )
        self._active_spans[span.span_id] = span
        return span
    
    def finish_span(
        self,
        span: TelemetrySpan,
        status: str = 'ok',
        error_message: Optional[str] = None
    ):
        """Finish a tracing span."""
        span.ended_at = datetime.now()
        span.status = status
        span.error_message = error_message
        
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO telemetry.traces (
                    trace_id, parent_span_id, span_id, operation_name,
                    service_name, started_at, ended_at, duration_ms, status, error_message
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    span.trace_id,
                    span.parent_span_id,
                    span.span_id,
                    span.operation_name,
                    span.service_name,
                    span.started_at,
                    span.ended_at,
                    span.duration_ms,
                    span.status,
                    span.error_message,
                )
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception:
            pass
        
        self._active_spans.pop(span.span_id, None)


# Convenience decorators

def timed(func: F) -> F:
    """
    Decorator to automatically time function execution.
    
    Usage:
        @timed
        def my_function():
            pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        collector = TelemetryCollector()
        with collector.operation_scope(func.__name__):
            return func(*args, **kwargs)
    return wrapper  # type: ignore


def logged(
    event_type: Optional[str] = None,
    severity: Severity = Severity.INFO
):
    """
    Decorator to log function calls.
    
    Usage:
        @logged('training.started')
        def train():
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            collector = TelemetryCollector()
            event = event_type or f"{func.__name__}.called"
            
            # Capture arguments (safely)
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            # Filter out sensitive data
            safe_args = {
                k: v for k, v in bound.arguments.items()
                if k not in ('password', 'token', 'secret', 'api_key')
            }
            
            collector.log_event(event, {'args': safe_args}, severity)
            
            try:
                result = func(*args, **kwargs)
                collector.log_event(
                    f"{func.__name__}.completed",
                    {'result_type': type(result).__name__},
                    Severity.INFO
                )
                return result
            except Exception as e:
                collector.log_error(e, operation=func.__name__)
                raise
        return wrapper  # type: ignore
    return decorator


# Context manager aliases for cleaner imports
operation_scope = TelemetryCollector().operation_scope
job_scope = TelemetryCollector().job_scope
