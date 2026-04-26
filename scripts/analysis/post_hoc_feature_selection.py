"""
Post-Hoc Feature Selection Workflow

Smart workflow for finding optimal features:
1. Train ONE model with ALL 220+ features
2. Extract feature importance from trained model
3. Test progressively smaller feature sets (top 200, 150, 100, 75, 50, 30, 20)
4. Stop when performance plateaus
5. Retrain final model with optimal feature count

This is MORE efficient than ablation study:
- 1 full training + 5-6 small retrainings
- vs 6 full ablation runs

Can test PAST 50 features to find if 100, 150, or 200 features are optimal.

Usage:
    # Step 1: Train with all features and extract importance
    uv run python scripts/analysis/post_hoc_feature_selection.py --phase 1 --sample 100000

    # Step 2: Test progressively smaller feature sets (default: 200,150,100,75,50,30,20)
    uv run python scripts/analysis/post_hoc_feature_selection.py --phase 2

    # Step 2 with custom sizes: Test if 150 or 100 features are optimal
    uv run python scripts/analysis/post_hoc_feature_selection.py --phase 2 --subset-sizes "200,150,100,75,50"

    # Step 3: Retrain final model with optimal features
    uv run python scripts/analysis/post_hoc_feature_selection.py --phase 3 --n-features 75
"""

import argparse
import json
import os
import pickle
from datetime import datetime

import numpy as np
import pandas as pd
import psycopg2
import xgboost as xgb
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split


DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/retrosheet')
RESULTS_DIR = 'models/post_hoc_selection'
os.makedirs(RESULTS_DIR, exist_ok=True)


def load_data_with_features(conn, features: list[str], sample_size: int) -> tuple[pd.DataFrame, pd.Series]:
    """Load data with specified features."""

    feature_cols = ', '.join([f'ef."{f}"' for f in features])

    query = f"""
    SELECT
        ef.pitch_id,
        ef.outcome_tier1 as target,
        {feature_cols}
    FROM features_pitch.engineered_features ef
    WHERE ef.outcome_tier1 IS NOT NULL
      AND ef.outcome_tier1 != 'U'
    LIMIT {sample_size}
    """

    df = pd.read_sql(query, conn)

    y = df['target']
    X = df.drop(['target', 'pitch_id'], axis=1)

    # Handle missing values
    X = X.fillna(X.median())

    # Encode target
    y_encoded = pd.Categorical(y).codes

    return X, pd.Series(y_encoded, index=y.index)


