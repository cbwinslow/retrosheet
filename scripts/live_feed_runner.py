#!/usr/bin/env python3
"""
Live Feed Runner - Complete real-time MLB data ingestion system

Orchestrates the smart scheduler to continuously ingest live MLB game data
with adaptive polling rates based on game schedule.

Usage:
    python scripts/live_feed_runner.py
    python scripts/live_feed_runner.py --daemon
    python scripts/live_feed_runner.py --once  # Single run, no loop
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from baseball.ingestion.smart_scheduler import SmartScheduler, PollingSchedule
from baseball.utils.logging_config import get_logger

logger = get_logger(__name__)


class LiveFeedDaemon:
    """Daemon wrapper for live feed ingestion."""
    
    def __init__(self, schedule: PollingSchedule = None):
        self.scheduler = SmartScheduler(schedule=schedule)
        self._shutdown_event = asyncio.Event()
        
    async def run(self):
        """Run the live feed daemon."""
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._signal_handler)
        
        logger.info("Starting Live Feed Daemon")
        
        try:
            await self.scheduler.start()
            await self._shutdown_event.wait()  # Wait for shutdown signal
        except asyncio.CancelledError:
            logger.info("Daemon cancelled")
        finally:
            await self.scheduler.stop()
            logger.info("Live Feed Daemon stopped")
    
    def _signal_handler(self):
        """Handle shutdown signals."""
        logger.info("Shutdown signal received")
        self._shutdown_event.set()


async def run_single_ingestion():
    """Run a single ingestion pass (no daemon mode)."""
    from scripts.data_ingestion.ingest_live_games import main as ingest_main
    
    logger.info("Running single live feed ingestion")
    
    # Set up argparse args for single run
    class Args:
        active = True
        game_pk = None
        continuous = False
    
    # Call the ingestion main
    return ingest_main()


def main():
    parser = argparse.ArgumentParser(
        description='Live Feed Runner - Real-time MLB data ingestion'
    )
    parser.add_argument(
        '--daemon', '-d',
        action='store_true',
        help='Run as continuous daemon with adaptive polling'
    )
    parser.add_argument(
        '--once', '-o',
        action='store_true',
        help='Run single ingestion pass and exit'
    )
    parser.add_argument(
        '--active', '-a',
        action='store_true',
        help='Ingest only active games'
    )
    parser.add_argument(
        '--game-pk', '-g',
        type=int,
        help='Specific game PK to ingest'
    )
    parser.add_argument(
        '--pre-game-minutes', '-p',
        type=int,
        default=60,
        help='Minutes before game to start polling (default: 60)'
    )
    parser.add_argument(
        '--in-game-interval', '-i',
        type=int,
        default=10,
        help='Polling interval in seconds during games (default: 10)'
    )
    parser.add_argument(
        '--off-hours-interval', '-f',
        type=int,
        default=3600,
        help='Polling interval in seconds off-hours (default: 3600)'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.once or not args.daemon:
        # Single run mode
        if args.game_pk:
            # Specific game
            from scripts.data_ingestion.ingest_live_games import fetch_live_game
            result = fetch_live_game(args.game_pk)
            status = "success" if result else "failed"
            logger.info(f"Game {args.game_pk}: {status}")
        elif args.active:
            # All active games
            from scripts.data_ingestion.ingest_live_games import main as ingest_main
            ingest_main()
        else:
            parser.print_help()
            sys.exit(1)
    else:
        # Daemon mode with adaptive polling
        schedule = PollingSchedule(
            in_game=args.in_game_interval,
            off_hours=args.off_hours_interval,
            pre_game_minutes=args.pre_game_minutes
        )
        
        daemon = LiveFeedDaemon(schedule=schedule)
        
        try:
            asyncio.run(daemon.run())
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.exception("Fatal error in daemon")
            sys.exit(1)


if __name__ == '__main__':
    main()
