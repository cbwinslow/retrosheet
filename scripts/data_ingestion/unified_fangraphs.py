#!/usr/bin/env python3
"""
UNIFIED FanGraphs Download + Ingest Script
Downloads player/team stats via pybaseball and ingests ALL fields directly to database.

This script replaces the separate download + ingest pipeline with a single unified operation.
All 50+ FanGraphs fields are preserved without filtering.

Usage:
    python scripts/data_ingestion/unified_fangraphs.py --season 2024
    python scripts/data_ingestion/unified_fangraphs.py --season 2024 --type batting
    python scripts/data_ingestion/unified_fangraphs.py --season 2024 --type pitching
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import psycopg2

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Optional pybaseball import
try:
    from pybaseball import batting_stats, pitching_stats
    HAS_PYBASEBALL = True
except ImportError:
    HAS_PYBASEBASEBALL = False
    print("Warning: pybaseball not installed. FanGraphs download requires pybaseball.")


DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/retrosheet')


def get_conn():
    return psycopg2.connect(DB_URL)


def normalize_column_name(col: str) -> str:
    """Convert FanGraphs/pandas column names to snake_case for PostgreSQL."""
    # Special mappings for FanGraphs columns
    mappings = {
        'IDfg': 'player_id',
        'Team': 'team_abbr',
        'Name': 'player_name',
        'Season': 'season',
        'Age': 'age',
        'Age Rng': 'age_range',
        'TM': 'team_abbr',
        'playerid': 'player_id',
        'teamid': 'team_id',
        'WAR': 'war',
        'wRC+': 'wrc_plus',
        'wOBA': 'woba',
        'OPS+': 'ops_plus',
        'BB%': 'bb_pct',
        'K%': 'k_pct',
        'BB/K': 'bb_k_ratio',
        'ISO': 'iso',
        'BABIP': 'babip',
        'GB%': 'gb_pct',
        'FB%': 'fb_pct',
        'LD%': 'ld_pct',
        'IFFB%': 'iffb_pct',
        'HR/FB': 'hr_fb_ratio',
        'GB/FB': 'gb_fb_ratio',
        'O-Swing%': 'o_swing_pct',
        'Z-Swing%': 'z_swing_pct',
        'Swing%': 'swing_pct',
        'O-Contact%': 'o_contact_pct',
        'Z-Contact%': 'z_contact_pct',
        'Contact%': 'contact_pct',
        'Zone%': 'zone_pct',
        'F-Strike%': 'f_strike_pct',
        'SwStr%': 'swstr_pct',
        '2B': 'double',
        '3B': 'triple',
        'G': 'g',
        'PA': 'pa',
        'AB': 'ab',
        'R': 'r',
        'H': 'h',
        'HR': 'hr',
        'RBI': 'rbi',
        'SB': 'sb',
        'CS': 'cs',
        'BB': 'bb',
        'IBB': 'ibb',
        'SO': 'so',
        'HBP': 'hbp',
        'SF': 'sf',
        'SH': 'sh',
        'GDP': 'gdp',
        'AVG': 'avg',
        'OBP': 'obp',
        'SLG': 'slg',
        'OPS': 'ops',
        'wRAA': 'wraa',
        'Bat': 'bat',
        'BsR': 'bsr',
        'Fld': 'fld',
        'Off': 'off',
        'Def': 'def',
        'Pos': 'pos',
        '$': 'woba_dollars',
        'Dol': 'woba_dollars',
        '1B': 'single',
        'K/9': 'k_9',
        'BB/9': 'bb_9',
        'K/BB': 'k_bb_ratio',
        'IP': 'ip',
        'TBF': 'tbf',
        'H9': 'h_9',
        'ER': 'er',
        'ERA': 'era',
        'WHIP': 'whip',
        'FIP': 'fip',
        'xFIP': 'xfip',
        'SIERA': 'siera',
        'K-BB%': 'k_bb_pct',
        'LOB%': 'lob_pct',
        'FA%': 'fastball_pct',
        'SL%': 'slider_pct',
        'CT%': 'cutter_pct',
        'CB%': 'curveball_pct',
        'CH%': 'changeup_pct',
        'SF%': 'splitter_pct',
        'KN%': 'knuckleball_pct',
        'SI%': 'sinker_pct',
        'wFB': 'wfb',
        'wSL': 'wsl',
        'wCT': 'wct',
        'wCB': 'wcb',
        'wCH': 'wch',
        'wSF': 'wsf',
        'wKN': 'wkn',
        'vFA': 'v_fastball',
        'vSL': 'v_slider',
        'vCT': 'v_cutter',
        'vCB': 'v_curveball',
        'vCH': 'v_changeup',
        'vSF': 'v_splitter',
        'vKN': 'v_knuckleball',
        'vSI': 'v_sinker',
        'CSW%': 'csw_pct',
        'Velo': 'velo',
        'GS': 'gs',
        'W': 'w',
        'L': 'l',
        'SV': 'sv',
        'BS': 'bs',
        'HLD': 'hold',
        'QS': 'qs',
        'WP': 'wp',
        'BK': 'bk',
        'RA9-WAR': 'ra9_war',
        'RAR': 'rar',
    }
    
    if col in mappings:
        return mappings[col]
    
    # Default: lowercase, replace special chars with underscore
    import re
    normalized = re.sub(r'[^a-zA-Z0-9]+', '_', col).lower().strip('_')
    return normalized


def ensure_schema_exists():
    """Ensure raw_fangraphs schema exists."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("CREATE SCHEMA IF NOT EXISTS raw_fangraphs")
    conn.commit()
    cur.close()
    conn.close()


