#!/usr/bin/env python3
"""
Load a Statcast CSV file (full season) into raw_statcast.events.

Because a full‑season Statcast file can be > 1 GB, the script supports
optional chunked loading. If the file size exceeds 500 MB, it is split
into 5 M‑row chunks before being copied.

The loader uses a staging table (all TEXT) and then upserts into the
final `raw_statcast.events` table with proper numeric casts.

Usage:
    python scripts/external_data/load_statcast.py --file /path/to/statcast.csv
"""

import argparse
import os
import sys
import math
from pathlib import Path
import subprocess

import psycopg2

DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/retrosheet")
CHUNK_ROWS = 5_000_000  # rows per chunk for very large files

def get_conn():
    return psycopg2.connect(DB_URL)

def create_staging(cur):
    cur.execute("DROP TABLE IF EXISTS raw_statcast.stg_events")
    cur.execute("""
        CREATE TABLE raw_statcast.stg_events (
            game_pk TEXT,
            at_bat_number TEXT,
            pitch_number TEXT,
            pitcher TEXT,
            batter TEXT,
            release_speed TEXT,
            release_spin_rate TEXT,
            launch_angle TEXT,
            launch_speed TEXT,
            hit_distance_sc TEXT,
            events TEXT,
            pitch_type TEXT
        )
    """)

def copy_to_staging(cur, csv_path):
    with open(csv_path, "r", newline="") as f:
        cur.copy_expert(
            "COPY raw_statcast.stg_events FROM STDIN WITH CSV HEADER", f
        )

def upsert(cur):
    cur.execute("""
        INSERT INTO raw_statcast.events (
            game_pk, at_bat_number, pitch_number,
            pitcher_mlb_id, batter_mlb_id,
            release_speed, release_spin_rate,
            launch_angle, launch_speed,
            hit_distance, events, pitch_type
        )
        SELECT
            NULLIF(game_pk, '')::BIGINT,
            NULLIF(at_bat_number, '')::INT,
            NULLIF(pitch_number, '')::INT,
            NULLIF(pitcher, '')::INT,
            NULLIF(batter, '')::INT,
            NULLIF(release_speed, '')::REAL,
            NULLIF(release_spin_rate, '')::REAL,
            NULLIF(launch_angle, '')::REAL,
            NULLIF(launch_speed, '')::REAL,
            NULLIF(hit_distance_sc, '')::REAL,
            NULLIF(events, '')::TEXT,
            NULLIF(pitch_type, '')::TEXT
        FROM raw_statcast.stg_events
        ON CONFLICT (game_pk, at_bat_number, pitch_number) DO UPDATE SET
            pitcher_mlb_id = EXCLUDED.pitcher_mlb_id,
            batter_mlb_id  = EXCLUDED.batter_mlb_id,
            release_speed  = EXCLUDED.release_speed,
            release_spin_rate = EXCLUDED.release_spin_rate,
            launch_angle   = EXCLUDED.launch_angle,
            launch_speed   = EXCLUDED.launch_speed,
            hit_distance   = EXCLUDED.hit_distance,
            events         = EXCLUDED.events,
            pitch_type     = EXCLUDED.pitch_type;
    """)

def split_file(csv_path: Path):
    """Split a large CSV into smaller files with a header line preserved."""
    prefix = f"{csv_path}_part_"
    # Use GNU split – keep header in each part
    subprocess.run(
        f"head -n 1 {csv_path} > {prefix}header && tail -n +2 {csv_path} | split -l {CHUNK_ROWS} - {prefix}",
        shell=True,
        check=True,
    )
    parts = sorted(Path(".").glob(f"{prefix}*"))
    for part in parts:
        with open(part, "r") as src, open(part, "w") as dst:
            header = open(f"{prefix}header").read()
            dst.write(header)
            dst.write(src.read())
    os.remove(f"{prefix}header")
    return parts

def main():
    parser = argparse.ArgumentParser(description="Load Statcast CSV")
    parser.add_argument("--file", type=Path, required=True, help="Statcast CSV file")
    args = parser.parse_args()

    if not args.file.is_file():
        print(f"❌ File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    # If file > 500 MB, split into chunks
    if args.file.stat().st_size > 500 * 1024 * 1024:
        print("⚠️  Large Statcast file detected – splitting into chunks...")
        parts = split_file(args.file)
    else:
        parts = [args.file]

    conn = get_conn()
    try:
        cur = conn.cursor()
        for part in parts:
            create_staging(cur)
            copy_to_staging(cur, part)
            upsert(cur)
            conn.commit()
            print(f"✅ Loaded chunk {part.name}")
        print(f"✅ Completed Statcast load ({len(parts)} chunk(s))")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()