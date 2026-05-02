"""Models module for baseball prediction models.

This module provides model training and inference for:
- Next-Run Probability Model (binary classification: will a run score?)
- Plate Appearance Outcome Model (multi-class: out/walk/single/double/triple/HR)
- Backtesting framework with walk-forward validation
- Monte Carlo simulation with Markov chains and ML-based PA prediction
- Model calibration tools (ECE, Brier score, temperature scaling)

Uses Pydantic schemas for type-safe configuration and state management.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-30
"""

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
from .win_probability_model import WinProbabilityModel

from .calibration import (
    CalibrationMetrics,
    calibrate_model,
    calculate_ece,
    calculate_brier_score,
    temperature_scaling,
    is_well_calibrated,
)
from .registry import ModelRegistry, ModelEntry
from .serving import (
    ModelServer,
    ModelCache,
    PredictionResult,
    BatchPredictionResult,
    ABTestConfig,
    load_model,
    predict,
)

__all__ = [
    # Pydantic schemas (type-safe configuration)
    'AggregatedSimulationResult',
    # Backtesting (dataclass-based)
    'BacktestConfig',
    'BacktestEngine',
    'BacktestEventType',
    'BacktestIterationResult',
    'BacktestResponse',
    'BacktestResult',
    'BacktestStatus',
    # Base classes
    'BaseModel',
    'BaseOutState',
    # Simulation engines
    'BaseSimulator',
    'CalibrationResult',
    'EventHook',
    'EventType',
    'GameState',
    'LineupConfig',
    'MarkovChainSimulator',
    'ModelConfig',
    'ModelResult',
    'ModelType',
    'ModelVersion',
    'MonteCarloSimulator',
    # Model implementations
    'NextRunProbabilityModel',
    'PAOutcomeModel',
    'ProgressTracker',
    'PydanticBacktestConfig',
    'PydanticBacktestResult',
    'PydanticCalibrationResult',
    'SimulationConfig',
    'SimulationEventType',
    'SimulationResponse',
    'SimulationResult',
    'SimulationRun',
    'SimulationService',
    'SimulationStateRecord',
    'SimulationStatus',
    'SimulationType',
    'TrainingConfig',
    'TransitionRecord',
    'WinProbabilityModel',
    'backtest_exists',
    'get_backtest_status',
    'is_backtest_running',
    'on_iteration_complete',
    'on_progress',
    'run_game_simulation',
    'run_quick_backtest',
    'run_quick_simulation',
    # Calibration
    'CalibrationMetrics',
    'calibrate_model',
    'calculate_ece',
    'calculate_brier_score',
    'temperature_scaling',
    'is_well_calibrated',
    # Registry
    'ModelRegistry',
    'ModelEntry',
    # Serving
    'ModelServer',
    'ModelCache',
    'PredictionResult',
    'BatchPredictionResult',
    'ABTestConfig',
    'load_model',
    'predict',
]
