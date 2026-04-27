"""Bullpen feature calculator.

Computes bullpen fatigue, depth, and effectiveness metrics:
- Team bullpen status and availability
- Individual reliever fatigue
- Fatigue and depth scores
- Comparative bullpen advantage

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import logging
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

from .base import FeatureConfig, FeatureResult, FeatureStore


logger = logging.getLogger(__name__)


class AvailabilityStatus(Enum):
    """Reliever availability status."""

    AVAILABLE = 'available'
    TIRED = 'tired'
    REST = 'rest'
    INJURED = 'injured'
    UNAVAILABLE = 'unavailable'


@dataclass
class RelieverFatigue:
    """Individual reliever fatigue metrics.

    Attributes:
        player_id: Pitcher ID
        team_id: Team ID
        season: Season year
        as_of_date: Date calculated
        games_last_3_days: Appearances last 3 days
        games_last_7_days: Appearances last 7 days
        pitches_last_3_days: Total pitches last 3 days
        pitches_last_7_days: Total pitches last 7 days
        back_to_back_days: Pitched yesterday
        three_in_four_days: 3 appearances in 4 days
        days_rest: Days since last appearance
        fatigue_score: 0-1, higher = more fatigued
        availability: Current availability status
    """

    player_id: int
    team_id: int
    season: int
    as_of_date: date
    games_last_3_days: int = 0
    games_last_7_days: int = 0
    pitches_last_3_days: int = 0
    pitches_last_7_days: int = 0
    back_to_back_days: bool = False
    three_in_four_days: bool = False
    days_rest: int = 99
    fatigue_score: float = 0.0
    availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE

    @property
    def needs_rest(self) -> bool:
        """Check if reliever should not pitch today."""
        return self.fatigue_score > 0.70 or self.availability == AvailabilityStatus.REST

    @property
    def is_available(self) -> bool:
        """Check if reliever is available to pitch."""
        return self.availability == AvailabilityStatus.AVAILABLE and self.fatigue_score < 0.50


@dataclass
class TeamBullpenStatus:
    """Team bullpen status for a game.

    Attributes:
        team_id: Team ID
        game_pk: Game ID
        season: Season year
        game_date: Game date
        is_home_team: Is home team
        available_pitchers: Count of available relievers
        rested_pitchers: Count with 2+ days rest
        tired_pitchers: Count who are fatigued
        bullpen_era: Season bullpen ERA
        bullpen_whip: Season bullpen WHIP
        l7_bullpen_era: Last 7 days ERA
        l7_save_pct: Save conversion rate
        games_last_3_days: Team games in last 3 days
        fatigue_score: 0-1, higher = more fatigued
        depth_score: 0-1, higher = deeper/better
    """

    team_id: int
    game_pk: int
    season: int
    game_date: date
    is_home_team: bool
    available_pitchers: int = 0
    rested_pitchers: int = 0
    tired_pitchers: int = 0
    bullpen_era: float = 4.50
    bullpen_whip: float = 1.35
    l7_bullpen_era: float = 4.50
    l7_save_pct: float = 0.70
    games_last_3_days: int = 0
    fatigue_score: float = 0.0
    depth_score: float = 0.0

    @property
    def is_fatigued(self) -> bool:
        """Check if bullpen is fatigued."""
        return self.fatigue_score > 0.60

    @property
    def is_strong(self) -> bool:
        """Check if bullpen is strong and well-rested."""
        return self.bullpen_era < 3.50 and self.depth_score > 0.70 and self.available_pitchers >= 6


class BullpenCalculator(FeatureStore):
    """Calculator for bullpen features.

    Tracks team bullpen fatigue, individual reliever workloads,
    and comparative advantages between teams.

    Example:
        >>> calc = BullpenCalculator(db_connection=conn)
        >>> # Get team bullpen status
        >>> status = calc.get_team_bullpen(team_id=147, game_pk=777777, season=2026)
        >>> print(
        ...     f'Available: {status.available_pitchers}, Fatigue: {status.fatigue_score:.2f}'
        ... )
        >>> # Check reliever fatigue
        >>> fatigue = calc.get_reliever_fatigue(player_id=12345, team_id=147, season=2026)
        >>> if fatigue.needs_rest:
        >>>     print("Reliever needs rest")
        >>> # Compare bullpens for a game
        >>> advantage = calc.get_bullpen_advantage(
        ...     home_team_id=147, away_team_id=118, game_pk=777777, season=2026
        ... )
    """

    # Fatigue thresholds
    FATIGUE_THRESHOLD_HIGH = 0.70
    FATIGUE_THRESHOLD_MEDIUM = 0.50

    # Bullpen quality thresholds
    STRONG_BULLPEN_ERA = 3.50
    WEAK_BULLPEN_ERA = 5.00

    def __init__(self, db_connection=None, config: FeatureConfig | None = None):
        """Initialize bullpen calculator.

        Args:
            db_connection: Database connection
            config: Feature configuration
        """
        super().__init__(db_connection, config)
        self._bullpen_cache: dict[tuple[int, int, int], TeamBullpenStatus] = {}
        self._reliever_cache: dict[tuple[int, int, date], RelieverFatigue] = {}

    @property
    def feature_name(self) -> str:
        return 'bullpen'

    @property
    def table_name(self) -> str:
        return 'features.bullpen_features'

    def get_team_bullpen(
        self, team_id: int, game_pk: int, season: int, game_date: date | None = None
    ) -> TeamBullpenStatus | None:
        """Get bullpen status for a team in a game.

        Args:
            team_id: Team ID
            game_pk: Game ID
            season: Season year
            game_date: Game date

        Returns:
            TeamBullpenStatus or None if not found
        """
        cache_key = (team_id, game_pk, season)

        if cache_key in self._bullpen_cache:
            return self._bullpen_cache[cache_key]

        if self.db is None:
            return None

        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """SELECT team_id, game_pk, season, game_date, is_home_team,
                              available_pitchers, rested_pitchers, tired_pitchers,
                              bullpen_era, bullpen_whip,
                              l7_bullpen_era, l7_save_pct,
                              games_last_3_days,
                              fatigue_score, depth_score
                       FROM features.bullpen_status
                       WHERE team_id = %s AND game_pk = %s AND season = %s""",
                    (team_id, game_pk, season),
                )

                row = cur.fetchone()
                if row:
                    status = TeamBullpenStatus(
                        team_id=row[0],
                        game_pk=row[1],
                        season=row[2],
                        game_date=row[3],
                        is_home_team=row[4],
                        available_pitchers=row[5] or 0,
                        rested_pitchers=row[6] or 0,
                        tired_pitchers=row[7] or 0,
                        bullpen_era=float(row[8]) if row[8] else 4.50,
                        bullpen_whip=float(row[9]) if row[9] else 1.35,
                        l7_bullpen_era=float(row[10]) if row[10] else 4.50,
                        l7_save_pct=float(row[11]) if row[11] else 0.70,
                        games_last_3_days=row[12] or 0,
                        fatigue_score=float(row[13]) if row[13] else 0.0,
                        depth_score=float(row[14]) if row[14] else 0.0,
                    )
                    self._bullpen_cache[cache_key] = status
                    return status
        except Exception as e:
            logger.error(f'Failed to load bullpen status: {e}')

        return None

    def get_reliever_fatigue(
        self, player_id: int, team_id: int, season: int, as_of_date: date | None = None
    ) -> RelieverFatigue | None:
        """Get fatigue status for a reliever.

        Args:
            player_id: Pitcher ID
            team_id: Team ID
            season: Season year
            as_of_date: Date to check as of

        Returns:
            RelieverFatigue or None if not found
        """
        if as_of_date is None:
            as_of_date = date.today()

        cache_key = (player_id, season, as_of_date)

        if cache_key in self._reliever_cache:
            return self._reliever_cache[cache_key]

        if self.db is None:
            return None

        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """SELECT player_id, team_id, season, as_of_date,
                              games_last_3_days, games_last_7_days,
                              pitches_last_3_days, pitches_last_7_days,
                              back_to_back_days, three_in_four_days,
                              days_rest, fatigue_score, availability_status
                       FROM features.reliever_fatigue
                       WHERE player_id = %s AND team_id = %s AND season = %s
                         AND as_of_date <= %s
                       ORDER BY as_of_date DESC
                       LIMIT 1""",
                    (player_id, team_id, season, as_of_date),
                )

                row = cur.fetchone()
                if row:
                    fatigue = RelieverFatigue(
                        player_id=row[0],
                        team_id=row[1],
                        season=row[2],
                        as_of_date=row[3],
                        games_last_3_days=row[4] or 0,
                        games_last_7_days=row[5] or 0,
                        pitches_last_3_days=row[6] or 0,
                        pitches_last_7_days=row[7] or 0,
                        back_to_back_days=row[8] or False,
                        three_in_four_days=row[9] or False,
                        days_rest=row[10] or 99,
                        fatigue_score=float(row[11]) if row[11] else 0.0,
                        availability=AvailabilityStatus(row[12])
                        if row[12]
                        else AvailabilityStatus.AVAILABLE,
                    )
                    self._reliever_cache[cache_key] = fatigue
                    return fatigue
        except Exception as e:
            logger.error(f'Failed to load reliever fatigue: {e}')

        return None

    def calculate_fatigue_score(
        self, games_3d: int, pitches_1d: int, back_to_back: bool, days_rest: int
    ) -> float:
        """Calculate fatigue score from workload metrics.

        Args:
            games_3d: Games in last 3 days
            pitches_1d: Pitches thrown yesterday
            back_to_back: Pitched yesterday
            days_rest: Days since last appearance

        Returns:
            Fatigue score 0.0-1.0
        """
        score = 0.0

        # Yesterday's pitches (high impact)
        if pitches_1d > 30:
            score += 0.30
        elif pitches_1d > 15:
            score += 0.20
        elif pitches_1d > 0:
            score += 0.10

        # Games in last 3 days
        score += games_3d * 0.10

        # Back to back
        if back_to_back:
            score += 0.20

        # Rest reduces score
        if days_rest >= 3:
            score = max(0, score - 0.30)
        elif days_rest >= 2:
            score = max(0, score - 0.20)
        elif days_rest >= 1:
            score = max(0, score - 0.10)

        return min(1.0, score)

    def get_bullpen_advantage(
        self, home_team_id: int, away_team_id: int, game_pk: int, season: int
    ) -> dict[str, Any]:
        """Compare bullpens and determine advantage.

        Args:
            home_team_id: Home team ID
            away_team_id: Away team ID
            game_pk: Game ID
            season: Season year

        Returns:
            Dictionary with comparison results
        """
        home_status = self.get_team_bullpen(home_team_id, game_pk, season)
        away_status = self.get_team_bullpen(away_team_id, game_pk, season)

        if not home_status and not away_status:
            return {
                'fatigue_advantage': 'even',
                'depth_advantage': 'even',
                'overall_advantage': 'even',
                'advantage_score': 0.0,
                'narrative': 'Bullpen data unavailable',
            }

        # Fatigue advantage (lower fatigue = advantage)
        if home_status and away_status:
            if home_status.fatigue_score < away_status.fatigue_score:
                fatigue_adv = 'home'
                fatigue_score = away_status.fatigue_score - home_status.fatigue_score
            elif away_status.fatigue_score < home_status.fatigue_score:
                fatigue_adv = 'away'
                fatigue_score = -(home_status.fatigue_score - away_status.fatigue_score)
            else:
                fatigue_adv = 'even'
                fatigue_score = 0.0
        elif home_status:
            fatigue_adv = 'home'
            fatigue_score = 0.1
        else:
            fatigue_adv = 'away'
            fatigue_score = -0.1

        # Depth advantage (higher depth = advantage)
        if home_status and away_status:
            if home_status.depth_score > away_status.depth_score:
                depth_adv = 'home'
                depth_score = home_status.depth_score - away_status.depth_score
            elif away_status.depth_score > home_status.depth_score:
                depth_adv = 'away'
                depth_score = -(away_status.depth_score - home_status.depth_score)
            else:
                depth_adv = 'even'
                depth_score = 0.0
        elif home_status:
            depth_adv = 'home'
            depth_score = 0.1
        else:
            depth_adv = 'away'
            depth_score = -0.1

        # Overall (fatigue + depth)
        overall_score = fatigue_score + depth_score

        if overall_score > 0.2:
            overall_adv = 'home'
            narrative = 'Home bullpen advantage'
        elif overall_score < -0.2:
            overall_adv = 'away'
            narrative = 'Away bullpen advantage'
        else:
            overall_adv = 'even'
            narrative = 'Bullpens even'

        # Add specific notes
        if home_status and home_status.is_fatigued:
            narrative = 'Home bullpen fatigued'
        elif away_status and away_status.is_fatigued:
            narrative = 'Away bullpen fatigued'
        elif home_status and home_status.is_strong and away_status and away_status.is_strong:
            narrative = 'Both bullpens strong'

        return {
            'fatigue_advantage': fatigue_adv,
            'depth_advantage': depth_adv,
            'overall_advantage': overall_adv,
            'fatigue_score': fatigue_score,
            'depth_score': depth_score,
            'advantage_score': overall_score,
            'narrative': narrative,
            'home_available': home_status.available_pitchers if home_status else None,
            'away_available': away_status.available_pitchers if away_status else None,
            'home_fatigue': home_status.fatigue_score if home_status else None,
            'away_fatigue': away_status.fatigue_score if away_status else None,
        }

    def compute(self, game_state: Any) -> float | None:
        """Compute bullpen feature (required by base class).

        Args:
            game_state: Game state with team information

        Returns:
            Advantage score or None
        """
        home_id = getattr(game_state, 'home_team_id', None)
        away_id = getattr(game_state, 'away_team_id', None)
        game_pk = getattr(game_state, 'game_pk', None)
        season = getattr(game_state, 'season', None)

        if home_id and away_id and game_pk:
            result = self.get_bullpen_advantage(home_id, away_id, game_pk, season or 2026)
            return result.get('advantage_score', 0.0)

        return None

    def save_bullpen_features(
        self, game_pk: int, season: int, home_team_id: int, away_team_id: int
    ) -> bool:
        """Save computed bullpen features to database.

        Args:
            game_pk: Game ID
            season: Season year
            home_team_id: Home team ID
            away_team_id: Away team ID

        Returns:
            True if saved successfully
        """
        if self.db is None:
            return False

        try:
            # Get bullpen status for both teams
            home_status = self.get_team_bullpen(home_team_id, game_pk, season)
            away_status = self.get_team_bullpen(away_team_id, game_pk, season)

            # Calculate advantage
            advantage = self.get_bullpen_advantage(home_team_id, away_team_id, game_pk, season)

            with self.db.cursor() as cur:
                cur.execute(
                    """INSERT INTO features.bullpen_features 
                        (game_pk, season,
                         home_team_id, home_bullpen_fatigue, home_bullpen_depth,
                         home_available_pitchers, home_rested_pitchers,
                         home_bullpen_era, home_bullpen_l7_era, home_bullpen_save_pct,
                         away_team_id, away_bullpen_fatigue, away_bullpen_depth,
                         away_available_pitchers, away_rested_pitchers,
                         away_bullpen_era, away_bullpen_l7_era, away_bullpen_save_pct,
                         fatigue_advantage, depth_advantage, overall_bullpen_advantage,
                         fatigue_advantage_score, depth_advantage_score, overall_advantage_score)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                               %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (game_pk) DO UPDATE SET
                         home_bullpen_fatigue = EXCLUDED.home_bullpen_fatigue,
                         home_bullpen_depth = EXCLUDED.home_bullpen_depth,
                         away_bullpen_fatigue = EXCLUDED.away_bullpen_fatigue,
                         away_bullpen_depth = EXCLUDED.away_bullpen_depth,
                         fatigue_advantage = EXCLUDED.fatigue_advantage,
                         depth_advantage = EXCLUDED.depth_advantage,
                         overall_bullpen_advantage = EXCLUDED.overall_bullpen_advantage,
                         overall_advantage_score = EXCLUDED.overall_advantage_score,
                         computed_at = NOW()""",
                    (
                        game_pk,
                        season,
                        home_team_id,
                        home_status.fatigue_score if home_status else 0.0,
                        home_status.depth_score if home_status else 0.0,
                        home_status.available_pitchers if home_status else 0,
                        home_status.rested_pitchers if home_status else 0,
                        home_status.bullpen_era if home_status else 4.50,
                        home_status.l7_bullpen_era if home_status else 4.50,
                        home_status.l7_save_pct if home_status else 0.70,
                        away_team_id,
                        away_status.fatigue_score if away_status else 0.0,
                        away_status.depth_score if away_status else 0.0,
                        away_status.available_pitchers if away_status else 0,
                        away_status.rested_pitchers if away_status else 0,
                        away_status.bullpen_era if away_status else 4.50,
                        away_status.l7_bullpen_era if away_status else 4.50,
                        away_status.l7_save_pct if away_status else 0.70,
                        advantage['fatigue_advantage'],
                        advantage['depth_advantage'],
                        advantage['overall_advantage'],
                        advantage['fatigue_score'],
                        advantage['depth_score'],
                        advantage['advantage_score'],
                    ),
                )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f'Failed to save bullpen features: {e}')
            return False

    def get_fatigued_relievers(
        self, team_id: int, season: int, threshold: float = 0.50
    ) -> list[RelieverFatigue]:
        """Get list of fatigued relievers for a team.

        Args:
            team_id: Team ID
            season: Season year
            threshold: Fatigue score threshold

        Returns:
            List of fatigued relievers
        """
        if self.db is None:
            return []

        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """SELECT player_id, team_id, season, as_of_date,
                              games_last_3_days, games_last_7_days,
                              pitches_last_3_days, pitches_last_7_days,
                              back_to_back_days, three_in_four_days,
                              days_rest, fatigue_score, availability_status
                       FROM features.reliever_fatigue
                       WHERE team_id = %s AND season = %s
                         AND (fatigue_score > %s 
                              OR availability_status = 'tired'
                              OR availability_status = 'rest')
                       ORDER BY fatigue_score DESC""",
                    (team_id, season, threshold),
                )

                return [
                    RelieverFatigue(
                        player_id=row[0],
                        team_id=row[1],
                        season=row[2],
                        as_of_date=row[3],
                        games_last_3_days=row[4] or 0,
                        games_last_7_days=row[5] or 0,
                        pitches_last_3_days=row[6] or 0,
                        pitches_last_7_days=row[7] or 0,
                        back_to_back_days=row[8] or False,
                        three_in_four_days=row[9] or False,
                        days_rest=row[10] or 99,
                        fatigue_score=float(row[11]) if row[11] else 0.0,
                        availability=AvailabilityStatus(row[12])
                        if row[12]
                        else AvailabilityStatus.AVAILABLE,
                    )
                    for row in cur.fetchall()
                ]
        except Exception as e:
            logger.error(f'Failed to get fatigued relievers: {e}')
            return []

    def _build_historical(self, config: FeatureConfig, result: FeatureResult) -> None:
        """Build historical bullpen features.

        Args:
            config: Feature configuration
            result: Result object to update
        """
        logger.info('Building historical bullpen features')

        if self.db is None:
            result.add_error('No database connection')
            return

        try:
            result.rows_computed = 0
            result.rows_inserted = 0
        except Exception as e:
            result.add_error(f'Historical build failed: {e}')

    def _build_live(self, config: FeatureConfig, result: FeatureResult) -> None:
        """Build live bullpen features.

        Args:
            config: Feature configuration
            result: Result object to update
        """
        logger.info('Building live bullpen features')
        result.metadata['live_mode'] = 'on_demand'

    def get_reliever_recommendation(self, player_id: int, team_id: int, season: int) -> str:
        """Get usage recommendation for a reliever.

        Args:
            player_id: Pitcher ID
            team_id: Team ID
            season: Season year

        Returns:
            Recommendation string
        """
        fatigue = self.get_reliever_fatigue(player_id, team_id, season)

        if not fatigue:
            return 'Data unavailable'

        if fatigue.fatigue_score > 0.70 or fatigue.availability == AvailabilityStatus.REST:
            return 'Must rest - high fatigue'
        if fatigue.fatigue_score > 0.50:
            return 'Avoid using - elevated fatigue'
        if fatigue.back_to_back_days:
            return 'Monitor closely - pitched yesterday'
        if fatigue.three_in_four_days:
            return 'Caution - 3 games in 4 days'
        if fatigue.days_rest >= 2:
            return 'Well rested - good to use'
        return 'Available'
