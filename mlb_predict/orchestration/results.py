"""Orchestration Result Models (Pydantic).

Type-safe result classes for all database operations.
All results include timing, status, and metrics.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field


class OperationResult(BaseModel):
    """Base result for any operation."""

    operation_name: str
    status: str = 'pending'
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_seconds: float = 0.0
    rows_affected: int = 0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    checkpoint_id: str | None = None

    @property
    def duration(self) -> timedelta:
        return timedelta(seconds=self.duration_seconds)

    @property
    def success(self) -> bool:
        return self.status == 'completed' and not self.errors


class PhaseResult(OperationResult):
    """Result for a single phase of an operation."""

    phase_number: int
    phase_name: str
    sql_files_executed: list[str] = Field(default_factory=list)
    batch_results: list[BatchResult] = Field(default_factory=list)


class BatchResult(OperationResult):
    """Result for a single batch operation."""

    batch_number: int
    start_row: int
    end_row: int
    batch_size: int


class FeaturePopulationResult(OperationResult):
    """Result for feature population operations."""

    phases_completed: list[PhaseResult] = Field(default_factory=list)
    features_populated: dict[str, int] = Field(default_factory=dict)
    verification_results: dict[str, float] | None = None
    total_phases: int = 0
    completed_phases: int = 0


class BridgePopulationResult(OperationResult):
    """Result for bridge table population."""

    tables_populated: dict[str, int] = Field(default_factory=dict)
    validation_results: dict[str, Any] | None = None
    coverage_percentages: dict[str, float] = Field(default_factory=dict)


class IngestResult(OperationResult):
    """Result for data ingestion operations."""

    source: str
    seasons_processed: list[int] = Field(default_factory=list)
    records_downloaded: int = 0
    records_ingested: int = 0
    records_failed: int = 0
    checksum_valid: bool = True


class ValidationResult(OperationResult):
    """Result for validation operations."""

    tables_validated: list[str] = Field(default_factory=list)
    issues_found: list[dict[str, Any]] = Field(default_factory=list)
    coverage_report: dict[str, float] = Field(default_factory=dict)
    passed: bool = False


class ModelTrainingResult(OperationResult):
    """Result for model training operations."""

    model_type: str
    model_id: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    feature_importance: dict[str, float] | None = None
    model_path: str | None = None
