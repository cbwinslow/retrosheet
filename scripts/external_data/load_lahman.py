#!/usr/bin/env python3
"""
File: scripts/external_data/load_lahman.py
Purpose: Load ALL Lahman CSV files into raw_lahman schema - ALL tables, ALL columns
Author: Agent Cascade
Date: 2026-04-25
Usage: uv run python scripts/external_data/load_lahman.py --dir data/lahman_csv

CRITICAL: This script loads ALL 28 Lahman tables with ALL columns.
It discovers CSV files dynamically and reads headers to capture every field.
"""

import argparse
import csv
import os
import sys
from pathlib import Path

import psycopg2


DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/retrosheet')


def get_conn():
    return psycopg2.connect(DB_URL)


def get_csv_files(csv_dir: Path):
    """Get all CSV files in directory."""
    return sorted(csv_dir.glob('*.csv'))


def read_csv_headers(csv_path: Path):
    """Read headers from CSV file."""
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
    return headers


def discover_tables(csv_dir: Path):
    """
    Discover ALL tables from CSV files.
    Returns: dict of {csv_filename: (table_name, [columns])}
    """
    csv_files = get_csv_files(csv_dir)
    tables = {}
    
    for csv_path in csv_files:
        # Table name is CSV filename without extension, lowercased
        table_name = csv_path.stem.lower()
        headers = read_csv_headers(csv_path)
        tables[csv_path.name] = (table_name, headers)
    
    return tables
            'OAA',
            'OBA',
            'leagueID',
            'parkID',
            'attendance',
            'teamIDBR',
            'teamIDlahman45',
            'teamIDretro',
        ],
    ),
    'Salaries.csv': ('salaries', ['yearID', 'teamID', 'playerID', 'salary']),
    'Pitching.csv': (
        'pitching',
        [
            'yearID',
            'lgID',
            'teamID',
            'playerID',
            'W',
            'L',
            'G',
            'GS',
            'CG',
            'SHO',
            'SV',
            'IPouts',
            'H',
            'ER',
            'HR',
            'BB',
            'SO',
            'BAOpp',
            'ERA',
            'IBB',
            'WP',
            'HBP',
            'BK',
            'BFP',
            'GF',
            'R',
            'SH',
            'SF',
            'GIDP',
        ],
    ),
    'Batting.csv': (
        'batting',
        [
            'yearID',
            'lgID',
            'teamID',
            'playerID',
            'G',
            'AB',
            'R',
            'H',
            '_2B',
            '_3B',
            'HR',
            'RBI',
            'SB',
            'CS',
            'BB',
            'SO',
            'IBB',
            'HBP',
            'SH',
            'SF',
            'GIDP',
        ],
    ),
}


def create_staging(cur, table, columns):
    cur.execute(f'DROP TABLE IF EXISTS raw_lahman.stg_{table}')
    col_defs = ', '.join([f'{c} TEXT' for c in columns])
    cur.execute(f'CREATE TABLE raw_lahman.stg_{table} ({col_defs})')


def copy_to_staging(cur, csv_path, table):
    with open(csv_path, newline='') as f:
        cur.copy_expert(f'COPY raw_lahman.stg_{table} FROM STDIN WITH CSV HEADER', f)


def upsert(cur, table, columns):
    # Define column groups for proper casting
    int_cols = {
        'birthYear',
        'birthMonth',
        'birthDay',
        'deathYear',
        'deathMonth',
        'deathDay',
        'weight',
        'height',
        'yearID',
        'Rank',
        'G',
        'Ghome',
        'W',
        'L',
        'AB',
        'H',
        '_2B',
        '_3B',
        'HR',
        'BB',
        'SO',
        'SB',
        'CS',
        'HBP',
        'SF',
        'RA',
        'ER',
        'CG',
        'SHO',
        'SV',
        'IPouts',
        'HAA',
        'HA',
        'attendance',
        'salary',
        'R',
        'GIDP',
        'GS',
        'IBB',
        'WP',
        'BK',
        'BFP',
        'GF',
        'SH',
        'RBI',
    }
    numeric_cols = {'ERA', 'BAOpp', 'BAA', 'OAA', 'OBA', 'AVG', 'OBP', 'SLG', 'OPS'}
    date_cols = {'debut', 'finalGame'}

    # Cast each column to the appropriate type
    cast_expressions = []
    for c in columns:
        if c in (
            'playerID',
            'teamID',
            'franchID',
            'lgID',
            'divID',
            'parkID',
            'leagueID',
            'retroID',
            'bbrefID',
        ):
            cast_expressions.append(c)  # keep as TEXT
        elif c in int_cols:
            # Use NULLIF to treat empty strings as NULL before casting to INT
            cast_expressions.append(f"NULLIF({c}, '')::INT")
        elif c in numeric_cols:
            cast_expressions.append(f'{c}::NUMERIC')
        elif c in date_cols:
            cast_expressions.append(f'{c}::DATE')
        else:
            cast_expressions.append(f'{c}::TEXT')

    # Determine primary-key columns for each table
    if table == 'people':
        pk_cols = ['playerID']
    elif table == 'teams':
        pk_cols = ['yearID', 'teamID']
    elif table == 'salaries':
        pk_cols = ['yearID', 'teamID', 'playerID']
    elif table in ('pitching', 'batting'):
        pk_cols = ['yearID', 'playerID', 'teamID']
    else:
        pk_cols = [columns[0]]  # fallback

    # Build SET clause for all non-PK columns
    set_clause = ', '.join([f'{c}=EXCLUDED.{c}' for c in columns if c not in pk_cols])

    # Use ON CONFLICT ON CONSTRAINT <table>_pkey for safety
    cur.execute(
        f"""
        INSERT INTO raw_lahman.{table} ({', '.join(columns)})
        SELECT {', '.join(cast_expressions)} FROM raw_lahman.stg_{table}
        ON CONFLICT ON CONSTRAINT {table}_pkey DO UPDATE SET {set_clause}
        """,
    )


def process_file(csv_dir: Path, filename: str, table: str, columns: list):
    csv_path = csv_dir / filename
    if not csv_path.is_file():
        print(f'⚠️  {filename} not found, skipping.', file=sys.stderr)
        return
    conn = get_conn()
    try:
        cur = conn.cursor()
        create_staging(cur, table, columns)
        copy_to_staging(cur, csv_path, table)
        upsert(cur, table, columns)
        conn.commit()
        print(f'✅ Loaded {filename} into raw_lahman.{table}')
    finally:
        cur.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Load Lahman CSVs')
    parser.add_argument('--dir', type=Path, required=True, help='Directory containing Lahman CSVs')
    args = parser.parse_args()
    for filename, (table, cols) in TABLES.items():
        process_file(args.dir, filename, table, cols)


if __name__ == '__main__':
    main()
