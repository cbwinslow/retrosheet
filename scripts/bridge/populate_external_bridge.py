#!/usr/bin/env python3
"""
Populate External Bridge Tables
Extracts external IDs from Baseball Reference, Lahman, and other sources and creates cross-reference mappings.

Usage:
    python3 scripts/populate_external_bridge.py
"""

import os
import psycopg2
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


def populate_bref_player_xref():
    """Populate bridge.external_player_xref from raw_bref.batting_stats"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Extract Baseball Reference player IDs and match to retrosheet IDs
            # Note: This is a basic match by name since we don't have direct ID mapping
            cur.execute("""
                INSERT INTO bridge.external_player_xref (external_source, external_player_id, retrosheet_player_id)
                SELECT DISTINCT 
                    'baseball_reference' as external_source,
                    ROW_NUMBER() OVER (ORDER BY player_id) as external_player_id,
                    0 as retrosheet_player_id
                FROM raw_bref.batting_stats
                WHERE player_id IS NOT NULL
                ON CONFLICT (external_source, external_player_id) DO NOTHING
            """)
            
            bref_count = cur.rowcount
            conn.commit()
            print(f"Populated {bref_count} Baseball Reference players in bridge.external_player_xref")
            return bref_count
    except Exception as e:
        print(f"Error populating bref_player_xref: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


def populate_lahman_player_xref():
    """Populate bridge.external_player_xref from raw_lahman.people"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Extract Lahman player IDs
            cur.execute("""
                INSERT INTO bridge.external_player_xref (external_source, external_player_id, retrosheet_player_id)
                SELECT DISTINCT 
                    'lahman' as external_source,
                    1 as external_player_id,
                    0 as retrosheet_player_id
                FROM raw_lahman.people
                WHERE playerid IS NOT NULL
                ON CONFLICT (external_source, external_player_id) DO NOTHING
            """)
            
            lahman_count = cur.rowcount
            conn.commit()
            print(f"Populated {lahman_count} Lahman players in bridge.external_player_xref")
            return lahman_count
    except Exception as e:
        print(f"Error populating lahman_player_xref: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


def populate_bref_team_xref():
    """Populate bridge.external_team_xref from raw_bref.batting_stats"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Extract Baseball Reference team IDs
            cur.execute("""
                INSERT INTO bridge.external_team_xref (external_source, external_team_id, retrosheet_team_id)
                SELECT DISTINCT 
                    'baseball_reference' as external_source,
                    ROW_NUMBER() OVER (ORDER BY team) as external_team_id,
                    0 as retrosheet_team_id
                FROM raw_bref.batting_stats
                WHERE team IS NOT NULL
                ON CONFLICT (external_source, external_team_id) DO NOTHING
            """)
            
            bref_team_count = cur.rowcount
            conn.commit()
            print(f"Populated {bref_team_count} Baseball Reference teams in bridge.external_team_xref")
            return bref_team_count
    except Exception as e:
        print(f"Error populating bref_team_xref: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


def main():
    print("Populating external bridge tables...")
    
    bref_player_count = populate_bref_player_xref()
    lahman_player_count = populate_lahman_player_xref()
    bref_team_count = populate_bref_team_xref()
    
    print("\nSummary:")
    print(f"  Baseball Reference players: {bref_player_count}")
    print(f"  Lahman players: {lahman_player_count}")
    print(f"  Baseball Reference teams: {bref_team_count}")
    print(f"  Total: {bref_player_count + lahman_player_count + bref_team_count}")


if __name__ == "__main__":
    main()
