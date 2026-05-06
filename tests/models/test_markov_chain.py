"""
Comprehensive test suite for Markov Chain Prediction Models (#160)
Tests transition matrix, state analysis, and chain model functionality.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch
from datetime import datetime

from baseball.models.markov.chain_model import MarkovChainModel, MarkovConfig, TrainingResult
from baseball.models.markov.transition_matrix import TransitionMatrix
from baseball.models.markov.state_analyzer import StateAnalyzer, StateAnalysis


class TestMarkovConfig:
    """Test Markov configuration dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = MarkovConfig()
        
        assert config.order == 1
        assert config.include_count_state is True
        assert config.include_pitcher_specific is True
        assert config.include_batter_specific is True
        assert config.smoothing_factor == 0.1
        assert config.min_transitions == 5
        assert config.use_weighted_transitions is True
        assert config.recency_weight == 0.1
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = MarkovConfig(
            order=2,
            include_count_state=False,
            smoothing_factor=0.05,
            min_transitions=10
        )
        
        assert config.order == 2
        assert config.include_count_state is False
        assert config.smoothing_factor == 0.05
        assert config.min_transitions == 10


class TestTransitionMatrix:
    """Test transition matrix functionality."""
    
    @pytest.fixture
    def matrix(self):
        """Create transition matrix for testing."""
        return TransitionMatrix()
    
    @pytest.fixture
    def sample_transitions(self):
        """Create sample transition data."""
        return [
            ('FF', 'FT'), ('FT', 'SL'), ('SL', 'FF'), ('FF', 'CH'),
            ('CH', 'FF'), ('FF', 'FT'), ('FT', 'FT'), ('FT', 'SL'),
            ('SL', 'CU'), ('CU', 'FF'), ('FF', 'FF'), ('FF', 'SL')
        ]
    
    def test_matrix_initialization(self, matrix):
        """Test transition matrix initialization."""
        assert matrix.order == 1
        assert matrix.smoothing_factor == 0.1
        assert matrix.min_transitions == 5
        assert len(matrix.transitions) == 0
    
    def test_add_transitions(self, matrix, sample_transitions):
        """Test adding transitions to matrix."""
        for from_state, to_state in sample_transitions:
            matrix.add_transition(from_state, to_state)
        
        assert len(matrix.transitions) == len(sample_transitions)
        assert 'FF' in matrix.transition_counts
        assert 'FT' in matrix.transition_counts
    
    def test_transition_probabilities(self, matrix, sample_transitions):
        """Test transition probability calculation."""
        for from_state, to_state in sample_transitions:
            matrix.add_transition(from_state, to_state)
        
        probabilities = matrix.get_transition_probabilities('FF')
        
        assert isinstance(probabilities, dict)
        assert sum(probabilities.values()) == pytest.approx(1.0, rel=1e-10)
        assert 'FT' in probabilities
        assert 'CH' in probabilities
        assert 'SL' in probabilities
    
    def test_smoothing(self, matrix):
        """Test Laplace smoothing for unseen transitions."""
        # Add only FF -> FT transitions
        for _ in range(10):
            matrix.add_transition('FF', 'FT')
        
        probabilities = matrix.get_transition_probabilities('FF')
        
        # Should have some probability for unseen states due to smoothing
        assert len(probabilities) > 1
        assert sum(probabilities.values()) == pytest.approx(1.0, rel=1e-10)
    
    def test_min_transitions_filtering(self, matrix):
        """Test filtering by minimum transitions."""
        # Add few transitions below threshold
        for _ in range(3):
            matrix.add_transition('FF', 'FT')
        
        probabilities = matrix.get_transition_probabilities('FF')
        
        # Should return smoothed probabilities due to insufficient transitions
        assert isinstance(probabilities, dict)
    
    def test_weighted_transitions(self, matrix):
        """Test weighted transition calculation."""
        matrix.use_weighted_transitions = True
        matrix.recency_weight = 0.2
        
        # Add transitions with timestamps
        base_time = datetime.now()
        for i, (from_state, to_state) in enumerate([('FF', 'FT')] * 5):
            timestamp = base_time.timestamp() + i * 3600  # 1 hour apart
            matrix.add_transition(from_state, to_state, timestamp)
        
        probabilities = matrix.get_transition_probabilities('FF')
        
        assert isinstance(probabilities, dict)
        assert 'FT' in probabilities


