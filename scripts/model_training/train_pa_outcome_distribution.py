#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import catboost as cb
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import psycopg2
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, log_loss, top_k_accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sqlalchemy import URL, create_engine, text


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / 'data' / 'models'
TARGET_ID = 'pa_outcome_distribution'

BASIC_NUMERIC_FEATURES = [
    'inning',
    'is_bottom_inning',
    'outs_before',
    'start_bases',
    'balls',
    'strikes',
    'home_score_diff',
]
BASIC_CATEGORICAL_FEATURES = ['batter_hand', 'pitcher_hand', 'season_era', 'rules_context_era']

ADVANCED_NUMERIC_FEATURES = [
    *BASIC_NUMERIC_FEATURES,
    'batter_career_prior_pa',
    'batter_career_prior_hit_rate',
    'batter_career_prior_walk_rate',
    'batter_career_prior_strikeout_rate',
    'batter_career_prior_home_run_rate',
    'batter_career_prior_reach_base_rate',
    'pitcher_career_prior_batters_faced',
    'pitcher_career_prior_hit_allowed_rate',
    'pitcher_career_prior_walk_allowed_rate',
    'pitcher_career_prior_strikeout_rate',
    'pitcher_career_prior_home_run_allowed_rate',
    'pitcher_career_prior_reach_base_allowed_rate',
    'prior_matchup_pa',
    'prior_matchup_hit_rate',
    'prior_matchup_walk_rate',
    'prior_matchup_strikeout_rate',
    'prior_matchup_home_run_rate',
    'prior_matchup_reach_base_rate',
    'coarse_context_prior_pa',
    'coarse_context_prior_hit_rate',
    'coarse_context_prior_walk_rate',
    'coarse_context_prior_strikeout_rate',
    'coarse_context_prior_home_run_rate',
    'coarse_context_prior_reach_base_rate',
    'coarse_context_prior_extra_base_hit_rate',
    'park_prior_total_runs_per_game',
    'park_prior_home_win_rate',
    'batting_team_rolling_30_games',
    'batting_team_rolling_30_win_rate',
    'batting_team_rolling_30_runs_scored_per_game',
    'batting_team_rolling_30_runs_allowed_per_game',
    'fielding_team_rolling_30_games',
    'fielding_team_rolling_30_win_rate',
    'fielding_team_rolling_30_runs_scored_per_game',
    'fielding_team_rolling_30_runs_allowed_per_game',
]
ADVANCED_CATEGORICAL_FEATURES = [*BASIC_CATEGORICAL_FEATURES, 'park_id']
ADVANCED_COUNT_NUMERIC_FEATURES = [
    *ADVANCED_NUMERIC_FEATURES,
    'batter_count_state_prior_pa',
    'batter_count_state_prior_hit_rate',
    'batter_count_state_prior_walk_rate',
    'batter_count_state_prior_strikeout_rate',
    'batter_count_state_prior_home_run_rate',
    'batter_count_state_prior_reach_base_rate',
    'batter_count_state_prior_extra_base_hit_rate',
    'pitcher_count_state_prior_batters_faced',
    'pitcher_count_state_prior_hit_allowed_rate',
    'pitcher_count_state_prior_walk_allowed_rate',
    'pitcher_count_state_prior_strikeout_rate',
    'pitcher_count_state_prior_home_run_allowed_rate',
    'pitcher_count_state_prior_reach_base_allowed_rate',
    'pitcher_count_state_prior_extra_base_hit_allowed_rate',
    'count_state_context_prior_pa',
    'count_state_context_prior_hit_rate',
    'count_state_context_prior_walk_rate',
    'count_state_context_prior_strikeout_rate',
    'count_state_context_prior_home_run_rate',
    'count_state_context_prior_reach_base_rate',
    'count_state_context_prior_extra_base_hit_rate',
]
ADVANCED_COUNT_CATEGORICAL_FEATURES = ADVANCED_CATEGORICAL_FEATURES


