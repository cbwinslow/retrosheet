#!/usr/bin/env python3
"""
Bulk download MLB schedules for historical data collection.
Downloads schedules from start_date to end_date with rate limiting and deduplication.
"""

import argparse
import json
import time
import urllib.request
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import Json


def database_kwargs():
    """Database connection parameters."""
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "retrosheet"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }


def download_schedule_for_date(date_str: str) -> dict:
    """Download MLB schedule for a specific date."""
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}"

    try:
        start_time = time.time()
        with urllib.request.urlopen(url, timeout=30) as response:
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)

            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return {
                    "success": True,
                    "data": data,
                    "http_status": response.status,
                    "response_time_ms": response_time_ms,
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status}",
                    "http_status": response.status,
                    "response_time_ms": response_time_ms,
                }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "http_status": None,
            "response_time_ms": None,
        }


def store_schedule_snapshot(date_str: str, result: dict):
    """Store schedule snapshot in database."""
    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO raw_mlb.schedule_snapshots
                (snapshot_date, fetched_at, endpoint, payload, request_params,
                 http_status, response_time_ms, error_text)
                VALUES (%s, now(), %s, %s, %s, %s, %s, %s)
                ON CONFLICT (snapshot_date, fetched_at) DO NOTHING
            """,
                (
                    date_str,
                    f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}",
                    Json(result.get("data", {})) if result.get("success") else Json({}),
                    Json({"sportId": 1, "date": date_str}),
                    result.get("http_status"),
                    result.get("response_time_ms"),
                    result.get("error") if not result.get("success") else None,
                ),
            )

        conn.commit()

    finally:
        conn.close()


def get_date_range(start_date: str, end_date: str):
    """Generate list of dates to process."""
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    current = start

    dates = []
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return dates


def get_existing_dates():
    """Get dates we already have schedule data for."""
    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT snapshot_date
                FROM raw_mlb.schedule_snapshots
                WHERE http_status = 200
            """)
            return {row[0] for row in cur.fetchall()}

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Bulk download MLB schedules")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip dates we already have data for",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded")
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    print(f"🔄 MLB Schedule Bulk Download: {args.start_date} to {args.end_date}")

    # Get date range
    dates_to_process = get_date_range(args.start_date, args.end_date)

    # Filter out existing dates if requested
    if args.skip_existing:
        existing_dates = get_existing_dates()
        dates_to_process = [d for d in dates_to_process if d not in existing_dates]
        print(
            f"📊 Found {len(existing_dates)} existing dates, processing {len(dates_to_process)} new dates"
        )

    if not dates_to_process:
        print("✅ All dates already processed!")
        return

    if args.dry_run:
        print("📋 Would download schedules for:")
        for i, date in enumerate(dates_to_process[:10]):
            print(f"   {i + 1:3d}. {date}")
        if len(dates_to_process) > 10:
            print(f"   ... and {len(dates_to_process) - 10} more")
        return

    # Download schedules
    successful = 0
    failed = 0

    for i, date_str in enumerate(dates_to_process):
        print(f"📥 [{i + 1:4d}/{len(dates_to_process)}] Downloading {date_str}...")

        result = download_schedule_for_date(date_str)

        if result["success"]:
            store_schedule_snapshot(date_str, result)
            successful += 1
            status = "✅"
        else:
            failed += 1
            status = "❌"

        print(
            f"   {status} {date_str}: {result.get('http_status', 'ERROR')} "
            f"({result.get('response_time_ms', 0)}ms)"
        )

        # Rate limiting
        if i < len(dates_to_process) - 1:  # Don't delay on last request
            time.sleep(args.delay)

    print("\n🎯 Download Complete:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📊 Total processed: {len(dates_to_process)}")
    print(".1f")


if __name__ == "__main__":
    import os

    main()
