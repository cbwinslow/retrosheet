#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

import joblib
import numpy as np
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
from train_pa_outcome_distribution import (
    ROOT,
    TARGET_ID,
    database_kwargs,
    database_url,
)


DEFAULT_MODEL_NAME = 'hist_gradient_boosting_multiclass'


def load_registered_model(
    *,
    model_name: str,
    model_version: str | None,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            if model_version:
                cur.execute(
                    """
                    SELECT model_name, model_version, artifact_uri, feature_spec, metrics, is_active
                           , model_id
                    FROM models.model_registry
                    WHERE target_id = %s
                      AND model_name = %s
                      AND model_version = %s
                    """,
                    (TARGET_ID, model_name, model_version),
                )
            else:
                cur.execute(
                    """
                    SELECT model_name, model_version, artifact_uri, feature_spec, metrics, is_active
                           , model_id
                    FROM models.model_registry
                    WHERE target_id = %s
                      AND model_name = %s
                    ORDER BY is_active DESC, model_version DESC
                    LIMIT 1
                    """,
                    (TARGET_ID, model_name),
                )
            row = cur.fetchone()
            if not row:
                raise ValueError(
                    f'No registered {TARGET_ID} model found for {model_name}'
                    + (f' version {model_version}' if model_version else ''),
                )

    finally:
        conn.close()

    metadata = {
        'model_name': row[0],
        'model_version': row[1],
        'artifact_uri': row[2],
        'feature_spec': row[3],
        'metrics': row[4],
        'is_active': row[5],
        'model_id': row[6],
    }
    artifact_path = ROOT / metadata['artifact_uri']
    if not artifact_path.exists():
        raise FileNotFoundError(f'Model artifact not found: {artifact_path}')
    return joblib.load(artifact_path), metadata['feature_spec'], metadata


def normalize_rows(probabilities: np.ndarray) -> np.ndarray:
    probabilities = np.clip(probabilities, 1e-12, 1.0)
    row_sums = probabilities.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0.0] = 1.0
    return probabilities / row_sums


def apply_calibrators(probabilities: np.ndarray, calibrators: list[Any]) -> np.ndarray:
    calibrated = np.zeros_like(probabilities)
    for class_index, calibrator in enumerate(calibrators):
        calibrated[:, class_index] = calibrator.predict(probabilities[:, class_index])
    return normalize_rows(calibrated)


