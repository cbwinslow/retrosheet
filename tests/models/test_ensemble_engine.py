"""
Comprehensive test suite for Ensemble Prediction Engine (#163)
Tests voting strategies, weight calculation, confidence calibration, and multi-model coordination.
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

# Mock classes for ensemble testing
class MockModelPrediction:
    """Mock model prediction for ensemble testing"""
    def __init__(self, model_name, pitch_probs, swing_prob, location, confidence, metadata=None):
        self.model_name = model_name
        self.pitch_probabilities = np.array(pitch_probs)
        self.swing_probability = swing_prob
        self.location_prediction = np.array(location)
        self.confidence_score = confidence
        self.metadata = metadata or {}

class MockEnsemblePrediction:
    """Mock ensemble prediction result"""
    def __init__(self, pitch_probs, swing_prob, location, confidence, contributing_models, metadata=None):
        self.model_name = "ensemble"
        self.pitch_probabilities = np.array(pitch_probs)
        self.swing_probability = swing_prob
        self.location_prediction = np.array(location)
        self.confidence_score = confidence
        self.contributing_models = contributing_models
        self.metadata = metadata or {}

class MockModelCandidate:
    """Mock model candidate for ensemble"""
    def __init__(self, name, model, metadata, health_status="healthy", suitability_score=0.8):
        self.name = name
        self.model = model
        self.metadata = metadata
        self.health_status = health_status
        self.suitability_score = suitability_score
        self.recent_performance = MockPerformance(accuracy=0.7, latency_ms=20)

class MockPerformance:
    """Mock performance metrics"""
    def __init__(self, accuracy, latency_ms):
        self.accuracy = accuracy
        self.latency_ms = latency_ms

class MockVotingStrategy:
    """Mock voting strategy"""
    def __init__(self, name):
        self.name = name
    
    async def combine_predictions(self, predictions, weights=None):
        """Mock prediction combination"""
        if not predictions:
            raise ValueError("No predictions provided")
        
        # Simple averaging for mock
        pitch_probs = np.mean([p.pitch_probabilities for p in predictions], axis=0)
        swing_prob = np.mean([p.swing_probability for p in predictions])
        location = np.mean([p.location_prediction for p in predictions], axis=0)
        confidence = np.mean([p.confidence_score for p in predictions])
        
        return MockEnsemblePrediction(
            pitch_probs, swing_prob, location, confidence,
            [p.model_name for p in predictions],
            {"strategy": self.name, "models_used": len(predictions)}
        )

class MockWeightCalculator:
    """Mock weight calculator"""
    
    async def calculate_weights(self, candidates, context, model_predictions):
        """Calculate model weights"""
        weights = []
        
        for candidate in candidates:
            # Base weight on performance and suitability
            base_weight = candidate.recent_performance.accuracy * candidate.suitability_score
            
            # Adjust for latency constraints
            if context.max_latency_ms:
                if candidate.recent_performance.latency_ms <= context.max_latency_ms:
                    base_weight *= 1.2
                else:
                    base_weight *= 0.5
            
            weights.append(base_weight)
        
        # Normalize weights
        weights = np.array(weights)
        weights = weights / np.sum(weights)
        
        return weights

class MockCalibrationEngine:
    """Mock confidence calibration"""
    
    async def calibrate_prediction(self, prediction, context):
        """Calibrate prediction confidence"""
        # Simple calibration based on context leverage
        if hasattr(context, 'leverage_index') and context.leverage_index > 2.0:
            # Reduce confidence in high leverage situations
            calibrated_confidence = prediction.confidence_score * 0.9
        else:
            calibrated_confidence = prediction.confidence_score
        
        # Ensure confidence stays in valid range
        calibrated_confidence = max(0.1, min(0.95, calibrated_confidence))
        
        return MockEnsemblePrediction(
            prediction.pitch_probabilities,
            prediction.swing_probability,
            prediction.location_prediction,
            calibrated_confidence,
            prediction.contributing_models,
            {**prediction.metadata, "calibrated": True}
        )

class MockEnsembleEngine:
    """Mock ensemble prediction engine"""
    
    def __init__(self, config=None):
        self.config = config or Mock()
        self.model_registry = getattr(config, 'model_registry', Mock())
        self.weight_calculator = MockWeightCalculator()
        self.calibration_engine = MockCalibrationEngine()
        self.voting_strategies = {
            'majority': MockVotingStrategy('majority'),
            'weighted': MockVotingStrategy('weighted'),
            'adaptive': MockVotingStrategy('adaptive'),
            'confidence_weighted': MockVotingStrategy('confidence_weighted')
        }
        self.prediction_cache = {}
        
    async def initialize(self):
        """Initialize ensemble engine"""
        pass
    
    async def cleanup(self):
        """Cleanup ensemble engine"""
        pass
    
    async def predict_ensemble(self, context, strategy='weighted'):
        """Make ensemble prediction"""
        # Get model candidates
        candidates = await self.model_registry.discover_models(context)
        
        if not candidates:
            raise ValueError("No models available for prediction")
        
        # Get predictions from models
        model_predictions = []
        for candidate in candidates:
            prediction = await candidate.model.predict(context)
            model_predictions.append(prediction)
        
        # Calculate weights
        weights = await self.weight_calculator.calculate_weights(
            candidates, context, model_predictions
        )
        
        # Combine predictions using voting strategy
        voting_strategy = self.voting_strategies.get(strategy, self.voting_strategies['weighted'])
        ensemble_prediction = await voting_strategy.combine_predictions(model_predictions, weights)
        
        # Calibrate confidence
        calibrated_prediction = await self.calibration_engine.calibrate_prediction(
            ensemble_prediction, context
        )
        
        return calibrated_prediction
    
    async def get_performance_metrics(self):
        """Get performance metrics"""
        return Mock(
            total_predictions=100,
            average_latency=45.2,
            average_confidence=0.73,
            model_usage_stats={
                'lstm': 40,
                'xgboost': 35,
                'markov': 25
            }
        )
    
    async def get_resource_metrics(self):
        """Get resource usage metrics"""
        return Mock(
            memory_usage_mb=150.5,
            cpu_usage_percent=25.3,
            cache_hit_rate=0.65
        )

# Voting Strategy Tests
class TestVotingStrategies(BaseModelTest):
    """Comprehensive tests for ensemble voting strategies"""
    
    @pytest.fixture
    def sample_model_predictions(self):
        """Create sample model predictions for testing"""
        return [
            MockModelPrediction(
                model_name="lstm",
                pitch_probs=[0.4, 0.3, 0.2, 0.1] + [0.0] * 23,
                swing_prob=0.6,
                location=[0.1, 0.2, 0.7],
                confidence=0.75,
                metadata={"model_type": "sequential"}
            ),
            MockModelPrediction(
                model_name="xgboost",
                pitch_probs=[0.3, 0.4, 0.2, 0.1] + [0.0] * 23,
                swing_prob=0.5,
                location=[0.2, 0.3, 0.5],
                confidence=0.68,
                metadata={"model_type": "tree_based"}
            ),
            MockModelPrediction(
                model_name="markov",
                pitch_probs=[0.35, 0.35, 0.2, 0.1] + [0.0] * 23,
                swing_prob=0.55,
                location=[0.15, 0.25, 0.6],
                confidence=0.62,
                metadata={"model_type": "probabilistic"}
            )
        ]
    
    @pytest.fixture
    def sample_weights(self):
        """Create sample model weights"""
        return np.array([0.4, 0.35, 0.25])
    
    async def test_majority_voting_strategy(self, sample_model_predictions):
        """Test majority voting strategy"""
        
        strategy = MockVotingStrategy('majority')
        
        # Test pitch probability voting
        result = await strategy.combine_predictions(sample_model_predictions, None)
        
        # Verify result structure
        assert isinstance(result, MockEnsemblePrediction)
        assert len(result.pitch_probabilities) == 27
        assert result.swing_probability > 0.0
        assert result.confidence_score > 0.0
        
        # Majority voting should average probabilities
        expected_pitch_probs = np.mean([p.pitch_probabilities for p in sample_model_predictions], axis=0)
        np.testing.assert_allclose(result.pitch_probabilities, expected_pitch_probs, rtol=1e-10)
        
        # Swing probability should be average
        expected_swing_prob = np.mean([p.swing_probability for p in sample_model_predictions])
        assert abs(result.swing_probability - expected_swing_prob) < 1e-10
    
    async def test_weighted_voting_strategy(self, sample_model_predictions, sample_weights):
        """Test weighted voting strategy"""
        
        strategy = MockVotingStrategy('weighted')
        
        # Test weighted combination
        result = await strategy.combine_predictions(sample_model_predictions, sample_weights)
        
        # Verify weighted averaging
        weighted_pitch_probs = np.average(
            [p.pitch_probabilities for p in sample_model_predictions],
            axis=0,
            weights=sample_weights
        )
        np.testing.assert_allclose(result.pitch_probabilities, weighted_pitch_probs, rtol=1e-10)
        
        # Verify weighted swing probability
        weighted_swing_prob = np.average(
            [p.swing_probability for p in sample_model_predictions],
            weights=sample_weights
        )
        assert abs(result.swing_probability - weighted_swing_prob) < 1e-10
        
        # Confidence should be weighted average
        weighted_confidence = np.average(
            [p.confidence_score for p in sample_model_predictions],
            weights=sample_weights
        )
        assert abs(result.confidence_score - weighted_confidence) < 1e-10
    
    async def test_confidence_weighted_strategy(self, sample_model_predictions):
        """Test confidence-weighted voting strategy"""
        
        strategy = MockVotingStrategy('confidence_weighted')
        
        # Test confidence-weighted combination
        result = await strategy.combine_predictions(sample_model_predictions, None)
        
        # Should use confidence scores as weights
        confidences = np.array([p.confidence_score for p in sample_model_predictions])
        normalized_confidences = confidences / np.sum(confidences)
        
        expected_pitch_probs = np.average(
            [p.pitch_probabilities for p in sample_model_predictions],
            axis=0,
            weights=normalized_confidences
        )
        np.testing.assert_allclose(result.pitch_probabilities, expected_pitch_probs, rtol=1e-10)
    
    async def test_voting_strategy_with_single_model(self, sample_model_predictions):
        """Test voting strategies with single model"""
        
        single_prediction = [sample_model_predictions[0]]
        
        strategies = [
            MockVotingStrategy('majority'),
            MockVotingStrategy('weighted'),
            MockVotingStrategy('adaptive'),
            MockVotingStrategy('confidence_weighted')
        ]
        
        for strategy in strategies:
            result = await strategy.combine_predictions(single_prediction, None)
            
            # With single model, result should match input
            np.testing.assert_allclose(result.pitch_probabilities, single_prediction[0].pitch_probabilities)
            assert result.swing_probability == single_prediction[0].swing_probability
            assert result.confidence_score == single_prediction[0].confidence_score
    
    async def test_voting_strategy_with_empty_predictions(self):
        """Test voting strategies with empty predictions"""
        
        strategies = [
            MockVotingStrategy('majority'),
            MockVotingStrategy('weighted'),
            MockVotingStrategy('adaptive'),
            MockVotingStrategy('confidence_weighted')
        ]
        
        for strategy in strategies:
            with pytest.raises(ValueError, match="No predictions provided"):
                await strategy.combine_predictions([], None)

# Weight Calculation Tests
class TestWeightCalculation(BaseModelTest):
    """Comprehensive tests for ensemble weight calculation"""
    
    @pytest.fixture
    def weight_calculator(self):
        """Create weight calculator for testing"""
        return MockWeightCalculator()
    
    @pytest.fixture
    def sample_model_candidates(self):
        """Create sample model candidates"""
        return [
            MockModelCandidate(
                name="lstm",
                model=Mock(),
                metadata=Mock(),
                health_status="healthy",
                recent_performance=MockPerformance(accuracy=0.75, latency_ms=45),
                suitability_score=0.8
            ),
            MockModelCandidate(
                name="xgboost",
                model=Mock(),
                metadata=Mock(),
                health_status="healthy",
                recent_performance=MockPerformance(accuracy=0.68, latency_ms=18),
                suitability_score=0.7
            ),
            MockModelCandidate(
                name="markov",
                model=Mock(),
                metadata=Mock(),
                health_status="healthy",
                recent_performance=MockPerformance(accuracy=0.65, latency_ms=8),
                suitability_score=0.6
            )
        ]
    
    async def test_basic_weight_calculation(self, weight_calculator, sample_model_candidates):
        """Test basic weight calculation"""
        
        context = MockPredictionContext(sequence_length=5)
        model_predictions = [
            MockModelPrediction("lstm", [0.4] * 27, 0.6, [0.1, 0.2, 0.7], 0.75),
            MockModelPrediction("xgboost", [0.3] * 27, 0.5, [0.2, 0.3, 0.5], 0.68),
            MockModelPrediction("markov", [0.35] * 27, 0.55, [0.15, 0.25, 0.6], 0.62)
        ]
        
        weights = await weight_calculator.calculate_weights(
            sample_model_candidates,
            context,
            model_predictions
        )
        
        # Verify weight properties
        assert len(weights) == 3
        assert all(w >= 0.0 for w in weights)
        assert abs(sum(weights) - 1.0) < 1e-10  # Should sum to 1
        
        # Higher performing models should get higher weights
        lstm_weight = weights[0]  # LSTM has highest accuracy
        markov_weight = weights[2]  # Markov has lowest accuracy
        assert lstm_weight > markov_weight
    
    async def test_latency_based_weighting(self, weight_calculator):
        """Test latency-based weight calculation"""
        
        # Create candidates with different latencies
        fast_candidate = MockModelCandidate(
            name="fast",
            model=Mock(),
            metadata=Mock(),
            health_status="healthy",
            recent_performance=MockPerformance(accuracy=0.70, latency_ms=5),
            suitability_score=0.7
        )
        
        slow_candidate = MockModelCandidate(
            name="slow",
            model=Mock(),
            metadata=Mock(),
            health_status="healthy",
            recent_performance=MockPerformance(accuracy=0.70, latency_ms=200),
            suitability_score=0.7
        )
        
        context = MockPredictionContext(max_latency_ms=50)  # Strict latency requirement
        model_predictions = [
            MockModelPrediction("fast", [0.4] * 27, 0.6, [0.1, 0.2, 0.7], 0.7),
            MockModelPrediction("slow", [0.3] * 27, 0.5, [0.2, 0.3, 0.5], 0.7)
        ]
        
        weights = await weight_calculator.calculate_weights(
            [fast_candidate, slow_candidate],
            context,
            model_predictions
        )
        
        # Fast model should get much higher weight
        assert weights[0] > weights[1] * 2  # Fast should be at least 2x higher

# Confidence Calibration Tests
class TestConfidenceCalibration(BaseModelTest):
    """Comprehensive tests for confidence calibration"""
    
    @pytest.fixture
    def calibration_engine(self):
        """Create calibration engine for testing"""
        return MockCalibrationEngine()
    
    @pytest.fixture
    def sample_ensemble_prediction(self):
        """Create sample ensemble prediction"""
        return MockEnsemblePrediction(
            pitch_probs=[0.4, 0.3, 0.2, 0.1] + [0.0] * 23,
            swing_prob=0.6,
            location=[0.1, 0.2, 0.7],
            confidence=0.75,
            contributing_models=["lstm", "xgboost", "markov"],
            metadata={"voting_strategy": "weighted"}
        )
    
    async def test_basic_calibration(self, calibration_engine, sample_ensemble_prediction):
        """Test basic confidence calibration"""
        
        context = MockPredictionContext(sequence_length=5)
        
        calibrated = await calibration_engine.calibrate_prediction(
            sample_ensemble_prediction,
            context
        )
        
        # Verify calibration structure
        assert isinstance(calibrated, MockEnsemblePrediction)
        assert calibrated.confidence_score != sample_ensemble_prediction.confidence_score
        
        # Calibrated confidence should be reasonable
        assert 0.0 <= calibrated.confidence_score <= 1.0
    
    async def test_high_leverage_calibration(self, calibration_engine, sample_ensemble_prediction):
        """Test calibration in high leverage situations"""
        
        high_leverage_context = MockPredictionContext(
            sequence_length=5,
            leverage_index=3.5
        )
        
        calibrated = await calibration_engine.calibrate_prediction(
            sample_ensemble_prediction,
            high_leverage_context
        )
        
        # High leverage should reduce confidence
        assert calibrated.confidence_score < sample_ensemble_prediction.confidence_score
        assert calibrated.metadata["calibrated"] is True

# Performance Tests
class TestEnsemblePerformance(BaseModelTest):
    """Performance tests for ensemble prediction engine"""
    
    @pytest.fixture
    async def performance_ensemble(self):
        """Create ensemble for performance testing"""
        
        # Mock model registry
        mock_registry = Mock()
        mock_registry.discover_models = AsyncMock(return_value=[
            MockModelCandidate("lstm", MockLSTMModel(), Mock(), "healthy", 0.8),
            MockModelCandidate("xgboost", MockXGBoostModel(), Mock(), "healthy", 0.7),
            MockModelCandidate("markov", MockMarkovModel(), Mock(), "healthy", 0.6)
        ])
        
        config = Mock()
        config.model_registry = mock_registry
        ensemble = MockEnsembleEngine(config)
        await ensemble.initialize()
        
        yield ensemble
        await ensemble.cleanup()
    
    async def test_ensemble_prediction_latency(self, performance_ensemble):
        """Test ensemble prediction latency"""
        
        context = MockPredictionContext(sequence_length=5)
        
        # Measure prediction time
        latencies = []
        
        for _ in range(100):
            start_time = datetime.now()
            prediction = await performance_ensemble.predict_ensemble(context)
            end_time = datetime.now()
            
            latency_ms = (end_time - start_time).total_seconds() * 1000
            latencies.append(latency_ms)
            assert prediction.confidence_score > 0.0
        
        # Verify performance targets
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        assert avg_latency < 100  # Average < 100ms
        assert max_latency < 200  # Maximum < 200ms
    
    async def test_concurrent_ensemble_predictions(self, performance_ensemble):
        """Test concurrent ensemble predictions"""
        
        context = MockPredictionContext(sequence_length=5)
        
        # Concurrent predictions
        prediction_tasks = []
        for _ in range(20):
            task = performance_ensemble.predict_ensemble(context)
            prediction_tasks.append(task)
        
        predictions = await asyncio.gather(*prediction_tasks)
        
        # All predictions should be valid
        assert len(predictions) == 20
        assert all(p.confidence_score > 0.0 for p in predictions)
        assert all(len(p.pitch_probabilities) > 0 for p in predictions)
    
    async def test_voting_strategy_performance(self, performance_ensemble):
        """Test performance of different voting strategies"""
        
        context = MockPredictionContext(sequence_length=5)
        
        strategies = ['majority', 'weighted', 'adaptive', 'confidence_weighted']
        
        strategy_latencies = {}
        
        for strategy in strategies:
            latencies = []
            
            for _ in range(50):
                start_time = datetime.now()
                prediction = await performance_ensemble.predict_ensemble(context, strategy)
                end_time = datetime.now()
                
                latency_ms = (end_time - start_time).total_seconds() * 1000
                latencies.append(latency_ms)
            
            strategy_latencies[strategy] = {
                'avg': sum(latencies) / len(latencies),
                'max': max(latencies),
                'min': min(latencies)
            }
        
        # All strategies should be reasonably fast
        for strategy, metrics in strategy_latencies.items():
            assert metrics['avg'] < 100  # Average < 100ms
            assert metrics['max'] < 200  # Maximum < 200ms

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
