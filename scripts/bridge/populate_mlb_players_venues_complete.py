#!/usr/bin/env python3
"""
File: scripts/bridge/populate_mlb_players_venues_complete.py
Purpose: Populate mlb.players and mlb.venues from MLB API data
Author: Agent Cascade
Date: 2026-04-25
Usage: uv run python scripts/bridge/populate_mlb_players_venues_complete.py --season 2025

CRITICAL: This populates mlb.venues which is needed for features_pitch.mv_park_context
"""

import argparse
import json
import os

import psycopg2
import requests
from dotenv import load_dotenv


load_dotenv()

MLB_API_BASE = 'https://statsapi.mlb.com/api/v1'


def get_db_conn():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        dbname=os.getenv('POSTGRES_DB', 'retrosheet'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
    )


def fetch_mlb_players(season: int, limit: int = None):
    """Fetch ALL MLB players for a season."""
    url = f'{MLB_API_BASE}/sports/1/players'
    params = {'season': season}

    print(f'Fetching players for season {season}...')
    response = requests.get(url, params=params, timeout=60)

    if response.status_code != 200:
        print(f'Error: HTTP {response.status_code}')
        return []

    data = response.json()
    players = data.get('people', [])

    print(f'  Found {len(players):,} players')
    return players


def fetch_mlb_teams(season: int):
    """Fetch MLB teams with venues."""
    url = f'{MLB_API_BASE}/teams'
    params = {'season': season, 'sportId': 1}

    print(f'Fetching teams for season {season}...')
    response = requests.get(url, params=params, timeout=60)

    if response.status_code != 200:
        print(f'Error: HTTP {response.status_code}')
        return []

    data = response.json()
    teams = data.get('teams', [])

    print(f'  Found {len(teams):,} teams')
    return teams


def fetch_mlb_venues(season: int):
    """Fetch ALL MLB venues."""
    url = f'{MLB_API_BASE}/venues'
    params = {'season': season}

    print(f'Fetching venues for season {season}...')
    response = requests.get(url, params=params, timeout=60)

    if response.status_code != 200:
        print(f'Error: HTTP {response.status_code}')
        return []

    data = response.json()
    venues = data.get('venues', [])

    print(f'  Found {len(venues):,} venues')
    return venues


def store_mlb_players(conn, players: list, season: int):
    """Store players in mlb.players table."""
    cur = conn.cursor()
    inserted = 0

    for player in players:
        player_id = player.get('id')
        full_name = player.get('fullName', '')
        first_name = player.get('firstName', '')
        last_name = player.get('lastName', '')
        primary_position = player.get('primaryPosition', {}).get('abbreviation', '')
        birth_date = player.get('birthDate')
        current_team_id = player.get('currentTeam', {}).get('id')

        try:
            cur.execute(
                """
                INSERT INTO mlb.players (id, full_name, first_name, last_name, 
                                         primary_position, birth_date, current_team_id, 
                                         season, api_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    primary_position = EXCLUDED.primary_position,
                    current_team_id = EXCLUDED.current_team_id,
                    season = EXCLUDED.season,
                    api_data = EXCLUDED.api_data;
            """,
                (
                    player_id,
                    full_name,
                    first_name,
                    last_name,
                    primary_position,
                    birth_date,
                    current_team_id,
                    season,
                    json.dumps(player),
                ),
            )
            inserted += 1

            if inserted % 100 == 0:
                conn.commit()
                print(f'  Stored {inserted:,} players...', end='\r')
        except Exception as e:
            print(f'  Error storing player {player_id}: {e}')

    conn.commit()
    cur.close()
    print(f'  Stored {inserted:,} players total')
    return inserted


