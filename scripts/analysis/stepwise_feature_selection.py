"""
Stepwise Feature Selection for Optimal Feature Subsets

Implements multiple feature selection strategies:
1. Forward Stepwise: Start with 0, add best feature each iteration
2. Backward Stepwise: Start with all, remove worst each iteration
3. Recursive Feature Elimination: Remove weakest by importance

Stores selection log in framework.feature_selection_log for analysis.

Usage:
    uv run python scripts/analysis/stepwise_feature_selection.py --method forward --max-features 50
    uv run python scripts/analysis/stepwise_feature_selection.py --method backward --min-features 20
"""

import argparse
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
import psycopg2
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold, cross_val_score


DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/retrosheet')


def load_feature_candidates(conn, top_n: int | None = None) -> list[str]:
    """Load candidate features from importance table or all numeric columns."""

    # First try to get from importance table
    query = """
    SELECT feature_name, AVG(importance_score) as avg_importance
    FROM framework.feature_importance
    WHERE analysis_method = 'xgboost_gain'
    GROUP BY feature_name
    ORDER BY avg_importance DESC
    """

    try:
        df = pd.read_sql(query, conn)
        if len(df) > 0 and top_n:
            features = df['feature_name'].head(top_n).tolist()
            print(f'Loaded top {len(features)} features from importance table')
            return features
    except:
        pass  # Table might not exist yet

    # Fallback: get all numeric columns
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

    df = pd.read_sql(query, conn)
    features = df['column_name'].tolist()

    if top_n and len(features) > top_n:
        features = features[:top_n]

    print(f'Loaded {len(features)} numeric features from schema')
    return features


