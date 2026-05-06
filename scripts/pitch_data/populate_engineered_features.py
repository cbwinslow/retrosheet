#!/usr/bin/env python3
"""
Populate Engineered Features for Pitch-Level Modeling

Creates derived features from base_features including:
- Velocity categorization and percentiles
- Zone classification and distance metrics
- Outcome binaries for classification targets
- Derived physics metrics (break, approach angle, spin efficiency)
- Sequence context within plate appearances
- Game context and matchup history

Usage:
    python populate_engineered_features.py --all
    python populate_engineered_features.py --seasons 2020 2021 2022
    python populate_engineered_features.py --batch-size 50000
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from baseball.core.db import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_base_features_count(conn, seasons: Optional[list[int]] = None) -> int:
    """Get count of pitches available in base_features table."""
    cur = conn.cursor()
    
    if seasons:
        cur.execute("""
            SELECT COUNT(*) 
            FROM features_pitch.base_features 
            WHERE game_year = ANY(%s)
        """, (seasons,))
    else:
        cur.execute("SELECT COUNT(*) FROM features_pitch.base_features")
    
    count = cur.fetchone()[0]
    cur.close()
    return count


def get_engineered_features_count() -> int:
    """Get current count in engineered_features table."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM features_pitch.engineered_features")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count


