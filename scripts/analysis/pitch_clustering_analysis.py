"""
Pitch Clustering Analysis - Exploratory Model

Uses unsupervised learning to discover natural pitch groupings:
1. K-Means clustering on pitch physics (velocity, movement, spin)
2. Gaussian Mixture Models for probabilistic cluster assignment
3. Hierarchical clustering for pitch taxonomy

Helps answer:
- How many distinct pitch types exist in the data?
- What characterizes each cluster?
- Are traditional pitch classifications optimal?

Usage:
    uv run python scripts/analysis/pitch_clustering_analysis.py --method kmeans --n-clusters 8
    uv run python scripts/analysis/pitch_clustering_analysis.py --method gmm --n-clusters 12
"""

import argparse
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
import psycopg2
from sklearn.cluster import KMeans
from sklearn.metrics import calinski_harabasz_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler


DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/retrosheet')


def load_pitch_data(conn, sample_size: int = 100000) -> pd.DataFrame:
    """Load pitch data with physics characteristics."""

    print(f'Loading {sample_size:,} pitches for clustering...')

    query = """
    SELECT
        ef.pitch_id,
        ef.pitch_type,
        ef.pitch_type_family,
        bf.start_speed as velocity,
        bf.pfx_x as horizontal_movement,
        bf.pfx_z as vertical_movement,
        bf.release_spin_rate as spin_rate,
        bf.spin_axis,
        bf.release_pos_x,
        bf.release_pos_y,
        bf.release_pos_z,
        bf.plate_x,
        bf.plate_z,
        ef.velocity_percentile,
        ef.horizontal_break,
        ef.vertical_break,
        ef.spin_efficiency,
        ef.total_movement,
        ef.pitcher_id
    FROM features_pitch.engineered_features ef
    JOIN features_pitch.base_features bf ON ef.pitch_id = bf.pitch_id
    WHERE ef.is_valid_for_training = TRUE
      AND bf.start_speed IS NOT NULL
      AND bf.pfx_x IS NOT NULL
      AND bf.pfx_z IS NOT NULL
    ORDER BY RANDOM()
    LIMIT %(limit)s
    """

    df = pd.read_sql(query, conn, params={'limit': sample_size})
    print(f'Loaded {len(df):,} pitches')

    return df


def prepare_features(df: pd.DataFrame, feature_set: str = 'physics') -> tuple:
    """Prepare feature matrix for clustering."""

    if feature_set == 'physics':
        # Core physics features
        features = [
            'velocity',
            'horizontal_movement',
            'vertical_movement',
            'spin_rate',
            'total_movement',
        ]
    elif feature_set == 'location':
        # Location-based
        features = ['plate_x', 'plate_z', 'velocity', 'horizontal_movement']
    elif feature_set == 'full':
        # All numeric features
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        features = [c for c in numeric_cols if c not in ['pitch_id', 'pitcher_id', 'spin_axis']]
    else:
        features = ['velocity', 'horizontal_movement', 'vertical_movement', 'spin_rate']

    # Select available features
    available = [f for f in features if f in df.columns]
    print(f'Using {len(available)} features: {available}')

    X = df[available].values

    # Handle missing values
    mask = ~np.isnan(X).any(axis=1)
    X_clean = X[mask]
    df_clean = df.iloc[mask].copy()

    print(f'Clean data shape: {X_clean.shape} (removed {len(df) - len(df_clean)} rows with NaN)')

    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_clean)

    return X_scaled, df_clean, available, scaler


def run_kmeans(X: np.ndarray, n_clusters: int, df: pd.DataFrame) -> dict:
    """Run K-Means clustering."""

    print(f'\nRunning K-Means with {n_clusters} clusters...')

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    # Metrics
    silhouette = silhouette_score(X, labels)
    calinski = calinski_harabasz_score(X, labels)

    print(f'  Silhouette score: {silhouette:.3f}')
    print(f'  Calinski-Harabasz: {calinski:.1f}')

    # Cluster analysis
    df['cluster'] = labels

    cluster_stats = []
    for cluster_id in range(n_clusters):
        cluster_data = df[df['cluster'] == cluster_id]

        stats = {
            'cluster_id': int(cluster_id),
            'n_pitches': len(cluster_data),
            'pct_of_data': round(len(cluster_data) / len(df) * 100, 2),
            'velocity_mean': round(cluster_data['velocity'].mean(), 2)
            if 'velocity' in cluster_data
            else None,
            'velocity_std': round(cluster_data['velocity'].std(), 2)
            if 'velocity' in cluster_data
            else None,
            'top_pitch_types': cluster_data['pitch_type'].value_counts().head(3).to_dict()
            if 'pitch_type' in cluster_data
            else {},
            'inertia': float(kmeans.inertia_),
        }
        cluster_stats.append(stats)

    # Sort by size
    cluster_stats.sort(key=lambda x: x['n_pitches'], reverse=True)

    return {
        'method': 'kmeans',
        'n_clusters': n_clusters,
        'silhouette_score': round(silhouette, 4),
        'calinski_score': round(calinski, 2),
        'inertia': float(kmeans.inertia_),
        'cluster_centers': kmeans.cluster_centers_.tolist(),
        'cluster_stats': cluster_stats,
        'labels': labels.tolist(),
    }


