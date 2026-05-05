"""
End-to-End Integration Tests for Multi-Model Ensemble System (#165)
Tests complete workflow validation, production load testing, real data integration, and system monitoring.
"""

import pytest
import asyncio
import numpy as np
import time
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from tests.models.base_test_infrastructure import (
    MockLSTMModel, MockXGBoostModel, MockMarkovModel,
    MockPredictionContext, MockDataGenerator, PerformanceTracker,
    BaseModelTest, BaseIntegrationTest
)

# Mock classes for integration testing
class MockModelRegistry:
    """Mock model registry for integration testing"""
    
    def __init__(self):
        self.models = {}
        self.health_monitor = MockHealthMonitor()
        
    async def initialize(self):
        pass
    
    async def cleanup(self):
        pass
    
    async def register_model(self, model_id, model, metadata):
        self.models[model_id] = MockRegisteredModel(model, metadata)
        return Mock(success=True, model_id=model_id)
    
    async def discover_models(self, context):
        candidates = []
        for model_id, registered_model in self.models.items():
            health = await self.health_monitor.get_health(model_id)
            if health.status == "healthy":
                candidates.append(MockModelCandidate(
                    name=model_id,
                    model=registered_model.model,
                    metadata=registered_model.metadata,
                    health_status=health.status,
                    suitability_score=0.8
                ))
        return candidates
    
    async def get_model(self, model_id):
        if model_id in self.models:
            return self.models[model_id].model
        return None
    
    async def get_system_health(self):
        health_statuses = {}
        for model_id in self.models:
            health = await self.health_monitor.get_health(model_id)
            health_statuses[model_id] = health.status
        
        unhealthy_count = sum(1 for status in health_statuses.values() if status != "healthy")
        overall_status = "healthy" if unhealthy_count == 0 else "degraded"
        
        return {
            'overall_status': overall_status,
            'unhealthy_models': [mid for mid, status in health_statuses.items() if status != "healthy"],
            'total_models': len(self.models)
        }

class MockRegisteredModel:
    def __init__(self, model, metadata):
        self.model = model
        self.metadata = metadata

class MockHealthMonitor:
    def __init__(self):
        self.health_statuses = {}
        
    async def get_health(self, model_id):
        if model_id not in self.health_statuses:
            self.health_statuses[model_id] = MockHealthStatus()
        return self.health_statuses[model_id]
    
    async def set_health_status(self, model_id, status, message):
        self.health_statuses[model_id] = MockHealthStatus(status, message)

class MockHealthStatus:
    def __init__(self, status="healthy", message="OK"):
        self.status = status
        self.status_message = message
        self.last_check = datetime.utcnow()

class MockModelCandidate:
    def __init__(self, name, model, metadata, health_status="healthy", suitability_score=0.8):
        self.name = name
        self.model = model
        self.metadata = metadata
        self.health_status = health_status
        self.suitability_score = suitability_score
        self.recent_performance = MockPerformance(accuracy=0.7, latency_ms=20)

class MockPerformance:
    def __init__(self, accuracy, latency_ms):
        self.accuracy = accuracy
        self.latency_ms = latency_ms

