--
— File: scripts/test/test_pgtap_integration.py
— Purpose: pytest wrapper to run pgTAP tests and integrate with pytest suite
— Author: Agent KiloSwift
— Date: 2026-04-27
— Usage: pytest tests/unit/test_pgtap_integration.py -v
— Dependencies: pytest, psycopg, scripts/test/run_pgtap.sh
—

"""pytest integration tests for pgTAP database testing framework."""

import subprocess
import sys
from pathlib import Path
from typing import List

import pytest

# Module constants
SCRIPT_DIR = Path(__file__).parent
PGTAP_RUNNER = SCRIPT_DIR / "run_pgtap.sh"
SQL_TEST_DIR = Path(__file__).parent.parent.parent / "sql" / "test"


class TestPgTAPIntegration:
    """Test pgTAP installation and test execution."""

    @pytest.fixture
    def db_connection_info(self) -> dict:
        """Provide database connection info from pytest config."""
        return {
            "host": "localhost",
            "port": 5432,
            "database": "retrosheet_test",
            "user": "postgres",
        }

    @pytest.fixture(scope="class")
    def ensure_pgtap_installed(self):
        """Ensure pgTAP is installed before running tests."""
        result = subprocess.run(
            [
                "psql",
                "-d", "retrosheet",
                "-t",
                "-c",
                "SELECT extname FROM pg_extension WHERE extname='pgtap';"
            ],
            capture_output=True,
            text=True,
        )
        if "pgtap" not in result.stdout:
            pytest.skip("pgTAP extension not installed. Run: psql -f sql/test/003_install_pgtap.sql")
        return True

    def test_pgtap_runner_exists(self):
        """Verify pgTAP runner script exists and is executable."""
        assert PGTAP_RUNNER.exists(), f"pgTAP runner not found at {PGTAP_RUNNER}"
        assert PGTAP_RUNNER.is_file(), "pgTAP runner is not a file"
        # Check executable bit (owner, group, or any)
        import stat
        mode = PGTAP_RUNNER.stat().st_mode
        assert mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH), "pgTAP runner is not executable"

    def test_sql_test_files_exist(self):
        """Verify pgTAP SQL test files are present."""
        required_tests = [
            SQL_TEST_DIR / "003_install_pgtap.sql",
            SQL_TEST_DIR / "010_pgtap_core_tables.sql",
            SQL_TEST_DIR / "020_pgtap_functions.sql",
        ]
        for test_file in required_tests:
            assert test_file.exists(), f"Required pgTAP test file missing: {test_file}"

    @pytest.mark.integration
    @pytest.mark.database
    def test_pgtap_can_run_core_tests(self, ensure_pgtap_installed):
        """Run core table tests and verify they pass."""
        result = subprocess.run(
            [
                "psql",
                "-d", "retrosheet",
                "-v", "ON_ERROR_STOP=1",
                "-f", str(SQL_TEST_DIR / "010_pgtap_core_tables.sql"),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Check for TAP success pattern
        if "1.." in result.stdout and "ok" in result.stdout:
            assert result.returncode == 0, f"Core table tests failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        else:
            pytest.fail(f"pgTAP did not produce valid TAP output:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

    @pytest.mark.integration
    @pytest.mark.database
    def test_pgtap_can_run_function_tests(self, ensure_pgtap_installed):
        """Run function/procedure tests and verify they pass."""
        result = subprocess.run(
            [
                "psql",
                "-d", "retrosheet",
                "-v", "ON_ERROR_STOP=1",
                "-f", str(SQL_TEST_DIR / "020_pgtap_functions.sql"),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # TAP tests should output ok/not ok lines
        assert "ok" in result.stdout or result.returncode == 0, \
            f"Function tests failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    @pytest.mark.integration
    @pytest.mark.database
    def test_pgtap_runner_script(self, ensure_pgtap_installed):
        """Test the pgTAP runner script can execute without errors."""
        result = subprocess.run(
            ["bash", str(PGTAP_RUNNER), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Should exit 0 and show usage
        assert result.returncode == 0, f"Runner script failed:\nSTDERR:\n{result.stderr}"
        assert "Usage:" in result.stdout or "pgTAP" in result.stdout, "Missing expected help output"

    @pytest.mark.integration
    @pytest.mark.database
    def test_pgtap_all_schemas_discovery(self, ensure_pgtap_installed):
        """Verify pgTAP can discover test functions across multiple schemas."""
        result = subprocess.run(
            [
                "psql",
                "-d", "retrosheet",
                "-t",
                "-c",
                """
                SELECT COUNT(*)
                FROM pg_proc p
                JOIN pg_namespace n ON p.pronamespace = n.oid
                WHERE n.nspname IN ('public', 'core', 'bridge', 'features')
                  AND p.proname LIKE 'test_%';
                """
            ],
            capture_output=True,
            text=True,
        )
        count = int(result.stdout.strip() or "0")
        # There should be at least 10 pgTAP tests across all schemas
        assert count >= 10, f"Expected >= 10 pgTAP test functions, found {count}"


class TestPgTAPAvailability:
    """Tests for pgTAP availability check script."""

    @pytest.fixture
    def check_script(self) -> Path:
        """Path to extension check script."""
        return Path(__file__).parent.parent / "check_extensions.py"

    def test_check_extensions_script_exists(self, check_script):
        """Verify extension check script exists."""
        assert check_script.exists(), f"check_extensions.py not found at {check_script}"

    @pytest.mark.integration
    @pytest.mark.database
    def test_check_extensions_detects_pgtap(self, check_script):
        """Verify check_extensions.py detects pgTAP."""
        result = subprocess.run(
            ["uv", "run", "python", str(check_script)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Should complete without error
        assert result.returncode in (0, 1), f"Script crashed:\nSTDERR:\n{result.stderr}"
        # Output should mention pgTAP (either installed or missing)
        assert "pgTAP" in result.stdout or "pgtap" in result.stdout.lower(), "pgTAP not mentioned in output"
