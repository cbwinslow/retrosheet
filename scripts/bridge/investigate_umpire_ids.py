#!/usr/bin/env python3
"""
Investigate Umpire MLB ID Mapping
Tests whether umpire names can be matched to MLB IDs using available data sources.

Hypothesis: Umpire names in raw_retrosheet.season_umpires may be matchable to MLB umpire IDs
via MLB Stats API or other sources.
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
        port=os.getenv('PGPORT', '5432'),
        database=os.getenv('PGDATABASE', 'retrosheet'),
        user=os.getenv('PGUSER', os.getenv('USER')),
        password=os.getenv('PGPASSWORD'),
    )


def investigate_umpire_mlb_id_mapping():
    """Investigate whether umpire names can be matched to MLB IDs."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            print('Investigating umpire MLB ID mapping options...\n')

            # Check if season_umpires table exists and has data
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'raw_retrosheet'
                    AND table_name = 'season_umpires'
                )
            """)
            umpires_exists = cur.fetchone()[0]
            print(f'season_umpires table exists: {umpires_exists}')

            if umpires_exists:
                cur.execute('SELECT COUNT(*) FROM raw_retrosheet.season_umpires')
                umpires_count = cur.fetchone()[0]
                print(f'season_umpires row count: {umpires_count}')

                # Get sample umpire data
                print('\n--- Sample Retrosheet umpire data ---')
                cur.execute("""
                    SELECT
                        umpire_id,
                        last_name,
                        first_name,
                        season
                    FROM raw_retrosheet.season_umpires
                    LIMIT 10
                """)
                samples = cur.fetchall()
                for sample in samples:
                    print(
                        f'  Umpire ID: {sample[0]}, Name: {sample[2]} {sample[1]}, Season: {sample[3]}',
                    )

                # Check for unique umpires
                cur.execute("""
                    SELECT
                        COUNT(DISTINCT umpire_id) as unique_umpires,
                        COUNT(DISTINCT last_name || ' ' || first_name) as unique_names
                    FROM raw_retrosheet.season_umpires
                """)
                result = cur.fetchone()
                print(f'\nUnique umpire IDs: {result[0]}')
                print(f'Unique umpire names: {result[1]}')

                # Check if MLB data has umpire information
                print('\n--- Checking for MLB umpire data ---')
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'raw_mlb'
                        AND table_name = 'live_games'
                    )
                """)
                live_games_exists = cur.fetchone()[0]
                print(f'live_games table exists: {live_games_exists}')

                if live_games_exists:
                    # Check if live_games has umpire IDs in raw_payload
                    cur.execute("""
                        SELECT COUNT(*)
                        FROM core.live_games
                        WHERE raw_payload IS NOT NULL
                    """)
                    live_games_count = cur.fetchone()[0]
                    print(f'live_games with raw_payload: {live_games_count}')

                    if live_games_count > 0:
                        # Sample raw_payload to check for umpire IDs
                        cur.execute("""
                            SELECT raw_payload::text
                            FROM core.live_games
                            WHERE raw_payload IS NOT NULL
                            LIMIT 1
                        """)
                        payload = cur.fetchone()
                        if payload and payload[0]:
                            print(f'Sample raw_payload length: {len(payload[0])} chars')
                            # Check for umpire-related keys
                            if 'umpire' in payload[0].lower() or 'officials' in payload[0].lower():
                                print('✓ Raw payload contains umpire/officials data')
                            else:
                                print('✗ Raw payload does not contain obvious umpire data')

                # Check if biofile_legacy has umpire information
                print('\n--- Checking biofile_legacy for umpire data ---')
                cur.execute("""
                    SELECT COUNT(*)
                    FROM raw_retrosheet.biofile_legacy
                    WHERE umpire_debut IS NOT NULL
                """)
                umpire_players = cur.fetchone()[0]
                print(f'Players with umpire debut dates: {umpire_players}')

                if umpire_players > 0:
                    print('\nSample players who were umpires:')
                    cur.execute("""
                        SELECT
                            player_id,
                            last_name,
                            use_name,
                            umpire_debut,
                            umpire_lastgame
                        FROM raw_retrosheet.biofile_legacy
                        WHERE umpire_debut IS NOT NULL
                        LIMIT 5
                    """)
                    for row in cur.fetchall():
                        print(f'  {row[1]} ({row[2]}): {row[3]} - {row[4]}')

                # Recommendation
                print('\n--- Recommendation ---')
                if live_games_exists and live_games_count > 0:
                    print('✅ MLB live_games data available')
                    print(
                        'Recommendation: Investigate MLB API raw_payload structure for umpire IDs',
                    )
                    print(
                        'Next step: Extract umpire IDs from live_games raw_payload and match to umpire names',
                    )
                elif umpire_players > 0:
                    print(
                        '⚠️  Some umpire information in biofile_legacy (players who became umpires)',
                    )
                    print(
                        'Recommendation: This may help for historical umpires who were also players',
                    )
                    print(
                        'Next step: Cross-reference umpire names with biofile_legacy player names',
                    )
                else:
                    print('❌ No obvious MLB umpire ID sources available')
                    print(
                        'Recommendation: Investigate external sources (MLB Stats API umpire endpoint, Baseball Reference)',
                    )
                    print('Alternative: Use name-based matching with external APIs')

    except Error as e:
        print(f'Error investigating umpire MLB ID mapping: {e}')
    finally:
        conn.close()


def main():
    investigate_umpire_mlb_id_mapping()


if __name__ == '__main__':
    main()
