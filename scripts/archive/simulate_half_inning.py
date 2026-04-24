#!/usr/bin/env python3
"""
Monte Carlo Half-Inning Simulation Script

Uses trained plate appearance models to simulate half-inning outcomes.
Given a half-inning starting state, simulates each plate appearance to predict
scenarios like "any run scores" or "left-handed batter gets hit".
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import pandas as pd
import psycopg2
from sqlalchemy import URL, create_engine

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


def load_pa_model(target_id: str, model_name: str = "hist_gradient_boosting") -> Tuple:
    """Load a trained plate appearance model."""
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT artifact_uri, feature_spec
                FROM models.model_registry
                WHERE target_id = %s AND model_name = %s AND is_active = true
                ORDER BY model_version DESC
                LIMIT 1
                """,
                (target_id, model_name),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"No active model found for {target_id} with {model_name}")

            artifact_path = ROOT / row[0]
            feature_spec = row[1]

        model = joblib.load(artifact_path)
        return model, feature_spec
    finally:
        conn.close()


def get_half_inning_state(game_id: str, inning: int, is_bottom_inning: bool) -> Dict:
    """Get the starting state of a half-inning."""
    engine = create_engine(database_url())
    try:
        sql = """
            SELECT
                game_id,
                season,
                game_date,
                inning,
                is_bottom_inning,
                batting_team_id,
                fielding_team_id,
                start_outs,
                start_bases,
                start_balls,
                start_strikes,
                start_score_diff
            FROM features.half_inning_examples
            WHERE game_id = %s AND inning = %s AND is_bottom_inning = %s
        """
        df = pd.read_sql_query(sql, engine, params=(game_id, inning, is_bottom_inning))
        if df.empty:
            raise ValueError(f"Half-inning {game_id}:{inning}:{is_bottom_inning} not found")

        return df.iloc[0].to_dict()
    finally:
        engine.dispose()


def get_lineup_for_half_inning(game_id: str, inning: int, is_bottom_inning: bool) -> List[Dict]:
    """Get the plate appearances that occurred in this half-inning for context."""
    engine = create_engine(database_url())
    try:
        sql = """
            SELECT
                plate_appearance_id,
                batter_id,
                batter_hand,
                pitcher_id,
                pitcher_hand,
                outs_before,
                balls,
                strikes,
                start_bases,
                is_hit,
                is_walk,
                is_strikeout,
                runs_on_play
            FROM core.plate_appearances
            WHERE game_id = %s AND inning = %s AND is_bottom_inning = %s
            ORDER BY half_inning_pa_number
        """
        df = pd.read_sql_query(sql, engine, params=(game_id, inning, is_bottom_inning))
        return df.to_dict("records")
    finally:
        engine.dispose()


def simulate_plate_appearance(
    pa_number: int,
    current_outs: int,
    current_bases: int,
    current_balls: int,
    current_strikes: int,
    batter_id: str,
    batter_hand: str,
    pitcher_id: str,
    pitcher_hand: str,
    inning: int,
    is_bottom_inning: bool,
    score_diff: int,
    pa_models: Dict,
) -> Dict:
    """Simulate a single plate appearance using trained models."""

    # Create feature vector for this plate appearance
    features = pd.DataFrame(
        [
            {
                "inning": inning,
                "is_bottom_inning": int(is_bottom_inning),
                "outs_before": current_outs,
                "start_bases": current_bases,
                "balls": current_balls,
                "strikes": current_strikes,
                "home_score_diff": score_diff,
                "batter_hand": batter_hand or "U",
                "pitcher_hand": pitcher_hand or "U",
            }
        ]
    )

    # Get predictions for each outcome
    predictions = {}
    for target_name, (model, feature_spec) in pa_models.items():
        numeric_features = feature_spec["numeric_features"]
        categorical_features = feature_spec["categorical_features"]
        feature_cols = numeric_features + categorical_features

        # Make prediction
        proba = model.predict_proba(features[feature_cols])[0][1]
        predictions[target_name] = proba

    # Sample outcomes based on probabilities
    import random

    random.seed(42)  # For reproducibility

    outcomes = {}
    for target_name, proba in predictions.items():
        outcomes[target_name] = random.random() < proba

    # Determine what actually happens in this simulated PA
    # Logic: if strikeout, that's the outcome
    # If walk and not strikeout, batter reaches
    # If hit and not walk/strikeout, batter reaches and possibly advances runners
    # For simplicity, we'll focus on the key outcomes

    simulated_outcome = {
        "plate_appearance": pa_number,
        "outs_before": current_outs,
        "bases_before": current_bases,
        "balls_before": current_balls,
        "strikes_before": current_strikes,
        "predictions": predictions,
        "simulated_outcomes": outcomes,
    }

    # Update game state based on simulated outcomes
    new_outs = current_outs
    new_bases = current_bases
    runs_scored = 0

    # Strikeout increases outs
    if outcomes.get("pa_batter_strikeout", False):
        new_outs = min(3, current_outs + 1)
        simulated_outcome["result"] = "strikeout"
    # Walk advances batter to first (simplified)
    elif outcomes.get("pa_batter_walk", False):
        # Simple base advancement for walk
        if current_bases == 0:
            new_bases = 1
        elif current_bases == 1:
            new_bases = 3  # Runner on first, batter to second
        elif current_bases == 2:
            new_bases = 7  # Runner on second, batter to first
        elif current_bases == 3:
            new_bases = 7  # Bases loaded, batter to first, runner from first scores
            runs_scored = 1
        elif current_bases == 4:
            new_bases = 5  # Runner on third, batter to first
        simulated_outcome["result"] = "walk"
    # Hit - simplified single for now
    elif outcomes.get("pa_batter_hit", False):
        # Simple single advancement
        runs_scored = (current_bases & 4) >> 2  # Runner on third scores
        if current_bases == 0:
            new_bases = 1
        elif current_bases == 1:
            new_bases = 1  # Runner from first to second, batter to first
        elif current_bases == 2:
            new_bases = 3  # Runner from second to third, batter to first
        elif current_bases == 3:
            new_bases = 5  # Runner from first to second, from third scores, batter to first
            runs_scored = 1
        elif current_bases == 4:
            new_bases = 5  # Runner from third scores, batter to first
            runs_scored = 1
        simulated_outcome["result"] = "hit"
    else:
        # Assume out (flyout, groundout, etc.)
        new_outs = min(3, current_outs + 1)
        simulated_outcome["result"] = "out"

    simulated_outcome.update(
        {
            "outs_after": new_outs,
            "bases_after": new_bases,
            "runs_scored": runs_scored,
        }
    )

    return simulated_outcome


