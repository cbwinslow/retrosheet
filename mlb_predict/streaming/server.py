"""WebSocket server for real-time prediction streaming.

This module provides WebSocket infrastructure for streaming live
MLB game predictions to connected clients.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any


try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from mlb_predict.pipeline.live_prediction import LiveGameContext, LivePredictionPipeline
from mlb_predict.sources import LiveMlbSource


logger = logging.getLogger(__name__)


class PredictionWebSocketServer:
    """WebSocket server for streaming live MLB predictions.

    Features:
    - Multi-client support
    - Per-game subscription
    - Automatic state polling
    - JSON message format
    - Heartbeat/ping-pong

    Usage:
        server = PredictionWebSocketServer(host="localhost", port=8765)
        await server.start()
    """

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 8765,
        poll_interval: float = 10.0,
    ):
        self.host = host
        self.port = port
        self.poll_interval = poll_interval

        self._pipeline: LivePredictionPipeline | None = None
        self._live_source: LiveMlbSource | None = None

        # Connected clients: websocket -> {game_pks: Set[int], last_ping: float}
        self._clients: dict[WebSocketServerProtocol, dict[str, Any]] = {}

        # Active game subscriptions: game_pk -> Set[websocket]
        self._subscriptions: dict[int, set[WebSocketServerProtocol]] = {}

        # Last known state for each game
        self._last_states: dict[int, dict[str, Any]] = {}

        self._server = None
        self._running = False
        self._poll_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            raise RuntimeError('websockets package not installed. Run: uv add websockets')

        # Initialize pipeline
        self._pipeline = LivePredictionPipeline(cache_ttl_seconds=self.poll_interval)
        self._pipeline.load_model()
        self._live_source = LiveMlbSource()

        # Start server
        self._server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10,
        )

        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())

        logger.info(f'WebSocket server started on ws://{self.host}:{self.port}')

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        self._running = False

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        # Close all client connections
        for ws in list(self._clients.keys()):
            await ws.close()

        if self._server:
            self._server.close()
            await self._server.wait_closed()

        logger.info('WebSocket server stopped')

    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """Handle a new client connection."""
        client_id = id(websocket)
        logger.info(f'Client {client_id} connected from {websocket.remote_address}')

        # Register client
        self._clients[websocket] = {
            'game_pks': set(),
            'connected_at': datetime.now().isoformat(),
        }

        try:
            await self._send_message(websocket, {
                'type': 'connected',
                'message': 'Welcome to MLB Live Predictions',
                'commands': ['subscribe', 'unsubscribe', 'ping'],
            })

            # Handle messages from client
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_client_message(websocket, data)
                except json.JSONDecodeError:
                    await self._send_error(websocket, 'Invalid JSON')
                except Exception as e:
                    logger.error(f'Error processing message: {e}')
                    await self._send_error(websocket, str(e))

        except websockets.exceptions.ConnectionClosed:
            logger.info(f'Client {client_id} disconnected')
        finally:
            await self._unregister_client(websocket)

    async def _process_client_message(
        self,
        websocket: WebSocketServerProtocol,
        data: dict[str, Any],
    ) -> None:
        """Process a message from a client."""
        command = data.get('command')

        if command == 'subscribe':
            game_pk = data.get('game_pk')
            if game_pk:
                await self._subscribe(websocket, game_pk)
            else:
                await self._send_error(websocket, 'Missing game_pk')

        elif command == 'unsubscribe':
            game_pk = data.get('game_pk')
            if game_pk:
                await self._unsubscribe(websocket, game_pk)
            else:
                # Unsubscribe from all
                for pk in list(self._clients[websocket]['game_pks']):
                    await self._unsubscribe(websocket, pk)

        elif command == 'ping':
            await self._send_message(websocket, {'type': 'pong'})

        elif command == 'games':
            # Return list of active games
            games = self._live_source.get_active_games() if self._live_source else []
            await self._send_message(websocket, {
                'type': 'games',
                'games': [
                    {
                        'game_pk': g.game_pk,
                        'status': g.status,
                        'inning': g.inning,
                        'is_top': g.is_top,
                        'home_score': g.home_score,
                        'away_score': g.away_score,
                    }
                    for g in games
                ],
            })

        else:
            await self._send_error(websocket, f'Unknown command: {command}')

    async def _subscribe(
        self,
        websocket: WebSocketServerProtocol,
        game_pk: int,
    ) -> None:
        """Subscribe a client to a game."""
        self._clients[websocket]['game_pks'].add(game_pk)

        if game_pk not in self._subscriptions:
            self._subscriptions[game_pk] = set()
        self._subscriptions[game_pk].add(websocket)

        # Send initial state
        await self._poll_game(game_pk)

        await self._send_message(websocket, {
            'type': 'subscribed',
            'game_pk': game_pk,
        })

        logger.info(f'Client {id(websocket)} subscribed to game {game_pk}')

    async def _unsubscribe(
        self,
        websocket: WebSocketServerProtocol,
        game_pk: int,
    ) -> None:
        """Unsubscribe a client from a game."""
        self._clients[websocket]['game_pks'].discard(game_pk)
        self._subscriptions[game_pk].discard(websocket)

        if game_pk in self._subscriptions and not self._subscriptions[game_pk]:
            del self._subscriptions[game_pk]
            self._last_states.pop(game_pk, None)

        await self._send_message(websocket, {
            'type': 'unsubscribed',
            'game_pk': game_pk,
        })

    async def _unregister_client(self, websocket: WebSocketServerProtocol) -> None:
        """Unregister a client and clean up subscriptions."""
        if websocket not in self._clients:
            return

        # Remove from all subscriptions
        for game_pk in list(self._clients[websocket]['game_pks']):
            await self._unsubscribe(websocket, game_pk)

        del self._clients[websocket]

    async def _poll_loop(self) -> None:
        """Main polling loop for active games."""
        while self._running:
            try:
                # Poll each subscribed game
                for game_pk in list(self._subscriptions.keys()):
                    await self._poll_game(game_pk)

                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f'Error in poll loop: {e}')
                await asyncio.sleep(1)

    async def _poll_game(self, game_pk: int) -> None:
        """Poll a game and broadcast updates to subscribers."""
        if not self._live_source or not self._pipeline:
            return

        # Get current state
        state = self._live_source.poll_game(game_pk)
        if not state:
            return

        # Build context
        context = LiveGameContext(
            game_pk=state.game_pk,
            inning=state.inning,
            is_top=state.is_top,
            outs=state.outs,
            balls=state.balls,
            strikes=state.strikes,
            home_score=state.home_score,
            away_score=state.away_score,
            base_state=state.base_state,
            home_team_id=state.home_team_id,
            away_team_id=state.away_team_id,
            current_batter_id=state.current_batter_id,
            current_pitcher_id=state.current_pitcher_id,
        )

        # Check if state changed
        state_hash = f'{state.inning}_{state.is_top}_{state.outs}_{state.home_score}_{state.away_score}'
        if game_pk in self._last_states and self._last_states[game_pk].get('hash') == state_hash:
            return  # No change

        # Generate prediction
        result = self._pipeline.predict(context)

        # Update last state
        self._last_states[game_pk] = {
            'hash': state_hash,
            'state': state,
            'prediction': result,
        }

        # Broadcast to subscribers
        message = {
            'type': 'prediction',
            'game_pk': game_pk,
            'timestamp': datetime.now().isoformat(),
            'game_state': {
                'inning': state.inning,
                'is_top': state.is_top,
                'outs': state.outs,
                'balls': state.balls,
                'strikes': state.strikes,
                'home_score': state.home_score,
                'away_score': state.away_score,
                'base_state': state.base_state,
                'is_complete': state.is_complete,
            },
            'prediction': {
                'home_win_probability': result.home_win_probability,
                'away_win_probability': result.away_win_probability,
                'confidence': result.confidence,
                'model_version': result.model_version,
                'latency_ms': result.latency_ms,
            },
        }

        await self._broadcast(game_pk, message)

    async def _broadcast(self, game_pk: int, message: dict[str, Any]) -> None:
        """Broadcast a message to all subscribers of a game."""
        if game_pk not in self._subscriptions:
            return

        disconnected = []
        for ws in self._subscriptions[game_pk]:
            try:
                await self._send_message(ws, message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(ws)

        # Clean up disconnected clients
        for ws in disconnected:
            await self._unregister_client(ws)

    async def _send_message(
        self,
        websocket: WebSocketServerProtocol,
        message: dict[str, Any],
    ) -> None:
        """Send a JSON message to a client."""
        await websocket.send(json.dumps(message))

    async def _send_error(
        self,
        websocket: WebSocketServerProtocol,
        error: str,
    ) -> None:
        """Send an error message to a client."""
        await self._send_message(websocket, {
            'type': 'error',
            'message': error,
        })

    def get_stats(self) -> dict[str, Any]:
        """Get server statistics."""
        return {
            'connected_clients': len(self._clients),
            'active_subscriptions': len(self._subscriptions),
            'games_being_tracked': list(self._subscriptions.keys()),
            'pipeline_metrics': self._pipeline.get_metrics() if self._pipeline else {},
        }