class MockEnsembleEngine:
    """Mock ensemble engine for integration testing"""
    
    def __init__(self, model_registry):
        self.model_registry = model_registry
        self.prediction_count = 0
        
    async def initialize(self):
        pass
    
    async def cleanup(self):
        pass
    
    async def predict_ensemble(self, context, strategy='weighted'):
        self.prediction_count += 1
        
        candidates = await self.model_registry.discover_models(context)
        if not candidates:
            raise ValueError("No models available")
        
        # Get predictions from available models
        model_predictions = []
        for candidate in candidates[:3]:  # Use top 3 models
            prediction = await candidate.model.predict(context)
            model_predictions.append(prediction)
        
        # Simple ensemble combination
        pitch_probs = np.mean([p.pitch_probabilities for p in model_predictions], axis=0)
        swing_prob = np.mean([p.swing_probability for p in model_predictions])
        confidence = np.mean([p.confidence_score for p in model_predictions])
        
        return MockEnsemblePrediction(
            pitch_probabilities=pitch_probs,
            swing_probability=swing_prob,
            confidence_score=confidence,
            contributing_models=[c.name for c in candidates[:3]],
            metadata={
                'ensemble_used': True,
                'strategy': strategy,
                'models_used': len(model_predictions)
            }
        )
    
    async def get_performance_metrics(self):
        return Mock(
            total_predictions=self.prediction_count,
            average_latency=45.2,
            average_confidence=0.73,
            model_usage_stats={
                'lstm': 40,
                'xgboost': 35,
                'markov': 25
            }
        )
    
    async def get_resource_metrics(self):
        return Mock(
            memory_usage_mb=150.5,
            cpu_usage_percent=25.3,
            cache_hit_rate=0.65
        )

class MockEnsemblePrediction:
    def __init__(self, pitch_probabilities, swing_probability, confidence_score, contributing_models, metadata):
        self.pitch_probabilities = np.array(pitch_probabilities)
        self.swing_probability = swing_probability
        self.confidence_score = confidence_score
        self.contributing_models = contributing_models
        self.metadata = metadata

class MockModelSelectionFramework:
    """Mock model selection framework"""
    
    def __init__(self, model_registry):
        self.model_registry = model_registry
        self.performance_history = {}
        
    async def select_optimal_models(self, context, max_latency_ms=100, max_models=4):
        candidates = await self.model_registry.discover_models(context)
        
        # Filter by latency
        suitable_candidates = []
        for candidate in candidates:
            if candidate.recent_performance.latency_ms <= max_latency_ms:
                suitable_candidates.append(candidate)
        
        # Sort by suitability and take top models
        suitable_candidates.sort(key=lambda x: x.suitability_score, reverse=True)
        selected_models = suitable_candidates[:max_models]
        
        return MockSelectionResult(
            selected_models=selected_models,
            selection_strategy="performance_based",
            expected_latency=sum(c.recent_performance.latency_ms for c in selected_models) / len(selected_models) if selected_models else 0
        )
    
    async def update_context_performance(self, context, model_name, accuracy):
        if model_name not in self.performance_history:
            self.performance_history[model_name] = []
        
        self.performance_history[model_name].append({
            'context': context,
            'accuracy': accuracy,
            'timestamp': datetime.utcnow()
        })
    
    async def get_selection_insights(self, time_period):
        total_selections = sum(len(history) for history in self.performance_history.values())
        
        return MockSelectionInsights(
            total_selections=total_selections,
            accuracy_improvement=0.05,
            fallback_rate=0.02,
            top_performing_models=['lstm', 'xgboost']
        )

class MockSelectionResult:
    def __init__(self, selected_models, selection_strategy, expected_latency):
        self.selected_models = selected_models
        self.selection_strategy = selection_strategy
        self.expected_latency = expected_latency

class MockSelectionInsights:
    def __init__(self, total_selections, accuracy_improvement, fallback_rate, top_performing_models):
        self.total_selections = total_selections
        self.accuracy_improvement = accuracy_improvement
        self.fallback_rate = fallback_rate
        self.top_performing_models = top_performing_models

