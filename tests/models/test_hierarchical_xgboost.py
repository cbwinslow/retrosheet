"""
Comprehensive test suite for XGBoost Hierarchical Models (#159)
Tests two-tier hierarchical classification with XGBoost for pitch prediction.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch
from datetime import datetime
import xgboost as xgb

from baseball.models.xgboost.hierarchical_model import HierarchicalXGBoostModel, HierarchicalConfig


class TestHierarchicalConfig:
    """Test hierarchical configuration dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = HierarchicalConfig()
        
        assert config.feature_engineering is True
        assert config.cross_validation is True
        assert config.cv_folds == 5
        assert config.early_stopping_rounds == 50
        assert config.eval_metric == 'logloss'
        assert config.random_state == 42
        
        # Check default parameters are set
        assert 'objective' in config.tier1_params
        assert config.tier1_params['num_class'] == 3
        assert 'objective' in config.tier2_params
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = HierarchicalConfig(
            cv_folds=10,
            early_stopping_rounds=100,
            eval_metric='mlogloss'
        )
        
        assert config.cv_folds == 10
        assert config.early_stopping_rounds == 100
        assert config.eval_metric == 'mlogloss'
    
    def test_parameter_initialization(self):
        """Test parameter initialization."""
        config = HierarchicalConfig()
        
        # Tier 1 parameters
        assert config.tier1_params['objective'] == 'multi:softprob'
        assert config.tier1_params['num_class'] == 3
        assert config.tier1_params['max_depth'] == 6
        assert config.tier1_params['learning_rate'] == 0.1
        
        # Tier 2 parameters
        assert 'objective' in config.tier2_params
        assert 'max_depth' in config.tier2_params


