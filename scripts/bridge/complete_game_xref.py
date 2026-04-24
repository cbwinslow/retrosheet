#!/usr/bin/env python3
"""
Complete bridge.game_xref population by matching MLB games to Retrosheet games.

This script matches games by date + home/away teams using bridge.team_xref mappings.
It populates missing game_xref entries for recent MLB games that don't have Retrosheet mappings.
"""

from __future__ import annotations

import os
from datetime import date

import psycopg2


def database_kwargs() -> dict[str, str]:
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def complete_game_xref(
    season: int | None = None,
    min_date: date | None = None,
    max_date: date | None = None,
    dry_run: bool = False,
) -> None:
    """
    Populate bridge.game_xref by matching MLB games to Retrosheet games.

    Args:
        season: Filter by season (optional)
        min_date: Filter by minimum game date (optional)
        max_date: Filter by maximum game date (optional)
        dry_run: If True, print matches without inserting
    """
    conn = psycopg2.connect(**database_kwargs())
    try:
        with conn.cursor() as cur:
            # Build WHERE clause
            where_conditions = []

            if season is not None:
                where_conditions.append(f'season = {season}')

            if min_date is not None:
                where_conditions.append(f"game_date >= '{min_date}'")

            if max_date is not None:
                where_conditions.append(f"game_date <= '{max_date}'")

            # Get MLB games without game_xref mappings
            query = """
                WITH mlb_games_without_xref AS (
                    SELECT
                        g.mlb_game_pk as game_pk,
                        g.game_date::date as game_date,
                        g.season::int as season,
                        g.home_team_id,
                        g.away_team_id,
                        g.home_team_name,
                        g.away_team_name
                    FROM core.live_games g
                    LEFT JOIN bridge.game_xref x ON g.mlb_game_pk = x.mlb_game_pk
                    WHERE g.mlb_game_pk IS NOT NULL
                    AND x.mlb_game_pk IS NULL
            """

            # Add filters if provided
            if season is not None:
                query += f' AND g.season::int = {season}'
            if min_date is not None:
                query += f" AND g.game_date::date >= '{min_date}'"
            if max_date is not None:
                query += f" AND g.game_date::date <= '{max_date}'"

            query += """
                    ORDER BY g.game_date DESC
                )
                SELECT * FROM mlb_games_without_xref
            """

            cur.execute(query)
            mlb_games = cur.fetchall()

            print(f'Found {len(mlb_games)} MLB games without game_xref mappings')

            if dry_run:
                print('DRY RUN - No inserts will be performed')

            matched = 0
            unmatched = []

            for game in mlb_games:
                (
                    game_pk,
                    game_date,
                    season,
                    home_team_id,
                    away_team_id,
                    home_team_name,
                    away_team_name,
                ) = game

                # Extract numeric team ID from MLB text ID (e.g., "MLB146" -> 146)
                try:
                    home_team_id_int = int(home_team_id.replace('MLB', ''))
                except (ValueError, AttributeError):
                    home_team_id_int = None

                try:
                    away_team_id_int = int(away_team_id.replace('MLB', ''))
                except (ValueError, AttributeError):
                    away_team_id_int = None

                if not home_team_id_int or not away_team_id_int:
                    unmatched.append(
                        {
                            'game_pk': game_pk,
                            'game_date': str(game_date),
                            'reason': 'invalid team ID format',
                            'home_team': home_team_name,
                            'away_team': away_team_name,
                        },
                    )
                    continue

                # Get Retrosheet team IDs from bridge.team_xref
                cur.execute(
                    """
                    SELECT retrosheet_team_id
                    FROM bridge.team_xref
                    WHERE mlb_team_id = %s
                    LIMIT 1
                    """,
                    (home_team_id_int,),
                )
                home_retro = cur.fetchone()

                cur.execute(
                    """
                    SELECT retrosheet_team_id
                    FROM bridge.team_xref
                    WHERE mlb_team_id = %s
                    LIMIT 1
                    """,
                    (away_team_id_int,),
                )
                away_retro = cur.fetchone()

                if not home_retro or not away_retro:
                    unmatched.append(
                        {
                            'game_pk': game_pk,
                            'game_date': str(game_date),
                            'reason': 'missing team mapping',
                            'home_team': home_team_name,
                            'away_team': away_team_name,
                        },
                    )
                    continue

                home_retro_id = home_retro[0]
                away_retro_id = away_retro[0]

                # Match Retrosheet game by date + teams
                cur.execute(
                    """
                    SELECT game_id
                    FROM core.games
                    WHERE game_date = %s
                    AND home_team_id = %s
                    AND away_team_id = %s
                    LIMIT 1
                    """,
                    (game_date, home_retro_id, away_retro_id),
                )
                retro_game = cur.fetchone()

                # Check if retrosheet game already exists in bridge table
                cur.execute(
                    """
                    SELECT mlb_game_pk
                    FROM bridge.game_xref
                    WHERE retrosheet_game_id = %s
                    LIMIT 1
                    """,
                    (retro_game[0] if retro_game else None,),
                )
                existing_mapping = cur.fetchone()

                if existing_mapping:
                    unmatched.append(
                        {
                            'game_pk': game_pk,
                            'game_date': str(game_date),
                            'reason': 'retrosheet game already mapped',
                            'existing_mlb_pk': existing_mapping[0],
                            'home_team': home_team_name,
                            'away_team': away_team_name,
                        },
                    )
                    continue

                if not retro_game:
                    unmatched.append(
                        {
                            'game_pk': game_pk,
                            'game_date': str(game_date),
                            'reason': 'no matching retrosheet game',
                            'home_retro': home_retro_id,
                            'away_retro': away_retro_id,
                            'home_team': home_team_name,
                            'away_team': away_team_name,
                        },
                    )
                    continue

                retro_game_id = retro_game[0]

                if dry_run:
                    print(
                        f'Would match: MLB {game_pk} -> Retrosheet {retro_game_id} on {game_date}',
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO bridge.game_xref (mlb_game_pk, retrosheet_game_id, game_date, home_team_id, away_team_id, updated_at)
                        VALUES (%s, %s, %s, %s, %s, now())
                        ON CONFLICT (mlb_game_pk) DO UPDATE
                        SET retrosheet_game_id = EXCLUDED.retrosheet_game_id,
                            game_date = EXCLUDED.game_date,
                            home_team_id = EXCLUDED.home_team_id,
                            away_team_id = EXCLUDED.away_team_id,
                            updated_at = now()
                        """,
                        (game_pk, retro_game_id, game_date, home_team_id_int, away_team_id_int),
                    )

                matched += 1
                if matched % 100 == 0:
                    print(f'Matched {matched} games...')

            conn.commit()
            print(f'Total games matched: {matched}')
            print(f'Total games unmatched: {len(unmatched)}')

            if unmatched and len(unmatched) <= 20:
                print('Unmatched games:')
                for item in unmatched:
                    print(f'  {item}')
            elif unmatched:
                print('First 20 unmatched games:')
                for item in unmatched[:20]:
                    print(f'  {item}')

    finally:
        conn.close()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description='Complete bridge.game_xref population by matching MLB games to Retrosheet games.',
    )
    parser.add_argument('--season', type=int, help='Filter by season')
    parser.add_argument('--min-date', type=str, help='Minimum game date (YYYY-MM-DD)')
    parser.add_argument('--max-date', type=str, help='Maximum game date (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', help='Print matches without inserting')

    args = parser.parse_args()

    min_date = date.fromisoformat(args.min_date) if args.min_date else None
    max_date = date.fromisoformat(args.max_date) if args.max_date else None

    complete_game_xref(
        season=args.season,
        min_date=min_date,
        max_date=max_date,
        dry_run=args.dry_run,
    )


if __name__ == '__main__':
    main()
