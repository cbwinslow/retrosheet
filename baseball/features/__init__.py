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

from .base import FeatureConfig, FeatureResult, FeatureStore, GameState
from .bullpen import AvailabilityStatus, BullpenCalculator, RelieverFatigue, TeamBullpenStatus
from .leverage_index import LeverageIndexCalculator
from .matchup import MatchupCalculator, MatchupHistory, PlatoonSplit
from .rolling_form import BatterForm, PitcherForm, RollingFormCalculator, TrendDirection
from .run_expectancy import RunExpectancyCalculator
from .win_expectancy import WinExpectancyCalculator


__all__ = [
    'AvailabilityStatus',
    'BatterForm',
    'BullpenCalculator',
    'FeatureConfig',
    'FeatureResult',
    'FeatureStore',
    'GameState',
    'LeverageIndexCalculator',
    'MatchupCalculator',
    'MatchupHistory',
    'PitcherForm',
    'PlatoonSplit',
    'RelieverFatigue',
    'RollingFormCalculator',
    'RunExpectancyCalculator',
    'TeamBullpenStatus',
    'TrendDirection',
    'WinExpectancyCalculator',
]
