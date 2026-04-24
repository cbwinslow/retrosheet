"""
MLB Predict: Unified Framework for Baseball Prediction Research

This framework wraps and extends your existing working infrastructure:
- Uses existing feature marts (features_pitch.*, features.plate_appearance_*)
- Integrates with existing model_registry table
- Wraps existing training scripts (train_models.py, train_pa_outcome_distribution.py)
- Provides plugin system for custom models that output to existing registry

Example:
    from mlb_predict import ModelTrainer, Experiment
    
    # Use existing training infrastructure
    trainer = ModelTrainer.from_config('configs/my_experiment.yaml')
    result = trainer.train()  # Calls your existing train_models.py patterns
    
    # Or plug in custom model
    trainer.register_model('my_xgboost', MyXGBoostModel)
    result = trainer.train(model_name='my_xgboost')
"""

__version__ = "0.1.0"

from mlb_predict.core.trainer import ModelTrainer
from mlb_predict.core.experiment import Experiment
from mlb_predict.core.base_model import PluginModel
from mlb_predict.registry.model_store import ModelStore
from mlb_predict.data.feature_loader import FeatureLoader
from mlb_predict.utils.config import load_config

__all__ = [
    'ModelTrainer',
    'Experiment', 
    'PluginModel',
    'ModelStore',
    'FeatureLoader',
    'load_config',
]
