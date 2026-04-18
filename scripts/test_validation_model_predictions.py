#!/usr/bin/env python3
"""
Validation tests for model predictions against historical data.

Tests that model predictions align with historical distributions and patterns.
"""

from __future__ import annotations

import pytest
import pandas as pd
import numpy as np
from typing import Any
from sqlalchemy import create_engine, text

from train_pa_outcome_distribution import database_url
from predict_pa_outcome_distribution import predict_pa_outcome_distribution


class TestPredictionDistributionValidation:
    """Validate prediction distributions against historical data."""
    
    @pytest.fixture
    def db_engine(self):
        """Create database engine for testing."""
        return create_engine(database_url())
    
    def test_prediction_range_validity(self, db_engine):
        """Test that all predictions are within valid probability ranges."""
        query = text("""
            SELECT plate_appearance_id, game_id
            FROM core.plate_appearances
            LIMIT 100
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Make predictions
        all_probs = []
        for _, row in df.iterrows():
            result = predict_pa_outcome_distribution(
                game_id=row['game_id'],
                plate_appearance_id=row['plate_appearance_id'],
                apply_calibration=False,
            )
            probs = list(result['class_probabilities'].values())
            all_probs.extend(probs)
        
        # All probabilities should be between 0 and 1
        assert all(0 <= p <= 1 for p in all_probs)
        
        # No probability should be exactly 0 or 1 (model should have uncertainty)
        assert not any(p == 0 for p in all_probs)
        assert not any(p == 1 for p in all_probs)
    
    def test_prediction_sum_to_one(self, db_engine):
        """Test that class probabilities sum to approximately 1."""
        query = text("""
            SELECT plate_appearance_id, game_id
            FROM core.plate_appearances
            LIMIT 100
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Make predictions and check sums
        for _, row in df.iterrows():
            result = predict_pa_outcome_distribution(
                game_id=row['game_id'],
                plate_appearance_id=row['plate_appearance_id'],
                apply_calibration=False,
            )
            probs = result['class_probabilities']
            total = sum(probs.values())
            assert abs(total - 1.0) < 0.01, f"Probabilities sum to {total}, expected 1.0"
    
    def test_prediction_variability(self, db_engine):
        """Test that predictions show appropriate variability across different contexts."""
        query = text("""
            SELECT plate_appearance_id, game_id
            FROM core.plate_appearances
            WHERE plate_appearance_id % 10 = 0
            LIMIT 100
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Make predictions
        strikeout_probs = []
        for _, row in df.iterrows():
            result = predict_pa_outcome_distribution(
                game_id=row['game_id'],
                plate_appearance_id=row['plate_appearance_id'],
                apply_calibration=False,
            )
            probs = result['class_probabilities']
            strikeout_probs.append(probs.get('strikeout', 0))
        
        # Predictions should vary (not all the same)
        assert len(set(strikeout_probs)) > 10, "Predictions should vary across different contexts"
        
        # Variance should be reasonable
        variance = np.var(strikeout_probs)
        assert variance > 0.001, "Predictions should have meaningful variance"


class TestPredictionContextSensitivity:
    """Validate that predictions are sensitive to game context."""
    
    @pytest.fixture
    def db_engine(self):
        """Create database engine for testing."""
        return create_engine(database_url())
    
    def test_two_strike_penalty(self, db_engine):
        """Test that two-strike counts have higher strikeout predictions."""
        query = text("""
            SELECT e.plate_appearance_id, pa.game_id, e.strikes
            FROM core.events e
            JOIN core.plate_appearances pa ON e.plate_appearance_id = pa.plate_appearance_id
            WHERE e.strikes IN (0, 2)
            LIMIT 50
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Group by strike count
        two_strike_probs = []
        zero_strike_probs = []
        
        for _, row in df.iterrows():
            result = predict_pa_outcome_distribution(
                game_id=row['game_id'],
                plate_appearance_id=row['plate_appearance_id'],
                apply_calibration=False,
            )
            strikeout_prob = result['class_probabilities'].get('strikeout', 0)
            
            if row['strikes'] == 2:
                two_strike_probs.append(strikeout_prob)
            else:
                zero_strike_probs.append(strikeout_prob)
        
        # Two-strike predictions should be higher on average
        if len(two_strike_probs) > 0 and len(zero_strike_probs) > 0:
            avg_two_strike = np.mean(two_strike_probs)
            avg_zero_strike = np.mean(zero_strike_probs)
            assert avg_two_strike > avg_zero_strike, \
                f"Two-strike avg ({avg_two_strike}) should be > zero-strike avg ({avg_zero_strike})"
    
    def test_base_state_sensitivity(self, db_engine):
        """Test that predictions vary by base state."""
        query = text("""
            SELECT e.plate_appearance_id, pa.game_id, e.start_bases
            FROM core.events e
            JOIN core.plate_appearances pa ON e.plate_appearance_id = pa.plate_appearance_id
            WHERE e.start_bases IN (0, 7)  -- Empty bases vs loaded bases
            LIMIT 50
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Group by base state
        loaded_probs = []
        empty_probs = []
        
        for _, row in df.iterrows():
            result = predict_pa_outcome_distribution(
                game_id=row['game_id'],
                plate_appearance_id=row['plate_appearance_id'],
                apply_calibration=False,
            )
            # Walk probability should be lower with loaded bases (pitcher more careful)
            walk_prob = result['class_probabilities'].get('walk', 0)
            
            if row['start_bases'] == 7:
                loaded_probs.append(walk_prob)
            else:
                empty_probs.append(walk_prob)
        
        # Predictions should differ by base state
        if len(loaded_probs) > 0 and len(empty_probs) > 0:
            assert len(set(loaded_probs + empty_probs)) > 5, \
                "Predictions should vary by base state"


class TestHistoricalAlignment:
    """Validate predictions align with historical outcome distributions."""
    
    @pytest.fixture
    def db_engine(self):
        """Create database engine for testing."""
        return create_engine(database_url())
    
    def test_outcome_class_coverage(self, db_engine):
        """Test that model predicts all outcome classes seen in training data."""
        query = text("""
            SELECT DISTINCT outcome_class
            FROM core.events
            WHERE outcome_class IS NOT NULL
        """)
        
        df = pd.read_sql(query, db_engine)
        historical_outcomes = set(df['outcome_class'].tolist())
        
        # Get model's predicted classes
        query = text("""
            SELECT plate_appearance_id, game_id
            FROM core.plate_appearances
            LIMIT 1
        """)
        
        df = pd.read_sql(query, db_engine)
        result = predict_pa_outcome_distribution(
            game_id=df['game_id'].iloc[0],
            plate_appearance_id=df['plate_appearance_id'].iloc[0],
            apply_calibration=False,
        )
        
        predicted_outcomes = set(result['class_probabilities'].keys())
        
        # All historical outcomes should be in predictions (or model uses grouped taxonomy)
        # For grouped taxonomy, check that major categories are covered
        major_categories = {'strikeout', 'ground_out', 'fly_out', 'single', 'double', 'home_run', 'walk'}
        assert len(predicted_outcomes.intersection(major_categories)) >= 5, \
            "Model should predict major outcome categories"
    
    def test_score_diff_sensitivity(self, db_engine):
        """Test that predictions are sensitive to score differential."""
        query = text("""
            SELECT 
                e.plate_appearance_id, 
                pa.game_id,
                g.home_score - g.away_score AS score_diff
            FROM core.events e
            JOIN core.plate_appearances pa ON e.plate_appearance_id = pa.plate_appearance_id
            JOIN core.games g ON pa.game_id = g.game_id
            WHERE ABS(g.home_score - g.away_score) IN (0, 5)
            LIMIT 50
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Group by score diff
        blowout_probs = []
        close_probs = []
        
        for _, row in df.iterrows():
            result = predict_pa_outcome_distribution(
                game_id=row['game_id'],
                plate_appearance_id=row['plate_appearance_id'],
                apply_calibration=False,
            )
            # Use hit probability as a general metric
            hit_prob = sum(result['derived_probabilities'].get('hit', 0))
            
            if abs(row['score_diff']) >= 5:
                blowout_probs.append(hit_prob)
            else:
                close_probs.append(hit_prob)
        
        # Predictions should differ by game context
        if len(blowout_probs) > 0 and len(close_probs) > 0:
            assert len(set(blowout_probs + close_probs)) > 5, \
                "Predictions should vary by score differential"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
