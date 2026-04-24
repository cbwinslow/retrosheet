#!/usr/bin/env python3
"""
Optimized MLB Historical Data Bulk Downloader
Focuses on game days only and uses intelligent batching for efficiency.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
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


def download_schedule_batch(dates: list, delay: float = 1.0) -> list:
    """Download a batch of schedules with error handling."""
    results = []

    for date_str in dates:
        result = download_schedule_for_date(date_str)
        results.append((date_str, result))

        # Rate limiting
        time.sleep(delay)

    return results


def download_schedule_for_date(date_str: str) -> dict:
    """Download MLB schedule for a specific date."""
    import urllib.request

    url = f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}'

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


def store_schedule_batch(results: list):
    """Store multiple schedule results in database."""
    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            for date_str, result in results:
                # Idempotent raw acquisition rule: once a successful snapshot exists
                # for a schedule date, reruns should not append another success row.
                cur.execute(
                    """
                    INSERT INTO raw_mlb.schedule_snapshots
                    (snapshot_date, fetched_at, endpoint, payload, request_params,
                     http_status, response_time_ms, error_text)
                    SELECT %s, now(), %s, %s, %s, %s, %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM raw_mlb.schedule_snapshots existing
                        WHERE existing.snapshot_date = %s
                          AND existing.http_status = 200
                    )
                """,
                    (
                        date_str,
                        f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}',
                        Json(result.get('data', {})) if result.get('success') else Json({}),
                        Json({'sportId': 1, 'date': date_str}),
                        result.get('http_status'),
                        result.get('response_time_ms'),
                        result.get('error') if not result.get('success') else None,
                        date_str,
                    ),
                )

        conn.commit()

    finally:
        conn.close()


def get_game_days(start_date: str, end_date: str) -> list:
    """Get list of dates that had MLB games."""
    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT snapshot_date
                FROM raw_mlb.schedule_snapshots
                WHERE snapshot_date BETWEEN %s AND %s
                  AND http_status = 200
                  AND jsonb_array_length(payload->'dates'->0->'games') > 0
                ORDER BY snapshot_date
            """,
                (start_date, end_date),
            )

            return [row[0] for row in cur.fetchall()]

    finally:
        conn.close()


