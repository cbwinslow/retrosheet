#!/usr/bin/env python3
"""
Automated MLB live data ingestion workflow.

This script orchestrates the complete live data ingestion pipeline:
1. Fetch current MLB schedule and identify active games
2. Fetch live game feeds for active games
3. Transform feeds into core schema
4. Update any downstream features/models

Usage:
    python3 scripts/ingest_live_games.py --dry-run  # See what would be ingested
    python3 scripts/ingest_live_games.py --active   # Ingest currently active games
    python3 scripts/ingest_live_games.py --game-pk 123456  # Ingest specific game
    python3 scripts/ingest_live_games.py --schedule  # Ingest all games from today's schedule
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import psycopg2


ROOT = Path(__file__).resolve().parents[1]


def database_kwargs() -> dict[str, str]:
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def get_active_game_pks(date: str | None = None) -> list[int]:
    """Get list of active game PKs from the schedule fetcher."""
    cmd = [sys.executable, 'scripts/fetch_mlb_schedule.py']
    if date:
        cmd.extend(['--date', date])
    else:
        cmd.append('--yesterday')  # Include yesterday's completed games

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if result.returncode != 0:
        print(f'Error fetching schedule: {result.stderr}')
        return []

    # Parse the output to extract game PKs
    game_pks = []
    for line in result.stdout.splitlines():
        if '⚫' in line or '🔴' in line:  # Active or live games
            parts = line.split()
            for part in parts:
                if part.isdigit() and len(part) == 6:  # Game PKs are 6 digits
                    game_pks.append(int(part))

    return game_pks


def get_recently_ingested_games(hours: int = 24) -> list[int]:
    """Get list of games recently ingested to avoid duplicates."""
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT game_pk
                FROM raw_mlb.live_feed_snapshots
                WHERE fetched_at > now() - (%s * interval '1 hour')
                """,
                (hours,),
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def fetch_live_game(game_pk: int) -> bool:
    """Fetch live game data for a single game."""
    print(f'Fetching live data for game {game_pk}...')
    result = subprocess.run(
        [
            sys.executable,
            'scripts/warehouse.py',
            'fetch-live-game',
            '--game-pk',
            str(game_pk),
        ],
        cwd=ROOT,
    )
    return result.returncode == 0


def transform_live_game(game_pk: int) -> bool:
    """Transform live game data for a single game."""
    print(f'Transforming live data for game {game_pk}...')
    result = subprocess.run(
        [sys.executable, 'scripts/transform_live_game.py', '--game-pk', str(game_pk)],
        cwd=ROOT,
    )
    return result.returncode == 0


def ingest_game(game_pk: int, skip_existing: bool = True) -> bool:
    """Complete ingestion pipeline for a single game."""
    if skip_existing:
        recently_ingested = get_recently_ingested_games()
        if game_pk in recently_ingested:
            print(f'Game {game_pk} already ingested recently, skipping.')
            return True

    success = fetch_live_game(game_pk)
    if not success:
        print(f'Failed to fetch game {game_pk}')
        return False

    success = transform_live_game(game_pk)
    if not success:
        print(f'Failed to transform game {game_pk}')
        return False

    # Refresh live materialized views after ingestion
    refresh_success = refresh_live_views(game_pk)
    if not refresh_success:
        print(f'Failed to refresh live views for game {game_pk}')
        return False

    print(f'Successfully ingested game {game_pk}')
    return True


def refresh_live_views(game_pk: int) -> bool:
    """Refresh live materialized views after game ingestion."""
    print(f'Refreshing live views for game {game_pk}...')
    try:
        conn = psycopg2.connect(**database_kwargs())
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM maintenance.refresh_live_after_ingestion(%s)",
                    (str(game_pk),),
                )
                results = cur.fetchall()
                print(f'Refresh results: {len(results)} views refreshed')
                return True
        finally:
            conn.close()
    except Exception as e:
        print(f'Error refreshing live views: {e}')
        return False


def main():
    parser = argparse.ArgumentParser(description='Automated MLB live data ingestion')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be ingested without actually doing it',
    )
    parser.add_argument('--active', action='store_true', help='Ingest currently active/live games')
    parser.add_argument(
        '--schedule',
        action='store_true',
        help="Ingest all games from today's schedule",
    )
    parser.add_argument('--game-pk', type=int, help='Ingest a specific game by MLB game PK')
    parser.add_argument(
        '--date',
        help='Date to fetch schedule for (YYYY-MM-DD format, default: today)',
    )
    parser.add_argument(
        '--no-skip-existing',
        action='store_true',
        help="Don't skip games that were recently ingested",
    )

    args = parser.parse_args()

    if args.game_pk:
        # Ingest specific game
        game_pks = [args.game_pk]
    elif args.active or args.schedule:
        # Get games from schedule
        game_pks = get_active_game_pks(args.date)
        if not game_pks:
            print(
                'No active games found. Try --date with a specific date or add --yesterday to check recent games.',
            )
            return
    else:
        parser.print_help()
        return

    print(f'Found {len(game_pks)} games to process: {game_pks}')

    if args.dry_run:
        print('Dry run - would ingest:')
        for pk in game_pks:
            print(f'  Game {pk}')
        return

    success_count = 0
    for game_pk in game_pks:
        if ingest_game(game_pk, skip_existing=not args.no_skip_existing):
            success_count += 1

    print(f'\nIngestion complete: {success_count}/{len(game_pks)} games successful')


if __name__ == '__main__':
    main()
