#!/usr/bin/env python3
"""
Populate bridge.game_xref by matching MLB live feed snapshots to Retrosheet games.

This script:
1. Queries raw_mlb.live_feed_snapshots for game metadata (game_pk, date, teams)
2. Matches to core.games using date + team_ids via bridge.team_xref
3. Inserts matches into bridge.game_xref
4. Reports unmatched games for manual review

Usage:
    python3 scripts/populate_game_xref.py [--season 2024] [--dry-run]
"""

import argparse
import os
import sys
from typing import Optional

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


def get_distinct_mlb_games(conn, season: Optional[int] = None) -> list:
    """Get distinct MLB games from live feed snapshots."""
    query = """
        SELECT DISTINCT ON (lfs.game_pk)
            lfs.game_pk,
            -- Extract game date from payload datetime field
            CASE 
                WHEN lfs.game_date IS NOT NULL THEN lfs.game_date
                ELSE (lfs.payload->'gameData'->'datetime'->>'officialDate')::date
            END as game_date,
            lfs.season,
            (lfs.payload->'gameData'->'teams'->'away'->>'id')::int as away_team_id,
            (lfs.payload->'gameData'->'teams'->'home'->>'id')::int as home_team_id,
            lfs.payload->'gameData'->'teams'->'away'->>'name' as away_team_name,
            lfs.payload->'gameData'->'teams'->'home'->>'name' as home_team_name
        FROM raw_mlb.live_feed_snapshots lfs
        WHERE lfs.http_status = 200
    """
    params = []
    if season:
        query += " AND lfs.season = %s"
        params.append(season)
    query += " ORDER BY lfs.game_pk, lfs.fetched_at DESC"
    
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


def get_retrosheet_game_id(conn, game_date: str, away_team_id: int, home_team_id: int) -> Optional[str]:
    """Match MLB game to Retrosheet game using date and team mappings.
    
    First tries to match by MLB team IDs (normal games).
    Falls back to retrosheet team IDs for All-Star games and special cases.
    """
    # First try: Match by MLB team IDs (normal games)
    query = """
        SELECT g.game_id
        FROM core.games g
        JOIN bridge.team_xref atx ON g.away_team_id = atx.retrosheet_team_id
        JOIN bridge.team_xref htx ON g.home_team_id = htx.retrosheet_team_id
        WHERE g.game_date = %s
          AND atx.mlb_team_id = %s
          AND htx.mlb_team_id = %s
        LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(query, (game_date, away_team_id, home_team_id))
        row = cur.fetchone()
        if row:
            return row[0]
    
    # Second try: Match by retrosheet team IDs directly (All-Star games, etc.)
    # This handles cases where mlb_team_id is NULL (historical All-Star teams)
    query2 = """
        SELECT g.game_id
        FROM core.games g
        JOIN bridge.team_xref atx ON g.away_team_id = atx.retrosheet_team_id
        JOIN bridge.team_xref htx ON g.home_team_id = htx.retrosheet_team_id
        WHERE g.game_date = %s
          AND atx.mlb_team_id IS NULL
          AND htx.mlb_team_id IS NULL
          AND atx.retrosheet_team_id = (
              SELECT retrosheet_team_id FROM bridge.team_xref WHERE mlb_team_id = %s LIMIT 1
          )
          AND htx.retrosheet_team_id = (
              SELECT retrosheet_team_id FROM bridge.team_xref WHERE mlb_team_id = %s LIMIT 1
          )
        LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(query2, (game_date, away_team_id, home_team_id))
        row = cur.fetchone()
        return row[0] if row else None