def database_kwargs() -> dict[str, str]:
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def database_url() -> str | URL:
    if os.environ.get('DATABASE_URL'):
        return os.environ['DATABASE_URL']
    kwargs = database_kwargs()
    return URL.create(
        'postgresql+psycopg2',
        username=kwargs['user'],
        password=kwargs['password'] or None,
        host=kwargs['host'],
        port=int(kwargs['port']),
        database=kwargs['dbname'],
    )


def feature_columns(feature_set: str) -> tuple[list[str], list[str]]:
    if feature_set == 'advanced_count':
        return ADVANCED_COUNT_NUMERIC_FEATURES, ADVANCED_COUNT_CATEGORICAL_FEATURES
    if feature_set == 'advanced':
        return ADVANCED_NUMERIC_FEATURES, ADVANCED_CATEGORICAL_FEATURES
    return BASIC_NUMERIC_FEATURES, BASIC_CATEGORICAL_FEATURES


def load_examples(
    engine,
    *,
    min_season: int,
    max_season: int,
    sample_rate: float,
    feature_set: str,
    target_taxonomy: str,
) -> pd.DataFrame:
    if not 0 < sample_rate <= 1:
        raise ValueError('--sample-rate must be between 0 and 1')
    sample_ppm = int(sample_rate * 1_000_000)

    if target_taxonomy not in {'granular', 'grouped'}:
        raise ValueError('--target-taxonomy must be granular or grouped')

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
        sql = (
            """
            SELECT
                outcome.season,
                outcome."""
            + target_column
            + """ AS target,
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
            FROM """
            + source_relation
            + """ outcome
            JOIN """
            + advanced_relation
            + """ advanced
              ON advanced.game_id = outcome.game_id
             AND advanced.plate_appearance_id = outcome.plate_appearance_id
            WHERE outcome.season BETWEEN :min_season AND :max_season
              AND mod(abs(hashtext(outcome.game_id || ':' || outcome.plate_appearance_id::text)), 1000000) < :sample_ppm
        """
        )
    else:
        sql = (
            """
            SELECT
                season,
                """
            + target_column
            + """ AS target,
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
            FROM """
            + source_relation
            + """
            WHERE season BETWEEN :min_season AND :max_season
              AND mod(abs(hashtext(game_id || ':' || plate_appearance_id::text)), 1000000) < :sample_ppm
        """
        )

    return pd.read_sql_query(
        text(sql),
        engine,
        params={
            'min_season': min_season,
            'max_season': max_season,
            'sample_ppm': sample_ppm,
        },
    )


def filter_sparse_classes(frame: pd.DataFrame, min_class_rows: int) -> pd.DataFrame:
    counts = frame['target'].value_counts()
    keep = counts[counts >= min_class_rows].index
    return frame[frame['target'].isin(keep)].copy()


def apply_recent_window(
    frame: pd.DataFrame,
    *,
    train_through: int,
    recent_window: int | None,
) -> pd.DataFrame:
    if recent_window is None:
        return frame
    min_included_season = train_through - recent_window + 1
    return frame[frame['season'] >= min_included_season].copy()


def season_weight_map(
    *,
    min_season: int,
    max_season: int,
    train_through: int,
    season_half_life: float | None,
    downweight_2020: float | None,
) -> dict[int, float]:
    weights: dict[int, float] = {}
    for season in range(min_season, max_season + 1):
        weight = 1.0
        if season_half_life is not None:
            weight *= float(2 ** (-(train_through - season) / season_half_life))
        if downweight_2020 is not None and season == 2020:
            weight *= downweight_2020
        weights[season] = weight
    return weights


def add_temporal_weights(
    frame: pd.DataFrame,
    *,
    train_through: int,
    season_half_life: float | None,
    downweight_2020: float | None,
) -> tuple[pd.DataFrame, dict[int, float]]:
    frame = frame.copy()
    weights = season_weight_map(
        min_season=int(frame['season'].min()),
        max_season=int(frame['season'].max()),
        train_through=train_through,
        season_half_life=season_half_life,
        downweight_2020=downweight_2020,
    )
    frame['sample_weight'] = frame['season'].map(weights).astype(float)
    return frame, weights


