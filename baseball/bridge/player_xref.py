"""Player cross-reference service for ID resolution across data sources.

Maps player IDs between:
- MLB Stats API (mlb_id)
- Retrosheet (retro_id)
- ESPN (espn_id)
- Lahman (lahman_id)
- Baseball-Reference (bbref_id)
- FanGraphs (fg_id)

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlayerXref:
    """Cross-reference record for a player across data sources.

    Attributes:
        canonical_id: Unique canonical ID for this player
        mlb_id: MLB Stats API player ID
        retro_id: Retrosheet player ID
        espn_id: ESPN player ID
        lahman_id: Lahman database player ID
        bbref_id: Baseball-Reference player ID
        fg_id: FanGraphs player ID
        first_name: Player first name
        last_name: Player last name
        birth_date: Player birth date
        bats: Batting hand (L/R/S)
        throws: Throwing hand (L/R/S)
        debut_date: MLB debut date
        last_game_date: Last MLB game date
        active: Whether player is currently active
        source_priority: Ordered list of sources for conflict resolution
    """

    canonical_id: str
    mlb_id: int | None = None
    retro_id: str | None = None
    espn_id: int | None = None
    lahman_id: str | None = None
    bbref_id: str | None = None
    fg_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | None = None
    bats: str | None = None
    throws: str | None = None
    debut_date: date | None = None
    last_game_date: date | None = None
    active: bool = True
    source_priority: tuple = ('mlb', 'retro', 'lahman', 'espn', 'bbref', 'fg')

    @property
    def full_name(self) -> str:
        """Return player's full name."""
        if self.first_name and self.last_name:
            return f'{self.first_name} {self.last_name}'
        return self.last_name or self.first_name or 'Unknown'

    def get_id(self, source: str) -> Any | None:
        """Get ID for a specific source.

        Args:
            source: Source name (mlb, retro, espn, lahman, bbref, fg)

        Returns:
            Player ID for the specified source or None
        """
        id_map = {
            'mlb': self.mlb_id,
            'retro': self.retro_id,
            'espn': self.espn_id,
            'lahman': self.lahman_id,
            'bbref': self.bbref_id,
            'fg': self.fg_id,
        }
        return id_map.get(source.lower())

    def has_source(self, source: str) -> bool:
        """Check if player has an ID for the specified source."""
        return self.get_id(source) is not None

    def merge(self, other: 'PlayerXref') -> 'PlayerXref':
        """Merge another PlayerXref into this one, preferring non-None values.

        Uses source_priority to resolve conflicts when both have values.
        """

        def resolve(field: str, self_val: Any, other_val: Any) -> Any:
            if self_val is None:
                return other_val
            if other_val is None:
                return self_val
            # Both have values - use source priority
            self_idx = self.source_priority.index(field) if field in self.source_priority else 999
            other_idx = self.source_priority.index(field) if field in self.source_priority else 999
            return self_val if self_idx <= other_idx else other_val

        return PlayerXref(
            canonical_id=self.canonical_id,
            mlb_id=resolve('mlb', self.mlb_id, other.mlb_id),
            retro_id=resolve('retro', self.retro_id, other.retro_id),
            espn_id=resolve('espn', self.espn_id, other.espn_id),
            lahman_id=resolve('lahman', self.lahman_id, other.lahman_id),
            bbref_id=resolve('bbref', self.bbref_id, other.bbref_id),
            fg_id=resolve('fg', self.fg_id, other.fg_id),
            first_name=self.first_name or other.first_name,
            last_name=self.last_name or other.last_name,
            birth_date=self.birth_date or other.birth_date,
            bats=self.bats or other.bats,
            throws=self.throws or other.throws,
            debut_date=self.debut_date or other.debut_date,
            last_game_date=self.last_game_date or other.last_game_date,
            active=self.active or other.active,
        )


