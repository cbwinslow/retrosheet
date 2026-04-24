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
from psycopg2 import Error


load_dotenv()


def get_db_connection():
    """Get PostgreSQL connection from environment variables."""
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return psycopg2.connect(db_url)
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', 5432),
        database=os.getenv('PGDATABASE', 'retrosheet'),
        user=os.getenv('PGUSER', os.getenv('USER')),
        password=os.getenv('PGPASSWORD'),
    )


def populate_coach_xref():
    """Populate bridge.coach_xref from raw_retrosheet.coaches with names from biofile_legacy"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Extract unique coaches from raw_retrosheet.coaches
            # Join with biofile_legacy to get coach names (coach_id matches player_id)
            cur.execute("""
                INSERT INTO bridge.coach_xref (retrosheet_coach_id, source_system, coach_name, confidence_score, confidence_source)
                SELECT DISTINCT
                    c.coach_id,
                    'retrosheet' as source_system,
                    COALESCE(b.use_name, b.full_name, b.last_name, c.coach_id) as coach_name,
                    0.9 as confidence_score,
                    'biofile_legacy_name_match' as confidence_source
                FROM raw_retrosheet.coaches c
                LEFT JOIN raw_retrosheet.biofile_legacy b ON c.coach_id = b.player_id
                WHERE c.coach_id IS NOT NULL
                ON CONFLICT (retrosheet_coach_id) DO UPDATE SET
                    coach_name = EXCLUDED.coach_name,
                    confidence_score = EXCLUDED.confidence_score,
                    confidence_source = EXCLUDED.confidence_source,
                    updated_at = NOW()
            """)

            coach_count = cur.rowcount
            conn.commit()
            print(
                f'Populated {coach_count} coaches in bridge.coach_xref with names from biofile_legacy',
            )
            return coach_count
    except Error as e:
        print(f'Error populating coach_xref: {e}')
        conn.rollback()
        return 0
    finally:
        conn.close()


def populate_umpire_xref():
    """Populate bridge.umpire_xref from raw_retrosheet.season_umpires with biofile_legacy cross-reference"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Extract unique umpires from raw_retrosheet.season_umpires
            # Cross-reference with biofile_legacy for players who became umpires
            # Use subquery to handle duplicates properly
            cur.execute("""
                INSERT INTO bridge.umpire_xref (retrosheet_umpire_id, source_system, umpire_name, confidence_score, confidence_source)
                SELECT DISTINCT ON (u.umpire_id)
                    u.umpire_id,
                    'retrosheet' as source_system,
                    COALESCE(
                        CASE WHEN b.player_id IS NOT NULL THEN b.use_name || ' (former player)' END,
                        u.first_name || ' ' || u.last_name
                    ) as umpire_name,
                    CASE WHEN b.player_id IS NOT NULL THEN 0.9 ELSE 0.7 END as confidence_score,
                    CASE WHEN b.player_id IS NOT NULL THEN 'biofile_legacy_player_match' ELSE 'retrosheet_name_only' END as confidence_source
                FROM raw_retrosheet.season_umpires u
                LEFT JOIN raw_retrosheet.biofile_legacy b ON
                    (u.last_name = b.last_name OR u.last_name = b.use_name)
                    AND b.umpire_debut IS NOT NULL
                WHERE u.umpire_id IS NOT NULL
                ORDER BY u.umpire_id, u.season
                ON CONFLICT (retrosheet_umpire_id) DO UPDATE SET
                    umpire_name = EXCLUDED.umpire_name,
                    confidence_score = EXCLUDED.confidence_score,
                    confidence_source = EXCLUDED.confidence_source,
                    updated_at = NOW()
            """)

            umpire_count = cur.rowcount
            conn.commit()
            print(
                f'Populated {umpire_count} umpires in bridge.umpire_xref with biofile_legacy cross-reference',
            )
            return umpire_count
    except Error as e:
        print(f'Error populating umpire_xref: {e}')
        conn.rollback()
        return 0
    finally:
        conn.close()


def main():
    print('Populating coach and umpire bridge tables...')

    coach_count = populate_coach_xref()
    umpire_count = populate_umpire_xref()

    print('\nSummary:')
    print(f'  Coaches: {coach_count}')
    print(f'  Umpires: {umpire_count}')
    print(f'  Total: {coach_count + umpire_count}')


if __name__ == '__main__':
    main()
