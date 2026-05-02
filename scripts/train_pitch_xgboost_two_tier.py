#!/usr/bin/env python3
"""
Train Two-Tier XGBoost Pitch-Level Model

Tier 1: Classify pitch outcome as Ball / Strike / Ball-in-Play
Tier 2: If Ball-in-Play, classify as Single/Double/Triple/HR/Out

Usage:
    python scripts/train_pitch_xgboost_two_tier.py --train-seasons 2015-2023 --val-seasons 2024-2025
    python scripts/train_pitch_xgboost_two_tier.py --evaluate-only models/pitch_tier1_v1.0.pkl
"""

import argparse
import json
import logging
import pickle
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import xgboost as xgb
from sklearn.metrics import accuracy_score, log_loss, classification_report
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).parent.parent))

from baseball.core.db import get_db_connection
from baseball.utils.logging_config import get_logger

logger = get_logger(__name__)


# Feature columns for the model
FEATURE_COLUMNS = [
    'release_speed', 'release_pos_x', 'release_pos_y', 'release_pos_z',
    'pfx_x', 'pfx_z', 'plate_x', 'plate_z', 'plate_z_adj',
    'effective_speed', 'release_spin_rate', 'spin_axis',
    'balls', 'strikes',
    'break_magnitude', 'approach_angle',
    'leverage_index', 'score_diff',
    'plate_distance_from_center',
    'inning', 'outs_when_up'
]

TIER1_CLASSES = ['Ball', 'Strike', 'BallInPlay']
TIER2_CLASSES = ['Single', 'Double', 'Triple', 'HR', 'Out']


def fetch_training_data(
    train_seasons: list[int],
    val_seasons: list[int],
    version_tag: str = 'v1.0'
) -> tuple:
    """
    Fetch training and validation data from database.
    
    Returns:
        (X_train, y_tier1_train, X_val, y_tier1_val, y_tier2_train, y_tier2_val)
    """
    logger.info(f"Fetching training data: seasons {min(train_seasons)}-{max(train_seasons)}")
    logger.info(f"Validation seasons: {min(val_seasons)}-{max(val_seasons)}")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Build feature list with NULL handling
    features_sql = ', '.join([
        f"COALESCE(bf.{col}, 0) as {col}" 
        for col in FEATURE_COLUMNS
    ])
    
    # Fetch training data
    cur.execute(f"""
        SELECT 
            {features_sql},
            ef.outcome_tier1,
            ef.outcome_tier2
        FROM features_pitch.base_features bf
        JOIN features_pitch.engineered_features ef
            ON bf.pitch_id = ef.pitch_id
            AND bf.version_tag = ef.version_tag
        WHERE bf.game_year = ANY(%s)
        AND bf.version_tag = %s
        AND ef.outcome_tier1 IS NOT NULL
        AND ef.outcome_tier1 != 'Other'
    """, (train_seasons, version_tag))
    
    train_rows = cur.fetchall()
    logger.info(f"Fetched {len(train_rows):,} training rows")
    
    # Fetch validation data
    cur.execute(f"""
        SELECT 
            {features_sql},
            ef.outcome_tier1,
            ef.outcome_tier2
        FROM features_pitch.base_features bf
        JOIN features_pitch.engineered_features ef
            ON bf.pitch_id = ef.pitch_id
            AND bf.version_tag = ef.version_tag
        WHERE bf.game_year = ANY(%s)
        AND bf.version_tag = %s
        AND ef.outcome_tier1 IS NOT NULL
        AND ef.outcome_tier1 != 'Other'
    """, (val_seasons, version_tag))
    
    val_rows = cur.fetchall()
    logger.info(f"Fetched {len(val_rows):,} validation rows")
    
    cur.close()
    conn.close()
    
    # Convert to numpy arrays
    n_features = len(FEATURE_COLUMNS)
    
    X_train = np.array([row[:n_features] for row in train_rows])
    y_tier1_train = np.array([row[n_features] for row in train_rows])
    y_tier2_train = np.array([row[n_features + 1] for row in train_rows])
    
    X_val = np.array([row[:n_features] for row in val_rows])
    y_tier1_val = np.array([row[n_features] for row in val_rows])
    y_tier2_val = np.array([row[n_features + 1] for row in val_rows])
    
    return X_train, y_tier1_train, X_val, y_tier1_val, y_tier2_train, y_tier2_val


