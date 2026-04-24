#!/usr/bin/env python3
"""
Manage MLB game polling schedule - seasonal and game-hours aware.

This script provides commands to:
- Enable/disable polling based on MLB season
- Switch between 24/7 polling and game-hours-only polling
- Check current polling status and conditions

Usage:
    python scripts/utility/manage_game_polling.py status
    python scripts/utility/manage_game_polling.py enable-game-hours
    python scripts/utility/manage_game_polling.py enable-24-7
    python scripts/utility/manage_game_polling.py disable
    python scripts/utility/manage_game_polling.py test-season-check

MLB Season Schedule:
- Spring Training: February - March
- Regular Season: Late March - Early October
- Playoffs: October - November
- Offseason: November - January

Game Hours (ET):
- Day games: 1pm - 4pm
- Evening games: 7pm - 10pm
- Night games: 8pm - 11pm
- Extra innings: Can extend past midnight
"""

import argparse
import os
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=int(os.getenv('PGPORT', 5432)),
        database=os.getenv('PGDATABASE', 'retrosheet'),
        user=os.getenv('PGUSER', os.getenv('USER', 'postgres')),
    )


def get_polling_status(conn) -> list[dict]:
    """Get current cron job status."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT jobid, jobname, schedule, active, 
                   substring(command, 1, 80) as command_preview
            FROM cron.job
            WHERE jobname LIKE '%poll%' OR jobname LIKE '%game%'
            ORDER BY jobid
        """)
        return cur.fetchall()


def check_season_conditions(conn) -> dict:
    """Check if current conditions meet MLB season/game hours."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT 
                metadata.is_mlb_season() as is_season,
                metadata.is_game_hours() as is_game_hours,
                metadata.should_poll_games() as should_poll,
                metadata.has_scheduled_games_today() as has_games_today
        """)
        return cur.fetchone()


def enable_game_hours_polling(conn):
    """Switch to game-hours-only polling (conditional)."""
    with conn.cursor() as cur:
        # Unschedule old jobs
        cur.execute("SELECT cron.unschedule('live-game-poll-10s')")
        cur.execute("SELECT cron.unschedule('all-endpoints-poll-15s')")

        # Schedule conditional wrappers
        cur.execute("""
            SELECT cron.schedule(
                'live-game-poll-conditional',
                '*/10 * * * * *',
                'SELECT metadata.poll_active_games_conditional();'
            )
        """)
        cur.execute("""
            SELECT cron.schedule(
                'endpoints-poll-conditional',
                '*/15 * * * * *',
                'SELECT metadata.poll_all_endpoints_conditional();'
            )
        """)
        conn.commit()
    print('✅ Enabled game-hours-only polling (conditional)')


def enable_24_7_polling(conn):
    """Switch to 24/7 polling (unconditional)."""
    with conn.cursor() as cur:
        # Unschedule conditional jobs
        cur.execute("SELECT cron.unschedule('live-game-poll-conditional')")
        cur.execute("SELECT cron.unschedule('endpoints-poll-conditional')")

        # Schedule unconditional polling
        cur.execute("""
            SELECT cron.schedule(
                'live-game-poll-10s',
                '*/10 * * * * *',
                'SELECT raw_sportradar.poll_active_games();'
            )
        """)
        cur.execute("""
            SELECT cron.schedule(
                'all-endpoints-poll-15s',
                '*/15 * * * * *',
                'SELECT raw_mlb.poll_all_active_endpoints();'
            )
        """)
        conn.commit()
    print('✅ Enabled 24/7 polling (unconditional)')


def disable_polling(conn):
    """Disable all game polling jobs."""
    with conn.cursor() as cur:
        job_names = [
            'live-game-poll-10s',
            'all-endpoints-poll-15s',
            'live-game-poll-conditional',
            'endpoints-poll-conditional',
        ]
        for job in job_names:
            try:
                cur.execute(f"SELECT cron.unschedule('{job}')")
            except Exception as e:
                print(f'  Note: {job} - {e}')
        conn.commit()
    print('✅ Disabled all game polling')


