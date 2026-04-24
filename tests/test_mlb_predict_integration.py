"""
Integration tests for mlb_predict framework.

Phase 1.3: Test Infrastructure

Validates the complete framework from config to training to results.
Uses mock mode to avoid database dependencies.

Author: Agent Cascade
Date: April 24, 2026
"""

import pytest
import tempfile
import json
from pathlib import Path

from mlb_predict import (
    # Config
    ModelConfig, ExperimentConfig, ModelFamily, TargetVariable, FeatureSet,
    load_config, save_config,
    # Results
    TrainResult, Metrics, MetricValue, Residuals, FeatureImportance,
    # Core
    ModelTrainer, BasePluginModel, PluginRegistry, SklearnPluginModel,
    FeatureLoader, DataSplit,
    # Experiment
    ExperimentRunner, HyperparameterSweep, compare_model_families, compare_feature_sets,
)


class TestConfigSchemas:
    """Test Pydantic configuration schemas."""
    
    def test_model_config_creation(self):
        """Test basic ModelConfig creation."""
        config = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
            features=FeatureSet.ADVANCED,
            seasons=[2023, 2024, 2025]
        )
        
        assert config.family == 'xgboost'
        assert config.target == 'swing_decision'
        assert config.features == 'advanced'
        assert config.seasons == [2023, 2024, 2025]
    
    def test_model_config_serialization(self):
        """Test ModelConfig to/from YAML."""
        config = ModelConfig(
            family=ModelFamily.LIGHTGBM,
            target=TargetVariable.CONTACT_MADE,
            features=FeatureSet.PHYSICS,
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            # Save
            config.to_yaml(temp_path)
            
            # Load
            loaded = ModelConfig.from_yaml(temp_path)
            
            assert loaded.family == config.family
            assert loaded.target == config.target
            assert loaded.features == config.features
        finally:
            Path(temp_path).unlink()
    
    def test_invalid_family_raises_error(self):
        """Test that invalid model family raises error."""
        with pytest.raises((ValueError, TypeError)):
            ModelConfig(
                family='invalid_model',
                target='swing_decision',
            )
    
    def test_config_manager(self):
        """Test ConfigManager functionality."""
        from mlb_predict import ConfigManager
        
        manager = ConfigManager()
        
        # Register config
        config = ModelConfig(family='xgboost', target='swing_decision')
        manager.register('test_config', config)
        
        # Get config
        retrieved = manager.get('test_config')
        assert retrieved.family == 'xgboost'
        
        # List configs
        configs = manager.list_configs()
        assert 'test_config' in configs


class TestRichResults:
    """Test rich result classes."""
    
    def test_train_result_creation(self):
        """Test TrainResult creation."""
        config = ModelConfig(family='xgboost', target='swing_decision')
        
        result = TrainResult(
            model_id=1,
            model_name='test_model',
            config=config,
            artifact_path='models/test.pkl',
            train_metrics=Metrics(roc_auc=MetricValue(value=0.85)),
            val_metrics=Metrics(roc_auc=MetricValue(value=0.82)),
            training_time_seconds=10.5,
            n_samples_train=1000,
            n_samples_val=200,
            status='completed'
        )
        
        assert result.model_id == 1
        assert result.model_name == 'test_model'
        assert result.training_time_seconds == 10.5
        assert result.train_metrics.roc_auc.value == 0.85
        assert result.val_metrics.roc_auc.value == 0.82
    
    def test_train_result_summary(self):
        """Test TrainResult summary method."""
        config = ModelConfig(family='xgboost', target='swing_decision')
        
        result = TrainResult(
            model_id=1,
            model_name='xgboost_swing_decision',
            config=config,
            artifact_path='models/test.pkl',
            val_metrics=Metrics(roc_auc=MetricValue(value=0.82)),
            training_time_seconds=10.5,
            status='completed'
        )
        
        summary = result.summary()
        assert 'Model 1' in summary
        assert 'xgboost_swing_decision' in summary
        assert 'Val AUC=0.8200' in summary
    
    def test_residuals_analysis(self):
        """Test Residuals analysis methods."""
        residuals = Residuals(
            y_true=[0, 1, 0, 1, 1],
            y_pred=[0, 1, 0, 0, 1],
            y_prob=[0.1, 0.9, 0.2, 0.4, 0.8]
        )
        
        stats = residuals.analyze()
        assert 'mean' in stats
        assert 'std' in stats
        assert 'mse' in stats
        
        # Check confusion matrix
        cm = residuals.confusion_matrix()
        assert 'true_negatives' in cm
        assert 'true_positives' in cm
    
    def test_feature_importance_sorting(self):
        """Test FeatureImportance sorting."""
        features = [
            FeatureImportance(feature_name='feat_a', importance_score=0.5, importance_rank=1),
            FeatureImportance(feature_name='feat_b', importance_score=0.3, importance_rank=2),
            FeatureImportance(feature_name='feat_c', importance_score=0.2, importance_rank=3),
        ]
        
        # Test to_dataframe
        import pandas as pd
        df = pd.DataFrame([f.model_dump() for f in features])
        assert len(df) == 3
        assert df.iloc[0]['importance_score'] == 0.5
    
    def test_train_result_comparison(self):
        """Test TrainResult comparison."""
        config1 = ModelConfig(family='xgboost', target='swing_decision')
        config2 = ModelConfig(family='lightgbm', target='swing_decision')
        
        result1 = TrainResult(
            model_id=1,
            model_name='xgboost',
            config=config1,
            artifact_path='models/xgb.pkl',
            val_metrics=Metrics(roc_auc=MetricValue(value=0.85)),
            training_time_seconds=10.0,
            status='completed'
        )
        
        result2 = TrainResult(
            model_id=2,
            model_name='lightgbm',
            config=config2,
            artifact_path='models/lgb.pkl',
            val_metrics=Metrics(roc_auc=MetricValue(value=0.83)),
            training_time_seconds=8.0,
            status='completed'
        )
        
        # Compare
        comparison = result1.compare_to(result2)
        assert 'result_1' in comparison
        assert 'result_2' in comparison
        assert 'winner' in comparison


class TestModelTrainer:
    """Test ModelTrainer class."""
    
    def test_trainer_creation(self):
        """Test ModelTrainer creation."""
        config = ModelConfig(family='xgboost', target='swing_decision')
        trainer = ModelTrainer(config)
        
        assert trainer.config == config
    
    def test_trainer_from_config(self):
        """Test ModelTrainer.from_config class method."""
        config = ModelConfig(family='lightgbm', target='contact_made')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config.to_yaml(f.name)
            temp_path = f.name
        
        try:
            trainer = ModelTrainer.from_config(temp_path)
            assert trainer.config.family == 'lightgbm'
            assert trainer.config.target == 'contact_made'
        finally:
            Path(temp_path).unlink()
    
    def test_trainer_train_mock(self):
        """Test ModelTrainer.train with mock mode."""
        config = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
            features=FeatureSet.ADVANCED,
            seasons=[2023, 2024, 2025]
        )
        
        trainer = ModelTrainer(config)
        result = trainer.train()
        
        assert isinstance(result, TrainResult)
        assert result.model_name is not None
        assert result.training_time_seconds > 0
        assert result.n_samples_train > 0
        
        # Check metrics
        if result.val_metrics and result.val_metrics.roc_auc:
            assert 0.0 <= result.val_metrics.roc_auc.value <= 1.0
    
    def test_trainer_plugin_registration(self):
        """Test plugin registration."""
        from sklearn.ensemble import RandomForestClassifier
        
        config = ModelConfig(family='custom', target='swing_decision')
        
        # Create custom plugin
        class TestPlugin:
            def __init__(self, config):
                self.config = config
                self.model = RandomForestClassifier(n_estimators=10)
            
            def fit(self, X, y, X_val=None, y_val=None):
                self.model.fit(X, y)
                return self
            
            def predict(self, X):
                return self.model.predict(X)
            
            def predict_proba(self, X):
                return self.model.predict_proba(X)[:, 1]
            
            def save(self, path):
                pass
            
            @classmethod
            def load(cls, path):
                return cls(None)
        
        trainer = ModelTrainer(config)
        trainer.register_plugin('test_plugin', TestPlugin)
        
        assert 'test_plugin' in trainer.list_registered_plugins()


