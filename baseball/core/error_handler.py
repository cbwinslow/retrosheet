"""
Enterprise-level error handling system for baseball multi-model ensemble.

Provides comprehensive error logging, stack trace capture, runtime metrics,
and database-centric error tracking with Prometheus integration.
"""

import asyncio
import logging
import traceback
import time
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values
from prometheus_client import Counter, Histogram, Gauge

from baseball.core.db import get_db_connection


class ErrorLevel(Enum):
    """Error severity levels"""
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class ErrorCategory(Enum):
    """Error categories for better organization"""
    INGESTION = "INGESTION"
    MODELING = "MODELING"
    INFERENCE = "INFERENCE"
    SYSTEM = "SYSTEM"
    DATABASE = "DATABASE"
    NETWORK = "NETWORK"
    VALIDATION = "VALIDATION"


@dataclass
class ErrorContext:
    """Context information for errors"""
    command_name: Optional[str] = None
    subcommand: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    data_source: Optional[str] = None
    table_name: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column_name: Optional[str] = None
    sql_query: Optional[str] = None
    batch_size: Optional[int] = None
    model_name: Optional[str] = None
    operation_name: Optional[str] = None


@dataclass
class RuntimeMetrics:
    """Runtime performance metrics"""
    execution_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    disk_io_mb: float = 0.0
    network_io_mb: float = 0.0
    rows_processed: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_failed: int = 0
    throughput_per_second: float = 0.0


