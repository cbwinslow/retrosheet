#!/usr/bin/env python3
"""
Evaluate Model Calibration

Loads a trained model and evaluates calibration metrics on validation data.

Usage:
    python scripts/evaluate_model_calibration.py --model models/pitch_level/tier1_v1.0.pkl
    python scripts/evaluate_model_calibration.py --model tier1 --val-seasons 2024-2025
"""

import argparse
import glob
import pickle
import sys
from pathlib import Path
from typing import Optional

import numpy as np
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent))

from baseball.core.db import get_db_connection
from baseball.models.calibration import calibrate_model, CalibrationMetrics
from baseball.utils.logging_config import get_logger

logger = get_logger(__name__)
console = Console()


def load_model(model_path: str):
    """Load model artifact."""
    # Find model file
    if model_path in ['tier1', 'tier2']:
        files = glob.glob(f'models/pitch_level/{model_path}_*.pkl')
        if not files:
            raise FileNotFoundError(f"No {model_path} models found")
        model_path = sorted(files)[-1]  # Latest
    
    with open(model_path, 'rb') as f:
        artifact = pickle.load(f)
    
    return artifact['model'], artifact['metadata']


def fetch_validation_data(
    val_seasons: list[int],
    version_tag: str,
    limit: Optional[int] = None
) -> tuple:
    """Fetch validation data from database."""
    logger.info(f"Fetching validation data: seasons {val_seasons}")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    feature_cols = [
        'release_speed', 'release_pos_x', 'release_pos_y', 'release_pos_z',
        'pfx_x', 'pfx_z', 'plate_x', 'plate_z',
        'effective_speed', 'release_spin_rate', 'spin_axis',
        'balls', 'strikes',
        'break_magnitude', 'approach_angle',
        'leverage_index', 'score_diff',
        'plate_distance_from_center',
        'inning', 'outs_when_up'
    ]
    
    features_sql = ', '.join([f"COALESCE(bf.{col}, 0)" for col in feature_cols])
    
    limit_sql = f"LIMIT {limit}" if limit else ""
    
    cur.execute(f"""
        SELECT 
            {features_sql},
            ef.outcome_tier1,
            ef.outcome_tier2
        FROM features_pitch.base_features bf
        JOIN features_pitch.engineered_features ef
            ON bf.pitch_id = ef.pitch_id
            AND bf.version_tag = ef.version_tag
        WHERE bf.game_year = ANY(%s)
        AND bf.version_tag = %s
        AND ef.outcome_tier1 IS NOT NULL
        {limit_sql}
    """, (val_seasons, version_tag))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    n_features = len(feature_cols)
    X = np.array([row[:n_features] for row in rows])
    y_tier1 = np.array([row[n_features] for row in rows])
    y_tier2 = np.array([row[n_features + 1] for row in rows])
    
    return X, y_tier1, y_tier2


def evaluate_tier1_calibration(model, X_val, y_val, class_names: list) -> CalibrationMetrics:
    """Evaluate calibration for tier-1 model."""
    # Get predictions
    y_pred_proba = model.predict_proba(X_val)
    
    # Encode labels
    class_map = {name: i for i, name in enumerate(class_names)}
    y_val_enc = np.array([class_map.get(label, -1) for label in y_val])
    
    # Filter valid
    mask = y_val_enc >= 0
    X_val_f = X_val[mask]
    y_val_enc = y_val_enc[mask]
    y_pred_proba = y_pred_proba[mask]
    
    # Calculate calibration
    metrics = calibrate_model(
        y_val_enc,
        y_pred_proba,
        n_classes=len(class_names),
        apply_scaling=True
    )
    
    return metrics