def load_calibration_artifact(
    *,
    model_id: int,
    calibration_report_name: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            if calibration_report_name:
                cur.execute(
                    """
                    SELECT calibration_report_id, report_name, calibration_method, artifact_uri, summary
                    FROM predictions.calibration_reports
                    WHERE target_id = %s
                      AND model_id = %s
                      AND report_name = %s
                      AND artifact_uri IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (TARGET_ID, model_id, calibration_report_name),
                )
            else:
                cur.execute(
                    """
                    SELECT calibration_report_id, report_name, calibration_method, artifact_uri, summary
                    FROM predictions.calibration_reports
                    WHERE target_id = %s
                      AND model_id = %s
                      AND artifact_uri IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (TARGET_ID, model_id),
                )
            row = cur.fetchone()
            if not row:
                raise ValueError(
                    'No calibration artifact found for model_id '
                    f'{model_id}'
                    + (f' and report {calibration_report_name}' if calibration_report_name else ''),
                )
    finally:
        conn.close()

    metadata = {
        'calibration_report_id': row[0],
        'report_name': row[1],
        'calibration_method': row[2],
        'artifact_uri': row[3],
        'summary': row[4],
    }
    artifact_path = ROOT / metadata['artifact_uri']
    if not artifact_path.exists():
        raise FileNotFoundError(f'Calibration artifact not found: {artifact_path}')
    return joblib.load(artifact_path), metadata


def feature_query(feature_set: str) -> str:
    if feature_set in {'advanced', 'advanced_count'}:
        advanced_relation = (
            'features.plate_appearance_count_state_advanced_examples'
            if feature_set == 'advanced_count'
            else 'features.plate_appearance_advanced_examples'
        )
        return (
            """
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
                advanced.batter_career_prior_strikeout_rate,
                advanced.batter_career_prior_home_run_rate,
                advanced.batter_career_prior_reach_base_rate,
                advanced.pitcher_career_prior_batters_faced,
                advanced.pitcher_career_prior_hit_allowed_rate,
                advanced.pitcher_career_prior_walk_allowed_rate,
                advanced.pitcher_career_prior_strikeout_rate,
                advanced.pitcher_career_prior_home_run_allowed_rate,
                advanced.pitcher_career_prior_reach_base_allowed_rate,
                advanced.prior_matchup_pa,
                advanced.prior_matchup_hit_rate,
                advanced.prior_matchup_walk_rate,
                advanced.prior_matchup_strikeout_rate,
                advanced.prior_matchup_home_run_rate,
                advanced.prior_matchup_reach_base_rate,
                advanced.coarse_context_prior_pa,
                advanced.coarse_context_prior_hit_rate,
                advanced.coarse_context_prior_walk_rate,
                advanced.coarse_context_prior_strikeout_rate,
                advanced.coarse_context_prior_home_run_rate,
                advanced.coarse_context_prior_reach_base_rate,
                advanced.coarse_context_prior_extra_base_hit_rate,
                advanced.park_prior_total_runs_per_game,
                advanced.park_prior_home_win_rate,
                advanced.batting_team_rolling_30_games,
                advanced.batting_team_rolling_30_win_rate,
                advanced.batting_team_rolling_30_runs_scored_per_game,
                advanced.batting_team_rolling_30_runs_allowed_per_game,
                advanced.fielding_team_rolling_30_games,
                advanced.fielding_team_rolling_30_win_rate,
                advanced.fielding_team_rolling_30_runs_scored_per_game,
                advanced.fielding_team_rolling_30_runs_allowed_per_game"""
            + (
                """
                ,
                advanced.batter_count_state_prior_pa,
                advanced.batter_count_state_prior_hit_rate,
                advanced.batter_count_state_prior_walk_rate,
                advanced.batter_count_state_prior_strikeout_rate,
                advanced.batter_count_state_prior_home_run_rate,
                advanced.batter_count_state_prior_reach_base_rate,
                advanced.batter_count_state_prior_extra_base_hit_rate,
                advanced.pitcher_count_state_prior_batters_faced,
                advanced.pitcher_count_state_prior_hit_allowed_rate,
                advanced.pitcher_count_state_prior_walk_allowed_rate,
                advanced.pitcher_count_state_prior_strikeout_rate,
                advanced.pitcher_count_state_prior_home_run_allowed_rate,
                advanced.pitcher_count_state_prior_reach_base_allowed_rate,
                advanced.pitcher_count_state_prior_extra_base_hit_allowed_rate,
                advanced.count_state_context_prior_pa,
                advanced.count_state_context_prior_hit_rate,
                advanced.count_state_context_prior_walk_rate,
                advanced.count_state_context_prior_strikeout_rate,
                advanced.count_state_context_prior_home_run_rate,
                advanced.count_state_context_prior_reach_base_rate,
                advanced.count_state_context_prior_extra_base_hit_rate
                """
                if feature_set == 'advanced_count'
                else ''
            )
            + """
            FROM features.plate_appearance_outcome_examples outcome
            JOIN """
            + advanced_relation
            + """ advanced
              ON advanced.game_id = outcome.game_id
             AND advanced.plate_appearance_id = outcome.plate_appearance_id
            WHERE outcome.game_id = :game_id
              AND outcome.plate_appearance_id = :plate_appearance_id
        """
        )
    return """
        SELECT
            game_id,
            plate_appearance_id,
            season,
            outcome_class AS actual_outcome_class,
            season_era,
            rules_context_era,
            inning,
            is_bottom_inning::integer AS is_bottom_inning,
            outs_before,
            start_bases,
            balls,
            strikes,
            home_score_diff,
            COALESCE(batter_hand::text, 'U') AS batter_hand,
            COALESCE(pitcher_hand::text, 'U') AS pitcher_hand
        FROM features.plate_appearance_outcome_examples
        WHERE game_id = :game_id
          AND plate_appearance_id = :plate_appearance_id
    """


def probability(probabilities: dict[str, float], *classes: str) -> float:
    return float(sum(probabilities.get(label, 0.0) for label in classes))


def derived_probabilities(probabilities: dict[str, float]) -> dict[str, float]:
    p_hit = probability(probabilities, 'single', 'double', 'triple', 'home_run')
    p_extra_base_hit = probability(probabilities, 'double', 'triple', 'home_run')
    p_on_base_traditional = probability(
        probabilities,
        'single',
        'double',
        'triple',
        'home_run',
        'walk',
        'intentional_walk',
        'hit_by_pitch',
    )
    p_reach_base_any = p_on_base_traditional + probability(
        probabilities, 'error_on_batter', 'interference',
    )
    p_ball_in_play = probability(
        probabilities,
        'single',
        'double',
        'triple',
        'home_run',
        'ground_out',
        'fly_out',
        'line_out',
        'pop_out',
        'error_on_batter',
        'fielders_choice',
        'sacrifice_fly',
        'sacrifice_hit',
    )
    expected_total_bases = (
        probabilities.get('single', 0.0)
        + 2.0 * probabilities.get('double', 0.0)
        + 3.0 * probabilities.get('triple', 0.0)
        + 4.0 * probabilities.get('home_run', 0.0)
    )
    return {
        'p_hit': float(p_hit),
        'p_extra_base_hit': float(p_extra_base_hit),
        'p_on_base_traditional': float(p_on_base_traditional),
        'p_reach_base_any': float(p_reach_base_any),
        'p_ball_in_play': float(p_ball_in_play),
        'expected_total_bases': float(expected_total_bases),
    }


def predict_pa_outcome_distribution(
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
            text(feature_query(feature_set)),
            engine,
            params={'game_id': game_id, 'plate_appearance_id': plate_appearance_id},
        )
    finally:
        engine.dispose()

    if frame.empty:
        raise ValueError(f'Plate appearance not found: {game_id}:{plate_appearance_id}')

    missing_features = [
        column for column in numeric_features + categorical_features if column not in frame
    ]
    if missing_features:
        raise ValueError(f"Missing model features: {', '.join(missing_features)}")

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
            raise ValueError('Calibration artifact classes do not match model classes.')
        raw_probability_map = {
            label: float(raw_probabilities[index]) for index, label in enumerate(classes)
        }
        probability_vector = apply_calibrators(
            raw_probabilities.reshape(1, -1),
            calibration_artifact['calibrators'],
        )[0]

    probabilities = {label: float(probability_vector[index]) for index, label in enumerate(classes)}
    probability_sum = float(sum(probabilities.values()))

    result = {
        'target_id': TARGET_ID,
        'game_id': game_id,
        'plate_appearance_id': plate_appearance_id,
        'actual_outcome_class': frame.iloc[0].get('actual_outcome_class'),
        'model': {
            'model_name': metadata['model_name'],
            'model_version': metadata['model_version'],
            'artifact_uri': metadata['artifact_uri'],
            'feature_set': feature_set,
            'is_active': bool(metadata['is_active']),
        },
        'probability_sum': probability_sum,
        'class_probabilities': probabilities,
        'derived_probabilities': derived_probabilities(probabilities),
        'input_features': frame.iloc[0][numeric_features + categorical_features].to_dict(),
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
        description='Score a historical plate appearance with the multiclass PA outcome model.',
    )
    parser.add_argument('--game-id', required=True)
    parser.add_argument('--plate-appearance-id', required=True, type=int)
    parser.add_argument('--model-name', default=DEFAULT_MODEL_NAME)
    parser.add_argument('--model-version')
    parser.add_argument('--apply-calibration', action='store_true')
    parser.add_argument('--calibration-report-name')
    args = parser.parse_args()

    result = predict_pa_outcome_distribution(
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