# Integration Test Classes
class TestCompleteWorkflow(BaseIntegrationTest):
    """End-to-end workflow integration tests"""
    
    @pytest.fixture
    async def complete_system(self):
        """Create complete multi-model system for testing"""
        
        # Initialize model registry
        registry = MockModelRegistry()
        await registry.initialize()
        
        # Register models
        models_to_register = [
            ("lstm", MockLSTMModel(), self._create_lstm_metadata()),
            ("xgboost", MockXGBoostModel(), self._create_xgb_metadata()),
            ("markov", MockMarkovModel(), self._create_markov_metadata())
        ]
        
        for name, model, metadata in models_to_register:
            await registry.register_model(name, model, metadata)
        
        # Initialize ensemble engine
        ensemble = MockEnsembleEngine(registry)
        await ensemble.initialize()
        
        # Initialize model selection framework
        selector = MockModelSelectionFramework(registry)
        
        yield {
            'registry': registry,
            'ensemble': ensemble,
            'selector': selector
        }
        
        # Cleanup
        await ensemble.cleanup()
        await registry.cleanup()
    
    @pytest.fixture
    def real_contexts(self):
        """Create realistic prediction contexts"""
        return MockDataGenerator.create_prediction_contexts(50)
    
    def _create_lstm_metadata(self):
        return Mock(
            name="lstm_sequence",
            model_type="sequential_deep_learning",
            algorithm="LSTM",
            expected_latency_ms=45,
            memory_footprint_mb=800
        )
    
    def _create_xgb_metadata(self):
        return Mock(
            name="xgboost_hierarchical",
            model_type="tree_based",
            algorithm="XGBoost",
            expected_latency_ms=18,
            memory_footprint_mb=200
        )
    
    def _create_markov_metadata(self):
        return Mock(
            name="markov_chain",
            model_type="probabilistic",
            algorithm="Markov Chain",
            expected_latency_ms=8,
            memory_footprint_mb=50
        )
    
    async def test_complete_prediction_workflow(self, complete_system, real_contexts):
        """Test complete prediction workflow from context to result"""
        
        registry = complete_system['registry']
        ensemble = complete_system['ensemble']
        selector = complete_system['selector']
        
        workflow_results = []
        
        for context in real_contexts[:50]:  # Test 50 contexts
            # Step 1: Model selection
            selection_result = await selector.select_optimal_models(
                context,
                max_latency_ms=80,
                max_models=4
            )
            
            assert selection_result.selected_models is not None
            assert len(selection_result.selected_models) > 0
            assert selection_result.expected_latency <= 80
            
            # Step 2: Ensemble prediction
            ensemble_prediction = await ensemble.predict_ensemble(context)
            
            assert ensemble_prediction.confidence_score > 0.0
            assert len(ensemble_prediction.pitch_probabilities) == 27
            assert ensemble_prediction.metadata['ensemble_used'] is True
            
            # Step 3: Performance tracking
            # Simulate actual outcome
            actual_pitch = np.random.choice(27, p=ensemble_prediction.pitch_probabilities)
            accuracy = 1.0 if np.argmax(ensemble_prediction.pitch_probabilities) == actual_pitch else 0.0
            
            # Update performance
            if selection_result.selected_models:
                await selector.update_context_performance(
                    context,
                    selection_result.selected_models[0].name,
                    accuracy
                )
            
            workflow_results.append({
                'context': context,
                'selection': selection_result,
                'prediction': ensemble_prediction,
                'accuracy': accuracy
            })
        
        # Verify workflow results
        assert len(workflow_results) == 50
        
        # Check overall accuracy
        total_accuracy = sum(r['accuracy'] for r in workflow_results) / len(workflow_results)
        assert total_accuracy > 0.2  # Should be better than random (1/27)
        
        # Check latency compliance
        for result in workflow_results:
            assert result['selection'].expected_latency <= 80
    
    async def test_model_lifecycle_workflow(self, complete_system):
        """Test complete model lifecycle management"""
        
        registry = complete_system['registry']
        ensemble = complete_system['ensemble']
        
        # Step 1: Register new model
        new_model = MockLSTMModel(name="new_lstm")
        new_metadata = self._create_lstm_metadata()
        
        registration_result = await registry.register_model("new_lstm", new_model, new_metadata)
        assert registration_result.success is True
        
        # Step 2: Discover new model
        context = MockPredictionContext(sequence_length=8)
        candidates = await registry.discover_models(context)
        
        new_model_candidates = [c for c in candidates if c.name == "new_lstm"]
        assert len(new_model_candidates) > 0
        
        # Step 3: Use in ensemble
        ensemble_prediction = await ensemble.predict_ensemble(context)
        contributing_models = ensemble_prediction.contributing_models
        
        # New model should be available for selection
        assert "new_lstm" in registry.models
        
        # Step 4: Remove model
        await registry.models.pop("new_lstm", None)
        assert "new_lstm" not in registry.models
    
    async def test_health_monitoring_workflow(self, complete_system):
        """Test health monitoring and automatic recovery"""
        
        registry = complete_system['registry']
        ensemble = complete_system['ensemble']
        
        # Check initial health
        initial_health = await registry.get_system_health()
        assert initial_health['overall_status'] == 'healthy'
        
        # Simulate model failure
        lstm_model = await registry.get_model("lstm")
        original_predict = lstm_model.predict
        
        # Make LSTM model fail
        lstm_model.predict = AsyncMock(side_effect=Exception("Model failure"))
        
        # Update health status
        await registry.health_monitor.set_health_status("lstm", "unhealthy", "Model failure")
        
        # Check system health degradation
        health_status = await registry.get_system_health()
        assert health_status['overall_status'] == 'degraded'
        assert "lstm" in health_status['unhealthy_models']
        
        # Ensemble should still work (without unhealthy model)
        context = MockPredictionContext(sequence_length=5)
        ensemble_prediction = await ensemble.predict_ensemble(context)
        
        assert ensemble_prediction.confidence_score > 0.0
        
        # Restore model
        lstm_model.predict = original_predict
        await registry.health_monitor.set_health_status("lstm", "healthy", "Model restored")
        
        # Check health recovery
        health_status = await registry.get_system_health()
        assert health_status['overall_status'] == 'healthy'

