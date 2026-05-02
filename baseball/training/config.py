"""
Training Configuration Management

Defines configuration classes for training experiments.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ModelType(Enum):
    """Supported model types for training."""
    PITCH_LEVEL = "pitch_level"
    PA_OUTCOME = "pa_outcome"
    WIN_PROBABILITY = "win_probability"
    SWING_PROBABILITY = "swing_probability"
    CONTACT_PROBABILITY = "contact_probability"


@dataclass
class TrainingConfig:
    """Configuration for a training run."""
    
    # Data settings
    seasons: List[int]
    test_size: float = 0.2
    cv_folds: int = 5
    random_state: int = 42
    
    # Model settings
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    feature_set: Optional[List[str]] = None
    
    # Training settings
    early_stopping: bool = True
    early_stopping_rounds: int = 50
    max_iterations: int = 1000
    
    # Output settings
    artifacts_dir: str = "models/artifacts"
    save_checkpoints: bool = True
    checkpoint_every: int = 100
    
    def __post_init__(self):
        """Validate configuration."""
        if not self.seasons:
            raise ValueError("At least one season must be specified")
        if self.test_size < 0 or self.test_size > 1:
            raise ValueError("test_size must be between 0 and 1")
        if self.cv_folds < 2:
            raise ValueError("cv_folds must be at least 2")


@dataclass
class ExperimentConfig:
    """Configuration for a full experiment."""
    
    # Experiment metadata
    experiment_name: str
    model_type: ModelType
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Training configs to run
    training_configs: List[TrainingConfig] = field(default_factory=list)
    
    # Experiment settings
    parallel_runs: int = 1
    compare_baseline: bool = True
    
    # Tracking
    log_metrics: bool = True
    save_artifacts: bool = True
    
    def __post_init__(self):
        """Generate experiment ID."""
        self.experiment_id = f"{self.experiment_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.created_at = datetime.now().isoformat()
    
    experiment_id: str = field(init=False)
    created_at: str = field(init=False)


@dataclass
class ExperimentResult:
    """Result of an experiment run."""
    
    experiment_id: str
    experiment_name: str
    model_type: ModelType
    
    # Results
    training_results: List[Any]
    best_model_id: Optional[int] = None
    best_metric: Optional[float] = None
    
    # Comparison
    vs_baseline_improvement: Optional[float] = None
    
    # Metadata
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0
    status: str = "pending"  # pending, running, completed, failed
    
    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now().isoformat()


def create_default_config(
    model_type: ModelType,
    seasons: List[int],
    **overrides
) -> TrainingConfig:
    """
    Create a default configuration for a model type.
    
    Args:
        model_type: Type of model to train
        seasons: List of seasons to use
        **overrides: Override default values
    
    Returns:
        TrainingConfig with sensible defaults
    """
    defaults = {
        ModelType.PITCH_LEVEL: {
            'hyperparameters': {
                'n_estimators': 500,
                'max_depth': 8,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
            },
            'early_stopping_rounds': 50,
        },
        ModelType.PA_OUTCOME: {
            'hyperparameters': {
                'n_estimators': 300,
                'max_depth': 6,
                'learning_rate': 0.1,
            },
            'early_stopping_rounds': 30,
        },
        ModelType.WIN_PROBABILITY: {
            'hyperparameters': {
                'n_estimators': 200,
                'max_depth': 5,
                'learning_rate': 0.05,
            },
            'early_stopping_rounds': 20,
        },
        ModelType.SWING_PROBABILITY: {
            'hyperparameters': {
                'n_estimators': 400,
                'max_depth': 6,
                'learning_rate': 0.08,
            },
            'early_stopping_rounds': 40,
        },
        ModelType.CONTACT_PROBABILITY: {
            'hyperparameters': {
                'n_estimators': 400,
                'max_depth': 6,
                'learning_rate': 0.08,
            },
            'early_stopping_rounds': 40,
        },
    }
    
    model_defaults = defaults.get(model_type, {})
    
    # Apply overrides
    for key, value in overrides.items():
        model_defaults[key] = value
    
    return TrainingConfig(
        seasons=seasons,
        **model_defaults
    )