def preprocessor(
    *,
    numeric_features: list[str],
    categorical_features: list[str],
    scale_numeric: bool,
) -> ColumnTransformer:
    numeric_steps = [('imputer', SimpleImputer(strategy='median'))]
    if scale_numeric:
        numeric_steps.append(('scaler', StandardScaler()))
    numeric = Pipeline(numeric_steps)
    categorical = Pipeline(
        [
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('onehot', OneHotEncoder(handle_unknown='ignore')),
        ],
    )
    return ColumnTransformer(
        [
            ('numeric', numeric, numeric_features),
            ('categorical', categorical, categorical_features),
        ],
    )


def build_models(
    *,
    numeric_features: list[str],
    categorical_features: list[str],
    args,
) -> dict[str, Pipeline]:
    return {
        'multinomial_logistic_regression': Pipeline(
            [
                (
                    'preprocess',
                    preprocessor(
                        numeric_features=numeric_features,
                        categorical_features=categorical_features,
                        scale_numeric=True,
                    ),
                ),
                (
                    'model',
                    LogisticRegression(
                        max_iter=1000,
                        class_weight='balanced',
                    ),
                ),
            ],
        ),
        'hist_gradient_boosting_multiclass': Pipeline(
            [
                (
                    'preprocess',
                    preprocessor(
                        numeric_features=numeric_features,
                        categorical_features=categorical_features,
                        scale_numeric=False,
                    ),
                ),
                (
                    'model',
                    (
                        HistGradientBoostingClassifier(
                            max_iter=250,
                            learning_rate=0.05,
                            random_state=42,
                        )
                        if args.model_type == 'hist_gradient_boosting'
                        else xgb.XGBClassifier(
                            n_estimators=250,
                            learning_rate=0.05,
                            random_state=42,
                            use_label_encoder=False,
                            eval_metric='mlogloss',
                        )
                        if args.model_type == 'xgboost'
                        else lgb.LGBMClassifier(
                            n_estimators=250,
                            learning_rate=0.05,
                            random_state=42,
                            verbose=-1,
                        )
                        if args.model_type == 'lightgbm'
                        else cb.CatBoostClassifier(
                            iterations=250,
                            learning_rate=0.05,
                            random_state=42,
                            verbose=False,
                        )
                        if args.model_type == 'catboost'
                        else LogisticRegression(max_iter=1000, random_state=42)
                    ),
                ),
            ],
        ),
    }


def multiclass_brier_score(
    classes: np.ndarray,
    target: pd.Series,
    probabilities: np.ndarray,
) -> float:
    class_to_index = {label: index for index, label in enumerate(classes)}
    actual = np.zeros_like(probabilities)
    for row_index, label in enumerate(target):
        actual[row_index, class_to_index[label]] = 1.0
    return float(np.mean(np.sum((probabilities - actual) ** 2, axis=1)))


def metrics_for(
    model: Pipeline,
    frame: pd.DataFrame,
    *,
    numeric_features: list[str],
    categorical_features: list[str],
) -> dict[str, float | int]:
    features = frame[numeric_features + categorical_features]
    target = frame['target']
    probabilities = model.predict_proba(features)
    predictions = model.predict(features)
    classes = model.named_steps['model'].classes_
    return {
        'rows': len(frame),
        'classes': len(classes),
        'log_loss': float(log_loss(target, probabilities, labels=classes)),
        'brier_score_multiclass': multiclass_brier_score(classes, target, probabilities),
        'accuracy': float(accuracy_score(target, predictions)),
        'f1_macro': float(f1_score(target, predictions, average='macro')),
        'f1_weighted': float(f1_score(target, predictions, average='weighted')),
        'top_3_accuracy': float(
            top_k_accuracy_score(
                target,
                probabilities,
                k=min(3, len(classes)),
                labels=classes,
            ),
        ),
    }


