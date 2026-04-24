#!/usr/bin/env python3
"""
Populate MLB reference tables (players, teams, venues) from raw game feed data.
"""

import os

import psycopg2


def database_kwargs():
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def populate_mlb_teams():
    """Populate mlb.teams table from raw game feed data."""
    print('📊 Populating MLB teams...')

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Check how many records we can extract
            cur.execute("""
                SELECT COUNT(*) as total_feeds,
                       COUNT(CASE WHEN payload->'gameData'->'teams'->'home'->>'id' IS NOT NULL THEN 1 END) as home_teams,
                       COUNT(CASE WHEN payload->'gameData'->'teams'->'away'->>'id' IS NOT NULL THEN 1 END) as away_teams
                FROM raw_mlb.live_feed_snapshots
                WHERE http_status = 200;
            """)
            total_feeds, home_teams, away_teams = cur.fetchone()
            print(f'   Found {total_feeds} feeds, {home_teams} home teams, {away_teams} away teams')

            # Extract teams from game feeds
            cur.execute("""
                INSERT INTO mlb.teams (mlb_id, team_name, team_code, location_name, league_name, active, first_year)
                SELECT DISTINCT
                    (lfs.payload->'gameData'->'teams'->'home'->>'id')::bigint as mlb_id,
                    lfs.payload->'gameData'->'teams'->'home'->>'name' as team_name,
                    lfs.payload->'gameData'->'teams'->'home'->>'teamCode' as team_code,
                    lfs.payload->'gameData'->'teams'->'home'->>'locationName' as location_name,
                    'MLB' as league_name,
                    true as active,
                    EXTRACT(YEAR FROM CURRENT_DATE)::int as first_year
                FROM raw_mlb.live_feed_snapshots lfs
                WHERE lfs.http_status = 200
                  AND lfs.payload->'gameData'->'teams'->'home'->>'id' IS NOT NULL
                ON CONFLICT (mlb_id) DO NOTHING;
            """)

            home_count = cur.rowcount
            print(f'   Inserted {home_count} home teams')

            cur.execute("""
                INSERT INTO mlb.teams (mlb_id, team_name, team_code, location_name, league_name, active, first_year)
                SELECT DISTINCT
                    (lfs.payload->'gameData'->'teams'->'away'->>'id')::bigint as mlb_id,
                    lfs.payload->'gameData'->'teams'->'away'->>'name' as team_name,
                    lfs.payload->'gameData'->'teams'->'away'->>'teamCode' as team_code,
                    lfs.payload->'gameData'->'teams'->'away'->>'locationName' as location_name,
                    'MLB' as league_name,
                    true as active,
                    EXTRACT(YEAR FROM CURRENT_DATE)::int as first_year
                FROM raw_mlb.live_feed_snapshots lfs
                WHERE lfs.http_status = 200
                  AND lfs.payload->'gameData'->'teams'->'away'->>'id' IS NOT NULL
                ON CONFLICT (mlb_id) DO NOTHING;
            """)

            away_count = cur.rowcount
            print(f'   Inserted {away_count} away teams')

        conn.commit()
        print(f'✅ MLB teams populated: {home_count + away_count} total')

    finally:
        conn.close()


