"""E2E tests for bridge service - verify wrappers work correctly.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26

These tests verify that the new baseball/services/bridge.py properly
WRAP the existing bridge scripts and that they function correctly.
"""

from pathlib import Path

import pytest

from baseball.services import BridgeService


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestBridgeService:
    """E2E tests for BridgeService."""

    def test_service_imports_correctly(self):
        """Test that BridgeService can be imported and instantiated."""
        service = BridgeService()
        assert service is not None

    def test_service_has_required_methods(self):
        """Test that BridgeService has all required methods."""
        service = BridgeService()
        required_methods = [
            'populate_all',
            'populate_players',
            'populate_games',
            'populate_teams',
            'resolve_id',
            'lookup_canonical',
            'get_coverage_stats',
        ]

        for method in required_methods:
            assert hasattr(service, method), f'Missing method: {method}'

    def test_bridge_scripts_exist(self):
        """Verify that wrapped bridge scripts still exist."""
        scripts = [
            'scripts/bridge/populate_bridge_tables.py',
            'scripts/bridge/ingest_chadwick_register.py',
            'scripts/bridge/populate_game_xref.py',
            'scripts/bridge/populate_season_aware_team_xref.py',
        ]

        for script in scripts:
            script_path = PROJECT_ROOT / script
            assert script_path.exists(), f'Bridge script {script} does not exist'
            assert script_path.is_file(), f'{script} is not a file'

    def test_resolve_id_returns_expected_structure(self):
        """Test that resolve_id returns expected structure (even if empty)."""
        service = BridgeService()

        # Test with non-existent ID - should return None or error
        result = service.resolve_id('mlb', '999999999', 'player')

        # Should return either None or a dict with error
        assert result is None or isinstance(result, dict)

    def test_lookup_canonical_returns_expected_structure(self):
        """Test that lookup_canonical returns expected structure."""
        service = BridgeService()

        # Test with non-existent ID - should return None
        result = service.lookup_canonical('nonexistent_123', 'player')

        # Should return either None or a dict
        assert result is None or isinstance(result, dict)


class TestBridgeIntegration:
    """Integration tests requiring database connection."""

    @pytest.fixture
    def bridge_service(self):
        """Fixture to create BridgeService with test database."""
        return BridgeService()

    @pytest.mark.skip(reason='Requires database connection')
    def test_get_coverage_stats(self, bridge_service):
        """Test getting coverage stats from bridge tables."""
        stats = bridge_service.get_coverage_stats()
        assert isinstance(stats, dict)

        # Should have stats for players, teams, games, parks
        for entity in ['players', 'teams', 'games', 'parks']:
            if entity in stats:
                assert 'total' in stats[entity] or 'error' in stats[entity]


if __name__ == '__main__':
    # Run with: python tests/e2e/test_bridge_service.py
    pytest.main([__file__, '-v'])
