#!/usr/bin/env python3
"""
Export EDA views to pandas DataFrames or CSV for R/Spig.

Usage:
    python scripts/eda/export_view.py --view eda.handedness_matchup_outcomes
    python scripts/eda/export_view.py --view eda.era_comparison --csv
"""

import argparse
import os

import pandas as pd
import psycopg2


def get_connection():
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=int(os.getenv('PGPORT', 5432)),
        database=os.getenv('PGDATABASE', 'retrosheet'),
        user=os.getenv('PGUSER', os.getenv('USER')),
    )


VIEWS = {
    'eda.handedness_matchup_outcomes': 'Handedness matchup outcomes',
    'eda.era_comparison': 'Steroid era comparison',
    'eda.park_totals': 'Park run factors',
    'eda.home_field_by_team': 'Home field advantage by team',
    'eda.season_summary': 'Season summary stats',
    'eda.pitcher_batter_matchup': 'Pitcher vs batter outcomes',
    'eda.runner_context_outcomes': 'Runner context outcomes',
    'eda.pa_outcomes_by_season': 'PA outcomes by season',
    'eda.count_state_outcomes': 'Count state outcomes',
}


def main():
    parser = argparse.ArgumentParser(description='Export EDA views')
    parser.add_argument('--view', choices=list(VIEWS.keys()), required=True)
    parser.add_argument('--csv', action='store_true', help='Export to CSV')
    parser.add_argument('--limit', type=int, help='Limit rows')
    args = parser.parse_args()

    conn = get_connection()
    query = f'SELECT * FROM {args.view}'
    if args.limit:
        query += f' LIMIT {args.limit}'

    df = pd.read_sql(query, conn)
    conn.close()

    print(f'# {VIEWS[args.view]}')
    print(f'# Rows: {len(df)}, Columns: {len(df.columns)}')
    print(f'# Columns: {list(df.columns)}')

    if args.csv:
        output_file = args.view.replace('.', '_') + '.csv'
        df.to_csv(output_file, index=False)
        print(f'# Saved to: {output_file}')
    else:
        # Print as simple table
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(df.head(20).to_string())


if __name__ == '__main__':
    main()