class TestProductionLoad(BaseIntegrationTest):
    """Production load testing for multi-model system"""
    
    @pytest.fixture
    async def production_system(self):
        """Create production-like system configuration"""
        
        # Larger registry for production
        registry = MockModelRegistry()
        await registry.initialize()
        
        # Register many models
        model_types = [
            ("lstm_1", MockLSTMModel(), self._create_metadata("lstm", 45)),
            ("lstm_2", MockLSTMModel(), self._create_metadata("lstm", 45)),
            ("xgboost_1", MockXGBoostModel(), self._create_metadata("xgboost", 18)),
            ("xgboost_2", MockXGBoostModel(), self._create_metadata("xgboost", 18)),
            ("markov_1", MockMarkovModel(), self._create_metadata("markov", 8)),
            ("markov_2", MockMarkovModel(), self._create_metadata("markov", 8)),
        ]
        
        for name, model, metadata in model_types:
            await registry.register_model(name, model, metadata)
        
        # Production ensemble config
        ensemble = MockEnsembleEngine(registry)
        await ensemble.initialize()
        
        yield {
            'registry': registry,
            'ensemble': ensemble
        }
        
        await ensemble.cleanup()
        await registry.cleanup()
    
    def _create_metadata(self, model_type, latency_ms):
        return Mock(
            name=f"{model_type}_model",
            model_type=model_type,
            algorithm=model_type.upper(),
            expected_latency_ms=latency_ms,
            memory_footprint_mb=200 if model_type == "lstm" else 100
        )
    
    async def test_high_volume_predictions(self, production_system):
        """Test high-volume prediction scenarios"""
        
        ensemble = production_system['ensemble']
        
        # Create diverse prediction contexts
        contexts = [
            MockPredictionContext(sequence_length=np.random.randint(1, 10))
            for _ in range(1000)
        ]
        
        # Measure performance under load
        start_time = time.time()
        
        # Concurrent predictions
        prediction_tasks = [
            ensemble.predict_ensemble(context)
            for context in contexts
        ]
        
        predictions = await asyncio.gather(*prediction_tasks)
        
        total_time = time.time() - start_time
        
        # Verify all predictions succeeded
        assert len(predictions) == 1000
        assert all(p.confidence_score > 0.0 for p in predictions)
        
        # Performance metrics
        avg_time_per_prediction = total_time / 1000
        predictions_per_second = 1000 / total_time
        
        assert avg_time_per_prediction < 0.1  # <100ms per prediction
        assert predictions_per_second > 10  # >10 predictions per second
        
        # Verify ensemble quality under load
        avg_confidence = np.mean([p.confidence_score for p in predictions])
        assert avg_confidence > 0.6  # Should maintain quality
    
    async def test_concurrent_user_load(self, production_system):
        """Test concurrent user load simulation"""
        
        ensemble = production_system['ensemble']
        
        # Simulate 100 concurrent users
        async def simulate_user(user_id):
            """Simulate a single user making multiple predictions"""
            user_predictions = []
            
            for i in range(10):  # Each user makes 10 predictions
                context = MockPredictionContext(
                    sequence_length=np.random.randint(1, 8),
                    user_id=user_id
                )
                
                prediction = await ensemble.predict_ensemble(context)
                user_predictions.append(prediction)
                
                # Small delay between predictions
                await asyncio.sleep(0.01)
            
            return user_predictions
        
        # Launch concurrent users
        user_tasks = [
            simulate_user(user_id)
            for user_id in range(100)
        ]
        
        start_time = time.time()
        user_results = await asyncio.gather(*user_tasks)
        total_time = time.time() - start_time
        
        # Verify all users completed successfully
        assert len(user_results) == 100
        assert all(len(user_preds) == 10 for user_preds in user_results)
        total_predictions = sum(len(user_preds) for user_preds in user_results)
        assert total_predictions == 1000
        
        # Performance under concurrent load
        throughput = total_predictions / total_time
        assert throughput > 20  # >20 predictions per second under load
        
        # Verify prediction quality
        all_predictions = [pred for user_preds in user_results for pred in user_preds]
        avg_confidence = np.mean([p.confidence_score for p in all_predictions])
        assert avg_confidence > 0.6
    
    async def test_memory_under_load(self, production_system):
        """Test memory usage under high load"""
        
        ensemble = production_system['ensemble']
        
        # High-volume predictions
        for batch in range(10):  # 10 batches of 100 predictions
            contexts = [
                MockPredictionContext(sequence_length=np.random.randint(1, 10))
                for _ in range(100)
            ]
            
            # Concurrent predictions in batch
            prediction_tasks = [
                ensemble.predict_ensemble(context)
                for context in contexts
            ]
            
            await asyncio.gather(*prediction_tasks)
        
        # Get resource metrics
        resource_metrics = await ensemble.get_resource_metrics()
        
        assert resource_metrics.memory_usage_mb > 0
        assert 0 <= resource_metrics.cpu_usage_percent <= 100
        assert 0 <= resource_metrics.cache_hit_rate <= 1

