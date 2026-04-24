"""
Core abstractions for the framework.

Provides base classes that define the interface contracts for all components.
Researchers extend these to add their own implementations.
"""

from .base import (
    BaseModel,
    BaseFeature,
    BaseDataLoader,
    BaseTransformer,
    BaseMetric,
    BaseExperiment,
)

from .registry import (
    ModelRegistry,
    FeatureRegistry,
    PluginRegistry,
)

from .experiment import Experiment

__all__ = [
    "BaseModel",
    "BaseFeature",
    "BaseDataLoader", 
    "BaseTransformer",
    "BaseMetric",
    "BaseExperiment",
    "ModelRegistry",
    "FeatureRegistry",
    "PluginRegistry",
    "Experiment",
]
