"""Model Inference Pipeline for the baseball prediction warehouse.

Provides real-time prediction capabilities with:
- Model loading from registry
- Feature extraction
- Prediction with confidence intervals
- Result storage
- Batch inference

Author: Agent Cascade
Date: 2026-04-28
"""

import pickle
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from baseball.core.cache import cached_sync
from baseball.core.db import get_db_connection
from baseball.models.registry import ModelRegistry, ModelRegistryEntry


if TYPE_CHECKING:
    from baseball.models.base import BaseModel


@dataclass
class PredictionResult:
    """Result of a single prediction."""
    prediction_id: int | None = None
    prediction_type: str = ''
    model_version: str = ''
    predicted_value: float = 0.0
    predicted_class: str | None = None
    confidence_lower: float | None = None
    confidence_upper: float | None = None
    probability_distribution: dict[str, float] | None = None
    feature_vector: dict[str, Any] | None = None
    inference_time_ms: float = 0.0
    success: bool = False
    error_message: str = ''


class InferencePipeline:
    """Real-time inference pipeline for baseball prediction models.

    Handles:
    - Loading production models from registry
    - Feature extraction from database
    - Single and batch predictions
    - Confidence interval estimation
    - Prediction storage

    Usage:
        # Single game prediction
        pipeline = InferencePipeline(model_name="win_probability")
        result = pipeline.predict_game(game_pk=716190)

        # Batch prediction
        results = pipeline.predict_batch(game_pks=[716190, 716191, 716192])
    """

    def __init__(
        self,
        model_name: str,
        model_version: str | None = None,
        artifacts_dir: str = 'models/artifacts',
    ) -> None:
        self.model_name = model_name
        self.model_version = model_version
        self.artifacts_dir = Path(artifacts_dir)
        self.registry = ModelRegistry(artifacts_dir)

        self._model: BaseModel | None = None
        self._model_entry: ModelRegistryEntry | None = None

        # Load model on init
        self._load_model()

    def _load_model(self) -> bool:
        """Load model from registry and disk."""
        try:
            if self.model_version:
                # Load specific version
                models = self.registry.list_models(
                    model_name=self.model_name,
                    limit=10,
                )
                for entry in models:
                    if entry.model_version == self.model_version:
                        self._model_entry = entry
                        break
            else:
                # Load production model
                self._model_entry = self.registry.get_production_model(self.model_name)

            if self._model_entry is None:
                msg = (
                    f"Model {self.model_name} "
                    f"version {self.model_version or 'production'} not found"
                )
                raise ValueError(
                    msg,
                )

            # Load from disk
            artifact_path = Path(self._model_entry.artifact_path)
            if not artifact_path.exists():
                msg = f'Artifact not found: {artifact_path}'
                raise FileNotFoundError(msg)

            with open(artifact_path, 'rb') as f:
                self._model = pickle.load(f)

            return True

        except Exception as e:
            print(f'Error loading model: {e}')
            return False

    def predict_game(
        self,
        game_pk: int,
        store_result: bool = True,
        request_source: str = 'api',
    ) -> PredictionResult:
        """Predict win probability for a specific game.

        Args:
            game_pk: MLB game ID
            store_result: Whether to store prediction in database
            request_source: Source of request (api, cli, batch, etc.)

        Returns:
            PredictionResult with prediction and metadata
        """
        start_time = time.time()

        if self._model is None:
            return PredictionResult(
                success=False,
                error_message='Model not loaded',
            )

        try:
            # Extract features for game
            features = self._extract_game_features(game_pk)
            if features is None:
                return PredictionResult(
                    success=False,
                    error_message=f'Could not extract features for game {game_pk}',
                )

            # Make prediction
            X = np.array([features['vector']])
            y_pred_proba = self._model.predict_proba(X)

            # For binary classification, get probability of positive class
            if len(y_pred_proba.shape) > 1 and y_pred_proba.shape[1] > 1:
                home_win_prob = y_pred_proba[0][1]
            else:
                home_win_prob = y_pred_proba[0]

            # Calculate confidence interval (simple approach)
            # In production, use proper uncertainty quantification
            confidence_width = 0.1  # Placeholder
            confidence_lower = max(0.0, home_win_prob - confidence_width)
            confidence_upper = min(1.0, home_win_prob + confidence_width)

            inference_time = (time.time() - start_time) * 1000  # ms

            result = PredictionResult(
                prediction_type=self.model_name,
                model_version=self._model_entry.model_version if self._model_entry else 'unknown',
                predicted_value=float(home_win_prob),
                confidence_lower=float(confidence_lower),
                confidence_upper=float(confidence_upper),
                feature_vector=features['dict'],
                inference_time_ms=inference_time,
                success=True,
            )

            # Store in database if requested
            if store_result:
                result.prediction_id = self._store_prediction(
                    game_pk=game_pk,
                    result=result,
                    request_source=request_source,
                )

            return result

        except Exception as e:
            return PredictionResult(
                success=False,
                error_message=str(e),
                inference_time_ms=(time.time() - start_time) * 1000,
            )

    def predict_batch(
        self,
        game_pks: list[int],
        store_results: bool = True,
    ) -> list[PredictionResult]:
        """Predict for multiple games.

        Args:
            game_pks: List of MLB game IDs
            store_results: Whether to store predictions in database

        Returns:
            List of PredictionResult objects
        """
        results = []

        for game_pk in game_pks:
            result = self.predict_game(
                game_pk=game_pk,
                store_result=store_results,
                request_source='batch',
            )
            results.append(result)

        return results

    def predict_from_features(
        self,
        features: dict[str, float],
        store_result: bool = False,
    ) -> PredictionResult:
        """Predict from raw feature dictionary.

        Args:
            features: Dict of feature values
            store_result: Whether to store prediction

        Returns:
            PredictionResult
        """
        start_time = time.time()

        if self._model is None:
            return PredictionResult(
                success=False,
                error_message='Model not loaded',
            )

        try:
            # Convert features to vector (must match training order)
            feature_order = self._model_entry.feature_set if self._model_entry else list(features.keys())
            feature_vector = [features.get(k, 0.0) for k in feature_order]

            X = np.array([feature_vector])
            y_pred_proba = self._model.predict_proba(X)

            if len(y_pred_proba.shape) > 1 and y_pred_proba.shape[1] > 1:
                predicted_value = y_pred_proba[0][1]
            else:
                predicted_value = y_pred_proba[0]

            inference_time = (time.time() - start_time) * 1000

            return PredictionResult(
                prediction_type=self.model_name,
                model_version=self._model_entry.model_version if self._model_entry else 'unknown',
                predicted_value=float(predicted_value),
                feature_vector=features,
                inference_time_ms=inference_time,
                success=True,
            )

        except Exception as e:
            return PredictionResult(
                success=False,
                error_message=str(e),
            )

    @cached_sync(ttl=120, key_prefix='game_features')
    def _extract_game_features(self, game_pk: int) -> dict[str, Any] | None:
        """Extract normalized features for a game from database.

        Returns dict with 'vector' (numpy array) and 'dict' (feature dict).
        Cached for 2 minutes.
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Get latest state for game
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
                        home_score,
                        away_score,
                        inning,
                        is_top_inning,
                        outs
                    FROM features.win_probability_inputs
                    WHERE game_pk = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (game_pk,),
                )

                row = cur.fetchone()
                if not row:
                    # Try live games table
                    cur.execute(
                        """
                        SELECT
                            lg.inning::float / 9.0 as inning_norm,
                            lg.outs::float / 3.0 as outs_norm,
                            (lg.home_score - lg.away_score)::float / 10.0 as score_diff_norm,
                            lg.runner_on_first::int,
                            lg.runner_on_second::int,
                            lg.runner_on_third::int,
                            (CASE WHEN lg.is_top_inning THEN 0 ELSE 1 END) as batting_team_home,
                            (CASE WHEN lg.inning >= 9 THEN 1 ELSE 0 END) as is_final_inning,
                            lg.home_score,
                            lg.away_score,
                            lg.inning,
                            lg.is_top_inning,
                            lg.outs
                        FROM core.live_games lg
                        WHERE lg.game_pk = %s
                        ORDER BY lg.extracted_at DESC
                        LIMIT 1
                        """,
                        (game_pk,),
                    )
                    row = cur.fetchone()

                if not row:
                    return None

                # Build feature dict
                feature_dict = {
                    'inning_norm': row[0],
                    'outs_norm': row[1],
                    'score_diff_norm': row[2],
                    'runner_1b': row[3],
                    'runner_2b': row[4],
                    'runner_3b': row[5],
                    'batting_team_home': row[6],
                    'is_final_inning': row[7],
                    'home_score': row[8],
                    'away_score': row[9],
                    'inning': row[10],
                    'is_top_inning': row[11],
                    'outs': row[12],
                }

                # Build feature vector in correct order
                feature_order = [
                    'inning_norm', 'outs_norm', 'score_diff_norm',
                    'runner_1b', 'runner_2b', 'runner_3b',
                    'batting_team_home', 'is_final_inning',
                ]
                feature_vector = [feature_dict.get(k, 0.0) for k in feature_order]

                return {
                    'vector': np.array(feature_vector),
                    'dict': feature_dict,
                }
        finally:
            conn.close()

    def _store_prediction(
        self,
        game_pk: int,
        result: PredictionResult,
        request_source: str,
    ) -> int | None:
        """Store prediction in database."""
        if self._model_entry is None:
            return None

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT predictions.store_prediction(
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        result.prediction_type,
                        self._model_entry.model_id,
                        result.predicted_value,
                        game_pk,
                        result.feature_vector,
                        None,  # probability_distribution
                        result.confidence_lower,
                        result.confidence_upper,
                        request_source,
                        None,   # request_id
                    ),
                )
                prediction_id = cur.fetchone()[0]
                conn.commit()
                return prediction_id
        except Exception as e:
            print(f'Error storing prediction: {e}')
            return None
        finally:
            conn.close()

    def get_model_info(self) -> dict[str, Any] | None:
        """Get information about the loaded model."""
        if self._model_entry is None:
            return None

        return {
            'model_name': self._model_entry.model_name,
            'model_version': self._model_entry.model_version,
            'model_type': self._model_entry.model_type,
            'status': self._model_entry.status,
            'primary_metric': self._model_entry.primary_metric,
            'primary_metric_value': self._model_entry.primary_metric_value,
            'training_date': self._model_entry.training_date.isoformat() if self._model_entry.training_date else None,
            'feature_set': self._model_entry.feature_set,
        }


def predict_game_win_probability(
    game_pk: int,
    model_version: str | None = None,
    store_result: bool = True,
) -> PredictionResult:
    """Convenience function to predict win probability for a game.

    Args:
        game_pk: MLB game ID
        model_version: Specific model version (None for production)
        store_result: Whether to store in database

    Returns:
        PredictionResult
    """
    pipeline = InferencePipeline(
        model_name='win_probability',
        model_version=model_version,
    )
    return pipeline.predict_game(game_pk, store_result=store_result)


def predict_batch_win_probability(
    game_pks: list[int],
    model_version: str | None = None,
) -> list[PredictionResult]:
    """Predict win probability for multiple games.

    Args:
        game_pks: List of MLB game IDs
        model_version: Specific model version (None for production)

    Returns:
        List of PredictionResult
    """
    pipeline = InferencePipeline(
        model_name='win_probability',
        model_version=model_version,
    )
    return pipeline.predict_batch(game_pks)
