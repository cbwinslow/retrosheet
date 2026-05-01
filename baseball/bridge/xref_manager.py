"""Cross-reference manager for unified entity resolution.

Coordinates all xref services (player, team, game) and provides
a unified interface for entity resolution across data sources.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import logging
from typing import Any, TypeVar

from .game_xref import GameXref, GameXrefService
from .player_xref import PlayerXref, PlayerXrefService
from .team_xref import TeamXref, TeamXrefService


logger = logging.getLogger(__name__)

T = TypeVar('T')


class XrefManager:
    """Central manager for all cross-reference services.

    Provides unified access to player, team, and game xref services
    with automatic caching and database persistence.

    Example:
        >>> manager = XrefManager(db_connection=conn)
        >>> manager.load_all()
        >>> # Look up player by MLB ID
        >>> player = manager.players.lookup_by_mlb(12345)
        >>> # Look up team by code
        >>> team = manager.teams.lookup_by_code('NYY')
        >>> # Look up game by Retrosheet ID
        >>> game = manager.games.lookup_by_retro('202604040NYY01')
    """

    def __init__(self, db_connection=None) -> None:
        """Initialize the xref manager.

        Args:
            db_connection: Optional database connection for persistent storage
        """
        self._db = db_connection

        # Initialize sub-services
        self.players = PlayerXrefService(db_connection)
        self.teams = TeamXrefService(db_connection)
        self.games = GameXrefService(db_connection)

        logger.info('XrefManager initialized')

    def load_all(self) -> dict[str, int]:
        """Load all xref records from database.

        Returns:
            Dictionary with counts loaded per service
        """
        counts = {
            'players': self.players.load_from_db(),
            'games': self.games.load_from_db(),
            # Teams are loaded from hardcoded canonical list
            'teams': len(self.teams.get_all_teams()),
        }

        total = sum(counts.values())
        logger.info(f'Loaded {total} total xref records')
        return counts

    def load_for_season(self, year: int) -> dict[str, int]:
        """Load xref records for a specific season.

        Args:
            year: Season year to load

        Returns:
            Dictionary with counts loaded per service
        """
        counts = {
            'players': self.players.load_from_db(),  # Load all active players
            'games': self.games.load_from_db(year=year),
            'teams': len(self.teams.get_all_teams()),
        }

        total = sum(counts.values())
        logger.info(f'Loaded {total} xref records for {year} season')
        return counts

    def get_stats(self) -> dict[str, dict[str, int]]:
        """Get statistics for all xref services.

        Returns:
            Dictionary with stats per service
        """
        return {
            'players': self.players.get_stats(),
            'teams': self.teams.get_stats(),
            'games': self.games.get_stats(),
        }

    def resolve_player(self, source: str, player_id: Any) -> PlayerXref | None:
        """Resolve a player ID to canonical form.

        Args:
            source: Source name (mlb, retro, espn, lahman, bbref, fg)
            player_id: Player ID from that source

        Returns:
            PlayerXref with canonical IDs for all sources
        """
        return self.players.lookup(source, player_id)

    def resolve_team(self, source: str, team_id: Any) -> TeamXref | None:
        """Resolve a team ID to canonical form.

        Args:
            source: Source name (mlb, code, retro, espn, lahman)
            team_id: Team ID from that source

        Returns:
            TeamXref with canonical IDs for all sources
        """
        return self.teams.lookup(source, team_id)

    def resolve_game(self, source: str, game_id: Any) -> GameXref | None:
        """Resolve a game ID to canonical form.

        Args:
            source: Source name (mlb, retro, espn)
            game_id: Game ID from that source

        Returns:
            GameXref with canonical IDs for all sources
        """
        return self.games.lookup(source, game_id)

    def find_player(
        self, first_name: str, last_name: str, birth_date: Any | None = None,
    ) -> list[PlayerXref]:
        """Find players by name.

        Args:
            first_name: Player first name
            last_name: Player last name
            birth_date: Optional birth date for exact matching

        Returns:
            List of matching PlayerXref records
        """
        return self.players.find_candidates(first_name, last_name, birth_date)

    def find_games_by_date(self, game_date: Any) -> list[GameXref]:
        """Find all games on a specific date.

        Args:
            game_date: Game date (date object or string)

        Returns:
            List of GameXref records
        """
        if isinstance(game_date, str):
            from datetime import datetime

            game_date = datetime.strptime(game_date, '%Y-%m-%d').date()

        return self.games.find_by_date(game_date)

    def find_games_by_matchup(
        self, team1_code: str, team2_code: str, year: int | None = None,
    ) -> list[GameXref]:
        """Find games between two teams.

        Args:
            team1_code: First team code
            team2_code: Second team code
            year: Optional year filter

        Returns:
            List of GameXref records
        """
        results = []

        # Get team canonical IDs
        team1 = self.teams.lookup_by_code(team1_code)
        team2 = self.teams.lookup_by_code(team2_code)

        if not team1 or not team2:
            return results

        # Find games for team1 against team2
        games = self.games.find_by_teams(team1.canonical_id, team2.canonical_id)

        # Filter by year if specified
        if year:
            games = [g for g in games if g.year == year]

        return games

    def get_team_roster(self, team_code: str, year: int) -> list[PlayerXref]:
        """Get roster for a team in a specific year.

        Note: This is a placeholder that returns an empty list.
        Actual implementation would query a roster database table.

        Args:
            team_code: Team code (e.g., 'NYY')
            year: Season year

        Returns:
            List of PlayerXref records (currently empty - needs roster table)
        """
        logger.warning('get_team_roster requires roster database table')
        return []

    def register_player(self, xref: PlayerXref) -> bool:
        """Register a player xref.

        Args:
            xref: PlayerXref to register

        Returns:
            True if registered successfully
        """
        return self.players.register(xref)

    def register_team(self, xref: TeamXref) -> bool:
        """Register a team xref.

        Args:
            xref: TeamXref to register

        Returns:
            True if registered successfully
        """
        return self.teams.register(xref)

    def register_game(self, xref: GameXref) -> bool:
        """Register a game xref.

        Args:
            xref: GameXref to register

        Returns:
            True if registered successfully
        """
        return self.games.register(xref)

    def bulk_register_games(self, xrefs: list[GameXref]) -> int:
        """Bulk register game xrefs.

        Args:
            xrefs: List of GameXref to register

        Returns:
            Number of successfully registered games
        """
        count = 0
        for xref in xrefs:
            if self.games.register(xref):
                count += 1

        logger.info(f'Bulk registered {count}/{len(xrefs)} games')
        return count