class TestStateAnalyzer:
    """Test state analysis functionality."""
    
    @pytest.fixture
    def analyzer(self):
        """Create state analyzer for testing."""
        return StateAnalyzer()
    
    @pytest.fixture
    def sample_pitches(self):
        """Create sample pitch data."""
        return pd.DataFrame({
            'pitch_type': ['FF', 'FT', 'SL', 'FF', 'CH', 'FF', 'FT', 'SL'],
            'balls': [0, 1, 1, 2, 2, 3, 3, 4],
            'strikes': [0, 0, 1, 1, 2, 2, 2, 3],
            'pitcher_id': ['P1'] * 8,
            'batter_id': ['B1'] * 8,
            'game_date': ['2024-01-01'] * 8
        })
    
    def test_analyzer_initialization(self, analyzer):
        """Test state analyzer initialization."""
        assert analyzer.include_count_state is True
        assert analyzer.include_pitcher_specific is True
        assert analyzer.include_batter_specific is True
    
    def test_state_representation(self, analyzer, sample_pitches):
        """Test state representation generation."""
        states = analyzer.get_states(sample_pitches)
        
        assert len(states) == len(sample_pitches)
        assert all(isinstance(state, str) for state in states)
        
        # Check count state inclusion
        if analyzer.include_count_state:
            assert any('0-0' in state for state in states)
            assert any('3-2' in state for state in states)
    
    def test_pitcher_specific_states(self, analyzer, sample_pitches):
        """Test pitcher-specific state generation."""
        analyzer.include_pitcher_specific = True
        states = analyzer.get_states(sample_pitches)
        
        assert any('P1:' in state for state in states)
    
    def test_batter_specific_states(self, analyzer, sample_pitches):
        """Test batter-specific state generation."""
        analyzer.include_batter_specific = True
        states = analyzer.get_states(sample_pitches)
        
        assert any('B1:' in state for state in states)
    
    def test_state_analysis(self, analyzer, sample_pitches):
        """Test comprehensive state analysis."""
        analysis = analyzer.analyze_states(sample_pitches)
        
        assert isinstance(analysis, StateAnalysis)
        assert len(analysis.states) == len(sample_pitches)
        assert analysis.total_pitches == len(sample_pitches)
        assert analysis.unique_states > 0
        assert analysis.unique_pitch_types > 0
    
    def test_transition_sequences(self, analyzer, sample_pitches):
        """Test transition sequence extraction."""
        sequences = analyzer.get_transition_sequences(sample_pitches)
        
        assert isinstance(sequences, list)
        assert len(sequences) > 0
        assert all(isinstance(seq, list) for seq in sequences)
        assert all(len(seq) >= 2 for seq in sequences)


