#!/usr/bin/env python3
"""
Populate season-aware team_xref with valid_from_season and valid_to_season columns.

This script:
1. Populates valid_from_season and valid_to_season for all teams based on core.games data
2. Handles franchise moves by creating separate entries for each franchise period
3. Keeps current team entries with valid_to_season = NULL for active teams

Usage:
    python3 scripts/bridge/populate_season_aware_team_xref.py
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


def populate_season_aware_team_xref():
    """Populate valid_from_season and valid_to_season for bridge.team_xref."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # First, populate basic season ranges for all teams from core.games
            cur.execute("""
                UPDATE bridge.team_xref tx
                SET
                    valid_from_season = g.first_season,
                    valid_to_season = CASE WHEN g.last_season >= 2025 THEN NULL ELSE g.last_season END
                FROM (
                    SELECT
                        team_id,
                        MIN(season) as first_season,
                        MAX(season) as last_season
                    FROM (
                        SELECT home_team_id as team_id, season FROM core.games
                        UNION ALL
                        SELECT away_team_id as team_id, season FROM core.games
                    ) all_games
                    GROUP BY team_id
                ) g
                WHERE tx.retrosheet_team_id = g.team_id
            """)

            basic_count = cur.rowcount
            conn.commit()
            print(f'Updated {basic_count} teams with basic season ranges')

            # Handle franchise moves by inserting new entries for historical teams
            # Montreal Expos -> Washington Nationals
            cur.execute("""
                INSERT INTO bridge.team_xref (retrosheet_team_id, mlb_team_id, abbreviation, name, valid_from_season, valid_to_season)
                VALUES ('MON', 120, 'MON', 'Montreal Expos', 1969, 2004)
                ON CONFLICT (retrosheet_team_id) DO UPDATE SET
                    valid_from_season = EXCLUDED.valid_from_season,
                    valid_to_season = EXCLUDED.valid_to_season
            """)

            # Florida Marlins -> Miami Marlins
            cur.execute("""
                INSERT INTO bridge.team_xref (retrosheet_team_id, mlb_team_id, abbreviation, name, valid_from_season, valid_to_season)
                VALUES ('FLO', 146, 'FLO', 'Florida Marlins', 1993, 2011)
                ON CONFLICT (retrosheet_team_id) DO UPDATE SET
                    valid_from_season = EXCLUDED.valid_from_season,
                    valid_to_season = EXCLUDED.valid_to_season
            """)

            # Update Washington Nationals to show it started in 2005
            cur.execute("""
                UPDATE bridge.team_xref
                SET valid_from_season = 2005
                WHERE retrosheet_team_id = 'WAS'
            """)

            # Update Miami Marlins to show it started in 2012
            cur.execute("""
                UPDATE bridge.team_xref
                SET valid_from_season = 2012
                WHERE retrosheet_team_id = 'MIA'
            """)

            conn.commit()
            print('Added franchise move entries for MON->WAS and FLO->MIA')

            # Verify the season ranges
            cur.execute("""
                SELECT retrosheet_team_id, abbreviation, name, valid_from_season, valid_to_season
                FROM bridge.team_xref
                WHERE retrosheet_team_id IN ('MON', 'WAS', 'FLO', 'MIA')
                ORDER BY retrosheet_team_id
            """)

            print('\nFranchise move entries:')
            for row in cur.fetchall():
                if len(row) >= 5:
                    print(f'  {row[0]} ({row[1]}): {row[3]}-{row[4] if row[4] else "present"}')
                else:
                    print(f'  {row[0]}: insufficient data')

            return basic_count

    except Error as e:
        print(f'Error populating season-aware team_xref: {e}')
        conn.rollback()
        return 0
    finally:
        conn.close()


def main():
    print('Populating season-aware bridge.team_xref...')
    count = populate_season_aware_team_xref()
    print(f'\nTotal teams updated: {count}')


if __name__ == '__main__':
    main()
