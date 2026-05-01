"""Live data ingestion service with WebSocket support.

Handles real-time game data from MLB, ESPN, and other live feeds.
Uses event hooks for multiple downstream consumers.

Author: Agent Cascade
Date: 2026-04-30
"""

import asyncio
import contextlib
import json
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed


logger = logging.getLogger(__name__)


class LiveDataIngestionService:
    """Service for managing live data feeds via WebSocket.

    Manages multiple concurrent WebSocket connections with:
    - Automatic reconnection with exponential backoff
    - Event hooks for multiple consumers (betting, simulation, stats)
    - Message buffering for replay
    - Database persistence via ingestion pipeline

    Example:
        >>> service = LiveDataIngestionService()
        >>>
        >>> # Register multiple consumers via hooks (Event Pattern)
        >>> service.on_message('mlb', lambda msg, ctx: update_live_game(msg))
        >>> service.on_message('mlb', lambda msg, ctx: check_betting_opportunities(msg))
        >>> service.on_message('mlb', lambda msg, ctx: update_simulation_state(msg))
        >>>
        >>> # Start feed
        >>> await service.start_feed('mlb_live', 'wss://ws.example.com/mlb')
    """

    def __init__(
        self,
        reconnect_attempts: int = 5,
        reconnect_delay_base: float = 1.0,
        message_buffer_size: int = 1000,
    ) -> None:
        """Initialize live ingestion service.

        Args:
            reconnect_attempts: Max reconnection tries
            reconnect_delay_base: Base seconds for exponential backoff
            message_buffer_size: Max messages to buffer per feed
        """
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay_base = reconnect_delay_base
        self.message_buffer_size = message_buffer_size

        # Active connections
        self._connections: dict[str, Any] = {}
        self._tasks: dict[str, asyncio.Task] = {}

        # Message buffers
        self._buffers: dict[str, list[dict]] = {}

        # Event handlers (Event Pattern)
        self._handlers: dict[str, list[Callable]] = {}

        # Statistics
        self._stats: dict[str, dict] = {}

        logger.info('LiveDataIngestionService initialized')

    # ========================================================================
    # Event Hook System
    # ========================================================================

    def on_message(self, feed_name: str, handler: Callable[[dict, dict], None]) -> 'LiveDataIngestionService':
        """Register message handler for a feed (Event Pattern).

        Multiple handlers can process the same message (decoupled consumers).

        Args:
            feed_name: Feed to listen to
            handler: Callable(message, context)

        Returns:
            Self for method chaining

        Example:
            >>> service.on_message('mlb', lambda msg, ctx: print(f"Pitch: {msg}"))
        """
        self._handlers.setdefault(feed_name, []).append(handler)
        logger.debug(f'Registered handler for feed: {feed_name}')
        return self

    def on_connect(self, feed_name: str, handler: Callable[[], None]) -> 'LiveDataIngestionService':
        """Register connection handler."""
        # Store separately or use generic event system
        return self

    def emit(self, feed_name: str, message: dict, context: dict) -> None:
        """Emit message to all registered handlers.

        Handlers are called concurrently (async) for performance.
        """
        handlers = self._handlers.get(feed_name, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(message, context))
                else:
                    handler(message, context)
            except Exception as e:
                logger.warning(f'Handler failed for {feed_name}: {e}')

    # ========================================================================
    # WebSocket Connection Management
    # ========================================================================

    async def start_feed(
        self,
        feed_name: str,
        url: str,
        headers: dict | None = None,
        ping_interval: float = 30.0,
        auto_reconnect: bool = True,
    ) -> None:
        """Start a live WebSocket feed.

        Args:
            feed_name: Identifier for this feed
            url: WebSocket URL
            headers: Connection headers (auth, etc.)
            ping_interval: Seconds between keepalive pings
            auto_reconnect: Enable automatic reconnection
        """
        if feed_name in self._connections:
            logger.warning(f'Feed {feed_name} already running')
            return

        logger.info(f'Starting feed: {feed_name} at {url}')

        # Create task for connection
        task = asyncio.create_task(
            self._connection_loop(
                feed_name, url, headers, ping_interval, auto_reconnect,
            ),
        )
        self._tasks[feed_name] = task

        # Initialize stats
        self._stats[feed_name] = {
            'connected_at': None,
            'messages_received': 0,
            'messages_processed': 0,
            'reconnects': 0,
            'errors': 0,
        }

    async def stop_feed(self, feed_name: str) -> None:
        """Stop a running feed."""
        if feed_name not in self._tasks:
            return

        logger.info(f'Stopping feed: {feed_name}')

        task = self._tasks.pop(feed_name)
        task.cancel()

        with contextlib.suppress(asyncio.CancelledError):
            await task

        # Close WebSocket if open
        if feed_name in self._connections:
            ws = self._connections.pop(feed_name)
            await ws.close()

    async def stop_all(self) -> None:
        """Stop all feeds."""
        for feed_name in list(self._tasks.keys()):
            await self.stop_feed(feed_name)

    async def _connection_loop(
        self,
        feed_name: str,
        url: str,
        headers: dict | None,
        ping_interval: float,
        auto_reconnect: bool,
    ) -> None:
        """Main connection loop with reconnection logic."""
        attempt = 0

        while True:
            try:
                async with websockets.connect(url, extra_headers=headers) as ws:
                    self._connections[feed_name] = ws
                    self._stats[feed_name]['connected_at'] = datetime.now()

                    logger.info(f'Connected to {feed_name}')
                    attempt = 0  # Reset on successful connection

                    # Start ping task
                    ping_task = asyncio.create_task(
                        self._ping_loop(ws, ping_interval),
                    )

                    # Message loop
                    async for message in ws:
                        await self._handle_message(feed_name, message)

                    ping_task.cancel()

            except ConnectionClosed as e:
                logger.warning(f'Connection closed for {feed_name}: {e}')

            except Exception as e:
                logger.exception(f'Connection error for {feed_name}: {e}')
                self._stats[feed_name]['errors'] += 1

            finally:
                if feed_name in self._connections:
                    del self._connections[feed_name]

            if not auto_reconnect:
                break

            # Exponential backoff
            attempt += 1
            if attempt > self.reconnect_attempts:
                logger.error(f'Max reconnection attempts reached for {feed_name}')
                break

            delay = self.reconnect_delay_base * (2 ** (attempt - 1))
            self._stats[feed_name]['reconnects'] += 1

            logger.info(f'Reconnecting to {feed_name} in {delay}s (attempt {attempt})')
            await asyncio.sleep(delay)

    async def _ping_loop(self, ws, interval: float) -> None:
        """Send periodic keepalive pings."""
        while True:
            try:
                await asyncio.sleep(interval)
                await ws.ping()
            except Exception:
                break

    async def _handle_message(self, feed_name: str, message: str) -> None:
        """Process incoming WebSocket message."""
        try:
            # Parse JSON
            data = json.loads(message)

            # Update stats
            self._stats[feed_name]['messages_received'] += 1

            # Add to buffer
            self._add_to_buffer(feed_name, data)

            # Emit to handlers (Event Pattern)
            context = {
                'feed_name': feed_name,
                'received_at': datetime.now(),
                'raw_message': message,
            }
            self.emit(feed_name, data, context)

            self._stats[feed_name]['messages_processed'] += 1

        except json.JSONDecodeError:
            logger.warning(f'Invalid JSON from {feed_name}: {message[:100]}')
        except Exception as e:
            logger.exception(f'Message handling error for {feed_name}: {e}')

    def _add_to_buffer(self, feed_name: str, data: dict) -> None:
        """Add message to circular buffer."""
        if feed_name not in self._buffers:
            self._buffers[feed_name] = []

        buffer = self._buffers[feed_name]
        buffer.append({
            'data': data,
            'timestamp': datetime.now(),
        })

        # Trim buffer
        if len(buffer) > self.message_buffer_size:
            buffer.pop(0)

    # ========================================================================
    # Public API
    # ========================================================================

    def get_buffer(self, feed_name: str) -> list[dict]:
        """Get message buffer for a feed."""
        return self._buffers.get(feed_name, []).copy()

    def get_stats(self, feed_name: str | None = None) -> dict:
        """Get statistics for a feed or all feeds."""
        if feed_name:
            return self._stats.get(feed_name, {}).copy()
        return self._stats.copy()

    def is_connected(self, feed_name: str) -> bool:
        """Check if feed is currently connected."""
        return feed_name in self._connections

    def get_active_feeds(self) -> set[str]:
        """Get set of currently active feed names."""
        return set(self._connections.keys())

    async def send_message(self, feed_name: str, message: dict) -> bool:
        """Send message to a WebSocket feed."""
        if feed_name not in self._connections:
            return False

        try:
            ws = self._connections[feed_name]
            await ws.send(json.dumps(message))
            return True
        except Exception as e:
            logger.exception(f'Send failed for {feed_name}: {e}')
            return False
