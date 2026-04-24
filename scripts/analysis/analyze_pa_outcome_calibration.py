#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from predict_pa_outcome_distribution import load_registered_model
from sqlalchemy import create_engine, text
from train_pa_outcome_distribution import (
    database_url,
    feature_columns,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_NAME = 'hist_gradient_boosting_multiclass'


def load_validation_frame(
    *,
    engine,
    feature_set: str,
    target_taxonomy: str,
    train_through: int,
    min_season: int,
    max_season: int,
) -> pd.DataFrame:
    source_relation = (
        'features.plate_appearance_outcome_grouped_examples'
        if target_taxonomy == 'grouped'
        else 'features.plate_appearance_outcome_examples'
    )
    target_column = 'grouped_outcome_class' if target_taxonomy == 'grouped' else 'outcome_class'

    if feature_set in {'advanced', 'advanced_count'}:
        advanced_relation = (
            'features.plate_appearance_count_state_advanced_examples'
            if feature_set == 'advanced_count'
            else 'features.plate_appearance_advanced_examples'
        )
        sql = f"""
            SELECT
                outcome.game_id,
                outcome.plate_appearance_id,
                outcome.season,
                outcome.{target_column} AS target,
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
                outcome.season_era,
                outcome.rules_context_era,
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
                advanced.fielding_team_rolling_30_runs_allowed_per_game
                {"," if feature_set == "advanced_count" else ""}
                {"advanced.batter_count_state_prior_pa," if feature_set == "advanced_count" else ""}
                {"advanced.batter_count_state_prior_hit_rate," if feature_set == "advanced_count" else ""}
                {"advanced.batter_count_state_prior_walk_rate," if feature_set == "advanced_count" else ""}
                {"advanced.batter_count_state_prior_strikeout_rate," if feature_set == "advanced_count" else ""}
                {"advanced.batter_count_state_prior_home_run_rate," if feature_set == "advanced_count" else ""}
                {"advanced.batter_count_state_prior_reach_base_rate," if feature_set == "advanced_count" else ""}
                {"advanced.batter_count_state_prior_extra_base_hit_rate," if feature_set == "advanced_count" else ""}
                {"advanced.pitcher_count_state_prior_batters_faced," if feature_set == "advanced_count" else ""}
                {"advanced.pitcher_count_state_prior_hit_allowed_rate," if feature_set == "advanced_count" else ""}
                {"advanced.pitcher_count_state_prior_walk_allowed_rate," if feature_set == "advanced_count" else ""}
                {"advanced.pitcher_count_state_prior_strikeout_rate," if feature_set == "advanced_count" else ""}
                {"advanced.pitcher_count_state_prior_home_run_allowed_rate," if feature_set == "advanced_count" else ""}
                {"advanced.pitcher_count_state_prior_reach_base_allowed_rate," if feature_set == "advanced_count" else ""}
                {"advanced.pitcher_count_state_prior_extra_base_hit_allowed_rate," if feature_set == "advanced_count" else ""}
                {"advanced.count_state_context_prior_pa," if feature_set == "advanced_count" else ""}
                {"advanced.count_state_context_prior_hit_rate," if feature_set == "advanced_count" else ""}
                {"advanced.count_state_context_prior_walk_rate," if feature_set == "advanced_count" else ""}
                {"advanced.count_state_context_prior_strikeout_rate," if feature_set == "advanced_count" else ""}
                {"advanced.count_state_context_prior_home_run_rate," if feature_set == "advanced_count" else ""}
                {"advanced.count_state_context_prior_reach_base_rate," if feature_set == "advanced_count" else ""}
                {"advanced.count_state_context_prior_extra_base_hit_rate" if feature_set == "advanced_count" else ""}
            FROM {source_relation} outcome
            JOIN {advanced_relation} advanced
              ON advanced.game_id = outcome.game_id
             AND advanced.plate_appearance_id = outcome.plate_appearance_id
            WHERE outcome.season > :train_through
              AND outcome.season BETWEEN :min_season AND :max_season
        """
    else:
        sql = f"""
            SELECT
                game_id,
                plate_appearance_id,
                season,
                {target_column} AS target,
                inning,
                is_bottom_inning::integer AS is_bottom_inning,
                outs_before,
                start_bases,
                balls,
                strikes,
                home_score_diff,
                COALESCE(batter_hand::text, 'U') AS batter_hand,
                COALESCE(pitcher_hand::text, 'U') AS pitcher_hand,
                season_era,
                rules_context_era
            FROM {source_relation}
            WHERE season > :train_through
              AND season BETWEEN :min_season AND :max_season
        """

    return pd.read_sql_query(
        text(sql),
        engine,
        params={
            'train_through': train_through,
            'min_season': min_season,
            'max_season': max_season,
        },
    )


def expected_calibration_error(actual: np.ndarray, predicted: np.ndarray, bins: int) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(actual)
    ece = 0.0
    for left, right in zip(edges[:-1], edges[1:]):
        if right == 1.0:
            mask = (predicted >= left) & (predicted <= right)
        else:
            mask = (predicted >= left) & (predicted < right)
        if not np.any(mask):
            continue
        bin_actual = actual[mask].mean()
        bin_pred = predicted[mask].mean()
        ece += (mask.sum() / total) * abs(bin_actual - bin_pred)
    return float(ece)


def class_calibration_table(
    *,
    actual: np.ndarray,
    predicted: np.ndarray,
    bins: int,
    class_name: str,
) -> list[dict]:
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows: list[dict] = []
    for index, (left, right) in enumerate(zip(edges[:-1], edges[1:]), start=1):
        if right == 1.0:
            mask = (predicted >= left) & (predicted <= right)
        else:
            mask = (predicted >= left) & (predicted < right)
        count = int(mask.sum())
        if count == 0:
            continue
        rows.append(
            {
                'class_name': class_name,
                'bin_index': index,
                'bin_left': float(left),
                'bin_right': float(right),
                'count': count,
                'mean_predicted': float(predicted[mask].mean()),
                'observed_rate': float(actual[mask].mean()),
                'absolute_gap': float(abs(predicted[mask].mean() - actual[mask].mean())),
            },
        )
    return rows


def subgroup_rows(
    *,
    frame: pd.DataFrame,
    predicted_class: np.ndarray,
    probabilities: np.ndarray,
    classes: list[str],
) -> list[dict]:
    top_probability = probabilities.max(axis=1)
    top_correct = (predicted_class == frame['target'].to_numpy()).astype(int)
    subgroup_specs = {
        'balls_strikes': frame['balls'].astype(str) + '-' + frame['strikes'].astype(str),
        'outs_before': frame['outs_before'].astype(str),
        'start_bases': frame['start_bases'].astype(str),
        'handedness_matchup': frame['batter_hand'].astype(str)
        + 'v'
        + frame['pitcher_hand'].astype(str),
        'season': frame['season'].astype(str),
    }

    results: list[dict] = []
    for subgroup_name, series in subgroup_specs.items():
        temp = pd.DataFrame(
            {
                'subgroup_value': series,
                'target': frame['target'],
                'predicted_class': predicted_class,
                'top_probability': top_probability,
                'top_correct': top_correct,
            },
        )
        grouped = temp.groupby('subgroup_value', dropna=False)
        for subgroup_value, group in grouped:
            actual = group['top_correct'].to_numpy(dtype=float)
            predicted = group['top_probability'].to_numpy(dtype=float)
            results.append(
                {
                    'subgroup_name': subgroup_name,
                    'subgroup_value': str(subgroup_value),
                    'rows': len(group),
                    'accuracy': float(actual.mean()),
                    'mean_top_probability': float(predicted.mean()),
                    'top_probability_gap': float(abs(predicted.mean() - actual.mean())),
                },
            )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Evaluate calibration and subgroup reliability for a registered PA outcome model.',
    )
    parser.add_argument('--model-name', default=DEFAULT_MODEL_NAME)
    parser.add_argument('--model-version', default=None)
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

    features = frame[numeric_features + categorical_features]
    probabilities = model.predict_proba(features)
    predicted_class = model.predict(features)
    classes = [str(label) for label in model.named_steps['model'].classes_]

    per_class_summary: list[dict] = []
    calibration_bins: list[dict] = []
    class_to_index = {label: index for index, label in enumerate(classes)}
    target_array = frame['target'].to_numpy()

    for class_name in classes:
        index = class_to_index[class_name]
        actual = (target_array == class_name).astype(float)
        predicted = probabilities[:, index]
        support = int(actual.sum())
        class_ece = expected_calibration_error(actual, predicted, args.bins)
        calibration_bins.extend(
            class_calibration_table(
                actual=actual,
                predicted=predicted,
                bins=args.bins,
                class_name=class_name,
            ),
        )
        per_class_summary.append(
            {
                'class_name': class_name,
                'support': support,
                'mean_predicted_probability': float(predicted.mean()),
                'observed_rate': float(actual.mean()),
                'absolute_gap': float(abs(predicted.mean() - actual.mean())),
                'ece': class_ece,
            },
        )

    subgroup_summary = subgroup_rows(
        frame=frame,
        predicted_class=predicted_class,
        probabilities=probabilities,
        classes=classes,
    )

    report = {
        'model_name': metadata['model_name'],
        'model_version': metadata['model_version'],
        'feature_set': feature_set,
        'target_taxonomy': target_taxonomy,
        'train_through': train_through,
        'validation_seasons': [train_through + 1, max_season],
        'rows': len(frame),
        'classes': classes,
        'registered_validation_metrics': metadata['metrics']['validation'],
        'per_class_summary': per_class_summary,
        'calibration_bins': calibration_bins,
        'subgroup_summary': subgroup_summary,
    }

    if args.output_json:
        output_path = Path(args.output_json)
        if not output_path.is_absolute():
            output_path = ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8',
        )

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
