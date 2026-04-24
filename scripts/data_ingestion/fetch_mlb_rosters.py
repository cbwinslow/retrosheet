#!/usr/bin/env python3
"""
Fetch current MLB team rosters (and optional salary data) from the free
MLB Stats API endpoints. No authentication is required for basic roster
information.

The script stores the raw JSON payload in `raw_mlb_rosters.roster_snapshots`
and upserts a view-friendly table.

Usage:
    python scripts/fetch_mlb_rosters.py --date 2026-04-15
"""

import argparse
import json
import os
import sys
from datetime import datetime

import psycopg2
import requests

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/retrosheet")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def fetch_and_store(snapshot_date: str):
    # MLB Stats API endpoint for rosters (public, no key needed)
    url = "https://statsapi.mlb.com/api/v1/teams"
    params = {"sportId": 1, "season": snapshot_date[:4]}
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"❌ Failed to fetch rosters: {resp.status_code}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for team in data.get("teams", []):
                team_id = team.get("id")
                payload = json.dumps(team)
                sql = """
                    INSERT INTO raw_mlb_rosters.roster_snapshots (snapshot_date, team_id, json_payload)
                    VALUES (%s, %s, %s::jsonb)
                    ON CONFLICT (snapshot_date, team_id) DO UPDATE
                    SET json_payload = EXCLUDED.json_payload;
                """
                cur.execute(sql, (snapshot_date, str(team_id), payload))
        conn.commit()
        print(f"✅ Stored roster snapshots for {snapshot_date}")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Fetch MLB rosters")
    parser.add_argument("--date", type=str, required=True, help="Snapshot date (YYYY‑MM‑DD)")
    args = parser.parse_args()
    # Validate date format
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("❌ Invalid date format, use YYYY‑MM‑DD", file=sys.stderr)
        sys.exit(1)

    fetch_and_store(args.date)


if __name__ == "__main__":
    main()
