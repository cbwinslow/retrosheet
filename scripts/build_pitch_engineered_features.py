#!/usr/bin/env python3
"""
Build Pitch-Level Engineered Features

Creates derived metrics and hierarchical targets for the Two-Tier XGBoost model.

Targets:
  - outcome_tier1: Ball / Strike / Ball-in-Play (coarse)
  - outcome_tier2: Single/Double/Triple/HR/Out/Walk/K (fine, when BiP)

Derived Features:
  - Physics: break magnitude, approach angle, spin efficiency
  - Context: score differential, leverage index, inning factor
  - Player: pitcher arsenal, batter zone discipline (joined)

Usage:
    python scripts/build_pitch_engineered_features.py --version v1.0_20260502
    python scripts/build_pitch_engineered_features.py --all-versions
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from baseball.core.db import get_db_connection
from baseball.utils.logging_config import get_logger

logger = get_logger(__name__)


def calculate_break_magnitude(pfx_x: float, pfx_z: float) -> float:
    """Calculate total break magnitude from movement components."""
    return np.sqrt(pfx_x**2 + pfx_z**2)


def calculate_approach_angle(vx: float, vy: float, vz: float) -> float:
    """Calculate pitch approach angle (degrees above horizontal)."""
    velocity = np.sqrt(vx**2 + vy**2 + vz**2)
    if velocity == 0:
        return 0.0
    return np.degrees(np.arcsin(vz / velocity))


def get_outcome_tier1(description: str, pitch_type: str) -> str:
    """
    Map pitch description to tier-1 outcome.
    
    Returns: 'Ball' | 'Strike' | 'BallInPlay' | 'Other'
    """
    if not description:
        return 'Other'
    
    desc = description.lower()
    
    # Balls
    if any(kw in desc for kw in ['ball', 'intent ball', 'pitchout']):
        return 'Ball'
    
    # Strikes (swinging, called, foul)
    if any(kw in desc for kw in ['strike', 'foul', 'foul tip']):
        return 'Strike'
    
    # Ball in play
    if any(kw in desc for kw in ['in play', 'hit', 'single', 'double', 
                                  'triple', 'home run', 'field', 'ground',
                                  'line', 'fly', 'pop']):
        return 'BallInPlay'
    
    return 'Other'


def get_outcome_tier2(events: Optional[str], description: str, bb_type: Optional[str]) -> Optional[str]:
    """
    Map events/description to tier-2 outcome (only for BallInPlay or terminal outcomes).
    
    Returns: Single | Double | Triple | HR | Out | Walk | K | None
    """
    if not events and not description:
        return None
    
    evt = (events or '').lower()
    desc = (description or '').lower()
    
    # Walks
    if any(kw in evt for kw in ['walk', 'intent walk']) or \
       any(kw in desc for kw in ['intent walk', 'walk.']):
        return 'Walk'
    
    # Strikeouts
    if 'strikeout' in evt:
        return 'K'
    
    # Hits
    if 'single' in evt:
        return 'Single'
    if 'double' in evt:
        return 'Double'
    if 'triple' in evt:
        return 'Triple'
    if 'home run' in evt or 'homer' in evt:
        return 'HR'
    
    # Outs (for ball-in-play)
    if bb_type or any(kw in evt for kw in ['field out', 'force out', 'grounded into double play']):
        return 'Out'
    
    return None


def calculate_leverage_index(
    inning: int, outs: int, score_diff: float, is_top: bool
) -> float:
    """
    Approximate leverage index based on game situation.
    
    Simplified formula based on inning, outs, and score differential.
    Returns value ~1.0 (average), higher = more leverage.
    """
    base_leverage = 1.0
    
    # Inning factor (later innings = more leverage)
    inning_factor = 1.0 + (inning - 1) * 0.02
    
    # Out factor (fewer outs = more leverage)
    out_factor = 1.0 + (2 - outs) * 0.15
    
    # Score differential factor (closer games = more leverage)
    close_game_boost = max(0, 1.0 - abs(score_diff) / 4) * 0.5
    
    return base_leverage * inning_factor * out_factor + close_game_boost


def build_engineered_features(version_tag: str, batch_size: int = 50000) -> dict:
    """
    Build engineered features for a specific version of base_features.
    
    Args:
        version_tag: Version of base_features to process
        batch_size: Rows per batch
        
    Returns:
        Dict with build stats
    """
    start_time = datetime.now()
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get total count
    cur.execute(
        "SELECT COUNT(*) FROM features_pitch.base_features WHERE version_tag = %s",
        (version_tag,)
    )
    total_rows = cur.fetchone()[0]
    logger.info(f"Processing {total_rows:,} rows for version {version_tag}")
    
    if total_rows == 0:
        logger.error(f"No rows found for version {version_tag}")
        return {'status': 'error', 'reason': 'no_rows'}
    
    # Process in batches using a cursor
    cur.execute("""
        SELECT 
            pitch_id, release_speed, pfx_x, pfx_z,
            vx0, vy0, vz0, plate_x, plate_z,
            description, events, bb_type,
            home_score, away_score, bat_score, fld_score,
            inning, outs_when_up, inning_topbot,
            balls, strikes, count_label
        FROM features_pitch.base_features
        WHERE version_tag = %s
        ORDER BY pitch_id
    """, (version_tag,))
    
    processed = 0
    inserted = 0
    errors = 0
    
    batch_data = []
    
    for row in cur:
        try:
            (
                pitch_id, release_speed, pfx_x, pfx_z,
                vx0, vy0, vz0, plate_x, plate_z,
                description, events, bb_type,
                home_score, away_score, bat_score, fld_score,
                inning, outs, inning_topbot,
                balls, strikes, count_label
            ) = row
            
            # Calculate derived physics features
            break_mag = calculate_break_magnitude(pfx_x or 0, pfx_z or 0)
            approach = calculate_approach_angle(vx0 or 0, vy0 or 0, vz0 or 0)
            
            # Determine outcomes
            tier1 = get_outcome_tier1(description or '', '')
            tier2 = get_outcome_tier2(events, description or '', bb_type)
            
            # Context features
            score_diff = (bat_score or 0) - (fld_score or 0)
            is_top = inning_topbot == 'Top'
            leverage = calculate_leverage_index(
                inning or 1, outs or 0, score_diff, is_top
            )
            
            # Plate distance from center
            plate_dist = np.sqrt((plate_x or 0)**2 + (plate_z or 0)**2)
            
            batch_data.append((
                pitch_id, version_tag,
                tier1, tier2,
                break_mag, approach,
                leverage, score_diff,
                plate_dist,
                't1_v1.0', datetime.now()
            ))
            
            # Insert batch
            if len(batch_data) >= batch_size:
                insert_batch(conn, batch_data)
                inserted += len(batch_data)
                batch_data = []
                
                processed += batch_size
                if processed % 500000 == 0:
                    logger.info(f"Processed {processed:,} / {total_rows:,}")
        
        except Exception as e:
            errors += 1
            if errors <= 5:
                logger.warning(f"Error processing row {pitch_id}: {e}")
    
    # Insert remaining
    if batch_data:
        insert_batch(conn, batch_data)
        inserted += len(batch_data)
    
    cur.close()
    conn.close()
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    return {
        'status': 'complete',
        'version_tag': version_tag,
        'processed': processed,
        'inserted': inserted,
        'errors': errors,
        'time_seconds': elapsed,
        'rows_per_second': processed / elapsed if elapsed > 0 else 0
    }


def insert_batch(conn, batch_data):
    """Insert a batch of engineered features."""
    cur = conn.cursor()
    
    cur.executemany("""
        INSERT INTO features_pitch.engineered_features (
            pitch_id, version_tag,
            outcome_tier1, outcome_tier2,
            break_magnitude, approach_angle,
            leverage_index, score_diff,
            plate_distance_from_center,
            feature_version, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (pitch_id, feature_version) DO UPDATE SET
            outcome_tier1 = EXCLUDED.outcome_tier1,
            outcome_tier2 = EXCLUDED.outcome_tier2,
            break_magnitude = EXCLUDED.break_magnitude,
            approach_angle = EXCLUDED.approach_angle,
            leverage_index = EXCLUDED.leverage_index,
            score_diff = EXCLUDED.score_diff,
            plate_distance_from_center = EXCLUDED.plate_distance_from_center,
            updated_at = NOW()
    """, batch_data)
    
    conn.commit()
    cur.close()


def main():
    parser = argparse.ArgumentParser(
        description='Build engineered features for pitch-level models'
    )
    parser.add_argument(
        '--version', '-v',
        required=True,
        help='Version tag of base_features to process'
    )
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=50000,
        help='Rows per batch (default: 50000)'
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    stats = build_engineered_features(args.version, args.batch_size)
    
    print(f"\nEngineered features built:")
    print(f"  Version: {stats['version_tag']}")
    print(f"  Processed: {stats['processed']:,}")
    print(f"  Inserted: {stats['inserted']:,}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Time: {stats['time_seconds']:.1f}s")
    print(f"  Rate: {stats['rows_per_second']:,.0f} rows/sec")


if __name__ == '__main__':
    main()
