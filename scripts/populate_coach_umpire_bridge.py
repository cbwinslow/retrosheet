#!/usr/bin/env python3
"""
Populate Coach and Umpire Bridge Tables
Extracts coach and umpire IDs from Retrosheet data and creates cross-reference mappings.

Usage:
    python3 scripts/populate_coach_umpire_bridge.py
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
            port=os.getenv("PGPORT", 5432),
            database=os.getenv("PGDATABASE", "retrosheet"),
            user=os.getenv("PGUSER", os.getenv("USER")),
            password=os.getenv("PGPASSWORD"),
        )


def populate_coach_xref():
    """Populate bridge.coach_xref from raw_retrosheet.coaches"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Extract unique coaches from raw_retrosheet.coaches
            # Note: coaches table doesn't have name columns, populate with ID only for now
            # This is a placeholder - coach names would need to be sourced from elsewhere
            cur.execute("""
                INSERT INTO bridge.coach_xref (retrosheet_coach_id, source_system, coach_name)
                SELECT DISTINCT 
                    coach_id,
                    'retrosheet' as source_system,
                    coach_id as coach_name
                FROM raw_retrosheet.coaches
                WHERE coach_id IS NOT NULL
                ON CONFLICT (retrosheet_coach_id) DO UPDATE SET
                    coach_name = EXCLUDED.coach_name,
                    updated_at = NOW()
            """)
            
            coach_count = cur.rowcount
            conn.commit()
            print(f"Populated {coach_count} coaches in bridge.coach_xref")
            return coach_count
    except Exception as e:
        print(f"Error populating coach_xref: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


def populate_umpire_xref():
    """Populate bridge.umpire_xref from raw_retrosheet.season_umpires"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Extract unique umpires from raw_retrosheet.season_umpires
            # Use subquery to handle duplicates properly
            cur.execute("""
                INSERT INTO bridge.umpire_xref (retrosheet_umpire_id, source_system, umpire_name)
                SELECT DISTINCT ON (umpire_id)
                    umpire_id,
                    'retrosheet' as source_system,
                    first_name || ' ' || last_name as umpire_name
                FROM raw_retrosheet.season_umpires
                WHERE umpire_id IS NOT NULL
                ORDER BY umpire_id, season
                ON CONFLICT (retrosheet_umpire_id) DO NOTHING
            """)
            
            umpire_count = cur.rowcount
            conn.commit()
            print(f"Populated {umpire_count} umpires in bridge.umpire_xref")
            return umpire_count
    except Exception as e:
        print(f"Error populating umpire_xref: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


def main():
    print("Populating coach and umpire bridge tables...")
    
    coach_count = populate_coach_xref()
    umpire_count = populate_umpire_xref()
    
    print("\nSummary:")
    print(f"  Coaches: {coach_count}")
    print(f"  Umpires: {umpire_count}")
    print(f"  Total: {coach_count + umpire_count}")


if __name__ == "__main__":
    main()
