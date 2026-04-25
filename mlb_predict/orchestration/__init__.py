"""
MLB Predict Orchestration Module

Unified database orchestration framework using Pydantic.
Encapsulates all repeatable database processes with type-safe operations.

Usage:
    from mlb_predict.orchestration import DatabaseOrchestrator, FeaturePopulationConfig
    
    orch = DatabaseOrchestrator(db_url="postgresql://localhost:5432/retrosheet")
    config = FeaturePopulationConfig(phases=[1, 2, 3], batch_size=100000)
    result = orch.run_operation(config)
"""

from mlb_predict.orchestration.config import (
    OperationConfig,
    FeaturePopulationConfig,
    BridgePopulationConfig,
    IngestOperationConfig,
    ValidationConfig,
    ModelTrainingConfig,
)

from mlb_predict.orchestration.results import (
    OperationResult,
    FeaturePopulationResult,
    BridgePopulationResult,
    IngestResult,
    ValidationResult,
    ModelTrainingResult,
    PhaseResult,
    BatchResult,
)

from mlb_predict.orchestration.checkpoints import (
    Checkpoint,
    FeaturePhaseCheckpoint,
    BridgeTableCheckpoint,
    BatchProgressCheckpoint,
)

from mlb_predict.orchestration.engines import (
    BaseOperationEngine,
    FeaturePopulationEngine,
    BridgePopulationEngine,
    IngestionEngine,
    ValidationEngine,
    ModelTrainingEngine,
)

from mlb_predict.orchestration.adapter import SQLProcedureAdapter

from mlb_predict.orchestration.orchestrator import DatabaseOrchestrator

__all__ = [
    # Config
    "OperationConfig",
    "FeaturePopulationConfig",
    "BridgePopulationConfig",
    "IngestOperationConfig",
    "ValidationConfig",
    "ModelTrainingConfig",
    # Results
    "OperationResult",
    "FeaturePopulationResult",
    "BridgePopulationResult",
    "IngestResult",
    "ValidationResult",
    "ModelTrainingResult",
    "PhaseResult",
    "BatchResult",
    # Checkpoints
    "Checkpoint",
    "FeaturePhaseCheckpoint",
    "BridgeTableCheckpoint",
    "BatchProgressCheckpoint",
    # Engines
    "BaseOperationEngine",
    "FeaturePopulationEngine",
    "BridgePopulationEngine",
    "IngestionEngine",
    "ValidationEngine",
    "ModelTrainingEngine",
    # Adapter & Orchestrator
    "SQLProcedureAdapter",
    "DatabaseOrchestrator",
]
