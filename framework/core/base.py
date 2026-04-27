"""Base classes for the framework.

All components must extend these base classes to ensure compatibility
with the framework's logging, registry, and experiment systems.

Example:
    class MyModel(BaseModel):
        def __init__(self, config):
            super().__init__(config)
            self.model = xgb.XGBClassifier()

        def train(self, X, y):
            self.model.fit(X, y)
            self.log_metric('train_auc', roc_auc_score(y, self.model.predict_proba(X)[:,1]))

        def predict(self, X):
            return self.model.predict_proba(X)[:,1]
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from framework.utils.logger import get_logger, log_to_db


class BaseComponent(ABC):
    """Base class for all framework components."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.logger = get_logger(self.__class__.__name__)
        self.component_type = self.__class__.__name__
        self._created_at = datetime.now()
        self._experiment_id = None

    def log_message(self, level: str, message: str, details: dict | None = None):
        """Log a message to both console and database."""
        self.logger.log(getattr(__import__('logging'), level.upper()), message)
        log_to_db(
            level=level,
            component=self.component_type,
            operation=self._get_current_operation(),
            message=message,
            details=details,
            experiment_id=self._experiment_id,
        )

    def log_metric(self, name: str, value: float, step: int | None = None):
        """Log a metric to the database."""
        details = {'metric_name': name, 'value': value}
        if step is not None:
            details['step'] = step
        self.log_message('INFO', f'Metric: {name}={value}', details)

    def set_experiment_id(self, exp_id: int):
        """Associate this component with an experiment for logging."""
        self._experiment_id = exp_id

    def _get_current_operation(self) -> str:
        """Override in subclasses to track current operation."""
        return 'general'

    def get_metadata(self) -> dict:
        """Return metadata about this component."""
        return {
            'class': self.__class__.__name__,
            'module': self.__class__.__module__,
            'created_at': self._created_at.isoformat(),
            'config': self.config,
        }


class BaseModel(BaseComponent):
    """Base class for all prediction models.

    Supports sklearn-like interface with fit/predict, but also provides
    framework integration for logging, versioning, and experiment tracking.

    Args:
        config: Model hyperparameters and settings

    Example:
        class XGBoostPitchModel(BaseModel):
            def __init__(self, config):
                super().__init__(config)
                self.model = xgb.XGBClassifier(**config.get('xgb_params', {}))

            def train(self, X, y):
                self.model.fit(X, y)
                self.log_metric('train_accuracy', self.model.score(X, y))

            def predict(self, X):
                return self.model.predict_proba(X)[:, 1]

            def get_feature_importance(self):
                return dict(zip(self.feature_names, self.model.feature_importances_))
    """

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.model = None
        self.feature_names = []
        self.target_name = None
        self.is_trained = False

    @abstractmethod
    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Train the model on data.

        Args:
            X: Feature DataFrame
            y: Target series
        """

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate predictions.

        Args:
            X: Feature DataFrame

        Returns:
            Array of predictions (probabilities for classification)
        """

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> dict[str, float]:
        """Evaluate model performance. Override for custom metrics.

        Returns:
            Dictionary of metric_name -> value
        """
        from sklearn.metrics import accuracy_score, log_loss, roc_auc_score

        preds = self.predict(X)
        metrics = {
            'accuracy': accuracy_score(y, preds > 0.5),
            'roc_auc': roc_auc_score(y, preds),
            'log_loss': log_loss(y, preds),
        }

        for name, value in metrics.items():
            self.log_metric(name, value)

        return metrics

    def save(self, path: str) -> None:
        """Save model to disk. Override for custom serialization."""
        import pickle

        with open(path, 'wb') as f:
            pickle.dump(
                {
                    'model': self.model,
                    'config': self.config,
                    'feature_names': self.feature_names,
                    'is_trained': self.is_trained,
                },
                f,
            )
        self.log_message('INFO', f'Model saved to {path}')

    def load(self, path: str) -> None:
        """Load model from disk. Override for custom deserialization."""
        import pickle

        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.config = data['config']
            self.feature_names = data['feature_names']
            self.is_trained = data['is_trained']
        self.log_message('INFO', f'Model loaded from {path}')

    def _get_current_operation(self) -> str:
        return 'train' if not self.is_trained else 'predict'


class BaseFeature(BaseComponent):
    """Base class for feature transformers/engineering.

    Can be SQL-based (computed in database) or Python-based (computed in Python).
    The framework tracks dependencies and computes features in correct order.

    Args:
        config: Feature configuration including dependencies

    Example:
        class RollingAverageFeature(BaseFeature):
            def __init__(self, config):
                super().__init__(config)
                self.window = config.get('window', 5)
                self.column = config.get('column', 'batting_avg')

            def transform(self, df: pd.DataFrame) -> pd.DataFrame:
                df[f'{self.column}_rolling_{self.window}'] = df[self.column].rolling(self.window).mean()
                return df

            @property
            def sql_expression(self) -> Optional[str]:
                # Return SQL for database computation
                return f"AVG({self.column}) OVER (ORDER BY game_date ROWS {self.window} PRECEDING)"
    """

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.feature_name = config.get('name', self.__class__.__name__)
        self.dependencies = config.get('dependencies', [])
        self.output_column = config.get('output_column', self.feature_name)

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform DataFrame by adding feature column(s).

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with new feature column(s)
        """

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit (if needed) then transform. Default just transforms."""
        return self.transform(df)

    @property
    def sql_expression(self) -> str | None:
        """Return SQL expression for database computation.

        If implemented, the framework can compute this feature in SQL
        for better performance. Return None to use Python transform.
        """
        return None

    def get_metadata(self) -> dict:
        """Get feature metadata including dependencies."""
        meta = super().get_metadata()
        meta.update(
            {
                'feature_name': self.feature_name,
                'dependencies': self.dependencies,
                'output_column': self.output_column,
                'has_sql_implementation': self.sql_expression is not None,
            }
        )
        return meta

    def _get_current_operation(self) -> str:
        return 'transform'


