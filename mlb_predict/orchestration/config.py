"""
Orchestration Configuration Models (Pydantic)

Type-safe configuration for all database operations.
All configs include validation, defaults, and documentation.
"""

from __future__ import annotations

from abc import ABC
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, field_validator, model_validator


class DataSource(str, Enum):
    """Supported data sources for ingestion."""
    STATCAST = "statcast"
    MLB_API = "mlb_api"
    ESPN = "espn"
    BASEBALL_REFERENCE = "baseball_reference"
    LAHMAN = "lahman"
    CHADWICK = "chadwick"
    SPORTSRADAR = "sportradar"


class OperationMode(str, Enum):
    """Operation execution modes."""
    FULL = "full"           # Run complete operation
    RESUME = "resume"       # Resume from last checkpoint
    DRY_RUN = "dry_run"     # Show what would be executed
    QUICK = "quick"         # Skip expensive operations
    VALIDATE = "validate"   # Only run validation


class OperationStatus(str, Enum):
    """Operation execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"     # Some phases completed
    ABORTED = "aborted"


class LogLevel(str, Enum):
    """Logging verbosity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class OperationConfig(BaseModel, ABC):
    """
    Base configuration for any database operation.
    
    All operation configs inherit from this base class.
    Provides common validation, logging, and resume capabilities.
    
    Attributes:
        dry_run: If True, show what would be executed without running
        resume_from: Checkpoint ID to resume from (None = start fresh)
        batch_size: Rows to process per batch (for large operations)
        parallel_workers: Number of parallel workers (where supported)
        log_level: Logging verbosity
        mode: Execution mode (full, resume, dry_run, etc.)
        timeout_seconds: Max operation time before auto-abort
        max_retries: Number of retries on transient failures
        validate_after: Run validation after operation completes
    
    Example:
        ```python
        config = OperationConfig(
            dry_run=False,
            batch_size=100000,
            parallel_workers=4,
            validate_after=True
        )
        ```
    """
    
    # Execution Control
    dry_run: bool = Field(
        default=False,
        description="Show what would be executed without running"
    )
    resume_from: Optional[str] = Field(
        default=None,
        description="Checkpoint ID to resume from (None = start fresh)"
    )
    mode: OperationMode = Field(
        default=OperationMode.FULL,
        description="Execution mode"
    )
    
    # Performance Tuning
    batch_size: int = Field(
        default=100000,
        ge=1000,
        le=1000000,
        description="Rows to process per batch"
    )
    parallel_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Number of parallel workers"
    )
    
    # Reliability
    timeout_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Max operation time before auto-abort"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of retries on transient failures"
    )
    
    # Validation & Logging
    validate_after: bool = Field(
        default=True,
        description="Run validation after operation completes"
    )
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging verbosity"
    )
    
    # Metadata
    operation_name: Optional[str] = Field(
        default=None,
        description="Human-readable operation name"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (JSON serializable)"
    )
    
    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        """Ensure batch size is reasonable for memory constraints."""
        if v > 500000:
            raise ValueError("batch_size > 500k may cause memory issues")
        return v


