"""Next-Run Probability Model implementation.

Binary classification model to predict whether a run will score
in the remainder of the current inning given the game state.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import logging
from typing import Any

import numpy as np

from .base import ModelConfig, ModelType, SklearnBaseModel, TrainingConfig


logger = logging.getLogger(__name__)


class NextRunProbabilityModel(SklearnBaseModel):
    """Model to predict probability of a run scoring in remainder of inning.

    This is a binary classification model that takes game state features
    and outputs a probability that at least one run will score before the
    inning ends.

    Features used:
    - Game state: inning, outs, base_state, run_diff
    - Win expectancy and leverage index
    - Matchup features (batter vs pitcher)
    - Rolling form (recent performance)
    - Bullpen fatigue (if late inning)

    Target: did_run_score (boolean)

    Example:
        >>> model = NextRunProbabilityModel(db_connection=conn)
        >>> config = TrainingConfig(train_seasons=[2024, 2025], test_seasons=[2026])
        >>> result = model.train(config)
        >>>
        >>> # Make prediction
        >>> features = {
        ...     'inning': 7,
        ...     'outs': 1,
        ...     'base_state': 5,
        ...     'run_diff': 2,
        ...     'we': 0.65,
        ...     'li': 1.8,
        ...     'matchup_score': 0.45,
        ... }
        >>> prob = model.predict_proba([features])
        >>> print(f'Run probability: {prob[0]:.1%}')
    """

    DEFAULT_FEATURES = [
        'inning_normalized',
        'is_top_half',
        'outs',
        'base_state',
        'run_diff_normalized',
        'current_we',
        'we_delta_on_run',
        'current_li',
        'is_high_leverage',
        'run_probability',  # Historical rate
        'matchup_score',
        'is_platoon_advantage',
        'batter_l14_ops',
        'pitcher_l14_era',
    ]

    def __init__(self, db_connection=None, config: ModelConfig | None = None):
        """Initialize Next-Run Probability Model.

        Args:
            db_connection: Database connection
            config: Model configuration
        """
        super().__init__(db_connection, config)
        self._threshold = 0.5  # Classification threshold

    def _default_config(self) -> ModelConfig:
        """Return default configuration."""
        return ModelConfig(
            model_type=ModelType.NEXT_RUN_PROBABILITY,
            model_name='Next-Run Probability Model',
            version='1.0.0',
            random_seed=42,
            hyperparameters={
                'model_type': 'xgboost',  # or 'logistic_regression', 'random_forest'
                'max_depth': 6,
                'n_estimators': 100,
                'learning_rate': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
            },
            feature_columns=self.DEFAULT_FEATURES,
            target_column='did_run_score',
        )

    @property
    def model_type(self) -> ModelType:
        return ModelType.NEXT_RUN_PROBABILITY

    def _fit_model(self, X_train: Any, y_train: Any, config: TrainingConfig) -> None:
        """Fit the underlying model."""
        hp = self.config.hyperparameters
        model_type = hp.get('model_type', 'xgboost')

        if model_type == 'xgboost':
            try:
                from xgboost import XGBClassifier

                self._model = XGBClassifier(
                    max_depth=hp.get('max_depth', 6),
                    n_estimators=hp.get('n_estimators', 100),
                    learning_rate=hp.get('learning_rate', 0.1),
                    subsample=hp.get('subsample', 0.8),
                    colsample_bytree=hp.get('colsample_bytree', 0.8),
                    random_state=self.config.random_seed,
                    use_label_encoder=False,
                    eval_metric='logloss',
                )
            except ImportError:
                logger.warning('XGBoost not available, using RandomForest')
                model_type = 'random_forest'

        if model_type == 'random_forest':
            from sklearn.ensemble import RandomForestClassifier

            self._model = RandomForestClassifier(
                n_estimators=hp.get('n_estimators', 100),
                max_depth=hp.get('max_depth', 6),
                random_state=self.config.random_seed,
            )
        elif model_type == 'logistic_regression':
            from sklearn.linear_model import LogisticRegression

            self._model = LogisticRegression(
                max_iter=1000,
                random_state=self.config.random_seed,
            )

        self._model.fit(X_train, y_train)
        logger.info(f'Model fitted: {type(self._model).__name__}')

    def _evaluate_model(self, X: Any, y: Any) -> dict[str, float]:
        """Evaluate and return metrics."""
        from sklearn.metrics import (
            accuracy_score,
            brier_score_loss,
            f1_score,
            log_loss,
            precision_score,
            recall_score,
            roc_auc_score,
        )

        y_pred = self._model.predict(X)
        y_prob = (
            self._model.predict_proba(X)[:, 1] if hasattr(self._model, 'predict_proba') else y_pred
        )

        metrics = {
            'accuracy': accuracy_score(y, y_pred),
            'precision': precision_score(y, y_pred, zero_division=0),
            'recall': recall_score(y, y_pred, zero_division=0),
            'f1': f1_score(y, y_pred, zero_division=0),
            'roc_auc': roc_auc_score(y, y_prob) if len(np.unique(y)) > 1 else 0.5,
            'brier_score': brier_score_loss(y, y_prob),
            'log_loss': log_loss(y, y_prob) if len(np.unique(y)) > 1 else 0.0,
        }

        return metrics

    def _load_features_and_target(self, seasons: list[int]) -> tuple[Any, Any]:
        """Load features and target from database."""
        import pandas as pd

        if self.db is None:
            raise ValueError('No database connection')

        # Query training data
        query = """
            SELECT 
                nf.inning_normalized,
                nf.is_top_half::int as is_top_half,
                nf.outs,
                nf.base_state,
                nf.run_diff_normalized,
                nf.current_we,
                nf.we_delta_on_run,
                nf.current_li,
                nf.is_high_leverage::int as is_high_leverage,
                nf.run_probability as historical_run_rate,
                nf.matchup_score,
                nf.is_platoon_advantage::int as is_platoon_advantage,
                nf.batter_l14_ops,
                nf.pitcher_l14_era,
                t.did_run_score::int as target
            FROM models.next_run_features nf
            JOIN models.next_run_training_data t ON t.training_id = nf.training_id
            WHERE t.season = ANY(%s)
              AND t.did_run_score IS NOT NULL
        """

        try:
            df = pd.read_sql(query, self.db, params=(seasons,))

            # Handle missing values
            df = df.fillna(
                {
                    'matchup_score': 0.5,
                    'batter_l14_ops': 0.0,
                    'pitcher_l14_era': 4.5,
                    'is_platoon_advantage': 0,
                    'is_high_leverage': 0,
                }
            )

            # Separate features and target
            feature_cols = [c for c in df.columns if c != 'target']
            X = df[feature_cols].values
            y = df['target'].values

            self._feature_names = feature_cols

            logger.info(f'Loaded {len(y)} training samples')
            logger.info(f'Features: {feature_cols}')
            logger.info(f'Positive rate: {y.mean():.1%}')

            return X, y

        except Exception as e:
            logger.error(f'Failed to load training data: {e}')
            return None, None

    def predict_run_probability(self, game_state: dict[str, Any]) -> float:
        """Predict probability of run scoring for a single game state.

        Args:
            game_state: Dictionary with feature values

        Returns:
            Probability (0.0 to 1.0)
        """
        if not self.is_trained:
            raise ValueError('Model not trained')

        # Extract features in correct order
        features = []
        for col in self._feature_names:
            val = game_state.get(col, 0.0)
            if col == 'is_high_leverage' or col == 'is_platoon_advantage' or col == 'is_top_half':
                val = int(val) if val else 0
            features.append(float(val))

        X = np.array([features])
        prob = self._model.predict_proba(X)[0, 1]

        return float(prob)

    def predict_for_game(self, game_pk: int, season: int) -> list[dict[str, Any]]:
        """Generate predictions for all plays in a game.

        Args:
            game_pk: Game ID
            season: Season year

        Returns:
            List of prediction dictionaries
        """
        if self.db is None:
            raise ValueError('No database connection')

        import pandas as pd

        query = """
            SELECT 
                nf.game_pk,
                t.observation_at_bat_index,
                nf.inning_normalized,
                nf.is_top_half::int,
                nf.outs,
                nf.base_state,
                nf.run_diff_normalized,
                nf.current_we,
                nf.we_delta_on_run,
                nf.current_li,
                nf.is_high_leverage::int,
                nf.run_probability,
                nf.matchup_score,
                nf.is_platoon_advantage::int,
                nf.batter_l14_ops,
                nf.pitcher_l14_era
            FROM models.next_run_features nf
            JOIN models.next_run_training_data t ON t.training_id = nf.training_id
            WHERE nf.game_pk = %s AND nf.season = %s
        """

        df = pd.read_sql(query, self.db, params=(game_pk, season))

        if len(df) == 0:
            return []

        # Get features for prediction
        feature_cols = [c for c in df.columns if c not in ['game_pk', 'observation_at_bat_index']]
        X = df[feature_cols].fillna(0).values

        # Predict
        probabilities = self._model.predict_proba(X)[:, 1]

        # Build results
        results = []
        for i, row in df.iterrows():
            prob = probabilities[i]
            results.append(
                {
                    'game_pk': row['game_pk'],
                    'at_bat_index': row['observation_at_bat_index'],
                    'run_probability': float(prob),
                    'prediction': prob > 0.5,
                    'confidence': abs(prob - 0.5) * 2,  # 0-1 scale
                }
            )

        return results

    def save_predictions(self, predictions: list[dict[str, Any]], model_version: str) -> bool:
        """Save predictions to database.

        Args:
            predictions: List of prediction dictionaries
            model_version: Model version string

        Returns:
            True if successful
        """
        if self.db is None:
            return False

        try:
            with self.db.cursor() as cur:
                for pred in predictions:
                    cur.execute(
                        """INSERT INTO models.next_run_predictions
                            (model_version, game_pk, season,
                             observation_at_bat_index, inning, is_top,
                             run_probability, confidence, feature_snapshot)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (model_version, game_pk, observation_at_bat_index) 
                           DO UPDATE SET
                             run_probability = EXCLUDED.run_probability,
                             confidence = EXCLUDED.confidence,
                             predicted_at = NOW()""",
                        (
                            model_version,
                            pred['game_pk'],
                            pred.get('season', 2026),
                            pred['at_bat_index'],
                            pred.get('inning', 1),
                            pred.get('is_top', True),
                            pred['run_probability'],
                            pred.get('confidence', 0.5),
                            pred.get('features', {}),
                        ),
                    )
            self.db.commit()
            logger.info(f'Saved {len(predictions)} predictions')
            return True
        except Exception as e:
            logger.error(f'Failed to save predictions: {e}')
            return False

    def get_model_info(self) -> dict[str, Any]:
        """Get model information."""
        info = {
            'model_type': self.model_type.value,
            'model_name': self.config.model_name,
            'version': self.config.version,
            'status': self.status.value,
            'is_trained': self.is_trained,
            'features': self._feature_names,
            'hyperparameters': self.config.hyperparameters,
        }

        if self.is_trained and self._model is not None:
            info['model_class'] = type(self._model).__name__
            info['feature_importance'] = self.get_feature_importance()

        return info
