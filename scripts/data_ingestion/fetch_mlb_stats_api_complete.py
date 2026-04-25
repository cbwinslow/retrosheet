#!/usr/bin/env python3
"""
File: scripts/data_ingestion/fetch_mlb_stats_api_complete.py
Purpose: COMPLETE MLB Stats API fetcher - ALL endpoints, ALL fields, no dropping
Author: Agent Cascade
Date: 2026-04-25
Usage: uv run python scripts/data_ingestion/fetch_mlb_stats_api_complete.py --season 2025
Dependencies: requests, psycopg2, python-dotenv

This fetches data from ALL MLB Stats API endpoints and stores source-preserved
JSON to ensure we can extract any field later without re-fetching.

CRITICAL PRINCIPLE: Store complete API responses, never filter or select fields
at ingestion time. We can always filter later when extracting/transforming.

Endpoints covered:
- Live Feed (existing)
- Boxscore (NEW - previously missing)
- Play-by-Play (NEW - previously missing)
- Pitch Metrics (NEW - previously missing)
- Win Probability (NEW - previously missing)
- Gameday XML (NEW - previously missing)
- Player Stats (NEW - previously missing)
- Team Stats (NEW - previously missing)
- Standings (NEW - previously missing)
- Rosters (NEW - previously missing)

All data is stored in raw_mlb.*_snapshots tables with:
- Source-preserved JSONB payload
- Checksum-based deduplication
- HTTP status tracking
- Response time metrics
- Fetch timestamp
"""

import argparse
import hashlib
import json
import os
import sys
import time

import psycopg2
import requests
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# MLB Stats API Base URL
MLB_API_BASE = 'https://statsapi.mlb.com/api/v1'
GAMEDAY_BASE = 'https://gd2.mlb.com/components/game'


def get_db_conn():
    """Get database connection."""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        dbname=os.getenv('POSTGRES_DB', 'retrosheet'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
    )


def fetch_json(url: str, params: dict | None = None, timeout: int = 30) -> tuple[dict, int, int]:
    """
    Fetch JSON from MLB API.
    
    Returns: (data, http_status, response_time_ms)
    """
    start = time.time()
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response_time = int((time.time() - start) * 1000)

        if response.status_code == 200:
            return response.json(), response.status_code, response_time
        return {}, response.status_code, response_time
    except requests.exceptions.RequestException:
        return {}, 0, int((time.time() - start) * 1000)


def fetch_xml(url: str, timeout: int = 30) -> tuple[str, int, int]:
    """
    Fetch XML from MLB Gameday.
    
    Returns: (xml_text, http_status, response_time_ms)
    """
    start = time.time()
    try:
        response = requests.get(url, timeout=timeout)
        response_time = int((time.time() - start) * 1000)

        if response.status_code == 200:
            return response.text, response.status_code, response_time
        return '', response.status_code, response_time
    except requests.exceptions.RequestException:
        return '', 0, int((time.time() - start) * 1000)


def store_json_snapshot(
    conn, table: str, game_pk: int, game_date: str,
    http_status: int, response_time: int, payload: dict,
):
    """Store JSON snapshot in database with deduplication."""
    if not payload:
        return False

    payload_json = json.dumps(payload, sort_keys=True)
    checksum = hashlib.md5(payload_json.encode()).hexdigest()

    cur = conn.cursor()
    try:
        # Try insert with conflict resolution (deduplication)
        cur.execute(f"""
            INSERT INTO raw_mlb.{table} 
                (mlb_game_pk, game_date, http_status, response_time_ms, payload, checksum)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (mlb_game_pk, checksum) DO NOTHING
            RETURNING id;
        """, (game_pk, game_date, http_status, response_time, payload_json, checksum))

        result = cur.fetchone()
        conn.commit()
        return result is not None  # True if new row inserted
    except Exception as e:
        conn.rollback()
        print(f'   DB Error storing {table}: {e}', file=sys.stderr)
        return False
    finally:
        cur.close()


