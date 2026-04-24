#!/usr/bin/env python3
"""
Bulk download MLB game feeds for historical data collection.
Downloads live feeds for completed games with rate limiting and deduplication.
"""

import argparse
import json
import time

import psycopg2
from psycopg2.extras import Json


def database_kwargs():
    """Database connection parameters."""
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def get_games_to_download(start_date: str, end_date: str, max_games: int = None) -> list:
    """Get list of completed games that need live feed downloads."""
    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            query = """
                SELECT DISTINCT
                    (g->'gamePk')::integer as game_pk,
                    (g->'gameDate')::text as game_date,
                    (g->'status'->>'abstractGameState') as status
                FROM raw_mlb.schedule_snapshots s,
                     jsonb_array_elements(s.payload->'dates'->0->'games') g
                WHERE s.snapshot_date BETWEEN %s AND %s
                  AND s.http_status = 200
                  AND (g->'status'->>'abstractGameState') IN ('Final', 'Completed')
                  AND NOT EXISTS (
                      SELECT 1 FROM raw_mlb.live_feed_snapshots lfs
                      WHERE lfs.game_pk = (g->'gamePk')::integer
                      AND lfs.http_status = 200
                  )
                ORDER BY game_date, game_pk
            """

            if max_games:
                query += f' LIMIT {max_games}'

            cur.execute(query, (start_date, end_date))
            return cur.fetchall()

    finally:
        conn.close()


def download_game_feed(game_pk: int) -> dict:
    """Download live feed for a specific game."""
    url = f'https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live'

    try:
        start_time = time.time()
        with urllib.request.urlopen(url, timeout=30) as response:
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)

            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                return {
                    'success': True,
                    'data': data,
                    'http_status': response.status,
                    'response_time_ms': response_time_ms,
                }
            return {
                'success': False,
                'error': f'HTTP {response.status}',
                'http_status': response.status,
                'response_time_ms': response_time_ms,
            }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'http_status': None,
            'response_time_ms': None,
        }


def store_game_feed(game_pk: int, result: dict):
    """Store game feed in database."""
    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            # Extract metadata for indexing
            payload = result.get('data', {})
            game_data = payload.get('gameData', {})
            game_info = game_data.get('game', {})

            game_date = (
                game_info.get('gameDate', '').split('T')[0] if game_info.get('gameDate') else None
            )
            season = game_info.get('season')

            cur.execute(
                """
                INSERT INTO raw_mlb.live_feed_snapshots
                (game_pk, fetched_at, endpoint, payload, request_params,
                 http_status, response_time_ms, error_text, game_date, season)
                VALUES (%s, now(), %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (game_pk, fetched_at) DO NOTHING
            """,
                (
                    game_pk,
                    f'https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live',
                    Json(payload) if result.get('success') else Json({}),
                    Json({}),
                    result.get('http_status'),
                    result.get('response_time_ms'),
                    result.get('error') if not result.get('success') else None,
                    game_date,
                    season,
                ),
            )

        conn.commit()

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Bulk download MLB game feeds')
    parser.add_argument('--start-date', required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument(
        '--max-games',
        type=int,
        default=100,
        help='Maximum games to download (default: 100)',
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between requests in seconds (default: 2.0)',
    )
    parser.add_argument('--dry-run', action='store_true', help='Show what would be downloaded')

    args = parser.parse_args()

    print(f'🎮 MLB Game Feed Bulk Download: {args.start_date} to {args.end_date}')
    print(f'   Max games: {args.max_games}, Delay: {args.delay}s')

    # Get games to download
    games = get_games_to_download(args.start_date, args.end_date, args.max_games)

    print(f'📊 Found {len(games)} completed games needing live feeds')

    if not games:
        print('✅ No games need downloading!')
        return

    if args.dry_run:
        print('📋 Would download live feeds for:')
        for i, (game_pk, game_date, status) in enumerate(games[:10]):
            print(f'   {i + 1:3d}. Game {game_pk} ({game_date}) - {status}')
        if len(games) > 10:
            print(f'   ... and {len(games) - 10} more')
        return

    # Download game feeds
    successful = 0
    failed = 0
    rate_limited = 0

    for i, (game_pk, game_date, status) in enumerate(games):
        print(f'📥 [{i + 1:4d}/{len(games)}] Downloading game {game_pk} ({game_date})...')

        result = download_game_feed(game_pk)

        if result['success']:
            store_game_feed(game_pk, result)
            successful += 1
            status_emoji = '✅'
        else:
            failed += 1
            if '429' in str(result.get('error', '')):
                rate_limited += 1
            status_emoji = '❌'

        http_status = result.get('http_status', 'ERROR')
        response_time = result.get('response_time_ms', 0)
        print(f'   {status_emoji} Game {game_pk}: HTTP {http_status} ({response_time}ms)')

        # Rate limiting
        if i < len(games) - 1:  # Don't delay on last request
            time.sleep(args.delay)

    print('\n🎯 Download Complete:')
    print(f'   ✅ Successful: {successful}')
    print(f'   ❌ Failed: {failed}')
    if rate_limited > 0:
        print(f'   🚦 Rate limited: {rate_limited}')
    print(f'   📊 Total processed: {len(games)}')
    successful / len(games) * 100 if games else 0
    print('.1f')


if __name__ == '__main__':
    import os

    main()
