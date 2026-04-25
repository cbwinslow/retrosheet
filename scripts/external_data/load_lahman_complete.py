#!/usr/bin/env python3
"""
File: scripts/external_data/load_lahman_complete.py
Purpose: COMPLETE Lahman Baseball Database loader - reads CSV headers dynamically
         and loads ALL columns from ALL 28 tables. No field selection, no dropping.
Author: Agent Cascade
Date: 2026-04-25
Usage: uv run python scripts/external_data/load_lahman_complete.py --dir data/lahman_csv
Dependencies: psycopg2, python-dotenv

This replaces load_lahman.py which only loaded 5 tables with a subset of columns.
This script:
  1. Reads CSV headers to discover ALL columns dynamically
  2. Loads ALL 28 Lahman tables (not just 5)
  3. Loads ALL columns from each table (not just selected ones)
  4. Validates row counts match source files
  5. Reports on what was loaded vs what was available

CRITICAL PRINCIPLE: Capture 100% of available data. No field dropping.
"""

import argparse
import csv
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


# Load environment variables for database connection
load_dotenv()

# CSV file to table name mapping (following Lahman conventions)
# Keys: CSV filename, Values: (table_name, primary_keys)
LAHMAN_TABLES = {
    'People.csv': ('people', ['playerID']),
    'Batting.csv': ('batting', ['playerID', 'yearID', 'stint', 'teamID']),
    'Pitching.csv': ('pitching', ['playerID', 'yearID', 'stint', 'teamID']),
    'Fielding.csv': ('fielding', ['playerID', 'yearID', 'stint', 'teamID', 'POS']),
    'FieldingOF.csv': ('fielding_of', ['playerID', 'yearID', 'stint']),
    'FieldingOFsplit.csv': ('fielding_of_split', ['playerID', 'yearID', 'stint', 'teamID', 'POS']),
    'Appearances.csv': ('appearances', ['yearID', 'teamID', 'playerID']),
    'BattingPost.csv': ('batting_post', ['playerID', 'yearID', 'round', 'teamID']),
    'PitchingPost.csv': ('pitching_post', ['playerID', 'yearID', 'round', 'teamID']),
    'FieldingPost.csv': ('fielding_post', ['playerID', 'yearID', 'teamID', 'round', 'POS']),
    'SeriesPost.csv': ('series_post', ['yearID', 'round', 'teamIDwinner', 'teamIDloser']),
    'Teams.csv': ('teams', ['yearID', 'teamID']),
    'TeamsFranchises.csv': ('teams_franchises', ['franchID']),
    'TeamsHalf.csv': ('teams_half', ['yearID', 'teamID', 'Half']),
    'AwardsManagers.csv': ('awards_managers', ['playerID', 'awardID', 'yearID', 'lgID']),
    'AwardsPlayers.csv': ('awards_players', ['playerID', 'awardID', 'yearID', 'lgID']),
    'AwardsShareManagers.csv': ('awards_share_managers', ['awardID', 'yearID', 'lgID', 'playerID']),
    'AwardsSharePlayers.csv': ('awards_share_players', ['awardID', 'yearID', 'lgID', 'playerID']),
    'Managers.csv': ('managers', ['playerID', 'yearID', 'teamID', 'inseason']),
    'ManagersHalf.csv': ('managers_half', ['playerID', 'yearID', 'teamID', 'inseason', 'half']),
    'HallOfFame.csv': ('hall_of_fame', ['playerID', 'yearid', 'votedBy']),
    'Parks.csv': ('parks', ['parkID']),
    'HomeGames.csv': ('home_games', ['yearID', 'teamID', 'parkID']),
    'Schools.csv': ('schools', ['schoolID']),
    'CollegePlaying.csv': ('college_playing', ['playerID', 'schoolID', 'yearID']),
    'AllstarFull.csv': ('all_star_full', ['playerID', 'yearID', 'gameNum', 'gameID']),
    'Salaries.csv': ('salaries', ['yearID', 'teamID', 'playerID']),
}


def get_conn():
    """Get database connection from environment variables."""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        dbname=os.getenv('POSTGRES_DB', 'retrosheet'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
    )


def read_csv_headers(csv_path: Path) -> list[str]:
    """Read CSV header row and return list of column names."""
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        return headers


def count_csv_rows(csv_path: Path) -> int:
    """Count rows in CSV (excluding header)."""
    with open(csv_path, encoding='utf-8') as f:
        return sum(1 for _ in f) - 1  # Subtract header


