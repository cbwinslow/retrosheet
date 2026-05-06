"""
Pitch-level models for baseball outcome prediction.

This module provides:
- Two-Tier XGBoost baseline models
- Model calibration and evaluation framework
- Feature engineering utilities
- Model serving and prediction interfaces

Target Tiers:
- Tier 1: {ball, strike, ball_in_play} - coarse outcome
- Tier 2: {single, double, triple, home_run, out} - fine-grained
"""

from .train_tier1_xgboost import PitchTier1XGBoostModel
from .calibration import PitchModelCalibrator

__all__ = [
    'PitchTier1XGBoostModel',
    'PitchModelCalibrator'
]