def run_gmm(X: np.ndarray, n_clusters: int, df: pd.DataFrame) -> dict:
    """Run Gaussian Mixture Model clustering."""

    print(f'\nRunning Gaussian Mixture Model with {n_clusters} components...')

    gmm = GaussianMixture(n_components=n_clusters, random_state=42, n_init=3)
    labels = gmm.fit_predict(X)
    probs = gmm.predict_proba(X)

    # Metrics
    silhouette = silhouette_score(X, labels)
    aic = gmm.aic(X)
    bic = gmm.bic(X)

    print(f'  Silhouette score: {silhouette:.3f}')
    print(f'  AIC: {aic:.1f}, BIC: {bic:.1f}')

    # Cluster analysis
    df['cluster'] = labels
    df['max_prob'] = probs.max(axis=1)  # Confidence of assignment

    cluster_stats = []
    for cluster_id in range(n_clusters):
        cluster_data = df[df['cluster'] == cluster_id]

        stats = {
            'cluster_id': int(cluster_id),
            'n_pitches': len(cluster_data),
            'pct_of_data': round(len(cluster_data) / len(df) * 100, 2),
            'mean_confidence': round(cluster_data['max_prob'].mean(), 3),
            'velocity_mean': round(cluster_data['velocity'].mean(), 2)
            if 'velocity' in cluster_data
            else None,
            'top_pitch_types': cluster_data['pitch_type'].value_counts().head(3).to_dict()
            if 'pitch_type' in cluster_data
            else {},
            'weight': float(gmm.weights_[cluster_id]),
        }
        cluster_stats.append(stats)

    cluster_stats.sort(key=lambda x: x['n_pitches'], reverse=True)

    return {
        'method': 'gmm',
        'n_clusters': n_clusters,
        'silhouette_score': round(silhouette, 4),
        'aic': float(aic),
        'bic': float(bic),
        'cluster_stats': cluster_stats,
        'labels': labels.tolist(),
        'covariance_type': gmm.covariance_type,
    }


def find_optimal_clusters(X: np.ndarray, max_clusters: int = 15) -> dict:
    """Find optimal cluster count using elbow method and silhouette."""

    print(f'\nFinding optimal cluster count (2 to {max_clusters})...')

    results = []

    for k in range(2, max_clusters + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=5)
        labels = kmeans.fit_predict(X)

        silhouette = silhouette_score(X, labels)

        results.append(
            {
                'k': k,
                'inertia': float(kmeans.inertia_),
                'silhouette': float(silhouette),
            }
        )

        print(f'  k={k:2d}: silhouette={silhouette:.3f}, inertia={kmeans.inertia_:.1f}')

    # Find elbow (simplified - max silhouette)
    best_k = max(results, key=lambda x: x['silhouette'])['k']

    return {
        'optimal_k': int(best_k),
        'silhouette_scores': {r['k']: r['silhouette'] for r in results},
        'inertias': {r['k']: r['inertia'] for r in results},
    }


def save_results(results: dict, output_dir: str = 'models/clustering'):
    """Save clustering results."""

    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'{output_dir}/clustering_{results["method"]}_{timestamp}.json'

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f'\nResults saved to: {output_file}')

    # Print summary
    print('\n' + '=' * 60)
    print('CLUSTERING SUMMARY')
    print('=' * 60)
    print(f'Method: {results["method"]}')
    print(f'Clusters: {results["n_clusters"]}')
    print(f'Silhouette: {results["silhouette_score"]:.3f}')

    print('\nCluster Sizes:')
    for stat in results['cluster_stats']:
        print(
            f'  Cluster {stat["cluster_id"]}: {stat["n_pitches"]:,} pitches ({stat["pct_of_data"]}%)'
        )
        if stat.get('velocity_mean'):
            print(f'    Avg velocity: {stat["velocity_mean"]:.1f} mph')
        if stat.get('top_pitch_types'):
            top3 = list(stat['top_pitch_types'].keys())[:3]
            print(f'    Top types: {", ".join(top3)}')


def main():
    parser = argparse.ArgumentParser(description='Pitch Clustering Analysis')
    parser.add_argument(
        '--method',
        choices=['kmeans', 'gmm', 'hierarchical'],
        default='kmeans',
        help='Clustering method',
    )
    parser.add_argument('--n-clusters', type=int, default=8, help='Number of clusters')
    parser.add_argument('--find-optimal', action='store_true', help='Find optimal cluster count')
    parser.add_argument(
        '--max-clusters', type=int, default=15, help='Max clusters for optimization'
    )
    parser.add_argument(
        '--sample-size', type=int, default=100000, help='Number of pitches to analyze'
    )
    parser.add_argument(
        '--feature-set',
        choices=['physics', 'location', 'full'],
        default='physics',
        help='Which features to use',
    )
    args = parser.parse_args()

    print('=' * 70)
    print('PITCH CLUSTERING ANALYSIS')
    print('=' * 70)
    print(f'Method: {args.method}')
    print(f'Feature set: {args.feature_set}')
    print(f'Sample size: {args.sample_size:,}')
    print('=' * 70)

    conn = psycopg2.connect(DB_URL)

    try:
        # Load data
        df = load_pitch_data(conn, args.sample_size)

        # Prepare features
        X, df_clean, features, scaler = prepare_features(df, args.feature_set)

        # Find optimal clusters if requested
        if args.find_optimal:
            optimal = find_optimal_clusters(X, args.max_clusters)
            print(f'\nOptimal cluster count: {optimal["optimal_k"]}')
            args.n_clusters = optimal['optimal_k']

        # Run clustering
        if args.method == 'kmeans':
            results = run_kmeans(X, args.n_clusters, df_clean)
        elif args.method == 'gmm':
            results = run_gmm(X, args.n_clusters, df_clean)
        else:
            print(f'Method {args.method} not yet implemented')
            return

        # Add metadata
        results['timestamp'] = datetime.now().isoformat()
        results['feature_set'] = args.feature_set
        results['features_used'] = features
        results['n_samples'] = len(df_clean)

        # Save
        save_results(results)

        print('\n' + '=' * 70)
        print('ANALYSIS COMPLETE')
        print('=' * 70)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
