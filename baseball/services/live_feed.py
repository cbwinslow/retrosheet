"""Live Feed Polling Service.

Provides real-time game state polling with database persistence.
"""
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from baseball.core.db import get_db_connection
from baseball.sources.live_mlb import LiveMlbSource


@dataclass
class GameUpdate:
    """Represents a single game state update."""
    game_pk: int
    timestamp: datetime
    inning: int
    is_top: bool
    outs: int
    score_home: int
    score_away: int
    base_state: int
    home_win_prob: float | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


class LiveFeedPoller:
    """Polls MLB API for live game updates and persists to database."""

    def __init__(
        self,
        game_pk: int | None = None,
        poll_interval: int = 10,
        save_raw_snapshots: bool = True,
    ) -> None:
        self.game_pk = game_pk
        self.poll_interval = poll_interval
        self.save_raw = save_raw_snapshots
        self.source = LiveMlbSource(game_pk=game_pk, poll_interval=poll_interval)
        self._callbacks: list[Callable[[GameUpdate], None]] = []
        self._last_hashes: dict[int, str] = {}

    def add_callback(self, callback: Callable[[GameUpdate], None]) -> None:
        """Add callback to be called on each game update."""
        self._callbacks.append(callback)

    def poll(self) -> list[dict[str, Any]]:
        """Poll for updates. Returns list of updates found."""
        updates = []

        # Fetch live data
        result = self.source.download(game_pk=self.game_pk)
        if not result.success:
            return updates

        if self.game_pk:
            # Single game mode
            update = self._process_game(result.data)
            if update:
                updates.append(update)
        else:
            # All games mode
            for date_info in result.data.get('dates', []):
                for game in date_info.get('games', []):
                    game_update = self._process_game(game)
                    if game_update:
                        updates.append(game_update)

        return updates

    def _process_game(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Process single game data. Returns update if changed."""
        game_pk = data.get('gamePk') or data.get('gameData', {}).get('game', {}).get('pk')
        if not game_pk:
            return None

        # Check for changes
        content = json.dumps(data, sort_keys=True, default=str).encode()
        current_hash = hashlib.md5(content).hexdigest()

        if self._last_hashes.get(game_pk) == current_hash:
            return None  # No change

        self._last_hashes[game_pk] = current_hash

        # Extract state
        ingest = self.source.ingest(data)
        if not ingest.success:
            return None

        state = ingest.data.get('state', {})

        # Create update record
        update = GameUpdate(
            game_pk=game_pk,
            timestamp=datetime.utcnow(),
            inning=state.get('inning', 1),
            is_top=state.get('is_top', True),
            outs=state.get('outs', 0),
            score_home=state.get('score_home', 0),
            score_away=state.get('score_away', 0),
            base_state=state.get('base_state', 0),
            raw_data=data if self.save_raw else {},
        )

        # Save to database
        if self.save_raw:
            self._save_snapshot(game_pk, data, current_hash)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(update)
            except Exception:
                pass  # Don't let callbacks break polling

        return {
            'game_pk': game_pk,
            'update_type': 'game_state',
            'description': f"{update.score_away}-{update.score_home}, {update.inning}{'▲' if update.is_top else '▼'} {update.outs} outs",
            'timestamp': update.timestamp.isoformat(),
        }

    def _save_snapshot(self, game_pk: int, data: dict[str, Any], content_hash: str) -> None:
        """Save raw snapshot to database."""
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                # Check if table exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'raw_mlb'
                        AND table_name = 'live_feed_snapshots'
                    )
                """)
                exists = cur.fetchone()[0] if cur.fetchone() else False

                if not exists:
                    return  # Table doesn't exist yet

                cur.execute("""
                    INSERT INTO raw_mlb.live_feed_snapshots
                    (game_pk, endpoint, response_data, checksum, fetched_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (game_pk, checksum) DO NOTHING
                """, (game_pk, 'feed_live', json.dumps(data), content_hash))
                conn.commit()
        except Exception:
            pass  # Don't let DB errors break polling

    def get_live_games(self) -> list[dict[str, Any]]:
        """Get list of currently live games."""
        result = self.source.download()
        if not result.success:
            return []

        games = []
        for date_info in result.data.get('dates', []):
            for game in date_info.get('games', []):
                status = game.get('status', {}).get('abstractGameCode', '')
                if status in ('L', 'P'):
                    games.append({
                        'game_pk': game.get('gamePk'),
                        'home': game.get('teams', {}).get('home', {}).get('team', {}).get('name', 'Home'),
                        'away': game.get('teams', {}).get('away', {}).get('team', {}).get('name', 'Away'),
                        'status': game.get('status', {}).get('detailedState', 'Unknown'),
                        'inning': game.get('linescore', {}).get('currentInning'),
                        'score_home': game.get('teams', {}).get('home', {}).get('score', 0),
                        'score_away': game.get('teams', {}).get('away', {}).get('score', 0),
                    })
        return games
