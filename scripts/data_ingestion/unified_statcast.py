#!/usr/bin/env python3
"""
UNIFIED Statcast Download + Ingest Script
Downloads Statcast pitch-level data via pybaseball and ingests directly to database.

This script replaces the separate download + ingest pipeline with a single unified operation.
All Statcast fields are preserved without filtering.

Usage:
    python scripts/data_ingestion/unified_statcast.py --season 2024
    python scripts/data_ingestion/unified_statcast.py --start-date 2024-03-28 --end-date 2024-09-30
    python scripts/data_ingestion/unified_statcast.py --season 2024 --workers 4
"""

import argparse
import os
import sys
import tempfile
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import pandas as pd
import psycopg2

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.data_ingestion.download_statcast_pitch_level import download_statcast_range
from scripts.external_data.load_statcast import load_statcast_csv


DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/retrosheet')

# Complete Statcast field mapping (124+ fields)
STATCAST_COLUMNS = [
    'pitch_type', 'game_date', 'release_speed', 'release_pos_x', 'release_pos_z',
    'player_name', 'batter', 'pitcher', 'events', 'description', 'spin_dir',
    'spin_rate_deprecated', 'break_angle_deprecated', 'break_length_deprecated',
    'zone', 'des', 'game_type', 'stand', 'p_throws', 'home_team', 'away_team',
    'type', 'hit_location', 'bb_type', 'balls', 'strikes', 'game_year', 'pfx_x',
    'pfx_z', 'px', 'pz', 'on_3b', 'on_2b', 'on_1b', 'outs_when_up', 'inning',
    'inning_topbot', 'hc_x', 'hc_y', 'tfs_deprecated', 'tfs_zulu_deprecated',
    'fielder_2', 'umpire', 'sv_id', 'vx0', 'vy0', 'vz0', 'ax', 'ay', 'az',
    'sz_top', 'sz_bot', 'hit_distance_sc', 'launch_speed', 'launch_angle',
    'effective_speed', 'release_spin_rate', 'release_extension', 'game_pk',
    'pitcher_1', 'fielder_2_1', 'fielder_3', 'fielder_4', 'fielder_5',
    'fielder_6', 'fielder_7', 'fielder_8', 'fielder_9', 'release_pos_y',
    'estimated_ba_using_speedangle', 'estimated_woba_using_speedangle',
    'woba_value', 'woba_denom', 'babip_value', 'iso_value', 'launch_speed_angle',
    'at_bat_number', 'pitch_number', 'pitch_name', 'home_score', 'away_score',
    'bat_score', 'fld_score', 'post_away_score', 'post_home_score', 'post_bat_score',
    'post_fld_score', 'if_fielding_alignment', 'of_fielding_alignment',
    'spin_axis', 'delta_home_win_exp', 'delta_run_exp', 'bat_speed', 'swing_length',
    'attack_angle', 'attack_direction', 'swing_path_tilt', 'delta_pitcher_run_exp',
    'estimated_slg_using_speedangle', 'bat_win_exp', 'fld_win_exp', 'wpa', 're24',
    'index', 'rs', 'ra', 'innings_pitched', 'k_percent', 'barrel', 'hard_hit'
]


def get_conn():
    return psycopg2.connect(DB_URL)


