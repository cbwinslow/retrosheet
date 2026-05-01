"""WebSocket server for real-time prediction updates.

Provides real-time WebSocket connections for:
- Live game prediction streams
- Score updates
- Model prediction updates
- Client subscription management

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

from websockets.server import WebSocketServerProtocol, serve


logger = logging.getLogger(__name__)


@dataclass
class ClientSubscription:
    """Client subscription configuration.

    Attributes:
        client_id: Unique client identifier
        game_pk: Game to subscribe to (None = all games)
        prediction_types: Types of predictions to receive
        websocket: WebSocket connection
    """

    client_id: str
    game_pk: int | None
    prediction_types: set[str]  # 'next_run', 'pa_outcome', etc.
    websocket: WebSocketServerProtocol


class WebSocketServer:
    """WebSocket server for real-time prediction streaming.

    Manages client connections and broadcasts predictions.
    Supports subscriptions by game and prediction type.

    Example:
        >>> server = WebSocketServer(model_server=ms)
        >>> await server.start(host='0.0.0.0', port=8765)
        >>> # Broadcast prediction
        >>> await server.broadcast_prediction(game_pk=777777, prediction={...})
    """

    def __init__(self, model_server=None, host: str = '0.0.0.0', port: int = 8765) -> None:
        """Initialize WebSocket server.

        Args:
            model_server: Model server for predictions
            host: Host to bind to
            port: Port to listen on
        """
        self.model_server = model_server
        self.host = host
        self.port = port

        # Client management
        self._clients: dict[str, WebSocketServerProtocol] = {}
        self._subscriptions: dict[str, ClientSubscription] = {}
        self._game_subscribers: dict[int, set[str]] = {}  # game_pk -> client_ids

        # Server state
        self._running = False
        self._server = None

    async def start(self) -> None:
        """Start the WebSocket server."""
        logger.info(f'Starting WebSocket server on {self.host}:{self.port}')
        self._running = True

        async with serve(self._handle_client, self.host, self.port):
            logger.info('WebSocket server started')
            await asyncio.Future()  # Run forever

    def stop(self) -> None:
        """Stop the WebSocket server."""
        logger.info('Stopping WebSocket server')
        self._running = False

    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """Handle a new client connection.

        Args:
            websocket: WebSocket connection
            path: Connection path
        """
        client_id = f'{websocket.remote_address[0]}:{websocket.remote_address[1]}'
        logger.info(f'Client connected: {client_id}')

        self._clients[client_id] = websocket

        try:
            async for message in websocket:
                await self._process_message(client_id, websocket, message)
        except Exception as e:
            logger.exception(f'Client error {client_id}: {e}')
        finally:
            await self._disconnect_client(client_id)

    async def _process_message(
        self, client_id: str, websocket: WebSocketServerProtocol, message: str,
    ) -> None:
        """Process a message from a client.

        Args:
            client_id: Client identifier
            websocket: WebSocket connection
            message: JSON message
        """
        try:
            data = json.loads(message)
            msg_type = data.get('type', 'unknown')

            if msg_type == 'subscribe':
                await self._handle_subscribe(client_id, websocket, data)
            elif msg_type == 'unsubscribe':
                await self._handle_unsubscribe(client_id, data)
            elif msg_type == 'predict':
                await self._handle_predict_request(client_id, websocket, data)
            elif msg_type == 'ping':
                await websocket.send(json.dumps({'type': 'pong'}))
            else:
                await websocket.send(
                    json.dumps(
                        {
                            'type': 'error',
                            'message': f'Unknown message type: {msg_type}',
                        },
                    ),
                )

        except json.JSONDecodeError:
            await websocket.send(
                json.dumps(
                    {
                        'type': 'error',
                        'message': 'Invalid JSON',
                    },
                ),
            )
        except Exception as e:
            logger.exception(f'Error processing message from {client_id}: {e}')
            await websocket.send(
                json.dumps(
                    {
                        'type': 'error',
                        'message': str(e),
                    },
                ),
            )

    async def _handle_subscribe(
        self, client_id: str, websocket: WebSocketServerProtocol, data: dict,
    ) -> None:
        """Handle subscription request.

        Args:
            client_id: Client identifier
            websocket: WebSocket connection
            data: Subscription data
        """
        game_pk = data.get('game_pk')
        prediction_types = set(data.get('prediction_types', ['next_run', 'pa_outcome']))

        # Create subscription
        subscription = ClientSubscription(
            client_id=client_id,
            game_pk=game_pk,
            prediction_types=prediction_types,
            websocket=websocket,
        )

        self._subscriptions[client_id] = subscription

        # Add to game subscribers
        if game_pk:
            if game_pk not in self._game_subscribers:
                self._game_subscribers[game_pk] = set()
            self._game_subscribers[game_pk].add(client_id)

        logger.info(f'Client {client_id} subscribed to game {game_pk}')

        # Confirm subscription
        await websocket.send(
            json.dumps(
                {
                    'type': 'subscribed',
                    'client_id': client_id,
                    'game_pk': game_pk,
                    'prediction_types': list(prediction_types),
                },
            ),
        )

    async def _handle_unsubscribe(self, client_id: str, data: dict) -> None:
        """Handle unsubscription request."""
        subscription = self._subscriptions.get(client_id)

        if subscription:
            # Remove from game subscribers
            if subscription.game_pk and subscription.game_pk in self._game_subscribers:
                self._game_subscribers[subscription.game_pk].discard(client_id)

            del self._subscriptions[client_id]
            logger.info(f'Client {client_id} unsubscribed')

    async def _handle_predict_request(
        self, client_id: str, websocket: WebSocketServerProtocol, data: dict,
    ) -> None:
        """Handle prediction request from client.

        Args:
            client_id: Client identifier
            websocket: WebSocket connection
            data: Prediction request data
        """
        if not self.model_server:
            await websocket.send(
                json.dumps(
                    {
                        'type': 'error',
                        'message': 'Model server not available',
                    },
                ),
            )
            return

        model_name = data.get('model', 'next_run')
        features = data.get('features', {})
        request_id = data.get('request_id')

        # Make prediction
        result = self.model_server.predict(model_name, features)

        if result:
            response = {
                'type': 'prediction',
                'model': model_name,
                'result': result,
                'request_id': request_id,
            }
        else:
            response = {
                'type': 'error',
                'message': 'Prediction failed',
                'request_id': request_id,
            }

        await websocket.send(json.dumps(response))

    async def _disconnect_client(self, client_id: str) -> None:
        """Handle client disconnection."""
        logger.info(f'Client disconnected: {client_id}')

        # Clean up subscriptions
        subscription = self._subscriptions.get(client_id)
        if subscription:
            if subscription.game_pk and subscription.game_pk in self._game_subscribers:
                self._game_subscribers[subscription.game_pk].discard(client_id)
            del self._subscriptions[client_id]

        # Remove client
        if client_id in self._clients:
            del self._clients[client_id]

    async def broadcast_prediction(self, game_pk: int, prediction: dict[str, Any]) -> int:
        """Broadcast prediction to subscribed clients.

        Args:
            game_pk: Game ID
            prediction: Prediction data

        Returns:
            Number of clients notified
        """
        if game_pk not in self._game_subscribers:
            return 0

        message = json.dumps(
            {
                'type': 'prediction_update',
                'game_pk': game_pk,
                'prediction': prediction,
                'timestamp': asyncio.get_event_loop().time(),
            },
        )

        notified = 0
        disconnected = []

        for client_id in self._game_subscribers[game_pk]:
            subscription = self._subscriptions.get(client_id)
            if not subscription:
                continue

            # Check if client wants this prediction type
            pred_type = prediction.get('model', 'unknown')
            if pred_type not in subscription.prediction_types:
                continue

            try:
                await subscription.websocket.send(message)
                notified += 1
            except Exception as e:
                logger.warning(f'Failed to send to {client_id}: {e}')
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            await self._disconnect_client(client_id)

        return notified

    async def broadcast_game_update(self, game_pk: int, update: dict[str, Any]) -> int:
        """Broadcast general game update to subscribers.

        Args:
            game_pk: Game ID
            update: Update data

        Returns:
            Number of clients notified
        """
        if game_pk not in self._game_subscribers:
            return 0

        message = json.dumps(
            {
                'type': 'game_update',
                'game_pk': game_pk,
                'update': update,
                'timestamp': asyncio.get_event_loop().time(),
            },
        )

        notified = 0
        disconnected = []

        for client_id in self._game_subscribers[game_pk]:
            subscription = self._subscriptions.get(client_id)
            if not subscription:
                continue

            try:
                await subscription.websocket.send(message)
                notified += 1
            except Exception as e:
                logger.warning(f'Failed to send to {client_id}: {e}')
                disconnected.append(client_id)

        for client_id in disconnected:
            await self._disconnect_client(client_id)

        return notified

    def get_stats(self) -> dict[str, Any]:
        """Get server statistics.

        Returns:
            Statistics dictionary
        """
        return {
            'connected_clients': len(self._clients),
            'subscriptions': len(self._subscriptions),
            'games_watched': len(self._game_subscribers),
            'running': self._running,
        }


# For direct execution
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='WebSocket Server for Predictions')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind')
    parser.add_argument('--port', type=int, default=8765, help='Port to bind')

    args = parser.parse_args()

    # Create and start server
    server = WebSocketServer(host=args.host, port=args.port)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info('Server stopped by user')
