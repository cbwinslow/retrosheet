"""Leverage Index calculator.

Computes situational importance based on potential swing in win probability.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import logging
from enum import Enum
from typing import Any

from .base import FeatureConfig, FeatureResult, FeatureStore, GameState


logger = logging.getLogger(__name__)


class LeverageRating(Enum):
    """Categorical leverage ratings."""

    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    VERY_HIGH = 'very_high'


class LeverageIndexCalculator(FeatureStore):
    """Calculator for Leverage Index (LI) features.

    LI measures the importance of a game situation based on how much
    the win probability could change. Average LI = 1.0.

    Example:
        >>> calc = LeverageIndexCalculator(db_connection=conn)
        >>> calc.load_from_db()
        >>> state = GameState(
        ...     inning=9,
        ...     is_top=False,
        ...     outs=2,
        ...     runner_1b=True,
        ...     runner_3b=True,  # RISP
        ...     score_home=3,
        ...     score_away=3,
        ... )
        >>> li = calc.compute(state)
        >>> rating = calc.get_rating(li)
        >>> print(f'Leverage: {li:.2f} ({rating.value})')
    """

    # Thresholds for leverage ratings
    LOW_THRESHOLD = 0.7
    MEDIUM_THRESHOLD = 1.3
    HIGH_THRESHOLD = 2.0

    def __init__(self, db_connection=None, config: FeatureConfig | None = None):
        """Initialize LI calculator.

        Args:
            db_connection: Database connection for LI matrix
            config: Feature configuration
        """
        super().__init__(db_connection, config)
        self._li_matrix: dict[tuple, float] = {}

    @property
    def feature_name(self) -> str:
        return 'leverage_index'

    @property
    def table_name(self) -> str:
        return 'features.game_state_li'

    def load_from_db(self, season: int | None = None) -> int:
        """Load LI matrix from database.

        Args:
            season: Optional season to load specific matrix

        Returns:
            Number of states loaded
        """
        if self.db is None:
            logger.warning('No database connection, using default LI values')
            self._load_default_matrix()
            return len(self._li_matrix)

        count = 0
        try:
            with self.db.cursor() as cur:
                if season:
                    cur.execute(
                        """SELECT inning, is_top, outs, base_state, score_diff, leverage_index
                           FROM features.leverage_index_matrix
                           WHERE season_from <= %s AND (season_to >= %s OR season_to IS NULL)""",
                        (season, season),
                    )
                else:
                    cur.execute(
                        """SELECT inning, is_top, outs, base_state, score_diff, leverage_index
                           FROM features.leverage_index_matrix""",
                    )

                for row in cur.fetchall():
                    key = (row[0], row[1], row[2], row[3], row[4])
                    self._li_matrix[key] = float(row[5])
                    count += 1

            logger.info(f'Loaded {count} LI matrix entries')
        except Exception as e:
            logger.error(f'Failed to load LI matrix: {e}')
            self._load_default_matrix()

        return count

    def _load_default_matrix(self) -> None:
        """Load default LI matrix for common states."""
        # High-leverage situations
        high_leverage = [
            (9, True, 2, '111', 0, 3.5),  # Bases loaded, top 9, 2 outs, tie
            (9, False, 2, '111', 0, 3.8),  # Bases loaded, bot 9, 2 outs, tie
            (9, True, 1, '011', -1, 2.8),  # RISP, down 1, top 9
            (9, False, 2, '011', 1, 3.2),  # RISP, up 1, bot 9
        ]

        # Medium-leverage situations
        medium_leverage = [
            (7, True, 2, '111', 0, 1.8),  # Bases loaded, 7th
            (8, False, 1, '011', 0, 1.6),  # RISP, tie, 8th
            (9, True, 0, '000', 0, 1.5),  # Top 9, tie, bases empty
        ]

        # Low-leverage situations
        low_leverage = [
            (1, True, 0, '000', 0, 0.8),  # Early, bases empty
            (3, False, 1, '000', 5, 0.4),  # Up by 5 in 3rd
            (7, True, 2, '000', -6, 0.3),  # Down by 6 in 7th
        ]

        all_states = high_leverage + medium_leverage + low_leverage

        for state in all_states:
            key = state[:5]
            self._li_matrix[key] = state[5]

        logger.info(f'Loaded {len(all_states)} default LI states')

    def compute(self, game_state: GameState) -> float | None:
        """Compute leverage index for a game state.

        Args:
            game_state: Current game state

        Returns:
            Leverage index (1.0 = average) or None if unknown
        """
        # Cap inning at 9 for extra innings
        lookup_inning = min(game_state.inning, 9)

        # Cap score differential at ±10
        score_diff = max(-10, min(10, game_state.score_diff))

        key = (
            lookup_inning,
            game_state.is_top,
            game_state.outs,
            game_state.base_state,
            score_diff,
        )

        # Look up in matrix
        li = self._li_matrix.get(key)

        if li is None:
            # Estimate based on game situation
            li = self._estimate_li(game_state)

        return li

    def _estimate_li(self, state: GameState) -> float:
        """Estimate leverage index when exact state not in matrix.

        Uses heuristics based on inning, score, and base runners.

        Args:
            state: Game state

        Returns:
            Estimated leverage index
        """
        li = 1.0  # Start at average

        # Late game multiplier
        if state.inning >= 9:
            if abs(state.score_diff) <= 1:
                li *= 2.5  # Close late game
            elif abs(state.score_diff) <= 3:
                li *= 1.8
            else:
                li *= 0.7  # Blowout
        elif state.inning >= 7:
            if abs(state.score_diff) <= 1:
                li *= 1.8
            elif abs(state.score_diff) <= 3:
                li *= 1.3

        # Base runners multiplier
        if state.runners_on == 3:
            li *= 1.4  # Bases loaded
        elif state.runners_on == 2:
            li *= 1.25  # Two runners
        elif state.runners_on == 1:
            li *= 1.1  # One runner

        # Outs multiplier
        if state.outs == 2 and state.runners_on > 0:
            li *= 1.2  # High pressure with 2 outs

        return round(li, 2)

    def get_rating(self, li: float) -> LeverageRating:
        """Get categorical rating for leverage index.

        Args:
            li: Leverage index value

        Returns:
            Categorical rating
        """
        if li >= self.HIGH_THRESHOLD:
            return LeverageRating.VERY_HIGH
        if li >= self.MEDIUM_THRESHOLD:
            return LeverageRating.HIGH
        if li >= self.LOW_THRESHOLD:
            return LeverageRating.MEDIUM
        return LeverageRating.LOW

    def is_high_leverage(self, li: float) -> bool:
        """Check if leverage index indicates high leverage.

        Args:
            li: Leverage index value

        Returns:
            True if high leverage (LI >= 1.5)
        """
        return li >= 1.5

    def get_swing_potential(self, game_state: GameState) -> float:
        """Estimate maximum possible win probability swing.

        This is related to leverage - higher potential swing = higher leverage.

        Args:
            game_state: Current game state

        Returns:
            Estimated max win probability change (0-1)
        """
        li = self.compute(game_state) or 1.0

        # Approximate swing potential from LI
        # Average swing is ~4.6%, so swing = LI * 0.046
        return li * 0.046

    def compute_game_li_series(self, plays: list[dict[str, Any]]) -> list[dict]:
        """Compute LI for each play in a game.

        Args:
            plays: List of play dictionaries with game state info

        Returns:
            List of plays with added LI and rating fields
        """
        results = []

        for play in plays:
            # Extract game state
            state = GameState(
                inning=play.get('inning', 1),
                is_top=play.get('is_top', True),
                outs=play.get('outs', 0),
                runner_1b=play.get('runner_1b', False),
                runner_2b=play.get('runner_2b', False),
                runner_3b=play.get('runner_3b', False),
                score_home=play.get('score_home', 0),
                score_away=play.get('score_away', 0),
            )

            # Compute LI
            li = self.compute(state)
            rating = self.get_rating(li) if li else LeverageRating.MEDIUM

            # Add to results
            result = {
                **play,
                'leverage_index': li,
                'leverage_rating': rating.value,
                'is_high_leverage': self.is_high_leverage(li) if li else False,
            }
            results.append(result)

        return results

    def _build_historical(self, config: FeatureConfig, result: FeatureResult) -> None:
        """Build historical LI features.

        Args:
            config: Feature configuration
            result: Result object to update
        """
        logger.info('Building historical leverage index features')

        if self.db is None:
            result.add_error('No database connection for historical build')
            return

        try:
            season = config.season

            with self.db.cursor() as cur:
                # Get game states
                cur.execute(
                    """SELECT game_pk, at_bat_index, inning, is_top, outs,
                              runner_1b, runner_2b, runner_3b,
                              score_home, score_away
                       FROM raw_gumbo.game_states
                       WHERE season = %s
                       ORDER BY game_pk, at_bat_index""",
                    (season,),
                )

                rows = cur.fetchall()
                result.rows_computed = len(rows)

                # Compute LI for each state
                inserted = 0
                for row in rows:
                    state = GameState(
                        inning=row[2],
                        is_top=row[3],
                        outs=row[4],
                        runner_1b=row[5],
                        runner_2b=row[6],
                        runner_3b=row[7],
                        score_home=row[8],
                        score_away=row[9],
                    )

                    li = self.compute(state)

                    if li is not None:
                        success = self.save(
                            row[0],
                            row[1],
                            li,
                            {'rating': self.get_rating(li).value},
                        )
                        if success:
                            inserted += 1

                result.rows_inserted = inserted

        except Exception as e:
            result.add_error(f'Historical build failed: {e}')
            logger.exception('Historical LI build failed')

    def _build_live(self, config: FeatureConfig, result: FeatureResult) -> None:
        """Build live LI features.

        Args:
            config: Feature configuration
            result: Result object to update
        """
        logger.info('Building live leverage index features')
        result.metadata['live_mode'] = 'on_demand'

    def get_clutch_opportunities(self, game_pk: int, batter_id: int) -> list[dict]:
        """Get high-leverage opportunities for a batter in a game.

        Args:
            game_pk: Game ID
            batter_id: Batter ID

        Returns:
            List of high-leverage at-bats
        """
        if self.db is None:
            return []

        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """SELECT at_bat_index, leverage_index, inning, outs, base_state
                       FROM features.game_state_li
                       WHERE game_pk = %s AND batter_id = %s
                         AND is_high_leverage = TRUE
                       ORDER BY leverage_index DESC""",
                    (game_pk, batter_id),
                )

                return [
                    {
                        'at_bat_index': row[0],
                        'leverage_index': row[1],
                        'inning': row[2],
                        'outs': row[3],
                        'base_state': row[4],
                    }
                    for row in cur.fetchall()
                ]
        except Exception as e:
            logger.error(f'Failed to get clutch opportunities: {e}')
            return []

    def get_matrix_stats(self) -> dict[str, Any]:
        """Get statistics about the loaded LI matrix.

        Returns:
            Dictionary with matrix statistics
        """
        if not self._li_matrix:
            return {'loaded': False, 'entries': 0}

        li_values = list(self._li_matrix.values())

        high_leverage = sum(1 for li in li_values if li >= 1.5)

        return {
            'loaded': True,
            'entries': len(li_values),
            'min_li': min(li_values),
            'max_li': max(li_values),
            'avg_li': sum(li_values) / len(li_values),
            'high_leverage_count': high_leverage,
            'high_leverage_pct': high_leverage / len(li_values) * 100,
        }
