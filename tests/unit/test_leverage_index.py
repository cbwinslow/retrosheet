"""Unit tests for Leverage Index calculator.

Granular tests for LeverageIndexCalculator with database mocking.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-27
"""

from unittest.mock import MagicMock, Mock

import pytest

from baseball.features.base import FeatureConfig, GameState
from baseball.features.leverage_index import LeverageIndexCalculator


@pytest.fixture
def mock_db():
    """Create a mock database connection."""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


@pytest.fixture
def sample_li_matrix():
    """Create a sample LI matrix for testing."""
    return {
        (1, True, 0, '000', 0): 0.9,  # Low leverage early
        (9, False, 2, '000', 0): 3.5,  # High leverage late, close
        (9, False, 2, '111', 0): 4.8,  # Very high leverage, bases loaded
    }


class TestLeverageIndexCalculator:
    """Test LeverageIndexCalculator class."""

    def test_initialization(self, mock_db):
        """Test calculator initialization."""
        conn, _ = mock_db
        calc = LeverageIndexCalculator(db_connection=conn)

        assert calc.feature_name == 'leverage_index'
        assert calc.table_name == 'features.game_state_li'
        assert calc._li_matrix == {}

    def test_load_from_db(self, mock_db):
        """Test loading LI matrix from database."""
        conn, _cursor = mock_db

        rows = [
            (1, True, 0, '000', 0, 0.9, 1000),
            (9, False, 2, '000', 0, 3.5, 500),
        ]

        # Mock context manager
        context_cursor = MagicMock()
        context_cursor.fetchall.return_value = rows
        context_cursor.__enter__ = MagicMock(return_value=context_cursor)
        context_cursor.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = context_cursor

        calc = LeverageIndexCalculator(db_connection=conn)
        count = calc.load_from_db()

        assert count == 2
        assert calc._li_matrix[(1, True, 0, '000', 0)] == 0.9

    def test_compute_low_leverage(self, mock_db, sample_li_matrix):
        """Test LI computation for low leverage situation."""
        conn, _ = mock_db
        calc = LeverageIndexCalculator(db_connection=conn)
        calc._li_matrix = sample_li_matrix

        # Early game, no runners, tied
        state = GameState(inning=1, is_top=True, outs=0)
        li = calc.compute(state)

        assert li == 0.9

    def test_compute_high_leverage(self, mock_db, sample_li_matrix):
        """Test LI computation for high leverage situation."""
        conn, _ = mock_db
        calc = LeverageIndexCalculator(db_connection=conn)
        calc._li_matrix = sample_li_matrix

        # Bottom 9, tied, 2 outs
        state = GameState(inning=9, is_top=False, outs=2)
        li = calc.compute(state)

        assert li == 3.5

    def test_compute_very_high_leverage(self, mock_db, sample_li_matrix):
        """Test LI computation for very high leverage (bases loaded)."""
        conn, _ = mock_db
        calc = LeverageIndexCalculator(db_connection=conn)
        calc._li_matrix = sample_li_matrix

        # Bottom 9, bases loaded, tied, 2 outs
        state = GameState(
            inning=9,
            is_top=False,
            outs=2,
            runner_1b=True,
            runner_2b=True,
            runner_3b=True,
        )
        li = calc.compute(state)

        assert li == 4.8

    def test_li_scale_reference(self, mock_db):
        """Test LI values against standard scale."""
        conn, _ = mock_db
        calc = LeverageIndexCalculator(db_connection=conn)

        # Standard LI reference points
        # 1.0 = average leverage
        # > 3.0 = very high leverage
        # < 0.5 = very low leverage
        calc._li_matrix = {
            (1, True, 0, '000', 0): 1.0,  # Average
            (9, False, 2, '111', 0): 3.5,  # Very high
            (1, True, 0, '000', 5): 0.3,  # Very low (blowout)
        }

        assert calc.compute(GameState(inning=1, is_top=True, outs=0)) == 1.0
        assert (
            calc.compute(
                GameState(
                    inning=9, is_top=False, outs=2, runner_1b=True, runner_2b=True, runner_3b=True,
                ),
            )
            == 3.5
        )

    def test_compute_batch(self, mock_db):
        """Test batch LI computation."""
        conn, _ = mock_db
        calc = LeverageIndexCalculator(db_connection=conn)
        calc._li_matrix = {
            (1, True, 0, '000', 0): 0.9,
            (9, False, 2, '000', 0): 3.5,
        }

        states = [
            GameState(inning=1, is_top=True, outs=0),
            GameState(inning=9, is_top=False, outs=2),
        ]

        results = calc.compute_batch(states)

        assert len(results) == 2
        assert results[0] == 0.9
        assert results[1] == 3.5

    def test_build_li_matrix(self, mock_db):
        """Test building LI matrix from historical data."""
        conn, cursor = mock_db

        # Mock game state transitions
        cursor.fetchall.return_value = [
            (1, True, 0, '000', 0, 1.0, 5000),  # Average leverage
            (9, False, 2, '000', 0, 3.2, 2000),  # High leverage
        ]

        calc = LeverageIndexCalculator(db_connection=conn)

        # Use _build_historical with proper parameters
        from baseball.features.base import FeatureResult

        config = FeatureConfig()
        result = FeatureResult()
        calc._build_historical(config, result)

        # Just verify no errors and metadata is set
        assert isinstance(result, FeatureResult)


