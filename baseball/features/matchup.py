"""Matchup feature calculator.

Computes batter vs pitcher matchup features including:
- Career head-to-head history
- Platoon splits (lefty/righty)
- Recent matchup performance
- Combined matchup score

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .base import FeatureConfig, FeatureResult, FeatureStore


logger = logging.getLogger(__name__)


class Handedness(Enum):
    """Player handedness."""

    LEFT = 'L'
    RIGHT = 'R'
    SWITCH = 'S'


@dataclass
class MatchupHistory:
    """Batter vs pitcher matchup history.

    Attributes:
        batter_id: Batter canonical ID
        pitcher_id: Pitcher canonical ID
        career_pa: Career plate appearances vs this pitcher
        career_avg: Career batting average
        career_ops: Career OPS
        career_hr: Career home runs
        recent_pa: Recent PA (last 2 seasons)
        recent_avg: Recent batting average
        first_met: First matchup date
        last_met: Last matchup date
    """

    batter_id: int
    pitcher_id: int
    career_pa: int = 0
    career_avg: float = 0.0
    career_ops: float = 0.0
    career_hr: int = 0
    recent_pa: int = 0
    recent_avg: float = 0.0
    first_met: str | None = None
    last_met: str | None = None

    @property
    def has_history(self) -> bool:
        """Check if there's meaningful matchup history."""
        return self.career_pa >= 5

    @property
    def familiarity(self) -> str:
        """Categorize matchup familiarity."""
        if self.career_pa >= 20:
            return 'familiar'
        if self.career_pa >= 5:
            return 'some_history'
        if self.career_pa > 0:
            return 'rare'
        return 'first_meeting'


@dataclass
class PlatoonSplit:
    """Platoon split for a player.

    Attributes:
        player_id: Player canonical ID
        player_type: 'batter' or 'pitcher'
        season: Season year
        throws: Pitcher throwing hand (L/R)
        bats: Batter batting side (L/R/S)
        vs_l_ops: OPS vs left-handed
        vs_r_ops: OPS vs right-handed
        platoon_advantage: OPS difference
        vs_l_pa: PA vs left-handed
        vs_r_pa: PA vs right-handed
    """

    player_id: int
    player_type: str
    season: int
    throws: str | None = None
    bats: str | None = None
    vs_l_ops: float = 0.0
    vs_r_ops: float = 0.0
    vs_l_pa: int = 0
    vs_r_pa: int = 0

    @property
    def platoon_advantage(self) -> float:
        """Calculate platoon advantage.

        For batters: positive = better vs RHP (typical for LHB)
        For pitchers: negative = better vs RHB (typical for RHP)
        """
        return (
            self.vs_r_ops - self.vs_l_ops
            if self.player_type == 'batter'
            else self.vs_l_ops - self.vs_r_ops
        )

    def get_vs_hand_ops(self, opponent_hand: str) -> float:
        """Get OPS vs specific opponent hand.

        Args:
            opponent_hand: 'L' or 'R'

        Returns:
            OPS vs that hand
        """
        if opponent_hand == 'L':
            return self.vs_l_ops
        return self.vs_r_ops


