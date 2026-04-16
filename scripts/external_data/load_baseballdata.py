#!/usr/bin/env python3
"""
Loader for Baseball‑Data.com play‑by‑play CSV files.

The CSV format from Baseball‑Data.com is fairly flat; this script maps the
columns to the `raw_external.baseball_data_com` table defined in
`sql/200_external_data.sql`.  It also populates the bridge table
`bridge.external_player_xref` so that downstream joins can resolve player IDs
to the canonical Retrosheet IDs.

Usage:
    python scripts/external_data/load_baseballdata.py --file path/to/pbp_2024.csv
"""

import argparse
import csv
import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/retrosheet")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def load_pbp(csv_path: Path):
    if not csv_path.is_file():
        print(f"❌ CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        player_links = set()
        for row in reader:
            event_id = int(row.get("event_id") or 0)
            rows.append((
                event_id,
                int(row.get("game_id") or 0),
                int(row.get("inning") or 0),
                row.get("half") or None,
                int(row.get("batter_id") or 0),
                int(row.get("pitcher_id") or 0),
                row.get("event_type") or None,
                row.get("description") or None,
            ))
            # collect player mapping candidates
            player_links.add((
                "baseball_data_com",
                int(row.get("batter_id") or 0),
                None  # retrosheet ID unknown at load time
            ))
            player_links.add((
                "baseball_data_com",
                int(row.get("pitcher_id") or 0),
                None
            ))

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Insert raw play‑by‑play rows
            sql_pbp = """
                INSERT INTO raw_external.baseball_data_com (
                    event_id, game_id, inning, half,
                    batter_id, pitcher_id, event_type, description
                ) VALUES %s
                ON CONFLICT (event_id) DO UPDATE
                SET
                    game_id = EXCLUDED.game_id,
                    inning  = EXCLUDED.inning,
                    half    = EXCLUDED.half,
                    batter_id = EXCLUDED.batter_id,
                    pitcher_id = EXCLUDED.pitcher_id,
                    event_type = EXCLUDED.event_type,
                    description = EXCLUDED.description;
            """
            execute_values(cur, sql_pbp, rows, page_size=1000)

            # Populate bridge table with placeholder mappings (to be filled later)
            sql_bridge = """
                INSERT INTO bridge.external_player_xref (external_source, external_player_id, retrosheet_player_id)
                VALUES %s
                ON CONFLICT (external_source, external_player_id) DO NOTHING;
            """
            execute_values(cur, sql_bridge, list(player_links), page_size=500)

        conn.commit()
        print(f"✅ Loaded {len(rows)} Baseball‑Data.com rows and {len(player_links)} player placeholders.")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Load Baseball‑Data.com PBP CSV")
    parser.add_argument("--file", type=Path, required=True, help="Path to the CSV file")
    args = parser.parse_args()
    load_pbp(args.file)


if __name__ == "__main__":
    main()