class TestHierarchicalXGBoostModel:
    """Test hierarchical XGBoost model functionality."""
    
    @pytest.fixture
    def model(self):
        """Create hierarchical model for testing."""
        config = HierarchicalConfig(
            cv_folds=3,
            early_stopping_rounds=10
        )
        return HierarchicalXGBoostModel(config)
    
    @pytest.fixture
    def training_data(self):
        """Create training data for hierarchical model."""
        np.random.seed(42)
        n_samples = 1000
        
        return pd.DataFrame({
            'pitch_type': np.random.choice(['FF', 'FT', 'SL', 'CH', 'CU'], n_samples),
            'balls': np.random.randint(0, 4, n_samples),
            'strikes': np.random.randint(0, 3, n_samples),
            'release_speed': np.random.normal(90, 5, n_samples),
            'zone_x': np.random.normal(0, 0.5, n_samples),
            'zone_y': np.random.normal(2.5, 0.5, n_samples),
            'pitcher_id': np.random.choice([f'P{i}' for i in range(20)], n_samples),
            'batter_id': np.random.choice([f'B{i}' for i in range(50)], n_samples),
            'game_date': ['2024-01-01'] * n_samples,
            'inning': np.random.randint(1, 10, n_samples),
            'outs': np.random.randint(0, 3, n_samples),
            'run_diff': np.random.randint(-5, 6, n_samples)
        })
    
    def test_model_initialization(self, model):
        """Test model initialization."""
        assert isinstance(model.config, HierarchicalConfig)
        assert model.tier1_model is None
        assert model.tier2_model is None
        assert model.feature_engine is not None
        assert model.is_trained is False
    
    def test_feature_engineering(self, model, training_data):
        """Test feature engineering for hierarchical model."""
        features = model._engineer_features(training_data)
        
        assert isinstance(features, pd.DataFrame)
        assert len(features) == len(training_data)
        
        # Check for expected feature columns
        expected_features = [
            'release_speed', 'zone_x', 'zone_y', 'balls', 'strikes',
            'inning', 'outs', 'run_diff'
        ]
        for feature in expected_features:
            assert feature in features.columns
    
    def test_tier1_target_creation(self, model, training_data):
        """Test tier 1 target creation."""
        tier1_target = model._create_tier1_target(training_data)
        
        assert isinstance(tier1_target, np.ndarray)
        assert len(tier1_target) == len(training_data)
        assert len(np.unique(tier1_target)) == 3  # Ball, Strike, Ball-in-Play
    
    def test_tier2_target_creation(self, model, training_data):
        """Test tier 2 target creation."""
        tier2_target = model._create_tier2_target(training_data)
        
        assert isinstance(tier2_target, np.ndarray)
        assert len(tier2_target) == len(training_data)
        
        # Check that ball-in-play cases have detailed targets
        bip_mask = training_data['pitch_type'].isin(['FF', 'FT', 'SL', 'CH', 'CU'])
        assert np.any(tier2_target[bip_mask] > 0)
    
    def test_model_training(self, model, training_data):
        """Test model training."""
        result = model.train(training_data)
        
        assert result.success is True
        assert result.model_version is not None
        assert result.rows_processed == len(training_data)
        assert result.training_time_seconds > 0
        assert model.is_trained is True
        assert model.tier1_model is not None
        assert model.tier2_model is not None
    
    def test_tier1_prediction(self, model, training_data):
        """Test tier 1 prediction."""
        model.train(training_data)
        
        # Create test context
        test_context = {
            'release_speed': 92.0,
            'zone_x': 0.1,
            'zone_y': 2.6,
            'balls': 1,
            'strikes': 0,
            'inning': 5,
            'outs': 1,
            'run_diff': 0,
            'pitcher_id': 'P1',
            'batter_id': 'B1'
        }
        
        tier1_pred = model._predict_tier1(test_context)
        
        assert isinstance(tier1_pred, np.ndarray)
        assert len(tier1_pred) == 3  # 3 classes
        assert abs(tier1_pred.sum() - 1.0) < 1e-10  # Probabilities sum to 1
    
    def test_tier2_prediction(self, model, training_data):
        """Test tier 2 prediction."""
        model.train(training_data)
        
        # Create test context
        test_context = {
            'release_speed': 92.0,
            'zone_x': 0.1,
            'zone_y': 2.6,
            'balls': 1,
            'strikes': 0,
            'inning': 5,
            'outs': 1,
            'run_diff': 0,
            'pitcher_id': 'P1',
            'batter_id': 'B1'
        }
        
        tier2_pred = model._predict_tier2(test_context)
        
        assert isinstance(tier2_pred, np.ndarray)
        assert len(tier2_pred) > 0  # Has detailed predictions
    
    def test_hierarchical_prediction(self, model, training_data):
        """Test full hierarchical prediction."""
        model.train(training_data)
        
        # Create test context
        test_context = {
            'release_speed': 92.0,
            'zone_x': 0.1,
            'zone_y': 2.6,
            'balls': 1,
            'strikes': 0,
            'inning': 5,
            'outs': 1,
            'run_diff': 0,
            'pitcher_id': 'P1',
            'batter_id': 'B1'
        }
        
        prediction = model.predict(test_context)
        
        assert hasattr(prediction, 'tier1_prediction')
        assert hasattr(prediction, 'tier2_prediction')
        assert hasattr(prediction, 'final_prediction')
        assert hasattr(prediction, 'confidence')
        assert hasattr(prediction, 'prediction_path')
    
    def test_batch_prediction(self, model, training_data):
        """Test batch prediction."""
        model.train(training_data)
        
        # Create test contexts
        test_contexts = [
            {
                'release_speed': 92.0,
                'zone_x': 0.1,
                'zone_y': 2.6,
                'balls': 1,
                'strikes': 0,
                'pitcher_id': 'P1',
                'batter_id': 'B1'
            },
            {
                'release_speed': 88.0,
                'zone_x': -0.2,
                'zone_y': 2.3,
                'balls': 2,
                'strikes': 1,
                'pitcher_id': 'P2',
                'batter_id': 'B2'
            }
        ]
        
        predictions = model.predict_batch(test_contexts)
        
        assert len(predictions) == len(test_contexts)
        for pred in predictions:
            assert hasattr(pred, 'tier1_prediction')
            assert hasattr(pred, 'tier2_prediction')
            assert hasattr(pred, 'final_prediction')
    
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
            loaded_model = HierarchicalXGBoostModel.load(model_path)
            
            # Test loaded model
            assert loaded_model.is_trained is True
            assert loaded_model.config.cv_folds == model.config.cv_folds
            
            # Test prediction with loaded model
            test_context = {
                'release_speed': 92.0,
                'zone_x': 0.1,
                'zone_y': 2.6,
                'balls': 1,
                'strikes': 0,
                'pitcher_id': 'P1',
                'batter_id': 'B1'
            }
            prediction = loaded_model.predict(test_context)
            assert hasattr(prediction, 'final_prediction')
            
        finally:
            if os.path.exists(model_path):
                os.unlink(model_path)
    
    def test_cross_validation(self, model, training_data):
        """Test cross-validation functionality."""
        config = HierarchicalConfig(cross_validation=True, cv_folds=3)
        model = HierarchicalXGBoostModel(config)
        
        result = model.train(training_data)
        
        assert result.success is True
        assert 'cv_score' in result.metrics
        assert result.metrics['cv_score'] > 0
    
    def test_no_cross_validation(self, model, training_data):
        """Test training without cross-validation."""
        config = HierarchicalConfig(cross_validation=False)
        model = HierarchicalXGBoostModel(config)
        
        result = model.train(training_data)
        
        assert result.success is True
        # CV score should not be present without CV
        assert 'cv_score' not in result.metrics or result.metrics['cv_score'] == 0
    
    def test_early_stopping(self, model, training_data):
        """Test early stopping functionality."""
        config = HierarchicalConfig(early_stopping_rounds=5)
        model = HierarchicalXGBoostModel(config)
        
        result = model.train(training_data)
        
        assert result.success is True
        assert model.tier1_model is not None
        assert model.tier2_model is not None
    
    def test_different_eval_metrics(self, training_data):
        """Test different evaluation metrics."""
        metrics = ['logloss', 'mlogloss', 'merror']
        
        for metric in metrics:
            config = HierarchicalConfig(eval_metric=metric)
            model = HierarchicalXGBoostModel(config)
            
            result = model.train(training_data)
            
            assert result.success is True
            assert model.is_trained is True


