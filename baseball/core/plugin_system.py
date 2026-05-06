"""
Modular plugin system for baseball namespace error handling.

Provides flexible, interchangeable components for:
- Error handlers
- Data sources
- Model components
- Monitoring systems
- Configuration providers
"""

import asyncio
import importlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import json
import yaml

from baseball.core.error_architecture import ErrorHandler, ErrorEvent, RecoveryAction


class PluginType(Enum):
    """Plugin types for modular system"""
    ERROR_HANDLER = "error_handler"
    DATA_SOURCE = "data_source"
    MODEL_COMPONENT = "model_component"
    MONITORING = "monitoring"
    CONFIG_PROVIDER = "config_provider"


@dataclass
class PluginMetadata:
    """Plugin metadata for registration and discovery"""
    name: str
    plugin_type: PluginType
    version: str
    description: str
    author: str
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 50


class Plugin(ABC):
    """Abstract base class for all plugins"""
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Plugin metadata"""
        pass
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize plugin with configuration"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """Shutdown plugin gracefully"""
        pass


class PluginRegistry:
    """Central plugin registry for managing plugins"""
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.plugins_by_type: Dict[PluginType, List[Plugin]] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
    
    def register_plugin(self, plugin: Plugin, config: Optional[Dict[str, Any]] = None):
        """Register a plugin"""
        metadata = plugin.metadata
        
        if metadata.name in self.plugins:
            raise ValueError(f"Plugin {metadata.name} already registered")
        
        self.plugins[metadata.name] = plugin
        self.plugin_configs[metadata.name] = config or {}
        
        if metadata.plugin_type not in self.plugins_by_type:
            self.plugins_by_type[metadata.plugin_type] = []
        
        self.plugins_by_type[metadata.plugin_type].append(plugin)
        
        # Sort by priority
        self.plugins_by_type[metadata.plugin_type].sort(
            key=lambda p: p.metadata.priority,
            reverse=True
        )
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get plugin by name"""
        return self.plugins.get(name)
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[Plugin]:
        """Get all plugins of a specific type"""
        return self.plugins_by_type.get(plugin_type, [])
    
    async def initialize_all(self):
        """Initialize all enabled plugins"""
        for plugin in self.plugins.values():
            if plugin.metadata.enabled:
                config = self.plugin_configs[plugin.metadata.name]
                await plugin.initialize(config)
    
    async def shutdown_all(self):
        """Shutdown all plugins"""
        for plugin in self.plugins.values():
            await plugin.shutdown()


class PluginLoader:
    """Plugin loader for dynamic plugin discovery"""
    
    def __init__(self, registry: PluginRegistry):
        self.registry = registry
    
    async def load_from_directory(self, plugin_dir: Path):
        """Load plugins from directory"""
        if not plugin_dir.exists():
            return
        
        for plugin_file in plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            await self._load_plugin_from_file(plugin_file)
    
    async def load_from_config(self, config_file: Path):
        """Load plugins from configuration file"""
        if not config_file.exists():
            return
        
        with open(config_file, 'r') as f:
            if config_file.suffix == '.json':
                config = json.load(f)
            elif config_file.suffix in ['.yml', '.yaml']:
                config = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported config format: {config_file.suffix}")
        
        for plugin_config in config.get('plugins', []):
            await self._load_plugin_from_config(plugin_config)
    
    async def _load_plugin_from_file(self, plugin_file: Path):
        """Load plugin from Python file"""
        module_name = plugin_file.stem
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Look for plugin classes
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, Plugin) and 
                attr != Plugin):
                
                plugin_instance = attr()
                self.registry.register_plugin(plugin_instance)
    
    async def _load_plugin_from_config(self, plugin_config: Dict[str, Any]):
        """Load plugin from configuration"""
        plugin_type = plugin_config.get('type')
        plugin_class = plugin_config.get('class')
        plugin_name = plugin_config.get('name')
        
        if not all([plugin_type, plugin_class, plugin_name]):
            raise ValueError("Plugin config must include type, class, and name")
        
        # Dynamic import
        module_path, class_name = plugin_class.rsplit('.', 1)
        module = importlib.import_module(module_path)
        plugin_class = getattr(module, class_name)
        
        plugin_instance = plugin_class()
        self.registry.register_plugin(
            plugin_instance,
            plugin_config.get('config', {})
        )


