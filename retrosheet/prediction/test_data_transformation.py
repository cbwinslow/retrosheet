#!/usr/bin/env python3
"""
Unit tests for data transformation logic.

Tests data transformation and normalization functions.
"""

from __future__ import annotations

import pytest
import pandas as pd
import numpy as np
from typing import Any
from sqlalchemy import create_engine, text

from train_pa_outcome_distribution import database_url


class TestDataNormalization:
    """Test data normalization functions."""
    
    @pytest.fixture
    def db_engine(self):
        """Create database engine for testing."""
        return create_engine(database_url())
    
    def test_game_id_format(self, db_engine):
        """Test that game IDs follow the expected format."""
        query = text("""
            SELECT game_id
            FROM core.games
            LIMIT 100
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Game IDs should follow pattern: TEAMYYYYMMDD (e.g., WAS201910260)
        for game_id in df['game_id']:
            assert len(game_id) == 12, f"Game ID {game_id} should be 12 characters"
            assert game_id[3:7].isdigit(), f"Game ID {game_id} should have year in positions 3-7"
            assert game_id[7:9].isdigit(), f"Game ID {game_id} should have month in positions 7-9"
            assert game_id[9:11].isdigit(), f"Game ID {game_id} should have day in positions 9-11"
    
    def test_team_id_format(self, db_engine):
        """Test that team IDs follow the expected format."""
        query = text("""
            SELECT DISTINCT home_team_id, away_team_id
            FROM core.games
            LIMIT 100
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Team IDs should be 3-letter uppercase codes
        all_teams = pd.concat([df['home_team_id'], df['away_team_id']]).unique()
        for team_id in all_teams:
            assert len(team_id) == 3, f"Team ID {team_id} should be 3 characters"
            assert team_id.isupper(), f"Team ID {team_id} should be uppercase"
            assert team_id.isalpha(), f"Team ID {team_id} should be alphabetic"
    
    def test_season_range(self, db_engine):
        """Test that season values are within expected range."""
        query = text("""
            SELECT MIN(season) AS min_season, MAX(season) AS max_season
            FROM core.games
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Season should be between 1900 and current year
        assert df['min_season'].iloc[0] >= 1900
        assert df['max_season'].iloc[0] <= 2100
    
    def test_score_consistency(self, db_engine):
        """Test that scores are non-negative and reasonable."""
        query = text("""
            SELECT home_score, away_score
            FROM core.games
            LIMIT 1000
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Scores should be non-negative
        assert (df['home_score'] >= 0).all()
        assert (df['away_score'] >= 0).all()
        
        # Scores should be reasonable (less than 50 in a single game)
        assert (df['home_score'] < 50).all()
        assert (df['away_score'] < 50).all()


class TestEventTransformation:
    """Test event data transformation."""
    
    @pytest.fixture
    def db_engine(self):
        """Create database engine for testing."""
        return create_engine(database_url())
    
    def test_outcome_class_distribution(self, db_engine):
        """Test that outcome classes are distributed reasonably."""
        query = text("""
            SELECT outcome_class, COUNT(*) AS count
            FROM core.events
            GROUP BY outcome_class
            ORDER BY count DESC
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Should have multiple outcome classes
        assert len(df) > 5
        
        # No single outcome should dominate completely (> 90%)
        max_proportion = df['count'].max() / df['count'].sum()
        assert max_proportion < 0.9
    
    def test_inning_progression(self, db_engine):
        """Test that inning values are reasonable."""
        query = text("""
            SELECT inning, COUNT(*) AS count
            FROM core.events
            GROUP BY inning
            ORDER BY inning
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Inning should be between 1 and 20
        assert df['inning'].min() >= 1
        assert df['inning'].max() <= 20
        
        # Should have data for multiple innings
        assert len(df) > 5
    
    def test_base_occupancy_encoding(self, db_engine):
        """Test that base occupancy is properly encoded."""
        query = text("""
            SELECT start_bases
            FROM core.events
            WHERE start_bases IS NOT NULL
            LIMIT 1000
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Bases should be encoded as bitmask (0-7)
        assert df['start_bases'].min() >= 0
        assert df['start_bases'].max() <= 7
        
        # Should have variety of base states
        assert df['start_bases'].nunique() > 3


class TestPlateAppearanceTransformation:
    """Test plate appearance data transformation."""
    
    @pytest.fixture
    def db_engine(self):
        """Create database engine for testing."""
        return create_engine(database_url())
    
    def test_pa_to_game_relationship(self, db_engine):
        """Test that plate appearances are properly linked to games."""
        query = text("""
            SELECT COUNT(DISTINCT pa.game_id) AS unique_games,
                   COUNT(DISTINCT pa.plate_appearance_id) AS total_pas
            FROM core.plate_appearances pa
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # Should have multiple games
        assert df['unique_games'].iloc[0] > 10
        
        # Should have more PAs than games
        assert df['total_pas'].iloc[0] > df['unique_games'].iloc[0]
    
    def test_batter_pitcher_relationship(self, db_engine):
        """Test that PAs have valid batter and pitcher IDs."""
        query = text("""
            SELECT COUNT(*) FILTER (WHERE batter_id IS NULL) AS null_batter,
                   COUNT(*) FILTER (WHERE pitcher_id IS NULL) AS null_pitcher
            FROM core.plate_appearances
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # All PAs should have batter and pitcher
        assert df['null_batter'].iloc[0] == 0
        assert df['null_pitcher'].iloc[0] == 0
    
    def test_pa_sequence_consistency(self, db_engine):
        """Test that PA sequence numbers are consistent within games."""
        query = text("""
            SELECT game_id, COUNT(*) AS pa_count,
                   COUNT(DISTINCT pa_sequence) AS unique_sequences
            FROM core.plate_appearances
            WHERE pa_sequence IS NOT NULL
            GROUP BY game_id
            LIMIT 100
        """)
        
        df = pd.read_sql(query, db_engine)
        
        # PA count should equal unique sequence count (no duplicates)
        assert (df['pa_count'] == df['unique_sequences']).all()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