def insert_game_mappings(conn, mappings: list, dry_run: bool = False) -> tuple:
    """Insert game xref mappings. Returns (inserted, skipped)."""
    if not mappings:
        return 0, 0
    
    inserted = 0
    skipped = 0
    duplicate_retro_ids = set()
    
    with conn.cursor() as cur:
        for game_pk, retrosheet_game_id, season, game_date in mappings:
            # Check if this retrosheet game already mapped (skip duplicates)
            if retrosheet_game_id in duplicate_retro_ids:
                skipped += 1
                continue
            
            # Check if mapping already exists in DB
            cur.execute(
                "SELECT 1 FROM bridge.game_xref WHERE mlb_game_pk = %s",
                (game_pk,)
            )
            if cur.fetchone():
                skipped += 1
                continue
            
            if not dry_run:
                try:
                    cur.execute(
                        """
                        INSERT INTO bridge.game_xref 
                            (mlb_game_pk, retrosheet_game_id, updated_at)
                        VALUES (%s, %s, now())
                        ON CONFLICT (mlb_game_pk) DO UPDATE SET
                            retrosheet_game_id = EXCLUDED.retrosheet_game_id,
                            updated_at = now()
                        """,
                        (game_pk, retrosheet_game_id)
                    )
                    inserted += 1
                    duplicate_retro_ids.add(retrosheet_game_id)
                except psycopg2.errors.UniqueViolation:
                    # Retrosheet game already mapped to different MLB game
                    skipped += 1
                    duplicate_retro_ids.add(retrosheet_game_id)
                    conn.rollback()
    
    if not dry_run:
        conn.commit()
    
    return inserted, skipped


def main():
    parser = argparse.ArgumentParser(
        description="Populate bridge.game_xref from live feed snapshots"
    )
    parser.add_argument(
        "--season",
        type=int,
        help="Only process games from this season"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Commit every N mappings"
    )
    args = parser.parse_args()
    
    conn = get_db_connection()
    
    try:
        # Check pre-requisites
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM bridge.team_xref WHERE mlb_team_id IS NOT NULL")
            team_count = cur.fetchone()[0]
            if team_count == 0:
                print("ERROR: bridge.team_xref is empty. Run populate_bridge_tables.py first.")
                sys.exit(1)
            print(f"✓ Found {team_count} team mappings in bridge.team_xref")
        
        # Get MLB games from snapshots
        print(f"\nFetching MLB games from live feed snapshots...")
        if args.season:
            print(f"  Filtering to season: {args.season}")
        
        mlb_games = get_distinct_mlb_games(conn, args.season)
        print(f"  Found {len(mlb_games)} distinct MLB games")
        
        # Match to Retrosheet games
        print(f"\nMatching to Retrosheet games...")
        mappings = []
        unmatched = []
        
        for i, (game_pk, game_date, season, away_team_id, home_team_id, 
                away_name, home_name) in enumerate(mlb_games, 1):
            
            if game_date is None:
                unmatched.append((game_pk, season, "missing game_date in snapshot"))
                continue
            
            retro_id = get_retrosheet_game_id(conn, game_date, away_team_id, home_team_id)
            
            if retro_id:
                mappings.append((game_pk, retro_id, season, game_date))
            else:
                unmatched.append((game_pk, season, f"no match for {away_name}@{home_name} on {game_date}"))
            
            if i % 1000 == 0:
                print(f"  Processed {i}/{len(mlb_games)} games...")
        
        print(f"\nMatching complete:")
        print(f"  ✓ Matched: {len(mappings)} games")
        print(f"  ✗ Unmatched: {len(unmatched)} games")
        
        # Insert mappings
        if mappings:
            print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Inserting mappings...")
            inserted, skipped = insert_game_mappings(conn, mappings, args.dry_run)
            print(f"  Inserted: {inserted}")
            print(f"  Skipped (already exist): {skipped}")
        
        # Report unmatched
        if unmatched and len(unmatched) <= 20:
            print(f"\nUnmatched games (showing all {len(unmatched)}):")
            for game_pk, season, reason in unmatched:
                print(f"  {game_pk} (season {season}): {reason}")
        elif unmatched:
            print(f"\nUnmatched games (showing first 20 of {len(unmatched)}):")
            for game_pk, season, reason in unmatched[:20]:
                print(f"  {game_pk} (season {season}): {reason}")
            print(f"  ... and {len(unmatched) - 20} more")
        
        # Final stats
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM bridge.game_xref")
            total = cur.fetchone()[0]
            print(f"\nFinal: bridge.game_xref now has {total} mappings")
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()
