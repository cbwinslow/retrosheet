#!/usr/bin/env python3
"""
Automatic Model Promotion Script

Uses cross-validation results to automatically promote the best models
for each target, ensuring we always have the highest-performing active models.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import psycopg2

import cross_validate_models


ROOT = Path(__file__).resolve().parents[1]


def database_kwargs() -> dict[str, str]:
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "retrosheet"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }


def get_targets_to_evaluate(prefix: str = None) -> List[str]:
    """Get all targets that have active models."""
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            if prefix:
                cur.execute(
                    """
                    SELECT DISTINCT target_id
                    FROM models.model_registry
                    WHERE is_active = true AND target_id LIKE %s
                    ORDER BY target_id
                    """,
                    (f"{prefix}%",),
                )
            else:
                cur.execute(
                    """
                    SELECT DISTINCT target_id
                    FROM models.model_registry
                    WHERE is_active = true
                    ORDER BY target_id
                    """
                )
            rows = cur.fetchall()
            return [row[0] for row in rows]
    finally:
        conn.close()


def evaluate_and_rank_models(
    target_id: str, sample_rate: float = 0.05
) -> List[Tuple[str, float]]:
    """Evaluate all active models for a target and rank by CV ROC AUC."""
    cv_results = cross_validate_models.run_cross_validation(
        target_id, sample_rate, cv_folds=3
    )

    # Extract ROC AUC scores for ranking
    model_scores = []
    for model_name, result in cv_results.items():
        metrics = result["metrics"]
        if "roc_auc" in metrics and "mean" in metrics["roc_auc"]:
            score = metrics["roc_auc"]["mean"]
            model_scores.append((model_name, score))

    # Sort by ROC AUC descending
    model_scores.sort(key=lambda x: x[1], reverse=True)
    return model_scores


def promote_best_models(
    target_id: str,
    ranked_models: List[Tuple[str, float]],
    min_validation_rows: int = 10000,
) -> None:
    """Promote the best model for a target."""
    if not ranked_models:
        print(f"No models to evaluate for {target_id}")
        return

    best_model_name, best_score = ranked_models[0]
    print(
        f"Best model for {target_id}: {best_model_name} (CV ROC AUC: {best_score:.4f})"
    )

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # First, deactivate all other models for this target
            cur.execute(
                """
                UPDATE models.model_registry
                SET is_active = false, updated_at = now()
                WHERE target_id = %s AND model_name != %s AND is_active = true
                """,
                (target_id, best_model_name),
            )

            # Then activate the best model (if not already active)
            cur.execute(
                """
                UPDATE models.model_registry
                SET is_active = true, updated_at = now()
                WHERE target_id = %s AND model_name = %s
                """,
                (target_id, best_model_name),
            )

            print(f"Promoted {best_model_name} for {target_id}")
        conn.commit()
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Automatically promote best models based on cross-validation"
    )
    parser.add_argument(
        "--target-prefix",
        help="Only evaluate targets with this prefix (e.g., 'pa_' for plate appearance models)",
    )
    parser.add_argument(
        "--sample-rate", type=float, default=0.05, help="Sample rate for CV evaluation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be promoted without making changes",
    )

    args = parser.parse_args()

    targets = get_targets_to_evaluate(args.target_prefix)
    print(f"Evaluating {len(targets)} targets: {targets}")

    for target_id in targets:
        print(f"\n--- Evaluating {target_id} ---")

        try:
            ranked_models = evaluate_and_rank_models(target_id, args.sample_rate)
            if ranked_models:
                print("Model ranking:")
                for i, (model_name, score) in enumerate(ranked_models[:3], 1):
                    print(f"  {i}. {model_name}: {score:.4f}")

                if not args.dry_run:
                    promote_best_models(target_id, ranked_models)
                else:
                    best_model_name, best_score = ranked_models[0]
                    print(
                        f"Would promote: {best_model_name} (CV ROC AUC: {best_score:.4f})"
                    )
            else:
                print(f"No valid models found for {target_id}")

        except Exception as e:
            print(f"Error evaluating {target_id}: {e}")

    if args.dry_run:
        print("\n--- DRY RUN COMPLETE ---")
        print("No changes were made. Remove --dry-run to apply promotions.")
    else:
        print("\n--- PROMOTION COMPLETE ---")


if __name__ == "__main__":
    main()
