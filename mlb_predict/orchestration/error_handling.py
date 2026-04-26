"""Error Handling Abstraction Layer.

Provides retry logic, circuit breakers, and graceful degradation for database operations.
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

import psycopg2


T = TypeVar('T')

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategies for failed operations."""
    FIXED = 'fixed'
    EXPONENTIAL = 'exponential'
    LINEAR = 'linear'


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = 'closed'      # Normal operation
    OPEN = 'open'          # Failing, reject calls
    HALF_OPEN = 'half_open'  # Testing if recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retryable_exceptions: tuple[type[Exception], ...] = (
        psycopg2.OperationalError,
        psycopg2.InterfaceError,
        ConnectionError,
    )
    on_retry: Callable[[int, Exception], None] | None = None


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3


@dataclass
class OperationResult:
    """Result of an operation with metadata."""
    success: bool
    value: Any = None
    error: Exception | None = None
    attempts: int = 0
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time: float | None = None
        self.half_open_calls = 0

    def can_execute(self) -> bool:
        """Check if operation can execute."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info(f'Circuit {self.name}: transitioning to HALF_OPEN')
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.config.half_open_max_calls

        return True

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try reset."""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout

    def record_success(self) -> None:
        """Record successful operation."""
        self.failures = 0
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.state = CircuitState.CLOSED
                logger.info(f'Circuit {self.name}: closed (recovered)')

    def record_failure(self) -> None:
        """Record failed operation."""
        self.failures += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f'Circuit {self.name}: opened (failure in half-open)')
        elif self.failures >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f'Circuit {self.name}: opened ({self.failures} failures)')


def with_retry(config: RetryConfig | None = None):
    """Decorator to add retry logic to a function."""
    cfg = config or RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., OperationResult]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> OperationResult:
            start_time = time.time()
            last_error: Exception | None = None

            for attempt in range(cfg.max_retries + 1):
                try:
                    value = func(*args, **kwargs)
                    return OperationResult(
                        success=True,
                        value=value,
                        attempts=attempt + 1,
                        duration_ms=(time.time() - start_time) * 1000,
                    )
                except Exception as e:
                    last_error = e

                    # Check if exception is retryable
                    if not isinstance(e, cfg.retryable_exceptions):
                        break

                    # Don't retry on last attempt
                    if attempt >= cfg.max_retries:
                        break

                    # Calculate delay
                    if cfg.strategy == RetryStrategy.FIXED:
                        delay = cfg.base_delay
                    elif cfg.strategy == RetryStrategy.EXPONENTIAL:
                        delay = min(cfg.base_delay * (2 ** attempt), cfg.max_delay)
                    else:  # LINEAR
                        delay = cfg.base_delay * (attempt + 1)

                    logger.warning(
                        f'{func.__name__} failed (attempt {attempt + 1}), '
                        f'retrying in {delay:.1f}s: {e}',
                    )

                    if cfg.on_retry:
                        cfg.on_retry(attempt + 1, e)

                    time.sleep(delay)

            # All retries exhausted
            return OperationResult(
                success=False,
                error=last_error,
                attempts=cfg.max_retries + 1,
                duration_ms=(time.time() - start_time) * 1000,
            )

        return wrapper
    return decorator


def with_circuit_breaker(breaker: CircuitBreaker):
    """Decorator to add circuit breaker to a function."""
    def decorator(func: Callable[..., T]) -> Callable[..., OperationResult]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> OperationResult:
            if not breaker.can_execute():
                return OperationResult(
                    success=False,
                    error=Exception(f"Circuit breaker '{breaker.name}' is OPEN"),
                    metadata={'circuit_state': breaker.state.value},
                )

            start_time = time.time()
            try:
                value = func(*args, **kwargs)
                breaker.record_success()
                return OperationResult(
                    success=True,
                    value=value,
                    duration_ms=(time.time() - start_time) * 1000,
                )
            except Exception as e:
                breaker.record_failure()
                return OperationResult(
                    success=False,
                    error=e,
                    duration_ms=(time.time() - start_time) * 1000,
                )

        return wrapper
    return decorator


class DatabaseOperation:
    """Wrapper for database operations with full error handling."""

    def __init__(
        self,
        name: str,
        retry_config: RetryConfig | None = None,
        breaker: CircuitBreaker | None = None,
    ):
        self.name = name
        self.retry_config = retry_config or RetryConfig()
        self.breaker = breaker

    def execute(
        self,
        conn: psycopg2.extensions.connection,
        operation: Callable[[psycopg2.extensions.connection], T],
    ) -> OperationResult:
        """Execute database operation with full error handling."""
        start_time = time.time()

        # Check circuit breaker
        if self.breaker and not self.breaker.can_execute():
            return OperationResult(
                success=False,
                error=Exception(f"Circuit breaker '{self.breaker.name}' is OPEN"),
                metadata={'circuit_state': self.breaker.state.value},
            )

        last_error: Exception | None = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                value = operation(conn)

                if self.breaker:
                    self.breaker.record_success()

                return OperationResult(
                    success=True,
                    value=value,
                    attempts=attempt + 1,
                    duration_ms=(time.time() - start_time) * 1000,
                    metadata={'operation': self.name},
                )

            except self.retry_config.retryable_exceptions as e:
                last_error = e

                if attempt >= self.retry_config.max_retries:
                    break

                # Calculate delay
                if self.retry_config.strategy == RetryStrategy.EXPONENTIAL:
                    delay = min(
                        self.retry_config.base_delay * (2 ** attempt),
                        self.retry_config.max_delay,
                    )
                else:
                    delay = self.retry_config.base_delay

                logger.warning(
                    f'{self.name} failed (attempt {attempt + 1}), '
                    f'retrying in {delay:.1f}s: {e}',
                )

                if self.retry_config.on_retry:
                    self.retry_config.on_retry(attempt + 1, e)

                time.sleep(delay)

            except Exception as e:
                # Non-retryable exception
                last_error = e
                break

        # All retries exhausted or non-retryable error
        if self.breaker:
            self.breaker.record_failure()

        return OperationResult(
            success=False,
            error=last_error,
            attempts=attempt + 1,
            duration_ms=(time.time() - start_time) * 1000,
            metadata={'operation': self.name, 'final_error': str(last_error)},
        )


# Pre-configured circuit breakers
db_circuit_breaker = CircuitBreaker(
    'database',
    CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0),
)

api_circuit_breaker = CircuitBreaker(
    'external_api',
    CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60.0),
)