def register_model(
    conn,
    *,
    model_name: str,
    version: str,
    artifact_path: Path,
    feature_spec: dict,
    metrics: dict,
    activate: bool,
) -> None:
    with conn.cursor() as cur:
        if activate:
            cur.execute(
                """
                UPDATE models.model_registry
                SET is_active = false
                WHERE target_id = %(target_id)s
                  AND model_name = %(model_name)s;
                """,
                {'target_id': TARGET_ID, 'model_name': model_name},
            )
        cur.execute(
            """
            INSERT INTO models.model_registry (
                target_id, model_name, model_family, model_version, artifact_uri,
                feature_spec, metrics, is_active
            )
            VALUES (
                %(target_id)s, %(model_name)s, %(model_name)s, %(version)s, %(artifact_uri)s,
                %(feature_spec)s::jsonb, %(metrics)s::jsonb, %(activate)s
            )
            ON CONFLICT (target_id, model_name, model_version) DO UPDATE
            SET artifact_uri = EXCLUDED.artifact_uri,
                feature_spec = EXCLUDED.feature_spec,
                metrics = EXCLUDED.metrics,
                is_active = EXCLUDED.is_active;
            """,
            {
                'target_id': TARGET_ID,
                'model_name': model_name,
                'version': version,
                'artifact_uri': str(artifact_path.relative_to(ROOT)),
                'feature_spec': json.dumps(feature_spec),
                'metrics': json.dumps(metrics),
                'activate': activate,
            },
        )
    conn.commit()


