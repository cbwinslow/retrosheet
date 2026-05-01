#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sqlalchemy import create_engine

# Import the sibling ``train_models`` module using a relative import so that the
# package can be resolved correctly when the ``scripts`` directory is a Python
# package (as defined by ``scripts/__init__.py``).
from . import train_models


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / 'data' / 'models'


def feature_columns(target_id: str, feature_set: str) -> tuple[list[str], list[str]]:
    if target_id == 'game_home_win':
        if feature_set == 'advanced':
            return (
                train_models.GAME_ADVANCED_NUMERIC_FEATURES,
                train_models.GAME_ADVANCED_CATEGORICAL_FEATURES,
            )
        if feature_set == 'enriched':
            return (
                train_models.GAME_ENRICHED_NUMERIC_FEATURES,
                train_models.GAME_ENRICHED_CATEGORICAL_FEATURES,
            )
        return train_models.GAME_NUMERIC_FEATURES, train_models.GAME_CATEGORICAL_FEATURES

    if target_id in train_models.PA_TARGETS:
        if feature_set == 'advanced':
            return (
                train_models.PA_ADVANCED_NUMERIC_FEATURES,
                train_models.PA_ADVANCED_CATEGORICAL_FEATURES,
            )
        if feature_set == 'enriched':
            return (
                train_models.PA_ENRICHED_NUMERIC_FEATURES,
                train_models.PA_ENRICHED_CATEGORICAL_FEATURES,
            )
        return train_models.PA_NUMERIC_FEATURES, train_models.PA_CATEGORICAL_FEATURES

    msg = f'Unknown target_id: {target_id}'
    raise ValueError(msg)


def hgb_candidates() -> list[tuple[str, HistGradientBoostingClassifier]]:
    grid = itertools.product(
        [150, 250, 400],
        [0.03, 0.05, 0.08],
        [15, 31, 63],
        [0.0, 0.01, 0.1],
    )
    return [
        (
            f'hgb_iter{max_iter}_lr{str(learning_rate).replace(".", "")}_leaf{max_leaf_nodes}_l2{str(l2_regularization).replace(".", "")}',
            HistGradientBoostingClassifier(
                max_iter=max_iter,
                learning_rate=learning_rate,
                max_leaf_nodes=max_leaf_nodes,
                l2_regularization=l2_regularization,
                random_state=42,
            ),
        )
        for max_iter, learning_rate, max_leaf_nodes, l2_regularization in grid
    ]


def logistic_candidates() -> list[tuple[str, LogisticRegression]]:
    return [
        (
            f'logreg_c{str(c_value).replace(".", "")}',
            LogisticRegression(C=c_value, max_iter=2000),
        )
        for c_value in [0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
    ]


def train_candidate(
    *,
    model,
    numeric_features: list[str],
    categorical_features: list[str],
    train_frame,
    validation_frame,
) -> tuple[Pipeline, dict]:
    pipeline = Pipeline(
        [
            (
                'preprocess',
                train_models.preprocessor(
                    numeric_features=numeric_features,
                    categorical_features=categorical_features,
                    scale_numeric=isinstance(model, LogisticRegression),
                ),
            ),
            ('model', model),
        ],
    )
    pipeline.fit(train_frame[numeric_features + categorical_features], train_frame['target'])
    metrics = {
        'train': train_models.metrics_for(
            pipeline,
            train_frame,
            numeric_features=numeric_features,
            categorical_features=categorical_features,
        ),
        'validation': train_models.metrics_for(
            pipeline,
            validation_frame,
            numeric_features=numeric_features,
            categorical_features=categorical_features,
        ),
    }
    return pipeline, metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Run a reproducible hyperparameter sweep against warehouse examples.',
    )
    parser.add_argument('--target-id', required=True)
    parser.add_argument(
        '--feature-set',
        choices=['basic', 'enriched', 'advanced'],
        default='advanced',
    )
    parser.add_argument('--min-season', type=int, default=2000)
    parser.add_argument('--max-season', type=int, default=2025)
    parser.add_argument('--train-through', type=int, default=2022)
    parser.add_argument('--sample-rate', type=float, default=0.05)
    parser.add_argument(
        '--families',
        nargs='+',
        choices=['hgb', 'logistic'],
        default=['hgb', 'logistic'],
    )
    parser.add_argument('--max-candidates', type=int, default=12)
    parser.add_argument('--activate', action='store_true')
    args = parser.parse_args()

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    numeric_features, categorical_features = feature_columns(args.target_id, args.feature_set)
    engine = create_engine(train_models.database_url())
    conn = train_models.psycopg2.connect(**train_models.database_kwargs())
    try:
        frame = train_models.load_examples(
            engine,
            target_id=args.target_id,
            min_season=args.min_season,
            max_season=args.max_season,
            sample_rate=args.sample_rate,
            feature_set=args.feature_set,
        )
        train_frame = frame[frame['season'] <= args.train_through].copy()
        validation_frame = frame[frame['season'] > args.train_through].copy()
        if train_frame.empty or validation_frame.empty:
            msg = 'Need both training and validation rows.'
            raise SystemExit(msg)

        candidates = []
        if 'hgb' in args.families:
            candidates.extend(hgb_candidates())
        if 'logistic' in args.families:
            candidates.extend(logistic_candidates())
        candidates = candidates[: args.max_candidates]
        version = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')

        leaderboard = []
        for candidate_name, model in candidates:
            pipeline, metrics = train_candidate(
                model=model,
                numeric_features=numeric_features,
                categorical_features=categorical_features,
                train_frame=train_frame,
                validation_frame=validation_frame,
            )
            model_name = f'sweep_{candidate_name}'
            artifact_path = MODEL_DIR / f'{args.target_id}_{model_name}_{version}.joblib'
            joblib.dump(pipeline, artifact_path)
            feature_spec = {
                'numeric_features': numeric_features,
                'categorical_features': categorical_features,
                'target': 'target',
                'feature_set': args.feature_set,
                'sweep': True,
            }
            metrics.update(
                {
                    'sample_rate': args.sample_rate,
                    'min_season': args.min_season,
                    'max_season': args.max_season,
                    'train_through': args.train_through,
                    'candidate_name': candidate_name,
                },
            )
            train_models.register_model(
                conn,
                target_id=args.target_id,
                model_name=model_name,
                model_family=type(model).__name__,
                version=version,
                artifact_path=artifact_path,
                feature_spec=feature_spec,
                metrics=metrics,
                activate=args.activate,
            )
            leaderboard.append(
                (
                    candidate_name,
                    metrics['validation']['roc_auc'],
                    metrics['validation']['log_loss'],
                ),
            )
            print(f'trained {candidate_name}: {json.dumps(metrics["validation"], sort_keys=True)}')

        print('\nLeaderboard:')
        for name, roc_auc, loss in sorted(leaderboard, key=lambda row: row[1], reverse=True):
            print(f'{name}\troc_auc={roc_auc:.6f}\tlog_loss={loss:.6f}')
    finally:
        engine.dispose()
        conn.close()


if __name__ == '__main__':
    main()
