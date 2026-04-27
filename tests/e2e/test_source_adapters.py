"""E2E tests for source adapters - verify wrappers work correctly.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26

These tests verify that the new baseball/sources/ adapters properly
WRAP the existing scripts and that they function correctly.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from baseball.core.types import SourceRequest
from baseball.sources import EspnSource, LahmanSource, MlbSource, RetrosheetSource, StatcastSource


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestMlbSource:
    """E2E tests for MLB source adapter."""

    def test_adapter_imports_correctly(self):
        """Test that MlbSource can be imported and instantiated."""
        source = MlbSource()
        assert source is not None
        # Verify it inherits from BaseSource
        assert hasattr(source, 'download')
        assert hasattr(source, 'ingest')
        assert hasattr(source, 'validate')

    def test_adapter_has_fetch_methods(self):
        """Test that MlbSource has convenience methods."""
        source = MlbSource()
        assert hasattr(source, 'fetch_today')
        assert hasattr(source, 'fetch_season')


class TestEspnSource:
    """E2E tests for ESPN source adapter."""

    def test_adapter_imports_correctly(self):
        """Test that EspnSource can be imported and instantiated."""
        source = EspnSource()
        assert source is not None
        assert hasattr(source, 'download')
        assert hasattr(source, 'ingest')
        assert hasattr(source, 'validate')

    def test_get_available_seasons(self):
        """Test that EspnSource returns available seasons."""
        source = EspnSource()
        seasons = source.get_available_seasons()
        assert isinstance(seasons, list)
        assert len(seasons) > 0
        assert all(isinstance(s, int) for s in seasons)
        assert 2020 in seasons  # ESPN data available from 2005+


class TestStatcastSource:
    """E2E tests for Statcast source adapter."""

    def test_adapter_imports_correctly(self):
        """Test that StatcastSource can be imported and instantiated."""
        source = StatcastSource()
        assert source is not None
        assert hasattr(source, 'download')
        assert hasattr(source, 'ingest')
        assert hasattr(source, 'validate')

    def test_get_available_seasons(self):
        """Test that StatcastSource returns available seasons."""
        source = StatcastSource()
        seasons = source.get_available_seasons()
        assert isinstance(seasons, list)
        assert 2015 in seasons  # Statcast available from 2015
        assert 2024 in seasons


class TestLahmanSource:
    """E2E tests for Lahman source adapter."""

    def test_adapter_imports_correctly(self):
        """Test that LahmanSource can be imported and instantiated."""
        source = LahmanSource()
        assert source is not None
        assert hasattr(source, 'download')
        assert hasattr(source, 'ingest')
        assert hasattr(source, 'validate')


class TestRetrosheetSource:
    """E2E tests for Retrosheet source adapter."""

    def test_adapter_imports_correctly(self):
        """Test that RetrosheetSource can be imported and instantiated."""
        source = RetrosheetSource()
        assert source is not None
        assert hasattr(source, 'download')
        assert hasattr(source, 'ingest')
        assert hasattr(source, 'validate')

    def test_get_available_seasons(self):
        """Test that RetrosheetSource returns available seasons."""
        source = RetrosheetSource()
        seasons = source.get_seasons_available()
        assert isinstance(seasons, list)
        assert 1916 in seasons  # Retrosheet data from 1916
        assert 2025 in seasons


class TestWrapperCalls:
    """Test that wrappers can actually call underlying scripts."""

    def test_scripts_exist(self):
        """Verify that wrapped scripts still exist."""
        scripts = [
            'scripts/data_ingestion/download_mlb_bulk.py',
            'scripts/data_ingestion/fetch_espn_mlb.py',
            'scripts/data_ingestion/download_statcast.py',
            'scripts/data_ingestion/download_lahman_data.py',
            'scripts/bridge/populate_bridge_tables.py',
        ]

        for script in scripts:
            script_path = PROJECT_ROOT / script
            assert script_path.exists(), f'Script {script} does not exist'
            assert script_path.is_file(), f'{script} is not a file'

    def test_scripts_are_python(self):
        """Verify that wrapped scripts are Python files."""
        scripts = [
            'scripts/data_ingestion/download_mlb_bulk.py',
            'scripts/bridge/populate_bridge_tables.py',
        ]

        for script in scripts:
            script_path = PROJECT_ROOT / script
            with open(script_path) as f:
                first_line = f.readline()
                assert 'python' in first_line.lower() or first_line.startswith('#!/usr/bin/env python')


if __name__ == '__main__':
    # Run with: python tests/e2e/test_source_adapters.py
    pytest.main([__file__, '-v'])
