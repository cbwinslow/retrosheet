"""
Integration layer that brings together all error handling, monitoring, and plugin systems.

Provides:
- Unified interface for all baseball components
- Automatic error handling and recovery
- System-wide monitoring and benchmarking
- Plugin management and orchestration
- Encapsulated abstraction layers
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps

from baseball.core.error_architecture import (
    EncapsulatedComponent, ErrorContext, handle_error_intelligent,
    ErrorSeverity
)
from baseball.core.intelligent_recovery import intelligent_recovery
from baseball.core.system_monitoring import system_monitor
from baseball.core.plugin_system import plugin_registry, PluginType


@dataclass
class ComponentConfig:
    """Configuration for baseball components"""
    name: str
    component_type: str
    enabled: bool = True
    error_handling: bool = True
    monitoring: bool = True
    benchmarking: bool = True
    custom_config: Dict[str, Any] = field(default_factory=dict)


class BaseballIntegrationLayer:
    """Main integration layer for baseball namespace"""
    
    def __init__(self):
        self.components: Dict[str, EncapsulatedComponent] = {}
        self.component_configs: Dict[str, ComponentConfig] = {}
        self.integration_active: bool = False
        self.startup_time: Optional[datetime] = None
        
    async def initialize(self, config_dir: Optional[str] = None):
        """Initialize the integration layer"""
        self.startup_time = datetime.now(timezone.utc)
        self.integration_active = True
        
        # Initialize plugin system
        from baseball.core.plugin_system import initialize_plugin_system
        await initialize_plugin_system()
        
        # Start system monitoring
        await system_monitor.start_monitoring()
        
        # Register default error handlers
        self._register_default_error_handlers()
        
        return True
    
    def _register_default_error_handlers(self):
        """Register default error handlers"""
        from baseball.core.intelligent_recovery import (
            DatabaseErrorHandler, NetworkErrorHandler, ModelErrorHandler
        )
        
        plugin_registry.register_handler(DatabaseErrorHandler())
        plugin_registry.register_handler(NetworkErrorHandler())
        plugin_registry.register_handler(ModelErrorHandler())
    
    async def register_component(self, component: EncapsulatedComponent, 
                            config: ComponentConfig):
        """Register a component with full integration"""
        if not config.enabled:
            return False
        
        # Store component and config
        self.components[config.name] = component
        self.component_configs[config.name] = config
        
        # Configure component
        component.load_config(config.custom_config)
        
        # Set up error handling
        if config.error_handling:
            component.error_context = ErrorContext(
                command_name=config.name,
                operation_name="component_operation"
            )
        
        # Set up monitoring
        if config.monitoring:
            # Register with system monitor
            pass  # Would integrate with actual monitoring
        
        return True
    
    async def execute_component_operation(self, component_name: str, 
                                    operation_name: str, 
                                    operation: Callable, *args, **kwargs):
        """Execute a component operation with full integration"""
        if component_name not in self.components:
            raise ValueError(f"Component {component_name} not registered")
        
        component = self.components[component_name]
        config = self.component_configs[component_name]
        
        # Start benchmarking if enabled
        if config.benchmarking:
            component.start_benchmark(f"{component_name}_{operation_name}")
        
        start_time = time.time()
        
        try:
            # Execute with error handling if enabled
            if config.error_handling:
                result = await component.execute_with_error_handling(
                    operation, *args, **kwargs
                )
            else:
                result = await operation(*args, **kwargs)
            
            # Record performance metrics
            if config.monitoring:
                duration_ms = (time.time() - start_time) * 1000
                await system_monitor.record_operation_performance(
                    f"{component_name}_{operation_name}",
                    duration_ms
                )
            
            # End benchmarking
            if config.benchmarking:
                component.end_benchmark(f"{component_name}_{operation_name}")
            
            return result
            
        except Exception as e:
            # Handle error with intelligent recovery
            if config.error_handling:
                recovery_success = await intelligent_recovery.handle_error_intelligently(
                    e,
                    component.error_context,
                    f"{component_name}_{operation_name}"
                )
                
                if not recovery_success:
                    # Log to system monitor
                    await system_monitor.record_operation_performance(
                        f"{component_name}_{operation_name}",
                        (time.time() - start_time) * 1000,
                        error_count=1
                    )
            
            # End benchmarking even on error
            if config.benchmarking:
                component.end_benchmark(f"{component_name}_{operation_name}")
            
            raise e
    
    async def shutdown(self):
        """Shutdown the integration layer"""
        self.integration_active = False
        
        # Stop system monitoring
        await system_monitor.stop_monitoring()
        
        # Shutdown all plugins
        await plugin_registry.shutdown_all()
        
        return True
    
    def get_component(self, name: str) -> Optional[EncapsulatedComponent]:
        """Get a registered component"""
        return self.components.get(name)
    
    def get_component_config(self, name: str) -> Optional[ComponentConfig]:
        """Get component configuration"""
        return self.component_configs.get(name)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        uptime_seconds = 0
        if self.startup_time:
            uptime_seconds = (datetime.now(timezone.utc) - self.startup_time).total_seconds()
        
        return {
            'integration_layer': {
                'active': self.integration_active,
                'startup_time': self.startup_time.isoformat() if self.startup_time else None,
                'uptime_seconds': uptime_seconds,
                'registered_components': len(self.components)
            },
            'system_monitoring': await system_monitor.generate_health_report(),
            'plugin_system': {
                'total_plugins': len(plugin_registry.plugins),
                'plugins_by_type': {
                    plugin_type.value: len(plugins)
                    for plugin_type, plugins in plugin_registry.plugins_by_type.items()
                }
            },
            'intelligent_recovery': intelligent_recovery.get_recovery_stats()
        }


def with_integration(component_name: str, operation_name: str = None):
    """Decorator for automatic integration"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get integration layer
            integration = get_integration_layer()
            
            # Use operation name from decorator or function name
            op_name = operation_name or func.__name__
            
            # Execute with integration
            return await integration.execute_component_operation(
                component_name, op_name, func, self, *args, **kwargs
            )
        return wrapper
    return decorator


