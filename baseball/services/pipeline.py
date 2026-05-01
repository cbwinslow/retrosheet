"""Pipeline execution service for the baseball platform.

Handles pipeline configuration loading, step execution, checkpointing,
and integration with admin.pipeline_runs and admin.pipeline_checkpoints.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-27
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from baseball.core.db import get_db_connection


if TYPE_CHECKING:
    from baseball.sources.base import BaseSource


logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    """Pipeline execution status."""

    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    PARTIAL = 'partial'


class StepStatus(Enum):
    """Individual step execution status."""

    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    SKIPPED = 'skipped'


@dataclass
class PipelineStep:
    """A single pipeline step."""

    name: str
    status: StepStatus = StepStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    result: dict = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Pipeline configuration loaded from YAML."""

    name: str
    steps: list[str]
    description: str = ''
    checkpoint_table: str = 'admin.pipeline_checkpoints'
    poll_interval_seconds: int | None = None
    parameters: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class PipelineRun:
    """A pipeline execution instance."""

    run_id: int
    pipeline_name: str
    status: PipelineStatus
    started_at: datetime
    completed_at: datetime | None = None
    steps: list[PipelineStep] = field(default_factory=list)
    parameters: dict = field(default_factory=dict)
    error_message: str | None = None


class PipelineService:
    """Service for executing and managing pipelines."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize pipeline service.

        Args:
            config_path: Path to pipelines.yml config file
        """
        self.config_path = (
            config_path or Path(__file__).parent.parent.parent / 'config' / 'pipelines.yml'
        )
        self._pipelines: dict[str, PipelineConfig] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load pipeline configurations from YAML."""
        if not self.config_path.exists():
            logger.warning(f'Pipeline config not found: {self.config_path}')
            return

        with open(self.config_path) as f:
            data = yaml.safe_load(f)

        if not data or 'pipelines' not in data:
            logger.warning('No pipelines defined in config')
            return

        for name, config in data['pipelines'].items():
            self._pipelines[name] = PipelineConfig(
                name=name,
                steps=config.get('steps', []),
                description=config.get('description', ''),
                checkpoint_table=config.get('checkpoint_table', 'admin.pipeline_checkpoints'),
                poll_interval_seconds=config.get('poll_interval_seconds'),
                parameters=config.get('parameters', []),
                metadata=config.get('metadata', {}),
            )

        logger.info(f'Loaded {len(self._pipelines)} pipeline configs')

    def list_pipelines(self) -> list[PipelineConfig]:
        """Return list of available pipeline configurations."""
        return list(self._pipelines.values())

    def get_pipeline(self, name: str) -> PipelineConfig | None:
        """Get pipeline config by name."""
        return self._pipelines.get(name)

    def get_last_checkpoint(self, pipeline_name: str, run_id: int) -> str | None:
        """Get the last completed step from checkpoint table.

        Args:
            pipeline_name: Name of the pipeline
            run_id: Pipeline run ID

        Returns:
            Name of last completed step, or None if no checkpoint
        """
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT step_name, status
                    FROM admin.pipeline_checkpoints
                    WHERE pipeline_name = %s AND run_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (pipeline_name, run_id),
                )
                row = cur.fetchone()
                if row and row[1] == 'completed':
                    return row[0]
        except Exception as e:
            logger.warning(f'Could not load checkpoint: {e}')

        return None

    def save_checkpoint(
        self,
        pipeline_name: str,
        run_id: int,
        step_name: str,
        status: str,
        metadata: dict | None = None,
    ) -> None:
        """Save checkpoint to database.

        Args:
            pipeline_name: Name of the pipeline
            run_id: Pipeline run ID
            step_name: Name of the step
            status: Step status (pending, running, completed, failed)
            metadata: Optional step metadata
        """
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO admin.pipeline_checkpoints
                        (pipeline_name, run_id, step_name, status, metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        pipeline_name,
                        run_id,
                        step_name,
                        status,
                        json.dumps(metadata) if metadata else None,
                    ),
                )
                conn.commit()
                logger.debug(f'Checkpoint saved: {pipeline_name}/{step_name} = {status}')
        except Exception as e:
            logger.warning(f'Could not save checkpoint: {e}')

    def create_run(
        self,
        pipeline_name: str,
        parameters: dict | None = None,
    ) -> int:
        """Create a new pipeline run record.

        Args:
            pipeline_name: Name of the pipeline
            parameters: Optional run parameters

        Returns:
            Run ID
        """
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO admin.pipeline_runs
                        (pipeline_name, status, started_at, parameters)
                    VALUES (%s, %s, NOW(), %s)
                    RETURNING run_id
                    """,
                    (
                        pipeline_name,
                        PipelineStatus.RUNNING.value,
                        json.dumps(parameters) if parameters else None,
                    ),
                )
                run_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f'Created pipeline run: {run_id} for {pipeline_name}')
                return run_id
        except Exception as e:
            logger.exception(f'Could not create pipeline run: {e}')
            raise

    def update_run_status(
        self,
        run_id: int,
        status: PipelineStatus,
        error_message: str | None = None,
    ) -> None:
        """Update pipeline run status.

        Args:
            run_id: Pipeline run ID
            status: New status
            error_message: Optional error message
        """
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                if status in (
                    PipelineStatus.COMPLETED,
                    PipelineStatus.FAILED,
                    PipelineStatus.PARTIAL,
                ):
                    cur.execute(
                        """
                        UPDATE admin.pipeline_runs
                        SET status = %s, completed_at = NOW(), error_message = %s
                        WHERE run_id = %s
                        """,
                        (status.value, error_message, run_id),
                    )
                else:
                    cur.execute(
                        'UPDATE admin.pipeline_runs SET status = %s WHERE run_id = %s',
                        (status.value, run_id),
                    )
                conn.commit()
                logger.info(f'Updated run {run_id} status: {status.value}')
        except Exception as e:
            logger.warning(f'Could not update run status: {e}')

    def get_run_status(self, run_id: int) -> PipelineRun | None:
        """Get pipeline run status by ID.

        Args:
            run_id: Pipeline run ID

        Returns:
            PipelineRun if found, None otherwise
        """
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT run_id, pipeline_name, status, started_at, completed_at, parameters, error_message
                    FROM admin.pipeline_runs
                    WHERE run_id = %s
                    """,
                    (run_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None

                return PipelineRun(
                    run_id=row[0],
                    pipeline_name=row[1],
                    status=PipelineStatus(row[2]),
                    started_at=row[3],
                    completed_at=row[4],
                    parameters=json.loads(row[5]) if row[5] else {},
                    error_message=row[6],
                )
        except Exception as e:
            logger.warning(f'Could not get run status: {e}')
            return None

    def get_recent_runs(
        self,
        pipeline_name: str | None = None,
        limit: int = 10,
    ) -> list[PipelineRun]:
        """Get recent pipeline runs.

        Args:
            pipeline_name: Optional filter by pipeline name
            limit: Maximum number of runs to return

        Returns:
            List of PipelineRun objects
        """
        runs = []
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                if pipeline_name:
                    cur.execute(
                        """
                        SELECT run_id, pipeline_name, status, started_at, completed_at, parameters, error_message
                        FROM admin.pipeline_runs
                        WHERE pipeline_name = %s
                        ORDER BY started_at DESC
                        LIMIT %s
                        """,
                        (pipeline_name, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT run_id, pipeline_name, status, started_at, completed_at, parameters, error_message
                        FROM admin.pipeline_runs
                        ORDER BY started_at DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )

                for row in cur.fetchall():
                    runs.append(
                        PipelineRun(
                            run_id=row[0],
                            pipeline_name=row[1],
                            status=PipelineStatus(row[2]),
                            started_at=row[3],
                            completed_at=row[4],
                            parameters=json.loads(row[5]) if row[5] else {},
                            error_message=row[6],
                        ),
                    )
        except Exception as e:
            logger.warning(f'Could not get recent runs: {e}')

        return runs

    def execute_step(
        self,
        pipeline_name: str,
        run_id: int,
        step_name: str,
        parameters: dict | None = None,
    ) -> tuple[bool, str | None]:
        """Execute a single pipeline step.

        This is a placeholder that routes to appropriate source adapters
        based on step name. In production, this would call actual ingestion
        or feature building code.

        Args:
            pipeline_name: Name of the pipeline
            run_id: Pipeline run ID
            step_name: Name of the step to execute
            parameters: Optional step parameters

        Returns:
            Tuple of (success, error_message)
        """
        logger.info(f'Executing step: {step_name} for {pipeline_name}')

        # Map step names to functions (placeholder implementation)
        step_handlers = {
            'download': self._handle_download,
            'ingest': self._handle_ingest,
            'validate': self._handle_validate,
            'predict': self._handle_predict,
            'run_expectancy': self._handle_feature_build,
            'win_expectancy': self._handle_feature_build,
            'leverage_index': self._handle_feature_build,
            'matchup_features': self._handle_feature_build,
            'rolling_form': self._handle_feature_build,
        }

        handler = step_handlers.get(step_name)
        if not handler:
            logger.warning(f'No handler for step: {step_name}')
            return True, None  # Skip unknown steps

        try:
            self.save_checkpoint(pipeline_name, run_id, step_name, 'running', parameters)
            success = handler(pipeline_name, run_id, step_name, parameters)

            if success:
                self.save_checkpoint(pipeline_name, run_id, step_name, 'completed', parameters)
                return True, None
            error = f'Step {step_name} returned failure'
            self.save_checkpoint(pipeline_name, run_id, step_name, 'failed', {'error': error})
            return False, error

        except Exception as e:
            error = str(e)
            logger.exception(f'Step {step_name} failed: {e}')
            self.save_checkpoint(pipeline_name, run_id, step_name, 'failed', {'error': error})
            return False, error

    def _get_source_adapter(self, source_name: str) -> 'BaseSource | None':
        """Get source adapter by name.

        Args:
            source_name: Name of the source (mlb, retrosheet, statcast, espn, lahman)

        Returns:
            Source adapter instance or None
        """
        from baseball.sources.espn import EspnSource
        from baseball.sources.lahman import LahmanSource
        from baseball.sources.mlb import MlbSource
        from baseball.sources.retrosheet import RetrosheetSource
        from baseball.sources.statcast import StatcastSource

        adapter_map = {
            'mlb': MlbSource,
            'mlb_live': MlbSource,
            'retrosheet': RetrosheetSource,
            'statcast': StatcastSource,
            'espn': EspnSource,
            'lahman': LahmanSource,
        }

        adapter_class = adapter_map.get(source_name)
        if adapter_class:
            return adapter_class()
        return None

    def _extract_source_from_step(self, step_name: str) -> tuple[str | None, str]:
        """Extract source name and operation from step name.

        Args:
            step_name: Pipeline step name (e.g., 'mlb_live_download', 'download')

        Returns:
            Tuple of (source_name, operation)
        """
        # Map compound step names to source + operation
        step_mappings = {
            # MLB steps
            'mlb_live_download': ('mlb', 'download'),
            'mlb_live_ingest': ('mlb', 'ingest'),
            # Retrosheet steps
            'retrosheet_download': ('retrosheet', 'download'),
            'retrosheet_ingest': ('retrosheet', 'ingest'),
            # Statcast steps
            'statcast_download': ('statcast', 'download'),
            'statcast_ingest': ('statcast', 'ingest'),
            # ESPN steps
            'espn_download': ('espn', 'download'),
            'espn_ingest': ('espn', 'ingest'),
            # Lahman steps
            'lahman_download': ('lahman', 'download'),
            'lahman_ingest': ('lahman', 'ingest'),
            # Generic steps (source determined from pipeline context)
            'download': (None, 'download'),
            'ingest': (None, 'ingest'),
            'validate': (None, 'validate'),
            'predict': (None, 'predict'),
        }

        if step_name in step_mappings:
            return step_mappings[step_name]

        # Try to parse from step name pattern: {source}_{operation}
        parts = step_name.rsplit('_', 1)
        if len(parts) == 2 and parts[1] in ('download', 'ingest', 'validate'):
            return (parts[0], parts[1])

        return (None, step_name)

    # Step handlers that call actual source adapters
    def _handle_download(self, pipeline: str, run_id: int, step: str, params: dict | None) -> bool:
        """Handle download step by calling source adapter."""
        logger.info(f'Download step: {step} for pipeline {pipeline}')

        source_name, _ = self._extract_source_from_step(step)

        # Try to infer source from pipeline name if not in step
        if source_name is None:
            if 'retrosheet' in pipeline:
                source_name = 'retrosheet'
            elif 'mlb' in pipeline or 'live' in pipeline:
                source_name = 'mlb'
            elif 'statcast' in pipeline:
                source_name = 'statcast'
            elif 'espn' in pipeline:
                source_name = 'espn'
            elif 'lahman' in pipeline:
                source_name = 'lahman'

        if not source_name:
            logger.warning(f'Could not determine source for download step: {step}')
            return True  # Skip if can't determine source

        adapter = self._get_source_adapter(source_name)
        if not adapter:
            logger.warning(f'No adapter found for source: {source_name}')
            return True  # Skip if no adapter

        try:
            # Build download parameters
            download_params = {}
            if params:
                if 'year' in params:
                    download_params['season'] = params['year']
                if 'date' in params:
                    download_params['date'] = params['date']
                if 'start_date' in params:
                    download_params['start_date'] = params['start_date']
                if 'end_date' in params:
                    download_params['end_date'] = params['end_date']

            # Call the download method
            if source_name == 'retrosheet':
                result = adapter.download(**download_params)
            elif source_name == 'mlb':
                from baseball.core.types import SourceRequest
                request = SourceRequest(
                    source_type='mlb',
                    params=download_params,
                )
                result = adapter.download(request)
            else:
                result = adapter.download(**download_params)

            logger.info(f'Download completed: {result}')
            return True

        except Exception as e:
            logger.exception(f'Download failed for {source_name}: {e}')
            return False

    def _handle_ingest(self, pipeline: str, run_id: int, step: str, params: dict | None) -> bool:
        """Handle ingest step by calling source adapter."""
        logger.info(f'Ingest step: {step} for pipeline {pipeline}')

        source_name, _ = self._extract_source_from_step(step)

        # Try to infer source from pipeline name if not in step
        if source_name is None:
            if 'retrosheet' in pipeline:
                source_name = 'retrosheet'
            elif 'mlb' in pipeline or 'live' in pipeline:
                source_name = 'mlb'
            elif 'statcast' in pipeline:
                source_name = 'statcast'
            elif 'espn' in pipeline:
                source_name = 'espn'
            elif 'lahman' in pipeline:
                source_name = 'lahman'

        if not source_name:
            logger.warning(f'Could not determine source for ingest step: {step}')
            return True

        adapter = self._get_source_adapter(source_name)
        if not adapter:
            logger.warning(f'No adapter found for source: {source_name}')
            return True

        try:
            # Build ingest parameters
            ingest_params = {}
            if params:
                if 'year' in params:
                    ingest_params['season'] = params['year']
                if 'date' in params:
                    ingest_params['date'] = params['date']

            # Call the ingest method
            result = adapter.ingest(**ingest_params)

            logger.info(f'Ingest completed: {result}')
            return True

        except Exception as e:
            logger.exception(f'Ingest failed for {source_name}: {e}')
            return False

    def _handle_validate(self, pipeline: str, run_id: int, step: str, params: dict | None) -> bool:
        """Handle validate step by calling source adapter."""
        logger.info(f'Validate step: {step} for pipeline {pipeline}')

        source_name, _ = self._extract_source_from_step(step)

        # Try to infer source from pipeline name
        if source_name is None:
            if 'retrosheet' in pipeline:
                source_name = 'retrosheet'
            elif 'mlb' in pipeline or 'live' in pipeline:
                source_name = 'mlb'
            elif 'statcast' in pipeline:
                source_name = 'statcast'
            elif 'espn' in pipeline:
                source_name = 'espn'
            elif 'lahman' in pipeline:
                source_name = 'lahman'

        if not source_name:
            logger.warning(f'Could not determine source for validate step: {step}')
            return True

        adapter = self._get_source_adapter(source_name)
        if not adapter:
            logger.warning(f'No adapter found for source: {source_name}')
            return True

        try:
            result = adapter.validate()
            logger.info(f'Validation completed: {result}')
            return result.success if hasattr(result, 'success') else True

        except Exception as e:
            logger.exception(f'Validation failed for {source_name}: {e}')
            return False

    def _handle_predict(self, pipeline: str, run_id: int, step: str, params: dict | None) -> bool:
        """Handle predict step - placeholder for model inference."""
        logger.info(f'Predict step: {step} for pipeline {pipeline}')

        # TODO: Implement actual prediction logic using ModelServer
        # This would call the model serving layer to generate predictions

        logger.info('Prediction step completed (placeholder)')
        return True

    def _handle_feature_build(
        self, pipeline: str, run_id: int, step: str, params: dict | None,
    ) -> bool:
        """Handle feature building step."""
        logger.info(f'Feature build step: {step} for pipeline {pipeline}')

        # Map step names to feature calculators
        feature_map = {
            'run_expectancy': 'RunExpectancyCalculator',
            'win_expectancy': 'WinExpectancyCalculator',
            'leverage_index': 'LeverageIndexCalculator',
            'matchup_features': 'MatchupCalculator',
            'rolling_form': 'RollingFormCalculator',
            'refresh_features': 'all',
            'build_features': 'all',
            'compute_features': 'all',
        }

        calculator_name = feature_map.get(step, step)

        try:
            if calculator_name == 'all' or step in ('refresh_features', 'build_features', 'compute_features'):
                # Build all features
                logger.info('Building all features (placeholder - would call feature calculators)')
                # TODO: Call feature calculator registry to build all features
            else:
                # Build specific feature
                logger.info(f'Building feature: {calculator_name} (placeholder)')
                # TODO: Call specific feature calculator

            return True

        except Exception as e:
            logger.exception(f'Feature build failed for {step}: {e}')
            return False

    def run_pipeline(
        self,
        pipeline_name: str,
        resume: bool = False,
        parameters: dict | None = None,
    ) -> tuple[int, bool, str | None]:
        """Run a complete pipeline.

        Args:
            pipeline_name: Name of the pipeline to run
            resume: Whether to resume from last checkpoint
            parameters: Optional run parameters

        Returns:
            Tuple of (run_id, success, error_message)
        """
        config = self.get_pipeline(pipeline_name)
        if not config:
            msg = f'Pipeline not found: {pipeline_name}'
            raise ValueError(msg)

        # Create run record
        run_id = self.create_run(pipeline_name, parameters)

        try:
            # Determine starting step
            start_index = 0
            if resume:
                last_step = self.get_last_checkpoint(pipeline_name, run_id)
                if last_step and last_step in config.steps:
                    start_index = config.steps.index(last_step) + 1
                    logger.info(f'Resuming from step {last_step} (index {start_index})')

            # Execute steps
            for i, step_name in enumerate(config.steps[start_index:], start=start_index):
                logger.info(f'Step {i + 1}/{len(config.steps)}: {step_name}')
                success, error = self.execute_step(
                    pipeline_name,
                    run_id,
                    step_name,
                    parameters,
                )

                if not success:
                    self.update_run_status(run_id, PipelineStatus.PARTIAL, error)
                    return run_id, False, error

            # Mark complete
            self.update_run_status(run_id, PipelineStatus.COMPLETED)
            return run_id, True, None

        except Exception as e:
            error = str(e)
            logger.exception(f'Pipeline {pipeline_name} failed: {e}')
            self.update_run_status(run_id, PipelineStatus.FAILED, error)
            return run_id, False, error


# Singleton instance
_pipeline_service: PipelineService | None = None


def get_pipeline_service() -> PipelineService:
    """Get or create pipeline service singleton."""
    global _pipeline_service
    if _pipeline_service is None:
        _pipeline_service = PipelineService()
    return _pipeline_service
