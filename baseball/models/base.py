"""Base classes for baseball prediction models.

Provides abstract base class and shared infrastructure for:
- Model lifecycle management (train, evaluate, predict)
- Version tracking and registry
- Feature extraction
- Result storage

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Type of prediction model."""

    NEXT_RUN_PROBABILITY = 'next_run_probability'
    PA_OUTCOME = 'pa_outcome'
    WIN_PROBABILITY = 'win_probability'
    RUN_TOTAL = 'run_total'


class ModelStatus(Enum):
    """Status of model in lifecycle."""

    UNTRAINED = 'untrained'
    TRAINING = 'training'
    TRAINED = 'trained'
    VALIDATED = 'validated'
    PRODUCTION = 'production'
    DEPRECATED = 'deprecated'
    FAILED = 'failed'


@dataclass
class ModelConfig:
    """Configuration for model training and inference.

    Attributes:
        model_type: Type of model
        model_name: Human-readable name
        version: Version string (e.g., '1.0.0')
        random_seed: For reproducibility
        hyperparameters: Model-specific hyperparameters
        feature_columns: List of feature column names
        target_column: Name of target column
    """

    model_type: ModelType
    model_name: str
    version: str = '0.1.0'
    random_seed: int = 42
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    feature_columns: list[str] = field(default_factory=list)
    target_column: str = 'target'

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'model_type': self.model_type.value,
            'model_name': self.model_name,
            'version': self.version,
            'random_seed': self.random_seed,
            'hyperparameters': self.hyperparameters,
            'feature_columns': self.feature_columns,
            'target_column': self.target_column,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ModelConfig':
        """Create config from dictionary."""
        return cls(
            model_type=ModelType(data['model_type']),
            model_name=data['model_name'],
            version=data['version'],
            random_seed=data.get('random_seed', 42),
            hyperparameters=data.get('hyperparameters', {}),
            feature_columns=data.get('feature_columns', []),
            target_column=data.get('target_column', 'target'),
        )


@dataclass
class TrainingConfig:
    """Configuration for training runs.

    Attributes:
        train_seasons: List of seasons for training data
        test_seasons: List of seasons for test data
        validation_split: Fraction of training data for validation
        batch_size: Training batch size
        max_epochs: Maximum training epochs
        early_stopping_patience: Epochs without improvement before stopping
        learning_rate: Optimizer learning rate
        regularization: L1/L2 regularization strength
    """

    train_seasons: list[int] = field(default_factory=list)
    test_seasons: list[int] = field(default_factory=list)
    validation_split: float = 0.2
    batch_size: int = 1024
    max_epochs: int = 100
    early_stopping_patience: int = 10
    learning_rate: float = 0.001
    regularization: float = 0.0001

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'train_seasons': self.train_seasons,
            'test_seasons': self.test_seasons,
            'validation_split': self.validation_split,
            'batch_size': self.batch_size,
            'max_epochs': self.max_epochs,
            'early_stopping_patience': self.early_stopping_patience,
            'learning_rate': self.learning_rate,
            'regularization': self.regularization,
        }


@dataclass
class ModelVersion:
    """Model version record for registry.

    Attributes:
        version_id: Unique version ID
        model_type: Type of model
        version: Version string
        status: Current status
        training_config: Training configuration used
        metrics: Performance metrics
        training_date: When model was trained
        deployed_date: When model went to production
        model_path: Path to serialized model
        feature_hash: Hash of feature set for reproducibility
        notes: Human notes
    """

    version_id: int
    model_type: ModelType
    version: str
    status: ModelStatus
    training_config: TrainingConfig | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    training_date: datetime | None = None
    deployed_date: datetime | None = None
    model_path: str | None = None
    feature_hash: str | None = None
    notes: str = ''


@dataclass
class ModelResult:
    """Result from model training or evaluation.

    Attributes:
        success: Whether operation succeeded
        model_version: Version string if trained
        metrics: Performance metrics
        error_message: Error description if failed
        rows_processed: Number of rows processed
        training_time_seconds: Time spent training
        predictions: Sample predictions for validation
    """

    success: bool = False
    model_version: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    error_message: str | None = None
    rows_processed: int = 0
    training_time_seconds: float = 0.0
    predictions: list[dict[str, Any]] = field(default_factory=list)

    def add_metric(self, name: str, value: float) -> None:
        """Add a metric."""
        self.metrics[name] = value

    def add_error(self, message: str) -> None:
        """Add error message."""
        self.success = False
        self.error_message = message
        logger.error(message)


