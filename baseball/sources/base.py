"""Base source adapter pattern for the baseball platform.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from abc import ABC, abstractmethod
from pathlib import Path

from baseball.core.types import SourceRequest, SourceResult


class BaseSource(ABC):
    """Abstract base class for all data source adapters.

    Checkpoint-Driven Resume:
        All source adapters support resumable downloads via the staging.source_checkpoints
        table. Set resume=True in the SourceRequest to continue from last known state.

    Example:
        >>> config = SourceRequest(
        ...     source_type='retrosheet',
        ...     seasons=[2020, 2021],
        ...     resume=True  # Resume from last checkpoint
        ... )
        >>> result = adapter.download(config)
    """

    def __init__(self) -> None:
        self._ingest_run_id: int | None = None
        self._checkpoints_enabled: bool = True

    def _get_source_name(self) -> str:
        """Return the source name for checkpoint tracking.

        Override in subclasses to return specific source identifier.
        """
        return self.__class__.__name__.lower().replace('source', '')

    def _start_checkpoint(
        self,
        season: int,
        entity_type: str,
        entity_key: str,
        metadata: dict | None = None,
    ) -> int:
        """Start a checkpoint for tracking download progress.

        Args:
            season: Season/year being processed
            entity_type: Type of entity (events, games, rosters, etc.)
            entity_key: Specific file or URL identifier
            metadata: Optional JSON-serializable checkpoint data

        Returns:
            checkpoint_id for updating/completing later
        """
        # Import here to avoid circular dependency
        from baseball.core.db import get_db_connection

        if not self._checkpoints_enabled:
            return -1

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT staging.start_checkpoint(
                        %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        self._get_source_name(),
                        season,
                        entity_type,
                        entity_key,
                        self._ingest_run_id,
                        metadata or {},
                    ),
                )
                result = cur.fetchone()
                conn.commit()
                return result[0] if result else -1
        finally:
            conn.close()

    def _complete_checkpoint(
        self,
        checkpoint_id: int,
        file_path: str | None = None,
        records_processed: int | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Mark a checkpoint as successfully completed.

        Args:
            checkpoint_id: ID from _start_checkpoint()
            file_path: Local path where file was saved
            records_processed: Number of records successfully handled
            metadata: Final checkpoint metadata
        """
        from baseball.core.db import get_db_connection

        if not self._checkpoints_enabled or checkpoint_id < 0:
            return

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT staging.complete_checkpoint(%s, %s, %s, %s)
                    """,
                    (checkpoint_id, file_path, records_processed, metadata or {}),
                )
                conn.commit()
        finally:
            conn.close()

    def _fail_checkpoint(
        self,
        checkpoint_id: int,
        error: str,
        error_code: str | None = None,
        records_processed: int | None = None,
    ) -> None:
        """Mark a checkpoint as failed with error information.

        Args:
            checkpoint_id: ID from _start_checkpoint()
            error: Error message
            error_code: Optional error code/category
            records_processed: Records successfully processed before failure
        """
        from baseball.core.db import get_db_connection

        if not self._checkpoints_enabled or checkpoint_id < 0:
            return

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT staging.fail_checkpoint(%s, %s, %s, %s)
                    """,
                    (checkpoint_id, error, error_code, records_processed),
                )
                conn.commit()
        finally:
            conn.close()

    def get_resumable_entities(
        self,
        season: int,
        entity_type: str | None = None,
    ) -> list[dict]:
        """Get list of entities that can be resumed from checkpoint.

        Args:
            season: Season to check
            entity_type: Optional filter by entity type

        Returns:
            List of dicts with entity_key, status, progress info
        """
        from baseball.core.db import get_db_connection

        if not self._checkpoints_enabled:
            return []

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM staging.get_resumable_checkpoints(%s, %s, %s)
                    """,
                    (self._get_source_name(), season, entity_type),
                )
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row, strict=False)) for row in cur.fetchall()]
        finally:
            conn.close()

    @abstractmethod
    def download(self, config: SourceRequest) -> SourceResult:
        """Download data from source to local storage.

        Args:
            config: Source request configuration

        Returns:
            Source result with download status
        """

    @abstractmethod
    def ingest(self, source_path: Path) -> SourceResult:
        """Transform and load to database.

        Args:
            source_path: Path to downloaded source data

        Returns:
            Source result with ingest status
        """

    @abstractmethod
    def validate(self, ingest_result: SourceResult) -> SourceResult:
        """Validate ingested data.

        Args:
            ingest_result: Result from ingest operation

        Returns:
            Source result with validation status
        """
