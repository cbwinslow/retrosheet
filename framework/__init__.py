"""
Framework: Modular Baseball Prediction Warehouse

A researcher-friendly framework for building, extending, and experimenting with
baseball prediction models. Provides base classes, configuration, logging,
and a plugin system.

Example:
    from framework import BaseModel, Experiment, config
    
    class MyModel(BaseModel):
        def train(self, X, y):
            # Your training logic
            pass
        
        def predict(self, X):
            # Your prediction logic
            return predictions
    
    exp = Experiment(config.load('my_experiment.yaml'))
    exp.run(MyModel())

Layers:
    - core: Base classes and abstractions
    - models: Model implementations and registry
    - features: Feature engineering and registry
    - cli: Command-line interface
    - plugins: Plugin system
    - utils: Logging, batching, database helpers
    - config: Configuration management
"""

__version__ = "0.1.0"
__author__ = "Retrosheet Warehouse Team"

from framework.core.base import (
    BaseModel,
    BaseFeature,
    BaseDataLoader,
    BaseTransformer,
    BaseMetric,
    BaseExperiment,
)

from framework.core.registry import (
    ModelRegistry,
    FeatureRegistry,
    PluginRegistry,
)

from framework.core.experiment import Experiment

from framework.config.manager import ConfigManager

from framework.utils.logger import get_logger, log_to_db
from framework.utils.batch import BatchProcessor
from framework.utils.database import get_connection, execute_sql

__all__ = [
    # Base classes
    "BaseModel",
    "BaseFeature", 
    "BaseDataLoader",
    "BaseTransformer",
    "BaseMetric",
    "BaseExperiment",
    # Registry
    "ModelRegistry",
    "FeatureRegistry",
    "PluginRegistry",
    # Experiment
    "Experiment",
    # Config
    "ConfigManager",
    # Utils
    "get_logger",
    "log_to_db",
    "BatchProcessor",
    "get_connection",
    "execute_sql",
]