class BaseModel(ABC):
    """Abstract base class for baseball prediction models.

    All models must implement:
    - train(): Train on historical data
    - evaluate(): Evaluate on test data
    - predict(): Make predictions on new data
    - save(): Serialize model to storage
    - load(): Deserialize model from storage

    Example:
        >>> class MyModel(BaseModel):
        ...     def train(self, config: TrainingConfig) -> ModelResult:
        ...         # Implementation
        ...         pass
        >>> model = MyModel(db_connection=conn)
        >>> result = model.train(config)
        >>> if result.success:
        ...     predictions = model.predict(game_states)
    """

    def __init__(self, db_connection=None, config: ModelConfig | None = None) -> None:
        """Initialize model.

        Args:
            db_connection: Database connection for data loading
            config: Model configuration
        """
        self.db = db_connection
        self.config = config or self._default_config()
        self.status = ModelStatus.UNTRAINED
        self._model = None  # Underlying model object
        self._is_fitted = False

    @abstractmethod
    def _default_config(self) -> ModelConfig:
        """Return default configuration for this model type."""

    @property
    @abstractmethod
    def model_type(self) -> ModelType:
        """Return model type."""

    @property
    def is_trained(self) -> bool:
        """Check if model has been trained."""
        return (
            self.status in (ModelStatus.TRAINED, ModelStatus.VALIDATED, ModelStatus.PRODUCTION)
            and self._is_fitted
        )

    @abstractmethod
    def train(self, config: TrainingConfig) -> ModelResult:
        """Train the model.

        Args:
            config: Training configuration

        Returns:
            ModelResult with training metrics
        """

    @abstractmethod
    def evaluate(self, test_data: Any) -> ModelResult:
        """Evaluate model on test data.

        Args:
            test_data: Test dataset

        Returns:
            ModelResult with evaluation metrics
        """

    @abstractmethod
    def predict(self, features: Any) -> Any:
        """Make predictions on new data.

        Args:
            features: Feature vectors

        Returns:
            Predictions (format depends on model type)
        """

    @abstractmethod
    def save(self, path: str) -> bool:
        """Save model to disk.

        Args:
            path: Save path

        Returns:
            True if successful
        """

    @abstractmethod
    def load(self, path: str) -> bool:
        """Load model from disk.

        Args:
            path: Load path

        Returns:
            True if successful
        """

    def register_version(self, metrics: dict[str, float]) -> ModelVersion:
        """Register this model version in the registry.

        Args:
            metrics: Performance metrics

        Returns:
            ModelVersion record
        """
        if self.db is None:
            logger.warning('No database connection for version registration')
            return ModelVersion(
                version_id=0,
                model_type=self.model_type,
                version=self.config.version,
                status=self.status,
                metrics=metrics,
            )

        try:
            with self.db.cursor() as cur:
                cur.execute(
                    """INSERT INTO models.model_registry
                        (model_type, model_version, status, metrics,
                         hyperparameters, feature_columns, training_date, notes)
                       VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
                       RETURNING registry_id""",
                    (
                        self.model_type.value,
                        self.config.version,
                        self.status.value,
                        json.dumps(metrics),
                        json.dumps(self.config.hyperparameters),
                        json.dumps(self.config.feature_columns),
                        f'Trained {self.model_type.value} v{self.config.version}',
                    ),
                )
                version_id = cur.fetchone()[0]
                self.db.commit()

                return ModelVersion(
                    version_id=version_id,
                    model_type=self.model_type,
                    version=self.config.version,
                    status=self.status,
                    metrics=metrics,
                    training_date=datetime.now(),
                )
        except Exception as e:
            logger.exception(f'Failed to register version: {e}')
            return ModelVersion(
                version_id=0,
                model_type=self.model_type,
                version=self.config.version,
                status=ModelStatus.FAILED,
                error_message=str(e),
            )

    def load_training_data(self, seasons: list[int], limit: int | None = None) -> Any:
        """Load training data from database.

        Args:
            seasons: List of seasons to load
            limit: Maximum rows to load

        Returns:
            Training data (format depends on implementation)
        """
        if self.db is None:
            msg = 'No database connection'
            raise ValueError(msg)

        # Base implementation - subclasses may override
        logger.info(f'Loading training data for seasons: {seasons}')
        return None

    def compute_metrics(self, y_true: Any, y_pred: Any) -> dict[str, float]:
        """Compute standard evaluation metrics.

        Args:
            y_true: True labels
            y_pred: Predicted labels

        Returns:
            Dictionary of metrics
        """
        return {}

    def get_feature_importance(self) -> dict[str, float]:
        """Get feature importance if available.

        Returns:
            Feature name -> importance score
        """
        return {}


