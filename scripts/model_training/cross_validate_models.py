#!/usr/bin/env python3
"""
Cross-Validation Evaluation Script

Provides robust model evaluation using k-fold cross-validation
to give better performance estimates and avoid overfitting.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
import psycopg2
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import roc_auc_score, accuracy_score, log_loss, brier_score_loss
from sqlalchemy import create_engine

import train_models


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "data" / "models"


def database_kwargs() -> dict[str, str]:
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "retrosheet"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }


def database_url() -> str:
    kwargs = database_kwargs()
    return f"postgresql+psycopg2://{kwargs['user']}:{kwargs['password']}@{kwargs['host']}:{kwargs['port']}/{kwargs['dbname']}"


def get_active_models(target_id: str) -> List[Dict]:
    """Get all active models for a target."""
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT model_name, model_family, artifact_uri, feature_spec
                FROM models.model_registry
                WHERE target_id = %s AND is_active = true
                ORDER BY model_family, model_name
                """,
                (target_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "model_name": row[0],
                    "model_family": row[1],
                    "artifact_path": ROOT / row[2],
                    "feature_spec": row[3],
                }
                for row in rows
            ]
    finally:
        conn.close()


def load_training_data(target_id: str, sample_rate: float = 0.1) -> pd.DataFrame:
    """Load training data for cross-validation."""
    engine = create_engine(database_url())

    # Use the same logic as train_models.py to determine feature set
    if target_id == "game_home_win":
        feature_set = "enriched"  # Default for game models
    elif target_id in train_models.PA_TARGETS:
        feature_set = "enriched"  # Default for PA models
    elif target_id in train_models.HI_TARGETS:
        feature_set = "basic"  # Only basic for half-inning
    else:
        raise ValueError(f"Unknown target_id: {target_id}")

    try:
        frame = train_models.load_examples(
            engine,
            target_id=target_id,
            min_season=2000,
            max_season=2022,  # Use data through 2022 for CV
            sample_rate=sample_rate,
            feature_set=feature_set,
        )
        return frame
    finally:
        engine.dispose()


def evaluate_model_cv(
    model_path: Path, feature_spec: Dict, data: pd.DataFrame, cv_folds: int = 5
) -> Dict:
    """Evaluate a model using cross-validation."""

    # Load the trained model
    model = joblib.load(model_path)

    # Extract features
    numeric_features = feature_spec["numeric_features"]
    categorical_features = feature_spec["categorical_features"]
    feature_cols = numeric_features + categorical_features

    X = data[feature_cols]
    y = data["target"]

    # Set up cross-validation
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)

    # Define scoring metrics
    scoring_metrics = {
        "roc_auc": roc_auc_score,
        "accuracy": accuracy_score,
        "neg_log_loss": lambda y_true, y_pred: -log_loss(y_true, y_pred),
        "brier_score": lambda y_true, y_pred: -brier_score_loss(y_true, y_pred),
    }

    results = {}

    for metric_name, metric_func in scoring_metrics.items():
        try:
            if metric_name == "roc_auc":
                # For ROC AUC, we need predicted probabilities
                scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
            elif metric_name == "accuracy":
                scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
            elif metric_name == "neg_log_loss":
                scores = cross_val_score(model, X, y, cv=cv, scoring="neg_log_loss")
            elif metric_name == "brier_score":
                # Custom scoring for brier score
                brier_scores = []
                for train_idx, test_idx in cv.split(X, y):
                    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
                    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

                    model.fit(X_train, y_train)
                    y_pred_proba = model.predict_proba(X_test)[:, 1]
                    brier_scores.append(-brier_score_loss(y_test, y_pred_proba))
                scores = np.array(brier_scores)

            results[metric_name] = {
                "mean": float(scores.mean()),
                "std": float(scores.std()),
                "scores": scores.tolist(),
            }

        except Exception as e:
            results[metric_name] = {"error": str(e)}

    return results


def run_cross_validation(
    target_id: str, sample_rate: float = 0.1, cv_folds: int = 5
) -> Dict:
    """Run cross-validation evaluation for all active models of a target."""

    print(f"Running {cv_folds}-fold cross-validation for {target_id}")

    # Get active models
    models = get_active_models(target_id)
    if not models:
        raise ValueError(f"No active models found for {target_id}")

    # Load training data
    data = load_training_data(target_id, sample_rate)
    print(f"Loaded {len(data)} training samples")

    # Evaluate each model
    results = {}
    for model_info in models:
        model_name = model_info["model_name"]
        print(f"Evaluating {model_name}...")

        cv_results = evaluate_model_cv(
            model_info["artifact_path"], model_info["feature_spec"], data, cv_folds
        )

        results[model_name] = {
            "model_family": model_info["model_family"],
            "cv_folds": cv_folds,
            "sample_rate": sample_rate,
            "training_samples": len(data),
            "metrics": cv_results,
        }

    return results


def print_summary(results: Dict) -> None:
    """Print a summary of cross-validation results."""
    print("\n" + "=" * 60)
    print("CROSS-VALIDATION RESULTS SUMMARY")
    print("=" * 60)

    for model_name, result in results.items():
        print(f"\n{model_name} ({result['model_family']}):")
        print(f"  CV Folds: {result['cv_folds']}")
        print(f"  Training Samples: {result['training_samples']:,}")

        metrics = result["metrics"]
        for metric_name, metric_data in metrics.items():
            if "error" in metric_data:
                print(f"  {metric_name}: ERROR - {metric_data['error']}")
            else:
                mean_val = metric_data["mean"]
                std_val = metric_data["std"]
                if metric_name in ["roc_auc", "accuracy"]:
                    print(".4f")
                elif metric_name in ["neg_log_loss"]:
                    print(".4f")
                elif metric_name in ["brier_score"]:
                    print(".4f")


def main():
    parser = argparse.ArgumentParser(
        description="Run cross-validation evaluation on trained models"
    )
    parser.add_argument(
        "--target-id",
        required=True,
        help="Target to evaluate (e.g., pa_batter_hit, half_inning_any_run)",
    )
    parser.add_argument(
        "--sample-rate", type=float, default=0.05, help="Sample rate for training data"
    )
    parser.add_argument(
        "--cv-folds", type=int, default=5, help="Number of cross-validation folds"
    )
    parser.add_argument("--output-json", type=str, help="Save results to JSON file")

    args = parser.parse_args()

    try:
        results = run_cross_validation(args.target_id, args.sample_rate, args.cv_folds)

        print_summary(results)

        if args.output_json:
            with open(args.output_json, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to {args.output_json}")

    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
