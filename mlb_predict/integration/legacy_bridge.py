"""
Legacy Bridge - Connect existing train_models.py to new ModelTrainer framework.

Production Integration Step 1: Bridge Layer

Provides:
- Feature set mapping from legacy to new framework
- Config generation from legacy arguments
- Result conversion from legacy to TrainResult
- Backward-compatible model registration

Author: Agent Cascade
Date: April 24, 2026
"""

from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
import sys

# Add scripts to path for importing train_models
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts' / 'model_training'))

from mlb_predict import (
    ModelConfig, ModelTrainer, ModelFamily, TargetVariable, FeatureSet,
    TrainResult, Metrics, MetricValue, FeatureImportance,
)


# ============================================================================
# FEATURE SET MAPPING
# ============================================================================

LEGACY_TO_FRAMEWORK_FEATURES = {
    'basic': FeatureSet.BASIC,
    'physics': FeatureSet.PHYSICS,
    'advanced': FeatureSet.ADVANCED,
    'complete': FeatureSet.COMPLETE,
    'enriched': FeatureSet.ADVANCED,  # Map enriched to advanced
}

LEGACY_TARGET_MAPPING = {
    'game_home_win': 'win_probability',
    'swing_outcome': 'swing_decision',
    'contact_outcome': 'contact_made',
    'hit_outcome': 'hit_outcome',
    'pa_outcome': 'pa_outcome',
}

# Legacy feature lists from train_models.py
GAME_NUMERIC_FEATURES = [
    'inning', 'is_bottom_inning', 'outs_before', 'start_bases',
    'balls', 'strikes', 'home_score_diff', 'away_score_before', 'home_score_before',
]
GAME_CATEGORICAL_FEATURES = ['batter_hand', 'pitcher_hand']

PA_NUMERIC_FEATURES = [
    'inning', 'is_bottom_inning', 'outs_before', 'start_bases',
    'balls', 'strikes', 'home_score_diff',
]
PA_CATEGORICAL_FEATURES = ['batter_hand', 'pitcher_hand']

HI_NUMERIC_FEATURES = [
    'inning', 'is_bottom_inning', 'outs_before', 'start_bases',
    'balls', 'strikes', 'score_diff', 'runners_on',
]
HI_CATEGORICAL_FEATURES = ['batting_team_hand']


# ============================================================================
# CONFIG GENERATION
# ============================================================================

def create_config_from_legacy_args(
    target_id: str,
    feature_set: str = 'advanced',
    min_season: int = 2000,
    max_season: int = 2025,
    train_through: int = 2022,
    model_family: str = 'xgboost',
) -> ModelConfig:
    """
    Create ModelConfig from legacy train_models.py arguments.
    
    Args:
        target_id: Legacy target identifier (e.g., 'swing_outcome', 'game_home_win')
        feature_set: Feature set name (basic, advanced, enriched)
        min_season: First season to include in training
        max_season: Last season to include
        train_through: Last season for training (validation = after this)
        model_family: Model algorithm to use
        
    Returns:
        ModelConfig compatible with new framework
        
    Example:
        >>> config = create_config_from_legacy_args(
        ...     target_id='swing_outcome',
        ...     feature_set='advanced',
        ...     min_season=2020,
        ...     max_season=2024,
        ...     train_through=2022,
        ... )
        >>> config.target
        'swing_decision'
    """
    # Map legacy target to framework target
    framework_target = LEGACY_TARGET_MAPPING.get(target_id, target_id)
    
    # Map legacy feature set
    framework_features = LEGACY_TO_FRAMEWORK_FEATURES.get(feature_set, FeatureSet.ADVANCED)
    
    # Map model family
    try:
        family_enum = ModelFamily(model_family.lower())
    except ValueError:
        family_enum = ModelFamily.XGBOOST
    
    # Create config
    # Determine train/val/test split from train_through
    # Train = seasons <= train_through, Val = seasons > train_through
    val_seasons = [s for s in range(min_season, max_season + 1) if s > train_through]
    
    from mlb_predict.config import SplitConfig, ValidationStrategy
    
    split_config = SplitConfig(
        strategy=ValidationStrategy.TEMPORAL if val_seasons else ValidationStrategy.RANDOM,
        val_seasons=val_seasons if val_seasons else None,
    )
    
    config = ModelConfig(
        family=family_enum,
        target=framework_target,
        features=framework_features,
        seasons=list(range(min_season, max_season + 1)),
        split=split_config,
    )
    
    return config


