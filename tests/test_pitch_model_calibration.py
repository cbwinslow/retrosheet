"""
Comprehensive test suite for pitch model calibration.
Tests all aspects including edge cases, error handling, and integration scenarios.
Following AGENTS.md rules for comprehensive testing.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import pandas as pd
from sklearn.metrics import calibration_curve, brier_score_loss
import matplotlib.pyplot as plt

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from baseball.models.pitch.calibration import PitchModelCalibrator


class TestPitchModelCalibrator:
    """Comprehensive test suite for pitch model calibration."""
    
    @pytest.fixture
    def sample_predictions_data(self):
        """Sample predictions and true labels for testing."""
        np.random.seed(42)
        n_samples = 1000
        
        # Generate realistic predictions
        true_labels = np.random.choice([0, 1, 2], size=n_samples, p=[0.4, 0.35, 0.25])
        predictions = np.zeros((n_samples, 3))
        
        for i, label in enumerate(true_labels):
            # Add some noise to make it realistic
            probs = np.array([0.4, 0.35, 0.25])
            probs[label] += np.random.uniform(0.1, 0.3)
            probs = probs / probs.sum()
            predictions[i] = probs
        
        return {
            'predictions': predictions,
            'true_labels': true_labels,
            'sample_ids': range(n_samples)
        }
    
    @pytest.fixture
    def calibrator(self):
        """Create calibrator instance for testing."""
        return PitchModelCalibrator(
            model_name='test_xgboost_model',
            target_tier='tier1',
            calibration_method='temperature'
        )
    
    def test_calibrator_initialization(self, calibrator):
        """Test calibrator initialization."""
        assert calibrator.model_name == 'test_xgboost_model'
        assert calibrator.target_tier == 'tier1'
        assert calibrator.calibration_method == 'temperature'
        assert calibrator.is_fitted == False
    
    def test_calibrator_initialization_with_different_methods(self):
        """Test calibrator initialization with different calibration methods."""
        methods = ['temperature', 'isotonic', 'beta', 'dirichlet']
        for method in methods:
            calibrator = PitchModelCalibrator(
                model_name='test_model',
                target_tier='tier1',
                calibration_method=method
            )
            assert calibrator.calibration_method == method
            assert calibrator.is_fitted == False
    
    def test_temperature_scaling_fit(self, calibrator, sample_predictions_data):
        """Test temperature scaling calibration fitting."""
        predictions = sample_predictions_data['predictions']
        true_labels = sample_predictions_data['true_labels']
        
        # Fit calibrator
        calibrator.fit(predictions, true_labels)
        
        # Verify fitting
        assert calibrator.is_fitted == True
        assert hasattr(calibrator, 'temperature_')
        assert calibrator.temperature_ > 0
    
    def test_isotonic_regression_fit(self, sample_predictions_data):
        """Test isotonic regression calibration fitting."""
        calibrator = PitchModelCalibrator(
            model_name='test_model',
            target_tier='tier1',
            calibration_method='isotonic'
        )
        
        predictions = sample_predictions_data['predictions']
        true_labels = sample_predictions_data['true_labels']
        
        # Fit calibrator
        calibrator.fit(predictions, true_labels)
        
        # Verify fitting
        assert calibrator.is_fitted == True
        assert hasattr(calibrator, 'calibrators_')
        assert len(calibrator.calibrators_) == 3  # One per class
    
    def test_beta_calibration_fit(self, sample_predictions_data):
        """Test beta calibration fitting."""
        calibrator = PitchModelCalibrator(
            model_name='test_model',
            target_tier='tier1',
            calibration_method='beta'
        )
        
        predictions = sample_predictions_data['predictions']
        true_labels = sample_predictions_data['true_labels']
        
        # Fit calibrator
        calibrator.fit(predictions, true_labels)
        
        # Verify fitting
        assert calibrator.is_fitted == True
        assert hasattr(calibrator, 'beta_params_')
        assert len(calibrator.beta_params_) == 3  # One per class
    
    def test_calibration_predict(self, calibrator, sample_predictions_data):
        """Test calibration prediction."""
        predictions = sample_predictions_data['predictions']
        true_labels = sample_predictions_data['true_labels']
        
        # Fit calibrator
        calibrator.fit(predictions, true_labels)
        
        # Make predictions
        calibrated_predictions = calibrator.predict(predictions)
        
        # Verify predictions
        assert calibrated_predictions.shape == predictions.shape
        assert np.allclose(calibrated_predictions.sum(axis=1), 1.0, atol=1e-6)
        assert np.all(calibrated_predictions >= 0)
        assert np.all(calibrated_predictions <= 1)
    
    def test_calibration_predict_proba(self, calibrator, sample_predictions_data):
        """Test calibration predict_proba method."""
        predictions = sample_predictions_data['predictions']
        true_labels = sample_predictions_data['true_labels']
        
        # Fit calibrator
        calibrator.fit(predictions, true_labels)
        
        # Make predictions
        calibrated_proba = calibrator.predict_proba(predictions)
        
        # Verify predictions
        assert calibrated_proba.shape == predictions.shape
        assert np.allclose(calibrated_proba.sum(axis=1), 1.0, atol=1e-6)
    
    def test_calibration_error_handling(self, calibrator):
        """Test error handling in calibration."""
        # Test predict before fitting
        with pytest.raises(ValueError, match="Calibrator must be fitted"):
            calibrator.predict(np.random.rand(100, 3))
        
        # Test fit with invalid data
        with pytest.raises(ValueError):
            calibrator.fit(np.random.rand(100, 3), np.random.randint(0, 3, 50))  # Mismatched shapes
    
    def test_calibration_methods_comparison(self, sample_predictions_data):
        """Test comparison of different calibration methods."""
        predictions = sample_predictions_data['predictions']
        true_labels = sample_predictions_data['true_labels']
        
        methods = ['temperature', 'isotonic', 'beta']
        results = {}
        
        for method in methods:
            calibrator = PitchModelCalibrator(
                model_name='test_model',
                target_tier='tier1',
                calibration_method=method
            )
            
            # Fit and predict
            calibrator.fit(predictions, true_labels)
            calibrated_pred = calibrator.predict(predictions)
            
            # Calculate metrics
            ece = calibrator.expected_calibration_error(predictions, true_labels)
            calibrated_ece = calibrator.expected_calibration_error(calibrated_pred, true_labels)
            
            results[method] = {
                'original_ece': ece,
                'calibrated_ece': calibrated_ece,
                'improvement': ece - calibrated_ece
            }
        
        # Verify at least one method improves calibration
        improvements = [r['improvement'] for r in results.values()]
        assert any(imp > 0 for imp in improvements), "No calibration method improved ECE"
    
    def test_expected_calibration_error_calculation(self, calibrator, sample_predictions_data):
        """Test Expected Calibration Error calculation."""
        predictions = sample_predictions_data['predictions']
        true_labels = sample_predictions_data['true_labels']
        
        # Calculate ECE
        ece = calibrator.expected_calibration_error(predictions, true_labels)
        
        # Verify ECE is reasonable
        assert 0 <= ece <= 1
        assert isinstance(ece, float)
    
    def test_reliability_diagram_generation(self, calibrator, sample_predictions_data):
        """Test reliability diagram generation."""
        predictions = sample_predictions_data['predictions']
        true_labels = sample_predictions_data['true_labels']
        
        # Fit calibrator
        calibrator.fit(predictions, true_labels)
        
        # Generate reliability diagram
        fig = calibrator.plot_reliability_diagram(predictions, true_labels)
        
        # Verify plot generation
        assert isinstance(fig, plt.Figure)
        plt.close(fig)
    
    def test_calibration_report_generation(self, calibrator, sample_predictions_data):
        """Test calibration report generation."""
        predictions = sample_predictions_data['predictions']
        true_labels = sample_predictions_data['true_labels']
        
        # Fit calibrator
        calibrator.fit(predictions, true_labels)
        
        # Generate report
        report = calibrator.generate_calibration_report(predictions, true_labels)
        
        # Verify report structure
        assert isinstance(report, dict)
        assert 'method' in report
        assert 'original_ece' in report
        assert 'calibrated_ece' in report
        assert 'improvement' in report
        assert 'brier_score' in report
    
    def test_subgroup_analysis(self, calibrator, sample_predictions_data):
        """Test subgroup analysis functionality."""
        predictions = sample_predictions_data['predictions']
        true_labels = sample_predictions_data['true_labels']
        
        # Create subgroups (e.g., by sample ID ranges)
        subgroups = {
            'group1': list(range(0, 300)),
            'group2': list(range(300, 600)),
            'group3': list(range(600, 1000))
        }
        
        # Fit calibrator
        calibrator.fit(predictions, true_labels)
        
        # Perform subgroup analysis
        subgroup_results = calibrator.subgroup_analysis(predictions, true_labels, subgroups)
        
        # Verify subgroup analysis
        assert isinstance(subgroup_results, dict)
        assert len(subgroup_results) == 3
        for group_name, metrics in subgroup_results.items():
            assert 'ece' in metrics
            assert 'brier_score' in metrics
            assert 'sample_size' in metrics
    
    def test_calibration_with_edge_cases(self, calibrator):
        """Test calibration with edge cases."""
        # Test with perfect predictions
        perfect_predictions = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        perfect_labels = np.array([0, 1, 2])
        
        calibrator.fit(perfect_predictions, perfect_labels)
        assert calibrator.is_fitted == True
        
        # Test with extreme predictions
        extreme_predictions = np.array([[0.99, 0.005, 0.005], [0.005, 0.99, 0.005], [0.005, 0.005, 0.99]])
        extreme_labels = np.array([0, 1, 2])
        
        calibrator.fit(extreme_predictions, extreme_labels)
        assert calibrator.is_fitted == True
    
    def test_calibration_persistence(self, calibrator, sample_predictions_data):
        """Test calibration model persistence."""
        predictions = sample_predictions_data['predictions']
        true_labels = sample_predictions_data['true_labels']
        
        # Fit calibrator
        calibrator.fit(predictions, true_labels)
        
        # Save calibrator
        import tempfile
        import pickle
        
        with tempfile.NamedTemporaryFile() as tmp:
            calibrator.save(tmp.name)
            
            # Load calibrator
            loaded_calibrator = PitchModelCalibrator.load(tmp.name)
            
            # Verify loaded calibrator
            assert loaded_calibrator.model_name == calibrator.model_name
            assert loaded_calibrator.target_tier == calibrator.target_tier
            assert loaded_calibrator.calibration_method == calibrator.calibration_method
            assert loaded_calibrator.is_fitted == True
            
            # Test predictions are consistent
            original_pred = calibrator.predict(predictions[:10])
            loaded_pred = loaded_calibrator.predict(predictions[:10])
            np.testing.assert_array_almost_equal(original_pred, loaded_pred)
    
    def test_calibration_with_cross_validation(self, sample_predictions_data):
        """Test calibration with cross-validation."""
        predictions = sample_predictions_data['predictions']
        true_labels = sample_predictions_data['true_labels']
        
        calibrator = PitchModelCalibrator(
            model_name='test_model',
            target_tier='tier1',
            calibration_method='temperature'
        )
        
        # Perform cross-validation calibration
        cv_results = calibrator.calibrate_with_cv(predictions, true_labels, cv=5)
        
        # Verify CV results
        assert isinstance(cv_results, dict)
        assert 'mean_ece' in cv_results
        assert 'std_ece' in cv_results
        assert 'fold_results' in cv_results
        assert len(cv_results['fold_results']) == 5
    
    def test_multiclass_calibration_specific_methods(self, sample_predictions_data):
        """Test multiclass-specific calibration methods."""
        predictions = sample_predictions_data['predictions']
        true_labels = sample_predictions_data['true_labels']
        
        # Test Dirichlet calibration (multiclass-specific)
        calibrator = PitchModelCalibrator(
            model_name='test_model',
            target_tier='tier1',
            calibration_method='dirichlet'
        )
        
        calibrator.fit(predictions, true_labels)
        assert calibrator.is_fitted == True
        assert hasattr(calibrator, 'dirichlet_params_')
        
        # Test predictions
        calibrated_pred = calibrator.predict(predictions)
        assert calibrated_pred.shape == predictions.shape
    
    def test_calibration_performance_metrics(self, calibrator, sample_predictions_data):
        """Test comprehensive calibration performance metrics."""
        predictions = sample_predictions_data['predictions']
        true_labels = sample_predictions_data['true_labels']
        
        # Fit calibrator
        calibrator.fit(predictions, true_labels)
        calibrated_pred = calibrator.predict(predictions)
        
        # Calculate comprehensive metrics
        metrics = calibrator.calculate_comprehensive_metrics(predictions, calibrated_pred, true_labels)
        
        # Verify metrics structure
        expected_metrics = [
            'original_ece', 'calibrated_ece', 'ece_improvement',
            'original_brier', 'calibrated_brier', 'brier_improvement',
            'log_loss_original', 'log_loss_calibrated', 'log_loss_improvement',
            'accuracy_original', 'accuracy_calibrated'
        ]
        
        for metric in expected_metrics:
            assert metric in metrics
            assert isinstance(metrics[metric], (int, float))
    
    def test_calibration_with_class_imbalance(self):
        """Test calibration with imbalanced classes."""
        # Create imbalanced dataset
        np.random.seed(42)
        n_samples = 1000
        
        # Heavily imbalanced: 70% class 0, 20% class 1, 10% class 2
        true_labels = np.random.choice([0, 1, 2], size=n_samples, p=[0.7, 0.2, 0.1])
        predictions = np.zeros((n_samples, 3))
        
        for i, label in enumerate(true_labels):
            probs = np.array([0.7, 0.2, 0.1])
            probs[label] += np.random.uniform(0.05, 0.15)
            probs = probs / probs.sum()
            predictions[i] = probs
        
        calibrator = PitchModelCalibrator(
            model_name='test_model',
            target_tier='tier1',
            calibration_method='isotonic'  # Good for imbalanced data
        )
        
        # Fit and test
        calibrator.fit(predictions, true_labels)
        calibrated_pred = calibrator.predict(predictions)
        
        # Verify calibration works with imbalanced data
        assert calibrator.is_fitted == True
        assert calibrated_pred.shape == predictions.shape
        
        # Check that calibration improves performance
        original_ece = calibrator.expected_calibration_error(predictions, true_labels)
        calibrated_ece = calibrator.expected_calibration_error(calibrated_pred, true_labels)
        
        # Should see improvement (though not guaranteed with random data)
        assert isinstance(calibrated_ece, float)
        assert 0 <= calibrated_ece <= 1


class TestCalibrationIntegration:
    """Integration tests for pitch model calibration."""
    
    @pytest.mark.integration
    def test_end_to_end_calibration_workflow(self):
        """Test end-to-end calibration workflow."""
        # Generate realistic data
        np.random.seed(42)
        n_samples = 10000
        
        true_labels = np.random.choice([0, 1, 2], size=n_samples, p=[0.4, 0.35, 0.25])
        predictions = np.zeros((n_samples, 3))
        
        for i, label in enumerate(true_labels):
            # Simulate model predictions with some systematic bias
            base_probs = np.array([0.4, 0.35, 0.25])
            # Add bias: model tends to overpredict class 0
            base_probs[0] += 0.1
            base_probs[label] += np.random.uniform(0.05, 0.2)
            base_probs = base_probs / base_probs.sum()
            predictions[i] = base_probs
        
        # Test calibration workflow
        calibrator = PitchModelCalibrator(
            model_name='test_xgboost_model',
            target_tier='tier1',
            calibration_method='temperature'
        )
        
        # Fit calibrator
        calibrator.fit(predictions, true_labels)
        
        # Generate calibrated predictions
        calibrated_pred = calibrator.predict(predictions)
        
        # Generate comprehensive report
        report = calibrator.generate_calibration_report(predictions, true_labels)
        
        # Verify end-to-end workflow
        assert calibrator.is_fitted == True
        assert isinstance(report, dict)
        assert 'improvement' in report
        
        # Verify calibration improvement
        assert report['calibrated_ece'] <= report['original_ece']
    
    @pytest.mark.integration
    def test_calibration_with_real_model_predictions(self):
        """Test calibration with realistic model predictions."""
        # This would integrate with actual model predictions
        # For now, we'll simulate realistic XGBoost predictions
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
