"""Baseball data platform package.

This package provides a unified CLI for baseball data ingestion,
feature engineering, model training, and prediction.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

__version__ = '0.1.0'

# Core namespace exports
from baseball.predictions import (
    LivePredictionEngine,
    MarkovPitchPredictor,
    Prediction,
    LiveGameContext,
    PredictionType,
    get_prediction_engine,
    display_prediction,
)

__all__ = [
    '__version__',
    # Predictions
    'LivePredictionEngine',
    'MarkovPitchPredictor',
    'Prediction',
    'LiveGameContext',
    'PredictionType',
    'get_prediction_engine',
    'display_prediction',
]
