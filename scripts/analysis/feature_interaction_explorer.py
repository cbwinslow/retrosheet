"""
Feature Interaction Explorer - Discover Non-Linear Feature Pairs

Tests pairwise feature interactions to find combinations that predict
outcomes better than individual features alone.

Methods:
1. Correlation of interaction with target
2. XGBoost interaction importance (gain from feature pairs)
3. Polynomial feature testing (x1 * x2)

Helps answer:
- Which feature pairs are most predictive together?
- Do interactions like (velocity * location) matter?
- Should we add interaction terms to the model?

Usage:
    uv run python scripts/analysis/feature_interaction_explorer.py --top-features 20
"""

import argparse
import json
import os
from datetime import datetime
from itertools import combinations

import numpy as np
import pandas as pd
import psycopg2
import xgboost as xgb
from sklearn.metrics import mutual_info_classif


DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/retrosheet')


def load_top_features(conn, n_features: int = 20, sample_size: int = 50000) -> pd.DataFrame:
    """Load top features by importance."""

    print(f'Loading top {n_features} features...')

    # Try to get from importance table first
    query = f"""
    SELECT feature_name
    FROM analysis.feature_importance
    WHERE analysis_method = 'xgboost_gain'
    GROUP BY feature_name
    ORDER BY AVG(importance_score) DESC
    LIMIT {n_features}
    """

    try:
        features_df = pd.read_sql(query, conn)
        if len(features_df) > 0:
            features = features_df['feature_name'].tolist()
            print(f'Loaded {len(features)} features from importance table')
        else:
            raise Exception('No importance data')
    except:
        # Fallback to numeric columns
        query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'features_pitch'
          AND table_name = 'engineered_features'
          AND data_type IN ('integer', 'numeric', 'real', 'double precision')
          AND column_name NOT IN (
              'pitch_id', 'game_pk', 'batter_id', 'pitcher_id',
              'outcome_tier1', 'outcome_tier2', 'swing_decision'
          )
        LIMIT 30
        """
        features_df = pd.read_sql(query, conn)
        features = features_df['column_name'].tolist()
        print(f'Loaded {len(features)} numeric features from schema')

    # Load data
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
    print(f'Loaded {len(df)} samples with {len(features)} features')

    return df, features


def test_interaction(
    df: pd.DataFrame,
    f1: str,
    f2: str,
    target: pd.Series,
    method: str = 'mutual_info',
) -> dict:
    """Test the predictive power of a feature interaction."""

    # Get feature values
    x1 = df[f1].fillna(df[f1].median()).values
    x2 = df[f2].fillna(df[f2].median()).values
    y = target.values

    # Individual mutual information
    mi1 = mutual_info_classif(x1.reshape(-1, 1), y, random_state=42)[0]
    mi2 = mutual_info_classif(x2.reshape(-1, 1), y, random_state=42)[0]

    # Interaction term (product)
    interaction = (x1 * x2).reshape(-1, 1)
    mi_interaction = mutual_info_classif(interaction, y, random_state=42)[0]

    # Interaction gain over individual features
    max_individual = max(mi1, mi2)
    interaction_gain = mi_interaction - max_individual

    # Correlation between features
    feature_corr = np.corrcoef(x1, x2)[0, 1]

    return {
        'feature_1': f1,
        'feature_2': f2,
        'mi_feature_1': round(float(mi1), 6),
        'mi_feature_2': round(float(mi2), 6),
        'mi_interaction': round(float(mi_interaction), 6),
        'interaction_gain': round(float(interaction_gain), 6),
        'feature_correlation': round(float(feature_corr), 4),
        'is_synergistic': bool(interaction_gain > 0.01),  # Threshold
    }


def find_top_interactions(
    df: pd.DataFrame,
    features: list[str],
    target: pd.Series,
    top_n: int = 50,
) -> list[dict]:
    """Find top feature interactions."""

    print(f'\nTesting {len(features)} choose 2 = {len(features) * (len(features) - 1) // 2} interactions...')

    interactions = []
    tested = 0

    for f1, f2 in combinations(features, 2):
        tested += 1
        if tested % 50 == 0:
            print(f'  Tested {tested} interactions...', end='\r')

        try:
            result = test_interaction(df, f1, f2, target)
            interactions.append(result)
        except Exception:
            # Skip problematic pairs
            continue

    print(f"{' '*50}\r", end='')
    print(f'Tested {tested} interactions')

    # Sort by interaction gain
    interactions.sort(key=lambda x: x['mi_interaction'], reverse=True)

    return interactions[:top_n]


def analyze_interaction_types(top_interactions: list[dict]) -> dict:
    """Categorize top interactions by type."""

    categories = {
        'velocity_movement': [],
        'velocity_location': [],
        'location_count': [],
        'physics_combo': [],
        'context_combo': [],
        'other': [],
    }

    for inter in top_interactions:
        f1, f2 = inter['feature_1'], inter['feature_2']

        # Categorize based on feature names
        has_velocity = 'velocity' in f1.lower() or 'velocity' in f2.lower()
        has_movement = 'movement' in f1.lower() or 'movement' in f2.lower() or 'pfx' in f1.lower() or 'pfx' in f2.lower()
        has_location = 'plate' in f1.lower() or 'plate' in f2.lower() or 'zone' in f1.lower() or 'zone' in f2.lower()
        has_count = 'count' in f1.lower() or 'count' in f2.lower() or 'ball' in f1.lower() or 'strike' in f2.lower()
        has_spin = 'spin' in f1.lower() or 'spin' in f2.lower()

        if has_velocity and has_movement:
            categories['velocity_movement'].append(inter)
        elif has_velocity and has_location:
            categories['velocity_location'].append(inter)
        elif has_location and has_count:
            categories['location_count'].append(inter)
        elif (has_velocity or has_movement or has_spin) and (has_velocity or has_movement or has_spin):
            categories['physics_combo'].append(inter)
        else:
            categories['other'].append(inter)

    # Summarize
    summary = {}
    for cat, items in categories.items():
        if items:
            summary[cat] = {
                'count': len(items),
                'avg_mi': round(sum(i['mi_interaction'] for i in items) / len(items), 6),
                'top_pair': items[0] if items else None,
            }

    return summary


def test_xgboost_with_interactions(
    df: pd.DataFrame,
    features: list[str],
    target: pd.Series,
    top_interactions: list[dict],
) -> dict:
    """Test if adding top interactions improves XGBoost performance."""

    print('\nTesting XGBoost with interactions...')

    # Baseline: Individual features only
    X_baseline = df[features].fillna(df[features].median())

    # With interactions: Add top 5 interaction terms
    top_5 = top_interactions[:5]
    X_enhanced = X_baseline.copy()

    for inter in top_5:
        f1, f2 = inter['feature_1'], inter['feature_2']
        col_name = f'{f1}_x_{f2}'
        X_enhanced[col_name] = df[f1].fillna(df[f1].median()) * df[f2].fillna(df[f2].median())

    # Quick evaluation with small XGBoost
    from sklearn.model_selection import cross_val_score

    model = xgb.XGBClassifier(
        max_depth=4,
        n_estimators=50,
        learning_rate=0.1,
        random_state=42,
        n_jobs=-1,
        eval_metric='mlogloss',
    )

    # Sample for speed
    sample_idx = np.random.choice(len(X_baseline), size=min(10000, len(X_baseline)), replace=False)

    score_baseline = cross_val_score(
        model, X_baseline.iloc[sample_idx], target.iloc[sample_idx],
        cv=3, scoring='roc_auc_ovo', n_jobs=-1,
    ).mean()

    score_enhanced = cross_val_score(
        model, X_enhanced.iloc[sample_idx], target.iloc[sample_idx],
        cv=3, scoring='roc_auc_ovo', n_jobs=-1,
    ).mean()

    print(f'  Baseline AUC:  {score_baseline:.4f}')
    print(f'  Enhanced AUC:  {score_enhanced:.4f}')
    print(f'  Improvement:   {score_enhanced - score_baseline:+.4f}')

    return {
        'baseline_auc': round(score_baseline, 4),
        'enhanced_auc': round(score_enhanced, 4),
        'improvement': round(score_enhanced - score_baseline, 4),
        'top_interactions_added': [f"{i['feature_1']}_x_{i['feature_2']}" for i in top_5],
    }


def save_results(results: dict, output_dir: str = 'models/interaction_analysis'):
    """Save interaction analysis results."""

    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'{output_dir}/interactions_{timestamp}.json'

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f'\nResults saved to: {output_file}')


def main():
    parser = argparse.ArgumentParser(description='Feature Interaction Explorer')
    parser.add_argument('--top-features', type=int, default=20,
                       help='Number of top features to test')
    parser.add_argument('--top-interactions', type=int, default=50,
                       help='Number of top interactions to return')
    parser.add_argument('--sample-size', type=int, default=50000,
                       help='Sample size for analysis')
    args = parser.parse_args()

    print('='*70)
    print('FEATURE INTERACTION EXPLORER')
    print('='*70)
    print(f'Testing top {args.top_features} features')
    print(f'Sample size: {args.sample_size:,}')
    print('='*70)

    conn = psycopg2.connect(DB_URL)

    try:
        # Load data
        df, features = load_top_features(conn, args.top_features, args.sample_size)
        target = df['target']

        # Find top interactions
        top_interactions = find_top_interactions(
            df, features, target, args.top_interactions,
        )

        # Categorize
        categories = analyze_interaction_types(top_interactions[:20])

        # Test with XGBoost
        xgboost_test = test_xgboost_with_interactions(df, features, target, top_interactions)

        # Compile results
        results = {
            'timestamp': datetime.now().isoformat(),
            'n_features_tested': len(features),
            'features': features,
            'top_interactions': top_interactions[:20],
            'categories': categories,
            'xgboost_improvement_test': xgboost_test,
            'recommendations': [],
        }

        # Generate recommendations
        if xgboost_test['improvement'] > 0.01:
            results['recommendations'].append(
                f"Add top 5 interactions: improves AUC by {xgboost_test['improvement']:.4f}",
            )

        # Top synergistic pairs
        synergistic = [i for i in top_interactions if i['is_synergistic']]
        if synergistic:
            results['recommendations'].append(
                f'Found {len(synergistic)} synergistic feature pairs (interaction > individual)',
            )

        # Category insights
        for cat, data in categories.items():
            if data['count'] > 0:
                results['recommendations'].append(
                    f"{cat}: {data['count']} strong interactions (avg MI: {data['avg_mi']:.4f})",
                )

        # Save
        save_results(results)

        # Print summary
        print('\n' + '='*70)
        print('INTERACTION ANALYSIS SUMMARY')
        print('='*70)

        print('\nTop 5 Feature Interactions:')
        for i, inter in enumerate(top_interactions[:5], 1):
            print(f"  {i}. {inter['feature_1']} × {inter['feature_2']}")
            print(f"     MI: {inter['mi_interaction']:.4f} (gain: {inter['interaction_gain']:+.4f})")

        print('\nCategory Breakdown:')
        for cat, data in categories.items():
            if data['count'] > 0:
                print(f"  {cat}: {data['count']} pairs, avg MI: {data['avg_mi']:.4f}")

        print('\nXGBoost Test:')
        print(f"  Baseline:  {xgboost_test['baseline_auc']:.4f}")
        print(f"  Enhanced:  {xgboost_test['enhanced_auc']:.4f}")
        print(f"  Δ:         {xgboost_test['improvement']:+.4f}")

        print('\nRecommendations:')
        for rec in results['recommendations']:
            print(f'  • {rec}')

    finally:
        conn.close()


if __name__ == '__main__':
    main()
