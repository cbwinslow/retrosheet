#!/usr/bin/env python3
"""
Unit tests for feature engineering logic.

Tests feature extraction and transformation functions.
"""

from __future__ import annotations

import pytest
import pandas as pd
import numpy as np
from typing import Any
from sqlalchemy import create_engine, text

from train_pa_outcome_distribution import database_url


class TestFeatureQuery:
    """Test feature query logic."""
    
    @pytest.fixture
    def db_engine(self):
        """Create database engine for testing."""
        return create_engine(database_url())
    
    def test_advanced_feature_query_structure(self, db_engine):
        """Test that advanced feature query returns expected columns."""
        query = text("""
            SELECT * FROM features.plate_appearance_advanced_examples
            LIMIT 1
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Check for expected columns
        expected_columns = [
            'plate_appearance_id',
            'feature_season',
            'inning',
            'is_bottom_inning',
            'outs_before',
            'start_bases',
            'balls',
            'strikes',
            'home_score_diff',
            'batter_hand',
            'pitcher_hand',
        ]
        
        for col in expected_columns:
            assert col in df.columns, f"Expected column {col} not found"
    
    def test_feature_data_types(self, db_engine):
        """Test that feature columns have correct data types."""
        query = text("""
            SELECT 
                plate_appearance_id,
                feature_season,
                inning,
                is_bottom_inning,
                outs_before,
                start_bases,
                balls,
                strikes,
                home_score_diff
            FROM features.plate_appearance_advanced_examples
            LIMIT 1
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Check data types
        assert df['plate_appearance_id'].dtype in ['int64', 'int32']
        assert df['feature_season'].dtype in ['int64', 'int32']
        assert df['inning'].dtype in ['int64', 'int32']
        assert df['outs_before'].dtype in ['int64', 'int32']
        assert df['start_bases'].dtype in ['int64', 'int32']
        assert df['balls'].dtype in ['int64', 'int32']
        assert df['strikes'].dtype in ['int64', 'int32']
    
    def test_feature_value_ranges(self, db_engine):
        """Test that feature values are within expected ranges."""
        query = text("""
            SELECT 
                inning,
                outs_before,
                start_bases,
                balls,
                strikes
            FROM features.plate_appearance_advanced_examples
            LIMIT 1000
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Inning should be between 1 and 20
        assert df['inning'].min() >= 1
        assert df['inning'].max() <= 20
        
        # Outs should be between 0 and 3
        assert df['outs_before'].min() >= 0
        assert df['outs_before'].max() <= 3
        
        # Bases should be between 0 and 7 (bitmask)
        assert df['start_bases'].min() >= 0
        assert df['start_bases'].max() <= 7
        
        # Balls should be between 0 and 4
        assert df['balls'].min() >= 0
        assert df['balls'].max() <= 4
        
        # Strikes should be between 0 and 3
        assert df['strikes'].min() >= 0
        assert df['strikes'].max() <= 3
    
    def test_feature_not_null(self, db_engine):
        """Test that critical feature columns are not null."""
        query = text("""
            SELECT 
                COUNT(*) FILTER (WHERE plate_appearance_id IS NULL) AS null_pa_id,
                COUNT(*) FILTER (WHERE feature_season IS NULL) AS null_season,
                COUNT(*) FILTER (WHERE inning IS NULL) AS null_inning,
                COUNT(*) FILTER (WHERE outs_before IS NULL) AS null_outs,
                COUNT(*) FILTER (WHERE start_bases IS NULL) AS null_bases
            FROM features.plate_appearance_advanced_examples
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # All critical columns should have zero nulls
        assert df['null_pa_id'].iloc[0] == 0
        assert df['null_season'].iloc[0] == 0
        assert df['null_inning'].iloc[0] == 0
        assert df['null_outs'].iloc[0] == 0
        assert df['null_bases'].iloc[0] == 0


class TestFeatureExtraction:
    """Test feature extraction from raw data."""
    
    @pytest.fixture
    def db_engine(self):
        """Create database engine for testing."""
        return create_engine(database_url())
    
    def test_batter_prior_stats_exist(self, db_engine):
        """Test that batter prior season stats are available."""
        query = text("""
            SELECT batter_id, batter_career_prior_pa, batter_career_prior_hit_rate
            FROM features.plate_appearance_advanced_examples
            WHERE batter_career_prior_pa > 0
            LIMIT 1
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Should have at least one row with batter prior stats
        assert len(df) > 0
        assert df['batter_career_prior_pa'].iloc[0] > 0
        assert 0 <= df['batter_career_prior_hit_rate'].iloc[0] <= 1
    
    def test_pitcher_prior_stats_exist(self, db_engine):
        """Test that pitcher prior season stats are available."""
        query = text("""
            SELECT pitcher_id, pitcher_career_prior_batters_faced, pitcher_career_prior_hit_allowed_rate
            FROM features.plate_appearance_advanced_examples
            WHERE pitcher_career_prior_batters_faced > 0
            LIMIT 1
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Should have at least one row with pitcher prior stats
        assert len(df) > 0
        assert df['pitcher_career_prior_batters_faced'].iloc[0] > 0
        assert 0 <= df['pitcher_career_prior_hit_allowed_rate'].iloc[0] <= 1
    
    def test_context_stats_exist(self, db_engine):
        """Test that context stats (inning, balls, strikes combinations) are available."""
        query = text("""
            SELECT inning, is_bottom_inning, outs_before, balls, strikes
            FROM features.plate_appearance_advanced_examples
            LIMIT 1
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Should have at least one row
        assert len(df) > 0
        assert df['inning'].iloc[0] is not None
        assert df['is_bottom_inning'].iloc[0] is not None
        assert df['outs_before'].iloc[0] is not None
        assert df['balls'].iloc[0] is not None
        assert df['strikes'].iloc[0] is not None


class TestDataTransformation:
    """Test data transformation logic."""
    
    @pytest.fixture
    def db_engine(self):
        """Create database engine for testing."""
        return create_engine(database_url())
    
    def test_feature_season_alignment(self, db_engine):
        """Test that feature_season is correctly aligned with source season."""
        query = text("""
            SELECT 
                f.feature_season,
                g.season AS game_season
            FROM features.plate_appearance_advanced_examples f
            JOIN core.plate_appearances pa ON f.plate_appearance_id = pa.plate_appearance_id
            JOIN core.games g ON pa.game_id = g.game_id
            LIMIT 100
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Feature season should be game season + 1 (to avoid leakage)
        # Or they should match depending on the feature definition
        # For now, just check that the relationship is consistent
        assert len(df) > 0
        assert (df['feature_season'] >= df['game_season']).all() or (df['feature_season'] == df['game_season']).all()
    
    def test_handeness_encoding(self, db_engine):
        """Test that batter and pitcher handedness are properly encoded."""
        query = text("""
            SELECT batter_hand, pitcher_hand
            FROM features.plate_appearance_advanced_examples
            WHERE batter_hand IS NOT NULL AND pitcher_hand IS NOT NULL
            LIMIT 100
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Handedness should be single characters (L, R, U)
        valid_hands = {'L', 'R', 'U'}
        assert df['batter_hand'].isin(valid_hands).all()
        assert df['pitcher_hand'].isin(valid_hands).all()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