class TestHierarchicalModelIntegration:
    """Integration tests for hierarchical XGBoost models."""
    
    @pytest.fixture
    def large_training_data(self):
        """Create larger training dataset."""
        np.random.seed(42)
        n_pitches = 5000
        
        pitch_types = ['FF', 'FT', 'SL', 'CH', 'CU']
        pitcher_ids = [f'P{i}' for i in range(50)]
        batter_ids = [f'B{i}' for i in range(100)]
        
        return pd.DataFrame({
            'pitch_type': np.random.choice(pitch_types, n_pitches),
            'balls': np.random.randint(0, 4, n_pitches),
            'strikes': np.random.randint(0, 3, n_pitches),
            'release_speed': np.random.normal(90, 5, n_pitches),
            'zone_x': np.random.normal(0, 0.5, n_pitches),
            'zone_y': np.random.normal(2.5, 0.5, n_pitches),
            'pitcher_id': np.random.choice(pitcher_ids, n_pitches),
            'batter_id': np.random.choice(batter_ids, n_pitches),
            'game_date': ['2024-01-01'] * n_pitches,
            'inning': np.random.randint(1, 10, n_pitches),
            'outs': np.random.randint(0, 3, n_pitches),
            'run_diff': np.random.randint(-5, 6, n_pitches)
        })
    
    def test_large_dataset_training(self, large_training_data):
        """Test training on larger dataset."""
        model = HierarchicalXGBoostModel()
        
        result = model.train(large_training_data)
        
        assert result.success is True
        assert result.rows_processed == len(large_training_data)
        assert model.is_trained is True
        assert model.tier1_model is not None
        assert model.tier2_model is not None
    
    def test_prediction_consistency(self, large_training_data):
        """Test prediction consistency."""
        model = HierarchicalXGBoostModel()
        model.train(large_training_data)
        
        # Test same context multiple times
        test_context = {
            'release_speed': 92.0,
            'zone_x': 0.1,
            'zone_y': 2.6,
            'balls': 1,
            'strikes': 0,
            'inning': 5,
            'outs': 1,
            'run_diff': 0,
            'pitcher_id': 'P1',
            'batter_id': 'B1'
        }
        
        predictions = [model.predict(test_context) for _ in range(3)]
        
        # Predictions should be consistent
        first_final = predictions[0].final_prediction
        for pred in predictions[1:]:
            assert pred.final_prediction == first_final
    
    def test_different_configurations(self, large_training_data):
        """Test different model configurations."""
        configs = [
            HierarchicalConfig(cv_folds=3, early_stopping_rounds=10),
            HierarchicalConfig(cv_folds=5, feature_engineering=False),
            HierarchicalConfig(cv_folds=10, eval_metric='mlogloss')
        ]
        
        results = []
        for config in configs:
            model = HierarchicalXGBoostModel(config)
            result = model.train(large_training_data)
            results.append(result)
        
        # All should succeed
        assert all(result.success for result in results)
        
        # Should have different characteristics
        assert len(set(result.model_version for result in results)) > 1


