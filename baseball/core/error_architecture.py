"""
Comprehensive error handling architecture for baseball namespace.

Provides intelligent, flexible, modular error handling with:
- Plugin-based error handlers
- Intelligent error detection and auto-recovery
- System-wide benchmarking and monitoring
- Encapsulated abstraction layers
- Flexible configuration management
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Type, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import json
from datetime import datetime, timezone

from baseball.core.error_handler import ErrorLevel, ErrorCategory, ErrorContext


class ErrorSeverity(Enum):
    """Error severity levels for intelligent routing"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class RecoveryAction(Enum):
    """Automatic recovery actions"""
    RETRY = "RETRY"
    FALLBACK = "FALLBACK"
    CIRCUIT_BREAK = "CIRCUIT_BREAK"
    ESCALATE = "ESCALATE"
    IGNORE = "IGNORE"


@dataclass
class ErrorEvent:
    """Rich error event with full context"""
    error: Exception
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stack_trace: str = field(default="")
    metadata: Dict[str, Any] = field(default_factory=dict)
    recovery_attempts: int = 0
    max_retries: int = 3


class ErrorHandler(ABC):
    """Abstract base class for plugin error handlers"""
    
    @abstractmethod
    async def can_handle(self, event: ErrorEvent) -> bool:
        """Check if this handler can process the error"""
        pass
    
    @abstractmethod
    async def handle(self, event: ErrorEvent) -> RecoveryAction:
        """Process the error and return recovery action"""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Handler priority (higher = more priority)"""
        pass


class IntelligentErrorRouter:
    """Intelligent error routing with plugin system"""
    
    def __init__(self):
        self.handlers: List[ErrorHandler] = []
        self.circuit_breakers: Dict[str, bool] = {}
        self.error_patterns: Dict[str, RecoveryAction] = {}
        self.performance_metrics: Dict[str, float] = {}
    
    def register_handler(self, handler: ErrorHandler):
        """Register a plugin error handler"""
        self.handlers.append(handler)
        self.handlers.sort(key=lambda h: h.get_priority(), reverse=True)
    
    async def route_error(self, event: ErrorEvent) -> RecoveryAction:
        """Route error to appropriate handler"""
        # Check circuit breakers
        circuit_key = f"{event.category.value}:{event.context.command_name}"
        if self.circuit_breakers.get(circuit_key, False):
            return RecoveryAction.ESCALATE
        
        # Check error patterns
        error_key = f"{type(event.error).__name__}"
        if error_key in self.error_patterns:
            return self.error_patterns[error_key]
        
        # Route to handlers
        for handler in self.handlers:
            if await handler.can_handle(event):
                try:
                    action = await handler.handle(event)
                    self._update_metrics(handler.__class__.__name__, True)
                    return action
                except Exception as e:
                    self._update_metrics(handler.__class__.__name__, False)
                    continue
        
        return RecoveryAction.ESCALATE
    
    def _update_metrics(self, handler_name: str, success: bool):
        """Update handler performance metrics"""
        key = f"{handler_name}_success_rate"
        current = self.performance_metrics.get(key, 0.0)
        self.performance_metrics[key] = (current + (1.0 if success else 0.0)) / 2


class DatabaseErrorHandler(ErrorHandler):
    """Database-specific error handler with intelligent recovery"""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
    
    async def can_handle(self, event: ErrorEvent) -> bool:
        return event.category == ErrorCategory.DATABASE
    
    async def handle(self, event: ErrorEvent) -> RecoveryAction:
        if "connection" in str(event.error).lower():
            if event.recovery_attempts < self.max_retries:
                await asyncio.sleep(2 ** event.recovery_attempts)  # Exponential backoff
                return RecoveryAction.RETRY
            return RecoveryAction.FALLBACK
        
        if "timeout" in str(event.error).lower():
            return RecoveryAction.RETRY
        
        return RecoveryAction.ESCALATE
    
    def get_priority(self) -> int:
        return 100


class NetworkErrorHandler(ErrorHandler):
    """Network-specific error handler with circuit breaking"""
    
    def __init__(self, failure_threshold: int = 5):
        self.failure_threshold = failure_threshold
        self.failure_count = 0
    
    async def can_handle(self, event: ErrorEvent) -> bool:
        return event.category == ErrorCategory.NETWORK
    
    async def handle(self, event: ErrorEvent) -> RecoveryAction:
        self.failure_count += 1
        
        if self.failure_count >= self.failure_threshold:
            return RecoveryAction.CIRCUIT_BREAK
        
        if "timeout" in str(event.error).lower():
            return RecoveryAction.RETRY
        
        return RecoveryAction.FALLBACK
    
    def get_priority(self) -> int:
        return 90


class ModelErrorHandler(ErrorHandler):
    """Model-specific error handler with intelligent fallback"""
    
    async def can_handle(self, event: ErrorEvent) -> bool:
        return event.category == ErrorCategory.MODELING
    
    async def handle(self, event: ErrorEvent) -> RecoveryAction:
        if "memory" in str(event.error).lower():
            return RecoveryAction.FALLBACK
        
        if "convergence" in str(event.error).lower():
            return RecoveryAction.RETRY
        
        return RecoveryAction.ESCALATE
    
    def get_priority(self) -> int:
        return 80


class SystemWideErrorManager:
    """System-wide error management with intelligent routing"""
    
    def __init__(self):
        self.router = IntelligentErrorRouter()
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default error handlers"""
        self.router.register_handler(DatabaseErrorHandler())
        self.router.register_handler(NetworkErrorHandler())
        self.router.register_handler(ModelErrorHandler())
    
    async def handle_error(self, error: Exception, context: ErrorContext, 
                          severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> bool:
        """Handle error with intelligent routing"""
        event = ErrorEvent(
            error=error,
            severity=severity,
            category=self._categorize_error(error),
            context=context
        )
        
        action = await self.router.route_error(event)
        
        # Execute recovery action
        return await self._execute_recovery(action, event)
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Intelligently categorize errors"""
        error_str = str(error).lower()
        
        if "database" in error_str or "sql" in error_str:
            return ErrorCategory.DATABASE
        elif "network" in error_str or "connection" in error_str:
            return ErrorCategory.NETWORK
        elif "model" in error_str or "training" in error_str:
            return ErrorCategory.MODELING
        elif "validation" in error_str:
            return ErrorCategory.VALIDATION
        else:
            return ErrorCategory.SYSTEM
    
    async def _execute_recovery(self, action: RecoveryAction, event: ErrorEvent) -> bool:
        """Execute recovery action"""
        if action == RecoveryAction.RETRY:
            event.recovery_attempts += 1
            return event.recovery_attempts < event.max_retries
        
        elif action == RecoveryAction.FALLBACK:
            # Implement fallback logic
            return True
        
        elif action == RecoveryAction.CIRCUIT_BREAK:
            # Implement circuit breaking
            return False
        
        elif action == RecoveryAction.ESCALATE:
            # Implement escalation
            return False
        
        return True


# Global error manager instance
error_manager = SystemWideErrorManager()


def handle_error_intelligent(error: Exception, context: ErrorContext, 
                           severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> bool:
    """Convenience function for intelligent error handling"""
    return asyncio.run(error_manager.handle_error(error, context, severity))


class BenchmarkingMixin:
    """Mixin for adding benchmarking to any class"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._benchmarks: Dict[str, List[float]] = {}
        self._start_times: Dict[str, float] = {}
    
    def start_benchmark(self, operation: str):
        """Start benchmarking an operation"""
        self._start_times[operation] = time.time()
    
    def end_benchmark(self, operation: str) -> float:
        """End benchmarking and return duration"""
        if operation in self._start_times:
            duration = time.time() - self._start_times[operation]
            if operation not in self._benchmarks:
                self._benchmarks[operation] = []
            self._benchmarks[operation].append(duration)
            del self._start_times[operation]
            return duration
        return 0.0
    
    def get_benchmark_stats(self, operation: str) -> Dict[str, float]:
        """Get benchmark statistics"""
        if operation not in self._benchmarks:
            return {}
        
        times = self._benchmarks[operation]
        return {
            'count': len(times),
            'avg': sum(times) / len(times),
            'min': min(times),
            'max': max(times),
            'total': sum(times)
        }


class ConfigurableMixin:
    """Mixin for adding configuration management"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config: Dict[str, Any] = {}
    
    def set_config(self, key: str, value: Any):
        """Set configuration value"""
        self._config[key] = value
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)
    
    def load_config(self, config_dict: Dict[str, Any]):
        """Load configuration from dictionary"""
        self._config.update(config_dict)


class EncapsulatedComponent(BenchmarkingMixin, ConfigurableMixin):
    """Base class for all encapsulated components"""
    
    def __init__(self, name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.error_context = ErrorContext(
            command_name=name,
            operation_name="component_operation"
        )
    
    async def execute_with_error_handling(self, operation: Callable, *args, **kwargs):
        """Execute operation with intelligent error handling"""
        self.start_benchmark(f"{self.name}_operation")
        
        try:
            result = await operation(*args, **kwargs)
            self.end_benchmark(f"{self.name}_operation")
            return result
        
        except Exception as e:
            self.end_benchmark(f"{self.name}_operation")
            await handle_error_intelligent(e, self.error_context)
            raise
