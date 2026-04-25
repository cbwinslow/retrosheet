"""
Orchestration Result Models (Pydantic).

Type-safe result classes for all database operations.
All results include timing, status, and metrics.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OperationResult(BaseModel):
    """Base result for any operation."""

    operation_name: str
    status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    rows_affected: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    checkpoint_id: Optional[str] = None

    @property
    def duration(self) -> timedelta:
        return timedelta(seconds=self.duration_seconds)

    @property
    def success(self) -> bool:
        return self.status == "completed" and not self.errors


class PhaseResult(OperationResult):
    """Result for a single phase of an operation."""

    phase_number: int
    phase_name: str
    sql_files_executed: List[str] = Field(default_factory=list)
    batch_results: List[BatchResult] = Field(default_factory=list)


class BatchResult(OperationResult):
    """Result for a single batch operation."""

    batch_number: int
    start_row: int
    end_row: int
    batch_size: int


class FeaturePopulationResult(OperationResult):
    """Result for feature population operations."""

    phases_completed: List[PhaseResult] = Field(default_factory=list)
    features_populated: Dict[str, int] = Field(default_factory=dict)
    verification_results: Optional[Dict[str, float]] = None
    total_phases: int = 0
    completed_phases: int = 0


class BridgePopulationResult(OperationResult):
    """Result for bridge table population."""

    tables_populated: Dict[str, int] = Field(default_factory=dict)
    validation_results: Optional[Dict[str, Any]] = None
    coverage_percentages: Dict[str, float] = Field(default_factory=dict)


class IngestResult(OperationResult):
    """Result for data ingestion operations."""

    source: str
    seasons_processed: List[int] = Field(default_factory=list)
    records_downloaded: int = 0
    records_ingested: int = 0
    records_failed: int = 0
    checksum_valid: bool = True


class ValidationResult(OperationResult):
    """Result for validation operations."""

    tables_validated: List[str] = Field(default_factory=list)
    issues_found: List[Dict[str, Any]] = Field(default_factory=list)
    coverage_report: Dict[str, float] = Field(default_factory=dict)
    passed: bool = False


class ModelTrainingResult(OperationResult):
    """Result for model training operations."""

    model_type: str
    model_id: Optional[str] = None
    metrics: Dict[str, float] = Field(default_factory=dict)
    feature_importance: Optional[Dict[str, float]] = None
    model_path: Optional[str] = None