class ComponentFactory:
    """Factory for creating baseball components with automatic integration"""
    
    @staticmethod
    async def create_component(component_class, config: ComponentConfig) -> EncapsulatedComponent:
        """Create a component with full integration"""
        # Create component instance
        component = component_class(name=config.name)
        
        # Get integration layer
        integration = get_integration_layer()
        
        # Register with integration layer
        await integration.register_component(component, config)
        
        return component
    
    @staticmethod
    async def create_data_source(source_class, source_name: str, 
                              custom_config: Dict[str, Any] = None) -> EncapsulatedComponent:
        """Create a data source with integration"""
        config = ComponentConfig(
            name=source_name,
            component_type="data_source",
            custom_config=custom_config or {}
        )
        
        return await ComponentFactory.create_component(source_class, config)
    
    @staticmethod
    async def create_model(model_class, model_name: str, 
                        custom_config: Dict[str, Any] = None) -> EncapsulatedComponent:
        """Create a model with integration"""
        config = ComponentConfig(
            name=model_name,
            component_type="model",
            custom_config=custom_config or {}
        )
        
        return await ComponentFactory.create_component(model_class, config)
    
    @staticmethod
    async def create_service(service_class, service_name: str, 
                         custom_config: Dict[str, Any] = None) -> EncapsulatedComponent:
        """Create a service with integration"""
        config = ComponentConfig(
            name=service_name,
            component_type="service",
            custom_config=custom_config or {}
        )
        
        return await ComponentFactory.create_component(service_class, config)


# Global integration layer instance
_integration_layer: Optional[BaseballIntegrationLayer] = None


