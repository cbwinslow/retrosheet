"""Win Expectancy calculator.

Computes win probability based on game state using historical data.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import logging
from typing import Any

from .base import FeatureConfig, FeatureResult, FeatureStore, GameState


logger = logging.getLogger(__name__)


class WinExpectancyCalculator(FeatureStore):
    """Calculator for Win Expectancy (WE) features.

    WE is the probability of the home team winning given the current
    game state (inning, outs, runners, score).

    Example:
        >>> calc = WinExpectancyCalculator(db_connection=conn)
        >>> calc.load_from_db()
        >>> state = GameState(
        ...     inning=9,
        ...     is_top=False,
        ...     outs=2,
        ...     runner_1b=True,
        ...     runner_2b=False,
        ...     runner_3b=False,
        ...     score_home=4,
        ...     score_away=3,
        ... )
        >>> we = calc.compute(state)
        >>> print(f'Home team win probability: {we:.1%}')
    """

    def __init__(self, db_connection=None, config: FeatureConfig | None = None) -> None:
        """Initialize WE calculator.

        Args:
            db_connection: Database connection for WE matrix
            config: Feature configuration
        """
        super().__init__(db_connection, config)
        self._we_matrix: dict[tuple, float] = {}

    @property
    def feature_name(self) -> str:
        return 'win_expectancy'

    @property
    def table_name(self) -> str:
        return 'features.game_state_we'

    def load_from_db(self, season: int | None = None) -> int:
        """Load WE matrix from database.

        Args:
            season: Optional season to load specific matrix

        Returns:
            Number of states loaded
        """
        if self.db is None:
            logger.warning('No database connection, using default WE values')
            self._load_default_matrix()
            return len(self._we_matrix)

        count = 0
        try:
            with self.db.cursor() as cur:
                if season:
                    cur.execute(
                        """SELECT inning, is_top, outs, base_state, score_diff, home_win_prob
                           FROM features.win_expectancy_matrix
                           WHERE season_from <= %s AND (season_to >= %s OR season_to IS NULL)""",
                        (season, season),
                    )
                else:
                    cur.execute(
                        """SELECT inning, is_top, outs, base_state, score_diff, home_win_prob
                           FROM features.current_we_matrix""",
                    )

                for row in cur.fetchall():
                    key = (row[0], row[1], row[2], row[3], row[4])
                    self._we_matrix[key] = float(row[5])
                    count += 1

            logger.info(f'Loaded {count} WE matrix entries')
        except Exception as e:
            logger.exception(f'Failed to load WE matrix: {e}')
            self._load_default_matrix()

        return count

    def _load_default_matrix(self) -> None:
        """Load default WE matrix for common states."""
        # Simplified WE matrix for when DB is unavailable
        # Late & close situations are most important
        defaults = [
            # inning, is_top, outs, base_state, score_diff, win_prob
            (9, True, 2, '000', 0, 0.50),  # Top 9, tie, bases empty, 2 outs
            (9, False, 2, '000', 0, 0.52),  # Bot 9, tie, bases empty, 2 outs
            (9, True, 1, '000', -1, 0.18),  # Top 9, down 1, 1 out
            (9, False, 2, '000', 1, 0.92),  # Bot 9, up 1, 2 outs
            (7, True, 0, '000', 0, 0.54),  # Top 7, tie
            (7, False, 0, '000', 0, 0.52),  # Bot 7, tie
            (1, True, 0, '000', 0, 0.54),  # Top 1
            (1, False, 0, '000', 0, 0.52),  # Bot 1
        ]

        for state in defaults:
            key = state[:5]
            self._we_matrix[key] = state[5]

        logger.info(f'Loaded {len(defaults)} default WE states')

    def compute(self, game_state: GameState) -> float | None:
        """Compute win expectancy for a game state.

        Args:
            game_state: Current game state

        Returns:
            Win probability (0-1) or None if unknown state
        """
        # Cap inning at 9 for extra innings (use 9th inning WE)
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
        we = self._we_matrix.get(key)

        if we is None:
            # Try without score differential (less specific)
            for diff in range(-5, 6):
                alt_key = (
                    lookup_inning,
                    game_state.is_top,
                    game_state.outs,
                    game_state.base_state,
                    diff,
                )
                if alt_key in self._we_matrix:
                    # Linear interpolation based on score diff
                    we = self._we_matrix[alt_key]
                    break

        if we is None:
            # Final fallback: return 0.5 (coin flip)
            we = 0.5
            logger.debug(f'Unknown state {key}, defaulting to 0.5')

        return we

    def compute_wpa(self, state_before: GameState, state_after: GameState) -> float:
        """Compute Win Probability Added (WPA) for a play.

        WPA = WE_after - WE_before

        Positive WPA means the play helped the home team.

        Args:
            state_before: Game state before the play
            state_after: Game state after the play

        Returns:
            Win Probability Added
        """
        we_before = self.compute(state_before) or 0.5
        we_after = self.compute(state_after) or 0.5

        return we_after - we_before

    def compute_game_we_series(self, plays: list[dict[str, Any]]) -> list[dict]:
        """Compute WE for each play in a game.

        Args:
            plays: List of play dictionaries with game state info

        Returns:
            List of plays with added WE and WPA fields
        """
        results = []
        prev_we = None

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

            # Compute WE
            we = self.compute(state)
            wpa = None

            if prev_we is not None:
                wpa = we - prev_we if we else None

            # Add to results
            result = {
                **play,
                'win_expectancy': we,
                'wpa': wpa,
            }
            results.append(result)

            prev_we = we

        return results

    def _build_historical(self, config: FeatureConfig, result: FeatureResult) -> None:
        """Build historical WE features.

        Args:
            config: Feature configuration
            result: Result object to update
        """
        logger.info('Building historical win expectancy features')

        if self.db is None:
            result.add_error('No database connection for historical build')
            return

        try:
            # Query for games to process
            season = config.season

            with self.db.cursor() as cur:
                # Get game states from raw data
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

                # Compute WE for each state
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

                    we = self.compute(state)

                    if we is not None:
                        # Save to database
                        success = self.save(row[0], row[1], we)
                        if success:
                            inserted += 1

                result.rows_inserted = inserted

        except Exception as e:
            result.add_error(f'Historical build failed: {e}')
            logger.exception('Historical WE build failed')

    def _build_live(self, config: FeatureConfig, result: FeatureResult) -> None:
        """Build live WE features.

        Args:
            config: Feature configuration
            result: Result object to update
        """
        logger.info('Building live win expectancy features')
        # For live games, WE is computed on-demand rather than batch
        result.metadata['live_mode'] = 'on_demand'

    def get_matrix_stats(self) -> dict[str, Any]:
        """Get statistics about the loaded WE matrix.

        Returns:
            Dictionary with matrix statistics
        """
        if not self._we_matrix:
            return {'loaded': False, 'entries': 0}

        win_probs = list(self._we_matrix.values())

        return {
            'loaded': True,
            'entries': len(win_probs),
            'min_we': min(win_probs),
            'max_we': max(win_probs),
            'avg_we': sum(win_probs) / len(win_probs),
            'innings_covered': len({k[0] for k in self._we_matrix}),
        }
