#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

import pandas as pd
from predict_pa_outcome_distribution import (
    DEFAULT_MODEL_NAME,
    apply_calibrators,
    derived_probabilities,
    load_calibration_artifact,
    load_registered_model,
)
from sqlalchemy import create_engine, text
from train_pa_outcome_distribution import TARGET_ID, database_url


def live_feature_query(feature_set: str) -> str:
    if feature_set != 'advanced_count':
        msg = (
            'Live scoring currently supports only feature_set=advanced_count. '
            'Historical models with other feature sets are not yet wired to a live parity view.'
        )
        raise ValueError(
            msg,
        )
    return """
        SELECT *
        FROM features.live_plate_appearance_advanced_count_examples
        WHERE game_id = :game_id
          AND plate_appearance_id = :plate_appearance_id
    """


def predict_live_pa_outcome_distribution(
    *,
    game_id: str,
    plate_appearance_id: int,
    model_name: str = DEFAULT_MODEL_NAME,
    model_version: str | None = None,
    apply_calibration: bool = False,
    calibration_report_name: str | None = None,
) -> dict[str, Any]:
    model, feature_spec, metadata = load_registered_model(
        model_name=model_name,
        model_version=model_version,
    )
    numeric_features = feature_spec['numeric_features']
    categorical_features = feature_spec['categorical_features']
    feature_set = feature_spec.get('feature_set', 'basic')

    engine = create_engine(database_url())
    try:
        frame = pd.read_sql_query(
            text(live_feature_query(feature_set)),
            engine,
            params={'game_id': game_id, 'plate_appearance_id': plate_appearance_id},
        )
    finally:
        engine.dispose()

    if frame.empty:
        msg = f'Live plate appearance not found: {game_id}:{plate_appearance_id}'
        raise ValueError(msg)

    missing_features = [
        column for column in numeric_features + categorical_features if column not in frame
    ]
    if missing_features:
        msg = f'Missing live model features: {", ".join(missing_features)}'
        raise ValueError(msg)

    feature_frame = frame[numeric_features + categorical_features]
    raw_probabilities = model.predict_proba(feature_frame)[0]
    classes = list(model.named_steps['model'].classes_)
    probability_vector = raw_probabilities
    calibration_metadata = None
    raw_probability_map = None
    if apply_calibration:
        calibration_artifact, calibration_metadata = load_calibration_artifact(
            model_id=int(metadata['model_id']),
            calibration_report_name=calibration_report_name,
        )
        artifact_classes = [str(label) for label in calibration_artifact['classes']]
        if artifact_classes != classes:
            msg = 'Calibration artifact classes do not match model classes.'
            raise ValueError(msg)
        raw_probability_map = {
            label: float(raw_probabilities[index]) for index, label in enumerate(classes)
        }
        probability_vector = apply_calibrators(
            raw_probabilities.reshape(1, -1),
            calibration_artifact['calibrators'],
        )[0]

    probabilities = {label: float(probability_vector[index]) for index, label in enumerate(classes)}
    result = {
        'target_id': TARGET_ID,
        'source_type': 'mlb_live',
        'game_id': game_id,
        'plate_appearance_id': plate_appearance_id,
        'model': {
            'model_name': metadata['model_name'],
            'model_version': metadata['model_version'],
            'artifact_uri': metadata['artifact_uri'],
            'feature_set': feature_set,
            'is_active': bool(metadata['is_active']),
        },
        'probability_sum': float(sum(probabilities.values())),
        'class_probabilities': probabilities,
        'derived_probabilities': derived_probabilities(probabilities),
        'input_features': frame.iloc[0][numeric_features + categorical_features].to_dict(),
        'live_context': {
            'mlb_game_pk': frame.iloc[0].get('mlb_game_pk'),
            'snapshot_id': frame.iloc[0].get('snapshot_id'),
            'plate_appearance_index': frame.iloc[0].get('plate_appearance_index'),
            'event_text': frame.iloc[0].get('event_text'),
        },
    }
    if calibration_metadata is not None:
        result['calibration'] = {
            'applied': True,
            'calibration_report_id': calibration_metadata['calibration_report_id'],
            'report_name': calibration_metadata['report_name'],
            'calibration_method': calibration_metadata['calibration_method'],
            'artifact_uri': calibration_metadata['artifact_uri'],
        }
        result['raw_class_probabilities'] = raw_probability_map
        result['raw_derived_probabilities'] = derived_probabilities(raw_probability_map)
    else:
        result['calibration'] = {'applied': False}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Score a live MLB plate appearance with the multiclass PA outcome model.',
    )
    parser.add_argument('--game-id', required=True)
    parser.add_argument('--plate-appearance-id', required=True, type=int)
    parser.add_argument('--model-name', default=DEFAULT_MODEL_NAME)
    parser.add_argument('--model-version')
    parser.add_argument('--apply-calibration', action='store_true')
    parser.add_argument('--calibration-report-name')
    args = parser.parse_args()

    result = predict_live_pa_outcome_distribution(
        game_id=args.game_id,
        plate_appearance_id=args.plate_appearance_id,
        model_name=args.model_name,
        model_version=args.model_version,
        apply_calibration=args.apply_calibration or bool(args.calibration_report_name),
        calibration_report_name=args.calibration_report_name,
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
