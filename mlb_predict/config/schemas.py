"""Pydantic Configuration Schemas for MLB Prediction Framework

This module defines all configuration classes with type-safe validation.
All configurations can be serialized to/from YAML for reproducibility.

Author: Agent Cascade
Date: April 24, 2026
Depends On: pydantic>=2.0
Used By: mlb_predict.core.trainer, mlb_predict.core.experiment
"""

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ModelFamily(str, Enum):
    """Supported model families for prediction."""

    XGBOOST = 'xgboost'
    LIGHTGBM = 'lightgbm'
    CATBOOST = 'catboost'
    SKLEARN_GBM = 'sklearn_histgradient'
    LOGISTIC = 'logistic_regression'
    RANDOM_FOREST = 'random_forest'
    CUSTOM = 'custom'


class TargetVariable(str, Enum):
    """Available prediction targets for baseball outcomes."""

    SWING_DECISION = 'swing_decision'  # Binary: Swing (1) vs Take (0)
    CONTACT_MADE = 'contact_made'  # Binary: Contact (1) vs Whiff (0)
    HIT_OUTCOME = 'hit_outcome'  # Binary: Hit (1) vs Out (0)
    PA_OUTCOME = 'pa_outcome'  # Multiclass: Full PA distribution
    WIN_PROBABILITY = 'win_probability'  # Regression: Game state win prob
    RUN_EXPECTANCY = 'run_expectancy'  # Regression: Runs scored from state


class FeatureSet(str, Enum):
    """Pre-defined feature sets from the feature mart."""

    BASIC = 'basic'  # 20 core features (physics + count)
    PHYSICS = 'physics'  # 50 physics features (release, movement, speed)
    CONTEXT = 'context'  # 40 context features (count, inning, runners)
    ADVANCED = 'advanced'  # 150 features (physics + context + derived)
    COMPLETE = 'complete'  # 220+ features (all available)
    CUSTOM = 'custom'  # User-defined feature list


class ValidationStrategy(str, Enum):
    """Cross-validation strategies for temporal and non-temporal data."""

    TEMPORAL = 'temporal'  # Time-based split (default for baseball)
    RANDOM = 'random'  # Random split
    K_FOLD = 'k_fold'  # K-fold CV
    GROUP = 'group'  # Group-based (e.g., by game, pitcher)
    STRATIFIED = 'stratified'  # Stratified by target distribution


class XGBoostConfig(BaseModel):
    """XGBoost hyperparameters with validation.

    All parameters validated against reasonable ranges for baseball prediction.
    Defaults tuned for 220-feature pitch-level models.
    """

    max_depth: int = Field(
        default=6,
        ge=1,
        le=20,
        description='Maximum tree depth. Higher = more complex, risk of overfitting.',
    )
    n_estimators: int = Field(
        default=200,
        ge=10,
        le=2000,
        description='Number of boosting rounds.',
    )
    learning_rate: float = Field(
        default=0.05,
        ge=0.001,
        le=1.0,
        description='Step size shrinkage. Lower = slower but better generalization.',
    )
    subsample: float = Field(
        default=0.8,
        ge=0.1,
        le=1.0,
        description='Fraction of samples for each tree. Prevents overfitting.',
    )
    colsample_bytree: float = Field(
        default=0.8,
        ge=0.1,
        le=1.0,
        description='Fraction of features for each tree.',
    )
    colsample_bylevel: float = Field(
        default=1.0,
        ge=0.1,
        le=1.0,
        description='Fraction of features for each level.',
    )
    colsample_bynode: float = Field(
        default=1.0,
        ge=0.1,
        le=1.0,
        description='Fraction of features for each split.',
    )
    min_child_weight: int = Field(
        default=3,
        ge=1,
        le=20,
        description='Minimum sum of instance weight in child. Higher = more conservative.',
    )
    gamma: float = Field(
        default=0,
        ge=0,
        le=10,
        description='Minimum loss reduction for split. Higher = more conservative.',
    )
    reg_alpha: float = Field(
        default=0,
        ge=0,
        le=10,
        description='L1 regularization. Higher = more sparsity.',
    )
    reg_lambda: float = Field(
        default=1,
        ge=0,
        le=10,
        description='L2 regularization. Higher = more conservative.',
    )
    scale_pos_weight: float | None = Field(
        default=None,
        ge=0.1,
        le=100,
        description='Balance positive/negative weights. Auto-calculated if None.',
    )
    max_delta_step: float = Field(
        default=0,
        ge=0,
        le=10,
        description='Maximum delta step for leaf weights.',
    )
    tree_method: str = Field(
        default='hist',
        pattern='^(exact|approx|hist|gpu_hist)$',
        description="Tree construction algorithm. 'hist' is fast and accurate.",
    )
    grow_policy: str = Field(
        default='depthwise',
        pattern='^(depthwise|lossguide)$',
        description="Tree growing policy. 'lossguide' for large datasets.",
    )

    class Config:
        validate_assignment = True


