"""
Tests for Rich Result Classes

Tests cover:
- MetricValue and Metrics
- ValidationCurve
- FeatureImportance
- Residuals analysis
- TrainResult functionality

Author: Agent Cascade
Date: April 24, 2026
"""

import numpy as np
import pytest


pytest.importorskip('pydantic', minversion='2.0')

from mlb_predict.config import ModelConfig, ModelFamily, TargetVariable
from mlb_predict.core.results import (
    FeatureImportance,
    Metrics,
    MetricValue,
    Residuals,
    TrainResult,
    ValidationCurve,
)


class TestMetricValue:
    """Test MetricValue class."""

    def test_basic_value(self):
        """Test basic metric value."""
        m = MetricValue(value=0.85)
        assert m.value == 0.85
        assert float(m) == 0.85

    def test_with_confidence_interval(self):
        """Test metric with CI."""
        m = MetricValue(value=0.85, std=0.02, ci_lower=0.81, ci_upper=0.89)
        assert m.value == 0.85
        assert m.std == 0.02
        assert m.ci_lower == 0.81
        assert m.ci_upper == 0.89

    def test_repr(self):
        """Test string representation."""
        m = MetricValue(value=0.85, std=0.02)
        assert '0.85' in repr(m)
        assert '0.02' in repr(m)


class TestMetrics:
    """Test Metrics collection."""

    def test_empty_metrics(self):
        """Test empty metrics."""
        m = Metrics()
        assert m.to_dict() == {}

    def test_basic_metrics(self):
        """Test setting basic metrics."""
        m = Metrics(
            roc_auc=MetricValue(value=0.85),
            accuracy=MetricValue(value=0.80),
            log_loss=MetricValue(value=0.35),
        )
        assert m.roc_auc.value == 0.85
        assert m.accuracy.value == 0.80
        assert m.log_loss.value == 0.35

    def test_to_dict(self):
        """Test conversion to dict."""
        m = Metrics(
            roc_auc=MetricValue(value=0.85),
            custom={'my_metric': MetricValue(value=0.90)},
        )
        d = m.to_dict()
        assert d['roc_auc'] == 0.85
        assert d['custom_my_metric'] == 0.90

    def test_get_best_metric(self):
        """Test finding best metric."""
        m = Metrics(roc_auc=MetricValue(value=0.85))
        name, value = m.get_best_metric()
        assert name == 'roc_auc'
        assert value == 0.85

    def test_compare_to(self):
        """Test comparing two metrics."""
        m1 = Metrics(roc_auc=MetricValue(value=0.85))
        m2 = Metrics(roc_auc=MetricValue(value=0.83))

        diff = m1.compare_to(m2)
        assert diff['roc_auc'] == pytest.approx(0.02, abs=0.001)


class TestValidationCurve:
    """Test ValidationCurve."""

    def test_basic_curve(self):
        """Test creating a validation curve."""
        curve = ValidationCurve(
            metric_name='auc',
            train_values=[0.80, 0.85, 0.88, 0.90],
            val_values=[0.78, 0.82, 0.83, 0.82],
            iterations=[0, 50, 100, 150],
            best_iteration=100,
            best_val_value=0.83,
        )
        assert curve.metric_name == 'auc'
        assert len(curve.train_values) == 4
        assert curve.best_iteration == 100

    def test_find_best_iteration_max(self):
        """Test finding best iteration with max mode."""
        curve = ValidationCurve(
            metric_name='auc',
            train_values=[0.8, 0.85, 0.88],
            val_values=[0.75, 0.83, 0.82],
            iterations=[0, 100, 200],
        )
        best_iter = curve.find_best_iteration(mode='max')
        assert best_iter == 100  # Highest val value

    def test_find_best_iteration_min(self):
        """Test finding best iteration with min mode."""
        curve = ValidationCurve(
            metric_name='logloss',
            train_values=[0.5, 0.4, 0.35],
            val_values=[0.6, 0.45, 0.48],
            iterations=[0, 100, 200],
        )
        best_iter = curve.find_best_iteration(mode='min')
        assert best_iter == 100  # Lowest val value


class TestFeatureImportance:
    """Test FeatureImportance."""

    def test_basic_importance(self):
        """Test basic feature importance."""
        fi = FeatureImportance(
            feature_name='pitch_speed',
            importance_score=0.15,
            importance_rank=1,
            method='gain',
        )
        assert fi.feature_name == 'pitch_speed'
        assert fi.importance_score == 0.15
        assert fi.importance_rank == 1
        assert fi.method == 'gain'


class TestResiduals:
    """Test Residuals class."""

    def test_basic_residuals(self):
        """Test creating residuals."""
        y_true = [1, 0, 1, 0, 1]
        y_pred = [1, 1, 1, 0, 0]
        y_prob = [0.8, 0.6, 0.7, 0.3, 0.4]

        res = Residuals(
            y_true=y_true,
            y_pred=y_pred,
            y_prob=y_prob,
        )

        assert len(res.y_true) == 5
        assert len(res.residuals) == 5
        assert res.residuals == [0, -1, 0, 0, 1]

    def test_residuals_analysis(self):
        """Test residuals statistics."""
        np.random.seed(42)
        y_true = [1, 0, 1, 0, 1, 0, 1, 0]
        y_pred = [1, 0, 1, 0, 0, 1, 1, 0]  # 2 errors
        y_prob = [0.8, 0.3, 0.9, 0.2, 0.4, 0.6, 0.85, 0.15]

        res = Residuals(y_true=y_true, y_pred=y_pred, y_prob=y_prob)
        stats = res.analyze()

        assert 'mean' in stats
        assert 'std' in stats
        assert 'max_abs' in stats

    def test_residuals_to_dataframe(self):
        """Test converting residuals to DataFrame."""
        pytest.importorskip('pandas')

        res = Residuals(
            y_true=[1, 0, 1],
            y_pred=[1, 0, 0],
            y_prob=[0.8, 0.3, 0.4],
        )

        df = res.to_dataframe()
        assert len(df) == 3
        assert 'y_true' in df.columns
        assert 'y_pred' in df.columns
        assert 'y_prob' in df.columns
        assert 'residual' in df.columns


