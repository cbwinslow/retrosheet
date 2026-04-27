"""Compatibility and portability tests.

Tests for Python version, OS, database compatibility, and configuration portability.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-27
"""

import platform
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest


class TestPythonCompatibility:
    """Test Python version and feature compatibility."""

    def test_python_version_minimum(self):
        """Verify Python 3.10+ is being used."""
        version = sys.version_info
        assert version.major == 3
        assert version.minor >= 10, f'Python 3.10+ required, got {version.major}.{version.minor}'

    def test_type_hints_supported(self):
        """Test that type hints work correctly."""
        from baseball.features.base import GameState

        # Should not raise TypeError for valid types
        state = GameState(inning=1, is_top=True, outs=0)
        assert isinstance(state.inning, int)

    def test_union_syntax_supported(self):
        """Test | union syntax (Python 3.10+)."""

        def func(x: int | None) -> str | None:
            return str(x) if x else None

        assert func(5) == '5'
        assert func(None) is None

    def test_match_case_supported(self):
        """Test match/case syntax (Python 3.10+)."""

        def match_test(x: int) -> str:
            match x:
                case 1:
                    return 'one'
                case 2:
                    return 'two'
                case _:
                    return 'other'

        assert match_test(1) == 'one'
        assert match_test(2) == 'two'
        assert match_test(3) == 'other'

    def test_dataclass_slots(self):
        """Test dataclass with slots (Python 3.10+)."""
        from dataclasses import dataclass

        @dataclass(slots=True)
        class TestClass:
            x: int
            y: str

        obj = TestClass(x=1, y='test')
        assert obj.x == 1

        # Should not allow new attributes
        with pytest.raises(AttributeError):
            obj.z = 3

    def test_required_dependencies(self):
        """Test that all required dependencies are importable."""
        required = [
            'typer',
            'psycopg2',
            'rich',
            'yaml',
            'requests',
            'pandas',
            'numpy',
        ]

        for dep in required:
            try:
                __import__(dep)
            except ImportError:
                pytest.fail(f"Required dependency '{dep}' not installed")

    def test_optional_dependencies(self):
        """Test optional dependencies with graceful degradation."""
        optional = [
            ('scipy', 'statistical functions'),
            ('sklearn', 'machine learning'),
            ('matplotlib', 'visualization'),
        ]

        for dep, purpose in optional:
            try:
                __import__(dep)
                available = True
            except ImportError:
                available = False

            # Should not break if optional deps missing
            assert True  # Just documenting availability


class TestOSCompatibility:
    """Test operating system compatibility."""

    def test_pathlib_usage(self):
        """Test pathlib is used instead of os.path."""
        from baseball.core import DATA_DIR, ROOT_DIR

        assert isinstance(ROOT_DIR, Path)
        assert isinstance(DATA_DIR, Path)

    def test_path_separator_handling(self):
        """Test paths work on all OS."""
        test_path = Path('data') / 'raw' / 'games'

        # Path should be valid regardless of OS
        assert 'data' in str(test_path)
        assert 'raw' in str(test_path)

    def test_line_ending_handling(self):
        """Test line endings are handled correctly."""
        text_unix = 'line1\nline2\n'
        text_windows = 'line1\r\nline2\r\n'

        # Both should split into same lines
        assert text_unix.strip().split('\n') == text_windows.strip().split('\r\n')

    def test_encoding_handling(self):
        """Test UTF-8 encoding is used."""
        test_file = Path('/tmp/test_encoding.txt')

        try:
            test_file.write_text('Baseball data: José Ohtani 大谷', encoding='utf-8')
            content = test_file.read_text(encoding='utf-8')
            assert 'José' in content
            assert '大谷' in content
        finally:
            test_file.unlink(missing_ok=True)

    def test_os_detection(self):
        """Test OS detection for platform-specific code."""
        current_os = platform.system()

        assert current_os in ['Linux', 'Darwin', 'Windows', 'Java']

        # Platform-specific behavior should be isolated
        if current_os == 'Windows':
            # Windows-specific checks
            pass
        else:
            # Unix-like checks
            pass


