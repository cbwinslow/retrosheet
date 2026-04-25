#!/usr/bin/env python3
"""
Chadwick Bureau Register Ingestion Script

Downloads and ingests the Chadwick Bureau Register data into the database.
This is the authoritative source for baseball player ID crosswalks.

Data Source: https://github.com/chadwickbureau/register
Files: people-{0-9,a-f}.csv (16 files)

Usage:
    python3 scripts/bridge/ingest_chadwick_register.py
    python3 scripts/bridge/ingest_chadwick_register.py --dry-run
    python3 scripts/bridge/ingest_chadwick_register.py --suffixes a b c

Author: Agent Cascade
Date: 2026-04-24
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import execute_values

# Add parent directories to path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def get_db_connection() -> psycopg2.extensions.connection:
    """Get PostgreSQL connection from environment variables."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        database=os.getenv("PGDATABASE", "retrosheet"),
        user=os.getenv("PGUSER", os.getenv("USER", "postgres")),
        password=os.getenv("PGPASSWORD", ""),
    )


def download_chadwick_files(
    suffixes: list[str] | None = None, temp_dir: Path | None = None
) -> list[Path]:
    """
    Download Chadwick Bureau Register CSV files.
    
    Args:
        suffixes: List of file suffixes to download (0-9, a-f). If None, downloads all.
        temp_dir: Directory to save files. If None, creates temp directory.
        
    Returns:
        List of paths to downloaded files
    """
    base_url = "https://github.com/chadwickbureau/register/raw/master/data/people-{}.csv"
    
    if temp_dir is None:
        temp_dir = Path(tempfile.mkdtemp(prefix="chadwick_"))
    
    if suffixes is None:
        suffixes = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", 
                    "a", "b", "c", "d", "e", "f"]
    
    downloaded: list[Path] = []
    
    print(f"Downloading {len(suffixes)} Chadwick Register files...")
    print(f"Destination: {temp_dir}")
    
    for suffix in suffixes:
        url = base_url.format(suffix)
        local_file = temp_dir / f"chadwick_register_{suffix}.csv"
        
        try:
            print(f"  Downloading people-{suffix}.csv...", end=" ")
            urllib.request.urlretrieve(url, local_file)
            file_size = local_file.stat().st_size
            print(f"✓ ({file_size:,} bytes)")
            downloaded.append(local_file)
        except Exception as e:
            print(f"✗ Failed: {e}")
    
    print(f"\nSuccessfully downloaded {len(downloaded)} files")
    return downloaded


def parse_chadwick_record(row: dict[str, str]) -> dict[str, Any]:
    """
    Parse a Chadwick CSV row into a typed record dictionary.
    
    Args:
        row: CSV row from DictReader
        
    Returns:
        Dictionary with properly typed values
    """
    def parse_int(value: str | None) -> int | None:
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None
    
    def parse_date(value: str | None) -> str | None:
        if not value or value == "":
            return None
        return value
    
    return {
        "key_uuid": row.get("key_uuid"),
        "key_mlbam": row.get("key_mlbam"),
        "key_retro": row.get("key_retro"),
        "key_bbref": row.get("key_bbref"),
        "key_fangraphs": row.get("key_fangraphs"),
        "key_baseball_prospectus": row.get("key_baseball_prospectus"),
        "key_cbs": row.get("key_cbs"),
        "key_espn": row.get("key_espn"),
        "key_fanduel": row.get("key_fanduel"),
        "key_draftkings": row.get("key_draftkings"),
        "key_yahoo": row.get("key_yahoo"),
        "key_nfbc": row.get("key_nfbc"),
        "key_rotowire": row.get("key_rotowire"),
        "key_rotoworld": row.get("key_rotoworld"),
        "key_kffl": row.get("key_kffl"),
        "name_first": row.get("name_first"),
        "name_last": row.get("name_last"),
        "name_full": row.get("name_full"),
        "name_given": row.get("name_given"),
        "name_matrilineal": row.get("name_matrilineal"),
        "bats": row.get("bats"),
        "throws": row.get("throws"),
        "birth_year": parse_int(row.get("birth_year")),
        "birth_month": parse_int(row.get("birth_month")),
        "birth_day": parse_int(row.get("birth_day")),
        "death_year": parse_int(row.get("death_year")),
        "death_month": parse_int(row.get("death_month")),
        "death_day": parse_int(row.get("death_day")),
        "birth_city": row.get("birth_city"),
        "birth_state": row.get("birth_state"),
        "birth_country": row.get("birth_country"),
        "death_city": row.get("death_city"),
        "death_state": row.get("death_state"),
        "death_country": row.get("death_country"),
        "weight": parse_int(row.get("weight")),
        "height": parse_int(row.get("height")),
        "debut": parse_date(row.get("debut")),
        "final_game": parse_date(row.get("final_game")),
        "mlb_played_first": parse_int(row.get("mlb_played_first")),
        "mlb_played_last": parse_int(row.get("mlb_played_last")),
        "retro_played_first": parse_int(row.get("retro_played_first")),
        "retro_played_last": parse_int(row.get("retro_played_last")),
        "college": row.get("college"),
        "college_id": parse_int(row.get("college_id")),
        "high_school": row.get("high_school"),
        "high_school_id": parse_int(row.get("high_school_id")),
        "bats_throws_source": row.get("bats_throws_source"),
        "birth_source": row.get("birth_source"),
        "death_source": row.get("death_source"),
        "weight_height_source": row.get("weight_height_source"),
        "debut_source": row.get("debut_source"),
        "mlb_organization": row.get("mlb_organization"),
        "mlb_position": row.get("mlb_position"),
        "twitter_id": row.get("twitter_id"),
        "wikipedia_id": row.get("wikipedia_id"),
        "gelb_id": row.get("gelb_id"),
        "lahman_id": row.get("lahman_id"),
    }