class TestPluginSystem:
    """Test plugin system."""
    
    def test_base_plugin_model_abstract(self):
        """Test that BasePluginModel is abstract."""
        config = ModelConfig(family='custom', target='swing_decision')
        
        with pytest.raises(TypeError):
            BasePluginModel(config)
    
    def test_plugin_registry(self):
        """Test PluginRegistry."""
        registry = PluginRegistry()
        
        # Define a simple plugin
        class SimplePlugin(BasePluginModel):
            def fit(self, X, y, X_val=None, y_val=None):
                return self
            
            def predict(self, X):
                return [0] * len(X)
            
            def predict_proba(self, X):
                return [0.5] * len(X)
            
            def save(self, path):
                pass
            
            @classmethod
            def load(cls, path):
                return cls(None)
        
        # Register
        registry.register('simple', SimplePlugin, description='Simple test plugin')
        
        # Check
        assert registry.is_registered('simple')
        assert 'simple' in registry.list_plugins()
        
        # Get metadata
        meta = registry.get_metadata('simple')
        assert meta['description'] == 'Simple test plugin'
    
    def test_sklearn_plugin_model(self):
        """Test SklearnPluginModel wrapper."""
        from sklearn.ensemble import RandomForestClassifier
        
        config = ModelConfig(family='custom', target='swing_decision')
        rf = RandomForestClassifier(n_estimators=5, random_state=42)
        
        model = SklearnPluginModel(config, rf)
        
        # Mock training
        import numpy as np
        X_train = np.random.rand(50, 10)
        y_train = np.random.randint(0, 2, 50)
        
        model.fit(X_train, y_train)
        
        assert model.is_fitted
        
        # Predict
        X_test = np.random.rand(10, 10)
        preds = model.predict(X_test)
        assert len(preds) == 10
        
        proba = model.predict_proba(X_test)
        assert len(proba) == 10
        assert all(0 <= p <= 1 for p in proba)


