"""Pydantic schemas for baseball ML models and simulation.

Provides type-safe configuration and state management for:
- Simulation runs and state tracking
- Backtesting configuration and results
- Model registry entries with validation

Uses Pydantic v2 for validation, serialization, and settings management.

Author: Agent Cascade
Date: 2026-04-30
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# Enums
# ============================================================================

class SimulationType(StrEnum):
    """Type of baseball game simulation."""
    MARKOV = 'markov'
    MONTE_CARLO = 'monte_carlo'
    HYBRID = 'hybrid'


class SimulationStatus(StrEnum):
    """Status of a simulation run."""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class EventType(StrEnum):
    """Types of events in baseball simulation."""
    OUT = 'out'
    WALK = 'walk'
    SINGLE = 'single'
    DOUBLE = 'double'
    TRIPLE = 'triple'
    HOME_RUN = 'home_run'
    ERROR = 'error'
    FIELDERS_CHOICE = 'fielders_choice'
    DOUBLE_PLAY = 'double_play'
    TRIPLE_PLAY = 'triple_play'
    STOLEN_BASE = 'stolen_base'
    CAUGHT_STEALING = 'caught_stealing'
    PASSED_BALL = 'passed_ball'
    WILD_PITCH = 'wild_pitch'


class WindDirection(StrEnum):
    """Wind direction relative to ballpark orientation."""
    IN = 'in'           # Blowing in from outfield
    OUT = 'out'         # Blowing out to outfield
    LEFT = 'left'       # Blowing to left field
    RIGHT = 'right'     # Blowing to right field
    CROSS_LEFT = 'cross_left'    # Crosswind toward left
    CROSS_RIGHT = 'cross_right'  # Crosswind toward right
    CALM = 'calm'       # < 5 mph


class BacktestStatus(StrEnum):
    """Status of a backtest run."""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


# ============================================================================
# Base Schemas
# ============================================================================

class BaseState(BaseModel):
    """Base class for all state schemas with common configuration."""
    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        extra='forbid',
        json_schema_extra={
            'examples': [],
        },
    )


# ============================================================================
# Simulation Schemas
# ============================================================================

class BaseOutState(BaseState):
    """24 base-out states (8 base configurations × 3 out states).

    Encoding: state = outs * 8 + base_encoding
    - outs: 0, 1, 2 (3 outs = inning over, not a state)
    - base_encoding: 0-7 bitmask (1=1B, 2=2B, 4=3B)

    Examples:
        - 0: 0 outs, empty (___)
        - 3: 0 outs, runners on 1B and 2B (12_)
        - 7: 0 outs, bases loaded (123)
        - 10: 1 out, runner on 2B (_2_)
        - 23: 2 outs, bases loaded (123)
    """
    outs: int = Field(..., ge=0, le=2, description='Number of outs (0-2)')
    base_encoding: int = Field(..., ge=0, le=7, description='Base occupancy bitmask')

    @property
    def state_id(self) -> int:
        """Compute integer state ID (0-23)."""
        return self.outs * 8 + self.base_encoding

    @property
    def bases_occupied(self) -> list[int]:
        """Return list of occupied bases (1=1B, 2=2B, 4=3B)."""
        bases = []
        if self.base_encoding & 1:
            bases.append(1)
        if self.base_encoding & 2:
            bases.append(2)
        if self.base_encoding & 4:
            bases.append(3)
        return bases

    @classmethod
    def from_state_id(cls, state_id: int) -> 'BaseOutState':
        """Create state from integer ID."""
        return cls(outs=state_id // 8, base_encoding=state_id % 8)

    @field_validator('outs', 'base_encoding')
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        if v < 0:
            msg = 'Value must be non-negative'
            raise ValueError(msg)
        return v


class GameState(BaseState):
    """Complete game state for simulation.

    Captures all information needed to simulate from a given point.
    """
    inning: int = Field(..., ge=1, le=50, description='Current inning (1-50)')
    is_bottom: bool = Field(..., description='True if bottom of inning')
    home_score: int = Field(default=0, ge=0, description='Home team runs')
    away_score: int = Field(default=0, ge=0, description='Away team runs')
    outs: int = Field(..., ge=0, le=2, description='Current outs')
    bases: int = Field(..., ge=0, le=7, description='Base occupancy bitmask')

    # Current matchup
    batter_id: str | None = Field(None, description='Current batter ID')
    pitcher_id: str | None = Field(None, description='Current pitcher ID')
    batter_order_position: int | None = Field(None, ge=1, le=9, description="Batter's lineup position")

    # Count (optional, for pitch-level tracking)
    balls: int = Field(default=0, ge=0, le=4)
    strikes: int = Field(default=0, ge=0, le=3)

    @property
    def base_out_state(self) -> BaseOutState:
        """Return base-out state representation."""
        return BaseOutState(outs=self.outs, base_encoding=self.bases)

    @property
    def batting_team_score(self) -> int:
        """Score of team currently batting."""
        return self.home_score if self.is_bottom else self.away_score

    @property
    def fielding_team_score(self) -> int:
        """Score of team currently fielding."""
        return self.away_score if self.is_bottom else self.home_score

    @property
    def score_differential(self) -> int:
        """Score diff from batting team's perspective."""
        return self.batting_team_score - self.fielding_team_score


