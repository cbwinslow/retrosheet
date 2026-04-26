#!/usr/bin/env python3
"""
Model Training Campaign - Train All Production Models

This script trains the 4 core models for baseball prediction:
1. Swing Decision (will batter swing?)
2. Contact Made (will batter make contact?)
3. Hit Outcome (will result be a hit?)
4. Home Win (will home team win?)

Usage:
    # Train all models
    python run_model_training_campaign.py --all
    
    # Train specific model
    python run_model_training_campaign.py --target swing_decision
    
    # Train with custom seasons
    python run_model_training_campaign.py --all --min-season 2020 --max-season 2025 --train-through 2023

Author: Agent Cascade
Date: April 24, 2026
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy import create_engine


# ============================================================================
# TARGET DEFINITIONS
# ============================================================================

TARGETS = {
    'swing_decision': {
        'description': 'Will batter swing at pitch?',
        'target_col': 'swing_outcome',
        'table': 'features.pitch_decision_examples',
        'metrics': ['roc_auc', 'accuracy', 'log_loss'],
    },
    'contact_made': {
        'description': 'Will batter make contact?',
        'target_col': 'contact_outcome',
        'table': 'features.pitch_contact_examples',
        'metrics': ['roc_auc', 'accuracy', 'log_loss'],
    },
    'hit_outcome': {
        'description': 'Will result be a hit?',
        'target_col': 'hit_outcome',
        'table': 'features.plate_appearance_examples',
        'metrics': ['roc_auc', 'accuracy', 'log_loss'],
    },
    'win_probability': {
        'description': 'Will home team win?',
        'target_col': 'final_home_win',
        'table': 'features.game_outcome_advanced_examples',
        'metrics': ['roc_auc', 'accuracy', 'log_loss'],
    },
}

# ============================================================================
# FEATURE SETS
# ============================================================================

FEATURE_SETS = {
    'basic': {
        'numeric': ['inning', 'is_bottom_inning', 'outs_before', 'start_bases', 'balls', 'strikes', 'home_score_diff'],
        'categorical': ['batter_hand', 'pitcher_hand'],
    },
    'advanced': {
        'numeric': [
            'inning', 'is_bottom_inning', 'outs_before', 'start_bases', 'balls', 'strikes', 'home_score_diff',
            'batter_career_prior_pa', 'batter_career_prior_hit_rate', 'batter_career_prior_walk_rate',
            'pitcher_career_prior_batters_faced', 'pitcher_career_prior_hit_allowed_rate',
        ],
        'categorical': ['batter_hand', 'pitcher_hand', 'park_id'],
    },
}

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def database_url() -> str:
    """Get database URL from environment."""
    import os
    host = os.getenv('PGHOST', 'localhost')
    port = os.getenv('PGPORT', '5432')
    db = os.getenv('PGDATABASE', 'retrosheet')
    user = os.getenv('PGUSER', 'cbwinslow')
    password = os.getenv('PGPASSWORD', '')
    # Use psycopg2 driver explicitly
    return f'postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}'


def database_kwargs() -> dict:
    """Get database connection kwargs."""
    import os
    return {
        'host': os.getenv('PGHOST', 'localhost'),
        'port': os.getenv('PGPORT', '5432'),
        'dbname': os.getenv('PGDATABASE', 'retrosheet'),
        'user': os.getenv('PGUSER', 'cbwinslow'),
        'password': os.getenv('PGPASSWORD', ''),
    }


# ============================================================================
# DATA LOADING
# ============================================================================

def load_training_data(
    engine,
    target_id: str,
    feature_set: str,
    min_season: int,
    max_season: int,
    train_through: int,
    sample_rate: float = 1.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load training data from database.
    
    Returns:
        Tuple of (train_df, val_df, test_df)
    """
    target_info = TARGETS[target_id]
    features = FEATURE_SETS[feature_set]

    # Build query
    numeric_cols = ', '.join(features['numeric'])
    categorical_cols = ', '.join(features['categorical'])
    target_col = target_info['target_col']
    table = target_info['table']

    sql = f"""
    SELECT 
        season,
        {numeric_cols},
        {categorical_cols},
        {target_col}::integer as target
    FROM {table}
    WHERE season BETWEEN {min_season} AND {max_season}
      AND {target_col} IS NOT NULL
    """

    if sample_rate < 1.0:
        sql += f'\n      AND random() < {sample_rate}'

    print(f'[INFO] Loading data from {table}...')
    print(f'[INFO] Query: {sql[:200]}...')

    df = pd.read_sql(sql, engine)

    print(f'[INFO] Loaded {len(df)} rows')

    # Split by season
    train_df = df[df['season'] <= train_through].copy()
    val_df = df[(df['season'] > train_through) & (df['season'] <= train_through + 1)].copy()
    test_df = df[df['season'] > train_through + 1].copy()

    print(f'[INFO] Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}')

    return train_df, val_df, test_df


