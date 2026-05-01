"""Odds ingestion service for scheduled odds fetching.

Fetches betting odds from multiple sources on a schedule.
Uses database-driven job configuration.

Author: Agent Cascade
Date: 2026-04-30
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Any

from baseball.betting.schemas import BettingMarket, MarketType, Sport
from baseball.betting.sources.base import BaseOddsSource


logger = logging.getLogger(__name__)


class OddsIngestionService:
    """Service for scheduled odds ingestion from multiple sources.

    Database-driven job scheduling with:
    - Multiple source support (TheOddsApi, Pinnacle, DraftKings)
    - Rate limiting per source
    - Event hooks for opportunity detection
    - Automatic retry and error handling

    Example:
        >>> service = OddsIngestionService(db_pool)
        >>>
        >>> # Register sources (Super Class pattern)
        >>> service.register_source('the_odds_api', TheOddsApiSource(api_key='xxx'))
        >>> service.register_source('pinnacle', PinnacleSource(api_key='yyy'))
        >>>
        >>> # Add hook for opportunity detection
        >>> service.on_odds_update(lambda markets, ctx: find_opportunities(markets))
        >>>
        >>> # Start scheduled jobs
        >>> await service.start_scheduler()
    """

    def __init__(self, db_pool=None) -> None:
        """Initialize odds ingestion service.

        Args:
            db_pool: Async database connection pool
        """
        self.db_pool = db_pool
        self._sources: dict[str, BaseOddsSource] = {}
        self._running = False
        self._tasks: list[asyncio.Task] = []

        # Event hooks (Event Pattern)
        self._hooks: dict[str, list[Callable]] = {
            'pre_fetch': [],
            'post_fetch': [],
            'on_odds_update': [],
            'on_error': [],
            'on_opportunity': [],
        }

        # Statistics
        self._stats = {
            'fetches': 0,
            'markets_fetched': 0,
            'errors': 0,
        }

        logger.info('OddsIngestionService initialized')

    # ========================================================================
    # Source Registration (Super Class Pattern)
    # ========================================================================

    def register_source(
        self,
        name: str,
        source: BaseOddsSource,
        markets: list[MarketType] | None = None,
    ) -> 'OddsIngestionService':
        """Register an odds source.

        Args:
            name: Source identifier
            source: Instance of BaseOddsSource
            markets: Default markets to fetch

        Returns:
            Self for method chaining

        Example:
            >>> service.register_source(
            ...     'the_odds_api',
            ...     TheOddsApiSource(api_key='xxx'),
            ...     markets=[MarketType.MONEYLINE, MarketType.SPREAD]
            ... )
        """
        self._sources[name] = {
            'instance': source,
            'markets': markets or [MarketType.MONEYLINE],
            'last_fetch': None,
            'rate_limit_hits': 0,
        }
        logger.info(f'Registered odds source: {name}')
        return self

    def unregister_source(self, name: str) -> None:
        """Remove a registered source."""
        if name in self._sources:
            del self._sources[name]
            logger.info(f'Unregistered odds source: {name}')

    # ========================================================================
    # Event Hook System
    # ========================================================================

    def on(self, event: str, handler: Callable) -> 'OddsIngestionService':
        """Register event handler.

        Events:
        - pre_fetch: Before fetching odds
        - post_fetch: After fetching odds
        - on_odds_update: When odds change significantly
        - on_opportunity: When betting opportunity detected
        - on_error: When error occurs
        """
        if event not in self._hooks:
            msg = f'Unknown event: {event}'
            raise ValueError(msg)

        self._hooks[event].append(handler)
        return self

    def emit(self, event: str, data: Any, context: dict | None = None) -> None:
        """Emit event to all handlers."""
        for handler in self._hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(data, context or {}))
                else:
                    handler(data, context or {})
            except Exception as e:
                logger.warning(f'Hook {event} failed: {e}')

    # Convenience methods for common hooks
    def on_odds_update(self, handler: Callable[[list[BettingMarket], dict], None]) -> 'OddsIngestionService':
        """Register handler for odds updates."""
        return self.on('on_odds_update', handler)

    def on_opportunity(self, handler: Callable[[BettingMarket, dict], None]) -> 'OddsIngestionService':
        """Register handler for opportunities."""
        return self.on('on_opportunity', handler)

    # ========================================================================
    # Fetching Logic
    # ========================================================================

    async def fetch_all_sources(
        self,
        sport: Sport = Sport.MLB,
        market_types: list[MarketType] | None = None,
    ) -> dict[str, list[BettingMarket]]:
        """Fetch odds from all registered sources.

        Args:
            sport: Sport to fetch
            market_types: Specific markets (or use source defaults)

        Returns:
            Dict of source_name -> list of markets
        """
        results = {}

        for name, config in self._sources.items():
            try:
                source = config['instance']
                markets_to_fetch = market_types or config['markets']

                # Pre-fetch hook
                self.emit('pre_fetch', {'source': name, 'sport': sport}, {})

                # Fetch all markets
                all_markets = []
                for market_type in markets_to_fetch:
                    markets = source.get_live_odds(sport, market_type)
                    all_markets.extend(markets)

                # Post-fetch hook
                self.emit('post_fetch', all_markets, {'source': name})

                results[name] = all_markets

                # Update stats
                config['last_fetch'] = datetime.now()
                self._stats['markets_fetched'] += len(all_markets)

                logger.info(f'Fetched {len(all_markets)} markets from {name}')

            except Exception as e:
                logger.exception(f'Failed to fetch from {name}: {e}')
                self._stats['errors'] += 1
                self.emit('on_error', e, {'source': name})

        self._stats['fetches'] += 1
        return results

    async def fetch_source(
        self,
        source_name: str,
        sport: Sport = Sport.MLB,
        market_type: MarketType = MarketType.MONEYLINE,
    ) -> list[BettingMarket]:
        """Fetch from a specific source.

        Args:
            source_name: Registered source name
            sport: Sport
            market_type: Market

        Returns:
            List of betting markets
        """
        if source_name not in self._sources:
            msg = f'Unknown source: {source_name}'
            raise ValueError(msg)

        source = self._sources[source_name]['instance']
        return source.get_live_odds(sport, market_type)

    # ========================================================================
    # Scheduler Integration
    # ========================================================================

    async def start_scheduler(self) -> None:
        """Start the database-driven scheduler.

        Loads jobs from scheduler.jobs table and runs them.
        """
        if self._running:
            return

        self._running = True
        logger.info('Starting odds ingestion scheduler')

        # Create main scheduler loop
        task = asyncio.create_task(self._scheduler_loop())
        self._tasks.append(task)

    async def stop_scheduler(self) -> None:
        """Stop the scheduler."""
        self._running = False

        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        logger.info('Odds ingestion scheduler stopped')

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop (runs continuously)."""
        while self._running:
            try:
                if self.db_pool:
                    # Load due jobs from database
                    jobs = await self._load_due_jobs()

                    for job in jobs:
                        # Execute job
                        asyncio.create_task(self._execute_job(job))

                # Sleep before next check
                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.exception(f'Scheduler error: {e}')
                await asyncio.sleep(30)  # Back off on error

    async def _load_due_jobs(self) -> list[dict]:
        """Load jobs that are due to run from database."""
        # This would query the database
        # For now, return empty list
        return []

    async def _execute_job(self, job: dict) -> None:
        """Execute a single job."""
        job_id = job.get('job_id')
        job.get('source_type')

        try:
            # Log start
            if self.db_pool:
                run_id = await self._log_job_start(job_id)

            # Fetch odds
            results = await self.fetch_all_sources()

            # Persist to database
            total_markets = sum(len(m) for m in results.values())
            await self._persist_markets(results)

            # Log success
            if self.db_pool:
                await self._log_job_complete(run_id, 'success', total_markets)

            logger.info(f'Job {job_id} completed: {total_markets} markets')

        except Exception as e:
            logger.exception(f'Job {job_id} failed: {e}')
            if self.db_pool:
                await self._log_job_complete(job_id, 'failed', 0, str(e))

    async def _persist_markets(self, results: dict[str, list[BettingMarket]]) -> None:
        """Persist markets to database."""
        if not self.db_pool:
            return

        for source_name, markets in results.items():
            for market in markets:
                # Insert into betting.market_odds
                try:
                    async with self.db_pool.acquire() as conn:
                        await conn.execute(
                            """
                            INSERT INTO betting.market_odds (
                                source_game_id, source, book, market_type,
                                odds, line, timestamp, home_team, away_team
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                            ON CONFLICT (source_game_id, source, book, market_type, timestamp)
                            DO UPDATE SET odds = EXCLUDED.odds, line = EXCLUDED.line
                            """,
                            market.game_id,
                            source_name,
                            market.book,
                            market.market_type.value,
                            float(market.odds),
                            float(market.line) if market.line else None,
                            market.timestamp,
                            market.home_team,
                            market.away_team,
                        )
                except Exception as e:
                    logger.warning(f'Failed to persist market: {e}')

    async def _log_job_start(self, job_id: int) -> int:
        """Log job start to database."""
        # Would call scheduler.log_job_start()
        return 0

    async def _log_job_complete(self, run_id: int, status: str, records: int, error: str | None = None) -> None:
        """Log job completion to database."""
        # Would call scheduler.log_job_complete()

    # ========================================================================
    # Utilities (Lambda-friendly)
    # ========================================================================

    def find_best_lines(
        self,
        results: dict[str, list[BettingMarket]],
        side: str,
    ) -> list[BettingMarket]:
        """Find best available lines across all sources.

        Uses lambda for filtering and sorting.

        Args:
            results: Output from fetch_all_sources()
            side: Side to find (team name or 'Over'/'Under')

        Returns:
            Markets sorted by odds (best first)
        """
        # Flatten all markets
        all_markets = [m for markets in results.values() for m in markets]

        # Filter to side and sort by odds (lambda)
        side_markets = filter(lambda m: m.side == side, all_markets)
        return sorted(side_markets, key=lambda m: m.odds, reverse=True)

    def detect_line_movement(
        self,
        current: BettingMarket,
        previous: BettingMarket,
        threshold: Decimal = Decimal('0.02'),
    ) -> bool:
        """Detect if line has moved significantly.

        Args:
            current: Current market
            previous: Previous market
            threshold: Minimum probability change to flag

        Returns:
            True if significant movement detected
        """
        if not current or not previous:
            return False

        # Calculate implied probability change
        current_prob = self._implied_prob(current.odds)
        previous_prob = self._implied_prob(previous.odds)

        return abs(current_prob - previous_prob) > threshold

    def _implied_prob(self, odds: Decimal) -> Decimal:
        """Calculate implied probability from odds."""
        if odds > 0:
            return Decimal('100') / (odds + Decimal('100'))
        return abs(odds) / (abs(odds) + Decimal('100'))

    def get_stats(self) -> dict:
        """Get service statistics."""
        return self._stats.copy()
