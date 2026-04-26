"""MLB Predict Configuration Module

Type-safe configuration management with Pydantic validation.

Example:
    from mlb_predict.config import ModelConfig, ModelFamily
    
    config = ModelConfig(
        family=ModelFamily.XGBOOST,
        target="swing_decision"
    )
    
    # Save for reproducibility
    config.to_yaml("my_config.yaml")
    
    # Load and reproduce
    config = ModelConfig.from_yaml("my_config.yaml")
"""

from .loader import (
    ConfigManager,
    load_config,
    load_experiment_config,
    load_from_json,
    load_from_yaml,
    load_model_config,
    save_config,
    save_experiment_config,
    save_model_config,
)
from .schemas import (
    CalibrationConfig,
    CatBoostConfig,
    EarlyStoppingConfig,
    ExperimentConfig,
    FeatureImportanceConfig,
    FeatureSet,
    FeatureSubsetConfig,
    LightGBMConfig,
    LoggingConfig,
    ModelConfig,
    ModelFamily,
    SplitConfig,
    TargetVariable,
    ValidationStrategy,
    XGBoostConfig,
    get_default_lightgbm_config,
    get_default_xgboost_config,
    get_hyperparameter_search_experiment,
    get_model_comparison_experiment,
    get_quick_test_config,
)


__all__ = [
    # Schemas
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
    'ModelConfig',
    'ExperimentConfig',
    'FeatureSubsetConfig',
    # Defaults
    'get_default_xgboost_config',
    'get_default_lightgbm_config',
    'get_quick_test_config',
    'get_model_comparison_experiment',
    'get_hyperparameter_search_experiment',
    # Loader
    'load_config',
    'load_from_yaml',
    'load_from_json',
    'save_config',
    'ConfigManager',
    'load_model_config',
    'load_experiment_config',
    'save_model_config',
    'save_experiment_config',
]