def get_integration_layer() -> BaseballIntegrationLayer:
    """Get the global integration layer instance"""
    global _integration_layer
    if _integration_layer is None:
        _integration_layer = BaseballIntegrationLayer()
    return _integration_layer


async def initialize_baseball_integration(config_dir: Optional[str] = None):
    """Initialize the baseball integration system"""
    integration = get_integration_layer()
    return await integration.initialize(config_dir)


async def shutdown_baseball_integration():
    """Shutdown the baseball integration system"""
    integration = get_integration_layer()
    return await integration.shutdown()


# Convenience functions for common operations
async def run_with_monitoring(operation_name: str, operation: Callable, *args, **kwargs):
    """Run an operation with system monitoring"""
    integration = get_integration_layer()
    return await integration.execute_component_operation(
        "system_operation", operation_name, operation, *args, **kwargs
    )


async def run_with_error_handling(operation_name: str, operation: Callable, *args, **kwargs):
    """Run an operation with intelligent error handling"""
    integration = get_integration_layer()
    return await integration.execute_component_operation(
        "error_handled_operation", operation_name, operation, *args, **kwargs
    )


async def run_with_benchmarking(operation_name: str, operation: Callable, *args, **kwargs):
    """Run an operation with benchmarking"""
    integration = get_integration_layer()
    return await integration.execute_component_operation(
        "benchmarked_operation", operation_name, operation, *args, **kwargs
    )


# Mixin classes for easy integration
class IntegratedComponent(EncapsulatedComponent):
    """Base class for components that want automatic integration"""
    
    def __init__(self, name: str, component_type: str = "generic"):
        super().__init__(name)
        self.component_type = component_type
        self._integration_registered: bool = False
    
    async def register_with_integration(self, custom_config: Dict[str, Any] = None):
        """Register this component with the integration layer"""
        if self._integration_registered:
            return True
        
        config = ComponentConfig(
            name=self.name,
            component_type=self.component_type,
            custom_config=custom_config or {}
        )
        
        integration = get_integration_layer()
        success = await integration.register_component(self, config)
        
        if success:
            self._integration_registered = True
        
        return success


class IntegratedDataSource(IntegratedComponent):
    """Base class for data sources with automatic integration"""
    
    def __init__(self, name: str):
        super().__init__(name, "data_source")
    
    @with_integration("data_source")
    async def download(self, *args, **kwargs):
        """Download data with integration"""
        raise NotImplementedError("Subclasses must implement download method")
    
    @with_integration("data_source")
    async def ingest(self, *args, **kwargs):
        """Ingest data with integration"""
        raise NotImplementedError("Subclasses must implement ingest method")


class IntegratedModel(IntegratedComponent):
    """Base class for models with automatic integration"""
    
    def __init__(self, name: str):
        super().__init__(name, "model")
    
    @with_integration("model")
    async def train(self, *args, **kwargs):
        """Train model with integration"""
        raise NotImplementedError("Subclasses must implement train method")
    
    @with_integration("model")
    async def predict(self, *args, **kwargs):
        """Make predictions with integration"""
        raise NotImplementedError("Subclasses must implement predict method")
    
    @with_integration("model")
    async def evaluate(self, *args, **kwargs):
        """Evaluate model with integration"""
        raise NotImplementedError("Subclasses must implement evaluate method")


class IntegratedService(IntegratedComponent):
    """Base class for services with automatic integration"""
    
    def __init__(self, name: str):
        super().__init__(name, "service")
    
    @with_integration("service")
    async def start(self, *args, **kwargs):
        """Start service with integration"""
        raise NotImplementedError("Subclasses must implement start method")
    
    @with_integration("service")
    async def stop(self, *args, **kwargs):
        """Stop service with integration"""
        raise NotImplementedError("Subclasses must implement stop method")
    
    @with_integration("service")
    async def health_check(self, *args, **kwargs):
        """Health check with integration"""
        raise NotImplementedError("Subclasses must implement health_check method")