def get_table_for_type(stat_type: str) -> str:
    """Get target table name for stat type."""
    return {
        'batting': 'player_batting_season',
        'pitching': 'player_pitching_season',
    }.get(stat_type, 'player_batting_season')


def ingest_batting_stats(df: pd.DataFrame, season: int) -> int:
    """Ingest batting stats DataFrame."""
    if df.empty:
        return 0
    
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Create staging table
        cur.execute("DROP TABLE IF EXISTS raw_fangraphs.stg_batting")
        
        original_cols = df.columns.tolist()
        normalized_cols = [normalize_column_name(c) for c in original_cols]
        
        # Build column definitions
        col_defs = []
        for col in original_cols:
            norm = normalize_column_name(col)
            col_defs.append(f'"{norm}" TEXT')
        
        cur.execute(f"CREATE TABLE raw_fangraphs.stg_batting ({', '.join(col_defs)})")
        
        # Insert data
        col_list = ', '.join([f'"{c}"' for c in normalized_cols])
        placeholders = ', '.join(['%s'] * len(normalized_cols))
        
        rows = []
        for _, row in df.iterrows():
            rows.append([str(v) if pd.notna(v) else None for v in row.values])
        
        if rows:
            cur.executemany(
                f'INSERT INTO raw_fangraphs.stg_batting ({col_list}) VALUES ({placeholders})',
                rows
            )
        
        # Build upsert
        # Primary key: player_id + season
        update_cols = [c for c in normalized_cols if c not in ['player_id', 'season']]
        
        # Build type casting for known columns
        cast_map = {
            'season': '::INT',
            'age': '::INT',
            'g': '::INT',
            'pa': '::INT',
            'ab': '::INT',
            'h': '::INT',
            'single': '::INT',
            'double': '::INT',
            'triple': '::INT',
            'hr': '::INT',
            'r': '::INT',
            'rbi': '::INT',
            'sb': '::INT',
            'cs': '::INT',
            'bb': '::INT',
            'ibb': '::INT',
            'so': '::INT',
            'hbp': '::INT',
            'sf': '::INT',
            'sh': '::INT',
            'gdp': '::INT',
            'avg': '::REAL',
            'obp': '::REAL',
            'slg': '::REAL',
            'ops': '::REAL',
            'woba': '::REAL',
            'wrc_plus': '::INT',
            'war': '::REAL',
            'bb_pct': '::REAL',
            'k_pct': '::REAL',
            'bb_k_ratio': '::REAL',
            'iso': '::REAL',
            'babip': '::REAL',
            'gb_pct': '::REAL',
            'fb_pct': '::REAL',
            'ld_pct': '::REAL',
            'iffb_pct': '::REAL',
            'hr_fb_ratio': '::REAL',
            'gb_fb_ratio': '::REAL',
            'o_swing_pct': '::REAL',
            'z_swing_pct': '::REAL',
            'swing_pct': '::REAL',
            'o_contact_pct': '::REAL',
            'z_contact_pct': '::REAL',
            'contact_pct': '::REAL',
            'zone_pct': '::REAL',
            'f_strike_pct': '::REAL',
            'swstr_pct': '::REAL',
            'bat': '::REAL',
            'bsr': '::REAL',
            'fld': '::REAL',
            'off': '::REAL',
            'def': '::REAL',
            'wraa': '::REAL',
        }
        
        # Build SELECT with type casting
        select_parts = []
        for col in normalized_cols:
            cast = cast_map.get(col, '')
            select_parts.append(f'NULLIF("{col}", \'\'){cast} as "{col}"')
        
        select_sql = ', '.join(select_parts)
        
        if update_cols:
            update_set = ', '.join([f'"{c}" = EXCLUDED."{c}"' for c in update_cols])
            upsert_sql = f"""
                INSERT INTO raw_fangraphs.player_batting_season ({', '.join(normalized_cols)})
                SELECT {select_sql}
                FROM raw_fangraphs.stg_batting
                ON CONFLICT (player_id, season)
                DO UPDATE SET {update_set}
            """
        else:
            upsert_sql = f"""
                INSERT INTO raw_fangraphs.player_batting_season ({', '.join(normalized_cols)})
                SELECT {select_sql}
                FROM raw_fangraphs.stg_batting
                ON CONFLICT (player_id, season) DO NOTHING
            """
        
        cur.execute(upsert_sql)
        
        # Cleanup
        cur.execute("DROP TABLE IF EXISTS raw_fangraphs.stg_batting")
        
        conn.commit()
        return len(rows)
        
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def ingest_pitching_stats(df: pd.DataFrame, season: int) -> int:
    """Ingest pitching stats DataFrame."""
    if df.empty:
        return 0
    
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("DROP TABLE IF EXISTS raw_fangraphs.stg_pitching")
        
        original_cols = df.columns.tolist()
        normalized_cols = [normalize_column_name(c) for c in original_cols]
        
        col_defs = []
        for col in original_cols:
            norm = normalize_column_name(col)
            col_defs.append(f'"{norm}" TEXT')
        
        cur.execute(f"CREATE TABLE raw_fangraphs.stg_pitching ({', '.join(col_defs)})")
        
        col_list = ', '.join([f'"{c}"' for c in normalized_cols])
        placeholders = ', '.join(['%s'] * len(normalized_cols))
        
        rows = []
        for _, row in df.iterrows():
            rows.append([str(v) if pd.notna(v) else None for v in row.values])
        
        if rows:
            cur.executemany(
                f'INSERT INTO raw_fangraphs.stg_pitching ({col_list}) VALUES ({placeholders})',
                rows
            )
        
        update_cols = [c for c in normalized_cols if c not in ['player_id', 'season']]
        
        cast_map = {
            'season': '::INT',
            'age': '::INT',
            'g': '::INT',
            'gs': '::INT',
            'ip': '::REAL',
            'tbf': '::INT',
            'h': '::INT',
            'r': '::INT',
            'er': '::INT',
            'hr': '::INT',
            'bb': '::INT',
            'ibb': '::INT',
            'so': '::INT',
            'hbp': '::INT',
            'wp': '::INT',
            'bk': '::INT',
            'w': '::INT',
            'l': '::INT',
            'sv': '::INT',
            'bs': '::INT',
            'hold': '::INT',
            'qs': '::INT',
            'era': '::REAL',
            'whip': '::REAL',
            'k_9': '::REAL',
            'bb_9': '::REAL',
            'k_bb_ratio': '::REAL',
            'fip': '::REAL',
            'xfip': '::REAL',
            'siera': '::REAL',
            'war': '::REAL',
            'ra9_war': '::REAL',
            'k_pct': '::REAL',
            'bb_pct': '::REAL',
            'k_bb_pct': '::REAL',
            'hr_fb_ratio': '::REAL',
            'lob_pct': '::REAL',
            'gb_pct': '::REAL',
            'fb_pct': '::REAL',
            'ld_pct': '::REAL',
            'gb_fb_ratio': '::REAL',
            'o_swing_pct': '::REAL',
            'z_swing_pct': '::REAL',
            'swing_pct': '::REAL',
            'o_contact_pct': '::REAL',
            'z_contact_pct': '::REAL',
            'contact_pct': '::REAL',
            'zone_pct': '::REAL',
            'f_strike_pct': '::REAL',
            'swstr_pct': '::REAL',
            'csw_pct': '::REAL',
            'velo': '::REAL',
            'v_fastball': '::REAL',
            'v_slider': '::REAL',
            'v_curveball': '::REAL',
            'v_changeup': '::REAL',
            'v_cutter': '::REAL',
            'v_sinker': '::REAL',
            'v_splitter': '::REAL',
            'v_knuckleball': '::REAL',
            'fastball_pct': '::REAL',
            'slider_pct': '::REAL',
            'curveball_pct': '::REAL',
            'changeup_pct': '::REAL',
            'cutter_pct': '::REAL',
            'sinker_pct': '::REAL',
            'splitter_pct': '::REAL',
            'knuckleball_pct': '::REAL',
            'wfb': '::REAL',
            'wsl': '::REAL',
            'wcb': '::REAL',
            'wch': '::REAL',
            'wsf': '::REAL',
            'wkn': '::REAL',
        }
        
        select_parts = []
        for col in normalized_cols:
            cast = cast_map.get(col, '')
            select_parts.append(f'NULLIF("{col}", \'\'){cast} as "{col}"')
        
        select_sql = ', '.join(select_parts)
        
        if update_cols:
            update_set = ', '.join([f'"{c}" = EXCLUDED."{c}"' for c in update_cols])
            upsert_sql = f"""
                INSERT INTO raw_fangraphs.player_pitching_season ({', '.join(normalized_cols)})
                SELECT {select_sql}
                FROM raw_fangraphs.stg_pitching
                ON CONFLICT (player_id, season)
                DO UPDATE SET {update_set}
            """
        else:
            upsert_sql = f"""
                INSERT INTO raw_fangraphs.player_pitching_season ({', '.join(normalized_cols)})
                SELECT {select_sql}
                FROM raw_fangraphs.stg_pitching
                ON CONFLICT (player_id, season) DO NOTHING
            """
        
        cur.execute(upsert_sql)
        cur.execute("DROP TABLE IF EXISTS raw_fangraphs.stg_pitching")
        
        conn.commit()
        return len(rows)
        
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def unified_download_ingest(season: int, stat_type: str = 'batting', **kwargs) -> dict:
    """
    Download and ingest FanGraphs stats in one operation.
    
    Args:
        season: MLB season year
        stat_type: 'batting' or 'pitching'
        **kwargs: Additional args for pybaseball functions
        
    Returns:
        Dict with statistics
    """
    if not HAS_PYBASEBALL:
        return {'success': False, 'error': 'pybaseball not installed'}
    
    print(f"Downloading FanGraphs {stat_type} stats for season {season}...")
    
    # Ensure schema exists
    ensure_schema_exists()
    
    try:
        if stat_type == 'batting':
            df = batting_stats(season, **kwargs)
            ingested = ingest_batting_stats(df, season)
            table = 'player_batting_season'
        elif stat_type == 'pitching':
            df = pitching_stats(season, **kwargs)
            ingested = ingest_pitching_stats(df, season)
            table = 'player_pitching_season'
        else:
            return {'success': False, 'error': f'Unknown stat_type: {stat_type}'}
        
        print(f"  Downloaded: {len(df):,} players")
        print(f"  Ingested: {ingested:,} rows to raw_fangraphs.{table}")
        
        return {
            'season': season,
            'stat_type': stat_type,
            'downloaded': len(df),
            'ingested': ingested,
            'success': True
        }
        
    except Exception as e:
        print(f"  ERROR: {e}")
        return {
            'season': season,
            'stat_type': stat_type,
            'success': False,
            'error': str(e)
        }


def main():
    parser = argparse.ArgumentParser(
        description='UNIFIED FanGraphs Download + Ingest - Downloads and loads ALL fields to database'
    )
    parser.add_argument('--season', type=int, required=True, help='MLB season year')
    parser.add_argument('--type', type=str, default='batting', 
                       choices=['batting', 'pitching'],
                       help='Type of stats to download')
    parser.add_argument('--qual', type=str, default='y',
                       help='Qualified only (y/n)')
    
    args = parser.parse_args()
    
    if not HAS_PYBASEBALL:
        print("Error: pybaseball is required. Install with: pip install pybaseball")
        sys.exit(1)
    
    kwargs = {'qual': args.qual}
    
    result = unified_download_ingest(args.season, args.type, **kwargs)
    
    if result.get('success'):
        print(f"\n✓ Unified FanGraphs download+ingest complete")
        sys.exit(0)
    else:
        print(f"\n✗ Unified FanGraphs download+ingest failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
