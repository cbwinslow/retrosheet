"""Base source adapter interface.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from mlb_predict import ModelConfig


@dataclass
class DownloadResult:
    """Result of a download operation."""

    success: bool
    rows_downloaded: int = 0
    rows_failed: int = 0
    output_path: Path | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class IngestResult:
    """Result of an ingest operation."""

    success: bool
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_failed: int = 0
    error_message: str | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    success: bool
    issues: list[dict[str, Any]] = None
    warning_count: int = 0
    error_count: int = 0
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.metadata is None:
            self.metadata = {}


class BaseSource(ABC):
    """Abstract base class for data source adapters.

    All data sources (MLB, Retrosheet, ESPN, Statcast) must implement
    this interface for unified pipeline orchestration.
    """

    def __init__(self, config: ModelConfig | None = None):
        self.config = config
        self._name = self.__class__.__name__.replace('Source', '').lower()

    @property
    def name(self) -> str:
        """Source identifier (e.g., 'mlb', 'retrosheet')."""
        return self._name

    @abstractmethod
    def download(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        game_pks: list[int] | None = None,
        output_dir: Path | None = None,
        force: bool = False,
    ) -> DownloadResult:
        """Download raw data from source.

        Args:
            start_date: Start date for range download
            end_date: End date for range download
            game_pks: Specific game IDs to download
            output_dir: Where to save downloaded files
            force: Re-download even if exists

        Returns:
            DownloadResult with counts and paths
        """

    @abstractmethod
    def ingest(
        self,
        input_path: Path | None = None,
        validate: bool = True,
    ) -> IngestResult:
        """Ingest downloaded data into database.

        Args:
            input_path: Path to downloaded files (or use default)
            validate: Run validation checks after ingest

        Returns:
            IngestResult with row counts
        """

    @abstractmethod
    def validate(self) -> ValidationResult:
        """Validate ingested data quality.

        Returns:
            ValidationResult with issues found
        """

    @abstractmethod
    def get_available_dates(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[date]:
        """Get list of dates with available data.

        Returns:
            List of dates that can be downloaded
        """

    def status(self) -> dict[str, Any]:
        """Get current source status."""
        return {
            'name': self.name,
            'configured': self.config is not None,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