class EnterpriseErrorHandler:
    """
    Enterprise-level error handling system for baseball multi-model ensemble.
    
    Features:
    - Comprehensive error logging with stack traces
    - Database-based error tracking and resolution
    - Prometheus metrics integration
    - Runtime performance monitoring
    - Automatic error pattern detection
    - Context-aware error reporting
    """
    
    def __init__(self, logger_name: str = "baseball.enterprise"):
        self.logger = logging.getLogger(logger_name)
        
        # Prometheus metrics
        self.error_counter = Counter(
            'baseball_enterprise_errors_total',
            'Total number of errors',
            ['error_level', 'error_category', 'error_source']
        )
        
        self.execution_histogram = Histogram(
            'baseball_enterprise_execution_duration_seconds',
            'Execution time in seconds',
            ['command_name', 'operation_name']
        )
        
        self.memory_gauge = Gauge(
            'baseball_enterprise_memory_usage_bytes',
            'Memory usage in bytes',
            ['component_name']
        )
        
        self.cpu_gauge = Gauge(
            'baseball_enterprise_cpu_usage_percent',
            'CPU usage percentage',
            ['component_name']
        )
        
        # Database connection pool
        self._db_pool = []
        self._max_pool_size = 5
        
    def log_error(
        self,
        error: Exception,
        level: ErrorLevel = ErrorLevel.ERROR,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        context: Optional[ErrorContext] = None,
        recovery_attempted: bool = False,
        recovery_successful: bool = False,
        recovery_message: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> int:
        """
        Log an error with full context and stack trace to database.
        
        Returns:
            error_id: Database ID of the logged error
        """
        try:
            # Get stack trace
            stack_trace = traceback.format_exc()
            
            # Extract error code from exception
            error_code = getattr(error, 'code', type(error).__name__)
            
            # Get current execution metrics
            metrics = self._get_current_metrics()
            
            # Log to database
            error_id = self._log_to_database(
                level=level.value,
                category=category.value,
                error_source=context.data_source if context else None,
                error_code=error_code,
                error_message=str(error),
                stack_trace=stack_trace,
                context_data=asdict(context) if context else None,
                user_id=user_id,
                command_name=context.command_name if context else None,
                function_name=context.operation_name if context else None,
                file_path=context.file_path if context else None,
                line_number=context.line_number if context else None,
                column_name=context.column_name if context else None,
                table_name=context.table_name if context else None,
                sql_query=context.sql_query if context else None,
                execution_time_ms=int(metrics.execution_time_ms),
                memory_usage_mb=metrics.memory_usage_mb,
                cpu_usage_percent=metrics.cpu_usage_percent,
                affected_rows=metrics.rows_processed,
                recovery_attempted=recovery_attempted,
                recovery_successful=recovery_successful,
                recovery_message=recovery_message
            )
            
            # Update Prometheus metrics
            self.error_counter.labels(
                error_level=level.value,
                error_category=category.value,
                error_source=context.data_source if context else 'unknown'
            ).inc()
            
            # Log to standard logger
            self.logger.error(
                f"Error logged to database (ID: {error_id}): {level.value} - "
                f"{category.value} - {str(error)}"
            )
            
            return error_id
            
        except Exception as log_error:
            # Fallback logging if database logging fails
            self.logger.critical(
                f"CRITICAL: Failed to log error to database: {log_error}. "
                f"Original error: {str(error)}"
            )
            return -1
    
    def log_pipeline_start(
        self,
        command_name: str,
        subcommand: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> int:
        """Log the start of a pipeline execution."""
        try:
            return self._log_pipeline_to_database(
                command_name=command_name,
                subcommand=subcommand,
                parameters=json.dumps(parameters) if parameters else None,
                status="RUNNING",
                started_at=datetime.now(timezone.utc),
                user_id=user_id
            )
        except Exception as e:
            self.logger.error(f"Failed to log pipeline start: {e}")
            return -1
    
    def log_pipeline_complete(
        self,
        run_id: int,
        status: str,
        rows_processed: int = 0,
        rows_inserted: int = 0,
        rows_updated: int = 0,
        rows_failed: int = 0,
        error_count: int = 0,
        warning_count: int = 0,
        performance_score: float = 0.0
    ) -> bool:
        """Log the completion of a pipeline execution."""
        try:
            # Calculate performance score
            success_rate = (rows_processed - rows_failed) / rows_processed if rows_processed > 0 else 0
            performance_score = min(100, success_rate * 100)
            
            return self._update_pipeline_in_database(
                run_id=run_id,
                status=status,
                completed_at=datetime.now(timezone.utc),
                duration_seconds=None,  # Will be calculated by trigger
                rows_processed=rows_processed,
                rows_inserted=rows_inserted,
                rows_updated=rows_updated,
                rows_failed=rows_failed,
                error_count=error_count,
                warning_count=warning_count,
                performance_score=performance_score
            )
        except Exception as e:
            self.logger.error(f"Failed to log pipeline completion: {e}")
            return False
    
    def log_runtime_metrics(
        self,
        metric_type: str,
        metric_name: str,
        metric_value: float,
        metric_unit: str = "count",
        model_name: Optional[str] = None,
        data_source: Optional[str] = None,
        operation_name: Optional[str] = None,
        batch_size: Optional[int] = None,
        throughput_per_second: float = 0.0,
        latency_p50_ms: float = 0.0,
        latency_p95_ms: float = 0.0,
        latency_p99_ms: float = 0.0,
        error_rate_percent: float = 0.0,
        custom_tags: Optional[Dict[str, str]] = None
    ) -> bool:
        """Log runtime metrics to database and Prometheus."""
        try:
            # Log to database
            success = self._log_metrics_to_database(
                metric_type=metric_type,
                metric_name=metric_name,
                metric_value=metric_value,
                metric_unit=metric_unit,
                model_name=model_name,
                data_source=data_source,
                operation_name=operation_name,
                batch_size=batch_size,
                throughput_per_second=throughput_per_second,
                latency_p50_ms=latency_p50_ms,
                latency_p95_ms=latency_p95_ms,
                latency_p99_ms=latency_p99_ms,
                error_rate_percent=error_rate_percent,
                memory_usage_mb=None,  # Will be updated by trigger
                cpu_usage_percent=None,  # Will be updated by trigger
                disk_usage_mb=None,  # Will be updated by trigger
                network_io_mb=None,  # Will be updated by trigger
                custom_tags=json.dumps(custom_tags) if custom_tags else None
            )
            
            # Update Prometheus gauges
            if model_name:
                self.memory_gauge.labels(component_name=model_name).set(
                    self._get_current_metrics().memory_usage_mb * 1024 * 1024  # Convert to bytes
                )
                self.cpu_gauge.labels(component_name=model_name).set(
                    self._get_current_metrics().cpu_usage_percent
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to log runtime metrics: {e}")
            return False
    
    def log_system_health(
        self,
        component_name: str,
        status: str,
        cpu_usage_percent: float = 0.0,
        memory_usage_percent: float = 0.0,
        disk_usage_percent: float = 0.0,
        network_latency_ms: float = 0.0,
        database_connections: int = 0,
        active_models: int = 0,
        queue_depth: int = 0,
        error_rate: float = 0.0,
        uptime_seconds: float = 0.0,
        alerts: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log system health snapshot."""
        try:
            # Calculate health score
            health_score = self._calculate_health_score(
                status=status,
                cpu_usage_percent=cpu_usage_percent,
                memory_usage_percent=memory_usage_percent,
                error_rate=error_rate
            )
            
            return self._log_health_to_database(
                component_name=component_name,
                status=status,
                cpu_usage_percent=cpu_usage_percent,
                memory_usage_percent=memory_usage_percent,
                disk_usage_percent=disk_usage_percent,
                network_latency_ms=network_latency_ms,
                database_connections=database_connections,
                active_models=active_models,
                queue_depth=queue_depth,
                error_rate=error_rate,
                uptime_seconds=uptime_seconds,
                health_score=health_score,
                alerts=json.dumps(alerts) if alerts else None
            )
            
        except Exception as e:
            self.logger.error(f"Failed to log system health: {e}")
            return False
    
    def _log_to_database(self, **kwargs) -> int:
        """Log error to database with connection pooling."""
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Insert error log
            columns = [
                'error_level', 'error_category', 'error_source', 'error_code',
                'error_message', 'stack_trace', 'context_data', 'user_id',
                'command_name', 'function_name', 'file_path', 'line_number',
                'column_name', 'table_name', 'sql_query', 'execution_time_ms',
                'memory_usage_mb', 'cpu_usage_percent', 'affected_rows',
                'recovery_attempted', 'recovery_successful', 'recovery_message'
            ]
            
            values = [
                kwargs.get(col) for col in columns
            ]
            
            cursor.execute(
                f"""
                INSERT INTO admin.error_logs (
                    {', '.join(columns)}
                ) VALUES (
                    {', '.join(['%s'] * len(columns))}
                ) RETURNING error_id
                """,
                values
            )
            
            result = cursor.fetchone()
            conn.commit()
            
            return result[0] if result else -1
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error logging failed: {e}")
            return -1
        finally:
            if conn:
                self._return_db_connection(conn)
    
    def _log_pipeline_to_database(self, **kwargs) -> int:
        """Log pipeline run to database."""
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO admin.pipeline_runs (
                    command_name, subcommand, parameters, status, started_at, user_id
                                ) VALUES (%s, %s, %s, %s, %s, %s) RETURNING run_id
                """,
                (
                    kwargs.get('command_name'),
                    kwargs.get('subcommand'),
                    kwargs.get('parameters'),
                                        kwargs.get('status'),
                    kwargs.get('started_at'),
                    kwargs.get('user_id')
                )
            )
            
            result = cursor.fetchone()
            conn.commit()
            
            return result[0] if result else -1
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Pipeline logging failed: {e}")
            return -1
        finally:
            if conn:
                self._return_db_connection(conn)
    
    def _update_pipeline_in_database(self, **kwargs) -> bool:
        """Update pipeline run in database."""
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Calculate duration if not provided
            if 'duration_seconds' not in kwargs and 'run_id' in kwargs:
                cursor.execute(
                    "SELECT started_at FROM admin.pipeline_runs WHERE run_id = %s",
                    (kwargs['run_id'],)
                )
                result = cursor.fetchone()
                if result and result[0]:
                    started_at = result[0]
                    if isinstance(started_at, str):
                        started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    duration = (datetime.now(timezone.utc) - started_at).total_seconds()
                    kwargs['duration_seconds'] = int(duration)
            
            # Update fields
            update_fields = []
            update_values = []
            
            for field in ['status', 'completed_at', 'duration_seconds', 'rows_processed',
                         'rows_inserted', 'rows_updated', 'rows_failed',
                         'error_count', 'warning_count', 'performance_score']:
                if field in kwargs and kwargs[field] is not None:
                    update_fields.append(f"{field} = %s")
                    update_values.append(kwargs[field])
            
            if update_fields:
                cursor.execute(
                    f"""
                    UPDATE admin.pipeline_runs 
                    SET {', '.join(update_fields)}
                    WHERE run_id = %s
                    """,
                    update_values + [kwargs['run_id']]
                )
            
            conn.commit()
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Pipeline update failed: {e}")
            return False
        finally:
            if conn:
                self._return_db_connection(conn)
    
    def _log_metrics_to_database(self, **kwargs) -> bool:
        """Log runtime metrics to database."""
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO admin.runtime_metrics (
                    metric_type, metric_name, metric_value, metric_unit,
                    model_name, data_source, operation_name, batch_size,
                    throughput_per_second, latency_p50_ms, latency_p95_ms, latency_p99_ms,
                    error_rate_percent, memory_usage_mb, cpu_usage_percent,
                    disk_usage_mb, network_io_mb, custom_tags
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    kwargs.get('metric_type'), kwargs.get('metric_name'),
                    kwargs.get('metric_value'), kwargs.get('metric_unit'),
                    kwargs.get('model_name'), kwargs.get('data_source'),
                    kwargs.get('operation_name'), kwargs.get('batch_size'),
                    kwargs.get('throughput_per_second'), kwargs.get('latency_p50_ms'),
                    kwargs.get('latency_p95_ms'), kwargs.get('latency_p99_ms'),
                    kwargs.get('error_rate_percent'), kwargs.get('memory_usage_mb'),
                    kwargs.get('cpu_usage_percent'), kwargs.get('disk_usage_mb'),
                    kwargs.get('network_io_mb'), kwargs.get('custom_tags')
                )
            )
            
            conn.commit()
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Metrics logging failed: {e}")
            return False
        finally:
            if conn:
                self._return_db_connection(conn)
    
    def _log_health_to_database(self, **kwargs) -> bool:
        """Log system health to database."""
        conn = None
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO admin.system_health (
                    component_name, status, cpu_usage_percent, memory_usage_percent,
                    disk_usage_percent, network_latency_ms, database_connections,
                    active_models, queue_depth, error_rate, uptime_seconds,
                    health_score, alerts
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    kwargs.get('component_name'), kwargs.get('status'),
                    kwargs.get('cpu_usage_percent'), kwargs.get('memory_usage_percent'),
                    kwargs.get('disk_usage_percent'), kwargs.get('network_latency_ms'),
                    kwargs.get('database_connections'), kwargs.get('active_models'),
                    kwargs.get('queue_depth'), kwargs.get('error_rate'),
                    kwargs.get('uptime_seconds'), kwargs.get('health_score'),
                    kwargs.get('alerts')
                )
            )
            
            conn.commit()
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Health logging failed: {e}")
            return False
        finally:
            if conn:
                self._return_db_connection(conn)
    
    def _get_db_connection(self):
        """Get database connection from pool or create new one."""
        try:
            if self._db_pool:
                return self._db_pool.pop()
            else:
                return get_db_connection()
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise
    
    def _return_db_connection(self, conn):
        """Return connection to pool if not full."""
        try:
            if len(self._db_pool) < self._max_pool_size:
                self._db_pool.append(conn)
            else:
                conn.close()
        except Exception as e:
            self.logger.error(f"Error returning connection to pool: {e}")
    
    def _get_current_metrics(self) -> RuntimeMetrics:
        """Get current runtime metrics."""
        try:
            import psutil
            
            return RuntimeMetrics(
                memory_usage_mb=psutil.virtual_memory().used / 1024 / 1024,
                cpu_usage_percent=psutil.cpu_percent(),
                disk_io_mb=psutil.disk_io_counters().read_bytes / 1024 / 1024,
                network_io_mb=psutil.net_io_counters().bytes_sent / 1024 / 1024
            )
        except Exception as e:
            self.logger.warning(f"Failed to get system metrics: {e}")
            return RuntimeMetrics()
    
    def _calculate_health_score(
        self,
        status: str,
        cpu_usage_percent: float,
        memory_usage_percent: float,
        error_rate: float
    ) -> float:
        """Calculate overall health score (0-100)."""
        score = 100.0
        
        # Status impact
        if status == "HEALTHY":
            pass  # Full score
        elif status == "DEGRADED":
            score -= 30
        elif status == "UNHEALTHY":
            score -= 60
        
        # Resource usage impact
        if cpu_usage_percent > 80:
            score -= 20
        elif cpu_usage_percent > 60:
            score -= 10
        
        if memory_usage_percent > 80:
            score -= 20
        elif memory_usage_percent > 60:
            score -= 10
        
        # Error rate impact
        if error_rate > 5:
            score -= 25
        elif error_rate > 1:
            score -= 10
        
        return max(0, score)


# Global error handler instance
error_handler = EnterpriseErrorHandler()


def handle_error(
    error: Exception,
    level: ErrorLevel = ErrorLevel.ERROR,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    context: Optional[ErrorContext] = None,
    reraise: bool = False
) -> Optional[int]:
    """
    Convenience function to handle errors with enterprise-level logging.
    
    Args:
        error: The exception to handle
        level: Error severity level
        category: Error category
        context: Error context information
        reraise: Whether to re-raise the error after logging
    
    Returns:
        error_id: Database ID of logged error, or None if logging failed
    """
    error_id = error_handler.log_error(
        error=error,
        level=level,
        category=category,
        context=context
    )
    
    if reraise:
        raise error
    
    return error_id


def handle_pipeline_error(
    error: Exception,
    command_name: str,
    subcommand: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    reraise: bool = False
) -> Optional[int]:
    """
    Handle pipeline-specific errors with context.
    """
    error_context = ErrorContext(
        command_name=command_name,
        subcommand=subcommand,
        parameters=parameters,
        data_source=context.get('data_source') if context else None,
        table_name=context.get('table_name') if context else None,
        file_path=context.get('file_path') if context else None
    )
    
    return handle_error(
        error=error,
        level=ErrorLevel.ERROR,
        category=ErrorCategory.INGESTION,
        context=error_context,
        reraise=reraise
    )


def handle_model_error(
    error: Exception,
    model_name: str,
    operation_name: str,
    context: Optional[Dict[str, Any]] = None,
    reraise: bool = False
) -> Optional[int]:
    """
    Handle model-specific errors with context.
    """
    error_context = ErrorContext(
        model_name=model_name,
        operation_name=operation_name,
        data_source=context.get('data_source') if context else None,
        table_name=context.get('table_name') if context else None,
        batch_size=context.get('batch_size') if context else None
    )
    
    return handle_error(
        error=error,
        level=ErrorLevel.ERROR,
        category=ErrorCategory.MODELING,
        context=error_context,
        reraise=reraise
    )


class PerformanceTimer:
    """Context manager for timing operations and logging metrics."""
    
    def __init__(
        self,
        operation_name: str,
        metric_name: Optional[str] = None,
        model_name: Optional[str] = None,
        data_source: Optional[str] = None,
        log_metrics: bool = True
    ):
        self.operation_name = operation_name
        self.metric_name = metric_name or f"{operation_name}_duration"
        self.model_name = model_name
        self.data_source = data_source
        self.log_metrics = log_metrics
        self.start_time = None
        self.start_metrics = None
        self.rows_processed = 0
    
    def __enter__(self):
        self.start_time = time.time()
        self.start_metrics = error_handler._get_current_metrics()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            
            if self.log_metrics:
                error_handler.log_runtime_metrics(
                    metric_type="MODEL_INFERENCE" if self.model_name else "DATA_INGESTION",
                    metric_name=self.metric_name,
                    metric_value=duration_ms,
                    metric_unit="ms",
                    model_name=self.model_name,
                    data_source=self.data_source,
                    operation_name=self.operation_name,
                    throughput_per_second=self.rows_processed / (duration_ms / 1000) if duration_ms > 0 and self.rows_processed > 0 else 0
                )
        
        return False  # Don't suppress exceptions
    
    def update_rows_processed(self, count: int):
        """Update the count of rows processed."""
        self.rows_processed += count
