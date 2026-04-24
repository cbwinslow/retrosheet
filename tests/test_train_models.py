"""Unit tests for the model training pipeline utilities.

These tests focus on the pure-Python helper functions in
[`scripts/train_models.py`](scripts/train_models.py) and the feature column
resolution logic in [`scripts/sweep_hyperparameters.py`](scripts/sweep_hyperparameters.py).
Database-related functions are deliberately not exercised - they require a
PostgreSQL instance - and are covered by integration tests elsewhere.
"""

import pandas as pd

from scripts.model_training import sweep_hyperparameters, train_models


def test_preprocessor_structure() -> None:
    """Ensure the preprocessor returns a ColumnTransformer with expected sub-pipelines.

    The function should create two transformers named ``numeric`` and ``categorical``
    with the appropriate imputer (and optional scaler for numeric data).
    """
    numeric_features = ['num1', 'num2']
    categorical_features = ['cat1']
    # With scaling enabled
    ct = train_models.preprocessor(
        numeric_features=numeric_features,
        categorical_features=categorical_features,
        scale_numeric=True,
    )
    # The ColumnTransformer stores transformers in ``transformers_`` after fit;
    # however, we can inspect the ``transformers`` attribute directly.
    transformer_names = [name for name, _, _ in ct.transformers]
    assert set(transformer_names) == {'numeric', 'categorical'}

    # Verify that the numeric pipeline contains both imputer and scaler steps.
    numeric_pipeline = ct.transformers[0][1]
    step_names = [name for name, _ in numeric_pipeline.steps]
    assert 'imputer' in step_names
    assert 'scaler' in step_names

    # Verify that the categorical pipeline contains imputer and one-hot encoder.
    categorical_pipeline = ct.transformers[1][1]
    cat_step_names = [name for name, _ in categorical_pipeline.steps]
    assert 'imputer' in cat_step_names
    assert 'onehot' in cat_step_names


def test_build_models_returns_pipelines() -> None:
    """Check that ``build_models`` creates two pipelines with expected estimators."""
    numeric = ['num']
    categorical = []
    models = train_models.build_models(numeric_features=numeric, categorical_features=categorical)
    assert set(models.keys()) == {'logistic_regression', 'hist_gradient_boosting'}
    # Each value should be a sklearn Pipeline instance.
    for name, pipeline in models.items():
        assert hasattr(pipeline, 'fit') and hasattr(pipeline, 'predict_proba')
        # The final step should be the estimator matching the key.
        estimator = pipeline.steps[-1][1]
        if name == 'logistic_regression':
            from sklearn.linear_model import LogisticRegression

            assert isinstance(estimator, LogisticRegression)
        else:
            from sklearn.ensemble import HistGradientBoostingClassifier

            assert isinstance(estimator, HistGradientBoostingClassifier)


def test_metrics_for_computes_expected_keys() -> None:
    """Run ``metrics_for`` on a tiny synthetic dataset and verify output shape.

    The function should return a dictionary containing numeric metric values.
    """
    # Create a simple binary classification problem.
    df = pd.DataFrame(
        {
            'num': [0.1, 0.4, 0.35, 0.8],
            'cat': ['A', 'B', 'A', 'B'],
            'target': [0, 1, 0, 1],
        },
    )
    # Build a minimal logistic regression model.
    model = train_models.build_models(numeric_features=['num'], categorical_features=['cat'])[
        'logistic_regression'
    ]
    model.fit(df[['num', 'cat']], df['target'])
    metrics = train_models.metrics_for(
        model,
        df,
        numeric_features=['num'],
        categorical_features=['cat'],
    )
    # Expected keys
    expected_keys = {'rows', 'log_loss', 'roc_auc', 'brier_score', 'accuracy'}
    assert set(metrics.keys()) == expected_keys
    # Basic sanity checks on types and ranges.
    assert metrics['rows'] == len(df)
    assert 0.0 <= metrics['accuracy'] <= 1.0
    assert metrics['log_loss'] >= 0.0
    assert metrics['brier_score'] >= 0.0
    assert 0.0 <= metrics['roc_auc'] <= 1.0


def test_feature_columns_mapping() -> None:
    """Validate that ``feature_columns`` resolves to the correct feature lists.

    The function should delegate to the constants defined in ``train_models``.
    """
    # Game target with enriched features
    num, cat = sweep_hyperparameters.feature_columns(
        target_id='game_home_win', feature_set='enriched',
    )
    assert num == train_models.GAME_ENRICHED_NUMERIC_FEATURES
    assert cat == train_models.GAME_ENRICHED_CATEGORICAL_FEATURES

    # Plate appearance target with basic features
    num2, cat2 = sweep_hyperparameters.feature_columns(
        target_id='pa_batter_hit', feature_set='basic',
    )
    assert num2 == train_models.PA_NUMERIC_FEATURES
    assert cat2 == train_models.PA_CATEGORICAL_FEATURES

    # Unknown target should raise a ValueError.
    import pytest

    with pytest.raises(ValueError):
        sweep_hyperparameters.feature_columns(target_id='unknown', feature_set='basic')
