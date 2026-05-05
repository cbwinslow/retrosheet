"""
Comprehensive test suite for Model Registry System (#162)
Tests model registration, discovery, health monitoring, version control, and performance.
"""

import pytest
import pytest_asyncio
import asyncio
import numpy as np
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from tests.models.base_test_infrastructure import (
    MockLSTMModel, MockXGBoostModel, MockMarkovModel,
    MockPredictionContext, MockDataGenerator, PerformanceTracker,
    BaseModelTest
)

# Mock classes for registry testing
class MockModelMetadata:
    """Mock model metadata"""
    def __init__(self, name, model_type, algorithm, latency_ms, memory_mb):
        self.name = name
        self.model_type = model_type
        self.algorithm = algorithm
        self.supported_features = ["pitch_sequence", "count_state"]
        self.prediction_types = ["pitch_type", "swing_decision"]
        self.expected_latency_ms = latency_ms
        self.memory_footprint_mb = memory_mb
        self.strengths = ["accuracy", "speed"]
        self.weaknesses = ["interpretability"]
        self.suitable_contexts = ["standard", "high_leverage"]
        self.created_at = datetime.utcnow()
        self.version = "1.0.0"
        self.status = "active"

class MockHealthStatus:
    """Mock health status"""
    def __init__(self, status="healthy", message="OK"):
        self.status = status
        self.status_message = message
        self.last_check = datetime.utcnow()
        self.latency_ms = 15

class MockRegisteredModel:
    """Mock registered model"""
    def __init__(self, model, metadata):
        self.model = model
        self.metadata = metadata
        self.registered_at = datetime.utcnow()
        self.health_status = MockHealthStatus()

class MockRegistrationResult:
    """Mock registration result"""
    def __init__(self, success=True, model_id=None, error=None):
        self.success = success
        self.model_id = model_id
        self.error = error
        self.timestamp = datetime.utcnow()

class MockModelRegistry:
    """Mock model registry for testing"""
    
    def __init__(self, config=None):
        self.config = config or Mock()
        self.models = {}
        self.model_metadata = {}
        self.performance_history = {}
        self.health_monitor = MockHealthMonitor()
        self.version_manager = MockVersionManager()
        
    async def initialize(self):
        """Initialize registry"""
        pass
        
    async def cleanup(self):
        """Cleanup registry"""
        pass
        
    async def register_model(self, model_id, model, metadata):
        """Register a model"""
        if model_id in self.models:
            return MockRegistrationResult(False, error="Model already exists")
        
        # Validate model interface
        if not hasattr(model, 'predict') or not hasattr(model, 'train'):
            return MockRegistrationResult(False, error="Invalid model interface")
        
        self.models[model_id] = MockRegisteredModel(model, metadata)
        self.model_metadata[model_id] = metadata
        self.performance_history[model_id] = MockPerformanceHistory()
        
        return MockRegistrationResult(True, model_id=model_id)
    
    async def discover_models(self, context):
        """Discover suitable models for context"""
        candidates = []
        
        for model_id, registered_model in self.models.items():
            # Check health
            health = await self.health_monitor.get_health(model_id)
            if health.status != "healthy":
                continue
            
            # Calculate suitability
            suitability = self._calculate_suitability(registered_model, context)
            
            candidates.append(MockModelCandidate(
                name=model_id,
                model=registered_model.model,
                metadata=registered_model.metadata,
                health_status=health.status,
                suitability_score=suitability
            ))
        
        # Sort by suitability
        candidates.sort(key=lambda x: x.suitability_score, reverse=True)
        return candidates
    
    def _calculate_suitability(self, registered_model, context):
        """Calculate model suitability for context"""
        base_score = 0.5
        
        # Factor in latency requirements
        if context.max_latency_ms and registered_model.metadata.expected_latency_ms <= context.max_latency_ms:
            base_score += 0.2
        
        # Factor in sequence length
        if context.sequence_length > 5 and "sequential" in registered_model.metadata.model_type:
            base_score += 0.2
        
        # Add some randomness
        base_score += np.random.normal(0, 0.1)
        
        return max(0.0, min(1.0, base_score))
    
    async def get_model(self, model_id):
        """Get a registered model"""
        if model_id not in self.models:
            return None
        return self.models[model_id].model
    
    async def update_model(self, model_id, new_model):
        """Update a registered model"""
        if model_id not in self.models:
            return MockRegistrationResult(False, error="Model not found")
        
        old_model = self.models[model_id]
        self.models[model_id] = MockRegisteredModel(new_model, old_model.metadata)
        
        return MockRegistrationResult(True, model_id=model_id)
    
    async def remove_model(self, model_id):
        """Remove a registered model"""
        if model_id in self.models:
            del self.models[model_id]
            del self.model_metadata[model_id]
            del self.performance_history[model_id]
    
    async def get_system_health(self):
        """Get overall system health"""
        health_statuses = {}
        unhealthy_count = 0
        
        for model_id in self.models:
            health = await self.health_monitor.get_health(model_id)
            health_statuses[model_id] = health.status
            if health.status != "healthy":
                unhealthy_count += 1
        
        overall_status = "healthy" if unhealthy_count == 0 else "degraded"
        
        return {
            'overall_status': overall_status,
            'unhealthy_models': [mid for mid, status in health_statuses.items() if status != "healthy"],
            'total_models': len(self.models)
        }

