"""Base source adapter pattern for the baseball platform.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from abc import ABC, abstractmethod
from pathlib import Path

from baseball.core.types import SourceRequest, SourceResult


class BaseSource(ABC):
    """Abstract base class for all data source adapters."""

    @abstractmethod
    def download(self, config: SourceRequest) -> SourceResult:
        """Download data from source to local storage.

        Args:
            config: Source request configuration

        Returns:
            Source result with download status
        """
        pass

    @abstractmethod
    def ingest(self, source_path: Path) -> SourceResult:
        """Transform and load to database.

        Args:
            source_path: Path to downloaded source data

        Returns:
            Source result with ingest status
        """
        pass

    @abstractmethod
    def validate(self, ingest_result: SourceResult) -> SourceResult:
        """Validate ingested data.

        Args:
            ingest_result: Result from ingest operation

        Returns:
            Source result with validation status
        """
        pass
