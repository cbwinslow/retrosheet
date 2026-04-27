"""Experiment Runner - Multi-model comparison and hyperparameter sweeps.

Phase 2.4: Experiment Runner

Runs multiple model configurations, compares results, and generates
comparison reports. Supports hyperparameter sweeps and A/B testing.

Author: Agent Cascade
Date: April 24, 2026
"""

import itertools
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from mlb_predict.config import ExperimentConfig, ModelConfig
from mlb_predict.core.results import Metrics, TrainResult
from mlb_predict.core.trainer import ModelTrainer


@dataclass
class ExperimentRun:
    """Single run within an experiment."""

    run_id: str
    config: ModelConfig
    result: TrainResult | None = None
    status: str = 'pending'  # pending, running, completed, failed
    error_message: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def duration_seconds(self) -> float:
        """Get run duration."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


@dataclass
class ExperimentSummary:
    """Summary of experiment results."""

    experiment_id: str
    experiment_name: str
    n_runs: int
    n_completed: int
    n_failed: int
    best_run_id: str | None = None
    best_metric_value: float | None = None
    metric_name: str = 'val_roc_auc'
    runs: list[ExperimentRun] = field(default_factory=list)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame for analysis."""
        data = []
        for run in self.runs:
            row = {
                'run_id': run.run_id,
                'status': run.status,
                'duration_seconds': run.duration_seconds,
            }

            # Add config info
            row['family'] = run.config.family
            row['target'] = run.config.target
            row['features'] = run.config.features

            # Add metrics if completed
            if run.result and run.result.val_metrics:
                metrics = run.result.val_metrics
                if metrics.roc_auc:
                    row['val_roc_auc'] = metrics.roc_auc.value
                if metrics.accuracy:
                    row['val_accuracy'] = metrics.accuracy.value
                if metrics.log_loss:
                    row['val_log_loss'] = metrics.log_loss.value

                row['training_time'] = run.result.training_time_seconds
                row['n_samples_train'] = run.result.n_samples_train

            data.append(row)

        return pd.DataFrame(data)


