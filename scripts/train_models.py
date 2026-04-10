#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import psycopg2
from sqlalchemy import URL, create_engine
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "data" / "models"


NUMERIC_FEATURES = [
    "inning",
    "is_bottom_inning",
    "outs_before",
    "start_bases",
    "balls",
    "strikes",
    "home_score_diff",
    "away_score_before",
    "home_score_before",
]
CATEGORICAL_FEATURES = ["batter_hand", "pitcher_hand"]
TARGET = "final_home_win"


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


def load_examples(engine, *, min_season: int, max_season: int, sample_rate: float) -> pd.DataFrame:
    if not 0 < sample_rate <= 1:
        raise ValueError("--sample-rate must be between 0 and 1")
    sample_ppm = int(sample_rate * 1_000_000)
    sql = """
        SELECT
            season,
            inning,
            is_bottom_inning::integer AS is_bottom_inning,
            outs_before,
            start_bases,
            balls,
            strikes,
            home_score_diff,
            away_score_before,
            home_score_before,
            COALESCE(batter_hand::text, 'U') AS batter_hand,
            COALESCE(pitcher_hand::text, 'U') AS pitcher_hand,
            final_home_win::integer AS final_home_win
        FROM features.game_outcome_examples
        WHERE season BETWEEN %(min_season)s AND %(max_season)s
          AND final_home_win IS NOT NULL
          AND mod(abs(hashtext(game_id || ':' || event_id::text)), 1000000) < %(sample_ppm)s
    """
    return pd.read_sql_query(
        sql,
        conn,
        params={"min_season": min_season, "max_season": max_season, "sample_ppm": sample_ppm},
    )


def preprocessor(*, scale_numeric: bool) -> ColumnTransformer:
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
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ]
    )


def build_models() -> dict[str, Pipeline]:
    return {
        "logistic_regression": Pipeline(
            [
                ("preprocess", preprocessor(scale_numeric=True)),
                ("model", LogisticRegression(max_iter=1000)),
            ]
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("preprocess", preprocessor(scale_numeric=False)),
                ("model", HistGradientBoostingClassifier(max_iter=250, learning_rate=0.05, random_state=42)),
            ]
        ),
    }


def metrics_for(model: Pipeline, frame: pd.DataFrame) -> dict[str, float]:
    features = frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    target = frame[TARGET]
    probabilities = model.predict_proba(features)[:, 1]
    predictions = probabilities >= 0.5
    return {
        "rows": int(len(frame)),
        "log_loss": float(log_loss(target, probabilities)),
        "roc_auc": float(roc_auc_score(target, probabilities)),
        "brier_score": float(brier_score_loss(target, probabilities)),
        "accuracy": float(accuracy_score(target, predictions)),
    }


def register_model(conn, *, model_name: str, model_family: str, version: str, artifact_path: Path, metrics: dict) -> None:
    feature_spec = {
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "target": TARGET,
    }
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO models.model_registry (
                target_id, model_name, model_family, model_version, artifact_uri,
                feature_spec, metrics, is_active
            )
            VALUES (
                'game_home_win', %(model_name)s, %(model_family)s, %(version)s, %(artifact_uri)s,
                %(feature_spec)s::jsonb, %(metrics)s::jsonb, false
            )
            ON CONFLICT (target_id, model_name, model_version) DO UPDATE
            SET artifact_uri = EXCLUDED.artifact_uri,
                feature_spec = EXCLUDED.feature_spec,
                metrics = EXCLUDED.metrics;
            """,
            {
                "model_name": model_name,
                "model_family": model_family,
                "version": version,
                "artifact_uri": str(artifact_path.relative_to(ROOT)),
                "feature_spec": json.dumps(feature_spec),
                "metrics": json.dumps(metrics),
            },
        )
    conn.commit()


def train(args: argparse.Namespace) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    conn = psycopg2.connect(**database_kwargs())
    engine = create_engine(database_url())
    try:
        frame = load_examples(
            engine,
            min_season=args.min_season,
            max_season=args.max_season,
            sample_rate=args.sample_rate,
        )
        if frame.empty:
            raise SystemExit("No training rows returned. Check features.game_outcome_examples and season filters.")

        train_frame = frame[frame["season"] <= args.train_through].copy()
        validation_frame = frame[frame["season"] > args.train_through].copy()
        if train_frame.empty or validation_frame.empty:
            raise SystemExit("Need both training and validation rows. Adjust --train-through or season range.")

        version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        for model_name, model in build_models().items():
            model.fit(train_frame[NUMERIC_FEATURES + CATEGORICAL_FEATURES], train_frame[TARGET])
            metrics = {
                "train": metrics_for(model, train_frame),
                "validation": metrics_for(model, validation_frame),
                "sample_rate": args.sample_rate,
                "min_season": args.min_season,
                "max_season": args.max_season,
                "train_through": args.train_through,
            }
            artifact_path = MODEL_DIR / f"game_home_win_{model_name}_{version}.joblib"
            joblib.dump(model, artifact_path)
            register_model(
                conn,
                model_name=model_name,
                model_family=model_name,
                version=version,
                artifact_path=artifact_path,
                metrics=metrics,
            )
            print(f"trained {model_name}: {json.dumps(metrics['validation'], sort_keys=True)}")
            print(f"artifact: {artifact_path}")
    finally:
        engine.dispose()
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Train warehouse-backed Retrosheet prediction models.")
    parser.add_argument("--min-season", type=int, default=2000)
    parser.add_argument("--max-season", type=int, default=2025)
    parser.add_argument("--train-through", type=int, default=2022)
    parser.add_argument("--sample-rate", type=float, default=0.10, help="Deterministic row sample from 0.0 to 1.0.")
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
