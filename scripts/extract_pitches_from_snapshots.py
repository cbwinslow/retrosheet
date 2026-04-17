#!/usr/bin/env python3
"""
Extract pitch-level data from raw_mlb.live_feed_snapshots (Option B).

This script transforms stored MLB live feed JSON into pitch-level granularity:
- One row per pitch (not per plate appearance)
- All pitches have metrics: speed, spin, location, break
- Populates mlb.play_events and mlb.pitches tables
- Uses already-downloaded snapshots (no API calls)

Usage:
    python3 scripts/extract_pitches_from_snapshots.py [--season 2024] [--limit 100] [--batch-size 100]

Output tables:
    mlb.play_events - One row per at-bat (plate appearance)
    mlb.pitches - One row per pitch with full metrics

Schema alignment:
    - mlb.play_events: (game_pk, event_index) PK, stores at-bat level data
    - mlb.pitches: (game_pk, event_index, pitch_index) PK, references play_events
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import execute_values


def get_db_connection():
    """Create database connection from environment or defaults."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "retrosheet"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
    )


def get_snapshots_to_process(
    conn, 
    season: Optional[int] = None, 
    limit: Optional[int] = None,
    game_pk: Optional[int] = None
) -> List[Tuple]:
    """Get snapshots that haven't been extracted yet."""
    if game_pk:
        # Single game mode
        query = """
            SELECT DISTINCT ON (lfs.game_pk)
                lfs.snapshot_id,
                lfs.game_pk,
                (lfs.payload->'gameData'->'datetime'->>'officialDate')::date as game_date,
                lfs.payload
            FROM raw_mlb.live_feed_snapshots lfs
            WHERE lfs.http_status = 200
              AND lfs.game_pk = %s
            ORDER BY lfs.game_pk, lfs.fetched_at DESC
            LIMIT 1
        """
        params = [game_pk]
    else:
        # Batch mode
        query = """
            SELECT DISTINCT ON (lfs.game_pk)
                lfs.snapshot_id,
                lfs.game_pk,
                (lfs.payload->'gameData'->'datetime'->>'officialDate')::date as game_date,
                lfs.payload
            FROM raw_mlb.live_feed_snapshots lfs
            WHERE lfs.http_status = 200
              AND NOT EXISTS (
                  SELECT 1 FROM mlb.play_events pe 
                  WHERE pe.game_pk = lfs.game_pk 
                  LIMIT 1
              )
        """
        params = []
        if season:
            query += " AND lfs.season = %s"
            params.append(season)
        query += " ORDER BY lfs.game_pk, lfs.fetched_at DESC"
        if limit:
            query += " LIMIT %s"
            params.append(limit)
    
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def extract_play_event(play: Dict, game_pk: int, event_index: int, game_date) -> Optional[Dict]:
    """Extract play_event row from a play (at-bat) object."""
    about = play.get("about", {})
    matchup = play.get("matchup", {})
    result = play.get("result", {})
    count = play.get("count", {})
    
    # Get base state from runners
    runners = play.get("runners", [])
    runner_on_1b = any(r.get("movement", {}).get("end") == "1B" for r in runners)
    runner_on_2b = any(r.get("movement", {}).get("end") == "2B" for r in runners)
    runner_on_3b = any(r.get("movement", {}).get("end") == "3B" for r in runners)
    
    batter = matchup.get("batter", {})
    pitcher = matchup.get("pitcher", {})
    
    return {
        "game_pk": game_pk,
        "event_index": event_index,
        "event_type": result.get("eventType"),
        "event_description": result.get("description", "")[:500],  # Truncate long descriptions
        "inning": about.get("inning"),
        "is_top_inning": about.get("isTopInning"),
        "balls_before": play.get("count", {}).get("balls", 0),
        "strikes_before": play.get("count", {}).get("strikes", 0),
        "outs_before": play.get("count", {}).get("outs", 0),
        "batter_id": batter.get("id"),
        "pitcher_id": pitcher.get("id"),
        "on_deck_batter_id": None,  # Not always available
        "in_hole_batter_id": None,
        "runner_on_1b_id": None,  # Would need to track from previous play
        "runner_on_2b_id": None,
        "runner_on_3b_id": None,
        "event_code": result.get("event"),
        "event_result": result.get("eventType"),
        "is_scoring_play": result.get("isScoringPlay", False),
        "runs_batted_in": result.get("rbi", 0),
        "balls_after": count.get("balls", 0),
        "strikes_after": count.get("strikes", 0),
        "outs_after": count.get("outs", 0),
        "home_score_after": result.get("homeScore", 0),
        "away_score_after": result.get("awayScore", 0),
        "event_start_time": None,  # Would parse from ISO string
        "event_end_time": None,
        "api_source": "mlb_api",
        "data_quality_score": 1.0,
    }