class LineupConfig(BaseState):
    """Lineup configuration for simulation."""
    player_ids: list[str] = Field(..., min_length=9, max_length=9, description='9 player IDs in batting order')
    starting_pitcher_id: str | None = Field(None, description='Starting pitcher ID')
    team_id: str | None = Field(None, description='Team identifier')

    @field_validator('player_ids')
    @classmethod
    def validate_lineup_length(cls, v: list[str]) -> list[str]:
        if len(v) != 9:
            msg = 'Lineup must have exactly 9 players'
            raise ValueError(msg)
        return v


class WeatherConfig(BaseState):
    """Weather conditions for simulation adjustments.

    Weather significantly affects scoring:
    - Temperature: Every 10°F above/below 70°F = ~0.25 runs
    - Wind >15mph in = suppresses HRs, >15mph out = increases HRs
    - Humidity affects ball carry (dry air = more carry)
    """
    temperature_f: float = Field(..., ge=20, le=120, description='Temperature in Fahrenheit')
    wind_speed_mph: float = Field(default=0, ge=0, le=50, description='Wind speed in MPH')
    wind_direction: WindDirection = Field(default=WindDirection.CALM)
    humidity_percent: float = Field(default=50, ge=0, le=100, description='Relative humidity')

    # Derived adjustments (calculated at runtime)
    @property
    def run_expectancy_adjustment(self) -> float:
        """Total run adjustment factor.

        Based on sabermetric research:
        - 70°F baseline
        - Each degree = 0.025 runs
        - Wind 15+ mph in/out = ±0.5 runs
        """
        temp_adj = (self.temperature_f - 70) * 0.025

        wind_adj = 0.0
        if self.wind_speed_mph >= 15:
            if self.wind_direction in (WindDirection.IN,):
                wind_adj = -0.5
            elif self.wind_direction in (WindDirection.OUT,):
                wind_adj = 0.5

        return temp_adj + wind_adj

    @property
    def hr_rate_adjustment(self) -> float:
        """Home run rate adjustment multiplier.

        Returns:
            Factor to multiply HR rate (e.g., 0.85 = 15% reduction)
        """
        base = 1.0

        # Temperature effect
        if self.temperature_f > 80:
            base += (self.temperature_f - 80) * 0.005
        elif self.temperature_f < 60:
            base -= (60 - self.temperature_f) * 0.003

        # Wind effect (dominant factor)
        if self.wind_speed_mph >= 10:
            if self.wind_direction == WindDirection.IN:
                base -= (self.wind_speed_mph - 10) * 0.03
            elif self.wind_direction == WindDirection.OUT:
                base += (self.wind_speed_mph - 10) * 0.03

        return max(0.5, min(1.5, base))


