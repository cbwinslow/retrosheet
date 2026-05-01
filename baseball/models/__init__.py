"""Models module for baseball prediction models.

This module provides model training and inference for:
- Next-Run Probability Model (binary classification: will a run score?)
- Plate Appearance Outcome Model (multi-class: out/walk/single/double/triple/HR)
- Backtesting framework with walk-forward validation
- Monte Carlo simulation with Markov chains and ML-based PA prediction

Uses Pydantic schemas for type-safe configuration and state management.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-30
"""

from .base import (
    BaseModel,
    ModelConfig,
    ModelResult,
    ModelType,
    ModelVersion,
    TrainingConfig,
)
from .next_run_model import NextRunProbabilityModel
from .pa_outcome_model import PAOutcomeModel
from .win_probability_model import WinProbabilityModel
from .backtesting import (
    BacktestConfig,
    BacktestEngine,
    BacktestEventType,
    BacktestIterationResult,
    BacktestResult,
    BacktestStatus,
    CalibrationResult,
    EventHook,
    ProgressTracker,
    backtest_exists,
    get_backtest_status,
    is_backtest_running,
    on_iteration_complete,
    on_progress,
    run_quick_backtest,
)
from .schemas import (
    AggregatedSimulationResult,
    BacktestConfig as PydanticBacktestConfig,
    BacktestResponse,
    BacktestResult as PydanticBacktestResult,
    BaseOutState,
    CalibrationResult as PydanticCalibrationResult,
    EventType,
    GameState,
    LineupConfig,
    SimulationConfig,
    SimulationResponse,
    SimulationResult,
    SimulationRun,
    SimulationStateRecord,
    SimulationStatus,
    SimulationType,
    TransitionRecord,
)
from .simulation import (
    BaseSimulator,
    MarkovChainSimulator,
    MonteCarloSimulator,
    SimulationEventType,
    SimulationService,
    run_game_simulation,
    run_quick_simulation,
)


__all__ = [
    # Base classes
    'BaseModel',
    'ModelConfig',
    'ModelResult',
    'ModelVersion',
    'TrainingConfig',
    'ModelType',
    # Model implementations
    'NextRunProbabilityModel',
    'PAOutcomeModel',
    'WinProbabilityModel',
    # Backtesting (dataclass-based)
    'BacktestConfig',
    'BacktestEngine',
    'BacktestEventType',
    'BacktestIterationResult',
    'BacktestResult',
    'BacktestStatus',
    'CalibrationResult',
    'EventHook',
    'ProgressTracker',
    'backtest_exists',
    'get_backtest_status',
    'is_backtest_running',
    'on_iteration_complete',
    'on_progress',
    'run_quick_backtest',
    # Pydantic schemas (type-safe configuration)
    'AggregatedSimulationResult',
    'BaseOutState',
    'EventType',
    'GameState',
    'LineupConfig',
    'PydanticBacktestConfig',
    'PydanticBacktestResult',
    'PydanticCalibrationResult',
    'SimulationConfig',
    'SimulationResponse',
    'SimulationResult',
    'SimulationRun',
    'SimulationStateRecord',
    'SimulationStatus',
    'SimulationType',
    'TransitionRecord',
    'BacktestResponse',
    # Simulation engines
    'BaseSimulator',
    'MarkovChainSimulator',
    'MonteCarloSimulator',
    'SimulationEventType',
    'SimulationService',
    'run_game_simulation',
    'run_quick_simulation',
]
