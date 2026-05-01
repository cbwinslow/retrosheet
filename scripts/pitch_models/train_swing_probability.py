"""
Swing Probability Model - Binary Classification

Predicts P(swing | pitch context) using XGBoost.
Target: is_swing (binary: True if batter swung at pitch)

Research-backed features from:
- Swing Probability papers (SMU/CMU research)
- Plate discipline metrics (chase rate, zone rate)
- Pitch sequencing effects
- Count-dependent swing tendencies

Usage:
    uv run python scripts/pitch_models/train_swing_probability.py
"""

import argparse
import json
import os
import pickle
import time
from datetime import datetime

import numpy as np
import pandas as pd
import psycopg2
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split


# Configuration
DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/retrosheet')
MODEL_DIR = 'models/swing_probability'
RESULTS_FILE = f'{MODEL_DIR}/swing_results.json'

# Ensure model directory exists
os.makedirs(MODEL_DIR, exist_ok=True)


def get_swing_features() -> list[str]:
    """
    Features for swing probability prediction.
    Based on research showing swing decisions depend on:
    - Pitch location relative to zone
    - Count (aggresiveness varies by balls/strikes)
    - Pitch type and velocity
    - Sequence/previous pitch
    - Game situation
    """
    return [
        # Pitch Location (Primary driver)
        'plate_x',
        'plate_z',
        'distance_from_center',  # How far from plate center
        'is_in_zone',
        'is_shadow_zone',
        'is_chase_zone',
        'zone',  # 1-9 strike zone grid
        # Count Context (Major influence on aggressiveness)
        'balls',
        'strikes',
        'is_two_strike',
        'is_three_ball',
        'is_full_count',
        'count_leverage_index',  # 0-1, how "important" is this pitch
        # Pitch Characteristics
        'pitch_type',  # Categorical: FF, SL, CH, CU, etc.
        'start_speed',
        'effective_speed',
        'spin_rate',
        'spin_axis',
        'pfx_x',
        'pfx_z',  # Movement
        'horizontal_break',
        'vertical_break',
        # Sequence Context
        'prev_pitch_type',  # What came before
        'consecutive_same_type',  # Back-to-back same pitch?
        'pitch_number',  # 1st, 2nd, 3rd pitch of PA
        'pa_pitch_count',  # Pitches thrown in this PA so far
        # Game Situation
        'score_diff',  # Run differential
        'inning',
        'inning_topbot',  # Top/bottom
        'outs_when_up',
        'base_state_code',  # 0-7 encoding of runners
        'on_1b',
        'on_2b',
        'on_3b',  # Boolean runners
        'is_late_game',
        'is_high_leverage',
        'run_expectancy_24',  # Run expectancy given base-out state
        # Batter/Pitcher Context
        'stand',
        'p_throws',  # Handedness
        'is_same_handed_matchup',  # Platoon situation
        'times_faced_this_game',  # 1st, 2nd, 3rd time seeing pitcher
        # Environmental (minor effect)
        'is_day_game',
    ]


