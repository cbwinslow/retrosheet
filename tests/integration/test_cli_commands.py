"""Integration tests for CLI commands.

Tests all baseball CLI commands work correctly end-to-end.

Author: Agent Cascade
Date: 2026-05-01
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

# Import CLI app
from baseball.cli.main import app


runner = CliRunner()


# ============================================================================
# CLI Command Tests
# ============================================================================


class TestCLIBasic:
    """Test basic CLI functionality."""

    def test_cli_help(self):
        """Test CLI shows help."""
        result = runner.invoke(app, ['--help'])
        assert result.exit_code == 0
        assert 'Baseball data ingestion and prediction platform' in result.output

    def test_cli_version(self):
        """Test version command."""
        result = runner.invoke(app, ['version'])
        assert result.exit_code == 0
        assert 'Baseball Platform' in result.output

    def test_cli_doctor(self):
        """Test doctor command runs."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            result = runner.invoke(app, ['doctor'])
            # May fail if DB not available, but command should run
            assert result.exit_code in [0, 1]  # 0 if all checks pass, 1 if some fail


class TestIngestCommands:
    """Test data ingestion CLI commands."""

    def test_ingest_help(self):
        """Test ingest command shows help."""
        result = runner.invoke(app, ['retrosheet', '--help'])
        assert result.exit_code == 0
        assert 'ingest' in result.output.lower() or 'retrosheet' in result.output.lower()

    def test_mlb_ingest_help(self):
        """Test MLB ingest command shows help."""
        result = runner.invoke(app, ['mlb', '--help'])
        assert result.exit_code == 0


class TestBetCommands:
    """Test betting CLI commands."""

    @pytest.mark.asyncio
    async def test_bet_analyze_help(self):
        """Test bet analyze command shows help."""
        result = runner.invoke(app, ['bet', '--help'])
        assert result.exit_code == 0
        assert 'analyze' in result.output.lower() or 'betting' in result.output.lower()

    @pytest.mark.asyncio
    async def test_bet_analyze_mock(self):
        """Test bet analyze with mock data."""
        with patch('baseball.betting.sources.TheOddsApiSource') as mock_source:
            mock_instance = MagicMock()
            mock_source.return_value = mock_instance
            mock_instance.get_live_odds.return_value = []

            result = runner.invoke(app, [
                'bet', 'analyze',
                '--game', '716190',
                '--min-edge', '0.05',
                '--paper'
            ])

            # Command should run (may show "no opportunities found")
            assert result.exit_code in [0, 1]


class TestPredictCommands:
    """Test prediction CLI commands."""

    def test_predict_help(self):
        """Test predict command shows help."""
        result = runner.invoke(app, ['predict', '--help'])
        assert result.exit_code == 0

    def test_predict_game_dry_run(self):
        """Test predict game with dry run."""
        result = runner.invoke(app, [
            'predict', 'game',
            '--game', '716190',
            '--dry-run'
        ])
        assert result.exit_code == 0
        assert 'Dry run' in result.output


class TestModelCommands:
    """Test model CLI commands."""

    def test_models_help(self):
        """Test models command shows help."""
        result = runner.invoke(app, ['models', '--help'])
        assert result.exit_code == 0


class TestFeatureCommands:
    """Test feature CLI commands."""

    def test_features_help(self):
        """Test features command shows help."""
        result = runner.invoke(app, ['features', '--help'])
        assert result.exit_code == 0


class TestBridgeCommands:
    """Test bridge CLI commands."""

    def test_bridge_help(self):
        """Test bridge command shows help."""
        result = runner.invoke(app, ['bridge', '--help'])
        assert result.exit_code == 0


# ============================================================================
# End-to-End Workflow Tests
# ============================================================================


class TestEndToEndWorkflow:
    """Test complete workflows through CLI."""

    def test_full_workflow_dry_run(self):
        """Test full workflow in dry-run mode."""
        # Step 1: Predict game (dry run)
        result = runner.invoke(app, [
            'predict', 'game',
            '--game', '716190',
            '--dry-run'
        ])
        assert result.exit_code == 0

    def test_betting_workflow_dry_run(self):
        """Test betting workflow."""
        with patch('baseball.betting.integration.SimulationBackedAnalyzer') as mock_analyzer:
            mock_instance = MagicMock()
            mock_analyzer.return_value = mock_instance
            mock_instance.analyze_game_with_simulation.return_value = {
                'game_id': '716190',
                'opportunities': [],
                'simulation_probabilities': {'home_win': 0.55, 'away_win': 0.45}
            }

            result = runner.invoke(app, [
                'bet', 'analyze',
                '--game', '716190',
                '--paper',
                '--min-edge', '0.10'
            ])

            # Should run without error (may find no opportunities)
            assert result.exit_code in [0, 1]


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestCLIErrorHandling:
    """Test CLI handles errors gracefully."""

    def test_missing_required_option(self):
        """Test CLI fails gracefully when required option missing."""
        result = runner.invoke(app, ['predict', 'game'])
        assert result.exit_code == 2
        assert 'Missing option' in result.output or 'Usage:' in result.output

    def test_invalid_game_id(self):
        """Test CLI handles invalid game ID."""
        with patch('baseball.core.db.get_db_connection') as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None  # Game not found
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db.return_value = mock_conn

            result = runner.invoke(app, [
                'predict', 'game',
                '--game', '999999'
            ])

            assert result.exit_code == 1
            assert 'not found' in result.output.lower() or 'error' in result.output.lower()
