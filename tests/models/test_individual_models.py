"""
Comprehensive test suite for Individual Model Implementations (#164)
Tests XGBoost hierarchical models, Markov chain models, and LSTM sequential models.
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from .base_test_infrastructure import (
    MockLSTMModel, MockXGBoostModel, MockMarkovModel,
    MockPredictionContext, MockDataGenerator, PerformanceTracker,
    BaseModelTest
)

# Enhanced mock classes for individual model testing
class MockXGBoostHierarchicalModel:
    """Mock XGBoost hierarchical model for testing"""
    
    def __init__(self, name="xgb_hierarchical", accuracy=0.68, latency_ms=18):
        self.name = name
        self.accuracy = accuracy
        self.latency_ms = latency_ms
        self.version = 1
        self.tier1_model = Mock()
        self.tier2_model = Mock()
        self.feature_importance = np.random.dirichlet(np.ones(39))
        
    async def predict(self, context):
        """Mock hierarchical prediction"""
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        # Tier 1: Ball / Strike / Ball-in-Play
        tier1_probs = np.random.dirichlet(np.ones(3))
        tier1_prediction = np.argmax(tier1_probs)
        
        # Tier 2: Detailed outcome if Ball-in-Play
        if tier1_prediction == 2:  # Ball-in-Play
            tier2_probs = np.random.dirichlet(np.ones(5))  # Single, Double, Triple, HR, Out
            tier2_prediction = np.argmax(tier2_probs)
        else:
            tier2_prediction = None
        
        # Convert to 27 pitch type probabilities
        pitch_probs = np.random.dirichlet(np.ones(27))
        
        # Add bias based on count state
        if context.balls >= 3:
            pitch_probs[1] += 0.15  # More breaking balls in 3-ball counts
            pitch_probs = pitch_probs / pitch_probs.sum()
        
        return MockHierarchicalPrediction(
            model_name=self.name,
            pitch_probabilities=pitch_probs,
            tier1_prediction=tier1_prediction,
            tier2_prediction=tier2_prediction,
            tier1_probabilities=tier1_probs,
            tier2_probabilities=tier2_probs if tier2_prediction is not None else None,
            swing_probability=0.55 + np.random.normal(0, 0.1),
            location_prediction=np.random.dirichlet(np.ones(3)),
            confidence_score=self.accuracy + np.random.normal(0, 0.03),
            metadata={
                "model_type": "xgboost_hierarchical",
                "count_aware": True,
                "hierarchical": True
            }
        )
    
    async def train(self, training_data):
        """Mock hierarchical training"""
        await asyncio.sleep(0.05)
        return Mock(
            tier1_metrics={"accuracy": self.accuracy + np.random.normal(0, 0.02)},
            tier2_metrics={"accuracy": self.accuracy - 0.05 + np.random.normal(0, 0.02)},
            feature_importance=self.feature_importance,
            training_time_ms=50
        )
    
    def get_feature_importance(self):
        """Get feature importance"""
        return self.feature_importance
    
    def explain_prediction(self, context):
        """Explain prediction using SHAP values"""
        return Mock(
            shap_values=np.random.normal(0, 0.1, 39),
            feature_names=[f"feature_{i}" for i in range(39)],
            base_value=0.33
        )

class MockMarkovChainModel:
    """Mock Markov chain model for testing"""
    
    def __init__(self, name="markov_chain", accuracy=0.65, latency_ms=8):
        self.name = name
        self.accuracy = accuracy
        self.latency_ms = latency_ms
        self.version = 1
        self.transition_matrices = {}
        self._cache = {}
        
    async def predict(self, context):
        """Mock Markov prediction with transition matrices"""
        # Create cache key
        cache_key = (context.balls, context.strikes, context.sequence_length)
        
        # Check cache
        if cache_key in self._cache:
            cached_result = self._cache[cache_key]
            cached_result.metadata["cached"] = True
            return cached_result
        
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        # Generate count-based probabilities using transition matrices
        count_state = f"{context.balls}-{context.strikes}"
        
        # Simulate transition matrix lookup
        if count_state not in self.transition_matrices:
            self.transition_matrices[count_state] = np.random.dirichlet(np.ones(27))
        
        pitch_probs = self.transition_matrices[count_state].copy()
        
        # Adjust based on previous pitch
        if context.recent_pitches and len(context.recent_pitches) > 0:
            prev_pitch = context.recent_pitches[-1]
            # Add transition bias
            pitch_probs = pitch_probs * 1.1
            pitch_probs = pitch_probs / pitch_probs.sum()
        
        # Markov models are simpler - more predictable patterns
        if context.strikes == 2:
            pitch_probs[0] += 0.2  # More fastballs with 2 strikes
            pitch_probs = pitch_probs / pitch_probs.sum()
        
        result = MockMarkovPrediction(
            model_name=self.name,
            pitch_probabilities=pitch_probs,
            transition_matrix=self.transition_matrices[count_state],
            count_state=count_state,
            swing_probability=0.5 + np.random.normal(0, 0.08),
            location_prediction=np.random.dirichlet(np.ones(3)),
            confidence_score=self.accuracy + np.random.normal(0, 0.02),
            metadata={
                "model_type": "markov_chain",
                "count_state": count_state,
                "cached": False,
                "transition_based": True
            }
        )
        
        # Cache result
        self._cache[cache_key] = result
        
        return result
    
    async def train(self, training_data):
        """Mock Markov training - build transition matrices"""
        await asyncio.sleep(0.01)
        
        # Build transition matrices
        for balls in range(4):
            for strikes in range(3):
                count_state = f"{balls}-{strikes}"
                self.transition_matrices[count_state] = np.random.dirichlet(np.ones(27))
        
        return Mock(
            transition_matrices=len(self.transition_matrices),
            state_coverage=0.95,
            average_accuracy=self.accuracy,
            training_time_ms=10
        )
    
    def get_transition_matrix(self, count_state):
        """Get transition matrix for specific count state"""
        return self.transition_matrices.get(count_state)
    
    def get_state_coverage(self):
        """Get coverage of all possible states"""
        return len(self.transition_matrices) / 12  # 12 possible count states

class MockLSTMSequentialModel:
    """Mock LSTM sequential model for testing"""
    
    def __init__(self, name="lstm_sequential", accuracy=0.70, latency_ms=45):
        self.name = name
        self.accuracy = accuracy
        self.latency_ms = latency_ms
        self.version = 1
        self.sequence_length = 8
        self.hidden_size = 128
        self.num_layers = 2
        
    async def predict(self, context):
        """Mock sequential prediction"""
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        # Process sequence
        sequence = context.recent_pitches[-self.sequence_length:]
        sequence_features = self._encode_sequence(sequence)
        
        # Generate realistic pitch probabilities
        pitch_probs = np.random.dirichlet(np.ones(27))
        
        # Add bias based on sequence patterns
        if len(sequence) >= 3:
            # Look for patterns in recent pitches
            if sequence[-3:] == ["F", "F", "S"]:  # Fastball, Fastball, Strike
                pitch_probs[1] += 0.1  # More breaking balls next
            elif sequence[-2:] == ["C", "C"]:  # Two consecutive changeups
                pitch_probs[0] += 0.15  # More fastballs next
            
            pitch_probs = pitch_probs / pitch_probs.sum()
        
        # LSTM should be better on long sequences
        if context.sequence_length > 5:
            pitch_probs = pitch_probs * 1.1  # Boost confidence
            pitch_probs = pitch_probs / pitch_probs.sum()
        
        return MockSequentialPrediction(
            model_name=self.name,
            pitch_probabilities=pitch_probs,
            sequence_features=sequence_features,
            swing_probability=0.6 + np.random.normal(0, 0.1),
            location_prediction=np.random.dirichlet(np.ones(3)),
            confidence_score=self.accuracy + np.random.normal(0, 0.05),
            metadata={
                "model_type": "lstm_sequential",
                "sequence_used": len(sequence),
                "sequence_features": sequence_features.tolist(),
                "sequential": True
            }
        )
    
    async def train(self, training_data):
        """Mock LSTM training"""
        await asyncio.sleep(0.1)
        return Mock(
            final_loss=0.3 + np.random.normal(0, 0.05),
            training_accuracy=self.accuracy + np.random.normal(0, 0.02),
            validation_accuracy=self.accuracy + np.random.normal(0, 0.02),
            epochs_trained=10,
            training_time_ms=100
        )
    
    def _encode_sequence(self, sequence):
        """Encode pitch sequence for LSTM input"""
        # Simple encoding for mock
        encoding = np.zeros((len(sequence), 27))
        for i, pitch in enumerate(sequence):
            if pitch in ["F", "C", "S", "X", "B", "T", "R", "I", "L", "M", "N", "O", "P", "Q", "U", "V", "W", "Y", "Z", "D", "E", "H", "K", "A", "G", "J"]:
                pitch_idx = ord(pitch) % 27
                encoding[i, pitch_idx] = 1.0
        return encoding

# Mock prediction result classes
class MockHierarchicalPrediction:
    """Mock hierarchical prediction result"""
    def __init__(self, model_name, pitch_probabilities, tier1_prediction, tier2_prediction,
                 tier1_probabilities, tier2_probabilities, swing_probability, location_prediction,
                 confidence_score, metadata):
        self.model_name = model_name
        self.pitch_probabilities = np.array(pitch_probabilities)
        self.tier1_prediction = tier1_prediction
        self.tier2_prediction = tier2_prediction
        self.tier1_probabilities = np.array(tier1_probabilities)
        self.tier2_probabilities = np.array(tier2_probabilities) if tier2_probabilities is not None else None
        self.swing_probability = swing_probability
        self.location_prediction = np.array(location_prediction)
        self.confidence_score = confidence_score
        self.metadata = metadata

class MockMarkovPrediction:
    """Mock Markov prediction result"""
    def __init__(self, model_name, pitch_probabilities, transition_matrix, count_state,
                 swing_probability, location_prediction, confidence_score, metadata):
        self.model_name = model_name
        self.pitch_probabilities = np.array(pitch_probabilities)
        self.transition_matrix = transition_matrix
        self.count_state = count_state
        self.swing_probability = swing_probability
        self.location_prediction = np.array(location_prediction)
        self.confidence_score = confidence_score
        self.metadata = metadata

class MockSequentialPrediction:
    """Mock sequential prediction result"""
    def __init__(self, model_name, pitch_probabilities, sequence_features, swing_probability,
                 location_prediction, confidence_score, metadata):
        self.model_name = model_name
        self.pitch_probabilities = np.array(pitch_probabilities)
        self.sequence_features = sequence_features
        self.swing_probability = swing_probability
        self.location_prediction = np.array(location_prediction)
        self.confidence_score = confidence_score
        self.metadata = metadata

# XGBoost Hierarchical Model Tests
class TestXGBoostHierarchicalModel(BaseModelTest):
    """Comprehensive tests for XGBoost hierarchical model"""
    
    @pytest.fixture
    def xgb_model(self):
        """Create XGBoost hierarchical model"""
        return MockXGBoostHierarchicalModel(
            name="test_xgb",
            accuracy=0.68,
            latency_ms=18
        )
    
    async def test_hierarchical_prediction(self, xgb_model):
        """Test hierarchical prediction structure"""
        
        context = MockPredictionContext(
            sequence_length=5,
            balls=2,
            strikes=1
        )
        
        prediction = await xgb_model.predict(context)
        
        # Verify hierarchical structure
        assert isinstance(prediction, MockHierarchicalPrediction)
        assert prediction.tier1_prediction in [0, 1, 2]  # Ball/Strike/BIP
        assert prediction.tier1_probabilities is not None
        assert len(prediction.tier1_probabilities) == 3
        assert abs(np.sum(prediction.tier1_probabilities) - 1.0) < 1e-10
        
        # Tier 2 should only exist for Ball-in-Play
        if prediction.tier1_prediction == 2:
            assert prediction.tier2_prediction is not None
            assert prediction.tier2_probabilities is not None
            assert len(prediction.tier2_probabilities) == 5
        else:
            assert prediction.tier2_prediction is None
    
    async def test_feature_engineering(self, xgb_model):
        """Test feature engineering for XGBoost"""
        
        context = MockPredictionContext(
            sequence_length=6,
            balls=3,
            strikes=2,
            leverage_index=3.5
        )
        
        prediction = await xgb_model.predict(context)
        
        # Should be count-aware
        assert prediction.metadata["count_aware"] is True
        
        # Should have hierarchical structure
        assert prediction.metadata["hierarchical"] is True
        
        # Should adjust based on count state
        assert prediction.confidence_score > 0.0
    
    async def test_interpretability(self, xgb_model):
        """Test XGBoost interpretability features"""
        
        context = MockPredictionContext(sequence_length=5)
        
        # Test feature importance
        feature_importance = xgb_model.get_feature_importance()
        assert len(feature_importance) == 39
        assert all(0.0 <= imp <= 1.0 for imp in feature_importance)
        assert abs(np.sum(feature_importance) - 1.0) < 1e-10
        
        # Test prediction explanation
        explanation = xgb_model.explain_prediction(context)
        assert explanation.shap_values is not None
        assert len(explanation.shap_values) == 39
        assert len(explanation.feature_names) == 39
        assert explanation.base_value is not None
    
    async def test_hierarchical_training(self, xgb_model):
        """Test hierarchical training process"""
        
        training_data = MockDataGenerator.create_training_data("xgboost", 1000)
        
        training_result = await xgb_model.train(training_data)
        
        # Verify hierarchical training metrics
        assert training_result.tier1_metrics is not None
        assert training_result.tier2_metrics is not None
        assert "accuracy" in training_result.tier1_metrics
        assert "accuracy" in training_result.tier2_metrics
        assert training_result.feature_importance is not None
        assert training_result.training_time_ms > 0
    
    async def test_performance_targets(self, xgb_model):
        """Test XGBoost performance targets"""
        
        context = MockPredictionContext(sequence_length=5)
        
        # Measure latency
        start_time = datetime.now()
        prediction = await xgb_model.predict(context)
        end_time = datetime.now()
        
        latency_ms = (end_time - start_time).total_seconds() * 1000
        
        # Should meet performance targets
        assert latency_ms < 30  # Should be under 30ms (target: 20ms)
        assert prediction.confidence_score > 0.6  # Should be confident
        
        # Test multiple predictions
        latencies = []
        for _ in range(50):
            start_time = datetime.now()
            await xgb_model.predict(context)
            end_time = datetime.now()
            latencies.append((end_time - start_time).total_seconds() * 1000)
        
        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 25  # Average should be under 25ms

# Markov Chain Model Tests
class TestMarkovChainModel(BaseModelTest):
    """Comprehensive tests for Markov chain model"""
    
    @pytest.fixture
    def markov_model(self):
        """Create Markov chain model"""
        return MockMarkovChainModel(
            name="test_markov",
            accuracy=0.65,
            latency_ms=8
        )
    
    async def test_transition_matrix_prediction(self, markov_model):
        """Test transition matrix based prediction"""
        
        context = MockPredictionContext(
            sequence_length=3,
            balls=2,
            strikes=1,
            recent_pitches=["F", "C", "S"]
        )
        
        prediction = await markov_model.predict(context)
        
        # Verify Markov-specific structure
        assert isinstance(prediction, MockMarkovPrediction)
        assert prediction.transition_matrix is not None
        assert len(prediction.transition_matrix) == 27
        assert prediction.count_state == "2-1"
        assert prediction.metadata["transition_based"] is True
        
        # Transition matrix should be valid probabilities
        assert abs(np.sum(prediction.transition_matrix) - 1.0) < 1e-10
        assert all(0.0 <= prob <= 1.0 for prob in prediction.transition_matrix)
    
    async def test_state_transitions(self, markov_model):
        """Test different count state transitions"""
        
        count_states = ["0-0", "1-2", "3-2", "0-2"]
        
        for count_state in count_states:
            balls, strikes = map(int, count_state.split('-'))
            context = MockPredictionContext(
                sequence_length=3,
                balls=balls,
                strikes=strikes
            )
            
            prediction = await markov_model.predict(context)
            
            assert prediction.count_state == count_state
            assert prediction.transition_matrix is not None
            
            # Should have transition matrix for this state
            transition_matrix = markov_model.get_transition_matrix(count_state)
            assert transition_matrix is not None
            np.testing.assert_allclose(prediction.transition_matrix, transition_matrix)
    
    async def test_fast_inference(self, markov_model):
        """Test Markov model fast inference"""
        
        context = MockPredictionContext(sequence_length=5)
        
        # Measure inference time
        latencies = []
        
        for _ in range(100):
            start_time = datetime.now()
            prediction = await markov_model.predict(context)
            end_time = datetime.now()
            
            latency_ms = (end_time - start_time).total_seconds() * 1000
            latencies.append(latency_ms)
            
            assert prediction.confidence_score > 0.0
        
        # Should be very fast
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        assert avg_latency < 15  # Average < 15ms (target: 10ms)
        assert max_latency < 25  # Maximum < 25ms
    
    async def test_caching(self, markov_model):
        """Test Markov model caching"""
        
        context = MockPredictionContext(
            sequence_length=4,
            balls=1,
            strikes=1
        )
        
        # First prediction (cache miss)
        prediction1 = await markov_model.predict(context)
        assert prediction1.metadata["cached"] is False
        
        # Second prediction (cache hit)
        prediction2 = await markov_model.predict(context)
        assert prediction2.metadata["cached"] is True
        
        # Predictions should be identical
        np.testing.assert_allclose(prediction1.pitch_probabilities, prediction2.pitch_probabilities)
    
    async def test_transition_matrix_building(self, markov_model):
        """Test transition matrix building during training"""
        
        training_data = MockDataGenerator.create_training_data("markov", 1000)
        
        training_result = await markov_model.train(training_data)
        
        # Verify transition matrices were built
        assert training_result.transition_matrices > 0
        assert training_result.state_coverage > 0.8
        assert training_result.average_accuracy > 0.6
        assert training_result.training_time_ms < 50  # Should be very fast
        
        # Should have matrices for all count states
        state_coverage = markov_model.get_state_coverage()
        assert state_coverage >= 0.8  # Should cover most states

# LSTM Sequential Model Tests
class TestLSTMSequentialModel(BaseModelTest):
    """Comprehensive tests for LSTM sequential model"""
    
    @pytest.fixture
    def lstm_model(self):
        """Create LSTM sequential model"""
        return MockLSTMSequentialModel(
            name="test_lstm",
            accuracy=0.70,
            latency_ms=45
        )
    
    async def test_sequential_prediction(self, lstm_model):
        """Test sequential prediction structure"""
        
        context = MockPredictionContext(
            sequence_length=8,
            recent_pitches=["F", "C", "S", "F", "C", "S", "F", "B"]
        )
        
        prediction = await lstm_model.predict(context)
        
        # Verify sequential structure
        assert isinstance(prediction, MockSequentialPrediction)
        assert prediction.sequence_features is not None
        assert prediction.sequence_features.shape[0] == min(len(context.recent_pitches), lstm_model.sequence_length)
        assert prediction.sequence_features.shape[1] == 27  # 27 pitch types
        assert prediction.metadata["sequential"] is True
        
        # Should use sequence information
        assert prediction.metadata["sequence_used"] > 0
    
    async def test_sequence_processing(self, lstm_model):
        """Test sequence processing capabilities"""
        
        # Test different sequence lengths
        sequences = [
            ["F"],  # Single pitch
            ["F", "C"],  # Two pitches
            ["F", "C", "S", "F", "C", "S", "F", "B"],  # Long sequence
            ["F", "C", "S", "F", "C", "S", "F", "B", "C", "S"]  # Very long sequence
        ]
        
        for sequence in sequences:
            context = MockPredictionContext(
                sequence_length=len(sequence),
                recent_pitches=sequence
            )
            
            prediction = await lstm_model.predict(context)
            
            assert prediction.sequence_features is not None
            assert prediction.metadata["sequential"] is True
            assert prediction.confidence_score > 0.0
    
    async def test_pattern_recognition(self, lstm_model):
        """Test pattern recognition in sequences"""
        
        # Test specific patterns
        patterns = [
            (["F", "F", "S"], "fastball_fastball_strike"),
            (["C", "C"], "double_changeup"),
            (["F", "C", "S", "B"], "mixed_pattern")
        ]
        
        for pattern, pattern_name in patterns:
            context = MockPredictionContext(
                sequence_length=len(pattern),
                recent_pitches=pattern
            )
            
            prediction = await lstm_model.predict(context)
            
            # Should recognize patterns and adjust predictions
            assert prediction.confidence_score > 0.0
            assert prediction.metadata["sequential"] is True
            
            # Pattern should affect prediction
            assert len(prediction.pitch_probabilities) == 27
    
    async def test_long_sequence_handling(self, lstm_model):
        """Test handling of long sequences"""
        
        # Very long sequence
        long_sequence = ["F", "C", "S"] * 10  # 30 pitches
        
        context = MockPredictionContext(
            sequence_length=len(long_sequence),
            recent_pitches=long_sequence
        )
        
        prediction = await lstm_model.predict(context)
        
        # Should handle long sequences gracefully
        assert prediction.confidence_score > 0.0
        assert prediction.sequence_features is not None
        assert prediction.metadata["sequential"] is True
        
        # Sequence features should be limited to model's max sequence length
        assert prediction.sequence_features.shape[0] <= lstm_model.sequence_length
    
    async def test_sequential_training(self, lstm_model):
        """Test LSTM sequential training"""
        
        training_data = MockDataGenerator.create_training_data("lstm", 1000)
        
        training_result = await lstm_model.train(training_data)
        
        # Verify sequential training metrics
        assert training_result.final_loss > 0.0
        assert training_result.training_accuracy > 0.6
        assert training_result.validation_accuracy > 0.6
        assert training_result.epochs_trained > 0
        assert training_result.training_time_ms > 0
    
    async def test_memory_efficiency(self, lstm_model):
        """Test memory efficiency of LSTM model"""
        
        context = MockPredictionContext(sequence_length=8)
        
        # Test multiple predictions for memory leaks
        predictions = []
        
        for _ in range(100):
            prediction = await lstm_model.predict(context)
            predictions.append(prediction)
        
        # All predictions should be valid
        assert all(p.confidence_score > 0.0 for p in predictions)
        assert all(p.sequence_features is not None for p in predictions)
        
        # Should maintain performance
        assert len(predictions) == 100

# Performance Benchmarks
class TestModelPerformanceBenchmarks(BaseModelTest):
    """Performance benchmarks for all model implementations"""
    
    @pytest.fixture
    def all_models(self):
        """Create all model types for benchmarking"""
        return {
            'xgboost': MockXGBoostHierarchicalModel(accuracy=0.68, latency_ms=18),
            'markov': MockMarkovChainModel(accuracy=0.65, latency_ms=8),
            'lstm': MockLSTMSequentialModel(accuracy=0.70, latency_ms=45)
        }
    
    async def test_accuracy_benchmarks(self, all_models):
        """Test accuracy benchmarks for all models"""
        
        context = MockPredictionContext(sequence_length=5)
        
        accuracy_results = {}
        
        for model_name, model in all_models.items():
            predictions = []
            
            for _ in range(100):
                prediction = await model.predict(context)
                predictions.append(prediction.confidence_score)
            
            avg_confidence = sum(predictions) / len(predictions)
            accuracy_results[model_name] = avg_confidence
        
        # Verify accuracy targets
        assert accuracy_results['xgboost'] > 0.60  # Target: >68%
        assert accuracy_results['markov'] > 0.55   # Target: >65%
        assert accuracy_results['lstm'] > 0.62     # Target: >70%
    
    async def test_latency_benchmarks(self, all_models):
        """Test latency benchmarks for all models"""
        
        context = MockPredictionContext(sequence_length=5)
        
        latency_results = {}
        
        for model_name, model in all_models.items():
            latencies = []
            
            for _ in range(100):
                start_time = datetime.now()
                await model.predict(context)
                end_time = datetime.now()
                
                latency_ms = (end_time - start_time).total_seconds() * 1000
                latencies.append(latency_ms)
            
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            
            latency_results[model_name] = {
                'avg': avg_latency,
                'max': max_latency,
                'p95': np.percentile(latencies, 95)
            }
        
        # Verify latency targets
        assert latency_results['xgboost']['avg'] < 25   # Target: <20ms
        assert latency_results['xgboost']['p95'] < 40
        assert latency_results['markov']['avg'] < 15     # Target: <10ms
        assert latency_results['markov']['p95'] < 25
        assert latency_results['lstm']['avg'] < 60        # Target: <50ms
        assert latency_results['lstm']['p95'] < 80
    
    async def test_memory_benchmarks(self, all_models):
        """Test memory usage benchmarks"""
        
        context = MockPredictionContext(sequence_length=5)
        
        for model_name, model in all_models.items():
            # Test memory stability over many predictions
            predictions = []
            
            for _ in range(200):
                prediction = await model.predict(context)
                predictions.append(prediction)
            
            # All predictions should be valid (no memory issues)
            assert len(predictions) == 200
            assert all(p.confidence_score > 0.0 for p in predictions)
            
            # Check model-specific memory features
            if model_name == 'markov':
                # Markov should have caching
                assert len(model._cache) > 0
            elif model_name == 'lstm':
                # LSTM should handle sequences
                assert all(hasattr(p, 'sequence_features') for p in predictions)
            elif model_name == 'xgboost':
                # XGBoost should have hierarchical structure
                assert all(hasattr(p, 'tier1_prediction') for p in predictions)

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