def load_to_staging(
    conn: psycopg2.extensions.connection,
    file_paths: list[Path],
    dry_run: bool = False,
) -> int:
    """
    Load Chadwick CSV files into staging table.
    
    Args:
        conn: Database connection
        file_paths: List of CSV file paths
        dry_run: If True, don't actually insert into database
        
    Returns:
        Number of records processed
    """
    total_records = 0
    
    # Clear staging table (if not dry run)
    if not dry_run:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE bridge._staging_chadwick_register")
            conn.commit()
        print("Cleared staging table")
    
    # Process each file
    for file_path in file_paths:
        print(f"\nProcessing {file_path.name}...")
        records: list[tuple] = []
        
        with file_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                record = parse_chadwick_record(row)
                
                # Create tuple for insertion
                # Order must match the table columns
                records.append((
                    record["key_uuid"],
                    record["key_mlbam"],
                    record["key_retro"],
                    record["key_bbref"],
                    record["key_fangraphs"],
                    record["key_baseball_prospectus"],
                    record["key_cbs"],
                    record["key_espn"],
                    record["key_fanduel"],
                    record["key_draftkings"],
                    record["key_yahoo"],
                    record["key_nfbc"],
                    record["key_rotowire"],
                    record["key_rotoworld"],
                    record["key_kffl"],
                    record["name_first"],
                    record["name_last"],
                    record["name_full"],
                    record["name_given"],
                    record["name_matrilineal"],
                    record["bats"],
                    record["throws"],
                    record["birth_year"],
                    record["birth_month"],
                    record["birth_day"],
                    record["death_year"],
                    record["death_month"],
                    record["death_day"],
                    record["birth_city"],
                    record["birth_state"],
                    record["birth_country"],
                    record["death_city"],
                    record["death_state"],
                    record["death_country"],
                    record["weight"],
                    record["height"],
                    record["debut"],
                    record["final_game"],
                    record["mlb_played_first"],
                    record["mlb_played_last"],
                    record["retro_played_first"],
                    record["retro_played_last"],
                    record["college"],
                    record["college_id"],
                    record["high_school"],
                    record["high_school_id"],
                    record["bats_throws_source"],
                    record["birth_source"],
                    record["death_source"],
                    record["weight_height_source"],
                    record["debut_source"],
                    record["mlb_organization"],
                    record["mlb_position"],
                    record["twitter_id"],
                    record["wikipedia_id"],
                    record["gelb_id"],
                    record["lahman_id"],
                ))
        
        file_count = len(records)
        total_records += file_count
        print(f"  Parsed {file_count:,} records")
        
        if not dry_run and records:
            # Batch insert
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    INSERT INTO bridge._staging_chadwick_register (
                        key_uuid, key_mlbam, key_retro, key_bbref, key_fangraphs,
                        key_baseball_prospectus, key_cbs, key_espn, key_fanduel,
                        key_draftkings, key_yahoo, key_nfbc, key_rotowire, key_rotoworld,
                        key_kffl, name_first, name_last, name_full, name_given, name_matrilineal,
                        bats, throws, birth_year, birth_month, birth_day, death_year, death_month,
                        death_day, birth_city, birth_state, birth_country, death_city, death_state,
                        death_country, weight, height, debut, final_game, mlb_played_first,
                        mlb_played_last, retro_played_first, retro_played_last, college, college_id,
                        high_school, high_school_id, bats_throws_source, birth_source, death_source,
                        weight_height_source, debut_source, mlb_organization, mlb_position,
                        twitter_id, wikipedia_id, gelb_id, lahman_id, source_timestamp
                    ) VALUES %s
                    ON CONFLICT (key_uuid) DO UPDATE SET
                        key_mlbam = EXCLUDED.key_mlbam,
                        key_retro = EXCLUDED.key_retro,
                        key_bbref = EXCLUDED.key_bbref,
                        updated_at = NOW()
                    """,
                    records,
                    page_size=1000,
                )
                conn.commit()
            print(f"  Inserted {file_count:,} records to staging")
    
    return total_records


def run_upsert_to_player_xref(
    conn: psycopg2.extensions.connection, dry_run: bool = False
) -> dict[str, int]:
    """
    Run the upsert procedure to merge staging data into player_xref.
    
    Args:
        conn: Database connection
        dry_run: If True, don't actually execute
        
    Returns:
        Dictionary with statistics
    """
    if dry_run:
        print("\n[DRY RUN] Would execute: CALL bridge.upsert_chadwick_to_player_xref()")
        return {"inserted": 0, "updated": 0}
    
    print("\nExecuting upsert to bridge.player_xref...")
    
    with conn.cursor() as cur:
        cur.execute("CALL bridge.upsert_chadwick_to_player_xref()")
        conn.commit()
    
    # Get statistics
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM bridge.player_xref")
    total_bridge = cur.fetchone()[0]
    
    return {
        "total_in_bridge": total_bridge,
        "message": "Upsert complete. Check PostgreSQL NOTICE messages for details.",
    }


def run_validation_tests(conn: psycopg2.extensions.connection) -> dict[str, Any]:
    """
    Run all bridge validation tests.
    
    Args:
        conn: Database connection
        
    Returns:
        Dictionary with test results
    """
    print("\n" + "=" * 70)
    print("RUNNING BRIDGE VALIDATION TESTS")
    print("=" * 70)
    
    results = {
        "tests": [],
        "passed": 0,
        "failed": 0,
        "total": 0,
    }
    
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM bridge.run_all_bridge_tests()")
        rows = cur.fetchall()
        
        for row in rows:
            test_name, passed, actual, expected, details = row
            results["tests"].append({
                "name": test_name,
                "passed": passed,
                "actual": actual,
                "expected": expected,
                "details": details,
            })
            results["total"] += 1
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
            
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"\n{status}: {test_name}")
            print(f"  Expected: {expected}")
            print(f"  Actual:   {actual}")
            print(f"  Details:  {details}")
    
    # Get summary
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM bridge.get_bridge_test_summary()")
        summary = cur.fetchone()
        if summary:
            results["summary"] = {
                "total_tests": summary[0],
                "passed_tests": summary[1],
                "failed_tests": summary[2],
                "pass_rate": float(summary[3]),
                "status": summary[4],
            }
    
    print("\n" + "=" * 70)
    print(f"TEST SUMMARY: {results['passed']}/{results['total']} passed ({results['summary']['pass_rate']:.1f}%)")
    print(f"STATUS: {results['summary']['status']}")
    print("=" * 70)
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Ingest Chadwick Bureau Register data into bridge tables"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse files but don't write to database",
    )
    parser.add_argument(
        "--suffixes",
        nargs="+
        help="Specific file suffixes to download (0-9, a-f). Default: all",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download, assume files exist in temp directory",
    )
    parser.add_argument(
        "--temp-dir",
        type=Path,
        help="Directory for downloaded files",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only run validation tests, skip ingestion",
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("CHADWICK BUREAU REGISTER INGESTION")
    print("=" * 70)
    print(f"Date: 2026-04-24")
    print(f"Source: https://github.com/chadwickbureau/register")
    print(f"Target: bridge.player_xref")
    if args.dry_run:
        print("MODE: DRY RUN (no database changes)")
    print("=" * 70)
    
    # Get database connection
    conn = get_db_connection()
    print(f"\nConnected to database: {conn.get_dsn_parameters()['dbname']}")
    
    try:
        # Validation only mode
        if args.validate_only:
            results = run_validation_tests(conn)
            return 0 if results["failed"] == 0 else 1
        
        # Step 1: Download files
        if not args.skip_download:
            downloaded_files = download_chadwick_files(
                suffixes=args.suffixes, temp_dir=args.temp_dir
            )
        else:
            temp_dir = args.temp_dir or Path(tempfile.gettempdir())
            downloaded_files = list(temp_dir.glob("chadwick_register_*.csv"))
            print(f"\nUsing existing files: {len(downloaded_files)} found")
        
        if not downloaded_files:
            print("ERROR: No files to process")
            return 1
        
        # Step 2: Load to staging
        total_records = load_to_staging(conn, downloaded_files, dry_run=args.dry_run)
        print(f"\nTotal records processed: {total_records:,}")
        
        # Step 3: Upsert to player_xref
        if not args.dry_run:
            upsert_stats = run_upsert_to_player_xref(conn, dry_run=args.dry_run)
            print(f"\nUpsert statistics:")
            for key, value in upsert_stats.items():
                print(f"  {key}: {value}")
        
        # Step 4: Run validation
        if not args.dry_run:
            results = run_validation_tests(conn)
            
            # Final status
            print("\n" + "=" * 70)
            if results["failed"] == 0:
                print("✓ ALL VALIDATION TESTS PASSED")
                return 0
            else:
                print(f"✗ {results['failed']} VALIDATION TESTS FAILED")
                return 1
        else:
            print("\n[DRY RUN COMPLETE - No database changes made]")
            return 0
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()
        print("\nDatabase connection closed")


if __name__ == "__main__":
    sys.exit(main())