class TestMarkovChainModel:
    """Test Markov chain model functionality."""
    
    @pytest.fixture
    def model(self):
        """Create Markov chain model for testing."""
        config = MarkovConfig(
            order=1,
            include_count_state=True,
            include_pitcher_specific=True,
            smoothing_factor=0.1
        )
        return MarkovChainModel(config)
    
    @pytest.fixture
    def training_data(self):
        """Create training data for model."""
        return pd.DataFrame({
            'pitch_type': ['FF', 'FT', 'SL', 'FF', 'CH', 'FF', 'FT', 'SL', 'CU', 'FF'],
            'balls': [0, 1, 1, 2, 2, 3, 3, 4, 0, 1],
            'strikes': [0, 0, 1, 1, 2, 2, 2, 3, 0, 0],
            'pitcher_id': ['P1'] * 10,
            'batter_id': ['B1'] * 10,
            'game_date': ['2024-01-01'] * 10,
            'release_speed': [95.0, 93.0, 85.0, 96.0, 82.0, 94.0, 92.0, 84.0, 78.0, 95.0],
            'zone_x': [0.0, 0.5, -0.5, 0.2, -0.2, 0.1, -0.1, 0.3, -0.3, 0.0],
            'zone_y': [2.5, 2.8, 1.5, 2.6, 1.8, 2.4, 2.7, 1.6, 2.3, 2.5]
        })
    
    def test_model_initialization(self, model):
        """Test model initialization."""
        assert isinstance(model.config, MarkovConfig)
        assert isinstance(model.transition_matrix, TransitionMatrix)
        assert isinstance(model.state_analyzer, StateAnalyzer)
        assert model.is_trained is False
    
    def test_model_training(self, model, training_data):
        """Test model training."""
        result = model.train(training_data)
        
        assert isinstance(result, TrainingResult)
        assert result.success is True
        assert result.total_pitches == len(training_data)
        assert result.unique_states > 0
        assert result.training_time > 0
        assert model.is_trained is True
    
    def test_prediction_after_training(self, model, training_data):
        """Test prediction after training."""
        model.train(training_data)
        
        # Test prediction with current state
        current_state = {'pitch_type': 'FF', 'balls': 1, 'strikes': 0, 'pitcher_id': 'P1', 'batter_id': 'B1'}
        prediction = model.predict(current_state)
        
        assert hasattr(prediction, 'probabilities')
        assert hasattr(prediction, 'predicted_class')
        assert len(prediction.probabilities) > 0
        assert sum(prediction.probabilities.values()) == pytest.approx(1.0, rel=1e-10)
    
    def test_batch_prediction(self, model, training_data):
        """Test batch prediction."""
        model.train(training_data)
        
        # Create test states
        test_states = [
            {'pitch_type': 'FF', 'balls': 1, 'strikes': 0, 'pitcher_id': 'P1', 'batter_id': 'B1'},
            {'pitch_type': 'FT', 'balls': 2, 'strikes': 1, 'pitcher_id': 'P1', 'batter_id': 'B1'}
        ]
        
        predictions = model.predict_batch(test_states)
        
        assert len(predictions) == len(test_states)
        assert all(hasattr(pred, 'probabilities') for pred in predictions)
    
    def test_unseen_state_prediction(self, model, training_data):
        """Test prediction with unseen state."""
        model.train(training_data)
        
        # Test with completely unseen state
        unseen_state = {'pitch_type': 'XX', 'balls': 0, 'strikes': 0, 'pitcher_id': 'P999', 'batter_id': 'B999'}
        prediction = model.predict(unseen_state)
        
        # Should still return prediction due to smoothing
        assert hasattr(prediction, 'probabilities')
        assert len(prediction.probabilities) > 0
    
    def test_model_serialization(self, model, training_data):
        """Test model save/load functionality."""
        # Train model
        model.train(training_data)
        
        # Save model
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False) as f:
            model_path = f.name
        
        try:
            model.save(model_path)
            assert os.path.exists(model_path)
            
            # Load model
            loaded_model = MarkovChainModel.load(model_path)
            
            # Test loaded model
            assert loaded_model.is_trained is True
            assert loaded_model.config.order == model.config.order
            
            # Test prediction with loaded model
            current_state = {'pitch_type': 'FF', 'balls': 1, 'strikes': 0, 'pitcher_id': 'P1', 'batter_id': 'B1'}
            prediction = loaded_model.predict(current_state)
            assert hasattr(prediction, 'probabilities')
            
        finally:
            if os.path.exists(model_path):
                os.unlink(model_path)
    
    def test_performance_metrics(self, model, training_data):
        """Test performance metrics calculation."""
        model.train(training_data)
        
        metrics = model.get_performance_metrics()
        
        assert hasattr(metrics, 'accuracy')
        assert hasattr(metrics, 'log_loss')
        assert hasattr(metrics, 'confusion_matrix')
        
        # Metrics should be reasonable
        assert 0 <= metrics.accuracy <= 1
        assert metrics.log_loss >= 0
    
    def test_order_2_markov_chain(self, training_data):
        """Test second-order Markov chain."""
        config = MarkovConfig(order=2)
        model = MarkovChainModel(config)
        
        result = model.train(training_data)
        
        assert result.success is True
        assert model.is_trained is True
        
        # Test prediction
        current_state = {'pitch_type': 'FF', 'balls': 1, 'strikes': 0, 'pitcher_id': 'P1', 'batter_id': 'B1'}
        prediction = model.predict(current_state)
        
        assert hasattr(prediction, 'probabilities')
    
    def test_no_count_state_config(self, training_data):
        """Test model without count state."""
        config = MarkovConfig(include_count_state=False)
        model = MarkovChainModel(config)
        
        result = model.train(training_data)
        
        assert result.success is True
        assert model.is_trained is True
    
    def test_no_player_specific_config(self, training_data):
        """Test model without player-specific states."""
        config = MarkovConfig(
            include_pitcher_specific=False,
            include_batter_specific=False
        )
        model = MarkovChainModel(config)
        
        result = model.train(training_data)
        
        assert result.success is True
        assert model.is_trained is True