def extract_pitch(
    pitch_event: Dict,
    game_pk: int,
    event_index: int,
    pitch_index: int,
    batter_id: Optional[int],
    pitcher_id: Optional[int],
    inning: Optional[int],
    is_top_inning: Optional[bool],
    balls_before: int,
    strikes_before: int,
    outs_before: int
) -> Optional[Dict]:
    """Extract pitch row from a pitch event."""
    if not pitch_event.get("isPitch", False):
        return None
    
    details = pitch_event.get("details", {})
    pitch_data = pitch_event.get("pitchData", {})
    coords = pitch_data.get("coordinates", {})
    breaks = pitch_data.get("breaks", {})
    
    # Generate unique pitch ID
    pitch_id_str = f"{game_pk}_{event_index}_{pitch_index}_{pitch_event.get('startTime', '')}"
    pitch_uid = hashlib.md5(pitch_id_str.encode()).hexdigest()
    
    return {
        "game_pk": game_pk,
        "event_index": event_index,
        "pitch_index": pitch_index,
        "pitch_number": pitch_index + 1,  # 1-based pitch number
        "play_id": pitch_event.get("playId"),
        "pitch_uid": pitch_uid,
        "pitch_type_code": details.get("type", {}).get("code"),
        "pitch_type_description": details.get("type", {}).get("description"),
        "pitch_type_confidence": pitch_data.get("typeConfidence"),
        "pitch_call_code": details.get("call", {}).get("code"),
        "pitch_call_description": details.get("call", {}).get("description"),
        "pitch_call_confidence": None,  # Not in this API
        "plate_x": coords.get("pX"),
        "plate_z": coords.get("pZ"),
        "plate_zone": pitch_data.get("zone"),
        "start_speed": pitch_data.get("startSpeed"),
        "end_speed": pitch_data.get("endSpeed"),
        "extension": pitch_data.get("extension"),
        "spin_rate": breaks.get("spinRate"),
        "spin_direction": breaks.get("spinDirection"),
        "break_angle": breaks.get("breakAngle"),
        "break_length": breaks.get("breakLength"),
        "break_vertical": breaks.get("breakVertical"),
        "break_horizontal": breaks.get("breakHorizontal"),
        "pfx_x": coords.get("pfxX"),
        "pfx_z": coords.get("pfxZ"),
        "plate_time": pitch_data.get("plateTime"),
        "reaction_time": None,  # Calculated, not stored
        "batter_id": batter_id,
        "pitcher_id": pitcher_id,
        "balls_before": balls_before,
        "strikes_before": strikes_before,
        "outs_before": outs_before,
        "inning": inning,
        "is_top_inning": is_top_inning,
        "runner_on_1b": None,  # Would need runner state
        "runner_on_2b": None,
        "runner_on_3b": None,
        "home_score": None,  # From play result
        "away_score": None,
        "api_source": "mlb_api",
        "data_quality_score": 1.0,
        "pitch_system": "statcast",
    }