def download_game_feeds_for_season(season: int, max_workers: int = 4) -> int:
    """Download all game feeds for a given season using parallel processing."""
    print(f'🔄 Downloading game feeds for {season} season')

    # Get all games for the season
    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT (g->'gamePk')::integer as game_pk
                FROM raw_mlb.schedule_snapshots s,
                     jsonb_array_elements(s.payload->'dates'->0->'games') g
                WHERE s.http_status = 200
                  AND EXTRACT(YEAR FROM s.snapshot_date) = %s
                  AND (g->'status'->>'abstractGameState') IN ('Final', 'Completed')
                  AND NOT EXISTS (
                      SELECT 1 FROM raw_mlb.live_feed_snapshots lfs
                      WHERE lfs.game_pk = (g->'gamePk')::integer
                      AND lfs.http_status = 200
                  )
                ORDER BY game_pk
            """,
                (season,),
            )

            games = [row[0] for row in cur.fetchall()]

    finally:
        conn.close()

    if not games:
        print(f'✅ No games to download for {season}')
        return 0

    print(f'📊 Found {len(games)} games to download for {season}')

    # Download in parallel batches
    batch_size = 10
    downloaded = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i in range(0, len(games), batch_size):
            batch = games[i : i + batch_size]
            print(
                f'📥 Processing batch {i // batch_size + 1}/{(len(games) + batch_size - 1) // batch_size}',
            )

            # Submit batch for parallel processing
            futures = [executor.submit(download_and_store_game_feed, game_pk) for game_pk in batch]

            # Wait for batch completion
            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    downloaded += 1

            # Rate limiting between batches
            time.sleep(1)

    print(f'✅ Downloaded {downloaded}/{len(games)} game feeds for {season}')
    return downloaded


def download_and_store_game_feed(game_pk: int) -> bool:
    """Download and store a single game feed."""
    import urllib.request

    url = f'https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live'
    conn = None

    try:
        start_time = time.time()
        with urllib.request.urlopen(url, timeout=30) as response:
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)

            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                payload_json = json.dumps(data, separators=(',', ':'))

                # Extract metadata for indexing
                game_data = data.get('gameData', {})
                game_info = game_data.get('game', {})
                game_date = (
                    game_info.get('gameDate', '').split('T')[0]
                    if game_info.get('gameDate')
                    else None
                )
                season = game_info.get('season')
                payload_checksum = hashlib.sha256(payload_json.encode('utf-8')).hexdigest()
                request_params = {'game_pk': int(game_pk)}

                # Store in database
                conn = psycopg2.connect(**database_kwargs())
                try:
                    with conn.cursor() as cur:
                        # Idempotent raw acquisition rule: once a successful game feed
                        # exists for a game_pk, reruns should not append another success row.
                        cur.execute(
                            """
                            INSERT INTO raw_mlb.live_feed_snapshots
                            (game_pk, fetched_at, endpoint, payload, request_params,
                             http_status, response_time_ms, error_text, payload_checksum, game_date, season)
                            SELECT %s, now(), %s, %s, %s, %s, %s, %s, %s, %s, %s
                            WHERE NOT EXISTS (
                                SELECT 1
                                FROM raw_mlb.live_feed_snapshots existing
                                WHERE existing.game_pk = %s
                                  AND existing.http_status = 200
                            )
                        """,
                            (
                                game_pk,
                                url,
                                Json(data),
                                Json(request_params),
                                response.status,
                                response_time_ms,
                                None,
                                payload_checksum,
                                game_date,
                                season,
                                game_pk,
                            ),
                        )

                    conn.commit()
                    return True

                finally:
                    conn.close()

            else:
                print(f'❌ HTTP {response.status} for game {game_pk}')
                conn = psycopg2.connect(**database_kwargs())
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO raw_mlb.live_feed_snapshots
                        (game_pk, fetched_at, endpoint, payload, request_params,
                         http_status, response_time_ms, error_text, payload_checksum, game_date, season)
                        VALUES (%s, now(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                        (
                            game_pk,
                            url,
                            Json({}),
                            Json({'game_pk': int(game_pk)}),
                            response.status,
                            response_time_ms,
                            f'HTTP {response.status}',
                            None,
                            None,
                            None,
                        ),
                    )
                conn.commit()
                return False

    except Exception as e:
        print(f'❌ Error downloading game {game_pk}: {e}')
        try:
            conn = psycopg2.connect(**database_kwargs())
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO raw_mlb.live_feed_snapshots
                    (game_pk, fetched_at, endpoint, payload, request_params,
                     http_status, response_time_ms, error_text, payload_checksum, game_date, season)
                    VALUES (%s, now(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        game_pk,
                        url,
                        Json({}),
                        Json({'game_pk': int(game_pk)}),
                        None,
                        None,
                        str(e),
                        None,
                        None,
                        None,
                    ),
                )
            conn.commit()
        except Exception as insert_error:
            print(f'❌ Failed to persist download error for game {game_pk}: {insert_error}')
        return False
    finally:
        if conn is not None:
            conn.close()


def main():

    parser = argparse.ArgumentParser(description='Optimized MLB historical data bulk downloader')
    parser.add_argument('--start-season', type=int, default=2020, help='Start season year')
    parser.add_argument('--end-season', type=int, default=2024, help='End season year')
    parser.add_argument(
        '--mode',
        choices=['schedules', 'games', 'both'],
        default='both',
        help='What to download: schedules, games, or both',
    )
    parser.add_argument('--workers', type=int, default=8, help='Number of parallel workers')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests')

    args = parser.parse_args()

    print('🚀 MLB Historical Data Bulk Downloader')
    print(f'   Seasons: {args.start_season} - {args.end_season}')
    print(f'   Mode: {args.mode}')
    print(f'   Workers: {args.workers}')

    total_downloaded = 0

    for season in range(args.start_season, args.end_season + 1):
        print(f'\n{"=" * 50}')
        print(f'🏏 Processing {season} MLB Season')
        print(f'{"=" * 50}')

        if args.mode in ['schedules', 'both']:
            print(f'\n📅 Downloading {season} schedules...')

            # Generate all dates for the season (March-November)
            season_dates = []
            for month in range(3, 12):  # March to November
                if month <= 9:
                    days_in_month = 31 if month in [3, 5, 7, 8] else 30 if month != 2 else 28
                else:
                    days_in_month = 31 if month == 10 else 30

                for day in range(1, days_in_month + 1):
                    date_str = f'{season}-{month:02d}-{day:02d}'
                    season_dates.append(date_str)

            # Download in batches of 50 dates
            batch_size = 50
            season_downloaded = 0

            for i in range(0, len(season_dates), batch_size):
                batch = season_dates[i : i + batch_size]
                print(f'   Batch {i // batch_size + 1}: {len(batch)} dates')

                results = download_schedule_batch(batch, args.delay)
                successful = [r for r in results if r[1].get('success')]

                if successful:
                    store_schedule_batch(successful)
                    season_downloaded += len(successful)

                print(f'   ✅ {len(successful)}/{len(batch)} schedules downloaded')

            print(f'📊 {season} schedules: {season_downloaded} total')

        if args.mode in ['games', 'both']:
            # Download game feeds for the season
            games_downloaded = download_game_feeds_for_season(season, args.workers)
            total_downloaded += games_downloaded

    print('\n🎯 Bulk Download Complete!')
    print(f'   📊 Total game feeds downloaded: {total_downloaded}')

    # Summary statistics
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) as schedules,
                    COUNT(*) FILTER (WHERE http_status = 200) as successful_schedules,
                    (SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots) as game_feeds,
                    (SELECT COUNT(*) FROM raw_mlb.live_feed_snapshots WHERE http_status = 200) as successful_feeds
                FROM raw_mlb.schedule_snapshots
            """)

            schedules, successful_schedules, feeds, successful_feeds = cur.fetchone()

            print('\n📈 Summary:')
            print(f'   📅 Schedule snapshots: {successful_schedules}/{schedules}')
            print(f'   🎮 Game feed snapshots: {successful_feeds}/{feeds}')

            if successful_feeds > 0:
                success_rate = successful_feeds / feeds * 100
                print(f'   ✅ Success rate: {success_rate:.1f}%')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
