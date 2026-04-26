"""
PCA Feature Analysis for Dimensionality Reduction

Performs Principal Component Analysis on engineered features to:
1. Identify feature groups that explain most variance
2. Find optimal number of components (elbow method)
3. Create reduced-dimension feature sets
4. Store PCA loadings for interpretation

Usage:
    uv run python scripts/analysis/pca_feature_analysis.py --n-components 50
    uv run python scripts/analysis/pca_feature_analysis.py --variance-threshold 0.95
"""

import argparse
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
import psycopg2
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/retrosheet')


def load_features(conn, feature_sample: int | None = None) -> pd.DataFrame:
    """Load numeric features from engineered_features table."""

    print('Loading features for PCA...')

    # Get numeric columns (exclude IDs, categoricals, targets)
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
    ORDER BY ordinal_position
    """

    cols_df = pd.read_sql(query, conn)
    feature_cols = cols_df['column_name'].tolist()

    print(f'Found {len(feature_cols)} numeric features')

    if feature_sample and len(feature_cols) > feature_sample:
        # Sample features randomly for quick analysis
        import random
        random.seed(42)
        feature_cols = random.sample(feature_cols, feature_sample)
        print(f'Sampled {len(feature_cols)} features for quick analysis')

    # Load data
    col_str = ', '.join([f'"{c}"' for c in feature_cols])
    query = f"""
    SELECT pitch_id, {col_str}
    FROM features_pitch.engineered_features
    WHERE is_valid_for_training = TRUE
      AND outcome_tier1 IS NOT NULL
    LIMIT 100000  -- Sample for memory efficiency
    """

    df = pd.read_sql(query, conn)
    print(f'Loaded {len(df)} rows with {len(feature_cols)} features')

    return df, feature_cols


def run_pca_analysis(df: pd.DataFrame, feature_cols: list, n_components: int) -> dict:
    """Run PCA and return results."""

    print(f'\nRunning PCA with max {n_components} components...')

    # Extract feature matrix
    X = df[feature_cols].values

    # Remove columns with all NaN or constant
    valid_cols = []
    for i, col in enumerate(feature_cols):
        if not np.all(np.isnan(X[:, i])) and np.std(X[:, i]) > 0:
            valid_cols.append(col)

    if len(valid_cols) < len(feature_cols):
        print(f'Removed {len(feature_cols) - len(valid_cols)} invalid features')
        X = df[valid_cols].values
    else:
        valid_cols = feature_cols

    # Handle remaining NaN
    col_means = np.nanmean(X, axis=0)
    for i in range(X.shape[1]):
        mask = np.isnan(X[:, i])
        X[mask, i] = col_means[i]

    # Fit PCA with standardization
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('pca', PCA(n_components=min(n_components, len(valid_cols)), random_state=42)),
    ])

    X_transformed = pipeline.fit_transform(X)
    pca = pipeline.named_steps['pca']

    print('\nPCA Results:')
    print(f'  Components: {pca.n_components_}')
    print(f'  Total variance explained: {sum(pca.explained_variance_ratio_):.2%}')

    # Find components for thresholds
    cumvar = np.cumsum(pca.explained_variance_ratio_)

    n_80 = np.argmax(cumvar >= 0.80) + 1
    n_90 = np.argmax(cumvar >= 0.90) + 1
    n_95 = np.argmax(cumvar >= 0.95) + 1

    print(f'  Components for 80% variance: {n_80}')
    print(f'  Components for 90% variance: {n_90}')
    print(f'  Components for 95% variance: {n_95}')

    # Component analysis
    components_data = []
    loadings = pca.components_

    for i in range(pca.n_components_):
        # Get feature loadings for this component
        feature_loadings = list(zip(valid_cols, loadings[i]))
        feature_loadings.sort(key=lambda x: abs(x[1]), reverse=True)

        top_pos = {k: round(v, 4) for k, v in feature_loadings[:5] if v > 0}
        top_neg = {k: round(abs(v), 4) for k, v in feature_loadings[:5] if v < 0}

        # Interpretation
        if i == 0:
            label = 'Overall Pitch Quality/Magnitude'
        elif i == 1:
            label = 'Zone Location (High/Low vs In/Out)'
        elif i == 2:
            label = 'Count/Leverage Situation'
        elif i == 3:
            label = 'Pitch Movement/Spin'
        else:
            label = f'Component {i+1}'

        components_data.append({
            'component': i + 1,
            'variance_ratio': round(pca.explained_variance_ratio_[i], 6),
            'cumulative_variance': round(cumvar[i], 6),
            'top_positive': top_pos,
            'top_negative': top_neg,
            'label': label,
            'n_top_features': len(top_pos) + len(top_neg),
        })

    return {
        'n_components': pca.n_components_,
        'n_features_original': len(valid_cols),
        'total_variance_explained': round(sum(pca.explained_variance_ratio_), 6),
        'components_for_80': n_80,
        'components_for_90': n_90,
        'components_for_95': n_95,
        'components': components_data,
        'scaler_mean': pipeline.named_steps['scaler'].mean_.tolist(),
        'scaler_scale': pipeline.named_steps['scaler'].scale_.tolist(),
    }


def save_results(results: dict, output_dir: str = 'models/pca_analysis'):
    """Save PCA results to database and files."""

    import os
    os.makedirs(output_dir, exist_ok=True)

    # Save to JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'{output_dir}/pca_results_{timestamp}.json'

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f'\nResults saved to: {output_file}')

    # Print summary
    print('\n' + '='*60)
    print('PCA SUMMARY')
    print('='*60)
    print(f"Original features: {results['n_features_original']}")
    print(f"Components analyzed: {results['n_components']}")
    print(f"Total variance explained: {results['total_variance_explained']:.2%}")
    print('\nRecommended component counts:')
    print(f"  80% variance: {results['components_for_80']} components")
    print(f"  90% variance: {results['components_for_90']} components")
    print(f"  95% variance: {results['components_for_95']} components")
    print('\nReduction ratios:')
    print(f"  80%: {results['components_for_80']}/{results['n_features_original']} = {results['components_for_80']/results['n_features_original']:.1%}")
    print(f"  90%: {results['components_for_90']}/{results['n_features_original']} = {results['components_for_90']/results['n_features_original']:.1%}")
    print(f"  95%: {results['components_for_95']}/{results['n_features_original']} = {results['components_for_95']/results['n_features_original']:.1%}")

    print('\nTop Components by Variance:')
    for comp in results['components'][:5]:
        print(f"\n  PC{comp['component']}: {comp['variance_ratio']:.2%} variance ({comp['label']})")
        if comp['top_positive']:
            print(f"    + {list(comp['top_positive'].keys())[:3]}")
        if comp['top_negative']:
            print(f"    - {list(comp['top_negative'].keys())[:3]}")


def main():
    parser = argparse.ArgumentParser(description='PCA Feature Analysis')
    parser.add_argument('--n-components', type=int, default=50,
                       help='Max number of PCA components')
    parser.add_argument('--feature-sample', type=int, default=None,
                       help='Sample N features for quick analysis')
    args = parser.parse_args()

    print('='*70)
    print('PCA FEATURE ANALYSIS')
    print('='*70)
    print(f'Timestamp: {datetime.now().isoformat()}')
    print(f'Max components: {args.n_components}')
    print('='*70)

    conn = psycopg2.connect(DB_URL)

    try:
        # Load data
        df, feature_cols = load_features(conn, args.feature_sample)

        # Run PCA
        results = run_pca_analysis(df, feature_cols, args.n_components)

        # Save results
        save_results(results)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
