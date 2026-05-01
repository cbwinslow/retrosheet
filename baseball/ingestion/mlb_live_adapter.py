"""MLB Stats API Live Feed Ingestion Adapter.

Integrates LiveMlbSource with BaseIngestionSource for real-time
game data ingestion into the betting pipeline.

Author: Agent Cascade
Date: 2026-04-30
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from baseball.ingestion.base import BaseIngestionSource, IngestionResult
from baseball.sources.live_mlb import LiveMlbSource


logger = logging.getLogger(__name__)


class MlbLiveIngestionSource(BaseIngestionSource):
    """Ingestion source adapter for MLB Stats API live feed.

    Polls the MLB Stats API for game state updates and yields
    transformed data for the betting pipeline.

    Example:
        >>> source = MlbLiveIngestionSource(game_pk=716190, poll_interval=5)
        >>> async for update in source.stream():
        ...     print(f"Inning {update['state']['inning']}")
    """

    def __init__(
        self,
        game_pk: int,
        poll_interval: int = 10,
        transform_fn: Callable | None = None,
        filter_fn: Callable | None = None,
        name: str = 'mlb_live',
    ) -> None:
        """Initialize MLB live ingestion source.

        Args:
            game_pk: MLB game identifier
            poll_interval: Seconds between polls (default: 10)
            transform_fn: Optional transform function for delegate pattern
            filter_fn: Optional filter function for delegate pattern
            name: Source name identifier
        """
        super().__init__(
            name=name,
            source_type='live_feed',
            transform_fn=transform_fn,
            filter_fn=filter_fn,
        )
        self.game_pk = game_pk
        self.poll_interval = poll_interval
        self._live_source = LiveMlbSource(
            game_pk=game_pk,
            poll_interval=poll_interval,
        )
        self._last_state: dict | None = None
        self._update_count = 0

        logger.info(f'Initialized MLB live source for game {game_pk}')

    async def fetch(self) -> dict[str, Any] | None:
        """Fetch current game state from MLB API.

        Returns:
            Raw game data or None if no update/error
        """
        try:
            # Run blocking I/O in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,  # Default executor
                self._live_source.poll,
                self.game_pk,
            )

            if result is None:
                return None

            # Transform to canonical format
            ingest_result = self._live_source.ingest(result)

            if not ingest_result.success:
                logger.warning(f'Ingest failed: {ingest_result.error}')
                return None

            return ingest_result.data

        except Exception as e:
            logger.exception(f'Error fetching game {self.game_pk}: {e}')
            return None

    async def stream(self, duration: int | None = None):
        """Async generator yielding game state updates.

        Args:
            duration: Optional max duration in seconds

        Yields:
            Dict with game state and metadata
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            current_time = asyncio.get_event_loop().time()

            if duration and (current_time - start_time) > duration:
                logger.info(f'Stream duration reached: {duration}s')
                break

            # Fetch update
            data = await self.fetch()

            if data:
                self._update_count += 1

                # Apply transform delegate if provided
                if self.transform_fn:
                    data = self.transform_fn(data)

                # Apply filter delegate if provided
                if self.filter_fn and not self.filter_fn(data):
                    continue

                # Create result
                result = IngestionResult(
                    success=True,
                    data=data,
                    source_name=self.name,
                    timestamp=datetime.utcnow().isoformat(),
                )

                # Trigger event hook
                await self._trigger_event('on_data', data)

                yield result

            # Wait for next poll
            await asyncio.sleep(self.poll_interval)

    def get_status(self) -> dict[str, Any]:
        """Get current source status.

        Returns:
            Status dict with connection and update info
        """
        return {
            'name': self.name,
            'game_pk': self.game_pk,
            'poll_interval': self.poll_interval,
            'updates_received': self._update_count,
            'connected': True,
            'status': 'streaming' if self._update_count > 0 else 'waiting',
        }


class MlbScheduleIngestionSource(BaseIngestionSource):
    """Ingestion source for MLB schedule/today's games.

    Fetches all live/preview games for current day.
    Useful for discovering what games are available.

    Example:
        >>> source = MlbScheduleIngestionSource()
        >>> result = await source.fetch_today()
        >>> for game in result['games']:
        ...     print(f"Game {game['game_pk']}: {game['status']}")
    """

    def __init__(
        self,
        transform_fn: Callable | None = None,
        filter_fn: Callable | None = None,
        name: str = 'mlb_schedule',
    ) -> None:
        """Initialize schedule ingestion source."""
        super().__init__(
            name=name,
            source_type='schedule',
            transform_fn=transform_fn,
            filter_fn=filter_fn,
        )
        self._live_source = LiveMlbSource(poll_interval=60)

        logger.info('Initialized MLB schedule source')

    async def fetch_today(self) -> IngestionResult:
        """Fetch today's schedule with live game detection.

        Returns:
            IngestionResult with list of games
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._live_source.download,
            )

            if not result.success:
                return IngestionResult(
                    success=False,
                    error=result.error,
                    source_name=self.name,
                )

            data = result.data
            games = []

            # Extract games from schedule
            for date_info in data.get('dates', []):
                for game in date_info.get('games', []):
                    status = game.get('status', {}).get('abstractGameCode', 'U')
                    games.append({
                        'game_pk': game.get('gamePk'),
                        'status': status,
                        'home_team': game.get('teams', {}).get('home', {}).get('team', {}).get('name'),
                        'away_team': game.get('teams', {}).get('away', {}).get('team', {}).get('name'),
                        'start_time': game.get('gameDate'),
                        'is_live': status == 'L',
                        'is_preview': status == 'P',
                    })

            # Apply filters
            if self.filter_fn:
                games = [g for g in games if self.filter_fn(g)]

            # Apply transform
            if self.transform_fn:
                games = self.transform_fn(games)

            return IngestionResult(
                success=True,
                data={'games': games, 'count': len(games)},
                source_name=self.name,
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            logger.exception(f'Error fetching schedule: {e}')
            return IngestionResult(
                success=False,
                error=str(e),
                source_name=self.name,
            )

    def get_live_games(self, result: IngestionResult) -> list[dict]:
        """Extract live games from schedule result.

        Args:
            result: IngestionResult from fetch_today()

        Returns:
            List of live game dicts
        """
        if not result.success or not result.data:
            return []

        games = result.data.get('games', [])
        return [g for g in games if g.get('is_live')]


# Convenience functions for common use cases

async def stream_game_state(
    game_pk: int,
    on_update: Callable | None = None,
    duration: int | None = None,
    poll_interval: int = 10,
) -> None:
    """Stream game state updates with callback.

    Args:
        game_pk: Game to monitor
        on_update: Callback function(state_dict)
        duration: Max duration in seconds
        poll_interval: Seconds between polls

    Example:
        >>> async def handle_update(state):
        ...     print(f"Score: {state['score_home']}-{state['score_away']}")
        >>> await stream_game_state(716190, handle_update, duration=300)
    """
    source = MlbLiveIngestionSource(
        game_pk=game_pk,
        poll_interval=poll_interval,
    )

    async for result in source.stream(duration=duration):
        if result.success and on_update:
            await on_update(result.data)


async def get_todays_live_games() -> list[dict]:
    """Get list of currently live games.

    Returns:
        List of game dicts with game_pk, teams, status

    Example:
        >>> games = await get_todays_live_games()
        >>> for g in games:
        ...     print(f"Live: {g['away_team']} @ {g['home_team']}")
    """
    source = MlbScheduleIngestionSource()
    result = await source.fetch_today()

    if not result.success:
        logger.error(f'Failed to fetch schedule: {result.error}')
        return []

    return source.get_live_games(result)
