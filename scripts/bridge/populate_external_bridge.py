#!/usr/bin/env python3
"""
Populate External Bridge Tables
Uses bridge.player_xref as source of truth to map external player/team IDs to Retrosheet IDs.

Usage:
    python3 scripts/bridge/populate_external_bridge.py
"""

import os

import psycopg2
from dotenv import load_dotenv
from psycopg2 import Error


_ = load_dotenv()


def get_db_connection():
    """Get PostgreSQL connection from environment variables."""
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return psycopg2.connect(db_url)
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', '5432'),
        database=os.getenv('PGDATABASE', 'retrosheet'),
        user=os.getenv('PGUSER', os.getenv('USER')),
        password=os.getenv('PGPASSWORD'),
    )


def populate_statcast_player_xref():
    """Populate bridge.external_player_xref for Statcast using bridge.player_xref mlb_id mappings."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Pre-filter player_xref to only include rows with valid retrosheet_id
            cur.execute("""
                INSERT INTO bridge.external_player_xref (external_source, external_player_id, retrosheet_player_id)
                SELECT DISTINCT
                    'statcast' as external_source,
                    s.batter::text as external_player_id,
                    px.retrosheet_id as retrosheet_player_id
                FROM raw_mlb.statcast s
                JOIN (
                    SELECT mlb_id, retrosheet_id
                    FROM bridge.player_xref
                    WHERE mlb_id IS NOT NULL
                    AND retrosheet_id IS NOT NULL
                    AND retrosheet_id != ''
                ) px ON s.batter = px.mlb_id
                WHERE s.batter IS NOT NULL
                ON CONFLICT (external_source, external_player_id) DO UPDATE SET
                    retrosheet_player_id = EXCLUDED.retrosheet_player_id
            """)

            batter_count = cur.rowcount
            conn.commit()
            print(f'Populated {batter_count} Statcast batters in bridge.external_player_xref')

            # Map Statcast pitcher IDs to Retrosheet IDs via bridge.player_xref
            cur.execute("""
                INSERT INTO bridge.external_player_xref (external_source, external_player_id, retrosheet_player_id)
                SELECT DISTINCT
                    'statcast' as external_source,
                    s.pitcher::text as external_player_id,
                    px.retrosheet_id as retrosheet_player_id
                FROM raw_mlb.statcast s
                JOIN (
                    SELECT mlb_id, retrosheet_id
                    FROM bridge.player_xref
                    WHERE mlb_id IS NOT NULL
                    AND retrosheet_id IS NOT NULL
                    AND retrosheet_id != ''
                ) px ON s.pitcher = px.mlb_id
                WHERE s.pitcher IS NOT NULL
                ON CONFLICT (external_source, external_player_id) DO UPDATE SET
                    retrosheet_player_id = EXCLUDED.retrosheet_player_id
            """)

            pitcher_count = cur.rowcount
            conn.commit()
            print(f'Populated {pitcher_count} Statcast pitchers in bridge.external_player_xref')

            return batter_count + pitcher_count
    except Error as e:
        print(f'Error populating statcast_player_xref: {e}')
        conn.rollback()
        return 0
    finally:
        conn.close()


def populate_bref_player_xref():
    """Populate bridge.external_player_xref for Baseball Reference using bridge.player_xref baseball_reference_id mappings."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Map Baseball Reference IDs to Retrosheet IDs via bridge.player_xref
            cur.execute("""
                INSERT INTO bridge.external_player_xref (external_source, external_player_id, retrosheet_player_id)
                SELECT DISTINCT
                    'baseball_reference' as external_source,
                    px.baseball_reference_id as external_player_id,
                    px.retrosheet_id as retrosheet_player_id
                FROM bridge.player_xref px
                WHERE px.baseball_reference_id IS NOT NULL
                AND px.baseball_reference_id != ''
                AND px.retrosheet_id IS NOT NULL
                AND px.retrosheet_id != ''
                ON CONFLICT (external_source, external_player_id) DO UPDATE SET
                    retrosheet_player_id = EXCLUDED.retrosheet_player_id
            """)

            bref_count = cur.rowcount
            conn.commit()
            print(
                f'Populated {bref_count} Baseball Reference players in bridge.external_player_xref',
            )
            return bref_count
    except Error as e:
        print(f'Error populating bref_player_xref: {e}')
        conn.rollback()
        return 0
    finally:
        conn.close()


def populate_lahman_player_xref():
    """Populate bridge.external_player_xref for Lahman using retroID column."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Map Lahman playerID to Retrosheet IDs via retroID column
            cur.execute("""
                INSERT INTO bridge.external_player_xref (external_source, external_player_id, retrosheet_player_id)
                SELECT DISTINCT
                    'lahman' as external_source,
                    l."playerID" as external_player_id,
                    l."retroID" as retrosheet_player_id
                FROM lahman.people l
                WHERE l."retroID" IS NOT NULL
                AND l."retroID" != ''
                ON CONFLICT (external_source, external_player_id) DO UPDATE SET
                    retrosheet_player_id = EXCLUDED.retrosheet_player_id
            """)

            lahman_count = cur.rowcount
            conn.commit()
            print(f'Populated {lahman_count} Lahman players in bridge.external_player_xref')
            return lahman_count
    except Error as e:
        print(f'Error populating lahman_player_xref: {e}')
        conn.rollback()
        return 0
    finally:
        conn.close()


def main():
    print('Populating external bridge tables...')

    statcast_count = populate_statcast_player_xref()
    bref_count = populate_bref_player_xref()
    lahman_count = populate_lahman_player_xref()

    print('\nSummary:')
    print(f'  Statcast players: {statcast_count}')
    print(f'  Baseball Reference players: {bref_count}')
    print(f'  Lahman players: {lahman_count}')
    print(f'  Total: {statcast_count + bref_count + lahman_count}')


if __name__ == '__main__':
    main()
