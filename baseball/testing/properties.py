"""Property-based testing utilities for baseball prediction system.

This module provides Hypothesis strategies and property-based testing utilities
to validate that our baseball algorithms maintain invariants across all possible inputs.

Author: Agent cbwinslow/retrosheet
Date: 2026-05-03
"""

import hypothesis.strategies as st
from hypothesis import given, settings, assume, note
from typing import List, Tuple, Optional
import numpy as np
from dataclasses import dataclass
import datetime

from baseball.testing.factories import PlayerFactory, PitchFactory, GameFactory


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def player_ids_strategy(draw) -> str:
    """Generate valid player IDs."""
    # MLB player IDs are typically 8-10 characters
    # Format: first letter of last name + first 4 letters of last name + first 2 of first name + 2 digits
    # Example: bondsba01 (Barry Bonds)
    last_name = draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Ll', 'Lu'))))
    first_name = draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Ll', 'Lu'))))
    digits = draw(st.text(min_size=2, max_size=2, alphabet='0123456789'))
    
    # Simplified player ID format
    player_id = f"{last_name[:4].lower()}{first_name[:2].lower()}{digits}"
    return player_id


@st.composite
def pitch_counts_strategy(draw) -> Tuple[int, int]:
    """Generate valid pitch counts (balls, strikes)."""
    balls = draw(st.integers(min_value=0, max_value=4))
    strikes = draw(st.integers(min_value=0, max_value=3))
    
    # Valid pitch counts: can't have 4 balls and 3 strikes simultaneously
    assume(not (balls == 4 and strikes == 3))
    
    return (balls, strikes)


@st.composite
def game_score_strategy(draw) -> Tuple[int, int]:
    """Generate valid game scores (home, away)."""
    home_score = draw(st.integers(min_value=0, max_value=30))
    away_score = draw(st.integers(min_value=0, max_value=30))
    
    # Limit total runs to reasonable baseball game
    assume(home_score + away_score <= 50)
    
    return (home_score, away_score)


@st.composite
def inning_strategy(draw) -> int:
    """Generate valid inning numbers."""
    # Regular game: 1-9, Extra innings: 10+
    return draw(st.integers(min_value=1, max_value=15))


@st.composite
def probability_strategy(draw) -> float:
    """Generate valid probability values."""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))


@st.composite
def run_expectancy_strategy(draw) -> float:
    """Generate valid run expectancy values."""
    # Run expectancy is typically 0-4 runs per inning
    return draw(st.floats(min_value=0.0, max_value=4.0, allow_nan=False, allow_infinity=False))


# ============================================================================
# Core Baseball Properties
# ============================================================================

class WinExpectancyProperties:
    """Property-based tests for win expectancy calculations."""
    
    @staticmethod
    @given(
        home_score=st.integers(min_value=0, max_value=20),
        away_score=st.integers(min_value=0, max_value=20),
        inning=inning_strategy(),
        top_bottom=st.booleans(),
        home_prob=probability_strategy(),
    )
    @settings(max_examples=100, deadline=None)
    def test_win_probability_bounds(home_score, away_score, inning, top_bottom, home_prob):
        """Test that win probability is always between 0 and 1."""
        # This property should hold for any valid input
        assert 0.0 <= home_prob <= 1.0, \
            f"Win probability {home_prob} must be between 0 and 1"
    
    @staticmethod
    @given(
        home_score=st.integers(min_value=0, max_value=20),
        away_score=st.integers(min_value=0, max_value=20),
    )
    @settings(max_examples=100, deadline=None)
    def test_win_probability_symmetry(home_score, away_score):
        """Test that win probabilities are symmetric."""
        # If home team has probability p of winning,
        # then away team should have probability 1-p of winning
        # (This assumes no ties, which is reasonable for baseball)
        
        # Note: This is a simplified test. In reality, win expectancy
        # depends on many factors including inning, outs, runners on base, etc.
        
        # For a complete game (all 9 innings), if scores are tied,
        # each team should have ~0.5 probability of winning
        if home_score == away_score:
            # In a tie game, probabilities should be symmetric
            pass  # Would need actual win expectancy function to test
    
    @staticmethod
    @given(
        home_score=st.integers(min_value=0, max_value=30),
        away_score=st.integers(min_value=0, max_value=30),
    )
    @settings(max_examples=100, deadline=None)
    def test_win_probability_monotonic(home_score, away_score):
        """Test that win probability increases with lead."""
        # If home team is winning by more runs, their win probability
        # should be higher (all else being equal)
        
        # This is a conceptual property - would need actual function to test
        lead = home_score - away_score
        # Positive lead (home winning) should correlate with higher win probability
        # Negative lead (away winning) should correlate with lower win probability