class LightGBMConfig(BaseModel):
    """LightGBM hyperparameters with validation.

    Optimized for large-scale gradient boosting on baseball data.
    """

    num_leaves: int = Field(
        default=31,
        ge=2,
        le=256,
        description='Maximum leaves per tree. Controls complexity.',
    )
    n_estimators: int = Field(
        default=200,
        ge=10,
        le=2000,
        description='Number of boosting rounds.',
    )
    learning_rate: float = Field(
        default=0.05,
        ge=0.001,
        le=1.0,
        description='Step size shrinkage.',
    )
    feature_fraction: float = Field(
        default=0.8,
        ge=0.1,
        le=1.0,
        description='Fraction of features per tree (colsample_bytree).',
    )
    bagging_fraction: float = Field(
        default=0.8,
        ge=0.1,
        le=1.0,
        description='Fraction of data per iteration (subsample).',
    )
    bagging_freq: int = Field(
        default=5,
        ge=0,
        le=100,
        description='Frequency of bagging. 0 disables bagging.',
    )
    min_child_samples: int = Field(
        default=20,
        ge=1,
        le=100,
        description='Minimum data in leaf.',
    )
    min_child_weight: float = Field(
        default=0.001,
        ge=0.0001,
        le=1000,
        description='Minimum sum of hessian in leaf.',
    )
    reg_alpha: float = Field(
        default=0,
        ge=0,
        le=10,
        description='L1 regularization.',
    )
    reg_lambda: float = Field(
        default=0,
        ge=0,
        le=10,
        description='L2 regularization.',
    )
    max_depth: int = Field(
        default=-1,
        ge=-1,
        le=100,
        description='Max tree depth. -1 means unlimited (use num_leaves instead).',
    )

    class Config:
        validate_assignment = True


class CatBoostConfig(BaseModel):
    """CatBoost hyperparameters with validation."""

    iterations: int = Field(
        default=200,
        ge=10,
        le=2000,
        description='Number of boosting iterations.',
    )
    learning_rate: float = Field(
        default=0.05,
        ge=0.001,
        le=1.0,
        description='Step size shrinkage.',
    )
    depth: int = Field(
        default=6,
        ge=1,
        le=16,
        description='Tree depth.',
    )
    l2_leaf_reg: float = Field(
        default=3.0,
        ge=0,
        le=100,
        description='L2 regularization.',
    )
    random_strength: float = Field(
        default=1.0,
        ge=0,
        le=100,
        description='Randomness for scoring splits.',
    )
    bagging_temperature: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description='Bayesian bootstrap temperature.',
    )
    border_count: int = Field(
        default=254,
        ge=1,
        le=65535,
        description='Number of splits for numerical features.',
    )

    class Config:
        validate_assignment = True


class SplitConfig(BaseModel):
    """Data splitting configuration for train/validation/test."""

    strategy: ValidationStrategy = Field(
        default=ValidationStrategy.TEMPORAL,
        description='Splitting strategy. TEMPORAL recommended for time-series data.',
    )
    train_ratio: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description='Fraction for training set.',
    )
    val_ratio: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description='Fraction for validation set.',
    )
    test_ratio: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description='Fraction for test set.',
    )
    test_seasons: list[int] | None = Field(
        default=None,
        description='Specific seasons for test set (temporal strategy only).',
    )
    val_seasons: list[int] | None = Field(
        default=None,
        description='Specific seasons for validation set (temporal strategy only).',
    )
    random_seed: int = Field(
        default=42,
        ge=0,
        le=999999,
        description='Random seed for reproducibility.',
    )
    n_folds: int = Field(
        default=5,
        ge=2,
        le=10,
        description='Number of folds for K-fold CV.',
    )
    group_column: str | None = Field(
        default=None,
        description='Column name for group-based splitting.',
    )
    stratify_column: str | None = Field(
        default=None,
        description='Column name for stratification.',
    )

    @model_validator(mode='after')
    def validate_ratios(self):
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > 0.001:
            raise ValueError(f'Split ratios must sum to 1.0, got {total}')
        return self

    @model_validator(mode='after')
    def validate_temporal_settings(self):
        if self.strategy == ValidationStrategy.TEMPORAL:
            if self.test_seasons and self.test_ratio > 0:
                # If specific seasons given, test_ratio should be 0 or consistent
                pass
        return self

    class Config:
        validate_assignment = True