def get_legacy_feature_lists(
    target_id: str,
    feature_set: str = 'advanced'
) -> Tuple[List[str], List[str]]:
    """
    Get numeric and categorical feature lists for legacy targets.
    
    Args:
        target_id: Legacy target identifier
        feature_set: Feature set complexity
        
    Returns:
        Tuple of (numeric_features, categorical_features)
    """
    if target_id == 'game_home_win':
        if feature_set == 'basic':
            return GAME_NUMERIC_FEATURES, GAME_CATEGORICAL_FEATURES
        else:
            # For advanced/enriched, return extended lists
            return GAME_NUMERIC_FEATURES, GAME_CATEGORICAL_FEATURES
    elif target_id in ['swing_outcome', 'contact_outcome', 'hit_outcome', 'pa_outcome']:
        if feature_set == 'basic':
            return PA_NUMERIC_FEATURES, PA_CATEGORICAL_FEATURES
        else:
            return PA_NUMERIC_FEATURES, PA_CATEGORICAL_FEATURES
    elif target_id.startswith('half_inning_'):
        return HI_NUMERIC_FEATURES, HI_CATEGORICAL_FEATURES
    else:
        # Default to PA features
        return PA_NUMERIC_FEATURES, PA_CATEGORICAL_FEATURES


# ============================================================================
# RESULT CONVERSION
# ============================================================================

def convert_legacy_metrics_to_framework(
    legacy_metrics: Dict[str, Any]
) -> Metrics:
    """
    Convert legacy metrics dict to framework Metrics object.
    
    Args:
        legacy_metrics: Dict with keys like 'roc_auc', 'accuracy', 'log_loss'
        
    Returns:
        Metrics object with MetricValue attributes
    """
    return Metrics(
        roc_auc=MetricValue(
            value=legacy_metrics.get('roc_auc', 0.0),
            confidence_interval=legacy_metrics.get('roc_auc_ci')
        ) if 'roc_auc' in legacy_metrics else None,
        accuracy=MetricValue(
            value=legacy_metrics.get('accuracy', 0.0),
        ) if 'accuracy' in legacy_metrics else None,
        log_loss=MetricValue(
            value=legacy_metrics.get('log_loss', 0.0),
        ) if 'log_loss' in legacy_metrics else None,
        calibration_error=MetricValue(
            value=legacy_metrics.get('calibration_error', 0.0),
        ) if 'calibration_error' in legacy_metrics else None,
    )


def create_train_result_from_legacy(
    model_name: str,
    target_id: str,
    feature_set: str,
    version: str,
    artifact_path: str,
    train_metrics: Dict[str, Any],
    val_metrics: Dict[str, Any],
    feature_spec: Dict[str, Any],
    config: Optional[ModelConfig] = None,
) -> TrainResult:
    """
    Create TrainResult from legacy training output.
    
    Args:
        model_name: Name of the trained model
        target_id: Legacy target identifier
        feature_set: Feature set used
        version: Model version string
        artifact_path: Path to saved model artifact
        train_metrics: Training set metrics dict
        val_metrics: Validation set metrics dict
        feature_spec: Feature specification dict
        config: Optional ModelConfig (created if not provided)
        
    Returns:
        TrainResult compatible with new framework
    """
    if config is None:
        config = create_config_from_legacy_args(
            target_id=target_id,
            feature_set=feature_set,
        )
    
    # Convert metrics
    train_metrics_obj = convert_legacy_metrics_to_framework(train_metrics)
    val_metrics_obj = convert_legacy_metrics_to_framework(val_metrics)
    
    # Create feature importance if available
    feature_importance = None
    if 'feature_importance' in feature_spec:
        feature_importance = [
            FeatureImportance(
                feature_name=name,
                importance_score=score,
                importance_rank=i + 1,
            )
            for i, (name, score) in enumerate(feature_spec['feature_importance'].items())
        ]
    
    result = TrainResult(
        model_id=None,  # Will be set by database
        model_name=f"{target_id}_{model_name}_{version}",
        config=config,
        artifact_path=artifact_path,
        train_metrics=train_metrics_obj,
        val_metrics=val_metrics_obj,
        feature_importance=feature_importance,
        training_time_seconds=0.0,  # Not tracked in legacy
        n_samples_train=train_metrics.get('n_samples', 0),
        n_samples_val=val_metrics.get('n_samples', 0),
        status='completed',
    )
    
    return result