def ensure_game_exists(conn, game_pk: int, game_date, payload: Dict) -> bool:
    """Ensure the game exists in mlb.games table."""
    # Check if game exists
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM mlb.games WHERE game_pk = %s", (game_pk,))
        if cur.fetchone():
            return True
    
    # Extract game data from payload
    game_data = payload.get("gameData", {})
    game_info = game_data.get("game", {})
    teams = game_data.get("teams", {})
    venue = game_data.get("venue", {})
    
    away_team = teams.get("away", {})
    home_team = teams.get("home", {})
    
    with conn.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO mlb.games (
                    game_pk, game_date, season,
                    away_team_id, home_team_id,
                    venue_id, venue_name,
                    game_type,
                    api_source, data_quality_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (game_pk) DO NOTHING
                """,
                (
                    game_pk,
                    game_date,
                    game_info.get("season"),
                    away_team.get("id"),
                    home_team.get("id"),
                    venue.get("id"),
                    venue.get("name", ""),
                    game_info.get("type", "R"),
                    "mlb_api",
                    1.0
                )
            )
            return True
        except Exception as e:
            print(f"Warning: Could not insert game {game_pk}: {e}")
            return False


def process_snapshot(
    conn, 
    snapshot_id: int, 
    game_pk: int, 
    game_date, 
    payload: Dict
) -> Tuple[List[Dict], List[Dict], int, int]:
    """Process a single game snapshot and extract play events and pitches."""
    live_data = payload.get("liveData", {})
    plays = live_data.get("plays", {})
    all_plays = plays.get("allPlays", [])
    
    play_events = []
    pitches = []
    total_pitches_in_game = 0
    total_plays = len(all_plays)
    
    for event_index, play in enumerate(all_plays):
        # Extract play event (at-bat level)
        play_event = extract_play_event(play, game_pk, event_index, game_date)
        if play_event:
            play_events.append(play_event)
        
        # Extract pitches within this play
        matchup = play.get("matchup", {})
        batter_id = matchup.get("batter", {}).get("id")
        pitcher_id = matchup.get("pitcher", {}).get("id")
        about = play.get("about", {})
        inning = about.get("inning")
        is_top_inning = about.get("isTopInning")
        
        play_events_list = play.get("playEvents", [])
        balls_before = 0
        strikes_before = 0
        outs_before = play.get("count", {}).get("outs", 0)
        
        pitch_index = 0
        for pe in play_events_list:
            if pe.get("isPitch", False):
                pitch = extract_pitch(
                    pe, game_pk, event_index, pitch_index,
                    batter_id, pitcher_id, inning, is_top_inning,
                    balls_before, strikes_before, outs_before
                )
                if pitch:
                    pitches.append(pitch)
                    total_pitches_in_game += 1
                    pitch_index += 1
                
                # Update count for next pitch
                details = pe.get("details", {})
                if details.get("ball", False):
                    balls_before += 1
                elif details.get("strike", False) and not details.get("isInPlay", False):
                    strikes_before += 1
                # Ball in play ends the PA
    
    return play_events, pitches, total_plays, total_pitches_in_game


def insert_play_events(conn, events: List[Dict]) -> int:
    """Insert play events into mlb.play_events."""
    if not events:
        return 0
    
    columns = [
        "game_pk", "event_index", "event_type", "event_description",
        "inning", "is_top_inning", "balls_before", "strikes_before", "outs_before",
        "batter_id", "pitcher_id", "on_deck_batter_id", "in_hole_batter_id",
        "runner_on_1b_id", "runner_on_2b_id", "runner_on_3b_id",
        "event_code", "event_result", "is_scoring_play", "runs_batted_in",
        "balls_after", "strikes_after", "outs_after",
        "home_score_after", "away_score_after",
        "api_source", "data_quality_score"
    ]
    
    values = []
    for e in events:
        row = tuple(e.get(col) for col in columns)
        values.append(row)
    
    with conn.cursor() as cur:
        # Build ON CONFLICT update clause
        update_cols = [c for c in columns if c not in ["game_pk", "event_index"]]
        update_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
        
        query = f"""
            INSERT INTO mlb.play_events ({', '.join(columns)})
            VALUES %s
            ON CONFLICT (game_pk, event_index) DO UPDATE SET
                {update_clause},
                last_updated = now()
        """
        execute_values(cur, query, values, page_size=1000)
    
    return len(events)


def insert_pitches(conn, pitches: List[Dict]) -> int:
    """Insert pitch rows into mlb.pitches."""
    if not pitches:
        return 0
    
    columns = [
        "game_pk", "event_index", "pitch_index", "pitch_number", "play_id", "pitch_uid",
        "pitch_type_code", "pitch_type_description", "pitch_type_confidence",
        "pitch_call_code", "pitch_call_description", "pitch_call_confidence",
        "plate_x", "plate_z", "plate_zone",
        "start_speed", "end_speed", "extension",
        "spin_rate", "spin_direction", "break_angle", "break_length",
        "break_vertical", "break_horizontal", "pfx_x", "pfx_z",
        "plate_time", "reaction_time",
        "batter_id", "pitcher_id",
        "balls_before", "strikes_before", "outs_before",
        "inning", "is_top_inning",
        "runner_on_1b", "runner_on_2b", "runner_on_3b",
        "home_score", "away_score",
        "api_source", "data_quality_score", "pitch_system"
    ]
    
    values = []
    for p in pitches:
        row = tuple(p.get(col) for col in columns)
        values.append(row)
    
    with conn.cursor() as cur:
        # Build ON CONFLICT update clause
        update_cols = [c for c in columns if c not in ["game_pk", "event_index", "pitch_index"]]
        update_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
        
        query = f"""
            INSERT INTO mlb.pitches ({', '.join(columns)})
            VALUES %s
            ON CONFLICT (game_pk, event_index, pitch_index) DO UPDATE SET
                {update_clause},
                last_updated = now()
        """
        execute_values(cur, query, values, page_size=1000)
    
    return len(pitches)


def main():
    parser = argparse.ArgumentParser(
        description="Extract pitch-level data from MLB live feed snapshots",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process single game
    python3 scripts/extract_pitches_from_snapshots.py --game-pk 744795
    
    # Process all unextracted games for 2024
    python3 scripts/extract_pitches_from_snapshots.py --season 2024
    
    # Process small batch for testing
    python3 scripts/extract_pitches_from_snapshots.py --season 2024 --limit 10 --dry-run
        """
    )
    parser.add_argument(
        "--season",
        type=int,
        help="Only process games from this season"
    )
    parser.add_argument(
        "--game-pk",
        type=int,
        help="Process single specific game"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of games to process (for testing)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Commit every N games (default: 100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse but don't insert (shows what would be processed)"
    )
    args = parser.parse_args()
    
    conn = get_db_connection()
    
    try:
        # Get snapshots to process
        print("=" * 60)
        print("MLB Pitch Extraction from Snapshots (Option B)")
        print("=" * 60)
        
        snapshots = get_snapshots_to_process(
            conn, 
            season=args.season, 
            limit=args.limit,
            game_pk=args.game_pk
        )
        
        if not snapshots:
            print("\nNo new games to process. All snapshots already extracted.")
            return 0
        
        print(f"\nFound {len(snapshots)} game(s) to process")
        if args.dry_run:
            print("[DRY RUN MODE - No database changes will be made]")
        print()
        
        # Process snapshots
        total_play_events = 0
        total_pitches = 0
        total_plays_count = 0
        processed = 0
        errors = 0
        
        for snapshot_id, game_pk, game_date, payload in snapshots:
            try:
                # Ensure game exists in mlb.games first
                if not args.dry_run:
                    if not ensure_game_exists(conn, game_pk, game_date, payload):
                        print(f"Skipping game {game_pk} - could not create game record")
                        errors += 1
                        continue
                
                play_events, pitches, num_plays, num_pitches = process_snapshot(
                    conn, snapshot_id, game_pk, game_date, payload
                )
                
                if args.dry_run:
                    # Just count, don't insert
                    total_play_events += len(play_events)
                    total_pitches += len(pitches)
                    total_plays_count += num_plays
                    print(f"[DRY RUN] Game {game_pk} ({game_date}): "
                          f"{num_plays} plays, {num_pitches} pitches")
                else:
                    # Insert data
                    events_inserted = insert_play_events(conn, play_events)
                    pitches_inserted = insert_pitches(conn, pitches)
                    
                    total_play_events += events_inserted
                    total_pitches += pitches_inserted
                    total_plays_count += num_plays
                    
                    # Commit periodically
                    if (processed + 1) % args.batch_size == 0:
                        conn.commit()
                        print(f"Committed batch: {processed + 1} games processed...")
                
                processed += 1
                
            except Exception as e:
                errors += 1
                print(f"ERROR processing game {game_pk}: {e}")
                if not args.dry_run:
                    conn.rollback()
                continue
        
        # Final commit
        if not args.dry_run and processed > 0:
            conn.commit()
        
        # Summary
        print("\n" + "=" * 60)
        print("EXTRACTION COMPLETE")
        print("=" * 60)
        print(f"Games processed: {processed}")
        print(f"Errors: {errors}")
        print(f"Total plays (at-bats): {total_plays_count}")
        print(f"Total play events: {total_play_events}")
        print(f"Total pitches: {total_pitches}")
        
        if not args.dry_run:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM mlb.play_events")
                pe_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM mlb.pitches")
                p_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(DISTINCT game_pk) FROM mlb.pitches")
                games_with_pitches = cur.fetchone()[0]
                
                print(f"\nDatabase totals:")
                print(f"  mlb.play_events: {pe_count:,} rows")
                print(f"  mlb.pitches: {p_count:,} pitches from {games_with_pitches:,} games")
        
        return 0 if errors == 0 else 1
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Rolling back...")
        if not args.dry_run:
            conn.rollback()
        return 130
    
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
