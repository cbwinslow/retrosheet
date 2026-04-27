"""Markov Chain Game Simulator for Baseball

Models game states as Markov chains and simulates innings/games.

State: S = (inning, outs, base_state, score_diff)
Transition: P(S_{t+1} | S_t, outcome)

Author: Agent Cascade
Date: April 24, 2026
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum

import numpy as np


# ============================================================================
# BASE STATE ENUMERATION
# ============================================================================


class BaseState(IntEnum):
    """Enumeration of all 8 possible base states.

    Encoding: (runner on 3rd, runner on 2nd, runner on 1st) as binary
    """

    EMPTY = 0  # 000 - no runners
    FIRST = 1  # 001 - runner on 1st
    SECOND = 2  # 010 - runner on 2nd
    THIRD = 4  # 100 - runner on 3rd
    FIRST_SECOND = 3  # 011 - runners on 1st & 2nd
    FIRST_THIRD = 5  # 101 - runners on 1st & 3rd
    SECOND_THIRD = 6  # 110 - runners on 2nd & 3rd
    LOADED = 7  # 111 - bases loaded


# Base state transitions for each outcome
BASE_TRANSITIONS: dict[str, dict[BaseState, list[tuple[float, BaseState, int]]]] = {
    # Single: batter to 1st, runners advance 1-2 bases
    'single': {
        BaseState.EMPTY: [(1.0, BaseState.FIRST, 0)],
        BaseState.FIRST: [(0.7, BaseState.FIRST, 1), (0.3, BaseState.FIRST_SECOND, 0)],
        BaseState.SECOND: [(0.6, BaseState.FIRST, 1), (0.4, BaseState.FIRST_SECOND, 0)],
        BaseState.THIRD: [(0.5, BaseState.FIRST, 1), (0.5, BaseState.FIRST, 0)],
        BaseState.FIRST_SECOND: [
            (0.5, BaseState.FIRST, 2),
            (0.3, BaseState.FIRST_SECOND, 1),
            (0.2, BaseState.LOADED, 0),
        ],
        BaseState.FIRST_THIRD: [
            (0.4, BaseState.FIRST, 2),
            (0.4, BaseState.FIRST_SECOND, 1),
            (0.2, BaseState.FIRST, 1),
        ],
        BaseState.SECOND_THIRD: [
            (0.4, BaseState.FIRST, 2),
            (0.4, BaseState.FIRST_SECOND, 1),
            (0.2, BaseState.FIRST, 1),
        ],
        BaseState.LOADED: [
            (0.4, BaseState.FIRST, 2),
            (0.4, BaseState.FIRST_SECOND, 1),
            (0.2, BaseState.FIRST_THIRD, 1),
        ],
    },
    # Double: batter to 2nd, runners advance 2 bases
    'double': {
        BaseState.EMPTY: [(1.0, BaseState.SECOND, 0)],
        BaseState.FIRST: [(0.6, BaseState.SECOND, 1), (0.4, BaseState.SECOND_THIRD, 0)],
        BaseState.SECOND: [(0.7, BaseState.SECOND, 1), (0.3, BaseState.SECOND, 0)],
        BaseState.THIRD: [(0.8, BaseState.SECOND, 1), (0.2, BaseState.SECOND, 0)],
        BaseState.FIRST_SECOND: [(0.5, BaseState.SECOND, 2), (0.5, BaseState.SECOND_THIRD, 1)],
        BaseState.FIRST_THIRD: [(0.5, BaseState.SECOND, 2), (0.5, BaseState.SECOND_THIRD, 1)],
        BaseState.SECOND_THIRD: [(0.6, BaseState.SECOND, 2), (0.4, BaseState.SECOND, 1)],
        BaseState.LOADED: [(0.5, BaseState.SECOND, 3), (0.5, BaseState.SECOND_THIRD, 2)],
    },
    # Triple: batter to 3rd, all runners score
    'triple': {
        BaseState.EMPTY: [(1.0, BaseState.THIRD, 0)],
        BaseState.FIRST: [(1.0, BaseState.THIRD, 1)],
        BaseState.SECOND: [(1.0, BaseState.THIRD, 1)],
        BaseState.THIRD: [(1.0, BaseState.THIRD, 1)],
        BaseState.FIRST_SECOND: [(1.0, BaseState.THIRD, 2)],
        BaseState.FIRST_THIRD: [(1.0, BaseState.THIRD, 2)],
        BaseState.SECOND_THIRD: [(1.0, BaseState.THIRD, 2)],
        BaseState.LOADED: [(1.0, BaseState.THIRD, 3)],
    },
    # Home run: all runners score, batter scores
    'home_run': {
        BaseState.EMPTY: [(1.0, BaseState.EMPTY, 1)],
        BaseState.FIRST: [(1.0, BaseState.EMPTY, 2)],
        BaseState.SECOND: [(1.0, BaseState.EMPTY, 2)],
        BaseState.THIRD: [(1.0, BaseState.EMPTY, 2)],
        BaseState.FIRST_SECOND: [(1.0, BaseState.EMPTY, 3)],
        BaseState.FIRST_THIRD: [(1.0, BaseState.EMPTY, 3)],
        BaseState.SECOND_THIRD: [(1.0, BaseState.EMPTY, 3)],
        BaseState.LOADED: [(1.0, BaseState.EMPTY, 4)],
    },
    # Walk/HBP: batter to 1st, forced runners advance
    'walk': {
        BaseState.EMPTY: [(1.0, BaseState.FIRST, 0)],
        BaseState.FIRST: [(1.0, BaseState.FIRST_SECOND, 0)],
        BaseState.SECOND: [(1.0, BaseState.FIRST_SECOND, 0)],
        BaseState.THIRD: [(1.0, BaseState.FIRST_THIRD, 0)],
        BaseState.FIRST_SECOND: [(1.0, BaseState.LOADED, 0)],
        BaseState.FIRST_THIRD: [(1.0, BaseState.LOADED, 0)],
        BaseState.SECOND_THIRD: [(1.0, BaseState.FIRST_SECOND, 1)],
        BaseState.LOADED: [(1.0, BaseState.LOADED, 1)],
    },
    # Strikeout: no base change, out recorded
    'strikeout': {state: [(1.0, state, 0)] for state in BaseState},
    # Ball in play out: bases depend on type (simplify to no advancement)
    'ball_in_play_out': {state: [(1.0, state, 0)] for state in BaseState},
    # Error: treat as single with advancement
    'error': {
        BaseState.EMPTY: [(1.0, BaseState.FIRST, 0)],
        BaseState.FIRST: [(0.6, BaseState.FIRST, 1), (0.4, BaseState.FIRST_SECOND, 0)],
        BaseState.SECOND: [(0.6, BaseState.FIRST, 1), (0.4, BaseState.FIRST_SECOND, 0)],
        BaseState.THIRD: [(0.6, BaseState.FIRST, 1), (0.4, BaseState.FIRST, 0)],
        BaseState.FIRST_SECOND: [
            (0.4, BaseState.FIRST, 2),
            (0.4, BaseState.FIRST_SECOND, 1),
            (0.2, BaseState.LOADED, 0),
        ],
        BaseState.FIRST_THIRD: [
            (0.4, BaseState.FIRST, 2),
            (0.4, BaseState.FIRST_SECOND, 1),
            (0.2, BaseState.FIRST_THIRD, 0),
        ],
        BaseState.SECOND_THIRD: [
            (0.4, BaseState.FIRST, 2),
            (0.4, BaseState.FIRST_SECOND, 1),
            (0.2, BaseState.FIRST, 1),
        ],
        BaseState.LOADED: [
            (0.4, BaseState.FIRST, 3),
            (0.4, BaseState.FIRST_SECOND, 2),
            (0.2, BaseState.FIRST_THIRD, 1),
        ],
    },
    # Sacrifice: runners advance, out recorded
    'sacrifice': {
        BaseState.EMPTY: [(1.0, BaseState.EMPTY, 0)],
        BaseState.FIRST: [(0.8, BaseState.EMPTY, 0), (0.2, BaseState.FIRST, 0)],
        BaseState.SECOND: [(0.8, BaseState.EMPTY, 1), (0.2, BaseState.SECOND, 0)],
        BaseState.THIRD: [(0.8, BaseState.EMPTY, 1), (0.2, BaseState.THIRD, 0)],
        BaseState.FIRST_SECOND: [(0.7, BaseState.FIRST, 1), (0.3, BaseState.FIRST_SECOND, 0)],
        BaseState.FIRST_THIRD: [(0.7, BaseState.FIRST, 1), (0.3, BaseState.FIRST_THIRD, 0)],
        BaseState.SECOND_THIRD: [(0.7, BaseState.EMPTY, 2), (0.3, BaseState.SECOND_THIRD, 0)],
        BaseState.LOADED: [(0.7, BaseState.FIRST, 2), (0.3, BaseState.LOADED, 0)],
    },
}

# Merge walk and hit_by_pitch
BASE_TRANSITIONS['hit_by_pitch'] = BASE_TRANSITIONS['walk']


# ============================================================================
# GAME STATE
# ============================================================================


@dataclass
class GameState:
    """Complete state of a baseball game."""

    inning: int = 1  # Current inning (1-9+)
    is_bottom: bool = False  # Bottom of inning?
    outs: int = 0  # Outs (0-2)
    bases: BaseState = BaseState.EMPTY  # Base runner state
    home_score: int = 0  # Home team runs
    away_score: int = 0  # Away team runs

    def copy(self) -> GameState:
        """Create a copy of the state."""
        return GameState(
            inning=self.inning,
            is_bottom=self.is_bottom,
            outs=self.outs,
            bases=self.bases,
            home_score=self.home_score,
            away_score=self.away_score,
        )

    @property
    def score_diff(self) -> int:
        """Home score minus away score."""
        return self.home_score - self.away_score

    @property
    def batting_team_score(self) -> int:
        """Score of team currently batting."""
        return self.home_score if self.is_bottom else self.away_score

    @property
    def fielding_team_score(self) -> int:
        """Score of team currently fielding."""
        return self.away_score if self.is_bottom else self.home_score

    def is_game_over(self) -> bool:
        """Check if game has ended."""
        # Game ends after 9 innings if not tied
        if self.inning > 9 and self.score_diff != 0:
            return True
        # Extra innings end when score differs after bottom
        if self.inning > 9 and self.is_bottom and self.home_score > self.away_score:
            return True
        return False

    def advance_inning(self):
        """Move to next half-inning."""
        if self.is_bottom:
            self.inning += 1
            self.is_bottom = False
        else:
            self.is_bottom = True
        self.outs = 0
        self.bases = BaseState.EMPTY

    def __str__(self) -> str:
        team = 'Home' if self.is_bottom else 'Away'
        base_str = format(int(self.bases), '03b')
        return f'{team} {self.inning}{"B" if self.is_bottom else "T"} O:{self.outs} B:{base_str} Score:{self.away_score}-{self.home_score}'


# ============================================================================
# MARKOV CHAIN SIMULATOR
# ============================================================================


class MarkovChainSimulator:
    """Simulates baseball games using Markov chains.

    Given P(outcome | state), simulates full innings and games.
    """

    def __init__(
        self,
        outcome_probs_fn: Callable[[GameState], dict[str, float]],
        max_innings: int = 12,
    ):
        """Parameters:
        -----------
        outcome_probs_fn : callable
            Function that takes GameState and returns {outcome: probability}
        max_innings : int
            Maximum innings to simulate
        """
        self.outcome_probs_fn = outcome_probs_fn
        self.max_innings = max_innings

    def simulate_plate_appearance(
        self,
        state: GameState,
        rng: np.random.Generator | None = None,
    ) -> tuple[str, int, BaseState]:
        """Simulate a single plate appearance.

        Returns:
        --------
        (outcome, runs_scored, new_base_state)
        """
        if rng is None:
            rng = np.random.default_rng()

        # Get outcome probabilities for current state
        probs = self.outcome_probs_fn(state)

        # Sample outcome
        outcomes = list(probs.keys())
        probabilities = list(probs.values())
        outcome = rng.choice(outcomes, p=probabilities)

        # Get transition for this outcome
        transitions = BASE_TRANSITIONS.get(outcome, BASE_TRANSITIONS['ball_in_play_out'])
        state_transitions = transitions.get(state.bases, [(1.0, state.bases, 0)])

        # Sample from possible transitions
        probs_t = [t[0] for t in state_transitions]
        idx = rng.choice(len(state_transitions), p=np.array(probs_t) / sum(probs_t))
        _, new_bases, runs_scored = state_transitions[idx]

        return outcome, runs_scored, new_bases

    def simulate_half_inning(
        self,
        initial_state: GameState,
        rng: np.random.Generator | None = None,
    ) -> tuple[GameState, int, list[str]]:
        """Simulate a half-inning.

        Returns:
        --------
        (final_state, runs_scored, outcomes_list)
        """
        if rng is None:
            rng = np.random.default_rng()

        state = initial_state.copy()
        runs_scored = 0
        outcomes = []

        while state.outs < 3 and not state.is_game_over():
            outcome, runs, new_bases = self.simulate_plate_appearance(state, rng)
            outcomes.append(outcome)

            # Update state
            runs_scored += runs
            if state.is_bottom:
                state.home_score += runs
            else:
                state.away_score += runs

            # Update bases and outs
            state.bases = new_bases

            # Check for out
            if outcome in ['strikeout', 'ball_in_play_out', 'sacrifice']:
                state.outs += 1

        return state, runs_scored, outcomes

    def simulate_game(
        self,
        rng: np.random.Generator | None = None,
    ) -> tuple[GameState, dict]:
        """Simulate a complete game.

        Returns:
        --------
        (final_state, game_log)
        """
        if rng is None:
            rng = np.random.default_rng()

        state = GameState()
        game_log = {
            'innings': [],
            'total_plate_appearances': 0,
            'outcomes': [],
        }

        while not state.is_game_over() and state.inning <= self.max_innings:
            # Simulate half-inning
            state_copy = state.copy()
            final_state, runs, outcomes = self.simulate_half_inning(state_copy, rng)

            # Log inning
            inning_log = {
                'inning': state.inning,
                'half': 'bottom' if state.is_bottom else 'top',
                'runs': runs,
                'outcomes': outcomes,
                'score_after': (final_state.away_score, final_state.home_score),
            }
            game_log['innings'].append(inning_log)
            game_log['total_plate_appearances'] += len(outcomes)
            game_log['outcomes'].extend(outcomes)

            # Update state
            state.home_score = final_state.home_score
            state.away_score = final_state.away_score

            # Advance inning
            state.advance_inning()

        game_log['final_score'] = (state.away_score, state.home_score)
        game_log['home_win'] = state.home_score > state.away_score

        return state, game_log

    def simulate_many_games(
        self,
        n_sims: int = 1000,
        seed: int = 42,
    ) -> dict:
        """Run Monte Carlo simulation of many games.

        Returns:
        --------
        Dict with win probabilities and statistics
        """
        rng = np.random.default_rng(seed)

        results = {
            'home_wins': 0,
            'away_wins': 0,
            'ties': 0,
            'total_runs_home': [],
            'total_runs_away': [],
            'score_diffs': [],
            'game_lengths': [],
        }

        for _ in range(n_sims):
            final_state, game_log = self.simulate_game(rng)

            # Record result
            if final_state.home_score > final_state.away_score:
                results['home_wins'] += 1
            elif final_state.away_score > final_state.home_score:
                results['away_wins'] += 1
            else:
                results['ties'] += 1

            results['total_runs_home'].append(final_state.home_score)
            results['total_runs_away'].append(final_state.away_score)
            results['score_diffs'].append(final_state.score_diff)
            results['game_lengths'].append(final_state.inning - 1)

        # Compute statistics
        total = n_sims
        results['home_win_prob'] = results['home_wins'] / total
        results['away_win_prob'] = results['away_wins'] / total
        results['tie_prob'] = results['ties'] / total
        results['avg_runs_home'] = np.mean(results['total_runs_home'])
        results['avg_runs_away'] = np.mean(results['total_runs_away'])
        results['avg_score_diff'] = np.mean(results['score_diffs'])
        results['avg_game_length'] = np.mean(results['game_lengths'])

        return results


# ============================================================================
# WIN PROBABILITY CALCULATOR
# ============================================================================


def calculate_win_probability(
    state: GameState,
    outcome_probs_fn: Callable[[GameState], dict[str, float]],
    n_sims: int = 1000,
    seed: int = 42,
    team: str = 'batting',  # 'batting' or 'home'
) -> float:
    """Calculate win probability from current game state using Monte Carlo.

    Parameters:
    -----------
    state : GameState
        Current game state
    outcome_probs_fn : callable
        Function returning outcome probabilities
    n_sims : int
        Number of simulations
    seed : int
        Random seed
    team : str
        Which team's win probability to calculate

    Returns:
    --------
    float : win probability (0-1)
    """
    simulator = MarkovChainSimulator(outcome_probs_fn, max_innings=12)
    rng = np.random.default_rng(seed)

    wins = 0

    for _ in range(n_sims):
        # Copy state
        sim_state = state.copy()

        # Simulate remainder of game
        while not sim_state.is_game_over() and sim_state.inning <= 12:
            final_state, _, _ = simulator.simulate_half_inning(sim_state, rng)
            sim_state.home_score = final_state.home_score
            sim_state.away_score = final_state.away_score
            sim_state.advance_inning()

        # Check win
        if team == 'home':
            if sim_state.home_score > sim_state.away_score:
                wins += 1
        elif team == 'batting':
            if sim_state.is_bottom:
                if sim_state.home_score > sim_state.away_score:
                    wins += 1
            else:
                if sim_state.away_score > sim_state.home_score:
                    wins += 1

    return wins / n_sims


# ============================================================================
# EXPECTED RUNS MATRIX
# ============================================================================


def compute_expected_runs_matrix(
    outcome_probs_fn: Callable[[BaseState, int], dict[str, float]],
    n_sims: int = 10000,
    seed: int = 42,
) -> np.ndarray:
    """Compute expected runs matrix for all base/out states.

    Returns 8x3 matrix: E[runs | bases, outs]
    """
    rng = np.random.default_rng(seed)
    expected_runs = np.zeros((8, 3))

    for base_state in BaseState:
        for outs in range(3):
            total_runs = 0

            for _ in range(n_sims):
                # Create temporary game state
                state = GameState(
                    inning=1,
                    is_bottom=False,
                    outs=outs,
                    bases=base_state,
                    home_score=0,
                    away_score=0,
                )

                # Simulate remainder of inning
                simulator = MarkovChainSimulator(
                    lambda s: outcome_probs_fn(s.bases, s.outs),
                    max_innings=1,
                )
                final_state, runs, _ = simulator.simulate_half_inning(state, rng)
                total_runs += runs

            expected_runs[int(base_state), outs] = total_runs / n_sims

    return expected_runs
