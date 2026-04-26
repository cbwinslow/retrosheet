"""Core abstractions for the framework.

Provides base classes that define the interface contracts for all components.
Researchers extend these to add their own implementations.
"""

from .base import (
    BaseDataLoader,
    BaseExperiment,
    BaseFeature,
    BaseMetric,
    BaseModel,
    BaseTransformer,
)
from .experiment import Experiment
from .registry import (
    FeatureRegistry,
    ModelRegistry,
    PluginRegistry,
)


__all__ = [
    'BaseDataLoader',
    'BaseExperiment',
    'BaseFeature',
    'BaseMetric',
    'BaseModel',
    'BaseTransformer',
    'Experiment',
    'FeatureRegistry',
    'ModelRegistry',
    'PluginRegistry',
]
