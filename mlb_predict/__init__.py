"""
MLB Predict: Unified Framework for Baseball Prediction Research

Phase 1.1: Pydantic Configuration Schemas ✅ COMPLETE

This framework wraps and extends your existing working infrastructure:
- Uses existing feature marts (features_pitch.*, features.plate_appearance_*)
- Integrates with existing model_registry table
- Wraps existing training scripts (train_models.py, train_pa_outcome_distribution.py)
- Provides plugin system for custom models that output to existing registry

Example:
    from mlb_predict.config import ModelConfig, ModelFamily, TargetVariable
    
    config = ModelConfig(
        family=ModelFamily.XGBOOST,
        target=TargetVariable.SWING_DECISION
    )
    config.to_yaml("my_experiment.yaml")
"""

__version__ = "0.1.0"

# Phase 1.1: Configuration - COMPLETE
from mlb_predict.config import (
    ModelConfig,
    ExperimentConfig,
    ModelFamily,
    TargetVariable,
    FeatureSet,
    ValidationStrategy,
    XGBoostConfig,
    LightGBMConfig,
    CatBoostConfig,
    SplitConfig,
    EarlyStoppingConfig,
    CalibrationConfig,
    FeatureImportanceConfig,
    LoggingConfig,
    load_config,
    save_config,
    ConfigManager,
    get_default_xgboost_config,
    get_default_lightgbm_config,
    get_quick_test_config,
)

# Phase 1.2: Rich Result Classes - COMPLETE
from mlb_predict.core.results import (
    TrainResult,
    PredictResult,
    Residuals,
    Metrics,
    MetricValue,
    ValidationCurve,
    FeatureImportance,
)

# Phase 2.1: ModelTrainer - COMPLETE
from mlb_predict.core.trainer import ModelTrainer

# Phase 2.2: Plugin Registry - COMPLETE
from mlb_predict.core.plugin import (
    BasePluginModel,
    SklearnPluginModel,
    PluginRegistry,
    get_global_registry,
    register_plugin,
    get_plugin,
    list_plugins,
)

# TODO: Phase 2.3 - FeatureLoader
# from mlb_predict.data.feature_loader import FeatureLoader

# TODO: Phase 2.4 - Experiment Runner
# from mlb_predict.core.experiment import Experiment

__all__ = [
    # Configuration (Phase 1.1)
    'ModelConfig',
    'ExperimentConfig',
    'ModelFamily',
    'TargetVariable',
    'FeatureSet',
    'ValidationStrategy',
    'XGBoostConfig',
    'LightGBMConfig',
    'CatBoostConfig',
    'SplitConfig',
    'EarlyStoppingConfig',
    'CalibrationConfig',
    'FeatureImportanceConfig',
    'LoggingConfig',
    'load_config',
    'save_config',
    'ConfigManager',
    'get_default_xgboost_config',
    'get_default_lightgbm_config',
    'get_quick_test_config',
    # Rich Results (Phase 1.2)
    'TrainResult',
    'PredictResult',
    'Residuals',
    'Metrics',
    'MetricValue',
    'ValidationCurve',
    'FeatureImportance',
    # Core Trainer (Phase 2.1)
    'ModelTrainer',
    # Plugin System (Phase 2.2)
    'BasePluginModel',
    'SklearnPluginModel',
    'PluginRegistry',
    'get_global_registry',
    'register_plugin',
    'get_plugin',
    'list_plugins',
]