class TestTrainResult:
    """Test TrainResult class."""

    @pytest.fixture
    def basic_config(self):
        """Create basic config for tests."""
        return ModelConfig(
            family=ModelFamily.XGBOOST,
            target=TargetVariable.SWING_DECISION,
        )

    def test_basic_result(self, basic_config):
        """Test creating basic TrainResult."""
        result = TrainResult(
            model_id=123,
            model_name='test_model',
            config=basic_config,
            artifact_path='models/test.pkl',
            train_metrics=Metrics(roc_auc=MetricValue(value=0.85)),
            val_metrics=Metrics(roc_auc=MetricValue(value=0.83)),
            training_time_seconds=45.0,
            n_samples_train=10000,
            n_samples_val=2000,
            n_features=220,
        )

        assert result.model_id == 123
        assert result.model_name == 'test_model'
        assert result.training_time_seconds == 45.0
        assert result.n_features == 220

    def test_get_best_features(self, basic_config):
        """Test getting top features."""
        result = TrainResult(
            model_id=123,
            model_name='test_model',
            config=basic_config,
            artifact_path='models/test.pkl',
            train_metrics=Metrics(),
            val_metrics=Metrics(),
            training_time_seconds=45.0,
            n_samples_train=10000,
            n_samples_val=2000,
            n_features=220,
            feature_importance=[
                FeatureImportance(feature_name='f1', importance_score=0.20, importance_rank=1),
                FeatureImportance(feature_name='f2', importance_score=0.15, importance_rank=2),
                FeatureImportance(feature_name='f3', importance_score=0.10, importance_rank=3),
            ],
        )

        top = result.get_best_features(n=2)
        assert len(top) == 2
        assert top[0].feature_name == 'f1'
        assert top[1].feature_name == 'f2'

    def test_compare_to(self, basic_config):
        """Test comparing two results."""
        result1 = TrainResult(
            model_id=1,
            model_name='model_a',
            config=basic_config,
            artifact_path='models/a.pkl',
            train_metrics=Metrics(),
            val_metrics=Metrics(roc_auc=MetricValue(value=0.85)),
            training_time_seconds=40.0,
            n_samples_train=10000,
            n_samples_val=2000,
            n_features=220,
        )

        result2 = TrainResult(
            model_id=2,
            model_name='model_b',
            config=basic_config,
            artifact_path='models/b.pkl',
            train_metrics=Metrics(),
            val_metrics=Metrics(roc_auc=MetricValue(value=0.83)),
            training_time_seconds=50.0,
            n_samples_train=8000,
            n_samples_val=2000,
            n_features=220,
        )

        comparison = result1.compare_to(result2)
        assert comparison['val_auc_diff'] == pytest.approx(0.02, abs=0.001)
        assert comparison['model_a_id'] == 1
        assert comparison['model_b_id'] == 2

    def test_is_better_than(self, basic_config):
        """Test is_better_than comparison."""
        result1 = TrainResult(
            model_id=1,
            model_name='model_a',
            config=basic_config,
            artifact_path='models/a.pkl',
            train_metrics=Metrics(),
            val_metrics=Metrics(roc_auc=MetricValue(value=0.85)),
            training_time_seconds=40.0,
            n_samples_train=10000,
            n_samples_val=2000,
            n_features=220,
        )

        result2 = TrainResult(
            model_id=2,
            model_name='model_b',
            config=basic_config,
            artifact_path='models/b.pkl',
            train_metrics=Metrics(),
            val_metrics=Metrics(roc_auc=MetricValue(value=0.83)),
            training_time_seconds=40.0,
            n_samples_train=10000,
            n_samples_val=2000,
            n_features=220,
        )

        assert result1.is_better_than(result2)
        assert not result2.is_better_than(result1)

    def test_summary(self, basic_config):
        """Test summary method."""
        result = TrainResult(
            model_id=123,
            model_name='test_model',
            config=basic_config,
            artifact_path='models/test.pkl',
            train_metrics=Metrics(roc_auc=MetricValue(value=0.85)),
            val_metrics=Metrics(roc_auc=MetricValue(value=0.83)),
            training_time_seconds=45.0,
            n_samples_train=10000,
            n_samples_val=2000,
            n_features=220,
        )

        summary = result.summary()
        assert '123' in summary
        assert 'test_model' in summary
        assert '0.83' in summary
        assert '45.0' in summary

    def test_generate_report(self, basic_config, tmp_path):
        """Test report generation."""
        result = TrainResult(
            model_id=123,
            model_name='test_model',
            config=basic_config,
            artifact_path='models/test.pkl',
            train_metrics=Metrics(roc_auc=MetricValue(value=0.85)),
            val_metrics=Metrics(roc_auc=MetricValue(value=0.83)),
            training_time_seconds=45.0,
            n_samples_train=10000,
            n_samples_val=2000,
            n_features=220,
        )

        report_path = tmp_path / 'report.md'
        report = result.generate_report(str(report_path))

        assert 'test_model' in report
        assert '123' in report
        assert report_path.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
