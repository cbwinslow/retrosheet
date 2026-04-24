"""
MLB Predict Configuration Module

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

from .schemas import (
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
    ModelConfig,
    ExperimentConfig,
    FeatureSubsetConfig,
    get_default_xgboost_config,
    get_default_lightgbm_config,
    get_quick_test_config,
    get_model_comparison_experiment,
    get_hyperparameter_search_experiment,
)

from .loader import (
    load_config,
    load_from_yaml,
    load_from_json,
    save_config,
    ConfigManager,
    load_model_config,
    load_experiment_config,
    save_model_config,
    save_experiment_config,
)

__all__ = [
    # Schemas
    "ModelFamily",
    "TargetVariable",
    "FeatureSet",
    "ValidationStrategy",
    "XGBoostConfig",
    "LightGBMConfig",
    "CatBoostConfig",
    "SplitConfig",
    "EarlyStoppingConfig",
    "CalibrationConfig",
    "FeatureImportanceConfig",
    "LoggingConfig",
    "ModelConfig",
    "ExperimentConfig",
    "FeatureSubsetConfig",
    # Defaults
    "get_default_xgboost_config",
    "get_default_lightgbm_config",
    "get_quick_test_config",
    "get_model_comparison_experiment",
    "get_hyperparameter_search_experiment",
    # Loader
    "load_config",
    "load_from_yaml",
    "load_from_json",
    "save_config",
    "ConfigManager",
    "load_model_config",
    "load_experiment_config",
    "save_model_config",
    "save_experiment_config",
]