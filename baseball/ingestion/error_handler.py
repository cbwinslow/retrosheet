"""Robust error handling and recovery system for live data ingestion.

Provides comprehensive error handling, retry logic, circuit breakers,
and monitoring for live data pipeline components.

Author: Agent Cascade
Date: 2026-05-04
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar
from dataclasses import dataclass, field

from baseball.core.db import get_db_connection


logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class ErrorRecord:
    """Error record for tracking and analysis."""
    timestamp: datetime
    component: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    retry_count: int = 0


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_exceptions: List[Type[Exception]] = field(default_factory=lambda: [Exception])


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: Type[Exception] = Exception
    success_threshold: int = 3


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures."""
    
    def __init__(self, config: CircuitBreakerConfig) -> None:
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0
        
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to apply circuit breaker to a function."""
        def wrapper(*args, **kwargs) -> T:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.config.expected_exception as e:
                self._on_failure()
                raise
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        if self.last_failure_time is None:
            return False
        
        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.config.recovery_timeout
    
    def _on_success(self) -> None:
        """Handle successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class RetryHandler:
    """Retry handler with exponential backoff and jitter."""
    
    def __init__(self, config: RetryConfig) -> None:
        self.config = config
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to apply retry logic to a function."""
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(self.config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except tuple(self.config.retry_on_exceptions) as e:
                    last_exception = e
                    
                    if attempt == self.config.max_attempts - 1:
                        # Last attempt, re-raise the exception
                        raise
                    
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f'Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s'
                    )
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            # Add jitter to avoid thundering herd
            import random
            jitter_factor = random.uniform(0.8, 1.2)
            delay *= jitter_factor
        
        return delay


class ErrorHandler:
    """Comprehensive error handling and monitoring system."""
    
    def __init__(
        self,
        component_name: str,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        error_buffer_size: int = 1000,
    ) -> None:
        """Initialize error handler.
        
        Args:
            component_name: Name of the component being monitored
            retry_config: Configuration for retry logic
            circuit_breaker_config: Configuration for circuit breaker
            error_buffer_size: Number of errors to keep in memory
        """
        self.component_name = component_name
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        self.error_buffer_size = error_buffer_size
        
        # Error tracking
        self.error_buffer: List[ErrorRecord] = []
        self.error_counts: Dict[str, int] = {}
        self.error_rates: Dict[str, float] = {}
        
        # Circuit breakers and retry handlers
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_handlers: Dict[str, RetryHandler] = {}
        
        # Statistics
        self.stats = {
            'total_errors': 0,
            'errors_by_severity': {
                ErrorSeverity.LOW: 0,
                ErrorSeverity.MEDIUM: 0,
                ErrorSeverity.HIGH: 0,
                ErrorSeverity.CRITICAL: 0,
            },
            'resolved_errors': 0,
            'average_resolution_time': 0.0,
            'last_error_time': None,
        }
        
        logger.info(f'ErrorHandler initialized for component: {component_name}')
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ) -> ErrorRecord:
        """Handle an error and record it.
        
        Args:
            error: The exception that occurred
            context: Additional context information
            severity: Error severity level
            
        Returns:
            ErrorRecord for the handled error
        """
        error_record = ErrorRecord(
            timestamp=datetime.now(),
            component=self.component_name,
            error_type=type(error).__name__,
            error_message=str(error),
            severity=severity,
            context=context or {},
        )
        
        # Add to buffer
        self._add_error_to_buffer(error_record)
        
        # Update statistics
        self._update_statistics(error_record)
        
        # Log error
        self._log_error(error_record)
        
        # Store in database
        asyncio.create_task(self._store_error_record(error_record))
        
        # Check for alert conditions
        self._check_alert_conditions(error_record)
        
        return error_record
    
    def resolve_error(self, error_id: str) -> bool:
        """Mark an error as resolved.
        
        Args:
            error_id: Unique identifier for the error
            
        Returns:
            True if error was found and resolved
        """
        for error in self.error_buffer:
            if str(id(error)) == error_id and not error.resolved:
                error.resolved = True
                error.resolution_time = datetime.now()
                
                # Update statistics
                self.stats['resolved_errors'] += 1
                
                # Calculate resolution time
                if error.resolution_time and error.timestamp:
                    resolution_time = (error.resolution_time - error.timestamp).total_seconds()
                    self._update_average_resolution_time(resolution_time)
                
                logger.info(f'Error resolved: {error_id}')
                return True
        
        return False
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of error statistics."""
        recent_errors = [
            error for error in self.error_buffer
            if error.timestamp > datetime.now() - timedelta(hours=1)
        ]
        
        return {
            'component': self.component_name,
            'total_errors': self.stats['total_errors'],
            'recent_errors_1h': len(recent_errors),
            'error_rates': self.error_rates.copy(),
            'errors_by_severity': self.stats['errors_by_severity'].copy(),
            'resolved_errors': self.stats['resolved_errors'],
            'average_resolution_time': self.stats['average_resolution_time'],
            'last_error_time': self.stats['last_error_time'],
            'active_circuit_breakers': [
                name for name, cb in self.circuit_breakers.items()
                if cb.state == CircuitBreakerState.OPEN
            ],
        }
    
    def create_retry_handler(self, name: str, config: Optional[RetryConfig] = None) -> RetryHandler:
        """Create a retry handler for a specific operation."""
        handler_config = config or self.retry_config
        retry_handler = RetryHandler(handler_config)
        self.retry_handlers[name] = retry_handler
        return retry_handler
    
    def create_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Create a circuit breaker for a specific operation."""
        breaker_config = config or self.circuit_breaker_config
        circuit_breaker = CircuitBreaker(breaker_config)
        self.circuit_breakers[name] = circuit_breaker
        return circuit_breaker
    
    def safe_execute(
        self,
        func: Callable[..., T],
        operation_name: str,
        *args,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        **kwargs
    ) -> T:
        """Safely execute a function with error handling, retry, and circuit breaker.
        
        Args:
            func: Function to execute
            operation_name: Name of the operation for tracking
            retry_config: Override retry configuration
            circuit_breaker_config: Override circuit breaker configuration
            
        Returns:
            Result of the function execution
            
        Raises:
            Exception: If all retries fail or circuit breaker is open
        """
        # Get or create retry handler
        retry_handler = self.retry_handlers.get(operation_name)
        if retry_handler is None:
            retry_handler = self.create_retry_handler(operation_name, retry_config)
        
        # Get or create circuit breaker
        circuit_breaker = self.circuit_breakers.get(operation_name)
        if circuit_breaker is None:
            circuit_breaker = self.create_circuit_breaker(operation_name, circuit_breaker_config)
        
        # Apply circuit breaker and retry logic
        @circuit_breaker
        @retry_handler
        def safe_func(*args, **kwargs) -> T:
            return func(*args, **kwargs)
        
        try:
            return safe_func(*args, **kwargs)
        except Exception as e:
            # Handle the error
            self.handle_error(
                error=e,
                context={
                    'operation': operation_name,
                    'args': str(args)[:200],  # Truncate for storage
                    'kwargs': str(kwargs)[:200],
                },
                severity=ErrorSeverity.HIGH if isinstance(e, (ConnectionError, TimeoutError)) else ErrorSeverity.MEDIUM,
            )
            raise
    
    def _add_error_to_buffer(self, error_record: ErrorRecord) -> None:
        """Add error to buffer and maintain size."""
        self.error_buffer.append(error_record)
        
        # Trim buffer if necessary
        if len(self.error_buffer) > self.error_buffer_size:
            self.error_buffer.pop(0)
    
    def _update_statistics(self, error_record: ErrorRecord) -> None:
        """Update error statistics."""
        self.stats['total_errors'] += 1
        self.stats['errors_by_severity'][error_record.severity] += 1
        self.stats['last_error_time'] = error_record.timestamp
        
        # Update error counts by type
        error_type = error_record.error_type
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Calculate error rates
        self._calculate_error_rates()
    
    def _calculate_error_rates(self) -> None:
        """Calculate error rates by type."""
        total_errors = sum(self.error_counts.values())
        if total_errors == 0:
            return
        
        for error_type, count in self.error_counts.items():
            self.error_rates[error_type] = count / total_errors
    
    def _update_average_resolution_time(self, resolution_time: float) -> None:
        """Update average resolution time."""
        current_avg = self.stats['average_resolution_time']
        resolved_count = self.stats['resolved_errors']
        
        if resolved_count == 1:
            self.stats['average_resolution_time'] = resolution_time
        else:
            # Weighted average
            weight = 1.0 / resolved_count
            self.stats['average_resolution_time'] = (
                current_avg * (1 - weight) + resolution_time * weight
            )
    
    def _log_error(self, error_record: ErrorRecord) -> None:
        """Log error with appropriate level."""
        msg = f'[{self.component_name}] {error_record.error_type}: {error_record.error_message}'
        
        if error_record.severity == ErrorSeverity.CRITICAL:
            logger.critical(msg)
        elif error_record.severity == ErrorSeverity.HIGH:
            logger.error(msg)
        elif error_record.severity == ErrorSeverity.MEDIUM:
            logger.warning(msg)
        else:
            logger.info(msg)
    
    async def _store_error_record(self, error_record: ErrorRecord) -> None:
        """Store error record in database."""
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO monitoring.error_records
                    (component, error_type, error_message, severity, context, 
                     created_at, resolved, resolution_time, retry_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    error_record.component,
                    error_record.error_type,
                    error_record.error_message,
                    error_record.severity.value,
                    json.dumps(error_record.context),
                    error_record.timestamp,
                    error_record.resolved,
                    error_record.resolution_time,
                    error_record.retry_count,
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f'Failed to store error record: {e}')
    
    def _check_alert_conditions(self, error_record: ErrorRecord) -> None:
        """Check for alert conditions and send alerts."""
        alerts = []
        
        # Check for critical errors
        if error_record.severity == ErrorSeverity.CRITICAL:
            alerts.append({
                'type': 'critical_error',
                'message': f'Critical error in {self.component_name}: {error_record.error_message}',
                'severity': 'critical',
            })
        
        # Check for high error rate
        recent_errors = [
            error for error in self.error_buffer
            if error.timestamp > datetime.now() - timedelta(minutes=5)
        ]
        
        if len(recent_errors) > 10:
            alerts.append({
                'type': 'high_error_rate',
                'message': f'High error rate in {self.component_name}: {len(recent_errors)} errors in 5 minutes',
                'severity': 'warning',
            })
        
        # Check for circuit breaker activations
        open_breakers = [
            name for name, cb in self.circuit_breakers.items()
            if cb.state == CircuitBreakerState.OPEN
        ]
        
        if open_breakers:
            alerts.append({
                'type': 'circuit_breaker_open',
                'message': f'Circuit breakers open in {self.component_name}: {open_breakers}',
                'severity': 'warning',
            })
        
        # Send alerts
        for alert in alerts:
            asyncio.create_task(self._send_alert(alert))
    
    async def _send_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert notification."""
        logger.warning(f'ALERT [{alert["severity"].upper()}]: {alert["message"]}')
        
        # Store alert in database
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO monitoring.error_alerts
                    (alert_type, message, severity, component, created_at, metadata)
                    VALUES (%s, %s, %s, %s, NOW(), %s)
                """, (
                    alert['type'],
                    alert['message'],
                    alert['severity'],
                    self.component_name,
                    json.dumps(alert),
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f'Failed to store alert: {e}')