class BaseDataLoader(BaseComponent):
    """Base class for data loading.

    Provides consistent interface for loading data from various sources:
    database, files, APIs, etc. Supports batching and filtering.

    Args:
        config: Data source configuration

    Example:
        class StatcastLoader(BaseDataLoader):
            def load(self, game_ids: List[str]) -> pd.DataFrame:
                query = "SELECT * FROM features_pitch.locations WHERE game_pk = ANY(%s)"
                return self.execute_query(query, (game_ids,))

            def get_schema(self) -> Dict:
                return {'game_pk': 'int', 'pitch_type': 'text', ...}
    """

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.source = config.get('source', 'database')
        self.batch_size = config.get('batch_size', 10000)

    @abstractmethod
    def load(self, **kwargs) -> pd.DataFrame:
        """Load data from source.

        Returns:
            DataFrame with data
        """

    def load_batch(self, offset: int, limit: int, **kwargs) -> pd.DataFrame:
        """Load a batch of data. Override for efficient batching.

        Args:
            offset: Start row
            limit: Number of rows

        Returns:
            DataFrame batch
        """
        df = self.load(**kwargs)
        return df.iloc[offset : offset + limit]

    def get_total_count(self, **kwargs) -> int:
        """Get total number of rows available. Override for progress tracking."""
        return -1  # Unknown

    def get_schema(self) -> dict[str, str]:
        """Return schema of data.

        Returns:
            Dictionary mapping column names to data types
        """
        return {}

    def _get_current_operation(self) -> str:
        return 'load'


class BaseTransformer(BaseComponent):
    """Base class for data transformers (preprocessing, normalization, etc.).

    Similar to sklearn transformers with fit/transform pattern, but with
    framework logging integration.

    Example:
        class OutlierClipper(BaseTransformer):
            def __init__(self, config):
                super().__init__(config)
                self.lower = config.get('lower', 0.01)
                self.upper = config.get('upper', 0.99)

            def fit(self, df: pd.DataFrame) -> 'OutlierClipper':
                self.bounds_ = {
                    col: (df[col].quantile(self.lower), df[col].quantile(self.upper))
                    for col in df.select_dtypes(include=[np.number]).columns
                }
                return self

            def transform(self, df: pd.DataFrame) -> pd.DataFrame:
                result = df.copy()
                for col, (low, high) in self.bounds_.items():
                    result[col] = df[col].clip(low, high)
                return result
    """

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.is_fitted = False

    def fit(self, df: pd.DataFrame) -> 'BaseTransformer':
        """Fit transformer to data. Override if needed."""
        self.is_fitted = True
        return self

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform data."""

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit then transform."""
        return self.fit(df).transform(df)

    def _get_current_operation(self) -> str:
        return 'transform'


class BaseMetric(BaseComponent):
    """Base class for custom evaluation metrics.

    Allows researchers to define their own metrics beyond standard sklearn.

    Example:
        class CalibrationError(BaseMetric):
            def compute(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
                # Compute expected calibration error
                bins = np.linspace(0, 1, 11)
                bin_indices = np.digitize(y_pred, bins)
                calibration_errors = []
                for i in range(1, len(bins)):
                    mask = bin_indices == i
                    if mask.sum() > 0:
                        avg_confidence = y_pred[mask].mean()
                        avg_accuracy = y_true[mask].mean()
                        calibration_errors.append(abs(avg_confidence - avg_accuracy))
                return np.mean(calibration_errors)
    """

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.metric_name = config.get('name', self.__class__.__name__)

    @abstractmethod
    def compute(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Compute the metric.

        Args:
            y_true: Ground truth labels
            y_pred: Predicted probabilities or labels

        Returns:
            Metric value
        """

    def compute_batch(
        self, y_true: np.ndarray, y_pred: np.ndarray, batch_size: int = 10000
    ) -> float:
        """Compute metric in batches for large datasets."""
        if len(y_true) <= batch_size:
            return self.compute(y_true, y_pred)

        # Sample-based estimate for large datasets
        indices = np.random.choice(len(y_true), batch_size, replace=False)
        return self.compute(y_true[indices], y_pred[indices])

    def _get_current_operation(self) -> str:
        return 'evaluate'


class BaseExperiment(ABC):
    """Base class for experiment orchestration.

    Use this to define complex multi-step experiments that go beyond
    the simple train/evaluate flow.

    Example:
        class HyperparameterSearch(BaseExperiment):
            def run(self):
                results = []
                for lr in [0.01, 0.1, 0.5]:
                    for depth in [3, 5, 7]:
                        model = XGBoostModel({'learning_rate': lr, 'max_depth': depth})
                        model.train(self.train_data)
                        score = model.evaluate(self.val_data)
                        results.append({'lr': lr, 'depth': depth, 'score': score})
                return self.find_best(results)
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.logger = get_logger(self.__class__.__name__)
        self._experiment_id = None

    @abstractmethod
    def run(self) -> Any:
        """Execute the experiment."""

    def set_experiment_id(self, exp_id: int):
        """Set experiment ID for logging."""
        self._experiment_id = exp_id