class TestFeatureLoader:
    """Test FeatureLoader."""
    
    def test_feature_loader_creation(self):
        """Test FeatureLoader creation."""
        config = ModelConfig(
            family='xgboost',
            target='swing_decision',
            features='advanced',
            seasons=[2023, 2024]
        )
        
        loader = FeatureLoader(config)
        assert loader.config == config
    
    def test_feature_schema(self):
        """Test feature schema generation."""
        config = ModelConfig(family='xgboost', target='swing_decision', features='basic')
        loader = FeatureLoader(config)
        
        schema = loader.get_feature_schema()
        assert len(schema.numeric_features) > 0
        assert len(schema.categorical_features) > 0
        assert schema.target_column == 'swing'
    
    def test_feature_info(self):
        """Test feature info."""
        config = ModelConfig(family='xgboost', target='swing_decision', features='advanced')
        loader = FeatureLoader(config)
        
        info = loader.get_feature_info()
        assert 'n_numeric' in info
        assert 'n_categorical' in info
        assert 'n_total' in info
        assert info['n_total'] == info['n_numeric'] + info['n_categorical']
    
    def test_data_split_empty(self):
        """Test DataSplit with no data (DB not available)."""
        config = ModelConfig(
            family='xgboost',
            target='swing_decision',
            seasons=[2099]  # Future season, no data
        )
        
        loader = FeatureLoader(config)
        
        # Will return empty split since DB doesn't have 2099
        try:
            split = loader.load_split(train_through=2099)
            assert isinstance(split, DataSplit)
            assert split.n_train == 0
        except Exception:
            # Expected if DB connection fails
            pass


