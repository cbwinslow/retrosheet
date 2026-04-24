#!/usr/bin/env python3
"""
Investigate Coach Name Resolution
Tests whether coach names can be resolved using biofile_legacy data.

Hypothesis: coach_id in raw_retrosheet.coaches may match player_id in raw_retrosheet.biofile_legacy,
allowing us to use the name fields from biofile_legacy to populate coach_name in bridge.coach_xref.
"""

import os

import psycopg2
from dotenv import load_dotenv
from psycopg2 import Error

_ = load_dotenv()


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


def investigate_coach_name_resolution():
    """Investigate whether coach names can be resolved using biofile_legacy."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            print("Investigating coach name resolution options...\n")

            # Check if biofile_legacy table exists and has data
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'raw_retrosheet' 
                    AND table_name = 'biofile_legacy'
                )
            """)
            biofile_exists = cur.fetchone()[0]
            print(f"biofile_legacy table exists: {biofile_exists}")

            if biofile_exists:
                cur.execute("SELECT COUNT(*) FROM raw_retrosheet.biofile_legacy")
                biofile_count = cur.fetchone()[0]
                print(f"biofile_legacy row count: {biofile_count}")

                # Check if coaches table exists and has data
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'raw_retrosheet' 
                        AND table_name = 'coaches'
                    )
                """)
                coaches_exists = cur.fetchone()[0]
                print(f"coaches table exists: {coaches_exists}")

                if coaches_exists:
                    cur.execute("SELECT COUNT(*) FROM raw_retrosheet.coaches")
                    coaches_count = cur.fetchone()[0]
                    print(f"coaches row count: {coaches_count}")

                    # Test hypothesis: Can coach_id match player_id in biofile_legacy?
                    print("\n--- Testing coach_id to player_id matching ---")
                    cur.execute("""
                        SELECT 
                            COUNT(DISTINCT c.coach_id) as total_coaches,
                            COUNT(DISTINCT b.player_id) as matching_players,
                            ROUND(100.0 * COUNT(DISTINCT b.player_id) / NULLIF(COUNT(DISTINCT c.coach_id), 0), 2) as match_percentage
                        FROM raw_retrosheet.coaches c
                        LEFT JOIN raw_retrosheet.biofile_legacy b ON c.coach_id = b.player_id
                    """)
                    result = cur.fetchone()
                    print(f"Total coaches: {result[0]}")
                    print(f"Matching players in biofile_legacy: {result[1]}")
                    print(f"Match percentage: {result[2]}%")

                    # Show sample matches
                    print("\n--- Sample coach_id matches ---")
                    cur.execute("""
                        SELECT 
                            c.coach_id,
                            c.season,
                            c.team_id,
                            c.role,
                            b.player_id,
                            b.last_name,
                            b.use_name,
                            b.full_name,
                            b.coach_debut,
                            b.coach_lastgame
                        FROM raw_retrosheet.coaches c
                        JOIN raw_retrosheet.biofile_legacy b ON c.coach_id = b.player_id
                        LIMIT 10
                    """)
                    samples = cur.fetchall()
                    for sample in samples:
                        print(
                            f"  Coach ID: {sample[0]}, Season: {sample[1]}, Team: {sample[2]}, Role: {sample[3]}"
                        )
                        print(f"    Name: {sample[6]} (Last: {sample[4]}, Use: {sample[5]})")
                        print(f"    Coaching: {sample[7]} - {sample[8]}")

                    # Check for coaches without biofile matches
                    print("\n--- Coaches without biofile matches ---")
                    cur.execute("""
                        SELECT 
                            COUNT(DISTINCT c.coach_id) as unmatched_count
                        FROM raw_retrosheet.coaches c
                        LEFT JOIN raw_retrosheet.biofile_legacy b ON c.coach_id = b.player_id
                        WHERE b.player_id IS NULL
                    """)
                    unmatched = cur.fetchone()[0]
                    print(f"Unmatched coaches: {unmatched}")

                    if unmatched > 0:
                        print("\nSample unmatched coaches:")
                        cur.execute("""
                            SELECT DISTINCT c.coach_id, c.team_id, c.role
                            FROM raw_retrosheet.coaches c
                            LEFT JOIN raw_retrosheet.biofile_legacy b ON c.coach_id = b.player_id
                            WHERE b.player_id IS NULL
                            LIMIT 10
                        """)
                        for row in cur.fetchall():
                            print(f"  Coach ID: {row[0]}, Team: {row[1]}, Role: {row[2]}")

                    # Recommendation
                    print("\n--- Recommendation ---")
                    if result[2] >= 70:
                        print(
                            f"✅ GOOD: {result[2]}% of coaches can be resolved via biofile_legacy"
                        )
                        print(
                            "Recommendation: Use biofile_legacy to populate coach names for matched coaches"
                        )
                        print(
                            "For unmatched coaches, investigate alternative sources (MLB API, Baseball Reference)"
                        )
                    elif result[2] >= 50:
                        print(
                            f"⚠️  MODERATE: {result[2]}% of coaches can be resolved via biofile_legacy"
                        )
                        print(
                            "Recommendation: Use biofile_legacy as primary source, investigate alternatives for remaining"
                        )
                    else:
                        print(
                            f"❌ POOR: Only {result[2]}% of coaches can be resolved via biofile_legacy"
                        )
                        print(
                            "Recommendation: Investigate alternative primary sources (MLB API, Baseball Reference)"
                        )

                else:
                    print("coaches table does not exist - cannot investigate")
            else:
                print("biofile_legacy table does not exist - cannot investigate")

    except Error as e:
        print(f"Error investigating coach name resolution: {e}")
    finally:
        conn.close()


def main():
    investigate_coach_name_resolution()


if __name__ == "__main__":
    main()
