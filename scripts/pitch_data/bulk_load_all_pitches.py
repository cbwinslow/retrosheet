#!/usr/bin/env python3
"""
BULK load ALL Statcast pitch data using INSERT...SELECT
This loads ALL pitches for ALL seasons without the 50K batch cursor limit.

Usage:
    python scripts/pitch_data/bulk_load_all_pitches.py --seasons 2025
    python scripts/pitch_data/bulk_load_all_pitches.py --all
    python scripts/pitch_data/bulk_load_all_pitches.py --dry-run
"""

import argparse
import logging
import os

import psycopg2


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_connection():
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=int(os.getenv('PGPORT', 5432)),
        database=os.getenv('PGDATABASE', 'retrosheet'),
        user=os.getenv('PGUSER', os.getenv('USER', 'postgres')),
    )


def get_season_counts(conn) -> list[tuple[int, int]]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT game_year::int, COUNT(*) 
            FROM raw_mlb.statcast 
            WHERE game_year IS NOT NULL AND plate_x IS NOT NULL
            GROUP BY game_year::int 
            ORDER BY game_year::int DESC
        """)
        return cur.fetchall()


def get_loaded_counts(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute('SELECT game_year, COUNT(*) FROM features_pitch.locations GROUP BY game_year')
        return {row[0]: row[1] for row in cur.fetchall()}


def load_season_bulk(conn, season: int) -> int:
    """Load entire season using single INSERT...SELECT (fastest for PostgreSQL)."""
    logger.info(f'BULK loading season {season}...')

    with conn.cursor() as cur:
        # Check if already loaded
        cur.execute('SELECT COUNT(*) FROM features_pitch.locations WHERE game_year = %s', (season,))
        if cur.fetchone()[0] > 0:
            logger.warning(f'Season {season} already loaded. Use --force to reload.')
            return 0

        # Single bulk insert - let PostgreSQL handle it efficiently
        cur.execute(
            """
            INSERT INTO features_pitch.locations (
                game_year, game_pk, batter_id, pitcher_id, pitch_type,
                plate_x, plate_z, sz_top, sz_bot, pfx_x, pfx_z,
                start_speed, spin_rate, pitch_result, zone, balls, strikes,
                inning, inning_topbot, hc_x, hc_y, hit_location, bb_type,
                launch_speed, launch_angle, hit_distance
            )
            SELECT 
                s.game_year::integer,
                s.game_pk::integer,
                s.batter::integer,
                s.pitcher::integer,
                s.pitch_type,
                s.plate_x::numeric,
                s.plate_z::numeric,
                s.sz_top::numeric,
                s.sz_bot::numeric,
                s.pfx_x::numeric,
                s.pfx_z::numeric,
                s.release_speed::numeric,
                s.spin_rate_deprecated::numeric,
                s.des,
                s.zone::integer,
                s.balls::integer,
                s.strikes::integer,
                s.inning::integer,
                s.inning_topbot,
                s.hc_x::numeric,
                s.hc_y::numeric,
                s.hit_location::integer,
                s.bb_type,
                s.launch_speed::numeric,
                s.launch_angle::numeric,
                s.hit_distance_sc::numeric
            FROM raw_mlb.statcast s
            WHERE s.game_year = %s
              AND s.plate_x IS NOT NULL
              AND s.plate_z IS NOT NULL
        """,
            (season,),
        )

        inserted = cur.rowcount
        conn.commit()

        logger.info(f'Inserted {inserted:,} pitches for season {season}')

        # Update geometry
        logger.info(f'Updating PostGIS geometry for {inserted:,} pitches...')
        cur.execute(
            """
            UPDATE features_pitch.locations 
            SET location = ST_SetSRID(ST_MakePoint(plate_x, plate_z), 4326)
            WHERE game_year = %s
              AND plate_x IS NOT NULL 
              AND plate_z IS NOT NULL
        """,
            (season,),
        )

        conn.commit()
        logger.info(f'✓ Season {season} complete: {inserted:,} pitches with geometry')
        return inserted


def clear_season(conn, season: int):
    """Clear existing data for a season."""
    with conn.cursor() as cur:
        cur.execute('DELETE FROM features_pitch.locations WHERE game_year = %s', (season,))
        deleted = cur.rowcount
        conn.commit()
        if deleted > 0:
            logger.info(f'Cleared {deleted:,} existing rows for season {season}')


def main():
    parser = argparse.ArgumentParser(description='BULK Load ALL Statcast pitch data')
    parser.add_argument('--seasons', type=str, help='Seasons to load (e.g., 2015-2025)')
    parser.add_argument('--all', action='store_true', help='Load all seasons')
    parser.add_argument('--force', action='store_true', help='Force reload')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be loaded')

    args = parser.parse_args()

    conn = get_connection()

    try:
        available = get_season_counts(conn)
        loaded = get_loaded_counts(conn)

        logger.info('=' * 70)
        logger.info('BULK STATCAST PITCH LOADER')
        logger.info('=' * 70)

        logger.info('\nAvailable vs Loaded:')
        for year, count in available:
            loaded_count = loaded.get(year, 0)
            status = '✅' if loaded_count == count else f'⚠️  ({loaded_count:,}/{count:,})'
            logger.info(f'  {year}: {count:,} available, {loaded_count:,} loaded {status}')

        if args.dry_run:
            logger.info('\nDry run complete.')
            return

        # Parse seasons
        seasons_to_load = []
        if args.all:
            seasons_to_load = [year for year, _ in available]
        elif args.seasons:
            for part in args.seasons.split(','):
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    seasons_to_load.extend(range(start, end + 1))
                else:
                    seasons_to_load.append(int(part))

        available_years = {year for year, _ in available}
        seasons_to_load = [s for s in seasons_to_load if s in available_years]

        if not seasons_to_load:
            logger.error('No valid seasons to load')
            return

        logger.info(f'\nLoading {len(seasons_to_load)} season(s): {seasons_to_load}')
        logger.info('-' * 70)

        total = 0
        for season in seasons_to_load:
            if args.force:
                clear_season(conn, season)
            count = load_season_bulk(conn, season)
            total += count

        logger.info('-' * 70)
        logger.info(f'TOTAL PITCHES LOADED: {total:,}')
        logger.info('=' * 70)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
