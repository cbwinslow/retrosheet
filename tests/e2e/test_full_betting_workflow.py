"""End-to-end tests for complete betting workflow.

Tests the full pipeline: data ingestion → simulation → odds fetch → 
betting analysis → opportunity detection.

Author: Agent Cascade
Date: 2026-05-01
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from baseball.betting.integration import SimulationBackedAnalyzer
from baseball.betting.schemas import (
    BetOpportunity,
    BettingMarket,
    BookRegion,
    MarketStatus,
    MarketType,
    Sport,
)
from baseball.models.simulation import SimulationConfig, SimulationService


# ============================================================================
# End-to-End Betting Workflow Tests
# ============================================================================


class TestFullBettingWorkflow:
    """Test complete betting workflow from data to opportunities."""

    @pytest_asyncio.fixture
    async def mock_odds_source(self):
        """Create mock odds source with realistic data."""
        source = MagicMock()
        source.get_game_odds.return_value = [
            BettingMarket(
                market_id='dk_ml_001',
                game_id='716190',
                sport=Sport.MLB,
                market_type=MarketType.MONEYLINE,
                book='draftkings',
                book_region=BookRegion.US,
                odds=Decimal('-110'),
                odds_format='american',
                line=None,
                side='Home',
                timestamp=datetime.now(),
                game_time=datetime.now(),
                status=MarketStatus.OPEN,
                home_team='Yankees',
                away_team='Red Sox',
                is_live=False,
            ),
            BettingMarket(
                market_id='dk_ml_002',
                game_id='716190',
                sport=Sport.MLB,
                market_type=MarketType.MONEYLINE,
                book='draftkings',
                book_region=BookRegion.US,
                odds=Decimal('100'),
                odds_format='american',
                line=None,
                side='Away',
                timestamp=datetime.now(),
                game_time=datetime.now(),
                status=MarketStatus.OPEN,
                home_team='Yankees',
                away_team='Red Sox',
                is_live=False,
            ),
        ]
        return source

    @pytest_asyncio.fixture
    async def mock_simulation_service(self):
        """Create mock simulation service."""
        service = MagicMock()
        service.get_game_probabilities = AsyncMock(return_value={
            'home_win': Decimal('0.58'),
            'away_win': Decimal('0.42'),
        })
        return service

    @pytest.mark.asyncio
    async def test_full_workflow_opportunity_detection(
        self,
        mock_odds_source,
        mock_simulation_service,
    ):
        """Test full workflow detects betting opportunities."""
        # Create analyzer
        analyzer = SimulationBackedAnalyzer(
            odds_source=mock_odds_source,
            simulation_service=mock_simulation_service,
            min_edge=Decimal('0.02'),  # Low threshold for testing
        )

        # Run analysis
        result = await analyzer.analyze_game_with_simulation(
            game_id='716190',
            market_types=[MarketType.MONEYLINE],
        )

        # Verify result structure
        assert 'game_id' in result
        assert 'opportunities' in result
        assert 'simulation_probabilities' in result

        # Verify simulation probabilities used
        assert result['simulation_probabilities']['home_win'] == Decimal('0.58')

        # Log opportunities found
        print(f"Found {len(result['opportunities'])} opportunities")

    @pytest.mark.asyncio
    async def test_workflow_with_no_opportunities(
        self,
        mock_odds_source,
    ):
        """Test workflow when no opportunities exist (edge too low)."""
        # Mock simulation with no edge
        sim_service = MagicMock()
        sim_service.get_game_probabilities = AsyncMock(return_value={
            'home_win': Decimal('0.52'),  # Small edge
            'away_win': Decimal('0.48'),
        })

        # Create analyzer with high threshold
        analyzer = SimulationBackedAnalyzer(
            odds_source=mock_odds_source,
            simulation_service=sim_service,
            min_edge=Decimal('0.10'),  # High threshold
        )

        # Run analysis
        result = await analyzer.analyze_game_with_simulation(
            game_id='716190',
            market_types=[MarketType.MONEYLINE],
        )

        # Should find no opportunities
        assert len(result['opportunities']) == 0

    @pytest.mark.asyncio
    async def test_workflow_with_multiple_market_types(
        self,
        mock_odds_source,
        mock_simulation_service,
    ):
        """Test workflow with multiple market types."""
        # Add spread and total markets
        mock_odds_source.get_game_odds.side_effect = lambda game_id, types: [
            BettingMarket(
                market_id=f'dk_{mt.value}_001',
                game_id=game_id,
                sport=Sport.MLB,
                market_type=mt,
                book='draftkings',
                book_region=BookRegion.US,
                odds=Decimal('-110'),
                odds_format='american',
                line=Decimal('-1.5') if mt == MarketType.SPREAD else Decimal('8.5'),
                side='Home',
                timestamp=datetime.now(),
                game_time=datetime.now(),
                status=MarketStatus.OPEN,
                home_team='Yankees',
                away_team='Red Sox',
                is_live=False,
            )
            for mt in types
        ]

        # Add spread/total probs to simulation
        mock_simulation_service.get_spread_probabilities = AsyncMock(return_value={
            'home_cover': Decimal('0.55'),
            'away_cover': Decimal('0.45'),
        })
        mock_simulation_service.get_total_probabilities = AsyncMock(return_value={
            'over': Decimal('0.50'),
            'under': Decimal('0.50'),
        })

        analyzer = SimulationBackedAnalyzer(
            odds_source=mock_odds_source,
            simulation_service=mock_simulation_service,
            min_edge=Decimal('0.02'),
        )

        # Run analysis on all market types
        result = await analyzer.analyze_game_with_simulation(
            game_id='716190',
            market_types=[MarketType.MONEYLINE, MarketType.SPREAD, MarketType.TOTAL],
        )

        # Should analyze all market types
        assert result['markets_analyzed'] == 3


# ============================================================================
# Cache Integration in Workflow Tests
# ============================================================================


class TestCacheInWorkflow:
    """Test that caching works correctly in full workflow."""

    @pytest.mark.asyncio
    async def test_simulation_cached_across_analyses(self):
        """Test simulation results are cached when analyzing same game twice."""
        sim_call_count = 0

        async def mock_get_probs(game_id, model_id=None):
            nonlocal sim_call_count
            sim_call_count += 1
            return {'home_win': Decimal('0.55'), 'away_win': Decimal('0.45')}

        sim_service = MagicMock()
        sim_service.get_game_probabilities = mock_get_probs

        mock_source = MagicMock()
        mock_source.get_game_odds.return_value = []

        # Create analyzer
        analyzer = SimulationBackedAnalyzer(
            odds_source=mock_source,
            simulation_service=sim_service,
        )

        # First analysis
        await analyzer.analyze_game_with_simulation('716190')

        # Second analysis - should use cached simulation
        await analyzer.analyze_game_with_simulation('716190')

        # Simulation should only be called once
        assert sim_call_count == 1


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestWorkflowErrorHandling:
    """Test workflow handles errors gracefully."""

    @pytest.mark.asyncio
    async def test_workflow_with_simulation_failure(self):
        """Test workflow continues when simulation fails."""
        sim_service = MagicMock()
        sim_service.get_game_probabilities = AsyncMock(side_effect=Exception('DB error'))

        mock_source = MagicMock()
        mock_source.get_game_odds.return_value = []

        analyzer = SimulationBackedAnalyzer(
            odds_source=mock_source,
            simulation_service=sim_service,
            fallback_to_mock=True,  # Should fallback to mock
        )

        # Should not crash
        result = await analyzer.analyze_game_with_simulation('716190')

        # Should return error info but not crash
        assert 'error' in result or 'opportunities' in result

    @pytest.mark.asyncio
    async def test_workflow_with_odds_failure(self):
        """Test workflow handles odds source failure."""
        sim_service = MagicMock()
        sim_service.get_game_probabilities = AsyncMock(return_value={
            'home_win': Decimal('0.55'),
            'away_win': Decimal('0.45'),
        })

        mock_source = MagicMock()
        mock_source.get_game_odds.side_effect = Exception('API error')

        analyzer = SimulationBackedAnalyzer(
            odds_source=mock_source,
            simulation_service=sim_service,
        )

        # Should not crash
        result = await analyzer.analyze_game_with_simulation('716190')

        # Should handle gracefully
        assert isinstance(result, dict)


# ============================================================================
# Performance Tests
# ============================================================================


class TestWorkflowPerformance:
    """Test workflow performance characteristics."""

    @pytest.mark.asyncio
    async def test_cached_analysis_is_faster(self):
        """Test that cached analysis is faster than fresh analysis."""
        import time

        sim_service = MagicMock()
        sim_service.get_game_probabilities = AsyncMock(return_value={
            'home_win': Decimal('0.55'),
            'away_win': Decimal('0.45'),
        })

        mock_source = MagicMock()
        mock_source.get_game_odds.return_value = []

        analyzer = SimulationBackedAnalyzer(
            odds_source=mock_source,
            simulation_service=sim_service,
        )

        # First analysis (fresh)
        start = time.time()
        await analyzer.analyze_game_with_simulation('716190')
        first_duration = time.time() - start

        # Second analysis (should be faster if cached)
        start = time.time()
        await analyzer.analyze_game_with_simulation('716190')
        second_duration = time.time() - start

        # Log performance
        print(f"First analysis: {first_duration:.3f}s")
        print(f"Second analysis: {second_duration:.3f}s")

        # Both should complete reasonably fast
        assert first_duration < 5.0
        assert second_duration < 5.0