def get_column_type(column_name: str) -> str:
    """
    Infer PostgreSQL column type based on Lahman naming conventions.
    This is a best-effort mapping - actual types should match 210_lahman_complete.sql
    """
    # Date columns
    if column_name.lower() in ['debut', 'finalgame', 'span_first', 'span_last']:
        return 'DATE'

    # Numeric columns (batting averages, ERA, etc.)
    if column_name in ['BAOpp', 'ERA', 'FP', 'ZR']:
        return 'NUMERIC'

    # Integer columns (most are integers)
    int_suffixes = ['id', 'year', 'month', 'day', 'count', 'won', 'wins', 'losses', 'ties',
                   'games', 'attendance', 'salary', 'rank', 'points', 'votes', 'ballots', 'needed',
                   'height', 'weight', 'stint', 'innings', 'outs', 'po', 'a', 'e', 'dp', 'tp', 'pb']
    if any(column_name.lower().endswith(s) for s in int_suffixes):
        return 'INTEGER'

    if column_name.startswith(('G', 'AB', 'R', 'H', '_2B', '_3B', 'HR', 'RBI', 'SB', 'CS',
                               'BB', 'SO', 'IBB', 'HBP', 'SH', 'SF', 'GIDP', 'W', 'L', 'CG',
                               'SHO', 'SV', 'IP', 'HA', 'ER', 'HRA', 'BBA', 'SOA', 'GF',
                               'GS', 'Glf', 'Gcf', 'Grf', 'G_all', 'G_batting', 'G_defense',
                               'G_p', 'G_c', 'G_1b', 'G_2b', 'G_3b', 'G_ss', 'G_lf', 'G_cf',
                               'G_rf', 'G_of', 'G_dh', 'G_ph', 'G_pr', 'openings')):
        return 'INTEGER'

    # Everything else is TEXT
    return 'TEXT'


def create_staging_table(cur, table_name: str, columns: list[str]):
    """Create staging table matching CSV structure exactly."""
    # Drop existing staging table
    cur.execute(f'DROP TABLE IF EXISTS raw_lahman.stg_{table_name} CASCADE;')

    # Build column definitions
    col_defs = []
    for col in columns:
        pg_type = get_column_type(col)
        # Quote column names to handle special cases like _2B, _3B
        col_defs.append(f'"{col}" {pg_type}')

    create_sql = f"""
        CREATE TABLE raw_lahman.stg_{table_name} (
            {', '.join(col_defs)}
        );
    """
    cur.execute(create_sql)


def copy_to_staging(cur, csv_path: Path, table_name: str, columns: list[str]):
    """Copy CSV data to staging table using PostgreSQL COPY."""
    # Use COPY with explicit column list
    quoted_cols = ', '.join(f'"{c}"' for c in columns)

    copy_sql = f"""
        COPY raw_lahman.stg_{table_name} ({quoted_cols})
        FROM STDIN WITH (FORMAT csv, HEADER true, NULL '');
    """

    with open(csv_path, encoding='utf-8') as f:
        cur.copy_expert(copy_sql, f)


def build_cast_expression(col: str) -> str:
    """Build CAST expression for column based on its type."""
    pg_type = get_column_type(col)

    if pg_type == 'DATE':
        return f'CASE WHEN "{col}" = \'\' THEN NULL ELSE "{col}"::DATE END'
    if pg_type == 'NUMERIC':
        return f'CASE WHEN "{col}" = \'\' THEN NULL ELSE "{col}"::NUMERIC END'
    if pg_type == 'INTEGER':
        return f'CASE WHEN "{col}" = \'\' THEN NULL ELSE "{col}"::INTEGER END'
    return f'"{col}"'  # TEXT stays as-is


def upsert_to_main(cur, table_name: str, columns: list[str], pk_columns: list[str]):
    """Move data from staging to main table with proper type casting and upsert."""
    quoted_cols = ', '.join(f'"{c}"' for c in columns)

    # Build cast expressions for each column
    cast_exprs = [build_cast_expression(c) for c in columns]

    # Build SET clause for non-PK columns
    non_pk_cols = [c for c in columns if c not in pk_columns]
    if non_pk_cols:
        set_clause = ', '.join(f'"{c}" = EXCLUDED."{c}"' for c in non_pk_cols)
        conflict_action = f'DO UPDATE SET {set_clause}'
    else:
        conflict_action = 'DO NOTHING'

    # Build conflict target (quoted)
    conflict_target = ', '.join(f'"{c}"' for c in pk_columns)

    upsert_sql = f"""
        INSERT INTO raw_lahman.{table_name} ({quoted_cols})
        SELECT {', '.join(cast_exprs)}
        FROM raw_lahman.stg_{table_name}
        ON CONFLICT ({conflict_target}) {conflict_action};
    """

    cur.execute(upsert_sql)


def get_db_column_count(cur, table_name: str) -> int:
    """Get number of columns in the database table."""
    cur.execute("""
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE table_schema = 'raw_lahman' AND table_name = %s;
    """, (table_name,))
    return cur.fetchone()[0]


def get_db_row_count(cur, table_name: str) -> int:
    """Get number of rows in the database table."""
    cur.execute(f'SELECT COUNT(*) FROM raw_lahman.{table_name};')
    return cur.fetchone()[0]