class TestHierarchicalModelPerformance:
    """Performance tests for hierarchical XGBoost models."""
    
    def test_training_performance(self):
        """Test training performance."""
        import time
        
        # Create medium-sized dataset
        n_pitches = 2000
        training_data = pd.DataFrame({
            'pitch_type': np.random.choice(['FF', 'FT', 'SL', 'CH'], n_pitches),
            'balls': np.random.randint(0, 4, n_pitches),
            'strikes': np.random.randint(0, 3, n_pitches),
            'release_speed': np.random.normal(90, 5, n_pitches),
            'zone_x': np.random.normal(0, 0.5, n_pitches),
            'zone_y': np.random.normal(2.5, 0.5, n_pitches),
            'pitcher_id': np.random.choice([f'P{i}' for i in range(20)], n_pitches),
            'batter_id': np.random.choice([f'B{i}' for i in range(40)], n_pitches),
            'game_date': ['2024-01-01'] * n_pitches,
            'inning': np.random.randint(1, 10, n_pitches),
            'outs': np.random.randint(0, 3, n_pitches),
            'run_diff': np.random.randint(-5, 6, n_pitches)
        })
        
        model = HierarchicalXGBoostModel()
        
        start_time = time.time()
        result = model.train(training_data)
        end_time = time.time()
        
        training_time = end_time - start_time
        
        assert result.success is True
        assert training_time < 60.0  # Should complete within 60 seconds
        assert result.training_time_seconds > 0
    
    def test_prediction_performance(self):
        """Test prediction performance."""
        import time
        
        # Train model
        training_data = pd.DataFrame({
            'pitch_type': ['FF', 'FT', 'SL', 'CH'] * 500,
            'balls': np.random.randint(0, 4, 2000),
            'strikes': np.random.randint(0, 3, 2000),
            'release_speed': np.random.normal(90, 5, 2000),
            'zone_x': np.random.normal(0, 0.5, 2000),
            'zone_y': np.random.normal(2.5, 0.5, 2000),
            'pitcher_id': np.random.choice([f'P{i}' for i in range(20)], 2000),
            'batter_id': np.random.choice([f'B{i}' for i in range(40)], 2000),
            'game_date': ['2024-01-01'] * 2000,
            'inning': np.random.randint(1, 10, 2000),
            'outs': np.random.randint(0, 3, 2000),
            'run_diff': np.random.randint(-5, 6, 2000)
        })
        
        model = HierarchicalXGBoostModel()
        model.train(training_data)
        
        # Test prediction performance
        test_contexts = [
            {
                'release_speed': 92.0,
                'zone_x': 0.1,
                'zone_y': 2.6,
                'balls': 1,
                'strikes': 0,
                'pitcher_id': 'P1',
                'batter_id': 'B1'
            }
        ] * 1000
        
        start_time = time.time()
        predictions = model.predict_batch(test_contexts)
        end_time = time.time()
        
        prediction_time = end_time - start_time
        
        assert len(predictions) == len(test_contexts)
        assert prediction_time < 10.0  # Should complete within 10 seconds
        assert prediction_time / len(test_contexts) < 0.01  # < 10ms per prediction


