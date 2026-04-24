#!/usr/bin/env python3
"""
Populate bridge tables with player ID mappings from Chadwick Bureau Register.

This script downloads the latest Chadwick Bureau Register data and populates
the bridge.player_xref table with mappings between MLB, Retrosheet, and other
player ID systems.
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
import urllib.request
from pathlib import Path

import psycopg2


ROOT = Path(__file__).resolve().parents[1]

# bridge.team_xref is currently seasonless, so franchise moves/renames that share a
# single MLBAM team id can only map to one canonical Retrosheet team id here.
# These mappings prioritize the current/canonical franchise label for live scoring.
TEAM_ABBREVIATION_TO_RETROSHEET = {
    'ANA': 'ANA',
    'ATH': 'OAK',
    'ATL': 'ATL',
    'AZ': 'ARI',
    'BAL': 'BAL',
    'BOS': 'BOS',
    'CHC': 'CHN',
    'CIN': 'CIN',
    'CLE': 'CLE',
    'COL': 'COL',
    'CWS': 'CHA',
    'DET': 'DET',
    'FLA': 'MIA',
    'HOU': 'HOU',
    'KC': 'KCA',
    'LA': 'ANA',
    'LAA': 'ANA',
    'LAD': 'LAN',
    'MIA': 'MIA',
    'MIL': 'MIL',
    'MIN': 'MIN',
    'MON': 'WAS',
    'NYM': 'NYN',
    'NYY': 'NYA',
    'OAK': 'OAK',
    'PHI': 'PHI',
    'PIT': 'PIT',
    'SD': 'SDN',
    'SEA': 'SEA',
    'SF': 'SFN',
    'STL': 'SLN',
    'TB': 'TBA',
    'TEX': 'TEX',
    'TOR': 'TOR',
    'WSH': 'WAS',
}

# MLB venue ids are stable for a venue even as the display name changes.
# Using venue ids avoids name-alias drift for 2000-2025 park reconciliation.
MLB_VENUE_ID_TO_RETROSHEET_PARK = {
    1: 'ANA01',
    2: 'BAL12',
    3: 'BOS07',
    4: 'CHI12',
    5: 'CLE08',
    7: 'KAN06',
    8: 'MIN03',
    9: 'NYC16',
    10: 'OAK01',
    12: 'STP01',
    13: 'ARL02',
    14: 'TOR02',
    15: 'PHO01',
    16: 'ATL02',
    17: 'CHI11',
    18: 'CIN08',
    19: 'DEN02',
    20: 'MIA01',
    22: 'LOS03',
    23: 'MIL05',
    24: 'MON02',
    25: 'NYC17',
    26: 'PHI12',
    27: 'PIT07',
    28: 'SAN01',
    30: 'STL09',
    31: 'PIT08',
    32: 'MIL06',
    680: 'SEA03',
    2392: 'HOU03',
    2394: 'DET05',
    2395: 'SFO03',
    2523: 'TAM02',
    2602: 'CIN09',
    2680: 'SAN02',
    2681: 'PHI13',
    2721: 'WAS10',
    2889: 'STL10',
    3289: 'NYC20',
    3309: 'WAS11',
    3312: 'MIN04',
    3313: 'NYC21',
    4169: 'MIA02',
    4705: 'ATL03',
    5325: 'ARL03',
}


def database_kwargs() -> dict[str, str]:
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def download_chadwick_register() -> list[Path]:
    """Download all Chadwick Bureau Register data files."""
    base_url = 'https://github.com/chadwickbureau/register/raw/master/data/people-{}.csv'
    temp_dir = Path(tempfile.mkdtemp())
    files = []

    print('Downloading Chadwick Bureau Register files...')
    for suffix in '0123456789abcdef':
        url = base_url.format(suffix)
        local_file = temp_dir / f'chadwick_register_{suffix}.csv'

        try:
            urllib.request.urlretrieve(url, local_file)
            files.append(local_file)
            print(f'Downloaded people-{suffix}.csv')
        except Exception as e:
            print(f'Failed to download people-{suffix}.csv: {e}')
            break

    return files


def parse_chadwick_csv(file_paths: list[Path]) -> list[dict[str, str]]:
    """Parse Chadwick CSV files into records."""
    records = []
    for file_path in file_paths:
        print(f'Parsing {file_path.name}...')
        with file_path.open('r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
    return records


def insert_player_mappings(conn, records: list[dict[str, str]]) -> None:
    """Insert player ID mappings into bridge.player_xref table."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'bridge' AND table_name = 'player_xref'
            """,
        )
        columns = {row[0] for row in cur.fetchall()}

    canonical_schema = 'retrosheet_player_id' in columns

    with conn.cursor() as cur:
        inserted = 0
        for record in records:
            # Only insert records that have at least MLBAM or Retrosheet IDs
            mlb_id = record.get('key_mlbam')
            retro_id = record.get('key_retro')

            if not retro_id:
                continue

            # Prepare data
            data = {
                'retrosheet_player_id': retro_id or None,
                'mlb_player_id': int(mlb_id) if mlb_id else None,
                'chadwick_register_id': record.get('key_uuid') or None,
                'first_name': record.get('name_first') or None,
                'last_name': record.get('name_last') or None,
                'bats': (record.get('bats') or 'U')[:1].upper(),
                'throws': (record.get('throws') or 'U')[:1].upper(),
            }

            # Insert record
            if canonical_schema:
                cur.execute(
                    """
                    INSERT INTO bridge.player_xref (
                        retrosheet_player_id, mlb_player_id, chadwick_register_id,
                        first_name, last_name, bats, throws
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (retrosheet_player_id) DO UPDATE
                    SET mlb_player_id = EXCLUDED.mlb_player_id,
                        chadwick_register_id = EXCLUDED.chadwick_register_id,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        bats = EXCLUDED.bats,
                        throws = EXCLUDED.throws,
                        updated_at = now()
                """,
                    (
                        data['retrosheet_player_id'],
                        data['mlb_player_id'],
                        data['chadwick_register_id'],
                        data['first_name'],
                        data['last_name'],
                        data['bats'],
                        data['throws'],
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO bridge.player_xref (
                        retrosheet_id, mlb_id, baseball_reference_id,
                        name_first, name_last, source_notes, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, now())
                    ON CONFLICT (retrosheet_id) DO UPDATE
                    SET mlb_id = EXCLUDED.mlb_id,
                        baseball_reference_id = EXCLUDED.baseball_reference_id,
                        name_first = EXCLUDED.name_first,
                        name_last = EXCLUDED.name_last,
                        source_notes = EXCLUDED.source_notes,
                        updated_at = now()
                """,
                    (
                        data['retrosheet_player_id'],
                        data['mlb_player_id'],
                        record.get('key_bbref') or None,
                        data['first_name'],
                        data['last_name'],
                        json.dumps(
                            {
                                'chadwick_register_id': data['chadwick_register_id'],
                                'bats': data['bats'],
                                'throws': data['throws'],
                            },
                        ),
                    ),
                )

            inserted += 1
            if inserted % 10000 == 0:
                print(f'Inserted {inserted} player mappings...')

        conn.commit()
        print(f'Total player mappings inserted: {inserted}')