def populate_engineered_features(
    conn,
    seasons: Optional[list[int]] = None,
    batch_size: int = 100000,
    dry_run: bool = False,
) -> dict:
    """
    Populate engineered_features table from base_features.
    
    Args:
        conn: Database connection
        seasons: List of seasons to process (None = all)
        batch_size: Rows per batch
        dry_run: If True, don't actually insert
        
    Returns:
        Dict with processing stats
    """
    start_time = datetime.now()
    version_tag = f"v1.0_{start_time.strftime('%Y%m%d')}"
    
    # Get source count
    source_count = get_base_features_count(conn, seasons)
    logger.info(f"Source pitches to process: {source_count:,}")
    
    if dry_run:
        logger.info("DRY RUN - no inserts will occur")
        return {'status': 'dry_run', 'source_count': source_count}
    
    cur = conn.cursor()
    
    # Build season filter
    season_filter = "WHERE bf.game_year = ANY(%s)" if seasons else ""
    params = (seasons,) if seasons else ()
    
    # Process in batches
    total_processed = 0
    batch_num = 0
    
    while True:
        batch_start = datetime.now()
        
        # Main engineered features query
        query = f"""
            INSERT INTO features_pitch.engineered_features (
                pitch_id,
                
                -- Velocity categorization
                velocity_category,
                velocity_percentile,
                velocity_diff_from_avg,
                
                -- Zone classification
                zone_region,
                is_in_zone,
                is_in_shadow_zone,
                is_in_chase_zone,
                distance_from_zone_center,
                
                -- Outcome binaries
                is_strike,
                is_swing,
                is_whiff,
                is_called_strike,
                is_foul,
                is_foul_tip,
                is_ball_in_play,
                is_hit,
                is_single,
                is_double,
                is_triple,
                is_home_run,
                is_xbh,
                is_out,
                is_ground_ball,
                is_fly_ball,
                is_line_drive,
                is_popup,
                is_hard_hit,
                is_barrel,
                
                -- Tier 1 & 2 outcomes
                outcome_tier1,
                outcome_tier2,
                swing_decision,
                
                -- Derived physics
                horizontal_break,
                vertical_break,
                approach_angle,
                spin_efficiency,
                induced_vertical_break,
                horizontal_release_deviation,
                release_velocity_diff,
                
                -- Sequence context
                pa_pitch_count,
                prev_pitch_type,
                prev_pitch_result,
                prev_plate_x,
                prev_plate_z,
                prev_velocity,
                prev_break_x,
                prev_break_z,
                prev_was_strike,
                prev_was_ball,
                prev_was_swing,
                count_started_this_pa,
                is_full_count,
                is_two_strike,
                is_three_ball,
                
                -- Game context
                score_diff,
                score_diff_bucket,
                is_late_game,
                is_high_leverage,
                base_state_code,
                base_state_name,
                count_code,
                
                -- Metadata
                engineered_at,
                engineer_version,
                source_calculations
            )
            SELECT 
                bf.pitch_id,
                
                -- Velocity categorization
                CASE 
                    WHEN bf.release_speed < 80 THEN 'slow'
                    WHEN bf.release_speed < 90 THEN 'medium'
                    WHEN bf.release_speed < 95 THEN 'fast'
                    ELSE 'elite'
                END as velocity_category,
                
                -- Velocity percentile (simplified - would need window function for true percentile)
                CASE 
                    WHEN bf.release_speed < 85 THEN 25.0
                    WHEN bf.release_speed < 90 THEN 50.0
                    WHEN bf.release_speed < 95 THEN 75.0
                    ELSE 90.0
                END as velocity_percentile,
                
                bf.release_speed - 92.0 as velocity_diff_from_avg, -- Assuming 92 mph avg
                
                -- Zone classification
                CASE 
                    WHEN bf.zone IN (1, 2, 3) THEN 'heart'
                    WHEN bf.zone IN (4, 5, 6, 7, 8, 9) THEN 'shadow'
                    WHEN bf.zone IN (11, 12, 13, 14) THEN 'chase'
                    ELSE 'waste'
                END as zone_region,
                
                bf.zone BETWEEN 1 AND 9 as is_in_zone,
                bf.zone IN (4, 5, 6, 7, 8, 9) as is_in_shadow_zone,
                bf.zone IN (11, 12, 13, 14) as is_in_chase_zone,
                
                -- Distance from zone center (simplified)
                SQRT(POWER(bf.plate_x, 2) + POWER(bf.plate_z - 2.5, 2)) as distance_from_zone_center,
                
                -- Outcome binaries
                bf.type = 'S' as is_strike,
                bf.description IN ('swinging_strike', 'swinging_strike_blocked', 'foul_tip', 'foul_bunt_tip') as is_swing,
                bf.description IN ('swinging_strike', 'swinging_strike_blocked') as is_whiff,
                bf.description IN ('called_strike') as is_called_strike,
                bf.description LIKE '%foul%' as is_foul,
                bf.description = 'foul_tip' as is_foul_tip,
                bf.type = 'X' as is_ball_in_play,
                bf.events IN ('single', 'double', 'triple', 'home_run') as is_hit,
                bf.events = 'single' as is_single,
                bf.events = 'double' as is_double,
                bf.events = 'triple' as is_triple,
                bf.events = 'home_run' as is_home_run,
                bf.events IN ('double', 'triple', 'home_run') as is_xbh,
                bf.type = 'X' AND bf.events NOT IN ('single', 'double', 'triple', 'home_run') as is_out,
                bf.bb_type = 'ground_ball' as is_ground_ball,
                bf.bb_type = 'fly_ball' as is_fly_ball,
                bf.bb_type = 'line_drive' as is_line_drive,
                bf.bb_type = 'popup' as is_popup,
                bf.launch_speed >= 95 as is_hard_hit,
                bf.barrel = 1 as is_barrel,
                
                -- Tier 1 & 2 outcomes
                CASE 
                    WHEN bf.type = 'B' THEN 'ball'
                    WHEN bf.type = 'S' AND bf.description NOT LIKE '%foul%' THEN 'strike'
                    WHEN bf.type = 'X' THEN 'ball_in_play'
                    ELSE 'other'
                END as outcome_tier1,
                
                CASE 
                    WHEN bf.events = 'single' THEN 'single'
                    WHEN bf.events = 'double' THEN 'double'
                    WHEN bf.events = 'triple' THEN 'triple'
                    WHEN bf.events = 'home_run' THEN 'home_run'
                    WHEN bf.type = 'X' AND bf.events NOT IN ('single', 'double', 'triple', 'home_run') THEN 'out'
                    ELSE NULL
                END as outcome_tier2,
                
                CASE 
                    WHEN bf.description IN ('swinging_strike', 'swinging_strike_blocked', 'foul_tip', 'foul_bunt_tip', 'hit_into_play', 'hit_into_play_score', 'hit_into_play_no_score') THEN 'swing'
                    WHEN bf.description IN ('called_strike', 'ball', 'blocked_ball') THEN 'take'
                    ELSE NULL
                END as swing_decision,
                
                -- Derived physics
                bf.pfx_x as horizontal_break,
                bf.pfx_z as vertical_break,
                -- Simplified approach angle calculation
                ATAN2(bf.release_pos_z - 5.5, 17.4 - bf.release_pos_y) * 180 / PI() as approach_angle,
                
                -- Spin efficiency (simplified)
                CASE 
                    WHEN bf.release_spin_rate > 0 THEN 
                        (SQRT(POWER(bf.pfx_x, 2) + POWER(bf.pfx_z, 2)) / bf.release_spin_rate) * 100
                    ELSE NULL
                END as spin_efficiency,
                
                bf.pfx_z as induced_vertical_break,
                -- Horizontal release deviation (simplified)
                bf.release_pos_x as horizontal_release_deviation,
                bf.release_speed - 92.0 as release_velocity_diff,
                
                -- Sequence context (simplified - would need window functions for full context)
                bf.pitch_number as pa_pitch_count,
                NULL as prev_pitch_type,  -- Would need LAG() window function
                NULL as prev_pitch_result,
                NULL as prev_plate_x,
                NULL as prev_plate_z,
                NULL as prev_velocity,
                NULL as prev_break_x,
                NULL as prev_break_z,
                NULL as prev_was_strike,
                NULL as prev_was_ball,
                NULL as prev_was_swing,
                bf.pitch_number = 1 as count_started_this_pa,
                bf.balls = 3 AND bf.strikes = 2 as is_full_count,
                bf.strikes = 2 as is_two_strike,
                bf.balls = 3 as is_three_ball,
                
                -- Game context
                bf.bat_score - bf.fld_score as score_diff,
                CASE 
                    WHEN ABS(bf.bat_score - bf.fld_score) >= 5 THEN 'blowout'
                    WHEN ABS(bf.bat_score - bf.fld_score) >= 3 THEN 'moderate'
                    ELSE 'close'
                END as score_diff_bucket,
                bf.inning > 7 as is_late_game,
                ABS(bf.delta_home_win_exp) > 0.05 as is_high_leverage,
                
                -- Base state encoding
                (CASE WHEN bf.on_1b THEN 1 ELSE 0 END) + 
                (CASE WHEN bf.on_2b THEN 2 ELSE 0 END) + 
                (CASE WHEN bf.on_3b THEN 4 ELSE 0 END) as base_state_code,
                
                CASE 
                    WHEN NOT bf.on_1b AND NOT bf.on_2b AND NOT bf.on_3b THEN 'bases_empty'
                    WHEN bf.on_1b AND NOT bf.on_2b AND NOT bf.on_3b THEN 'runner_1b'
                    WHEN NOT bf.on_1b AND bf.on_2b AND NOT bf.on_3b THEN 'runner_2b'
                    WHEN NOT bf.on_1b AND NOT bf.on_2b AND bf.on_3b THEN 'runner_3b'
                    WHEN bf.on_1b AND bf.on_2b AND NOT bf.on_3b THEN 'runners_1b_2b'
                    WHEN bf.on_1b AND NOT bf.on_2b AND bf.on_3b THEN 'runners_1b_3b'
                    WHEN NOT bf.on_1b AND bf.on_2b AND bf.on_3b THEN 'runners_2b_3b'
                    WHEN bf.on_1b AND bf.on_2b AND bf.on_3b THEN 'bases_loaded'
                END as base_state_name,
                
                bf.balls || '-' || bf.strikes as count_code,
                
                -- Metadata
                NOW() as engineered_at,
                1 as engineer_version,
                '{{"velocity_cat", "zone_class", "outcome_binary", "physics_derived"}}'::jsonb as source_calculations
            FROM features_pitch.base_features bf
            {season_filter}
            AND NOT EXISTS (
                SELECT 1 FROM features_pitch.engineered_features ef 
                WHERE ef.pitch_id = bf.pitch_id
            )
            ORDER BY bf.game_pk, bf.pitch_number
            LIMIT %s
        """
        
        if params:
            cur.execute(query, (*params, batch_size))
        else:
            cur.execute(query, [batch_size])
        
        processed = cur.rowcount
        total_processed += processed
        batch_num += 1
        
        conn.commit()
        
        elapsed = (datetime.now() - batch_start).total_seconds()
        logger.info(
            f"Batch {batch_num}: Processed {processed:,} rows "
            f"({total_processed:,} total) in {elapsed:.1f}s"
        )
        
        if processed < batch_size:
            break
    
    cur.close()
    conn.close()
    
    total_time = (datetime.now() - start_time).total_seconds()
    
    stats = {
        'status': 'complete',
        'source_count': source_count,
        'processed': total_processed,
        'version_tag': version_tag,
        'batches': batch_num,
        'time_seconds': total_time,
        'rows_per_second': total_processed / total_time if total_time > 0 else 0
    }
    
    logger.info(f"Engineering complete: {total_processed:,} rows in {total_time:.1f}s")
    
    return stats