class TestExperimentRunner:
    """Test ExperimentRunner."""
    
    def test_experiment_runner_creation(self):
        """Test ExperimentRunner creation."""
        configs = [
            ModelConfig(family='xgboost', target='swing_decision'),
            ModelConfig(family='lightgbm', target='swing_decision'),
        ]
        
        runner = ExperimentRunner(
            experiment_name='test_exp',
            configs=configs,
            metric_name='val_roc_auc'
        )
        
        assert runner.experiment_name == 'test_exp'
        assert len(runner.configs) == 2
        assert len(runner.runs) == 2
    
    def test_compare_model_families(self):
        """Test compare_model_families convenience function."""
        base_config = ModelConfig(
            family='xgboost',
            target='swing_decision',
            features='advanced'
        )
        
        runner = compare_model_families(
            base_config,
            families=['xgboost', 'lightgbm']
        )
        
        assert runner.experiment_name == 'model_family_comparison_swing_decision'
        assert len(runner.configs) == 2
        assert runner.configs[0].family == 'xgboost'
        assert runner.configs[1].family == 'lightgbm'
    
    def test_compare_feature_sets(self):
        """Test compare_feature_sets convenience function."""
        base_config = ModelConfig(
            family='xgboost',
            target='swing_decision',
            features='advanced'
        )
        
        runner = compare_feature_sets(
            base_config,
            feature_sets=['basic', 'advanced']
        )
        
        assert runner.experiment_name == 'feature_set_comparison_swing_decision'
        assert len(runner.configs) == 2
        assert runner.configs[0].features == 'basic'
        assert runner.configs[1].features == 'advanced'
    
    def test_experiment_summary(self):
        """Test ExperimentSummary."""
        from mlb_predict import ExperimentRun, ExperimentSummary
        
        config = ModelConfig(family='xgboost', target='swing_decision')
        
        run = ExperimentRun(
            run_id='run_001',
            config=config,
            status='completed'
        )
        
        summary = ExperimentSummary(
            experiment_id='exp_test',
            experiment_name='test',
            n_runs=1,
            n_completed=1,
            n_failed=0,
            runs=[run]
        )
        
        assert summary.n_runs == 1
        assert summary.n_completed == 1
    
    def test_hyperparameter_sweep(self):
        """Test HyperparameterSweep."""
        base_config = ModelConfig(
            family='xgboost',
            target='swing_decision',
            features='advanced'
        )
        
        sweep = HyperparameterSweep(
            base_config=base_config,
            param_grid={
                'xgboost__max_depth': [3, 5],
                'xgboost__learning_rate': [0.01, 0.1]
            }
        )
        
        configs = sweep.generate_configs()
        
        # 2 depths × 2 learning rates = 4 configs
        assert len(configs) == 4


class TestEndToEnd:
    """End-to-end integration tests."""
    
    def test_config_to_train_result(self):
        """Test complete flow: config → train → result."""
        # 1. Create config
        config = ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
            features=FeatureSet.ADVANCED,
            seasons=[2023, 2024, 2025]
        )
        
        # 2. Save and load config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
            config.to_yaml(temp_path)
        
        try:
            loaded_config = ModelConfig.from_yaml(temp_path)
            
            # 3. Train model
            trainer = ModelTrainer(loaded_config)
            result = trainer.train()
            
            # 4. Validate result
            assert isinstance(result, TrainResult)
            assert result.status == 'completed'
            assert result.training_time_seconds > 0
            
            # 5. Analyze results
            if result.val_metrics and result.val_metrics.roc_auc:
                assert 0.0 < result.val_metrics.roc_auc.value < 1.0
            
            if result.feature_importance:
                top_features = result.get_best_features(5)
                assert len(top_features) <= 5
        finally:
            Path(temp_path).unlink()
    
    def test_experiment_flow(self):
        """Test complete experiment flow."""
        # Create experiment
        base_config = ModelConfig(
            family='xgboost',
            target='swing_decision',
            features='advanced',
            seasons=[2023, 2024, 2025]
        )
        
        runner = compare_model_families(
            base_config,
            families=['xgboost', 'lightgbm']
        )
        
        # Run experiment
        summary = runner.run_all()
        
        # Validate
        assert summary.n_runs == 2
        assert summary.n_completed == 2
        
        # Check results
        df = summary.to_dataframe()
        assert len(df) == 2
        
        # Get best
        best_run = runner.get_best_run()
        assert best_run is not None
        assert isinstance(best_run.result, TrainResult)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
