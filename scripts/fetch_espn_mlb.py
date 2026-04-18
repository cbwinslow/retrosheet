#!/usr/bin/env python3
"""
ESPN MLB Data Fetcher
Fetches MLB data from ESPN API and stores source-preserved JSON snapshots.

Usage:
    python3 scripts/fetch_espn_mlb.py --schedule --date 2024-04-15
    python3 scripts/fetch_espn_mlb.py --game --game-id 401434845
    python3 scripts/fetch_espn_mlb.py --player-stats --player-id 40539 --season 2024
    python3 scripts/fetch_espn_mlb.py --team-stats --team-id 16 --season 2024

Data Flow:
    ESPN API -> raw_espn.*_snapshots (source-preserved JSON)
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import requests
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ESPN API Endpoints
ESPN_BASE_URL = "http://site.api.espn.com/apis/site/v2/sports/baseball/mlb"
ENDPOINTS = {
    "scoreboard": f"{ESPN_BASE_URL}/scoreboard",
    "schedule": f"{ESPN_BASE_URL}/schedule",
    "game": f"{ESPN_BASE_URL}/scoreboard",
}


def get_db_connection():
    """Get PostgreSQL connection from environment variables."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)
    else:
        return psycopg2.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=os.getenv("PGPORT", "5432"),
            database=os.getenv("PGDATABASE", "retrosheet"),
            user=os.getenv("PGUSER", os.getenv("USER")),
            password=os.getenv("PGPASSWORD"),
        )


def get_git_commit():
    """Get current git commit hash."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def start_run(source_name: str, script_name: str, command_args: dict) -> int:
    """Start a new ingest run and return run_id."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            git_commit = get_git_commit()
            cur.execute("""
                SELECT raw_retrosheet.start_ingest_run(
                    %s, NULL, %s, NULL, %s, %s
                )
            """, (source_name, script_name, git_commit, json.dumps(command_args)))
            run_id = cur.fetchone()[0]
        conn.commit()
        return run_id
    except Exception as e:
        print(f"Error starting run: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def update_run_progress(run_id: int, records_downloaded: int = None, records_ingested: int = None, records_failed: int = None):
    """Update run progress counters."""
    if not run_id:
        return
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT raw_retrosheet.update_ingest_run_progress(%s, %s, %s, %s)
            """, (run_id, records_downloaded, records_ingested, records_failed))
        conn.commit()
    except Exception as e:
        print(f"Error updating run progress: {e}")
        conn.rollback()
    finally:
        conn.close()


def complete_run(run_id: int, final_details: dict = None):
    """Mark run as completed."""
    if not run_id:
        return
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT raw_retrosheet.complete_ingest_run(%s, %s)
            """, (run_id, json.dumps(final_details) if final_details else None))
        conn.commit()
    except Exception as e:
        print(f"Error completing run: {e}")
        conn.rollback()
    finally:
        conn.close()


