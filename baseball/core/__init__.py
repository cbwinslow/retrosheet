"""Core shared utilities for baseball platform with comprehensive error handling and monitoring.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from baseball.core.settings import (
    DatabaseSettings,
    DataPathsSettings,
    LoggingSettings,
    MLBStatsAPISettings,
    ModelSettings,
    Settings,
    get_settings,
    settings,
)
from baseball.core.cache import (
    CacheManager,
    ModelPredictionCache,
    FeatureCache,
    cache_manager,
    cached,
)


__all__ = [
    'DataPathsSettings',
    'DatabaseSettings',
    'LoggingSettings',
    'MLBStatsAPISettings',
    'ModelSettings',
    'Settings',
    'get_settings',
    'settings',
    # Cache
    'CacheManager',
    'ModelPredictionCache',
    'FeatureCache',
    'cache_manager',
    'cached',
]

# Error handling and monitoring
from baseball.core.error_architecture import (
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    ErrorEvent,
    RecoveryAction,
    ErrorHandler,
    IntelligentErrorRouter,
    DatabaseErrorHandler,
    NetworkErrorHandler,
    ModelErrorHandler,
    SystemWideErrorManager,
    handle_error_intelligent,
    BenchmarkingMixin,
    ConfigurableMixin,
    EncapsulatedComponent
)

from baseball.core.intelligent_recovery import (
    ErrorPattern,
    RecoveryStrategy,
    IntelligentErrorDetector,
    CircuitBreaker,
    SmartRetryManager,
    FallbackManager,
    IntelligentRecoveryEngine,
    intelligent_recovery
)

from baseball.core.system_monitoring import (
    MetricType,
    SystemMetrics,
    PerformanceMetrics,
    HealthStatus,
    SystemMonitor,
    system_monitor
)

from baseball.core.plugin_system import (
    PluginType,
    PluginMetadata,
    Plugin,
    PluginRegistry,
    PluginLoader,
    ModularErrorHandler,
    ModularDataSource,
    ModularModelComponent,
    ModularMonitoring,
    ModularConfigProvider,
    plugin_registry,
    plugin_loader,
    initialize_plugin_system,
    register_plugin,
    get_plugin,
    get_plugins_by_type
)

from baseball.core.integration_layer import (
    ComponentConfig,
    BaseballIntegrationLayer,
    with_integration,
    ComponentFactory,
    get_integration_layer,
    initialize_baseball_integration,
    shutdown_baseball_integration,
    run_with_monitoring,
    run_with_error_handling,
    run_with_benchmarking,
    IntegratedComponent,
    IntegratedDataSource,
    IntegratedModel,
    IntegratedService
)


__all__ = [
    # Settings
    'DataPathsSettings',
    'DatabaseSettings',
    'LoggingSettings',
    'MLBStatsAPISettings',
    'ModelSettings',
    'Settings',
    'get_settings',
    'settings',
    
    # Cache
    'CacheManager',
    'ModelPredictionCache',
    'FeatureCache',
    'cache_manager',
    'cached',
    
    # Error Architecture
    'ErrorSeverity',
    'ErrorCategory',
    'ErrorContext',
    'ErrorEvent',
    'RecoveryAction',
    'ErrorHandler',
    'IntelligentErrorRouter',
    'DatabaseErrorHandler',
    'NetworkErrorHandler',
    'ModelErrorHandler',
    'SystemWideErrorManager',
    'handle_error_intelligent',
    'BenchmarkingMixin',
    'ConfigurableMixin',
    'EncapsulatedComponent',
    
    # Intelligent Recovery
    'ErrorPattern',
    'RecoveryStrategy',
    'IntelligentErrorDetector',
    'CircuitBreaker',
    'SmartRetryManager',
    'FallbackManager',
    'IntelligentRecoveryEngine',
    'intelligent_recovery',
    
    # System Monitoring
    'MetricType',
    'SystemMetrics',
    'PerformanceMetrics',
    'HealthStatus',
    'SystemMonitor',
    'system_monitor',
    
    # Plugin System
    'PluginType',
    'PluginMetadata',
    'Plugin',
    'PluginRegistry',
    'PluginLoader',
    'ModularErrorHandler',
    'ModularDataSource',
    'ModularModelComponent',
    'ModularMonitoring',
    'ModularConfigProvider',
    'plugin_registry',
    'plugin_loader',
    'initialize_plugin_system',
    'register_plugin',
    'get_plugin',
    'get_plugins_by_type',
    
    # Integration Layer
    'ComponentConfig',
    'BaseballIntegrationLayer',
    'with_integration',
    'ComponentFactory',
    'get_integration_layer',
    'initialize_baseball_integration',
    'shutdown_baseball_integration',
    'run_with_monitoring',
    'run_with_error_handling',
    'run_with_benchmarking',
    'IntegratedComponent',
    'IntegratedDataSource',
    'IntegratedModel',
    'IntegratedService'
]
