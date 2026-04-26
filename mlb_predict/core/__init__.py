"""MLB Predict Core Module - Rich Results and Training

Phase 1.2: Rich Result Classes ✅ COMPLETE

Example:
    from mlb_predict.core import TrainResult, Residuals, Metrics
    
    result = TrainResult(
        model_id=123,
        model_name="my_model",
        config=config,
        train_metrics=Metrics(roc_auc=MetricValue(value=0.85)),
        val_metrics=Metrics(roc_auc=MetricValue(value=0.83)),
        # ...
    )
    
    # Analyze residuals
    residuals = result.residuals
    stats = residuals.analyze()
    residuals.plot_residuals()
    
    # Get top features
    top_features = result.get_best_features(n=20)
    
    # Compare to another model
    comparison = result.compare_to(other_result)
"""

__version__ = '0.1.0'

# Phase 1.2: Rich Result Classes - COMPLETE
from mlb_predict.core.results import (
    FeatureImportance,
    Metrics,
    MetricValue,
    PredictionRecord,
    PredictResult,
    Residuals,
    TrainResult,
    ValidationCurve,
)


# TODO: Phase 2.1 - ModelTrainer
# from mlb_predict.core.trainer import ModelTrainer

# TODO: Phase 2.2 - Plugin System
# from mlb_predict.core.plugin import PluginModel, PluginRegistry

# TODO: Phase 2.4 - Experiment Runner
# from mlb_predict.core.experiment import Experiment

__all__ = [
    # Rich Results (Phase 1.2)
    'MetricValue',
    'Metrics',
    'ValidationCurve',
    'FeatureImportance',
    'Residuals',
    'PredictionRecord',
    'PredictResult',
    'TrainResult',
]