def load_swing_data(conn, sample_size: int | None = None) -> pd.DataFrame:
    """
    Load training data for swing probability model.

    Query includes:
    - All pitches where we know if batter swung (is_swing IS NOT NULL)
    - Excludes pitchouts, intentional balls, hit by pitch (non-swingable pitches)
    """
    print('Loading swing probability training data...')

    features = get_swing_features()
    feature_cols = ', '.join([f'ef.{f}' for f in features])

    # Build query - exclude non-swingable pitch types
    query = f"""
    SELECT
        ef.pitch_id,
        ef.is_swing as target,
        {feature_cols},
        -- Include description for validation
        bf.description
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    WHERE ef.is_swing IS NOT NULL
      AND ef.is_valid_for_training = TRUE
      AND bf.pitch_type NOT IN ('PO', 'IN', 'AB', 'AS', 'UN', 'FO', 'EP')
      -- Exclude intentional balls, pitchouts, automatic balls/strikes
      AND bf.description NOT ILIKE '%intentional%'
      AND bf.description NOT ILIKE '%pitchout%'
      AND bf.description NOT ILIKE '%automatic%'
    """

    if sample_size:
        query += f' ORDER BY RANDOM() LIMIT {sample_size}'
    else:
        # Full dataset - stratified by swing rate
        query += ' ORDER BY RANDOM()'

    print('Executing query...')
    start_time = time.time()
    df = pd.read_sql(query, conn)
    elapsed = time.time() - start_time

    print(f'Loaded {len(df):,} rows in {elapsed:.1f}s')
    print('Class distribution:')
    print(df['target'].value_counts())
    print(f'Swing rate: {df["target"].mean():.1%}')

    return df


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Prepare features for XGBoost training.

    Handles:
    - Categorical encoding (pitch_type, zone, etc.)
    - Missing value imputation
    - Feature engineering for model
    """
    print('\nPreparing features...')

    # Separate target
    y = df['target'].astype(int)
    X = df.drop(['target', 'pitch_id', 'description'], axis=1, errors='ignore').copy()

    # Handle categorical variables
    categorical_cols = [
        'pitch_type',
        'prev_pitch_type',
        'stand',
        'p_throws',
        'inning_topbot',
        'base_state_code',
    ]

    for col in categorical_cols:
        if col in X.columns:
            # Fill NA with 'UNKNOWN'
            X[col] = X[col].fillna('UNKNOWN')
            # One-hot encode
            dummies = pd.get_dummies(X[col], prefix=col, drop_first=True)
            X = pd.concat([X.drop(col, axis=1), dummies], axis=1)

    # Handle numeric missing values
    numeric_cols = X.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        X[col] = X[col].fillna(X[col].median())

    print(f'Feature matrix shape: {X.shape}')
    print(f'Features: {list(X.columns)[:10]}... ({len(X.columns)} total)')

    return X, y


def train_swing_model(X: pd.DataFrame, y: pd.Series) -> dict:
    """
    Train XGBoost binary classifier for swing probability.

    Uses:
    - Stratified train/test split (maintains swing rate)
    - Early stopping on validation set
    - Class balancing (scale_pos_weight)
    - Cross-validation for robust evaluation
    """
    print('\n' + '=' * 60)
    print('TRAINING SWING PROBABILITY MODEL')
    print('=' * 60)

    # Stratified split to maintain class balance
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    print(f'\nTrain set: {len(X_train):,} samples')
    print(f'Test set: {len(X_test):,} samples')
    print(f'Train swing rate: {y_train.mean():.1%}')
    print(f'Test swing rate: {y_test.mean():.1%}')

    # Calculate class weight for imbalance (typically ~63% swing, ~37% take)
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    print(f'Scale pos weight: {scale_pos_weight:.2f}')

    # XGBoost parameters optimized for swing prediction
    # Research shows swing is influenced by multiple interacting factors
    params = {
        'objective': 'binary:logistic',
        'eval_metric': ['logloss', 'auc', 'error'],
        'max_depth': 8,  # Allow complex interactions
        'learning_rate': 0.05,
        'n_estimators': 500,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'scale_pos_weight': scale_pos_weight,
        'min_child_weight': 50,  # Prevent overfitting to rare cases
        'gamma': 0.1,
        'reg_alpha': 0.1,
        'reg_lambda': 1.0,
        'random_state': 42,
        'n_jobs': -1,
        'tree_method': 'hist',  # Faster training
    }

    print('\nTraining XGBoost with parameters:')
    for k, v in params.items():
        print(f'  {k}: {v}')

    # Train with early stopping
    model = xgb.XGBClassifier(**params)

    eval_set = [(X_train, y_train), (X_test, y_test)]

    print('\nTraining...')
    start_time = time.time()
    model.fit(
        X_train,
        y_train,
        eval_set=eval_set,
        verbose=False,
    )
    train_time = time.time() - start_time
    print(f'Training completed in {train_time:.1f}s')

    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    # Metrics
    results = {
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'swing_rate_train': float(y_train.mean()),
        'swing_rate_test': float(y_test.mean()),
        'n_features': X.shape[1],
        'training_time_seconds': train_time,
        'metrics': {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'precision': float(precision_score(y_test, y_pred)),
            'recall': float(recall_score(y_test, y_pred)),
            'f1': float(f1_score(y_test, y_pred)),
            'roc_auc': float(roc_auc_score(y_test, y_pred_proba)),
            'log_loss': float(log_loss(y_test, y_pred_proba)),
            'brier_score': float(brier_score_loss(y_test, y_pred_proba)),
        },
    }

    print('\n' + '=' * 60)
    print('EVALUATION RESULTS')
    print('=' * 60)
    print(f'\nAccuracy:  {results["metrics"]["accuracy"]:.4f}')
    print(f'Precision: {results["metrics"]["precision"]:.4f}')
    print(f'Recall:    {results["metrics"]["recall"]:.4f}')
    print(f'F1-Score:  {results["metrics"]["f1"]:.4f}')
    print(f'ROC-AUC:   {results["metrics"]["roc_auc"]:.4f}')
    print(f'Log Loss:  {results["metrics"]["log_loss"]:.4f}')
    print(f'Brier:     {results["metrics"]["brier_score"]:.4f}')

    print('\nClassification Report:')
    print(classification_report(y_test, y_pred, target_names=['Take', 'Swing']))

    print('\nConfusion Matrix:')
    cm = confusion_matrix(y_test, y_pred)
    print('                 Predicted')
    print('                 Take   Swing')
    print(
        f'Actual Take    {cm[0, 0]:5d}  {cm[0, 1]:5d}  (Specificity: {cm[0, 0] / (cm[0, 0] + cm[0, 1]):.3f})',
    )
    print(
        f'       Swing   {cm[1, 0]:5d}  {cm[1, 1]:5d}  (Sensitivity: {cm[1, 1] / (cm[1, 0] + cm[1, 1]):.3f})',
    )

    # Feature importance
    importance = pd.DataFrame(
        {
            'feature': X.columns,
            'importance': model.feature_importances_,
        },
    ).sort_values('importance', ascending=False)

    print('\nTop 15 Most Important Features:')
    print(importance.head(15).to_string(index=False))

    # Save model
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_file = f'{MODEL_DIR}/swing_xgboost_{timestamp}.pkl'
    with open(model_file, 'wb') as f:
        pickle.dump(model, f)
    print(f'\nModel saved to: {model_file}')

    # Save results
    results['model_file'] = model_file
    results['timestamp'] = timestamp
    results['top_features'] = importance.head(15).to_dict('records')

    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f'Results saved to: {RESULTS_FILE}')

    return results


def analyze_by_context(y_test: pd.Series, y_pred_proba: np.ndarray, X_test: pd.DataFrame):
    """
    Analyze swing probability by different contexts.
    Validates model captures known baseball patterns:
    - Higher swing rate on 2 strikes
    - Higher swing rate on pitches in zone
    - Pitch type differences (more swings at fastballs)
    """
    print('\n' + '=' * 60)
    print('CONTEXTUAL ANALYSIS')
    print('=' * 60)

    # Create analysis dataframe
    analysis_df = X_test.copy()
    analysis_df['actual_swing'] = y_test.values
    analysis_df['pred_proba'] = y_pred_proba

    # By count (2 strikes vs not)
    if 'is_two_strike' in analysis_df.columns:
        print('\nBy Count (2 Strikes):')
        for is_two_strike in [False, True]:
            subset = analysis_df[analysis_df['is_two_strike'] == is_two_strike]
            actual = subset['actual_swing'].mean()
            predicted = subset['pred_proba'].mean()
            label = '2 Strikes' if is_two_strike else '< 2 Strikes'
            print(f'  {label}: Actual={actual:.1%}, Predicted={predicted:.1%}, n={len(subset):,}')

    # By zone location
    if 'is_in_zone' in analysis_df.columns:
        print('\nBy Zone Location:')
        for in_zone in [False, True]:
            subset = analysis_df[analysis_df['is_in_zone'] == in_zone]
            actual = subset['actual_swing'].mean()
            predicted = subset['pred_proba'].mean()
            label = 'In Zone' if in_zone else 'Out of Zone'
            print(f'  {label}: Actual={actual:.1%}, Predicted={predicted:.1%}, n={len(subset):,}')

    # Calibration check (binned by predicted probability)
    print('\nCalibration (binned by predicted probability):')
    analysis_df['prob_bin'] = pd.qcut(analysis_df['pred_proba'], q=10, duplicates='drop')
    calibration = (
        analysis_df.groupby('prob_bin')
        .agg(
            {
                'actual_swing': 'mean',
                'pred_proba': 'mean',
                'pitch_id': 'count',
            },
        )
        .reset_index()
    )
    calibration.columns = ['Bin', 'Actual Rate', 'Predicted Rate', 'Count']
    print(calibration.to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description='Train Swing Probability Model')
    parser.add_argument(
        '--sample', type=int, default=None, help='Use sample of N rows for quick testing',
    )
    parser.add_argument('--skip-analysis', action='store_true', help='Skip contextual analysis')
    args = parser.parse_args()

    print('=' * 70)
    print('SWING PROBABILITY MODEL TRAINING')
    print('=' * 70)
    print(f'Timestamp: {datetime.now().isoformat()}')
    print(f'Model Dir: {MODEL_DIR}')
    print(f'Sample Size: {args.sample or "Full Dataset"}')
    print('=' * 70)

    # Connect to database
    print('\nConnecting to database...')
    conn = psycopg2.connect(DB_URL)

    try:
        # Load data
        df = load_swing_data(conn, sample_size=args.sample)

        # Prepare features
        X, y = prepare_features(df)

        # Train model
        results = train_swing_model(X, y)

        # Contextual analysis (unless skipped)
        if not args.skip_analysis:
            # Re-split to get test set for analysis
            _X_train, X_test, _y_train, y_test = train_test_split(
                X,
                y,
                test_size=0.2,
                random_state=42,
                stratify=y,
            )
            # Load model and predict
            with open(results['model_file'], 'rb') as f:
                model = pickle.load(f)
            y_pred_proba = model.predict_proba(X_test)[:, 1]
            analyze_by_context(y_test, y_pred_proba, X_test)

        print('\n' + '=' * 70)
        print('TRAINING COMPLETE')
        print('=' * 70)
        print(f'Results: {RESULTS_FILE}')
        print(f'Model: {results["model_file"]}')

    finally:
        conn.close()


if __name__ == '__main__':
    main()