def encode_tier1(labels: np.ndarray) -> tuple[np.ndarray, dict]:
    """Encode tier-1 labels to integers."""
    class_map = {cls: i for i, cls in enumerate(TIER1_CLASSES)}
    encoded = np.array([class_map.get(label, -1) for label in labels])
    return encoded, class_map


def encode_tier2(labels: np.ndarray) -> tuple[np.ndarray, dict]:
    """Encode tier-2 labels to integers."""
    class_map = {cls: i for i, cls in enumerate(TIER2_CLASSES)}
    encoded = np.array([class_map.get(label, -1) for label in labels])
    return encoded, class_map


def train_tier1_model(X_train, y_train, X_val, y_val) -> tuple:
    """Train Tier-1 XGBoost classifier."""
    logger.info("Training Tier-1 model (Ball/Strike/BallInPlay)")
    
    y_train_enc, class_map = encode_tier1(y_train)
    y_val_enc, _ = encode_tier1(y_val)
    
    # Filter out unknown classes
    mask_train = y_train_enc >= 0
    mask_val = y_val_enc >= 0
    
    X_train_f = X_train[mask_train]
    y_train_enc = y_train_enc[mask_train]
    X_val_f = X_val[mask_val]
    y_val_enc = y_val_enc[mask_val]
    
    model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=len(TIER1_CLASSES),
        max_depth=8,
        learning_rate=0.1,
        n_estimators=500,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        eval_metric='mlogloss',
        early_stopping_rounds=20
    )
    
    model.fit(
        X_train_f, y_train_enc,
        eval_set=[(X_val_f, y_val_enc)],
        verbose=False
    )
    
    # Evaluate
    y_pred = model.predict(X_val_f)
    y_pred_proba = model.predict_proba(X_val_f)
    
    accuracy = accuracy_score(y_val_enc, y_pred)
    loss = log_loss(y_val_enc, y_pred_proba)
    
    logger.info(f"Tier-1 Accuracy: {accuracy:.4f}")
    logger.info(f"Tier-1 Log Loss: {loss:.4f}")
    
    return model, accuracy, loss, class_map


def train_tier2_model(X_train, y_train, X_val, y_val) -> tuple:
    """Train Tier-2 XGBoost classifier for Ball-in-Play outcomes."""
    logger.info("Training Tier-2 model (Single/Double/Triple/HR/Out)")
    
    y_train_enc, class_map = encode_tier2(y_train)
    y_val_enc, _ = encode_tier2(y_val)
    
    # Filter to only Ball-in-Play and known tier-2 classes
    mask_train = y_train_enc >= 0
    mask_val = y_val_enc >= 0
    
    X_train_f = X_train[mask_train]
    y_train_enc = y_train_enc[mask_train]
    X_val_f = X_val[mask_val]
    y_val_enc = y_val_enc[mask_val]
    
    if len(X_train_f) < 1000:
        logger.warning("Insufficient Ball-in-Play data for Tier-2 model")
        return None, 0, 0, class_map
    
    model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=len(TIER2_CLASSES),
        max_depth=10,
        learning_rate=0.05,
        n_estimators=1000,
        subsample=0.7,
        colsample_bytree=0.7,
        random_state=42,
        n_jobs=-1,
        eval_metric='mlogloss',
        early_stopping_rounds=30
    )
    
    model.fit(
        X_train_f, y_train_enc,
        eval_set=[(X_val_f, y_val_enc)],
        verbose=False
    )
    
    # Evaluate
    y_pred = model.predict(X_val_f)
    y_pred_proba = model.predict_proba(X_val_f)
    
    accuracy = accuracy_score(y_val_enc, y_pred)
    loss = log_loss(y_val_enc, y_pred_proba)
    
    logger.info(f"Tier-2 Accuracy: {accuracy:.4f}")
    logger.info(f"Tier-2 Log Loss: {loss:.4f}")
    
    return model, accuracy, loss, class_map


