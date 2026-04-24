#!/usr/bin/env python3
"""
Train a basic win probability model using the MLB features.
"""

import os

import joblib
import pandas as pd
import psycopg2
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split


def database_kwargs():
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def load_training_data():
    """Load training data from PostgreSQL."""
    print('📊 Loading training data...')

    conn = psycopg2.connect(**database_kwargs())

    query = """
    SELECT
        inning,
        is_bottom_inning,
        outs_before,
        balls,
        strikes,
        score_diff,
        runners_on_base,
        batter_avg,
        pitcher_era,
        team_win_pct,
        batting_team_wins as target
    FROM mlb_models.win_probability_training
    WHERE inning <= 9  -- Focus on regulation innings
      AND batter_avg IS NOT NULL
      AND pitcher_era IS NOT NULL
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    print(f'✅ Loaded {len(df)} training samples')
    print(f'   Win rate: {df["target"].mean():.3f}')
    print(f'   Features: {list(df.columns[:-1])}')

    return df


def prepare_features(df):
    """Prepare features for modeling."""
    print('🔧 Preparing features...')

    # Convert boolean to int
    df['is_bottom_inning'] = df['is_bottom_inning'].astype(int)

    # Create runners on base features
    df['runner_on_1b'] = (df['runners_on_base'] & 1).astype(int)
    df['runner_on_2b'] = (df['runners_on_base'] & 2).astype(int)
    df['runner_on_3b'] = (df['runners_on_base'] & 4).astype(int)

    # Create count features
    df['total_pitches'] = df['balls'] + df['strikes']
    df['is_two_strike'] = (df['strikes'] >= 2).astype(int)
    df['is_three_ball'] = (df['balls'] >= 3).astype(int)

    # Drop original runners column
    df = df.drop('runners_on_base', axis=1)

    # Define feature columns
    feature_cols = [
        'inning',
        'is_bottom_inning',
        'outs_before',
        'balls',
        'strikes',
        'score_diff',
        'runner_on_1b',
        'runner_on_2b',
        'runner_on_3b',
        'batter_avg',
        'pitcher_era',
        'team_win_pct',
        'total_pitches',
        'is_two_strike',
        'is_three_ball',
    ]

    X = df[feature_cols]
    y = df['target']

    print(f'✅ Prepared {len(feature_cols)} features')
    return X, y, feature_cols


def train_model(X, y):
    """Train a Random Forest model."""
    print('🤖 Training win probability model...')

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    print(f'   Training set: {len(X_train)} samples')
    print(f'   Test set: {len(X_test)} samples')

    # Train model
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)

    model.fit(X_train, y_train)

    # Evaluate
    train_pred = model.predict_proba(X_train)[:, 1]
    test_pred = model.predict_proba(X_test)[:, 1]

    train_auc = roc_auc_score(y_train, train_pred)
    test_auc = roc_auc_score(y_test, test_pred)

    print('✅ Model trained!')
    print(f'   Train AUC: {train_auc:.3f}')
    print(f'   Test AUC: {test_auc:.3f}')

    return model, X_test, y_test


def save_model(model, feature_cols):
    """Save the trained model."""
    print('💾 Saving model...')

    # Create models directory
    os.makedirs('models', exist_ok=True)

    # Save model
    model_path = 'models/win_probability_model.pkl'
    joblib.dump(model, model_path)

    # Save feature info
    feature_info = {
        'feature_columns': feature_cols,
        'model_type': 'RandomForestClassifier',
        'training_date': pd.Timestamp.now().isoformat(),
        'description': 'MLB Win Probability Model v1.0',
    }

    info_path = 'models/model_info.pkl'
    joblib.dump(feature_info, info_path)

    print(f'✅ Model saved to {model_path}')
    print(f'✅ Feature info saved to {info_path}')


def main():
    print('🎯 MLB Win Probability Model Training')
    print('=' * 50)

    # Load data
    df = load_training_data()

    # Prepare features
    X, y, feature_cols = prepare_features(df)

    # Train model
    model, _X_test, _y_test = train_model(X, y)

    # Save model
    save_model(model, feature_cols)

    print('\n🎉 Model training complete!')
    print('\nNext steps:')
    print('1. Evaluate model performance on test data')
    print('2. Add more features (pitch physics, matchup history)')
    print('3. Tune hyperparameters')
    print('4. Deploy for real-time predictions')


if __name__ == '__main__':
    main()