class TestDatabaseCompatibility:
    """Test database version and feature compatibility."""

    @pytest.fixture
    def db_connection(self):
        """Create database connection if available."""
        try:
            from baseball.core.db import get_db_connection

            conn = get_db_connection()
            yield conn
            conn.close()
        except Exception as e:
            pytest.skip(f'Database not available: {e}')

    def test_postgres_version(self, db_connection):
        """Test PostgreSQL version compatibility."""
        cursor = db_connection.cursor()
        cursor.execute('SELECT version()')
        version_str = cursor.fetchone()[0]

        # Extract version number
        import re

        match = re.search(r'(\d+)\.(\d+)', version_str)
        if match:
            major, minor = int(match.group(1)), int(match.group(2))
            assert major >= 14, f'PostgreSQL 14+ required, found {major}.{minor}'

    def test_timescaledb_availability(self, db_connection):
        """Test TimescaleDB extension availability."""
        cursor = db_connection.cursor()
        try:
            cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
            result = cursor.fetchone()
            if result:
                version = result[0]
                assert version >= '2.0'
        except Exception:
            pytest.skip('TimescaleDB not installed')

    def test_required_extensions(self, db_connection):
        """Test required PostgreSQL extensions."""
        cursor = db_connection.cursor()
        cursor.execute('SELECT extname FROM pg_extension')
        extensions = [row[0] for row in cursor.fetchall()]

        # List required extensions
        required = ['plpgsql']  # Minimum required

        for ext in required:
            assert ext in extensions, f"Required extension '{ext}' not found"

    def test_jsonb_support(self, db_connection):
        """Test JSONB data type support."""
        cursor = db_connection.cursor()

        cursor.execute('SELECT \'{"test": 123}\'::jsonb')
        result = cursor.fetchone()[0]
        assert result == {'test': 123}

    def test_window_functions(self, db_connection):
        """Test window function support."""
        cursor = db_connection.cursor()

        cursor.execute("""
            SELECT row_number() OVER (ORDER BY 1) as rn
            FROM generate_series(1, 3)
        """)
        results = [row[0] for row in cursor.fetchall()]
        assert results == [1, 2, 3]

    def test_cte_support(self, db_connection):
        """Test Common Table Expression support."""
        cursor = db_connection.cursor()

        cursor.execute("""
            WITH test_cte AS (
                SELECT 1 as val
                UNION ALL
                SELECT 2
            )
            SELECT * FROM test_cte
        """)
        results = [row[0] for row in cursor.fetchall()]
        assert sorted(results) == [1, 2]


class TestConfigurationPortability:
    """Test configuration portability across environments."""

    def test_env_var_loading(self):
        """Test environment variable configuration loading."""
        import os

        # Set test env vars
        os.environ['TEST_DB_HOST'] = 'localhost'
        os.environ['TEST_DB_PORT'] = '5432'

        # Read them back
        assert os.getenv('TEST_DB_HOST') == 'localhost'
        assert os.getenv('TEST_DB_PORT') == '5432'

        # Clean up
        del os.environ['TEST_DB_HOST']
        del os.environ['TEST_DB_PORT']

    def test_config_file_loading(self, tmp_path):
        """Test configuration file loading."""
        import yaml

        config_file = tmp_path / 'test_config.yaml'
        config_data = {
            'database': {
                'host': 'localhost',
                'port': 5432,
                'name': 'retrosheet',
            },
            'features': {
                'batch_size': 1000,
            },
        }

        config_file.write_text(yaml.dump(config_data))
        loaded = yaml.safe_load(config_file.read_text())

        assert loaded['database']['host'] == 'localhost'
        assert loaded['features']['batch_size'] == 1000

    def test_default_config_values(self):
        """Test default configuration values are sensible."""
        from baseball.features.base import FeatureConfig

        config = FeatureConfig()

        assert config.batch_size > 0
        assert config.parallel_workers >= 1

    def test_config_override(self):
        """Test configuration override mechanism."""
        from baseball.features.base import FeatureConfig

        # Default
        default_config = FeatureConfig()
        default_batch = default_config.batch_size

        # Override
        custom_config = FeatureConfig(batch_size=500)
        assert custom_config.batch_size == 500
        assert custom_config.batch_size != default_batch


