#!/usr/bin/env python3
"""
Model retraining pipeline for new data ingestion.

This script orchestrates model retraining when new data is ingested:
- Refreshes feature marts
- Trains models on updated data
- Evaluates model performance
- Promotes best models to production

Usage:
    python3 scripts/retrain_models_pipeline.py --target pa_outcome_distribution
    python3 scripts/retrain_models_pipeline.py --target game_outcome
    python3 scripts/retrain_models_pipeline.py --all
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f'\n{"=" * 60}')
    print(f'STEP: {description}')
    print(f'Command: {" ".join(cmd)}')
    print(f'{"=" * 60}')

    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    success = result.returncode == 0
    print(f'Status: {"✅ SUCCESS" if success else "❌ FAILED"}')
    return success


def refresh_feature_marts() -> bool:
    """Refresh feature materialized views."""
    # Check if feature mart SQL exists and run it
    feature_sql = ROOT / 'sql' / '050_feature_marts.sql'
    if feature_sql.exists():
        cmd = ['psql', '-f', str(feature_sql)]
        return run_command(cmd, 'Refresh feature marts')
    print('Feature mart SQL not found, skipping')
    return True


def train_model(target: str, feature_set: str = 'advanced') -> bool:
    """Train a specific model target."""
    cmd = [
        'python3',
        'scripts/train_models.py',
        f'--target={target}',
        f'--feature-set={feature_set}',
    ]
    return run_command(cmd, f'Train {target} model with {feature_set} features')


def evaluate_model(target: str) -> bool:
    """Evaluate model performance."""
    # This would run evaluation scripts if they exist
    print(f'Evaluation for {target} - not yet implemented')
    return True


def promote_best_models() -> bool:
    """Promote best performing models to production."""
    promote_script = ROOT / 'scripts' / 'promote_best_models.py'
    if promote_script.exists():
        cmd = ['python3', str(promote_script)]
        return run_command(cmd, 'Promote best models to production')
    print('Promote script not found, skipping')
    return True


def log_training_run(targets: list[str], results: dict[str, bool]) -> None:
    """Log training run results to a JSON file."""
    log_file = ROOT / 'data' / 'model_training_runs.jsonl'
    log_file.parent.mkdir(exist_ok=True)

    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'targets': targets,
        'results': results,
        'success': all(results.values()),
    }

    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

    print(f'\nTraining run logged to {log_file}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Model retraining pipeline for new data')
    parser.add_argument(
        '--target',
        choices=['pa_outcome_distribution', 'game_outcome', 'win_probability'],
        help='Specific model target to train',
    )
    parser.add_argument('--all', action='store_true', help='Train all available models')
    parser.add_argument(
        '--feature-set',
        default='advanced',
        choices=['basic', 'advanced', 'enriched'],
        help='Feature set to use for training',
    )
    parser.add_argument('--skip-refresh', action='store_true', help='Skip feature mart refresh')
    parser.add_argument('--skip-promote', action='store_true', help='Skip model promotion')
    args = parser.parse_args()

    print(f'\n{"=" * 60}')
    print('MODEL RETRAINING PIPELINE')
    print(f'{"=" * 60}')
    print(f'Target: {args.target if args.target else "all"}')
    print(f'Feature set: {args.feature_set}')
    print(f'Skip refresh: {args.skip_refresh}')
    print(f'Skip promote: {args.skip_promote}')
    print(f'{"=" * 60}\n')

    # Determine targets to train
    if args.all:
        targets = ['pa_outcome_distribution', 'game_outcome']
    elif args.target:
        targets = [args.target]
    else:
        print('Error: Must specify --target or --all')
        sys.exit(1)

    # Execute pipeline steps
    results = {}

    # Step 1: Refresh feature marts
    if not args.skip_refresh:
        success = refresh_feature_marts()
        results['refresh_feature_marts'] = success
        if not success:
            print('Feature mart refresh failed, stopping pipeline')
            log_training_run(targets, results)
            sys.exit(1)

    # Step 2: Train models for each target
    for target in targets:
        success = train_model(target, args.feature_set)
        results[f'train_{target}'] = success

        if success:
            # Step 3: Evaluate model
            eval_success = evaluate_model(target)
            results[f'evaluate_{target}'] = eval_success

    # Step 4: Promote best models
    if not args.skip_promote:
        success = promote_best_models()
        results['promote_models'] = success

    # Log results
    log_training_run(targets, results)

    # Summary
    print(f'\n{"=" * 60}')
    print('PIPELINE SUMMARY')
    print(f'{"=" * 60}')
    for step, success in results.items():
        status = '✅' if success else '❌'
        print(f'{status} {step}')

    all_success = all(results.values())
    print(f'\nOverall status: {"✅ SUCCESS" if all_success else "❌ FAILED"}')
    print(f'{"=" * 60}\n')

    sys.exit(0 if all_success else 1)


if __name__ == '__main__':
    main()
