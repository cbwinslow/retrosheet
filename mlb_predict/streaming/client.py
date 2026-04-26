"""WebSocket client for consuming live MLB prediction streams.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any


try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False


logger = logging.getLogger(__name__)


class PredictionStreamClient:
    """WebSocket client for streaming MLB predictions.

    Usage:
        client = PredictionStreamClient("ws://localhost:8765")

        @client.on_prediction
        def handle_prediction(data):
            print(f"Home win prob: {data['prediction']['home_win_probability']}")

        await client.connect()
        await client.subscribe(12345)  # game_pk
    """

    def __init__(self, uri: str = 'ws://localhost:8765'):
        self.uri = uri
        self._websocket: WebSocketClientProtocol | None = None
        self._connected = False
        self._subscribed_games: set[int] = set()

        # Callbacks
        self._on_prediction: Callable[[dict[str, Any]], None] | None = None
        self._on_connect: Callable[[], None] | None = None
        self._on_disconnect: Callable[[], None] | None = None
        self._on_error: Callable[[str], None] | None = None

    def on_prediction(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register callback for prediction updates."""
        self._on_prediction = callback

    def on_connect(self, callback: Callable[[], None]) -> None:
        """Register callback for connection established."""
        self._on_connect = callback

    def on_disconnect(self, callback: Callable[[], None]) -> None:
        """Register callback for disconnection."""
        self._on_disconnect = callback

    def on_error(self, callback: Callable[[str], None]) -> None:
        """Register callback for errors."""
        self._on_error = callback

    async def connect(self) -> None:
        """Connect to the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            raise RuntimeError('websockets package not installed')

        try:
            self._websocket = await websockets.connect(self.uri)
            self._connected = True

            if self._on_connect:
                self._on_connect()

            # Start message handler
            asyncio.create_task(self._message_loop())

            logger.info(f'Connected to {self.uri}')

        except Exception as e:
            logger.error(f'Connection failed: {e}')
            if self._on_error:
                self._on_error(str(e))
            raise

    async def disconnect(self) -> None:
        """Disconnect from the server."""
        if self._websocket:
            await self._websocket.close()
            self._connected = False
            self._websocket = None

            if self._on_disconnect:
                self._on_disconnect()

    async def subscribe(self, game_pk: int) -> None:
        """Subscribe to predictions for a game."""
        if not self._connected:
            raise RuntimeError('Not connected')

        await self._send({
            'command': 'subscribe',
            'game_pk': game_pk,
        })
        self._subscribed_games.add(game_pk)

    async def unsubscribe(self, game_pk: int | None = None) -> None:
        """Unsubscribe from a game (or all games if game_pk is None)."""
        if not self._connected:
            return

        await self._send({
            'command': 'unsubscribe',
            'game_pk': game_pk,
        })

        if game_pk:
            self._subscribed_games.discard(game_pk)
        else:
            self._subscribed_games.clear()

    async def get_games(self) -> dict[str, Any]:
        """Get list of active games."""
        if not self._connected:
            raise RuntimeError('Not connected')

        await self._send({'command': 'games'})

        # Wait for response
        # This is a simplified version - in production use a request/response pattern
        return {}

    async def _send(self, message: dict[str, Any]) -> None:
        """Send a message to the server."""
        if self._websocket:
            await self._websocket.send(json.dumps(message))

    async def _message_loop(self) -> None:
        """Main loop for receiving messages."""
        try:
            async for message in self._websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.error(f'Invalid JSON: {message}')
        except websockets.exceptions.ConnectionClosed:
            logger.info('Connection closed')
            self._connected = False
            if self._on_disconnect:
                self._on_disconnect()
        except Exception as e:
            logger.error(f'Error in message loop: {e}')
            if self._on_error:
                self._on_error(str(e))

    async def _handle_message(self, data: dict[str, Any]) -> None:
        """Handle a message from the server."""
        msg_type = data.get('type')

        if msg_type == 'prediction':
            if self._on_prediction:
                self._on_prediction(data)

        elif msg_type == 'error':
            logger.error(f"Server error: {data.get('message')}")
            if self._on_error:
                self._on_error(data.get('message', 'Unknown error'))

        elif msg_type == 'connected':
            logger.info(f"Server: {data.get('message')}")

        elif msg_type == 'subscribed':
            logger.info(f"Subscribed to game {data.get('game_pk')}")

        elif msg_type == 'pong':
            pass  # Heartbeat response
