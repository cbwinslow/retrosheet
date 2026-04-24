#!/usr/bin/env python3
"""
Orchestrate current MLB season data ingestion.

This script provides a repeatable pipeline for ingesting current season MLB data:
1. Fetch schedule for current season
2. Discover active/completed games
3. Ingest live game feeds
4. Transform to canonical live tables
5. Extract pitch-level data
6. Validate ingestion status

Usage:
    python3 scripts/ingest_current_season.py --season 2026
    python3 scripts/ingest_current_season.py --days-back 7
    python3 scripts/ingest_current_season.py --schedule-only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'=' * 60}")
    print(f'STEP: {description}')
    print(f"Command: {' '.join(cmd)}")
    print(f"{'=' * 60}")

    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    success = result.returncode == 0
    print(f"Status: {'✅ SUCCESS' if success else '❌ FAILED'}")
    return success


def fetch_schedule(season: int | None = None, days_back: int | None = None) -> bool:
    """Fetch MLB schedule for current season or recent days."""
    if season:
        cmd = ['python3', 'scripts/fetch_mlb_schedule.py', '--season', str(season)]
        description = f'Fetch MLB schedule for season {season}'
    else:
        cmd = ['python3', 'scripts/fetch_mlb_schedule.py', '--days-back', str(days_back or 7)]
        description = f'Fetch MLB schedule for last {days_back or 7} days'

    return run_command(cmd, description)


def ingest_live_games(schedule_only: bool = False) -> bool:
    """Ingest live games from schedule."""
    if schedule_only:
        cmd = ['python3', 'scripts/ingest_live_games.py', '--schedule']
        description = 'Ingest live games from schedule'
    else:
        cmd = ['python3', 'scripts/ingest_live_games.py', '--schedule', '--transform']
        description = 'Ingest and transform live games'

    return run_command(cmd, description)


def populate_bridge_tables() -> bool:
    """Populate bridge tables with latest mappings."""
    cmd = ['python3', 'scripts/populate_bridge_tables.py']
    description = 'Populate bridge tables (players, teams, parks)'
    return run_command(cmd, description)


def complete_game_xref(season: int | None = None) -> bool:
    """Complete game cross-reference table."""
    cmd = ['python3', 'scripts/complete_game_xref.py']
    if season:
        cmd.extend(['--season', str(season)])
    description = 'Complete game cross-reference table'
    return run_command(cmd, description)


def validate_ingestion() -> bool:
    """Validate ingestion status."""
    cmd = [
        'python3',
        '-c',
        """
import os
import psycopg2

def database_kwargs():
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "retrosheet"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }

conn = psycopg2.connect(**database_kwargs())
cur = conn.cursor()

print("\\n=== INGESTION VALIDATION ===")

# Check live feed snapshots
cur.execute("SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots")
snapshots = cur.fetchone()[0]
print(f"Live feed snapshots: {snapshots:,}")

# Check live games
cur.execute("SELECT COUNT(*) FROM core.live_games")
live_games = cur.fetchone()[0]
print(f"Live games: {live_games:,}")

# Check live events
cur.execute("SELECT COUNT(*) FROM core.live_events")
live_events = cur.fetchone()[0]
print(f"Live events: {live_events:,}")

# Check bridge tables
cur.execute("SELECT COUNT(*) FROM bridge.game_xref")
game_xref = cur.fetchone()[0]
print(f"Bridge game_xref: {game_xref:,}")

cur.execute("SELECT COUNT(*) FROM bridge.player_xref")
player_xref = cur.fetchone()[0]
print(f"Bridge player_xref: {player_xref:,}")

# Check recent data
cur.execute("SELECT MAX(game_date) FROM core.live_games")
max_date = cur.fetchone()[0]
print(f"Latest game date: {max_date}")

conn.close()
print("\\n=== VALIDATION COMPLETE ===")
""",
    ]
    description = 'Validate ingestion status'
    return run_command(cmd, description)


def main() -> None:
    parser = argparse.ArgumentParser(description='Orchestrate current MLB season data ingestion')
    parser.add_argument('--season', type=int, help='Season to ingest (e.g., 2026)')
    parser.add_argument('--days-back', type=int, help='Number of days back to ingest (default: 7)')
    parser.add_argument(
        '--schedule-only', action='store_true', help="Only fetch schedule, don't ingest games",
    )
    parser.add_argument('--skip-bridge', action='store_true', help='Skip bridge table population')
    parser.add_argument(
        '--skip-xref', action='store_true', help='Skip game cross-reference completion',
    )
    parser.add_argument('--no-validate', action='store_true', help='Skip validation step')

    args = parser.parse_args()

    season = args.season or datetime.now().year
    days_back = args.days_back or 7

    print(f"\n{'=' * 60}")
    print('CURRENT SEASON INGESTION PIPELINE')
    print(f"{'=' * 60}")
    print(f'Season: {season}')
    print(f'Days back: {days_back}')
    print(f'Schedule only: {args.schedule_only}')
    print(f'Skip bridge: {args.skip_bridge}')
    print(f'Skip xref: {args.skip_xref}')
    print(f'No validate: {args.no_validate}')
    print(f"{'=' * 60}\n")

    steps = []

    # Step 1: Fetch schedule
    steps.append(('Fetch schedule', lambda: fetch_schedule(season, days_back)))

    # Step 2: Populate bridge tables (unless skipped)
    if not args.skip_bridge:
        steps.append(('Populate bridge tables', populate_bridge_tables))

    # Step 3: Complete game xref (unless skipped)
    if not args.skip_xref:
        steps.append(('Complete game xref', lambda: complete_game_xref(season)))

    # Step 4: Ingest live games
    steps.append(('Ingest live games', lambda: ingest_live_games(args.schedule_only)))

    # Step 5: Validate ingestion (unless skipped)
    if not args.no_validate:
        steps.append(('Validate ingestion', validate_ingestion))

    # Execute steps
    results = []
    for step_name, step_func in steps:
        success = step_func()
        results.append((step_name, success))

        if not success:
            print(f'\n❌ Pipeline failed at step: {step_name}')
            print('Stopping pipeline execution.')
            break

    # Summary
    print(f"\n{'=' * 60}")
    print('PIPELINE SUMMARY')
    print(f"{'=' * 60}")
    for step_name, success in results:
        status = '✅' if success else '❌'
        print(f'{status} {step_name}')

    all_success = all(success for _, success in results)
    print(f"\nOverall status: {'✅ SUCCESS' if all_success else '❌ FAILED'}")
    print(f"{'=' * 60}\n")

    sys.exit(0 if all_success else 1)


if __name__ == '__main__':
    main()