class TestHierarchicalModelEdgeCases:
    """Edge case tests for hierarchical XGBoost models."""
    
    def test_empty_training_data(self):
        """Test training with empty data."""
        model = HierarchicalXGBoostModel()
        empty_data = pd.DataFrame()
        
        result = model.train(empty_data)
        
        assert result.success is False
        assert result.error_message is not None
    
    def test_single_pitch_type(self):
        """Test training with only one pitch type."""
        model = HierarchicalXGBoostModel()
        single_type_data = pd.DataFrame({
            'pitch_type': ['FF'] * 100,
            'balls': np.random.randint(0, 4, 100),
            'strikes': np.random.randint(0, 3, 100),
            'release_speed': np.random.normal(90, 5, 100),
            'zone_x': np.random.normal(0, 0.5, 100),
            'zone_y': np.random.normal(2.5, 0.5, 100),
            'pitcher_id': ['P1'] * 100,
            'batter_id': ['B1'] * 100,
            'game_date': ['2024-01-01'] * 100,
            'inning': np.random.randint(1, 10, 100),
            'outs': np.random.randint(0, 3, 100),
            'run_diff': np.random.randint(-5, 6, 100)
        })
        
        result = model.train(single_type_data)
        
        # Should still train but with warnings
        assert result.success is True
    
    def test_missing_features(self):
        """Test prediction with missing features."""
        model = HierarchicalXGBoostModel()
        
        # Train with basic data
        training_data = pd.DataFrame({
            'pitch_type': ['FF', 'FT', 'SL'] * 100,
            'balls': np.random.randint(0, 4, 300),
            'strikes': np.random.randint(0, 3, 300),
            'release_speed': np.random.normal(90, 5, 300),
            'zone_x': np.random.normal(0, 0.5, 300),
            'zone_y': np.random.normal(2.5, 0.5, 300),
            'pitcher_id': np.random.choice(['P1', 'P2'], 300),
            'batter_id': np.random.choice(['B1', 'B2'], 300),
            'game_date': ['2024-01-01'] * 300,
            'inning': np.random.randint(1, 10, 300),
            'outs': np.random.randint(0, 3, 300),
            'run_diff': np.random.randint(-5, 6, 300)
        })
        
        model.train(training_data)
        
        # Test with missing features
        incomplete_context = {
            'release_speed': 92.0,
            'balls': 1,
            'strikes': 0
            # Missing zone_x, zone_y, etc.
        }
        
        # Should handle missing features gracefully
        try:
            prediction = model.predict(incomplete_context)
            # Should either work with defaults or raise informative error
            assert True
        except Exception as e:
            assert 'missing' in str(e).lower() or 'feature' in str(e).lower()
    
    def test_extreme_values(self):
        """Test with extreme feature values."""
        model = HierarchicalXGBoostModel()
        
        # Training data with extreme values
        extreme_data = pd.DataFrame({
            'pitch_type': ['FF', 'FT', 'SL'] * 100,
            'balls': np.random.randint(0, 4, 300),
            'strikes': np.random.randint(0, 3, 300),
            'release_speed': np.concatenate([
                np.random.normal(90, 5, 150),  # Normal
                np.random.normal(150, 10, 150)  # Extreme high
            ]),
            'zone_x': np.concatenate([
                np.random.normal(0, 0.5, 150),   # Normal
                np.random.normal(5, 2, 150)     # Extreme
            ]),
            'zone_y': np.concatenate([
                np.random.normal(2.5, 0.5, 150),  # Normal
                np.random.normal(10, 3, 150)     # Extreme high
            ]),
            'pitcher_id': np.random.choice(['P1', 'P2'], 300),
            'batter_id': np.random.choice(['B1', 'B2'], 300),
            'game_date': ['2024-01-01'] * 300,
            'inning': np.random.randint(1, 10, 300),
            'outs': np.random.randint(0, 3, 300),
            'run_diff': np.random.randint(-5, 6, 300)
        })
        
        result = model.train(extreme_data)
        
        assert result.success is True
        assert model.is_trained is True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
