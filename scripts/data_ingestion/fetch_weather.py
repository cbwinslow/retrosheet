#!/usr/bin/env python3
"""
Fetch daily weather observations for a given venue (park) from the public
NOAA API (no API key required for basic requests). The script stores the
raw observations in `raw_weather.daily`.

Usage:
    python scripts/fetch_weather.py --date 2026-04-15 --venue-id SFG
"""

import argparse
import os
import sys
from datetime import datetime

import psycopg2
import requests


DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/retrosheet')


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def fetch_weather(date: str, venue_id: str):
    # NOAA API endpoint (example - replace with actual public endpoint if needed)
    base_url = 'https://www.ncei.noaa.gov/access/services/data/v1'
    params = {
        'dataset': 'daily-summaries',
        'stations': venue_id,
        'startDate': date,
        'endDate': date,
        'format': 'json',
        'units': 'metric',
    }
    resp = requests.get(base_url, params=params, timeout=30)
    if resp.status_code != 200:
        print(f'❌ NOAA request failed: {resp.status_code}', file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    if not data:
        print('⚠️  No weather data returned', file=sys.stderr)
        return

    record = data[0]
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO raw_weather.daily (
                    observation_date, venue_id,
                    temperature_c, wind_speed_mps, precipitation_mm
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (observation_date, venue_id) DO UPDATE
                SET
                    temperature_c = EXCLUDED.temperature_c,
                    wind_speed_mps = EXCLUDED.wind_speed_mps,
                    precipitation_mm = EXCLUDED.precipitation_mm;
            """
            cur.execute(
                sql,
                (
                    date,
                    venue_id,
                    float(record.get('TMP') or 0),
                    float(record.get('WDF2') or 0),
                    float(record.get('PRCP') or 0),
                ),
            )
        conn.commit()
        print(f'✅ Stored weather for {venue_id} on {date}')
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Fetch NOAA weather')
    parser.add_argument('--date', type=str, required=True, help='Observation date (YYYY-MM-DD)')
    parser.add_argument(
        '--venue-id',
        type=str,
        required=True,
        help='Venue/station identifier (e.g., SFG for San Francisco)',
    )
    args = parser.parse_args()
    # Validate date
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print('❌ Invalid date format', file=sys.stderr)
        sys.exit(1)

    fetch_weather(args.date, args.venue_id)


if __name__ == '__main__':
    main()