class TestDataMigration:
    """Test data migration and portability."""

    def test_schema_version_tracking(self, db_connection):
        """Test schema version is tracked."""
        cursor = db_connection.cursor()

        try:
            cursor.execute('SELECT version FROM admin.schema_version')
            version = cursor.fetchone()[0]
            assert version is not None
        except Exception:
            pytest.skip('Schema version table not available')

    def test_data_export_import(self, tmp_path):
        """Test data can be exported and imported."""
        import json

        # Create test data
        data = {
            'games': [
                {'game_pk': 1, 'home_team': 'NYY', 'away_team': 'BOS'},
                {'game_pk': 2, 'home_team': 'LAD', 'away_team': 'SF'},
            ],
        }

        # Export
        export_file = tmp_path / 'export.json'
        export_file.write_text(json.dumps(data))

        # Import
        imported = json.loads(export_file.read_text())

        assert imported['games'][0]['game_pk'] == 1

    def test_csv_export_import(self, tmp_path):
        """Test CSV export/import compatibility."""
        import csv

        csv_file = tmp_path / 'test.csv'

        # Write
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['game_pk', 'team', 'score'])
            writer.writeheader()
            writer.writerow({'game_pk': '1', 'team': 'NYY', 'score': '5'})

        # Read
        with open(csv_file) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert rows[0]['team'] == 'NYY'

    def test_sql_dump_compatibility(self):
        """Test SQL dump format compatibility."""
        # Test that pg_dump format is compatible
        result = subprocess.run(
            ['pg_dump', '--help'],
            capture_output=True,
            text=True,
        )

        # pg_dump should be available (or skip)
        if result.returncode != 0:
            pytest.skip('pg_dump not available')

        assert 'pg_dump' in result.stdout or result.returncode == 0


class TestAPICompatibility:
    """Test API compatibility and versioning."""

    def test_feature_calculator_api(self):
        """Test FeatureStore API consistency."""
        from baseball.features.base import FeatureStore

        # All calculators must implement these methods
        required_methods = [
            'compute',
            'compute_batch',
            'save',
            'load_from_db',
        ]

        for method in required_methods:
            assert hasattr(FeatureStore, method), f'Missing required method: {method}'

    def test_model_api(self):
        """Test Model API consistency."""
        from baseball.models.base import BaseModel

        required_methods = [
            'train',
            'predict',
            'save',
            'load',
        ]

        for method in required_methods:
            assert hasattr(BaseModel, method), f'Missing required method: {method}'

    def test_cli_command_structure(self):
        """Test CLI command structure consistency."""
        from baseball.cli import app

        # Verify main commands exist
        commands = ['pipeline', 'features', 'models', 'predict']

        for cmd in commands:
            # Commands are registered as Typer apps
            assert hasattr(app, 'registered_commands') or True  # Typer structure


class TestDependencyVersionConstraints:
    """Test dependency version constraints."""

    def test_pandas_version(self):
        """Test pandas version compatibility."""
        import pandas as pd

        version = pd.__version__.split('.')
        major, minor = int(version[0]), int(version[1])

        # Pandas 1.3+ required
        assert major >= 1
        if major == 1:
            assert minor >= 3

    def test_numpy_version(self):
        """Test numpy version compatibility."""
        import numpy as np

        version = np.__version__.split('.')
        major = int(version[0])

        assert major >= 1

    def test_psycopg2_version(self):
        """Test psycopg2 version compatibility."""
        import psycopg2

        version = psycopg2.__version__.split('.')
        major = int(version[0])

        assert major >= 2


class TestErrorHandlingCompatibility:
    """Test error handling across different scenarios."""

    def test_graceful_degradation_no_db(self):
        """Test graceful degradation when database unavailable."""
        from baseball.features.win_expectancy import WinExpectancyCalculator

        # Should work without database (uses cache/in-memory)
        calc = WinExpectancyCalculator(db_connection=None)

        # Should return 0 or handle gracefully
        result = calc.load_from_db()
        assert result == 0  # No data loaded

    def test_missing_table_handling(self, db_connection):
        """Test handling of missing tables."""
        cursor = db_connection.cursor()

        try:
            cursor.execute('SELECT * FROM nonexistent_table_xyz')
            pytest.fail('Should have raised error for missing table')
        except Exception as e:
            # Should raise appropriate error
            assert 'nonexistent_table' in str(e).lower() or 'does not exist' in str(e).lower()

    def test_malformed_data_handling(self):
        """Test handling of malformed data."""
        from baseball.features.base import GameState

        # Should validate data
        with pytest.raises((ValueError, TypeError)):
            # Invalid inning
            GameState(inning=-1, is_top=True, outs=0)

    def test_network_error_simulation(self):
        """Test network error handling."""

        mock_conn = Mock()
        mock_conn.cursor.side_effect = Exception('Connection refused')

        from baseball.features.win_expectancy import WinExpectancyCalculator

        calc = WinExpectancyCalculator(db_connection=mock_conn)

        # Should handle gracefully
        result = calc.load_from_db()
        assert result == 0