class EarlyStoppingConfig(BaseModel):
    """Early stopping configuration to prevent overfitting."""

    enabled: bool = Field(default=True)
    rounds: int = Field(
        default=50,
        ge=5,
        le=500,
        description='Stop if no improvement after N rounds.',
    )
    metric: str = Field(
        default='auc',
        pattern='^(auc|logloss|error|rmse|mae)$',
        description='Metric to monitor for early stopping.',
    )
    min_delta: float = Field(
        default=0.001,
        ge=0.0,
        le=1.0,
        description='Minimum change to qualify as improvement.',
    )

    class Config:
        validate_assignment = True


class CalibrationConfig(BaseModel):
    """Probability calibration configuration."""

    enabled: bool = Field(default=True)
    method: str = Field(
        default='isotonic',
        pattern='^(isotonic|sigmoid|beta)$',
        description='Calibration method. Isotonic recommended.',
    )
    n_bins: int = Field(
        default=10,
        ge=5,
        le=50,
        description='Number of bins for calibration curve.',
    )
    cv_folds: int = Field(
        default=3,
        ge=2,
        le=10,
        description='CV folds for calibration if using sigmoid.',
    )

    class Config:
        validate_assignment = True


class FeatureImportanceConfig(BaseModel):
    """Feature importance computation configuration."""

    enabled: bool = Field(default=True)
    methods: list[str] = Field(
        default=['gain', 'weight', 'cover'],
        description='Importance methods to compute.',
    )
    compute_shap: bool = Field(
        default=False,
        description='Compute SHAP values (computationally expensive).',
    )
    shap_sample_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description='Sample size for SHAP computation.',
    )
    top_n: int = Field(
        default=50,
        ge=10,
        le=500,
        description='Number of top features to return.',
    )

    class Config:
        validate_assignment = True


class LoggingConfig(BaseModel):
    """Logging and monitoring configuration."""

    log_level: str = Field(
        default='INFO',
        pattern='^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$',
    )
    log_to_db: bool = Field(default=True)
    log_to_file: bool = Field(default=True)
    log_file_path: str | None = Field(default=None)
    log_metrics_every_n: int = Field(
        default=10,
        ge=1,
        le=100,
        description='Log metrics every N iterations.',
    )
    progress_bar: bool = Field(default=True)

    class Config:
        validate_assignment = True


