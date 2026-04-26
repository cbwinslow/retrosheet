"""Bridge Population Orchestrator.

Central controller for bridge table population with checkpointing,
validation, and error recovery.
"""

from __future__ import annotations

import json
import logging
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2

from mlb_predict.orchestration.error_handling import (
    DatabaseOperation,
    OperationResult,
    RetryConfig,
    db_circuit_breaker,
)
from mlb_predict.orchestration.validation import validate_chadwick_staging


logger = logging.getLogger(__name__)


@dataclass
class Checkpoint:
    """Checkpoint for resumable operations."""
    stage: str
    timestamp: datetime
    completed_steps: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    validation_results: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'stage': self.stage,
            'timestamp': self.timestamp.isoformat(),
            'completed_steps': self.completed_steps,
            'metadata': self.metadata,
            'validation_results': self.validation_results,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Checkpoint:
        return cls(
            stage=data['stage'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            completed_steps=data['completed_steps'],
            metadata=data.get('metadata', {}),
            validation_results=data.get('validation_results'),
        )


@dataclass
class StageResult:
    """Result of a pipeline stage."""
    stage: str
    success: bool
    duration_seconds: float
    records_processed: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    operation_result: OperationResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'stage': self.stage,
            'success': self.success,
            'duration_seconds': self.duration_seconds,
            'records_processed': self.records_processed,
            'errors': self.errors,
            'warnings': self.warnings,
            'operation_result': self.operation_result.__dict__ if self.operation_result else None,
        }


class CheckpointManager:
    """Manages checkpoints for resumable operations."""

    def __init__(self, checkpoint_dir: Path | None = None):
        self.checkpoint_dir = checkpoint_dir or Path(tempfile.gettempdir()) / 'bridge_checkpoints'
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, operation_id: str, checkpoint: Checkpoint) -> Path:
        """Save checkpoint to disk."""
        checkpoint_file = self.checkpoint_dir / f'{operation_id}.json'
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint.to_dict(), f, indent=2)
        logger.info(f'Checkpoint saved: {checkpoint_file}')
        return checkpoint_file

    def load_checkpoint(self, operation_id: str) -> Checkpoint | None:
        """Load checkpoint from disk if exists."""
        checkpoint_file = self.checkpoint_dir / f'{operation_id}.json'
        if not checkpoint_file.exists():
            return None

        with open(checkpoint_file) as f:
            data = json.load(f)

        return Checkpoint.from_dict(data)

    def clear_checkpoint(self, operation_id: str) -> None:
        """Clear checkpoint after successful completion."""
        checkpoint_file = self.checkpoint_dir / f'{operation_id}.json'
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info(f'Checkpoint cleared: {checkpoint_file}')


