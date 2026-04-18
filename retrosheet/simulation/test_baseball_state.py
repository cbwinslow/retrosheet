#!/usr/bin/env python3
"""
Exhaustive tests for baseball state transitions.

Validates state machine rules against expected baseball behavior.
"""

import pytest

from retrosheet.simulation.baseball_state import (
    BaseOccupancy,
    GameState,
    PlayOutcome,
    advance_runners,
    apply_base_transition,
    apply_out_transition,
)


class TestBaseOccupancy:
    """Test BaseOccupancy state machine."""

    def test_empty_bases(self):
        """Test empty bases state."""
        bases = BaseOccupancy()
        assert bases.to_tuple() == (False, False, False)
        assert bases.runners_on() == 0
        assert bases.is_empty() is True
        assert bases.is_loaded() is False

    def test_loaded_bases(self):
        """Test loaded bases state."""
        bases = BaseOccupancy(first=True, second=True, third=True)
        assert bases.to_tuple() == (True, True, True)
        assert bases.runners_on() == 3
        assert bases.is_empty() is False
        assert bases.is_loaded() is True

    def test_partial_occupancy(self):
        """Test various partial occupancy states."""
        # First and second
        bases = BaseOccupancy(first=True, second=True, third=False)
        assert bases.runners_on() == 2
        assert bases.is_loaded() is False

        # First and third
        bases = BaseOccupancy(first=True, second=False, third=True)
        assert bases.runners_on() == 2
        assert bases.is_loaded() is False

        # Second and third
        bases = BaseOccupancy(first=False, second=True, third=True)
        assert bases.runners_on() == 2
        assert bases.is_loaded() is False

    def test_from_tuple(self):
        """Test creating BaseOccupancy from tuple."""
        state = (True, False, True)
        bases = BaseOccupancy.from_tuple(state)
        assert bases.first is True
        assert bases.second is False
        assert bases.third is True


class TestGameState:
    """Test GameState validation and methods."""

    def test_initial_state(self):
        """Test initial game state."""
        state = GameState()
        assert state.inning == 1
        assert state.top_inning is True
        assert state.outs == 0
        assert state.home_score == 0
        assert state.away_score == 0
        assert state.is_legal() is True

    def test_illegal_states(self):
        """Test detection of illegal game states."""
        # Negative inning
        state = GameState(inning=-1)
        assert state.is_legal() is False

        # Too many outs
        state = GameState(outs=4)
        assert state.is_legal() is False

        # Negative scores
        state = GameState(home_score=-1)
        assert state.is_legal() is False

    def test_half_inning_key(self):
        """Test half-inning key generation."""
        state = GameState(inning=1, top_inning=True)
        assert state.half_inning_key() == "1_away"

        state = GameState(inning=5, top_inning=False)
        assert state.half_inning_key() == "5_home"


class TestBaseTransitions:
    """Test base occupancy transitions."""

    def test_home_run_clears_bases(self):
        """Test home run clears all bases and scores all runners."""
        bases = BaseOccupancy(first=True, second=True, third=True)
        new_bases, runs = apply_base_transition(bases, PlayOutcome.HOME_RUN)
        assert new_bases.is_empty() is True
        assert runs == 4  # 3 runners + batter

    def test_home_run_empty_bases(self):
        """Test home run with empty bases."""
        bases = BaseOccupancy()
        new_bases, runs = apply_base_transition(bases, PlayOutcome.HOME_RUN)
        assert new_bases.is_empty() is True
        assert runs == 1  # Just the batter

    def test_single_advances_runners(self):
        """Test single advances runners appropriately."""
        # Runner on first only
        bases = BaseOccupancy(first=True, second=False, third=False)
        new_bases, runs = apply_base_transition(bases, PlayOutcome.SINGLE)
        assert new_bases.first is True
        assert new_bases.second is True
        assert new_bases.third is False
        assert runs == 0

        # Runner on second only
        bases = BaseOccupancy(first=False, second=True, third=False)
        new_bases, runs = apply_base_transition(bases, PlayOutcome.SINGLE)
        assert new_bases.first is True
        assert new_bases.second is False
        assert new_bases.third is True
        assert runs == 0

        # Runner on third only - scores
        bases = BaseOccupancy(first=False, second=False, third=True)
        new_bases, runs = apply_base_transition(bases, PlayOutcome.SINGLE)
        assert new_bases.first is True
        assert new_bases.second is False
        assert new_bases.third is False
        assert runs == 1

    def test_double_advances_runners(self):
        """Test double advances runners appropriately."""
        # Runner on first only
        bases = BaseOccupancy(first=True, second=False, third=False)
        new_bases, runs = apply_base_transition(bases, PlayOutcome.DOUBLE)
        assert new_bases.first is False
        assert new_bases.second is True
        assert new_bases.third is True
        assert runs == 0

        # Runner on third - scores
        bases = BaseOccupancy(first=False, second=False, third=True)
        new_bases, runs = apply_base_transition(bases, PlayOutcome.DOUBLE)
        assert new_bases.first is False
        assert new_bases.second is True
        assert new_bases.third is False
        assert runs == 1

    def test_walk_loads_bases(self):
        """Test walk with bases loaded scores a run."""
        bases = BaseOccupancy(first=True, second=True, third=True)
        new_bases, runs = apply_base_transition(bases, PlayOutcome.WALK)
        assert new_bases.is_loaded() is True
        assert runs == 1

    def test_walk_empty_bases(self):
        """Test walk with empty bases."""
        bases = BaseOccupancy()
        new_bases, runs = apply_base_transition(bases, PlayOutcome.WALK)
        assert new_bases.first is True
        assert new_bases.second is False
        assert new_bases.third is False
        assert runs == 0

    def test_sacrifice_fly(self):
        """Test sacrifice fly with runner on third."""
        bases = BaseOccupancy(first=False, second=False, third=True)
        new_bases, runs = apply_base_transition(bases, PlayOutcome.SACRIFICE_FLY, outs=0)
        assert new_bases.third is False
        assert runs == 1