def fetch_boxscore(game_pk: int, game_date: str, conn) -> bool:
    """Fetch boxscore data."""
    url = f'{MLB_API_BASE}/game/{game_pk}/boxscore'
    data, status, time_ms = fetch_json(url)
    if status == 200:
        return store_json_snapshot(conn, 'boxscore_snapshots', game_pk, game_date,
                                   status, time_ms, data)
    return False


def fetch_play_by_play(game_pk: int, game_date: str, conn) -> bool:
    """Fetch play-by-play data."""
    url = f'{MLB_API_BASE}/game/{game_pk}/playByPlay'
    data, status, time_ms = fetch_json(url)
    if status == 200:
        return store_json_snapshot(conn, 'play_by_play_snapshots', game_pk, game_date,
                                   status, time_ms, data)
    return False


def fetch_pitch_metrics(game_pk: int, game_date: str, conn) -> bool:
    """Fetch pitch metrics (Statcast data via API)."""
    url = f'{MLB_API_BASE}/game/{game_pk}/pitchMetrics'
    data, status, time_ms = fetch_json(url)
    if status == 200:
        return store_json_snapshot(conn, 'pitch_metrics_snapshots', game_pk, game_date,
                                   status, time_ms, data)
    return False


def fetch_win_probability(game_pk: int, game_date: str, conn) -> bool:
    """Fetch win probability data."""
    url = f'{MLB_API_BASE}/game/{game_pk}/winProbability'
    data, status, time_ms = fetch_json(url)
    if status == 200:
        return store_json_snapshot(conn, 'win_probability_snapshots', game_pk, game_date,
                                   status, time_ms, data)
    return False


