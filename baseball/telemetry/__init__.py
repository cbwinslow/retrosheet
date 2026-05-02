"""
Telemetry Module - Enterprise Observability System

A reusable, modular telemetry system for tracking:
- Application events
- Performance metrics
- Database query logs
- Batch job execution
- Error tracking
- Distributed tracing

This module is designed to be completely independent and reusable
across any Python application.

Usage:
    from baseball.telemetry import TelemetryCollector, timed, logged
    
    # Context manager for operations
    with TelemetryCollector().operation_scope('train_model'):
        train_my_model()
    
    # Decorator for functions
    @timed
    @logged
    def my_function():
        pass
    
    # Manual logging
    telemetry = TelemetryCollector()
    telemetry.log_event('training.started', {'model': 'xgb'})
    telemetry.record_metric('accuracy', 0.95)
"""

from baseball.telemetry.collector import (
    TelemetryCollector,
    TelemetryConfig,
    timed,
    logged,
    operation_scope,
    job_scope,
)

from baseball.telemetry.models import (
    TelemetryEvent,
    TelemetryMetric,
    TelemetryQuery,
    TelemetryJob,
    TelemetryError,
    TelemetrySpan,
)

__all__ = [
    # Main collector
    'TelemetryCollector',
    'TelemetryConfig',
    
    # Decorators
    'timed',
    'logged',
    'operation_scope',
    'job_scope',
    
    # Models
    'TelemetryEvent',
    'TelemetryMetric',
    'TelemetryQuery',
    'TelemetryJob',
    'TelemetryError',
    'TelemetrySpan',
]