class ExperimentRunner:
    """Run and compare multiple model configurations.

    Supports:
    - Multi-model comparison (XGBoost vs LightGBM vs CatBoost)
    - Hyperparameter sweeps
    - Feature set comparison (basic vs advanced vs complete)
    - A/B testing different approaches

    Example:
        # Compare model families
        configs = [
            ModelConfig(family='xgboost', target='swing_decision'),
            ModelConfig(family='lightgbm', target='swing_decision'),
            ModelConfig(family='catboost', target='swing_decision'),
        ]

        runner = ExperimentRunner(
            experiment_name="model_family_comparison",
            configs=configs
        )

        summary = runner.run_all()

        # Get best model
        best_run = summary.runs[0]  # Already sorted by metric
        print(f"Best: {best_run.config.family} with AUC={best_run.result.val_metrics.roc_auc}")

        # Generate comparison report
        runner.generate_report("experiments/model_comparison.html")
    """

    def __init__(
        self,
        experiment_name: str,
        configs: list[ModelConfig],
        experiment_id: str | None = None,
        metric_name: str = 'val_roc_auc',
        higher_is_better: bool = True,
        output_dir: str | None = None,
    ):
        """Initialize experiment runner.

        Args:
            experiment_name: Name of the experiment
            configs: List of ModelConfig to compare
            experiment_id: Optional unique ID (generated if not provided)
            metric_name: Metric to optimize (val_roc_auc, val_accuracy, etc.)
            higher_is_better: Whether higher metric is better
            output_dir: Directory to save results
        """
        self.experiment_name = experiment_name
        self.experiment_id = experiment_id or self._generate_id()
        self.configs = configs
        self.metric_name = metric_name
        self.higher_is_better = higher_is_better
        self.output_dir = Path(output_dir) if output_dir else Path('experiments')

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize runs
        self.runs: list[ExperimentRun] = [
            ExperimentRun(
                run_id=f'run_{i:03d}',
                config=config,
            )
            for i, config in enumerate(configs)
        ]

        self._summary: ExperimentSummary | None = None

    @staticmethod
    def _generate_id() -> str:
        """Generate unique experiment ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f'exp_{timestamp}'

    def run_all(
        self,
        parallel: bool = False,
        max_workers: int = 4,
        continue_on_error: bool = True,
    ) -> ExperimentSummary:
        """Run all configurations in the experiment.

        Args:
            parallel: Whether to run in parallel (not implemented yet)
            max_workers: Max parallel workers if parallel=True
            continue_on_error: Whether to continue if one run fails

        Returns:
            ExperimentSummary with all results
        """
        print(f'[INFO] Starting experiment: {self.experiment_name}')
        print(f'[INFO] Runs: {len(self.runs)}')

        for i, run in enumerate(self.runs):
            print(f'\n[INFO] Run {i + 1}/{len(self.runs)}: {run.run_id}')

            try:
                self._execute_run(run)
            except Exception as e:
                run.status = 'failed'
                run.error_message = str(e)
                print(f'[ERROR] Run {run.run_id} failed: {e}')

                if not continue_on_error:
                    break

        # Generate summary
        self._summary = self._create_summary()

        # Save results
        self._save_results()

        return self._summary

    def _execute_run(self, run: ExperimentRun) -> None:
        """Execute a single run."""
        run.start_time = datetime.now()
        run.status = 'running'

        # Create trainer and run
        trainer = ModelTrainer(run.config)
        result = trainer.train()

        run.result = result
        run.status = 'completed'
        run.end_time = datetime.now()

        print(f'[INFO] Run {run.run_id} completed: {result.summary()}')

    def _create_summary(self) -> ExperimentSummary:
        """Create experiment summary from runs."""
        completed_runs = [r for r in self.runs if r.status == 'completed']
        failed_runs = [r for r in self.runs if r.status == 'failed']

        # Find best run
        best_run = None
        best_value = float('-inf') if self.higher_is_better else float('inf')

        for run in completed_runs:
            if run.result and run.result.val_metrics:
                metric_value = self._get_metric_value(run.result.val_metrics)

                if metric_value is not None:
                    if (self.higher_is_better and metric_value > best_value) or (
                        not self.higher_is_better and metric_value < best_value
                    ):
                        best_value = metric_value
                        best_run = run

        return ExperimentSummary(
            experiment_id=self.experiment_id,
            experiment_name=self.experiment_name,
            n_runs=len(self.runs),
            n_completed=len(completed_runs),
            n_failed=len(failed_runs),
            best_run_id=best_run.run_id if best_run else None,
            best_metric_value=best_value if best_run else None,
            metric_name=self.metric_name,
            runs=self.runs,
        )

    def _get_metric_value(self, metrics: Metrics) -> float | None:
        """Extract metric value from Metrics object."""
        if self.metric_name == 'val_roc_auc' and metrics.roc_auc:
            return metrics.roc_auc.value
        if self.metric_name == 'val_accuracy' and metrics.accuracy:
            return metrics.accuracy.value
        if self.metric_name == 'val_log_loss' and metrics.log_loss:
            return metrics.log_loss.value
        return None

    def _save_results(self) -> None:
        """Save experiment results to disk."""
        exp_dir = self.output_dir / self.experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        # Save summary as JSON
        summary_dict = {
            'experiment_id': self._summary.experiment_id,
            'experiment_name': self._summary.experiment_name,
            'n_runs': self._summary.n_runs,
            'n_completed': self._summary.n_completed,
            'n_failed': self._summary.n_failed,
            'best_run_id': self._summary.best_run_id,
            'best_metric_value': self._summary.best_metric_value,
            'metric_name': self._summary.metric_name,
            'runs': [
                {
                    'run_id': run.run_id,
                    'config': {
                        'family': run.config.family,
                        'target': run.config.target,
                        'features': run.config.features,
                    },
                    'status': run.status,
                    'duration_seconds': run.duration_seconds,
                    'result': {
                        'model_id': run.result.model_id if run.result else None,
                        'model_name': run.result.model_name if run.result else None,
                        'val_roc_auc': run.result.val_metrics.roc_auc.value
                        if run.result and run.result.val_metrics and run.result.val_metrics.roc_auc
                        else None,
                    }
                    if run.result
                    else None,
                    'error_message': run.error_message,
                }
                for run in self.runs
            ],
        }

        with open(exp_dir / 'summary.json', 'w') as f:
            json.dump(summary_dict, f, indent=2, default=str)

        # Save as CSV
        df = self._summary.to_dataframe()
        df.to_csv(exp_dir / 'results.csv', index=False)

        print(f'[INFO] Results saved to {exp_dir}')

    def get_best_run(self) -> ExperimentRun | None:
        """Get the best run from the experiment."""
        if self._summary and self._summary.best_run_id:
            for run in self.runs:
                if run.run_id == self._summary.best_run_id:
                    return run
        return None

    def compare_runs(self, run_ids: list[str] | None = None) -> pd.DataFrame:
        """Compare specific runs or all runs.

        Args:
            run_ids: List of run IDs to compare (default: all completed)

        Returns:
            DataFrame with comparison
        """
        if run_ids:
            runs = [r for r in self.runs if r.run_id in run_ids]
        else:
            runs = [r for r in self.runs if r.status == 'completed']

        data = []
        for run in runs:
            if run.result:
                row = {
                    'run_id': run.run_id,
                    'family': run.config.family,
                    'target': run.config.target,
                    'features': run.config.features,
                    'training_time': run.result.training_time_seconds,
                    'n_samples': run.result.n_samples_train,
                }

                # Add all metrics
                if run.result.val_metrics:
                    if run.result.val_metrics.roc_auc:
                        row['val_auc'] = run.result.val_metrics.roc_auc.value
                    if run.result.val_metrics.accuracy:
                        row['val_accuracy'] = run.result.val_metrics.accuracy.value
                    if run.result.val_metrics.log_loss:
                        row['val_log_loss'] = run.result.val_metrics.log_loss.value

                if run.result.train_metrics:
                    if run.result.train_metrics.roc_auc:
                        row['train_auc'] = run.result.train_metrics.roc_auc.value

                data.append(row)

        return pd.DataFrame(data)

    def generate_report(self, output_path: str | None = None) -> str:
        """Generate HTML report of experiment results.

        Args:
            output_path: Path for HTML file (default: auto-generated)

        Returns:
            Path to generated report
        """
        if output_path is None:
            output_path = self.output_dir / self.experiment_id / 'report.html'
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build HTML
        df = self._summary.to_dataframe() if self._summary else pd.DataFrame()

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Experiment Report: {self.experiment_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .metric {{ font-weight: bold; color: #4CAF50; }}
        .error {{ color: #f44336; }}
        .summary {{ background-color: #e7f3fe; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>Experiment Report: {self.experiment_name}</h1>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Experiment ID:</strong> {self.experiment_id}</p>
        <p><strong>Total Runs:</strong> {len(self.runs)}</p>
        <p><strong>Completed:</strong> {len([r for r in self.runs if r.status == 'completed'])}</p>
        <p><strong>Failed:</strong> {len([r for r in self.runs if r.status == 'failed'])}</p>
        {f'<p><strong>Best Run:</strong> {self._summary.best_run_id} ({self.metric_name}={self._summary.best_metric_value:.4f})</p>' if self._summary and self._summary.best_run_id else ''}
    </div>
    
    <h2>Results</h2>
    {df.to_html(index=False, classes='results') if not df.empty else '<p>No results yet</p>'}
    
</body>
</html>
"""

        with open(output_path, 'w') as f:
            f.write(html)

        print(f'[INFO] Report saved to {output_path}')
        return str(output_path)

    @classmethod
    def from_config(cls, config: ExperimentConfig) -> 'ExperimentRunner':
        """Create runner from ExperimentConfig.

        Args:
            config: ExperimentConfig with models to compare

        Returns:
            ExperimentRunner instance
        """
        return cls(
            experiment_name=config.name,
            configs=config.models,
            experiment_id=config.experiment_id,
            metric_name=config.comparison_metric,
            output_dir=config.output_dir,
        )