def phase_1_train_full_model(sample_size: int = 100000):
    """
    Phase 1: Train ONE model with ALL available features.
    Extract and save feature importance.
    """

    print('='*70)
    print('PHASE 1: Train Full Model with All Features')
    print('='*70)

    conn = psycopg2.connect(DB_URL)

    try:
        # Get all numeric features
        query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'features_pitch'
          AND table_name = 'engineered_features'
          AND data_type IN ('integer', 'numeric', 'real', 'double precision')
          AND column_name NOT IN (
              'pitch_id', 'game_pk', 'batter_id', 'pitcher_id',
              'outcome_tier1', 'outcome_tier2', 'swing_decision',
              'engineered_at', 'is_valid_for_training'
          )
        """

        features_df = pd.read_sql(query, conn)
        all_features = features_df['column_name'].tolist()

        print(f'Found {len(all_features)} features')
        print(f'Loading {sample_size:,} samples...')

        # Load data
        X, y = load_data_with_features(conn, all_features, sample_size)

        print(f'Data shape: {X.shape}')
        print(f'\nTraining XGBoost with ALL {X.shape[1]} features...')

        # Train model
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y,
        )

        model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=len(np.unique(y)),
            max_depth=6,
            learning_rate=0.1,
            n_estimators=200,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            tree_method='hist',
            eval_metric='mlogloss',
        )

        model.fit(X_train, y_train, verbose=False)

        # Evaluate
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)

        full_results = {
            'n_features': X.shape[1],
            'sample_size': sample_size,
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'log_loss': float(log_loss(y_test, y_pred_proba)),
            'auc': float(roc_auc_score(y_test, y_pred_proba, multi_class='ovo')),
        }

        print('\nFull Model Performance:')
        print(f"  Accuracy: {full_results['accuracy']:.4f}")
        print(f"  Log Loss: {full_results['log_loss']:.4f}")
        print(f"  AUC:      {full_results['auc']:.4f}")

        # Extract feature importance using sklearn API
        importance_scores = model.feature_importances_

        # Convert to sorted list
        feature_importance = []
        for i, feat in enumerate(X.columns):
            score = importance_scores[i]
            feature_importance.append({
                'feature': feat,
                'importance': float(score),
                'rank': 0,  # Will fill in after sorting
            })

        # Sort by importance
        feature_importance.sort(key=lambda x: x['importance'], reverse=True)

        # Assign ranks and cumulative importance
        total_importance = sum(x['importance'] for x in feature_importance)
        cumsum = 0
        for i, fi in enumerate(feature_importance):
            fi['rank'] = i + 1
            cumsum += fi['importance']
            fi['cumulative_pct'] = round(cumsum / total_importance * 100, 2) if total_importance > 0 else 0

        print('\nTop 10 Most Important Features:')
        for fi in feature_importance[:10]:
            print(f"  {fi['rank']:2d}. {fi['feature'][:40]:40} = {fi['importance']:,.0f} ({fi['cumulative_pct']:.1f}%)")

        # Save everything
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save model
        model_file = f'{RESULTS_DIR}/full_model_{timestamp}.pkl'
        with open(model_file, 'wb') as f:
            pickle.dump(model, f)

        # Save importance
        importance_file = f'{RESULTS_DIR}/feature_importance_{timestamp}.json'
        with open(importance_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'n_features': len(feature_importance),
                'full_model_performance': full_results,
                'feature_importance': feature_importance,
            }, f, indent=2)

        print('\nSaved:')
        print(f'  Model: {model_file}')
        print(f'  Importance: {importance_file}')

        return importance_file

    finally:
        conn.close()


def phase_2_test_feature_subsets(
    importance_file: str,
    sample_size: int = 50000,
    subset_sizes: list = None,
):
    """
    Phase 2: Test progressively smaller feature subsets.
    Train models with top N features for various N values.

    Default tests: [200, 150, 100, 75, 50, 30, 20] or configurable.
    Can test BEYOND 50 features (e.g., 200, 150) to find optimal point.
    """

    print('='*70)
    print('PHASE 2: Test Progressive Feature Subsets')
    print('='*70)

    # Load importance
    with open(importance_file) as f:
        importance_data = json.load(f)

    feature_importance = importance_data['feature_importance']
    full_performance = importance_data['full_model_performance']

    available_features = len(feature_importance)
    print(f'Total available features: {available_features}')

    # Default subset sizes - can go PAST 50 features (e.g., 200, 150)
    if subset_sizes is None:
        # Smart default: test from ~90% of features down to 20
        subset_sizes = []
        if available_features >= 200:
            subset_sizes.extend([200, 175, 150])
        elif available_features >= 150:
            subset_sizes.extend([150, 125])
        elif available_features >= 100:
            subset_sizes.append(100)

        # Always test these smaller sizes
        subset_sizes.extend([75, 50, 30, 20])

    # Filter to available features
    subset_sizes = [s for s in subset_sizes if s <= available_features and s >= 10]
    # Remove duplicates and sort descending
    subset_sizes = sorted(list(set(subset_sizes)), reverse=True)

    print(f'Testing {len(subset_sizes)} subset sizes: {subset_sizes}')
    print(f"Full model baseline: AUC={full_performance['auc']:.4f}")

    conn = psycopg2.connect(DB_URL)

    try:
        results = []

        for n_features in subset_sizes:
            print(f"\n{'='*70}")
            print(f'Testing with TOP {n_features} features')
            print(f"{'='*70}")

            # Get top N features
            top_features = [fi['feature'] for fi in feature_importance[:n_features]]

            print('Loading data...')
            X, y = load_data_with_features(conn, top_features, sample_size)

            print(f'Training with {X.shape[1]} features...')

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y,
            )

            model = xgb.XGBClassifier(
                objective='multi:softprob',
                num_class=len(np.unique(y)),
                max_depth=6,
                learning_rate=0.1,
                n_estimators=200,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                tree_method='hist',
                eval_metric='mlogloss',
            )

            model.fit(X_train, y_train, verbose=False)

            # Evaluate
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test)

            result = {
                'n_features': int(n_features),
                'accuracy': float(accuracy_score(y_test, y_pred)),
                'log_loss': float(log_loss(y_test, y_pred_proba)),
                'auc': float(roc_auc_score(y_test, y_pred_proba, multi_class='ovo')),
                'auc_vs_full': 0.0,  # Will calculate
                'features': top_features[:5],  # Store first 5 for reference
            }

            result['auc_vs_full'] = round(result['auc'] - full_performance['auc'], 4)

            results.append(result)

            print(f"  Accuracy: {result['accuracy']:.4f}")
            print(f"  AUC:      {result['auc']:.4f} ({result['auc_vs_full']:+.4f} vs full)")

            # Early stopping: if performance within 0.5% of full, this is optimal
            if result['auc_vs_full'] > -0.005:
                print('  ✓ Performance within 0.5% of full model - OPTIMAL POINT FOUND')

        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f'{RESULTS_DIR}/subset_results_{timestamp}.json'

        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'full_model_auc': full_performance['auc'],
                'results': results,
            }, f, indent=2)

        print(f"\n{'='*70}")
        print('PHASE 2 COMPLETE')
        print(f"{'='*70}")
        print(f'Results saved: {results_file}')

        # Find optimal
        best = max(results, key=lambda x: x['auc'])
        print(f"\nBest performance: {best['auc']:.4f} with {best['n_features']} features")

        # Find smallest within 0.5% of full
        threshold = full_performance['auc'] - 0.005
        efficient = [r for r in results if r['auc'] >= threshold]
        if efficient:
            smallest_efficient = min(efficient, key=lambda x: x['n_features'])
            print(f"Most efficient: {smallest_efficient['auc']:.4f} with {smallest_efficient['n_features']} features")
            print(f"  ({smallest_efficient['n_features']}/{available_features} = {smallest_efficient['n_features']/available_features:.0%} of features)")

        return results_file

    finally:
        conn.close()


def phase_3_train_final_model(n_features: int, sample_size: int = 200000):
    """
    Phase 3: Retrain final model with optimal feature count on more data.
    """

    print('='*70)
    print(f'PHASE 3: Train Final Model with {n_features} Features')
    print('='*70)

    # Load importance to get features
    importance_files = sorted([f for f in os.listdir(RESULTS_DIR) if f.startswith('feature_importance_')])
    if not importance_files:
        print('Error: No importance file found. Run Phase 1 first.')
        return

    with open(f'{RESULTS_DIR}/{importance_files[-1]}') as f:
        importance_data = json.load(f)

    feature_importance = importance_data['feature_importance']
    top_features = [fi['feature'] for fi in feature_importance[:n_features]]

    print(f'Using top {n_features} features')
    print(f'Training on {sample_size:,} samples...')

    conn = psycopg2.connect(DB_URL)

    try:
        X, y = load_data_with_features(conn, top_features, sample_size)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y,
        )

        print(f'Final training: {X_train.shape}')

        model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=len(np.unique(y)),
            max_depth=8,              # Slightly deeper for final model
            learning_rate=0.05,       # Lower LR for final model
            n_estimators=500,         # More trees
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            n_jobs=-1,
            tree_method='hist',
            eval_metric='mlogloss',
        )

        model.fit(X_train, y_train, verbose=False)

        # Evaluate
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)

        final_results = {
            'n_features': n_features,
            'sample_size': sample_size,
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'log_loss': float(log_loss(y_test, y_pred_proba)),
            'auc': float(roc_auc_score(y_test, y_pred_proba, multi_class='ovo')),
            'features_used': top_features,
        }

        print('\nFinal Model Performance:')
        print(f"  Accuracy: {final_results['accuracy']:.4f}")
        print(f"  Log Loss: {final_results['log_loss']:.4f}")
        print(f"  AUC:      {final_results['auc']:.4f}")

        # Save
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_file = f'models/pitch_tier1/final_model_{n_features}features_{timestamp}.pkl'
        results_file = f'models/pitch_tier1/final_results_{n_features}features_{timestamp}.json'

        with open(model_file, 'wb') as f:
            pickle.dump(model, f)

        with open(results_file, 'w') as f:
            json.dump(final_results, f, indent=2)

        print('\nSaved:')
        print(f'  Model: {model_file}')
        print(f'  Results: {results_file}')

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Post-Hoc Feature Selection')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3], required=True,
                       help='Which phase to run')
    parser.add_argument('--sample-size', type=int, default=100000,
                       help='Sample size for training')
    parser.add_argument('--n-features', type=int, default=50,
                       help='Number of features for Phase 3')
    parser.add_argument('--importance-file', type=str,
                       help='Path to importance file for Phase 2')
    parser.add_argument('--subset-sizes', type=str,
                       help='Comma-separated list of feature counts to test in Phase 2. '
                            'Can test PAST 50 features (e.g., "200,150,100,75,50,30,20")')
    args = parser.parse_args()

    if args.phase == 1:
        phase_1_train_full_model(args.sample_size)

    elif args.phase == 2:
        if args.importance_file:
            importance_file = args.importance_file
        else:
            # Find latest importance file
            files = sorted([f for f in os.listdir(RESULTS_DIR) if f.startswith('feature_importance_')])
            if not files:
                print('Error: No importance file found. Run Phase 1 first.')
                return
            importance_file = f'{RESULTS_DIR}/{files[-1]}'

        # Parse custom subset sizes if provided
        subset_sizes = None
        if args.subset_sizes:
            subset_sizes = [int(s.strip()) for s in args.subset_sizes.split(',')]
            print(f'Custom subset sizes: {subset_sizes}')

        phase_2_test_feature_subsets(importance_file, args.sample_size, subset_sizes)

    elif args.phase == 3:
        phase_3_train_final_model(args.n_features, args.sample_size)


if __name__ == '__main__':
    main()
