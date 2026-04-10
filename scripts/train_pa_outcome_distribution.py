#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import psycopg2
from sqlalchemy import URL, create_engine, text
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, log_loss, top_k_accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "data" / "models"
TARGET_ID = "pa_outcome_distribution"

BASIC_NUMERIC_FEATURES = [
    "inning",
    "is_bottom_inning",
    "outs_before",
    "start_bases",
    "balls",
    "strikes",
    "home_score_diff",
]
BASIC_CATEGORICAL_FEATURES = ["batter_hand", "pitcher_hand"]

ADVANCED_NUMERIC_FEATURES = BASIC_NUMERIC_FEATURES + [
    "batter_career_prior_pa",
    "batter_career_prior_hit_rate",
    "batter_career_prior_walk_rate",
    "batter_career_prior_strikeout_rate",
    "batter_career_prior_home_run_rate",
    "batter_career_prior_reach_base_rate",
    "pitcher_career_prior_batters_faced",
    "pitcher_career_prior_hit_allowed_rate",
    "pitcher_career_prior_walk_allowed_rate",
    "pitcher_career_prior_strikeout_rate",
    "pitcher_career_prior_home_run_allowed_rate",
    "pitcher_career_prior_reach_base_allowed_rate",
    "prior_matchup_pa",
    "prior_matchup_hit_rate",
    "prior_matchup_walk_rate",
    "prior_matchup_strikeout_rate",
    "prior_matchup_home_run_rate",
    "prior_matchup_reach_base_rate",
    "coarse_context_prior_pa",
    "coarse_context_prior_hit_rate",
    "coarse_context_prior_walk_rate",
    "coarse_context_prior_strikeout_rate",
    "coarse_context_prior_home_run_rate",
    "coarse_context_prior_reach_base_rate",
    "coarse_context_prior_extra_base_hit_rate",
    "park_prior_total_runs_per_game",
    "park_prior_home_win_rate",
    "batting_team_rolling_30_games",
    "batting_team_rolling_30_win_rate",
    "batting_team_rolling_30_runs_scored_per_game",
    "batting_team_rolling_30_runs_allowed_per_game",
    "fielding_team_rolling_30_games",
    "fielding_team_rolling_30_win_rate",
    "fielding_team_rolling_30_runs_scored_per_game",
    "fielding_team_rolling_30_runs_allowed_per_game",
]
ADVANCED_CATEGORICAL_FEATURES = BASIC_CATEGORICAL_FEATURES + ["park_id"]


def database_kwargs() -> dict[str, str]:
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "retrosheet"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }


def database_url() -> str | URL:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    kwargs = database_kwargs()
    return URL.create(
        "postgresql+psycopg2",
        username=kwargs["user"],
        password=kwargs["password"] or None,
        host=kwargs["host"],
        port=int(kwargs["port"]),
        database=kwargs["dbname"],
    )


def feature_columns(feature_set: str) -> tuple[list[str], list[str]]:
    if feature_set == "advanced":
        return ADVANCED_NUMERIC_FEATURES, ADVANCED_CATEGORICAL_FEATURES
    return BASIC_NUMERIC_FEATURES, BASIC_CATEGORICAL_FEATURES


def load_examples(
    engine,
    *,
    min_season: int,
    max_season: int,
    sample_rate: float,
    feature_set: str,
) -> pd.DataFrame:
    if not 0 < sample_rate <= 1:
        raise ValueError("--sample-rate must be between 0 and 1")
    sample_ppm = int(sample_rate * 1_000_000)

    if feature_set == "advanced":
        sql = """
            SELECT
                outcome.season,
                outcome.outcome_class AS target,
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
                advanced.fielding_team_rolling_30_runs_allowed_per_game
            FROM features.plate_appearance_outcome_examples outcome
            JOIN features.plate_appearance_advanced_examples advanced
              ON advanced.game_id = outcome.game_id
             AND advanced.plate_appearance_id = outcome.plate_appearance_id
            WHERE outcome.season BETWEEN :min_season AND :max_season
              AND mod(abs(hashtext(outcome.game_id || ':' || outcome.plate_appearance_id::text)), 1000000) < :sample_ppm
        """
    else:
        sql = """
            SELECT
                season,
                outcome_class AS target,
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
            WHERE season BETWEEN :min_season AND :max_season
              AND mod(abs(hashtext(game_id || ':' || plate_appearance_id::text)), 1000000) < :sample_ppm
        """

    return pd.read_sql_query(
        text(sql),
        engine,
        params={
            "min_season": min_season,
            "max_season": max_season,
            "sample_ppm": sample_ppm,
        },
    )


def filter_sparse_classes(frame: pd.DataFrame, min_class_rows: int) -> pd.DataFrame:
    counts = frame["target"].value_counts()
    keep = counts[counts >= min_class_rows].index
    return frame[frame["target"].isin(keep)].copy()


