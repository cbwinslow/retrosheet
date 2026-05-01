#!/usr/bin/env python3
"""
File: scripts/bridge/populate_live_plate_appearances.py
Purpose: Populate core.live_plate_appearances from MLB API data
Author: Agent Cascade
Date: 2026-04-25
Usage: uv run python scripts/bridge/populate_live_plate_appearances.py --season 2025

This fills the empty core.live_plate_appearances table (currently 0 rows).
Extracts plate appearance data from raw_mlb.live_feed_snapshots.
"""

import argparse
import json
import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()


def get_db_conn():
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        dbname=os.getenv('POSTGRES_DB', 'retrosheet'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
    )


def extract_plate_appearances_from_payload(payload: dict):
    """Extract plate appearance data from MLB API live feed payload."""
    pas = []

    if not payload or not isinstance(payload, dict):
        return pas

    # Navigate to plays
    live_data = payload.get('liveData', {})
    plays = live_data.get('plays', {})
    all_plays = plays.get('allPlays', [])

    game_pk = payload.get('gamePk')
    game_data = payload.get('gameData', {})
    datetime_info = game_data.get('datetime', {})
    game_date = datetime_info.get('officialDate')

    teams = game_data.get('teams', {})
    home_team = teams.get('home', {})
    away_team = teams.get('away', {})
    home_team_id = home_team.get('id')
    away_team_id = away_team.get('id')

    for play in all_plays:
        # Extract PA information
        result = play.get('result', {})
        about = play.get('about', {})
        matchup = play.get('matchup', {})

        pa_data = {
            'mlb_game_pk': game_pk,
            'game_date': game_date,
            'home_team_id': home_team_id,
            'away_team_id': away_team_id,
            'at_bat_index': play.get('atBatIndex'),
            'half_inning': about.get('halfInning'),
            'inning': about.get('inning'),
            'is_top_inning': about.get('isTopInning'),
            'outs': about.get('outs'),
            'pitcher_id': matchup.get('pitcher', {}).get('id'),
            'pitcher_name': matchup.get('pitcher', {}).get('fullName'),
            'pitcher_hand': matchup.get('pitchHand', {}).get('code'),
            'batter_id': matchup.get('batter', {}).get('id'),
            'batter_name': matchup.get('batter', {}).get('fullName'),
            'batter_hand': matchup.get('batSide', {}).get('code'),
            'event': result.get('event'),
            'event_type': result.get('eventType'),
            'description': result.get('description'),
            'rbi': result.get('rbi', 0),
            'away_score': result.get('awayScore'),
            'home_score': result.get('homeScore'),
            'is_out': result.get('isOut', False),
            'is_scoring_play': about.get('isScoringPlay', False),
            'has_review': about.get('hasReview', False),
            'has_out': about.get('hasOut', False),
            'count_strikes': about.get('count', {}).get('strikes'),
            'count_balls': about.get('count', {}).get('balls'),
            'count_outs': about.get('count', {}).get('outs'),
            'start_time': about.get('startTime'),
            'end_time': about.get('endTime'),
            'is_complete': about.get('isComplete', False),
            'is_pa_complete': result.get('isComplete', False),
            'play_id': play.get('playId'),
            'runners': json.dumps(play.get('runners', [])),
            'play_events': json.dumps(play.get('playEvents', [])),
            'api_payload': json.dumps(play),
        }

        pas.append(pa_data)

    return pas