class FeaturePopulationConfig(OperationConfig):
    """
    Configuration for feature population operations.
    
    Controls how ML features are populated from raw data.
    Supports phased execution for incremental feature building.
    
    Attributes:
        phases: List of phase numbers to run (empty = all phases)
        skip_verification: Skip post-population verification
        checkpoint_interval: Rows between checkpoints
        include_physics_features: Include pitch physics features
        include_location_features: Include pitch location features
        include_context_features: Include game context features
        include_matchup_features: Include batter-pitcher matchup features
        feature_categories: Categories of features to populate
    
    Phases:
        0: Prerequisites (verify base_features exists)
        1: Core Engineered (velocity, movement, outcomes)
        2: Additional (platoon, spin, fatigue)
        3: Extended (pitch quality, RE24, WPA)
        4: Context (weather, momentum, umpire)
        5: Final (Markov chains, matchups, postseason)
        6: Specialized (attendance, stadium physics)
        7: Verification & Views
    
    Example:
        ```python
        config = FeaturePopulationConfig(
            phases=[1, 2, 3],  # Run phases 1-3 only
            batch_size=100000,
            checkpoint_interval=100000,
            validate_after=True
        )
        ```
    """
    
    # Phase Control
    phases: List[int] = Field(
        default_factory=list,
        description="Phase numbers to run (empty = all phases 0-7)"
    )
    skip_verification: bool = Field(
        default=False,
        description="Skip post-population verification"
    )
    checkpoint_interval: int = Field(
        default=100000,
        ge=10000,
        le=500000,
        description="Rows between checkpoints"
    )
    
    # Feature Categories
    include_physics_features: bool = Field(default=True)
    include_location_features: bool = Field(default=True)
    include_context_features: bool = Field(default=True)
    include_matchup_features: bool = Field(default=True)
    include_sequential_features: bool = Field(default=False)  # Expensive
    
    feature_categories: Set[str] = Field(
        default_factory=lambda: {
            "physics", "location", "context", "matchup", "quality"
        },
        description="Categories of features to populate"
    )
    
    # Schema Target
    target_schema: str = Field(
        default="features_pitch",
        description="Schema containing engineered_features table"
    )
    target_table: str = Field(
        default="engineered_features",
        description="Table to populate"
    )
    
    @field_validator("phases")
    @classmethod
    def validate_phases(cls, v: List[int]) -> List[int]:
        """Ensure phase numbers are valid (0-7)."""
        if v:
            invalid = [p for p in v if p < 0 or p > 7]
            if invalid:
                raise ValueError(f"Invalid phases: {invalid}. Must be 0-7")
        return sorted(set(v)) if v else []
    
    @model_validator(mode="after")
    def set_operation_name(self) -> FeaturePopulationConfig:
        """Auto-set operation name if not provided."""
        if not self.operation_name:
            if self.phases:
                phase_str = ",".join(map(str, self.phases))
                self.operation_name = f"feature_population_phases_{phase_str}"
            else:
                self.operation_name = "feature_population_all_phases"
        return self


class BridgePopulationConfig(OperationConfig):
    """
    Configuration for bridge table population operations.
    
    Controls how ID cross-reference tables are populated.
    Links IDs across Retrosheet, MLB API, Lahman, and other sources.
    
    Attributes:
        include_player_xref: Populate player ID cross-references
        include_team_xref: Populate team ID cross-references
        include_game_xref: Populate game ID cross-references
        include_park_xref: Populate park ID cross-references
        include_coach_xref: Populate coach ID cross-references
        include_umpire_xref: Populate umpire ID cross-references
        include_external_xref: Populate external source ID cross-references
        chadwick_register_files: List of Chadwick register files to ingest
        gap_fill_from_lahman: Use Lahman to fill gaps in player_xref
        run_validation_tests: Run validation tests after population
    
    Dependency Order:
        1. team_xref (required by others)
        2. park_xref
        3. player_xref (slow, optional)
        4. game_xref
        5. coach_xref
        6. umpire_xref
    
    Example:
        ```python
        config = BridgePopulationConfig(
            include_player_xref=True,  # Slow operation
            include_game_xref=True,
            include_team_xref=True,
            run_validation_tests=True
        )
        ```
    """
    
    # Bridge Tables to Populate
    include_player_xref: bool = Field(
        default=True,
        description="Populate player ID cross-references (slow)"
    )
    include_team_xref: bool = Field(
        default=True,
        description="Populate team ID cross-references"
    )
    include_game_xref: bool = Field(
        default=True,
        description="Populate game ID cross-references"
    )
    include_park_xref: bool = Field(
        default=True,
        description="Populate park ID cross-references"
    )
    include_coach_xref: bool = Field(
        default=True,
        description="Populate coach ID cross-references"
    )
    include_umpire_xref: bool = Field(
        default=True,
        description="Populate umpire ID cross-references"
    )
    include_external_xref: bool = Field(
        default=False,
        description="Populate external source ID cross-references"
    )
    
    # Data Sources
    chadwick_register_files: Optional[List[str]] = Field(
        default=None,
        description="Chadwick register files to ingest (None = all)"
    )
    gap_fill_from_lahman: bool = Field(
        default=True,
        description="Use Lahman to fill gaps in player_xref"
    )
    
    # Validation
    run_validation_tests: bool = Field(
        default=True,
        description="Run validation tests after population"
    )
    min_coverage_pct: Dict[str, float] = Field(
        default_factory=lambda: {
            "player_mlb": 95.0,
            "player_retrosheet": 20.0,
            "team_retrosheet": 100.0,
            "pitch_data": 100.0,
        },
        description="Minimum coverage percentages for validation"
    )
    
    # Source-Preserved Options
    preserve_source_data: bool = Field(
        default=True,
        description="Keep source data files for reproducibility"
    )
    
    @model_validator(mode="after")
    def validate_dependencies(self) -> BridgePopulationConfig:
        """Ensure required dependencies are enabled."""
        # game_xref requires team_xref
        if self.include_game_xref and not self.include_team_xref:
            raise ValueError("game_xref requires team_xref (enable both)")
        return self


