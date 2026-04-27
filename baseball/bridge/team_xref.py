"""Team cross-reference service for ID resolution across data sources.

Maps team IDs between:
- MLB Stats API (mlb_id, team_code)
- Retrosheet (retro_id, team_code)
- ESPN (espn_id)
- Lahman (lahman_id, team_code)

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TeamXref:
    """Cross-reference record for a team across data sources.

    Attributes:
        canonical_id: Unique canonical ID (typically MLB team ID)
        mlb_id: MLB Stats API team ID
        mlb_code: MLB 2-3 letter team code (e.g., 'NYY', 'LAD')
        retro_id: Retrosheet team ID
        retro_code: Retrosheet team code
        espn_id: ESPN team ID
        lahman_id: Lahman database team ID
        lahman_code: Lahman team code
        name: Full team name
        city: Team city
        nickname: Team nickname
        league: League ('AL' or 'NL')
        division: Division name
        first_year: First year of franchise
        last_year: Last year of franchise (None if active)
        active: Whether team is currently active
    """

    canonical_id: int
    mlb_id: int | None = None
    mlb_code: str | None = None
    retro_id: str | None = None
    retro_code: str | None = None
    espn_id: int | None = None
    lahman_id: str | None = None
    lahman_code: str | None = None
    name: str | None = None
    city: str | None = None
    nickname: str | None = None
    league: str | None = None
    division: str | None = None
    first_year: int | None = None
    last_year: int | None = None
    active: bool = True

    @property
    def full_name(self) -> str:
        """Return full team name (City + Nickname)."""
        if self.city and self.nickname:
            return f'{self.city} {self.nickname}'
        return self.name or 'Unknown'

    def get_id(self, source: str) -> Any | None:
        """Get ID for a specific source.

        Args:
            source: Source name (mlb, retro, espn, lahman)

        Returns:
            Team ID for the specified source or None
        """
        id_map = {
            'mlb': self.mlb_id,
            'retro': self.retro_id,
            'espn': self.espn_id,
            'lahman': self.lahman_id,
        }
        return id_map.get(source.lower())

    def get_code(self, source: str) -> str | None:
        """Get team code for a specific source.

        Args:
            source: Source name (mlb, retro, lahman)

        Returns:
            Team code for the specified source or None
        """
        code_map = {
            'mlb': self.mlb_code,
            'retro': self.retro_code,
            'lahman': self.lahman_code,
        }
        return code_map.get(source.lower())

    def has_source(self, source: str) -> bool:
        """Check if team has an ID for the specified source."""
        return self.get_id(source) is not None


class TeamXrefService:
    """Service for team ID cross-referencing.

    Manages the mapping of team IDs across multiple data sources.
    Provides lookup by any ID type and returns canonical team info.
    """

    # MLB team mappings (canonical)
    MLB_TEAMS = {
        108: {
            'code': 'ANA',
            'name': 'Los Angeles Angels',
            'city': 'Los Angeles',
            'nickname': 'Angels',
            'league': 'AL',
            'division': 'West',
        },
        109: {
            'code': 'ARI',
            'name': 'Arizona Diamondbacks',
            'city': 'Arizona',
            'nickname': 'Diamondbacks',
            'league': 'NL',
            'division': 'West',
        },
        110: {
            'code': 'BAL',
            'name': 'Baltimore Orioles',
            'city': 'Baltimore',
            'nickname': 'Orioles',
            'league': 'AL',
            'division': 'East',
        },
        111: {
            'code': 'BOS',
            'name': 'Boston Red Sox',
            'city': 'Boston',
            'nickname': 'Red Sox',
            'league': 'AL',
            'division': 'East',
        },
        112: {
            'code': 'CHC',
            'name': 'Chicago Cubs',
            'city': 'Chicago',
            'nickname': 'Cubs',
            'league': 'NL',
            'division': 'Central',
        },
        113: {
            'code': 'CIN',
            'name': 'Cincinnati Reds',
            'city': 'Cincinnati',
            'nickname': 'Reds',
            'league': 'NL',
            'division': 'Central',
        },
        114: {
            'code': 'CLE',
            'name': 'Cleveland Guardians',
            'city': 'Cleveland',
            'nickname': 'Guardians',
            'league': 'AL',
            'division': 'Central',
        },
        115: {
            'code': 'COL',
            'name': 'Colorado Rockies',
            'city': 'Colorado',
            'nickname': 'Rockies',
            'league': 'NL',
            'division': 'West',
        },
        116: {
            'code': 'DET',
            'name': 'Detroit Tigers',
            'city': 'Detroit',
            'nickname': 'Tigers',
            'league': 'AL',
            'division': 'Central',
        },
        117: {
            'code': 'HOU',
            'name': 'Houston Astros',
            'city': 'Houston',
            'nickname': 'Astros',
            'league': 'AL',
            'division': 'West',
        },
        118: {
            'code': 'KCR',
            'name': 'Kansas City Royals',
            'city': 'Kansas City',
            'nickname': 'Royals',
            'league': 'AL',
            'division': 'Central',
        },
        119: {
            'code': 'LAD',
            'name': 'Los Angeles Dodgers',
            'city': 'Los Angeles',
            'nickname': 'Dodgers',
            'league': 'NL',
            'division': 'West',
        },
        120: {
            'code': 'WSN',
            'name': 'Washington Nationals',
            'city': 'Washington',
            'nickname': 'Nationals',
            'league': 'NL',
            'division': 'East',
        },
        121: {
            'code': 'NYM',
            'name': 'New York Mets',
            'city': 'New York',
            'nickname': 'Mets',
            'league': 'NL',
            'division': 'East',
        },
        133: {
            'code': 'OAK',
            'name': 'Oakland Athletics',
            'city': 'Oakland',
            'nickname': 'Athletics',
            'league': 'AL',
            'division': 'West',
        },
        134: {
            'code': 'PIT',
            'name': 'Pittsburgh Pirates',
            'city': 'Pittsburgh',
            'nickname': 'Pirates',
            'league': 'NL',
            'division': 'Central',
        },
        135: {
            'code': 'SDP',
            'name': 'San Diego Padres',
            'city': 'San Diego',
            'nickname': 'Padres',
            'league': 'NL',
            'division': 'West',
        },
        136: {
            'code': 'SEA',
            'name': 'Seattle Mariners',
            'city': 'Seattle',
            'nickname': 'Mariners',
            'league': 'AL',
            'division': 'West',
        },
        137: {
            'code': 'SFG',
            'name': 'San Francisco Giants',
            'city': 'San Francisco',
            'nickname': 'Giants',
            'league': 'NL',
            'division': 'West',
        },
        138: {
            'code': 'STL',
            'name': 'St. Louis Cardinals',
            'city': 'St. Louis',
            'nickname': 'Cardinals',
            'league': 'NL',
            'division': 'Central',
        },
        139: {
            'code': 'TBR',
            'name': 'Tampa Bay Rays',
            'city': 'Tampa Bay',
            'nickname': 'Rays',
            'league': 'AL',
            'division': 'East',
        },
        140: {
            'code': 'TEX',
            'name': 'Texas Rangers',
            'city': 'Texas',
            'nickname': 'Rangers',
            'league': 'AL',
            'division': 'West',
        },
        141: {
            'code': 'TOR',
            'name': 'Toronto Blue Jays',
            'city': 'Toronto',
            'nickname': 'Blue Jays',
            'league': 'AL',
            'division': 'East',
        },
        142: {
            'code': 'MIN',
            'name': 'Minnesota Twins',
            'city': 'Minnesota',
            'nickname': 'Twins',
            'league': 'AL',
            'division': 'Central',
        },
        143: {
            'code': 'PHI',
            'name': 'Philadelphia Phillies',
            'city': 'Philadelphia',
            'nickname': 'Phillies',
            'league': 'NL',
            'division': 'East',
        },
        144: {
            'code': 'ATL',
            'name': 'Atlanta Braves',
            'city': 'Atlanta',
            'nickname': 'Braves',
            'league': 'NL',
            'division': 'East',
        },
        145: {
            'code': 'CHW',
            'name': 'Chicago White Sox',
            'city': 'Chicago',
            'nickname': 'White Sox',
            'league': 'AL',
            'division': 'Central',
        },
        146: {
            'code': 'MIA',
            'name': 'Miami Marlins',
            'city': 'Miami',
            'nickname': 'Marlins',
            'league': 'NL',
            'division': 'East',
        },
        147: {
            'code': 'NYY',
            'name': 'New York Yankees',
            'city': 'New York',
            'nickname': 'Yankees',
            'league': 'AL',
            'division': 'East',
        },
        158: {
            'code': 'MIL',
            'name': 'Milwaukee Brewers',
            'city': 'Milwaukee',
            'nickname': 'Brewers',
            'league': 'NL',
            'division': 'Central',
        },
    }

    # Historical teams (no longer active)
    HISTORICAL_TEAMS = {
        100: {
            'code': 'MLA',
            'name': 'Milwaukee Brewers (1901)',
            'league': 'AL',
        },  # 1901 Milwaukee Brewers
    }

    def __init__(self, db_connection=None):
        """Initialize the team xref service.

        Args:
            db_connection: Optional database connection for persistent storage
        """
        self._db = db_connection
        self._cache: dict[int, TeamXref] = {}
        self._by_code: dict[str, int] = {}
        self._by_retro: dict[str, int] = {}
        self._by_espn: dict[int, int] = {}
        self._by_lahman: dict[str, int] = {}

        # Load canonical MLB teams
        self._load_canonical_teams()

    def _load_canonical_teams(self) -> None:
        """Load canonical MLB team mappings."""
        for mlb_id, info in self.MLB_TEAMS.items():
            xref = TeamXref(
                canonical_id=mlb_id,
                mlb_id=mlb_id,
                mlb_code=info['code'],
                retro_id=info['code'],  # Usually same
                retro_code=info['code'],
                name=info['name'],
                city=info['city'],
                nickname=info['nickname'],
                league=info['league'],
                division=info['division'],
                active=True,
            )
            self._add_to_cache(xref)

    def _add_to_cache(self, xref: TeamXref) -> None:
        """Add xref to cache and index maps."""
        self._cache[xref.canonical_id] = xref

        if xref.mlb_code:
            self._by_code[xref.mlb_code.upper()] = xref.canonical_id
        if xref.retro_id:
            self._by_retro[xref.retro_id.upper()] = xref.canonical_id
        if xref.espn_id:
            self._by_espn[xref.espn_id] = xref.canonical_id
        if xref.lahman_id:
            self._by_lahman[xref.lahman_id] = xref.canonical_id

    def lookup_by_mlb(self, mlb_id: int) -> TeamXref | None:
        """Look up team by MLB ID."""
        return self._cache.get(mlb_id)

    def lookup_by_code(self, code: str) -> TeamXref | None:
        """Look up team by team code (case insensitive)."""
        canonical = self._by_code.get(code.upper())
        return self._cache.get(canonical) if canonical else None

    def lookup_by_retro(self, retro_id: str) -> TeamXref | None:
        """Look up team by Retrosheet ID."""
        canonical = self._by_retro.get(retro_id.upper())
        return self._cache.get(canonical) if canonical else None

    def lookup_by_espn(self, espn_id: int) -> TeamXref | None:
        """Look up team by ESPN ID."""
        canonical = self._by_espn.get(espn_id)
        return self._cache.get(canonical) if canonical else None

    def lookup_by_lahman(self, lahman_id: str) -> TeamXref | None:
        """Look up team by Lahman ID."""
        canonical = self._by_lahman.get(lahman_id)
        return self._cache.get(canonical) if canonical else None

    def lookup(self, source: str, team_id: Any) -> TeamXref | None:
        """Generic lookup by source and ID.

        Args:
            source: Source name (mlb, code, retro, espn, lahman)
            team_id: Team ID from that source

        Returns:
            TeamXref if found, None otherwise
        """
        if source.lower() == 'code':
            return self.lookup_by_code(str(team_id))

        lookup_map = {
            'mlb': self.lookup_by_mlb,
            'retro': self.lookup_by_retro,
            'espn': self.lookup_by_espn,
            'lahman': self.lookup_by_lahman,
        }

        lookup_fn = lookup_map.get(source.lower())
        if lookup_fn:
            # Handle type conversion
            if source.lower() in ('mlb', 'espn'):
                try:
                    team_id = int(team_id)
                except (ValueError, TypeError):
                    return None
            return lookup_fn(team_id)
        return None

    def get_all_teams(self, active_only: bool = True) -> list[TeamXref]:
        """Get all teams.

        Args:
            active_only: If True, return only active teams

        Returns:
            List of TeamXref records
        """
        teams = list(self._cache.values())
        if active_only:
            teams = [t for t in teams if t.active]
        return teams

    def get_teams_by_league(self, league: str) -> list[TeamXref]:
        """Get teams by league (AL or NL).

        Args:
            league: League code ('AL' or 'NL')

        Returns:
            List of TeamXref records
        """
        return [
            t
            for t in self._cache.values()
            if t.league and t.league.upper() == league.upper() and t.active
        ]

    def get_teams_by_division(self, division: str) -> list[TeamXref]:
        """Get teams by division.

        Args:
            division: Division name (e.g., 'East', 'Central', 'West')

        Returns:
            List of TeamXref records
        """
        return [
            t
            for t in self._cache.values()
            if t.division and division.lower() in t.division.lower() and t.active
        ]

    def register(self, xref: TeamXref) -> bool:
        """Register a new team xref.

        Args:
            xref: TeamXref to register

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
            logger.error(f'Failed to register team xref: {e}')
            return False

    def _save_to_db(self, xref: TeamXref) -> None:
        """Save xref record to database."""
        try:
            with self._db.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO bridge.team_xref (
                        canonical_id, mlb_id, mlb_code, retro_id, retro_code,
                        espn_id, lahman_id, lahman_code, name, city, nickname,
                        league, division, first_year, last_year, active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (canonical_id) DO UPDATE SET
                        mlb_id = EXCLUDED.mlb_id,
                        mlb_code = EXCLUDED.mlb_code,
                        retro_id = EXCLUDED.retro_id,
                        retro_code = EXCLUDED.retro_code,
                        espn_id = EXCLUDED.espn_id,
                        lahman_id = EXCLUDED.lahman_id,
                        lahman_code = EXCLUDED.lahman_code,
                        name = EXCLUDED.name,
                        city = EXCLUDED.city,
                        nickname = EXCLUDED.nickname,
                        league = EXCLUDED.league,
                        division = EXCLUDED.division,
                        first_year = EXCLUDED.first_year,
                        last_year = EXCLUDED.last_year,
                        active = EXCLUDED.active,
                        updated_at = NOW()
                    """,
                    (
                        xref.canonical_id,
                        xref.mlb_id,
                        xref.mlb_code,
                        xref.retro_id,
                        xref.retro_code,
                        xref.espn_id,
                        xref.lahman_id,
                        xref.lahman_code,
                        xref.name,
                        xref.city,
                        xref.nickname,
                        xref.league,
                        xref.division,
                        xref.first_year,
                        xref.last_year,
                        xref.active,
                    ),
                )
            self._db.commit()
        except Exception as e:
            logger.error(f'Failed to save team xref to DB: {e}')
            raise

    def get_stats(self) -> dict[str, int]:
        """Return statistics about the xref database."""
        active = sum(1 for t in self._cache.values() if t.active)
        return {
            'total_teams': len(self._cache),
            'active_teams': active,
            'historical_teams': len(self._cache) - active,
            'al_teams': len(self.get_teams_by_league('AL')),
            'nl_teams': len(self.get_teams_by_league('NL')),
        }
