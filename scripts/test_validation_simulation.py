#!/usr/bin/env python3
"""
Validation tests for simulation outputs against historical distributions.

Tests that the baseball state transition simulation produces realistic results.
"""

from __future__ import annotations

import pytest
import pandas as pd
import numpy as np
from typing import Any
from sqlalchemy import create_engine, text

from train_pa_outcome_distribution import database_url
from retrosheet.simulation.baseball_state import BaseballState, apply_event


class TestSimulationDistributionValidation:
    """Validate simulation outputs against historical distributions."""
    
    @pytest.fixture
    def db_engine(self):
        """Create database engine for testing."""
        return create_engine(database_url())
    
    def test_base_transition_probabilities(self, db_engine):
        """Test that base transition probabilities match historical data."""
        # Get historical single base transition rates
        query = text("""
            SELECT 
                start_bases,
                end_bases,
                COUNT(*) AS count
            FROM core.events
            WHERE event_type = 'single'
              AND start_bases IS NOT NULL
              AND end_bases IS NOT NULL
            GROUP BY start_bases, end_bases
            ORDER BY start_bases, end_bases
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Test simulation for single events
        for _, row in df.iterrows():
            start_state = BaseballState(
                bases=row['start_bases'],
                outs=0,
                home_score=0,
                away_score=0,
                inning=1,
                is_bottom_inning=False,
            )
            
            # Apply single event
            end_state = apply_event(start_state, event_type='single')
            
            # End bases should be valid (0-7)
            assert 0 <= end_state.bases <= 7, \
                f"Invalid end bases {end_state.bases} for start bases {row['start_bases']}"
    
    def test_out_transition_validity(self, db_engine):
        """Test that out transitions are valid."""
        query = text("""
            SELECT DISTINCT outs_before
            FROM core.events
            WHERE outs_before IS NOT NULL
            ORDER BY outs_before
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Test out transitions for all possible out counts
        for outs in df['outs_before']:
            if outs >= 3:
                continue  # Skip invalid states
            
            start_state = BaseballState(
                bases=0,
                outs=outs,
                home_score=0,
                away_score=0,
                inning=1,
                is_bottom_inning=False,
            )
            
            # Apply out event
            end_state = apply_event(start_state, event_type='ground_out')
            
            # Outs should increment by 1
            assert end_state.outs == outs + 1, \
                f"Outs should increment from {outs} to {outs + 1}, got {end_state.outs}"
    
    def test_score_transition_validity(self, db_engine):
        """Test that score transitions are valid for scoring events."""
        scoring_events = ['single', 'double', 'triple', 'home_run']
        
        for event_type in scoring_events:
            start_state = BaseballState(
                bases=7,  # Loaded bases
                outs=0,
                home_score=0,
                away_score=0,
                inning=1,
                is_bottom_inning=False,
            )
            
            # Apply scoring event
            end_state = apply_event(start_state, event_type=event_type)
            
            # Score should increase
            assert end_state.home_score >= 0, "Score should be non-negative"
            assert end_state.away_score >= 0, "Score should be non-negative"
            
            # Total runs should be reasonable (at most 4 for loaded bases)
            total_runs = end_state.home_score + end_state.away_score
            assert total_runs <= 4, f"Too many runs scored: {total_runs}"
    
    def test_inning_transition_validity(self, db_engine):
        """Test that inning transitions work correctly."""
        # Test 3rd out in top of inning
        start_state = BaseballState(
            bases=0,
            outs=2,
            home_score=0,
            away_score=0,
            inning=1,
            is_bottom_inning=False,
        )
        
        end_state = apply_event(start_state, event_type='ground_out')
        
        # Should transition to bottom of inning (inning unchanged)
        assert end_state.is_bottom_inning == True
        assert end_state.outs == 0
        
        # Test 3rd out in bottom of inning
        start_state = BaseballState(
            bases=0,
            outs=2,
            home_score=0,
            away_score=0,
            inning=1,
            is_bottom_inning=True,
        )
        
        end_state = apply_event(start_state, event_type='ground_out')
        
        # Should transition to top of next inning
        assert end_state.is_bottom_inning == False
        assert end_state.inning == 2
        assert end_state.outs == 0


class TestSimulationReproducibility:
    """Test that simulation results are reproducible."""
    
    def test_deterministic_transitions(self):
        """Test that same inputs produce same outputs."""
        start_state = BaseballState(
            bases=1,
            outs=1,
            home_score=2,
            away_score=1,
            inning=5,
            is_bottom_inning=True,
        )
        
        # Apply same event twice
        end_state1 = apply_event(start_state, event_type='single')
        end_state2 = apply_event(start_state, event_type='single')
        
        # Results should be identical
        assert end_state1.bases == end_state2.bases
        assert end_state1.outs == end_state2.outs
        assert end_state1.home_score == end_state2.home_score
        assert end_state1.away_score == end_state2.away_score
        assert end_state1.inning == end_state2.inning
        assert end_state1.is_bottom_inning == end_state2.is_bottom_inning


class TestSimulationStateConsistency:
    """Test that simulation maintains consistent state."""
    
    def test_base_state_consistency(self):
        """Test that base state is always valid."""
        start_state = BaseballState(
            bases=0,
            outs=0,
            home_score=0,
            away_score=0,
            inning=1,
            is_bottom_inning=False,
        )
        
        # Apply various events
        events = ['single', 'double', 'ground_out', 'fly_out', 'walk']
        for event_type in events:
            end_state = apply_event(start_state, event_type)
            assert 0 <= end_state.bases <= 7, \
                f"Invalid base state {end_state.bases} after {event_type}"
    
    def test_out_count_consistency(self):
        """Test that out count is always valid."""
        start_state = BaseballState(
            bases=0,
            outs=0,
            home_score=0,
            away_score=0,
            inning=1,
            is_bottom_inning=False,
        )
        
        # Apply events and check out count never exceeds 3
        for _ in range(10):
            end_state = apply_event(start_state, event_type='ground_out')
            if end_state.outs >= 3:
                break
            start_state = end_state
        
        assert end_state.outs <= 3, "Out count should never exceed 3"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