class HyperparameterSweep:
    """Hyperparameter sweep for a single model.

    Example:
        sweep = HyperparameterSweep(
            base_config=ModelConfig(family='xgboost', target='swing_decision'),
            param_grid={
                'xgboost__max_depth': [3, 5, 7, 10],
                'xgboost__learning_rate': [0.01, 0.1, 0.3],
            }
        )

        runner = sweep.create_runner(experiment_name="xgb_depth_lr_sweep")
        summary = runner.run_all()
    """

    def __init__(
        self,
        base_config: ModelConfig,
        param_grid: dict[str, list[Any]],
    ):
        """Initialize hyperparameter sweep.

        Args:
            base_config: Base ModelConfig to modify
            param_grid: Dict mapping param paths to lists of values
                       (e.g., {'xgboost__max_depth': [3, 5, 7]})
        """
        self.base_config = base_config
        self.param_grid = param_grid

    def generate_configs(self) -> list[ModelConfig]:
        """Generate all config combinations."""
        # Get param names and values
        param_names = list(self.param_grid.keys())
        param_values = [self.param_grid[name] for name in param_names]

        configs = []

        # Generate all combinations
        for combo in itertools.product(*param_values):
            # Copy base config
            config_dict = self.base_config.model_dump()

            # Update with param values
            for param_name, value in zip(param_names, combo):
                # Handle nested params like 'xgboost__max_depth'
                if '__' in param_name:
                    section, param = param_name.split('__', 1)
                    if section in config_dict and isinstance(config_dict[section], dict):
                        config_dict[section][param] = value
                else:
                    config_dict[param_name] = value

            # Create new config
            from mlb_predict.config import ModelConfig

            config = ModelConfig(**config_dict)
            configs.append(config)

        return configs

    def create_runner(
        self,
        experiment_name: str,
        metric_name: str = 'val_roc_auc',
    ) -> ExperimentRunner:
        """Create ExperimentRunner for this sweep.

        Args:
            experiment_name: Name for the experiment
            metric_name: Metric to optimize

        Returns:
            Configured ExperimentRunner
        """
        configs = self.generate_configs()

        return ExperimentRunner(
            experiment_name=experiment_name,
            configs=configs,
            metric_name=metric_name,
        )


