"""Models module for baseball prediction models.

This module provides model training and inference for:
- Next-Run Probability Model (binary classification: will a run score?)
- Plate Appearance Outcome Model (multi-class: out/walk/single/double/triple/HR)

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from .base import (
    BaseModel,
    ModelConfig,
    ModelResult,
    ModelType,
    ModelVersion,
    TrainingConfig,
)
from .next_run_model import NextRunProbabilityModel
from .pa_outcome_model import PAOutcomeModel


__all__ = [
    # Base classes
    'BaseModel',
    'ModelConfig',
    'ModelResult',
    'ModelVersion',
    'TrainingConfig',
    'ModelType',
    # Model implementations
    'NextRunProbabilityModel',
    'PAOutcomeModel',
]
