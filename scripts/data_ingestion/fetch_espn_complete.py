#!/usr/bin/env python3
"""
File: scripts/data_ingestion/fetch_espn_complete.py
Purpose: Fetch ALL ESPN data - player stats, team stats, plays
Author: Agent Cascade
Date: 2026-04-25
Usage: uv run python scripts/data_ingestion/fetch_espn_complete.py --season 2025

Fills empty tables:
- raw_espn.player_stats_snapshots (currently 0 rows)
- raw_espn.team_stats_snapshots (currently 0 rows)
- raw_espn.plays_snapshots (only 1,271 rows - needs more)
"""

import argparse
import hashlib
import json
import os
import time

import psycopg2
import requests
from dotenv import load_dotenv


load_dotenv()

# ESPN API endpoints
ESPN_API_BASE = 'https://site.api.espn.com/apis/site/v2/sports/baseball/mlb'


def get_db_conn():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        dbname=os.getenv('POSTGRES_DB', 'retrosheet'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
    )


def fetch_json(url: str, params: dict = None):
    """Fetch JSON from ESPN API."""
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json(), response.status_code
        return None, response.status_code
    except Exception as e:
        print(f'  Error fetching {url}: {e}')
        return None, 0


def fetch_espn_schedule(season: int, limit: int = None):
    """Fetch ESPN schedule to get game IDs."""
    url = f'{ESPN_API_BASE}/scoreboard'

    # ESPN uses calendar dates
    games = []

    # Fetch for each month of the season
    months = ['03', '04', '05', '06', '07', '08', '09', '10']

    for month in months:
        # Get dates in the month
        start_date = f'{season}{month}01'

        params = {
            'dates': start_date,
            'limit': 100,
        }

        data, status = fetch_json(url, params)

        if data and 'events' in data:
            for event in data['events']:
                game_id = event.get('id')
                game_date = event.get('date', '')[:10]

                if game_id:
                    games.append({
                        'espn_game_id': game_id,
                        'game_date': game_date,
                        'name': event.get('name', ''),
                        'status': event.get('status', {}).get('type', {}).get('name', ''),
                    })

        time.sleep(0.5)  # Rate limiting

        if limit and len(games) >= limit:
            break

    return games


def fetch_espn_game_plays(espn_game_id: str):
    """Fetch play-by-play data for a specific game."""
    url = f'{ESPN_API_BASE}/summary'
    params = {'event': espn_game_id}

    data, status = fetch_json(url, params)

    if not data:
        return None

    # Extract plays from the response
    plays = []

    # Look for plays in various locations
    if 'plays' in data:
        plays.extend(data['plays'])

    if 'drives' in data and 'current' in data['drives']:
        if 'plays' in data['drives']['current']:
            plays.extend(data['drives']['current']['plays'])

    # Also check for boxscore data
    boxscore = data.get('boxscore', {})

    return {
        'plays': plays,
        'boxscore': boxscore,
        'full_response': data,
    }


def fetch_espn_player_stats(season: int):
    """Fetch player statistics leaders/stats from ESPN."""
    # ESPN player stats are typically in game summaries or leaderboards
    # We'll fetch from the statistics endpoint
    url = f'{ESPN_API_BASE}/statistics'

    params = {
        'season': season,
        'limit': 500,
    }

    data, status = fetch_json(url, params)

    if not data:
        return []

    # ESPN returns stats in categories
    stats = []

    categories = data.get('categories', [])
    for category in categories:
        for athlete in category.get('athletes', []):
            stats.append({
                'player_id': athlete.get('id'),
                'player_name': athlete.get('name', ''),
                'category': category.get('name', ''),
                'stats': athlete.get('statistics', []),
            })

    return stats


def fetch_espn_team_stats(season: int):
    """Fetch team statistics from ESPN."""
    url = f'{ESPN_API_BASE}/teams'

    params = {
        'season': season,
        'limit': 50,
    }

    data, status = fetch_json(url, params)

    if not data:
        return []

    teams = []
    for team in data.get('sports', [{}])[0].get('leagues', [{}])[0].get('teams', []):
        team_data = team.get('team', {})
        teams.append({
            'team_id': team_data.get('id'),
            'team_name': team_data.get('name', ''),
            'abbreviation': team_data.get('abbreviation', ''),
            'record': team_data.get('record', {}),
        })

    return teams


def store_espn_plays(conn, espn_game_id: str, game_date: str, plays_data: dict):
    """Store ESPN plays data."""
    if not plays_data:
        return False

    cur = conn.cursor()

    payload_json = json.dumps(plays_data, sort_keys=True)
    checksum = hashlib.md5(payload_json.encode()).hexdigest()

    try:
        cur.execute("""
            INSERT INTO raw_espn.plays_snapshots 
                (espn_game_id, game_date, http_status, response_time_ms, payload, checksum)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (espn_game_id, checksum) DO NOTHING
            RETURNING id;
        """, (espn_game_id, game_date, 200, 0, payload_json, checksum))

        result = cur.fetchone()
        conn.commit()
        return result is not None
    except Exception as e:
        conn.rollback()
        print(f'  DB Error: {e}')
        return False
    finally:
        cur.close()