def verify_engineered_features(version_tag: str) -> dict:
    """Verify engineered features data quality."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Row count
    cur.execute("SELECT COUNT(*) FROM features_pitch.engineered_features")
    row_count = cur.fetchone()[0]
    
    # Target distribution
    cur.execute("""
        SELECT outcome_tier1, COUNT(*) 
        FROM features_pitch.engineered_features 
        WHERE outcome_tier1 IS NOT NULL
        GROUP BY outcome_tier1 
        ORDER BY outcome_tier1
    """)
    tier1_dist = {row[0]: row[1] for row in cur.fetchall()}
    
    cur.execute("""
        SELECT outcome_tier2, COUNT(*) 
        FROM features_pitch.engineered_features 
        WHERE outcome_tier2 IS NOT NULL
        GROUP BY outcome_tier2 
        ORDER BY outcome_tier2
    """)
    tier2_dist = {row[0]: row[1] for row in cur.fetchall()}
    
    # Data quality checks
    cur.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE outcome_tier1 IS NULL) as null_tier1,
            COUNT(*) FILTER (WHERE velocity_category IS NULL) as null_velocity,
            COUNT(*) FILTER (WHERE zone_region IS NULL) as null_zone,
            COUNT(*) FILTER (WHERE is_strike IS NULL) as null_strike
        FROM features_pitch.engineered_features
    """)
    quality = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return {
        'row_count': row_count,
        'tier1_distribution': tier1_dist,
        'tier2_distribution': tier2_dist,
        'null_tier1': quality[0],
        'null_velocity': quality[1],
        'null_zone': quality[2],
        'null_strike': quality[3]
    }