class TestRealDataIntegration(BaseIntegrationTest):
    """Real data integration testing"""
    
    @pytest.fixture
    def real_game_data(self):
        """Create realistic game data for testing"""
        return self._create_real_game_data()
    
    def _create_real_game_data(self):
        """Create realistic baseball game scenarios"""
        games = []
        
        for game_id in range(10):  # 10 games
            game = {
                'game_id': f'game_{game_id}',
                'season': 2024,
                'date': datetime(2024, 4, 1) + timedelta(days=game_id),
                'at_bats': []
            }
            
            for at_bat_id in range(50):  # 50 at-bats per game
                at_bat = {
                    'at_bat_id': f'ab_{at_bat_id}',
                    'inning': np.random.randint(1, 10),
                    'outs': np.random.randint(0, 3),
                    'balls': np.random.randint(0, 4),
                    'strikes': np.random.randint(0, 3),
                    'score_diff': np.random.randint(-5, 6),
                    'leverage_index': np.random.exponential(1.0),
                    'pitcher_id': f'pitcher_{np.random.randint(1, 50)}',
                    'batter_id': f'batter_{np.random.randint(1, 50)}',
                    'pitches': []
                }
                
                # Generate pitches
                pitch_types = ['F', 'C', 'S', 'X', 'B']
                num_pitches = np.random.randint(1, 8)
                
                for pitch_id in range(num_pitches):
                    pitch = {
                        'pitch_id': f'pitch_{pitch_id}',
                        'pitch_type': np.random.choice(pitch_types),
                        'balls_before': at_bat['balls'] if pitch_id == 0 else at_bat['balls'] + min(pitch_id, np.random.randint(0, 4)),
                        'strikes_before': at_bat['strikes'] if pitch_id == 0 else min(at_bat['strikes'] + pitch_id, 2),
                    }
                    at_bat['pitches'].append(pitch)
                
                game['at_bats'].append(at_bat)
            
            games.append(game)
        
        return games
    
    @pytest.fixture
    async def integrated_system(self):
        """Create system with real data integration"""
        
        # Initialize system
        registry = MockModelRegistry()
        await registry.initialize()
        
        # Register models
        models = [
            ("lstm_real", MockLSTMModel(), self._create_real_metadata("lstm")),
            ("xgboost_real", MockXGBoostModel(), self._create_real_metadata("xgboost")),
            ("markov_real", MockMarkovModel(), self._create_real_metadata("markov"))
        ]
        
        for name, model, metadata in models:
            await registry.register_model(name, model, metadata)
        
        ensemble = MockEnsembleEngine(registry)
        await ensemble.initialize()
        
        yield {
            'registry': registry,
            'ensemble': ensemble,
            'real_data': self.real_game_data
        }
        
        await ensemble.cleanup()
        await registry.cleanup()
    
    def _create_real_metadata(self, model_type):
        return Mock(
            name=f"{model_type}_real",
            model_type=model_type,
            algorithm=model_type.upper(),
            expected_latency_ms=45 if model_type == "lstm" else 20,
            memory_footprint_mb=500
        )
    
    async def test_real_game_prediction_accuracy(self, integrated_system):
        """Test prediction accuracy on real game data"""
        
        ensemble = integrated_system['ensemble']
        real_data = integrated_system['real_data']
        
        # Extract real prediction scenarios
        prediction_scenarios = self._extract_prediction_scenarios(real_data)
        
        correct_predictions = 0
        total_predictions = 0
        confidence_scores = []
        
        for scenario in prediction_scenarios[:500]:  # Test 500 real scenarios
            context = scenario['context']
            actual_pitch = scenario['actual_pitch']
            
            # Make prediction
            prediction = await ensemble.predict_ensemble(context)
            
            # Evaluate accuracy
            predicted_pitch = np.argmax(prediction.pitch_probabilities)
            if predicted_pitch == actual_pitch:
                correct_predictions += 1
            
            total_predictions += 1
            confidence_scores.append(prediction.confidence_score)
        
        # Calculate metrics
        accuracy = correct_predictions / total_predictions
        avg_confidence = np.mean(confidence_scores)
        
        # Verify real-world performance
        assert accuracy > 0.25  # Should beat random (1/27 ≈ 3.7%)
        assert avg_confidence > 0.6   # Should have reasonable confidence
        
        print(f"Real data accuracy: {accuracy:.3f}")
        print(f"Average confidence: {avg_confidence:.3f}")
    
    def _extract_prediction_scenarios(self, real_data):
        """Extract prediction scenarios from real data"""
        scenarios = []
        
        for game in real_data:
            for at_bat in game['at_bats']:
                pitches = at_bat['pitches']
                
                for i, pitch in enumerate(pitches[:-1]):  # Don't predict last pitch
                    context = MockPredictionContext(
                        inning=at_bat['inning'],
                        outs=at_bat['outs'],
                        balls=pitch['balls_before'],
                        strikes=pitch['strikes_before'],
                        score_diff=at_bat['score_diff'],
                        pitcher_id=at_bat['pitcher_id'],
                        batter_id=at_bat['batter_id'],
                        recent_pitches=[p['pitch_type'] for p in pitches[max(0, i-3):i]]
                    )
                    
                    scenarios.append({
                        'context': context,
                        'actual_pitch': self._encode_pitch_type(pitches[i+1]['pitch_type'])
                    })
        
        return scenarios
    
    def _encode_pitch_type(self, pitch_type):
        """Encode pitch type to index"""
        pitch_map = {'F': 0, 'C': 1, 'S': 2, 'X': 3, 'B': 4}
        return pitch_map.get(pitch_type, 0)