class TestMarkovChainIntegration:
    """Integration tests for Markov chain models."""
    
    @pytest.fixture
    def large_training_data(self):
        """Create larger training dataset."""
        np.random.seed(42)
        n_pitches = 1000
        
        pitch_types = ['FF', 'FT', 'SL', 'CH', 'CU', 'KC']
        pitcher_ids = [f'P{i}' for i in range(10)]
        batter_ids = [f'B{i}' for i in range(20)]
        
        return pd.DataFrame({
            'pitch_type': np.random.choice(pitch_types, n_pitches),
            'balls': np.random.randint(0, 4, n_pitches),
            'strikes': np.random.randint(0, 3, n_pitches),
            'pitcher_id': np.random.choice(pitcher_ids, n_pitches),
            'batter_id': np.random.choice(batter_ids, n_pitches),
            'game_date': ['2024-01-01'] * n_pitches,
            'release_speed': np.random.normal(90, 5, n_pitches),
            'zone_x': np.random.normal(0, 0.5, n_pitches),
            'zone_y': np.random.normal(2.5, 0.5, n_pitches)
        })
    
    def test_large_dataset_training(self, large_training_data):
        """Test training on larger dataset."""
        model = MarkovChainModel()
        
        result = model.train(large_training_data)
        
        assert result.success is True
        assert result.total_pitches == len(large_training_data)
        assert result.unique_states > 0
        assert model.is_trained is True
    
    def test_prediction_consistency(self, large_training_data):
        """Test prediction consistency."""
        model = MarkovChainModel()
        model.train(large_training_data)
        
        # Test same state multiple times
        test_state = {
            'pitch_type': 'FF',
            'balls': 1,
            'strikes': 1,
            'pitcher_id': 'P1',
            'batter_id': 'B1'
        }
        
        predictions = [model.predict(test_state) for _ in range(5)]
        
        # Predictions should be consistent
        first_probs = predictions[0].probabilities
        for pred in predictions[1:]:
            assert pred.probabilities == first_probs
    
    def test_different_configurations(self, large_training_data):
        """Test different model configurations."""
        configs = [
            MarkovConfig(order=1, include_count_state=True),
            MarkovConfig(order=2, include_count_state=False),
            MarkovConfig(order=1, smoothing_factor=0.05),
            MarkovConfig(order=1, min_transitions=10)
        ]
        
        results = []
        for config in configs:
            model = MarkovChainModel(config)
            result = model.train(large_training_data)
            results.append(result)
        
        # All should succeed
        assert all(result.success for result in results)
        
        # Should have different characteristics
        assert len(set(result.unique_states for result in results)) > 1


class TestMarkovChainPerformance:
    """Performance tests for Markov chain models."""
    
    def test_training_performance(self):
        """Test training performance."""
        import time
        
        # Create medium-sized dataset
        n_pitches = 5000
        training_data = pd.DataFrame({
            'pitch_type': np.random.choice(['FF', 'FT', 'SL', 'CH'], n_pitches),
            'balls': np.random.randint(0, 4, n_pitches),
            'strikes': np.random.randint(0, 3, n_pitches),
            'pitcher_id': np.random.choice([f'P{i}' for i in range(50)], n_pitches),
            'batter_id': np.random.choice([f'B{i}' for i in range(100)], n_pitches),
            'game_date': ['2024-01-01'] * n_pitches
        })
        
        model = MarkovChainModel()
        
        start_time = time.time()
        result = model.train(training_data)
        end_time = time.time()
        
        training_time = end_time - start_time
        
        assert result.success is True
        assert training_time < 10.0  # Should complete within 10 seconds
        assert result.training_time > 0
    
    def test_prediction_performance(self):
        """Test prediction performance."""
        import time
        
        # Train model
        training_data = pd.DataFrame({
            'pitch_type': ['FF', 'FT', 'SL', 'CH'] * 1000,
            'balls': np.random.randint(0, 4, 4000),
            'strikes': np.random.randint(0, 3, 4000),
            'pitcher_id': np.random.choice([f'P{i}' for i in range(20)], 4000),
            'batter_id': np.random.choice([f'B{i}' for i in range(40)], 4000),
            'game_date': ['2024-01-01'] * 4000
        })
        
        model = MarkovChainModel()
        model.train(training_data)
        
        # Test prediction performance
        test_states = [
            {
                'pitch_type': 'FF',
                'balls': 1,
                'strikes': 1,
                'pitcher_id': 'P1',
                'batter_id': 'B1'
            }
        ] * 1000
        
        start_time = time.time()
        predictions = model.predict_batch(test_states)
        end_time = time.time()
        
        prediction_time = end_time - start_time
        
        assert len(predictions) == len(test_states)
        assert prediction_time < 5.0  # Should complete within 5 seconds
        assert prediction_time / len(test_states) < 0.01  # < 10ms per prediction


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