def display_reliability_diagram(reliability_data: list):
    """Display reliability diagram as table."""
    table = Table(title="Reliability Diagram")
    table.add_column("Confidence Range", style="cyan")
    table.add_column("Samples", style="blue", justify="right")
    table.add_column("Avg Confidence", style="yellow", justify="right")
    table.add_column("Accuracy", style="green", justify="right")
    table.add_column("Gap", style="red", justify="right")
    
    for bin_data in reliability_data:
        gap = bin_data['gap']
        gap_str = f"{gap:+.3f}"
        gap_style = "red" if abs(gap) > 0.1 else "yellow" if abs(gap) > 0.05 else "green"
        
        table.add_row(
            f"[{bin_data['bin_lower']:.2f}, {bin_data['bin_upper']:.2f}]",
            f"{bin_data['count']:,}",
            f"{bin_data['confidence']:.3f}",
            f"{bin_data['accuracy']:.3f}",
            f"[{gap_style}]{gap_str}[/]"
        )
    
    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate model calibration'
    )
    parser.add_argument(
        '--model', '-m',
        required=True,
        help='Model path or "tier1"/"tier2" for latest'
    )
    parser.add_argument(
        '--val-seasons', '-v',
        default='2024-2025',
        help='Validation season range'
    )
    parser.add_argument(
        '--version-tag', '-g',
        default='v1.0',
        help='Version tag for features'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Limit validation samples (for testing)'
    )
    
    args = parser.parse_args()
    
    # Load model
    console.print(f"[dim]Loading model: {args.model}[/dim]")
    model, metadata = load_model(args.model)
    
    classes = metadata.get('classes', [])
    tier = metadata.get('tier', 1)
    
    console.print(f"[green]✓ Model loaded: Tier-{tier}[/green]")
    console.print(f"  Classes: {', '.join(classes)}")
    console.print(f"  Features: {len(metadata.get('features', []))}")
    
    # Parse seasons
    start, end = args.val_seasons.split('-')
    val_seasons = list(range(int(start), int(end) + 1))
    
    # Fetch data
    X_val, y_tier1, y_tier2 = fetch_validation_data(
        val_seasons, args.version_tag, args.limit
    )
    
    console.print(f"[dim]Validation samples: {len(X_val):,}[/dim]")
    
    # Evaluate
    if tier == 1:
        y_val = y_tier1
    else:
        # For tier 2, only use Ball-in-Play samples
        bip_mask = y_tier1 == 'BallInPlay'
        X_val = X_val[bip_mask]
        y_val = y_tier2[bip_mask]
        console.print(f"[dim]Ball-in-Play samples: {len(X_val):,}[/dim]")
    
    metrics = evaluate_tier1_calibration(model, X_val, y_val, classes)
    
    # Display results
    console.print(f"\n[bold]Calibration Metrics[/bold]")
    console.print(f"  ECE: {metrics.ece:.4f} ({metrics.ece*100:.2f}%)")
    console.print(f"  Brier Score: {metrics.brier_score:.4f}")
    console.print(f"  Temperature: {metrics.temperature:.3f}")
    
    # Threshold check
    well_calibrated = metrics.ece < 0.05 and metrics.brier_score < 0.2
    status = "✓ Well calibrated" if well_calibrated else "⚠ Needs improvement"
    color = "green" if well_calibrated else "yellow"
    console.print(f"\n[{color}]{status}[/{color}]")
    
    # Reliability diagram
    console.print(f"\n[bold]Reliability Diagram[/bold]")
    display_reliability_diagram(metrics.reliability_diagram)
    
    # Recommendations
    console.print(f"\n[bold]Recommendations:[/bold]")
    if metrics.ece > 0.05:
        console.print("  • High ECE - apply temperature scaling at inference")
        console.print(f"    Use temperature T={metrics.temperature:.3f}")
    if metrics.brier_score > 0.2:
        console.print("  • High Brier - consider ensemble or model retraining")
    if not well_calibrated:
        console.print("  • Consider Platt scaling or isotonic regression")
    else:
        console.print("  • Model is production-ready for calibrated predictions")


if __name__ == '__main__':
    main()
