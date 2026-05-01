"""Game cross-reference service for ID resolution across data sources.

Maps game IDs between:
- MLB Stats API (mlb_id, game_pk)
- Retrosheet (retro_id, game_id format: 'YYYYMMDDTTTHH')
- ESPN (espn_id)

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GameXref:
    """Cross-reference record for a game across data sources.

    Attributes:
        canonical_id: Unique canonical ID (typically MLB game_pk)
        mlb_id: MLB Stats API game ID (game_pk)
        retro_id: Retrosheet game ID (format: YYYYMMDDTTTHH)
        espn_id: ESPN game ID
        game_date: Game date
        game_type: Game type (R=Regular, P=Postseason, S=Spring, E=Exhibition)
        home_team_id: Home team canonical ID
        away_team_id: Away team canonical ID
        home_team_code: Home team code
        away_team_code: Away team code
        year: Season year
        doubleheader: Doubleheader flag (0=single, 1=first, 2=second)
        season: Season year
        status: Game status (Final, Live, Scheduled, etc.)
    """

    canonical_id: int
    mlb_id: int | None = None
    retro_id: str | None = None
    espn_id: int | None = None
    game_date: date | None = None
    game_type: str | None = None
    home_team_id: int | None = None
    away_team_id: int | None = None
    home_team_code: str | None = None
    away_team_code: str | None = None
    year: int | None = None
    doubleheader: int = 0
    season: int | None = None
    status: str | None = None

    @property
    def matchup(self) -> str:
        """Return matchup string (e.g., 'NYY @ BOS')."""
        if self.away_team_code and self.home_team_code:
            return f'{self.away_team_code} @ {self.home_team_code}'
        return 'Unknown matchup'

    def get_id(self, source: str) -> Any | None:
        """Get ID for a specific source.

        Args:
            source: Source name (mlb, retro, espn)

        Returns:
            Game ID for the specified source or None
        """
        id_map = {
            'mlb': self.mlb_id,
            'retro': self.retro_id,
            'espn': self.espn_id,
        }
        return id_map.get(source.lower())

    def has_source(self, source: str) -> bool:
        """Check if game has an ID for the specified source."""
        return self.get_id(source) is not None

    @classmethod
    def parse_retro_id(cls, retro_id: str) -> dict[str, Any] | None:
        """Parse a Retrosheet game ID into components.

        Retrosheet format: YYYYMMDDTTTHH
        - YYYYMMDD: Date
        - TTT: Home team code
        - HH: Doubleheader flag (01, 02)

        Args:
            retro_id: Retrosheet game ID

        Returns:
            Dictionary with parsed components or None if invalid
        """
        if not retro_id or len(retro_id) != 12:
            return None

        try:
            year = int(retro_id[0:4])
            month = int(retro_id[4:6])
            day = int(retro_id[6:8])
            home_team = retro_id[8:11]
            dh = int(retro_id[11:12])

            return {
                'date': date(year, month, day),
                'home_team': home_team,
                'doubleheader': dh,
            }
        except (ValueError, IndexError):
            return None

    @classmethod
    def generate_retro_id(cls, game_date: date, home_team_code: str, doubleheader: int = 0) -> str:
        """Generate a Retrosheet-style game ID.

        Args:
            game_date: Game date
            home_team_code: Home team code (3 letters)
            doubleheader: Doubleheader flag (0, 1, or 2)

        Returns:
            Retrosheet game ID
        """
        return f'{game_date.strftime("%Y%m%d")}{home_team_code.upper()}{doubleheader:02d}'


class GameXrefService:
    """Service for game ID cross-referencing.

    Manages the mapping of game IDs across multiple data sources.
    Provides lookup by any ID type and returns canonical game info.
    """

    def __init__(self, db_connection=None) -> None:
        """Initialize the game xref service.

        Args:
            db_connection: Optional database connection for persistent storage
        """
        self._db = db_connection
        self._cache: dict[int, GameXref] = {}
        self._by_retro: dict[str, int] = {}
        self._by_espn: dict[int, int] = {}
        # Index by date for efficient range queries
        self._by_date: dict[date, list[int]] = {}

    def load_from_db(self, year: int | None = None) -> int:
        """Load xref records from database.

        Args:
            year: Optional year to filter by

        Returns:
            Number of records loaded
        """
        if self._db is None:
            logger.warning('No database connection, cannot load from DB')
            return 0

        count = 0
        try:
            with self._db.cursor() as cur:
                if year:
                    cur.execute(
                        'SELECT * FROM bridge.game_xref WHERE season = %s',
                        (year,),
                    )
                else:
                    cur.execute('SELECT * FROM bridge.game_xref')

                for row in cur.fetchall():
                    xref = self._row_to_xref(row)
                    self._add_to_cache(xref)
                    count += 1

            logger.info(f'Loaded {count} game xref records from database')
        except Exception as e:
            logger.exception(f'Failed to load game xref from DB: {e}')

        return count

    def _row_to_xref(self, row: tuple) -> GameXref:
        """Convert database row to GameXref."""
        return GameXref(
            canonical_id=row[0],
            mlb_id=row[1],
            retro_id=row[2],
            espn_id=row[3],
            game_date=row[4],
            game_type=row[5],
            home_team_id=row[6],
            away_team_id=row[7],
            home_team_code=row[8],
            away_team_code=row[9],
            year=row[10],
            doubleheader=row[11] or 0,
            season=row[12],
            status=row[13],
        )

    def _add_to_cache(self, xref: GameXref) -> None:
        """Add xref to cache and index maps."""
        self._cache[xref.canonical_id] = xref

        if xref.retro_id:
            self._by_retro[xref.retro_id] = xref.canonical_id
        if xref.espn_id:
            self._by_espn[xref.espn_id] = xref.canonical_id

        # Index by date
        if xref.game_date:
            if xref.game_date not in self._by_date:
                self._by_date[xref.game_date] = []
            if xref.canonical_id not in self._by_date[xref.game_date]:
                self._by_date[xref.game_date].append(xref.canonical_id)

    def lookup_by_mlb(self, mlb_id: int) -> GameXref | None:
        """Look up game by MLB ID."""
        return self._cache.get(mlb_id)

    def lookup_by_retro(self, retro_id: str) -> GameXref | None:
        """Look up game by Retrosheet ID."""
        canonical = self._by_retro.get(retro_id)
        return self._cache.get(canonical) if canonical else None

    def lookup_by_espn(self, espn_id: int) -> GameXref | None:
        """Look up game by ESPN ID."""
        canonical = self._by_espn.get(espn_id)
        return self._cache.get(canonical) if canonical else None

    def lookup(self, source: str, game_id: Any) -> GameXref | None:
        """Generic lookup by source and ID.

        Args:
            source: Source name (mlb, retro, espn)
            game_id: Game ID from that source

        Returns:
            GameXref if found, None otherwise
        """
        lookup_map = {
            'mlb': self.lookup_by_mlb,
            'retro': self.lookup_by_retro,
            'espn': self.lookup_by_espn,
        }

        lookup_fn = lookup_map.get(source.lower())
        if lookup_fn:
            try:
                game_id = str(game_id) if source.lower() == 'retro' else int(game_id)
            except (ValueError, TypeError):
                return None
            return lookup_fn(game_id)
        return None

    def find_by_date(self, game_date: date) -> list[GameXref]:
        """Find all games on a specific date.

        Args:
            game_date: Date to search

        Returns:
            List of GameXref records
        """
        canonical_ids = self._by_date.get(game_date, [])
        return [self._cache[cid] for cid in canonical_ids if cid in self._cache]

    def find_by_date_range(self, start_date: date, end_date: date) -> list[GameXref]:
        """Find all games in a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of GameXref records
        """
        results = []
        current = start_date
        while current <= end_date:
            results.extend(self.find_by_date(current))
            # Move to next day
            current = date.fromordinal(current.toordinal() + 1)
        return results

    def find_by_teams(
        self,
        team_id: int,
        opponent_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[GameXref]:
        """Find games by team(s).

        Args:
            team_id: Team canonical ID to search for
            opponent_id: Optional opponent team ID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of GameXref records
        """
        results = []

        games = list(self._cache.values())
        if start_date and end_date:
            games = self.find_by_date_range(start_date, end_date)

        for game in games:
            # Check if team is in this game
            if game.home_team_id == team_id or game.away_team_id == team_id:
                # Check opponent if specified
                if opponent_id:
                    if game.home_team_id == opponent_id or game.away_team_id == opponent_id:
                        results.append(game)
                else:
                    results.append(game)

        return results

    def register(self, xref: GameXref) -> bool:
        """Register a new game xref.

        Args:
            xref: GameXref to register

        Returns:
            True if registered successfully
        """
        try:
            self._add_to_cache(xref)

            # Persist to DB if available
            if self._db:
                self._save_to_db(xref)

            return True
        except Exception as e:
            logger.exception(f'Failed to register game xref: {e}')
            return False

    def _save_to_db(self, xref: GameXref) -> None:
        """Save xref record to database."""
        try:
            with self._db.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO bridge.game_xref (
                        canonical_id, mlb_id, retro_id, espn_id, game_date,
                        game_type, home_team_id, away_team_id, home_team_code,
                        away_team_code, year, doubleheader, season, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (canonical_id) DO UPDATE SET
                        mlb_id = EXCLUDED.mlb_id,
                        retro_id = EXCLUDED.retro_id,
                        espn_id = EXCLUDED.espn_id,
                        game_date = EXCLUDED.game_date,
                        game_type = EXCLUDED.game_type,
                        home_team_id = EXCLUDED.home_team_id,
                        away_team_id = EXCLUDED.away_team_id,
                        home_team_code = EXCLUDED.home_team_code,
                        away_team_code = EXCLUDED.away_team_code,
                        year = EXCLUDED.year,
                        doubleheader = EXCLUDED.doubleheader,
                        season = EXCLUDED.season,
                        status = EXCLUDED.status,
                        updated_at = NOW()
                    """,
                    (
                        xref.canonical_id,
                        xref.mlb_id,
                        xref.retro_id,
                        xref.espn_id,
                        xref.game_date,
                        xref.game_type,
                        xref.home_team_id,
                        xref.away_team_id,
                        xref.home_team_code,
                        xref.away_team_code,
                        xref.year,
                        xref.doubleheader,
                        xref.season,
                        xref.status,
                    ),
                )
            self._db.commit()
        except Exception as e:
            logger.exception(f'Failed to save game xref to DB: {e}')
            raise

    def get_stats(self) -> dict[str, int]:
        """Return statistics about the xref database."""
        return {
            'total_games': len(self._cache),
            'with_retro_id': len(self._by_retro),
            'with_espn_id': len(self._by_espn),
            'unique_dates': len(self._by_date),
        }
