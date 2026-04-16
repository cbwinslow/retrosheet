#!/usr/bin/env python3
"""
Loader for the public Statcast park‑factors CSV.

Usage:
    python scripts/external_data/load_park_factors.py --file park_factors.csv
"""

import argparse
import csv
import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/retrosheet")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def main():
    parser = argparse.ArgumentParser(description="Load Statcast park factors")
    parser.add_argument("--file", type=Path, required=True,
                        help="CSV file downloaded from Baseball‑Savant")
    args = parser.parse_args()

    with args.file.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append((
                int(row.get("season") or 0),
                row.get("park_id"),
                row.get("park_name"),
                float(row.get("runs_factor") or 0),
                float(row.get("home_runs_factor") or 0),
                float(row.get("slugging_factor") or 0)
            ))

    sql = """
        INSERT INTO raw_park_factors.factors (
            season, park_id, park_name, runs_factor,
            home_runs_factor, slugging_factor
        ) VALUES %s
        ON CONFLICT (season, park_id) DO UPDATE
        SET
            park_name = EXCLUDED.park_name,
            runs_factor = EXCLUDED.runs_factor,
            home_runs_factor = EXCLUDED.home_runs_factor,
            slugging_factor = EXCLUDED.slugging_factor;
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows, page_size=500)
        conn.commit()
        print(f"✅ Loaded {len(rows)} park‑factor rows")
    finally:
        conn.close()

if __name__ == "__main__":
    main()