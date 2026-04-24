#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

import joblib
import numpy as np
import psycopg2
from analyze_pa_outcome_calibration import feature_columns, load_validation_frame
from calibrate_pa_outcome_model import (
    apply_calibrators,
    fit_isotonic_calibrators,
    metric_summary,
    per_class_ece,
)
from predict_pa_outcome_distribution import load_registered_model
from psycopg2.extras import Json
from sqlalchemy import create_engine
from train_pa_outcome_distribution import ROOT, TARGET_ID, database_kwargs, database_url


CALIBRATION_DIR = ROOT / 'data' / 'models' / 'calibration' / TARGET_ID
DEFAULT_MODEL_NAME = 'hist_gradient_boosting_multiclass'


def parse_year_window(values: list[int]) -> str:
    if len(values) != 2:
        raise ValueError(f'Expected two years, got {values}')
    return f'[{values[0]}-01-01,{values[1] + 1}-01-01)'


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Fit, persist, and register an isotonic calibration artifact for a PA outcome model.',
    )
    parser.add_argument('--model-name', default=DEFAULT_MODEL_NAME)
    parser.add_argument('--model-version', required=True)
    parser.add_argument('--calibration-through', type=int, default=2024)
    parser.add_argument('--evaluation-season', type=int, default=2025)
    parser.add_argument('--bins', type=int, default=10)
    parser.add_argument('--report-name')
    parser.add_argument('--notes', default=None)
    args = parser.parse_args()

    model, feature_spec, metadata = load_registered_model(
        model_name=args.model_name,
        model_version=args.model_version,
    )
    model_id = int(metadata['model_id'])
    feature_set = feature_spec['feature_set']
    target_taxonomy = feature_spec.get('target_taxonomy', 'granular')
    train_through = int(metadata['metrics']['train_through'])
    min_season = int(metadata['metrics']['min_season'])
    max_season = int(metadata['metrics']['max_season'])
    numeric_features, categorical_features = feature_columns(feature_set)

    engine = create_engine(database_url())
    try:
        frame = load_validation_frame(
            engine=engine,
            feature_set=feature_set,
            target_taxonomy=target_taxonomy,
            train_through=train_through,
            min_season=min_season,
            max_season=max_season,
        )
    finally:
        engine.dispose()

    calibration_frame = frame[frame['season'] <= args.calibration_through].copy()
    evaluation_frame = frame[frame['season'] == args.evaluation_season].copy()
    if calibration_frame.empty or evaluation_frame.empty:
        raise SystemExit('Calibration or evaluation split is empty.')

    classes = [str(label) for label in model.named_steps['model'].classes_]
    calibration_frame = calibration_frame[calibration_frame['target'].isin(classes)].copy()
    evaluation_frame = evaluation_frame[evaluation_frame['target'].isin(classes)].copy()
    if calibration_frame.empty or evaluation_frame.empty:
        raise SystemExit("No rows remain after restricting to the model's trained class set.")

    features_cal = calibration_frame[numeric_features + categorical_features]
    features_eval = evaluation_frame[numeric_features + categorical_features]
    raw_cal = model.predict_proba(features_cal)
    raw_eval = model.predict_proba(features_eval)

    class_to_index = {label: index for index, label in enumerate(classes)}
    calibration_targets = calibration_frame['target'].to_numpy()
    evaluation_targets = evaluation_frame['target'].to_numpy()
    calibration_index = np.array(
        [class_to_index[label] for label in calibration_targets], dtype=int,
    )

    calibrators = fit_isotonic_calibrators(raw_cal, calibration_index)
    calibrated_eval = apply_calibrators(raw_eval, calibrators)

    raw_metrics = metric_summary(evaluation_targets, raw_eval, classes)
    calibrated_metrics = metric_summary(evaluation_targets, calibrated_eval, classes)
    raw_ece = per_class_ece(evaluation_targets, raw_eval, classes, args.bins)
    calibrated_ece = per_class_ece(evaluation_targets, calibrated_eval, classes, args.bins)

    generated_at = datetime.now(UTC)
    report_name = args.report_name or f'{args.model_version}_isotonic_artifact'
    CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
    artifact_path = CALIBRATION_DIR / f'{report_name}.joblib'
    artifact_payload = {
        'target_id': TARGET_ID,
        'model_name': metadata['model_name'],
        'model_version': metadata['model_version'],
        'model_id': model_id,
        'classes': classes,
        'calibration_method': 'one_vs_rest_isotonic',
        'feature_set': feature_set,
        'target_taxonomy': target_taxonomy,
        'train_through': train_through,
        'calibration_seasons': [train_through + 1, args.calibration_through],
        'evaluation_season': args.evaluation_season,
        'generated_at': generated_at.isoformat(),
        'calibrators': calibrators,
    }
    joblib.dump(artifact_payload, artifact_path)

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
                    'calibration_artifact',
                    'completed',
                    Json(
                        {
                            'model_name': metadata['model_name'],
                            'model_version': metadata['model_version'],
                            'artifact_uri': str(artifact_path.relative_to(ROOT)),
                            'generated_at': generated_at.isoformat(),
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
                    calibration_method, calibration_window, evaluation_window, artifact_uri,
                    summary, per_class_summary, subgroup_summary, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::daterange, %s::daterange, %s, %s, %s, %s, %s)
                """,
                (
                    TARGET_ID,
                    model_id,
                    prediction_run_id,
                    report_name,
                    f'heldout_{args.evaluation_season}_artifact',
                    'one_vs_rest_isotonic',
                    parse_year_window([train_through + 1, args.calibration_through]),
                    parse_year_window([args.evaluation_season, args.evaluation_season]),
                    str(artifact_path.relative_to(ROOT)),
                    Json(
                        {
                            'raw_metrics': raw_metrics,
                            'calibrated_metrics': calibrated_metrics,
                        },
                    ),
                    Json(
                        {
                            'raw': raw_ece,
                            'calibrated': calibrated_ece,
                        },
                    ),
                    Json([]),
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
                'model_name': metadata['model_name'],
                'model_version': metadata['model_version'],
                'report_name': report_name,
                'artifact_uri': str(artifact_path.relative_to(ROOT)),
                'prediction_run_id': prediction_run_id,
                'raw_metrics': raw_metrics,
                'calibrated_metrics': calibrated_metrics,
            },
            indent=2,
            sort_keys=True,
        ),
    )


if __name__ == '__main__':
    main()