def train(args: argparse.Namespace) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    numeric_features, categorical_features = feature_columns(args.feature_set)
    engine = create_engine(database_url())
    conn = psycopg2.connect(**database_kwargs())
    try:
        frame = load_examples(
            engine,
            min_season=args.min_season,
            max_season=args.max_season,
            sample_rate=args.sample_rate,
            feature_set=args.feature_set,
            target_taxonomy=args.target_taxonomy,
        )
        if args.exclude_2020:
            frame = frame[frame['season'] != 2020].copy()
        frame = apply_recent_window(
            frame,
            train_through=args.train_through,
            recent_window=args.recent_window,
        )
        frame = filter_sparse_classes(frame, args.min_class_rows)
        if frame.empty:
            raise SystemExit('No rows returned after sparse-class filtering.')

        train_frame = frame[frame['season'] <= args.train_through].copy()
        validation_frame = frame[frame['season'] > args.train_through].copy()
        if train_frame.empty or validation_frame.empty:
            raise SystemExit('Need both training and validation rows.')
        train_frame, train_season_weights = add_temporal_weights(
            train_frame,
            train_through=args.train_through,
            season_half_life=args.season_half_life,
            downweight_2020=args.downweight_2020,
        )
        validation_frame['sample_weight'] = 1.0

        version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        class_counts = frame['target'].value_counts().sort_index().to_dict()
        feature_spec = {
            'numeric_features': numeric_features,
            'categorical_features': categorical_features,
            'target': 'target',
            'target_id': TARGET_ID,
            'feature_set': args.feature_set,
            'target_taxonomy': args.target_taxonomy,
            'min_class_rows': args.min_class_rows,
            'classes': sorted(frame['target'].unique().tolist()),
            'recent_window': args.recent_window,
            'season_half_life': args.season_half_life,
            'exclude_2020': args.exclude_2020,
            'downweight_2020': args.downweight_2020,
        }

        for model_name, model in build_models(
            numeric_features=numeric_features,
            categorical_features=categorical_features,
            args=args,
        ).items():
            model.fit(
                train_frame[numeric_features + categorical_features],
                train_frame['target'],
                model__sample_weight=train_frame['sample_weight'].to_numpy(),
            )
            metrics = {
                'train': metrics_for(
                    model,
                    train_frame,
                    numeric_features=numeric_features,
                    categorical_features=categorical_features,
                ),
                'validation': metrics_for(
                    model,
                    validation_frame,
                    numeric_features=numeric_features,
                    categorical_features=categorical_features,
                ),
                'sample_rate': args.sample_rate,
                'min_season': args.min_season,
                'max_season': args.max_season,
                'train_through': args.train_through,
                'target_taxonomy': args.target_taxonomy,
                'recent_window': args.recent_window,
                'season_half_life': args.season_half_life,
                'exclude_2020': args.exclude_2020,
                'downweight_2020': args.downweight_2020,
                'train_weight_sum': float(train_frame['sample_weight'].sum()),
                'season_weights': {str(k): float(v) for k, v in train_season_weights.items()},
                'class_counts': class_counts,
            }
            artifact_path = MODEL_DIR / f'{TARGET_ID}_{model_name}_{version}.joblib'
            joblib.dump(model, artifact_path)
            register_model(
                conn,
                model_name=model_name,
                version=version,
                artifact_path=artifact_path,
                feature_spec=feature_spec,
                metrics=metrics,
                activate=not args.no_activate,
            )
            print(f'trained {model_name}: {json.dumps(metrics["validation"], sort_keys=True)}')
            print(f'artifact: {artifact_path}')
    finally:
        engine.dispose()
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Train a multiclass plate-appearance outcome distribution model.',
    )
    parser.add_argument('--min-season', type=int, default=2000)
    parser.add_argument('--max-season', type=int, default=2025)
    parser.add_argument('--train-through', type=int, default=2022)
    parser.add_argument('--sample-rate', type=float, default=0.05)
    parser.add_argument(
        '--recent-window',
        type=int,
        default=None,
        help='Restrict training/validation rows to the most recent N seasons up to --max-season.',
    )
    parser.add_argument(
        '--season-half-life',
        type=float,
        default=None,
        help='Apply exponential recency weighting with half-life in seasons.',
    )
    parser.add_argument(
        '--exclude-2020',
        action='store_true',
        help='Exclude the shortened 2020 season entirely before training/validation splits.',
    )
    parser.add_argument(
        '--downweight-2020',
        type=float,
        default=None,
        help='Multiply 2020 training weight by this factor. Ignored if --exclude-2020 is set.',
    )
    parser.add_argument(
        '--feature-set',
        choices=['basic', 'advanced', 'advanced_count'],
        default='advanced',
        help='Use basic features, the existing advanced PA view, or the count-state-enhanced advanced PA view.',
    )
    parser.add_argument(
        '--target-taxonomy',
        choices=['granular', 'grouped'],
        default='granular',
        help='Train against the raw granular PA outcome classes or the grouped baseline taxonomy.',
    )
    parser.add_argument(
        '--min-class-rows',
        type=int,
        default=100,
        help='Drop classes with fewer sampled rows before training.',
    )
    parser.add_argument(
        '--model-type',
        type=str,
        default='hist_gradient_boosting',
        choices=[
            'hist_gradient_boosting',
            'xgboost',
            'lightgbm',
            'catboost',
            'logistic_regression',
        ],
        help='Model type to train',
    )
    parser.add_argument(
        '--no-activate',
        action='store_true',
        help='Register model metrics without marking the new version active.',
    )
    args = parser.parse_args()
    if args.recent_window is not None and args.recent_window <= 0:
        raise SystemExit('--recent-window must be positive.')
    if args.season_half_life is not None and args.season_half_life <= 0:
        raise SystemExit('--season-half-life must be positive.')
    if args.downweight_2020 is not None and not 0 < args.downweight_2020 <= 1:
        raise SystemExit('--downweight-2020 must be in the interval (0, 1].')
    if args.exclude_2020 and args.downweight_2020 is not None:
        raise SystemExit('--exclude-2020 and --downweight-2020 are mutually exclusive.')
    train(args)


if __name__ == '__main__':
    main()