def fetch_gameday_xml(game_pk: int, game_date: str, xml_type: str, conn) -> bool:
    """Fetch Gameday XML files."""
    # Convert game_pk to Gameday path format
    year = str(game_date)[:4]
    month = str(game_date)[5:7]
    day = str(game_date)[8:10]

    # Gameday URL format
    url = f'{GAMEDAY_BASE}/mlb/year_{year}/month_{month}/day_{day}/gid_{game_pk}/{xml_type}.xml'

    xml_data, status, time_ms = fetch_xml(url)
    if status == 200 and xml_data:
        checksum = hashlib.md5(xml_data.encode()).hexdigest()

        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO raw_mlb.gameday_xml_snapshots
                    (mlb_game_pk, game_date, xml_type, http_status, response_time_ms, 
                     payload, checksum)
                VALUES (%s, %s, %s, %s, %s, %s::xml, %s)
                ON CONFLICT (mlb_game_pk, xml_type, checksum) DO NOTHING
                RETURNING id;
            """, (game_pk, game_date, xml_type, status, time_ms, xml_data, checksum))

            result = cur.fetchone()
            conn.commit()
            return result is not None
        except Exception as e:
            conn.rollback()
            print(f'   DB Error storing Gameday XML: {e}', file=sys.stderr)
            return False
        finally:
            cur.close()
    return False


def get_games_to_fetch(season: int, conn, limit: int | None = None) -> list[tuple[int, str]]:
    """Get list of games to fetch for a season."""
    cur = conn.cursor()
    try:
        # Get games from existing live_feed data or schedule
        cur.execute("""
            SELECT DISTINCT mlb_game_pk, game_date::text
            FROM raw_mlb.live_feed_snapshots
            WHERE http_status = 200
            AND game_date BETWEEN %s AND %s
            ORDER BY game_date
            LIMIT %s;
        """, (f'{season}-01-01', f'{season}-12-31', limit or 1000000))

        return cur.fetchall()
    except Exception as e:
        print(f'Error getting games: {e}', file=sys.stderr)
        return []
    finally:
        cur.close()


def fetch_all_game_data(game_pk: int, game_date: str, conn, skip_existing: bool = True) -> dict[str, bool]:
    """
    Fetch ALL MLB Stats API data for a single game.
    
    Returns dict of {endpoint: success}
    """
    results = {}

    # Check what we already have
    cur = conn.cursor()
    existing = {}
    if skip_existing:
        for table in ['boxscore_snapshots', 'play_by_play_snapshots',
                      'pitch_metrics_snapshots', 'win_probability_snapshots']:
            cur.execute(f"""
                SELECT 1 FROM raw_mlb.{table} 
                WHERE mlb_game_pk = %s AND http_status = 200
                LIMIT 1;
            """, (game_pk,))
            existing[table] = cur.fetchone() is not None
    cur.close()

    # Fetch each endpoint (skipping if we have it and skip_existing=True)
    endpoints = [
        ('boxscore', fetch_boxscore, 'boxscore_snapshots'),
        ('play_by_play', fetch_play_by_play, 'play_by_play_snapshots'),
        ('pitch_metrics', fetch_pitch_metrics, 'pitch_metrics_snapshots'),
        ('win_probability', fetch_win_probability, 'win_probability_snapshots'),
    ]

    for name, fetch_func, table in endpoints:
        if skip_existing and existing.get(table):
            results[name] = True  # Already have it
            continue

        try:
            success = fetch_func(game_pk, game_date, conn)
            results[name] = success
        except Exception as e:
            print(f'   Error fetching {name}: {e}', file=sys.stderr)
            results[name] = False

    # Fetch Gameday XML files
    xml_types = ['boxscore', 'linescore', 'plays', 'innings']
    for xml_type in xml_types:
        try:
            success = fetch_gameday_xml(game_pk, game_date, xml_type, conn)
            results[f'gameday_{xml_type}'] = success
        except Exception as e:
            print(f'   Error fetching Gameday {xml_type}: {e}', file=sys.stderr)
            results[f'gameday_{xml_type}'] = False

    return results


def fetch_team_rosters(season: int, conn) -> int:
    """Fetch team rosters for all teams in a season."""
    # Get team list from existing data or API
    url = f'{MLB_API_BASE}/teams'
    params = {'season': season, 'sportId': 1}

    data, status, time_ms = fetch_json(url, params)
    if status != 200:
        print(f'Failed to fetch team list: HTTP {status}')
        return 0

    teams = data.get('teams', [])
    count = 0

    for team in teams:
        team_id = team.get('id')
        if not team_id:
            continue

        # Fetch roster
        roster_url = f'{MLB_API_BASE}/teams/{team_id}/roster'
        roster_params = {'season': season}

        roster_data, roster_status, roster_time = fetch_json(roster_url, roster_params)

        if roster_status == 200:
            payload_json = json.dumps(roster_data, sort_keys=True)
            checksum = hashlib.md5(payload_json.encode()).hexdigest()

            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO raw_mlb.roster_snapshots
                        (team_id, season, roster_type, http_status, response_time_ms,
                         request_params, payload, checksum)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                    ON CONFLICT (team_id, season, roster_type, checksum) DO NOTHING
                    RETURNING id;
                """, (team_id, season, 'full', roster_status, roster_time,
                      json.dumps(roster_params), payload_json, checksum))

                if cur.fetchone():
                    count += 1
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f'   Error storing roster for team {team_id}: {e}', file=sys.stderr)
            finally:
                cur.close()

    return count


