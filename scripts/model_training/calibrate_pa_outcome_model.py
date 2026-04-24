#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from analyze_pa_outcome_calibration import (
    expected_calibration_error,
    feature_columns,
    load_validation_frame,
)
from predict_pa_outcome_distribution import load_registered_model
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import accuracy_score, f1_score, log_loss, top_k_accuracy_score
from sqlalchemy import create_engine
from train_pa_outcome_distribution import database_url


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_NAME = 'hist_gradient_boosting_multiclass'


def multiclass_brier_score(probabilities: np.ndarray, actual_index: np.ndarray) -> float:
    actual = np.zeros_like(probabilities)
    actual[np.arange(len(actual_index)), actual_index] = 1.0
    return float(np.mean(np.sum((probabilities - actual) ** 2, axis=1)))


def normalize_rows(probabilities: np.ndarray) -> np.ndarray:
    probabilities = np.clip(probabilities, 1e-12, 1.0)
    row_sums = probabilities.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0.0] = 1.0
    return probabilities / row_sums


def fit_isotonic_calibrators(
    probabilities: np.ndarray,
    target_index: np.ndarray,
) -> list[IsotonicRegression]:
    calibrators: list[IsotonicRegression] = []
    for class_index in range(probabilities.shape[1]):
        calibrator = IsotonicRegression(out_of_bounds='clip')
        y_binary = (target_index == class_index).astype(float)
        calibrator.fit(probabilities[:, class_index], y_binary)
        calibrators.append(calibrator)
    return calibrators


def apply_calibrators(
    probabilities: np.ndarray,
    calibrators: list[IsotonicRegression],
) -> np.ndarray:
    calibrated = np.zeros_like(probabilities)
    for class_index, calibrator in enumerate(calibrators):
        calibrated[:, class_index] = calibrator.predict(probabilities[:, class_index])
    return normalize_rows(calibrated)


def metric_summary(
    target_labels: np.ndarray,
    probabilities: np.ndarray,
    classes: list[str],
) -> dict[str, float | int]:
    predicted_index = probabilities.argmax(axis=1)
    predicted_labels = np.array(classes, dtype=object)[predicted_index]
    class_to_index = {label: index for index, label in enumerate(classes)}
    actual_index = np.array([class_to_index[label] for label in target_labels], dtype=int)
    return {
        'rows': len(target_labels),
        'classes': len(classes),
        'log_loss': float(log_loss(target_labels, probabilities, labels=classes)),
        'brier_score_multiclass': multiclass_brier_score(probabilities, actual_index),
        'accuracy': float(accuracy_score(target_labels, predicted_labels)),
        'f1_macro': float(f1_score(target_labels, predicted_labels, average='macro')),
        'f1_weighted': float(f1_score(target_labels, predicted_labels, average='weighted')),
        'top_3_accuracy': float(
            top_k_accuracy_score(
                target_labels,
                probabilities,
                k=min(3, len(classes)),
                labels=classes,
            ),
        ),
    }


def per_class_ece(
    target_labels: np.ndarray,
    probabilities: np.ndarray,
    classes: list[str],
    bins: int,
) -> list[dict]:
    rows: list[dict] = []
    for class_index, class_name in enumerate(classes):
        actual = (target_labels == class_name).astype(float)
        predicted = probabilities[:, class_index]
        rows.append(
            {
                'class_name': class_name,
                'support': int(actual.sum()),
                'mean_predicted_probability': float(predicted.mean()),
                'observed_rate': float(actual.mean()),
                'ece': expected_calibration_error(actual, predicted, bins),
                'absolute_gap': float(abs(predicted.mean() - actual.mean())),
            },
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Fit and evaluate post-hoc isotonic calibration for a registered PA outcome model.',
    )
    parser.add_argument('--model-name', default=DEFAULT_MODEL_NAME)
    parser.add_argument('--model-version', required=True)
    parser.add_argument('--calibration-through', type=int, default=2024)
    parser.add_argument('--evaluation-season', type=int, default=2025)
    parser.add_argument('--bins', type=int, default=10)
    parser.add_argument('--output-json', default=None)
    args = parser.parse_args()

    model, feature_spec, metadata = load_registered_model(
        model_name=args.model_name,
        model_version=args.model_version,
    )
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
        [class_to_index[label] for label in calibration_targets],
        dtype=int,
    )

    calibrators = fit_isotonic_calibrators(raw_cal, calibration_index)
    calibrated_eval = apply_calibrators(raw_eval, calibrators)

    raw_metrics = metric_summary(evaluation_targets, raw_eval, classes)
    calibrated_metrics = metric_summary(evaluation_targets, calibrated_eval, classes)

    raw_ece = per_class_ece(evaluation_targets, raw_eval, classes, args.bins)
    calibrated_ece = per_class_ece(evaluation_targets, calibrated_eval, classes, args.bins)

    report = {
        'model_name': metadata['model_name'],
        'model_version': metadata['model_version'],
        'feature_set': feature_set,
        'target_taxonomy': target_taxonomy,
        'train_through': train_through,
        'calibration_seasons': [train_through + 1, args.calibration_through],
        'evaluation_season': args.evaluation_season,
        'raw_metrics': raw_metrics,
        'calibrated_metrics': calibrated_metrics,
        'raw_per_class_ece': raw_ece,
        'calibrated_per_class_ece': calibrated_ece,
    }

    if args.output_json:
        output_path = Path(args.output_json)
        if not output_path.is_absolute():
            output_path = ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + '\n',
            encoding='utf-8',
        )

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