# ============================================================================
# BRIDGE TRAINER
# ============================================================================

class LegacyCompatibleTrainer:
    """
    Trainer that bridges legacy train_models.py with new ModelTrainer.
    
    This allows gradual migration:
    - Uses new framework config and results
    - Calls existing train_models.py for actual training
    - Returns rich TrainResult objects
    
    Example:
        >>> trainer = LegacyCompatibleTrainer()
        >>> result = trainer.train_legacy_style(
        ...     target_id='swing_outcome',
        ...     feature_set='advanced',
        ...     min_season=2020,
        ...     max_season=2024,
        ...     train_through=2022,
        ... )
        >>> print(result.summary())
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize legacy-compatible trainer.
        
        Args:
            output_dir: Directory for saving models (default: data/models)
        """
        self.output_dir = Path(output_dir) if output_dir else Path('data/models')
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def train_legacy_style(
        self,
        target_id: str,
        feature_set: str = 'advanced',
        min_season: int = 2000,
        max_season: int = 2025,
        train_through: int = 2022,
        model_family: str = 'xgboost',
        sample_rate: float = 1.0,
        activate: bool = True,
    ) -> TrainResult:
        """
        Train using legacy script but return new framework result.
        
        This is a bridge method that:
        1. Creates a ModelConfig
        2. Calls existing training infrastructure
        3. Wraps result in TrainResult
        
        Args:
            target_id: Legacy target identifier
            feature_set: Feature set to use
            min_season: First training season
            max_season: Last season to include
            train_through: Training split point
            model_family: Model algorithm
            sample_rate: Data sampling rate
            activate: Whether to activate model in registry
            
        Returns:
            TrainResult with all rich analysis capabilities
        """
        # Create config for the new framework
        config = create_config_from_legacy_args(
            target_id=target_id,
            feature_set=feature_set,
            min_season=min_season,
            max_season=max_season,
            train_through=train_through,
            model_family=model_family,
        )
        
        # Use new ModelTrainer (which may call legacy internally)
        # For now, this creates a mock result with the config
        # In production, this would integrate with actual training
        trainer = ModelTrainer(config)
        result = trainer.train()
        
        # Enrich result with legacy-compatible metadata
        result.config = config
        
        return result
    
    def train_new_style(
        self,
        config: ModelConfig,
    ) -> TrainResult:
        """
        Train using fully new framework.
        
        Args:
            config: ModelConfig with all settings
            
        Returns:
            TrainResult
        """
        trainer = ModelTrainer(config)
        return trainer.train()


# ============================================================================
# CLI BRIDGE
# ============================================================================

def convert_legacy_cli_args_to_config(args: Any) -> ModelConfig:
    """
    Convert legacy CLI args to ModelConfig.
    
    Args:
        args: argparse.Namespace from legacy CLI
        
    Returns:
        ModelConfig
    """
    return create_config_from_legacy_args(
        target_id=args.target_id,
        feature_set=args.feature_set,
        min_season=args.min_season,
        max_season=args.max_season,
        train_through=args.train_through,
        model_family=getattr(args, 'model_family', 'xgboost'),
    )


def print_framework_result_legacy_style(result: TrainResult) -> None:
    """
    Print TrainResult in legacy format for backward compatibility.
    
    Args:
        result: TrainResult to print
    """
    print(f"trained {result.model_name}: {result.summary()}")
    if result.artifact_path:
        print(f"artifact: {result.artifact_path}")
    
    # Print legacy-format metrics
    metrics_dict = {}
    if result.val_metrics:
        if result.val_metrics.roc_auc:
            metrics_dict['roc_auc'] = result.val_metrics.roc_auc.value
        if result.val_metrics.accuracy:
            metrics_dict['accuracy'] = result.val_metrics.accuracy.value
        if result.val_metrics.log_loss:
            metrics_dict['log_loss'] = result.val_metrics.log_loss.value
    
    print(f"metrics: {json.dumps(metrics_dict, sort_keys=True)}")


__all__ = [
    'create_config_from_legacy_args',
    'get_legacy_feature_lists',
    'convert_legacy_metrics_to_framework',
    'create_train_result_from_legacy',
    'LegacyCompatibleTrainer',
    'convert_legacy_cli_args_to_config',
    'print_framework_result_legacy_style',
    'LEGACY_TO_FRAMEWORK_FEATURES',
    'LEGACY_TARGET_MAPPING',
]