class SklearnBaseModel(BaseModel):
    """Base class for scikit-learn based models.

    Provides common functionality for sklearn models including:
    - Standard train/evaluate/predict flow
    - Model serialization
    - Feature importance extraction
    """

    def __init__(self, db_connection=None, config: ModelConfig | None = None) -> None:
        super().__init__(db_connection, config)
        self._feature_names: list[str] = []

    def train(self, config: TrainingConfig) -> ModelResult:
        """Train using sklearn API."""
        import time

        from sklearn.model_selection import train_test_split

        result = ModelResult()
        start_time = time.time()

        try:
            # Load data
            X, y = self._load_features_and_target(config.train_seasons)
            if X is None or y is None:
                result.add_error('Failed to load training data')
                return result

            result.rows_processed = len(y)

            # Split validation
            X_train, X_val, y_train, y_val = train_test_split(
                X,
                y,
                test_size=config.validation_split,
                random_state=self.config.random_seed,
            )

            # Train model (implemented by subclass)
            self._fit_model(X_train, y_train, config)

            # Validate
            val_metrics = self._evaluate_model(X_val, y_val)

            # Update status
            self.status = ModelStatus.TRAINED
            self._is_fitted = True

            # Build result
            result.success = True
            result.training_time_seconds = time.time() - start_time
            for name, value in val_metrics.items():
                result.add_metric(f'val_{name}', value)

            logger.info(f'Training complete in {result.training_time_seconds:.1f}s')

        except Exception as e:
            result.add_error(f'Training failed: {e}')
            self.status = ModelStatus.FAILED

        return result

    def evaluate(self, test_data: Any) -> ModelResult:
        """Evaluate on test data."""
        result = ModelResult()

        if not self.is_trained:
            result.add_error('Model not trained')
            return result

        try:
            X_test, y_test = test_data
            metrics = self._evaluate_model(X_test, y_test)

            result.success = True
            for name, value in metrics.items():
                result.add_metric(name, value)

            result.rows_processed = len(y_test)

        except Exception as e:
            result.add_error(f'Evaluation failed: {e}')

        return result

    def predict(self, features: Any) -> Any:
        """Make predictions."""
        if not self.is_trained:
            msg = 'Model not trained'
            raise ValueError(msg)

        if self._model is None:
            msg = 'Model not loaded'
            raise ValueError(msg)

        return self._model.predict(features)

    def predict_proba(self, features: Any) -> Any:
        """Make probability predictions."""
        if not self.is_trained:
            msg = 'Model not trained'
            raise ValueError(msg)

        if self._model is None:
            msg = 'Model not loaded'
            raise ValueError(msg)

        if hasattr(self._model, 'predict_proba'):
            return self._model.predict_proba(features)
        msg = 'Model does not support probability predictions'
        raise ValueError(msg)

    def save(self, path: str) -> bool:
        """Save model using joblib."""
        try:
            import joblib

            joblib.dump(
                {
                    'model': self._model,
                    'config': self.config.to_dict(),
                    'status': self.status.value,
                    'feature_names': self._feature_names,
                },
                path,
            )
            logger.info(f'Model saved to {path}')
            return True
        except Exception as e:
            logger.exception(f'Failed to save model: {e}')
            return False

    def load(self, path: str) -> bool:
        """Load model using joblib."""
        try:
            import joblib

            data = joblib.load(path)

            self._model = data['model']
            self.config = ModelConfig.from_dict(data['config'])
            self.status = ModelStatus(data['status'])
            self._feature_names = data.get('feature_names', [])
            self._is_fitted = True

            logger.info(f'Model loaded from {path}')
            return True
        except Exception as e:
            logger.exception(f'Failed to load model: {e}')
            return False

    def get_feature_importance(self) -> dict[str, float]:
        """Get feature importance from sklearn model."""
        if not self.is_trained or self._model is None:
            return {}

        if hasattr(self._model, 'feature_importances_'):
            importances = self._model.feature_importances_
        elif hasattr(self._model, 'coef_'):
            importances = abs(self._model.coef_[0])
        else:
            return {}

        return {name: float(imp) for name, imp in zip(self._feature_names, importances, strict=False)}

    @abstractmethod
    def _fit_model(self, X_train: Any, y_train: Any, config: TrainingConfig) -> None:
        """Fit the underlying model."""

    @abstractmethod
    def _evaluate_model(self, X: Any, y: Any) -> dict[str, float]:
        """Evaluate and return metrics."""

    @abstractmethod
    def _load_features_and_target(self, seasons: list[int]) -> tuple[Any, Any]:
        """Load features and target from database."""
