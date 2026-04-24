#!/usr/bin/env python3
"""
Train Tier-1 XGBoost Baseline for Pitch Outcome Prediction

Tier 1 Classification: {Strike (S), Ball (B), Ball-in-Play (X)}
Target: >80% accuracy on coarse outcomes

This script uses ALL engineered features from the research-backed feature set.
NO features are dropped for token savings - maximum coverage maintained.

Author: AI Agent
Date: 2026-04-24
Epic: #78
"""

import argparse
import json
import logging
import pickle
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    log_loss,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection using environment variables."""
    import os

    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', '5432'),
        database=os.getenv('PGDATABASE', 'retrosheet'),
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD', 'postgres'),
    )


def get_feature_columns() -> list[str]:
    """
    Get ALL feature columns for modeling - NO DROPPING for token savings.

    Feature categories from research paper:
    1. Velocity features
    2. Strike zone features
    3. Outcome flags (not used as features, these are targets)
    4. Pitch movement
    5. Game context
    6. Count features
    """
    return [
        # Velocity features
        'velocity_percentile',
        'velocity_diff_from_avg',
        # Strike zone features
        'distance_from_zone_center',
        'is_in_zone',
        'is_in_shadow_zone',
        'is_in_chase_zone',
        # Pitch movement
        'horizontal_break',
        'vertical_break',
        'approach_angle',
        'spin_efficiency',
        'induced_vertical_break',
        'horizontal_release_deviation',
        'release_velocity_diff',
        # Sequence context
        'pa_pitch_count',
        'is_full_count',
        'is_two_strike',
        'is_three_ball',
        # Game context
        'score_diff',
        'is_late_game',
        'is_high_leverage',
        'base_state_code',
        # Count
        # Note: we encode count_code as separate balls/strikes below
    ]


def encode_count_code(df: pd.DataFrame) -> pd.DataFrame:
    """Encode count code (e.g., '3_2') into balls and strikes columns."""
    df[['balls', 'strikes']] = df['count_code'].str.split('_', expand=True).astype(int)
    return df


def encode_base_state(df: pd.DataFrame) -> pd.DataFrame:
    """Create binary indicators for base states."""
    df['on_1b'] = df['base_state_code'].apply(lambda x: 1 if x & 1 else 0)
    df['on_2b'] = df['base_state_code'].apply(lambda x: 1 if x & 2 else 0)
    df['on_3b'] = df['base_state_code'].apply(lambda x: 1 if x & 4 else 0)
    return df


def load_training_data(conn, limit: int | None = None) -> pd.DataFrame:
    """
    Load training data from engineered_features table.

    Uses ALL features - no dropping for token savings.
    Filters to valid Tier 1 outcomes (S, B, X only - no U)
    Uses stratified sampling if limit is specified.
    """
    logger.info('Loading training data from database...')

    if limit:
        # Use stratified sampling to ensure all classes are represented
        query = f"""
        WITH stratified AS (
            SELECT 
                ef.pitch_id,
                ef.outcome_tier1 as target,
                ef.velocity_percentile,
                ef.velocity_diff_from_avg,
                ef.distance_from_zone_center,
                ef.is_in_zone,
                ef.is_in_shadow_zone,
                ef.is_in_chase_zone,
                ef.horizontal_break,
                ef.vertical_break,
                ef.approach_angle,
                ef.spin_efficiency,
                ef.induced_vertical_break,
                ef.horizontal_release_deviation,
                ef.release_velocity_diff,
                ef.pa_pitch_count,
                ef.is_full_count,
                ef.is_two_strike,
                ef.is_three_ball,
                ef.score_diff,
                ef.score_diff_bucket,
                ef.is_late_game,
                ef.is_high_leverage,
                ef.base_state_code,
                ef.base_state_name,
                ef.count_code,
                ef.outcome_tier2,
                ef.is_hard_hit,
                ef.is_barrel,
                ef.swing_decision,
                ROW_NUMBER() OVER (PARTITION BY ef.outcome_tier1 ORDER BY RANDOM()) as rn
            FROM features_pitch.engineered_features ef
            WHERE ef.outcome_tier1 IN ('S', 'B', 'X')
              AND ef.distance_from_zone_center IS NOT NULL
        )
        SELECT * FROM stratified
        WHERE rn <= {limit // 3}
        LIMIT {limit}
        """
    else:
        query = """
        SELECT 
            ef.pitch_id,
            ef.outcome_tier1 as target,
            ef.velocity_percentile,
            ef.velocity_diff_from_avg,
            ef.distance_from_zone_center,
            ef.is_in_zone,
            ef.is_in_shadow_zone,
            ef.is_in_chase_zone,
            ef.horizontal_break,
            ef.vertical_break,
            ef.approach_angle,
            ef.spin_efficiency,
            ef.induced_vertical_break,
            ef.horizontal_release_deviation,
            ef.release_velocity_diff,
            ef.pa_pitch_count,
            ef.is_full_count,
            ef.is_two_strike,
            ef.is_three_ball,
            ef.score_diff,
            ef.score_diff_bucket,
            ef.is_late_game,
            ef.is_high_leverage,
            ef.base_state_code,
            ef.base_state_name,
            ef.count_code,
            ef.outcome_tier2,
            ef.is_hard_hit,
            ef.is_barrel,
            ef.swing_decision
        FROM features_pitch.engineered_features ef
        WHERE ef.outcome_tier1 IN ('S', 'B', 'X')
          AND ef.distance_from_zone_center IS NOT NULL
        """

    df = pd.read_sql(query, conn)
    logger.info(f'Loaded {len(df)} rows')

    # Encode categorical features
    df = encode_count_code(df)
    df = encode_base_state(df)

    # Convert booleans to int
    bool_cols = [
        'is_in_zone',
        'is_in_shadow_zone',
        'is_in_chase_zone',
        'is_full_count',
        'is_two_strike',
        'is_three_ball',
        'is_late_game',
        'is_high_leverage',
    ]
    for col in bool_cols:
        df[col] = df[col].astype(int)

    return df


def prepare_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Prepare feature matrix X and target vector y.

    Returns:
        X: Feature matrix
        y: Target vector (encoded)
        feature_names: List of feature column names
    """
    # Define feature columns - using ALL available features
    feature_cols = [
        'velocity_percentile',
        'velocity_diff_from_avg',
        'distance_from_zone_center',
        'is_in_zone',
        'is_in_shadow_zone',
        'is_in_chase_zone',
        'horizontal_break',
        'vertical_break',
        'approach_angle',
        'spin_efficiency',
        'induced_vertical_break',
        'horizontal_release_deviation',
        'release_velocity_diff',
        'pa_pitch_count',
        'is_full_count',
        'is_two_strike',
        'is_three_ball',
        'balls',
        'strikes',  # From count_code encoding
        'score_diff',
        'is_late_game',
        'is_high_leverage',
        'on_1b',
        'on_2b',
        'on_3b',  # From base_state encoding
    ]

    X = df[feature_cols].fillna(0).values
    y = df['target'].values

    return X, y, feature_cols


def train_model(X: np.ndarray, y: np.ndarray, feature_names: list[str]) -> dict:
    """
    Train Tier-1 XGBoost classifier.

    Target: >80% accuracy on coarse outcomes (S, B, X)
    """
    logger.info('Training Tier-1 XGBoost classifier...')

    # Encode target labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    logger.info(f'Classes: {le.classes_}')
    logger.info(f'Class distribution: {np.bincount(y_encoded)}')

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded,
    )

    logger.info(f'Train: {len(X_train)}, Test: {len(X_test)}')

    # XGBoost parameters - optimized for speed and accuracy
    params = {
        'objective': 'multi:softprob',
        'num_class': len(le.classes_),
        'eval_metric': 'mlogloss',
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 200,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'reg_alpha': 0.1,
        'reg_lambda': 1.0,
        'min_child_weight': 3,
        'gamma': 0.1,
        'random_state': 42,
        'n_jobs': -1,
        'tree_method': 'hist',  # Fast histogram-based algorithm
        'device': 'cpu',
    }

    # Train model
    model = xgb.XGBClassifier(**params)
    model.fit(X_train, y_train, verbose=False)

    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)

    # Metrics
    accuracy = accuracy_score(y_test, y_pred)
    logloss = log_loss(y_test, y_pred_proba)

    # Per-class metrics
    report = classification_report(y_test, y_pred, target_names=le.classes_, output_dict=True)

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)

    # Feature importance
    importance = model.feature_importances_
    feature_importance = sorted(zip(feature_names, importance), key=lambda x: x[1], reverse=True)

    results = {
        'accuracy': accuracy,
        'log_loss': logloss,
        'accuracy_target_met': accuracy >= 0.80,
        'classification_report': report,
        'confusion_matrix': cm.tolist(),
        'feature_importance': feature_importance[:15],  # Top 15
        'classes': le.classes_.tolist(),
        'n_features': len(feature_names),
        'n_train': len(X_train),
        'n_test': len(X_test),
    }

    logger.info(f"\n{'=' * 50}")
    logger.info('Tier-1 XGBoost Results')
    logger.info(f"{'=' * 50}")
    logger.info(f'Accuracy: {accuracy:.4f} (Target: ≥0.80)')
    logger.info(f'Log Loss: {logloss:.4f}')
    logger.info(f"Target Met: {results['accuracy_target_met']}")
    logger.info('\nTop 5 Features:')
    for feat, imp in feature_importance[:5]:
        logger.info(f'  {feat}: {imp:.4f}')

    # Save model
    model_dir = Path('models/pitch_tier1')
    model_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_path = model_dir / f'tier1_xgboost_{timestamp}.pkl'

    model_data = {
        'model': model,
        'label_encoder': le,
        'feature_names': feature_names,
        'results': results,
        'timestamp': timestamp,
    }

    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)

    logger.info(f'\nModel saved to: {model_path}')

    # Save results JSON
    results_path = model_dir / f'tier1_results_{timestamp}.json'
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f'Results saved to: {results_path}')

    return results


def main():
    parser = argparse.ArgumentParser(description='Train Tier-1 XGBoost pitch outcome model')
    parser.add_argument('--limit', type=int, help='Limit rows for testing')
    parser.add_argument('--dry-run', action='store_true', help='Validate setup without training')
    args = parser.parse_args()

    conn = get_db_connection()

    try:
        if args.dry_run:
            logger.info('DRY RUN - Validating setup...')
            df = load_training_data(conn, limit=1000)
            logger.info(f'✓ Data load successful: {len(df)} rows')
            logger.info(f'✓ Features: {len(get_feature_columns())}')
            logger.info(f"✓ Target distribution: {df['target'].value_counts().to_dict()}")
            return

        # Load data
        df = load_training_data(conn, limit=args.limit)

        # Prepare features
        X, y, feature_names = prepare_features(df)

        # Train model
        results = train_model(X, y, feature_names)

        # Exit with appropriate code
        sys.exit(0 if results['accuracy_target_met'] else 1)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
