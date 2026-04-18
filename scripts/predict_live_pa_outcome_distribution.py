#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text

from train_pa_outcome_distribution import ROOT, TARGET_ID, database_url
from retrosheet.prediction import (
    DEFAULT_MODEL_NAME,
    apply_calibrators,
    derived_probabilities,
    load_calibration_artifact,
    load_registered_model,
)


def _state_snapshot(frame: pd.DataFrame, numeric_features: list[str], categorical_features: list[str]) -> dict[str, Any]:
    """Extract game state snapshot from live feature frame for prediction logging."""
    row = frame.iloc[0]
    state_fields = [
        "inning", "top_inning", "outs", "balls", "strikes", 
        "runner_on_1b", "runner_on_2b", "runner_on_3b",
        "home_score", "away_score"
    ]
    return {field: row.get(field) for field in state_fields if field in row}


def _null_feature_names(frame: pd.DataFrame, numeric_features: list[str], categorical_features: list[str]) -> list[str]:
    """Identify which features are null/missing in the live feature frame."""
    row = frame.iloc[0]
    all_features = numeric_features + categorical_features
    return [col for col in all_features if col in row and pd.isna(row[col])]


def persist_live_prediction(
    *,
    game_id: str,
    plate_appearance_id: int,
    target_id: str,
    model_id: int,
    prediction_run_id: int | None,
    feature_snapshot: dict[str, Any],
    state_snapshot: dict[str, Any],
    missing_features: list[str],
    predicted_outcome: str,
    predicted_probabilities: dict[str, float],
    aggregated_metrics: dict[str, float],
    request_context: dict[str, Any],
    is_calibrated: bool,
    calibration_artifact_uri: str | None,
) -> int:
    """Persist live prediction to predictions.live_pa_predictions table."""
    engine = create_engine(database_url())
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO predictions.live_pa_predictions (
                        game_id, plate_appearance_id, target_id, model_id, prediction_run_id,
                        feature_snapshot, state_snapshot, missing_features,
                        predicted_outcome, predicted_probabilities, aggregated_metrics,
                        request_context, is_calibrated, calibration_artifact_uri
                    ) VALUES (
                        :game_id, :plate_appearance_id, :target_id, :model_id, :prediction_run_id,
                        :feature_snapshot::jsonb, :state_snapshot::jsonb, :missing_features,
                        :predicted_outcome, :predicted_probabilities::jsonb, :aggregated_metrics::jsonb,
                        :request_context::jsonb, :is_calibrated, :calibration_artifact_uri
                    ) RETURNING live_pa_prediction_id
                """),
                {
                    "game_id": game_id,
                    "plate_appearance_id": plate_appearance_id,
                    "target_id": target_id,
                    "model_id": model_id,
                    "prediction_run_id": prediction_run_id,
                    "feature_snapshot": json.dumps(feature_snapshot),
                    "state_snapshot": json.dumps(state_snapshot),
                    "missing_features": missing_features,
                    "predicted_outcome": predicted_outcome,
                    "predicted_probabilities": json.dumps(predicted_probabilities),
                    "aggregated_metrics": json.dumps(aggregated_metrics),
                    "request_context": json.dumps(request_context),
                    "is_calibrated": is_calibrated,
                    "calibration_artifact_uri": calibration_artifact_uri,
                }
            )
            return result.scalar()
    finally:
        engine.dispose()


def live_feature_query(feature_set: str) -> str:
    if feature_set != "advanced_count":
        raise ValueError(
            "Live scoring currently supports only feature_set=advanced_count. "
            "Historical models with other feature sets are not yet wired to a live parity view."
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
    apply_calibration: bool = True,
    calibration_report_name: str | None = None,
    persist_prediction: bool = False,
    request_context: dict[str, Any] | None = None,
    prediction_run_id: int | None = None,
) -> dict[str, Any]:
    model, feature_spec, metadata = load_registered_model(
        model_name=model_name,
        model_version=model_version,
    )
    numeric_features = feature_spec["numeric_features"]
    categorical_features = feature_spec["categorical_features"]
    feature_set = feature_spec.get("feature_set", "basic")

    engine = create_engine(database_url())
    try:
        frame = pd.read_sql_query(
            text(live_feature_query(feature_set)),
            engine,
            params={"game_id": game_id, "plate_appearance_id": plate_appearance_id},
        )
    finally:
        engine.dispose()

    if frame.empty:
        raise ValueError(f"Live plate appearance not found: {game_id}:{plate_appearance_id}")

    missing_features = [
        column for column in numeric_features + categorical_features if column not in frame
    ]
    if missing_features:
        raise ValueError(f"Missing live model features: {', '.join(missing_features)}")

    feature_frame = frame[numeric_features + categorical_features]
    raw_probabilities = model.predict_proba(feature_frame)[0]
    classes = list(model.named_steps["model"].classes_)
    probability_vector = raw_probabilities
    calibration_metadata = None
    raw_probability_map = None
    calibration_artifact_uri = None
    if apply_calibration:
        calibration_artifact, calibration_metadata = load_calibration_artifact(
            model_id=int(metadata["model_id"]),
            calibration_report_name=calibration_report_name,
        )
        artifact_classes = [str(label) for label in calibration_artifact["classes"]]
        if artifact_classes != classes:
            raise ValueError("Calibration artifact classes do not match model classes.")
        raw_probability_map = {
            label: float(raw_probabilities[index]) for index, label in enumerate(classes)
        }
        probability_vector = apply_calibrators(
            raw_probabilities.reshape(1, -1),
            calibration_artifact["calibrators"],
        )[0]
        calibration_artifact_uri = calibration_metadata.get("artifact_uri")

    probabilities = {label: float(probability_vector[index]) for index, label in enumerate(classes)}
    derived = derived_probabilities(probabilities)
    
    # Extract state snapshot and null feature names
    state = _state_snapshot(frame)
    null_features = _null_feature_names(frame, numeric_features, categorical_features)
    
    result = {
        "target_id": TARGET_ID,
        "source_type": "mlb_live",
        "game_id": game_id,
        "plate_appearance_id": plate_appearance_id,
        "model": {
            "model_name": metadata["model_name"],
            "model_version": metadata["model_version"],
            "artifact_uri": metadata["artifact_uri"],
            "feature_set": feature_set,
            "is_active": bool(metadata["is_active"]),
        },
        "probability_sum": float(sum(probabilities.values())),
        "class_probabilities": probabilities,
        "derived_probabilities": derived,
        "input_features": frame.iloc[0][numeric_features + categorical_features].to_dict(),
        "state_snapshot": state,
        "missing_features": null_features,
        "live_context": {
            "mlb_game_pk": frame.iloc[0].get("mlb_game_pk"),
            "snapshot_id": frame.iloc[0].get("snapshot_id"),
            "plate_appearance_index": frame.iloc[0].get("plate_appearance_index"),
            "event_text": frame.iloc[0].get("event_text"),
        },
    }
    if calibration_metadata is not None:
        result["calibration"] = {
            "applied": True,
            "calibration_report_id": calibration_metadata["calibration_report_id"],
            "report_name": calibration_metadata["report_name"],
            "calibration_method": calibration_metadata["calibration_method"],
            "artifact_uri": calibration_metadata["artifact_uri"],
        }
        result["raw_class_probabilities"] = raw_probability_map
        result["raw_derived_probabilities"] = derived_probabilities(raw_probability_map)
    else:
        result["calibration"] = {"applied": False}
    
    # Persist prediction if requested
    live_pa_prediction_id = None
    if persist_prediction:
        predicted_outcome = max(probabilities, key=probabilities.get)
        live_pa_prediction_id = persist_live_prediction(
            game_id=game_id,
            plate_appearance_id=plate_appearance_id,
            target_id=TARGET_ID,
            model_id=int(metadata["model_id"]),
            prediction_run_id=prediction_run_id,
            feature_snapshot=frame.iloc[0][numeric_features + categorical_features].to_dict(),
            state_snapshot=state,
            missing_features=null_features,
            predicted_outcome=predicted_outcome,
            predicted_probabilities=probabilities,
            aggregated_metrics=derived,
            request_context=request_context or {},
            is_calibrated=apply_calibration,
            calibration_artifact_uri=calibration_artifact_uri,
        )
        result["logging"] = {
            "persisted": True,
            "live_pa_prediction_id": live_pa_prediction_id,
            "prediction_run_id": prediction_run_id,
        }
    else:
        result["logging"] = {"persisted": False}
    
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score a live MLB plate appearance with the multiclass PA outcome model."
    )
    parser.add_argument("--game-id", required=True)
    parser.add_argument("--plate-appearance-id", required=True, type=int)
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--model-version")
    parser.add_argument("--apply-calibration", action="store_true")
    parser.add_argument("--calibration-report-name")
    parser.add_argument("--persist-prediction", action="store_true", help="Persist prediction to database")
    parser.add_argument("--prediction-run-id", type=int, help="Optional prediction run ID for logging")
    args = parser.parse_args()

    request_context = {
        "source": "cli",
        "apply_calibration": args.apply_calibration or bool(args.calibration_report_name),
    }

    result = predict_live_pa_outcome_distribution(
        game_id=args.game_id,
        plate_appearance_id=args.plate_appearance_id,
        model_name=args.model_name,
        model_version=args.model_version,
        apply_calibration=args.apply_calibration or bool(args.calibration_report_name),
        calibration_report_name=args.calibration_report_name,
        persist_prediction=args.persist_prediction,
        request_context=request_context,
        prediction_run_id=args.prediction_run_id,
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
