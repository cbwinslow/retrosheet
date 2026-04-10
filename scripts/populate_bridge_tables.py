#!/usr/bin/env python3
"""
Populate bridge tables with player ID mappings from Chadwick Bureau Register.

This script downloads the latest Chadwick Bureau Register data and populates
the bridge.player_xref table with mappings between MLB, Retrosheet, and other
player ID systems.
"""

from __future__ import annotations

import csv
import gzip
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, List

import psycopg2


ROOT = Path(__file__).resolve().parents[1]


def database_kwargs() -> dict[str, str]:
    return {
        "host": "localhost",
        "port": "5432",
        "dbname": "retrosheet",
        "user": "postgres",
        "password": "",
    }


def download_chadwick_register() -> List[Path]:
    """Download all Chadwick Bureau Register data files."""
    base_url = (
        "https://github.com/chadwickbureau/register/raw/master/data/people-{}.csv"
    )
    temp_dir = Path(tempfile.mkdtemp())
    files = []

    print("Downloading Chadwick Bureau Register files...")
    for suffix in "0123456789abcdef":
        url = base_url.format(suffix)
        local_file = temp_dir / f"chadwick_register_{suffix}.csv"

        try:
            urllib.request.urlretrieve(url, local_file)
            files.append(local_file)
            print(f"Downloaded people-{suffix}.csv")
        except Exception as e:
            print(f"Failed to download people-{suffix}.csv: {e}")
            break

    return files


def parse_chadwick_csv(file_paths: List[Path]) -> List[Dict[str, str]]:
    """Parse Chadwick CSV files into records."""
    records = []
    for file_path in file_paths:
        print(f"Parsing {file_path.name}...")
        with file_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
    return records


def insert_player_mappings(conn, records: List[Dict[str, str]]) -> None:
    """Insert player ID mappings into bridge.player_xref table."""
    with conn.cursor() as cur:
        # Clear existing data
        cur.execute("TRUNCATE TABLE bridge.player_xref RESTART IDENTITY")

        inserted = 0
        for record in records:
            # Only insert records that have at least MLBAM or Retrosheet IDs
            mlb_id = record.get("key_mlbam")
            retro_id = record.get("key_retro")

            if not mlb_id and not retro_id:
                continue

            # Prepare data
            data = {
                "retrosheet_id": retro_id or None,
                "mlb_id": int(mlb_id) if mlb_id else None,
                "baseball_reference_id": record.get("key_bbref") or None,
                "name_first": record.get("name_first") or None,
                "name_last": record.get("name_last") or None,
            }

            # Insert record
            cur.execute(
                """
                INSERT INTO bridge.player_xref (
                    retrosheet_id, mlb_id, baseball_reference_id,
                    name_first, name_last
                ) VALUES (%s, %s, %s, %s, %s)
            """,
                (
                    data["retrosheet_id"],
                    data["mlb_id"],
                    data["baseball_reference_id"],
                    data["name_first"],
                    data["name_last"],
                ),
            )

            inserted += 1
            if inserted % 10000 == 0:
                print(f"Inserted {inserted} player mappings...")

        conn.commit()
        print(f"Total player mappings inserted: {inserted}")


def populate_bridge_tables() -> None:
    """Main function to populate bridge tables."""
    try:
        # Download data
        data_files = download_chadwick_register()
        print(f"Downloaded {len(data_files)} Chadwick Register files")

        # Parse data
        records = parse_chadwick_csv(data_files)
        print(f"Parsed {len(records)} total records from Chadwick Register")

        # Connect to database and insert
        conn = psycopg2.connect(**database_kwargs())
        try:
            insert_player_mappings(conn, records)
            print("Bridge table population complete!")
        finally:
            conn.close()

        # Cleanup
        for data_file in data_files:
            data_file.unlink()
        data_files[0].parent.rmdir()

    except Exception as e:
        print(f"Error populating bridge tables: {e}")
        raise


if __name__ == "__main__":
    populate_bridge_tables()