class IngestOperationConfig(OperationConfig):
    """
    Configuration for data ingestion operations.
    
    Controls how external data is downloaded and loaded into database.
    Supports multiple data sources with source-specific options.
    
    Attributes:
        source: Data source to ingest from
        seasons: List of seasons to ingest
        date_range: Alternative to seasons (start_date, end_date)
        validate_checksums: Verify data integrity with checksums
        deduplicate: Remove duplicate records
        use_cache: Use local cache for API responses
        api_delay_seconds: Delay between API calls (rate limiting)
        max_api_calls_per_minute: Rate limit for API
        fetch_play_by_play: Include play-by-play data
        fetch_player_stats: Include player statistics
        fetch_team_stats: Include team statistics
    
    Example:
        ```python
        # Ingest Statcast for 2024-2025
        config = IngestOperationConfig(
            source=DataSource.STATCAST,
            seasons=[2024, 2025],
            validate_checksums=True,
            api_delay_seconds=1.0
        )
        
        # Ingest ESPN data for date range
        config = IngestOperationConfig(
            source=DataSource.ESPN,
            date_range=("2024-04-01", "2024-10-01"),
            use_cache=True
        )
        ```
    """
    
    # Data Source
    source: DataSource = Field(
        ...,  # Required
        description="Data source to ingest from"
    )
    
    # Time Range (one of these required)
    seasons: List[int] = Field(
        default_factory=list,
        description="Seasons to ingest (e.g., [2024, 2025])"
    )
    date_range: Optional[tuple[str, str]] = Field(
        default=None,
        description="Date range as (start_date, end_date) in YYYY-MM-DD format"
    )
    
    # Data Quality
    validate_checksums: bool = Field(
        default=True,
        description="Verify data integrity with checksums"
    )
    deduplicate: bool = Field(
        default=True,
        description="Remove duplicate records"
    )
    
    # API Configuration
    use_cache: bool = Field(
        default=True,
        description="Use local cache for API responses"
    )
    api_delay_seconds: float = Field(
        default=1.0,
        ge=0.0,
        le=60.0,
        description="Delay between API calls (rate limiting)"
    )
    max_api_calls_per_minute: int = Field(
        default=60,
        ge=1,
        le=300,
        description="Rate limit for API calls"
    )
    
    # Data Types to Fetch
    fetch_play_by_play: bool = Field(default=True)
    fetch_player_stats: bool = Field(default=True)
    fetch_team_stats: bool = Field(default=True)
    fetch_schedule: bool = Field(default=True)
    fetch_boxscores: bool = Field(default=True)
    
    # Source-Specific Options
    statcast_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Options specific to Statcast ingestion"
    )
    mlb_api_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Options specific to MLB API ingestion"
    )
    
    @model_validator(mode="after")
    def validate_time_range(self) -> IngestOperationConfig:
        """Ensure either seasons or date_range is provided."""
        if not self.seasons and not self.date_range:
            raise ValueError("Either seasons or date_range must be provided")
        if self.seasons and self.date_range:
            raise ValueError("Provide either seasons OR date_range, not both")
        return self
    
    @field_validator("date_range")
    @classmethod
    def validate_date_range(cls, v: Optional[tuple[str, str]]) -> Optional[tuple[str, str]]:
        """Validate date range format."""
        if v is None:
            return v
        start, end = v
        try:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            if start_dt > end_dt:
                raise ValueError("Start date must be before end date")
        except ValueError as e:
            raise ValueError(f"Invalid date range format: {e}. Use YYYY-MM-DD") from e
        return v