def store_espn_player_stats(conn, season: int, stats: list):
    """Store ESPN player stats."""
    cur = conn.cursor()
    inserted = 0

    for stat in stats:
        player_id = stat.get('player_id')
        if not player_id:
            continue

        payload_json = json.dumps(stat, sort_keys=True)
        checksum = hashlib.md5(payload_json.encode()).hexdigest()

        try:
            cur.execute("""
                INSERT INTO raw_espn.player_stats_snapshots
                    (season, player_id, stat_category, http_status, response_time_ms,
                     request_params, payload, checksum)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                ON CONFLICT (season, player_id, stat_category, checksum) DO NOTHING
                RETURNING id;
            """, (season, player_id, stat.get('category', 'general'), 200, 0,
                  json.dumps({'season': season}), payload_json, checksum))

            if cur.fetchone():
                inserted += 1

            if inserted % 100 == 0:
                conn.commit()
        except Exception as e:
            conn.rollback()
            print(f'  Error storing player {player_id}: {e}')

    conn.commit()
    cur.close()
    return inserted


def store_espn_team_stats(conn, season: int, teams: list):
    """Store ESPN team stats."""
    cur = conn.cursor()
    inserted = 0

    for team in teams:
        team_id = team.get('team_id')
        if not team_id:
            continue

        payload_json = json.dumps(team, sort_keys=True)
        checksum = hashlib.md5(payload_json.encode()).hexdigest()

        try:
            cur.execute("""
                INSERT INTO raw_espn.team_stats_snapshots
                    (season, team_id, team_name, http_status, response_time_ms,
                     request_params, payload, checksum)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                ON CONFLICT (season, team_id, checksum) DO NOTHING
                RETURNING id;
            """, (season, team_id, team.get('team_name', ''), 200, 0,
                  json.dumps({'season': season}), payload_json, checksum))

            if cur.fetchone():
                inserted += 1

            if inserted % 30 == 0:
                conn.commit()
        except Exception as e:
            conn.rollback()
            print(f'  Error storing team {team_id}: {e}')

    conn.commit()
    cur.close()
    return inserted


def main():
    parser = argparse.ArgumentParser(description='Fetch ESPN data')
    parser.add_argument('--season', type=int, required=True)
    parser.add_argument('--limit', type=int, help='Limit number of games')
    parser.add_argument('--plays-only', action='store_true')
    parser.add_argument('--stats-only', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    conn = get_db_conn()

    try:
        print('=' * 70)
        print(f'Fetching ESPN Data - Season {args.season}')
        print('=' * 70)

        if not args.stats_only:
            # Fetch games and plays
            print('\nFetching ESPN games...')
            games = fetch_espn_schedule(args.season, args.limit)
            print(f'  Found {len(games):,} games')

            if args.dry_run:
                print('  DRY RUN - Would fetch plays for these games')
            else:
                print('\nFetching plays for each game...')
                play_count = 0
                for i, game in enumerate(games):
                    if i % 100 == 0:
                        print(f'  Processing game {i+1}/{len(games)}...', end='\r')

                    plays_data = fetch_espn_game_plays(game['espn_game_id'])
                    if plays_data:
                        if store_espn_plays(conn, game['espn_game_id'],
                                          game['game_date'], plays_data):
                            play_count += 1

                    time.sleep(0.1)

                print(f'\n  Stored plays for {play_count:,} games')

        if not args.plays_only:
            # Fetch player stats
            print('\nFetching ESPN player stats...')
            player_stats = fetch_espn_player_stats(args.season)
            if player_stats and not args.dry_run:
                count = store_espn_player_stats(conn, args.season, player_stats)
                print(f'  Stored {count:,} player stat records')

            # Fetch team stats
            print('\nFetching ESPN team stats...')
            teams = fetch_espn_team_stats(args.season)
            if teams and not args.dry_run:
                count = store_espn_team_stats(conn, args.season, teams)
                print(f'  Stored {count:,} team records')

        # Summary
        if not args.dry_run:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM raw_espn.plays_snapshots')
            plays_count = cur.fetchone()[0]

            cur.execute('SELECT COUNT(*) FROM raw_espn.player_stats_snapshots')
            player_count = cur.fetchone()[0]

            cur.execute('SELECT COUNT(*) FROM raw_espn.team_stats_snapshots')
            team_count = cur.fetchone()[0]

            cur.close()

            print('=' * 70)
            print('SUMMARY')
            print('=' * 70)
            print(f'raw_espn.plays_snapshots: {plays_count:,}')
            print(f'raw_espn.player_stats_snapshots: {player_count:,}')
            print(f'raw_espn.team_stats_snapshots: {team_count:,}')
            print('=' * 70)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
