#!/usr/bin/env python3
"""
Integration tests for prediction serving.

Tests the full prediction pipeline with real warehouse data.
"""

from __future__ import annotations

import pytest
import pandas as pd
import numpy as np
from typing import Any
from sqlalchemy import create_engine, text

from train_pa_outcome_distribution import database_url
from predict_pa_outcome_distribution import predict_pa_outcome_distribution


class TestPredictionIntegration:
    """Integration tests for prediction serving."""
    
    @pytest.fixture
    def db_engine(self):
        """Create database engine for testing."""
        return create_engine(database_url())
    
    def test_predict_historical_pa(self, db_engine):
        """Test prediction for a historical plate appearance."""
        # Get a sample plate appearance ID
        query = text("""
            SELECT plate_appearance_id, game_id
            FROM core.plate_appearances
            LIMIT 1
        """)
        
        df = pd.read_sql(query, db_engine)
        pa_id = df['plate_appearance_id'].iloc[0]
        game_id = df['game_id'].iloc[0]
        
        # Make prediction
        result = predict_pa_outcome_distribution(
            game_id=game_id,
            plate_appearance_id=pa_id,
            apply_calibration=False,  # Test raw prediction first
        )
        
        # Check result structure
        assert 'class_probabilities' in result
        assert 'derived_probabilities' in result
        assert 'model_metadata' in result
        assert 'state_snapshot' in result
        assert 'missing_features' in result
        
        # Check probabilities sum to approximately 1
        probs = result['class_probabilities']
        total_prob = sum(probs.values())
        assert abs(total_prob - 1.0) < 0.01
    
    def test_predict_with_calibration(self, db_engine):
        """Test prediction with calibration applied."""
        query = text("""
            SELECT plate_appearance_id, game_id
            FROM core.plate_appearances
            LIMIT 1
        """)
        
        df = pd.read_sql(query, db_engine)
        pa_id = df['plate_appearance_id'].iloc[0]
        game_id = df['game_id'].iloc[0]
        
        # Make prediction with calibration
        result = predict_pa_outcome_distribution(
            game_id=game_id,
            plate_appearance_id=pa_id,
            apply_calibration=True,
        )
        
        # Check result structure
        assert 'class_probabilities' in result
        assert 'derived_probabilities' in result
        
        # Check probabilities are still valid
        probs = result['class_probabilities']
        total_prob = sum(probs.values())
        assert abs(total_prob - 1.0) < 0.01
        
        # All probabilities should be non-negative
        assert all(p >= 0 for p in probs.values())
    
    def test_predict_multiple_pas(self, db_engine):
        """Test predictions for multiple plate appearances."""
        query = text("""
            SELECT plate_appearance_id, game_id
            FROM core.plate_appearances
            LIMIT 10
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Make predictions for all PAs
        results = []
        for _, row in df.iterrows():
            result = predict_pa_outcome_distribution(
                game_id=row['game_id'],
                plate_appearance_id=row['plate_appearance_id'],
                apply_calibration=False,
            )
            results.append(result)
        
        # All predictions should succeed
        assert len(results) == 10
        
        # All should have valid probabilities
        for result in results:
            probs = result['class_probabilities']
            total_prob = sum(probs.values())
            assert abs(total_prob - 1.0) < 0.01
    
    def test_model_metadata_consistency(self, db_engine):
        """Test that model metadata is consistent across predictions."""
        query = text("""
            SELECT plate_appearance_id, game_id
            FROM core.plate_appearances
            LIMIT 2
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Make two predictions
        result1 = predict_pa_outcome_distribution(
            game_id=df['game_id'].iloc[0],
            plate_appearance_id=df['plate_appearance_id'].iloc[0],
            apply_calibration=False,
        )
        
        result2 = predict_pa_outcome_distribution(
            game_id=df['game_id'].iloc[1],
            plate_appearance_id=df['plate_appearance_id'].iloc[1],
            apply_calibration=False,
        )
        
        # Model ID should be the same
        assert result1['model_metadata']['model_id'] == result2['model_metadata']['model_id']
        assert result1['model_metadata']['model_name'] == result2['model_metadata']['model_name']
    
    def test_state_snapshot_completeness(self, db_engine):
        """Test that state snapshot includes expected fields."""
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
        
        snapshot = result['state_snapshot']
        
        # Check for expected state fields
        expected_fields = [
            'inning',
            'is_bottom_inning',
            'outs_before',
            'start_bases',
            'balls',
            'strikes',
            'home_score_diff',
        ]
        
        for field in expected_fields:
            assert field in snapshot, f"Expected field {field} in state snapshot"


class TestFeatureExtractionIntegration:
    """Integration tests for feature extraction."""
    
    @pytest.fixture
    def db_engine(self):
        """Create database engine for testing."""
        return create_engine(database_url())
    
    def test_feature_query_performance(self, db_engine):
        """Test that feature queries complete in reasonable time."""
        import time
        
        query = text("""
            SELECT * FROM features.plate_appearance_advanced_examples
            WHERE plate_appearance_id IN (
                SELECT plate_appearance_id FROM core.plate_appearances LIMIT 100
            )
        """)
        
        start = time.time()
        df = pd.read_sql(query, db_engine)
        elapsed = time.time() - start
        
        # Should complete in less than 5 seconds for 100 rows
        assert elapsed < 5.0
        assert len(df) > 0
    
    def test_feature_consistency_with_core(self, db_engine):
        """Test that feature data is consistent with core data."""
        query = text("""
            SELECT 
                f.plate_appearance_id,
                f.inning AS feature_inning,
                e.inning AS event_inning,
                f.outs_before AS feature_outs,
                e.outs_before AS event_outs
            FROM features.plate_appearance_advanced_examples f
            JOIN core.events e ON f.plate_appearance_id = e.plate_appearance_id
            LIMIT 100
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Feature data should match core data
        assert (df['feature_inning'] == df['event_inning']).all()
        assert (df['feature_outs'] == df['event_outs']).all()


class TestEndToEndPipeline:
    """End-to-end pipeline tests."""
    
    @pytest.fixture
    def db_engine(self):
        """Create database engine for testing."""
        return create_engine(database_url())
    
    def test_game_to_prediction_pipeline(self, db_engine):
        """Test complete pipeline from game lookup to prediction."""
        # Get a sample game
        query = text("""
            SELECT game_id
            FROM core.games
            LIMIT 1
        """)
        
        df = pd.read_sql(query, db_engine)
        game_id = df['game_id'].iloc[0]
        
        # Get plate appearances for this game
        query = text("""
            SELECT plate_appearance_id
            FROM core.plate_appearances
            WHERE game_id = :game_id
            LIMIT 5
        """)
        
        df = pd.read_sql(query, db_engine, params={'game_id': game_id})
        
        # Make predictions for all PAs
        results = []
        for pa_id in df['plate_appearance_id']:
            result = predict_pa_outcome_distribution(
                game_id=game_id,
                plate_appearance_id=pa_id,
                apply_calibration=False,
            )
            results.append(result)
        
        # All predictions should succeed
        assert len(results) == 5
        
        # All should have valid structure
        for result in results:
            assert 'class_probabilities' in result
            assert 'derived_probabilities' in result
            assert result['model_metadata']['game_id'] == game_id


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
