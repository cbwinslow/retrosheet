"""
Training Pipeline Framework for baseball prediction models.

Provides unified training orchestration with experiment tracking,
configuration management, and CLI integration.

Usage:
    from baseball.training import TrainingOrchestrator, ExperimentConfig
    
    # Run a training experiment
    orchestrator = TrainingOrchestrator()
    result = orchestrator.run_experiment(
        model_type='pitch_level',
        seasons=[2020, 2021, 2022, 2023, 2024],
        experiment_name='pitch_xgboost_v2'
    )
"""

from .config import ExperimentConfig, ModelType, TrainingConfig
from .pipeline import TrainingOrchestrator
from .tracker import ExperimentTracker

__all__ = [
    'ExperimentConfig',
    'ExperimentTracker',
    'ModelType',
    'TrainingConfig',
    'TrainingOrchestrator',
]
