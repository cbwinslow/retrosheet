#!/usr/bin/env python3
"""
Production Training Script - Using New Framework with Legacy Integration.

This script demonstrates Production Integration by:
1. Using new ModelConfig/ModelTrainer framework
2. Integrating with existing train_models.py infrastructure
3. Returning rich TrainResult objects
4. Supporting both legacy and new-style training

Usage:
    # Legacy-style (backward compatible)
    python train_with_framework.py --target-id swing_outcome --feature-set advanced

    # New-style with config file
    python train_with_framework.py --config configs/xgboost_swing.yaml

    # Compare multiple models
    python train_with_framework.py --compare --target swing_outcome --families xgboost lightgbm

Author: Agent Cascade
Date: April 24, 2026
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mlb_predict import (
    ModelConfig,
    ModelTrainer,
    TrainResult,
    compare_feature_sets,
    compare_model_families,
)
from mlb_predict.integration import (
    LegacyCompatibleTrainer,
    create_config_from_legacy_args,
    print_framework_result_legacy_style,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Train models using new framework with legacy compatibility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train with legacy arguments
  python train_with_framework.py --target-id swing_outcome --feature-set advanced

  # Train with config file
  python train_with_framework.py --config configs/xgboost.yaml

  # Compare model families
  python train_with_framework.py --compare --target swing_outcome --families xgboost lightgbm

  # Production training with full feature set
  python train_with_framework.py --target-id hit_outcome --feature-set complete \\
    --min-season 2020 --max-season 2025 --train-through 2023
""",
    )

    # Mode selection
    parser.add_argument(
        '--config', '-c', type=str, help='Path to ModelConfig YAML file (new-style)',
    )
    parser.add_argument('--compare', action='store_true', help='Run comparison experiment')

    # Legacy-style arguments
    parser.add_argument(
        '--target-id', type=str, help='Target to train (e.g., swing_outcome, hit_outcome)',
    )
    parser.add_argument(
        '--feature-set',
        type=str,
        default='advanced',
        choices=['basic', 'advanced', 'enriched', 'complete'],
        help='Feature set complexity',
    )
    parser.add_argument('--min-season', type=int, default=2020, help='First season to include')
    parser.add_argument('--max-season', type=int, default=2025, help='Last season to include')
    parser.add_argument(
        '--train-through',
        type=int,
        default=2023,
        help='Last season for training (validation = after)',
    )
    parser.add_argument(
        '--model-family',
        type=str,
        default='xgboost',
        choices=['xgboost', 'lightgbm', 'catboost'],
        help='Model algorithm family',
    )

    # Comparison arguments
    parser.add_argument('--target', type=str, help='Target for comparison (when using --compare)')
    parser.add_argument(
        '--families', nargs='+', default=['xgboost', 'lightgbm'], help='Model families to compare',
    )
    parser.add_argument('--feature-sets', nargs='+', help='Feature sets to compare (optional)')

    # Output options
    parser.add_argument(
        '--output', '-o', type=str, default='results', help='Output directory for results',
    )
    parser.add_argument('--save-config', type=str, help='Save generated config to YAML file')
    parser.add_argument(
        '--report', action='store_true', help='Generate HTML report (for experiments)',
    )
    parser.add_argument(
        '--legacy-output', action='store_true', help='Print results in legacy format',
    )

    return parser.parse_args()


def train_legacy_style(args: argparse.Namespace) -> TrainResult:
    """
    Train using legacy-style arguments but new framework.

    Args:
        args: Command line arguments

    Returns:
        TrainResult with rich analysis
    """
    print('[INFO] Training with legacy-style arguments')
    print(f'[INFO] Target: {args.target_id}')
    print(f'[INFO] Feature set: {args.feature_set}')
    print(
        f'[INFO] Seasons: {args.min_season}-{args.max_season} (train through {args.train_through})',
    )
    print(f'[INFO] Model family: {args.model_family}')

    # Create config from legacy args
    config = create_config_from_legacy_args(
        target_id=args.target_id,
        feature_set=args.feature_set,
        min_season=args.min_season,
        max_season=args.max_season,
        train_through=args.train_through,
        model_family=args.model_family,
    )

    # Save config if requested
    if args.save_config:
        config.to_yaml(args.save_config)
        print(f'[INFO] Config saved to {args.save_config}')

    # Train using compatible trainer
    trainer = LegacyCompatibleTrainer(output_dir=args.output)
    return trainer.train_legacy_style(
        target_id=args.target_id,
        feature_set=args.feature_set,
        min_season=args.min_season,
        max_season=args.max_season,
        train_through=args.train_through,
        model_family=args.model_family,
    )



