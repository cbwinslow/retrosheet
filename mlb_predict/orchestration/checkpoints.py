"""Checkpoint Models for Resumable Operations.

Provides checkpoint dataclasses for tracking operation progress.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Checkpoint:
    """Base checkpoint for any operation."""

    operation_id: str
    stage: str
    timestamp: datetime
    completed_steps: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FeaturePhaseCheckpoint(Checkpoint):
    """Checkpoint for feature population phases."""

    phase_number: int = 0
    phase_name: str = ''
    rows_processed: int = 0
    last_row_id: Any = None


@dataclass
class BridgeTableCheckpoint(Checkpoint):
    """Checkpoint for bridge table population."""

    table_name: str = ''
    records_processed: int = 0
    validation_passed: bool = False


@dataclass
class BatchProgressCheckpoint(Checkpoint):
    """Checkpoint for batch operations."""

    batch_number: int = 0
    total_batches: int = 0
    batch_size: int = 0
    start_row: int = 0
    end_row: int = 0
