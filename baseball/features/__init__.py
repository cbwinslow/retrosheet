"""Features module for ML-ready feature computation.

This module provides feature computation for baseball prediction models:
- Win Expectancy (WE) calculation from game state
- Leverage Index (LI) for situational importance
- Run Expectancy (RE) matrix
- Matchup features (batter vs pitcher)
- Rolling form features (recent performance)
- Bullpen features (fatigue, depth)
- Pitch sequence features (next-pitch prediction)
- Live inference features (real-time prediction)

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from .base import FeatureConfig, FeatureResult, FeatureStore, GameState
from .bullpen import AvailabilityStatus, BullpenCalculator, RelieverFatigue, TeamBullpenStatus
from .bullpen_fatigue import BullpenFatigueCalculator, RelieverWorkload, get_fatigue_calculator
from .leverage_index import LeverageIndexCalculator
from .matchup import MatchupCalculator, MatchupHistory, PlatoonSplit
from .pitch_sequence import (
    ParsedPitch,
    PitchSequenceConfig,
    PitchSequenceFeatureStore,
    ValidationError,
    get_pitch_training_rows,
    parse_pitch_sequence,
    validate_pitch_sequences,
)
from .rolling_form import BatterForm, PitcherForm, RollingFormCalculator, TrendDirection
from .run_expectancy import RunExpectancyCalculator
from .win_expectancy import WinExpectancyCalculator
from .live_inference import LiveFeatureMapper, get_live_features
from .player_context import (
    BatterContext,
    PitcherContext,
    MatchupHistory,
    PlayerContextStore,
    get_batter_context,
    get_pitcher_context,
    get_matchup_history,
)
from .star_players import (
    StarBatter,
    StarPitcher,
    StarMatchup,
    ActiveStarPlayer,
    StarPlayerStore,
    get_star_batter,
    get_star_pitcher,
    get_active_stars,
)


__all__ = [
    'AvailabilityStatus',
    'BatterForm',
    'BullpenCalculator',
    'BullpenFatigueCalculator',
    'FeatureConfig',
    'FeatureResult',
    'FeatureStore',
    'GameState',
    'LeverageIndexCalculator',
    'MatchupCalculator',
    'MatchupHistory',
    'ParsedPitch',
    'PitchSequenceConfig',
    'PitchSequenceFeatureStore',
    'PitcherForm',
    'PlatoonSplit',
    'RelieverFatigue',
    'RelieverWorkload',
    'RollingFormCalculator',
    'RunExpectancyCalculator',
    'TeamBullpenStatus',
    'TrendDirection',
    'ValidationError',
    'WinExpectancyCalculator',
    'get_fatigue_calculator',
    'get_live_features',
    'get_pitch_training_rows',
    'parse_pitch_sequence',
    'validate_pitch_sequences',
    'LiveFeatureMapper',
    'BatterContext',
    'PitcherContext',
    'MatchupHistory',
    'PlayerContextStore',
    'get_batter_context',
    'get_pitcher_context',
    'get_matchup_history',
    # Star Players
    'StarBatter',
    'StarPitcher',
    'StarMatchup',
    'ActiveStarPlayer',
    'StarPlayerStore',
    'get_star_batter',
    'get_star_pitcher',
    'get_active_stars',
]
