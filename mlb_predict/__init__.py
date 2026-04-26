"""MLB Prediction Framework

Phase 1 & 2 Implementation - Pydantic Configs, Rich Results, ModelTrainer, Plugins

Example:
    from mlb_predict import ModelConfig, ModelTrainer, FeatureLoader
    
    # Create config
    config = ModelConfig(family='xgboost', target='swing_decision')
    
    # Load features
    data = FeatureLoader(config).load_split(train_through=2022)
    
    # Train model
    trainer = ModelTrainer(config)
    result = trainer.train()
    
    # Analyze results
    print(result.summary())
    top_features = result.get_best_features(20)
"""

# Phase 1.1: Configuration - COMPLETE
from mlb_predict.config import (
    CalibrationConfig,
    CatBoostConfig,
    ConfigManager,
    EarlyStoppingConfig,
    ExperimentConfig,
    FeatureImportanceConfig,
    FeatureSet,
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
    get_quick_test_config,
    load_config,
    save_config,
)

# Phase 2.4: Experiment Runner - COMPLETE
from mlb_predict.core.experiment import (
    ExperimentRun,
    ExperimentRunner,
    ExperimentSummary,
    HyperparameterSweep,
    compare_feature_sets,
    compare_model_families,
)

# Phase 2.3: FeatureLoader - COMPLETE
from mlb_predict.core.feature_loader import (
    DataSplit,
    FeatureLoader,
    FeatureSchema,
    load_features_for_config,
)

# Phase 2.2: Plugin Registry - COMPLETE
from mlb_predict.core.plugin import (
    BasePluginModel,
    PluginRegistry,
    SklearnPluginModel,
    get_global_registry,
    get_plugin,
    list_plugins,
    register_plugin,
)

# Phase 1.2: Rich Results - COMPLETE
from mlb_predict.core.results import (
    FeatureImportance,
    Metrics,
    MetricValue,
    PredictResult,
    Residuals,
    TrainResult,
    ValidationCurve,
)

# Phase 2.1: ModelTrainer - COMPLETE
from mlb_predict.core.trainer import ModelTrainer

# Production Integration - Legacy Bridge
from mlb_predict.integration import (
    LEGACY_TARGET_MAPPING,
    LEGACY_TO_FRAMEWORK_FEATURES,
    LegacyCompatibleTrainer,
    convert_legacy_cli_args_to_config,
    create_config_from_legacy_args,
    print_framework_result_legacy_style,
)

# Phase 3: Database Orchestration - Complete pipeline abstraction
from mlb_predict.orchestration import (
    BridgePopulationConfig,
    BridgePopulationResult,
    DatabaseOrchestrator,
    FeaturePopulationConfig,
    FeaturePopulationResult,
    IngestOperationConfig,
    IngestResult,
    ModelTrainingConfig,
    ModelTrainingResult,
    OperationConfig,
    OperationResult,
    ValidationConfig,
    ValidationResult,
)


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
    # Data Loading (Phase 2.3)
    'FeatureLoader',
    'FeatureSchema',
    'DataSplit',
    'load_features_for_config',
    # Experiment Runner (Phase 2.4)
    'ExperimentRun',
    'ExperimentSummary',
    'ExperimentRunner',
    'HyperparameterSweep',
    'compare_feature_sets',
    'compare_model_families',
    # Production Integration
    'create_config_from_legacy_args',
    'LegacyCompatibleTrainer',
    'convert_legacy_cli_args_to_config',
    'print_framework_result_legacy_style',
    'LEGACY_TO_FRAMEWORK_FEATURES',
    'LEGACY_TARGET_MAPPING',
    # Database Orchestration (Phase 3)
    'DatabaseOrchestrator',
    'OperationConfig',
    'FeaturePopulationConfig',
    'BridgePopulationConfig',
    'IngestOperationConfig',
    'ValidationConfig',
    'ModelTrainingConfig',
    'OperationResult',
    'FeaturePopulationResult',
    'BridgePopulationResult',
    'IngestResult',
    'ValidationResult',
    'ModelTrainingResult',
]
