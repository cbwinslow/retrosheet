#!/usr/bin/env python3
"""Generate historical PA outcome predictions in bulk and store in predictions.pa_predictions."""
from __future__ import annotations

import argparse
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm

from train_pa_outcome_distribution import TARGET_ID, database_url
from retrosheet.prediction import (
    DEFAULT_MODEL_NAME,
    apply_calibrators,
    load_calibration_artifact,
    load_registered_model,
)


def feature_query(feature_set: str) -> str:
    """Generate SQL query for feature extraction based on feature set."""
    if feature_set in {"advanced", "advanced_count"}:
        advanced_relation = (
            "features.plate_appearance_count_state_advanced_examples"
            if feature_set == "advanced_count"
            else "features.plate_appearance_advanced_examples"
        )
        return f"""
            SELECT
                outcome.game_id,
                outcome.plate_appearance_id,
                outcome.season,
                outcome.outcome_class AS actual_outcome_class,
                outcome.season_era,
                outcome.rules_context_era,
                advanced.inning,
                advanced.is_bottom_inning::integer AS is_bottom_inning,
                advanced.outs_before,
                advanced.start_bases,
                advanced.balls,
                advanced.strikes,
                advanced.home_score_diff,
                COALESCE(advanced.batter_hand::text, 'U') AS batter_hand,
                COALESCE(advanced.pitcher_hand::text, 'U') AS pitcher_hand,
                COALESCE(advanced.park_id, 'UNK') AS park_id,
                advanced.batter_career_prior_pa,
                advanced.batter_career_prior_hit_rate,
                advanced.batter_career_prior_walk_rate,
                advanced.batter_career_prior_k_rate,
                advanced.batter_career_prior_extra_base_hit_rate,
                advanced.pitcher_career_prior_pa,
                advanced.pitcher_career_prior_hit_rate,
                advanced.pitcher_career_prior_walk_rate,
                advanced.pitcher_career_prior_k_rate,
                advanced.pitcher_career_prior_whip,
                advanced.team_rolling_30_win_rate,
                advanced.opponent_rolling_30_win_rate,
                advanced.park_prior_total_runs_per_game,
                advanced.batting_team_rolling_30_win_rate,
                advanced.fielding_team_rolling_30_win_rate
            FROM features.plate_appearance_outcome_grouped_examples outcome
            JOIN {advanced_relation} advanced
                ON outcome.game_id = advanced.game_id
                AND outcome.plate_appearance_id = advanced.plate_appearance_id
            WHERE outcome.game_id = :game_id
                AND outcome.plate_appearance_id = :plate_appearance_id
        """
    else:
        return """
            SELECT
                outcome.game_id,
                outcome.plate_appearance_id,
                outcome.season,
                outcome.outcome_class AS actual_outcome_class,
                outcome.season_era,
                outcome.rules_context_era,
                basic.inning,
                basic.is_bottom_inning::integer AS is_bottom_inning,
                basic.outs_before,
                basic.start_bases,
                basic.balls,
                basic.strikes,
                basic.home_score_diff,
                COALESCE(basic.batter_hand::text, 'U') AS batter_hand,
                COALESCE(basic.pitcher_hand::text, 'U') AS pitcher_hand,
                COALESCE(basic.park_id, 'UNK') AS park_id,
                basic.batter_career_prior_pa,
                basic.batter_career_prior_hit_rate,
                basic.batter_career_prior_walk_rate,
                basic.batter_career_prior_k_rate,
                basic.batter_career_prior_extra_base_hit_rate,
                basic.pitcher_career_prior_pa,
                basic.pitcher_career_prior_hit_rate,
                basic.pitcher_career_prior_walk_rate,
                basic.pitcher_career_prior_k_rate,
                basic.pitcher_career_prior_whip
            FROM features.plate_appearance_outcome_grouped_examples outcome
            JOIN features.plate_appearance_examples basic
                ON outcome.game_id = basic.game_id
                AND outcome.plate_appearance_id = basic.plate_appearance_id
            WHERE outcome.game_id = :game_id
                AND outcome.plate_appearance_id = :plate_appearance_id
        """


def _state_snapshot(frame: pd.DataFrame) -> dict[str, Any]:
    """Extract state snapshot from feature frame."""
    row = frame.iloc[0]
    return {
        "inning": int(row.get("inning", 0)),
        "is_bottom_inning": bool(row.get("is_bottom_inning", False)),
        "outs_before": int(row.get("outs_before", 0)),
        "start_bases": str(row.get("start_bases", "000")),
        "balls": int(row.get("balls", 0)),
        "strikes": int(row.get("strikes", 0)),
        "home_score_diff": int(row.get("home_score_diff", 0)),
    }


def _missing_features(frame: pd.DataFrame, numeric_features: list[str], categorical_features: list[str]) -> list[str]:
    """Identify which features are null/missing in the feature frame."""
    row = frame.iloc[0]
    all_features = numeric_features + categorical_features
    return [col for col in all_features if col in row and pd.isna(row[col])]


