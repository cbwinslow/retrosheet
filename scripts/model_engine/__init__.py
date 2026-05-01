"""Factory for selecting a model engine.

The project already has a pure-CPU logistic-regression trainer.  This module
adds a thin abstraction layer so that we can optionally use a GPU-accelerated
implementation (XGBoost, PyTorch, etc.) without changing the rest of the code
base.

Usage::

    from scripts.model_engine import get_engine

    engine = get_engine('auto')  # picks the fastest available
    engine.fit(X_train, y_train)
    preds = engine.predict_proba(X_val)

The factory prefers XGBoost-GPU if CUDA is available, then a PyTorch NN, and
finally falls back to the original logistic-regression implementation.
"""

import torch

from .logistic_regression import LogisticRegressionEngine
from .pytorch_nn import PyTorchEngine
from .xgboost_gpu import XGBoostGPUEngine


def get_engine(preferred: str = 'auto'):
    """Return an instantiated :class:`ModelEngine`.

    Parameters
    ----------
    preferred: str, optional
        "auto" (default) - pick the fastest available implementation.
        "xgboost" - force XGBoost GPU (will raise if CUDA not present).
        "pytorch" - force PyTorch NN (uses CPU if no CUDA).
        "logreg" - force the original logistic-regression engine.
    """

    if preferred == 'auto':
        # Prefer XGBoost GPU if CUDA is present
        try:
            import xgboost as xgb  # noqa: F401

            if torch.cuda.is_available():
                return XGBoostGPUEngine()
        except Exception:
            pass

        # Next try PyTorch (will use GPU automatically if available)
        if torch.cuda.is_available():
            return PyTorchEngine()

        # Fallback to pure CPU logistic regression
        return LogisticRegressionEngine()

    if preferred == 'xgboost':
        return XGBoostGPUEngine()
    if preferred == 'pytorch':
        return PyTorchEngine()
    if preferred == 'logreg':
        return LogisticRegressionEngine()

    msg = f'Unknown engine request: {preferred}'
    raise ValueError(msg)
