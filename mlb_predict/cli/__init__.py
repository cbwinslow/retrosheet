"""MLB Prediction CLI Module.

Provides command-line interface for the framework.

Usage:
    mlb-predict --help
    mlb-predict train --config configs/xgboost.yaml
    mlb-predict experiment --compare-families xgboost lightgbm --target swing_decision
"""

from mlb_predict.cli.main import create_parser, main


__all__ = ['create_parser', 'main']
