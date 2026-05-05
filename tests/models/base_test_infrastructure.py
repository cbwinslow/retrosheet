"""
Base test infrastructure for multi-model ensemble system testing.
Provides common fixtures, mocks, and utilities for all test suites.
"""

import pytest
import asyncio
import numpy as np
import time
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass

# Mock classes for testing
@dataclass
class MockPredictionContext:
    """Mock prediction context for testing"""
    sequence_length: int = 5
    balls: int = 0
    strikes: int = 0
    outs: int = 2
    inning: int = 5
    score_diff: int = 0
    leverage_index: float = 1.0
    max_latency_ms: float = 100.0
    pitcher_id: str = "test_pitcher"
    batter_id: str = "test_batter"
    recent_pitches: List[str] = None
    
    def __post_init__(self):
        if self.recent_pitches is None:
            self.recent_pitches = ["F", "C", "S"][:self.sequence_length]

@dataclass
class MockModelPrediction:
    """Mock model prediction result"""
    model_name: str
    pitch_probabilities: np.ndarray
    swing_probability: float
    location_prediction: np.ndarray
    confidence_score: float
    metadata: Dict[str, Any]

class MockLSTMModel:
    """Mock LSTM model for testing"""
    
    def __init__(self, name="mock_lstm", accuracy=0.70, latency_ms=45):
        self.name = name
        self.accuracy = accuracy
        self.latency_ms = latency_ms
        self.version = 1
        
    async def predict(self, context):
        """Mock prediction with realistic timing"""
        # Simulate model latency
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        # Generate realistic pitch probabilities
        pitch_probs = np.random.dirichlet(np.ones(27))
        
        # Add some bias based on sequence length
        if context.sequence_length > 5:
            pitch_probs[0] += 0.1  # More fastballs in long sequences
            pitch_probs = pitch_probs / pitch_probs.sum()
        
        return MockModelPrediction(
            model_name=self.name,
            pitch_probabilities=pitch_probs,
            swing_probability=0.6 + np.random.normal(0, 0.1),
            location_prediction=np.random.dirichlet(np.ones(3)),
            confidence_score=self.accuracy + np.random.normal(0, 0.05),
            metadata={"model_type": "lstm", "sequence_used": context.sequence_length}
        )
    
    async def train(self, training_data):
        """Mock training"""
        await asyncio.sleep(0.1)  # Simulate training time
        return Mock(
            final_loss=0.3 + np.random.normal(0, 0.05),
            training_accuracy=self.accuracy + np.random.normal(0, 0.02),
            validation_accuracy=self.accuracy + np.random.normal(0, 0.02),
            epochs_trained=10
        )

class MockXGBoostModel:
    """Mock XGBoost model for testing"""
    
    def __init__(self, name="mock_xgboost", accuracy=0.68, latency_ms=18):
        self.name = name
        self.accuracy = accuracy
        self.latency_ms = latency_ms
        self.version = 1
        
    async def predict(self, context):
        """Mock prediction with realistic timing"""
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        # Generate realistic pitch probabilities
        pitch_probs = np.random.dirichlet(np.ones(27))
        
        # Add bias based on count state
        if context.balls >= 3:
            pitch_probs[1] += 0.15  # More breaking balls in 3-ball counts
            pitch_probs = pitch_probs / pitch_probs.sum()
        
        return MockModelPrediction(
            model_name=self.name,
            pitch_probabilities=pitch_probs,
            swing_probability=0.55 + np.random.normal(0, 0.1),
            location_prediction=np.random.dirichlet(np.ones(3)),
            confidence_score=self.accuracy + np.random.normal(0, 0.03),
            metadata={"model_type": "xgboost", "count_aware": True}
        )
    
    async def train(self, training_data):
        """Mock training"""
        await asyncio.sleep(0.05)  # Faster training for XGBoost
        return Mock(
            tier1_metrics={"accuracy": self.accuracy + np.random.normal(0, 0.02)},
            tier2_metrics={"accuracy": self.accuracy - 0.05 + np.random.normal(0, 0.02)},
            feature_importance=np.random.dirichlet(np.ones(39))
        )