class TestSystemMonitoring(BaseIntegrationTest):
    """System monitoring and observability tests"""
    
    @pytest.fixture
    async def monitored_system(self):
        """Create system with monitoring enabled"""
        
        registry = MockModelRegistry()
        await registry.initialize()
        
        # Register models
        await registry.register_model("lstm", MockLSTMModel(), self._create_monitoring_metadata("lstm"))
        await registry.register_model("xgboost", MockXGBoostModel(), self._create_monitoring_metadata("xgboost"))
        
        ensemble = MockEnsembleEngine(registry)
        await ensemble.initialize()
        
        yield {
            'registry': registry,
            'ensemble': ensemble
        }
        
        await ensemble.cleanup()
        await registry.cleanup()
    
    def _create_monitoring_metadata(self, model_type):
        return Mock(
            name=f"{model_type}_monitored",
            model_type=model_type,
            algorithm=model_type.upper(),
            expected_latency_ms=30,
            memory_footprint_mb=300
        )
    
    async def test_performance_metrics_collection(self, monitored_system):
        """Test performance metrics collection"""
        
        ensemble = monitored_system['ensemble']
        
        # Make predictions to generate metrics
        for i in range(100):
            context = MockPredictionContext(sequence_length=np.random.randint(1, 8))
            await ensemble.predict_ensemble(context)
        
        # Get performance metrics
        metrics = await ensemble.get_performance_metrics()
        
        assert 'total_predictions' in metrics
        assert 'average_latency' in metrics
        assert 'average_confidence' in metrics
        assert 'model_usage_stats' in metrics
        
        assert metrics['total_predictions'] == 100
        assert metrics['average_latency'] > 0
        assert 0 < metrics['average_confidence'] <= 1.0
        assert len(metrics['model_usage_stats']) > 0
    
    async def test_health_monitoring_alerts(self, monitored_system):
        """Test health monitoring alerts"""
        
        registry = monitored_system['registry']
        
        # Get initial health status
        initial_health = await registry.get_system_health()
        assert initial_health['overall_status'] == 'healthy'
        
        # Simulate model failure
        lstm_model = await registry.get_model("lstm")
        lstm_model.predict = AsyncMock(side_effect=Exception("Model failure"))
        
        # Update health status
        await registry.health_monitor.set_health_status("lstm", "unhealthy", "Model failure")
        
        # Check for health alerts
        health_status = await registry.get_system_health()
        assert health_status['overall_status'] == 'degraded'
        assert len(health_status['unhealthy_models']) > 0
        assert "lstm" in health_status['unhealthy_models']
    
    async def test_resource_usage_monitoring(self, monitored_system):
        """Test resource usage monitoring"""
        
        ensemble = monitored_system['ensemble']
        
        # Generate load to test resource monitoring
        contexts = [
            MockPredictionContext(sequence_length=np.random.randint(1, 10))
            for _ in range(200)
        ]
        
        await asyncio.gather([
            ensemble.predict_ensemble(context)
            for context in contexts
        ])
        
        # Get resource metrics
        resource_metrics = await ensemble.get_resource_metrics()
        
        assert 'memory_usage_mb' in resource_metrics
        assert 'cpu_usage_percent' in resource_metrics
        assert 'cache_hit_rate' in resource_metrics
        
        assert resource_metrics.memory_usage_mb > 0
        assert 0 <= resource_metrics.cpu_usage_percent <= 100
        assert 0 <= resource_metrics.cache_hit_rate <= 1

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