def save_model(model, filepath: Path, metadata: dict):
    """Save model with metadata."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    artifact = {
        'model': model,
        'metadata': metadata,
        'saved_at': datetime.now().isoformat()
    }
    
    with open(filepath, 'wb') as f:
        pickle.dump(artifact, f)
    
    logger.info(f"Model saved to {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description='Train Two-Tier XGBoost pitch-level model'
    )
    parser.add_argument(
        '--train-seasons', '-t',
        default='2015-2023',
        help='Training season range (e.g., 2015-2023)'
    )
    parser.add_argument(
        '--val-seasons', '-v',
        default='2024-2025',
        help='Validation season range (e.g., 2024-2025)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=Path,
        default=Path('models/pitch_level'),
        help='Output directory for models'
    )
    parser.add_argument(
        '--version-tag', '-g',
        default='v1.0',
        help='Base features version tag'
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse season ranges
    train_start, train_end = map(int, args.train_seasons.split('-'))
    val_start, val_end = map(int, args.val_seasons.split('-'))
    train_seasons = list(range(train_start, train_end + 1))
    val_seasons = list(range(val_start, val_end + 1))
    
    # Fetch data
    X_train, y_t1_train, X_val, y_t1_val, y_t2_train, y_t2_val = fetch_training_data(
        train_seasons, val_seasons, args.version_tag
    )
    
    # Train Tier-1
    tier1_model, t1_acc, t1_loss, t1_map = train_tier1_model(
        X_train, y_t1_train, X_val, y_t1_val
    )
    
    # Train Tier-2 (on Ball-in-Play subset)
    bip_mask_train = y_t1_train == 'BallInPlay'
    bip_mask_val = y_t1_val == 'BallInPlay'
    
    tier2_model, t2_acc, t2_loss, t2_map = train_tier2_model(
        X_train[bip_mask_train], y_t2_train[bip_mask_train],
        X_val[bip_mask_val], y_t2_val[bip_mask_val]
    )
    
    # Save models
    model_version = f"t1_{datetime.now().strftime('%Y%m%d')}"
    
    save_model(
        tier1_model,
        args.output_dir / f'tier1_{model_version}.pkl',
        {
            'model_type': 'xgboost',
            'tier': 1,
            'classes': TIER1_CLASSES,
            'class_map': t1_map,
            'features': FEATURE_COLUMNS,
            'accuracy': t1_acc,
            'log_loss': t1_loss,
            'train_seasons': train_seasons,
            'val_seasons': val_seasons
        }
    )
    
    if tier2_model:
        save_model(
            tier2_model,
            args.output_dir / f'tier2_{model_version}.pkl',
            {
                'model_type': 'xgboost',
                'tier': 2,
                'classes': TIER2_CLASSES,
                'class_map': t2_map,
                'features': FEATURE_COLUMNS,
                'accuracy': t2_acc,
                'log_loss': t2_loss,
                'train_seasons': train_seasons,
                'val_seasons': val_seasons
            }
        )
    
    # Summary
    print(f"\n{'='*60}")
    print("TRAINING COMPLETE - Two-Tier XGBoost Pitch Model")
    print(f"{'='*60}")
    print(f"\nTier-1 (Ball/Strike/BallInPlay):")
    print(f"  Accuracy: {t1_acc:.4f} ({t1_acc*100:.1f}%)")
    print(f"  Log Loss: {t1_loss:.4f}")
    print(f"  Target: >80% (SMU benchmark: 58%)")
    print(f"  Status: {'✓ ABOVE TARGET' if t1_acc > 0.8 else '⚠ BELOW TARGET'}")
    
    if tier2_model:
        print(f"\nTier-2 (Outcome when Ball-in-Play):")
        print(f"  Accuracy: {t2_acc:.4f} ({t2_acc*100:.1f}%)")
        print(f"  Log Loss: {t2_loss:.4f}")
    
    print(f"\nModels saved to: {args.output_dir}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
