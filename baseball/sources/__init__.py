"""Baseball data source adapters.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26

This package contains source adapters that WRAP existing scripts,
preserving working logic while adding the new baseball CLI interface.

Available sources:
- MlbSource: MLB Stats API
- EspnSource: ESPN API (secondary/fallback)
- StatcastSource: Baseball Savant Statcast
- LahmanSource: Lahman Baseball Databank
- RetrosheetSource: Retrosheet historical events
"""

from baseball.sources.base import BaseSource
from baseball.sources.espn import EspnSource
from baseball.sources.lahman import LahmanSource
from baseball.sources.mlb import MlbSource
from baseball.sources.retrosheet import RetrosheetSource
from baseball.sources.statcast import StatcastSource


__all__ = [
    'BaseSource',
    'EspnSource',
    'LahmanSource',
    'MlbSource',
    'RetrosheetSource',
    'StatcastSource',
]
