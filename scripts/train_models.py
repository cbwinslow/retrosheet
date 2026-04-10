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
from sqlalchemy import URL, create_engine, text
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "data" / "models"


GAME_NUMERIC_FEATURES = [
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
GAME_CATEGORICAL_FEATURES = ["batter_hand", "pitcher_hand"]
GAME_TARGET = "final_home_win"

PA_NUMERIC_FEATURES = [
    "inning",
    "is_bottom_inning",
    "outs_before",
    "start_bases",
    "balls",
    "strikes",
    "home_score_diff",
]
PA_CATEGORICAL_FEATURES = ["batter_hand", "pitcher_hand"]
PA_ENRICHED_NUMERIC_FEATURES = PA_NUMERIC_FEATURES + [
    "batter_prior_pa",
    "batter_prior_hit_rate",
    "batter_prior_walk_rate",
    "batter_prior_strikeout_rate",
    "batter_prior_home_run_rate",
    "batter_prior_reach_base_rate",
    "batter_prior_extra_base_hit_rate",
    "pitcher_prior_batters_faced",
    "pitcher_prior_hit_allowed_rate",
    "pitcher_prior_walk_allowed_rate",
    "pitcher_prior_strikeout_rate",
    "pitcher_prior_home_run_allowed_rate",
    "pitcher_prior_reach_base_allowed_rate",
    "pitcher_prior_extra_base_hit_allowed_rate",
    "batting_team_prior_win_rate",
    "batting_team_prior_runs_scored_per_game",
    "batting_team_prior_runs_allowed_per_game",
    "fielding_team_prior_win_rate",
    "fielding_team_prior_runs_scored_per_game",
    "fielding_team_prior_runs_allowed_per_game",
    "context_prior_pa",
    "context_prior_hit_rate",
    "context_prior_walk_rate",
    "context_prior_strikeout_rate",
    "context_prior_home_run_rate",
    "context_prior_reach_base_rate",
    "context_prior_extra_base_hit_rate",
    "context_prior_batting_team_win_rate",
]
PA_ENRICHED_CATEGORICAL_FEATURES = PA_CATEGORICAL_FEATURES

GAME_ENRICHED_NUMERIC_FEATURES = GAME_NUMERIC_FEATURES + [
    "batter_prior_pa",
    "batter_prior_hit_rate",
    "batter_prior_walk_rate",
    "batter_prior_strikeout_rate",
    "batter_prior_home_run_rate",
    "batter_prior_reach_base_rate",
    "batter_prior_extra_base_hit_rate",
    "pitcher_prior_batters_faced",
    "pitcher_prior_hit_allowed_rate",
    "pitcher_prior_walk_allowed_rate",
    "pitcher_prior_strikeout_rate",
    "pitcher_prior_home_run_allowed_rate",
    "pitcher_prior_reach_base_allowed_rate",
    "pitcher_prior_extra_base_hit_allowed_rate",
    "home_team_prior_win_rate",
    "home_team_prior_runs_scored_per_game",
    "home_team_prior_runs_allowed_per_game",
    "away_team_prior_win_rate",
    "away_team_prior_runs_scored_per_game",
    "away_team_prior_runs_allowed_per_game",
    "context_prior_pa",
    "context_prior_hit_rate",
    "context_prior_walk_rate",
    "context_prior_strikeout_rate",
    "context_prior_home_run_rate",
    "context_prior_reach_base_rate",
    "context_prior_extra_base_hit_rate",
    "context_prior_batting_team_win_rate",
]
GAME_ENRICHED_CATEGORICAL_FEATURES = GAME_CATEGORICAL_FEATURES
PA_TARGETS = {
    "pa_batter_hit": "is_hit",
    "pa_batter_walk": "is_walk",
    "pa_batter_strikeout": "is_strikeout",
    "pa_batter_home_run": "is_home_run",
    "pa_batter_reach_base": "is_reach_base",
    "pa_batter_extra_base_hit": "is_extra_base_hit",
}


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


def load_examples(
    engine,
    *,
    target_id: str,
    min_season: int,
    max_season: int,
    sample_rate: float,
    feature_set: str,
) -> pd.DataFrame:
    if not 0 < sample_rate <= 1:
        raise ValueError("--sample-rate must be between 0 and 1")
    sample_ppm = int(sample_rate * 1_000_000)

    if target_id == "game_home_win" and feature_set == "basic":
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
            WHERE season BETWEEN :min_season AND :max_season
              AND final_home_win IS NOT NULL
              AND mod(abs(hashtext(game_id || ':' || event_id::text)), 1000000) < :sample_ppm
        """
        target_col = "final_home_win"
    elif target_id == "game_home_win" and feature_set == "enriched":
        sql = """
            SELECT
                examples.season,
                examples.inning,
                examples.is_bottom_inning::integer AS is_bottom_inning,
                examples.outs_before,
                examples.start_bases,
                examples.balls,
                examples.strikes,
                examples.home_score_diff,
                examples.away_score_before,
                examples.home_score_before,
                COALESCE(examples.batter_hand::text, 'U') AS batter_hand,
                COALESCE(examples.pitcher_hand::text, 'U') AS pitcher_hand,
                batter.prior_pa AS batter_prior_pa,
                batter.prior_hit_rate AS batter_prior_hit_rate,
                batter.prior_walk_rate AS batter_prior_walk_rate,
                batter.prior_strikeout_rate AS batter_prior_strikeout_rate,
                batter.prior_home_run_rate AS batter_prior_home_run_rate,
                batter.prior_reach_base_rate AS batter_prior_reach_base_rate,
                batter.prior_extra_base_hit_rate AS batter_prior_extra_base_hit_rate,
                pitcher.prior_batters_faced AS pitcher_prior_batters_faced,
                pitcher.prior_hit_allowed_rate AS pitcher_prior_hit_allowed_rate,
                pitcher.prior_walk_allowed_rate AS pitcher_prior_walk_allowed_rate,
                pitcher.prior_strikeout_rate AS pitcher_prior_strikeout_rate,
                pitcher.prior_home_run_allowed_rate AS pitcher_prior_home_run_allowed_rate,
                pitcher.prior_reach_base_allowed_rate AS pitcher_prior_reach_base_allowed_rate,
                pitcher.prior_extra_base_hit_allowed_rate AS pitcher_prior_extra_base_hit_allowed_rate,
                home_team.prior_win_rate AS home_team_prior_win_rate,
                home_team.prior_runs_scored_per_game AS home_team_prior_runs_scored_per_game,
                home_team.prior_runs_allowed_per_game AS home_team_prior_runs_allowed_per_game,
                away_team.prior_win_rate AS away_team_prior_win_rate,
                away_team.prior_runs_scored_per_game AS away_team_prior_runs_scored_per_game,
                away_team.prior_runs_allowed_per_game AS away_team_prior_runs_allowed_per_game,
                context.prior_pa AS context_prior_pa,
                context.prior_hit_rate AS context_prior_hit_rate,
                context.prior_walk_rate AS context_prior_walk_rate,
                context.prior_strikeout_rate AS context_prior_strikeout_rate,
                context.prior_home_run_rate AS context_prior_home_run_rate,
                context.prior_reach_base_rate AS context_prior_reach_base_rate,
                context.prior_extra_base_hit_rate AS context_prior_extra_base_hit_rate,
                context.prior_batting_team_win_rate AS context_prior_batting_team_win_rate,
                examples.final_home_win::integer AS final_home_win
            FROM features.game_outcome_examples examples
            LEFT JOIN features.batter_prior_season_pa_summary batter
              ON batter.feature_season = examples.season
             AND batter.batter_id = examples.batter_id
            LEFT JOIN features.pitcher_prior_season_pa_summary pitcher
              ON pitcher.feature_season = examples.season
             AND pitcher.pitcher_id = examples.pitcher_id
            LEFT JOIN features.team_prior_season_summary home_team
              ON home_team.feature_season = examples.season
             AND home_team.team_id = examples.home_team_id
            LEFT JOIN features.team_prior_season_summary away_team
              ON away_team.feature_season = examples.season
             AND away_team.team_id = examples.away_team_id
            LEFT JOIN features.pa_context_prior_season_rates context
              ON context.feature_season = examples.season
             AND context.batter_hand = COALESCE(examples.batter_hand::text, 'U')
             AND context.pitcher_hand = COALESCE(examples.pitcher_hand::text, 'U')
             AND context.inning = examples.inning
             AND context.is_bottom_inning = examples.is_bottom_inning
             AND context.outs_before = examples.outs_before
             AND context.start_bases = examples.start_bases
             AND context.balls = examples.balls
             AND context.strikes = examples.strikes
            WHERE examples.season BETWEEN :min_season AND :max_season
              AND examples.final_home_win IS NOT NULL
              AND mod(abs(hashtext(examples.game_id || ':' || examples.event_id::text)), 1000000) < :sample_ppm
        """
        target_col = "final_home_win"
    elif target_id in PA_TARGETS and feature_set == "basic":
        target_col_name = PA_TARGETS[target_id]
        sql = f"""
            SELECT
                season,
                inning,
                is_bottom_inning::integer AS is_bottom_inning,
                outs_before,
                start_bases,
                balls,
                strikes,
                home_score_diff,
                COALESCE(batter_hand::text, 'U') AS batter_hand,
                COALESCE(pitcher_hand::text, 'U') AS pitcher_hand,
                {target_col_name}::integer AS target
            FROM features.plate_appearance_examples
            WHERE season BETWEEN :min_season AND :max_season
              AND {target_col_name} IS NOT NULL
              AND mod(abs(hashtext(game_id || ':' || plate_appearance_id::text)), 1000000) < :sample_ppm
        """
        target_col = "target"
    elif target_id in PA_TARGETS and feature_set == "enriched":
        target_col_name = PA_TARGETS[target_id]
        sql = f"""
            SELECT
                examples.season,
                examples.inning,
                examples.is_bottom_inning::integer AS is_bottom_inning,
                examples.outs_before,
                examples.start_bases,
                examples.balls,
                examples.strikes,
                examples.home_score_diff,
                COALESCE(examples.batter_hand::text, 'U') AS batter_hand,
                COALESCE(examples.pitcher_hand::text, 'U') AS pitcher_hand,
                batter.prior_pa AS batter_prior_pa,
                batter.prior_hit_rate AS batter_prior_hit_rate,
                batter.prior_walk_rate AS batter_prior_walk_rate,
                batter.prior_strikeout_rate AS batter_prior_strikeout_rate,
                batter.prior_home_run_rate AS batter_prior_home_run_rate,
                batter.prior_reach_base_rate AS batter_prior_reach_base_rate,
                batter.prior_extra_base_hit_rate AS batter_prior_extra_base_hit_rate,
                pitcher.prior_batters_faced AS pitcher_prior_batters_faced,
                pitcher.prior_hit_allowed_rate AS pitcher_prior_hit_allowed_rate,
                pitcher.prior_walk_allowed_rate AS pitcher_prior_walk_allowed_rate,
                pitcher.prior_strikeout_rate AS pitcher_prior_strikeout_rate,
                pitcher.prior_home_run_allowed_rate AS pitcher_prior_home_run_allowed_rate,
                pitcher.prior_reach_base_allowed_rate AS pitcher_prior_reach_base_allowed_rate,
                pitcher.prior_extra_base_hit_allowed_rate AS pitcher_prior_extra_base_hit_allowed_rate,
                batting_team.prior_win_rate AS batting_team_prior_win_rate,
                batting_team.prior_runs_scored_per_game AS batting_team_prior_runs_scored_per_game,
                batting_team.prior_runs_allowed_per_game AS batting_team_prior_runs_allowed_per_game,
                fielding_team.prior_win_rate AS fielding_team_prior_win_rate,
                fielding_team.prior_runs_scored_per_game AS fielding_team_prior_runs_scored_per_game,
                fielding_team.prior_runs_allowed_per_game AS fielding_team_prior_runs_allowed_per_game,
                context.prior_pa AS context_prior_pa,
                context.prior_hit_rate AS context_prior_hit_rate,
                context.prior_walk_rate AS context_prior_walk_rate,
                context.prior_strikeout_rate AS context_prior_strikeout_rate,
                context.prior_home_run_rate AS context_prior_home_run_rate,
                context.prior_reach_base_rate AS context_prior_reach_base_rate,
                context.prior_extra_base_hit_rate AS context_prior_extra_base_hit_rate,
                context.prior_batting_team_win_rate AS context_prior_batting_team_win_rate,
                examples.{target_col_name}::integer AS target
            FROM features.plate_appearance_examples examples
            LEFT JOIN features.batter_prior_season_pa_summary batter
              ON batter.feature_season = examples.season
             AND batter.batter_id = examples.batter_id
            LEFT JOIN features.pitcher_prior_season_pa_summary pitcher
              ON pitcher.feature_season = examples.season
             AND pitcher.pitcher_id = examples.pitcher_id
            LEFT JOIN features.team_prior_season_summary batting_team
              ON batting_team.feature_season = examples.season
             AND batting_team.team_id = examples.batting_team_id
            LEFT JOIN features.team_prior_season_summary fielding_team
              ON fielding_team.feature_season = examples.season
             AND fielding_team.team_id = examples.fielding_team_id
            LEFT JOIN features.pa_context_prior_season_rates context
              ON context.feature_season = examples.season
             AND context.batter_hand = COALESCE(examples.batter_hand::text, 'U')
             AND context.pitcher_hand = COALESCE(examples.pitcher_hand::text, 'U')
             AND context.inning = examples.inning
             AND context.is_bottom_inning = examples.is_bottom_inning
             AND context.outs_before = examples.outs_before
             AND context.start_bases = examples.start_bases
             AND context.balls = examples.balls
             AND context.strikes = examples.strikes
            WHERE examples.season BETWEEN :min_season AND :max_season
              AND examples.{target_col_name} IS NOT NULL
              AND mod(abs(hashtext(examples.game_id || ':' || examples.plate_appearance_id::text)), 1000000) < :sample_ppm
        """
        target_col = "target"
    else:
        raise ValueError(f"Unknown target_id: {target_id}")

    df = pd.read_sql_query(
        text(sql),
        engine,
        params={
            "min_season": min_season,
            "max_season": max_season,
            "sample_ppm": sample_ppm,
        },
    )
    return df.rename(columns={target_col: "target"})


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
        "logistic_regression": Pipeline(
            [
                (
                    "preprocess",
                    preprocessor(
                        numeric_features=numeric_features,
                        categorical_features=categorical_features,
                        scale_numeric=True,
                    ),
                ),
                ("model", LogisticRegression(max_iter=1000)),
            ]
        ),
        "hist_gradient_boosting": Pipeline(
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
                        max_iter=250, learning_rate=0.05, random_state=42
                    ),
                ),
            ]
        ),
    }


def metrics_for(
    model: Pipeline,
    frame: pd.DataFrame,
    *,
    numeric_features: list[str],
    categorical_features: list[str],
) -> dict[str, float]:
    features = frame[numeric_features + categorical_features]
    target = frame["target"]
    probabilities = model.predict_proba(features)[:, 1]
    predictions = probabilities >= 0.5
    return {
        "rows": int(len(frame)),
        "log_loss": float(log_loss(target, probabilities)),
        "roc_auc": float(roc_auc_score(target, probabilities)),
        "brier_score": float(brier_score_loss(target, probabilities)),
        "accuracy": float(accuracy_score(target, predictions)),
    }


def register_model(
    conn,
    *,
    target_id: str,
    model_name: str,
    model_family: str,
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
                {"target_id": target_id, "model_name": model_name},
            )
        cur.execute(
            """
            INSERT INTO models.model_registry (
                target_id, model_name, model_family, model_version, artifact_uri,
                feature_spec, metrics, is_active
            )
            VALUES (
                %(target_id)s, %(model_name)s, %(model_family)s, %(version)s, %(artifact_uri)s,
                %(feature_spec)s::jsonb, %(metrics)s::jsonb, %(activate)s
            )
            ON CONFLICT (target_id, model_name, model_version) DO UPDATE
            SET artifact_uri = EXCLUDED.artifact_uri,
                feature_spec = EXCLUDED.feature_spec,
                metrics = EXCLUDED.metrics,
                is_active = EXCLUDED.is_active;
            """,
            {
                "target_id": target_id,
                "model_name": model_name,
                "model_family": model_family,
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
    conn = psycopg2.connect(**database_kwargs())
    engine = create_engine(database_url())
    try:
        if args.target_id == "game_home_win":
            if args.feature_set == "enriched":
                numeric_features = GAME_ENRICHED_NUMERIC_FEATURES
                categorical_features = GAME_ENRICHED_CATEGORICAL_FEATURES
            else:
                numeric_features = GAME_NUMERIC_FEATURES
                categorical_features = GAME_CATEGORICAL_FEATURES
        elif args.target_id in PA_TARGETS:
            if args.feature_set == "enriched":
                numeric_features = PA_ENRICHED_NUMERIC_FEATURES
                categorical_features = PA_ENRICHED_CATEGORICAL_FEATURES
            else:
                numeric_features = PA_NUMERIC_FEATURES
                categorical_features = PA_CATEGORICAL_FEATURES
        else:
            raise ValueError(f"Unknown target_id: {args.target_id}")

        frame = load_examples(
            engine,
            target_id=args.target_id,
            min_season=args.min_season,
            max_season=args.max_season,
            sample_rate=args.sample_rate,
            feature_set=args.feature_set,
        )
        if frame.empty:
            raise SystemExit(
                f"No training rows returned for {args.target_id}. Check the feature table and season filters."
            )

        train_frame = frame[frame["season"] <= args.train_through].copy()
        validation_frame = frame[frame["season"] > args.train_through].copy()
        if train_frame.empty or validation_frame.empty:
            raise SystemExit(
                "Need both training and validation rows. Adjust --train-through or season range."
            )

        version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        feature_spec = {
            "numeric_features": numeric_features,
            "categorical_features": categorical_features,
            "target": "target",
            "feature_set": args.feature_set,
        }
        for model_name, model in build_models(
            numeric_features=numeric_features, categorical_features=categorical_features
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
            }
            artifact_path = (
                MODEL_DIR / f"{args.target_id}_{model_name}_{version}.joblib"
            )
            joblib.dump(model, artifact_path)
            register_model(
                conn,
                target_id=args.target_id,
                model_name=model_name,
                model_family=model_name,
                version=version,
                artifact_path=artifact_path,
                feature_spec=feature_spec,
                metrics=metrics,
                activate=not args.no_activate,
            )
            print(
                f"trained {model_name}: {json.dumps(metrics['validation'], sort_keys=True)}"
            )
            print(f"artifact: {artifact_path}")
    finally:
        engine.dispose()
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train warehouse-backed Retrosheet prediction models."
    )
    parser.add_argument("--target-id", required=True, help="Target to train model for")
    parser.add_argument("--min-season", type=int, default=2000)
    parser.add_argument("--max-season", type=int, default=2025)
    parser.add_argument("--train-through", type=int, default=2022)
    parser.add_argument(
        "--sample-rate",
        type=float,
        default=0.10,
        help="Deterministic row sample from 0.0 to 1.0.",
    )
    parser.add_argument(
        "--feature-set",
        choices=["basic", "enriched"],
        default="enriched",
        help="Use basic state features or enriched prior-season feature marts.",
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
