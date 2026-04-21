#!/usr/bin/env python3
"""
Populate bridge.game_xref table by matching games between Retrosheet and MLB.

This script matches games from core.games (Retrosheet) with core.live_games (MLB)
using date and team IDs, with bridge.team_xref for team ID translation.
"""

import os
import psycopg2
from psycopg2 import Error
from dotenv import load_dotenv

load_dotenv()


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


def populate_game_xref():
    """Populate bridge.game_xref by matching games between Retrosheet and MLB."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Match games using date, team IDs, and game number to handle doubleheaders
            # Extract MLB team IDs, date, and game number from raw_payload JSON, translate to Retrosheet IDs via bridge.team_xref
            # Use DISTINCT ON to pick one match per mlb_game_pk to avoid duplicates
            cur.execute("""
                WITH mlb_games AS (
                    SELECT 
                        lg.mlb_game_pk,
                        (lg.raw_payload->'gameData'->'datetime'->>'originalDate')::date AS game_date,
                        (lg.raw_payload->'gameData'->'game'->>'gameNumber')::int AS game_number,
                        (lg.raw_payload->'gameData'->'teams'->'home'->>'id')::int AS mlb_home_id,
                        (lg.raw_payload->'gameData'->'teams'->'away'->>'id')::int AS mlb_away_id
                    FROM core.live_games lg
                    WHERE lg.mlb_game_pk IS NOT NULL
                    AND lg.raw_payload IS NOT NULL
                    AND (lg.raw_payload->'gameData'->'datetime'->>'originalDate') IS NOT NULL
                ),
                matched_games AS (
                    SELECT DISTINCT ON (mg.mlb_game_pk)
                        rg.game_id AS retrosheet_game_id,
                        mg.mlb_game_pk,
                        rg.game_date,
                        rg.home_team_id AS retrosheet_home_team_id,
                        rg.away_team_id AS retrosheet_away_team_id,
                        mg.mlb_home_id AS mlb_home_team_id,
                        mg.mlb_away_id AS mlb_away_team_id
                    FROM core.games rg
                    JOIN mlb_games mg ON rg.game_date = mg.game_date
                    JOIN bridge.team_xref txh ON mg.mlb_home_id = txh.mlb_team_id AND rg.home_team_id = txh.retrosheet_team_id
                    JOIN bridge.team_xref txa ON mg.mlb_away_id = txa.mlb_team_id AND rg.away_team_id = txa.retrosheet_team_id
                    ORDER BY mg.mlb_game_pk, COALESCE(rg.game_number, 0) = COALESCE(mg.game_number, 0) DESC
                )
                INSERT INTO bridge.game_xref (
                    retrosheet_game_id,
                    mlb_game_pk,
                    game_date,
                    retrosheet_home_team_id,
                    retrosheet_away_team_id,
                    mlb_home_team_id,
                    mlb_away_team_id
                )
                SELECT 
                    retrosheet_game_id,
                    mlb_game_pk,
                    game_date,
                    retrosheet_home_team_id,
                    retrosheet_away_team_id,
                    mlb_home_team_id,
                    mlb_away_team_id
                FROM matched_games
                ON CONFLICT (retrosheet_game_id) DO UPDATE SET
                    mlb_game_pk = EXCLUDED.mlb_game_pk,
                    game_date = EXCLUDED.game_date,
                    retrosheet_home_team_id = EXCLUDED.retrosheet_home_team_id,
                    retrosheet_away_team_id = EXCLUDED.retrosheet_away_team_id,
                    mlb_home_team_id = EXCLUDED.mlb_home_team_id,
                    mlb_away_team_id = EXCLUDED.mlb_away_team_id
            """)
            
            matched_count = cur.rowcount
            conn.commit()
            print(f"Matched and inserted {matched_count} games in bridge.game_xref")
            
            # Check for unmatched games
            cur.execute("""
                SELECT COUNT(*) 
                FROM core.live_games 
                WHERE mlb_game_pk IS NOT NULL 
                AND game_date_parsed IS NOT NULL
                AND game_id NOT IN (
                    SELECT retrosheet_game_id FROM bridge.game_xref WHERE retrosheet_game_id IS NOT NULL
                )
            """)
            unmatched_mlb = cur.fetchone()[0]
            print(f"Unmatched MLB games: {unmatched_mlb}")
            
            cur.execute("""
                SELECT COUNT(*) 
                FROM core.games 
                WHERE game_date >= '2026-01-01'
                AND game_id NOT IN (
                    SELECT retrosheet_game_id FROM bridge.game_xref
                )
            """)
            result = cur.fetchone()
            unmatched_retrosheet = result[0] if result else 0
            print(f"Unmatched Retrosheet games (2026+): {unmatched_retrosheet}")
            
            return matched_count
            
    except Error as e:
        print(f"Error populating game_xref: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


def main():
    print("Populating bridge.game_xref...")
    count = populate_game_xref()
    print(f"\nTotal games matched: {count}")


if __name__ == "__main__":
    main()