def ensure_table_exists():
    """Create raw_mlb.statcast table with ALL columns if not exists."""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS raw_mlb.statcast (
            -- Identity
            statcast_id BIGSERIAL PRIMARY KEY,
            game_pk INT NOT NULL,
            at_bat_number INT,
            pitch_number INT,
            sv_id TEXT,
            
            -- Timestamps
            game_date DATE,
            game_year INT,
            
            -- Players
            player_name TEXT,
            batter INT,
            pitcher INT,
            pitcher_1 INT,
            fielder_2 INT,
            fielder_2_1 INT,
            fielder_3 INT,
            fielder_4 INT,
            fielder_5 INT,
            fielder_6 INT,
            fielder_7 INT,
            fielder_8 INT,
            fielder_9 INT,
            umpire INT,
            
            -- Game Context
            game_type TEXT,
            home_team TEXT,
            away_team TEXT,
            stand TEXT,
            p_throws TEXT,
            inning INT,
            inning_topbot TEXT,
            outs_when_up INT,
            
            -- Count
            balls INT,
            strikes INT,
            
            -- Base State
            on_1b INT,
            on_2b INT,
            on_3b INT,
            
            -- Scores
            home_score INT,
            away_score INT,
            bat_score INT,
            fld_score INT,
            post_home_score INT,
            post_away_score INT,
            post_bat_score INT,
            post_fld_score INT,
            
            -- Pitch Characteristics
            pitch_type TEXT,
            pitch_name TEXT,
            release_speed REAL,
            release_pos_x REAL,
            release_pos_y REAL,
            release_pos_z REAL,
            release_spin_rate REAL,
            release_extension REAL,
            effective_speed REAL,
            spin_axis REAL,
            
            -- Pitch Physics
            pfx_x REAL,
            pfx_z REAL,
            px REAL,
            pz REAL,
            vx0 REAL,
            vy0 REAL,
            vz0 REAL,
            ax REAL,
            ay REAL,
            az REAL,
            
            -- Strike Zone
            sz_top REAL,
            sz_bot REAL,
            zone INT,
            
            -- Pitch Outcome
            type TEXT,
            events TEXT,
            description TEXT,
            des TEXT,
            
            -- Batted Ball
            bb_type TEXT,
            hit_location INT,
            hc_x REAL,
            hc_y REAL,
            hit_distance_sc REAL,
            launch_speed REAL,
            launch_angle REAL,
            launch_speed_angle INT,
            
            -- Expected Stats
            estimated_ba_using_speedangle REAL,
            estimated_woba_using_speedangle REAL,
            estimated_slg_using_speedangle REAL,
            
            -- Value Stats
            woba_value REAL,
            woba_denom REAL,
            babip_value REAL,
            iso_value REAL,
            
            -- Run Expectancy
            delta_run_exp REAL,
            delta_home_win_exp REAL,
            delta_pitcher_run_exp REAL,
            bat_win_exp REAL,
            fld_win_exp REAL,
            wpa REAL,
            re24 REAL,
            
            -- Bat Tracking (2024+)
            bat_speed REAL,
            swing_length REAL,
            attack_angle REAL,
            attack_direction REAL,
            swing_path_tilt REAL,
            
            -- Quality Metrics
            barrel BOOLEAN,
            hard_hit BOOLEAN,
            k_percent REAL,
            
            -- Alignments
            if_fielding_alignment TEXT,
            of_fielding_alignment TEXT,
            
            -- Deprecated
            spin_dir REAL,
            spin_rate_deprecated REAL,
            break_angle_deprecated REAL,
            break_length_deprecated REAL,
            tfs_deprecated TEXT,
            tfs_zulu_deprecated TIMESTAMPTZ,
            
            -- Metadata
            index INT,
            rs INT,
            ra INT,
            innings_pitched REAL,
            
            -- Ingest tracking
            ingested_at TIMESTAMPTZ DEFAULT NOW(),
            ingest_run_id BIGINT,
            
            -- Unique constraint
            CONSTRAINT unique_statcast_pitch UNIQUE (game_pk, at_bat_number, pitch_number, sv_id)
        );
    """)
    
    # Create indexes
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_statcast_game ON raw_mlb.statcast(game_pk);
        CREATE INDEX IF NOT EXISTS idx_statcast_date ON raw_mlb.statcast(game_date);
        CREATE INDEX IF NOT EXISTS idx_statcast_batter ON raw_mlb.statcast(batter);
        CREATE INDEX IF NOT EXISTS idx_statcast_pitcher ON raw_mlb.statcast(pitcher);
        CREATE INDEX IF NOT EXISTS idx_statcast_season ON raw_mlb.statcast(game_year);
    """)
    
    conn.commit()
    cur.close()
    conn.close()