def main():
    parser = argparse.ArgumentParser(
        description='Populate engineered features for pitch-level modeling'
    )
    parser.add_argument(
        '--seasons', '-s',
        nargs='+',
        type=int,
        help='Specific seasons to process (default: all)'
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Process all seasons'
    )
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=50000,
        help='Rows per batch (default: 50000)'
    )
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Show what would be processed without inserting'
    )
    parser.add_argument(
        '--verify', '-v',
        action='store_true',
        help='Verify engineered features data quality'
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.verify:
        stats = verify_engineered_features("latest")
        print(f"\nEngineered Features Verification:")
        print(f"  Total rows: {stats['row_count']:,}")
        print(f"  Tier 1 distribution: {stats['tier1_distribution']}")
        print(f"  Tier 2 distribution: {stats['tier2_distribution']}")
        print(f"\n  Data quality:")
        print(f"    Null tier1: {stats['null_tier1']:,}")
        print(f"    Null velocity: {stats['null_velocity']:,}")
        print(f"    Null zone: {stats['null_zone']:,}")
        print(f"    Null strike: {stats['null_strike']:,}")
        return
    
    # Determine seasons
    seasons = None
    if args.seasons:
        seasons = args.seasons
    elif not args.all:
        # Show current state
        base_count = get_base_features_count(conn)
        eng_count = get_engineered_features_count()
        print(f"\nSource (base_features): {base_count:,} pitches")
        print(f"Target (engineered_features): {eng_count:,} pitches")
        print(f"\nUse --all to process all, --seasons to process specific seasons")
        return
    
    # Run engineering
    stats = populate_engineered_features(
        seasons=seasons,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )
    
    if not args.dry_run:
        print(f"\nEngineering complete:")
        print(f"  Processed: {stats['processed']:,} / {stats['source_count']:,}")
        print(f"  Batches: {stats['batches']}")
        print(f"  Time: {stats['time_seconds']:.1f}s")
        print(f"  Rate: {stats['rows_per_second']:,.0f} rows/sec")
        
        # Auto-verify
        verify_stats = verify_engineered_features("latest")
        print(f"\n  Verification:")
        print(f"    Row count: {verify_stats['row_count']:,}")
        print(f"    Tier 1 classes: {len(verify_stats['tier1_distribution'])}")


if __name__ == '__main__':
    main()
