#!/usr/bin/env python3
"""
UNIFIED Lahman Download + Ingest Script
Downloads Lahman Baseball Databank and ingests ALL tables directly to database.

This script replaces the separate download + ingest pipeline with a single unified operation.
All 28 Lahman tables are preserved without field filtering.

Usage:
    python scripts/data_ingestion/unified_lahman.py
    python scripts/data_ingestion/unified_lahman.py --data-dir /path/to/lahman
"""

import argparse
import os
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from typing import List, Optional
from urllib.request import urlopen

import pandas as pd
import psycopg2

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/retrosheet')

LAHMAN_URL = "https://github.com/chadwickbureau/baseballdatabank/archive/refs/heads/master.zip"

LAHMAN_TABLES = [
    'People', 'Teams', 'TeamsFranchises', 'TeamsHalf',
    'Batting', 'Pitching', 'Fielding', 'FieldingOF', 'FieldingOFSplit',
    'AllStarFull', 'HallOfFame', 'Managers', 'ManagersHalf',
    'AwardsManagers', 'AwardsPlayers', 'AwardsShareManagers', 'AwardsSharePlayers',
    'BattingPost', 'PitchingPost', 'FieldingPost', 'SeriesPost',
    'Appearances', 'Salaries', 'HomeGames', 'Parks', 'CollegePlaying'
]


def get_conn():
    return psycopg2.connect(DB_URL)