class MockMarkovModel:
    """Mock Markov model for testing"""
    
    def __init__(self, name="mock_markov", accuracy=0.65, latency_ms=8):
        self.name = name
        self.accuracy = accuracy
        self.latency_ms = latency_ms
        self.version = 1
        self._cache = {}
        
    async def predict(self, context):
        """Mock prediction with caching"""
        # Create cache key
        cache_key = (context.balls, context.strikes, context.sequence_length)
        
        # Check cache
        if cache_key in self._cache:
            cached_result = self._cache[cache_key]
            cached_result.metadata["cached"] = True
            return cached_result
        
        # Simulate very fast prediction
        await asyncio.sleep(self.latency_ms / 1000.0)
        
        # Generate count-based probabilities
        pitch_probs = np.random.dirichlet(np.ones(27))
        
        # Markov models are simpler - more predictable patterns
        if context.strikes == 2:
            pitch_probs[0] += 0.2  # More fastballs with 2 strikes
            pitch_probs = pitch_probs / pitch_probs.sum()
        
        result = MockModelPrediction(
            model_name=self.name,
            pitch_probabilities=pitch_probs,
            swing_probability=0.5 + np.random.normal(0, 0.08),
            location_prediction=np.random.dirichlet(np.ones(3)),
            confidence_score=self.accuracy + np.random.normal(0, 0.02),
            metadata={"model_type": "markov", "count_state": f"{context.balls}-{context.strikes}", "cached": False}
        )
        
        # Cache result
        self._cache[cache_key] = result
        
        return result
    
    async def train(self, training_data):
        """Mock training - very fast for Markov"""
        await asyncio.sleep(0.01)
        return Mock(
            transition_matrices=1000,
            state_coverage=0.95,
            average_accuracy=self.accuracy
        )

# Test data generators
class MockDataGenerator:
    """Generates mock data for testing"""
    
    @staticmethod
    def create_training_data(model_type, sample_size=1000):
        """Create mock training data for specified model type"""
        return Mock(
            model_type=model_type,
            sample_size=sample_size,
            features=np.random.rand(sample_size, 39),  # 39 features
            targets=np.random.randint(0, 27, sample_size),  # 27 pitch types
            contexts=[MockPredictionContext() for _ in range(sample_size)]
        )
    
    @staticmethod
    def create_prediction_contexts(count=100):
        """Create diverse prediction contexts"""
        contexts = []
        
        for i in range(count):
            contexts.append(MockPredictionContext(
                sequence_length=np.random.randint(1, 10),
                balls=np.random.randint(0, 4),
                strikes=np.random.randint(0, 3),
                outs=np.random.randint(0, 3),
                inning=np.random.randint(1, 10),
                score_diff=np.random.randint(-5, 6),
                leverage_index=np.random.exponential(1.0),
                max_latency_ms=np.random.choice([50, 100, 200]),
                pitcher_id=f"pitcher_{np.random.randint(1, 100)}",
                batter_id=f"batter_{np.random.randint(1, 100)}"
            ))
        
        return contexts

# Performance measurement utilities
class PerformanceTracker:
    """Tracks performance metrics during tests"""
    
    def __init__(self):
        self.measurements = []
    
    def start_measurement(self, name: str):
        """Start timing a measurement"""
        return {
            'name': name,
            'start_time': time.time(),
            'start_memory': self._get_memory_usage()
        }
    
    def end_measurement(self, measurement: Dict[str, Any]) -> Dict[str, Any]:
        """End timing and calculate metrics"""
        end_time = time.time()
        end_memory = self._get_memory_usage()
        
        result = {
            'name': measurement['name'],
            'duration_ms': (end_time - measurement['start_time']) * 1000,
            'memory_delta_mb': end_memory - measurement['start_memory'],
            'timestamp': datetime.utcnow()
        }
        
        self.measurements.append(result)
        return result
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0

# Base test classes
class BaseModelTest:
    """Base class for model unit tests"""
    
    @pytest.fixture
    def performance_tracker(self):
        """Performance tracker fixture"""
        return PerformanceTracker()
    
    @pytest.fixture
    def mock_context(self):
        """Mock prediction context fixture"""
        return MockPredictionContext()
    
    @pytest.fixture
    def mock_contexts(self):
        """Multiple mock contexts fixture"""
        return MockDataGenerator.create_prediction_contexts(50)
    
    def assert_prediction_valid(self, prediction, expected_latency_ms=None):
        """Assert prediction has valid structure and performance"""
        assert prediction.confidence_score > 0.0
        assert prediction.confidence_score <= 1.0
        assert len(prediction.pitch_probabilities) == 27
        assert abs(np.sum(prediction.pitch_probabilities) - 1.0) < 1e-10
        assert 0.0 <= prediction.swing_probability <= 1.0
        assert len(prediction.location_prediction) == 3

# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Common test data
@pytest.fixture
def sample_models():
    """Sample models for testing"""
    return {
        'lstm': MockLSTMModel(),
        'xgboost': MockXGBoostModel(),
        'markov': MockMarkovModel()
    }