def compare_feature_sets(
    base_config: ModelConfig,
    feature_sets: list[str] = ['basic', 'physics', 'advanced', 'complete'],
) -> ExperimentRunner:
    """Compare different feature sets.

    Convenience function to quickly compare feature sets.

    Args:
        base_config: Base config (family, target, etc.)
        feature_sets: List of feature sets to compare

    Returns:
        Configured ExperimentRunner
    """
    configs = []
    for fs in feature_sets:
        config_dict = base_config.model_dump()
        config_dict['features'] = fs
        configs.append(ModelConfig(**config_dict))

    return ExperimentRunner(
        experiment_name=f'feature_set_comparison_{base_config.target}',
        configs=configs,
        metric_name='val_roc_auc',
    )


def compare_model_families(
    base_config: ModelConfig,
    families: list[str] = ['xgboost', 'lightgbm', 'catboost'],
) -> ExperimentRunner:
    """Compare different model families.

    Convenience function to quickly compare model families.

    Args:
        base_config: Base config (target, features, etc.)
        families: List of model families to compare

    Returns:
        Configured ExperimentRunner
    """
    configs = []
    for family in families:
        config_dict = base_config.model_dump()
        config_dict['family'] = family
        configs.append(ModelConfig(**config_dict))

    return ExperimentRunner(
        experiment_name=f'model_family_comparison_{base_config.target}',
        configs=configs,
        metric_name='val_roc_auc',
    )


__all__ = [
    'ExperimentRun',
    'ExperimentRunner',
    'ExperimentSummary',
    'HyperparameterSweep',
    'compare_feature_sets',
    'compare_model_families',
]