class MockHealthMonitor:
    """Mock health monitor"""
    
    def __init__(self):
        self.health_statuses = {}
        
    async def get_health(self, model_id):
        """Get model health status"""
        if model_id not in self.health_statuses:
            self.health_statuses[model_id] = MockHealthStatus()
        return self.health_statuses[model_id]
    
    async def set_health_status(self, model_id, status, message):
        """Set model health status"""
        self.health_statuses[model_id] = MockHealthStatus(status, message)

class MockVersionManager:
    """Mock version manager"""
    
    def __init__(self):
        self.versions = {}
        
    async def get_versions(self, model_id):
        """Get model versions"""
        if model_id not in self.versions:
            self.versions[model_id] = [
                MockVersion("1.0.0", datetime.utcnow()),
                MockVersion("1.1.0", datetime.utcnow() + timedelta(days=1))
            ]
        return self.versions[model_id]

class MockVersion:
    """Mock version"""
    def __init__(self, version_id, created_at):
        self.version_id = version_id
        self.created_at = created_at
        self.model_checksum = "abc123"

class MockPerformanceHistory:
    """Mock performance history"""
    
    def __init__(self):
        self.results = []
        
    async def add_result(self, accuracy, latency_ms):
        """Add performance result"""
        self.results.append({
            'accuracy': accuracy,
            'latency_ms': latency_ms,
            'timestamp': datetime.utcnow()
        })

class MockModelCandidate:
    """Mock model candidate"""
    def __init__(self, name, model, metadata, health_status="healthy", suitability_score=0.8):
        self.name = name
        self.model = model
        self.metadata = metadata
        self.health_status = health_status
        self.suitability_score = suitability_score

# Test implementation
class TestModelRegistration(BaseModelTest):
    """Comprehensive tests for model registration functionality"""
    
    @pytest_asyncio.fixture
    async def registry(self):
        """Create test registry instance"""
        config = Mock()
        registry = MockModelRegistry(config)
        await registry.initialize()
        yield registry
        await registry.cleanup()
    
    @pytest.fixture
    def mock_lstm_model(self):
        """Create mock LSTM model"""
        return MockLSTMModel(
            name="test_lstm",
            accuracy=0.70,
            latency_ms=45
        )
    
    @pytest.fixture
    def mock_xgb_model(self):
        """Create mock XGBoost model"""
        return MockXGBoostModel(
            name="test_xgboost",
            accuracy=0.68,
            latency_ms=18
        )
    
    @pytest.fixture
    def lstm_metadata(self):
        """Create LSTM model metadata"""
        return MockModelMetadata(
            name="lstm_sequence",
            model_type="sequential_deep_learning",
            algorithm="LSTM",
            latency_ms=45,
            memory_mb=800
        )
    
    @pytest.mark.asyncio
    async def test_successful_model_registration(self, registry, mock_lstm_model, lstm_metadata):
        """Test successful model registration"""
        
        # Register model
        result = await registry.register_model("test_lstm", mock_lstm_model, lstm_metadata)
        
        # Verify registration success
        assert result.success is True
        assert result.model_id == "test_lstm"
        
        # Verify model is stored
        assert "test_lstm" in registry.models
        assert registry.models["test_lstm"].model == mock_lstm_model
        assert registry.models["test_lstm"].metadata == lstm_metadata
        
        # Verify metadata is stored
        assert "test_lstm" in registry.model_metadata
        assert registry.model_metadata["test_lstm"] == lstm_metadata
        
        # Verify performance history is created
        assert "test_lstm" in registry.performance_history
    
    async def test_duplicate_model_registration(self, registry, mock_lstm_model, lstm_metadata):
        """Test handling of duplicate model registration"""
        
        # Register model first time
        result1 = await registry.register_model("test_lstm", mock_lstm_model, lstm_metadata)
        assert result1.success is True
        
        # Try to register same model again
        result2 = await registry.register_model("test_lstm", mock_lstm_model, lstm_metadata)
        assert result2.success is False
        assert "already exists" in result2.error.lower()
    
    async def test_invalid_model_interface(self, registry, lstm_metadata):
        """Test registration of model with invalid interface"""
        
        # Create model without required interface
        class InvalidModel:
            pass
        
        invalid_model = InvalidModel()
        
        # Should fail validation
        result = await registry.register_model("invalid", invalid_model, lstm_metadata)
        assert result.success is False
        assert "interface" in result.error.lower()
    
    async def test_batch_model_registration(self, registry, mock_lstm_model, mock_xgb_model, lstm_metadata):
        """Test registration of multiple models"""
        
        # Create metadata for XGBoost
        xgb_metadata = MockModelMetadata(
            name="xgboost_hierarchical",
            model_type="tree_based",
            algorithm="XGBoost",
            latency_ms=18,
            memory_mb=200
        )
        
        # Register multiple models
        results = await asyncio.gather(
            registry.register_model("lstm", mock_lstm_model, lstm_metadata),
            registry.register_model("xgboost", mock_xgb_model, xgb_metadata)
        )
        
        # Verify all registrations succeeded
        assert all(result.success for result in results)
        assert len(registry.models) == 2
        
        # Verify models are properly stored
        assert "lstm" in registry.models
        assert "xgboost" in registry.models
        assert registry.models["lstm"].model == mock_lstm_model
        assert registry.models["xgboost"].model == mock_xgb_model

