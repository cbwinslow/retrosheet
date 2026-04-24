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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import Json

# Load environment variables
load_dotenv()

# ESPN API Endpoints
ESPN_BASE_URL = "http://site.api.espn.com/apis/site/v2/sports/baseball/mlb"
ESPN_CORE_URL = "https://sports.core.api.espn.com/v2/sports/baseball/mlb"
ENDPOINTS = {
    "scoreboard": f"{ESPN_BASE_URL}/scoreboard",
    "schedule": f"{ESPN_BASE_URL}/schedule",
    "game": f"{ESPN_BASE_URL}/scoreboard",
    "summary": f"{ESPN_BASE_URL}/summary",
    "plays": f"{ESPN_CORE_URL}/events",
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
            cwd=os.path.dirname(os.path.abspath(__file__)),
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
            cur.execute(
                """
                SELECT raw_retrosheet.start_ingest_run(
                    %s, NULL, %s, NULL, %s, %s
                )
            """,
                (source_name, script_name, git_commit, json.dumps(command_args)),
            )
            run_id = cur.fetchone()[0]
        conn.commit()
        return run_id
    except Exception as e:
        print(f"Error starting run: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def update_run_progress(
    run_id: int,
    records_downloaded: int = None,
    records_ingested: int = None,
    records_failed: int = None,
):
    """Update run progress counters."""
    if not run_id:
        return
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT raw_retrosheet.update_ingest_run_progress(%s, %s, %s, %s)
            """,
                (run_id, records_downloaded, records_ingested, records_failed),
            )
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
            cur.execute(
                """
                SELECT raw_retrosheet.complete_ingest_run(%s, %s)
            """,
                (run_id, json.dumps(final_details) if final_details else None),
            )
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
            cur.execute(
                """
                SELECT raw_retrosheet.fail_ingest_run(%s, %s, %s)
            """,
                (run_id, error_message, json.dumps(error_details) if error_details else None),
            )
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
    """Fetch MLB schedule for a specific date from ESPN API.

    ESPN API uses the scoreboard endpoint with dates parameter for schedule data.
    Date format should be YYYYMMDD (no hyphens).
    """
    # Convert YYYY-MM-DD to YYYYMMDD format for ESPN API
    date_formatted = date.replace("-", "")
    url = f"{ENDPOINTS['scoreboard']}?dates={date_formatted}"

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
    """Fetch specific MLB game data from ESPN API using summary endpoint for detailed data."""
    url = f"http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event={game_id}"

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


def fetch_espn_plays(game_id: str) -> Optional[Dict[str, Any]]:
    """Fetch play-by-play data for a specific game from ESPN summary endpoint.

    NOTE: Previously used ESPN Core API v2 endpoint which returns 404.
    Changed to summary endpoint which contains plays array in the response.
    This is the correct endpoint for ESPN play-by-play data.

    The plays data is included in the summary response, not a separate endpoint."""
    url = f"http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event={game_id}"

    try:
        start_time = time.time()
        response = requests.get(url, timeout=30)
        response_time_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            data = response.json()
            # Extract plays from the summary response
            plays_data = data.get("plays", [])

            # Return the plays data wrapped in the expected structure
            result = {
                "url": url,
                "status": response.status_code,
                "response_time_ms": response_time_ms,
                "data": plays_data,
                "checksum": compute_checksum(plays_data),
            }

            # Also include game metadata from header
            if "header" in data and "competitions" in data["header"]:
                comp = data["header"]["competitions"][0]
                result["game_date"] = comp.get("date")
                # Extract season year from date if not in season.type
                season_year = comp.get("season", {}).get("year")
                if not season_year and comp.get("date"):
                    # Extract year from date string (format: "2026-04-19T01:38Z")
                    season_year = int(comp["date"][:4])
                result["season"] = season_year

            return result
        else:
            print(f"Error fetching plays for game {game_id}: HTTP {response.status_code}")
            return {
                "url": url,
                "status": response.status_code,
                "response_time_ms": response_time_ms,
                "data": None,
                "checksum": None,
            }
    except Exception as e:
        print(f"Error fetching plays for game {game_id}: {e}")
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
            cur.execute(
                """
                SELECT snapshot_id FROM raw_espn.schedule_snapshots
                WHERE date = %s AND checksum = %s
            """,
                (date, snapshot_data["checksum"]),
            )

            if cur.fetchone():
                print(f"Schedule snapshot for {date} already exists (same checksum)")
                return True

            # Insert new snapshot
            cur.execute(
                """
                INSERT INTO raw_espn.schedule_snapshots
                (date, endpoint, http_status, fetched_at, response_time_ms, raw_payload, checksum, season)
                VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s)
                ON CONFLICT (date, fetched_at) DO NOTHING
            """,
                (
                    date,
                    snapshot_data["url"],
                    snapshot_data["status"],
                    snapshot_data["response_time_ms"],
                    Json(snapshot_data["data"]),
                    snapshot_data["checksum"],
                    season,
                ),
            )

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
            cur.execute(
                """
                SELECT snapshot_id FROM raw_espn.game_snapshots
                WHERE game_id = %s AND checksum = %s
            """,
                (game_id, snapshot_data["checksum"]),
            )

            if cur.fetchone():
                print(f"Game snapshot for {game_id} already exists (same checksum)")
                return True

            # Insert new snapshot
            cur.execute(
                """
                INSERT INTO raw_espn.game_snapshots
                (game_id, endpoint, http_status, fetched_at, response_time_ms, raw_payload, checksum, game_date, season)
                VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s, %s)
                ON CONFLICT (game_id, fetched_at) DO NOTHING
            """,
                (
                    game_id,
                    snapshot_data["url"],
                    snapshot_data["status"],
                    snapshot_data["response_time_ms"],
                    Json(snapshot_data["data"]),
                    snapshot_data["checksum"],
                    game_date,
                    season,
                ),
            )

        conn.commit()
        print(f"Stored game snapshot for {game_id}")
        return True
    except Exception as e:
        print(f"Error storing game snapshot: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def store_plays_snapshot(snapshot_data: Dict[str, Any], game_id: str) -> bool:
    """Store plays snapshot in raw_espn.plays_snapshots."""
    if not snapshot_data or snapshot_data["data"] is None:
        return False

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Extract game_date and season from snapshot_data (now included by fetch_espn_plays)
            game_date = snapshot_data.get("game_date")
            season = snapshot_data.get("season")

            # Check if snapshot already exists
            cur.execute(
                """
                SELECT snapshot_id FROM raw_espn.plays_snapshots
                WHERE game_id = %s AND checksum = %s
            """,
                (game_id, snapshot_data["checksum"]),
            )

            if cur.fetchone():
                print(f"Plays snapshot for {game_id} already exists (same checksum)")
                return True

            # Insert new snapshot
            cur.execute(
                """
                INSERT INTO raw_espn.plays_snapshots
                (game_id, endpoint, http_status, fetched_at, response_time_ms, raw_payload, checksum, game_date, season)
                VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s, %s)
                ON CONFLICT (game_id, checksum) DO NOTHING
            """,
                (
                    game_id,
                    snapshot_data["url"],
                    snapshot_data["status"],
                    snapshot_data["response_time_ms"],
                    Json(snapshot_data["data"]),
                    snapshot_data["checksum"],
                    game_date,
                    season,
                ),
            )

        conn.commit()
        print(f"Stored plays snapshot for {game_id}")
        return True
    except Exception as e:
        print(f"Error storing plays snapshot: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def fetch_games_batch(
    game_ids: List[str], include_plays: bool = False, max_workers: int = 10
) -> Dict[str, int]:
    """Fetch multiple games in parallel using ThreadPoolExecutor.

    Returns dict with counts: {'downloaded': int, 'ingested': int, 'failed': int}
    """
    counts = {"downloaded": 0, "ingested": 0, "failed": 0}

    def fetch_and_store_game(game_id: str) -> Dict[str, int]:
        """Fetch and store a single game, return counts for this game."""
        local_counts = {"downloaded": 0, "ingested": 0, "failed": 0}

        # Fetch game summary
        snapshot = fetch_espn_game(game_id)
        if snapshot and snapshot["data"]:
            local_counts["downloaded"] += 1
            if store_game_snapshot(snapshot, game_id):
                local_counts["ingested"] += 1
            else:
                local_counts["failed"] += 1

            # Fetch plays if requested
            if include_plays:
                plays_snapshot = fetch_espn_plays(game_id)
                if plays_snapshot and plays_snapshot["data"]:
                    local_counts["downloaded"] += 1
                    if store_plays_snapshot(plays_snapshot, game_id):
                        local_counts["ingested"] += 1
                    else:
                        local_counts["failed"] += 1
        else:
            local_counts["failed"] += 1

        return local_counts

    print(f"Fetching {len(game_ids)} games with {max_workers} workers...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_and_store_game, game_id): game_id for game_id in game_ids}

        for future in as_completed(futures):
            game_id = futures[future]
            try:
                result = future.result()
                counts["downloaded"] += result["downloaded"]
                counts["ingested"] += result["ingested"]
                counts["failed"] += result["failed"]
                print(f"Completed game {game_id}: {result}")
            except Exception as e:
                print(f"Error processing game {game_id}: {e}")
                counts["failed"] += 1

    return counts


def main():
    parser = argparse.ArgumentParser(description="Fetch ESPN MLB data")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Fetch schedule data")
    schedule_parser.add_argument(
        "--date", type=str, help="Date in YYYY-MM-DD format (default: today)"
    )

    # Game command
    game_parser = subparsers.add_parser("game", help="Fetch game data")
    game_parser.add_argument("--game-id", type=str, required=True, help="ESPN game ID")
    game_parser.add_argument(
        "--include-plays", action="store_true", help="Also fetch play-by-play data"
    )

    # Plays command
    plays_parser = subparsers.add_parser("plays", help="Fetch play-by-play data")
    plays_parser.add_argument("--game-id", type=str, required=True, help="ESPN game ID")

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Fetch multiple games in parallel")
    batch_parser.add_argument(
        "--game-ids", type=str, required=True, help="Comma-separated list of ESPN game IDs"
    )
    batch_parser.add_argument(
        "--include-plays", action="store_true", help="Also fetch play-by-play data"
    )
    batch_parser.add_argument(
        "--workers", type=int, default=10, help="Number of parallel workers (default: 10)"
    )

    # Ingest historical command
    historical_parser = subparsers.add_parser(
        "ingest-historical", help="Ingest historical games from a date range"
    )
    historical_parser.add_argument(
        "--start-date", type=str, required=True, help="Start date in YYYY-MM-DD format"
    )
    historical_parser.add_argument(
        "--end-date", type=str, required=True, help="End date in YYYY-MM-DD format"
    )
    historical_parser.add_argument(
        "--workers", type=int, default=10, help="Number of parallel workers (default: 10)"
    )

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

                # Fetch plays if requested
                if args.include_plays:
                    print(f"Fetching ESPN plays for game {game_id}")
                    plays_snapshot = fetch_espn_plays(game_id)
                    if plays_snapshot:
                        update_run_progress(run_id, records_downloaded=1)
                        if store_plays_snapshot(plays_snapshot, game_id):
                            update_run_progress(run_id, records_ingested=1)
                        else:
                            update_run_progress(run_id, records_failed=1)
            else:
                fail_run(run_id, f"Failed to fetch game {game_id}")

        elif args.command == "plays":
            game_id = args.game_id
            print(f"Fetching ESPN plays for game {game_id}")

            snapshot = fetch_espn_plays(game_id)
            if snapshot:
                update_run_progress(run_id, records_downloaded=1)
                if store_plays_snapshot(snapshot, game_id):
                    update_run_progress(run_id, records_ingested=1)
                else:
                    update_run_progress(run_id, records_failed=1)
            else:
                fail_run(run_id, f"Failed to fetch plays for game {game_id}")

        elif args.command == "batch":
            game_ids = args.game_ids.split(",")
            game_ids = [gid.strip() for gid in game_ids]
            print(f"Fetching {len(game_ids)} games in batch mode")

            counts = fetch_games_batch(game_ids, args.include_plays, args.workers)
            update_run_progress(run_id, records_downloaded=counts["downloaded"])
            update_run_progress(run_id, records_ingested=counts["ingested"])
            update_run_progress(run_id, records_failed=counts["failed"])

            print(f"Batch fetch complete: {counts}")

        elif args.command == "ingest-historical":
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")

            # Iterate backwards from end_date to start_date
            current_date = end_date
            all_game_ids = []

            while current_date >= start_date:
                date_str = current_date.strftime("%Y-%m-%d")
                print(f"Fetching schedule for {date_str}")

                schedule = fetch_espn_schedule(date_str)
                if schedule and schedule["data"]:
                    events = schedule["data"].get("events", [])
                    game_ids = [event.get("id") for event in events if event.get("id")]
                    all_game_ids.extend(game_ids)
                    print(f"  Found {len(game_ids)} games on {date_str}")

                    # Store schedule snapshot
                    store_schedule_snapshot(schedule, date_str)

                current_date -= timedelta(days=1)

            # Deduplicate game IDs
            all_game_ids = list(set(all_game_ids))
            print(f"Total unique games to fetch: {len(all_game_ids)}")

            # Batch fetch all games
            if all_game_ids:
                counts = fetch_games_batch(
                    all_game_ids, include_plays=True, max_workers=args.workers
                )
                update_run_progress(run_id, records_downloaded=counts["downloaded"])
                update_run_progress(run_id, records_ingested=counts["ingested"])
                update_run_progress(run_id, records_failed=counts["failed"])
                print(f"Historical ingestion complete: {counts}")
            else:
                print("No games found in date range")

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
