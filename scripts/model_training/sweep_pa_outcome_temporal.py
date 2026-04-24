#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRAINER = ROOT / 'scripts' / 'train_pa_outcome_distribution.py'


def parse_int_list(value: str) -> list[int]:
    if not value.strip():
        return []
    return [int(item.strip()) for item in value.split(',') if item.strip()]


def parse_float_list(value: str) -> list[float]:
    if not value.strip():
        return []
    return [float(item.strip()) for item in value.split(',') if item.strip()]


def run_candidate(command: list[str]) -> list[dict]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    results: list[dict] = []
    for line in completed.stdout.splitlines():
        if not line.startswith('trained '):
            continue
        model_name, metrics_json = line[len('trained ') :].split(': ', 1)
        results.append(
            {
                'model_name': model_name.strip(),
                'validation_metrics': json.loads(metrics_json),
                'stdout': completed.stdout,
            },
        )
    if not results:
        raise RuntimeError(
            f'No model metrics found in trainer output.\n{completed.stdout}\n{completed.stderr}',
        )
    return results


def policy_label(
    *,
    recent_window: int | None,
    season_half_life: float | None,
    exclude_2020: bool,
    downweight_2020: float | None,
) -> str:
    parts: list[str] = []
    parts.append(f'window_{recent_window}' if recent_window is not None else 'window_all')
    parts.append(
        f'half_life_{season_half_life:g}' if season_half_life is not None else 'half_life_none',
    )
    if exclude_2020:
        parts.append('exclude_2020')
    elif downweight_2020 is not None:
        parts.append(f'downweight_2020_{downweight_2020:g}')
    else:
        parts.append('keep_2020')
    return '__'.join(parts)


def build_command(
    args: argparse.Namespace, *, recent_window: int | None, season_half_life: float | None,
) -> list[str]:
    command = [
        sys.executable,
        str(TRAINER),
        '--feature-set',
        args.feature_set,
        '--target-taxonomy',
        args.target_taxonomy,
        '--sample-rate',
        str(args.sample_rate),
        '--train-through',
        str(args.train_through),
        '--min-season',
        str(args.min_season),
        '--max-season',
        str(args.max_season),
        '--min-class-rows',
        str(args.min_class_rows),
        '--no-activate',
    ]
    if recent_window is not None:
        command.extend(['--recent-window', str(recent_window)])
    if season_half_life is not None:
        command.extend(['--season-half-life', str(season_half_life)])
    if args.exclude_2020:
        command.append('--exclude-2020')
    elif args.downweight_2020 is not None:
        command.extend(['--downweight-2020', str(args.downweight_2020)])
    return command


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Run a reproducible temporal-policy sweep for PA outcome distribution training.',
    )
    parser.add_argument('--feature-set', choices=['basic', 'advanced'], default='advanced')
    parser.add_argument('--target-taxonomy', choices=['granular', 'grouped'], default='grouped')
    parser.add_argument('--sample-rate', type=float, default=0.05)
    parser.add_argument('--train-through', type=int, default=2022)
    parser.add_argument('--min-season', type=int, default=2000)
    parser.add_argument('--max-season', type=int, default=2025)
    parser.add_argument('--min-class-rows', type=int, default=100)
    parser.add_argument('--recent-windows', default='3,5,7,10,15')
    parser.add_argument('--include-all-window', action='store_true')
    parser.add_argument('--season-half-lives', default='3,5,7,10')
    parser.add_argument('--exclude-2020', action='store_true')
    parser.add_argument('--downweight-2020', type=float, default=None)
    parser.add_argument(
        '--output-json',
        default=None,
        help='Optional path for the full sweep JSON report.',
    )
    args = parser.parse_args()

    if args.exclude_2020 and args.downweight_2020 is not None:
        raise SystemExit('--exclude-2020 and --downweight-2020 are mutually exclusive.')

    recent_windows = parse_int_list(args.recent_windows)
    if args.include_all_window:
        recent_windows.append(None)  # type: ignore[arg-type]
    half_lives = parse_float_list(args.season_half_lives)

    policy_pairs: list[tuple[int | None, float | None]] = []
    for recent_window in recent_windows:
        policy_pairs.append((recent_window, None))
    for half_life in half_lives:
        policy_pairs.append((None, half_life))

    results: list[dict] = []
    for recent_window, season_half_life in policy_pairs:
        command = build_command(
            args,
            recent_window=recent_window,
            season_half_life=season_half_life,
        )
        candidate_results = run_candidate(command)
        policy = policy_label(
            recent_window=recent_window,
            season_half_life=season_half_life,
            exclude_2020=args.exclude_2020,
            downweight_2020=args.downweight_2020,
        )
        for candidate in candidate_results:
            metrics = candidate['validation_metrics']
            row = {
                'policy': policy,
                'recent_window': recent_window,
                'season_half_life': season_half_life,
                'exclude_2020': args.exclude_2020,
                'downweight_2020': args.downweight_2020,
                'feature_set': args.feature_set,
                'target_taxonomy': args.target_taxonomy,
                'sample_rate': args.sample_rate,
                'train_through': args.train_through,
                'model_name': candidate['model_name'],
                'rows': metrics['rows'],
                'classes': metrics['classes'],
                'log_loss': metrics['log_loss'],
                'brier_score_multiclass': metrics['brier_score_multiclass'],
                'accuracy': metrics['accuracy'],
                'f1_macro': metrics['f1_macro'],
                'f1_weighted': metrics['f1_weighted'],
                'top_3_accuracy': metrics['top_3_accuracy'],
            }
            results.append(row)
            print(json.dumps(row, sort_keys=True))

    results.sort(key=lambda row: (row['log_loss'], row['model_name'], row['policy']))
    summary = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'feature_set': args.feature_set,
        'target_taxonomy': args.target_taxonomy,
        'sample_rate': args.sample_rate,
        'train_through': args.train_through,
        'results': results,
        'best_by_log_loss': results[0] if results else None,
    }

    if args.output_json:
        output_path = Path(args.output_json)
        if not output_path.is_absolute():
            output_path = ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8',
        )


if __name__ == '__main__':
    main()
