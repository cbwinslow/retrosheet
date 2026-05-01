"""Run Expectancy calculator.

Computes expected runs for remainder of inning based on base-out state.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-28
"""

import logging
from typing import Any

from .base import FeatureConfig, FeatureResult, FeatureStore, GameState


logger = logging.getLogger(__name__)


class RunExpectancyCalculator(FeatureStore):
    """Calculator for Run Expectancy (RE) features.

    Run Expectancy is the expected number of runs scored in the
    remainder of the inning given the current base-out state.

    The 24 base-out states:
    - 8 base states (bases empty, 1st, 2nd, 3rd, 1st+2nd, 1st+3rd, 2nd+3rd, loaded)
    - 3 out states (0, 1, 2 outs)
    - Total: 24 states

    Example:
        >>> calc = RunExpectancyCalculator(db_connection=conn)
        >>> calc.load_from_db()
        >>> re = calc.get_re(base_state=1, outs=0)  # Runner on 1st, 0 outs
        >>> print(f'Expected runs: {re:.2f}')
    """

    def __init__(self, db_connection=None, config: FeatureConfig | None = None) -> None:
        """Initialize RE calculator.

        Args:
            db_connection: Database connection for RE matrix
            config: Feature configuration
        """
        super().__init__(db_connection, config)
        self._re_matrix: dict[tuple[int, int], float] = {}

    @property
    def feature_name(self) -> str:
        return 'run_expectancy'

    @property
    def table_name(self) -> str:
        return 'features.run_expectancy_matrix'

    def load_from_db(self, season: int | None = None) -> int:
        """Load RE matrix from database.

        Args:
            season: Optional season to load specific matrix

        Returns:
            Number of states loaded
        """
        if self.db is None:
            logger.warning('No database connection, using default RE values')
            self._load_default_matrix()
            return len(self._re_matrix)

        count = 0
        try:
            with self.db.cursor() as cur:
                if season:
                    cur.execute(
                        """SELECT base_state, outs, expected_runs
                           FROM features.run_expectancy_matrix
                           WHERE season = %s""",
                        (season,),
                    )
                else:
                    cur.execute(
                        """SELECT base_state, outs, expected_runs
                           FROM features.run_expectancy_matrix
                           WHERE season IS NULL""",
                    )

                for row in cur.fetchall():
                    key = (int(row[0]), int(row[1]))
                    self._re_matrix[key] = float(row[2])
                    count += 1

            logger.info(f'Loaded {count} RE matrix entries')
        except Exception as e:
            logger.exception(f'Failed to load RE matrix: {e}')
            self._load_default_matrix()

        return count

    def _load_default_matrix(self) -> None:
        """Load default MLB-average RE values."""
        # These are approximate MLB averages
        defaults = {
            # (base_state, outs): expected_runs
            # base_state: 0=empty, 1=1st, 2=2nd, 3=3rd,
            #             4=1st+2nd, 5=1st+3rd, 6=2nd+3rd, 7=loaded
            (0, 0): 0.461,  # Bases empty, 0 outs
            (0, 1): 0.243,  # Bases empty, 1 out
            (0, 2): 0.095,  # Bases empty, 2 outs
            (1, 0): 0.831,  # 1st, 0 outs
            (1, 1): 0.489,  # 1st, 1 out
            (1, 2): 0.214,  # 1st, 2 outs
            (2, 0): 1.068,  # 2nd, 0 outs
            (2, 1): 0.644,  # 2nd, 1 out
            (2, 2): 0.305,  # 2nd, 2 outs
            (3, 0): 1.426,  # 3rd, 0 outs
            (3, 1): 0.864,  # 3rd, 1 out
            (3, 2): 0.413,  # 3rd, 2 outs
            (4, 0): 1.313,  # 1st+2nd, 0 outs
            (4, 1): 0.814,  # 1st+2nd, 1 out
            (4, 2): 0.400,  # 1st+2nd, 2 outs
            (5, 0): 1.741,  # 1st+3rd, 0 outs
            (5, 1): 1.118,  # 1st+3rd, 1 out
            (5, 2): 0.510,  # 1st+3rd, 2 outs
            (6, 0): 1.844,  # 2nd+3rd, 0 outs
            (6, 1): 1.152,  # 2nd+3rd, 1 out
            (6, 2): 0.494,  # 2nd+3rd, 2 outs
            (7, 0): 2.292,  # Loaded, 0 outs
            (7, 1): 1.542,  # Loaded, 1 out
            (7, 2): 0.747,  # Loaded, 2 outs
        }
        self._re_matrix = defaults
        logger.info(f'Loaded {len(defaults)} default RE values')

    def get_re(self, base_state: int, outs: int) -> float:
        """Get run expectancy for a base-out state.

        Args:
            base_state: 0-7 (0=empty, 1=1st, 2=2nd, 3=3rd,
                       4=1st+2nd, 5=1st+3rd, 6=2nd+3rd, 7=loaded)
            outs: 0, 1, or 2

        Returns:
            Expected runs for remainder of inning
        """
        key = (base_state, outs)
        if key not in self._re_matrix:
            logger.warning(f'Unknown RE state: base={base_state}, outs={outs}')
            return 0.5  # Conservative default
        return self._re_matrix[key]

    def get_re24_change(
        self,
        base_state_start: int,
        outs_start: int,
        base_state_end: int,
        outs_end: int,
        runs_scored: int,
    ) -> float:
        """Calculate RE24 change from a plate appearance.

        RE24 = (RE_start - RE_end - runs_scored_on_play)

        This measures the run value contributed by the batter/pitcher.

        Args:
            base_state_start: Base state at start of PA
            outs_start: Outs at start of PA
            base_state_end: Base state at end of PA
            outs_end: Outs at end of PA
            runs_scored: Runs scored on the play

        Returns:
            RE24 value (positive = good for offense)
        """
        re_start = self.get_re(base_state_start, outs_start)
        re_end = self.get_re(base_state_end, outs_end)

        # RE24 = runs_scored + RE_end - RE_start
        # But we negate because RE measures future runs
        re24 = runs_scored + re_end - re_start

        return round(re24, 3)

    def compute(self, game_state: GameState) -> float:
        """Compute run expectancy for current game state.

        Args:
            game_state: Current game state

        Returns:
            Expected runs this inning
        """
        base_state = self._compute_base_state(game_state)
        return self.get_re(base_state, game_state.outs)

    def _compute_base_state(self, game_state: GameState) -> int:
        """Compute base state integer from game state.

        Returns 0-7 representing base occupancy.
        """
        state = 0
        if game_state.runner_1b:
            state += 1
        if game_state.runner_2b:
            state += 2
        if game_state.runner_3b:
            state += 4
        return state

    def build(self, config: FeatureConfig | None = None) -> FeatureResult:
        """Build RE matrix from historical data.

        Computes expected runs from each base-out state by analyzing
        historical play-by-play data.

        Args:
            config: Feature configuration

        Returns:
            FeatureResult with computation status
        """
        config = config or self.config or FeatureConfig()
        result = FeatureResult()

        if self.db is None:
            result.add_error('No database connection available')
            return result

        try:
            with self.db.cursor() as cur:
                # Compute RE from historical data
                # For each base-out state, average runs scored in remainder of inning
                cur.execute(
                    """
                    WITH inning_states AS (
                        SELECT
                            game_id,
                            inning,
                            CASE
                                WHEN runner_1b AND runner_2b AND runner_3b THEN 7
                                WHEN runner_2b AND runner_3b THEN 6
                                WHEN runner_1b AND runner_3b THEN 5
                                WHEN runner_1b AND runner_2b THEN 4
                                WHEN runner_3b THEN 3
                                WHEN runner_2b THEN 2
                                WHEN runner_1b THEN 1
                                ELSE 0
                            END as base_state,
                            outs,
                            runs_scored_on_event as runs_scored
                        FROM core.events
                        WHERE season = %s
                    ),
                    future_runs AS (
                        SELECT
                            inning_states.game_id,
                            inning_states.inning,
                            inning_states.base_state,
                            inning_states.outs,
                            inning_states.runs_scored,
                            COALESCE(SUM(e.runs_scored_on_event), 0) as future_runs
                        FROM inning_states
                        LEFT JOIN core.events e ON
                            inning_states.game_id = e.game_id
                            AND inning_states.inning = e.inning
                            AND e.event_id > inning_states.__row_number__
                        GROUP BY inning_states.game_id, inning_states.inning,
                                 inning_states.base_state, inning_states.outs,
                                 inning_states.runs_scored
                    )
                    SELECT
                        base_state,
                        outs,
                        AVG(runs_scored + future_runs) as expected_runs,
                        COUNT(*) as sample_size
                    FROM future_runs
                    GROUP BY base_state, outs
                    ORDER BY base_state, outs
                    """,
                    (config.season,),
                )

                rows_inserted = 0
                for row in cur.fetchall():
                    cur.execute(
                        """INSERT INTO features.run_expectancy_matrix
                           (base_state, outs, expected_runs, occurrences, season)
                           VALUES (%s, %s, %s, %s, %s)
                           ON CONFLICT (base_state, outs, season)
                           DO UPDATE SET
                               expected_runs = EXCLUDED.expected_runs,
                               occurrences = EXCLUDED.occurrences,
                               computed_at = CURRENT_TIMESTAMP""",
                        (row[0], row[1], row[2], row[3], config.season),
                    )
                    rows_inserted += 1

                self.db.commit()
                result.rows_computed = rows_inserted
                result.rows_inserted = rows_inserted
                result.mark_complete()

                logger.info(f'Built RE matrix with {rows_inserted} states for season {config.season}')

        except Exception as e:
            result.add_error(f'Failed to build RE matrix: {e}')
            logger.exception(f'RE matrix build failed: {e}')

        return result

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the loaded RE matrix."""
        if not self._re_matrix:
            return {'status': 'not_loaded', 'entries': 0}

        values = list(self._re_matrix.values())
        return {
            'status': 'loaded',
            'entries': len(self._re_matrix),
            'min_re': min(values),
            'max_re': max(values),
            'avg_re': sum(values) / len(values),
        }