def fail_run(run_id: int, error_message: str, error_details: dict = None):
    """Mark run as failed with error message."""
    if not run_id:
        return
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT raw_retrosheet.fail_ingest_run(%s, %s, %s)
            """, (run_id, error_message, json.dumps(error_details) if error_details else None))
        conn.commit()
    except Exception as e:
        print(f"Error failing run: {e}")
        conn.rollback()
    finally:
        conn.close()


def compute_checksum(data: Any) -> str:
    """Compute SHA256 checksum of data for deduplication."""
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data, sort_keys=True)
    else:
        data_str = str(data)
    return hashlib.sha256(data_str.encode()).hexdigest()


def fetch_espn_schedule(date: str) -> Optional[Dict[str, Any]]:
    """Fetch MLB schedule for a specific date from ESPN API."""
    url = f"{ENDPOINTS['schedule']}?dates={date}"
    
    try:
        start_time = time.time()
        response = requests.get(url, timeout=30)
        response_time_ms = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            checksum = compute_checksum(data)
            
            return {
                "url": url,
                "status": response.status_code,
                "response_time_ms": response_time_ms,
                "data": data,
                "checksum": checksum,
            }
        else:
            print(f"Error fetching schedule: HTTP {response.status_code}")
            return {
                "url": url,
                "status": response.status_code,
                "response_time_ms": response_time_ms,
                "data": None,
                "checksum": None,
            }
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        return None


def fetch_espn_game(game_id: str) -> Optional[Dict[str, Any]]:
    """Fetch specific MLB game data from ESPN API."""
    url = f"{ENDPOINTS['scoreboard']}?gameId={game_id}"
    
    try:
        start_time = time.time()
        response = requests.get(url, timeout=30)
        response_time_ms = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            checksum = compute_checksum(data)
            
            return {
                "url": url,
                "status": response.status_code,
                "response_time_ms": response_time_ms,
                "data": data,
                "checksum": checksum,
            }
        else:
            print(f"Error fetching game {game_id}: HTTP {response.status_code}")
            return {
                "url": url,
                "status": response.status_code,
                "response_time_ms": response_time_ms,
                "data": None,
                "checksum": None,
            }
    except Exception as e:
        print(f"Error fetching game {game_id}: {e}")
        return None


def store_schedule_snapshot(snapshot_data: Dict[str, Any], date: str) -> bool:
    """Store schedule snapshot in raw_espn.schedule_snapshots."""
    if not snapshot_data or snapshot_data["data"] is None:
        return False
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Determine season from date
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            season = date_obj.year if date_obj.month >= 4 else date_obj.year - 1
            
            # Check if snapshot already exists
            cur.execute("""
                SELECT snapshot_id FROM raw_espn.schedule_snapshots
                WHERE date = %s AND checksum = %s
            """, (date, snapshot_data["checksum"]))
            
            if cur.fetchone():
                print(f"Schedule snapshot for {date} already exists (same checksum)")
                return True
            
            # Insert new snapshot
            cur.execute("""
                INSERT INTO raw_espn.schedule_snapshots
                (date, endpoint, http_status, fetched_at, response_time_ms, raw_payload, checksum, season)
                VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s)
                ON CONFLICT (date, fetched_at) DO NOTHING
            """, (
                date,
                snapshot_data["url"],
                snapshot_data["status"],
                snapshot_data["response_time_ms"],
                Json(snapshot_data["data"]),
                snapshot_data["checksum"],
                season,
            ))
            
        conn.commit()
        print(f"Stored schedule snapshot for {date}")
        return True
    except Exception as e:
        print(f"Error storing schedule snapshot: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def store_game_snapshot(snapshot_data: Dict[str, Any], game_id: str) -> bool:
    """Store game snapshot in raw_espn.game_snapshots."""
    if not snapshot_data or snapshot_data["data"] is None:
        return False
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Extract game_date and season from data if available
            game_date = None
            season = None
            if snapshot_data["data"]:
                events = snapshot_data["data"].get("events", [])
                if events:
                    first_event = events[0]
                    game_date = first_event.get("date")
                    season = first_event.get("season", {}).get("year")
            
            # Check if snapshot already exists
            cur.execute("""
                SELECT snapshot_id FROM raw_espn.game_snapshots
                WHERE game_id = %s AND checksum = %s
            """, (game_id, snapshot_data["checksum"]))
            
            if cur.fetchone():
                print(f"Game snapshot for {game_id} already exists (same checksum)")
                return True
            
            # Insert new snapshot
            cur.execute("""
                INSERT INTO raw_espn.game_snapshots
                (game_id, endpoint, http_status, fetched_at, response_time_ms, raw_payload, checksum, game_date, season)
                VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s, %s)
                ON CONFLICT (game_id, fetched_at) DO NOTHING
            """, (
                game_id,
                snapshot_data["url"],
                snapshot_data["status"],
                snapshot_data["response_time_ms"],
                Json(snapshot_data["data"]),
                snapshot_data["checksum"],
                game_date,
                season,
            ))
            
        conn.commit()
        print(f"Stored game snapshot for {game_id}")
        return True
    except Exception as e:
        print(f"Error storing game snapshot: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Fetch ESPN MLB data")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Fetch schedule data")
    schedule_parser.add_argument("--date", type=str, help="Date in YYYY-MM-DD format (default: today)")

    # Game command
    game_parser = subparsers.add_parser("game", help="Fetch game data")
    game_parser.add_argument("--game-id", type=str, required=True, help="ESPN game ID")

    args = parser.parse_args()

    # Start run logging
    script_name = os.path.basename(__file__)
    command_args = vars(args)
    run_id = start_run("espn_api", script_name, command_args)

    if not run_id:
        print("Warning: Failed to start run logging, continuing without tracking")

    try:
        if args.command == "schedule":
            date = args.date or datetime.now().strftime("%Y-%m-%d")
            print(f"Fetching ESPN schedule for {date}")

            snapshot = fetch_espn_schedule(date)
            if snapshot:
                update_run_progress(run_id, records_downloaded=1)
                if store_schedule_snapshot(snapshot, date):
                    update_run_progress(run_id, records_ingested=1)
                else:
                    update_run_progress(run_id, records_failed=1)
            else:
                fail_run(run_id, "Failed to fetch schedule data")

        elif args.command == "game":
            game_id = args.game_id
            print(f"Fetching ESPN game {game_id}")

            snapshot = fetch_espn_game(game_id)
            if snapshot:
                update_run_progress(run_id, records_downloaded=1)
                if store_game_snapshot(snapshot, game_id):
                    update_run_progress(run_id, records_ingested=1)
                else:
                    update_run_progress(run_id, records_failed=1)
            else:
                fail_run(run_id, f"Failed to fetch game {game_id}")

        # Complete run successfully
        complete_run(run_id, {"command": args.command})
        print(f"Run completed successfully (run_id: {run_id})")

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(error_msg)
        fail_run(run_id, error_msg, {"exception_type": type(e).__name__})
        sys.exit(1)


if __name__ == "__main__":
    main()
