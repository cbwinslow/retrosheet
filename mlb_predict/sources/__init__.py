"""Data source adapters for MLB data ingestion.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from mlb_predict.sources.base import (
    BaseSource,
    DownloadResult,
    IngestResult,
    ValidationResult,
)
from mlb_predict.sources.espn import EspnSource
from mlb_predict.sources.lahman import LahmanSource
from mlb_predict.sources.live import GameState, LiveMlbSource
from mlb_predict.sources.mlb import MlbSource
from mlb_predict.sources.retrosheet import RetrosheetSource
from mlb_predict.sources.statcast import StatcastSource


__all__ = [
    'BaseSource',
    'DownloadResult',
    'EspnSource',
    'GameState',
    'IngestResult',
    'LahmanSource',
    'LiveMlbSource',
    'MlbSource',
    'RetrosheetSource',
    'StatcastSource',
    'ValidationResult',
]
