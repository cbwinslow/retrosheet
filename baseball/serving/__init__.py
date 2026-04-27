"""Model serving module for real-time predictions.

Provides:
- Model loading and caching
- REST API for predictions
- WebSocket for real-time updates
- Prediction caching for performance

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from .model_server import ModelCache, ModelServer
from .prediction_api import PredictionAPI, create_app
from .websocket_server import WebSocketServer


__all__ = [
    'ModelCache',
    'ModelServer',
    'PredictionAPI',
    'WebSocketServer',
    'create_app',
]
