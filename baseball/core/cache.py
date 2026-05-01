"""Redis caching layer for performance optimization.

Provides caching decorators and utilities for simulation queries,
odds data, and expensive computations.

Author: Agent Cascade
Date: 2026-04-30
"""

import functools
import hashlib
import logging
import pickle
from collections.abc import Callable
from typing import Any

import redis.asyncio as redis
from redis.asyncio import Redis


logger = logging.getLogger(__name__)


class CacheManager:
    """Manages Redis connection and caching operations.

    Provides:
    - Connection pooling
    - Cache decorators
    - Key management
    - Health checking

    Example:
        >>> cache = CacheManager()
        >>> await cache.connect()
        >>> result = await cache.get("sim:716190")
        >>> await cache.set("sim:716190", data, ttl=300)
    """

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        decode_responses: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        self._client: Redis | None = None

    async def connect(self) -> Redis:
        """Establish Redis connection."""
        if self._client is None:
            self._client = await redis.from_url(
                f'redis://{self.host}:{self.port}/{self.db}',
                password=self.password,
                decode_responses=self.decode_responses,
            )
            logger.info(f'Connected to Redis at {self.host}:{self.port}')
        return self._client

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info('Disconnected from Redis')

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        try:
            client = await self.connect()
            data = await client.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            logger.warning(f'Cache get error for {key}: {e}')
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set value in cache with optional TTL (seconds).

        Args:
            key: Cache key
            value: Value to cache (must be pickleable)
            ttl: Time to live in seconds (default: 300 = 5 minutes)
        """
        try:
            client = await self.connect()
            data = pickle.dumps(value)
            await client.set(key, data, ex=ttl or 300)
            return True
        except Exception as e:
            logger.warning(f'Cache set error for {key}: {e}')
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            client = await self.connect()
            await client.delete(key)
            return True
        except Exception as e:
            logger.warning(f'Cache delete error for {key}: {e}')
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            client = await self.connect()
            return await client.exists(key) > 0
        except Exception as e:
            logger.warning(f'Cache exists error for {key}: {e}')
            return False

    async def health_check(self) -> dict:
        """Check Redis health status."""
        try:
            client = await self.connect()
            info = await client.info()
            return {
                'status': 'healthy',
                'connected': True,
                'version': info.get('redis_version', 'unknown'),
                'used_memory': info.get('used_memory_human', 'unknown'),
                'clients_connected': info.get('connected_clients', 0),
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'connected': False,
                'error': str(e),
            }


# Global cache manager instance
cache_manager = CacheManager()


def cached(
    ttl: int = 300,
    key_prefix: str = '',
    key_builder: Callable | None = None,
):
    """Decorator to cache async function results.

    Args:
        ttl: Time to live in seconds (default: 300)
        key_prefix: Prefix for cache key
        key_builder: Optional custom key builder function

    Example:
        >>> @cached(ttl=600, key_prefix="sim")
        ... async def get_simulation(game_id: str):
        ...     # Expensive computation
        ...     return result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key: prefix:function_name:hash(args)
                key_data = f'{func.__name__}:{args!s}:{kwargs!s}'
                key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
                cache_key = f'{key_prefix}:{func.__name__}:{key_hash}' if key_prefix else f'{func.__name__}:{key_hash}'

            # Try to get from cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f'Cache hit: {cache_key}')
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            await cache_manager.set(cache_key, result, ttl=ttl)
            logger.debug(f'Cache miss - stored: {cache_key}')

            return result

        # Add cache bypass method
        async_wrapper.invalidate_cache = lambda *args, **kwargs: None  # Placeholder

        return async_wrapper
    return decorator


def cached_sync(
    ttl: int = 300,
    key_prefix: str = '',
    key_builder: Callable | None = None,
):
    """Decorator to cache synchronous function results.

    Args:
        ttl: Time to live in seconds (default: 300)
        key_prefix: Prefix for cache key
        key_builder: Optional custom key builder function

    Example:
        >>> @cached_sync(ttl=3600, key_prefix="transition")
        ... def load_transition_matrix():
        ...     # Expensive database query
        ...     return matrix
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key: prefix:function_name:hash(args)
                key_data = f'{func.__name__}:{args!s}:{kwargs!s}'
                key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
                cache_key = f'{key_prefix}:{func.__name__}:{key_hash}' if key_prefix else f'{func.__name__}:{key_hash}'

            # Try to get from cache (synchronously)
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, we can't use sync methods with async cache
                    # Fall back to no caching
                    logger.warning(f'Event loop running, skipping cache for {cache_key}')
                    return func(*args, **kwargs)
                
                cached_value = loop.run_until_complete(cache_manager.get(cache_key))
                if cached_value is not None:
                    logger.debug(f'Cache hit: {cache_key}')
                    return cached_value
            except Exception as e:
                logger.warning(f'Cache get error for {cache_key}: {e}')

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache (synchronously)
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    loop.run_until_complete(cache_manager.set(cache_key, result, ttl=ttl))
                    logger.debug(f'Cache miss - stored: {cache_key}')
            except Exception as e:
                logger.warning(f'Cache set error for {cache_key}: {e}')

            return result

        return sync_wrapper
    return decorator


def cached_simulation(ttl: int = 300):
    """Specialized decorator for simulation results.

    Uses game_id as key for easy invalidation.

    Example:
        >>> @cached_simulation(ttl=600)
        ... async def run_monte_carlo(game_id: str, **params):
        ...     return simulation_result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract game_id from args or kwargs
            game_id = kwargs.get('game_id') or (args[0] if args else 'unknown')
            cache_key = f'sim:{game_id}'

            # Check cache
            cached = await cache_manager.get(cache_key)
            if cached:
                logger.info(f'Simulation cache hit for game {game_id}')
                return cached

            # Run simulation
            result = await func(*args, **kwargs)

            # Cache result
            await cache_manager.set(cache_key, result, ttl=ttl)
            logger.info(f'Cached simulation for game {game_id}')

            return result

        # Add invalidate method
        async def invalidate(game_id: str) -> None:
            await cache_manager.delete(f'sim:{game_id}')
        wrapper.invalidate = invalidate

        return wrapper
    return decorator


def cached_odds(ttl: int = 60):
    """Specialized decorator for odds data (shorter TTL).

    Example:
        >>> @cached_odds(ttl=120)
        ... async def fetch_odds(game_id: str):
        ...     return odds_data
    """
    return cached(ttl=ttl, key_prefix='odds')


class CacheStats:
    """Track cache performance statistics."""

    def __init__(self) -> None:
        self.hits = 0
        self.misses = 0
        self.errors = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            'hits': self.hits,
            'misses': self.misses,
            'errors': self.errors,
            'hit_rate': f'{self.hit_rate:.1%}',
        }


# Global stats tracker
cache_stats = CacheStats()


async def invalidate_game_cache(game_id: str) -> None:
    """Invalidate all cached data for a game.

    Call when new data arrives that invalidates cached results.

    Args:
        game_id: Game identifier to invalidate
    """
    patterns = [
        f'sim:{game_id}',
        f'odds:*:{game_id}',
        f'pred:{game_id}',
    ]

    for pattern in patterns:
        await cache_manager.delete(pattern)

    logger.info(f'Invalidated cache for game {game_id}')


async def clear_all_cache() -> None:
    """Clear all cache entries. Use with caution!"""
    try:
        client = await cache_manager.connect()
        await client.flushdb()
        logger.warning('All cache entries cleared')
    except Exception as e:
        logger.exception(f'Failed to clear cache: {e}')