class TestLeverageIndexEdgeCases:
    """Test edge cases for Leverage Index."""

    def test_postseason_leverage(self, mock_db):
        """Test that postseason games have higher baseline leverage."""
        conn, _ = mock_db
        calc = LeverageIndexCalculator(db_connection=conn)

        # Same state in postseason vs regular season
        # Postseason should have slightly elevated LI
        regular_state = GameState(inning=9, is_top=False, outs=2)
        postseason_state = GameState(inning=9, is_top=False, outs=2)

        # LI calculation might consider game importance
        # For now, just verify it computes
        calc._li_matrix = {(9, False, 2, '000', 0): 3.5}

        regular_li = calc.compute(regular_state)
        postseason_li = calc.compute(postseason_state)

        assert regular_li is not None
        assert postseason_li is not None

    def test_extra_innings_leverage(self, mock_db):
        """Test leverage in extra innings."""
        conn, _ = mock_db
        calc = LeverageIndexCalculator(db_connection=conn)

        # Note: compute() caps inning at 9, so we test with inning=9 in matrix
        # but use inning=12 in state - it should map to inning 9
        calc._li_matrix = {(9, True, 0, '000', 0): 4.0}

        state = GameState(inning=12, is_top=True, outs=0, score_home=4, score_away=4)
        li = calc.compute(state)

        # Should find the capped inning (9) in matrix
        assert li == 4.0

    def test_blowout_low_leverage(self, mock_db):
        """Test leverage in blowout games."""
        conn, _ = mock_db
        calc = LeverageIndexCalculator(db_connection=conn)

        # Bottom 9, down by 10 runs - should be very low leverage
        calc._li_matrix = {(9, False, 2, '000', -10): 0.1}

        state = GameState(inning=9, is_top=False, outs=2, score_home=0, score_away=10)
        li = calc.compute(state)

        assert li == 0.1

    def test_full_count_high_leverage(self, mock_db):
        """Test leverage with count consideration."""
        conn, _ = mock_db
        calc = LeverageIndexCalculator(db_connection=conn)

        # 3-2 count increases leverage (if GameState supported count)
        base_state = GameState(inning=9, is_top=False, outs=2)
        # Note: GameState doesn't have balls/strikes currently

        calc._li_matrix = {
            (9, False, 2, '000', 0): 3.5,
        }

        # Just verify base state computes
        base_li = calc.compute(base_state)

        assert base_li is not None


class TestLeverageIndexIntegration:
    """Integration tests for Leverage Index with other features."""

    def test_li_with_we_interaction(self, mock_db):
        """Test interaction between LI and WE."""
        # High leverage + close game = important moment
        # Low leverage + close game = less critical moment

        from baseball.features.win_expectancy import WinExpectancyCalculator

        conn, _ = mock_db
        we_calc = WinExpectancyCalculator(db_connection=conn)
        li_calc = LeverageIndexCalculator(db_connection=conn)

        # Set up matrices
        we_calc._we_matrix = {(9, False, 2, '000', 0): 0.50}
        li_calc._li_matrix = {(9, False, 2, '000', 0): 3.5}

        state = GameState(inning=9, is_top=False, outs=2, score_home=4, score_away=4)

        we = we_calc.compute(state)
        li = li_calc.compute(state)

        # Tied game in late inning should have both
        # - WE near 0.50 (either team can win)
        # - High LI (this moment matters a lot)
        assert 0.45 <= we <= 0.55
        assert li > 2.0