def show_status(conn):
    """Display current polling status."""
    print('\n' + '=' * 60)
    print('MLB Game Polling Status')
    print('=' * 60)

    # Current time info
    now = datetime.now()
    et_hour = datetime.now().astimezone().strftime('%H:%M %Z')
    print(f"\nCurrent Time: {now.strftime('%Y-%m-%d %H:%M:%S')} ({et_hour})")

    # Season conditions
    conditions = check_season_conditions(conn)
    print('\nSeason Conditions:')
    print(f"  Is MLB Season (Feb-Oct):     {'✅ YES' if conditions['is_season'] else '❌ NO'}")
    print(f"  Is Game Hours (11am-1am ET): {'✅ YES' if conditions['is_game_hours'] else '❌ NO'}")
    print(
        f"  Has Games Scheduled Today:   {'✅ YES' if conditions['has_games_today'] else '❌ NO / Unknown'}",
    )
    print(f"  Should Poll:                 {'✅ YES' if conditions['should_poll'] else '❌ NO'}")

    # Cron jobs
    jobs = get_polling_status(conn)
    print('\nActive Cron Jobs:')
    if jobs:
        for job in jobs:
            status = '🟢 Active' if job['active'] else '🔴 Inactive'
            print(f"  [{job['jobid']}] {job['jobname']}")
            print(f"      Schedule: {job['schedule']}")
            print(f'      Status: {status}')
            print(f"      Command: {job['command_preview']}...")
    else:
        print('  No game polling jobs found')

    # Recommendation
    print('\nRecommendation:')
    if conditions['is_season'] and conditions['is_game_hours']:
        print('  🟢 Current conditions: Polling should be active')
    elif not conditions['is_season']:
        print('  ⚠️  Offseason detected: Consider disabling or using game-hours mode')
    else:
        print('  ⚠️  Outside game hours: Polling may be unnecessary')

    print('=' * 60 + '\n')


def test_season_check(conn):
    """Test the season/game hours functions."""
    print('\nTesting Season Check Functions:')

    with conn.cursor() as cur:
        # Test each function
        cur.execute('SELECT metadata.is_mlb_season() as result')
        is_season = cur.fetchone()[0]
        print(f'  metadata.is_mlb_season(): {is_season}')

        cur.execute('SELECT metadata.is_game_hours() as result')
        is_hours = cur.fetchone()[0]
        print(f'  metadata.is_game_hours(): {is_hours}')

        cur.execute('SELECT metadata.should_poll_games() as result')
        should_poll = cur.fetchone()[0]
        print(f'  metadata.should_poll_games(): {should_poll}')

        cur.execute('SELECT metadata.has_scheduled_games_today() as result')
        has_games = cur.fetchone()[0]
        print(f'  metadata.has_scheduled_games_today(): {has_games}')

    print('\n✅ All functions working correctly')


def main():
    parser = argparse.ArgumentParser(
        description='Manage MLB game polling schedule',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s status              # Show current status
    %(prog)s enable-game-hours   # Use conditional polling (season/game hours only)
    %(prog)s enable-24-7         # Use unconditional polling (24/7)
    %(prog)s disable             # Stop all polling
    %(prog)s test-season-check   # Test the season check functions
        """,
    )

    parser.add_argument(
        'command',
        choices=['status', 'enable-game-hours', 'enable-24-7', 'disable', 'test-season-check'],
        help='Command to execute',
    )

    args = parser.parse_args()

    conn = get_connection()

    try:
        if args.command == 'status':
            show_status(conn)
        elif args.command == 'enable-game-hours':
            enable_game_hours_polling(conn)
            show_status(conn)
        elif args.command == 'enable-24-7':
            enable_24_7_polling(conn)
            show_status(conn)
        elif args.command == 'disable':
            disable_polling(conn)
            show_status(conn)
        elif args.command == 'test-season-check':
            test_season_check(conn)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
