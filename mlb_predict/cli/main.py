"""Unified CLI for MLB Prediction Framework.

Phase 3.1: Unified CLI

Provides command-line interface for:
- Training models
- Running experiments
- Comparing models
- Generating predictions
- Managing plugins

Author: Agent Cascade
Date: April 24, 2026
"""

import argparse
import json
import sys
from pathlib import Path

from mlb_predict import (
    HyperparameterSweep,
    ModelConfig,
    ModelTrainer,
    compare_feature_sets,
    compare_model_families,
)


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        prog='mlb-predict',
        description='MLB Prediction Framework CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train a model
  mlb-predict train --config configs/xgboost.yaml
  
  # Run experiment comparing models
  mlb-predict experiment --compare-families xgboost lightgbm --target swing_decision
  
  # Compare feature sets
  mlb-predict experiment --compare-features basic advanced --target swing_decision
  
  # Hyperparameter sweep
  mlb-predict sweep --config configs/xgboost.yaml --param max_depth 3,5,7 --param learning_rate 0.01,0.1
        """,
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Train command
    train_parser = subparsers.add_parser('train', help='Train a single model')
    train_parser.add_argument('--config', '-c', required=True, help='Path to config YAML file')
    train_parser.add_argument('--output', '-o', help='Output directory for results')
    train_parser.add_argument(
        '--mock', action='store_true', help='Use mock training (no DB required)'
    )

    # Experiment command
    exp_parser = subparsers.add_parser('experiment', help='Run comparison experiments')
    exp_parser.add_argument(
        '--compare-families',
        nargs='+',
        choices=['xgboost', 'lightgbm', 'catboost'],
        help='Model families to compare',
    )
    exp_parser.add_argument(
        '--compare-features',
        nargs='+',
        choices=['basic', 'physics', 'advanced', 'complete'],
        help='Feature sets to compare',
    )
    exp_parser.add_argument(
        '--target',
        '-t',
        required=True,
        choices=['swing_decision', 'contact_made', 'hit_outcome'],
        help='Target variable',
    )
    exp_parser.add_argument(
        '--seasons', nargs='+', type=int, default=[2023, 2024, 2025], help='Seasons to use'
    )
    exp_parser.add_argument(
        '--output', '-o', default='experiments', help='Output directory for results'
    )
    exp_parser.add_argument('--report', action='store_true', help='Generate HTML report')

    # Sweep command
    sweep_parser = subparsers.add_parser('sweep', help='Run hyperparameter sweep')
    sweep_parser.add_argument('--config', '-c', required=True, help='Base config file')
    sweep_parser.add_argument(
        '--param',
        action='append',
        nargs=2,
        metavar=('NAME', 'VALUES'),
        help='Parameter and values (e.g., --param max_depth 3,5,7)',
    )
    sweep_parser.add_argument('--output', '-o', default='experiments', help='Output directory')

    # Info command
    info_parser = subparsers.add_parser('info', help='Show framework info')
    info_parser.add_argument('--config', '-c', help='Show config info')
    info_parser.add_argument('--list-targets', action='store_true', help='List available targets')
    info_parser.add_argument('--list-features', action='store_true', help='List feature sets')

    return parser


def cmd_train(args: argparse.Namespace) -> int:
    """Execute train command."""
    print(f'[INFO] Loading config from {args.config}')

    try:
        config = ModelConfig.from_yaml(args.config)
    except Exception as e:
        print(f'[ERROR] Failed to load config: {e}')
        return 1

    print(f'[INFO] Training {config.family} model for {config.target}')
    print(f'[INFO] Feature set: {config.features}')
    print(f'[INFO] Seasons: {config.seasons}')

    # Create trainer and train
    trainer = ModelTrainer(config)

    try:
        result = trainer.train()
    except Exception as e:
        print(f'[ERROR] Training failed: {e}')
        return 1

    # Print results
    print(f'\n{"=" * 60}')
    print('Training Complete!')
    print(f'{"=" * 60}')
    print(f'Model ID: {result.model_id}')
    print(f'Model Name: {result.model_name}')
    print(f'Training Time: {result.training_time_seconds:.1f}s')
    print(f'Samples: {result.n_samples_train} train, {result.n_samples_val} val')

    if result.train_metrics and result.train_metrics.roc_auc:
        print(f'Train AUC: {result.train_metrics.roc_auc.value:.4f}')

    if result.val_metrics and result.val_metrics.roc_auc:
        print(f'Val AUC: {result.val_metrics.roc_auc.value:.4f}')

    if result.feature_importance:
        print('\nTop 5 Features:')
        for feat in result.get_best_features(5):
            print(f'  {feat.importance_rank}. {feat.feature_name}: {feat.importance_score:.4f}')

    # Save results if output specified
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save summary
        summary = {
            'model_id': result.model_id,
            'model_name': result.model_name,
            'config': config.model_dump(),
            'metrics': {
                'train_auc': result.train_metrics.roc_auc.value
                if result.train_metrics and result.train_metrics.roc_auc
                else None,
                'val_auc': result.val_metrics.roc_auc.value
                if result.val_metrics and result.val_metrics.roc_auc
                else None,
            },
            'training_time': result.training_time_seconds,
        }

        with open(output_dir / 'train_result.json', 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        print(f'\n[INFO] Results saved to {output_dir}')

    return 0


def cmd_experiment(args: argparse.Namespace) -> int:
    """Execute experiment command."""
    print('[INFO] Running experiment')
    print(f'[INFO] Target: {args.target}')
    print(f'[INFO] Seasons: {args.seasons}')

    # Create base config
    base_config = ModelConfig(
        family='xgboost',
        target=args.target,
        features='advanced',
        seasons=args.seasons,
    )

    # Create runner based on comparison type
    if args.compare_families:
        print(f'[INFO] Comparing model families: {args.compare_families}')
        runner = compare_model_families(base_config, families=args.compare_families)
    elif args.compare_features:
        print(f'[INFO] Comparing feature sets: {args.compare_features}')
        runner = compare_feature_sets(base_config, feature_sets=args.compare_features)
    else:
        print('[ERROR] Must specify --compare-families or --compare-features')
        return 1

    # Run experiments
    try:
        summary = runner.run_all()
    except Exception as e:
        print(f'[ERROR] Experiment failed: {e}')
        return 1

    # Print results
    print(f'\n{"=" * 60}')
    print('Experiment Complete!')
    print(f'{"=" * 60}')
    print(f'Experiment ID: {summary.experiment_id}')
    print(f'Total Runs: {summary.n_runs}')
    print(f'Completed: {summary.n_completed}')
    print(f'Failed: {summary.n_failed}')

    if summary.best_run_id:
        print(f'\nBest Run: {summary.best_run_id}')
        print(f'Best {summary.metric_name}: {summary.best_metric_value:.4f}')

    # Print comparison table
    df = summary.to_dataframe()
    if not df.empty:
        print('\nResults:')
        print(df.to_string(index=False))

    # Generate report
    if args.report:
        report_path = runner.generate_report()
        print(f'\n[INFO] Report saved to {report_path}')

    return 0


def cmd_sweep(args: argparse.Namespace) -> int:
    """Execute sweep command."""
    print(f'[INFO] Loading base config from {args.config}')

    try:
        base_config = ModelConfig.from_yaml(args.config)
    except Exception as e:
        print(f'[ERROR] Failed to load config: {e}')
        return 1

    # Parse parameter grid
    param_grid = {}
    if args.param:
        for name, values_str in args.param:
            values = values_str.split(',')
            # Try to convert to int or float
            parsed_values = []
            for v in values:
                try:
                    parsed_values.append(int(v))
                except ValueError:
                    try:
                        parsed_values.append(float(v))
                    except ValueError:
                        parsed_values.append(v)
            param_grid[f'{base_config.family}__{name}'] = parsed_values

    print('[INFO] Parameter grid:')
    for name, values in param_grid.items():
        print(f'  {name}: {values}')

    # Create sweep
    sweep = HyperparameterSweep(base_config, param_grid)
    runner = sweep.create_runner(f'{base_config.family}_sweep')

    # Run sweep
    try:
        summary = runner.run_all()
    except Exception as e:
        print(f'[ERROR] Sweep failed: {e}')
        return 1

    # Print results
    print(f'\n{"=" * 60}')
    print('Hyperparameter Sweep Complete!')
    print(f'{"=" * 60}')
    print(f'Total Runs: {summary.n_runs}')

    if summary.best_run_id:
        print(f'\nBest Configuration: {summary.best_run_id}')
        print(f'Best {summary.metric_name}: {summary.best_metric_value:.4f}')

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Execute info command."""
    if args.list_targets:
        print('Available targets:')
        targets = ['swing_decision', 'contact_made', 'hit_outcome', 'pa_outcome', 'win_probability']
        for t in targets:
            print(f'  - {t}')
        return 0

    if args.list_features:
        print('Feature sets:')
        feature_sets = {
            'basic': '9 features (balls, strikes, outs, inning, score)',
            'physics': '13 features (+ release_speed, spin_rate, location)',
            'advanced': '21 features (+ pfx, launch metrics)',
            'complete': '29+ features (all available)',
        }
        for name, desc in feature_sets.items():
            print(f'  - {name}: {desc}')
        return 0

    if args.config:
        try:
            config = ModelConfig.from_yaml(args.config)
            print(f'Config: {args.config}')
            print(f'  Family: {config.family}')
            print(f'  Target: {config.target}')
            print(f'  Features: {config.features}')
            print(f'  Seasons: {config.seasons}')
            print('  Hyperparameters:')
            if config.xgboost:
                for k, v in config.xgboost.model_dump().items():
                    print(f'    {k}: {v}')
        except Exception as e:
            print(f'[ERROR] Failed to load config: {e}')
            return 1
        return 0

    # Default: show framework info
    print('MLB Prediction Framework')
    print('=' * 40)
    print('\nPhase 1: Foundation')
    print('  ✅ Pydantic Configuration Schemas')
    print('  ✅ Rich Result Classes (TrainResult, Residuals)')
    print('\nPhase 2: Core Wrappers')
    print('  ✅ ModelTrainer (wraps existing scripts)')
    print('  ✅ Plugin Registry (custom models)')
    print('  ✅ FeatureLoader (PostgreSQL data)')
    print('  ✅ Experiment Runner (multi-model comparison)')
    print('\nPhase 3: Polish (in progress)')
    print('  ✅ Unified CLI (this tool)')
    print('  🔄 Database Triggers')
    print('  🔄 Final Documentation')

    return 0


def main(args: list | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        return 1

    # Dispatch to command handler
    commands = {
        'train': cmd_train,
        'experiment': cmd_experiment,
        'sweep': cmd_sweep,
        'info': cmd_info,
    }

    handler = commands.get(parsed_args.command)
    if handler:
        return handler(parsed_args)
    print(f'[ERROR] Unknown command: {parsed_args.command}')
    return 1


if __name__ == '__main__':
    sys.exit(main())
