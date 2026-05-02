"""
Telemetry Data Models

Pydantic-style dataclasses for telemetry events and entities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import uuid


class Severity(Enum):
    """Event severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class MetricType(Enum):
    """Metric types for aggregation."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMING = "timing"


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TelemetryEvent:
    """Application event with structured payload."""
    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    severity: Severity = Severity.INFO
    source: Optional[str] = None
    correlation_id: Optional[uuid.UUID] = None
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    event_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'event_type': self.event_type,
            'event_version': 1,
            'severity': self.severity.value,
            'source': self.source,
            'correlation_id': str(self.correlation_id) if self.correlation_id else None,
            'session_id': self.session_id,
            'payload': self.payload,
            'created_at': self.created_at.isoformat(),
        }


@dataclass
class TelemetryMetric:
    """Time-series metric measurement."""
    metric_name: str
    value: float
    metric_type: MetricType = MetricType.GAUGE
    unit: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    source: Optional[str] = None
    recorded_at: datetime = field(default_factory=datetime.now)
    metric_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'metric_name': self.metric_name,
            'metric_type': self.metric_type.value,
            'value': self.value,
            'unit': self.unit,
            'labels': self.labels,
            'source': self.source,
            'recorded_at': self.recorded_at.isoformat(),
        }


@dataclass
class TelemetryQuery:
    """Database query performance log."""
    query_text: str
    duration_ms: float
    query_normalized: Optional[str] = None
    rows_affected: Optional[int] = None
    rows_returned: Optional[int] = None
    query_hash: Optional[str] = None
    was_slow: bool = False
    wait_event: Optional[str] = None
    wait_event_type: Optional[str] = None
    waited_ms: Optional[float] = None
    correlation_id: Optional[uuid.UUID] = None
    session_id: Optional[str] = None
    recorded_at: datetime = field(default_factory=datetime.now)
    query_id: Optional[int] = None
    
    def __post_init__(self):
        """Generate query hash if not provided."""
        if self.query_hash is None and self.query_normalized:
            import hashlib
            self.query_hash = hashlib.md5(
                self.query_normalized.encode()
            ).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'query_hash': self.query_hash,
            'query_text': self.query_text[:10000] if len(self.query_text) > 10000 else self.query_text,
            'query_normalized': self.query_normalized,
            'duration_ms': self.duration_ms,
            'rows_affected': self.rows_affected,
            'rows_returned': self.rows_returned,
            'was_slow': self.was_slow,
            'wait_event': self.wait_event,
            'wait_event_type': self.wait_event_type,
            'waited_ms': self.waited_ms,
            'correlation_id': str(self.correlation_id) if self.correlation_id else None,
            'session_id': self.session_id,
            'recorded_at': self.recorded_at.isoformat(),
        }


@dataclass
class TelemetryJob:
    """Batch job execution tracking."""
    job_name: str
    job_type: str = "batch"
    job_group: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    payload: Dict[str, Any] = field(default_factory=dict)
    total_steps: int = 1
    completed_steps: int = 0
    result_summary: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    memory_mb_peak: Optional[float] = None
    cpu_seconds: Optional[float] = None
    rows_processed: Optional[int] = None
    correlation_id: Optional[uuid.UUID] = None
    triggered_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    job_id: Optional[int] = None
    
    @property
    def progress_pct(self) -> float:
        """Calculate progress percentage."""
        if self.total_steps > 0:
            return (self.completed_steps / self.total_steps) * 100
        return 0.0
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate duration in milliseconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'job_name': self.job_name,
            'job_type': self.job_type,
            'job_group': self.job_group,
            'status': self.status.value,
            'payload': self.payload,
            'total_steps': self.total_steps,
            'completed_steps': self.completed_steps,
            'result_summary': self.result_summary,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'memory_mb_peak': self.memory_mb_peak,
            'cpu_seconds': self.cpu_seconds,
            'rows_processed': self.rows_processed,
            'correlation_id': str(self.correlation_id) if self.correlation_id else None,
            'triggered_by': self.triggered_by,
        }


@dataclass
class TelemetryError:
    """Error/exception tracking."""
    error_type: str
    error_message: str
    error_stacktrace: Optional[str] = None
    source: Optional[str] = None
    operation: Optional[str] = None
    correlation_id: Optional[uuid.UUID] = None
    session_id: Optional[str] = None
    environment: str = "development"
    release_version: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = "open"  # open, resolved, ignored
    occurrence_count: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    error_id: Optional[int] = None
    
    @property
    def error_hash(self) -> str:
        """Generate hash for deduplication."""
        import hashlib
        return hashlib.md5(
            f"{self.error_type}:{self.error_message[:200]}".encode()
        ).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'error_type': self.error_type,
            'error_message': self.error_message,
            'error_stacktrace': self.error_stacktrace,
            'error_hash': self.error_hash,
            'source': self.source,
            'operation': self.operation,
            'correlation_id': str(self.correlation_id) if self.correlation_id else None,
            'session_id': self.session_id,
            'environment': self.environment,
            'release_version': self.release_version,
            'payload': self.payload,
            'status': self.status,
        }


@dataclass
class TelemetrySpan:
    """Distributed tracing span."""
    operation_name: str
    service_name: str = "baseball"
    span_id: uuid.UUID = field(default_factory=uuid.uuid4)
    parent_span_id: Optional[uuid.UUID] = None
    trace_id: uuid.UUID = field(default_factory=uuid.uuid4)
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    status: str = "ok"  # ok, error, cancelled
    error_message: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Calculate span duration."""
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds() * 1000
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'trace_id': str(self.trace_id),
            'parent_span_id': str(self.parent_span_id) if self.parent_span_id else None,
            'span_id': str(self.span_id),
            'operation_name': self.operation_name,
            'service_name': self.service_name,
            'started_at': self.started_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration_ms': self.duration_ms,
            'status': self.status,
            'error_message': self.error_message,
            'tags': self.tags,
            'logs': self.logs,
        }