def populate_live_plate_appearances(conn, season: int, limit: int | None = None):
    """Populate live_plate_appearances from live_feed_snapshots."""
    cur = conn.cursor()

    print('Fetching live feed snapshots...')
    cur.execute(
        """
        SELECT mlb_game_pk, game_date, payload
        FROM raw_mlb.live_feed_snapshots
        WHERE http_status = 200
        AND game_date BETWEEN %s AND %s
        ORDER BY game_date
        %s;
    """,
        (f'{season}-01-01', f'{season}-12-31', f'LIMIT {limit}' if limit else ''),
    )

    rows = cur.fetchall()
    print(f'  Found {len(rows):,} games to process')

    total_pas = 0
    games_with_pas = 0

    for i, (game_pk, _game_date, payload) in enumerate(rows):
        if i % 100 == 0:
            print(f'  Processing game {i + 1}/{len(rows)}...', end='\r')

        if not payload:
            continue

        try:
            pas = extract_plate_appearances_from_payload(payload)

            if pas:
                games_with_pas += 1

                for pa in pas:
                    # Check if PA already exists
                    cur.execute(
                        """
                        SELECT 1 FROM core.live_plate_appearances
                        WHERE mlb_game_pk = %s AND at_bat_index = %s
                        LIMIT 1;
                    """,
                        (pa['mlb_game_pk'], pa['at_bat_index']),
                    )

                    if cur.fetchone():
                        continue

                    # Insert PA
                    cur.execute(
                        """
                        INSERT INTO core.live_plate_appearances (
                            mlb_game_pk, game_date, home_team_id, away_team_id,
                            at_bat_index, half_inning, inning, is_top_inning, outs,
                            pitcher_id, pitcher_name, pitcher_hand,
                            batter_id, batter_name, batter_hand,
                            event, event_type, description, rbi,
                            away_score, home_score, is_out, is_scoring_play,
                            has_review, has_out, count_strikes, count_balls, count_outs,
                            start_time, end_time, is_complete, is_pa_complete,
                            play_id, runners, play_events, api_payload
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s::jsonb, %s::jsonb, %s::jsonb
                        ) ON CONFLICT DO NOTHING;
                    """,
                        (
                            pa['mlb_game_pk'],
                            pa['game_date'],
                            pa['home_team_id'],
                            pa['away_team_id'],
                            pa['at_bat_index'],
                            pa['half_inning'],
                            pa['inning'],
                            pa['is_top_inning'],
                            pa['outs'],
                            pa['pitcher_id'],
                            pa['pitcher_name'],
                            pa['pitcher_hand'],
                            pa['batter_id'],
                            pa['batter_name'],
                            pa['batter_hand'],
                            pa['event'],
                            pa['event_type'],
                            pa['description'],
                            pa['rbi'],
                            pa['away_score'],
                            pa['home_score'],
                            pa['is_out'],
                            pa['is_scoring_play'],
                            pa['has_review'],
                            pa['has_out'],
                            pa['count_strikes'],
                            pa['count_balls'],
                            pa['count_outs'],
                            pa['start_time'],
                            pa['end_time'],
                            pa['is_complete'],
                            pa['is_pa_complete'],
                            pa['play_id'],
                            pa['runners'],
                            pa['play_events'],
                            pa['api_payload'],
                        ),
                    )

                    total_pas += 1

                # Commit every 10 games
                if games_with_pas % 10 == 0:
                    conn.commit()

        except Exception as e:
            print(f'\n  Error processing game {game_pk}: {e}')
            continue

    conn.commit()
    cur.close()

    print(f'\n  Games processed: {len(rows):,}')
    print(f'  Games with PAs: {games_with_pas:,}')
    print(f'  Total PAs inserted: {total_pas:,}')

    return total_pas


def main():
    parser = argparse.ArgumentParser(description='Populate live_plate_appearances')
    parser.add_argument('--season', type=int, required=True)
    parser.add_argument('--limit', type=int, help='Limit number of games')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    conn = get_db_conn()

    try:
        print('=' * 70)
        print(f'Populating core.live_plate_appearances - Season {args.season}')
        print('=' * 70)

        if args.dry_run:
            print('DRY RUN - Would process games and extract PAs')
            return

        populate_live_plate_appearances(conn, args.season, args.limit)

        # Final count
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM core.live_plate_appearances')
        total = cur.fetchone()[0]
        cur.close()

        print('=' * 70)
        print(f'FINAL: core.live_plate_appearances has {total:,} rows')
        print('=' * 70)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
