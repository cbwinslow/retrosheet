"""Rich Result Classes for MLB Prediction Framework

These classes provide comprehensive results with access to:
- Model artifacts and metadata
- Residuals for analysis
- Validation curves
- Feature importance
- Reproducibility info

Author: Agent Cascade
Date: April 24, 2026
Depends On: pydantic>=2.0, pandas, numpy, matplotlib
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class MetricValue(BaseModel):
    """Single metric with confidence interval."""
    value: float
    std: float | None = None
    ci_lower: float | None = None
    ci_upper: float | None = None

    def __float__(self):
        return self.value

    def __repr__(self):
        if self.std is not None:
            return f'{self.value:.4f} ± {self.std:.4f}'
        return f'{self.value:.4f}'


class Metrics(BaseModel):
    """Complete metrics collection for model evaluation."""
    # Binary classification metrics
    roc_auc: MetricValue | None = None
    pr_auc: MetricValue | None = None
    log_loss: MetricValue | None = None
    brier_score: MetricValue | None = None

    # Classification metrics
    accuracy: MetricValue | None = None
    precision: MetricValue | None = None
    recall: MetricValue | None = None
    f1: MetricValue | None = None
    f1_micro: MetricValue | None = None
    f1_macro: MetricValue | None = None
    f1_weighted: MetricValue | None = None

    # Calibration metrics
    calibration_error: MetricValue | None = None
    expected_calibration_error: MetricValue | None = None
    max_calibration_error: MetricValue | None = None

    # Ranking metrics
    ndcg: MetricValue | None = None
    map_score: MetricValue | None = None

    # Regression metrics (for run expectancy, win probability)
    rmse: MetricValue | None = None
    mae: MetricValue | None = None
    mape: MetricValue | None = None
    r2: MetricValue | None = None

    # Baseball-specific metrics
    log_likelihood: MetricValue | None = None

    # Custom metrics
    custom: dict[str, MetricValue] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, float]:
        """Convert to flat dict for serialization."""
        result = {}
        for field_name, metric in self.__dict__.items():
            if isinstance(metric, MetricValue):
                result[field_name] = metric.value
            elif isinstance(metric, dict) and field_name == 'custom':
                for k, v in metric.items():
                    if isinstance(v, MetricValue):
                        result[f'custom_{k}'] = v.value
        return result

    def get_best_metric(self) -> tuple[str, float]:
        """Get the best metric name and value.
        
        For binary classification, prefers ROC AUC.
        For multiclass, prefers accuracy or F1.
        """
        if self.roc_auc is not None:
            return ('roc_auc', self.roc_auc.value)
        if self.accuracy is not None:
            return ('accuracy', self.accuracy.value)
        if self.f1 is not None:
            return ('f1', self.f1.value)
        if self.rmse is not None:
            return ('rmse', -self.rmse.value)  # Lower is better
        # Return first available
        for name, metric in self.__dict__.items():
            if isinstance(metric, MetricValue):
                return (name, metric.value)
        return ('unknown', 0.0)

    def compare_to(self, other: 'Metrics') -> dict[str, float]:
        """Compare these metrics to another set.
        
        Returns:
            Dict mapping metric name to difference (self - other)
        """
        diffs = {}
        for field_name in self.__dict__.keys():
            if field_name == 'custom':
                continue
            self_val = getattr(self, field_name)
            other_val = getattr(other, field_name)
            if isinstance(self_val, MetricValue) and isinstance(other_val, MetricValue):
                diffs[field_name] = self_val.value - other_val.value
        return diffs


class ValidationCurve(BaseModel):
    """Training/validation curve for monitoring model convergence."""
    metric_name: str
    train_values: list[float]
    val_values: list[float]
    iterations: list[int]
    best_iteration: int | None = None
    best_train_value: float | None = None
    best_val_value: float | None = None

    def find_best_iteration(self, mode: str = 'max') -> int:
        """Find the iteration with best validation performance.
        
        Args:
            mode: 'max' for metrics where higher is better (AUC),
                  'min' for metrics where lower is better (loss)
        """
        if mode == 'max':
            best_idx = max(range(len(self.val_values)), key=lambda i: self.val_values[i])
        else:
            best_idx = min(range(len(self.val_values)), key=lambda i: self.val_values[i])
        return self.iterations[best_idx]

    def to_dataframe(self):
        """Convert to pandas DataFrame."""
        try:
            import pandas as pd
            return pd.DataFrame({
                'iteration': self.iterations,
                'train': self.train_values,
                'val': self.val_values,
                'gap': [t - v for t, v in zip(self.train_values, self.val_values)],
            })
        except ImportError:
            raise ImportError('pandas required for to_dataframe()')

    def plot(self, figsize: tuple[int, int] = (10, 6)):
        """Plot using matplotlib."""
        try:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=figsize)
            ax.plot(self.iterations, self.train_values, label='Train', linewidth=2)
            ax.plot(self.iterations, self.val_values, label='Validation', linewidth=2)

            if self.best_iteration is not None:
                ax.axvline(self.best_iteration, color='red', linestyle='--',
                          alpha=0.5, label=f'Best ({self.best_iteration})')

            ax.set_xlabel('Iteration')
            ax.set_ylabel(self.metric_name)
            ax.set_title(f'Training Curve: {self.metric_name}')
            ax.legend()
            ax.grid(True, alpha=0.3)

            return fig
        except ImportError:
            raise ImportError('matplotlib required for plot()')


class FeatureImportance(BaseModel):
    """Feature importance score with metadata."""
    feature_name: str
    importance_score: float
    importance_rank: int
    method: str = 'gain'  # 'gain', 'weight', 'cover', 'shap', 'permutation'
    std: float | None = None
    std_dev: float | None = None  # Alias for std

    class Config:
        populate_by_name = True


class Residuals(BaseModel):
    """Model residuals for deep analysis.
    
    Provides access to prediction errors and diagnostic tools
    for understanding model performance across different subgroups.
    """
    y_true: list[float]
    y_pred: list[float]  # Binary predictions (0 or 1)
    y_prob: list[float]  # Probability predictions
    residuals: list[float] | None = None  # y_true - y_pred
    sample_ids: list[int] | None = None
    feature_values: dict[str, list[Any]] | None = None  # For subgroup analysis

    def __init__(self, **data):
        super().__init__(**data)
        # Compute residuals if not provided
        if self.residuals is None and self.y_true and self.y_pred:
            self.residuals = [t - p for t, p in zip(self.y_true, self.y_pred)]

    def to_dataframe(self):
        """Convert to pandas DataFrame."""
        try:
            import pandas as pd
            data = {
                'y_true': self.y_true,
                'y_pred': self.y_pred,
                'y_prob': self.y_prob,
            }
            if self.residuals:
                data['residual'] = self.residuals
            if self.sample_ids:
                data['sample_id'] = self.sample_ids

            df = pd.DataFrame(data)

            # Add feature values if available
            if self.feature_values:
                for feature, values in self.feature_values.items():
                    df[feature] = values

            return df
        except ImportError:
            raise ImportError('pandas required for to_dataframe()')

    def analyze(self) -> dict[str, float]:
        """Compute residual statistics."""
        if not self.residuals:
            return {}

        import numpy as np
        res = np.array(self.residuals)

        stats = {
            'mean': float(np.mean(res)),
            'std': float(np.std(res)),
            'min': float(np.min(res)),
            'max': float(np.max(res)),
            'max_abs': float(np.max(np.abs(res))),
            'median': float(np.median(res)),
        }

        # Higher moments
        if len(res) > 3:
            try:
                from scipy import stats as scipy_stats
                stats['skewness'] = float(scipy_stats.skew(res))
                stats['kurtosis'] = float(scipy_stats.kurtosis(res))
            except ImportError:
                pass

        # Percentiles
        stats['q25'] = float(np.percentile(res, 25))
        stats['q75'] = float(np.percentile(res, 75))
        stats['iqr'] = stats['q75'] - stats['q25']

        return stats

    def analyze_by_feature(self, feature_name: str) -> dict[str, Any]:
        """Analyze residuals grouped by feature values."""
        if not self.feature_values or feature_name not in self.feature_values:
            raise ValueError(f"Feature '{feature_name}' not available in residuals")

        try:
            import numpy as np
            import pandas as pd

            df = self.to_dataframe()

            # Group by feature and compute stats
            grouped = df.groupby(feature_name).agg({
                'residual': ['mean', 'std', 'count'],
                'y_true': 'mean',
                'y_prob': 'mean',
            })

            return grouped.to_dict()
        except ImportError:
            raise ImportError('pandas required for analyze_by_feature()')

    def plot_residuals(self, figsize: tuple[int, int] = (12, 10)):
        """Create residual diagnostic plots."""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            from scipy import stats as scipy_stats

            fig, axes = plt.subplots(2, 2, figsize=figsize)

            res = np.array(self.residuals) if self.residuals else np.array([])
            y_prob = np.array(self.y_prob)

            if len(res) == 0:
                return fig

            # 1. Residual vs Fitted (Predicted Probability)
            ax1 = axes[0, 0]
            ax1.scatter(y_prob, res, alpha=0.5, s=20)
            ax1.axhline(y=0, color='r', linestyle='--', linewidth=2)
            ax1.set_xlabel('Predicted Probability')
            ax1.set_ylabel('Residual')
            ax1.set_title('Residuals vs Predicted')
            ax1.grid(True, alpha=0.3)

            # 2. Q-Q Plot
            ax2 = axes[0, 1]
            scipy_stats.probplot(res, dist='norm', plot=ax2)
            ax2.set_title('Q-Q Plot (Normality Check)')
            ax2.grid(True, alpha=0.3)

            # 3. Histogram
            ax3 = axes[1, 0]
            ax3.hist(res, bins=50, edgecolor='black', alpha=0.7, density=True)
            ax3.axvline(x=0, color='r', linestyle='--', linewidth=2)
            ax3.set_xlabel('Residual')
            ax3.set_ylabel('Density')
            ax3.set_title('Residual Distribution')
            ax3.grid(True, alpha=0.3)

            # 4. Residuals by predicted class
            ax4 = axes[1, 1]
            pred_classes = (y_prob > 0.5).astype(int)
            for cls in [0, 1]:
                mask = pred_classes == cls
                if mask.any():
                    ax4.hist(res[mask], bins=30, alpha=0.5,
                            label=f'Pred {cls}', density=True)
            ax4.set_xlabel('Residual')
            ax4.set_ylabel('Density')
            ax4.set_title('Residuals by Predicted Class')
            ax4.legend()
            ax4.grid(True, alpha=0.3)

            plt.tight_layout()
            return fig

        except ImportError as e:
            raise ImportError(f'matplotlib and scipy required for plot_residuals(): {e}')

    def plot_calibration(self, n_bins: int = 10, figsize: tuple[int, int] = (10, 6)):
        """Plot calibration curve."""
        try:
            import matplotlib.pyplot as plt
            import numpy as np

            y_true = np.array(self.y_true)
            y_prob = np.array(self.y_prob)

            # Compute calibration
            bin_boundaries = np.linspace(0, 1, n_bins + 1)
            bin_lowers = bin_boundaries[:-1]
            bin_uppers = bin_boundaries[1:]

            bin_centers = []
            bin_accuracies = []
            bin_counts = []

            for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
                in_bin = (y_prob > bin_lower) & (y_prob <= bin_upper)
                prop_in_bin = in_bin.mean()

                if prop_in_bin > 0:
                    accuracy_in_bin = y_true[in_bin].mean()
                    avg_confidence_in_bin = y_prob[in_bin].mean()
                    bin_centers.append(avg_confidence_in_bin)
                    bin_accuracies.append(accuracy_in_bin)
                    bin_counts.append(in_bin.sum())

            fig, ax = plt.subplots(figsize=figsize)

            # Perfect calibration line
            ax.plot([0, 1], [0, 1], 'k--', label='Perfect Calibration', linewidth=2)

            # Actual calibration
            ax.plot(bin_centers, bin_accuracies, 'o-', label='Model', linewidth=2, markersize=8)

            # Histogram of predictions
            ax2 = ax.twinx()
            ax2.hist(y_prob, bins=n_bins, range=(0, 1), alpha=0.3, label='Distribution')
            ax2.set_ylabel('Count')

            ax.set_xlabel('Mean Predicted Probability')
            ax.set_ylabel('Fraction of Positives')
            ax.set_title('Calibration Curve (Reliability Diagram)')
            ax.legend(loc='lower right')
            ax.grid(True, alpha=0.3)
            ax.set_xlim([0, 1])
            ax.set_ylim([0, 1])

            return fig

        except ImportError as e:
            raise ImportError(f'matplotlib and numpy required for plot_calibration(): {e}')


class PredictionRecord(BaseModel):
    """Single prediction record with metadata."""
    sample_id: int
    game_pk: int | None = None
    play_id: str | None = None
    batter_id: int | None = None
    pitcher_id: int | None = None

    # Features
    feature_values: dict[str, Any] | None = None

    # Predictions
    y_true: float | None = None
    y_pred: float
    y_prob: float

    # Metadata
    prediction_time: datetime | None = None
    model_id: int | None = None


class PredictResult(BaseModel):
    """Complete prediction result with full diagnostic capability."""

    model_id: int
    prediction_id: int | None = None
    prediction_name: str | None = None

    # Data
    predictions: list[PredictionRecord]
    n_predictions: int

    # Timing
    prediction_time_seconds: float
    created_at: datetime = Field(default_factory=datetime.now)

    # If ground truth available
    actual_outcomes: list[float] | None = None

    # Computed metrics
    metrics: Metrics | None = None
    residuals: Residuals | None = None

    # Calibration
    calibration_curve: dict[str, list[float]] | None = None

    def compute_metrics(self) -> Metrics:
        """Compute metrics from predictions."""
        import numpy as np
        from sklearn.metrics import (
            accuracy_score,
            brier_score_loss,
            f1_score,
            log_loss,
            precision_score,
            recall_score,
            roc_auc_score,
        )

        if not self.actual_outcomes:
            raise ValueError('No ground truth available for metric computation')

        y_true = np.array([p.y_true for p in self.predictions if p.y_true is not None])
        y_prob = np.array([p.y_prob for p in self.predictions if p.y_true is not None])
        y_pred = (y_prob > 0.5).astype(int)

        metrics = Metrics()

        # Binary metrics
        if len(np.unique(y_true)) == 2:
            try:
                metrics.roc_auc = MetricValue(value=roc_auc_score(y_true, y_prob))
            except:
                pass

            try:
                metrics.log_loss = MetricValue(value=log_loss(y_true, y_prob))
            except:
                pass

            try:
                metrics.brier_score = MetricValue(value=brier_score_loss(y_true, y_prob))
            except:
                pass

            metrics.accuracy = MetricValue(value=accuracy_score(y_true, y_pred))
            metrics.precision = MetricValue(value=precision_score(y_true, y_pred, zero_division=0))
            metrics.recall = MetricValue(value=recall_score(y_true, y_pred, zero_division=0))
            metrics.f1 = MetricValue(value=f1_score(y_true, y_pred, zero_division=0))

        self.metrics = metrics
        return metrics

    def to_dataframe(self):
        """Convert predictions to pandas DataFrame."""
        try:
            import pandas as pd

            data = []
            for pred in self.predictions:
                row = {
                    'sample_id': pred.sample_id,
                    'game_pk': pred.game_pk,
                    'batter_id': pred.batter_id,
                    'pitcher_id': pred.pitcher_id,
                    'y_true': pred.y_true,
                    'y_pred': pred.y_pred,
                    'y_prob': pred.y_prob,
                }
                if pred.feature_values:
                    row.update(pred.feature_values)
                data.append(row)

            return pd.DataFrame(data)
        except ImportError:
            raise ImportError('pandas required for to_dataframe()')

    def save_to_sql(self, table_name: str, connection_string: str):
        """Save predictions to SQL database."""
        try:
            from sqlalchemy import create_engine
            df = self.to_dataframe()
            engine = create_engine(connection_string)
            df.to_sql(table_name, engine, if_exists='append', index=False)
        except ImportError:
            raise ImportError('pandas and sqlalchemy required for save_to_sql()')


class TrainResult(BaseModel):
    """Complete training result with all artifacts for analysis.
    
    This is the main result class returned by ModelTrainer.train().
    It provides access to:
    - Model artifacts and metadata
    - Performance metrics (train/val/test)
    - Residuals for error analysis
    - Validation curves for convergence monitoring
    - Feature importance for interpretability
    - Full configuration for reproducibility
    """

    # Identity
    model_id: int
    model_name: str
    experiment_id: int | None = None
    run_id: str | None = None

    # Config
    config: Any  # ModelConfig - use Any to avoid circular import
    config_path: str | None = None

    # Provenance
    git_commit: str | None = None
    git_branch: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    # Paths
    artifact_path: str
    report_path: str | None = None
    config_output_path: str | None = None

    # Metrics
    train_metrics: Metrics
    val_metrics: Metrics
    test_metrics: Metrics | None = None

    # Detailed results
    validation_curves: list[ValidationCurve] = Field(default_factory=list)
    feature_importance: list[FeatureImportance] = Field(default_factory=list)
    cv_results: list[Metrics] | None = None
    cv_folds: int | None = None

    # Error analysis
    residuals: Residuals | None = None
    train_residuals: Residuals | None = None
    val_residuals: Residuals | None = None
    test_residuals: Residuals | None = None

    # SHAP values (stored separately due to size)
    shap_values_path: str | None = None
    shap_summary_path: str | None = None

    # Calibration
    calibration_data: dict[str, Any] | None = None

    # Metadata
    training_time_seconds: float
    n_samples_train: int
    n_samples_val: int
    n_samples_test: int | None = None
    n_features: int
    feature_names: list[str] | None = None

    # Status
    status: str = 'completed'  # completed, failed, interrupted
    error_message: str | None = None
    warnings: list[str] = Field(default_factory=list)

    def save_to_registry(self, connection_string: str | None = None) -> None:
        """Save result to models.model_registry."""
        try:
            import psycopg2

            if connection_string is None:
                connection_string = 'dbname=retrosheet'

            conn = psycopg2.connect(connection_string)
            cur = conn.cursor()

            # Update metrics in registry
            metrics_dict = {}
            if self.test_metrics:
                metrics_dict = self.test_metrics.to_dict()
            elif self.val_metrics:
                metrics_dict = self.val_metrics.to_dict()

            cur.execute("""
                UPDATE models.model_registry
                SET metrics = %s,
                    feature_spec = %s,
                    updated_at = NOW()
                WHERE model_id = %s
            """, (
                json.dumps(metrics_dict),
                json.dumps({
                    'n_features': self.n_features,
                    'feature_names': self.feature_names,
                    'training_time_seconds': self.training_time_seconds,
                }),
                self.model_id,
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f'Warning: Could not save to registry: {e}')

    def to_dataframe(self):
        """Convert to DataFrame summary."""
        try:
            import pandas as pd

            data = {
                'model_id': [self.model_id],
                'model_name': [self.model_name],
                'family': [self.config.family.value if hasattr(self.config, 'family') else 'unknown'],
                'target': [self.config.target.value if hasattr(self.config, 'target') else 'unknown'],
                'status': [self.status],
                'train_auc': [self.train_metrics.roc_auc.value if self.train_metrics.roc_auc else None],
                'val_auc': [self.val_metrics.roc_auc.value if self.val_metrics.roc_auc else None],
                'test_auc': [self.test_metrics.roc_auc.value if self.test_metrics and self.test_metrics.roc_auc else None],
                'training_time': [self.training_time_seconds],
                'n_samples_train': [self.n_samples_train],
                'n_samples_val': [self.n_samples_val],
                'n_samples_test': [self.n_samples_test],
                'n_features': [self.n_features],
                'created_at': [self.created_at],
            }

            return pd.DataFrame(data)
        except ImportError:
            raise ImportError('pandas required for to_dataframe()')

    def get_best_features(self, n: int = 20) -> list[FeatureImportance]:
        """Get top N features by importance."""
        if not self.feature_importance:
            return []

        sorted_features = sorted(
            self.feature_importance,
            key=lambda x: x.importance_score,
            reverse=True,
        )
        return sorted_features[:n]

    def get_feature_importance_dict(self) -> dict[str, float]:
        """Get feature importance as dictionary."""
        return {f.feature_name: f.importance_score for f in self.feature_importance}

    def compare_to(self, other: 'TrainResult') -> dict[str, Any]:
        """Compare this result to another model."""
        comparison = {
            'model_a': self.model_name,
            'model_b': other.model_name,
            'model_a_id': self.model_id,
            'model_b_id': other.model_id,
        }

        # Compare validation metrics
        if self.val_metrics.roc_auc and other.val_metrics.roc_auc:
            comparison['val_auc_diff'] = (
                self.val_metrics.roc_auc.value - other.val_metrics.roc_auc.value
            )

        # Compare test metrics
        if self.test_metrics and other.test_metrics:
            if self.test_metrics.roc_auc and other.test_metrics.roc_auc:
                comparison['test_auc_diff'] = (
                    self.test_metrics.roc_auc.value - other.test_metrics.roc_auc.value
                )

        # Training time ratio
        comparison['training_time_ratio'] = (
            self.training_time_seconds / other.training_time_seconds
            if other.training_time_seconds > 0 else float('inf')
        )

        # Sample size comparison
        comparison['n_samples_diff'] = self.n_samples_train - other.n_samples_train

        return comparison

    def is_better_than(self, other: 'TrainResult', metric: str = 'val_auc') -> bool:
        """Check if this model is better than another."""
        self_metric = getattr(self.val_metrics, metric)
        other_metric = getattr(other.val_metrics, metric)

        if self_metric is None or other_metric is None:
            return False

        return self_metric.value > other_metric.value

    def plot_validation_curves(self):
        """Plot all validation curves."""
        if not self.validation_curves:
            print('No validation curves available')
            return None

        try:
            import matplotlib.pyplot as plt

            n_curves = len(self.validation_curves)
            fig, axes = plt.subplots(1, n_curves, figsize=(6*n_curves, 5))

            if n_curves == 1:
                axes = [axes]

            for ax, curve in zip(axes, self.validation_curves):
                curve_plot = curve.plot()
                # Copy to subplot
                for line in curve_plot.axes[0].lines:
                    ax.plot(line.get_xdata(), line.get_ydata(),
                           label=line.get_label(), linewidth=2)
                ax.set_xlabel('Iteration')
                ax.set_ylabel(curve.metric_name)
                ax.set_title(f'{curve.metric_name} - Best: {curve.best_val_value:.4f}')
                ax.legend()
                ax.grid(True, alpha=0.3)

            plt.tight_layout()
            return fig

        except ImportError:
            raise ImportError('matplotlib required for plot_validation_curves()')

    def plot_feature_importance(self, top_n: int = 30, figsize: tuple[int, int] = (10, 8)):
        """Plot feature importance."""
        if not self.feature_importance:
            print('No feature importance available')
            return None

        try:
            import matplotlib.pyplot as plt
            import numpy as np

            top_features = self.get_best_features(top_n)

            fig, ax = plt.subplots(figsize=figsize)

            names = [f.feature_name for f in reversed(top_features)]
            scores = [f.importance_score for f in reversed(top_features)]

            colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(names)))

            ax.barh(range(len(names)), scores, color=colors)
            ax.set_yticks(range(len(names)))
            ax.set_yticklabels(names)
            ax.set_xlabel('Importance Score')
            ax.set_title(f'Top {top_n} Feature Importance')
            ax.grid(True, alpha=0.3, axis='x')

            plt.tight_layout()
            return fig

        except ImportError:
            raise ImportError('matplotlib and numpy required for plot_feature_importance()')

    def generate_report(self, output_path: str | None = None) -> str:
        """Generate HTML/Markdown report."""
        lines = [
            f'# Training Report: {self.model_name}',
            '',
            f'**Model ID**: {self.model_id}',
            f'**Status**: {self.status}',
            f"**Created**: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f'**Training Time**: {self.training_time_seconds:.1f}s',
            '',
            '## Configuration',
            f"- Family: {self.config.family.value if hasattr(self.config, 'family') else 'unknown'}",
            f"- Target: {self.config.target.value if hasattr(self.config, 'target') else 'unknown'}",
            f"- Features: {self.config.features.value if hasattr(self.config, 'features') else 'unknown'}",
            f'- N Features: {self.n_features}',
            '',
            '## Metrics',
            '',
            '### Training',
        ]

        for metric_name, metric in self.train_metrics.__dict__.items():
            if isinstance(metric, MetricValue):
                lines.append(f'- {metric_name}: {metric}')

        lines.extend(['', '### Validation'])
        for metric_name, metric in self.val_metrics.__dict__.items():
            if isinstance(metric, MetricValue):
                lines.append(f'- {metric_name}: {metric}')

        if self.test_metrics:
            lines.extend(['', '### Test'])
            for metric_name, metric in self.test_metrics.__dict__.items():
                if isinstance(metric, MetricValue):
                    lines.append(f'- {metric_name}: {metric}')

        lines.extend([
            '',
            '## Feature Importance (Top 10)',
            '',
        ])

        for feat in self.get_best_features(10):
            lines.append(f'{feat.importance_rank}. {feat.feature_name}: {feat.importance_score:.4f}')

        report = '\n'.join(lines)

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(report)

        return report

    def summary(self) -> str:
        """Get one-line summary."""
        val_auc = 'N/A'
        if self.val_metrics.roc_auc:
            val_auc = f'{self.val_metrics.roc_auc.value:.4f}'

        return (
            f'Model {self.model_id} ({self.model_name}): '
            f'Val AUC={val_auc}, '
            f'Time={self.training_time_seconds:.1f}s, '
            f'N={self.n_samples_train}'
        )

    def __repr__(self):
        return self.summary()


__all__ = [
    'FeatureImportance',
    'MetricValue',
    'Metrics',
    'PredictResult',
    'PredictionRecord',
    'Residuals',
    'TrainResult',
    'ValidationCurve',
]
