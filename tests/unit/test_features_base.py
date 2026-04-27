"""Unit tests for features base classes.

Granular tests for FeatureStore, FeatureConfig, GameState, and FeatureResult.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-27
"""

import pytest
from datetime import date
from unittest.mock import Mock, MagicMock

from baseball.features.base import (
    FeatureStore,
    FeatureConfig,
    FeatureResult,
    GameState,
    FeatureScope,
    FeatureStatus,
)


class TestFeatureConfig:
    """Test FeatureConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = FeatureConfig()
        
        assert config.scope == FeatureScope.BOTH
        assert config.batch_size == 1000
        assert config.use_cache is True
        assert config.force_recompute is False
        assert config.parallel_workers == 4
        assert config.start_date is None
        assert config.end_date is None
        assert config.season is None
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = FeatureConfig(
            scope=FeatureScope.HISTORICAL,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            season=2023,
            batch_size=500,
            use_cache=False,
            force_recompute=True,
            parallel_workers=8,
        )
        
        assert config.scope == FeatureScope.HISTORICAL
        assert config.start_date == date(2023, 1, 1)
        assert config.end_date == date(2023, 12, 31)
        assert config.season == 2023
        assert config.batch_size == 500
        assert config.use_cache is False
        assert config.force_recompute is True
        assert config.parallel_workers == 8
    
    def test_date_validation(self):
        """Test date range validation."""
        # Valid: start before end
        config = FeatureConfig(
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )
        assert config.start_date < config.end_date
        
        # Invalid: start after end (raises ValueError in __post_init__)
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            FeatureConfig(
                start_date=date(2023, 12, 31),
                end_date=date(2023, 1, 1),
            )


class TestGameState:
    """Test GameState dataclass."""
    
    def test_default_state(self):
        """Test default game state (start of game)."""
        state = GameState(inning=1, is_top=True, outs=0)
        
        assert state.inning == 1
        assert state.is_top is True
        assert state.outs == 0
        assert state.runner_1b is False
        assert state.runner_2b is False
        assert state.runner_3b is False
        assert state.score_home == 0
        assert state.score_away == 0
    
    def test_custom_state(self):
        """Test custom game state."""
        state = GameState(
            inning=9,
            is_top=False,
            outs=2,
            runner_1b=True,
            runner_2b=True,
            runner_3b=False,
            score_home=4,
            score_away=3,
        )
        
        assert state.inning == 9
        assert state.is_top is False
        assert state.outs == 2
        assert state.runner_1b is True
        assert state.runner_2b is True
        assert state.runner_3b is False
        assert state.score_home == 4
        assert state.score_away == 3
    
    def test_base_state_encoding(self):
        """Test base state encoding (for WE/LI lookup)."""
        # Empty bases
        state = GameState(inning=1, is_top=True, outs=0, runner_1b=False, runner_2b=False, runner_3b=False)
        assert state.base_state == "000"
        
        # Runners on 1st and 3rd
        state = GameState(inning=1, is_top=True, outs=0, runner_1b=True, runner_2b=False, runner_3b=True)
        assert state.base_state == "101"
        
        # Bases loaded
        state = GameState(inning=1, is_top=True, outs=0, runner_1b=True, runner_2b=True, runner_3b=True)
        assert state.base_state == "111"
    
    def test_score_differential(self):
        """Test score differential calculation."""
        state = GameState(inning=1, is_top=True, outs=0, score_home=5, score_away=3)
        assert state.score_diff == 2
        
        state = GameState(inning=1, is_top=True, outs=0, score_home=2, score_away=7)
        assert state.score_diff == -5
        
        state = GameState(inning=1, is_top=True, outs=0, score_home=4, score_away=4)
        assert state.score_diff == 0


class TestFeatureResult:
    """Test FeatureResult dataclass."""
    
    def test_successful_result(self):
        """Test successful feature computation result."""
        result = FeatureResult(
            success=True,
            rows_computed=1000,
            duration_seconds=5.5,
        )
        
        assert result.success is True
        assert result.rows_computed == 1000
        assert result.duration_seconds == 5.5
        assert result.rows_inserted == 0  # Default
        assert len(result.errors) == 0
    
    def test_failed_result(self):
        """Test failed feature computation result."""
        result = FeatureResult(
            success=False,
            rows_computed=0,
            duration_seconds=1.0,
        )
        
        # Add error using the method
        result.add_error("Database connection failed")
        
        assert result.success is False
        assert result.rows_computed == 0
        assert len(result.errors) == 1
        assert result.errors[0] == "Database connection failed"
    
    def test_result_with_metadata(self):
        """Test result with additional metadata."""
        result = FeatureResult(
            success=True,
            rows_computed=500,
            duration_seconds=2.0,
            metadata={
                "season": 2023,
                "games_processed": 100,
                "avg_li": 1.05,
            }
        )
        
        assert result.metadata["season"] == 2023
        assert result.metadata["games_processed"] == 100
        assert result.metadata["avg_li"] == 1.05
    
    def test_add_error_method(self):
        """Test add_error method."""
        result = FeatureResult()
        
        assert result.success is False  # Default
        assert result.status.name == "PENDING"
        
        result.add_error("Test error")
        
        assert result.success is False
        assert result.status.name == "FAILED"
        assert "Test error" in result.errors
    
    def test_mark_complete_method(self):
        """Test mark_complete method."""
        result = FeatureResult(errors=["Some error"])
        
        result.mark_complete()
        
        assert result.status.name == "COMPLETE"
        assert result.success is False  # Has errors
        
        # Now test with no errors
        result2 = FeatureResult()
        result2.mark_complete()
        
        assert result2.status.name == "COMPLETE"
        assert result2.success is True  # No errors


class TestFeatureStore:
    """Test FeatureStore base class."""
    
    def _create_concrete_store(self, db_connection=None, config=None):
        """Helper to create a concrete FeatureStore implementation."""
        
        class ConcreteStore(FeatureStore):
            @property
            def feature_name(self) -> str:
                return "test_feature"
            
            @property
            def table_name(self) -> str:
                return "features.test"
            
            def compute(self, game_state):
                return 0.5
            
            def compute_batch(self, game_states):
                return [0.5] * len(game_states)
            
            def load_from_db(self, season=None):
                return 100
        
        return ConcreteStore(db_connection=db_connection, config=config)
    
    def test_initialization(self):
        """Test FeatureStore initialization."""
        mock_conn = Mock()
        config = FeatureConfig(batch_size=500)
        
        store = self._create_concrete_store(db_connection=mock_conn, config=config)
        
        assert store.db == mock_conn
        assert store.config == config
    
    def test_initialization_defaults(self):
        """Test FeatureStore initialization with defaults."""
        store = self._create_concrete_store()
        
        assert store.db is None
        assert store.config is not None
        assert store.config.batch_size == 1000  # Default
    
    def test_abstract_methods(self):
        """Test that abstract methods must be implemented."""
        
        class IncompleteStore(FeatureStore):
            pass
        
        with pytest.raises(TypeError):
            IncompleteStore()
    
    def test_concrete_implementation(self):
        """Test concrete FeatureStore implementation."""
        
        store = self._create_concrete_store()
        assert store.feature_name == "test_feature"
        assert store.table_name == "features.test"
        assert store.compute(None) == 0.5
        assert store.load_from_db() == 100
    
    def test_cache_operations(self):
        """Test cache get/set operations."""
        store = self._create_concrete_store()
        
        # Access cache through internal attribute
        store._cache[(1, 2, 3)] = 0.75
        
        # Get cache
        assert store._cache[(1, 2, 3)] == 0.75
        assert store._cache.get((9, 9, 9)) is None
    
    def test_compute_batch(self):
        """Test batch computation."""
        store = self._create_concrete_store()
        
        states = [
            GameState(inning=1, is_top=True, outs=0),
            GameState(inning=1, is_top=True, outs=1),
        ]
        
        results = store.compute_batch(states)
        
        assert len(results) == 2
        assert results[0] == 0.5
        assert results[1] == 0.5


class TestFeatureScope:
    """Test FeatureScope enum."""
    
    def test_scope_values(self):
        """Test scope enum values."""
        assert FeatureScope.HISTORICAL.value == "historical"
        assert FeatureScope.LIVE.value == "live"
        assert FeatureScope.BOTH.value == "both"


class TestFeatureStatus:
    """Test FeatureStatus enum."""
    
    def test_status_values(self):
        """Test status enum values."""
        assert FeatureStatus.PENDING.value == "pending"
        assert FeatureStatus.COMPUTING.value == "computing"
        assert FeatureStatus.COMPLETE.value == "complete"
        assert FeatureStatus.FAILED.value == "failed"
