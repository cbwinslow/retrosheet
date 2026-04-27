"""Live MLB game data source adapter with real-time tracking.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from mlb_predict.sources.base import BaseSource, DownloadResult, IngestResult, ValidationResult


@dataclass
class GameState:
    """Current state of a live MLB game."""

    game_pk: int
    game_date: date
    status: str  # Preview, Live, Final, etc.
    inning: int
    is_top: bool
    outs: int
    home_score: int
    away_score: int
    home_team_id: int
    away_team_id: int
    current_batter_id: int | None = None
    current_pitcher_id: int | None = None
    base_state: int = 0  # 0-7 for empty to loaded
    last_play_at: datetime | None = None
    play_count: int = 0
    balls: int = 0
    strikes: int = 0
    raw_data: dict[str, Any] = field(default_factory=dict)

    @property
    def is_in_progress(self) -> bool:
        """Check if game is currently in progress."""
        return self.status in ('Live', 'In Progress', 'Warmup', 'Delayed Start')

    @property
    def is_complete(self) -> bool:
        """Check if game is complete."""
        return self.status in ('Final', 'Game Over', 'Completed Early')


class LiveMlbSource(BaseSource):
    """Live MLB data source adapter with real-time game state tracking.

    Wraps existing live ingestion scripts:
    - fetch_mlb_schedule.py (schedule discovery)
    - ingest_live_games.py (game feed ingestion)
    - transform_live_game.py (data transformation)

    Provides:
    - Active game discovery
    - Real-time game state polling
    - Event change detection
    - Change callbacks
    """

    def __init__(self, config: Any | None = None):
        super().__init__(config)
        self._scripts_dir = Path('scripts/data_ingestion')
        self._transform_dir = Path('scripts/transform')
        self._data_dir = Path('data/mlb_live')
        self._game_states: dict[int, GameState] = {}
        self._callbacks: list[Callable[[GameState], None]] = []
        self._poll_interval: float = 10.0  # seconds between polls
        self._last_poll: datetime | None = None

    def download(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        game_pks: list[int] | None = None,
        output_dir: Path | None = None,
        force: bool = False,
    ) -> DownloadResult:
        """Download live MLB data for specified games.

        For live data, this fetches current state rather than historical.
        """
        if game_pks:
            return self._download_specific_games(game_pks, force)

        # Get active games and download them
        active_games = self.get_active_games()
        if not active_games:
            return DownloadResult(
                success=True,
                rows_downloaded=0,
                metadata={'message': 'No active games found'},
            )

        game_pks = [g.game_pk for g in active_games]
        return self._download_specific_games(game_pks, force)

    def _download_specific_games(
        self,
        game_pks: list[int],
        force: bool,
    ) -> DownloadResult:
        """Download specific games by game_pk."""
        script = self._scripts_dir / 'ingest_live_games.py'

        if not script.exists():
            return DownloadResult(
                success=False,
                error_message=f'Script not found: {script}',
            )

        success_count = 0
        for game_pk in game_pks:
            cmd = [
                'uv',
                'run',
                'python',
                str(script),
                '--game-pk',
                str(game_pk),
            ]
            if force:
                cmd.append('--force')

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                success_count += 1

        return DownloadResult(
            success=success_count > 0,
            rows_downloaded=success_count,
            rows_failed=len(game_pks) - success_count,
            metadata={'games': game_pks},
        )

    def ingest(
        self,
        input_path: Path | None = None,
        validate: bool = True,
    ) -> IngestResult:
        """Ingest live MLB data - already ingested during download."""
        import psycopg2

        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='retrosheet',
            )

            with conn.cursor() as cur:
                # Get recent live game count
                cur.execute(
                    """
                    SELECT COUNT(DISTINCT game_pk)
                    FROM raw_mlb.live_feed_snapshots
                    WHERE fetched_at > NOW() - INTERVAL '24 hours'
                    """,
                )
                recent_count = cur.fetchone()[0]

                # Get active games count
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM core.live_games
                    WHERE status IN ('Live', 'In Progress')
                    """,
                )
                active_count = cur.fetchone()[0]

            conn.close()

            return IngestResult(
                success=True,
                rows_inserted=recent_count,
                metadata={
                    'games_24h': recent_count,
                    'active_games': active_count,
                },
            )

        except Exception as e:
            return IngestResult(
                success=False,
                error_message=str(e),
            )

    def validate(self) -> ValidationResult:
        """Validate live data quality."""
        import psycopg2

        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='retrosheet',
            )

            checks = []
            issues = []

            with conn.cursor() as cur:
                # Check live tables exist
                cur.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'raw_mlb'
                    AND table_name LIKE '%live%'
                    """,
                )
                table_count = cur.fetchone()[0]
                checks.append({'check': 'live_tables_exist', 'count': table_count})

                # Check for recent data
                cur.execute(
                    """
                    SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots
                    WHERE fetched_at > NOW() - INTERVAL '1 hour'
                    """,
                )
                recent_count = cur.fetchone()[0]
                checks.append({'check': 'recent_live_data', 'count': recent_count})

                if recent_count == 0:
                    issues.append('No live data fetched in last hour')

                # Check core.live_games
                cur.execute(
                    """
                    SELECT COUNT(*) FROM core.live_games
                    WHERE updated_at > NOW() - INTERVAL '1 hour'
                    """,
                )
                live_count = cur.fetchone()[0]
                checks.append({'check': 'core_live_games', 'count': live_count})

            conn.close()

            success = table_count >= 2 and (recent_count > 0 or live_count > 0)

            return ValidationResult(
                success=success,
                warning_count=len(issues),
                issues=issues,
                metadata={'checks': checks},
            )

        except Exception as e:
            return ValidationResult(
                success=False,
                error_count=1,
                error_message=str(e),
            )

    def get_active_games(self) -> list[GameState]:
        """Get list of currently active/live games."""
        import psycopg2

        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='retrosheet',
            )

            games = []
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        game_pk,
                        game_date,
                        status,
                        COALESCE(inning, 1),
                        COALESCE(is_top, true),
                        COALESCE(outs, 0),
                        COALESCE(home_score, 0),
                        COALESCE(away_score, 0),
                        home_team_id,
                        away_team_id
                    FROM core.live_games
                    WHERE status IN ('Live', 'In Progress', 'Warmup')
                    ORDER BY game_date, game_pk
                    """,
                )

                for row in cur.fetchall():
                    games.append(
                        GameState(
                            game_pk=row[0],
                            game_date=row[1],
                            status=row[2],
                            inning=row[3],
                            is_top=row[4],
                            outs=row[5],
                            home_score=row[6],
                            away_score=row[7],
                            home_team_id=row[8],
                            away_team_id=row[9],
                        ),
                    )

            conn.close()
            return games

        except Exception:
            return []

    def get_game_state(self, game_pk: int) -> GameState | None:
        """Get current state for a specific game."""
        import psycopg2

        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='retrosheet',
            )

            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        game_pk,
                        game_date,
                        status,
                        COALESCE(inning, 1),
                        COALESCE(is_top, true),
                        COALESCE(outs, 0),
                        COALESCE(home_score, 0),
                        COALESCE(away_score, 0),
                        home_team_id,
                        away_team_id,
                        current_batter_id,
                        current_pitcher_id
                    FROM core.live_games
                    WHERE game_pk = %s
                    """,
                    (game_pk,),
                )

                row = cur.fetchone()
                if row:
                    state = GameState(
                        game_pk=row[0],
                        game_date=row[1],
                        status=row[2],
                        inning=row[3],
                        is_top=row[4],
                        outs=row[5],
                        home_score=row[6],
                        away_score=row[7],
                        home_team_id=row[8],
                        away_team_id=row[9],
                        current_batter_id=row[10],
                        current_pitcher_id=row[11],
                    )
                    self._game_states[game_pk] = state
                    return state

            conn.close()

        except Exception:
            pass

        return None

    def poll_game(self, game_pk: int) -> GameState | None:
        """Poll a single game for updates.

        Returns new GameState if state changed, None otherwise.
        """
        # Fetch latest data
        self._download_specific_games([game_pk], force=True)

        # Transform the data
        transform_script = self._transform_dir / 'transform_live_game.py'
        if transform_script.exists():
            subprocess.run(
                [
                    'uv',
                    'run',
                    'python',
                    str(transform_script),
                    '--game-pk',
                    str(game_pk),
                ],
                capture_output=True,
            )

        # Get updated state
        new_state = self.get_game_state(game_pk)
        if not new_state:
            return None

        # Check if state changed
        old_state = self._game_states.get(game_pk)
        if old_state and self._state_changed(old_state, new_state):
            self._notify_callbacks(new_state)

        self._game_states[game_pk] = new_state
        return new_state

    def _state_changed(self, old: GameState, new: GameState) -> bool:
        """Check if game state has meaningfully changed."""
        return (
            old.inning != new.inning
            or old.is_top != new.is_top
            or old.outs != new.outs
            or old.home_score != new.home_score
            or old.away_score != new.away_score
            or old.balls != new.balls
            or old.strikes != new.strikes
            or old.base_state != new.base_state
            or old.current_batter_id != new.current_batter_id
        )

    def on_state_change(self, callback: Callable[[GameState], None]) -> None:
        """Register a callback for state changes."""
        self._callbacks.append(callback)

    def _notify_callbacks(self, state: GameState) -> None:
        """Notify all registered callbacks of state change."""
        for callback in self._callbacks:
            try:
                callback(state)
            except Exception:
                pass  # Continue even if one callback fails

    def get_available_dates(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[date]:
        """Not applicable for live data - returns empty list."""
        return []

    def get_todays_games(self) -> list[int]:
        """Get game PKs for today's games."""
        script = self._scripts_dir / 'fetch_mlb_schedule.py'

        if not script.exists():
            return []

        result = subprocess.run(
            ['uv', 'run', 'python', str(script)],
            capture_output=True,
            text=True,
        )

        game_pks = []
        for line in result.stdout.splitlines():
            parts = line.split()
            for part in parts:
                if part.isdigit() and len(part) == 6:
                    game_pks.append(int(part))

        return game_pks
