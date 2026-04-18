#!/usr/bin/env python3
"""
Baseball State Transition Engine

Implements canonical baseball state machine rules for:
- Base occupancy state transitions
- Out count state transitions  
- Run scoring logic
- Lineup progression
- Substitution handling

This module is designed to be validated against historical Retrosheet data
to ensure state transition accuracy before use in simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class Base(Enum):
    """Base position enum."""
    NONE = 0
    FIRST = 1
    SECOND = 2
    THIRD = 3


@dataclass
class BaseOccupancy:
    """Represents the current state of base occupancy."""
    first: bool = False
    second: bool = False
    third: bool = False

    def to_tuple(self) -> tuple[bool, bool, bool]:
        """Convert to tuple for hashing/comparison."""
        return (self.first, self.second, self.third)

    @classmethod
    def from_tuple(cls, state: tuple[bool, bool, bool]) -> "BaseOccupancy":
        """Create from tuple."""
        return cls(first=state[0], second=state[1], third=state[2])

    def runners_on(self) -> int:
        """Count total runners on base."""
        return sum([self.first, self.second, self.third])

    def is_loaded(self) -> bool:
        """Check if bases are loaded."""
        return self.first and self.second and self.third

    def is_empty(self) -> bool:
        """Check if bases are empty."""
        return not (self.first or self.second or self.third)


@dataclass
class GameState:
    """Represents the complete baseball game state."""
    inning: int = 1
    top_inning: bool = True  # True = top (away batting), False = bottom (home batting)
    outs: int = 0
    bases: BaseOccupancy = field(default_factory=BaseOccupancy)
    home_score: int = 0
    away_score: int = 0

    def is_legal(self) -> bool:
        """Validate that the game state is legal."""
        if not (0 <= self.inning <= 99):
            return False
        if not (0 <= self.outs <= 3):
            return False
        if self.home_score < 0 or self.away_score < 0:
            return False
        return True

    def half_inning_key(self) -> str:
        """Generate a unique key for the half-inning."""
        team = "away" if self.top_inning else "home"
        return f"{self.inning}_{team}"


class PlayOutcome(Enum):
    """Standard play outcomes that affect game state."""
    # Outs
    STRIKEOUT = "strikeout"
    GROUND_OUT = "ground_out"
    FLY_OUT = "fly_out"
    LINE_OUT = "line_out"
    POP_OUT = "pop_out"
    
    # Hits
    SINGLE = "single"
    DOUBLE = "double"
    TRIPLE = "triple"
    HOME_RUN = "home_run"
    
    # Walks
    WALK = "walk"
    HIT_BY_PITCH = "hit_by_pitch"
    
    # Other
    SACRIFICE_FLY = "sacrifice_fly"
    SACRIFICE_BUNT = "sacrifice_bunt"
    FIELDERS_CHOICE = "fielders_choice"
    ERROR = "error"
    DOUBLE_PLAY = "double_play"
    TRIPLE_PLAY = "triple_play"


def apply_base_transition(
    bases: BaseOccupancy,
    outcome: PlayOutcome,
    batter_reached: bool = True,
    outs: int = 0,
) -> tuple[BaseOccupancy, int]:
    """
    Apply base occupancy transition based on play outcome.
    
    Returns:
        tuple of (new bases, runs scored)
    """
    runs = 0
    new_bases = BaseOccupancy(
        first=bases.first,
        second=bases.second,
        third=bases.third,
    )

    if outcome == PlayOutcome.HOME_RUN:
        runs = 1 + bases.runners_on()
        new_bases = BaseOccupancy()  # Clear bases after HR
        return new_bases, runs

    if outcome == PlayOutcome.TRIPLE:
        runs = bases.third  # Runner on 3rd scores
        new_bases = BaseOccupancy(first=True, second=False, third=False)
        if bases.second:
            runs += 1
        if bases.first:
            new_bases.second = True
        if bases.second:
            new_bases.third = True
        return new_bases, runs

    if outcome == PlayOutcome.DOUBLE:
        runs = bases.third  # Runner on 3rd scores
        new_bases = BaseOccupancy(first=False, second=True, third=False)
        if bases.second:
            new_bases.third = True
        if bases.first:
            new_bases.third = True  # Runner on 1st advances to 3rd
        return new_bases, runs

    if outcome == PlayOutcome.SINGLE:
        runs = bases.third  # Runner on 3rd scores
        new_bases = BaseOccupancy(first=True, second=False, third=False)
        if bases.second:
            new_bases.third = True
        if bases.first:
            new_bases.second = True
        return new_bases, runs

    if outcome in (PlayOutcome.WALK, PlayOutcome.HIT_BY_PITCH):
        if not bases.is_loaded():
            # Simple walk - no forced runs
            if bases.first and bases.second:
                new_bases.third = True
                new_bases.second = True
                new_bases.first = True
            elif bases.first:
                new_bases.second = True
                new_bases.first = True
            elif bases.second:
                new_bases.first = True
                new_bases.second = True
            elif bases.third:
                new_bases.first = True
                new_bases.third = True
            else:
                new_bases.first = True
        else:
            # Bases loaded - runner from 3rd scores
            runs = 1
            new_bases.first = True
            new_bases.second = True
            new_bases.third = True
        return new_bases, runs

    if outcome == PlayOutcome.SACRIFICE_FLY:
        # Runner advances if possible, batter out
        if bases.third and bases.outs < 2:
            runs = 1
            new_bases.third = False
        return new_bases, runs

    # For outs and other plays, bases don't change (simplified)
    return new_bases, runs


def apply_out_transition(state: GameState, outs_added: int = 1) -> GameState:
    """
    Apply out count transition and handle half-inning ending.
    
    Returns new GameState (may have advanced to next half-inning).
    """
    new_outs = state.outs + outs_added
    new_state = GameState(
        inning=state.inning,
        top_inning=state.top_inning,
        outs=min(new_outs, 3),
        bases=BaseOccupancy(
            first=state.bases.first,
            second=state.bases.second,
            third=state.bases.third,
        ),
        home_score=state.home_score,
        away_score=state.away_score,
    )

    # Check for half-inning end
    if new_outs >= 3:
        # Clear bases, flip inning
        new_state.bases = BaseOccupancy()
        new_state.outs = 0
        
        if new_state.top_inning:
            # End of top inning
            new_state.top_inning = False
        else:
            # End of bottom inning - advance to next inning
            new_state.top_inning = True
            new_state.inning += 1

    return new_state


def advance_runners(state: GameState, outcome: PlayOutcome) -> tuple[GameState, int]:
    """
    Apply a complete play transition to the game state.
    
    Returns:
        tuple of (new GameState, runs scored on this play)
    """
    # Determine if batter reached base
    batter_reached = outcome not in [
        PlayOutcome.STRIKEOUT,
        PlayOutcome.GROUND_OUT,
        PlayOutcome.FLY_OUT,
        PlayOutcome.LINE_OUT,
        PlayOutcome.POP_OUT,
        PlayOutcome.SACRIFICE_FLY,
        PlayOutcome.SACRIFICE_BUNT,
    ]

    # Apply base transition
    new_bases, runs = apply_base_transition(state.bases, outcome, batter_reached)

    # Determine outs added
    outs_added = 1
    if outcome in (PlayOutcome.DOUBLE_PLAY,):
        outs_added = 2
    elif outcome == PlayOutcome.TRIPLE_PLAY:
        outs_added = 3
    elif outcome in (PlayOutcome.STRIKEOUT, PlayOutcome.GROUND_OUT, PlayOutcome.FLY_OUT,
                    PlayOutcome.LINE_OUT, PlayOutcome.POP_OUT):
        outs_added = 1
    elif outcome in (PlayOutcome.WALK, PlayOutcome.HIT_BY_PITCH, PlayOutcome.SINGLE,
                    PlayOutcome.DOUBLE, PlayOutcome.TRIPLE, PlayOutcome.HOME_RUN):
        outs_added = 0
    elif outcome == PlayOutcome.SACRIFICE_FLY:
        outs_added = 1
    elif outcome == PlayOutcome.SACRIFICE_BUNT:
        outs_added = 1

    # Apply out transition
    new_state = apply_out_transition(state, outs_added)
    new_state.bases = new_bases

    # Add runs to appropriate team score
    if state.top_inning:
        new_state.away_score += runs
    else:
        new_state.home_score += runs

    return new_state, runs


# Initialize module
__all__ = [
    "Base",
    "BaseOccupancy",
    "GameState",
    "PlayOutcome",
    "apply_base_transition",
    "apply_out_transition",
    "advance_runners",
]