class MatchupCalculator(FeatureStore):
    """Calculator for batter vs pitcher matchup features.

    Computes head-to-head history, platoon advantages, and
    combined matchup scores for predictions.

    Example:
        >>> calc = MatchupCalculator(db_connection=conn)
        >>> calc.load_matchup_history(batter_id=123, pitcher_id=456)
        >>> # Get platoon advantage
        >>> is_advantage = calc.is_platoon_advantage(batter_id=123, pitcher_id=456)
        >>> # Compute matchup score
        >>> score = calc.compute_matchup_score(batter_id=123, pitcher_id=456, season=2026)
    """

    def __init__(self, db_connection=None, config: FeatureConfig | None = None):
        """Initialize matchup calculator.

        Args:
            db_connection: Database connection
            config: Feature configuration
        """
        super().__init__(db_connection, config)
        self._matchup_cache: dict[tuple[int, int], MatchupHistory] = {}
        self._platoon_cache: dict[tuple[int, str], PlatoonSplit] = {}

    @property
    def feature_name(self) -> str:
        return 'matchup'

    @property
    def table_name(self) -> str:
        return 'features.matchup_features'

    def load_matchup_history(
        self, batter_id: int, pitcher_id: int, season: int | None = None
    ) -> MatchupHistory | None:
        """Load matchup history from database.

        Args:
            batter_id: Batter ID
            pitcher_id: Pitcher ID
            season: Optional season to filter

        Returns:
            MatchupHistory or None if not found
        """
        cache_key = (batter_id, pitcher_id)

        if cache_key in self._matchup_cache:
            return self._matchup_cache[cache_key]

        if self.db is None:
            return None

        try:
            with self.db.cursor() as cur:
                if season:
                    cur.execute(
                        """SELECT batter_id, pitcher_id, career_pa, career_avg,
                                  career_ops, career_hr, recent_pa, recent_avg,
                                  first_matchup_date, last_matchup_date
                           FROM features.batter_vs_pitcher_matchups
                           WHERE batter_id = %s AND pitcher_id = %s AND season = %s""",
                        (batter_id, pitcher_id, season),
                    )
                else:
                    cur.execute(
                        """SELECT batter_id, pitcher_id, 
                                  SUM(career_pa), AVG(career_avg),
                                  AVG(career_ops), SUM(career_hr),
                                  SUM(recent_pa), AVG(recent_avg),
                                  MIN(first_matchup_date), MAX(last_matchup_date)
                           FROM features.batter_vs_pitcher_matchups
                           WHERE batter_id = %s AND pitcher_id = %s
                           GROUP BY batter_id, pitcher_id""",
                        (batter_id, pitcher_id),
                    )

                row = cur.fetchone()
                if row:
                    history = MatchupHistory(
                        batter_id=row[0],
                        pitcher_id=row[1],
                        career_pa=row[2] or 0,
                        career_avg=float(row[3]) if row[3] else 0.0,
                        career_ops=float(row[4]) if row[4] else 0.0,
                        career_hr=row[5] or 0,
                        recent_pa=row[6] or 0,
                        recent_avg=float(row[7]) if row[7] else 0.0,
                        first_met=str(row[8]) if row[8] else None,
                        last_met=str(row[9]) if row[9] else None,
                    )
                    self._matchup_cache[cache_key] = history
                    return history
        except Exception as e:
            logger.error(f'Failed to load matchup history: {e}')

        return None

    def load_platoon_split(
        self, player_id: int, player_type: str, season: int | None = None
    ) -> PlatoonSplit | None:
        """Load platoon split for a player.

        Args:
            player_id: Player ID
            player_type: 'batter' or 'pitcher'
            season: Optional season to filter

        Returns:
            PlatoonSplit or None if not found
        """
        cache_key = (player_id, player_type)

        if cache_key in self._platoon_cache:
            return self._platoon_cache[cache_key]

        if self.db is None:
            return None

        try:
            with self.db.cursor() as cur:
                if season:
                    cur.execute(
                        """SELECT player_id, player_type, season, throws, bats,
                                  vs_l_ops, vs_r_ops, vs_l_pa, vs_r_pa
                           FROM features.platoon_splits
                           WHERE player_id = %s AND player_type = %s AND season = %s""",
                        (player_id, player_type, season),
                    )
                else:
                    cur.execute(
                        """SELECT player_id, player_type, season, throws, bats,
                                  vs_l_ops, vs_r_ops, vs_l_pa, vs_r_pa
                           FROM features.platoon_splits
                           WHERE player_id = %s AND player_type = %s
                           ORDER BY season DESC
                           LIMIT 1""",
                        (player_id, player_type),
                    )

                row = cur.fetchone()
                if row:
                    split = PlatoonSplit(
                        player_id=row[0],
                        player_type=row[1],
                        season=row[2],
                        throws=row[3],
                        bats=row[4],
                        vs_l_ops=float(row[5]) if row[5] else 0.0,
                        vs_r_ops=float(row[6]) if row[6] else 0.0,
                        vs_l_pa=row[7] or 0,
                        vs_r_pa=row[8] or 0,
                    )
                    self._platoon_cache[cache_key] = split
                    return split
        except Exception as e:
            logger.error(f'Failed to load platoon split: {e}')

        return None

    def is_platoon_advantage(
        self, batter_id: int, pitcher_id: int, season: int | None = None
    ) -> bool | None:
        """Check if platoon situation favors the batter.

        LHB vs RHP = advantage
        RHB vs LHP = advantage
        Switch hitters = advantage (they always take favorable side)

        Args:
            batter_id: Batter ID
            pitcher_id: Pitcher ID
            season: Optional season

        Returns:
            True if batter has advantage, False otherwise, None if unknown
        """
        batter_split = self.load_platoon_split(batter_id, 'batter', season)
        pitcher_split = self.load_platoon_split(pitcher_id, 'pitcher', season)

        if not batter_split or not pitcher_split:
            return None

        # Switch hitters always have advantage
        if batter_split.bats == 'S':
            return True

        # LHB vs RHP = advantage
        if batter_split.bats == 'L' and pitcher_split.throws == 'R':
            return True

        # RHB vs LHP = advantage
        if batter_split.bats == 'R' and pitcher_split.throws == 'L':
            return True

        # Same side = disadvantage for batter
        return False

    def compute_matchup_score(self, batter_id: int, pitcher_id: int, season: int) -> float:
        """Compute combined matchup score (0-1, higher = better for batter).

        Factors:
        - Career matchup history (if sufficient PA)
        - Platoon advantage
        - Batter recent form vs pitcher's hand
        - Pitcher recent form vs batter's hand

        Args:
            batter_id: Batter ID
            pitcher_id: Pitcher ID
            season: Season year

        Returns:
            Matchup score 0.0-1.0
        """
        scores = []
        weights = []

        # 1. Career matchup history (weight: 0.3 if >= 10 PA, 0.1 if 5-9 PA)
        history = self.load_matchup_history(batter_id, pitcher_id, season)
        if history and history.career_pa >= 10:
            # Normalize OPS to 0-1 scale (0.500 = 0.0, 1.000 = 1.0)
            ops_score = max(0.0, min(1.0, (history.career_ops - 0.500) * 2))
            scores.append(ops_score)
            weights.append(0.30)
        elif history and history.career_pa >= 5:
            ops_score = max(0.0, min(1.0, (history.career_ops - 0.500) * 2))
            scores.append(ops_score)
            weights.append(0.10)

        # 2. Platoon advantage (weight: 0.25)
        platoon_adv = self.is_platoon_advantage(batter_id, pitcher_id, season)
        if platoon_adv is True:
            scores.append(0.65)  # Slight advantage to batter
            weights.append(0.25)
        elif platoon_adv is False:
            scores.append(0.35)  # Disadvantage to batter
            weights.append(0.25)

        # 3. Batter vs pitcher's hand (weight: 0.25)
        batter_split = self.load_platoon_split(batter_id, 'batter', season)
        pitcher_split = self.load_platoon_split(pitcher_id, 'pitcher', season)

        if batter_split and pitcher_split and pitcher_split.throws:
            vs_hand_ops = batter_split.get_vs_hand_ops(pitcher_split.throws)
            if vs_hand_ops > 0:
                hand_score = max(0.0, min(1.0, (vs_hand_ops - 0.500) * 2))
                scores.append(hand_score)
                weights.append(0.25)

        # 4. Pitcher vs batter's hand (weight: 0.20)
        if pitcher_split and batter_split and batter_split.bats:
            pitcher_vs_hand = (
                pitcher_split.vs_r_ops if batter_split.bats == 'R' else pitcher_split.vs_l_ops
            )
            if pitcher_vs_hand > 0:
                # Invert because lower OPS is better for pitcher
                pitcher_score = 1.0 - max(0.0, min(1.0, (pitcher_vs_hand - 0.500) * 2))
                scores.append(pitcher_score)
                weights.append(0.20)

        # Calculate weighted average
        if not scores:
            return 0.50  # Unknown matchup

        total_weight = sum(weights)
        weighted_sum = sum(s * w for s, w in zip(scores, weights))

        return weighted_sum / total_weight if total_weight > 0 else 0.50

    def compute(self, game_state: Any) -> float | None:
        """Compute matchup feature (required by base class).

        This is a simplified interface - use compute_matchup_score
        for full matchup calculation.

        Args:
            game_state: Game state with batter_id and pitcher_id

        Returns:
            Matchup score or None
        """
        # Extract from game_state if possible
        batter_id = getattr(game_state, 'batter_id', None)
        pitcher_id = getattr(game_state, 'pitcher_id', None)
        season = getattr(game_state, 'season', None)

        if batter_id and pitcher_id:
            return self.compute_matchup_score(batter_id, pitcher_id, season or 2026)

        return None

    def save_matchup_features(
        self, game_pk: int, at_bat_index: int, batter_id: int, pitcher_id: int, season: int
    ) -> bool:
        """Save computed matchup features to database.

        Args:
            game_pk: Game ID
            at_bat_index: At-bat index
            batter_id: Batter ID
            pitcher_id: Pitcher ID
            season: Season year

        Returns:
            True if saved successfully
        """
        if self.db is None:
            return False

        try:
            # Compute all features
            history = self.load_matchup_history(batter_id, pitcher_id, season)
            platoon_adv = self.is_platoon_advantage(batter_id, pitcher_id, season)
            matchup_score = self.compute_matchup_score(batter_id, pitcher_id, season)

            batter_split = self.load_platoon_split(batter_id, 'batter', season)
            pitcher_split = self.load_platoon_split(pitcher_id, 'pitcher', season)

            with self.db.cursor() as cur:
                cur.execute(
                    """INSERT INTO features.matchup_features 
                        (game_pk, at_bat_index, season,
                         batter_id, pitcher_id,
                         career_matchup_pa, career_matchup_avg, career_matchup_ops,
                         has_matchup_history,
                         batter_handedness, pitcher_throws,
                         is_platoon_advantage,
                         matchup_score)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (game_pk, at_bat_index) DO UPDATE SET
                         career_matchup_pa = EXCLUDED.career_matchup_pa,
                         career_matchup_avg = EXCLUDED.career_matchup_avg,
                         career_matchup_ops = EXCLUDED.career_matchup_ops,
                         has_matchup_history = EXCLUDED.has_matchup_history,
                         batter_handedness = EXCLUDED.batter_handedness,
                         pitcher_throws = EXCLUDED.pitcher_throws,
                         is_platoon_advantage = EXCLUDED.is_platoon_advantage,
                         matchup_score = EXCLUDED.matchup_score,
                         computed_at = NOW()""",
                    (
                        game_pk,
                        at_bat_index,
                        season,
                        batter_id,
                        pitcher_id,
                        history.career_pa if history else 0,
                        history.career_avg if history else 0.0,
                        history.career_ops if history else 0.0,
                        history.has_history if history else False,
                        batter_split.bats if batter_split else None,
                        pitcher_split.throws if pitcher_split else None,
                        platoon_adv,
                        matchup_score,
                    ),
                )
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f'Failed to save matchup features: {e}')
            return False

    def _build_historical(self, config: FeatureConfig, result: FeatureResult) -> None:
        """Build historical matchup features.

        Args:
            config: Feature configuration
            result: Result object to update
        """
        logger.info('Building historical matchup features')

        if self.db is None:
            result.add_error('No database connection')
            return

        try:
            # This would populate matchup history tables from raw data
            # Implementation depends on raw data schema
            result.rows_computed = 0
            result.rows_inserted = 0
        except Exception as e:
            result.add_error(f'Historical build failed: {e}')

    def _build_live(self, config: FeatureConfig, result: FeatureResult) -> None:
        """Build live matchup features.

        Args:
            config: Feature configuration
            result: Result object to update
        """
        logger.info('Building live matchup features')
        result.metadata['live_mode'] = 'on_demand'

    def get_matchup_stats(self, batter_id: int, pitcher_id: int) -> dict[str, Any]:
        """Get comprehensive matchup statistics.

        Args:
            batter_id: Batter ID
            pitcher_id: Pitcher ID

        Returns:
            Dictionary with matchup statistics
        """
        history = self.load_matchup_history(batter_id, pitcher_id)

        return {
            'has_history': history.has_history if history else False,
            'familiarity': history.familiarity if history else 'unknown',
            'career_pa': history.career_pa if history else 0,
            'career_avg': history.career_avg if history else 0.0,
            'career_ops': history.career_ops if history else 0.0,
            'career_hr': history.career_hr if history else 0,
            'last_met': history.last_met if history else None,
        }
