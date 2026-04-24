#!/usr/bin/env python3
"""
Download missing 2023 MLB schedules.
"""

import json
import time
import urllib.request

import psycopg2
from psycopg2.extras import Json


def database_kwargs():
    import os

    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def download_schedule_for_date(date_str: str):
    """Download MLB schedule for a specific date."""
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


def store_schedule(date_str: str, result: dict):
    """Store schedule result in database."""
    conn = psycopg2.connect(**database_kwargs())

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO raw_mlb.schedule_snapshots
                (snapshot_date, fetched_at, endpoint, payload, request_params,
                 http_status, response_time_ms, error_text)
                VALUES (%s, now(), %s, %s, %s, %s, %s, %s)
                ON CONFLICT (snapshot_date, fetched_at) DO NOTHING
            """,
                (
                    date_str,
                    f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}',
                    Json(result.get('data', {})) if result.get('success') else Json({}),
                    Json({'sportId': 1, 'date': date_str}),
                    result.get('http_status'),
                    result.get('response_time_ms'),
                    result.get('error') if not result.get('success') else None,
                ),
            )

        conn.commit()

    finally:
        conn.close()


def main():
    # Get missing dates
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT expected_date::date::text
                FROM (
                    SELECT generate_series('2023-03-01'::date, '2023-11-30'::date, '1 day'::interval) as expected_date
                ) dates
                WHERE expected_date NOT IN (
                    SELECT snapshot_date
                    FROM raw_mlb.schedule_snapshots
                    WHERE EXTRACT(YEAR FROM snapshot_date) = 2023
                )
                ORDER BY expected_date
            """)
            missing_dates = [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

    print(f'Found {len(missing_dates)} missing dates for 2023')

    for date_str in missing_dates:
        print(f'Downloading {date_str}...')
        result = download_schedule_for_date(date_str)
        if result['success']:
            store_schedule(date_str, result)
            print(f'  ✅ Stored {date_str}')
        else:
            print(f"  ❌ Failed {date_str}: {result.get('error', 'Unknown error')}")
        time.sleep(1)  # Rate limiting

    print('Done!')


if __name__ == '__main__':
    main()