def simulate_half_inning(
    game_id: str, inning: int, is_bottom_inning: bool, num_simulations: int = 100
) -> Dict:
    """Run Monte Carlo simulation of a half-inning."""

    # Get half-inning starting state
    hi_state = get_half_inning_state(game_id, inning, is_bottom_inning)

    # Load trained plate appearance models
    pa_targets = ["pa_batter_hit", "pa_batter_walk", "pa_batter_strikeout"]
    pa_models = {}
    for target in pa_targets:
        try:
            pa_models[target] = load_pa_model(target)
        except ValueError:
            print(f"Warning: Could not load model for {target}, skipping")
            continue

    # Get actual lineup for context (we'll simulate a generic lineup)
    actual_lineup = get_lineup_for_half_inning(game_id, inning, is_bottom_inning)

    # Run simulations
    simulation_results = []

    for sim_num in range(num_simulations):
        # Reset half-inning state
        current_outs = hi_state["start_outs"]
        current_bases = hi_state["start_bases"]
        current_balls = hi_state["start_balls"]
        current_strikes = hi_state["start_strikes"]
        total_runs = 0
        plate_appearances = []

        pa_number = 1
        while current_outs < 3 and pa_number <= 12:  # Safety limit
            # Simulate plate appearance (using generic batter/pitcher for now)
            pa_result = simulate_plate_appearance(
                pa_number=pa_number,
                current_outs=current_outs,
                current_bases=current_bases,
                current_balls=current_balls,
                current_strikes=current_strikes,
                batter_id="generic",  # Would need real lineup data
                batter_hand="R",  # Default to right-handed
                pitcher_id="generic",
                pitcher_hand="R",
                inning=inning,
                is_bottom_inning=is_bottom_inning,
                score_diff=hi_state["start_score_diff"],
                pa_models=pa_models,
            )

            plate_appearances.append(pa_result)

            # Update state
            current_outs = pa_result["outs_after"]
            current_bases = pa_result["bases_after"]
            total_runs += pa_result["runs_scored"]
            current_balls = 0  # Reset count
            current_strikes = 0

            pa_number += 1

        simulation_results.append(
            {
                "simulation": sim_num,
                "total_runs": total_runs,
                "any_run": total_runs > 0,
                "plate_appearances": len(plate_appearances),
                "outs_recorded": current_outs,
            }
        )

    # Aggregate results
    runs_distribution = [r["total_runs"] for r in simulation_results]
    any_run_prob = sum(1 for r in simulation_results if r["any_run"]) / num_simulations

    # Convert date to string for JSON serialization
    hi_state_copy = hi_state.copy()
    if "game_date" in hi_state_copy:
        hi_state_copy["game_date"] = str(hi_state_copy["game_date"])

    return {
        "game_id": game_id,
        "inning": inning,
        "is_bottom_inning": is_bottom_inning,
        "half_inning_state": hi_state_copy,
        "num_simulations": num_simulations,
        "results": {
            "any_run_probability": any_run_prob,
            "average_runs": sum(runs_distribution) / len(runs_distribution),
            "runs_distribution": {
                "0": runs_distribution.count(0),
                "1": runs_distribution.count(1),
                "2": runs_distribution.count(2),
                "3+": sum(1 for r in runs_distribution if r >= 3),
            },
        },
        "sample_simulation": simulation_results[0] if simulation_results else None,
    }


def main():
    parser = argparse.ArgumentParser(description="Run Monte Carlo half-inning simulation")
    parser.add_argument("--game-id", required=True, help="Game ID")
    parser.add_argument("--inning", type=int, required=True, help="Inning number")
    parser.add_argument("--is-bottom", action="store_true", help="Bottom half of inning")
    parser.add_argument("--simulations", type=int, default=100, help="Number of simulations to run")

    args = parser.parse_args()

    try:
        result = simulate_half_inning(args.game_id, args.inning, args.is_bottom, args.simulations)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