# ============================================================================
# MODEL BUILDERS
# ============================================================================

def build_model_pipeline(
    numeric_features: list[str],
    categorical_features: list[str],
    model_family: str = 'xgboost',
) -> Pipeline:
    """Build sklearn pipeline with preprocessing and model."""

    # Preprocessing
    numeric_transformer = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
    ])

    categorical_transformer = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False)),
    ])

    preprocessor = ColumnTransformer([
        ('num', numeric_transformer, numeric_features),
        ('cat', categorical_transformer, categorical_features),
    ])

    # Model
    if model_family == 'xgboost':
        try:
            from xgboost import XGBClassifier
            model = XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                use_label_encoder=False,
                eval_metric='logloss',
            )
        except ImportError:
            print('[WARN] XGBoost not available, using HistGradientBoosting')
            model = HistGradientBoostingClassifier(
                max_iter=200,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
            )
    elif model_family == 'lightgbm':
        try:
            from lightgbm import LGBMClassifier
            model = LGBMClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                verbose=-1,
            )
        except ImportError:
            print('[WARN] LightGBM not available, using HistGradientBoosting')
            model = HistGradientBoostingClassifier(
                max_iter=200,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
            )
    elif model_family == 'logistic_regression':
        model = LogisticRegression(
            max_iter=1000,
            random_state=42,
            n_jobs=-1,
        )
    else:
        model = HistGradientBoostingClassifier(
            max_iter=200,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
        )

    # Pipeline
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('model', model),
    ])

    return pipeline


# ============================================================================
# METRICS
# ============================================================================

def compute_metrics(model, X: pd.DataFrame, y: pd.Series) -> dict:
    """Compute evaluation metrics."""
    y_pred = model.predict(X)
    y_prob = model.predict_proba(X)[:, 1]

    metrics = {
        'roc_auc': roc_auc_score(y, y_prob),
        'accuracy': accuracy_score(y, y_pred),
        'log_loss': log_loss(y, y_prob),
        'brier_score': brier_score_loss(y, y_prob),
        'n_samples': len(y),
    }

    return metrics


# ============================================================================
# TRAINING
# ============================================================================

def train_model(
    target_id: str,
    feature_set: str = 'advanced',
    model_family: str = 'xgboost',
    min_season: int = 2020,
    max_season: int = 2025,
    train_through: int = 2023,
    sample_rate: float = 1.0,
    output_dir: str = 'models/production',
) -> dict:
    """
    Train a single model and return results.
    
    Returns:
        Dict with training results and metrics
    """
    print(f"\n{'='*60}")
    print(f'Training: {target_id}')
    print(f'Feature set: {feature_set}')
    print(f'Model: {model_family}')
    print(f"{'='*60}")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Connect to database
    engine = create_engine(database_url())

    try:
        # Load data
        train_df, val_df, test_df = load_training_data(
            engine,
            target_id=target_id,
            feature_set=feature_set,
            min_season=min_season,
            max_season=max_season,
            train_through=train_through,
            sample_rate=sample_rate,
        )

        if len(train_df) == 0 or len(val_df) == 0:
            print(f'[ERROR] No data loaded for {target_id}')
            return {'status': 'failed', 'error': 'no_data'}

        # Get features
        features = FEATURE_SETS[feature_set]
        numeric_features = features['numeric']
        categorical_features = features['categorical']

        # Prepare data
        X_train = train_df[numeric_features + categorical_features]
        y_train = train_df['target']
        X_val = val_df[numeric_features + categorical_features]
        y_val = val_df['target']

        # Build and train model
        print(f'[INFO] Building {model_family} model...')
        model = build_model_pipeline(numeric_features, categorical_features, model_family)

        print(f'[INFO] Training on {len(X_train)} samples...')
        model.fit(X_train, y_train)

        # Compute metrics
        print('[INFO] Computing metrics...')
        train_metrics = compute_metrics(model, X_train, y_train)
        val_metrics = compute_metrics(model, X_val, y_val)

        # Save model
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_name = f'{target_id}_{model_family}_{feature_set}_{timestamp}'
        model_path = output_path / f'{model_name}.joblib'

        joblib.dump(model, model_path)
        print(f'[INFO] Model saved to {model_path}')

        # Save metadata
        metadata = {
            'target_id': target_id,
            'feature_set': feature_set,
            'model_family': model_family,
            'timestamp': timestamp,
            'model_name': model_name,
            'model_path': str(model_path),
            'features': {
                'numeric': numeric_features,
                'categorical': categorical_features,
            },
            'data': {
                'min_season': min_season,
                'max_season': max_season,
                'train_through': train_through,
                'n_train': len(train_df),
                'n_val': len(val_df),
                'n_test': len(test_df),
            },
            'metrics': {
                'train': train_metrics,
                'validation': val_metrics,
            },
        }

        metadata_path = output_path / f'{model_name}_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f'[INFO] Metadata saved to {metadata_path}')

        # Print results
        print('\n[RESULTS]')
        print(f"  Train AUC: {train_metrics['roc_auc']:.4f}")
        print(f"  Val AUC:   {val_metrics['roc_auc']:.4f}")
        print(f"  Val Acc:   {val_metrics['accuracy']:.4f}")
        print(f"  Val Loss:  {val_metrics['log_loss']:.4f}")

        return {
            'status': 'success',
            'model_name': model_name,
            'model_path': str(model_path),
            'train_auc': train_metrics['roc_auc'],
            'val_auc': val_metrics['roc_auc'],
            'metadata': metadata,
        }

    except Exception as e:
        print(f'[ERROR] Training failed: {e}')
        import traceback
        traceback.print_exc()
        return {'status': 'failed', 'error': str(e)}

    finally:
        engine.dispose()


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Run model training campaign',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train all models
  python run_model_training_campaign.py --all
  
  # Train specific target
  python run_model_training_campaign.py --target swing_decision
  
  # Train with custom seasons
  python run_model_training_campaign.py --all --min-season 2020 --max-season 2025 --train-through 2023
  
  # Compare models
  python run_model_training_campaign.py --compare --target swing_decision --families xgboost lightgbm