class ModularErrorHandler(ErrorHandler, Plugin):
    """Modular error handler plugin"""
    
    def __init__(self, name: str = "modular_error_handler"):
        self.name = name
        self._metadata = PluginMetadata(
            name=name,
            plugin_type=PluginType.ERROR_HANDLER,
            version="1.0.0",
            description="Modular error handler with configurable rules",
            author="Baseball Team",
            priority=75
        )
        self.error_rules: Dict[str, RecoveryAction] = {}
    
    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize with error rules"""
        self.error_rules = config.get('error_rules', {})
        return True
    
    async def shutdown(self) -> bool:
        """Shutdown gracefully"""
        return True
    
    async def can_handle(self, event: ErrorEvent) -> bool:
        """Check if can handle based on rules"""
        error_key = f"{type(event.error).__name__}"
        return error_key in self.error_rules
    
    async def handle(self, event: ErrorEvent) -> RecoveryAction:
        """Handle error based on configured rules"""
        error_key = f"{type(event.error).__name__}"
        return self.error_rules.get(error_key, RecoveryAction.ESCALATE)
    
    def get_priority(self) -> int:
        return self.metadata.priority


class ModularDataSource(Plugin):
    """Modular data source plugin"""
    
    def __init__(self, name: str, source_type: str):
        self.name = name
        self.source_type = source_type
        self._metadata = PluginMetadata(
            name=name,
            plugin_type=PluginType.DATA_SOURCE,
            version="1.0.0",
            description=f"Modular {source_type} data source",
            author="Baseball Team",
            priority=50
        )
    
    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize data source"""
        self.config = config
        return True
    
    async def shutdown(self) -> bool:
        """Shutdown data source"""
        return True
    
    @abstractmethod
    async def download(self, **kwargs) -> Any:
        """Download data"""
        pass
    
    @abstractmethod
    async def ingest(self, **kwargs) -> Any:
        """Ingest data"""
        pass


class ModularModelComponent(Plugin):
    """Modular model component plugin"""
    
    def __init__(self, name: str, model_type: str):
        self.name = name
        self.model_type = model_type
        self._metadata = PluginMetadata(
            name=name,
            plugin_type=PluginType.MODEL_COMPONENT,
            version="1.0.0",
            description=f"Modular {model_type} model component",
            author="Baseball Team",
            priority=60
        )
    
    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize model component"""
        self.config = config
        return True
    
    async def shutdown(self) -> bool:
        """Shutdown model component"""
        return True
    
    @abstractmethod
    async def train(self, **kwargs) -> Any:
        """Train model"""
        pass
    
    @abstractmethod
    async def predict(self, **kwargs) -> Any:
        """Make predictions"""
        pass


class ModularMonitoring(Plugin):
    """Modular monitoring plugin"""
    
    def __init__(self, name: str):
        self.name = name
        self._metadata = PluginMetadata(
            name=name,
            plugin_type=PluginType.MONITORING,
            version="1.0.0",
            description="Modular monitoring system",
            author="Baseball Team",
            priority=40
        )
    
    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize monitoring"""
        self.config = config
        return True
    
    async def shutdown(self) -> bool:
        """Shutdown monitoring"""
        return True
    
    @abstractmethod
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect metrics"""
        pass
    
    @abstractmethod
    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert"""
        pass


class ModularConfigProvider(Plugin):
    """Modular configuration provider plugin"""
    
    def __init__(self, name: str):
        self.name = name
        self._metadata = PluginMetadata(
            name=name,
            plugin_type=PluginType.CONFIG_PROVIDER,
            version="1.0.0",
            description="Modular configuration provider",
            author="Baseball Team",
            priority=30
        )
    
    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize config provider"""
        self.config = config
        return True
    
    async def shutdown(self) -> bool:
        """Shutdown config provider"""
        return True
    
    @abstractmethod
    async def get_config(self, key: str) -> Any:
        """Get configuration value"""
        pass
    
    @abstractmethod
    async def set_config(self, key: str, value: Any) -> bool:
        """Set configuration value"""
        pass


# Global plugin registry
plugin_registry = PluginRegistry()
plugin_loader = PluginLoader(plugin_registry)


async def initialize_plugin_system(config_dir: Path = None):
    """Initialize the plugin system"""
    if config_dir is None:
        config_dir = Path(__file__).parent.parent / "config" / "plugins"
    
    await plugin_loader.load_from_directory(config_dir / "handlers")
    await plugin_loader.load_from_directory(config_dir / "sources")
    await plugin_loader.load_from_directory(config_dir / "models")
    await plugin_loader.load_from_directory(config_dir / "monitoring")
    await plugin_loader.load_from_config(config_dir / "plugins.yaml")
    
    await plugin_registry.initialize_all()


def register_plugin(plugin: Plugin, config: Optional[Dict[str, Any]] = None):
    """Register a plugin"""
    plugin_registry.register_plugin(plugin, config)


def get_plugin(name: str) -> Optional[Plugin]:
    """Get plugin by name"""
    return plugin_registry.get_plugin(name)


def get_plugins_by_type(plugin_type: PluginType) -> List[Plugin]:
    """Get all plugins of a specific type"""
    return plugin_registry.get_plugins_by_type(plugin_type)