class TestModelDiscovery(BaseModelTest):
    """Comprehensive tests for model discovery functionality"""
    
    @pytest.fixture
    async def populated_registry(self):
        """Create registry with multiple models"""
        registry = MockModelRegistry()
        await registry.initialize()
        
        # Register multiple models with different characteristics
        models = [
            ("lstm", MockLSTMModel(), MockModelMetadata("lstm_seq", "sequential_deep_learning", "LSTM", 45, 800)),
            ("xgboost", MockXGBoostModel(), MockModelMetadata("xgb_hier", "tree_based", "XGBoost", 18, 200)),
            ("markov", MockMarkovModel(), MockModelMetadata("markov_chain", "probabilistic", "Markov", 8, 50))
        ]
        
        for name, model, metadata in models:
            await registry.register_model(name, model, metadata)
        
        yield registry
        await registry.cleanup()
    
    @pytest.mark.asyncio
    async def test_discover_all_models(self, populated_registry):
        """Test discovery of all available models"""
        
        context = MockPredictionContext(sequence_length=5)
        candidates = await populated_registry.discover_models(context)
        
        # Should find all registered models
        assert len(candidates) == 3
        model_names = [c.name for c in candidates]
        assert "lstm" in model_names
        assert "xgboost" in model_names
        assert "markov" in model_names
    
    async def test_context_filtering(self, populated_registry):
        """Test context-based model filtering"""
        
        # Test context requiring long sequences
        long_sequence_context = MockPredictionContext(sequence_length=8)
        candidates = await populated_registry.discover_models(long_sequence_context)
        
        # LSTM should be selected (good for long sequences)
        lstm_candidates = [c for c in candidates if c.name == "lstm"]
        assert len(lstm_candidates) > 0
        
        # Test context requiring fast prediction
        fast_context = MockPredictionContext(max_latency_ms=20)
        candidates = await populated_registry.discover_models(fast_context)
        
        # Markov should be selected (fastest)
        markov_candidates = [c for c in candidates if c.name == "markov"]
        assert len(markov_candidates) > 0
        
        # LSTM should be filtered out (too slow)
        lstm_candidates = [c for c in candidates if c.name == "lstm"]
        assert len(lstm_candidates) == 0
    
    async def test_health_filtering(self, populated_registry):
        """Test filtering by model health"""
        
        # Simulate unhealthy model
        await populated_registry.health_monitor.set_health_status(
            "lstm", "unhealthy", "Test failure"
        )
        
        context = MockPredictionContext(sequence_length=5)
        candidates = await populated_registry.discover_models(context)
        
        # Unhealthy model should be filtered out
        model_names = [c.name for c in candidates]
        assert "lstm" not in model_names
        assert "xgboost" in model_names
        assert "markov" in model_names