class ModelConfig(BaseModel):
    """Complete model configuration specification.

    This is the main configuration class used for training.
    It includes model family, target, features, hyperparameters,
    and all training settings.

    Example:
        config = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
            xgboost=XGBoostConfig(max_depth=8, n_estimators=300),
            calibration=CalibrationConfig(enabled=True)
        )

        # Save for reproducibility
        config.to_yaml("experiment.yaml")

        # Load and reproduce
        config = ModelConfig.from_yaml("experiment.yaml")
    """

    # Model specification
    family: ModelFamily = Field(
        ...,  # Required
        description='Model family/algorithm to use.',
    )
    target: TargetVariable = Field(
        ...,  # Required
        description='Prediction target.',
    )

    # Feature specification
    features: FeatureSet = Field(
        default=FeatureSet.ADVANCED,
        description='Predefined feature set.',
    )
    custom_features: list[str] | None = Field(
        default=None,
        description='List of specific feature names (for CUSTOM feature set).',
    )
    exclude_features: list[str] | None = Field(
        default=None,
        description='Features to exclude from the set.',
    )

    # Model-specific hyperparameters (only one should be set)
    xgboost: XGBoostConfig | None = None
    lightgbm: LightGBMConfig | None = None
    catboost: CatBoostConfig | None = None
    sklearn_params: dict[str, Any] | None = None
    custom_params: dict[str, Any] | None = None

    # Data specification
    seasons: list[int] = Field(
        default_factory=lambda: [2023, 2024, 2025],
        description='Seasons to include in training data.',
    )
    min_season: int | None = Field(default=None)
    max_season: int | None = Field(default=None)
    exclude_seasons: list[int] | None = Field(default=None)

    # Data splitting
    split: SplitConfig = Field(default_factory=SplitConfig)

    # Training configuration
    early_stopping: EarlyStoppingConfig = Field(default_factory=EarlyStoppingConfig)
    calibration: CalibrationConfig = Field(default_factory=CalibrationConfig)
    feature_importance: FeatureImportanceConfig = Field(default_factory=FeatureImportanceConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Training control
    batch_size: int | None = Field(
        default=None,
        description='Batch size. None = use all data.',
    )
    sample_weight: str | None = Field(
        default=None,
        description='Column name for sample weights.',
    )
    class_weight: str | None = Field(
        default=None,
        pattern='^(balanced|balanced_subsample|None)$',
        description='Class weight strategy.',
    )

    # Output configuration
    save_predictions: bool = Field(default=True)
    save_model: bool = Field(default=True)
    save_feature_importance: bool = Field(default=True)
    save_validation_curves: bool = Field(default=True)
    artifact_path: str | None = Field(
        default=None,
        description='Path to save artifacts. None = use default.',
    )

    # Metadata
    experiment_name: str | None = Field(default=None)
    run_name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    tags: list[str] | None = Field(default=None)
    git_commit: str | None = Field(default=None)

    # Validators
    @model_validator(mode='after')
    def set_model_specific_defaults(self):
        """Auto-create model-specific config if not provided."""
        if self.family == ModelFamily.XGBOOST and self.xgboost is None:
            self.xgboost = XGBoostConfig()
        elif self.family == ModelFamily.LIGHTGBM and self.lightgbm is None:
            self.lightgbm = LightGBMConfig()
        elif self.family == ModelFamily.CATBOOST and self.catboost is None:
            self.catboost = CatBoostConfig()
        return self

    @model_validator(mode='after')
    def validate_custom_features(self):
        """Ensure custom features provided when using CUSTOM feature set."""
        if self.features == FeatureSet.CUSTOM and not self.custom_features:
            raise ValueError('custom_features must be provided when features=CUSTOM')
        return self

    @model_validator(mode='after')
    def validate_seasons(self):
        """Validate season configuration."""
        if self.seasons and len(self.seasons) < 1:
            raise ValueError('At least one season required')
        if self.exclude_seasons:
            for season in self.exclude_seasons:
                if season in self.seasons:
                    self.seasons.remove(season)
        return self

    # Serialization methods
    def to_yaml(self, path: str | Path) -> None:
        """Save configuration to YAML file."""
        import yaml

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Use mode='json' to convert enums to strings, then safe_dump
        with open(path, 'w') as f:
            yaml.safe_dump(self.model_dump(mode='json'), f, default_flow_style=False)

    @classmethod
    def from_yaml(cls, path: str | Path) -> 'ModelConfig':
        """Load configuration from YAML file."""
        import yaml

        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_json(self, path: str | Path) -> None:
        """Save configuration to JSON file."""
        import json

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.model_dump(), f, indent=2)

    @classmethod
    def from_json(cls, path: str | Path) -> 'ModelConfig':
        """Load configuration from JSON file."""
        import json

        with open(path) as f:
            data = json.load(f)
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ModelConfig':
        """Create from dictionary."""
        return cls(**data)

    def get_model_id_string(self) -> str:
        """Generate a unique string identifier for this configuration."""
        import hashlib

        data = self.model_dump(
            exclude={'git_commit', 'experiment_name', 'run_name', 'description', 'tags'}
        )
        hash_str = hashlib.md5(str(data).encode()).hexdigest()[:8]
        return f'{self.family.value}_{self.target.value}_{hash_str}'

    class Config:
        validate_assignment = True
        use_enum_values = True
        extra = 'forbid'  # Prevent typos


class ExperimentConfig(BaseModel):
    """Configuration for multi-model experiments.

    Allows running multiple model configurations and comparing results.
    """

    experiment_name: str = Field(..., description='Name of the experiment.')
    description: str | None = Field(default=None)
    models: list[ModelConfig] = Field(
        default_factory=list,
        description='List of model configurations to train.',
    )
    parallel: bool = Field(
        default=False,
        description='Run models in parallel.',
    )
    max_workers: int = Field(
        default=2,
        ge=1,
        le=8,
        description='Maximum parallel workers.',
    )
    compare_metrics: list[str] = Field(
        default=['val_auc', 'test_auc', 'training_time'],
        description='Metrics to compare across models.',
    )
    save_comparison_report: bool = Field(default=True)

    def add_model(self, config: ModelConfig) -> None:
        """Add a model configuration to the experiment."""
        self.models.append(config)

    def to_yaml(self, path: str | Path) -> None:
        """Save experiment configuration to YAML."""
        import yaml

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Use mode='json' to convert enums to strings for YAML compatibility
        with open(path, 'w') as f:
            yaml.safe_dump(self.model_dump(mode='json'), f, default_flow_style=False)

    @classmethod
    def from_yaml(cls, path: str | Path) -> 'ExperimentConfig':
        """Load experiment configuration from YAML."""
        import yaml

        with open(path) as f:
            data = yaml.safe_load(f)
        # Reconstruct ModelConfig objects
        if 'models' in data:
            data['models'] = [ModelConfig(**m) for m in data['models']]
        return cls(**data)

    class Config:
        validate_assignment = True
        use_enum_values = True