def ingest_dataframe(df: pd.DataFrame, season: int) -> int:
    """Ingest a DataFrame directly to the database."""
    if df.empty:
        return 0
    
    conn = get_conn()
    cur = conn.cursor()
    
    # Create temporary staging table
    cur.execute("DROP TABLE IF EXISTS raw_mlb.stg_statcast")
    
    # Build column definitions for staging
    all_cols = df.columns.tolist()
    col_defs = ', '.join([f'"{c}" TEXT' for c in all_cols])
    cur.execute(f'CREATE TABLE raw_mlb.stg_statcast ({col_defs})')
    
    # Load data using COPY
    from io import StringIO
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=True)
    buffer.seek(0)
    cur.copy_expert("COPY raw_mlb.stg_statcast FROM STDIN WITH CSV HEADER", buffer)
    
    # Build upsert with ALL columns
    col_list = ', '.join([f'"{c}"' for c in all_cols])
    
    # Build SELECT with type casting
    select_cols = []
    for col in all_cols:
        if col in ['game_date']:
            select_cols.append(f'NULLIF("{col}", \'\')::DATE as "{col}"')
        elif col in ['game_pk', 'game_year', 'at_bat_number', 'pitch_number', 'batter', 'pitcher',
                     'pitcher_1', 'fielder_2', 'fielder_2_1', 'fielder_3', 'fielder_4', 'fielder_5',
                     'fielder_6', 'fielder_7', 'fielder_8', 'fielder_9', 'umpire', 'inning',
                     'outs_when_up', 'balls', 'strikes', 'on_1b', 'on_2b', 'on_3b', 'hit_location',
                     'home_score', 'away_score', 'bat_score', 'fld_score', 'post_home_score',
                     'post_away_score', 'post_bat_score', 'post_fld_score', 'zone', 'index', 'rs', 'ra',
                     'launch_speed_angle']:
            select_cols.append(f'NULLIF("{col}", \'\')::INT as "{col}"')
        elif col in ['release_speed', 'release_pos_x', 'release_pos_y', 'release_pos_z',
                     'release_spin_rate', 'release_extension', 'effective_speed', 'spin_axis',
                     'pfx_x', 'pfx_z', 'px', 'pz', 'vx0', 'vy0', 'vz0', 'ax', 'ay', 'az',
                     'sz_top', 'sz_bot', 'hc_x', 'hc_y', 'hit_distance_sc', 'launch_speed',
                     'launch_angle', 'estimated_ba_using_speedangle', 'estimated_woba_using_speedangle',
                     'estimated_slg_using_speedangle', 'woba_value', 'woba_denom', 'babip_value',
                     'iso_value', 'delta_run_exp', 'delta_home_win_exp', 'delta_pitcher_run_exp',
                     'bat_win_exp', 'fld_win_exp', 'wpa', 're24', 'bat_speed', 'swing_length',
                     'attack_angle', 'attack_direction', 'swing_path_tilt', 'spin_dir',
                     'spin_rate_deprecated', 'break_angle_deprecated', 'break_length_deprecated',
                     'innings_pitched', 'k_percent']:
            select_cols.append(f'NULLIF("{col}", \'\')::REAL as "{col}"')
        elif col in ['barrel', 'hard_hit']:
            select_cols.append(f'(NULLIF("{col}", \'\')::BOOLEAN OR "{col}" = \'1\' OR LOWER("{col}") = \'true\') as "{col}"')
        else:
            select_cols.append(f'"{col}"')
    
    select_sql = ', '.join(select_cols)
    
    # Build conflict columns for unique constraint
    conflict_cols = ['game_pk', 'at_bat_number', 'pitch_number']
    if 'sv_id' in all_cols:
        conflict_cols.append('COALESCE(sv_id, \'\')')
    
    conflict_sql = ', '.join(conflict_cols)
    
    # Build update set clause (exclude identity columns)
    update_cols = [c for c in all_cols if c not in ['game_pk', 'at_bat_number', 'pitch_number', 'sv_id']]
    update_set = ', '.join([f'"{c}" = EXCLUDED."{c}"' for c in update_cols])
    
    upsert_sql = f"""
        INSERT INTO raw_mlb.statcast ({col_list}, game_year, ingested_at)
        SELECT {select_sql}, {season}::INT, NOW()
        FROM raw_mlb.stg_statcast
        ON CONFLICT (game_pk, at_bat_number, pitch_number, COALESCE(sv_id, ''))
        DO UPDATE SET {update_set}, ingested_at = NOW()
    """
    
    cur.execute(upsert_sql)
    
    # Get count
    cur.execute("SELECT COUNT(*) FROM raw_mlb.stg_statcast")
    count = cur.fetchone()[0]
    
    # Cleanup
    cur.execute("DROP TABLE IF EXISTS raw_mlb.stg_statcast")
    
    conn.commit()
    cur.close()
    conn.close()
    
    return count


