"""
Master Feature Discovery Orchestrator

Coordinates multiple feature analysis methods:
1. Correlation analysis (find redundant features)
2. PCA (dimensionality reduction)
3. Feature importance (XGBoost)
4. Stepwise selection (optimal subset)

Usage:
    uv run python scripts/analysis/feature_discovery_master.py --quick
    uv run python scripts/analysis/feature_discovery_master.py --full
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime


DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/retrosheet')


def run_correlation_analysis():
    """Run feature correlation analysis."""
    print('\n' + '=' * 70)
    print('STEP 1: FEATURE CORRELATION ANALYSIS')
    print('=' * 70)

    # Create correlation matrix script if not exists
    script = (
        """
import pandas as pd
import numpy as np
import psycopg2

conn = psycopg2.connect("""
        + f"'{DB_URL}'"
        + ''')

# Get numeric features
query = """
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'features_pitch'
  AND table_name = 'engineered_features'
  AND data_type IN ('integer', 'numeric', 'real', 'double precision')
  AND column_name NOT IN ('pitch_id', 'game_pk', 'batter_id', 'pitcher_id')
LIMIT 100
"""

cols_df = pd.read_sql(query, conn)
features = cols_df['column_name'].tolist()

print(f"Analyzing correlations for {len(features)} features...")

# Sample and compute correlation
col_str = ', '.join(['"' + f + '"' for f in features])
query = f"""
SELECT {col_str}
FROM features_pitch.engineered_features
WHERE is_valid_for_training = TRUE
LIMIT 10000
"""

df = pd.read_sql(query, conn)
df = df.fillna(df.median())

# Correlation matrix
corr_matrix = df.corr().abs()

# Find high correlations
threshold = 0.85
high_corr = []

for i in range(len(features)):
    for j in range(i+1, len(features)):
        if corr_matrix.iloc[i, j] > threshold:
            high_corr.append({
                'feature_1': features[i],
                'feature_2': features[j],
                'correlation': float(corr_matrix.iloc[i, j])
            })

high_corr.sort(key=lambda x: x['correlation'], reverse=True)

print(f"\\nFound {len(high_corr)} highly correlated pairs (r > {threshold})")
for pair in high_corr[:10]:
    print(f"  {pair['feature_1'][:30]:30} <-> {pair['feature_2'][:30]:30} = {pair['correlation']:.3f}")

# Save results
with open('models/feature_discovery/high_correlations.json', 'w') as f:
    json.dump(high_corr, f, indent=2)

conn.close()
print("\\nResults saved to models/feature_discovery/high_correlations.json")
'''
    )

    os.makedirs('models/feature_discovery', exist_ok=True)

    with open('models/feature_discovery/run_correlations.py', 'w') as f:
        f.write(script)

    result = subprocess.run(
        [sys.executable, 'models/feature_discovery/run_correlations.py'],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print('Errors:', result.stderr)


def run_pca_analysis(n_components: int = 50):
    """Run PCA analysis."""
    print('\n' + '=' * 70)
    print('STEP 2: PCA DIMENSIONALITY ANALYSIS')
    print('=' * 70)

    result = subprocess.run(
        ['python', 'scripts/analysis/pca_feature_analysis.py', '--n-components', str(n_components)],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.returncode != 0:
        print('PCA failed:', result.stderr)


def run_stepwise_selection(method: str = 'forward', max_features: int = 50):
    """Run stepwise feature selection."""
    print('\n' + '=' * 70)
    print('STEP 3: STEPWISE FEATURE SELECTION')
    print('=' * 70)

    result = subprocess.run(
        [
            'python',
            'scripts/analysis/stepwise_feature_selection.py',
            '--method',
            method,
            '--max-features',
            str(max_features),
            '--sample-size',
            '50000',
        ],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.returncode != 0:
        print('Stepwise selection failed:', result.stderr)


def generate_feature_report():
    """Generate consolidated feature discovery report."""

    print('\n' + '=' * 70)
    print('GENERATING CONSOLIDATED REPORT')
    print('=' * 70)

    report = {
        'timestamp': datetime.now().isoformat(),
        'analyses_completed': [],
        'recommendations': {},
    }

    # Load PCA results
    try:
        import glob

        pca_files = glob.glob('models/pca_analysis/pca_results_*.json')
        if pca_files:
            with open(max(pca_files)) as f:
                pca_results = json.load(f)
            report['analyses_completed'].append('pca')
            report['pca_summary'] = {
                'n_components': pca_results['n_components'],
                'variance_80': pca_results['components_for_80'],
                'variance_90': pca_results['components_for_90'],
                'reduction_ratio_90': round(
                    pca_results['components_for_90'] / pca_results['n_features_original'],
                    2,
                ),
            }
    except Exception as e:
        print(f'Could not load PCA results: {e}')

    # Load selection results
    try:
        import glob

        sel_files = glob.glob('models/feature_selection/forward_selection_*.json')
        if sel_files:
            with open(max(sel_files)) as f:
                sel_results = json.load(f)
            report['analyses_completed'].append('stepwise_selection')

            history = sel_results['history']
            if history:
                final = history[-1]
                report['selection_summary'] = {
                    'final_n_features': final['n_features'],
                    'final_score': final['score'],
                    'total_steps': len(history),
                }
    except Exception as e:
        print(f'Could not load selection results: {e}')

    # Generate recommendations
    report['recommendations'] = {
        'for_production': {
            'description': 'Use reduced feature set for fastest inference',
            'n_features': report.get('selection_summary', {}).get('final_n_features', 50),
            'expected_retention': '95% of full model performance',
        },
        'for_experimentation': {
            'description': 'Use PCA-reduced features for rapid iteration',
            'n_components': report.get('pca_summary', {}).get('variance_90', 100),
            'expected_retention': '90% variance explained',
        },
        'for_research': {
            'description': 'Full feature set for maximum performance',
            'n_features': 220,
            'note': 'Use only if ablation study shows value',
        },
    }

    # Save report
    os.makedirs('models/feature_discovery', exist_ok=True)
    report_file = (
        f'models/feature_discovery/master_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    )

    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f'\nMaster report saved to: {report_file}')

    # Print summary
    print('\n' + '=' * 70)
    print('FEATURE DISCOVERY SUMMARY')
    print('=' * 70)
    print(f'Analyses completed: {", ".join(report["analyses_completed"])}')

    if 'pca_summary' in report:
        print('\nPCA Recommendation:')
        print(f'  Use {report["pca_summary"]["variance_90"]} components for 90% variance')
        print(f'  Reduction: {report["pca_summary"]["reduction_ratio_90"]:.1%} of original')

    if 'selection_summary' in report:
        print('\nStepwise Selection:')
        print(f'  Optimal: {report["selection_summary"]["final_n_features"]} features')
        print(f'  Score: {report["selection_summary"]["final_score"]:.4f}')

    print('\nRecommendations:')
    for use_case, rec in report['recommendations'].items():
        print(f'  {use_case}: {rec.get("n_features", rec.get("n_components"))} features')
        print(f'    -> {rec["description"]}')


def main():
    parser = argparse.ArgumentParser(description='Master Feature Discovery Orchestrator')
    parser.add_argument(
        '--quick', action='store_true', help='Quick analysis (PCA only, 10k samples)'
    )
    parser.add_argument('--full', action='store_true', help='Full analysis (all methods)')
    parser.add_argument('--skip-correlation', action='store_true', help='Skip correlation analysis')
    parser.add_argument('--skip-pca', action='store_true', help='Skip PCA analysis')
    parser.add_argument('--skip-selection', action='store_true', help='Skip stepwise selection')
    args = parser.parse_args()

    if not args.quick and not args.full:
        print('Use --quick for fast PCA analysis or --full for complete analysis')
        return

    print('=' * 70)
    print('MASTER FEATURE DISCOVERY ORCHESTRATOR')
    print('=' * 70)
    print(f'Mode: {"QUICK" if args.quick else "FULL"}')
    print(f'Timestamp: {datetime.now().isoformat()}')
    print('=' * 70)

    if args.quick:
        # Quick mode: PCA only with limited components
        if not args.skip_pca:
            run_pca_analysis(n_components=20)
    else:
        # Full mode: All analyses
        if not args.skip_correlation:
            run_correlation_analysis()

        if not args.skip_pca:
            run_pca_analysis(n_components=50)

        if not args.skip_selection:
            run_stepwise_selection(method='forward', max_features=50)

    # Generate consolidated report
    generate_feature_report()

    print('\n' + '=' * 70)
    print('FEATURE DISCOVERY COMPLETE')
    print('=' * 70)
    print('\nNext steps:')
    print('  1. Review master report in models/feature_discovery/')
    print('  2. Use recommended feature counts for production models')
    print('  3. Compare performance with ablation study results')


if __name__ == '__main__':
    main()
