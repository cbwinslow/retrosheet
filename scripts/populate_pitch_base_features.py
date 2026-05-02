#!/usr/bin/env python3
"""
Populate Pitch-Level Base Features Table

Migrates 7.66M pitches from features_pitch.locations to features_pitch.base_features
with versioning support for reproducible model training.

Usage:
    python scripts/populate_pitch_base_features.py --all
    python scripts/populate_pitch_base_features.py --seasons 2020 2021 2022
    python scripts/populate_pitch_base_features.py --incremental
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from baseball.core.db import get_db_connection
from baseball.utils.logging_config import get_logger

logger = get_logger(__name__)


def get_locations_count(seasons: Optional[list[int]] = None) -> int:
    """Get count of pitches available in locations table."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    if seasons:
        cur.execute("""
            SELECT COUNT(*) 
            FROM features_pitch.locations 
            WHERE game_year = ANY(%s)
        """, (seasons,))
    else:
        cur.execute("SELECT COUNT(*) FROM features_pitch.locations")
    
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count


def get_base_features_count() -> int:
    """Get current count in base_features table."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM features_pitch.base_features")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count


def populate_base_features(
    seasons: Optional[list[int]] = None,
    batch_size: int = 100000,
    dry_run: bool = False
) -> dict:
    """
    Populate base_features table from locations.
    
    Args:
        seasons: List of seasons to migrate (None = all)
        batch_size: Rows per batch
        dry_run: If True, don't actually insert
        
    Returns:
        Dict with migration stats
    """
    start_time = datetime.now()
    version_tag = f"v1.0_{start_time.strftime('%Y%m%d')}"
    
    # Get source count
    source_count = get_locations_count(seasons)
    logger.info(f"Source pitches to migrate: {source_count:,}")
    
    if dry_run:
        logger.info("DRY RUN - no inserts will occur")
        return {'status': 'dry_run', 'source_count': source_count}
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Build query
    season_filter = "WHERE game_year = ANY(%s)" if seasons else ""
    params = (seasons,) if seasons else ()
    
    # Insert in batches
    total_inserted = 0
    batch_num = 0
    
    while True:
        batch_start = datetime.now()
        
        query = f"""
            INSERT INTO features_pitch.base_features (
                pitch_id, game_pk, game_year, game_date,
                pitcher_id, batter_id,
                pitch_type, pitch_name, release_speed,
                release_pos_x, release_pos_y, release_pos_z,
                pfx_x, pfx_z, plate_x, plate_z, plate_z_adj,
                vx0, vy0, vz0, ax, ay, az,
                effective_speed, release_spin_rate, spin_axis,
                zone, balls, strikes,
                p_throws, stand,
                type, description, events,
                bb_type, hit_location, hc_x, hc_y,
                hit_distance_sc, launch_speed, launch_angle,
                estimated_ba_using_speedangle, estimated_woba_using_speedangle,
                woba_value, woba_denom, babip_value, iso_value,
                at_bat_number, pitch_number, pitch_name_seq,
                home_score, away_score, bat_score, fld_score,
                post_bat_score, post_fld_score,
                if_fielding_alignment, of_fielding_alignment,
                barrel, outs_when_up, inning, inning_topbot,
                game_type, home_team, away_team,
                balls_pre, strikes_pre, count_label,
                version_tag, created_at
            )
            SELECT 
                pitch_id, game_pk, game_year, game_date,
                pitcher_id, batter_id,
                pitch_type, pitch_name, release_speed,
                release_pos_x, release_pos_y, release_pos_z,
                pfx_x, pfx_z, plate_x, plate_z, plate_z_adj,
                vx0, vy0, vz0, ax, ay, az,
                effective_speed, release_spin_rate, spin_axis,
                zone, balls, strikes,
                p_throws, stand,
                type, description, events,
                bb_type, hit_location, hc_x, hc_y,
                hit_distance_sc, launch_speed, launch_angle,
                estimated_ba_using_speedangle, estimated_woba_using_speedangle,
                woba_value, woba_denom, babip_value, iso_value,
                at_bat_number, pitch_number, pitch_name_seq,
                home_score, away_score, bat_score, fld_score,
                post_bat_score, post_fld_score,
                if_fielding_alignment, of_fielding_alignment,
                barrel, outs_when_up, inning, inning_topbot,
                game_type, home_team, away_team,
                balls_pre, strikes_pre, 
                CASE 
                    WHEN balls_pre IS NOT NULL AND strikes_pre IS NOT NULL 
                    THEN balls_pre || '-' || strikes_pre 
                    ELSE NULL 
                END as count_label,
                %s as version_tag,
                NOW() as created_at
            FROM features_pitch.locations
            {season_filter}
            ORDER BY game_pk, pitch_number
            LIMIT %s
            ON CONFLICT (pitch_id, version_tag) DO NOTHING
            RETURNING pitch_id
        """
        
        cur.execute(query, (*params, version_tag, batch_size))
        
        inserted = cur.rowcount
        total_inserted += inserted
        batch_num += 1
        
        conn.commit()
        
        elapsed = (datetime.now() - batch_start).total_seconds()
        logger.info(
            f"Batch {batch_num}: Inserted {inserted:,} rows "
            f"({total_inserted:,} total) in {elapsed:.1f}s"
        )
        
        if inserted < batch_size:
            break
    
    cur.close()
    conn.close()
    
    total_time = (datetime.now() - start_time).total_seconds()
    
    stats = {
        'status': 'complete',
        'source_count': source_count,
        'inserted': total_inserted,
        'version_tag': version_tag,
        'batches': batch_num,
        'time_seconds': total_time,
        'rows_per_second': total_inserted / total_time if total_time > 0 else 0
    }
    
    logger.info(f"Migration complete: {total_inserted:,} rows in {total_time:.1f}s")
    
    return stats


def verify_migration(version_tag: str) -> dict:
    """Verify migrated data integrity."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Row count
    cur.execute(
        "SELECT COUNT(*) FROM features_pitch.base_features WHERE version_tag = %s",
        (version_tag,)
    )
    row_count = cur.fetchone()[0]
    
    # Season distribution
    cur.execute("""
        SELECT game_year, COUNT(*) 
        FROM features_pitch.base_features 
        WHERE version_tag = %s
        GROUP BY game_year 
        ORDER BY game_year
    """, (version_tag,))
    seasons = {row[0]: row[1] for row in cur.fetchall()}
    
    # Null check on critical fields
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE pitch_type IS NULL) as null_pitch_type,
            COUNT(*) FILTER (WHERE release_speed IS NULL) as null_speed,
            COUNT(*) FILTER (WHERE plate_x IS NULL) as null_location
        FROM features_pitch.base_features 
        WHERE version_tag = %s
    """, (version_tag,))
    nulls = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return {
        'row_count': row_count,
        'seasons': seasons,
        'null_pitch_type': nulls[0],
        'null_speed': nulls[1],
        'null_location': nulls[2]
    }


def main():
    parser = argparse.ArgumentParser(
        description='Populate pitch-level base features from locations'
    )
    parser.add_argument(
        '--seasons', '-s',
        nargs='+',
        type=int,
        help='Specific seasons to migrate (default: all)'
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Migrate all seasons'
    )
    parser.add_argument(
        '--incremental', '-i',
        action='store_true',
        help='Only migrate new pitches not in base_features'
    )
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=100000,
        help='Rows per batch (default: 100000)'
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Show what would be migrated without inserting'
    )
    parser.add_argument(
        '--verify', '-v',
        metavar='VERSION_TAG',
        help='Verify existing migration by version tag'
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.verify:
        stats = verify_migration(args.verify)
        print(f"\nVerification for {args.verify}:")
        print(f"  Total rows: {stats['row_count']:,}")
        print(f"  Seasons: {len(stats['seasons'])}")
        for year, count in sorted(stats['seasons'].items()):
            print(f"    {year}: {count:,}")
        print(f"\n  Data quality:")
        print(f"    Null pitch_type: {stats['null_pitch_type']:,}")
        print(f"    Null speed: {stats['null_speed']:,}")
        print(f"    Null location: {stats['null_location']:,}")
        return
    
    # Determine seasons
    seasons = None
    if args.seasons:
        seasons = args.seasons
    elif not args.all and not args.incremental:
        # Show current state
        loc_count = get_locations_count()
        base_count = get_base_features_count()
        print(f"\nSource (locations): {loc_count:,} pitches")
        print(f"Target (base_features): {base_count:,} pitches")
        print(f"\nUse --all to migrate all, --seasons to migrate specific seasons")
        return
    
    # Run migration
    stats = populate_base_features(
        seasons=seasons,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )
    
    if not args.dry_run:
        print(f"\nMigration complete:")
        print(f"  Version: {stats['version_tag']}")
        print(f"  Inserted: {stats['inserted']:,} / {stats['source_count']:,}")
        print(f"  Batches: {stats['batches']}")
        print(f"  Time: {stats['time_seconds']:.1f}s")
        print(f"  Rate: {stats['rows_per_second']:,.0f} rows/sec")
        
        # Auto-verify
        verify_stats = verify_migration(stats['version_tag'])
        print(f"\n  Verification:")
        print(f"    Row count: {verify_stats['row_count']:,}")
        print(f"    Seasons: {len(verify_stats['seasons'])}")


if __name__ == '__main__':
    main()
