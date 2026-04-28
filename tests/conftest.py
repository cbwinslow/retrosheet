#!/usr/bin/env python3
"""pytest conftest.py - shared fixtures for the retrosheet test suite."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEST_DB_NAME = os.environ.get("PGDATABASE", "retrosheet_test")
DEFAULT_DB_URL = "postgresql://postgres:postgres@localhost:5432/retrosheet_test"


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def db_available():
    """Check if PostgreSQL is running and accessible."""
    try:
        import psycopg
        conn = psycopg.connect(DEFAULT_DB_URL, connect_timeout=3)
        conn.close()
        return True
    except Exception:
        pytest.skip("PostgreSQL not available on localhost:5432")
        return False


@pytest.fixture(scope="session")
def test_db_connection(db_available):
    """Create a temporary test database and return connection URL."""
    import psycopg

    # Create test database if not exists
    admin_conn = psycopg.connect(
        "postgresql://postgres:postgres@localhost:5432/postgres"
    )
    admin_conn.autocommit = True
    with admin_conn.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
        cur.execute(f"CREATE DATABASE {TEST_DB_NAME}")
    admin_conn.close()

    yield DEFAULT_DB_URL

    # Teardown: drop test database
    admin_conn = psycopg.connect(
        "postgresql://postgres:postgres@localhost:5432/postgres"
    )
    admin_conn.autocommit = True
    with admin_conn.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
    admin_conn.close()


@pytest.fixture
def mock_db_connection():
    """Return a mock DB connection for unit tests (no real DB)."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
    return mock_conn


# ---------------------------------------------------------------------------
# File system fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def temp_dir():
    """Create a temporary directory for test artifacts."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def sample_data_dir(temp_dir):
    """Create sample data files for testing."""
    data_dir = temp_dir / "data"
    data_dir.mkdir()
    # Create minimal test files
    (data_dir / "test.csv").write_text("a,b,c\n1,2,3\n4,5,6")
    return data_dir


# ---------------------------------------------------------------------------
# Project structure fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def sql_files(project_root):
    """List all SQL files in the sql/ directory."""
    return sorted(Path(project_root / "sql").rglob("*.sql"))


@pytest.fixture
def script_files(project_root):
    """List all executable Python scripts in scripts/."""
    return sorted(
        f
        for f in Path(project_root / "scripts").rglob("*.py")
        if f.is_file() and f.name != "__init__.py"
    )


# ---------------------------------------------------------------------------
# Baseball-specific fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_game_state():
    """Return a sample game state dict for feature testing."""
    return {
        "inning": 7,
        "inning_top": False,  # home team batting
        "outs": 1,
        "balls": 2,
        "strikes": 1,
        "home_score": 5,
        "away_score": 4,
        "on_1b": 1001,  # hypothetical player IDs
        "on_2b": 1002,
        "on_3b": 1003,
        "season": 2024,
    }


@pytest.fixture
def sample_we_matrix():
    """Return a small win expectancy matrix for testing."""
    import numpy as np

    # 3x3x3x2x2x8 (inning 1-9, top/bot, outs 0-2, balls 0-2, strikes 0-2)
    matrix = np.random.rand(9, 2, 3, 3, 3)
    return matrix


# ---------------------------------------------------------------------------
# Command execution fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def run_command():
    """Fixture for running shell commands with error handling."""

    def _run(cmd: str, cwd: Path = PROJECT_ROOT, check: bool = True):
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True
        )
        if check and result.returncode != 0:
            pytest.fail(f"Command failed: {cmd}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
        return result

    return _run


# ---------------------------------------------------------------------------
# Performance benchmark fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def benchmark_logger():
    """Simple benchmark logger to replace pytest-benchmark."""
    import time

    class BenchmarkLogger:
        def __init__(self):
            self.timings = {}

        def start(self, name: str):
            self.timings[name] = {"start": time.perf_counter()}

        def end(self, name: str):
            self.timings[name]["end"] = time.perf_counter()
            elapsed = self.timings[name]["end"] - self.timings[name]["start"]
            print(f"[BENCH] {name}: {elapsed:.4f}s")
            return elapsed

    return BenchmarkLogger()
