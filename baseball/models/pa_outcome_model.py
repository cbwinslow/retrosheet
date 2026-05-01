"""Plate Appearance Outcome Model implementation.

Multi-class classification model to predict the outcome of a single
plate appearance: out, walk, single, double, triple, or home run.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import logging
from typing import Any

import numpy as np

from .base import ModelConfig, ModelType, SklearnBaseModel, TrainingConfig


logger = logging.getLogger(__name__)


class PAOutcomeModel(SklearnBaseModel):
    """Model to predict the outcome category of a plate appearance.

    This is a multi-class classification model that predicts one of:
    - out (strikeout, groundout, flyout, etc.)
    - walk (BB, HBP)
    - single
    - double
    - triple
    - home_run

    Features used:
    - Game state: inning, outs, base_state, leverage
    - Matchup: batter vs pitcher score, platoon advantage
    - Batter form: recent OPS, hot/cold status
    - Pitcher form: recent ERA, WHIP, K/9
    - Historical rates for this batter/pitcher profile

    Example:
        >>> model = PAOutcomeModel(db_connection=conn)
        >>> config = TrainingConfig(train_seasons=[2024, 2025])
        >>> result = model.train(config)
        >>>
        >>> # Predict single PA
        >>> probs = model.predict_class_probabilities(
        ...     {
        ...         'inning': 5,
        ...         'outs': 1,
        ...         'base_state': 1,
        ...         'matchup_score': 0.6,
        ...         'batter_l14_ops': 0.920,
        ...         'pitcher_l14_era': 4.50,
        ...     }
        ... )
        >>> print(f'Most likely: {max(probs, key=probs.get)}')
        >>> print(f'HR probability: {probs["home_run"]:.1%}')
    """

    # Outcome classes
    CLASSES = ['out', 'walk', 'single', 'double', 'triple', 'home_run']
    CLASS_ENCODINGS = {cls: i for i, cls in enumerate(CLASSES)}

    DEFAULT_FEATURES = [
        'inning_normalized',
        'is_top_half',
        'outs',
        'base_state',
        'run_diff_normalized',
        'leverage_index',
        'is_high_leverage',
        'matchup_score',
        'is_platoon_advantage',
        'batter_l7_ops',
        'batter_l14_ops',
        'batter_l30_ops',
        'batter_is_hot',
        'batter_vs_hand_ops',
        'pitcher_l7_era',
        'pitcher_l14_era',
        'pitcher_l30_era',
        'pitcher_is_hot',
        'pitcher_l30_k_9',
        'historical_out_rate',
        'historical_walk_rate',
        'historical_hit_rate',
        'historical_hr_rate',
    ]

    def __init__(self, db_connection=None, config: ModelConfig | None = None) -> None:
        """Initialize PA Outcome Model.

        Args:
            db_connection: Database connection
            config: Model configuration
        """
        super().__init__(db_connection, config)

    def _default_config(self) -> ModelConfig:
        """Return default configuration."""
        return ModelConfig(
            model_type=ModelType.PA_OUTCOME,
            model_name='PA Outcome Model',
            version='1.0.0',
            random_seed=42,
            hyperparameters={
                'model_type': 'xgboost',  # or 'random_forest', 'logistic_regression'
                'max_depth': 8,
                'n_estimators': 150,
                'learning_rate': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
            },
            feature_columns=self.DEFAULT_FEATURES,
            target_column='outcome_encoded',
        )

    @property
    def model_type(self) -> ModelType:
        return ModelType.PA_OUTCOME

    def _fit_model(self, X_train: Any, y_train: Any, config: TrainingConfig) -> None:
        """Fit the underlying model."""
        hp = self.config.hyperparameters
        model_type = hp.get('model_type', 'xgboost')

        if model_type == 'xgboost':
            try:
                from xgboost import XGBClassifier

                self._model = XGBClassifier(
                    max_depth=hp.get('max_depth', 8),
                    n_estimators=hp.get('n_estimators', 150),
                    learning_rate=hp.get('learning_rate', 0.1),
                    subsample=hp.get('subsample', 0.8),
                    colsample_bytree=hp.get('colsample_bytree', 0.8),
                    random_state=self.config.random_seed,
                    use_label_encoder=False,
                    eval_metric='mlogloss',
                    num_class=len(self.CLASSES),
                )
            except ImportError:
                logger.warning('XGBoost not available, using RandomForest')
                model_type = 'random_forest'

        if model_type == 'random_forest':
            from sklearn.ensemble import RandomForestClassifier

            self._model = RandomForestClassifier(
                n_estimators=hp.get('n_estimators', 150),
                max_depth=hp.get('max_depth', 8),
                random_state=self.config.random_seed,
            )
        elif model_type == 'logistic_regression':
            from sklearn.linear_model import LogisticRegression

            self._model = LogisticRegression(
                max_iter=1000,
                random_state=self.config.random_seed,
                multi_class='multinomial',
            )

        self._model.fit(X_train, y_train)
        logger.info(f'Model fitted: {type(self._model).__name__}')

    def _evaluate_model(self, X: Any, y: Any) -> dict[str, float]:
        """Evaluate and return metrics."""
        from sklearn.metrics import (
            accuracy_score,
            f1_score,
            log_loss,
            precision_score,
            recall_score,
        )

        y_pred = self._model.predict(X)
        y_prob = self._model.predict_proba(X) if hasattr(self._model, 'predict_proba') else None

        # Overall metrics
        metrics = {
            'accuracy': accuracy_score(y, y_pred),
            'macro_precision': precision_score(y, y_pred, average='macro', zero_division=0),
            'macro_recall': recall_score(y, y_pred, average='macro', zero_division=0),
            'macro_f1': f1_score(y, y_pred, average='macro', zero_division=0),
        }

        # Per-class metrics
        for i, cls in enumerate(self.CLASSES):
            try:
                metrics[f'{cls}_precision'] = precision_score(
                    y == i,
                    y_pred == i,
                    zero_division=0,
                )
                metrics[f'{cls}_recall'] = recall_score(
                    y == i,
                    y_pred == i,
                    zero_division=0,
                )
            except:
                pass

        # Log loss if probabilities available
        if y_prob is not None:
            metrics['log_loss'] = log_loss(y, y_prob)

        return metrics

    def _load_features_and_target(self, seasons: list[int]) -> tuple[Any, Any]:
        """Load features and target from database."""
        import pandas as pd

        if self.db is None:
            msg = 'No database connection'
            raise ValueError(msg)

        query = """
            SELECT
                pf.inning_normalized,
                pf.is_top_half::int as is_top_half,
                pf.outs,
                pf.base_state,
                pf.run_diff_normalized,
                pf.leverage_index,
                pf.is_high_leverage::int as is_high_leverage,
                pf.matchup_score,
                pf.is_platoon_advantage::int as is_platoon_advantage,
                pf.batter_l7_ops,
                pf.batter_l14_ops,
                pf.batter_l30_ops,
                pf.batter_is_hot::int as batter_is_hot,
                pf.batter_vs_hand_ops,
                pf.pitcher_l7_era,
                pf.pitcher_l14_era,
                pf.pitcher_l30_era,
                pf.pitcher_is_hot::int as pitcher_is_hot,
                pf.pitcher_l30_k_9,
                pf.historical_out_rate,
                pf.historical_walk_rate,
                pf.historical_hit_rate,
                pf.historical_hr_rate,
                t.outcome_encoded as target
            FROM models.pa_outcome_features pf
            JOIN models.pa_outcome_training_data t ON t.training_id = pf.training_id
            WHERE t.season = ANY(%s)
              AND t.outcome_encoded IS NOT NULL
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
                    'batter_is_hot': 0,
                    'pitcher_is_hot': 0,
                    'historical_out_rate': 0.68,
                    'historical_walk_rate': 0.09,
                    'historical_hit_rate': 0.23,
                    'historical_hr_rate': 0.035,
                },
            )

            # Separate features and target
            feature_cols = [c for c in df.columns if c != 'target']
            X = df[feature_cols].values
            y = df['target'].values

            self._feature_names = feature_cols

            logger.info(f'Loaded {len(y)} training samples')
            logger.info(f'Features: {feature_cols}')
            logger.info(f'Class distribution: {dict(zip(*np.unique(y, return_counts=True), strict=False))}')

            return X, y

        except Exception as e:
            logger.exception(f'Failed to load training data: {e}')
            return None, None

    def predict_class_probabilities(self, game_state: dict[str, Any]) -> dict[str, float]:
        """Predict class probabilities for a single PA.

        Args:
            game_state: Dictionary with feature values

        Returns:
            Dictionary mapping class names to probabilities
        """
        if not self.is_trained:
            msg = 'Model not trained'
            raise ValueError(msg)

        # Extract features in correct order
        features = []
        for col in self._feature_names:
            val = game_state.get(col, 0.0)
            if col in (
                'is_high_leverage',
                'is_platoon_advantage',
                'batter_is_hot',
                'pitcher_is_hot',
                'is_top_half',
            ):
                val = int(val) if val else 0
            features.append(float(val))

        X = np.array([features])

        if hasattr(self._model, 'predict_proba'):
            probs = self._model.predict_proba(X)[0]
        else:
            # Fallback to one-hot
            pred = self._model.predict(X)[0]
            probs = np.zeros(len(self.CLASSES))
            probs[pred] = 1.0

        return {cls: float(probs[i]) for i, cls in enumerate(self.CLASSES)}

    def predict_pa(self, game_state: dict[str, Any]) -> dict[str, Any]:
        """Full prediction for a plate appearance.

        Args:
            game_state: Feature dictionary

        Returns:
            Prediction result with probabilities and derived metrics
        """
        probs = self.predict_class_probabilities(game_state)

        # Most likely outcome
        predicted_class = max(probs, key=probs.get)
        confidence = probs[predicted_class]

        # Derived probabilities
        prob_hit = probs['single'] + probs['double'] + probs['triple'] + probs['home_run']
        prob_on_base = prob_hit + probs['walk']
        prob_xbh = probs['double'] + probs['triple'] + probs['home_run']

        # Expected bases
        expected_bases = (
            probs['walk'] * 1
            + probs['single'] * 1
            + probs['double'] * 2
            + probs['triple'] * 3
            + probs['home_run'] * 4
        )

        # Expected runs (simplified - would be context-dependent)
        expected_runs = (
            probs['home_run'] * 1.0
            + probs['triple'] * 0.7
            + probs['double'] * 0.4
            + probs['single'] * 0.2
            + probs['walk'] * 0.1
        )

        return {
            'predicted_outcome': predicted_class,
            'confidence': confidence,
            'probabilities': probs,
            'prob_hit': prob_hit,
            'prob_on_base': prob_on_base,
            'prob_xbh': prob_xbh,
            'expected_bases': expected_bases,
            'expected_runs': expected_runs,
        }

    def predict_for_game(self, game_pk: int, season: int) -> list[dict[str, Any]]:
        """Generate predictions for all PAs in a game.

        Args:
            game_pk: Game ID
            season: Season year

        Returns:
            List of prediction dictionaries
        """
        if self.db is None:
            msg = 'No database connection'
            raise ValueError(msg)

        import pandas as pd

        query = """
            SELECT
                pf.game_pk,
                t.at_bat_index,
                t.batter_id,
                t.pitcher_id,
                pf.inning_normalized,
                pf.is_top_half::int as is_top_half,
                pf.outs,
                pf.base_state,
                pf.run_diff_normalized,
                pf.leverage_index,
                pf.is_high_leverage::int as is_high_leverage,
                pf.matchup_score,
                pf.is_platoon_advantage::int as is_platoon_advantage,
                pf.batter_l14_ops,
                pf.batter_is_hot::int as batter_is_hot,
                pf.pitcher_l14_era,
                pf.pitcher_is_hot::int as pitcher_is_hot
            FROM models.pa_outcome_features pf
            JOIN models.pa_outcome_training_data t ON t.training_id = pf.training_id
            WHERE pf.game_pk = %s AND pf.season = %s
        """

        df = pd.read_sql(query, self.db, params=(game_pk, season))

        if len(df) == 0:
            return []

        results = []
        for _, row in df.iterrows():
            # Build feature dict
            features = {
                'inning_normalized': row['inning_normalized'],
                'is_top_half': row['is_top_half'],
                'outs': row['outs'],
                'base_state': row['base_state'],
                'run_diff_normalized': row['run_diff_normalized'],
                'leverage_index': row['leverage_index'],
                'is_high_leverage': row['is_high_leverage'],
                'matchup_score': row['matchup_score'],
                'is_platoon_advantage': row['is_platoon_advantage'],
                'batter_l14_ops': row['batter_l14_ops'],
                'batter_is_hot': row['batter_is_hot'],
                'pitcher_l14_era': row['pitcher_l14_era'],
                'pitcher_is_hot': row['pitcher_is_hot'],
            }

            pred = self.predict_pa(features)
            pred.update(
                {
                    'game_pk': row['game_pk'],
                    'at_bat_index': row['at_bat_index'],
                    'batter_id': row['batter_id'],
                    'pitcher_id': row['pitcher_id'],
                },
            )
            results.append(pred)

        return results

    def save_predictions(
        self, predictions: list[dict[str, Any]], model_version: str, season: int,
    ) -> bool:
        """Save predictions to database.

        Args:
            predictions: List of prediction results
            model_version: Model version string
            season: Season year

        Returns:
            True if successful
        """
        if self.db is None:
            return False

        try:
            with self.db.cursor() as cur:
                for pred in predictions:
                    probs = pred['probabilities']

                    cur.execute(
                        """INSERT INTO models.pa_outcome_predictions
                            (model_version, game_pk, season, at_bat_index,
                             inning, is_top, batter_id, pitcher_id,
                             prob_out, prob_walk, prob_single, prob_double,
                             prob_triple, prob_home_run,
                             confidence, entropy, expected_runs,
                             feature_snapshot)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                   %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (model_version, game_pk, at_bat_index)
                           DO UPDATE SET
                             prob_out = EXCLUDED.prob_out,
                             prob_walk = EXCLUDED.prob_walk,
                             prob_single = EXCLUDED.prob_single,
                             prob_double = EXCLUDED.prob_double,
                             prob_triple = EXCLUDED.prob_triple,
                             prob_home_run = EXCLUDED.prob_home_run,
                             confidence = EXCLUDED.confidence,
                             predicted_at = NOW()""",
                        (
                            model_version,
                            pred['game_pk'],
                            season,
                            pred['at_bat_index'],
                            1,  # inning - would be from features
                            True,  # is_top - would be from features
                            pred['batter_id'],
                            pred['pitcher_id'],
                            probs['out'],
                            probs['walk'],
                            probs['single'],
                            probs['double'],
                            probs['triple'],
                            probs['home_run'],
                            pred['confidence'],
                            0.0,  # entropy - would calculate from probs
                            pred['expected_runs'],
                            pred.get('features', {}),
                        ),
                    )
            self.db.commit()
            logger.info(f'Saved {len(predictions)} predictions')
            return True
        except Exception as e:
            logger.exception(f'Failed to save predictions: {e}')
            return False

    def get_top_predictions(
        self, game_states: list[dict[str, Any]], min_prob: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Get high-probability predictions for monitoring.

        Args:
            game_states: List of game states
            min_prob: Minimum probability threshold

        Returns:
            List of high-confidence predictions
        """
        results = []
        for state in game_states:
            pred = self.predict_pa(state)

            # Check for interesting predictions
            if pred['confidence'] >= min_prob:
                results.append(
                    {
                        'state': state,
                        'prediction': pred['predicted_outcome'],
                        'confidence': pred['confidence'],
                        'prob_hit': pred['prob_hit'],
                        'prob_home_run': pred['probabilities']['home_run'],
                    },
                )
            elif pred['probabilities']['home_run'] >= 0.15:
                results.append(
                    {
                        'state': state,
                        'prediction': 'home_run (threat)',
                        'confidence': pred['probabilities']['home_run'],
                        'prob_hit': pred['prob_hit'],
                        'prob_home_run': pred['probabilities']['home_run'],
                    },
                )

        return sorted(results, key=lambda x: x['confidence'], reverse=True)

    def get_model_info(self) -> dict[str, Any]:
        """Get model information."""
        info = {
            'model_type': self.model_type.value,
            'model_name': self.config.model_name,
            'version': self.config.version,
            'status': self.status.value,
            'is_trained': self.is_trained,
            'features': self._feature_names,
            'classes': self.CLASSES,
            'hyperparameters': self.config.hyperparameters,
        }

        if self.is_trained and self._model is not None:
            info['model_class'] = type(self._model).__name__
            info['feature_importance'] = self.get_feature_importance()

        return info