class WeatherAdjustments(BaseState):
    """Calculated probability adjustments from weather.

    Applied to PAOutcomeModel predictions to account for weather effects.
    """
    home_run_prob_multiplier: float = Field(default=1.0, ge=0.3, le=3.0)
    extra_base_prob_multiplier: float = Field(default=1.0, ge=0.5, le=2.0)
    walk_prob_multiplier: float = Field(default=1.0, ge=0.7, le=1.3)  # Wind affects control

    @classmethod
    def from_weather_config(cls, weather: WeatherConfig) -> 'WeatherAdjustments':
        """Calculate adjustments from weather config."""
        hr_mult = weather.hr_rate_adjustment

        # Extra bases also affected by temperature
        xb_mult = 1.0 + (weather.temperature_f - 70) * 0.002

        # Walks slightly affected by wind (pitcher control)
        if weather.wind_speed_mph > 20:
            walk_mult = 1.1  # Hard to throw strikes
        else:
            walk_mult = 1.0

        return cls(
            home_run_prob_multiplier=hr_mult,
            extra_base_prob_multiplier=xb_mult,
            walk_prob_multiplier=walk_mult,
        )


class SimulationConfig(BaseState):
    """Configuration for a simulation run.

    This is the primary input for starting a new simulation.
    """
    model_config = ConfigDict(json_schema_extra={
        'example': {
            'simulation_type': 'monte_carlo',
            'num_iterations': 10000,
            'game_id': '716190',
            'season': 2024,
            'starting_state': {
                'inning': 7,
                'is_bottom': True,
                'home_score': 4,
                'away_score': 2,
                'outs': 1,
                'bases': 3,
            },
        },
    })

    simulation_type: SimulationType = Field(..., description='Type of simulation to run')
    num_iterations: int = Field(default=10000, ge=100, le=1000000, description='Number of Monte Carlo iterations')

    # Game context
    game_id: str | None = Field(None, description='Game identifier')
    season: int | None = Field(None, ge=1900, le=2100, description='Season year')

    # Starting state
    starting_state: GameState | None = Field(None, description='Initial game state')

    # Lineups
    home_lineup: LineupConfig | None = Field(None, description='Home team lineup')
    away_lineup: LineupConfig | None = Field(None, description='Away team lineup')

    # Weather (optional - for weather-adjusted simulations)
    weather: WeatherConfig | None = Field(None, description='Weather conditions for run adjustment')
    venue_id: str | None = Field(None, description='Venue/park identifier (for park factors)')
    use_park_factors: bool = Field(default=True, description='Apply park-specific adjustments')

    # Execution
    parallel_workers: int = Field(default=1, ge=1, le=32, description='Number of parallel workers')
    random_seed: int | None = Field(None, description='Random seed for reproducibility')

    # Storage
    save_states: bool = Field(default=False, description='Save intermediate states to DB')
    save_transitions: bool = Field(default=True, description='Save transition log to DB')

    # Metadata
    tags: dict[str, str] = Field(default_factory=dict, description='User-defined tags')
    notes: str | None = Field(None, description='User notes')


