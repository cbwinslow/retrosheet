#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from analyze_pa_outcome_calibration import feature_columns, load_validation_frame
from predict_pa_outcome_distribution import load_registered_model
from sqlalchemy import create_engine
from train_pa_outcome_distribution import database_url


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_NAME = 'hist_gradient_boosting_multiclass'


def f1_from_confusion(confusion: np.ndarray) -> tuple[float, float]:
    tp = np.diag(confusion).astype(float)
    pred_count = confusion.sum(axis=0).astype(float)
    true_count = confusion.sum(axis=1).astype(float)

    precision = np.divide(tp, pred_count, out=np.zeros_like(tp), where=pred_count > 0)
    recall = np.divide(tp, true_count, out=np.zeros_like(tp), where=true_count > 0)
    denom = precision + recall
    f1 = np.divide(2 * precision * recall, denom, out=np.zeros_like(tp), where=denom > 0)

    macro = float(f1.mean())
    weights = np.divide(
        true_count,
        true_count.sum(),
        out=np.zeros_like(true_count),
        where=true_count.sum() > 0,
    )
    weighted = float((f1 * weights).sum())
    return macro, weighted


def build_game_cache(
    *,
    frame: pd.DataFrame,
    probabilities: np.ndarray,
    classes: list[str],
) -> tuple[dict[str, dict], dict[int, np.ndarray]]:
    class_to_index = {label: index for index, label in enumerate(classes)}
    target_index = np.array([class_to_index[label] for label in frame['target']], dtype=np.int64)
    predicted_index = probabilities.argmax(axis=1)
    top3_index = np.argpartition(probabilities, -min(3, len(classes)), axis=1)[
        :,
        -min(3, len(classes)) :,
    ]
    top3_correct = np.any(top3_index == target_index[:, None], axis=1).astype(np.int64)

    row_loss = -np.log(
        np.clip(probabilities[np.arange(len(target_index)), target_index], 1e-12, 1.0),
    )
    one_hot = np.zeros_like(probabilities)
    one_hot[np.arange(len(target_index)), target_index] = 1.0
    row_brier = np.sum((probabilities - one_hot) ** 2, axis=1)
    row_correct = (predicted_index == target_index).astype(np.int64)

    game_cache: dict[str, dict] = {}
    season_games: dict[int, np.ndarray] = {}

    for season, season_group in frame.groupby('season', sort=True):
        season_games[int(season)] = season_group['game_id'].drop_duplicates().to_numpy()

    for game_id, group in frame.groupby('game_id', sort=False):
        idx = group.index.to_numpy()
        confusion = np.zeros((len(classes), len(classes)), dtype=np.int64)
        np.add.at(confusion, (target_index[idx], predicted_index[idx]), 1)
        game_cache[str(game_id)] = {
            'n_rows': len(idx),
            'loss_sum': float(row_loss[idx].sum()),
            'brier_sum': float(row_brier[idx].sum()),
            'correct_sum': int(row_correct[idx].sum()),
            'top3_sum': int(top3_correct[idx].sum()),
            'confusion': confusion,
        }

    return game_cache, season_games


def bootstrap_game_samples(
    *,
    season_games: dict[int, np.ndarray],
    replicates: int,
    seed: int,
) -> list[list[str]]:
    rng = np.random.default_rng(seed)
    samples: list[list[str]] = []
    for _ in range(replicates):
        selected_games: list[str] = []
        for season in sorted(season_games):
            games = season_games[season]
            sampled = rng.choice(games, size=len(games), replace=True)
            selected_games.extend(str(game_id) for game_id in sampled.tolist())
        samples.append(selected_games)
    return samples


def metric_summary_from_games(game_ids: list[str], game_cache: dict[str, dict]) -> dict[str, float]:
    total_rows = 0
    total_loss = 0.0
    total_brier = 0.0
    total_correct = 0
    total_top3 = 0
    confusion = None

    for game_id in game_ids:
        entry = game_cache[game_id]
        total_rows += entry['n_rows']
        total_loss += entry['loss_sum']
        total_brier += entry['brier_sum']
        total_correct += entry['correct_sum']
        total_top3 += entry['top3_sum']
        if confusion is None:
            confusion = entry['confusion'].copy()
        else:
            confusion += entry['confusion']

    assert confusion is not None
    f1_macro, f1_weighted = f1_from_confusion(confusion)
    return {
        'log_loss': float(total_loss / total_rows),
        'brier_score_multiclass': float(total_brier / total_rows),
        'accuracy': float(total_correct / total_rows),
        'f1_macro': f1_macro,
        'f1_weighted': f1_weighted,
        'top_3_accuracy': float(total_top3 / total_rows),
    }


def summarize_metric(rows: list[dict], metric_name: str) -> dict[str, float]:
    values = np.array([row[metric_name] for row in rows], dtype=float)
    return {
        'mean': float(values.mean()),
        'std': float(values.std(ddof=1)),
        'p05': float(np.quantile(values, 0.05)),
        'p50': float(np.quantile(values, 0.50)),
        'p95': float(np.quantile(values, 0.95)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Run season-stratified cluster bootstrap evaluation for a registered PA outcome model.',
    )
    parser.add_argument('--model-name', default=DEFAULT_MODEL_NAME)
    parser.add_argument('--model-version', required=True)
    parser.add_argument('--replicates', type=int, default=100)
    parser.add_argument('--seed', type=int, default=42)
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

    classes = [str(label) for label in model.named_steps['model'].classes_]
    frame = frame[frame['target'].isin(classes)].copy().reset_index(drop=True)
    features = frame[numeric_features + categorical_features]
    probabilities = model.predict_proba(features)

    game_cache, season_games = build_game_cache(
        frame=frame,
        probabilities=probabilities,
        classes=classes,
    )
    sampled_games = bootstrap_game_samples(
        season_games=season_games,
        replicates=args.replicates,
        seed=args.seed,
    )
    replicate_metrics = [
        metric_summary_from_games(game_ids, game_cache) for game_ids in sampled_games
    ]

    summary = {
        'model_name': metadata['model_name'],
        'model_version': metadata['model_version'],
        'feature_set': feature_set,
        'target_taxonomy': target_taxonomy,
        'validation_seasons': [train_through + 1, max_season],
        'rows': len(frame),
        'replicates': args.replicates,
        'seed': args.seed,
        'metrics': {
            'log_loss': summarize_metric(replicate_metrics, 'log_loss'),
            'brier_score_multiclass': summarize_metric(replicate_metrics, 'brier_score_multiclass'),
            'accuracy': summarize_metric(replicate_metrics, 'accuracy'),
            'f1_macro': summarize_metric(replicate_metrics, 'f1_macro'),
            'f1_weighted': summarize_metric(replicate_metrics, 'f1_weighted'),
            'top_3_accuracy': summarize_metric(replicate_metrics, 'top_3_accuracy'),
        },
    }

    if args.output_json:
        output_path = Path(args.output_json)
        if not output_path.is_absolute():
            output_path = ROOT / args.output_json
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + '\n',
            encoding='utf-8',
        )

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
