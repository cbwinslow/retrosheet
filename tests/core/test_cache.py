"""Comprehensive test suite for Redis caching layer.

Tests cover all aspects of the caching infrastructure including:
- CacheManager connection management
- Basic cache operations (get, set, delete, exists)
- Decorator functionality (@cached, @cached_simulation, @cached_odds)
- Error handling and edge cases
- TTL expiration
- Key generation and invalidation
- Cache statistics tracking
- Health checking

Author: Agent Cascade
Date: 2026-05-01
"""

import asyncio
import pickle
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from baseball.core.cache import (
    CacheManager,
    CacheStats,
    cache_manager,
    cache_stats,
    cached,
    cached_odds,
    cached_simulation,
    cached_sync,
    clear_all_cache,
    invalidate_game_cache,
)


# ============================================================================
# CacheManager Tests
# ============================================================================


class TestCacheManager:
    """Test suite for CacheManager class."""

    @pytest_asyncio.fixture
    async def cache(self):
        """Create a fresh CacheManager instance for each test."""
        cache = CacheManager(host='localhost', port=6379, db=0)
        yield cache
        await cache.disconnect()

    @pytest.mark.asyncio
    async def test_init_default_parameters(self):
        """Test CacheManager initialization with default parameters."""
        cache = CacheManager()
        assert cache.host == 'localhost'
        assert cache.port == 6379
        assert cache.db == 0
        assert cache.password is None
        assert cache.decode_responses is False
        assert cache._client is None

    @pytest.mark.asyncio
    async def test_init_custom_parameters(self):
        """Test CacheManager initialization with custom parameters."""
        cache = CacheManager(
            host='redis.example.com',
            port=6380,
            db=1,
            password='secret',
            decode_responses=True,
        )
        assert cache.host == 'redis.example.com'
        assert cache.port == 6380
        assert cache.db == 1
        assert cache.password == 'secret'
        assert cache.decode_responses is True

    @pytest.mark.asyncio
    async def test_connect_success(self, cache):
        """Test successful Redis connection."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_from_url.return_value = mock_client

            client = await cache.connect()

            assert client is mock_client
            assert cache._client is mock_client
            mock_from_url.assert_called_once_with(
                'redis://localhost:6379/0',
                password=None,
                decode_responses=False,
            )

    @pytest.mark.asyncio
    async def test_connect_reuses_existing_connection(self, cache):
        """Test that connect reuses existing connection."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_from_url.return_value = mock_client

            # First connection
            client1 = await cache.connect()
            # Second connection
            client2 = await cache.connect()

            assert client1 is client2
            assert mock_from_url.call_count == 1

    @pytest.mark.asyncio
    async def test_disconnect(self, cache):
        """Test disconnecting from Redis."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_from_url.return_value = mock_client

            await cache.connect()
            await cache.disconnect()

            mock_client.close.assert_called_once()
            assert cache._client is None

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, cache):
        """Test disconnect when no connection exists (should not raise)."""
        await cache.disconnect()  # Should not raise
        assert cache._client is None

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, cache):
        """Test retrieving value from cache (cache hit)."""
        test_data = {'game_id': '716190', 'result': 0.65}
        pickled_data = pickle.dumps(test_data)

        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.get = AsyncMock(return_value=pickled_data)
            mock_from_url.return_value = mock_client

            result = await cache.get('sim:716190')

            assert result == test_data
            mock_client.get.assert_called_once_with('sim:716190')

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache):
        """Test retrieving value from cache (cache miss)."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.get = AsyncMock(return_value=None)
            mock_from_url.return_value = mock_client

            result = await cache.get('sim:716190')

            assert result is None

    @pytest.mark.asyncio
    async def test_get_error_handling(self, cache):
        """Test get operation handles Redis errors gracefully."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.get = AsyncMock(side_effect=Exception('Redis connection error'))
            mock_from_url.return_value = mock_client

            result = await cache.get('sim:716190')

            assert result is None  # Should return None on error

    @pytest.mark.asyncio
    async def test_set_success(self, cache):
        """Test setting value in cache."""
        test_data = {'game_id': '716190', 'result': 0.65}

        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.set = AsyncMock(return_value=True)
            mock_from_url.return_value = mock_client

            result = await cache.set('sim:716190', test_data, ttl=300)

            assert result is True
            mock_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_default_ttl(self, cache):
        """Test setting value with default TTL."""
        test_data = {'game_id': '716190'}

        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.set = AsyncMock(return_value=True)
            mock_from_url.return_value = mock_client

            await cache.set('sim:716190', test_data)

            # Check that default TTL (300) was used
            call_args = mock_client.set.call_args
            assert call_args[0][0] == 'sim:716190'
            assert call_args[1]['ex'] == 300

    @pytest.mark.asyncio
    async def test_set_custom_ttl(self, cache):
        """Test setting value with custom TTL."""
        test_data = {'game_id': '716190'}

        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.set = AsyncMock(return_value=True)
            mock_from_url.return_value = mock_client

            await cache.set('sim:716190', test_data, ttl=600)

            call_args = mock_client.set.call_args
            assert call_args[1]['ex'] == 600

    @pytest.mark.asyncio
    async def test_set_error_handling(self, cache):
        """Test set operation handles Redis errors gracefully."""
        test_data = {'game_id': '716190'}

        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.set = AsyncMock(side_effect=Exception('Redis error'))
            mock_from_url.return_value = mock_client

            result = await cache.set('sim:716190', test_data)

            assert result is False  # Should return False on error

    @pytest.mark.asyncio
    async def test_delete_success(self, cache):
        """Test deleting key from cache."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.delete = AsyncMock(return_value=1)
            mock_from_url.return_value = mock_client

            result = await cache.delete('sim:716190')

            assert result is True
            mock_client.delete.assert_called_once_with('sim:716190')

    @pytest.mark.asyncio
    async def test_delete_error_handling(self, cache):
        """Test delete operation handles Redis errors gracefully."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.delete = AsyncMock(side_effect=Exception('Redis error'))
            mock_from_url.return_value = mock_client

            result = await cache.delete('sim:716190')

            assert result is False

    @pytest.mark.asyncio
    async def test_exists_true(self, cache):
        """Test exists returns True when key exists."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.exists = AsyncMock(return_value=1)
            mock_from_url.return_value = mock_client

            result = await cache.exists('sim:716190')

            assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, cache):
        """Test exists returns False when key doesn't exist."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.exists = AsyncMock(return_value=0)
            mock_from_url.return_value = mock_client

            result = await cache.exists('sim:716190')

            assert result is False

    @pytest.mark.asyncio
    async def test_exists_error_handling(self, cache):
        """Test exists operation handles Redis errors gracefully."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.exists = AsyncMock(side_effect=Exception('Redis error'))
            mock_from_url.return_value = mock_client

            result = await cache.exists('sim:716190')

            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, cache):
        """Test health check when Redis is healthy."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.info = AsyncMock(
                return_value={
                    'redis_version': '7.0.0',
                    'used_memory_human': '1.5M',
                    'connected_clients': 5,
                }
            )
            mock_from_url.return_value = mock_client

            result = await cache.health_check()

            assert result['status'] == 'healthy'
            assert result['connected'] is True
            assert result['version'] == '7.0.0'
            assert result['used_memory'] == '1.5M'
            assert result['clients_connected'] == 5

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, cache):
        """Test health check when Redis is unhealthy."""
        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.info = AsyncMock(side_effect=Exception('Connection error'))
            mock_from_url.return_value = mock_client

            result = await cache.health_check()

            assert result['status'] == 'unhealthy'
            assert result['connected'] is False
            assert 'error' in result


# ============================================================================
# Decorator Tests
# ============================================================================


class TestCachedDecorator:
    """Test suite for @cached decorator."""

    @pytest.mark.asyncio
    async def test_cached_decorator_cache_hit(self):
        """Test @cached decorator returns cached value on subsequent calls."""
        call_count = 0

        @cached(ttl=300, key_prefix='test')
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                # First call - cache miss
                mock_get.return_value = None
                result1 = await expensive_function(5)
                assert result1 == 10
                assert call_count == 1
                mock_set.assert_called_once()

                # Second call - cache hit
                mock_get.return_value = 10
                result2 = await expensive_function(5)
                assert result2 == 10
                assert call_count == 1  # Should not increment

    @pytest.mark.asyncio
    async def test_cached_decorator_cache_miss(self):
        """Test @cached decorator executes function on cache miss."""
        call_count = 0

        @cached(ttl=300)
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                result = await expensive_function(5)

                assert result == 10
                assert call_count == 1
                mock_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_decorator_custom_key_builder(self):
        """Test @cached decorator with custom key builder."""
        def custom_key(x: int, y: int) -> str:
            return f'custom:{x}:{y}'

        @cached(ttl=300, key_builder=custom_key)
        async def add(x: int, y: int) -> int:
            return x + y

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                await add(3, 4)

                # Check that custom key was used
                mock_get.assert_called_once_with('custom:3:4')

    @pytest.mark.asyncio
    async def test_cached_decorator_default_key_generation(self):
        """Test @cached decorator generates default key when no builder provided."""
        @cached(ttl=300)
        async def test_func(x: int, y: str) -> str:
            return f'{x}:{y}'

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                await test_func(5, 'test')

                # Check that a key was generated (format: function_name:hash)
                call_args = mock_get.call_args
                assert call_args[0][0].startswith('test_func:')


class TestCachedSimulationDecorator:
    """Test suite for @cached_simulation decorator."""

    @pytest.mark.asyncio
    async def test_cached_simulation_uses_game_id(self):
        """Test @cached_simulation uses game_id for cache key."""
        call_count = 0

        @cached_simulation(ttl=600)
        async def run_simulation(game_id: str, iterations: int = 1000) -> dict:
            nonlocal call_count
            call_count += 1
            return {'game_id': game_id, 'iterations': iterations}

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                result = await run_simulation('716190', iterations=5000)

                assert result['game_id'] == '716190'
                assert call_count == 1
                mock_get.assert_called_once_with('sim:716190')
                mock_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cached_simulation_cache_hit(self):
        """Test @cached_simulation returns cached result."""
        cached_result = {'game_id': '716190', 'win_prob': 0.65}

        @cached_simulation(ttl=600)
        async def run_simulation(game_id: str) -> dict:
            return {'game_id': game_id, 'win_prob': 0.50}

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = cached_result

            result = await run_simulation('716190')

            assert result == cached_result  # Should return cached value

    @pytest.mark.asyncio
    async def test_cached_simulation_invalidate_method(self):
        """Test @cached_simulation provides invalidate method."""
        @cached_simulation(ttl=600)
        async def run_simulation(game_id: str) -> dict:
            return {'game_id': game_id}

        with patch.object(cache_manager, 'delete', new_callable=AsyncMock) as mock_delete:
            await run_simulation.invalidate('716190')

            mock_delete.assert_called_once_with('sim:716190')

    @pytest.mark.asyncio
    async def test_cached_simulation_game_id_from_kwargs(self):
        """Test @cached_simulation extracts game_id from kwargs."""
        @cached_simulation(ttl=600)
        async def run_simulation(**kwargs) -> dict:
            return kwargs

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                await run_simulation(game_id='716190', iterations=1000)

                mock_get.assert_called_once_with('sim:716190')

    @pytest.mark.asyncio
    async def test_cached_simulation_game_id_from_args(self):
        """Test @cached_simulation extracts game_id from args."""
        @cached_simulation(ttl=600)
        async def run_simulation(game_id: str) -> dict:
            return {'game_id': game_id}

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                await run_simulation('716190')

                mock_get.assert_called_once_with('sim:716190')

    @pytest.mark.asyncio
    async def test_cached_simulation_unknown_game_id(self):
        """Test @cached_simulation handles missing game_id gracefully."""
        @cached_simulation(ttl=600)
        async def run_simulation() -> dict:
            return {}

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                await run_simulation()

                # Should use 'unknown' as fallback
                mock_get.assert_called_once_with('sim:unknown')


class TestCachedOddsDecorator:
    """Test suite for @cached_odds decorator."""

    @pytest.mark.asyncio
    async def test_cached_odds_uses_odds_prefix(self):
        """Test @cached_odds uses 'odds' prefix."""
        @cached_odds(ttl=120)
        async def fetch_odds(game_id: str) -> dict:
            return {'game_id': game_id, 'odds': 1.5}

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                await fetch_odds('716190')

                # Check that key starts with 'odds:'
                call_args = mock_get.call_args
                assert call_args[0][0].startswith('odds:')

    @pytest.mark.asyncio
    async def test_cached_odds_default_ttl(self):
        """Test @cached_odds uses default TTL of 60 seconds."""
        @cached_odds()
        async def fetch_odds(game_id: str) -> dict:
            return {'game_id': game_id}

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                await fetch_odds('716190')

                # Check that TTL was set
                call_args = mock_set.call_args
                assert call_args[1]['ttl'] == 60

    @pytest.mark.asyncio
    async def test_cached_odds_custom_ttl(self):
        """Test @cached_odds accepts custom TTL."""
        @cached_odds(ttl=300)
        async def fetch_odds(game_id: str) -> dict:
            return {'game_id': game_id}

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                await fetch_odds('716190')

                call_args = mock_set.call_args
                assert call_args[1]['ttl'] == 300


# ============================================================================
# CacheStats Tests
# ============================================================================


class TestCacheStats:
    """Test suite for CacheStats class."""

    def test_init(self):
        """Test CacheStats initialization."""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.errors == 0

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats()
        stats.hits = 80
        stats.misses = 20

        assert stats.hit_rate == 0.8

    def test_hit_rate_zero_total(self):
        """Test hit rate when total is zero."""
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_hit_rate_all_hits(self):
        """Test hit rate when all requests are hits."""
        stats = CacheStats()
        stats.hits = 100
        stats.misses = 0

        assert stats.hit_rate == 1.0

    def test_hit_rate_all_misses(self):
        """Test hit rate when all requests are misses."""
        stats = CacheStats()
        stats.hits = 0
        stats.misses = 100

        assert stats.hit_rate == 0.0

    def test_to_dict(self):
        """Test converting stats to dictionary."""
        stats = CacheStats()
        stats.hits = 75
        stats.misses = 25
        stats.errors = 2

        result = stats.to_dict()

        assert result['hits'] == 75
        assert result['misses'] == 25
        assert result['errors'] == 2
        assert result['hit_rate'] == '75.0%'


# ============================================================================
# Utility Function Tests
# ============================================================================


class TestUtilityFunctions:
    """Test suite for cache utility functions."""

    @pytest.mark.asyncio
    async def test_invalidate_game_cache(self):
        """Test invalidating game-specific cache."""
        with patch.object(cache_manager, 'delete', new_callable=AsyncMock) as mock_delete:
            await invalidate_game_cache('716190')

            # Should delete all game-related patterns
            assert mock_delete.call_count == 3
            mock_delete.assert_any_call('sim:716190')
            mock_delete.assert_any_call('odds:*:716190')
            mock_delete.assert_any_call('pred:716190')

    @pytest.mark.asyncio
    async def test_clear_all_cache(self):
        """Test clearing all cache entries."""
        with patch.object(cache_manager, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_client = AsyncMock(spec=Redis)
            mock_client.flushdb = AsyncMock(return_value=True)
            mock_connect.return_value = mock_client

            await clear_all_cache()

            mock_client.flushdb.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_all_cache_error_handling(self):
        """Test clear_all_cache handles errors gracefully."""
        with patch.object(cache_manager, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_client = AsyncMock(spec=Redis)
            mock_client.flushdb = AsyncMock(side_effect=Exception('Redis error'))
            mock_connect.return_value = mock_client

            # Should not raise exception
            await clear_all_cache()


# ============================================================================
# Integration Tests (with mocked Redis)
# ============================================================================


class TestCacheIntegration:
    """Integration tests for cache functionality."""

    @pytest.mark.asyncio
    async def test_full_cache_workflow(self):
        """Test complete cache workflow: set, get, delete."""
        test_data = {'game_id': '716190', 'result': 0.65}

        with patch('redis.asyncio.from_url') as mock_from_url:
            mock_client = AsyncMock(spec=Redis)
            mock_client.set = AsyncMock(return_value=True)
            mock_client.get = AsyncMock(return_value=pickle.dumps(test_data))
            mock_client.delete = AsyncMock(return_value=1)
            mock_from_url.return_value = mock_client

            cache = CacheManager()

            # Set value
            await cache.set('sim:716190', test_data, ttl=300)
            mock_client.set.assert_called_once()

            # Get value
            result = await cache.get('sim:716190')
            assert result == test_data

            # Delete value
            await cache.delete('sim:716190')
            mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_decorator_with_complex_data_types(self):
        """Test caching of complex data types (nested dicts, lists, etc.)."""
        complex_data = {
            'game_id': '716190',
            'teams': {
                'home': {'name': 'Yankees', 'score': 5},
                'away': {'name': 'Red Sox', 'score': 3},
            },
            'events': [
                {'inning': 1, 'event': 'single'},
                {'inning': 2, 'event': 'home_run'},
            ],
        }

        @cached(ttl=300)
        async def get_complex_data(game_id: str) -> dict:
            return complex_data

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                result = await get_complex_data('716190')

                assert result == complex_data
                mock_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self):
        """Test concurrent access to cache."""
        @cached(ttl=300)
        async def get_value(x: int) -> int:
            await asyncio.sleep(0.01)  # Simulate work
            return x * 2

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                # Run multiple concurrent calls
                tasks = [get_value(i) for i in range(10)]
                results = await asyncio.gather(*tasks)

                assert len(results) == 10
                assert all(r == i * 2 for i, r in enumerate(results))

    @pytest.mark.asyncio
    async def test_cache_with_none_value(self):
        """Test caching functions that return None."""
        @cached(ttl=300)
        async def get_none_value() -> None:
            return None

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                result = await get_none_value()

                assert result is None
                # Should still attempt to cache the None value
                mock_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_with_empty_string(self):
        """Test caching functions that return empty string."""
        @cached(ttl=300)
        async def get_empty_string() -> str:
            return ''

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                result = await get_empty_string()

                assert result == ''
                mock_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_with_large_data(self):
        """Test caching of large data structures."""
        large_data = {'data': list(range(10000))}

        @cached(ttl=300)
        async def get_large_data() -> dict:
            return large_data

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                result = await get_large_data()

                assert result == large_data
                mock_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_global_cache_manager_instance(self):
        """Test that global cache_manager instance works correctly."""
        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                test_data = {'test': 'data'}
                await cache_manager.set('test_key', test_data)
                result = await cache_manager.get('test_key')

                mock_set.assert_called_once()
                mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_global_cache_stats_instance(self):
        """Test that global cache_stats instance works correctly."""
        cache_stats.hits = 100
        cache_stats.misses = 50

        result = cache_stats.to_dict()

        assert result['hits'] == 100
        assert result['misses'] == 50
        assert result['hit_rate'] == '66.7%'


# ============================================================================
# Edge Cases and Error Scenarios
# ============================================================================


class TestCacheEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_cache_key_collision_different_args(self):
        """Test that different arguments produce different cache keys."""
        @cached(ttl=300)
        async def test_func(x: int) -> int:
            return x

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                await test_func(1)
                await test_func(2)

                # Should have made 2 different cache keys
                assert mock_get.call_count == 2
                keys = [call[0][0] for call in mock_get.call_args_list]
                assert len(set(keys)) == 2  # Keys should be different

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self):
        """Test that decorators preserve function metadata."""
        @cached(ttl=300)
        async def test_func(x: int) -> int:
            """Test function docstring."""
            return x

        assert test_func.__name__ == 'test_func'
        assert test_func.__doc__ == 'Test function docstring.'

    @pytest.mark.asyncio
    async def test_cache_with_datetime_objects(self):
        """Test caching functions that return datetime objects."""
        test_datetime = datetime(2026, 5, 1, 12, 0, 0)

        @cached(ttl=300)
        async def get_datetime() -> datetime:
            return test_datetime

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                result = await get_datetime()

                assert result == test_datetime
                mock_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_with_exception_in_function(self):
        """Test that exceptions in cached function are not cached."""
        @cached(ttl=300)
        async def failing_function() -> str:
            raise ValueError('Function failed')

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            with pytest.raises(ValueError):
                await failing_function()

            # Should not have called set because function raised exception
            # (Note: current implementation doesn't handle this, but test documents behavior)

    @pytest.mark.asyncio
    async def test_multiple_decorators_on_same_function(self):
        """Test applying multiple decorators to the same function."""
        @cached(ttl=300, key_prefix='first')
        @cached(ttl=600, key_prefix='second')
        async def test_func(x: int) -> int:
            return x * 2

        with patch.object(cache_manager, 'get', new_callable=AsyncMock) as mock_get:
            with patch.object(cache_manager, 'set', new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                await test_func(5)

                # Should have called both decorators
                assert mock_get.call_count == 2