class SimulationRun(BaseState):
    """Represents a simulation run in the database.

    Maps to simulation.runs table.
    """
    run_id: UUID = Field(..., description='Unique simulation ID')
    model_id: int | None = Field(None, description='ML model ID if using ML-based sim')
    version_id: int | None = Field(None, description='Model version ID')

    simulation_type: SimulationType = Field(..., description='Type of simulation')
    num_iterations: int = Field(..., description='Total iterations planned')

    # Game context
    game_id: str | None = Field(None, description='Game identifier')
    season: int | None = Field(None, description='Season year')

    # Starting state (stored as JSONB in DB)
    starting_state: GameState | None = Field(None, description='Initial game state')

    # Execution tracking
    status: SimulationStatus = Field(default=SimulationStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = Field(None)
    completed_at: datetime | None = Field(None)
    duration_seconds: int | None = Field(None)

    # Results summary (populated when complete)
    completed_iterations: int = Field(default=0)
    home_win_probability: float | None = Field(None, ge=0, le=1)
    expected_home_score: float | None = Field(None)
    expected_away_score: float | None = Field(None)

    # Error tracking
    error_message: str | None = Field(None)

    @property
    def is_complete(self) -> bool:
        """Check if simulation is complete."""
        return self.status == SimulationStatus.COMPLETED

    @property
    def success(self) -> bool:
        """Check if simulation succeeded."""
        return self.status == SimulationStatus.COMPLETED and self.error_message is None


class SimulationStateRecord(BaseState):
    """Single state snapshot during simulation.

    Maps to simulation.states table.
    """
    state_id: int | None = Field(None, description='Auto-generated state ID')
    run_id: UUID = Field(..., description='Parent simulation run')
    iteration: int = Field(..., ge=0, description='Iteration number')
    plate_appearance_number: int = Field(default=0, ge=0)

    # Game state
    inning: int = Field(..., ge=1)
    is_bottom: bool = Field(...)
    outs: int = Field(..., ge=0, le=3)
    bases: int = Field(..., ge=0, le=7)
    home_score: int = Field(default=0)
    away_score: int = Field(default=0)

    # Matchup
    batter_id: str | None = Field(None)
    pitcher_id: str | None = Field(None)
    batter_order_position: int | None = Field(None, ge=1, le=9)

    # Timestamp for replay analysis
    state_timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def base_out_state(self) -> BaseOutState:
        """Get base-out state representation."""
        if self.outs >= 3:
            # Inning over state
            return BaseOutState(outs=2, base_encoding=0)
        return BaseOutState(outs=self.outs, base_encoding=self.bases)


class TransitionRecord(BaseState):
    """Single transition event in simulation.

    Maps to simulation.transitions table.
    """
    log_id: int | None = Field(None)
    run_id: UUID = Field(...)
    iteration: int = Field(..., ge=0)
    plate_appearance_number: int = Field(..., ge=0)

    # States
    from_base_out_state: int = Field(..., ge=0, le=23)
    to_base_out_state: int = Field(..., ge=0, le=24)  # 24 = inning over

    # Event
    event_type: EventType = Field(...)
    runs_scored: int = Field(default=0, ge=0)

    # Context
    batter_id: str | None = Field(None)
    pitcher_id: str | None = Field(None)
    inning: int | None = Field(None)
    is_bottom: bool | None = Field(None)

    event_timestamp: datetime = Field(default_factory=datetime.utcnow)


class SimulationResult(BaseState):
    """Final result of a single simulation iteration.

    Maps to simulation.results table.
    """
    result_id: int | None = Field(None)
    run_id: UUID = Field(...)
    iteration: int = Field(..., ge=0)

    # Final state
    final_inning: int = Field(..., ge=1)
    final_is_bottom: bool = Field(...)
    final_home_score: int = Field(..., ge=0)
    final_away_score: int = Field(..., ge=0)

    # Outcome
    home_won: bool = Field(...)
    is_tie: bool = Field(default=False)
    is_extra_innings: bool = Field(default=False)

    # Statistics
    total_plate_appearances: int = Field(default=0)
    total_hits: int = Field(default=0)
    total_walks: int = Field(default=0)
    total_home_runs: int = Field(default=0)

    # Performance
    duration_ms: int | None = Field(None)


class AggregatedSimulationResult(BaseState):
    """Aggregated results across all iterations.

    Computed from simulation.results table.
    """
    run_id: UUID = Field(...)
    simulation_type: SimulationType = Field(...)
    num_iterations: int = Field(...)
    completed_iterations: int = Field(...)

    # Win probabilities
    home_win_probability: float = Field(..., ge=0, le=1)
    away_win_probability: float = Field(..., ge=0, le=1)
    tie_probability: float = Field(default=0, ge=0, le=1)

    # Score expectations
    mean_home_score: float = Field(...)
    mean_away_score: float = Field(...)
    std_home_score: float = Field(default=0)
    std_away_score: float = Field(default=0)

    # Run distributions
    home_run_distribution: dict[str, float] = Field(
        default_factory=dict,
        description='Map of run count to probability',
    )
    away_run_distribution: dict[str, float] = Field(
        default_factory=dict,
        description='Map of run count to probability',
    )

    # Game length
    mean_total_pas: float = Field(default=0)
    mean_innings: float = Field(default=9)

    @property
    def predicted_winner(self) -> str:
        """Return predicted winner ('home', 'away', or 'tie')."""
        if self.home_win_probability > self.away_win_probability:
            return 'home'
        if self.away_win_probability > self.home_win_probability:
            return 'away'
        return 'tie'


# ============================================================================
# Backtest Schemas
# ============================================================================

class BacktestConfig(BaseState):
    """Configuration for model backtesting.

    Defines walk-forward validation parameters.
    """
    model_name: str = Field(..., description='Name of model to backtest')
    model_version: str | None = Field(None, description='Specific version')

    # Data split
    train_seasons: list[int] = Field(..., min_length=1, description='Seasons for training')
    test_seasons: list[int] = Field(..., min_length=1, description='Seasons for testing')

    # Walk-forward parameters
    test_window_days: int = Field(default=7, ge=1, le=30, description='Test window size')
    min_train_samples: int = Field(default=1000, ge=100, description='Minimum training samples')

    # Feature configuration
    feature_set: str = Field(default='default', description='Feature set name')
    feature_subset: list[str] | None = Field(None, description='Specific features to use')

    # Execution
    save_predictions: bool = Field(default=True, description='Store predictions in DB')
    save_feature_importance: bool = Field(default=False)

    # Metadata
    tags: dict[str, str] = Field(default_factory=dict)
    notes: str | None = Field(None)


class BacktestIterationResult(BaseState):
    """Result from a single backtest iteration.

    One train/test split in walk-forward validation.
    """
    iteration: int = Field(..., ge=0)

    # Date ranges
    train_start_date: date = Field(...)
    train_end_date: date = Field(...)
    test_start_date: date = Field(...)
    test_end_date: date = Field(...)

    # Sample counts
    train_samples: int = Field(..., ge=0)
    test_samples: int = Field(..., ge=0)

    # Metrics
    accuracy: float = Field(..., ge=0, le=1)
    log_loss: float = Field(..., ge=0)
    auc: float = Field(..., ge=0, le=1)
    brier_score: float = Field(..., ge=0)
    precision: float = Field(..., ge=0, le=1)
    recall: float = Field(..., ge=0, le=1)
    f1: float = Field(..., ge=0, le=1)
    calibration_error: float = Field(..., ge=0)

    # Execution
    predictions_made: int = Field(..., ge=0)
    predictions_stored: bool = Field(default=False)
    duration_seconds: float = Field(..., ge=0)

    # Status
    success: bool = Field(default=True)
    error_message: str | None = Field(None)


class CalibrationResult(BaseState):
    """Calibration analysis for probabilistic predictions."""
    bin_edges: list[float] = Field(..., description='Probability bin boundaries')
    bin_centers: list[float] = Field(..., description='Bin center points')
    observed_frequencies: list[float] = Field(..., description='Actual occurrence rate per bin')
    predicted_frequencies: list[float] = Field(..., description='Mean predicted probability per bin')
    bin_counts: list[int] = Field(..., description='Number of samples per bin')

    # Calibration metrics
    expected_calibration_error: float = Field(..., ge=0, description='Weighted average calibration error')
    maximum_calibration_error: float = Field(..., ge=0, description='Max calibration error across bins')


class BacktestResult(BaseState):
    """Complete backtest results across all iterations.

    Aggregated from all walk-forward iterations.
    """
    backtest_id: int | None = Field(None)
    model_name: str = Field(...)
    model_version: str | None = Field(None)

    # Status
    status: BacktestStatus = Field(default=BacktestStatus.PENDING)

    # Timing
    started_at: datetime | None = Field(None)
    completed_at: datetime | None = Field(None)
    duration_seconds: float = Field(default=0)

    # Aggregated metrics
    mean_accuracy: float = Field(default=0)
    std_accuracy: float = Field(default=0)
    mean_log_loss: float = Field(default=0)
    std_log_loss: float = Field(default=0)
    mean_auc: float = Field(default=0)
    std_auc: float = Field(default=0)
    mean_brier_score: float = Field(default=0)
    mean_calibration_error: float = Field(default=0)

    # Counts
    total_iterations: int = Field(default=0)
    completed_iterations: int = Field(default=0)
    failed_iterations: int = Field(default=0)
    total_predictions: int = Field(default=0)

    # Detailed results
    iterations: list[BacktestIterationResult] = Field(default_factory=list)
    calibration: CalibrationResult | None = Field(None)

    # Breakdowns
    by_season: dict[str, dict[str, float]] = Field(default_factory=dict)
    by_month: dict[str, dict[str, float]] = Field(default_factory=dict)

    # Error tracking
    error_message: str | None = Field(None)

    @property
    def success(self) -> bool:
        """Check if backtest completed successfully."""
        return self.status == BacktestStatus.COMPLETED and self.error_message is None

    @property
    def iteration_success_rate(self) -> float:
        """Fraction of iterations that succeeded."""
        if self.total_iterations == 0:
            return 0.0
        return (self.total_iterations - self.failed_iterations) / self.total_iterations


# ============================================================================
# Model Registry Schemas
# ============================================================================

class ModelRegistryEntry(BaseState):
    """Entry in the model registry.

    Maps to models.registry table.
    """
    model_id: int = Field(...)
    model_name: str = Field(...)
    model_type: str = Field(...)
    task: str = Field(...)
    description: str | None = Field(None)

    # Features
    features: list[str] = Field(default_factory=list)
    target_variable: str | None = Field(None)
    output_type: str | None = Field(None)

    # Versioning
    current_version: str | None = Field(None)
    total_versions: int = Field(default=0)

    # Status
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ModelVersionEntry(BaseState):
    """Specific model version.

    Maps to models.versions table.
    """
    version_id: int = Field(...)
    model_id: int = Field(...)
    version: str = Field(...)
    version_tag: str | None = Field(None)

    # Training info
    git_commit: str | None = Field(None)
    code_version: str | None = Field(None)
    training_run_id: int | None = Field(None)
    training_data_start: date | None = Field(None)
    training_data_end: date | None = Field(None)
    training_data_rows: int | None = Field(None)

    # Performance
    metrics: dict[str, float] = Field(default_factory=dict)
    validation_metrics: dict[str, float] = Field(default_factory=dict)
    test_metrics: dict[str, float] = Field(default_factory=dict)

    # Model characteristics
    algorithm: str | None = Field(None)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    feature_importance: dict[str, float] = Field(default_factory=dict)

    # Status
    status: str = Field(default='pending')
    is_production: bool = Field(default=False)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deployed_at: datetime | None = Field(None)


# ============================================================================
# API Response Schemas
# ============================================================================

class SimulationResponse(BaseState):
    """API response for simulation requests."""
    success: bool = Field(...)
    run_id: UUID | None = Field(None)
    message: str = Field(...)

    # Results (if complete)
    results: AggregatedSimulationResult | None = Field(None)

    # Status (if still running)
    status: SimulationStatus | None = Field(None)
    progress_percent: float | None = Field(None, ge=0, le=100)

    # Error (if failed)
    error: str | None = Field(None)


class BacktestResponse(BaseState):
    """API response for backtest requests."""
    success: bool = Field(...)
    backtest_id: int | None = Field(None)
    message: str = Field(...)

    # Results (if complete)
    results: BacktestResult | None = Field(None)

    # Status (if still running)
    status: BacktestStatus | None = Field(None)
    progress_percent: float | None = Field(None, ge=0, le=100)

    # Error (if failed)
    error: str | None = Field(None)


# ============================================================================
# Export for convenient importing
# ============================================================================

__all__ = [
    'AggregatedSimulationResult',
    # Backtest schemas
    'BacktestConfig',
    'BacktestIterationResult',
    'BacktestResponse',
    'BacktestResult',
    'BacktestStatus',
    # Simulation schemas
    'BaseOutState',
    'CalibrationResult',
    'EventType',
    'GameState',
    'LineupConfig',
    # Registry schemas
    'ModelRegistryEntry',
    'ModelVersionEntry',
    'SimulationConfig',
    # API schemas
    'SimulationResponse',
    'SimulationResult',
    'SimulationRun',
    'SimulationStateRecord',
    'SimulationStatus',
    # Enums
    'SimulationType',
    'TransitionRecord',
]