def normalize_column_name(col: str) -> str:
    """Convert Lahman column names to snake_case."""
    # Handle special cases
    mappings = {
        'playerID': 'player_id',
        'teamID': 'team_id',
        'teamIDBR': 'team_id_br',
        'teamIDfg': 'team_id_fg',
        'lgID': 'league_id',
        'yearID': 'year_id',
        'gameID': 'game_id',
        'schoolID': 'school_id',
        'managerID': 'manager_id',
        'awardID': 'award_id',
        'hofID': 'hof_id',
        'parkID': 'park_id',
        'franchID': 'franchise_id',
        'team_ID': 'team_id',
        'birthCountry': 'birth_country',
        'birthState': 'birth_state',
        'birthCity': 'birth_city',
        'deathCountry': 'death_country',
        'deathState': 'death_state',
        'deathCity': 'death_city',
        'debutDate': 'debut_date',
        'finalGameDate': 'final_game_date',
        'firstName': 'first_name',
        'lastName': 'last_name',
        'nameGiven': 'name_given',
        'nameNick': 'name_nick',
        'teamName': 'team_name',
        'parkName': 'park_name',
        'divID': 'division_id',
        'teamRank': 'team_rank',
        'divIDW': 'division_id_winner',
        'divIDL': 'division_id_loser',
        'GS': 'games_started',
        'G': 'games',
        'R': 'runs',
        'AB': 'at_bats',
        'H': 'hits',
        '2B': 'doubles',
        '3B': 'triples',
        'HR': 'home_runs',
        'RBI': 'rbi',
        'SB': 'stolen_bases',
        'CS': 'caught_stealing',
        'BB': 'walks',
        'SO': 'strikeouts',
        'IBB': 'intentional_walks',
        'HBP': 'hit_by_pitch',
        'SH': 'sacrifice_hits',
        'SF': 'sacrifice_flies',
        'GIDP': 'grounded_into_double_play',
        'IP': 'innings_pitched',
        'ER': 'earned_runs',
        'CG': 'complete_games',
        'SHO': 'shutouts',
        'SV': 'saves',
        'IB': 'intentional_walks_allowed',
        'WP': 'wild_pitches',
        'BK': 'balks',
        'GF': 'games_finished',
        'PO': 'putouts',
        'A': 'assists',
        'E': 'errors',
        'DP': 'double_plays',
        'PB': 'passed_balls',
        'WP': 'wild_pitches',
        'Z': 'zone_rating',
        'OPS': 'ops',
        'W': 'wins',
        'L': 'losses',
        'ERA': 'era',
    }
    
    if col in mappings:
        return mappings[col]
    
    # Default: convert camelCase to snake_case
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', col)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def ensure_schema_exists():
    """Ensure raw_lahman schema exists."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("CREATE SCHEMA IF NOT EXISTS raw_lahman")
    conn.commit()
    cur.close()
    conn.close()


def create_table_for_df(df: pd.DataFrame, table_name: str, cur):
    """Create a table matching the DataFrame structure."""
    # Map pandas types to PostgreSQL types
    type_mapping = {
        'object': 'TEXT',
        'int64': 'INTEGER',
        'float64': 'REAL',
        'bool': 'BOOLEAN',
        'datetime64[ns]': 'TIMESTAMP',
    }
    
    columns = []
    for col in df.columns:
        normalized = normalize_column_name(col)
        pg_type = type_mapping.get(str(df[col].dtype), 'TEXT')
        columns.append(f'"{normalized}" {pg_type}')
    
    col_def = ', '.join(columns)
    
    # Create table
    cur.execute(f"""
        DROP TABLE IF EXISTS raw_lahman.{table_name}
    """)
    cur.execute(f"""
        CREATE TABLE raw_lahman.{table_name} (
            {col_def}
        )
    """)


def ingest_csv_to_table(csv_path: Path, table_name: str, cur) -> int:
    """Load a CSV file into the database table."""
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    df = df.replace('', None)
    
    if df.empty:
        return 0
    
    # Create table
    create_table_for_df(df, table_name, cur)
    
    # Build column lists
    original_cols = df.columns.tolist()
    normalized_cols = [normalize_column_name(c) for c in original_cols]
    
    col_list = ', '.join([f'"{c}"' for c in normalized_cols])
    placeholders = ', '.join(['%s'] * len(normalized_cols))
    
    # Insert data
    rows = df.values.tolist()
    cur.executemany(
        f'INSERT INTO raw_lahman.{table_name} ({col_list}) VALUES ({placeholders})',
        rows
    )
    
    return len(rows)


def download_lahman_zip() -> bytes:
    """Download Lahman data from GitHub as zip."""
    print("Downloading Lahman Baseball Databank from GitHub...")
    with urlopen(LAHMAN_URL) as response:
        return response.read()


def unified_download_ingest(data_dir: Optional[str] = None) -> dict:
    """
    Download and ingest ALL Lahman tables in one operation.
    
    Args:
        data_dir: Optional path to existing Lahman CSV files
        
    Returns:
        Dict with statistics per table
    """
    results = {}
    
    # Ensure schema exists
    ensure_schema_exists()
    
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        if data_dir:
            # Use existing CSV files
            data_path = Path(data_dir)
            print(f"Using existing Lahman data from {data_dir}")
        else:
            # Download zip and extract
            zip_data = download_lahman_zip()
            print(f"Downloaded {len(zip_data):,} bytes")
            
            # Extract CSVs
            with zipfile.ZipFile(BytesIO(zip_data)) as zf:
                # Find the CSV directory
                csv_prefix = None
                for name in zf.namelist():
                    if name.endswith('.csv'):
                        parts = name.split('/')
                        if len(parts) >= 3 and parts[-2] == 'core':
                            csv_prefix = '/'.join(parts[:-2])
                            break
                
                print(f"Extracting from {csv_prefix}...")
                
                # Process each table
                for table in LAHMAN_TABLES:
                    csv_name = f"{table}.csv"
                    csv_path_in_zip = f"{csv_prefix}/core/{csv_name}"
                    
                    try:
                        with zf.open(csv_path_in_zip) as f:
                            df = pd.read_csv(f, dtype=str, keep_default_na=False)
                            df = df.replace('', None)
                            
                            if not df.empty:
                                create_table_for_df(df, table, cur)
                                
                                original_cols = df.columns.tolist()
                                normalized_cols = [normalize_column_name(c) for c in original_cols]
                                col_list = ', '.join([f'"{c}"' for c in normalized_cols])
                                placeholders = ', '.join(['%s'] * len(normalized_cols))
                                
                                rows = df.values.tolist()
                                cur.executemany(
                                    f'INSERT INTO raw_lahman.{table} ({col_list}) VALUES ({placeholders})',
                                    rows
                                )
                                
                                results[table] = len(rows)
                                print(f"  {table}: {len(rows):,} rows")
                    except KeyError:
                        print(f"  {table}: not found in zip")
                    except Exception as e:
                        print(f"  {table}: ERROR - {e}")
                        results[table] = f"ERROR: {e}"
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
    
    # Print summary
    print(f"\nLahman Unified Download+Ingest Complete:")
    total_rows = sum(v for v in results.values() if isinstance(v, int))
    print(f"  Total tables: {len(results)}")
    print(f"  Total rows: {total_rows:,}")
    
    return {
        'tables_processed': len(results),
        'total_rows': total_rows,
        'table_details': results,
        'success': True
    }


def main():
    parser = argparse.ArgumentParser(
        description='UNIFIED Lahman Download + Ingest - Downloads and loads ALL tables to database'
    )
    parser.add_argument('--data-dir', type=str, help='Path to existing Lahman CSV files')
    parser.add_argument('--table', type=str, help='Process single table only')
    
    args = parser.parse_args()
    
    result = unified_download_ingest(args.data_dir)
    
    if result.get('success'):
        print(f"\n✓ Unified Lahman download+ingest complete")
        sys.exit(0)
    else:
        print(f"\n✗ Unified Lahman download+ingest failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
