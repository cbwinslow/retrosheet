#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import Json
from train_pa_outcome_distribution import TARGET_ID, database_kwargs


ROOT = Path(__file__).resolve().parents[1]


def run_json_command(command: list[str]) -> dict:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def model_row(*, model_name: str, model_version: str) -> tuple[int, dict]:
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT model_id, metrics
                FROM models.model_registry
                WHERE target_id = %s
                  AND model_name = %s
                  AND model_version = %s
                """,
                (TARGET_ID, model_name, model_version),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f'Model not found: {model_name} {model_version}')
            return int(row[0]), row[1]
    finally:
        conn.close()


def parse_year_window(values: list[int]) -> str:
    if len(values) != 2:
        raise ValueError(f'Expected two years, got {values}')
    return f'[{values[0]}-01-01,{values[1] + 1}-01-01)'


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Persist PA outcome calibration and bootstrap reports into warehouse tables.',
    )
    parser.add_argument('--model-name', default='hist_gradient_boosting_multiclass')
    parser.add_argument('--model-version', required=True)
    parser.add_argument('--bootstrap-replicates', type=int, default=50)
    parser.add_argument('--bootstrap-seed', type=int, default=42)
    parser.add_argument('--calibration-through', type=int, default=2024)
    parser.add_argument('--evaluation-season', type=int, default=2025)
    parser.add_argument('--notes', default=None)
    args = parser.parse_args()

    model_id, metrics = model_row(model_name=args.model_name, model_version=args.model_version)
    validation_window = parse_year_window(
        [int(metrics['train_through']) + 1, int(metrics['max_season'])],
    )
    calibration_window = parse_year_window(
        [int(metrics['train_through']) + 1, args.calibration_through],
    )
    heldout_window = parse_year_window([args.evaluation_season, args.evaluation_season])

    raw_report = run_json_command(
        [
            sys.executable,
            'scripts/analyze_pa_outcome_calibration.py',
            '--model-name',
            args.model_name,
            '--model-version',
            args.model_version,
        ],
    )
    isotonic_report = run_json_command(
        [
            sys.executable,
            'scripts/calibrate_pa_outcome_model.py',
            '--model-name',
            args.model_name,
            '--model-version',
            args.model_version,
            '--calibration-through',
            str(args.calibration_through),
            '--evaluation-season',
            str(args.evaluation_season),
        ],
    )
    bootstrap_report = run_json_command(
        [
            sys.executable,
            'scripts/bootstrap_pa_outcome_evaluation.py',
            '--model-name',
            args.model_name,
            '--model-version',
            args.model_version,
            '--replicates',
            str(args.bootstrap_replicates),
            '--seed',
            str(args.bootstrap_seed),
        ],
    )

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predictions.prediction_runs (
                    target_id, model_id, run_context, finished_at, status, metadata
                )
                VALUES (%s, %s, %s, now(), %s, %s)
                RETURNING prediction_run_id
                """,
                (
                    TARGET_ID,
                    model_id,
                    'evaluation_report',
                    'completed',
                    Json(
                        {
                            'model_name': args.model_name,
                            'model_version': args.model_version,
                            'generated_at': datetime.now(UTC).isoformat(),
                            'notes': args.notes,
                        },
                    ),
                ),
            )
            prediction_run_id = int(cur.fetchone()[0])

            cur.execute(
                """
                INSERT INTO predictions.calibration_reports (
                    target_id, model_id, prediction_run_id, report_name, report_scope,
                    calibration_method, evaluation_window, summary, per_class_summary,
                    subgroup_summary, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::daterange, %s, %s, %s, %s)
                """,
                (
                    TARGET_ID,
                    model_id,
                    prediction_run_id,
                    f'{args.model_version}_raw_validation',
                    'validation_2023_2025',
                    'raw',
                    validation_window,
                    Json(raw_report['registered_validation_metrics']),
                    Json(raw_report['per_class_summary']),
                    Json(raw_report['subgroup_summary']),
                    args.notes,
                ),
            )

            cur.execute(
                """
                INSERT INTO predictions.calibration_reports (
                    target_id, model_id, prediction_run_id, report_name, report_scope,
                    calibration_method, calibration_window, evaluation_window, summary,
                    per_class_summary, subgroup_summary, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::daterange, %s::daterange, %s, %s, %s, %s)
                """,
                (
                    TARGET_ID,
                    model_id,
                    prediction_run_id,
                    f'{args.model_version}_isotonic_heldout',
                    'heldout_2025',
                    'one_vs_rest_isotonic',
                    calibration_window,
                    heldout_window,
                    Json(
                        {
                            'raw_metrics': isotonic_report['raw_metrics'],
                            'calibrated_metrics': isotonic_report['calibrated_metrics'],
                        },
                    ),
                    Json(isotonic_report['calibrated_per_class_ece']),
                    Json([]),
                    args.notes,
                ),
            )

            cur.execute(
                """
                INSERT INTO predictions.bootstrap_reports (
                    target_id, model_id, prediction_run_id, report_name, resampling_method,
                    replicates, seed, evaluation_window, summary, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::daterange, %s, %s)
                """,
                (
                    TARGET_ID,
                    model_id,
                    prediction_run_id,
                    f'{args.model_version}_bootstrap',
                    'season_stratified_game_cluster_bootstrap',
                    args.bootstrap_replicates,
                    args.bootstrap_seed,
                    validation_window,
                    Json(bootstrap_report['metrics']),
                    args.notes,
                ),
            )

        conn.commit()
    finally:
        conn.close()

    print(
        json.dumps(
            {
                'status': 'ok',
                'target_id': TARGET_ID,
                'model_name': args.model_name,
                'model_version': args.model_version,
                'prediction_run_id': prediction_run_id,
                'persisted_reports': [
                    'raw_validation_calibration',
                    'heldout_isotonic_calibration',
                    'bootstrap_summary',
                ],
            },
            indent=2,
            sort_keys=True,
        ),
    )


if __name__ == '__main__':
    main()