def preprocessor(
    *, numeric_features: list[str], categorical_features: list[str], scale_numeric: bool
) -> ColumnTransformer:
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))
    numeric = Pipeline(numeric_steps)
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric, numeric_features),
            ("categorical", categorical, categorical_features),
        ]
    )


def build_models(
    *, numeric_features: list[str], categorical_features: list[str]
) -> dict[str, Pipeline]:
    return {
        "multinomial_logistic_regression": Pipeline(
            [
                (
                    "preprocess",
                    preprocessor(
                        numeric_features=numeric_features,
                        categorical_features=categorical_features,
                        scale_numeric=True,
                    ),
                ),
                (
                    "model",
                    LogisticRegression(
                        max_iter=1000,
                        class_weight="balanced",
                    ),
                ),
            ]
        ),
        "hist_gradient_boosting_multiclass": Pipeline(
            [
                (
                    "preprocess",
                    preprocessor(
                        numeric_features=numeric_features,
                        categorical_features=categorical_features,
                        scale_numeric=False,
                    ),
                ),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        max_iter=250,
                        learning_rate=0.05,
                        random_state=42,
                    ),
                ),
            ]
        ),
    }


def multiclass_brier_score(classes: np.ndarray, target: pd.Series, probabilities: np.ndarray) -> float:
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
    target = frame["target"]
    probabilities = model.predict_proba(features)
    predictions = model.predict(features)
    classes = model.named_steps["model"].classes_
    return {
        "rows": int(len(frame)),
        "classes": int(len(classes)),
        "log_loss": float(log_loss(target, probabilities, labels=classes)),
        "brier_score_multiclass": multiclass_brier_score(classes, target, probabilities),
        "accuracy": float(accuracy_score(target, predictions)),
        "f1_macro": float(f1_score(target, predictions, average="macro")),
        "f1_weighted": float(f1_score(target, predictions, average="weighted")),
        "top_3_accuracy": float(
            top_k_accuracy_score(
                target,
                probabilities,
                k=min(3, len(classes)),
                labels=classes,
            )
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
                {"target_id": TARGET_ID, "model_name": model_name},
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
                "target_id": TARGET_ID,
                "model_name": model_name,
                "version": version,
                "artifact_uri": str(artifact_path.relative_to(ROOT)),
                "feature_spec": json.dumps(feature_spec),
                "metrics": json.dumps(metrics),
                "activate": activate,
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
        )
        frame = filter_sparse_classes(frame, args.min_class_rows)
        if frame.empty:
            raise SystemExit("No rows returned after sparse-class filtering.")

        train_frame = frame[frame["season"] <= args.train_through].copy()
        validation_frame = frame[frame["season"] > args.train_through].copy()
        if train_frame.empty or validation_frame.empty:
            raise SystemExit("Need both training and validation rows.")

        version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        class_counts = frame["target"].value_counts().sort_index().to_dict()
        feature_spec = {
            "numeric_features": numeric_features,
            "categorical_features": categorical_features,
            "target": "target",
            "target_id": TARGET_ID,
            "feature_set": args.feature_set,
            "min_class_rows": args.min_class_rows,
            "classes": sorted(frame["target"].unique().tolist()),
        }

        for model_name, model in build_models(
            numeric_features=numeric_features,
            categorical_features=categorical_features,
        ).items():
            model.fit(
                train_frame[numeric_features + categorical_features],
                train_frame["target"],
            )
            metrics = {
                "train": metrics_for(
                    model,
                    train_frame,
                    numeric_features=numeric_features,
                    categorical_features=categorical_features,
                ),
                "validation": metrics_for(
                    model,
                    validation_frame,
                    numeric_features=numeric_features,
                    categorical_features=categorical_features,
                ),
                "sample_rate": args.sample_rate,
                "min_season": args.min_season,
                "max_season": args.max_season,
                "train_through": args.train_through,
                "class_counts": class_counts,
            }
            artifact_path = MODEL_DIR / f"{TARGET_ID}_{model_name}_{version}.joblib"
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
            print(f"trained {model_name}: {json.dumps(metrics['validation'], sort_keys=True)}")
            print(f"artifact: {artifact_path}")
    finally:
        engine.dispose()
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train a multiclass plate-appearance outcome distribution model."
    )
    parser.add_argument("--min-season", type=int, default=2000)
    parser.add_argument("--max-season", type=int, default=2025)
    parser.add_argument("--train-through", type=int, default=2022)
    parser.add_argument("--sample-rate", type=float, default=0.05)
    parser.add_argument(
        "--feature-set",
        choices=["basic", "advanced"],
        default="advanced",
        help="Use basic game-state/count features or the existing advanced PA feature view.",
    )
    parser.add_argument(
        "--min-class-rows",
        type=int,
        default=100,
        help="Drop classes with fewer sampled rows before training.",
    )
    parser.add_argument(
        "--no-activate",
        action="store_true",
        help="Register model metrics without marking the new version active.",
    )
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
