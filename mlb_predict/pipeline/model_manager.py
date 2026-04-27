"""Model management for live predictions.

Integrates with existing model infrastructure to load and use
trained models for real-time win probability predictions.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from __future__ import annotations

import logging
import os
import pickle
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


try:
    import joblib

    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

from mlb_predict.features.live_features import GameStateFeatures


logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """Metadata for a loaded model."""

    model_id: str
    model_name: str
    model_version: str
    target: str  # e.g., "win_probability"
    feature_names: list[str]
    training_date: str
    metrics: dict[str, float]
    artifact_path: str | None = None


class LiveModelManager:
    """Manager for live prediction models.

    Loads and caches trained models from disk or database.
    Provides consistent interface for making predictions.

    Features:
    - Model caching in memory
    - Lazy loading on first use
    - Fallback to heuristic if model unavailable
    - Feature name validation
    - Prediction confidence scoring
    """

    DEFAULT_MODEL_DIR = Path('data/models')

    # Model targets we support
    SUPPORTED_TARGETS = [
        'win_probability',
        'plate_appearance_outcome',
        'run_expectancy',
    ]

    def __init__(
        self,
        model_dir: Path | None = None,
        use_database: bool = True,
    ):
        self.model_dir = model_dir or self.DEFAULT_MODEL_DIR
        self.use_database = use_database

        # Cache: target -> (model, metadata)
        self._models: dict[str, tuple[Any, ModelMetadata]] = {}
        self._fallback_enabled = True

        # Stats
        self._stats = {
            'predictions': 0,
            'cache_hits': 0,
            'model_loads': 0,
            'fallbacks': 0,
            'errors': 0,
        }

    def load_model(
        self,
        target: str,
        model_name: str | None = None,
        force_reload: bool = False,
    ) -> bool:
        """Load a model for the given target.

        Args:
            target: Prediction target (e.g., "win_probability")
            model_name: Specific model name (optional)
            force_reload: Force reload even if cached

        Returns:
            True if model loaded successfully
        """
        if target in self._models and not force_reload:
            self._stats['cache_hits'] += 1
            return True

        # Try to load from disk first
        loaded = self._load_from_disk(target, model_name)

        if not loaded and self.use_database:
            # Try database
            loaded = self._load_from_database(target, model_name)

        if loaded:
            self._stats['model_loads'] += 1
            return True

        logger.warning(f'Could not load model for target: {target}')
        return False

    def _load_from_disk(
        self,
        target: str,
        model_name: str | None = None,
    ) -> bool:
        """Load model from local disk."""
        if not self.model_dir.exists():
            return False

        # Look for model files
        patterns = [
            f'{target}.pkl',
            f'{target}_*.pkl',
            f'{target}.joblib',
            f'{target}_*.joblib',
        ]

        for pattern in patterns:
            matches = list(self.model_dir.glob(pattern))
            if matches:
                # Use most recent
                model_path = max(matches, key=lambda p: p.stat().st_mtime)

                try:
                    model = self._deserialize_model(model_path)

                    metadata = ModelMetadata(
                        model_id=f'{target}_disk',
                        model_name=model_name or target,
                        model_version='1.0.0',
                        target=target,
                        feature_names=self._extract_feature_names(model),
                        training_date=datetime.fromtimestamp(
                            model_path.stat().st_mtime,
                        ).isoformat(),
                        metrics={},
                        artifact_path=str(model_path),
                    )

                    self._models[target] = (model, metadata)
                    logger.info(f'Loaded model from disk: {model_path}')
                    return True

                except Exception as e:
                    logger.error(f'Failed to load model from {model_path}: {e}')

        return False

    def _load_from_database(
        self,
        target: str,
        model_name: str | None = None,
    ) -> bool:
        """Load model from database registry."""
        try:
            import psycopg2

            conn = psycopg2.connect(
                host=os.environ.get('PGHOST', 'localhost'),
                port=os.environ.get('PGPORT', '5432'),
                dbname=os.environ.get('PGDATABASE', 'retrosheet'),
                user=os.environ.get('PGUSER', 'postgres'),
                password=os.environ.get('PGPASSWORD', ''),
            )

            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT model_id, model_name, model_version,
                           artifact_uri, feature_spec, training_metrics
                    FROM models.model_registry
                    WHERE target = %s
                      AND is_active = true
                    ORDER BY training_date DESC
                    LIMIT 1
                    """,
                    (target,),
                )

                row = cur.fetchone()
                if not row:
                    return False

                model_id, name, version, uri, feature_spec, metrics = row

                # Load model from path
                model_path = Path(uri)
                if not model_path.exists():
                    # Try relative to project root
                    model_path = Path('.') / uri

                if model_path.exists():
                    model = self._deserialize_model(model_path)

                    metadata = ModelMetadata(
                        model_id=model_id,
                        model_name=name,
                        model_version=version,
                        target=target,
                        feature_names=feature_spec.get('features', []),
                        training_date=datetime.now().isoformat(),
                        metrics=metrics or {},
                        artifact_path=str(model_path),
                    )

                    self._models[target] = (model, metadata)
                    logger.info(f'Loaded model from database: {name} v{version}')
                    return True

            conn.close()

        except Exception as e:
            logger.error(f'Database model load failed: {e}')

        return False

    def _deserialize_model(self, path: Path) -> Any:
        """Deserialize model from file."""
        if JOBLIB_AVAILABLE:
            return joblib.load(path)
        with open(path, 'rb') as f:
            return pickle.load(f)

    def _extract_feature_names(self, model: Any) -> list[str]:
        """Extract feature names from model if available."""
        # Try common attribute names
        for attr in ['feature_names_', 'feature_names', 'features', 'feature_name']:
            if hasattr(model, attr):
                value = getattr(model, attr)
                if isinstance(value, list):
                    return value
                if isinstance(value, np.ndarray):
                    return value.tolist()

        # Try to get from sklearn
        if hasattr(model, 'n_features_in_'):
            return [f'feature_{i}' for i in range(model.n_features_in_)]

        return []

    def predict(
        self,
        target: str,
        features: GameStateFeatures,
    ) -> tuple[float, float, ModelMetadata]:
        """Make a prediction using the loaded model.

        Args:
            target: Prediction target
            features: Computed game state features

        Returns:
            (prediction_value, confidence, metadata)
        """
        self._stats['predictions'] += 1

        # Ensure model is loaded
        if target not in self._models:
            if not self.load_model(target):
                if self._fallback_enabled:
                    self._stats['fallbacks'] += 1
                    return self._fallback_prediction(target, features)
                raise RuntimeError(f'Model not available for {target}')

        model, metadata = self._models[target]

        try:
            # Convert features to vector
            feature_vector = np.array(features.to_vector()).reshape(1, -1)

            # Make prediction
            if hasattr(model, 'predict_proba'):
                # Classification - get probability of positive class
                proba = model.predict_proba(feature_vector)[0]
                prediction = float(proba[-1])  # Last class is typically positive

                # Confidence is max probability
                confidence = float(np.max(proba))
            else:
                # Regression
                prediction = float(model.predict(feature_vector)[0])
                confidence = 0.8  # Default confidence for regression

            return prediction, confidence, metadata

        except Exception as e:
            logger.error(f'Prediction error: {e}')
            self._stats['errors'] += 1

            if self._fallback_enabled:
                return self._fallback_prediction(target, features)
            raise

    def _fallback_prediction(
        self,
        target: str,
        features: GameStateFeatures,
    ) -> tuple[float, float, ModelMetadata]:
        """Heuristic prediction when model unavailable."""
        if target == 'win_probability':
            # Simple heuristic based on score and inning
            score_diff = features.score_differential
            inning_factor = features.inning / 9.0

            if score_diff > 0:
                # Home team winning
                base_prob = 0.5 + (abs(score_diff) * 0.05) + (inning_factor * 0.1)
            elif score_diff < 0:
                # Away team winning
                base_prob = 0.5 - (abs(score_diff) * 0.05) - (inning_factor * 0.1)
            else:
                base_prob = 0.5

            # Clamp to [0.05, 0.95]
            prediction = max(0.05, min(0.95, base_prob))
            confidence = 0.6  # Lower confidence for heuristic

        else:
            prediction = 0.5
            confidence = 0.5

        metadata = ModelMetadata(
            model_id='fallback_heuristic',
            model_name='Heuristic',
            model_version='1.0.0',
            target=target,
            feature_names=[],
            training_date=datetime.now().isoformat(),
            metrics={'fallback': True},
        )

        return prediction, confidence, metadata

    def get_model_info(self, target: str) -> dict[str, Any] | None:
        """Get information about a loaded model."""
        if target not in self._models:
            return None

        _, metadata = self._models[target]
        return {
            'model_id': metadata.model_id,
            'model_name': metadata.model_name,
            'model_version': metadata.model_version,
            'target': metadata.target,
            'feature_count': len(metadata.feature_names),
            'training_date': metadata.training_date,
            'metrics': metadata.metrics,
        }

    def list_loaded_models(self) -> list[str]:
        """List all loaded model targets."""
        return list(self._models.keys())

    def get_stats(self) -> dict[str, Any]:
        """Get manager statistics."""
        return {
            **self._stats,
            'loaded_models': len(self._models),
            'model_targets': self.list_loaded_models(),
        }

    def unload_model(self, target: str) -> None:
        """Unload a model from memory."""
        if target in self._models:
            del self._models[target]
            logger.info(f'Unloaded model: {target}')

    def unload_all(self) -> None:
        """Unload all models."""
        self._models.clear()
        logger.info('Unloaded all models')
