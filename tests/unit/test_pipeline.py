"""Unit tests for Pipeline Service and CLI commands.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-27
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from baseball.services.pipeline import (
    PipelineConfig,
    PipelineRun,
    PipelineService,
    PipelineStatus,
    StepStatus,
    get_pipeline_service,
)


class TestPipelineConfig:
    """Test pipeline configuration loading."""

    def test_load_config_from_yaml(self, tmp_path):
        """Test loading pipeline config from YAML file."""
        config_file = tmp_path / 'pipelines.yml'
        config_file.write_text("""
pipelines:
  test_pipeline:
    description: "Test pipeline"
    steps:
      - step1
      - step2
    checkpoint_table: "admin.checkpoints"
    parameters:
      - year
""")

        service = PipelineService(config_path=config_file)

        assert 'test_pipeline' in service._pipelines
        config = service.get_pipeline('test_pipeline')
        assert config.name == 'test_pipeline'
        assert config.description == 'Test pipeline'
        assert config.steps == ['step1', 'step2']
        assert config.checkpoint_table == 'admin.checkpoints'
        assert config.parameters == ['year']

    def test_list_pipelines(self, tmp_path):
        """Test listing all pipelines."""
        config_file = tmp_path / 'pipelines.yml'
        config_file.write_text("""
pipelines:
  pipeline_a:
    steps: [step1]
  pipeline_b:
    steps: [step1, step2]
""")

        service = PipelineService(config_path=config_file)
        pipelines = service.list_pipelines()

        assert len(pipelines) == 2
        names = [p.name for p in pipelines]
        assert 'pipeline_a' in names
        assert 'pipeline_b' in names

    def test_get_nonexistent_pipeline(self, tmp_path):
        """Test getting a pipeline that doesn't exist."""
        config_file = tmp_path / 'pipelines.yml'
        config_file.write_text('pipelines: {}\n')

        service = PipelineService(config_path=config_file)
        result = service.get_pipeline('nonexistent')

        assert result is None

    def test_missing_config_file(self, tmp_path):
        """Test behavior when config file is missing."""
        config_file = tmp_path / 'nonexistent.yml'

        service = PipelineService(config_path=config_file)

        assert len(service._pipelines) == 0


class TestPipelineServiceDatabase:
    """Test pipeline service database operations."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database connection."""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        return conn, cursor

    def test_create_run(self, mock_db):
        """Test creating a pipeline run record."""
        conn, cursor = mock_db
        cursor.fetchone.return_value = (42,)  # run_id

        with patch('baseball.services.pipeline.get_db_connection', return_value=conn):
            service = PipelineService(config_path=Path('/dev/null'))
            service._pipelines = {'test': PipelineConfig(name='test', steps=[])}

            run_id = service.create_run('test', {'year': 2024})

            assert run_id == 42
            assert cursor.execute.called

    def test_update_run_status(self, mock_db):
        """Test updating run status."""
        conn, cursor = mock_db

        with patch('baseball.services.pipeline.get_db_connection', return_value=conn):
            service = PipelineService(config_path=Path('/dev/null'))

            service.update_run_status(42, PipelineStatus.COMPLETED)

            assert cursor.execute.called
            assert conn.commit.called

    def test_save_checkpoint(self, mock_db):
        """Test saving checkpoint."""
        conn, cursor = mock_db

        with patch('baseball.services.pipeline.get_db_connection', return_value=conn):
            service = PipelineService(config_path=Path('/dev/null'))

            service.save_checkpoint('pipeline', 42, 'step1', 'completed', {'key': 'value'})

            assert cursor.execute.called
            assert conn.commit.called

    def test_get_last_checkpoint(self, mock_db):
        """Test retrieving last checkpoint."""
        conn, cursor = mock_db
        cursor.fetchone.return_value = ('step1', 'completed')

        with patch('baseball.services.pipeline.get_db_connection', return_value=conn):
            service = PipelineService(config_path=Path('/dev/null'))

            result = service.get_last_checkpoint('pipeline', 42)

            assert result == 'step1'

    def test_get_recent_runs(self, mock_db):
        """Test retrieving recent runs."""
        conn, cursor = mock_db
        cursor.fetchall.return_value = [
            (
                1,
                'pipeline_a',
                'completed',
                datetime(2026, 4, 27, 10, 0, 0),
                datetime(2026, 4, 27, 10, 5, 0),
                '{}',
                None,
            ),
        ]

        with patch('baseball.services.pipeline.get_db_connection', return_value=conn):
            service = PipelineService(config_path=Path('/dev/null'))

            runs = service.get_recent_runs(limit=5)

            assert len(runs) == 1
            assert runs[0].run_id == 1
            assert runs[0].status == PipelineStatus.COMPLETED

    def test_no_database_connection(self):
        """Test graceful handling when database is unavailable."""
        with patch('baseball.services.pipeline.get_db_connection', return_value=None):
            service = PipelineService(config_path=Path('/dev/null'))

            # Should not raise, just return None/empty
            result = service.get_last_checkpoint('pipeline', 42)
            assert result is None

            runs = service.get_recent_runs()
            assert runs == []


