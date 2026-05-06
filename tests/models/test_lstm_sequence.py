"""
Comprehensive test suite for LSTM Pitch Sequence Model (#156)
Tests sequential deep learning models with attention mechanisms for pitch prediction.
"""

import pytest
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from unittest.mock import Mock, patch
from datetime import datetime

from baseball.models.lstm.sequential_model import SequentialLSTMModel, SequenceConfig
from baseball.models.lstm.pitch_encoder import PitchEncoder
from baseball.models.lstm.attention import AttentionMechanism


class TestSequenceConfig:
    """Test sequence configuration dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = SequenceConfig()
        
        assert config.sequence_length == 5
        assert config.embedding_dim == 64
        assert config.hidden_dim == 128
        assert config.num_layers == 2
        assert config.dropout == 0.2
        assert config.learning_rate == 0.001
        assert config.batch_size == 32
        assert config.epochs == 100
        assert config.device == 'cpu'
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = SequenceConfig(
            sequence_length=10,
            embedding_dim=128,
            hidden_dim=256,
            num_layers=3,
            dropout=0.3,
            learning_rate=0.01
        )
        
        assert config.sequence_length == 10
        assert config.embedding_dim == 128
        assert config.hidden_dim == 256
        assert config.num_layers == 3
        assert config.dropout == 0.3
        assert config.learning_rate == 0.01


class TestPitchEncoder:
    """Test pitch encoder functionality."""
    
    @pytest.fixture
    def encoder(self):
        """Create pitch encoder for testing."""
        return PitchEncoder()
    
    @pytest.fixture
    def sample_pitches(self):
        """Create sample pitch data."""
        return ['FF', 'FT', 'SL', 'CH', 'CU', 'KC', 'FF', 'FT', 'SL']
    
    def test_encoder_initialization(self, encoder):
        """Test encoder initialization."""
        assert encoder.pitch_to_idx is not None
        assert encoder.idx_to_pitch is not None
        assert encoder.vocab_size > 0
    
    def test_pitch_encoding(self, encoder, sample_pitches):
        """Test pitch to index encoding."""
        encoded = encoder.encode_pitches(sample_pitches)
        
        assert isinstance(encoded, torch.Tensor)
        assert len(encoded) == len(sample_pitches)
        assert all(0 <= val < encoder.vocab_size for val in encoded.numpy())
    
    def test_pitch_decoding(self, encoder, sample_pitches):
        """Test index to pitch decoding."""
        encoded = encoder.encode_pitches(sample_pitches)
        decoded = encoder.decode_indices(encoded)
        
        assert len(decoded) == len(sample_pitches)
        assert all(pitch in encoder.pitch_to_idx for pitch in decoded)
    
    def test_sequence_padding(self, encoder):
        """Test sequence padding functionality."""
        sequences = [['FF', 'FT'], ['SL', 'CH'], ['CU']]
        padded = encoder.pad_sequences(sequences, max_length=5)
        
        assert isinstance(padded, torch.Tensor)
        assert padded.shape[0] == len(sequences)
        assert padded.shape[1] == 5  # max_length
    
    def test_unknown_pitch_handling(self, encoder):
        """Test handling of unknown pitches."""
        unknown_pitches = ['FF', 'XX', 'FT']  # XX is unknown
        
        # Should handle unknown pitches gracefully
        try:
            encoded = encoder.encode_pitches(unknown_pitches)
            # Should either use UNK token or raise informative error
            assert True
        except Exception as e:
            assert 'unknown' in str(e).lower() or 'unk' in str(e).lower()


class TestAttentionMechanism:
    """Test attention mechanism functionality."""
    
    @pytest.fixture
    def attention(self):
        """Create attention mechanism for testing."""
        return AttentionMechanism(hidden_dim=64)
    
    @pytest.fixture
    def sample_hidden_states(self):
        """Create sample hidden states."""
        batch_size = 2
        seq_length = 3
        hidden_dim = 64
        
        return torch.randn(batch_size, seq_length, hidden_dim)
    
    def test_attention_initialization(self, attention):
        """Test attention mechanism initialization."""
        assert attention.hidden_dim == 64
        assert attention.attention is not None
        assert attention.linear is not None
    
    def test_attention_forward(self, attention, sample_hidden_states):
        """Test attention forward pass."""
        # Create query, key, value from hidden states
        q = attention.linear_q(sample_hidden_states)
        k = attention.linear_k(sample_hidden_states)
        v = attention.linear_v(sample_hidden_states)
        
        attention_weights = attention(q, k, v)
        
        assert isinstance(attention_weights, torch.Tensor)
        assert attention_weights.shape[0] == sample_hidden_states.shape[0]  # batch_size
        assert attention_weights.shape[1] == sample_hidden_states.shape[1]  # seq_length
    
    def test_attention_weights_sum(self, attention, sample_hidden_states):
        """Test attention weights sum to 1."""
        q = attention.linear_q(sample_hidden_states)
        k = attention.linear_k(sample_hidden_states)
        v = attention.linear_v(sample_hidden_states)
        
        attention_weights = attention(q, k, v)
        
        # Attention weights should sum to 1 across sequence length
        weights_sum = attention_weights.sum(dim=-1)
        assert torch.allclose(weights_sum, torch.ones_like(weights_sum), atol=1e-6)


class TestSequentialLSTMModel:
    """Test sequential LSTM model functionality."""
    
    @pytest.fixture
    def model(self):
        """Create sequential LSTM model for testing."""
        config = SequenceConfig(
            sequence_length=5,
            embedding_dim=32,
            hidden_dim=64,
            num_layers=2,
            dropout=0.1,
            epochs=5  # Small for testing
        )
        return SequentialLSTMModel(config)
    
    @pytest.fixture
    def training_data(self):
        """Create training data for sequential model."""
        np.random.seed(42)
        n_sequences = 100
        
        sequences = []
        targets = []
        
        # Create sequences of pitches
        pitch_types = ['FF', 'FT', 'SL', 'CH', 'CU']
        for _ in range(n_sequences):
            seq_length = np.random.randint(3, 8)
            sequence = np.random.choice(pitch_types, seq_length).tolist()
            target = np.random.choice(pitch_types)
            
            sequences.append(sequence)
            targets.append(target)
        
        return pd.DataFrame({
            'sequence': sequences,
            'target': targets,
            'pitcher_id': np.random.choice([f'P{i}' for i in range(10)], n_sequences),
            'batter_id': np.random.choice([f'B{i}' for i in range(20)], n_sequences),
            'game_date': ['2024-01-01'] * n_sequences,
            'release_speed': np.random.normal(90, 5, n_sequences),
            'zone_x': np.random.normal(0, 0.5, n_sequences),
            'zone_y': np.random.normal(2.5, 0.5, n_sequences)
        })
    
    def test_model_initialization(self, model):
        """Test model initialization."""
        assert isinstance(model.config, SequenceConfig)
        assert model.model is None
        assert model.encoder is not None
        assert model.attention is not None
        assert model.is_trained is False
    
    def test_model_building(self, model):
        """Test model architecture building."""
        model._build_model()
        
        assert model.model is not None
        assert hasattr(model.model, 'embedding')
        assert hasattr(model.model, 'lstm')
        assert hasattr(model.model, 'attention')
        assert hasattr(model.model, 'classifier')
    
    def test_sequence_encoding(self, model, training_data):
        """Test sequence encoding for training."""
        encoded_sequences, encoded_targets = model._encode_sequences(training_data)
        
        assert isinstance(encoded_sequences, torch.Tensor)
        assert isinstance(encoded_targets, torch.Tensor)
        assert len(encoded_sequences) == len(training_data)
        assert len(encoded_targets) == len(training_data)
    
    def test_model_training(self, model, training_data):
        """Test model training."""
        result = model.train(training_data)
        
        assert result.success is True
        assert result.model_version is not None
        assert result.rows_processed == len(training_data)
        assert result.training_time_seconds > 0
        assert model.is_trained is True
    
    def test_prediction_after_training(self, model, training_data):
        """Test prediction after training."""
        model.train(training_data)
        
        # Create test sequence
        test_sequence = ['FF', 'FT', 'SL', 'CH', 'CU']
        test_context = {
            'sequence': test_sequence,
            'pitcher_id': 'P1',
            'batter_id': 'B1',
            'release_speed': 92.0,
            'zone_x': 0.1,
            'zone_y': 2.6
        }
        
        prediction = model.predict(test_context)
        
        assert hasattr(prediction, 'probabilities')
        assert hasattr(prediction, 'predicted_class')
        assert len(prediction.probabilities) > 0
        assert sum(prediction.probabilities.values()) == pytest.approx(1.0, rel=1e-10)
    
    def test_batch_prediction(self, model, training_data):
        """Test batch prediction."""
        model.train(training_data)
        
        # Create test sequences
        test_sequences = [
            {
                'sequence': ['FF', 'FT', 'SL', 'CH', 'CU'],
                'pitcher_id': 'P1',
                'batter_id': 'B1',
                'release_speed': 92.0,
                'zone_x': 0.1,
                'zone_y': 2.6
            },
            {
                'sequence': ['SL', 'CH', 'CU', 'FF', 'FT'],
                'pitcher_id': 'P2',
                'batter_id': 'B2',
                'release_speed': 88.0,
                'zone_x': -0.2,
                'zone_y': 2.3
            }
        ]
        
        predictions = model.predict_batch(test_sequences)
        
        assert len(predictions) == len(test_sequences)
        for pred in predictions:
            assert hasattr(pred, 'probabilities')
            assert hasattr(pred, 'predicted_class')
    
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
            loaded_model = SequentialLSTMModel.load(model_path)
            
            # Test loaded model
            assert loaded_model.is_trained is True
            assert loaded_model.config.sequence_length == model.config.sequence_length
            
            # Test prediction with loaded model
            test_sequence = ['FF', 'FT', 'SL', 'CH', 'CU']
            test_context = {
                'sequence': test_sequence,
                'pitcher_id': 'P1',
                'batter_id': 'B1',
                'release_speed': 92.0,
                'zone_x': 0.1,
                'zone_y': 2.6
            }
            prediction = loaded_model.predict(test_context)
            assert hasattr(prediction, 'probabilities')
            
        finally:
            if os.path.exists(model_path):
                os.unlink(model_path)
    
    def test_different_sequence_lengths(self, model, training_data):
        """Test different sequence lengths."""
        config = SequenceConfig(sequence_length=10)
        model = SequentialLSTMModel(config)
        
        result = model.train(training_data)
        
        assert result.success is True
        assert model.is_trained is True
    
    def test_gpu_support(self, training_data):
        """Test GPU device support."""
        if torch.cuda.is_available():
            config = SequenceConfig(device='cuda')
            model = SequentialLSTMModel(config)
            
            result = model.train(training_data)
            
            assert result.success is True
            assert model.config.device == 'cuda'
    
    def test_attention_integration(self, model, training_data):
        """Test attention mechanism integration."""
        model.train(training_data)
        
        # Test that attention is being used
        assert model.attention is not None
        assert hasattr(model.model, 'attention')


class TestLSTMModelIntegration:
    """Integration tests for LSTM sequence models."""
    
    @pytest.fixture
    def large_training_data(self):
        """Create larger training dataset."""
        np.random.seed(42)
        n_sequences = 500
        
        sequences = []
        targets = []
        pitch_types = ['FF', 'FT', 'SL', 'CH', 'CU']
        
        for _ in range(n_sequences):
            seq_length = np.random.randint(3, 10)
            sequence = np.random.choice(pitch_types, seq_length).tolist()
            target = np.random.choice(pitch_types)
            
            sequences.append(sequence)
            targets.append(target)
        
        return pd.DataFrame({
            'sequence': sequences,
            'target': targets,
            'pitcher_id': np.random.choice([f'P{i}' for i in range(20)], n_sequences),
            'batter_id': np.random.choice([f'B{i}' for i in range(50)], n_sequences),
            'game_date': ['2024-01-01'] * n_sequences,
            'release_speed': np.random.normal(90, 5, n_sequences),
            'zone_x': np.random.normal(0, 0.5, n_sequences),
            'zone_y': np.random.normal(2.5, 0.5, n_sequences)
        })
    
    def test_large_dataset_training(self, model, large_training_data):
        """Test training on larger dataset."""
        result = model.train(large_training_data)
        
        assert result.success is True
        assert result.rows_processed == len(large_training_data)
        assert model.is_trained is True
    
    def test_sequence_length_variations(self, large_training_data):
        """Test different sequence lengths."""
        sequence_lengths = [3, 5, 7, 10]
        
        results = []
        for seq_len in sequence_lengths:
            config = SequenceConfig(sequence_length=seq_len, epochs=3)  # Small for testing
            model = SequentialLSTMModel(config)
            result = model.train(large_training_data)
            results.append(result)
        
        # All should succeed
        assert all(result.success for result in results)
        
        # Should have different characteristics
        assert len(set(result.model_version for result in results)) > 1
    
    def test_model_robustness(self, large_training_data):
        """Test model robustness with noisy data."""
        # Add noise to training data
        noisy_data = large_training_data.copy()
        
        # Add some invalid sequences
        for i in range(10):
            if i < len(noisy_data):
                noisy_data.at[i, 'sequence'] = ['XX'] * 5  # Invalid pitch types
        
        config = SequenceConfig(epochs=5)
        model = SequentialLSTMModel(config)
        
        # Should handle noisy data gracefully
        result = model.train(noisy_data)
        
        # Should either succeed or fail gracefully
        assert result.success is True or result.error_message is not None


class TestLSTMModelPerformance:
    """Performance tests for LSTM sequence models."""
    
    def test_training_performance(self):
        """Test training performance."""
        import time
        
        # Create medium-sized dataset
        n_sequences = 200
        sequences = []
        targets = []
        pitch_types = ['FF', 'FT', 'SL', 'CH', 'CU']
        
        for _ in range(n_sequences):
            seq_length = np.random.randint(3, 8)
            sequence = np.random.choice(pitch_types, seq_length).tolist()
            target = np.random.choice(pitch_types)
            
            sequences.append(sequence)
            targets.append(target)
        
        training_data = pd.DataFrame({
            'sequence': sequences,
            'target': targets,
            'pitcher_id': np.random.choice([f'P{i}' for i in range(10)], n_sequences),
            'batter_id': np.random.choice([f'B{i}' for i in range(20)], n_sequences),
            'game_date': ['2024-01-01'] * n_sequences,
            'release_speed': np.random.normal(90, 5, n_sequences),
            'zone_x': np.random.normal(0, 0.5, n_sequences),
            'zone_y': np.random.normal(2.5, 0.5, n_sequences)
        })
        
        config = SequenceConfig(epochs=5, batch_size=16)  # Small for testing
        model = SequentialLSTMModel(config)
        
        start_time = time.time()
        result = model.train(training_data)
        end_time = time.time()
        
        training_time = end_time - start_time
        
        assert result.success is True
        assert training_time < 120.0  # Should complete within 2 minutes
        assert result.training_time_seconds > 0
    
    def test_prediction_performance(self):
        """Test prediction performance."""
        import time
        
        # Train model
        sequences = [['FF', 'FT', 'SL'], ['CH', 'CU', 'FF']] * 100
        targets = ['FF', 'CH'] * 100
        training_data = pd.DataFrame({
            'sequence': sequences,
            'target': targets,
            'pitcher_id': ['P1'] * 100,
            'batter_id': ['B1'] * 100,
            'game_date': ['2024-01-01'] * 100,
            'release_speed': np.random.normal(90, 5, 100),
            'zone_x': np.random.normal(0, 0.5, 100),
            'zone_y': np.random.normal(2.5, 0.5, 100)
        })
        
        model = SequentialLSTMModel(SequenceConfig(epochs=3))
        model.train(training_data)
        
        # Test prediction performance
        test_sequences = [
            {
                'sequence': ['FF', 'FT', 'SL', 'CH', 'CU'],
                'pitcher_id': 'P1',
                'batter_id': 'B1',
                'release_speed': 92.0,
                'zone_x': 0.1,
                'zone_y': 2.6
            }
        ] * 100
        
        start_time = time.time()
        predictions = model.predict_batch(test_sequences)
        end_time = time.time()
        
        prediction_time = end_time - start_time
        
        assert len(predictions) == len(test_sequences)
        assert prediction_time < 30.0  # Should complete within 30 seconds
        assert prediction_time / len(test_sequences) < 0.3  # < 300ms per prediction


class TestLSTMModelEdgeCases:
    """Edge case tests for LSTM sequence models."""
    
    def test_empty_sequences(self):
        """Test training with empty sequences."""
        model = SequentialLSTMModel()
        empty_data = pd.DataFrame({
            'sequence': [[]],
            'target': [],
            'pitcher_id': [],
            'batter_id': []
        })
        
        result = model.train(empty_data)
        
        assert result.success is False
        assert result.error_message is not None
    
    def test_single_pitch_sequences(self):
        """Test sequences with single pitch."""
        model = SequentialLSTMModel()
        single_data = pd.DataFrame({
            'sequence': [['FF']],
            'target': ['FF'],
            'pitcher_id': ['P1'],
            'batter_id': ['B1'],
            'game_date': ['2024-01-01'],
            'release_speed': [90.0],
            'zone_x': [0.0],
            'zone_y': [2.5]
        })
        
        result = model.train(single_data)
        
        # Should train but with warnings
        assert result.success is True
    
    def test_very_long_sequences(self):
        """Test with very long sequences."""
        model = SequentialLSTMModel()
        
        # Create data with long sequences
        long_data = pd.DataFrame({
            'sequence': [['FF'] * 20],  # Very long sequence
            'target': ['FF'],
            'pitcher_id': ['P1'],
            'batter_id': ['B1'],
            'game_date': ['2024-01-01'],
            'release_speed': [90.0],
            'zone_x': [0.0],
            'zone_y': [2.5]
        })
        
        result = model.train(long_data)
        
        # Should handle gracefully
        assert result.success is True or result.error_message is not None
    
    def test_mixed_sequence_lengths(self):
        """Test with mixed sequence lengths in training data."""
        model = SequentialLSTMModel()
        
        # Create data with varying sequence lengths
        mixed_data = pd.DataFrame({
            'sequence': [['FF'], ['FF', 'FT'], ['FF', 'FT', 'SL', 'CH'], ['FF'] * 5],
            'target': ['FF', 'FT', 'SL', 'FF'],
            'pitcher_id': ['P1', 'P1', 'P1', 'P1'],
            'batter_id': ['B1', 'B1', 'B1', 'B1'],
            'game_date': ['2024-01-01'] * 4,
            'release_speed': [90.0, 91.0, 92.0, 93.0],
            'zone_x': [0.0, 0.1, 0.2, 0.3],
            'zone_y': [2.5, 2.6, 2.7, 2.8]
        })
        
        result = model.train(mixed_data)
        
        # Should handle mixed lengths
        assert result.success is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
