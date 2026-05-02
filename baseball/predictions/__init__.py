"""Baseball prediction models and real-time inference.

This module provides:
- Markov chain models for pitch sequence prediction
- Live game prediction engine
- Model training and persistence
"""

from baseball.predictions.live_predictor import (
    LivePredictionEngine,
    MarkovPitchPredictor,
    Prediction,
    LiveGameContext,
    PredictionType,
    get_prediction_engine,
    display_prediction,
)

__all__ = [
    'LivePredictionEngine',
    'MarkovPitchPredictor',
    'Prediction',
    'LiveGameContext',
    'PredictionType',
    'get_prediction_engine',
    'display_prediction',
]
