"""Win Probability Model implementation.

Binary classification model to predict home team win probability
based on game state: inning, score differential, base runners, outs.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-28
"""

import logging
from typing import Any

import numpy as np

from .base import ModelConfig, ModelType, SklearnBaseModel, TrainingConfig


logger = logging.getLogger(__name__)


class WinProbabilityModel(SklearnBaseModel):
    """Model to predict home team win probability.

    This is a binary classification model that predicts the probability
    of the home team winning given the current game state.

    Features used:
    - Game state: inning, outs, base_state, score differential
    - Run Expectancy: expected runs for remainder of inning
    - Leverage Index: importance of current situation
    - Historical rates for this game situation

    Example:
        >>> model = WinProbabilityModel(db_connection=conn)
        >>> config = TrainingConfig(train_seasons=[2024, 2025])
        >>> result = model.train(config)
        >>>
        >>> # Predict win probability
        >>> prob = model.predict_win_probability(
        ...     {
        ...         'inning': 9,
        ...         'is_top': False,
        ...         'outs': 2,
        ...         'base_state': 0,
        ...         'score_diff': 1,
        ...         'run_expectancy': 0.095,
        ...         'leverage_index': 2.5,
        ...     }
        ... )
        >>> print(f'Home team win probability: {prob:.1%}')
    """

    DEFAULT_FEATURES = [
        'inning_normalized',
        'is_top_half',
        'outs',
        'base_state',
        'score_diff',
        'score_diff_abs',
        'is_close_game',
        'run_expectancy',
        'run_expectancy_diff',
        'leverage_index',
        'is_high_leverage',
        'is_late_game',
        'is_extra_innings',
        'historical_home_win_rate',
    ]

    def __init__(self, db_connection=None, config: ModelConfig | None = None) -> None:
        """Initialize Win Probability Model.

        Args:
            db_connection: Database connection
            config: Model configuration
        """
        super().__init__(db_connection, config)
        self.model_type = ModelType.WIN_PROBABILITY

    def _default_config(self) -> ModelConfig:
        """Return default configuration."""
        return ModelConfig(
            model_type=ModelType.WIN_PROBABILITY,
            model_name='win_probability_v1',
            description='Home team win probability based on game state',
            features=self.DEFAULT_FEATURES,
            algorithm='xgboost',
            hyperparameters={
                'n_estimators': 500,
                'max_depth': 6,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'objective': 'binary:logistic',
                'eval_metric': 'logloss',
            },
        )

    def predict_win_probability(self, game_state: dict[str, Any]) -> float:
        """Predict home team win probability.

        Args:
            game_state: Dictionary with game state features

        Returns:
            Probability of home team winning (0.0 to 1.0)
        """
        if self.model is None:
            logger.warning('Model not trained, using heuristic prediction')
            return self._heuristic_prediction(game_state)

        try:
            features = self._extract_features(game_state)
            X = np.array([features])
            prob = self.model.predict_proba(X)[0][1]  # Probability of class 1 (home win)
            return float(prob)
        except Exception as e:
            logger.exception(f'Prediction failed: {e}')
            return self._heuristic_prediction(game_state)

    def _heuristic_prediction(self, game_state: dict[str, Any]) -> float:
        """Simple heuristic when model is not available.

        Uses historical win expectancy based on inning, score, and base-out state.
        """
        inning = game_state.get('inning', 1)
        is_top = game_state.get('is_top', True)
        outs = game_state.get('outs', 0)
        score_diff = game_state.get('score_diff', 0)  # Home - Away
        base_state = game_state.get('base_state', 0)

        # Start with 50%
        prob = 0.5

        # Score differential has huge impact
        # Late in game, score diff matters more
        inning_weight = min(1.0, inning / 9.0)
        prob += inning_weight * (score_diff * 0.05)

        # Being at bat (bottom half) is advantage
        if not is_top:
            prob += 0.02 * inning_weight

        # Base-out state adjustment
        # More runners = more chance to score
        runners_advantage = {0: 0, 1: 0.03, 2: 0.05, 3: 0.08, 4: 0.06, 5: 0.09, 6: 0.10, 7: 0.12}
        prob += runners_advantage.get(base_state, 0) * inning_weight * (1 - outs / 3)

        # Clamp to valid range
        return max(0.01, min(0.99, prob))

    def _extract_features(self, game_state: dict[str, Any]) -> list[float]:
        """Extract features from game state.

        Args:
            game_state: Dictionary with game state

        Returns:
            List of feature values
        """
        inning = game_state.get('inning', 1)
        is_top = game_state.get('is_top', True)
        outs = game_state.get('outs', 0)
        base_state = game_state.get('base_state', 0)
        score_diff = game_state.get('score_diff', 0)
        run_expectancy = game_state.get('run_expectancy', 0.5)
        leverage_index = game_state.get('leverage_index', 1.0)

        return [
            inning / 9.0,  # inning_normalized
            1.0 if is_top else 0.0,  # is_top_half
            float(outs),
            float(base_state),
            float(score_diff),
            abs(float(score_diff)),  # score_diff_abs
            1.0 if abs(score_diff) <= 1 else 0.0,  # is_close_game
            float(run_expectancy),
            float(run_expectancy) - 0.5,  # run_expectancy_diff
            float(leverage_index),
            1.0 if leverage_index > 1.5 else 0.0,  # is_high_leverage
            1.0 if inning >= 7 else 0.0,  # is_late_game
            1.0 if inning > 9 else 0.0,  # is_extra_innings
            0.54,  # historical_home_win_rate (MLB average)
        ]


    def _prepare_training_data(
        self, config: TrainingConfig,
    ) -> tuple[np.ndarray, np.ndarray] | None:
        """Prepare training data from historical games.

        Args:
            config: Training configuration

        Returns:
            Tuple of (X, y) arrays or None if failed
        """
        if self.db is None:
            logger.error('No database connection for training')
            return None

        try:
            import pandas as pd

            # Query historical game states and outcomes
            query = """
                SELECT
                    e.inning,
                    e.is_top,
                    e.outs,
                    e.base_state,
                    e.score_home - e.score_away as score_diff,
                    g.winner_home,
                    e.run_expectancy,
                    e.leverage_index
                FROM core.events e
                JOIN core.games g ON e.game_id = g.game_id
                WHERE g.season = ANY(%s)
                  AND e.inning <= 12  -- Exclude very long extra inning games
                  AND g.game_type = 'R'  -- Regular season only for training
                ORDER BY RANDOM()
                LIMIT 100000
            """
            df = pd.read_sql(query, self.db, params=(config.train_seasons,))

            if len(df) < 1000:
                logger.error(f'Insufficient training data: {len(df)} rows')
                return None

            # Extract features
            X = []
            for _, row in df.iterrows():
                game_state = {
                    'inning': row['inning'],
                    'is_top': row['is_top'],
                    'outs': row['outs'],
                    'base_state': row['base_state'],
                    'score_diff': row['score_diff'],
                    'run_expectancy': row.get('run_expectancy', 0.5),
                    'leverage_index': row.get('leverage_index', 1.0),
                }
                X.append(self._extract_features(game_state))

            X = np.array(X)
            y = df['winner_home'].values.astype(int)

            logger.info(f'Prepared {len(X)} training samples')
            return X, y

        except Exception as e:
            logger.exception(f'Failed to prepare training data: {e}')
            return None

    def train(self, config: TrainingConfig) -> Any:
        """Train the win probability model.

        Args:
            config: Training configuration with train_seasons

        Returns:
            ModelResult with training metrics
        """
        import xgboost as xgb
        from sklearn.metrics import log_loss, roc_auc_score
        from sklearn.model_selection import train_test_split

        result = self._prepare_result()

        # Prepare data
        data = self._prepare_training_data(config)
        if data is None:
            result.error_message = 'Failed to prepare training data'
            return result

        X, y = data
        result.training_rows = len(X)

        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y,
        )

        # Train model
        try:
            model = xgb.XGBClassifier(**self.config.hyperparameters)
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False,
            )

            self.model = model

            # Calculate metrics
            y_pred_proba = model.predict_proba(X_val)[:, 1]
            result.validation_auc = roc_auc_score(y_val, y_pred_proba)
            result.log_loss = log_loss(y_val, y_pred_proba)
            result.success = True

            logger.info(
                f'Training complete: AUC={result.validation_auc:.4f}, '
                f'LogLoss={result.log_loss:.4f}',
            )

        except Exception as e:
            result.error_message = f'Training failed: {e}'
            logger.exception(result.error_message)

        return result
