"""Baseball data platform package.

This package provides a unified CLI for baseball data ingestion,
feature engineering, model training, and prediction.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from importlib import import_module
from typing import Any

__version__ = '0.1.0'

# Lazy-loaded exports to avoid hard runtime dependencies (numpy, etc.) when
# users run lightweight commands such as `python -m baseball --help`.
_LAZY_EXPORTS = {
    'LivePredictionEngine': ('baseball.predictions', 'LivePredictionEngine'),
    'MarkovPitchPredictor': ('baseball.predictions', 'MarkovPitchPredictor'),
    'Prediction': ('baseball.predictions', 'Prediction'),
    'LiveGameContext': ('baseball.predictions', 'LiveGameContext'),
    'PredictionType': ('baseball.predictions', 'PredictionType'),
    'get_prediction_engine': ('baseball.predictions', 'get_prediction_engine'),
    'display_prediction': ('baseball.predictions', 'display_prediction'),
}


def __getattr__(name: str) -> Any:
    """Lazily resolve top-level exports.

    This prevents import-time failures when optional scientific dependencies are
    unavailable but the caller does not need prediction internals.
    """
    if name in _LAZY_EXPORTS:
        module_name, attr_name = _LAZY_EXPORTS[name]
        module = import_module(module_name)
        return getattr(module, attr_name)
    raise AttributeError(f"module 'baseball' has no attribute {name!r}")

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