def unified_download_ingest_season(season: int, workers: int = 2, verbose: bool = False) -> dict:
    """
    Download and ingest all Statcast data for a season in one operation.
    
    Args:
        season: MLB season year
        workers: Number of parallel download workers
        verbose: Print verbose output
        
    Returns:
        Dict with download and ingest statistics
    """
    print(f"Starting unified Statcast download+ingest for season {season}")
    
    # Ensure table exists
    ensure_table_exists()
    
    # Calculate date range for season
    # MLB season typically: March 28 - September 30 (regular season)
    # Plus postseason through October
    start_date = date(season, 3, 1)
    end_date = date(season, 11, 5)
    
    # Download in monthly chunks to avoid timeouts
    total_downloaded = 0
    total_ingested = 0
    errors = []
    
    current = start_date
    while current <= end_date:
        # Calculate month end
        if current.month == 12:
            month_end = date(current.year, 12, 31)
        else:
            month_end = date(current.year, current.month + 1, 1) - pd.Timedelta(days=1)
        
        chunk_end = min(month_end, end_date)
        
        try:
            print(f"Downloading {current} to {chunk_end}...", end='', flush=True)
            
            # Download via pybaseball
            df = download_statcast_range(str(current), str(chunk_end))
            
            if df is not None and not df.empty:
                downloaded = len(df)
                total_downloaded += downloaded
                print(f" {downloaded} pitches", flush=True)
                
                # Ingest immediately
                print(f"  Ingesting...", end='', flush=True)
                ingested = ingest_dataframe(df, season)
                total_ingested += ingested
                print(f" {ingested} rows", flush=True)
            else:
                print(" no data", flush=True)
                
        except Exception as e:
            error_msg = f"Error processing {current} to {chunk_end}: {e}"
            print(f" ERROR: {e}", flush=True)
            errors.append(error_msg)
            if verbose:
                import traceback
                traceback.print_exc()
        
        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)
    
    result = {
        'season': season,
        'total_downloaded': total_downloaded,
        'total_ingested': total_ingested,
        'errors': errors,
        'success': len(errors) == 0
    }
    
    print(f"\nSeason {season} complete:")
    print(f"  Downloaded: {total_downloaded:,} pitches")
    print(f"  Ingested: {total_ingested:,} rows")
    if errors:
        print(f"  Errors: {len(errors)}")
    
    return result


def unified_download_ingest_range(start_date: str, end_date: str, workers: int = 2) -> dict:
    """
    Download and ingest Statcast data for a date range.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        workers: Number of parallel workers
        
    Returns:
        Dict with statistics
    """
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    season = start.year
    
    print(f"Downloading Statcast data from {start_date} to {end_date}")
    
    # Ensure table exists
    ensure_table_exists()
    
    try:
        df = download_statcast_range(start_date, end_date)
        
        if df is not None and not df.empty:
            ingested = ingest_dataframe(df, season)
            return {
                'start_date': start_date,
                'end_date': end_date,
                'downloaded': len(df),
                'ingested': ingested,
                'success': True
            }
        else:
            return {
                'start_date': start_date,
                'end_date': end_date,
                'downloaded': 0,
                'ingested': 0,
                'success': True
            }
    except Exception as e:
        return {
            'start_date': start_date,
            'end_date': end_date,
            'downloaded': 0,
            'ingested': 0,
            'success': False,
            'error': str(e)
        }


def main():
    parser = argparse.ArgumentParser(
        description='UNIFIED Statcast Download + Ingest - Downloads and loads ALL fields to database'
    )
    parser.add_argument('--season', type=int, help='MLB season year (e.g., 2024)')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--workers', type=int, default=2, help='Parallel download workers')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.season:
        result = unified_download_ingest_season(args.season, args.workers, args.verbose)
    elif args.start_date and args.end_date:
        result = unified_download_ingest_range(args.start_date, args.end_date, args.workers)
    else:
        parser.print_help()
        sys.exit(1)
    
    if result.get('success'):
        print(f"\n✓ Unified Statcast download+ingest complete")
        sys.exit(0)
    else:
        print(f"\n✗ Unified Statcast download+ingest failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
