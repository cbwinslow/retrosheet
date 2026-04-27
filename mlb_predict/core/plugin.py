"""Plugin System for Custom Models

Phase 2.2: Plugin Registry

Provides a standard interface for registering and using custom models.
Any model that implements the BasePluginModel interface can be registered
and used with the ModelTrainer.

Author: Agent Cascade
Date: April 24, 2026
"""

from abc import ABC, abstractmethod
from typing import Any

import joblib
import numpy as np

from mlb_predict.config import ModelConfig
from mlb_predict.core.results import FeatureImportance


class BasePluginModel(ABC):
    """Abstract base class for custom model plugins.

    Any custom model must inherit from this class and implement:
    - fit(X, y, X_val=None, y_val=None)
    - predict(X)
    - predict_proba(X)
    - save(path)
    - load(path) (classmethod)

    Example:
        class MyCustomModel(BasePluginModel):
            def __init__(self, config: ModelConfig):
                super().__init__(config)
                self.model = None

            def fit(self, X, y, X_val=None, y_val=None):
                from sklearn.ensemble import RandomForestClassifier
                self.model = RandomForestClassifier(n_estimators=100)
                self.model.fit(X, y)
                return self

            def predict(self, X):
                return self.model.predict(X)

            def predict_proba(self, X):
                return self.model.predict_proba(X)[:, 1]

            def save(self, path: str):
                joblib.dump(self.model, path)

            @classmethod
            def load(cls, path: str):
                instance = cls(ModelConfig(family='custom', target='swing_decision'))
                instance.model = joblib.load(path)
                return instance
    """

    def __init__(self, config: ModelConfig):
        """Initialize plugin with config.

        Args:
            config: ModelConfig with hyperparameters and settings
        """
        self.config = config
        self._is_fitted = False
        self._feature_names: list[str] | None = None
        self._feature_importance: dict[str, float] | None = None

    @abstractmethod
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
    ) -> 'BasePluginModel':
        """Fit the model on training data.

        Args:
            X: Training features (n_samples, n_features)
            y: Training targets (n_samples,)
            X_val: Optional validation features
            y_val: Optional validation targets

        Returns:
            self (fitted model)
        """

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make binary predictions.

        Args:
            X: Features (n_samples, n_features)

        Returns:
            Binary predictions (n_samples,)
        """

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Make probability predictions.

        Args:
            X: Features (n_samples, n_features)

        Returns:
            Probability predictions (n_samples,) - probability of positive class
        """

    @abstractmethod
    def save(self, path: str) -> None:
        """Save model to disk.

        Args:
            path: File path to save model
        """

    @classmethod
    @abstractmethod
    def load(cls, path: str) -> 'BasePluginModel':
        """Load model from disk.

        Args:
            path: File path to load model

        Returns:
            Loaded model instance
        """

    def get_feature_importance(self) -> list[FeatureImportance] | None:
        """Get feature importance if available.

        Returns:
            List of FeatureImportance objects or None
        """
        if self._feature_importance is None or self._feature_names is None:
            return None

        # Sort by importance
        sorted_items = sorted(
            self._feature_importance.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return [
            FeatureImportance(
                feature_name=name,
                importance_score=score,
                importance_rank=i + 1,
                method='model_specific',
            )
            for i, (name, score) in enumerate(sorted_items)
        ]

    def get_params(self) -> dict[str, Any]:
        """Get model parameters.

        Returns:
            Dict of parameter names to values
        """
        # Default implementation - subclasses can override
        return {
            'family': self.config.family,
            'target': self.config.target,
            'features': self.config.features,
        }

    def set_feature_names(self, feature_names: list[str]) -> None:
        """Set feature names for importance tracking."""
        self._feature_names = feature_names

    @property
    def is_fitted(self) -> bool:
        """Check if model has been fitted."""
        return self._is_fitted


class SklearnPluginModel(BasePluginModel):
    """Generic wrapper for scikit-learn models.

    Allows using any sklearn classifier as a plugin.

    Example:
        from sklearn.ensemble import RandomForestClassifier

        config = ModelConfig(family='custom', target='swing_decision')
        model = SklearnPluginModel(config, RandomForestClassifier(n_estimators=100))
    """

    def __init__(self, config: ModelConfig, sklearn_model: Any):
        """Initialize with sklearn model.

        Args:
            config: ModelConfig
            sklearn_model: Any sklearn classifier with fit/predict/predict_proba
        """
        super().__init__(config)
        self.model = sklearn_model

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
    ) -> 'SklearnPluginModel':
        """Fit the sklearn model."""
        self.model.fit(X, y)
        self._is_fitted = True

        # Try to get feature importance
        if hasattr(self.model, 'feature_importances_') and self._feature_names:
            self._feature_importance = dict(
                zip(self._feature_names, self.model.feature_importances_),
            )

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make binary predictions."""
        if not self._is_fitted:
            raise RuntimeError('Model must be fitted before predicting')
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Make probability predictions."""
        if not self._is_fitted:
            raise RuntimeError('Model must be fitted before predicting')

        proba = self.model.predict_proba(X)
        # Return probability of positive class (class 1)
        if proba.ndim == 2 and proba.shape[1] == 2:
            return proba[:, 1]
        return proba[:, 0] if proba.ndim == 2 else proba

    def save(self, path: str) -> None:
        """Save using joblib."""
        joblib.dump(
            {
                'model': self.model,
                'config': self.config,
                'is_fitted': self._is_fitted,
                'feature_names': self._feature_names,
                'feature_importance': self._feature_importance,
            },
            path,
        )

    @classmethod
    def load(cls, path: str) -> 'SklearnPluginModel':
        """Load from joblib."""
        data = joblib.load(path)
        instance = cls(data['config'], data['model'])
        instance._is_fitted = data['is_fitted']
        instance._feature_names = data['feature_names']
        instance._feature_importance = data['feature_importance']
        return instance


