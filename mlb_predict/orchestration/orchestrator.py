"""Main Database Orchestrator.

Central controller for all database operations.
Integrates engines, manages checkpoints, and provides unified interface.
"""

from mlb_predict.orchestration.config import (
    BridgePopulationConfig,
    FeaturePopulationConfig,
    IngestOperationConfig,
    ModelTrainingConfig,
    OperationConfig,
    ValidationConfig,
)
from mlb_predict.orchestration.engines import (
    BaseOperationEngine,
    BridgePopulationEngine,
    FeaturePopulationEngine,
    IngestionEngine,
    ModelTrainingEngine,
    ValidationEngine,
)
from mlb_predict.orchestration.results import OperationResult


class DatabaseOrchestrator:
    """Central orchestrator for all database operations.

    Usage:
        orch = DatabaseOrchestrator(db_url="postgresql://localhost:5432/retrosheet")

        # Populate features
        config = FeaturePopulationConfig(phases=[1, 2, 3])
        result = orch.run_operation(config)

        # Populate bridge tables
        config = BridgePopulationConfig(include_player_xref=True)
        result = orch.run_operation(config)
    """

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engines: dict[type[OperationConfig], BaseOperationEngine] = {
            FeaturePopulationConfig: FeaturePopulationEngine(db_url),
            BridgePopulationConfig: BridgePopulationEngine(db_url),
            IngestOperationConfig: IngestionEngine(db_url),
            ValidationConfig: ValidationEngine(db_url),
            ModelTrainingConfig: ModelTrainingEngine(db_url),
        }

    def run_operation(self, config: OperationConfig) -> OperationResult:
        """Run an operation with the given configuration."""
        config_type = type(config)

        if config_type not in self.engines:
            raise ValueError(f'No engine registered for config type: {config_type}')

        engine = self.engines[config_type]

        if not engine.validate_config(config):
            raise ValueError(f'Config validation failed for {config_type}')

        return engine.run(config)

    def get_engine(self, config_type: type[OperationConfig]) -> BaseOperationEngine:
        """Get the engine for a specific config type."""
        if config_type not in self.engines:
            raise ValueError(f'No engine registered for: {config_type}')
        return self.engines[config_type]