def store_mlb_venues(conn, venues: list, season: int):
    """Store venues in mlb.venues table."""
    cur = conn.cursor()
    inserted = 0

    for venue in venues:
        venue_id = venue.get('id')
        name = venue.get('name', '')
        city = venue.get('city', '')
        state = venue.get('state', '')
        country = venue.get('country', '')

        # Extract location info
        location = venue.get('location', {})
        default_coordinates = venue.get('defaultCoordinates', {})
        latitude = default_coordinates.get('latitude')
        longitude = default_coordinates.get('longitude')

        # Try to get timeZone from location or directly
        time_zone = location.get('timeZone', '') if isinstance(location, dict) else ''

        try:
            cur.execute(
                """
                INSERT INTO mlb.venues (id, name, city, state, country, 
                                       time_zone, latitude, longitude,
                                       season, api_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    city = EXCLUDED.city,
                    state = EXCLUDED.state,
                    country = EXCLUDED.country,
                    time_zone = EXCLUDED.time_zone,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    season = EXCLUDED.season,
                    api_data = EXCLUDED.api_data;
            """,
                (
                    venue_id,
                    name,
                    city,
                    state,
                    country,
                    time_zone,
                    latitude,
                    longitude,
                    season,
                    json.dumps(venue),
                ),
            )
            inserted += 1

            if inserted % 10 == 0:
                conn.commit()
                print(f'  Stored {inserted:,} venues...', end='\r')
        except Exception as e:
            print(f'  Error storing venue {venue_id}: {e}')

    conn.commit()
    cur.close()
    print(f'  Stored {inserted:,} venues total')
    return inserted


def link_venues_to_retrosheet(conn, season: int):
    """Link MLB venues to retrosheet park IDs using name matching."""
    cur = conn.cursor()

    print('Linking MLB venues to Retrosheet parks...')

    # Find venues that might match parks based on city/state
    cur.execute(
        """
        UPDATE mlb.venues v
        SET retrosheet_id = p.park_id
        FROM core.parks p
        WHERE v.retrosheet_id IS NULL
        AND (v.city = p.city OR v.name ILIKE '%' || p.name || '%')
        AND v.season = %s;
    """,
        (season,),
    )

    updated = cur.rowcount
    conn.commit()
    cur.close()

    print(f'  Linked {updated} venues to Retrosheet parks')
    return updated


def main():
    parser = argparse.ArgumentParser(description='Populate MLB players and venues')
    parser.add_argument('--season', type=int, required=True)
    parser.add_argument('--skip-players', action='store_true')
    parser.add_argument('--skip-venues', action='store_true')
    parser.add_argument(
        '--link-parks', action='store_true', help='Link venues to Retrosheet park IDs'
    )
    args = parser.parse_args()

    conn = get_db_conn()

    try:
        print('=' * 70)
        print(f'Populating MLB Players & Venues - Season {args.season}')
        print('=' * 70)

        # Players
        if not args.skip_players:
            players = fetch_mlb_players(args.season)
            if players:
                store_mlb_players(conn, players, args.season)

        # Venues
        if not args.skip_venues:
            venues = fetch_mlb_venues(args.season)
            if venues:
                store_mlb_venues(conn, venues, args.season)

        # Link to retrosheet
        if args.link_parks:
            link_venues_to_retrosheet(conn, args.season)

        # Summary
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM mlb.players')
        player_count = cur.fetchone()[0]

        cur.execute('SELECT COUNT(*) FROM mlb.venues')
        venue_count = cur.fetchone()[0]

        cur.execute('SELECT COUNT(*) FROM mlb.venues WHERE retrosheet_id IS NOT NULL')
        linked_count = cur.fetchone()[0]

        cur.close()

        print('=' * 70)
        print('SUMMARY')
        print('=' * 70)
        print(f'mlb.players: {player_count:,} total')
        print(f'mlb.venues: {venue_count:,} total')
        print(f'mlb.venues with retrosheet_id: {linked_count:,}')
        print('=' * 70)

        if linked_count > 0:
            print('✅ Venues linked to Retrosheet! mv_park_context should now work.')

    finally:
        conn.close()


if __name__ == '__main__':
    main()