def insert_team_mappings(conn) -> None:
    """Populate bridge.team_xref with current/canonical MLBAM team mappings."""
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH latest_teams AS (
                SELECT DISTINCT ON (mlb_team_id)
                    mlb_team_id,
                    abbreviation,
                    team_name,
                    season
                FROM core.mlb_api_teams
                WHERE mlb_team_id IS NOT NULL
                ORDER BY mlb_team_id, season DESC
            )
            SELECT mlb_team_id, abbreviation, team_name, season
            FROM latest_teams
            ORDER BY mlb_team_id
            """,
        )
        teams = cur.fetchall()

    inserted = 0
    skipped = []
    with conn.cursor() as cur:
        for mlb_team_id, abbreviation, team_name, season in teams:
            retrosheet_team_id = TEAM_ABBREVIATION_TO_RETROSHEET.get(abbreviation)
            if retrosheet_team_id is None:
                skipped.append(
                    {
                        'mlb_team_id': mlb_team_id,
                        'abbreviation': abbreviation,
                        'team_name': team_name,
                        'season': season,
                        'reason': 'no canonical abbreviation mapping',
                    },
                )
                continue

            cur.execute(
                """
                UPDATE bridge.team_xref
                SET mlb_team_id = %s,
                    updated_at = now()
                WHERE retrosheet_team_id = %s
                """,
                (mlb_team_id, retrosheet_team_id),
            )
            if cur.rowcount == 0:
                skipped.append(
                    {
                        'mlb_team_id': mlb_team_id,
                        'abbreviation': abbreviation,
                        'team_name': team_name,
                        'season': season,
                        'reason': f'missing bridge.team_xref row for {retrosheet_team_id}',
                    },
                )
                continue

            inserted += 1

    conn.commit()
    print(f'Total team mappings updated: {inserted}')
    if skipped:
        print('Team mappings skipped:')
        for item in skipped:
            print(json.dumps(item, sort_keys=True))


def insert_park_mappings(conn) -> None:
    """Populate bridge.park_xref with MLB venue id mappings for 2000-2025 venues."""
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH venues AS (
                SELECT DISTINCT ON (venue_id)
                    venue_id,
                    venue_name,
                    season
                FROM core.mlb_api_teams
                WHERE venue_id IS NOT NULL
                ORDER BY venue_id, season DESC
            )
            SELECT venue_id, venue_name, season
            FROM venues
            ORDER BY venue_id
            """,
        )
        venues = cur.fetchall()

    inserted = 0
    skipped = []
    with conn.cursor() as cur:
        for venue_id, venue_name, season in venues:
            retrosheet_park_id = MLB_VENUE_ID_TO_RETROSHEET_PARK.get(venue_id)
            if retrosheet_park_id is None:
                skipped.append(
                    {
                        'venue_id': venue_id,
                        'venue_name': venue_name,
                        'season': season,
                        'reason': 'no canonical venue mapping',
                    },
                )
                continue

            cur.execute(
                """
                UPDATE bridge.park_xref
                SET mlb_venue_id = %s,
                    updated_at = now()
                WHERE retrosheet_park_id = %s
                """,
                (venue_id, retrosheet_park_id),
            )
            if cur.rowcount == 0:
                skipped.append(
                    {
                        'venue_id': venue_id,
                        'venue_name': venue_name,
                        'season': season,
                        'reason': f'missing bridge.park_xref row for {retrosheet_park_id}',
                    },
                )
                continue

            inserted += 1

    conn.commit()
    print(f'Total park mappings updated: {inserted}')
    if skipped:
        print('Park mappings skipped:')
        for item in skipped:
            print(json.dumps(item, sort_keys=True))


def populate_bridge_tables() -> None:
    """Main function to populate bridge tables."""
    try:
        # Download data
        data_files = download_chadwick_register()
        print(f'Downloaded {len(data_files)} Chadwick Register files')

        # Parse data
        records = parse_chadwick_csv(data_files)
        print(f'Parsed {len(records)} total records from Chadwick Register')

        # Connect to database and insert
        conn = psycopg2.connect(**database_kwargs())
        try:
            insert_player_mappings(conn, records)
            insert_team_mappings(conn)
            insert_park_mappings(conn)
            print('Bridge table population complete!')
        finally:
            conn.close()

        # Cleanup
        for data_file in data_files:
            data_file.unlink()
        data_files[0].parent.rmdir()

    except Exception as e:
        print(f'Error populating bridge tables: {e}')
        raise


if __name__ == '__main__':
    populate_bridge_tables()