def predict_single_pa(
    game_id: str,
    plate_appearance_id: int,
    model,
    feature_spec: dict[str, Any],
    metadata: dict[str, Any],
    apply_calibration: bool = False,
    calibration_report_name: str | None = None,
) -> dict[str, Any]:
    """Predict a single plate appearance."""
    numeric_features = feature_spec["numeric_features"]
    categorical_features = feature_spec["categorical_features"]
    feature_set = feature_spec.get("feature_set", "basic")

    engine = create_engine(database_url())
    try:
        frame = pd.read_sql_query(
            text(feature_query(feature_set)),
            engine,
            params={"game_id": game_id, "plate_appearance_id": plate_appearance_id},
        )
    finally:
        engine.dispose()

    if frame.empty:
        return None

    missing_features = [
        column for column in numeric_features + categorical_features if column not in frame
    ]
    if missing_features:
        return None

    feature_frame = frame[numeric_features + categorical_features]
    raw_probabilities = model.predict_proba(feature_frame)[0]
    classes = list(model.named_steps["model"].classes_)
    probability_vector = raw_probabilities
    calibration_metadata = None
    raw_probability_map = None

    if apply_calibration:
        calibration_artifact, calibration_metadata = load_calibration_artifact(
            model_id=int(metadata["model_id"]),
            calibration_report_name=calibration_report_name,
        )
        artifact_classes = [str(label) for label in calibration_artifact["classes"]]
        if artifact_classes != classes:
            return None
        raw_probability_map = {
            label: float(raw_probabilities[index]) for index, label in enumerate(classes)
        }
        probability_vector = apply_calibrators(
            raw_probabilities.reshape(1, -1),
            calibration_artifact["calibrators"],
        )[0]

    probabilities = {label: float(probability_vector[index]) for index, label in enumerate(classes)}
    probability_sum = float(sum(probabilities.values()))

    state = _state_snapshot(frame)
    missing = _missing_features(frame, numeric_features, categorical_features)

    predicted_outcome = max(probabilities, key=probabilities.get)

    return {
        "game_id": game_id,
        "plate_appearance_id": plate_appearance_id,
        "target_id": TARGET_ID,
        "model_id": int(metadata["model_id"]),
        "feature_snapshot": frame.iloc[0][numeric_features + categorical_features].to_dict(),
        "state_snapshot": state,
        "missing_features": missing,
        "predicted_outcome": predicted_outcome,
        "predicted_probabilities": probabilities,
        "aggregated_metrics": {"probability_sum": probability_sum},
        "prediction_timestamp": datetime.now(timezone.utc),
        "is_calibrated": apply_calibration,
        "calibration_artifact_uri": calibration_metadata["artifact_uri"] if calibration_metadata else None,
        "actual_outcome": frame.iloc[0].get("actual_outcome_class"),
    }


def generate_predictions(
    season: int | None = None,
    limit: int | None = None,
    sample_rate: float = 1.0,
    model_name: str = DEFAULT_MODEL_NAME,
    model_version: str | None = None,
    apply_calibration: bool = False,
    calibration_report_name: str | None = None,
) -> None:
    """Generate predictions for historical plate appearances."""
    model, feature_spec, metadata = load_registered_model(
        model_name=model_name,
        model_version=model_version,
    )

    # Get plate appearances to predict
    engine = create_engine(database_url())
    try:
        where_clause = "WHERE 1=1"
        params: dict[str, Any] = {}
        if season is not None:
            where_clause += " AND season = :season"
            params["season"] = season
        if sample_rate < 1.0:
            where_clause += " AND (random() < :sample_rate)"
            params["sample_rate"] = sample_rate

        query = f"""
            SELECT game_id, plate_appearance_id
            FROM features.plate_appearance_outcome_grouped_examples
            {where_clause}
        """
        if limit is not None:
            query += f" LIMIT {limit}"

        pa_df = pd.read_sql_query(text(query), engine, params=params)
    finally:
        engine.dispose()

    print(f"Generating predictions for {len(pa_df)} plate appearances...")

    # Generate predictions
    predictions = []
    for _, row in tqdm(pa_df.iterrows(), total=len(pa_df)):
        result = predict_single_pa(
            game_id=row["game_id"],
            plate_appearance_id=row["plate_appearance_id"],
            model=model,
            feature_spec=feature_spec,
            metadata=metadata,
            apply_calibration=apply_calibration,
            calibration_report_name=calibration_report_name,
        )
        if result is not None:
            predictions.append(result)

    print(f"Successfully generated {len(predictions)} predictions")

    # Insert into database
    if predictions:
        engine = create_engine(database_url())
        try:
            pred_df = pd.DataFrame(predictions)
            pred_df.to_sql(
                "pa_predictions",
                engine,
                schema="predictions",
                if_exists="append",
                index=False,
            )
            print(f"Inserted {len(predictions)} predictions into predictions.pa_predictions")
        finally:
            engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate historical PA outcome predictions in bulk."
    )
    parser.add_argument("--season", type=int, help="Season to generate predictions for")
    parser.add_argument("--limit", type=int, help="Limit number of PAs to predict")
    parser.add_argument("--sample-rate", type=float, default=1.0, help="Sample rate for prediction")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--model-version")
    parser.add_argument("--apply-calibration", action="store_true")
    parser.add_argument("--calibration-report-name")
    args = parser.parse_args()

    generate_predictions(
        season=args.season,
        limit=args.limit,
        sample_rate=args.sample_rate,
        model_name=args.model_name,
        model_version=args.model_version,
        apply_calibration=args.apply_calibration or bool(args.calibration_report_name),
        calibration_report_name=args.calibration_report_name,
    )


if __name__ == "__main__":
    main()