class PlayerXrefService:
    """Service for player ID cross-referencing.

    Manages the mapping of player IDs across multiple data sources.
    Provides lookup by any ID type and returns canonical player info.
    """

    def __init__(self, db_connection=None):
        """Initialize the player xref service.

        Args:
            db_connection: Optional database connection for persistent storage
        """
        self._db = db_connection
        self._cache: dict[str, PlayerXref] = {}
        self._by_mlb: dict[int, str] = {}
        self._by_retro: dict[str, str] = {}
        self._by_espn: dict[int, str] = {}
        self._by_lahman: dict[str, str] = {}
        self._by_bbref: dict[str, str] = {}
        self._by_fg: dict[int, str] = {}

    def load_from_db(self) -> int:
        """Load xref records from database.

        Returns:
            Number of records loaded
        """
        if self._db is None:
            logger.warning('No database connection, cannot load from DB')
            return 0

        count = 0
        try:
            with self._db.cursor() as cur:
                cur.execute('SELECT * FROM bridge.player_xref WHERE active = true')
                for row in cur.fetchall():
                    xref = self._row_to_xref(row)
                    self._add_to_cache(xref)
                    count += 1
            logger.info(f'Loaded {count} player xref records from database')
        except Exception as e:
            logger.error(f'Failed to load player xref from DB: {e}')

        return count

    def _row_to_xref(self, row: tuple) -> PlayerXref:
        """Convert database row to PlayerXref."""
        # Assuming column order: canonical_id, mlb_id, retro_id, espn_id,
        # lahman_id, bbref_id, fg_id, first_name, last_name, birth_date,
        # bats, throws, debut_date, last_game_date, active
        return PlayerXref(
            canonical_id=row[0],
            mlb_id=row[1],
            retro_id=row[2],
            espn_id=row[3],
            lahman_id=row[4],
            bbref_id=row[5],
            fg_id=row[6],
            first_name=row[7],
            last_name=row[8],
            birth_date=row[9],
            bats=row[10],
            throws=row[11],
            debut_date=row[12],
            last_game_date=row[13],
            active=row[14] if row[14] is not None else True,
        )

    def _add_to_cache(self, xref: PlayerXref) -> None:
        """Add xref to cache and index maps."""
        self._cache[xref.canonical_id] = xref

        if xref.mlb_id:
            self._by_mlb[xref.mlb_id] = xref.canonical_id
        if xref.retro_id:
            self._by_retro[xref.retro_id] = xref.canonical_id
        if xref.espn_id:
            self._by_espn[xref.espn_id] = xref.canonical_id
        if xref.lahman_id:
            self._by_lahman[xref.lahman_id] = xref.canonical_id
        if xref.bbref_id:
            self._by_bbref[xref.bbref_id] = xref.canonical_id
        if xref.fg_id:
            self._by_fg[xref.fg_id] = xref.canonical_id

    def lookup_by_mlb(self, mlb_id: int) -> PlayerXref | None:
        """Look up player by MLB ID."""
        canonical = self._by_mlb.get(mlb_id)
        return self._cache.get(canonical) if canonical else None

    def lookup_by_retro(self, retro_id: str) -> PlayerXref | None:
        """Look up player by Retrosheet ID."""
        canonical = self._by_retro.get(retro_id)
        return self._cache.get(canonical) if canonical else None

    def lookup_by_espn(self, espn_id: int) -> PlayerXref | None:
        """Look up player by ESPN ID."""
        canonical = self._by_espn.get(espn_id)
        return self._cache.get(canonical) if canonical else None

    def lookup_by_lahman(self, lahman_id: str) -> PlayerXref | None:
        """Look up player by Lahman ID."""
        canonical = self._by_lahman.get(lahman_id)
        return self._cache.get(canonical) if canonical else None

    def lookup_by_bbref(self, bbref_id: str) -> PlayerXref | None:
        """Look up player by Baseball-Reference ID."""
        canonical = self._by_bbref.get(bbref_id)
        return self._cache.get(canonical) if canonical else None

    def lookup_by_fg(self, fg_id: int) -> PlayerXref | None:
        """Look up player by FanGraphs ID."""
        canonical = self._by_fg.get(fg_id)
        return self._cache.get(canonical) if canonical else None

    def lookup(self, source: str, player_id: Any) -> PlayerXref | None:
        """Generic lookup by source and ID.

        Args:
            source: Source name (mlb, retro, espn, lahman, bbref, fg)
            player_id: Player ID from that source

        Returns:
            PlayerXref if found, None otherwise
        """
        lookup_map = {
            'mlb': self.lookup_by_mlb,
            'retro': self.lookup_by_retro,
            'espn': self.lookup_by_espn,
            'lahman': self.lookup_by_lahman,
            'bbref': self.lookup_by_bbref,
            'fg': self.lookup_by_fg,
        }

        lookup_fn = lookup_map.get(source.lower())
        if lookup_fn:
            return lookup_fn(player_id)
        return None

    def register(self, xref: PlayerXref) -> bool:
        """Register a new player xref.

        If player already exists (by canonical_id), merges the records.

        Args:
            xref: PlayerXref to register

        Returns:
            True if registered/updated successfully
        """
        try:
            # Check if already exists
            existing = self._cache.get(xref.canonical_id)
            if existing:
                # Merge records
                xref = existing.merge(xref)

            # Update cache
            self._add_to_cache(xref)

            # Persist to DB if available
            if self._db:
                self._save_to_db(xref)

            return True
        except Exception as e:
            logger.error(f'Failed to register player xref: {e}')
            return False

    def _save_to_db(self, xref: PlayerXref) -> None:
        """Save xref record to database."""
        try:
            with self._db.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO bridge.player_xref (
                        canonical_id, mlb_id, retro_id, espn_id, lahman_id,
                        bbref_id, fg_id, first_name, last_name, birth_date,
                        bats, throws, debut_date, last_game_date, active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (canonical_id) DO UPDATE SET
                        mlb_id = EXCLUDED.mlb_id,
                        retro_id = EXCLUDED.retro_id,
                        espn_id = EXCLUDED.espn_id,
                        lahman_id = EXCLUDED.lahman_id,
                        bbref_id = EXCLUDED.bbref_id,
                        fg_id = EXCLUDED.fg_id,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        birth_date = EXCLUDED.birth_date,
                        bats = EXCLUDED.bats,
                        throws = EXCLUDED.throws,
                        debut_date = EXCLUDED.debut_date,
                        last_game_date = EXCLUDED.last_game_date,
                        active = EXCLUDED.active,
                        updated_at = NOW()
                    """,
                    (
                        xref.canonical_id,
                        xref.mlb_id,
                        xref.retro_id,
                        xref.espn_id,
                        xref.lahman_id,
                        xref.bbref_id,
                        xref.fg_id,
                        xref.first_name,
                        xref.last_name,
                        xref.birth_date,
                        xref.bats,
                        xref.throws,
                        xref.debut_date,
                        xref.last_game_date,
                        xref.active,
                    ),
                )
            self._db.commit()
        except Exception as e:
            logger.error(f'Failed to save player xref to DB: {e}')
            raise

    def find_candidates(
        self, first_name: str, last_name: str, birth_date: date | None = None
    ) -> list[PlayerXref]:
        """Find potential matches by name and optional birth date.

        Args:
            first_name: Player first name
            last_name: Player last name
            birth_date: Optional birth date for exact matching

        Returns:
            List of matching PlayerXref records
        """
        candidates = []

        for xref in self._cache.values():
            name_match = (
                xref.first_name
                and xref.first_name.lower() == first_name.lower()
                and xref.last_name
                and xref.last_name.lower() == last_name.lower()
            )

            if name_match:
                if birth_date is None or xref.birth_date == birth_date:
                    candidates.append(xref)

        return candidates

    def get_stats(self) -> dict[str, int]:
        """Return statistics about the xref database.

        Returns:
            Dictionary with counts by source
        """
        return {
            'total_players': len(self._cache),
            'with_mlb_id': len(self._by_mlb),
            'with_retro_id': len(self._by_retro),
            'with_espn_id': len(self._by_espn),
            'with_lahman_id': len(self._by_lahman),
            'with_bbref_id': len(self._by_bbref),
            'with_fg_id': len(self._by_fg),
        }