def train_new_style(config_path: str, output_dir: str) -> TrainResult:
    """
    Train using new-style config file.

    Args:
        config_path: Path to ModelConfig YAML
        output_dir: Output directory for results

    Returns:
        TrainResult
    """
    print(f'[INFO] Loading config from {config_path}')

    config = ModelConfig.from_yaml(config_path)

    print(f'[INFO] Training {config.family} model for {config.target}')
    print(f'[INFO] Features: {config.features}')
    print(f'[INFO] Seasons: {config.seasons}')

    # Train
    trainer = ModelTrainer(config)
    return trainer.train()



def run_comparison(args: argparse.Namespace) -> None:
    """
    Run comparison experiment.

    Args:
        args: Command line arguments
    """
    target = args.target or args.target_id or 'swing_decision'

    print('[INFO] Running comparison experiment')
    print(f'[INFO] Target: {target}')
    print(f'[INFO] Comparing: {args.families}')

    # Create base config
    base_config = create_config_from_legacy_args(
        target_id=target,
        feature_set=args.feature_set,
        min_season=args.min_season,
        max_season=args.max_season,
        train_through=args.train_through,
    )

    # Run comparison
    if args.feature_sets:
        print(f'[INFO] Comparing feature sets: {args.feature_sets}')
        runner = compare_feature_sets(base_config, feature_sets=args.feature_sets)
    else:
        runner = compare_model_families(base_config, families=args.families)

    # Execute
    summary = runner.run_all()

    # Print results
    print(f'\n{"=" * 60}')
    print('Comparison Results')
    print(f'{"=" * 60}')
    print(f'Total runs: {summary.n_runs}')
    print(f'Completed: {summary.n_completed}')
    print(f'Failed: {summary.n_failed}')

    if summary.best_run_id:
        print(f'\nBest run: {summary.best_run_id}')
        print(f'Best {summary.metric_name}: {summary.best_metric_value:.4f}')

    # Show comparison table
    df = runner.compare_runs()
    print(f'\n{df.to_string()}')

    # Generate report
    if args.report:
        report_path = runner.generate_report()
        print(f'\n[INFO] Report saved to {report_path}')

    # Save results
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path / 'comparison_results.csv', index=False)
    print(f'[INFO] Results saved to {output_path / "comparison_results.csv"}')


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        # Determine mode
        if args.compare:
            # Comparison mode
            run_comparison(args)

        elif args.config:
            # New-style with config file
            result = train_new_style(args.config, args.output)

            # Output results
            if args.legacy_output:
                print_framework_result_legacy_style(result)
            else:
                print(f'\n{"=" * 60}')
                print(result.summary())
                print(f'{"=" * 60}')

                if result.val_metrics and result.val_metrics.roc_auc:
                    print(f'Val AUC: {result.val_metrics.roc_auc.value:.4f}')

                if result.feature_importance:
                    print('\nTop 5 features:')
                    for feat in result.get_best_features(5):
                        print(
                            f'  {feat.importance_rank}. {feat.feature_name}: {feat.importance_score:.4f}',
                        )

        elif args.target_id:
            # Legacy-style training
            result = train_legacy_style(args)

            # Output results
            if args.legacy_output:
                print_framework_result_legacy_style(result)
            else:
                print(f'\n{"=" * 60}')
                print(result.summary())
                print(f'{"=" * 60}')

        else:
            print('[ERROR] Must specify either --config, --target-id, or --compare')
            print('[INFO] Use --help for usage examples')
            return 1

        return 0

    except Exception as e:
        print(f'[ERROR] Training failed: {e}')
        import traceback

        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
