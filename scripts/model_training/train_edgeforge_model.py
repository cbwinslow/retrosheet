#!/usr/bin/env python3
"""
EdgeForge: Train Enhanced MLB Win Probability Model
Focus: Calibrated betting edges with uncertainty quantification
"""

import os

import joblib
import pandas as pd
import psycopg2
from sklearn.calibration import calibration_curve
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split


def database_kwargs():
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def load_enhanced_training_data():
    """Load enhanced betting features for EdgeForge model."""
    print('📊 EdgeForge: Loading enhanced betting features...')

    conn = psycopg2.connect(**database_kwargs())

    query = """
    SELECT
        -- Basic game state
        inning, is_bottom_inning, outs_before, balls, strikes,
        score_diff, runners_on_base,

        -- Player performance
        batter_avg, pitcher_era, team_win_pct,

        -- Enhanced Statcast features
        pitch_velocity, pitch_spin_rate, pitch_distance_from_zone,

        -- Matchup edges
        matchup_experience, matchup_avg_vs_pitcher, matchup_slg_vs_pitcher,

        -- Situational betting factors
        high_leverage, close_game, runners_on,

        -- Target
        target

    FROM mlb_enhanced.betting_features
    WHERE batter_avg IS NOT NULL
      AND pitcher_era IS NOT NULL
      AND pitch_velocity IS NOT NULL
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    print(f'✅ Loaded {len(df)} enhanced training samples')
    print('.3f')
    print(f'   Enhanced features: {len(df.columns) - 1} (vs 15 basic)')

    return df


def prepare_betting_features(df):
    """Prepare features optimized for betting edge detection."""
    print('🎯 Preparing betting-optimized features...')

    # Create advanced betting features
    df['count_pressure'] = (df['balls'] - df['strikes']).clip(-2, 3)  # Count pressure
    df['momentum_shift'] = ((df['runners_on_base'] > 0) & (df['outs_before'] < 2)).astype(int)
    df['quality_matchup'] = ((df['batter_avg'] > 0.280) & (df['pitcher_era'] < 3.50)).astype(int)

    # Pitch effectiveness features
    df['pitch_effective'] = (
        (df['pitch_velocity'] > 92)
        | (df['pitch_spin_rate'] > 2500)
        | (df['pitch_distance_from_zone'] < 1.0)
    ).astype(int)

    # Matchup advantage features
    df['batter_advantage'] = (
        (df['matchup_avg_vs_pitcher'] > df['batter_avg'] + 0.030)
        | (df['matchup_slg_vs_pitcher'] > df['batter_avg'] * 1.2 + 0.100)
    ).astype(int)

    print(f'✅ Added {len(df.columns) - 23} advanced betting features')
    print(f'   Total features: {len(df.columns) - 1}')

    # Define final feature set
    feature_cols = [
        # Basic game state
        'inning',
        'is_bottom_inning',
        'outs_before',
        'balls',
        'strikes',
        'score_diff',
        'runners_on_base',
        # Player performance
        'batter_avg',
        'pitcher_era',
        'team_win_pct',
        # Statcast features
        'pitch_velocity',
        'pitch_spin_rate',
        'pitch_distance_from_zone',
        # Matchup features
        'matchup_experience',
        'matchup_avg_vs_pitcher',
        'matchup_slg_vs_pitcher',
        # Situational factors
        'high_leverage',
        'close_game',
        'runners_on',
        # Advanced betting features
        'count_pressure',
        'momentum_shift',
        'quality_matchup',
        'pitch_effective',
        'batter_advantage',
    ]

    X = df[feature_cols]
    y = df['target']

    print(f'🎲 Final feature set: {len(feature_cols)} features for betting edges')

    return X, y, feature_cols


def train_edgeforge_model(X, y):
    """Train EdgeForge model with betting-focused evaluation."""
    print('🤖 EdgeForge: Training enhanced win probability model...')

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
    print('.3f')
    # Train model
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_split=50,
        min_samples_leaf=25,
        random_state=42,
        n_jobs=-1,
        class_weight='balanced',
    )

    model.fit(X_train, y_train)

    # Evaluate with betting-relevant metrics
    train_pred = model.predict_proba(X_train)[:, 1]
    test_pred = model.predict_proba(X_test)[:, 1]

    # Standard metrics
    roc_auc_score(y_train, train_pred)
    roc_auc_score(y_test, test_pred)

    # Betting-specific metrics
    brier_score_loss(y_train, train_pred)
    brier_score_loss(y_test, test_pred)

    # Calibration analysis
    _prob_true, _prob_pred = calibration_curve(y_test, test_pred, n_bins=10)

    print('✅ EdgeForge model trained!')
    print('📊 Performance Metrics:')
    print('.3f')
    print('.3f')
    print('.3f')
    print('.4f')
    print('.4f')

    # Expected betting value analysis
    test_df = X_test.copy()
    test_df['prediction'] = test_pred
    test_df['actual'] = y_test

    # Analyze edge by confidence buckets
    test_df['confidence_bucket'] = pd.cut(
        test_df['prediction'],
        bins=[0, 0.4, 0.45, 0.55, 0.6, 1.0],
        labels=[
            'Strong_Favorite',
            'Favorite',
            'Toss_Up',
            'Underdog',
            'Strong_Underdog',
        ],
    )

    bucket_analysis = (
        test_df.groupby('confidence_bucket')
        .agg({'prediction': 'mean', 'actual': 'mean', 'prediction': 'count'})
        .round(4)
    )

    print('\n🎲 Confidence Bucket Analysis:')
    print('Bucket           | Pred | Actual | Samples | Edge')
    print('-' * 50)
    for _idx, row in bucket_analysis.iterrows():
        row['actual'] - row['prediction']
        print('15')

    return model, X_test, y_test, test_pred


def analyze_feature_importance(model, feature_cols):
    """Analyze which features drive betting edges."""
    print('📈 Analyzing feature importance for betting edges...')

    importance_df = pd.DataFrame(
        {'feature': feature_cols, 'importance': model.feature_importances_},
    ).sort_values('importance', ascending=False)

    print('🔝 Top 10 features driving betting edges:')
    for _i, _row in importance_df.head(10).iterrows():
        print('.3f')

    # Categorize features
    statcast_features = [f for f in feature_cols if 'pitch_' in f or 'distance' in f]
    matchup_features = [f for f in feature_cols if 'matchup' in f]
    situational_features = [
        f
        for f in feature_cols
        if f in ['high_leverage', 'close_game', 'runners_on', 'momentum_shift']
    ]
    basic_features = [
        f
        for f in feature_cols
        if f not in statcast_features + matchup_features + situational_features
    ]

    importance_df[importance_df['feature'].isin(statcast_features)]['importance'].sum()
    importance_df[importance_df['feature'].isin(matchup_features)]['importance'].sum()
    importance_df[importance_df['feature'].isin(situational_features)]['importance'].sum()
    importance_df[importance_df['feature'].isin(basic_features)]['importance'].sum()

    print('\n📊 Feature Category Importance:')
    print('.1%')
    print('.1%')
    print('.1%')
    print('.1%')

    return importance_df


def save_edgeforge_model(model, feature_cols):
    """Save EdgeForge model with betting intelligence metadata."""
    print('💾 Saving EdgeForge betting model...')

    # Create models directory
    os.makedirs('models', exist_ok=True)

    # Save model
    model_path = 'models/edgeforge_win_probability.pkl'
    joblib.dump(model, model_path)

    # Save metadata for betting applications
    metadata = {
        'model_type': 'EdgeForge Win Probability',
        'training_date': pd.Timestamp.now().isoformat(),
        'features': feature_cols,
        'description': 'Enhanced MLB win probability model for betting edges',
        'use_cases': [
            'Live game win probability updates',
            'Betting market edge detection',
            'Situational betting analysis',
            'Player matchup evaluation',
        ],
        'performance_targets': {
            'auc_target': 0.88,
            'calibration_target': 'Well-calibrated for betting',
            'edge_threshold': '0.02+ advantage over market',
        },
        'risk_controls': [
            'Confidence tier filtering',
            'Bankroll management integration',
            'Market liquidity awareness',
            'Auto-pause on edge decay',
        ],
    }

    metadata_path = 'models/edgeforge_metadata.pkl'
    joblib.dump(metadata, metadata_path)

    print(f'✅ EdgeForge model saved to {model_path}')
    print(f'✅ Betting metadata saved to {metadata_path}')


def main():
    print('🎯 EdgeForge: Enhanced MLB Win Probability Model')
    print('=' * 55)
    print('📊 Focus: Calibrated betting edges over hype')
    print('🎲 Goal: Monetizable sports intelligence platform')
    print('💰 Target: 0.88+ AUC with betting market integration')

    # Load enhanced data
    df = load_enhanced_training_data()

    # Prepare betting features
    X, y, feature_cols = prepare_betting_features(df)

    # Train EdgeForge model
    model, _X_test, _y_test, _test_pred = train_edgeforge_model(X, y)

    # Analyze feature importance
    analyze_feature_importance(model, feature_cols)

    # Save model
    save_edgeforge_model(model, feature_cols)

    print('\n' + '=' * 55)
    print('🎉 EDGEFORGE MODEL COMPLETE')
    print('=' * 55)
    print('✅ Enhanced features: Statcast + matchups + situational')
    print('✅ Betting-focused evaluation: AUC + calibration + buckets')
    print('✅ Feature importance: Identified key betting edges')
    print('✅ Production-ready: Saved for live betting applications')

    print('\n💰 MONETIZATION PATHS:')
    print('• Live win probability feeds')
    print('• Premium betting edge alerts')
    print('• Situational betting analysis')
    print('• Player prop market insights')

    print('\n🎲 Next: Integrate with betting markets + deploy live scoring')


if __name__ == '__main__':
    main()