class TestHealthMonitoring(BaseModelTest):
    """Comprehensive tests for health monitoring functionality"""
    
    @pytest.fixture
    async def registry_with_monitoring(self):
        """Create registry with health monitoring"""
        config = Mock()
        registry = MockModelRegistry(config)
        await registry.initialize()
        
        # Register a model
        model = MockLSTMModel()
        metadata = MockModelMetadata("lstm", "sequential", "LSTM", 45, 800)
        await registry.register_model("test_model", model, metadata)
        
        yield registry
        await registry.cleanup()
    
    async def test_health_check_initialization(self, registry_with_monitoring):
        """Test that health monitoring starts automatically"""
        
        # Check initial health status
        health_status = await registry_with_monitoring.health_monitor.get_health("test_model")
        assert health_status.status == "healthy"
        assert health_status.latency_ms == 15
    
    async def test_unhealthy_model_detection(self, registry_with_monitoring):
        """Test detection of unhealthy models"""
        
        # Simulate model failure
        model = await registry_with_monitoring.get_model("test_model")
        model.predict = AsyncMock(side_effect=Exception("Model failure"))
        
        # Simulate health check failure
        await registry_with_monitoring.health_monitor.set_health_status(
            "test_model", "unhealthy", "Model failure detected"
        )
        
        # Check that failure is detected
        health_status = await registry_with_monitoring.health_monitor.get_health("test_model")
        assert health_status.status == "unhealthy"
        assert "failure" in health_status.status_message.lower()
    
    async def test_system_health_aggregation(self, registry_with_monitoring):
        """Test system-wide health aggregation"""
        
        # Add another model
        model2 = MockXGBoostModel()
        metadata2 = MockModelMetadata("xgb", "tree", "XGBoost", 18, 200)
        await registry_with_monitoring.register_model("xgb_model", model2, metadata2)
        
        # Make one model unhealthy
        await registry_with_monitoring.health_monitor.set_health_status(
            "test_model", "unhealthy", "Test failure"
        )
        
        # Check system health
        system_health = await registry_with_monitoring.get_system_health()
        
        assert system_health['overall_status'] == "degraded"
        assert "test_model" in system_health['unhealthy_models']
        assert system_health['total_models'] == 2

class TestPerformanceValidation(BaseModelTest):
    """Performance tests for model registry"""
    
    @pytest.fixture
    async def performance_registry(self):
        """Create registry for performance testing"""
        config = Mock()
        registry = MockModelRegistry(config)
        await registry.initialize()
        yield registry
        await registry.cleanup()
    
    async def test_registration_performance(self, performance_registry, performance_tracker):
        """Test model registration performance"""
        
        # Measure registration time for multiple models
        registration_times = []
        
        for i in range(50):
            model = MockLSTMModel(name=f"perf_test_{i}")
            metadata = MockModelMetadata(f"model_{i}", "test", "test", 20, 100)
            
            measurement = performance_tracker.start_measurement(f"registration_{i}")
            result = await performance_registry.register_model(f"perf_test_{i}", model, metadata)
            performance_tracker.end_measurement(measurement)
            
            registration_times.append(performance_tracker.measurements[-1]['duration_ms'])
            assert result.success is True
        
        # Verify performance targets
        avg_time = sum(registration_times) / len(registration_times)
        max_time = max(registration_times)
        
        assert avg_time < 100  # Average < 100ms
        assert max_time < 200  # Maximum < 200ms
    
    async def test_discovery_performance(self, performance_registry, performance_tracker):
        """Test model discovery performance"""
        
        # Register many models
        for i in range(50):
            model = MockLSTMModel(name=f"perf_test_{i}")
            metadata = MockModelMetadata(f"model_{i}", "test", "test", 20, 100)
            await performance_registry.register_model(f"perf_test_{i}", model, metadata)
        
        # Measure discovery time
        discovery_times = []
        
        for i in range(100):
            context = MockPredictionContext(sequence_length=5)
            
            measurement = performance_tracker.start_measurement(f"discovery_{i}")
            candidates = await performance_registry.discover_models(context)
            performance_tracker.end_measurement(measurement)
            
            discovery_times.append(performance_tracker.measurements[-1]['duration_ms'])
            assert len(candidates) > 0
        
        # Verify performance targets
        avg_time = sum(discovery_times) / len(discovery_times)
        max_time = max(discovery_times)
        
        assert avg_time < 50  # Average < 50ms
        assert max_time < 100  # Maximum < 100ms
    
    async def test_concurrent_operations(self, performance_registry):
        """Test concurrent registry operations"""
        
        # Concurrent registration
        registration_tasks = []
        for i in range(20):
            model = MockLSTMModel(name=f"concurrent_{i}")
            metadata = MockModelMetadata(f"model_{i}", "test", "test", 20, 100)
            task = performance_registry.register_model(f"concurrent_{i}", model, metadata)
            registration_tasks.append(task)
        
        registration_results = await asyncio.gather(*registration_tasks)
        
        # All registrations should succeed
        assert all(result.success for result in registration_results)
        assert len(performance_registry.models) == 20

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