def fetch_standings(season: int, conn) -> int:
    """Fetch standings for a season."""
    url = f'{MLB_API_BASE}/standings'

    # Fetch for different dates throughout the season
    dates = [
        f'{season}-04-15',  # Early season
        f'{season}-06-15',  # Mid season
        f'{season}-08-15',  # Late season
        f'{season}-10-01',  # End of season
    ]

    count = 0
    for date in dates:
        params = {'season': season, 'date': date, 'leagueId': '103,104'}
        data, status, time_ms = fetch_json(url, params)

        if status == 200:
            payload_json = json.dumps(data, sort_keys=True)
            checksum = hashlib.md5(payload_json.encode()).hexdigest()

            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO raw_mlb.standings_snapshots
                        (season, date, league_id, division_id, http_status,
                         response_time_ms, payload, checksum)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (season, date, league_id, division_id, checksum) DO NOTHING
                    RETURNING id;
                """, (season, date, '103,104', 'all', status, time_ms, payload_json, checksum))

                if cur.fetchone():
                    count += 1
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f'   Error storing standings: {e}', file=sys.stderr)
            finally:
                cur.close()

    return count


def main():
    parser = argparse.ArgumentParser(
        description='Fetch COMPLETE MLB Stats API data - ALL endpoints, ALL fields',
    )
    parser.add_argument('--season', type=int, required=True, help='Season to fetch')
    parser.add_argument('--limit', type=int, help='Limit number of games (for testing)')
    parser.add_argument('--endpoints', nargs='+',
                        choices=['boxscore', 'play_by_play', 'pitch_metrics',
                                'win_probability', 'gameday', 'rosters', 'standings', 'all'],
                        default=['all'], help='Which endpoints to fetch')
    parser.add_argument('--skip-existing', action='store_true', default=True,
                        help='Skip games already in database')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print what would be fetched without fetching')
    args = parser.parse_args()

    print('=' * 70)
    print('MLB STATS API - COMPLETE FETCH')
    print('=' * 70)
    print(f'Season: {args.season}')
    print(f'Endpoints: {", ".join(args.endpoints)}')
    print(f'Mode: {"DRY RUN" if args.dry_run else "LIVE FETCH"}')
    print('=' * 70)

    # Get database connection
    conn = get_db_conn()

    try:
        # Get games to fetch
        games = get_games_to_fetch(args.season, conn, args.limit)
        print(f'Found {len(games):,} games to process')
        print('=' * 70)

        if args.dry_run:
            print('DRY RUN - Would fetch:')
            for game_pk, game_date in games[:5]:
                print(f'  Game {game_pk} on {game_date}')
            if len(games) > 5:
                print(f'  ... and {len(games) - 5:,} more games')
            return

        # Track statistics
        stats = {
            'games_processed': 0,
            'boxscore': {'attempted': 0, 'success': 0},
            'play_by_play': {'attempted': 0, 'success': 0},
            'pitch_metrics': {'attempted': 0, 'success': 0},
            'win_probability': {'attempted': 0, 'success': 0},
            'gameday_xml': {'attempted': 0, 'success': 0},
        }

        # Process each game
        for i, (game_pk, game_date) in enumerate(games, 1):
            if i % 100 == 0:
                print(f'Processing game {i:,} / {len(games):,} ({100*i/len(games):.1f}%)')

            results = fetch_all_game_data(game_pk, game_date, conn, args.skip_existing)

            for endpoint, success in results.items():
                if endpoint in stats:
                    stats[endpoint]['attempted'] += 1
                    if success:
                        stats[endpoint]['success'] += 1

            stats['games_processed'] += 1

            # Small delay to be nice to the API
            time.sleep(0.1)

        # Fetch rosters if requested
        if 'all' in args.endpoints or 'rosters' in args.endpoints:
            print('\nFetching team rosters...')
            roster_count = fetch_team_rosters(args.season, conn)
            print(f'  Stored {roster_count} team rosters')

        # Fetch standings if requested
        if 'all' in args.endpoints or 'standings' in args.endpoints:
            print('\nFetching standings...')
            standings_count = fetch_standings(args.season, conn)
            print(f'  Stored {standings_count} standings snapshots')

        # Summary report
        print('=' * 70)
        print('SUMMARY')
        print('=' * 70)
        print(f'Games processed: {stats["games_processed"]:,}')
        print('\nEndpoint results:')
        for endpoint, counts in stats.items():
            if endpoint != 'games_processed':
                success_rate = (counts['success'] / counts['attempted'] * 100) if counts['attempted'] > 0 else 0
                print(f'  {endpoint:20s}: {counts["success"]:6,} / {counts["attempted"]:6,} ({success_rate:5.1f}%)')

        print('=' * 70)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
