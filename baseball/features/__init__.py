"""Features module for ML-ready feature computation.

This module provides feature computation for baseball prediction models:
- Win Expectancy (WE) calculation from game state
- Leverage Index (LI) for situational importance
- Run Expectancy (RE) matrix
- Matchup features (batter vs pitcher)
- Rolling form features (recent performance)
- Bullpen features (fatigue, depth)

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from .base import FeatureStore, FeatureResult, FeatureConfig, GameState
from .win_expectancy import WinExpectancyCalculator
from .leverage_index import LeverageIndexCalculator
from .matchup import MatchupCalculator, MatchupHistory, PlatoonSplit
from .rolling_form import RollingFormCalculator, BatterForm, PitcherForm, TrendDirection
from .bullpen import BullpenCalculator, TeamBullpenStatus, RelieverFatigue, AvailabilityStatus

__all__ = [
    'FeatureStore',
    'FeatureResult',
    'FeatureConfig',
    'GameState',
    'WinExpectancyCalculator',
    'LeverageIndexCalculator',
    'MatchupCalculator',
    'MatchupHistory',
    'PlatoonSplit',
    'RollingFormCalculator',
    'BatterForm',
    'PitcherForm',
    'TrendDirection',
    'BullpenCalculator',
    'TeamBullpenStatus',
    'RelieverFatigue',
    'AvailabilityStatus',
]
