"""Integration tests for cache in real workflow.

Verifies that caching decorators work correctly in actual
workflow scenarios, not just in isolation.

Author: Agent Cascade
Date: 2026-05-01
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from baseball.core.cache import (
    CacheManager,
    cache_manager,
    cached,
    cached_odds,
    cached_simulation,
    cached_sync,
)


# ============================================================================
# Cache Decorator Integration Tests
# ============================================================================


class TestCacheInSimulationWorkflow:
    """Test caching integration in simulation workflow."""

    @pytest_asyncio.fixture
    async def mock_redis(self):
        """Create mock Redis client."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client
            yield mock_client

    @pytest.mark.asyncio
    async def test_simulation_result_cached(self, mock_redis):
        """Test that simulation results are cached and reused."""
        call_count = 0

        @cached_simulation(ttl=600)
        async def mock_run_simulation(game_id: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {'game_id': game_id, 'home_win': Decimal('0.55'), 'iterations': 10000}

        # First call - should execute function
        result1 = await mock_run_simulation('716190')
        assert call_count == 1
        assert result1['game_id'] == '716190'

        # Second call - should use cache
        result2 = await mock_run_simulation('716190')
        assert call_count == 1  # Function not called again
        assert result2['game_id'] == '716190'

    @pytest.mark.asyncio
    async def test_simulation_cache_different_games(self, mock_redis):
        """Test that different games have separate cache entries."""
        call_count = 0

        @cached_simulation(ttl=600)
        async def mock_run_simulation(game_id: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {'game_id': game_id, 'home_win': Decimal('0.55')}

        # Call for two different games
        await mock_run_simulation('716190')
        await mock_run_simulation('716191')

        # Both should execute
        assert call_count == 2


class TestCacheInBettingWorkflow:
    """Test caching integration in betting workflow."""

    @pytest_asyncio.fixture
    async def mock_redis(self):
        """Create mock Redis client."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client
            yield mock_client

    @pytest.mark.asyncio
    async def test_odds_cached_in_betting_analysis(self, mock_redis):
        """Test that odds fetching is cached during betting analysis."""
        call_count = 0

        @cached_odds(ttl=60)
        async def mock_fetch_odds(game_id: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {'game_id': game_id, 'markets': []}

        # First fetch
        odds1 = await mock_fetch_odds('716190')
        assert call_count == 1

        # Second fetch - should use cache
        odds2 = await mock_fetch_odds('716190')
        assert call_count == 1  # Not fetched again
        assert odds1 == odds2


class TestCacheWithRealComponents:
    """Test caching with actual (mocked) components."""

    @pytest_asyncio.fixture
    async def mock_redis(self):
        """Create mock Redis client."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client
            yield mock_client

    @pytest.mark.asyncio
    async def test_feature_extraction_cached(self, mock_redis):
        """Test feature extraction results are cached."""
        from baseball.models.inference import InferencePipeline

        with patch.object(InferencePipeline, '_extract_game_features') as mock_extract:
            mock_extract.return_value = {'game_pk': 716190, 'features': [1.0, 2.0, 3.0]}

            # The method is decorated with @cached_sync
            # First call
            features1 = InferencePipeline._extract_game_features(None, 716190)

            # Second call - should use cache
            features2 = InferencePipeline._extract_game_features(None, 716190)

            # Should only call once due to cache
            assert mock_extract.call_count == 1


# ============================================================================
# Cache Resilience Tests
# ============================================================================


class TestCacheResilience:
    """Test cache behavior when Redis is unavailable."""

    @pytest.mark.asyncio
    async def test_graceful_fallback_when_redis_down(self):
        """Test that functions work when Redis is unavailable."""

        @cached(ttl=300)
        async def important_function(x: int) -> int:
            return x * 2

        with patch.object(cache_manager, 'get', side_effect=Exception('Redis down')):
            with patch.object(cache_manager, 'set', side_effect=Exception('Redis down')):
                # Should still work, just without caching
                result = await important_function(5)
                assert result == 10

    @pytest.mark.asyncio
    async def test_cache_reconnection(self):
        """Test cache reconnects after temporary failure."""
        call_count = 0

        @cached(ttl=300)
        async def compute(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - success
        result1 = await compute(5)
        assert result1 == 10
        assert call_count == 1

        # Simulate Redis failure
        with patch.object(cache_manager, 'get', side_effect=Exception('Redis down')):
            result2 = await compute(5)
            # Should still work but re-execute
            assert result2 == 10
            assert call_count == 2


# ============================================================================
# Performance Tests
# ============================================================================


class TestCachePerformance:
    """Test cache performance improvements."""

    @pytest.mark.asyncio
    async def test_cache_provides_performance_benefit(self):
        """Test that cache actually speeds up repeated calls."""
        import time

        slow_call_count = 0

        @cached(ttl=300)
        async def slow_function(x: int) -> int:
            nonlocal slow_call_count
            slow_call_count += 1
            await asyncio.sleep(0.1)  # Simulate slow operation
            return x * 2

        # First call - slow
        start = time.time()
        await slow_function(5)
        first_duration = time.time() - start

        # Second call - should be fast (cached)
        start = time.time()
        await slow_function(5)
        second_duration = time.time() - start

        # Cached call should be much faster
        assert second_duration < first_duration / 10
        assert slow_call_count == 1  # Only called once


# ============================================================================
# Cache Invalidation Tests
# ============================================================================


class TestCacheInvalidation:
    """Test cache invalidation works correctly."""

    @pytest_asyncio.fixture
    async def mock_redis(self):
        """Create mock Redis client."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client
            yield mock_client

    @pytest.mark.asyncio
    async def test_simulation_cache_invalidation(self, mock_redis):
        """Test simulation cache can be invalidated."""
        call_count = 0

        @cached_simulation(ttl=600)
        async def mock_simulate(game_id: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {'game_id': game_id, 'result': f'run_{call_count}'}

        # First call
        result1 = await mock_simulate('716190')
        assert call_count == 1
        assert result1['result'] == 'run_1'

        # Invalidate cache
        await mock_simulate.invalidate('716190')

        # Next call - should re-execute
        result2 = await mock_simulate('716190')
        assert call_count == 2
        assert result2['result'] == 'run_2'