def populate_mlb_venues():
    """Populate mlb.venues table from raw game feed data."""
    print('🏟️ Populating MLB venues...')

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO mlb.venues (mlb_id, name, location, time_zone)
                SELECT DISTINCT
                    (v->>'id')::bigint as mlb_id,
                    v->>'name' as name,
                    COALESCE(v->>'location'->>'city', '') || ', ' || COALESCE(v->>'location'->>'state', '') as location,
                    v->>'timeZone'->>'id' as time_zone
                FROM raw_mlb.live_feed_snapshots lfs,
                     jsonb_array_elements(lfs.payload->'gameData'->'venue') as v
                WHERE lfs.http_status = 200
                  AND v->>'id' IS NOT NULL
                ON CONFLICT (mlb_id) DO NOTHING;
            """)

        conn.commit()
        print('✅ MLB venues populated')

    finally:
        conn.close()


def populate_mlb_players():
    """Populate mlb.players table from raw game feed data."""
    print('👥 Populating MLB players...')

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Extract players from boxscore
            cur.execute("""
                INSERT INTO mlb.players (
                    mlb_id, full_name, first_name, last_name, primary_number,
                    bat_side, pitch_hand, mlb_debut_date, active
                )
                SELECT DISTINCT
                    (p->>'id')::bigint as mlb_id,
                    p->>'fullName' as full_name,
                    p->>'firstName' as first_name,
                    p->>'lastName' as last_name,
                    NULLIF(p->>'primaryNumber', '') as primary_number,
                    CASE
                        WHEN p->>'batSide'->>'code' = 'R' THEN 'R'
                        WHEN p->>'batSide'->>'code' = 'L' THEN 'L'
                        WHEN p->>'batSide'->>'code' = 'S' THEN 'S'
                        ELSE NULL
                    END as bat_side,
                    CASE
                        WHEN p->>'pitchHand'->>'code' = 'R' THEN 'R'
                        WHEN p->>'pitchHand'->>'code' = 'L' THEN 'L'
                        ELSE NULL
                    END as pitch_hand,
                    NULLIF(p->>'mlbDebutDate', '')::date as mlb_debut_date,
                    CASE WHEN p->>'active' = 'true' THEN true ELSE false END as active
                FROM raw_mlb.live_feed_snapshots lfs,
                     jsonb_object_keys(lfs.payload->'gameData'->'players') as player_key,
                     jsonb_extract_path(lfs.payload->'gameData'->'players', player_key) as p
                WHERE lfs.http_status = 200
                  AND p->>'id' IS NOT NULL
                  AND p->>'fullName' IS NOT NULL
                ON CONFLICT (mlb_id) DO UPDATE SET
                    full_name = EXCLUDED.full_name,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    primary_number = EXCLUDED.primary_number,
                    bat_side = COALESCE(EXCLUDED.bat_side, mlb.players.bat_side),
                    pitch_hand = COALESCE(EXCLUDED.pitch_hand, mlb.players.pitch_hand),
                    mlb_debut_date = COALESCE(EXCLUDED.mlb_debut_date, mlb.players.mlb_debut_date),
                    active = EXCLUDED.active;
            """)

        conn.commit()
        print('✅ MLB players populated')

    finally:
        conn.close()


def populate_mlb_pitches():
    """Populate mlb.pitches table from raw game feed data."""
    print('⚾ Populating MLB pitches...')

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Extract pitches from all innings
            cur.execute("""
                INSERT INTO mlb.pitches (
                    game_pk, event_index, pitch_index, pitch_number,
                    pitch_type_code, pitch_type_description, pitch_call_code,
                    plate_x, plate_z, start_speed, spin_rate
                )
                SELECT
                    lfs.game_pk,
                    (play->>'atBatIndex')::int as event_index,
                    (pitch->>'pitchNumber')::int - 1 as pitch_index,
                    (pitch->>'pitchNumber')::int as pitch_number,
                    pitch->'pitchType'->>'code' as pitch_type_code,
                    pitch->'pitchType'->>'description' as pitch_type_description,
                    pitch->'pitchResult'->>'pitchResultType' as pitch_call_code,
                    (pitch->'coordinates'->>'pX')::numeric as plate_x,
                    (pitch->'coordinates'->>'pZ')::numeric as plate_z,
                    (pitch->'pitchData'->'startSpeed')::numeric as start_speed,
                    (pitch->'pitchData'->'breaks'->'spinRate')::int as spin_rate
                FROM raw_mlb.live_feed_snapshots lfs,
                     jsonb_array_elements(lfs.payload->'liveData'->'plays'->'allPlays') as play,
                     jsonb_array_elements(play->'playEvents') as event,
                     jsonb_array_elements(event->'pitchData'->'pitches') as pitch
                WHERE lfs.http_status = 200
                  AND play->>'atBatIndex' IS NOT NULL
                  AND pitch->'pitchNumber' IS NOT NULL
                ON CONFLICT (game_pk, event_index, pitch_index) DO NOTHING;
            """)

        conn.commit()
        print('✅ MLB pitches populated')

    finally:
        conn.close()


def update_team_venue_links():
    """Link teams to their home venues."""
    print('🔗 Linking teams to venues...')

    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE mlb.teams
                SET venue_id = v.mlb_id
                FROM mlb.venues v,
                     raw_mlb.live_feed_snapshots lfs,
                     jsonb_array_elements(lfs.payload->'gameData'->'teams'->'home') as t
                WHERE teams.mlb_id = (t->>'id')::bigint
                  AND v.mlb_id = (lfs.payload->'gameData'->'venue'->>'id')::bigint
                  AND lfs.http_status = 200
                  AND teams.venue_id IS NULL;
            """)

        conn.commit()
        print('✅ Team-venue links updated')

    finally:
        conn.close()


def main():
    print('🚀 Populating MLB reference tables...')

    populate_mlb_teams()
    populate_mlb_venues()
    populate_mlb_players()
    populate_mlb_pitches()
    update_team_venue_links()

    # Show summary
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM mlb.players) as players,
                    (SELECT COUNT(*) FROM mlb.teams) as teams,
                    (SELECT COUNT(*) FROM mlb.venues) as venues,
                    (SELECT COUNT(*) FROM mlb.pitches) as pitches
            """)
            players, teams, venues, pitches = cur.fetchone()
            print('\n📊 Population Summary:')
            print(f'   👥 Players: {players}')
            print(f'   🏟️ Teams: {teams}')
            print(f'   🏟️ Venues: {venues}')
            print(f'   ⚾ Pitches: {pitches}')

    finally:
        conn.close()

    print('🎉 MLB reference tables populated!')


if __name__ == '__main__':
    main()
