#!/usr/bin/env python3
"""
Fixed-seed reproducibility tests for baseball state transitions.

Ensures that state transitions are deterministic when given the same inputs.
"""

import random

from retrosheet.simulation.baseball_state import (
    BaseOccupancy,
    GameState,
    PlayOutcome,
    advance_runners,
)


def test_home_run_reproducibility():
    """Test home run transition is reproducible with fixed seed."""
    random.seed(42)
    
    state = GameState(
        inning=3,
        top_inning=True,
        outs=1,
        bases=BaseOccupancy(first=True, second=True, third=True),
        home_score=2,
        away_score=3,
    )
    
    # Run same transition multiple times
    results = []
    for _ in range(10):
        new_state, runs = advance_runners(state, PlayOutcome.HOME_RUN)
        results.append((new_state, runs))
    
    # All results should be identical
    first_result = results[0]
    for result in results[1:]:
        assert result[0].inning == first_result[0].inning
        assert result[0].outs == first_result[0].outs
        assert result[0].bases.to_tuple() == first_result[0].bases.to_tuple()
        assert result[0].home_score == first_result[0].home_score
        assert result[0].away_score == first_result[0].away_score
        assert result[1] == first_result[1]


def test_single_reproducibility():
    """Test single transition is reproducible with fixed seed."""
    random.seed(123)
    
    state = GameState(
        inning=5,
        top_inning=False,
        outs=2,
        bases=BaseOccupancy(first=True, second=False, third=False),
        home_score=1,
        away_score=0,
    )
    
    results = []
    for _ in range(10):
        new_state, runs = advance_runners(state, PlayOutcome.SINGLE)
        results.append((new_state, runs))
    
    first_result = results[0]
    for result in results[1:]:
        assert result[0].bases.to_tuple() == first_result[0].bases.to_tuple()
        assert result[1] == first_result[1]


def test_out_transition_reproducibility():
    """Test out transition is reproducible with fixed seed."""
    random.seed(456)
    
    state = GameState(inning=7, top_inning=True, outs=2)
    
    from retrosheet.simulation.baseball_state import apply_out_transition
    
    results = []
    for _ in range(10):
        new_state = apply_out_transition(state, outs_added=1)
        results.append(new_state)
    
    first_result = results[0]
    for result in results[1:]:
        assert result.inning == first_result.inning
        assert result.top_inning == first_result.top_inning
        assert result.outs == first_result.outs


def test_sequence_reproducibility():
    """Test a sequence of transitions is reproducible."""
    random.seed(789)
    
    state = GameState()
    sequence = [
        PlayOutcome.SINGLE,
        PlayOutcome.STRIKEOUT,
        PlayOutcome.DOUBLE,
        PlayOutcome.FLY_OUT,
        PlayOutcome.WALK,
    ]
    
    # Run sequence multiple times
    final_states = []
    for _ in range(5):
        temp_state = GameState()
        for outcome in sequence:
            temp_state, _ = advance_runners(temp_state, outcome)
        final_states.append(temp_state)
    
    # All final states should be identical
    first_state = final_states[0]
    for state in final_states[1:]:
        assert state.inning == first_state.inning
        assert state.top_inning == first_state.top_inning
        assert state.outs == first_state.outs
        assert state.bases.to_tuple() == first_state.bases.to_tuple()


if __name__ == "__main__":
    test_home_run_reproducibility()
    test_single_reproducibility()
    test_out_transition_reproducibility()
    test_sequence_reproducibility()
    print("All reproducibility tests passed.")
