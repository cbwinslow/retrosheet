"""
XGBoost Models Module

Hierarchical classification models for pitch prediction using XGBoost
with comprehensive feature engineering and model explainability.
"""

from .hierarchical_model import HierarchicalXGBoostModel, HierarchicalConfig, TrainingResult
from .feature_engine import FeatureEngine, FeatureConfig
from .explainer import ModelExplainer

__all__ = [
    'HierarchicalXGBoostModel',
    'HierarchicalConfig',
    'TrainingResult',
    'FeatureEngine',
    'FeatureConfig',
    'ModelExplainer'
]
