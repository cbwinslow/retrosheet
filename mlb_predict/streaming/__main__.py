#!/usr/bin/env python3
"""Entry point for MLB Live Prediction WebSocket Server.

Usage:
    python -m mlb_predict.streaming.server
    python -m mlb_predict.streaming.server --host localhost --port 8765

Environment Variables:
    WEBSOCKET_HOST: Server host (default: localhost)
    WEBSOCKET_PORT: Server port (default: 8765)
    POLL_INTERVAL: Game polling interval in seconds (default: 10.0)
    MAX_CLIENTS: Maximum concurrent clients (default: 1000)
    LOG_LEVEL: Logging level (default: INFO)

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import argparse
import asyncio
import logging
import os
import sys

from .server import PredictionWebSocketServer


def setup_logging(log_level: str) -> None:
    """Configure logging for the server."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> int:
    """Main entry point for the WebSocket server."""
    parser = argparse.ArgumentParser(
        description='MLB Live Prediction WebSocket Server',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        '--host',
        type=str,
        default=os.getenv('WEBSOCKET_HOST', 'localhost'),
        help='Server host address',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('WEBSOCKET_PORT', '8765')),
        help='Server port',
    )
    parser.add_argument(
        '--interval',
        type=float,
        default=float(os.getenv('POLL_INTERVAL', '10.0')),
        help='Game polling interval in seconds',
    )
    parser.add_argument(
        '--max-clients',
        type=int,
        default=int(os.getenv('MAX_CLIENTS', '1000')),
        help='Maximum concurrent clients',
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default=os.getenv('LOG_LEVEL', 'INFO'),
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Logging level',
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # Log startup info
    logger.info('Starting MLB Live Prediction WebSocket Server')
    logger.info(f'Host: {args.host}:{args.port}')
    logger.info(f'Poll interval: {args.interval}s')
    logger.info(f'Max clients: {args.max_clients}')

    # Create and start server
    server = PredictionWebSocketServer(
        host=args.host,
        port=args.port,
        poll_interval=args.interval,
        max_clients=args.max_clients,
    )

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info('Server stopped by user')
        return 0
    except Exception as e:
        logger.error(f'Server error: {e}', exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