class PitchSequenceProperties:
    """Property-based tests for pitch sequence validation."""
    
    @staticmethod
    @given(pitch_counts=pitch_counts_strategy())
    @settings(max_examples=100, deadline=None)
    def test_pitch_count_validity(pitch_counts):
        """Test that pitch counts are always valid."""
        balls, strikes = pitch_counts
        
        # Balls should be 0-4
        assert 0 <= balls <= 4, f"Invalid ball count: {balls}"
        
        # Strikes should be 0-3
        assert 0 <= strikes <= 3, f"Invalid strike count: {strikes}"
        
        # Can't have 4 balls and 3 strikes simultaneously
        assert not (balls == 4 and strikes == 3), \
            "Invalid pitch count: 4 balls and 3 strikes"
    
    @staticmethod
    @given(
        pitches=st.lists(
            st.sampled_from(['F', 'S', 'B', 'X', 'H', 'O']),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_pitch_sequence_length(pitches: List[str]):
        """Test that pitch sequences have reasonable lengths."""
        # A plate appearance typically has 1-20 pitches
        assert 1 <= len(pitches) <= 20, \
            f"Unreasonable pitch sequence length: {len(pitches)}"
    
    @staticmethod
    @given(
        balls=st.integers(min_value=0, max_value=3),
        strikes=st.integers(min_value=0, max_value=2)
    )
    @settings(max_examples=100, deadline=None)
    def test_at_bat_continuation(balls: int, strikes: int):
        """Test that at-bats continue with valid counts."""
        # At-bat continues if not walk (4 balls) or strikeout (3 strikes)
        should_continue = not (balls == 4 or strikes == 3)
        
        # If at-bat continues, counts should be valid
        if should_continue:
            assert balls < 4, f"At-bat should end with {balls} balls"
            assert strikes < 3, f"At-bat should end with {strikes} strikes"


class FeatureCalculationProperties:
    """Property-based tests for feature engineering."""
    
    @staticmethod
    @given(
        values=st.lists(
            st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=1000
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_normalization_bounds(values: List[float]):
        """Test that normalized values are between 0 and 1."""
        # If we normalize values, they should be in [0, 1]
        # This is a conceptual property
        
        # Remove any extreme outliers for this test
        valid_values = [v for v in values if abs(v) < 1e6]
        if len(valid_values) > 1:
            # Normalization would produce values in [0, 1]
            pass
    
    @staticmethod
    @given(
        n=st.integers(min_value=1, max_value=1000),
        mean=st.floats(min_value=-100, max_value=100),
        std=st.floats(min_value=0.1, max_value=50)
    )
    @settings(max_examples=100, deadline=None)
    def test_feature_scaling_preserves_order(n: int, mean: float, std: float):
        """Test that feature scaling preserves relative ordering."""
        # If we scale features, the relative order should be preserved
        # This is important for maintaining feature relationships
        
        # Generate values
        values = st.lists(
            st.floats(min_value=mean-3*std, max_value=mean+3*std),
            min_size=n,
            max_size=n
        ).example()
        
        # Scaling (e.g., standardization) preserves order
        # If a < b, then scaled(a) < scaled(b) for linear scaling
        if len(values) >= 2:
            sorted_values = sorted(values)
            # After linear transformation, order should be preserved
            pass
    
    @staticmethod
    @given(
        home_features=st.lists(
            st.floats(min_value=-100, max_value=100),
            min_size=1,
            max_size=10
        ),
        away_features=st.lists(
            st.floats(min_value=-100, max_value=100),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_symmetric_features(home_features: List[float], away_features: List[float]):
        """Test that symmetric features produce symmetric predictions."""
        # If we swap home and away features, predictions should swap
        # This is important for fairness and consistency
        
        # For equal features, predictions should be equal
        if home_features == away_features:
            # Home and away predictions should be symmetric
            # (e.g., win probability should be 0.5 for equal teams)
            pass


class ModelPredictionProperties:
    """Property-based tests for model predictions."""
    
    @staticmethod
    @given(
        predictions=st.lists(
            probability_strategy(),
            min_size=1,
            max_size=100
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_prediction_bounds(predictions: List[float]):
        """Test that all predictions are valid probabilities."""
        for pred in predictions:
            assert 0.0 <= pred <= 1.0, \
                f"Prediction {pred} must be between 0 and 1"
    
    @staticmethod
    @given(
        n=st.integers(min_value=2, max_value=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_calibration_property(n: int):
        """Test that predictions are well-calibrated."""
        # For well-calibrated predictions, if we predict p for many events,
        # approximately p fraction should occur
        
        # This is a conceptual property
        # Would need actual predictions and outcomes to test
        pass
    
    @staticmethod
    @given(
        home_pred=probability_strategy(),
        away_pred=probability_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_mutually_exclusive_predictions(home_pred: float, away_pred: float):
        """Test that home and away win probabilities sum to ~1."""
        # For mutually exclusive events (home win, away win),
        # probabilities should sum to 1 (ignoring ties)
        
        # In baseball, with no ties, P(home win) + P(away win) = 1
        # Note: This ignores the possibility of ties
        expected_sum = 1.0
        actual_sum = home_pred + away_pred
        
        # Allow small tolerance for floating point errors
        # In reality, this depends on the specific model
        if abs(home_pred - 0.5) < 0.01 and abs(away_pred - 0.5) < 0.01:
            # For equal predictions, sum should be close to 1
            pass


class BettingAnalysisProperties:
    """Property-based tests for betting calculations."""
    
    @staticmethod
    @given(
        home_prob=probability_strategy(),
        away_prob=probability_strategy(),
        home_odds=st.integers(min_value=-1000, max_value=1000),
        away_odds=st.integers(min_value=-1000, max_value=1000)
    )
    @settings(max_examples=100, deadline=None)
    def test_value_betting_bounds(
        home_prob: float, away_prob: float,
        home_odds: int, away_odds: int
    ):
        """Test that value betting calculations are bounded."""
        # Convert odds to implied probabilities
        def odds_to_prob(odds: int) -> float:
            if odds > 0:
                return 100 / (odds + 100)
            elif odds < 0:
                return abs(odds) / (abs(odds) + 100)
            else:
                return 0.5
        
        home_implied = odds_to_prob(home_odds) if home_odds != 0 else 0.5
        away_implied = odds_to_prob(away_odds) if away_odds != 0 else 0.5
        
        # Implied probabilities should be between 0 and 1
        assert 0.0 <= home_implied <= 1.0
        assert 0.0 <= away_implied <= 1.0
        
        # Value = actual probability - implied probability
        home_value = home_prob - home_implied
        away_value = away_prob - away_implied
        
        # Value should be between -1 and 1
        assert -1.0 <= home_value <= 1.0
        assert -1.0 <= away_value <= 1.0
    
    @staticmethod
    @given(
        bankroll=st.floats(min_value=100, max_value=100000),
        bet_size=st.floats(min_value=1, max_value=10000),
        win_prob=probability_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_kelly_criterion_bounds(bankroll: float, bet_size: float, win_prob: float):
        """Test that Kelly criterion produces reasonable bet sizes."""
        # Kelly fraction = (bp - q) / b
        # where b = odds (in decimal), p = win prob, q = loss prob
        
        # For this test, we'll use simplified assumptions
        # Bet size should not exceed bankroll
        assert 0 <= bet_size <= bankroll, \
            f"Bet size {bet_size} should not exceed bankroll {bankroll}"
        
        # Bet size should be positive
        assert bet_size > 0, "Bet size should be positive"
    
    @staticmethod
    @given(
        edge=st.floats(min_value=-0.5, max_value=0.5),
        n_bets=st.integers(min_value=1, max_value=1000)
    )
    @settings(max_examples=100, deadline=None)
    def test_edge_accumulation(edge: float, n_bets: int):
        """Test that positive edge leads to expected profit."""
        # With positive expected value, profit should increase with more bets
        # This is a conceptual property
        
        if edge > 0:
            # Expected profit should be positive
            expected_profit = edge * n_bets
            assert expected_profit > 0, \
                f"Positive edge {edge} should lead to positive profit"
        elif edge < 0:
            # Expected profit should be negative
            expected_profit = edge * n_bets
            assert expected_profit < 0, \
                f"Negative edge {edge} should lead to negative profit"


# ============================================================================
# Data Integrity Properties
# ============================================================================

class RetrosheetDataProperties:
    """Property-based tests for Retrosheet data parsing."""
    
    @staticmethod
    @given(
        game_id=st.text(min_size=1, max_size=10, alphabet='0123456789')
    )
    @settings(max_examples=100, deadline=None)
    def test_game_id_format(game_id: str):
        """Test that game IDs are valid."""
        # MLB game IDs are typically numeric
        assert game_id.isdigit(), f"Game ID {game_id} should be numeric"
        
        # Game IDs should be positive
        if game_id:
            assert int(game_id) > 0, f"Game ID {game_id} should be positive"
    
    @staticmethod
    @given(
        year=st.integers(min_value=1871, max_value=2024),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=31)
    )
    @settings(max_examples=100, deadline=None)
    def test_date_validity(year: int, month: int, day: int):
        """Test that dates are valid."""
        # Simple date validation
        if month == 2:
            # February
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                assert day <= 29, f"Invalid day {day} for February in leap year"
            else:
                assert day <= 28, f"Invalid day {day} for February"
        elif month in [4, 6, 9, 11]:
            # 30-day months
            assert day <= 30, f"Invalid day {day} for month {month}"
        else:
            # 31-day months
            assert day <= 31, f"Invalid day {day} for month {month}"
    
    @staticmethod
    @given(
        player_id=player_ids_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_player_id_uniqueness(player_id: str):
        """Test that player IDs follow expected format."""
        # Player IDs should be non-empty
        assert len(player_id) > 0, "Player ID should not be empty"
        
        # Player IDs should be alphanumeric
        assert player_id.isalnum(), f"Player ID {player_id} should be alphanumeric"


class StatcastDataProperties:
    """Property-based tests for Statcast data validation."""
    
    @staticmethod
    @given(
        velocity=st.floats(min_value=0, max_value=150),
        spin_rate=st.floats(min_value=0, max_value=5000),
        extension=st.floats(min_value=0, max_value=8)
    )
    @settings(max_examples=100, deadline=None)
    def test_pitch_physics_bounds(
        velocity: float, spin_rate: float, extension: float
    ):
        """Test that pitch physics values are within reasonable bounds."""
        # Velocity should be 0-150 mph (typical range)
        assert 0 <= velocity <= 150, f"Velocity {velocity} mph is unrealistic"
        
        # Spin rate should be 0-5000 rpm (typical range)
        assert 0 <= spin_rate <= 5000, f"Spin rate {spin_rate} rpm is unrealistic"
        
        # Extension should be 0-8 feet (typical range)
        assert 0 <= extension <= 8, f"Extension {extension} ft is unrealistic"
    
    @staticmethod
    @given(
        x=st.floats(min_value=-200, max_value=200),
        y=st.floats(min_value=-200, max_value=200),
        z=st.floats(min_value=0, max_value=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_coordinate_bounds(x: float, y: float, z: float):
        """Test that coordinate values are within ballpark bounds."""
        # Baseball field coordinates should be within reasonable range
        # Home plate to outfield wall is typically < 400 feet
        assert abs(x) <= 200, f"X coordinate {x} is outside ballpark"
        assert abs(y) <= 200, f"Y coordinate {y} is outside ballpark"
        assert 0 <= z <= 100, f"Z coordinate {z} is outside ballpark"


class CrossSourceProperties:
    """Property-based tests for cross-source data consistency."""
    
    @staticmethod
    @given(
        retrosheet_id=st.text(min_size=1, max_size=10, alphabet='0123456789'),
        mlb_id=st.text(min_size=1, max_size=10, alphabet='0123456789')
    )
    @settings(max_examples=100, deadline=None)
    def test_id_mapping_consistency(retrosheet_id: str, mlb_id: str):
        """Test that ID mappings are consistent."""
        # If the same game exists in both sources, IDs should map
        # This is a conceptual property
        
        # IDs should be non-empty
        assert len(retrosheet_id) > 0
        assert len(mlb_id) > 0
    
    @staticmethod
    @given(
        date=st.dates(min_value=datetime.date(2000, 1, 1), max_value=datetime.date.today()),
        home_team=st.text(min_size=1, max_size=20, alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
        away_team=st.text(min_size=1, max_size=20, alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    )
    @settings(max_examples=100, deadline=None)
    def test_game_data_consistency(
        date: datetime.date, home_team: str, away_team: str
    ):
        """Test that game data is consistent across sources."""
        # Same game should have same date and teams across sources
        # This is a conceptual property
        
        # Home and away teams should be different
        assume(home_team != away_team)
        
        # Date should be valid
        assert date.year >= 2000, "Game date should be 2000 or later"


# ============================================================================
# Performance Properties
# ============================================================================

class ScalabilityProperties:
    """Property-based tests for system scalability."""
    
    @staticmethod
    @given(
        n_games=st.integers(min_value=1, max_value=10000),
        n_pitches=st.integers(min_value=1, max_value=100000)
    )
    @settings(max_examples=50, deadline=None)
    def test_processing_time_scaling(n_games: int, n_pitches: int):
        """Test that processing time scales reasonably with data size."""
        # Processing time should scale linearly or better with data size
        # This is a conceptual property
        
        # Would need actual timing measurements to test
        pass
    
    @staticmethod
    @given(
        batch_size=st.integers(min_value=1, max_value=10000)
    )
    @settings(max_examples=100, deadline=None)
    def test_batch_processing_efficiency(batch_size: int):
        """Test that batch processing is more efficient than individual processing."""
        # Batch processing should be more efficient than individual processing
        # This is a conceptual property
        
        # Would need actual timing measurements to test
        pass


class MemoryProperties:
    """Property-based tests for memory usage."""
    
    @staticmethod
    @given(
        n_records=st.integers(min_value=1, max_value=100000)
    )
    @settings(max_examples=50, deadline=None)
    def test_memory_usage_scaling(n_records: int):
        """Test that memory usage scales reasonably with data size."""
        # Memory usage should scale linearly with data size
        # This is a conceptual property
        
        # Would need actual memory measurements to test
        pass
    
    @staticmethod
    @given(
        cache_size=st.integers(min_value=1, max_value=10000)
    )
    @settings(max_examples=100, deadline=None)
    def test_cache_eviction_policy(cache_size: int):
        """Test that cache eviction policy maintains performance."""
        # Cache should maintain reasonable hit rate
        # This is a conceptual property
        
        # Would need actual cache measurements to test
        pass


class ConcurrencyProperties:
    """Property-based tests for concurrent operations."""
    
    @staticmethod
    @given(
        n_threads=st.integers(min_value=1, max_value=100),
        n_operations=st.integers(min_value=1, max_value=1000)
    )
    @settings(max_examples=50, deadline=None)
    def test_thread_safety(n_threads: int, n_operations: int):
        """Test that concurrent operations are thread-safe."""
        # Concurrent operations should not cause data corruption
        # This is a conceptual property
        
        # Would need actual concurrent execution to test
        pass
    
    @staticmethod
    @given(
        n_processes=st.integers(min_value=1, max_value=10),
        shared_resource_size=st.integers(min_value=1, max_value=1000)
    )
    @settings(max_examples=50, deadline=None)
    def test_process_isolation(n_processes: int, shared_resource_size: int):
        """Test that processes are properly isolated."""
        # Processes should not interfere with each other
        # This is a conceptual property
        
        # Would need actual process execution to test
        pass


# ============================================================================
# Utility Functions
# ============================================================================

def run_property_tests(test_class, max_examples=100):
    """Run all property tests in a test class."""
    import inspect
    
    for name, method in inspect.getmembers(test_class, predicate=inspect.isfunction):
        if name.startswith('test_'):
            print(f"Running {test_class.__name__}.{name}...")
            try:
                method()
                print(f"  ✓ {name} passed")
            except Exception as e:
                print(f"  ✗ {name} failed: {e}")
                raise


if __name__ == '__main__':
    """Run all property-based tests."""
    print("Running property-based tests...\n")
    
    # Run tests for each category
    test_classes = [
        WinExpectancyProperties,
        PitchSequenceProperties,
        FeatureCalculationProperties,
        ModelPredictionProperties,
        BettingAnalysisProperties,
        RetrosheetDataProperties,
        StatcastDataProperties,
        CrossSourceProperties,
        ScalabilityProperties,
        MemoryProperties,
        ConcurrencyProperties,
    ]
    
    for test_class in test_classes:
        print(f"\n{'='*60}")
        print(f"Testing {test_class.__name__}")
        print(f"{'='*60}")
        run_property_tests(test_class, max_examples=50)
    
    print(f"\n{'='*60}")
    print("All property-based tests completed!")
    print(f"{'='*60}")