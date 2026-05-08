"""
Intelligent error recovery system with auto-detection and smart fallbacks.

Provides:
- Pattern-based error detection
- Automatic recovery strategies
- Circuit breaking for cascading failures
- Smart fallback mechanisms
- Learning from error patterns
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import hashlib

from baseball.core.error_architecture import (
    ErrorEvent, RecoveryAction, ErrorSeverity, ErrorContext, ErrorHandler
)


class ErrorPattern(Enum):
    """Common error patterns for intelligent detection"""
    DATABASE_CONNECTION = "database_connection"
    NETWORK_TIMEOUT = "network_timeout"
    MEMORY_ERROR = "memory_error"
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT = "rate_limit"
    CONVERGENCE_FAILURE = "convergence_failure"
    DATA_CORRUPTION = "data_corruption"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


@dataclass
class RecoveryStrategy:
    """Recovery strategy configuration"""
    pattern: ErrorPattern
    primary_action: RecoveryAction
    fallback_actions: List[RecoveryAction] = field(default_factory=list)
    max_retries: int = 3
    backoff_factor: float = 2.0
    timeout_seconds: int = 30
    circuit_break_threshold: int = 5
    success_criteria: str = "no_exception"
    custom_handler: Optional[str] = None


class IntelligentErrorDetector:
    """Intelligent error pattern detection"""
    
    def __init__(self):
        self.pattern_signatures: Dict[ErrorPattern, List[str]] = {}
        self._setup_patterns()
        self.learning_history: List[Dict[str, Any]] = []
    
    def _setup_patterns(self):
        """Setup error pattern signatures"""
        self.pattern_signatures = {
            ErrorPattern.DATABASE_CONNECTION: [
                "connection", "sql", "database", "psycopg2", "mysql", "postgresql"
            ],
            ErrorPattern.NETWORK_TIMEOUT: [
                "timeout", "network", "connection refused", "unreachable", "read timeout"
            ],
            ErrorPattern.MEMORY_ERROR: [
                "memory", "out of memory", "allocation", "malloc", "heap"
            ],
            ErrorPattern.VALIDATION_ERROR: [
                "validation", "invalid", "malformed", "schema", "constraint"
            ],
            ErrorPattern.AUTHENTICATION_ERROR: [
                "auth", "authentication", "unauthorized", "forbidden", "credentials"
            ],
            ErrorPattern.RATE_LIMIT: [
                "rate limit", "too many requests", "throttle", "quota exceeded"
            ],
            ErrorPattern.CONVERGENCE_FAILURE: [
                "convergence", "not converged", "iteration limit", "tolerance"
            ],
            ErrorPattern.DATA_CORRUPTION: [
                "corruption", "corrupt", "invalid checksum", "crc", "md5 mismatch"
            ],
            ErrorPattern.RESOURCE_EXHAUSTION: [
                "exhausted", "no space left", "disk full", "quota", "limit reached"
            ]
        }
    
    def detect_pattern(self, error: Exception) -> Optional[ErrorPattern]:
        """Detect error pattern from exception"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        for pattern, signatures in self.pattern_signatures.items():
            if any(sig in error_str for sig in signatures):
                self._record_detection(pattern, error_str, error_type)
                return pattern
        
        return None
    
    def _record_detection(self, pattern: ErrorPattern, error_str: str, error_type: str):
        """Record pattern detection for learning"""
        detection_record = {
            'pattern': pattern.value,
            'error_string': error_str,
            'error_type': error_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'confidence': self._calculate_confidence(error_str, pattern)
        }
        
        self.learning_history.append(detection_record)
        
        # Keep only recent history
        if len(self.learning_history) > 1000:
            self.learning_history = self.learning_history[-500:]
    
    def _calculate_confidence(self, error_str: str, pattern: ErrorPattern) -> float:
        """Calculate confidence score for pattern detection"""
        signatures = self.pattern_signatures.get(pattern, [])
        matches = sum(1 for sig in signatures if sig in error_str)
        base_confidence = matches / len(signatures) if signatures else 0.0
        
        # Boost confidence based on historical accuracy
        recent_detections = [
            d for d in self.learning_history[-100:] 
            if d['pattern'] == pattern.value
        ]
        
        if recent_detections:
            accuracy = sum(1 for d in recent_detections if d['confidence'] > 0.5)
            accuracy_rate = accuracy / len(recent_detections)
            base_confidence *= (0.5 + accuracy_rate)
        
        return min(1.0, base_confidence)
    
    def get_pattern_suggestions(self, error: Exception) -> List[RecoveryStrategy]:
        """Get recovery strategies for detected pattern"""
        pattern = self.detect_pattern(error)
        if pattern is None:
            return []
        
        # Return strategies based on detected pattern
        strategies = []
        
        if pattern == ErrorPattern.DATABASE_CONNECTION:
            strategies.append(RecoveryStrategy(
                pattern=pattern,
                primary_action=RecoveryAction.RETRY,
                fallback_actions=[RecoveryAction.FALLBACK, RecoveryAction.ESCALATE],
                max_retries=3,
                backoff_factor=2.0,
                timeout_seconds=30
            ))
        
        elif pattern == ErrorPattern.NETWORK_TIMEOUT:
            strategies.append(RecoveryStrategy(
                pattern=pattern,
                primary_action=RecoveryAction.RETRY,
                fallback_actions=[RecoveryAction.FALLBACK, RecoveryAction.CIRCUIT_BREAK],
                max_retries=2,
                backoff_factor=1.5,
                timeout_seconds=60
            ))
        
        elif pattern == ErrorPattern.MEMORY_ERROR:
            strategies.append(RecoveryStrategy(
                pattern=pattern,
                primary_action=RecoveryAction.FALLBACK,
                fallback_actions=[RecoveryAction.ESCALATE],
                max_retries=1,
                backoff_factor=1.0,
                timeout_seconds=10
            ))
        
        elif pattern == ErrorPattern.VALIDATION_ERROR:
            strategies.append(RecoveryStrategy(
                pattern=pattern,
                primary_action=RecoveryAction.IGNORE,
                fallback_actions=[RecoveryAction.ESCALATE],
                max_retries=0,
                backoff_factor=1.0,
                timeout_seconds=0
            ))
        
        elif pattern == ErrorPattern.RATE_LIMIT:
            strategies.append(RecoveryStrategy(
                pattern=pattern,
                primary_action=RecoveryAction.CIRCUIT_BREAK,
                fallback_actions=[RecoveryAction.ESCALATE],
                max_retries=0,
                backoff_factor=1.0,
                timeout_seconds=300
            ))
        
        return strategies


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures"""
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count: int = 0
        self.last_failure_time: Optional[datetime] = None
        self.state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.state_history: List[Dict[str, Any]] = []
    
    async def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with circuit breaking"""
        if self.state == "OPEN":
            raise Exception("Circuit breaker is OPEN - blocking operation")
        
        if self.state == "HALF_OPEN":
            # Allow some operations through
            if self.failure_count >= self.failure_threshold:
                raise Exception("Circuit breaker is HALF_OPEN - blocking operation")
        
        try:
            result = await operation(*args, **kwargs)
            self._record_success()
            return result
        
        except Exception as e:
            self._record_failure()
            raise e
    
    def _record_success(self):
        """Record successful operation"""
        self.failure_count = max(0, self.failure_count - 1)
        if self.failure_count == 0:
            self.state = "CLOSED"
        
        self.state_history.append({
            'state': self.state,
            'failure_count': self.failure_count,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def _record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
        elif self.failure_count >= self.failure_threshold // 2:
            self.state = "HALF_OPEN"
        
        self.state_history.append({
            'state': self.state,
            'failure_count': self.failure_count,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def reset(self):
        """Reset circuit breaker"""
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_failure_time = None


class SmartRetryManager:
    """Smart retry manager with exponential backoff"""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retry_history: List[Dict[str, Any]] = []
    
    async def execute_with_retry(self, operation: Callable, max_retries: int = 3, 
                               backoff_factor: float = 2.0, *args, **kwargs) -> Any:
        """Execute operation with intelligent retry"""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                delay = self._calculate_delay(attempt, backoff_factor)
                if attempt > 0:
                    await asyncio.sleep(delay)
                
                result = await operation(*args, **kwargs)
                self._record_success(attempt, delay)
                return result
            
            except Exception as e:
                last_exception = e
                self._record_failure(attempt, e, delay)
                
                # Check if we should stop retrying
                if self._should_stop_retrying(e, attempt, max_retries):
                    break
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int, backoff_factor: float) -> float:
        """Calculate delay with exponential backoff"""
        delay = self.base_delay * (backoff_factor ** attempt)
        return min(delay, self.max_delay)
    
    def _should_stop_retrying(self, error: Exception, attempt: int, max_retries: int) -> bool:
        """Determine if we should stop retrying"""
        if attempt >= max_retries:
            return True
        
        error_str = str(error).lower()
        
        # Don't retry on certain errors
        non_retryable_errors = [
            "authentication", "authorization", "forbidden", "not found",
            "invalid", "malformed", "syntax", "permission denied"
        ]
        
        return any(err in error_str for err in non_retryable_errors)
    
    def _record_success(self, attempt: int, delay: float):
        """Record successful retry"""
        self.retry_history.append({
            'attempt': attempt,
            'delay': delay,
            'success': True,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def _record_failure(self, attempt: int, error: Exception, delay: float):
        """Record failed retry"""
        self.retry_history.append({
            'attempt': attempt,
            'delay': delay,
            'success': False,
            'error': str(error),
            'timestamp': datetime.now(timezone.utc()).isoformat()
        })
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """Get retry statistics"""
        if not self.retry_history:
            return {}
        
        total_retries = len(self.retry_history)
        successful_retries = sum(1 for r in self.retry_history if r['success'])
        success_rate = successful_retries / total_retries if total_retries > 0 else 0.0
        
        return {
            'total_retries': total_retries,
            'successful_retries': successful_retries,
            'success_rate': success_rate,
            'average_delay': sum(r['delay'] for r in self.retry_history) / total_retries
        }


class FallbackManager:
    """Fallback manager for smart fallback strategies"""
    
    def __init__(self):
        self.fallback_strategies: Dict[str, List[Callable]] = {}
        self.fallback_history: List[Dict[str, Any]] = []
    
    def register_fallback(self, operation_name: str, strategy: Callable):
        """Register a fallback strategy"""
        if operation_name not in self.fallback_strategies:
            self.fallback_strategies[operation_name] = []
        
        self.fallback_strategies[operation_name].append(strategy)
    
    async def execute_with_fallback(self, operation_name: str, primary_operation: Callable, 
                                 *args, **kwargs) -> Any:
        """Execute operation with fallback strategies"""
        strategies = self.fallback_strategies.get(operation_name, [])
        
        if not strategies:
            # No fallbacks, just execute primary
            return await primary_operation(*args, **kwargs)
        
        # Try primary operation first
        try:
            result = await primary_operation(*args, **kwargs)
            self._record_success(operation_name, "primary")
            return result
        
        except Exception as primary_error:
            self._record_failure(operation_name, "primary", str(primary_error))
            
            # Try fallback strategies in order
            for i, fallback_strategy in enumerate(strategies):
                try:
                    result = await fallback_strategy(*args, **kwargs)
                    self._record_success(operation_name, f"fallback_{i}")
                    return result
                
                except Exception as fallback_error:
                    self._record_failure(operation_name, f"fallback_{i}", str(fallback_error))
                    continue
            
            # All fallbacks failed
            raise Exception(f"All fallback strategies failed for {operation_name}")
    
    def _record_success(self, operation_name: str, strategy: str):
        """Record successful operation"""
        self.fallback_history.append({
            'operation': operation_name,
            'strategy': strategy,
            'success': True,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def _record_failure(self, operation_name: str, strategy: str, error: str):
        """Record failed operation"""
        self.fallback_history.append({
            'operation': operation_name,
            'strategy': strategy,
            'success': False,
            'error': error,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def get_fallback_stats(self) -> Dict[str, Any]:
        """Get fallback statistics"""
        if not self.fallback_history:
            return {}
        
        total_operations = len(self.fallback_history)
        successful_operations = sum(1 for op in self.fallback_history if op['success'])
        success_rate = successful_operations / total_operations if total_operations > 0 else 0.0
        
        return {
            'total_operations': total_operations,
            'successful_operations': successful_operations,
            'success_rate': success_rate
        }


class IntelligentRecoveryEngine:
    """Main intelligent recovery engine"""
    
    def __init__(self):
        self.detector = IntelligentErrorDetector()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_managers: Dict[str, SmartRetryManager] = {}
        self.fallback_manager = FallbackManager()
        self.recovery_history: List[Dict[str, Any]] = []
    
    async def handle_error_intelligently(self, error: Exception, context: ErrorContext, 
                                      operation_name: str = None) -> bool:
        """Handle error with intelligent recovery"""
        # Detect error pattern
        pattern = self.detector.detect_pattern(error)
        
        # Get recovery strategies
        strategies = self.detector.get_pattern_suggestions(error)
        
        if not strategies:
            # No pattern detected, use default recovery
            await self._default_recovery(error, context)
            return False
        
        # Try each strategy
        for strategy in strategies:
            success = await self._execute_strategy(strategy, error, context, operation_name)
            if success:
                self._record_recovery(error, pattern, strategy.primary_action, True)
                return True
        
        # All strategies failed
        self._record_recovery(error, pattern, RecoveryAction.ESCALATE, False)
        return False
    
    async def _execute_strategy(self, strategy: RecoveryStrategy, error: Exception, 
                             context: ErrorContext, operation_name: str) -> bool:
        """Execute a specific recovery strategy"""
        try:
            if strategy.primary_action == RecoveryAction.RETRY:
                return await self._retry_operation(error, context, operation_name, strategy)
            
            elif strategy.primary_action == RecoveryAction.FALLBACK:
                return await self._fallback_operation(error, context, operation_name)
            
            elif strategy.primary_action == RecoveryAction.CIRCUIT_BREAK:
                return await self._circuit_break_operation(error, context, operation_name)
            
            elif strategy.primary_action == RecoveryAction.IGNORE:
                return True  # Simply ignore the error
            
            elif strategy.primary_action == RecoveryAction.ESCALATE:
                return False  # Let it escalate
            
            return False
        
        except Exception as e:
            # Strategy execution failed
            return False
    
    async def _retry_operation(self, error: Exception, context: ErrorContext, 
                           operation_name: str, strategy: RecoveryStrategy) -> bool:
        """Execute retry operation"""
        key = f"{context.command_name}:{operation_name}"
        
        if key not in self.retry_managers:
            self.retry_managers[key] = SmartRetryManager()
        
        retry_manager = self.retry_managers[key]
        
        try:
            await retry_manager.execute_with_retry(
                operation=lambda: self._retry_attempt(error, context),
                max_retries=strategy.max_retries,
                backoff_factor=strategy.backoff_factor
            )
            return True
        
        except Exception:
            return False
    
    async def _retry_attempt(self, original_error: Exception, context: ErrorContext):
        """Attempt the retry operation"""
        # This would be implemented based on the specific operation
        # For now, just re-raise the original error
        raise original_error
    
    async def _fallback_operation(self, error: Exception, context: ErrorContext, 
                              operation_name: str) -> bool:
        """Execute fallback operation"""
        key = f"{context.command_name}:{operation_name}"
        
        try:
            await self.fallback_manager.execute_with_fallback(
                operation_name=key,
                primary_operation=lambda: self._fallback_attempt(error, context),
                *[]  # No args for now
            )
            return True
        
        except Exception:
            return False
    
    async def _fallback_attempt(self, original_error: Exception, context: ErrorContext):
        """Attempt the fallback operation"""
        # This would be implemented based on the specific operation
        # For now, just re-raise the original error
        raise original_error
    
    async def _circuit_break_operation(self, error: Exception, context: ErrorContext, 
                                  operation_name: str, strategy: RecoveryStrategy) -> bool:
        """Execute circuit breaker operation"""
        key = f"{context.command_name}:{operation_name}"
        
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = CircuitBreaker(
                failure_threshold=strategy.circuit_break_threshold,
                timeout_seconds=strategy.timeout_seconds
            )
        
        circuit_breaker = self.circuit_breakers[key]
        
        try:
            await circuit_breaker.execute(
                operation=lambda: self._circuit_break_attempt(error, context)
            )
            return True
        
        except Exception:
            return False
    
    async def _circuit_break_attempt(self, original_error: Exception, context: ErrorContext):
        """Attempt the circuit breaker operation"""
        # This would be implemented based on the specific operation
        # For now, just re-raise the original error
        raise original_error
    
    async def _default_recovery(self, error: Exception, context: ErrorContext):
        """Default recovery when no pattern is detected"""
        # Basic retry for unknown errors
        try:
            await asyncio.sleep(1)  # Brief delay
            return True
        except Exception:
            return False
    
    def _record_recovery(self, error: Exception, pattern: ErrorPattern, action: RecoveryAction, success: bool):
        """Record recovery attempt"""
        recovery_record = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'pattern': pattern.value if pattern else 'unknown',
            'action': action.value,
            'success': success,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.recovery_history.append(recovery_record)
        
        # Keep only recent history
        if len(self.recovery_history) > 1000:
            self.recovery_history = self.recovery_history[-500:]
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        if not self.recovery_history:
            return {}
        
        total_recoveries = len(self.recovery_history)
        successful_recoveries = sum(1 for r in self.recovery_history if r['success'])
        success_rate = successful_recoveries / total_recoveries if total_recoveries > 0 else 0.0
        
        return {
            'total_recoveries': total_recoveries,
            'successful_recoveries': successful_recoveries,
            'success_rate': success_rate,
            'pattern_distribution': self._get_pattern_distribution()
        }
    
    def _get_pattern_distribution(self) -> Dict[str, int]:
        """Get distribution of error patterns"""
        pattern_counts = {}
        for record in self.recovery_history:
            pattern = record.get('pattern', 'unknown')
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        return pattern_counts


# Global intelligent recovery engine
intelligent_recovery = IntelligentRecoveryEngine()


# Concrete error handler implementations for use by integration_layer.py
class DatabaseErrorHandler(ErrorHandler):
    """Handles database connection and query errors with retry logic."""

    async def can_handle(self, event: ErrorEvent) -> bool:
        """Check if this is a database error."""
        error_msg = str(event.error).lower()
        db_keywords = ['connection', 'sql', 'database', 'psycopg2', 'mysql', 'postgresql',
                       'operationalerror', 'programmingerror', 'integrityerror']
        return any(kw in error_msg for kw in db_keywords)

    async def handle(self, event: ErrorEvent) -> RecoveryAction:
        """Attempt database error recovery."""
        if event.recovery_attempts < event.max_retries:
            return RecoveryAction.RETRY
        return RecoveryAction.ESCALATE

    def get_priority(self) -> int:
        """Database errors get high priority."""
        return 80


class NetworkErrorHandler(ErrorHandler):
    """Handles network timeout and connection refused errors."""

    async def can_handle(self, event: ErrorEvent) -> bool:
        """Check if this is a network error."""
        error_msg = str(event.error).lower()
        net_keywords = ['timeout', 'network', 'connection refused', 'unreachable',
                        'read timeout', 'connectionerror', 'urlerror']
        return any(kw in error_msg for kw in net_keywords)

    async def handle(self, event: ErrorEvent) -> RecoveryAction:
        """Attempt network error recovery."""
        if event.recovery_attempts < event.max_retries:
            return RecoveryAction.RETRY
        return RecoveryAction.FALLBACK

    def get_priority(self) -> int:
        """Network errors get medium-high priority."""
        return 70


class ModelErrorHandler(ErrorHandler):
    """Handles ML model inference and training errors."""

    async def can_handle(self, event: ErrorEvent) -> bool:
        """Check if this is a model error."""
        error_msg = str(event.error).lower()
        model_keywords = ['model', 'predict', 'inference', 'feature', 'shape',
                          'valueerror', 'nan', 'converge', 'overflow']
        return any(kw in error_msg for kw in model_keywords)

    async def handle(self, event: ErrorEvent) -> RecoveryAction:
        """Attempt model error recovery."""
        if event.recovery_attempts < event.max_retries:
            return RecoveryAction.FALLBACK
        return RecoveryAction.ESCALATE

    def get_priority(self) -> int:
        """Model errors get medium priority."""
        return 60