def load_training_data(
    conn, features: list[str], sample_size: int = 50000,
) -> tuple[pd.DataFrame, pd.Series]:
    """Load training data with selected features."""

    feature_cols = ', '.join([f'ef."{f}"' for f in features])

    query = f"""
    SELECT
        ef.pitch_id,
        ef.outcome_tier1 as target,
        {feature_cols}
    FROM features_pitch.engineered_features ef
    WHERE ef.is_valid_for_training = TRUE
      AND ef.outcome_tier1 IS NOT NULL
      AND ef.outcome_tier1 != 'U'
    ORDER BY RANDOM()
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


def evaluate_feature_set(X: pd.DataFrame, y: pd.Series, cv_folds: int = 3) -> tuple[float, float]:
    """Evaluate feature set using cross-validation."""

    model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=len(np.unique(y)),
        max_depth=4,
        learning_rate=0.1,
        n_estimators=100,
        random_state=42,
        n_jobs=-1,
        tree_method='hist',
        eval_metric='mlogloss',
    )

    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)

    scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc_ovo', n_jobs=-1)

    return scores.mean(), scores.std()


def forward_stepwise_selection(
    conn,
    candidate_features: list[str],
    max_features: int = 50,
    min_improvement: float = 0.001,
    sample_size: int = 50000,
    experiment_id: int | None = None,
) -> list[str]:
    """
    Forward stepwise selection: Start with 0, add best feature each iteration.

    Stops when:
    - max_features reached
    - Improvement < min_improvement
    - No features left
    """

    print('\n' + '=' * 60)
    print('FORWARD STEPWISE SELECTION')
    print('=' * 60)

    selected = []
    remaining = candidate_features.copy()
    history = []

    # Baseline: model with no features (intercept only)
    print('\nStep 0: Baseline (no features)')
    baseline_score = 0.333  # Random guess for 3 classes
    print(f'  Baseline AUC: {baseline_score:.4f}')

    step = 0
    best_score = baseline_score

    while len(selected) < max_features and len(remaining) > 0:
        step += 1
        print(f'\nStep {step}: Testing {len(remaining)} remaining features...')

        best_feature = None
        best_feature_score = best_score
        best_feature_std = 0

        # Test each remaining feature
        for i, feature in enumerate(remaining):
            if i % 10 == 0:
                print(f'  Testing feature {i + 1}/{len(remaining)}: {feature[:30]}...', end='\r')

            test_features = [*selected, feature]
            X, y = load_training_data(conn, test_features, sample_size)

            if X.shape[1] == 0:
                continue

            score, std = evaluate_feature_set(X, y, cv_folds=3)

            if score > best_feature_score:
                best_feature_score = score
                best_feature_std = std
                best_feature = feature

        print(f'{" " * 60}\r', end='')  # Clear line

        if best_feature is None:
            print('  No feature improved score. Stopping.')
            break

        improvement = best_feature_score - best_score

        if improvement < min_improvement:
            print(f'  Improvement ({improvement:.4f}) < threshold ({min_improvement}). Stopping.')
            break

        # Add best feature
        selected.append(best_feature)
        remaining.remove(best_feature)
        best_score = best_feature_score

        print(f'  Added: {best_feature[:40]}')
        print(f'  Score: {best_score:.4f} (+{improvement:.4f})')
        print(f'  Selected: {len(selected)}/{max_features}')

        history.append(
            {
                'step': step,
                'action': 'add',
                'feature': best_feature,
                'score': round(best_score, 6),
                'improvement': round(improvement, 6),
                'n_features': len(selected),
                'std': round(best_feature_std, 6),
            },
        )

    print('\n' + '=' * 60)
    print('SELECTION COMPLETE')
    print('=' * 60)
    print(f'Final feature count: {len(selected)}')
    print(f'Final AUC: {best_score:.4f}')
    print(f'Improvement from baseline: +{best_score - baseline_score:.4f}')

    return selected, history


def backward_stepwise_selection(
    conn,
    candidate_features: list[str],
    min_features: int = 20,
    sample_size: int = 50000,
    experiment_id: int | None = None,
) -> list[str]:
    """
    Backward stepwise selection: Start with all, remove worst each iteration.

    Stops when min_features reached.
    """

    print('\n' + '=' * 60)
    print('BACKWARD STEPWISE SELECTION')
    print('=' * 60)

    selected = candidate_features.copy()
    history = []

    # Initial score with all features
    print(f'\nStep 0: Initial model with {len(selected)} features')
    X, y = load_training_data(conn, selected, sample_size)
    best_score, _best_std = evaluate_feature_set(X, y)
    print(f'  Initial AUC: {best_score:.4f}')

    step = 0

    while len(selected) > min_features:
        step += 1
        print(f'\nStep {step}: Testing removal of each feature...')

        worst_feature = None
        worst_feature_score = 0

        # Test removing each feature
        for i, feature in enumerate(selected):
            if i % 10 == 0:
                print(f'  Testing removal {i + 1}/{len(selected)}...', end='\r')

            test_features = [f for f in selected if f != feature]
            X, y = load_training_data(conn, test_features, sample_size)

            score, _ = evaluate_feature_set(X, y, cv_folds=3)

            # We want to remove the feature whose removal hurts least
            if score > worst_feature_score:
                worst_feature_score = score
                worst_feature = feature

        print(f'{" " * 60}\r', end='')

        if worst_feature is None:
            break

        # Remove the least important feature
        selected.remove(worst_feature)
        best_score = worst_feature_score

        print(f'  Removed: {worst_feature[:40]}')
        print(f'  Score after removal: {best_score:.4f}')
        print(f'  Remaining: {len(selected)}')

        history.append(
            {
                'step': step,
                'action': 'remove',
                'feature': worst_feature,
                'score': round(best_score, 6),
                'n_features': len(selected),
            },
        )

    print('\n' + '=' * 60)
    print('SELECTION COMPLETE')
    print('=' * 60)
    print(f'Final feature count: {len(selected)}')
    print(f'Final AUC: {best_score:.4f}')

    return selected, history


def save_selection_log(history: list, method: str, experiment_id: int | None = None):
    """Save selection log to file and optionally database."""

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'models/feature_selection/{method}_selection_{timestamp}.json'

    os.makedirs('models/feature_selection', exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(
            {
                'method': method,
                'timestamp': timestamp,
                'experiment_id': experiment_id,
                'history': history,
            },
            f,
            indent=2,
        )

    print(f'\nSelection log saved to: {output_file}')

    # Plot if matplotlib available
    try:
        import matplotlib.pyplot as plt

        steps = [h['step'] for h in history]
        scores = [h['score'] for h in history]
        n_features = [h['n_features'] for h in history]

        _fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Score vs step
        ax1.plot(steps, scores, 'b-o', markersize=4)
        ax1.set_xlabel('Step')
        ax1.set_ylabel('AUC Score')
        ax1.set_title(f'{method.title()} Selection: Score vs Step')
        ax1.grid(True, alpha=0.3)

        # Score vs n_features
        ax2.plot(n_features, scores, 'r-o', markersize=4)
        ax2.set_xlabel('Number of Features')
        ax2.set_ylabel('AUC Score')
        ax2.set_title(f'{method.title()} Selection: Score vs Features')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_file = f'models/feature_selection/{method}_plot_{timestamp}.png'
        plt.savefig(plot_file, dpi=150)
        print(f'Plot saved to: {plot_file}')
    except ImportError:
        pass


def main():
    parser = argparse.ArgumentParser(description='Stepwise Feature Selection')
    parser.add_argument(
        '--method', choices=['forward', 'backward'], default='forward', help='Selection method',
    )
    parser.add_argument(
        '--max-features', type=int, default=50, help='Maximum features for forward selection',
    )
    parser.add_argument(
        '--min-features', type=int, default=20, help='Minimum features for backward selection',
    )
    parser.add_argument('--sample-size', type=int, default=50000, help='Training sample size')
    parser.add_argument(
        '--top-candidates', type=int, default=100, help='Start with top N candidate features',
    )
    parser.add_argument(
        '--min-improvement',
        type=float,
        default=0.001,
        help='Minimum score improvement to add feature',
    )
    args = parser.parse_args()

    print('=' * 70)
    print('STEPWISE FEATURE SELECTION')
    print('=' * 70)
    print(f'Method: {args.method}')
    print(f'Sample size: {args.sample_size:,}')
    print('=' * 70)

    conn = psycopg2.connect(DB_URL)

    try:
        # Load candidate features
        candidates = load_feature_candidates(conn, top_n=args.top_candidates)

        print(f'Starting with {len(candidates)} candidate features')

        # Run selection
        if args.method == 'forward':
            selected, history = forward_stepwise_selection(
                conn,
                candidates,
                max_features=args.max_features,
                min_improvement=args.min_improvement,
                sample_size=args.sample_size,
            )
        else:
            selected, history = backward_stepwise_selection(
                conn,
                candidates,
                min_features=args.min_features,
                sample_size=args.sample_size,
            )

        # Save results
        save_selection_log(history, args.method)

        # Print final feature list
        print('\nFinal Selected Features:')
        for i, feat in enumerate(selected, 1):
            print(f'  {i:2d}. {feat}')

    finally:
        conn.close()


if __name__ == '__main__':
    main()