class TestOutTransitions:
    """Test out count transitions."""

    def test_single_out(self):
        """Test adding one out."""
        state = GameState(outs=0)
        new_state = apply_out_transition(state, outs_added=1)
        assert new_state.outs == 1
        assert new_state.inning == 1
        assert new_state.top_inning is True

    def test_two_outs(self):
        """Test adding two outs triggers half-inning end."""
        state = GameState(outs=1)
        new_state = apply_out_transition(state, outs_added=2)
        assert new_state.outs == 0  # Half-inning ended, outs cleared

    def test_half_inning_end_top(self):
        """Test end of top inning flips to bottom."""
        state = GameState(inning=1, top_inning=True, outs=2)
        new_state = apply_out_transition(state, outs_added=1)
        assert new_state.outs == 0
        assert new_state.top_inning is False
        assert new_state.inning == 1
        assert new_state.bases.is_empty() is True

    def test_half_inning_end_bottom(self):
        """Test end of bottom inning advances to next inning."""
        state = GameState(inning=1, top_inning=False, outs=2)
        new_state = apply_out_transition(state, outs_added=1)
        assert new_state.outs == 0
        assert new_state.top_inning is True
        assert new_state.inning == 2
        assert new_state.bases.is_empty() is True


class TestCompletePlayTransitions:
    """Test complete play transitions."""

    def test_strikeout(self):
        """Test strikeout adds one out, bases unchanged."""
        state = GameState(outs=0, bases=BaseOccupancy(first=True))
        new_state, runs = advance_runners(state, PlayOutcome.STRIKEOUT)
        assert new_state.outs == 1
        assert new_state.bases.first is True
        assert runs == 0

    def test_single_with_runners(self):
        """Test single with runners on base."""
        state = GameState(
            outs=0,
            bases=BaseOccupancy(first=True, second=True, third=False),
            top_inning=True,
        )
        new_state, runs = advance_runners(state, PlayOutcome.SINGLE)
        assert new_state.bases.first is True
        assert new_state.bases.second is True
        assert new_state.bases.third is True
        assert new_state.away_score == 0  # No runs scored
        assert runs == 0

    def test_home_run_scores_all(self):
        """Test home run scores all runners plus batter."""
        state = GameState(
            outs=0,
            bases=BaseOccupancy(first=True, second=True, third=True),
            top_inning=True,
            home_score=0,
            away_score=2,
        )
        new_state, runs = advance_runners(state, PlayOutcome.HOME_RUN)
        assert new_state.bases.is_empty() is True
        assert new_state.away_score == 6  # 2 + 4 runs
        assert runs == 4

    def test_double_play(self):
        """Test double play adds two outs."""
        state = GameState(outs=0, bases=BaseOccupancy(first=True))
        new_state, runs = advance_runners(state, PlayOutcome.DOUBLE_PLAY)
        assert new_state.outs == 2
        assert runs == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