class PluginRegistry:
    """Registry for managing custom model plugins.

    Provides a centralized place to register, discover, and instantiate
    custom models that can be used with ModelTrainer.

    Example:
        # Register a custom model
        registry = PluginRegistry()
        registry.register('my_xgboost', MyXGBoostPlugin)

        # Use with ModelTrainer
        trainer = ModelTrainer(config)
        trainer.register_plugin('my_xgboost', registry.get('my_xgboost'))
        result = trainer.train()

        # Or use directly
        model_class = registry.get('my_xgboost')
        model = model_class(config)
        model.fit(X_train, y_train)
    """

    def __init__(self):
        """Initialize empty registry."""
        self._plugins: dict[str, type[BasePluginModel]] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        model_class: type[BasePluginModel],
        description: str | None = None,
        author: str | None = None,
        version: str | None = None,
    ) -> None:
        """Register a model plugin.

        Args:
            name: Unique plugin identifier
            model_class: Class inheriting from BasePluginModel
            description: Optional description
            author: Optional author name
            version: Optional version string

        Raises:
            ValueError: If name already registered or class doesn't inherit from BasePluginModel
        """
        if name in self._plugins:
            raise ValueError(f"Plugin '{name}' already registered")

        if not issubclass(model_class, BasePluginModel):
            raise ValueError(
                f'Model class must inherit from BasePluginModel, got {model_class.__name__}',
            )

        self._plugins[name] = model_class
        self._metadata[name] = {
            'description': description or model_class.__doc__ or 'No description',
            'author': author,
            'version': version,
            'class_name': model_class.__name__,
            'module': model_class.__module__,
        }

    def get(self, name: str) -> type[BasePluginModel]:
        """Get a registered plugin class.

        Args:
            name: Plugin identifier

        Returns:
            Plugin class

        Raises:
            KeyError: If plugin not found
        """
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' not found. Available: {list(self._plugins.keys())}")
        return self._plugins[name]

    def create(self, name: str, config: ModelConfig) -> BasePluginModel:
        """Create an instance of a registered plugin.

        Args:
            name: Plugin identifier
            config: ModelConfig for initialization

        Returns:
            Instantiated plugin model
        """
        model_class = self.get(name)
        return model_class(config)

    def unregister(self, name: str) -> None:
        """Unregister a plugin.

        Args:
            name: Plugin identifier
        """
        if name in self._plugins:
            del self._plugins[name]
            del self._metadata[name]

    def list_plugins(self) -> list[str]:
        """List all registered plugin names.

        Returns:
            List of plugin names
        """
        return list(self._plugins.keys())

    def get_metadata(self, name: str) -> dict[str, Any]:
        """Get metadata for a plugin.

        Args:
            name: Plugin identifier

        Returns:
            Dict with description, author, version, etc.
        """
        if name not in self._metadata:
            raise KeyError(f"Plugin '{name}' not found")
        return self._metadata[name].copy()

    def get_all_metadata(self) -> dict[str, dict[str, Any]]:
        """Get metadata for all plugins.

        Returns:
            Dict mapping plugin names to metadata
        """
        return {name: meta.copy() for name, meta in self._metadata.items()}

    def is_registered(self, name: str) -> bool:
        """Check if a plugin is registered.

        Args:
            name: Plugin identifier

        Returns:
            True if registered
        """
        return name in self._plugins

    def clear(self) -> None:
        """Clear all registered plugins."""
        self._plugins.clear()
        self._metadata.clear()

    def discover_from_module(self, module_name: str) -> list[str]:
        """Auto-discover plugins from a module.

        Scans module for classes inheriting from BasePluginModel
        and registers them.

        Args:
            module_name: Module to scan (e.g., 'my_models.plugins')

        Returns:
            List of discovered plugin names
        """
        import importlib
        import inspect

        discovered = []

        try:
            module = importlib.import_module(module_name)
        except ImportError:
            return discovered

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BasePluginModel)
                and obj is not BasePluginModel
                and not name.startswith('_')
            ):
                plugin_name = getattr(obj, 'PLUGIN_NAME', name.lower())

                try:
                    self.register(
                        plugin_name,
                        obj,
                        description=obj.__doc__,
                        version=getattr(obj, 'VERSION', None),
                    )
                    discovered.append(plugin_name)
                except ValueError:
                    # Already registered, skip
                    pass

        return discovered


# Global registry instance
_global_registry: PluginRegistry | None = None


def get_global_registry() -> PluginRegistry:
    """Get or create the global plugin registry.

    Returns:
        Global PluginRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry


def register_plugin(name: str, model_class: type[BasePluginModel], **kwargs) -> None:
    """Register a plugin in the global registry.

    Convenience function for quick registration.

    Example:
        register_plugin('my_model', MyModelClass, description='My custom model')
    """
    registry = get_global_registry()
    registry.register(name, model_class, **kwargs)


def get_plugin(name: str) -> type[BasePluginModel]:
    """Get plugin from global registry.

    Example:
        model_class = get_plugin('my_model')
        model = model_class(config)
    """
    registry = get_global_registry()
    return registry.get(name)


def list_plugins() -> list[str]:
    """List all plugins in global registry."""
    registry = get_global_registry()
    return registry.list_plugins()


__all__ = [
    'BasePluginModel',
    'PluginRegistry',
    'SklearnPluginModel',
    'get_global_registry',
    'get_plugin',
    'list_plugins',
    'register_plugin',
]