class ValidationConfig(OperationConfig):
    """
    Configuration for data validation operations.
    
    Controls how data quality checks are performed.
    Supports comprehensive validation across all data sources.
    
    Attributes:
        validation_types: Types of validation to run
        tables_to_validate: Specific tables to validate (empty = all)
        check_foreign_keys: Verify FK constraints
        check_null_counts: Check for unexpected NULLs
        check_duplicate_keys: Check for duplicate primary keys
        check_data_freshness: Verify data is up to date
        check_completeness: Verify expected data exists
        coverage_thresholds: Minimum coverage percentages
        generate_report: Generate validation report
        fail_on_warning: Treat warnings as failures
    
    Example:
        ```python
        config = ValidationConfig(
            validation_types=["completeness", "foreign_keys", "nulls"],
            tables_to_validate=["core.games", "core.events"],
            coverage_thresholds={"core.games": 100.0, "core.events": 95.0},
            generate_report=True
        )
        ```
    """
    
    # Validation Types
    validation_types: Set[str] = Field(
        default_factory=lambda: {
            "completeness", "foreign_keys", "nulls", 
            "duplicates", "freshness", "coverage"
        },
        description="Types of validation to run"
    )
    
    # Scope
    tables_to_validate: List[str] = Field(
        default_factory=list,
        description="Specific tables to validate (empty = all tables)"
    )
    schemas_to_validate: List[str] = Field(
        default_factory=lambda: ["core", "bridge", "features_pitch"],
        description="Schemas to validate"
    )
    
    # Checks
    check_foreign_keys: bool = Field(default=True)
    check_null_counts: bool = Field(default=True)
    check_duplicate_keys: bool = Field(default=True)
    check_data_freshness: bool = Field(default=True)
    check_completeness: bool = Field(default=True)
    check_row_counts: bool = Field(default=True)
    
    # Thresholds
    coverage_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "core.games": 100.0,
            "core.events": 95.0,
            "bridge.player_xref": 95.0,
        },
        description="Minimum coverage percentages by table"
    )
    max_null_pct: float = Field(
        default=5.0,
        ge=0.0,
        le=100.0,
        description="Maximum acceptable NULL percentage"
    )
    
    # Reporting
    generate_report: bool = Field(default=True)
    report_format: str = Field(
        default="markdown",
        pattern="^(markdown|json|html)$"
    )
    fail_on_warning: bool = Field(default=False)


class ModelTrainingConfig(OperationConfig):
    """
    Configuration for model training operations.
    
    Controls how ML models are trained on populated features.
    Integrates with MLB Predict Framework.
    
    Attributes:
        model_type: Type of model to train
        target_variable: Variable to predict
        feature_categories: Which feature categories to use
        train_seasons: Seasons for training data
        test_seasons: Seasons for test data
        validation_pct: Percentage for validation split
        hyperparameters: Model hyperparameters
        save_model: Save trained model to registry
        register_in_db: Register model in database
        cross_validate: Run cross-validation
        cv_folds: Number of CV folds
        early_stopping: Use early stopping
        calibration_method: Probability calibration method
    
    Example:
        ```python
        config = ModelTrainingConfig(
            model_type="xgboost",
            target_variable="pa_outcome",
            feature_categories=["physics", "location", "context"],
            train_seasons=[2015, 2023],
            test_seasons=[2024],
            hyperparameters={"max_depth": 6, "n_estimators": 100},
            save_model=True
        )
        ```
    """
    
    # Model Configuration
    model_type: str = Field(
        ...,
        description="Model type: xgboost, lightgbm, logistic, mlp"
    )
    target_variable: str = Field(
        ...,
        description="Target variable to predict"
    )
    feature_categories: List[str] = Field(
        default_factory=lambda: ["physics", "location", "context"],
        description="Feature categories to include"
    )
    
    # Data Split
    train_seasons: List[int] = Field(
        default_factory=list,
        description="Seasons for training data"
    )
    test_seasons: List[int] = Field(
        default_factory=list,
        description="Seasons for test data"
    )
    validation_pct: float = Field(
        default=0.2,
        ge=0.1,
        le=0.5,
        description="Validation split percentage"
    )
    
    # Training Options
    hyperparameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Model hyperparameters"
    )
    cross_validate: bool = Field(default=True)
    cv_folds: int = Field(default=5, ge=2, le=10)
    early_stopping: bool = Field(default=True)
    early_stopping_rounds: int = Field(default=50, ge=10, le=200)
    
    # Output
    save_model: bool = Field(default=True)
    register_in_db: bool = Field(default=True)
    calibration_method: Optional[str] = Field(
        default="platt",
        pattern="^(platt|isotonic|none)$"
    )
    
    # Database Integration
    use_engineered_features: bool = Field(default=True)
    min_feature_population_pct: float = Field(
        default=90.0,
        ge=50.0,
        le=100.0,
        description="Minimum feature population before training"
    )


# Type alias for any config type
OperationConfigType = OperationConfig | FeaturePopulationConfig | BridgePopulationConfig | IngestOperationConfig | ValidationConfig | ModelTrainingConfig
