"""
LSTM Models Module

Sequential deep learning models for pitch prediction using LSTM architecture
with attention mechanisms for sequence processing.
"""

from .sequential_model import SequentialLSTMModel
from .pitch_encoder import PitchEncoder
from .attention import AttentionMechanism

__all__ = [
    'SequentialLSTMModel',
    'PitchEncoder', 
    'AttentionMechanism'
]