class FeatureSubsetConfig(BaseModel):
    """Configuration for feature selection/subset experiments."""

    name: str = Field(..., description='Name of this feature subset.')
    feature_names: list[str] = Field(..., description='List of feature names.')
    description: str | None = Field(default=None)

    class Config:
        validate_assignment = True


# Default configurations for common use cases


def get_default_xgboost_config() -> ModelConfig:
    """Get default XGBoost configuration for pitch-level models."""
    return ModelConfig(
        family=ModelFamily.XGBOOST,
        target=TargetVariable.SWING_DECISION,
        features=FeatureSet.ADVANCED,
        xgboost=XGBoostConfig(),
        calibration=CalibrationConfig(enabled=True),
        feature_importance=FeatureImportanceConfig(compute_shap=False),
    )


def get_default_lightgbm_config() -> ModelConfig:
    """Get default LightGBM configuration for large datasets."""
    return ModelConfig(
        family=ModelFamily.LIGHTGBM,
        target=TargetVariable.SWING_DECISION,
        features=FeatureSet.ADVANCED,
        lightgbm=LightGBMConfig(),
        calibration=CalibrationConfig(enabled=True),
        feature_importance=FeatureImportanceConfig(compute_shap=False),
    )


def get_quick_test_config() -> ModelConfig:
    """Get quick test configuration for rapid iteration."""
    return ModelConfig(
        family=ModelFamily.XGBOOST,
        target=TargetVariable.SWING_DECISION,
        features=FeatureSet.BASIC,
        seasons=[2025],
        xgboost=XGBoostConfig(
            n_estimators=50,
            max_depth=4,
            learning_rate=0.1,
        ),
        early_stopping=EarlyStoppingConfig(rounds=10),
        calibration=CalibrationConfig(enabled=False),
        feature_importance=FeatureImportanceConfig(enabled=False),
    )


# Predefined experiment templates


def get_model_comparison_experiment(
    target: TargetVariable = TargetVariable.SWING_DECISION,
) -> ExperimentConfig:
    """Get experiment comparing XGBoost, LightGBM, and CatBoost."""
    exp = ExperimentConfig(
        experiment_name=f'model_comparison_{target.value}',
        description=f'Compare gradient boosting frameworks for {target.value}',
        compare_metrics=['val_auc', 'test_auc', 'val_logloss', 'training_time_seconds'],
    )

    # XGBoost
    xgb_config = get_default_xgboost_config()
    xgb_config.target = target
    xgb_config.xgboost.max_depth = 8
    exp.add_model(xgb_config)

    # LightGBM
    lgb_config = get_default_lightgbm_config()
    lgb_config.target = target
    lgb_config.lightgbm.num_leaves = 50
    exp.add_model(lgb_config)

    return exp


def get_hyperparameter_search_experiment() -> ExperimentConfig:
    """Get experiment for systematic hyperparameter search."""
    exp = ExperimentConfig(
        experiment_name='xgboost_depth_search',
        description='Search for optimal max_depth in XGBoost',
        compare_metrics=['val_auc', 'test_auc', 'n_estimators_trained'],
    )

    for depth in [4, 6, 8, 10, 12]:
        config = get_default_xgboost_config()
        config.xgboost.max_depth = depth
        config.run_name = f'max_depth_{depth}'
        exp.add_model(config)

    return exp


# Version information
__version__ = '0.1.0'
__all__ = [
    'CalibrationConfig',
    'CatBoostConfig',
    'EarlyStoppingConfig',
    'ExperimentConfig',
    'FeatureImportanceConfig',
    'FeatureSet',
    'FeatureSubsetConfig',
    'LightGBMConfig',
    'LoggingConfig',
    'ModelConfig',
    'ModelFamily',
    'SplitConfig',
    'TargetVariable',
    'ValidationStrategy',
    'XGBoostConfig',
    'get_default_lightgbm_config',
    'get_default_xgboost_config',
    'get_hyperparameter_search_experiment',
    'get_model_comparison_experiment',
    'get_quick_test_config',
]
