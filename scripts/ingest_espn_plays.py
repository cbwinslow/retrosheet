#!/usr/bin/env python3
"""
Ingest ESPN plays data for all games that don't have plays snapshots yet.
"""

import os
import sys
import psycopg2
from datetime import datetime
import time
import requests
import hashlib
import json
from typing import Dict, Any, Optional

# Load environment variables
LETTA_BASE_URL = os.getenv('LETTA_BASE_URL', 'http://localhost:8283')
LETTA_API_KEY = os.getenv('LETTA_API_KEY', 'sk-let-NzY2MDVkMWUtMGRmMy00MjExLTg1NDMtNjdhOGJjYTdiM2I0OmE3Y2I5MWM0LTdjYTctNDlmOC05N2Q0LTVk')

ESPN_CORE_URL = "https://sports.core.api.espn.com/v2/sports/baseball/mlb"

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

def compute_checksum(data: Dict[str, Any]) -> str:
    """Compute SHA256 checksum for JSON data."""
    if data is None:
        return None
    data_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(data_str.encode()).hexdigest()

def fetch_espn_plays(game_id: str) -> Optional[Dict[str, Any]]:
    """Fetch play-by-play data for a specific game from ESPN Core API v2."""
    url = f"{ESPN_CORE_URL}/events/{game_id}/competitions/{game_id}/plays"
    
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
            cur.execute("""
                SELECT snapshot_id FROM raw_espn.plays_snapshots
                WHERE game_id = %s AND checksum = %s
            """, (game_id, snapshot_data["checksum"]))
            
            if cur.fetchone():
                print(f"Plays snapshot already exists for game {game_id} (duplicate checksum)")
                return True
            
            # Insert new snapshot
            from psycopg2.extras import Json
            cur.execute("""
                INSERT INTO raw_espn.plays_snapshots
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
        print(f"Stored plays snapshot for game {game_id}")
        return True
    except Exception as e:
        print(f"Error storing plays snapshot: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Main function to ingest plays data for all games."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get all game IDs from 2024 onwards that don't have plays snapshots
            # ESPN only has play-by-play data for recent games (2024-2026)
            cur.execute("""
                SELECT DISTINCT g.game_id 
                FROM raw_espn.game_snapshots g
                WHERE g.game_id NOT IN (
                    SELECT DISTINCT p.game_id FROM raw_espn.plays_snapshots p
                )
                AND g.season >= 2024
                ORDER BY g.game_id
            """)
            
            game_ids = [row[0] for row in cur.fetchall()]
            print(f"Found {len(game_ids)} games from 2024+ without plays snapshots")
            
        conn.close()
        
        # Import fetch functions
        from fetch_espn_mlb import fetch_espn_game, fetch_espn_plays
        
        # Batch fetch plays data
        batch_size = 100
        total_games = len(game_ids)
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for i in range(0, total_games, batch_size):
            batch = game_ids[i:i+batch_size]
            print(f"\nProcessing batch {i//batch_size + 1}/{(total_games + batch_size - 1)//batch_size}")
            print(f"Games {i+1}-{min(i+batch_size, total_games)} of {total_games}")
            
            for game_id in batch:
                # First verify game data exists before fetching plays
                game_data = fetch_espn_game(game_id)
                if not game_data or game_data.get("status") != 200:
                    print(f"Skipping game {game_id} - no game data available")
                    skipped_count += 1
                    continue
                
                # Fetch plays data
                snapshot = fetch_espn_plays(game_id)
                if snapshot and snapshot["data"] is not None and len(snapshot["data"]) > 0:
                    if store_plays_snapshot(snapshot, game_id):
                        success_count += 1
                    else:
                        failed_count += 1
                elif snapshot and snapshot.get("status") == 404:
                    # Game doesn't have play-by-play data available, skip it
                    print(f"Skipping game {game_id} - no play-by-play data available")
                    skipped_count += 1
                else:
                    print(f"Skipping game {game_id} - empty plays array")
                    skipped_count += 1
            
            print(f"Batch complete: {success_count} success, {failed_count} failed, {skipped_count} skipped")
        
        print(f"\nFinal results: {success_count} success, {failed_count} failed, {skipped_count} skipped out of {total_games} games")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