class TestPipelineExecution:
    """Test pipeline execution logic."""

    @pytest.fixture
    def service_with_config(self, tmp_path):
        """Create service with test config."""
        config_file = tmp_path / 'pipelines.yml'
        config_file.write_text("""
pipelines:
  test_pipeline:
    steps:
      - download
      - ingest
      - validate
""")
        return PipelineService(config_path=config_file)

    @pytest.fixture
    def mock_db(self):
        """Create mock database connection."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)  # run_id
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        return conn, cursor

    def test_run_pipeline_success(self, service_with_config, mock_db):
        """Test successful pipeline execution."""
        conn, _cursor = mock_db

        with patch('baseball.services.pipeline.get_db_connection', return_value=conn):
            run_id, success, error = service_with_config.run_pipeline(
                'test_pipeline',
                resume=False,
                parameters={'year': 2024},
            )

            assert success is True
            assert error is None
            assert run_id == 1

    def test_run_pipeline_not_found(self, service_with_config):
        """Test running non-existent pipeline."""
        with pytest.raises(ValueError, match='Pipeline not found'):
            service_with_config.run_pipeline('nonexistent')

    def test_run_pipeline_with_resume(self, service_with_config, mock_db):
        """Test pipeline execution with resume flag."""
        conn, cursor = mock_db

        with patch('baseball.services.pipeline.get_db_connection', return_value=conn):
            # Mock checkpoint at 'download' step
            cursor.fetchone.return_value = ('download', 'completed')

            _run_id, success, _error = service_with_config.run_pipeline(
                'test_pipeline',
                resume=True,
            )

            # Should resume from after 'download'
            assert success is True

    def test_execute_step_success(self, service_with_config, mock_db):
        """Test executing individual step."""
        conn, _cursor = mock_db

        with patch('baseball.services.pipeline.get_db_connection', return_value=conn):
            success, error = service_with_config.execute_step(
                'test_pipeline',
                1,
                'download',
                {},
            )

            assert success is True
            assert error is None

    def test_execute_unknown_step(self, service_with_config, mock_db):
        """Test executing unknown step type."""
        conn, _cursor = mock_db

        with patch('baseball.services.pipeline.get_db_connection', return_value=conn):
            # Unknown steps are skipped (return True)
            success, _error = service_with_config.execute_step(
                'test_pipeline',
                1,
                'unknown_step',
                {},
            )

            assert success is True


class TestPipelineDataStructures:
    """Test pipeline data structures."""

    def test_pipeline_status_enum(self):
        """Test PipelineStatus enum values."""
        assert PipelineStatus.PENDING.value == 'pending'
        assert PipelineStatus.RUNNING.value == 'running'
        assert PipelineStatus.COMPLETED.value == 'completed'
        assert PipelineStatus.FAILED.value == 'failed'
        assert PipelineStatus.PARTIAL.value == 'partial'

    def test_step_status_enum(self):
        """Test StepStatus enum values."""
        assert StepStatus.PENDING.value == 'pending'
        assert StepStatus.RUNNING.value == 'running'
        assert StepStatus.COMPLETED.value == 'completed'
        assert StepStatus.FAILED.value == 'failed'
        assert StepStatus.SKIPPED.value == 'skipped'

    def test_pipeline_config_dataclass(self):
        """Test PipelineConfig dataclass."""
        config = PipelineConfig(
            name='test',
            steps=['a', 'b'],
            description='Test description',
        )

        assert config.name == 'test'
        assert config.steps == ['a', 'b']
        assert config.description == 'Test description'
        assert config.checkpoint_table == 'admin.pipeline_checkpoints'
        assert config.poll_interval_seconds is None

    def test_pipeline_run_dataclass(self):
        """Test PipelineRun dataclass."""
        run = PipelineRun(
            run_id=1,
            pipeline_name='test',
            status=PipelineStatus.COMPLETED,
            started_at=datetime.now(),
        )

        assert run.run_id == 1
        assert run.pipeline_name == 'test'
        assert run.status == PipelineStatus.COMPLETED


class TestSingleton:
    """Test pipeline service singleton."""

    def test_get_pipeline_service_singleton(self):
        """Test that get_pipeline_service returns singleton."""
        with patch('baseball.services.pipeline.PipelineService'):
            instance1 = get_pipeline_service()
            instance2 = get_pipeline_service()

            assert instance1 is instance2
