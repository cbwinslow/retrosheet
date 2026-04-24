"""
Model Trainer that wraps existing training infrastructure.

Integrates with:
- scripts/model_training/train_models.py
- scripts/model_training/train_pa_outcome_distribution.py  
- models.model_registry table
- Existing feature marts
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import psycopg2
from sqlalchemy import create_engine, text

# Add scripts path to import existing modules
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts' / 'model_training'))

# Import existing training functions
from train_models import (
    train as train_game_pa_models,
    database_kwargs,
    GAME_NUMERIC_FEATURES,
    GAME_CATEGORICAL_FEATURES,
    PA_NUMERIC_FEATURES,
    PA_CATEGORICAL_FEATURES,
    PA_ENRICHED_NUMERIC_FEATURES,
    PA_ENRICHED_CATEGORICAL_FEATURES,
    PA_ADVANCED_NUMERIC_FEATURES,
    PA_ADVANCED_CATEGORICAL_FEATURES,
)
from train_pa_outcome_distribution import (
    train as train_pa_distribution,
    BASIC_NUMERIC_FEATURES,
    BASIC_CATEGORICAL_FEATURES,
    ADVANCED_NUMERIC_FEATURES,
    ADVANCED_CATEGORICAL_FEATURES,
)


class ModelTrainer:
    """
    Unified trainer that wraps existing scripts and enables custom models.
    
    Example:
        # Train existing model types
        trainer = ModelTrainer({
            'target': 'pa_batter_hit',
            'feature_set': 'advanced',
            'seasons': [2020, 2021, 2022, 2023]
        })
        result = trainer.train()
        
        # Register and train custom model
        trainer.register_plugin('my_model', MyCustomModel)
        result = trainer.train(model_type='my_model')
    """
    
    # Feature sets from existing code
    FEATURE_SETS = {
        'game_basic': {
            'numeric': GAME_NUMERIC_FEATURES,
            'categorical': GAME_CATEGORICAL_FEATURES,
        },
        'pa_basic': {
            'numeric': PA_NUMERIC_FEATURES,
            'categorical': PA_CATEGORICAL_FEATURES,
        },
        'pa_enriched': {
            'numeric': PA_ENRICHED_NUMERIC_FEATURES,
            'categorical': PA_ENRICHED_CATEGORICAL_FEATURES,
        },
        'pa_advanced': {
            'numeric': PA_ADVANCED_NUMERIC_FEATURES,
            'categorical': PA_ADVANCED_CATEGORICAL_FEATURES,
        },
        'pa_distribution_basic': {
            'numeric': BASIC_NUMERIC_FEATURES,
            'categorical': BASIC_CATEGORICAL_FEATURES,
        },
        'pa_distribution_advanced': {
            'numeric': ADVANCED_NUMERIC_FEATURES,
            'categorical': ADVANCED_CATEGORICAL_FEATURES,
        },
    }
    
    # Target types and their training functions
    TARGET_TYPES = {
        'game_home_win': 'game',
        'pa_batter_hit': 'pa_binary',
        'pa_batter_walk': 'pa_binary',
        'pa_batter_strikeout': 'pa_binary',
        'pa_batter_home_run': 'pa_binary',
        'pa_batter_reach_base': 'pa_binary',
        'pa_batter_extra_base_hit': 'pa_binary',
        'pa_outcome_distribution': 'pa_multiclass',
        'half_inning_any_run': 'half_inning',
    }
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.target = config.get('target', 'pa_batter_hit')
        self.feature_set = config.get('feature_set', 'pa_advanced')
        self.seasons = config.get('seasons', [2020, 2021, 2022, 2023])
        self.train_through = config.get('train_through', max(self.seasons) - 1)
        self.sample_rate = config.get('sample_rate', 1.0)
        self.model_family = config.get('model_family', 'xgboost')
        self.experiment_id = config.get('experiment_id')
        
        # Plugin registry for custom models
        self._plugins: Dict[str, Callable] = {}
        
        # Database connection
        self._db_kwargs = database_kwargs()
    
    @classmethod
    def from_config(cls, config_path: str) -> 'ModelTrainer':
        """Load trainer from YAML config file."""
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
        return cls(config)
    
    def register_plugin(self, name: str, model_class: Callable):
        """
        Register a custom model plugin.
        
        The model_class must implement:
        - fit(X, y, **kwargs)
        - predict_proba(X) 
        - predict(X)
        - save(path)
        - load(path) (class method or static)
        """
        self._plugins[name] = model_class
        self._log('INFO', f'Registered plugin: {name}')
    
    def train(self, model_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute training using existing infrastructure.
        
        Args:
            model_type: 'logistic_regression', 'hist_gradient_boosting', 'xgboost',
                       'lightgbm', 'catboost', or registered plugin name
        
        Returns:
            Dict with training results, metrics, artifact paths
        """
        model_type = model_type or self.model_family
        target_type = self.TARGET_TYPES.get(self.target, 'unknown')
        
        self._log('INFO', f'Starting training: {self.target} with {model_type}')
        
        # Check if it's a custom plugin
        if model_type in self._plugins:
            return self._train_plugin(model_type)
        
        # Use existing training infrastructure
        if target_type == 'pa_multiclass':
            return self._train_pa_distribution(model_type)
        else:
            return self._train_game_pa(model_type)
    
    def _train_game_pa(self, model_type: str) -> Dict[str, Any]:
        """Wrap existing train_models.py for game/PA binary targets."""
        # Build args namespace matching train_models.py expectations
        class Args:
            target_id = self.target
            feature_set = self.feature_set.replace('pa_', '').replace('game_', '')
            min_season = min(self.seasons)
            max_season = max(self.seasons)
            train_through = self.train_through
            sample_rate = self.sample_rate
            no_activate = False
        
        args = Args()
        
        # Log experiment start
        self._log('INFO', f'Calling train_models.train with args: {vars(args)}')
        
        try:
            # Call existing training function
            train_game_pa_models(args)
            
            # Get results from registry
            result = self._get_latest_model_result()
            self._log('INFO', f'Training completed: {result}')
            return result
            
        except Exception as e:
            self._log('ERROR', f'Training failed: {str(e)}')
            raise
    
    def _train_pa_distribution(self, model_type: str) -> Dict[str, Any]:
        """Wrap existing train_pa_outcome_distribution.py."""
        # Map model_family to args
        model_type_map = {
            'hist_gradient_boosting': 'hist_gradient_boosting',
            'xgboost': 'xgboost',
            'lightgbm': 'lightgbm',
            'catboost': 'catboost',
            'logistic_regression': 'logistic_regression',
        }
        
        class Args:
            min_season = min(self.seasons)
            max_season = max(self.seasons)
            train_through = self.train_through
            sample_rate = self.sample_rate
            feature_set = self.feature_set.replace('pa_distribution_', '')
            target_taxonomy = 'granular'
            model_type = model_type_map.get(model_type, 'xgboost')
            no_activate = False
            min_class_rows = 100
            exclude_2020 = False
            downweight_2020 = False
            season_half_life = 0
            recent_window = None
        
        args = Args()
        
        self._log('INFO', f'Calling train_pa_outcome_distribution.train with args')
        
        try:
            train_pa_distribution(args)
            result = self._get_latest_model_result()
            self._log('INFO', f'Training completed: {result}')
            return result
        except Exception as e:
            self._log('ERROR', f'Training failed: {str(e)}')
            raise
    
    def _train_plugin(self, plugin_name: str) -> Dict[str, Any]:
        """Train a custom plugin model."""
        model_class = self._plugins[plugin_name]
        
        # Load data using existing patterns
        X_train, y_train, X_val, y_val = self._load_data()
        
        # Instantiate and train
        model = model_class(self.config)
        
        self._log('INFO', f'Training plugin model: {plugin_name}')
        model.fit(X_train, y_train)
        
        # Evaluate
        train_preds = model.predict_proba(X_train)
        val_preds = model.predict_proba(X_val)
        
        metrics = self._compute_metrics(y_train, train_preds, y_val, val_preds)
        
        # Save artifact
        artifact_path = self._save_artifact(model, plugin_name)
        
        # Register in existing model_registry
        self._register_model(plugin_name, artifact_path, metrics)
        
        return {
            'model_type': plugin_name,
            'artifact_path': str(artifact_path),
            'metrics': metrics,
        }
    
    def _load_data(self) -> tuple:
        """Load training data using existing feature marts."""
        from train_models import load_examples, database_url
        from sqlalchemy import create_engine
        
        engine = create_engine(database_url())
        
        # Load examples
        frame = load_examples(
            engine,
            target_id=self.target,
            min_season=min(self.seasons),
            max_season=max(self.seasons),
            sample_rate=self.sample_rate,
            feature_set=self.feature_set.replace('pa_', '').replace('game_', ''),
        )
        
        # Get features for this feature_set
        features = self.FEATURE_SETS.get(self.feature_set, self.FEATURE_SETS['pa_basic'])
        all_features = features['numeric'] + features['categorical']
        
        # Split
        train_frame = frame[frame['season'] <= self.train_through]
        val_frame = frame[frame['season'] > self.train_through]
        
        X_train = train_frame[all_features]
        y_train = train_frame['target']
        X_val = val_frame[all_features]
        y_val = val_frame['target']
        
        return X_train, y_train, X_val, y_val
    
    def _compute_metrics(self, y_train, train_preds, y_val, val_preds) -> Dict:
        """Compute metrics using sklearn."""
        from sklearn.metrics import accuracy_score, roc_auc_score, log_loss, brier_score_loss
        
        return {
            'train': {
                'accuracy': float(accuracy_score(y_train, train_preds > 0.5)),
                'roc_auc': float(roc_auc_score(y_train, train_preds)),
                'log_loss': float(log_loss(y_train, train_preds)),
                'brier_score': float(brier_score_loss(y_train, train_preds)),
            },
            'validation': {
                'accuracy': float(accuracy_score(y_val, val_preds > 0.5)),
                'roc_auc': float(roc_auc_score(y_val, val_preds)),
                'log_loss': float(log_loss(y_val, val_preds)),
                'brier_score': float(brier_score_loss(y_val, val_preds)),
            }
        }
    
    def _save_artifact(self, model, model_name: str) -> Path:
        """Save model to existing MODEL_DIR."""
        import joblib
        from datetime import datetime, timezone
        
        MODEL_DIR = ROOT / 'data' / 'models'
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        
        version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        artifact_path = MODEL_DIR / f'{self.target}_{model_name}_{version}.joblib'
        
        joblib.dump(model, artifact_path)
        return artifact_path
    
    def _register_model(self, model_name: str, artifact_path: Path, metrics: Dict):
        """Register in existing models.model_registry table."""
        conn = psycopg2.connect(**self._db_kwargs)
        try:
            with conn.cursor() as cur:
                # Deactivate old versions
                cur.execute("""
                    UPDATE models.model_registry
                    SET is_active = false
                    WHERE target_id = %s AND model_name = %s
                """, (self.target, model_name))
                
                # Insert new version
                cur.execute("""
                    INSERT INTO models.model_registry (
                        target_id, model_name, model_family, model_version, artifact_uri,
                        feature_spec, metrics, is_active
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s::jsonb, %s::jsonb, true
                    )
                """, (
                    self.target,
                    model_name,
                    model_name,
                    datetime.now().strftime('%Y%m%dT%H%M%SZ'),
                    str(artifact_path.relative_to(ROOT)),
                    json.dumps({
                        'numeric_features': self.FEATURE_SETS.get(self.feature_set, {}).get('numeric', []),
                        'categorical_features': self.FEATURE_SETS.get(self.feature_set, {}).get('categorical', []),
                        'feature_set': self.feature_set,
                    }),
                    json.dumps(metrics),
                ))
            conn.commit()
        finally:
            conn.close()
    
    def _get_latest_model_result(self) -> Dict[str, Any]:
        """Get latest model from registry."""
        conn = psycopg2.connect(**self._db_kwargs)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT model_name, model_version, artifact_uri, metrics, feature_spec
                    FROM models.model_registry
                    WHERE target_id = %s AND is_active = true
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (self.target,))
                
                row = cur.fetchone()
                if row:
                    return {
                        'model_name': row[0],
                        'model_version': row[1],
                        'artifact_path': row[2],
                        'metrics': row[3],
                        'feature_spec': row[4],
                    }
                return {}
        finally:
            conn.close()
    
    def _log(self, level: str, message: str):
        """Log to framework.log table if experiment_id set."""
        if self.experiment_id:
            conn = psycopg2.connect(**self._db_kwargs)
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO framework.log (log_level, component, operation, message, run_id)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (level, 'ModelTrainer', 'train', message, self.experiment_id))
                conn.commit()
            finally:
                conn.close()
        
        # Also print
        print(f"[{level}] {message}")
    
    def list_available_targets(self) -> List[str]:
        """List all available target types."""
        return list(self.TARGET_TYPES.keys())
    
    def list_available_feature_sets(self) -> List[str]:
        """List all available feature sets."""
        return list(self.FEATURE_SETS.keys())
    
    def list_registered_plugins(self) -> List[str]:
        """List registered plugin models."""
        return list(self._plugins.keys())
