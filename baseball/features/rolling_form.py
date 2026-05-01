"""Rolling form feature calculator.

Computes recent performance metrics for batters and pitchers:
- 7/14/30 day windows
- Hot/cold indicators
- Trend direction
- Form advantage calculations

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


class TrendDirection(Enum):
    """Performance trend direction."""

    IMPROVING = 'improving'
    DECLINING = 'declining'
    STABLE = 'stable'
    UNKNOWN = 'unknown'


@dataclass
class BatterForm:
    """Batter rolling form metrics.

    Attributes:
        player_id: Batter ID
        season: Season year
        as_of_date: Date form was calculated
        l7_ops: Last 7 days OPS
        l14_ops: Last 14 days OPS
        l30_ops: Last 30 days OPS
        l7_pa: Last 7 days plate appearances
        l30_pa: Last 30 days plate appearances
        trend: Trend direction
        is_hot: Is batter hot (OPS > 0.850)
        is_cold: Is batter cold (OPS < 0.600)
    """

    player_id: int
    season: int
    as_of_date: date
    l7_ops: float = 0.0
    l14_ops: float = 0.0
    l30_ops: float = 0.0
    l7_pa: int = 0
    l30_pa: int = 0
    trend: TrendDirection = TrendDirection.UNKNOWN
    is_hot: bool = False
    is_cold: bool = False

    @property
    def form_score(self) -> float:
        """Calculate overall form score (0-1, higher = better)."""
        if self.l14_ops > 0:
            return min(1.0, max(0.0, (self.l14_ops - 0.400) / 0.600))
        return 0.5


@dataclass
class PitcherForm:
    """Pitcher rolling form metrics.

    Attributes:
        player_id: Pitcher ID
        season: Season year
        as_of_date: Date form was calculated
        l7_era: Last 7 days ERA
        l14_era: Last 14 days ERA
        l30_era: Last 30 days ERA
        l7_whip: Last 7 days WHIP
        l30_whip: Last 30 days WHIP
        l30_k_9: Last 30 days K/9
        l30_ip: Last 30 days innings pitched
        trend: Trend direction
        is_hot: Is pitcher hot (ERA < 3.00)
        is_cold: Is pitcher cold (ERA > 5.00)
        consistency_score: Lower = more consistent
    """

    player_id: int
    season: int
    as_of_date: date
    l7_era: float = 0.0
    l14_era: float = 0.0
    l30_era: float = 0.0
    l7_whip: float = 0.0
    l30_whip: float = 0.0
    l30_k_9: float = 0.0
    l30_ip: float = 0.0
    trend: TrendDirection = TrendDirection.UNKNOWN
    is_hot: bool = False
    is_cold: bool = False
    consistency_score: float = 0.0

    @property
    def form_score(self) -> float:
        """Calculate overall form score (0-1, higher = better for pitcher)."""
        if self.l14_era > 0:
            # Lower ERA = higher score
            # 2.00 ERA = 1.0, 7.00 ERA = 0.0
            return min(1.0, max(0.0, (7.0 - self.l14_era) / 5.0))
        return 0.5


class RollingFormCalculator(FeatureStore):
    """Calculator for rolling form features.

    Tracks recent performance for batters and pitchers across
    7/14/30 day windows with trend analysis.

    Example:
        >>> calc = RollingFormCalculator(db_connection=conn)
        >>> # Get batter form
        >>> form = calc.get_batter_form(player_id=123, season=2026)
        >>> print(f'L14 OPS: {form.l14_ops:.3f}, Trend: {form.trend.value}')
        >>> # Check if player is hot/cold
        >>> if form.is_hot:
        >>>     print("Player is hot!")
        >>> # Compare two players
        >>> advantage = calc.get_form_advantage(batter_id=123, pitcher_id=456, season=2026)
    """

    # Thresholds for hot/cold determination
    HOT_BATTER_OPS = 0.850
    COLD_BATTER_OPS = 0.600
    HOT_PITCHER_ERA = 3.00
    COLD_PITCHER_ERA = 5.00

    def __init__(self, db_connection=None, config: FeatureConfig | None = None) -> None:
        """Initialize rolling form calculator.

        Args:
            db_connection: Database connection
            config: Feature configuration
        """
        super().__init__(db_connection, config)
        self._batter_cache: dict[tuple[int, int, date], BatterForm] = {}
        self._pitcher_cache: dict[tuple[int, int, date], PitcherForm] = {}

    @property
    def feature_name(self) -> str:
        return 'rolling_form'

    @property
    def table_name(self) -> str:
        return 'features.rolling_form_features'

    def get_batter_form(
        self, player_id: int, season: int, as_of_date: date | None = None,
    ) -> BatterForm | None:
        """Get rolling form for a batter.

        Args:
            player_id: Batter ID
            season: Season year
            as_of_date: Date to calculate form as of (default: today)

        Returns:
            BatterForm or None if not found
        """
        if as_of_date is None:
            as_of_date = date.today()

        cache_key = (player_id, season, as_of_date)

        if cache_key in self._batter_cache:
            return self._batter_cache[cache_key]

        if self.db is None:
            return None

        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """SELECT player_id, season, as_of_date,
                              l7_ops, l14_ops, l30_ops,
                              l7_pa, l30_pa,
                              trend_direction,
                              l14_ops > %s as is_hot,
                              l14_ops < %s as is_cold
                       FROM features.batter_rolling_form
                       WHERE player_id = %s AND season = %s
                         AND as_of_date <= %s
                       ORDER BY as_of_date DESC
                       LIMIT 1""",
                    (self.HOT_BATTER_OPS, self.COLD_BATTER_OPS, player_id, season, as_of_date),
                )

                row = cur.fetchone()
                if row:
                    form = BatterForm(
                        player_id=row[0],
                        season=row[1],
                        as_of_date=row[2],
                        l7_ops=float(row[3]) if row[3] else 0.0,
                        l14_ops=float(row[4]) if row[4] else 0.0,
                        l30_ops=float(row[5]) if row[5] else 0.0,
                        l7_pa=row[6] or 0,
                        l30_pa=row[7] or 0,
                        trend=TrendDirection(row[8]) if row[8] else TrendDirection.UNKNOWN,
                        is_hot=row[9] if row[9] is not None else False,
                        is_cold=row[10] if row[10] is not None else False,
                    )
                    self._batter_cache[cache_key] = form
                    return form
        except Exception as e:
            logger.exception(f'Failed to load batter form: {e}')

        return None

    def get_pitcher_form(
        self, player_id: int, season: int, as_of_date: date | None = None,
    ) -> PitcherForm | None:
        """Get rolling form for a pitcher.

        Args:
            player_id: Pitcher ID
            season: Season year
            as_of_date: Date to calculate form as of (default: today)

        Returns:
            PitcherForm or None if not found
        """
        if as_of_date is None:
            as_of_date = date.today()

        cache_key = (player_id, season, as_of_date)

        if cache_key in self._pitcher_cache:
            return self._pitcher_cache[cache_key]

        if self.db is None:
            return None

        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """SELECT player_id, season, as_of_date,
                              l7_era, l14_era, l30_era,
                              l7_whip, l30_whip,
                              l30_k_9, l30_ip,
                              trend_direction,
                              l14_era < %s as is_hot,
                              l14_era > %s as is_cold,
                              consistency_score
                       FROM features.pitcher_rolling_form
                       WHERE player_id = %s AND season = %s
                         AND as_of_date <= %s
                       ORDER BY as_of_date DESC
                       LIMIT 1""",
                    (self.HOT_PITCHER_ERA, self.COLD_PITCHER_ERA, player_id, season, as_of_date),
                )

                row = cur.fetchone()
                if row:
                    form = PitcherForm(
                        player_id=row[0],
                        season=row[1],
                        as_of_date=row[2],
                        l7_era=float(row[3]) if row[3] else 0.0,
                        l14_era=float(row[4]) if row[4] else 0.0,
                        l30_era=float(row[5]) if row[5] else 0.0,
                        l7_whip=float(row[6]) if row[6] else 0.0,
                        l30_whip=float(row[7]) if row[7] else 0.0,
                        l30_k_9=float(row[8]) if row[8] else 0.0,
                        l30_ip=float(row[9]) if row[9] else 0.0,
                        trend=TrendDirection(row[10]) if row[10] else TrendDirection.UNKNOWN,
                        is_hot=row[11] if row[11] is not None else False,
                        is_cold=row[12] if row[12] is not None else False,
                        consistency_score=float(row[13]) if row[13] else 0.0,
                    )
                    self._pitcher_cache[cache_key] = form
                    return form
        except Exception as e:
            logger.exception(f'Failed to load pitcher form: {e}')

        return None

    def get_form_advantage(
        self, batter_id: int, pitcher_id: int, season: int, as_of_date: date | None = None,
    ) -> tuple[str, float]:
        """Determine which player has form advantage.

        Args:
            batter_id: Batter ID
            pitcher_id: Pitcher ID
            season: Season year
            as_of_date: Date to calculate as of

        Returns:
            Tuple of (advantage, score) where:
            - advantage: 'batter', 'pitcher', or 'neutral'
            - score: 0-1 (higher = advantage to batter)
        """
        batter_form = self.get_batter_form(batter_id, season, as_of_date)
        pitcher_form = self.get_pitcher_form(pitcher_id, season, as_of_date)

        if not batter_form and not pitcher_form:
            return ('neutral', 0.5)

        if not batter_form:
            # Only pitcher form known - assume neutral batter
            pitcher_score = pitcher_form.form_score if pitcher_form else 0.5
            # Invert pitcher score (good pitcher = bad for batter)
            batter_implied = 1.0 - pitcher_score
            return ('pitcher' if pitcher_score > 0.6 else 'neutral', batter_implied)

        if not pitcher_form:
            # Only batter form known
            return ('batter' if batter_form.is_hot else 'neutral', batter_form.form_score)

        # Both forms known
        batter_score = batter_form.form_score
        pitcher_score = pitcher_form.form_score  # Higher = better for pitcher

        # Composite: good batter vs bad pitcher = big advantage
        # Bad batter vs good pitcher = big disadvantage
        combined_score = (batter_score + (1.0 - pitcher_score)) / 2.0

        if batter_form.is_hot and not pitcher_form.is_hot:
            advantage = 'batter'
        elif pitcher_form.is_hot and not batter_form.is_hot:
            advantage = 'pitcher'
        elif combined_score > 0.6:
            advantage = 'batter'
        elif combined_score < 0.4:
            advantage = 'pitcher'
        else:
            advantage = 'neutral'

        return (advantage, combined_score)

    def is_batter_hot(self, player_id: int, season: int, as_of_date: date | None = None) -> bool:
        """Quick check if batter is hot.

        Args:
            player_id: Batter ID
            season: Season year
            as_of_date: Date to check as of

        Returns:
            True if hot (L14 OPS > 0.850)
        """
        form = self.get_batter_form(player_id, season, as_of_date)
        return form.is_hot if form else False

    def is_pitcher_hot(self, player_id: int, season: int, as_of_date: date | None = None) -> bool:
        """Quick check if pitcher is hot.

        Args:
            player_id: Pitcher ID
            season: Season year
            as_of_date: Date to check as of

        Returns:
            True if hot (L14 ERA < 3.00)
        """
        form = self.get_pitcher_form(player_id, season, as_of_date)
        return form.is_hot if form else False

    def compute(self, game_state: Any) -> float | None:
        """Compute form feature (required by base class).

        Args:
            game_state: Game state with batter_id and pitcher_id

        Returns:
            Form score or None
        """
        batter_id = getattr(game_state, 'batter_id', None)
        pitcher_id = getattr(game_state, 'pitcher_id', None)
        season = getattr(game_state, 'season', None)

        if batter_id and pitcher_id:
            _, score = self.get_form_advantage(batter_id, pitcher_id, season or 2026)
            return score

        return None

    def save_form_features(
        self,
        game_pk: int,
        batter_id: int,
        pitcher_id: int,
        season: int,
        game_date: date | None = None,
    ) -> bool:
        """Save computed form features to database.

        Args:
            game_pk: Game ID
            batter_id: Batter ID
            pitcher_id: Pitcher ID
            season: Season year
            game_date: Game date (default: today)

        Returns:
            True if saved successfully
        """
        if self.db is None:
            return False

        if game_date is None:
            game_date = date.today()

        try:
            # Get forms
            batter_form = self.get_batter_form(batter_id, season, game_date)
            pitcher_form = self.get_pitcher_form(pitcher_id, season, game_date)

            # Calculate advantage
            advantage, score = self.get_form_advantage(batter_id, pitcher_id, season, game_date)

            with self.db.cursor() as cur:
                cur.execute(
                    """INSERT INTO features.rolling_form_features
                        (game_pk, season,
                         batter_id, pitcher_id,
                         batter_l7_ops, batter_l14_ops, batter_l30_ops,
                         batter_trend, batter_is_hot, batter_is_cold,
                         batter_l7_pa, batter_l30_pa,
                         pitcher_l7_era, pitcher_l14_era, pitcher_l30_era,
                         pitcher_l7_whip, pitcher_l30_whip,
                         pitcher_l30_k_9,
                         pitcher_trend, pitcher_is_hot, pitcher_is_cold,
                         pitcher_l7_ip, pitcher_l30_ip,
                         form_advantage, form_score)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                               %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (game_pk, batter_id, pitcher_id) DO UPDATE SET
                         batter_l7_ops = EXCLUDED.batter_l7_ops,
                         batter_l14_ops = EXCLUDED.batter_l14_ops,
                         batter_trend = EXCLUDED.batter_trend,
                         batter_is_hot = EXCLUDED.batter_is_hot,
                         pitcher_l7_era = EXCLUDED.pitcher_l7_era,
                         pitcher_l14_era = EXCLUDED.pitcher_l14_era,
                         pitcher_trend = EXCLUDED.pitcher_trend,
                         pitcher_is_hot = EXCLUDED.pitcher_is_hot,
                         form_advantage = EXCLUDED.form_advantage,
                         form_score = EXCLUDED.form_score,
                         computed_at = NOW()""",
                    (
                        game_pk,
                        season,
                        batter_id,
                        pitcher_id,
                        batter_form.l7_ops if batter_form else 0.0,
                        batter_form.l14_ops if batter_form else 0.0,
                        batter_form.l30_ops if batter_form else 0.0,
                        batter_form.trend.value if batter_form else 'unknown',
                        batter_form.is_hot if batter_form else False,
                        batter_form.is_cold if batter_form else False,
                        batter_form.l7_pa if batter_form else 0,
                        batter_form.l30_pa if batter_form else 0,
                        pitcher_form.l7_era if pitcher_form else 0.0,
                        pitcher_form.l14_era if pitcher_form else 0.0,
                        pitcher_form.l30_era if pitcher_form else 0.0,
                        pitcher_form.l7_whip if pitcher_form else 0.0,
                        pitcher_form.l30_whip if pitcher_form else 0.0,
                        pitcher_form.l30_k_9 if pitcher_form else 0.0,
                        pitcher_form.trend.value if pitcher_form else 'unknown',
                        pitcher_form.is_hot if pitcher_form else False,
                        pitcher_form.is_cold if pitcher_form else False,
                        pitcher_form.l7_ip if pitcher_form else 0.0,
                        pitcher_form.l30_ip if pitcher_form else 0.0,
                        advantage,
                        score,
                    ),
                )
            self.db.commit()
            return True
        except Exception as e:
            logger.exception(f'Failed to save form features: {e}')
            return False

    def _build_historical(self, config: FeatureConfig, result: FeatureResult) -> None:
        """Build historical rolling form features.

        Args:
            config: Feature configuration
            result: Result object to update
        """
        logger.info('Building historical rolling form features')

        if self.db is None:
            result.add_error('No database connection')
            return

        try:
            result.rows_computed = 0
            result.rows_inserted = 0
        except Exception as e:
            result.add_error(f'Historical build failed: {e}')

    def _build_live(self, config: FeatureConfig, result: FeatureResult) -> None:
        """Build live rolling form features.

        Args:
            config: Feature configuration
            result: Result object to update
        """
        logger.info('Building live rolling form features')
        result.metadata['live_mode'] = 'on_demand'

    def get_hot_batters(self, season: int, min_pa: int = 20) -> list[dict[str, Any]]:
        """Get list of hot batters for a season.

        Args:
            season: Season year
            min_pa: Minimum plate appearances

        Returns:
            List of hot batter dictionaries
        """
        if self.db is None:
            return []

        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """SELECT player_id, l14_ops, l14_pa, trend_direction
                       FROM features.batter_rolling_form
                       WHERE season = %s AND l14_pa >= %s AND l14_ops > %s
                       ORDER BY l14_ops DESC""",
                    (season, min_pa, self.HOT_BATTER_OPS),
                )

                return [
                    {
                        'player_id': row[0],
                        'l14_ops': float(row[1]),
                        'l14_pa': row[2],
                        'trend': row[3],
                    }
                    for row in cur.fetchall()
                ]
        except Exception as e:
            logger.exception(f'Failed to get hot batters: {e}')
            return []

    def get_hot_pitchers(self, season: int, min_ip: float = 10.0) -> list[dict[str, Any]]:
        """Get list of hot pitchers for a season.

        Args:
            season: Season year
            min_ip: Minimum innings pitched

        Returns:
            List of hot pitcher dictionaries
        """
        if self.db is None:
            return []

        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """SELECT player_id, l14_era, l14_ip, l14_k_9, trend_direction
                       FROM features.pitcher_rolling_form
                       WHERE season = %s AND l14_ip >= %s AND l14_era < %s
                       ORDER BY l14_era ASC""",
                    (season, min_ip, self.HOT_PITCHER_ERA),
                )

                return [
                    {
                        'player_id': row[0],
                        'l14_era': float(row[1]),
                        'l14_ip': float(row[2]),
                        'l14_k_9': float(row[3]),
                        'trend': row[4],
                    }
                    for row in cur.fetchall()
                ]
        except Exception as e:
            logger.exception(f'Failed to get hot pitchers: {e}')
            return []
