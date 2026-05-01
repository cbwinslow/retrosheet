"""Model Training Pipeline for the baseball prediction warehouse.

Provides standardized training workflows with:
- Cross-validation
- Hyperparameter tracking
- Model persistence
- Registry integration

Author: Agent Cascade
Date: 2026-04-28
"""

import pickle
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import accuracy_score, log_loss, mean_squared_error
from sklearn.model_selection import cross_val_score, train_test_split

from baseball.core.db import get_db_connection
from baseball.models.base import BaseModel, ModelConfig
from baseball.models.registry import ModelRegistry


@dataclass
class TrainingResult:
    """Result of a model training run."""
    success: bool
    model: Any | None = None
    model_id: int | None = None
    metrics: dict[str, float] = None
    cv_scores: list[float] = None
    feature_importance: dict[str, float] = None
    training_time_seconds: float = 0.0
    error_message: str = ''

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
        if self.cv_scores is None:
            self.cv_scores = []
        if self.feature_importance is None:
            self.feature_importance = {}


class TrainingPipeline:
    """Standardized training pipeline for baseball prediction models.

    Handles:
    - Data loading from database
    - Train/validation split
    - Cross-validation
    - Model training
    - Evaluation metrics
    - Model persistence and registry storage

    Usage:
        from baseball.models.win_probability_model import WinProbabilityModel

        pipeline = TrainingPipeline(
            model_class=WinProbabilityModel,
            model_name="win_probability",
            version="1.0.0"
        )

        result = pipeline.train(
            seasons=[2022, 2023, 2024],
            test_size=0.2,
            cv_folds=5
        )
    """

    def __init__(
        self,
        model_class: type,
        model_name: str,
        version: str = '1.0.0',
        artifacts_dir: str = 'models/artifacts',
    ) -> None:
        self.model_class = model_class
        self.model_name = model_name
        self.version = version
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.registry = ModelRegistry(artifacts_dir)

    def train(
        self,
        seasons: list[int],
        test_size: float = 0.2,
        cv_folds: int = 5,
        hyperparameters: dict[str, Any] | None = None,
        feature_set: list[str] | None = None,
        promote_to_production: bool = False,
        training_dataset: str = '',
    ) -> TrainingResult:
        """Execute full training pipeline.

        Args:
            seasons: List of seasons to train on
            test_size: Fraction of data for validation
            cv_folds: Number of cross-validation folds
            hyperparameters: Model hyperparameters
            feature_set: List of feature names
            promote_to_production: Auto-promote if validation passes
            training_dataset: Dataset identifier

        Returns:
            TrainingResult with model, metrics, and registry ID
        """
        start_time = time.time()

        try:
            # 1. Load training data
            print(f'Loading training data for seasons: {seasons}')
            X, y, features = self._load_training_data(seasons)

            if len(X) == 0:
                return TrainingResult(
                    success=False,
                    error_message='No training data found',
                )

            # Use provided feature_set or detected features
            feature_names = feature_set if feature_set else features

            # 2. Train/validation split
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y,
            )

            print(f'Training set: {len(X_train)}, Validation set: {len(X_val)}')

            # 3. Create and train model
            config = ModelConfig(
                model_name=self.model_name,
                version=self.version,
                hyperparameters=hyperparameters or {},
            )

            model = self.model_class(config)

            # 4. Cross-validation
            print(f'Running {cv_folds}-fold cross-validation...')
            cv_scores = cross_val_score(
                model.model, X_train, y_train,
                cv=cv_folds,
                scoring='neg_log_loss',
            )
            cv_scores = [-s for s in cv_scores]  # Convert back to positive log_loss

            # 5. Train on full training set
            print('Training final model...')
            model.fit(X_train, y_train)

            # 6. Validation evaluation
            y_pred_proba = model.predict_proba(X_val)
            y_pred = model.predict(X_val)

            # Calculate metrics
            metrics = self._calculate_metrics(y_val, y_pred, y_pred_proba, model.model_type)

            # 7. Feature importance
            feature_importance = self._get_feature_importance(model, feature_names)

            # 8. Save artifact
            artifact_path = self._save_artifact(model)

            # 9. Register model
            print('Registering model...')
            entry = self.registry.register_model(
                model_name=self.model_name,
                model_version=self.version,
                model_type=model.model_type,
                artifact_path=str(artifact_path),
                primary_metric='log_loss',
                primary_metric_value=metrics.get('log_loss', 0.0),
                hyperparameters=hyperparameters,
                feature_set=feature_names,
                validation_metrics=metrics,
                cv_folds=cv_folds,
                cv_mean=float(np.mean(cv_scores)),
                cv_std=float(np.std(cv_scores)),
                framework=model.framework,
                framework_version=model.framework_version,
                training_dataset=training_dataset or f"seasons_{'_'.join(map(str, seasons))}",
                training_start_date=f'{min(seasons)}-01-01',
                training_end_date=f'{max(seasons)}-12-31',
            )

            # 10. Optionally promote to production
            if promote_to_production and entry.model_id:
                if self._should_promote(metrics, cv_scores):
                    print('Promoting to production...')
                    self.registry.promote_model(entry.model_id)
                    entry = self.registry.get_model_by_id(entry.model_id)

            training_time = time.time() - start_time

            return TrainingResult(
                success=True,
                model=model,
                model_id=entry.model_id,
                metrics=metrics,
                cv_scores=cv_scores.tolist(),
                feature_importance=feature_importance,
                training_time_seconds=training_time,
            )

        except Exception as e:
            training_time = time.time() - start_time
            return TrainingResult(
                success=False,
                error_message=str(e),
                training_time_seconds=training_time,
            )

    def _load_training_data(
        self,
        seasons: list[int],
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """Load training data from database.

        Override this method in subclasses for specific model data needs.
        Default implementation loads from features.win_probability_inputs.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Default: load win probability training data
                cur.execute(
                    """
                    SELECT
                        inning_norm, outs_norm, score_diff_norm,
                        runner_1b, runner_2b, runner_3b,
                        batting_team_home, is_final_inning,
                        home_won
                    FROM features.win_probability_inputs
                    WHERE season = ANY(%s) AND home_won IS NOT NULL
                    """,
                    (seasons,),
                )

                rows = cur.fetchall()
                if not rows:
                    return np.array([]), np.array([]), []

                # Separate features and target
                feature_cols = [
                    'inning_norm', 'outs_norm', 'score_diff_norm',
                    'runner_1b', 'runner_2b', 'runner_3b',
                    'batting_team_home', 'is_final_inning',
                ]

                X = np.array([row[:-1] for row in rows])
                y = np.array([row[-1] for row in rows])

                return X, y, feature_cols
        finally:
            conn.close()

    def _calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_pred_proba: np.ndarray,
        model_type: str,
    ) -> dict[str, float]:
        """Calculate evaluation metrics."""
        metrics = {}

        if model_type == 'classification':
            metrics['log_loss'] = log_loss(y_true, y_pred_proba)
            metrics['accuracy'] = accuracy_score(y_true, y_pred)
        else:  # regression
            metrics['rmse'] = np.sqrt(mean_squared_error(y_true, y_pred))
            metrics['mae'] = mean_squared_error(y_true, y_pred, squared=False)

        return metrics

    def _get_feature_importance(
        self,
        model: BaseModel,
        feature_names: list[str],
    ) -> dict[str, float]:
        """Extract feature importance from model."""
        importance = {}

        try:
            if hasattr(model.model, 'feature_importances_'):
                # Tree-based models
                for name, imp in zip(feature_names, model.model.feature_importances_, strict=False):
                    importance[name] = float(imp)
            elif hasattr(model.model, 'coef_'):
                # Linear models
                coefs = model.model.coef_
                if len(coefs.shape) > 1:
                    coefs = coefs[0]  # Binary classification
                for name, coef in zip(feature_names, coefs, strict=False):
                    importance[name] = float(abs(coef))
        except:
            pass

        return importance

    def _save_artifact(self, model: BaseModel) -> Path:
        """Save model to disk."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{self.model_name}_{self.version}_{timestamp}.pkl'
        artifact_path = self.artifacts_dir / filename

        with open(artifact_path, 'wb') as f:
            pickle.dump(model, f)

        return artifact_path

    def _should_promote(
        self,
        metrics: dict[str, float],
        cv_scores: list[float],
    ) -> bool:
        """Determine if model should be auto-promoted to production.

        Override for custom promotion logic.
        """
        # Default: promote if log_loss < 0.5 and CV std < 0.05
        log_loss_val = metrics.get('log_loss', 1.0)
        cv_std = np.std(cv_scores) if cv_scores else 1.0

        return log_loss_val < 0.5 and cv_std < 0.05


class WinProbabilityTrainingPipeline(TrainingPipeline):
    """Specialized training pipeline for win probability models."""

    def __init__(self, version: str = '1.0.0') -> None:
        from baseball.models.win_probability_model import WinProbabilityModel
        super().__init__(
            model_class=WinProbabilityModel,
            model_name='win_probability',
            version=version,
        )

    def _load_training_data(
        self,
        seasons: list[int],
    ) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """Load win probability training data with all relevant features."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        inning_norm,
                        outs_norm,
                        score_diff_norm,
                        runner_1b::int,
                        runner_2b::int,
                        runner_3b::int,
                        batting_team_home::int,
                        is_final_inning::int,
                        home_won::int
                    FROM features.win_probability_inputs
                    WHERE season = ANY(%s)
                      AND home_won IS NOT NULL
                      AND inning <= 9
                    """,
                    (seasons,),
                )

                rows = cur.fetchall()
                if not rows:
                    return np.array([]), np.array([]), []

                feature_cols = [
                    'inning_norm', 'outs_norm', 'score_diff_norm',
                    'runner_1b', 'runner_2b', 'runner_3b',
                    'batting_team_home', 'is_final_inning',
                ]

                X = np.array([row[:-1] for row in rows])
                y = np.array([row[-1] for row in rows])

                print(f'Loaded {len(rows)} training examples')
                print(f'Home win rate: {y.mean():.3f}')

                return X, y, feature_cols
        finally:
            conn.close()


def train_win_probability_model(
    seasons: list[int] | None = None,
    version: str = '1.0.0',
    promote: bool = False,
) -> TrainingResult:
    """Convenience function to train a win probability model.

    Args:
        seasons: List of seasons to train on (default: [2022, 2023, 2024])
        version: Model version string
        promote: Auto-promote to production if validation passes

    Returns:
        TrainingResult
    """
    if seasons is None:
        seasons = [2022, 2023, 2024]

    pipeline = WinProbabilityTrainingPipeline(version=version)
    return pipeline.train(
        seasons=seasons,
        promote_to_production=promote,
    )
