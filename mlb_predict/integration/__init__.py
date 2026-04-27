"""MLB Predict Integration Module.

Provides bridges between legacy scripts and new framework.

Usage:
    from mlb_predict.integration import LegacyCompatibleTrainer

    trainer = LegacyCompatibleTrainer()
    result = trainer.train_legacy_style(
        target_id='swing_outcome',
        feature_set='advanced',
        min_season=2020,
        max_season=2024,
        train_through=2022,
    )
    print(result.summary())
"""

from mlb_predict.integration.legacy_bridge import (
    LEGACY_TARGET_MAPPING,
    LEGACY_TO_FRAMEWORK_FEATURES,
    LegacyCompatibleTrainer,
    convert_legacy_cli_args_to_config,
    convert_legacy_metrics_to_framework,
    create_config_from_legacy_args,
    create_train_result_from_legacy,
    get_legacy_feature_lists,
    print_framework_result_legacy_style,
)


__all__ = [
    'LEGACY_TARGET_MAPPING',
    'LEGACY_TO_FRAMEWORK_FEATURES',
    'LegacyCompatibleTrainer',
    'convert_legacy_cli_args_to_config',
    'convert_legacy_metrics_to_framework',
    'create_config_from_legacy_args',
    'create_train_result_from_legacy',
    'get_legacy_feature_lists',
    'print_framework_result_legacy_style',
]
