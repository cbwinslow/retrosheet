#!/usr/bin/env python3
"""
File: scripts/data_ingestion/fetch_baseball_reference_complete.py
Purpose: Fetch Baseball-Reference data - complete game logs
Author: Agent Cascade
Date: 2026-04-25
Usage: uv run python scripts/data_ingestion/fetch_baseball_reference_complete.py --season 2025

Fills empty table:
- raw_baseball_reference.game_logs (currently 0 rows)

Note: Baseball-Reference uses scraping or pybaseball library
"""

import argparse
import hashlib
import json
import os
import time

import psycopg2
from dotenv import load_dotenv


try:
    from pybaseball import batting_stats, pitching_stats, schedule_and_record

    PYBASEBALL_AVAILABLE = True
except ImportError:
    PYBASEBALL_AVAILABLE = False
    print('Warning: pybaseball not installed. Install with: uv add pybaseball')

load_dotenv()


def get_db_conn():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        dbname=os.getenv('POSTGRES_DB', 'retrosheet'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
    )


def fetch_br_schedule(season: int, team: str):
    """Fetch team schedule from Baseball-Reference."""
    if not PYBASEBALL_AVAILABLE:
        return None

    try:
        df = schedule_and_record(season, team)
        return df.to_dict('records')
    except Exception as e:
        print(f'  Error fetching {team}: {e}')
        return None


def store_br_game_logs(conn, season: int, team: str, games: list):
    """Store Baseball-Reference game logs."""
    cur = conn.cursor()
    inserted = 0

    for game in games:
        try:
            # Generate a unique game ID
            game_date = game.get('Date', '')
            opponent = game.get('Opp', '')

            if not game_date:
                continue

            # Create unique ID
            game_id = f'{season}_{team}_{game_date}_{opponent}'
            game_id_hash = hashlib.md5(game_id.encode()).hexdigest()

            payload_json = json.dumps(game, sort_keys=True)
            checksum = hashlib.md5(payload_json.encode()).hexdigest()

            cur.execute(
                """
                INSERT INTO raw_baseball_reference.game_logs (
                    game_date, season, team, opponent, 
                    http_status, response_time_ms, payload, checksum
                ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (checksum) DO NOTHING
                RETURNING id;
            """,
                (
                    game_date,
                    season,
                    team,
                    opponent,
                    200,
                    0,
                    payload_json,
                    checksum,
                ),
            )

            if cur.fetchone():
                inserted += 1

            if inserted % 50 == 0:
                conn.commit()

        except Exception as e:
            print(f'  Error storing game: {e}')
            continue

    conn.commit()
    cur.close()
    return inserted


def fetch_br_batting_stats(season: int):
    """Fetch batting stats from Baseball-Reference."""
    if not PYBASEBALL_AVAILABLE:
        return None

    try:
        df = batting_stats(season)
        return df.to_dict('records')
    except Exception as e:
        print(f'  Error fetching batting stats: {e}')
        return None


def fetch_br_pitching_stats(season: int):
    """Fetch pitching stats from Baseball-Reference."""
    if not PYBASEBALL_AVAILABLE:
        return None

    try:
        df = pitching_stats(season)
        return df.to_dict('records')
    except Exception as e:
        print(f'  Error fetching pitching stats: {e}')
        return None


def main():
    parser = argparse.ArgumentParser(description='Fetch Baseball-Reference data')
    parser.add_argument('--season', type=int, required=True)
    parser.add_argument('--teams', nargs='+', help='Specific teams to fetch')
    parser.add_argument('--skip-schedule', action='store_true')
    parser.add_argument('--skip-stats', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if not PYBASEBALL_AVAILABLE:
        print('ERROR: pybaseball library required')
        print('Install: uv add pybaseball')
        return

    conn = get_db_conn()

    try:
        print('=' * 70)
        print(f'Fetching Baseball-Reference Data - Season {args.season}')
        print('=' * 70)

        # Teams to fetch (MLB teams)
        teams = args.teams or [
            'ARI',
            'ATL',
            'BAL',
            'BOS',
            'CHC',
            'CHW',
            'CIN',
            'CLE',
            'COL',
            'DET',
            'HOU',
            'KCR',
            'LAA',
            'LAD',
            'MIA',
            'MIL',
            'MIN',
            'NYM',
            'NYY',
            'OAK',
            'PHI',
            'PIT',
            'SDP',
            'SEA',
            'SFG',
            'STL',
            'TBR',
            'TEX',
            'TOR',
            'WSN',
        ]

        if not args.skip_schedule and not args.dry_run:
            print(f'\nFetching schedules for {len(teams)} teams...')

            total_games = 0
            for i, team in enumerate(teams):
                print(f'  [{i + 1}/{len(teams)}] {team}...', end=' ')

                games = fetch_br_schedule(args.season, team)
                if games:
                    count = store_br_game_logs(conn, args.season, team, games)
                    total_games += count
                    print(f'{count} games')
                else:
                    print('failed')

                time.sleep(1)  # Rate limiting

            print(f'\nTotal games stored: {total_games:,}')

        if not args.skip_stats and not args.dry_run:
            print('\nFetching batting stats...')
            batting = fetch_br_batting_stats(args.season)
            if batting:
                print(f'  Found {len(batting):,} batting records')

            print('\nFetching pitching stats...')
            pitching = fetch_br_pitching_stats(args.season)
            if pitching:
                print(f'  Found {len(pitching):,} pitching records')

        if args.dry_run:
            print('\nDRY RUN - Would fetch:')
            print(f'  - Schedules for {len(teams)} teams')
            print(f'  - Batting stats for season {args.season}')
            print(f'  - Pitching stats for season {args.season}')

        # Summary
        if not args.dry_run:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM raw_baseball_reference.game_logs')
            log_count = cur.fetchone()[0]
            cur.close()

            print('=' * 70)
            print('SUMMARY')
            print('=' * 70)
            print(f'raw_baseball_reference.game_logs: {log_count:,}')
            print('=' * 70)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