""",
    )

    parser.add_argument('--all', action='store_true', help='Train all targets')
    parser.add_argument('--target', type=str, choices=list(TARGETS.keys()), help='Target to train')
    parser.add_argument('--feature-set', type=str, default='advanced', choices=['basic', 'advanced'])
    parser.add_argument('--model-family', type=str, default='xgboost', choices=['xgboost', 'lightgbm', 'logistic_regression', 'hist_gradient_boosting'])
    parser.add_argument('--families', nargs='+', default=['xgboost', 'lightgbm'], help='Model families for comparison')
    parser.add_argument('--compare', action='store_true', help='Run comparison')

    parser.add_argument('--min-season', type=int, default=2020)
    parser.add_argument('--max-season', type=int, default=2025)
    parser.add_argument('--train-through', type=int, default=2023)
    parser.add_argument('--sample-rate', type=float, default=1.0)

    parser.add_argument('--output-dir', type=str, default='models/production')
    parser.add_argument('--summary', type=str, default='models/training_summary.json')

    args = parser.parse_args()

    # Determine targets
    if args.all:
        targets = list(TARGETS.keys())
    elif args.target:
        targets = [args.target]
    else:
        print('[ERROR] Must specify --all or --target')
        return 1

    # Run training
    results = []

    for target_id in targets:
        if args.compare:
            # Run comparison for this target
            print(f"\n{'='*60}")
            print(f'Comparison for {target_id}')
            print(f"{'='*60}")

            for family in args.families:
                result = train_model(
                    target_id=target_id,
                    feature_set=args.feature_set,
                    model_family=family,
                    min_season=args.min_season,
                    max_season=args.max_season,
                    train_through=args.train_through,
                    sample_rate=args.sample_rate,
                    output_dir=args.output_dir,
                )
                results.append(result)
        else:
            # Train single model
            result = train_model(
                target_id=target_id,
                feature_set=args.feature_set,
                model_family=args.model_family,
                min_season=args.min_season,
                max_season=args.max_season,
                train_through=args.train_through,
                sample_rate=args.sample_rate,
                output_dir=args.output_dir,
            )
            results.append(result)

    # Save summary
    summary = {
        'timestamp': datetime.now().isoformat(),
        'args': vars(args),
        'results': results,
        'n_success': sum(1 for r in results if r.get('status') == 'success'),
        'n_failed': sum(1 for r in results if r.get('status') == 'failed'),
    }

    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print('Training Campaign Complete')
    print(f"{'='*60}")
    print(f'Total: {len(results)}')
    print(f"Success: {summary['n_success']}")
    print(f"Failed: {summary['n_failed']}")
    print(f'Summary saved to {summary_path}')

    return 0 if summary['n_failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