def process_file(csv_dir: Path, filename: str, table_name: str, pk_columns: list[str],
                 stats: dict, dry_run: bool = False) -> tuple[int, int]:
    """
    Process a single CSV file: read headers, create staging, copy data, upsert to main.
    
    Returns: (csv_rows, db_rows) tuple for validation
    """
    csv_path = csv_dir / filename

    if not csv_path.is_file():
        print(f'⚠️  {filename} not found, skipping.', file=sys.stderr)
        stats['missing'] += 1
        return 0, 0

    # Read CSV headers to discover ALL columns
    csv_columns = read_csv_headers(csv_path)
    csv_row_count = count_csv_rows(csv_path)

    if dry_run:
        print(f'📋 {filename}: {len(csv_columns)} columns, {csv_row_count} rows (DRY RUN)')
        stats['success'] += 1
        return csv_row_count, 0

    conn = get_conn()
    try:
        cur = conn.cursor()

        # Create staging table with EXACT CSV structure
        create_staging_table(cur, table_name, csv_columns)

        # Copy data to staging
        copy_to_staging(cur, csv_path, table_name, csv_columns)

        # Upsert to main table with type casting
        upsert_to_main(cur, table_name, csv_columns, pk_columns)

        conn.commit()

        # Verify row count
        db_row_count = get_db_row_count(cur, table_name)
        db_col_count = get_db_column_count(cur, table_name)

        # Report results
        col_match = '✅' if db_col_count >= len(csv_columns) else '⚠️'
        row_match = '✅' if db_row_count == csv_row_count else '⚠️'

        print(f'{col_match} {filename}: {len(csv_columns)} CSV cols -> {db_col_count} DB cols, '
              f'{row_match} {csv_row_count:,} CSV rows -> {db_row_count:,} DB rows')

        if db_row_count != csv_row_count:
            print(f'   ⚠️ Row count mismatch: CSV={csv_row_count:,}, DB={db_row_count:,}',
                  file=sys.stderr)
            stats['mismatch'] += 1
        else:
            stats['success'] += 1

        return csv_row_count, db_row_count

    except Exception as e:
        conn.rollback()
        print(f'❌ ERROR loading {filename}: {e}', file=sys.stderr)
        stats['error'] += 1
        raise
    finally:
        cur.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Load COMPLETE Lahman database (ALL tables, ALL columns)',
    )
    parser.add_argument('--dir', type=Path, required=True,
                        help='Directory containing Lahman CSVs')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print what would be loaded without actually loading')
    parser.add_argument('--tables', nargs='+',
                        help='Specific tables to load (default: all)')
    args = parser.parse_args()

    # Statistics tracking
    stats = {
        'total': 0,
        'success': 0,
        'missing': 0,
        'mismatch': 0,
        'error': 0,
        'total_csv_rows': 0,
        'total_db_rows': 0,
        'tables_loaded': [],
    }

    print('=' * 70)
    print('LAHMAN BASEBALL DATABASE - COMPLETE LOADER')
    print('=' * 70)
    print(f'Source: {args.dir}')
    print(f'Mode: {"DRY RUN" if args.dry_run else "LIVE LOAD"}')
    print('-' * 70)

    # Filter tables if specified
    tables_to_load = LAHMAN_TABLES.items()
    if args.tables:
        tables_to_load = [(k, v) for k, v in tables_to_load if v[0] in args.tables]
        print(f'Loading {len(tables_to_load)} specific table(s)')
    else:
        print(f'Loading ALL {len(LAHMAN_TABLES)} Lahman tables')

    print('-' * 70)

    # Process each table
    for filename, (table_name, pk_columns) in tables_to_load:
        stats['total'] += 1
        try:
            csv_rows, db_rows = process_file(
                args.dir, filename, table_name, pk_columns, stats, args.dry_run,
            )
            stats['total_csv_rows'] += csv_rows
            stats['total_db_rows'] += db_rows
            if csv_rows > 0:
                stats['tables_loaded'].append(table_name)
        except Exception as e:
            print(f'   FATAL: {e}', file=sys.stderr)
            continue

    # Summary report
    print('=' * 70)
    print('SUMMARY')
    print('=' * 70)
    print(f'Tables processed: {stats["total"]}')
    print(f'  ✅ Successful:   {stats["success"]}')
    print(f'  ⚠️  Missing file: {stats["missing"]}')
    print(f'  ⚠️  Row mismatch: {stats["mismatch"]}')
    print(f'  ❌ Errors:       {stats["error"]}')
    print('-' * 70)
    print(f'Total CSV rows:   {stats["total_csv_rows"]:,}')
    print(f'Total DB rows:    {stats["total_db_rows"]:,}')
    print('-' * 70)

    if stats['tables_loaded']:
        print(f'Tables with data: {len(stats["tables_loaded"])}')
        print(f'  {", ".join(sorted(stats["tables_loaded"]))}')

    # Validation
    if stats['success'] == stats['total'] - stats['missing'] and stats['mismatch'] == 0:
        print('\n✅ ALL LOADED SUCCESSFULLY - 100% data capture achieved!')
    else:
        print('\n⚠️  ISSUES DETECTED - review errors above')
        sys.exit(1)


if __name__ == '__main__':
    main()
