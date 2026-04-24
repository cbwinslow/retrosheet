"""
Plugin registry system for the framework.

Provides registration and discovery of:
- Models (sklearn, PyTorch, XGBoost, etc.)
- Features (SQL and Python-based)
- Data loaders
- Transformers
- Metrics

The registry uses a simple dictionary-based approach with database persistence
for tracking available plugins.
"""

from typing import Type, Dict, List, Optional, Any
import importlib
import inspect

from framework.core.base import BaseModel, BaseFeature, BaseDataLoader, BaseTransformer, BaseMetric
from framework.utils.database import execute_sql


class Registry:
    """Base registry for component registration."""
    
    def __init__(self, component_type: str):
        self.component_type = component_type
        self._registry: Dict[str, Type] = {}
        
    def register(self, name: str, cls: Type, metadata: Optional[Dict] = None):
        """Register a component class."""
        self._registry[name] = cls
        
        # Persist to database
        metadata = metadata or {}
        metadata['module'] = cls.__module__
        metadata['file'] = inspect.getfile(cls)
        
        execute_sql("""
            INSERT INTO framework.plugins (plugin_name, plugin_type, plugin_class, description)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (plugin_name) DO UPDATE SET
                plugin_class = EXCLUDED.plugin_class,
                updated_at = NOW()
        """, (name, self.component_type, f"{cls.__module__}.{cls.__name__}", metadata.get('description', '')))
        
    def get(self, name: str) -> Type:
        """Get a registered component class."""
        if name not in self._registry:
            # Try to load from database
            result = execute_sql("""
                SELECT plugin_class FROM framework.plugins
                WHERE plugin_name = %s AND plugin_type = %s AND is_active = true
            """, (name, self.component_type), fetch=True)
            
            if result:
                # Dynamic import
                module_path, class_name = result[0][0].rsplit('.', 1)
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)
                self._registry[name] = cls
            else:
                raise KeyError(f"Unknown {self.component_type}: {name}")
        
        return self._registry[name]
    
    def list(self) -> List[str]:
        """List all registered component names."""
        # Get from database for up-to-date list
        result = execute_sql("""
            SELECT plugin_name FROM framework.plugins
            WHERE plugin_type = %s AND is_active = true
            ORDER BY plugin_name
        """, (self.component_type,), fetch=True)
        return [r[0] for r in result]
    
    def create(self, name: str, config: Optional[Dict] = None):
        """Instantiate a registered component."""
        cls = self.get(name)
        return cls(config or {})


class ModelRegistry(Registry):
    """Registry for prediction models."""
    
    def __init__(self):
        super().__init__('model')
        
    def register_model(self, name: str, cls: Type[BaseModel], description: str = ""):
        """Register a model class."""
        if not issubclass(cls, BaseModel):
            raise ValueError(f"Model must extend BaseModel: {cls}")
        self.register(name, cls, {'description': description})
    
    def get_model(self, name: str) -> Type[BaseModel]:
        """Get a model class by name."""
        return self.get(name)
    
    def create_model(self, name: str, config: Optional[Dict] = None) -> BaseModel:
        """Create a model instance."""
        return self.create(name, config)


class FeatureRegistry(Registry):
    """Registry for feature transformers."""
    
    def __init__(self):
        super().__init__('feature')
        
    def register_feature(self, name: str, cls: Type[BaseFeature], description: str = ""):
        """Register a feature class."""
        if not issubclass(cls, BaseFeature):
            raise ValueError(f"Feature must extend BaseFeature: {cls}")
        self.register(name, cls, {'description': description})
    
    def get_feature(self, name: str) -> Type[BaseFeature]:
        return self.get(name)
    
    def create_feature(self, name: str, config: Optional[Dict] = None) -> BaseFeature:
        return self.create(name, config)
    
    def register_sql_feature(self, name: str, sql_expression: str, 
                            dependencies: List[str], description: str = ""):
        """Register a SQL-computed feature directly."""
        execute_sql("""
            INSERT INTO framework.feature_registry 
                (feature_name, feature_type, computation_method, dependencies, description)
            VALUES (%s, 'sql', %s, %s, %s)
            ON CONFLICT (feature_name) DO UPDATE SET
                computation_method = EXCLUDED.computation_method,
                dependencies = EXCLUDED.dependencies,
                updated_at = NOW()
        """, (name, sql_expression, dependencies, description))


class PluginRegistry:
    """Master registry for all plugin types."""
    
    def __init__(self):
        self.models = ModelRegistry()
        self.features = FeatureRegistry()
        self.data_loaders = Registry('data_loader')
        self.transformers = Registry('transformer')
        self.metrics = Registry('metric')
    
    def discover_plugins(self, package_name: str = 'framework.plugins'):
        """Auto-discover plugins in a package."""
        try:
            package = importlib.import_module(package_name)
            for name in dir(package):
                obj = getattr(package, name)
                if inspect.isclass(obj):
                    if issubclass(obj, BaseModel) and obj != BaseModel:
                        self.models.register(name, obj)
                    elif issubclass(obj, BaseFeature) and obj != BaseFeature:
                        self.features.register(name, obj)
                    elif issubclass(obj, BaseDataLoader) and obj != BaseDataLoader:
                        self.data_loaders.register(name, obj)
                    elif issubclass(obj, BaseTransformer) and obj != BaseTransformer:
                        self.transformers.register(name, obj)
                    elif issubclass(obj, BaseMetric) and obj != BaseMetric:
                        self.metrics.register(name, obj)
        except ImportError:
            pass  # Package doesn't exist
    
    def list_all(self) -> Dict[str, List[str]]:
        """List all registered plugins by type."""
        return {
            'models': self.models.list(),
            'features': self.features.list(),
            'data_loaders': self.data_loaders.list(),
            'transformers': self.transformers.list(),
            'metrics': self.metrics.list(),
        }


# Global registry instance
_registry = PluginRegistry()

def get_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    return _registry