class BridgeOrchestrator:
    """Orchestrates bridge table population with full error handling.
    
    Usage:
        orch = BridgeOrchestrator(db_url="postgresql://localhost/retrosheet")
        result = orch.run_chadwick_ingestion()
    """

    def __init__(
        self,
        db_url: str | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        enable_checkpoints: bool = True,
    ):
        self.db_url = db_url
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.enable_checkpoints = enable_checkpoints
        self.db_operation = DatabaseOperation(
            'bridge_operation',
            retry_config=RetryConfig(
                max_retries=3,
                base_delay=2.0,
                retryable_exceptions=(
                    psycopg2.OperationalError,
                    psycopg2.InterfaceError,
                    psycopg2.DatabaseError,
                ),
            ),
            breaker=db_circuit_breaker,
        )
        self.stage_results: list[StageResult] = []

    def _get_connection(self) -> psycopg2.extensions.connection:
        """Get database connection."""
        if self.db_url:
            return psycopg2.connect(self.db_url)

        # Use environment variables
        import os
        return psycopg2.connect(
            host=os.getenv('PGHOST', 'localhost'),
            port=os.getenv('PGPORT', '5432'),
            database=os.getenv('PGDATABASE', 'retrosheet'),
            user=os.getenv('PGUSER', 'postgres'),
            password=os.getenv('PGPASSWORD', ''),
        )

    def _execute_sql_file(self, conn: psycopg2.extensions.connection, file_path: Path) -> OperationResult:
        """Execute SQL file with error handling."""
        def operation(conn):
            with open(file_path) as f:
                sql = f.read()

            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            return {'file': str(file_path), 'executed': True}

        return self.db_operation.execute(conn, operation)

    def _run_with_checkpoint(
        self,
        operation_id: str,
        stage_name: str,
        func: Callable[[psycopg2.extensions.connection], Any],
        conn: psycopg2.extensions.connection,
    ) -> StageResult:
        """Run a stage with checkpointing."""
        start_time = datetime.now()

        # Check if already completed
        if self.enable_checkpoints:
            checkpoint = self.checkpoint_manager.load_checkpoint(operation_id)
            if checkpoint and stage_name in checkpoint.completed_steps:
                logger.info(f"Stage '{stage_name}' already completed, skipping")
                return StageResult(
                    stage=stage_name,
                    success=True,
                    duration_seconds=0,
                    metadata={'skipped': True, 'reason': 'already_completed'},
                )

        # Execute the operation
        result = self.db_operation.execute(conn, func)

        duration = (datetime.now() - start_time).total_seconds()

        stage_result = StageResult(
            stage=stage_name,
            success=result.success,
            duration_seconds=duration,
            operation_result=result,
            errors=[str(result.error)] if result.error else [],
        )

        # Save checkpoint on success
        if result.success and self.enable_checkpoints:
            checkpoint = checkpoint or Checkpoint(
                stage=operation_id,
                timestamp=datetime.now(),
                completed_steps=[stage_name],
            )
            if stage_name not in checkpoint.completed_steps:
                checkpoint.completed_steps.append(stage_name)
            self.checkpoint_manager.save_checkpoint(operation_id, checkpoint)

        return stage_result

    def run_chadwick_ingestion(
        self,
        skip_download: bool = False,
        skip_validation: bool = False,
        operation_id: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Run complete Chadwick Register ingestion pipeline.
        
        Args:
            skip_download: Skip download if files already exist
            skip_validation: Skip validation tests
            operation_id: Unique ID for checkpointing/resuming
            dry_run: If True, simulate all operations without committing changes
            
        Returns:
            Complete result dictionary with all stage results
        """
        operation_id = operation_id or f"chadwick_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        results = {
            'operation_id': operation_id,
            'start_time': datetime.now().isoformat(),
            'stages': [],
            'success': False,
            'dry_run': dry_run,
        }

        conn = self._get_connection()

        try:
            # Stage 1: Create SQL Procedures
            stage1 = self._run_with_checkpoint(
                operation_id,
                'create_procedures',
                self._stage_create_procedures,
                conn,
            )
            results['stages'].append(stage1.to_dict())

            if not stage1.success:
                results['error'] = 'Failed to create SQL procedures'
                return results

            # Stage 2: Download and Load Data
            stage2 = self._run_with_checkpoint(
                operation_id,
                'download_and_load',
                lambda c: self._stage_download_and_load(c, skip_download),
                conn,
            )
            results['stages'].append(stage2.to_dict())

            if not stage2.success:
                results['error'] = 'Failed to download and load Chadwick data'
                return results

            # Stage 3: Validation (pre-upsert)
            if not skip_validation:
                validation_report = validate_chadwick_staging(conn)
                results['validation'] = validation_report.to_dict()

                if not validation_report.passed:
                    results['error'] = 'Validation failed'
                    results['success'] = False
                    return results

            # Stage 4: Upsert to player_xref
            stage4 = self._run_with_checkpoint(
                operation_id,
                'upsert_player_xref',
                lambda c: self._stage_upsert_player_xref(c, dry_run=dry_run),
                conn,
            )
            results['stages'].append(stage4.to_dict())

            if not stage4.success:
                results['error'] = 'Failed to upsert to player_xref'
                return results

            # Stage 5: Validation (post-upsert)
            if not skip_validation:
                stage5 = self._run_with_checkpoint(
                    operation_id,
                    'post_validation',
                    self._stage_post_validation,
                    conn,
                )
                results['stages'].append(stage5.to_dict())

            # Success!
            results['success'] = True
            results['end_time'] = datetime.now().isoformat()

            # Clear checkpoints on success
            if self.enable_checkpoints:
                self.checkpoint_manager.clear_checkpoint(operation_id)

            return results

        except Exception as e:
            results['error'] = f'Unexpected error: {e}'
            logger.exception('Chadwick ingestion failed')
            return results

        finally:
            conn.close()

    def _stage_create_procedures(self, conn: psycopg2.extensions.connection) -> dict[str, Any]:
        """Create SQL procedures."""
        from pathlib import Path

        sql_dir = Path(__file__).parents[3] / 'sql' / 'bridge'
        sql_files = [
            '930_chadwick_register_bridge.sql',
            '931_lahman_bridge_population.sql',
            '940_bridge_validation_tests.sql',
        ]

        executed = []
        for sql_file in sql_files:
            file_path = sql_dir / sql_file
            if file_path.exists():
                result = self._execute_sql_file(conn, file_path)
                if not result.success:
                    raise result.error or Exception(f'Failed to execute {sql_file}')
                executed.append(sql_file)

        return {'files_executed': executed}

    def _stage_download_and_load(
        self,
        conn: psycopg2.extensions.connection,
        skip_download: bool,
    ) -> dict[str, Any]:
        """Download and load Chadwick data."""
        import sys
        from pathlib import Path

        # Import the ingestion script
        scripts_dir = Path(__file__).parents[3] / 'scripts' / 'bridge'
        sys.path.insert(0, str(scripts_dir))

        from ingest_chadwick_register import (
            download_chadwick_files,
            load_to_staging,
        )

        # Download files
        if not skip_download:
            files = download_chadwick_files()
        else:
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            files = list(temp_dir.glob('chadwick_register_*.csv'))

        if not files:
            raise Exception('No Chadwick files to process')

        # Load to staging
        total_records = load_to_staging(conn, files, dry_run=False)

        return {
            'files_downloaded': len(files),
            'records_loaded': total_records,
        }

    def _stage_upsert_player_xref(
        self,
        conn: psycopg2.extensions.connection,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Run upsert procedure."""
        if dry_run:
            # In dry-run mode, just count what would be affected
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE NULLIF(cr.key_retro, '') IS NOT NULL
                            AND NULLIF(cr.key_retro, '') NOT IN (
                                SELECT retrosheet_id FROM bridge.player_xref WHERE retrosheet_id IS NOT NULL
                            )) as new_records,
                        COUNT(*) FILTER (WHERE NULLIF(cr.key_retro, '') IS NOT NULL
                            AND NULLIF(cr.key_retro, '') IN (
                                SELECT retrosheet_id FROM bridge.player_xref WHERE retrosheet_id IS NOT NULL
                            )) as update_records
                    FROM bridge._staging_chadwick_register cr
                """)
                row = cur.fetchone()
                new_records = row[0] if row else 0
                update_records = row[1] if row else 0

            return {
                'dry_run': True,
                'new_records': new_records,
                'update_records': update_records,
                'total_player_xref_records': None,  # Would be populated after actual upsert
            }

        # Real execution
        with conn.cursor() as cur:
            cur.execute('CALL bridge.upsert_chadwick_to_player_xref()')
        conn.commit()

        # Get stats
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM bridge.player_xref')
            total_records = cur.fetchone()[0]

        return {'total_player_xref_records': total_records}

    def _stage_post_validation(self, conn: psycopg2.extensions.connection) -> dict[str, Any]:
        """Run post-upsert validation."""
        import sys
        from pathlib import Path

        scripts_dir = Path(__file__).parents[3] / 'scripts' / 'bridge'
        sys.path.insert(0, str(scripts_dir))

        from ingest_chadwick_register import run_validation_tests

        results = run_validation_tests(conn)

        return {
            'tests_passed': results['passed'],
            'tests_failed': results['failed'],
            'pass_rate': results['summary']['pass_rate'] if results.get('summary') else 0,
        }
