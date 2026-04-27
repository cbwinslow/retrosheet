"""Pytest configuration and shared fixtures.

Shared fixtures for all test modules.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-27
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def mock_db_connection():
    """Create mock database connection."""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=False)
    return mock_conn, mock_cursor


@pytest.fixture
def sample_game_state_data():
    """Provide sample game state data."""
    return {
        'inning': 5,
        'is_top': True,
        'outs': 1,
        'runner_1b': True,
        'runner_2b': False,
        'runner_3b': True,
        'score_home': 3,
        'score_away': 2,
    }


@pytest.fixture
def sample_we_matrix():
    """Provide sample Win Expectancy matrix data."""
    return {
        (1, True, 0, '000', 0): 0.50,
        (1, True, 1, '000', 0): 0.48,
        (9, False, 2, '000', 0): 0.70,
        (9, False, 2, '111', 0): 0.85,
    }


@pytest.fixture
def sample_li_matrix():
    """Provide sample Leverage Index matrix data."""
    return {
        (1, True, 0, '000', 0): 0.9,
        (5, False, 2, '111', 0): 4.2,
        (9, False, 2, '111', 0): 5.8,
    }


@pytest.fixture(scope='session')
def db_available():
    """Check if database is available."""
    try:
        from baseball.core.db import get_db_connection

        conn = get_db_connection()
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture
def skip_if_no_db(db_available):
    """Skip test if database not available."""
    if not db_available:
        pytest.skip('Database not available')


@pytest.fixture
def benchmark_logger(temp_dir):
    """Create benchmark logger for tests."""
    from baseball.core.benchmark import BenchmarkLogger

    log_file = temp_dir / 'test_benchmark.jsonl'
    logger = BenchmarkLogger(log_file=str(log_file))
    return logger


@pytest.fixture
def project_root():
    """Return project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def sql_files(project_root):
    """Find all SQL files in project."""
    sql_dir = project_root / 'sql'
    if sql_dir.exists():
        return list(sql_dir.rglob('*.sql'))
    return []


@pytest.fixture
def script_files(project_root):
    """Find all script files in project."""
    scripts_dir = project_root / 'scripts'
    if scripts_dir.exists():
        return list(scripts_dir.rglob('*.sh'))
    return []


def pytest_configure(config):
    """Configure pytest."""
    # Add custom markers
    config.addinivalue_line('markers', 'unit: Unit tests (fast, isolated)')
    config.addinivalue_line('markers', 'integration: Integration tests')
    config.addinivalue_line('markers', 'e2e: End-to-end tests')
    config.addinivalue_line('markers', 'slow: Slow tests (>1s)')
    config.addinivalue_line('markers', 'database: Tests requiring database')
    config.addinivalue_line('markers', 'benchmark: Performance benchmarks')


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Add markers based on test location
    for item in items:
        # Mark tests in unit/ directory as unit tests
        if 'unit' in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Mark tests in integration/ directory as integration tests
        if 'integration' in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Mark tests in e2e/ directory as e2e tests
        if 'e2e' in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


def pytest_runtest_setup(item):
    """Setup before each test."""
    # Skip database tests if no database
    if item.get_closest_marker('database'):
        try:
            from baseball.core.db import get_db_connection

            conn = get_db_connection()
            conn.close()
        except Exception:
            pytest.skip('Database not available')
