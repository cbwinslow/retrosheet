#!/usr/bin/env python3
"""
Load all Statcast pitch seasons into features_pitch.locations table.
Follows pybaseball schema conventions for column naming.

Usage:
    python scripts/pitch_data/load_all_pitch_seasons.py --seasons 2015-2025
    python scripts/pitch_data/load_all_pitch_seasons.py --seasons 2024
    python scripts/pitch_data/load_all_pitch_seasons.py --dry-run  # Show what would be loaded

References:
    - pybaseball schema: https://github.com/jldbc/pybaseball
    - Baseball Savant CSV docs: https://baseballsavant.mlb.com/csv-docs
"""

import argparse
import logging
import os
import sys
from typing import List, Tuple

import psycopg2
from psycopg2.extras import execute_values

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_connection():
    """Get PostgreSQL connection from environment or defaults."""
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", 5432)),
        database=os.getenv("PGDATABASE", "retrosheet"),
        user=os.getenv("PGUSER", os.getenv("USER", "postgres")),
    )


def get_season_counts(conn) -> List[Tuple[int, int]]:
    """Get pitch counts by season from raw_mlb.statcast."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT game_year::int, COUNT(*) 
            FROM raw_mlb.statcast 
            WHERE game_year IS NOT NULL
            GROUP BY game_year 
            ORDER BY game_year DESC
        """)
        return cur.fetchall()


def get_loaded_season_counts(conn) -> List[Tuple[int, int]]:
    """Get already loaded pitch counts by season."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT game_year, COUNT(*) 
            FROM features_pitch.locations 
            GROUP BY game_year 
            ORDER BY game_year DESC
        """)
        return cur.fetchall()


def load_season(conn, season: int, batch_size: int = 50000) -> int:
    """
    Load a single season's pitch data into features_pitch.locations.

    Uses batched inserts for memory efficiency with large datasets.
    """
    logger.info(f"Loading season {season}...")

    with conn.cursor() as cur:
        # First, count how many rows we'll be inserting
        cur.execute(
            """
            SELECT COUNT(*) 
            FROM raw_mlb.statcast 
            WHERE game_year = %s 
              AND plate_x IS NOT NULL 
              AND plate_z IS NOT NULL
        """,
            (season,),
        )

        total_rows = cur.fetchone()[0]

        if total_rows == 0:
            logger.warning(f"No pitch data found for season {season}")
            return 0

        logger.info(f"Found {total_rows:,} pitches to load for season {season}")

        # Check if we already have data for this season
        cur.execute(
            """
            SELECT COUNT(*) FROM features_pitch.locations WHERE game_year = %s
        """,
            (season,),
        )

        existing = cur.fetchone()[0]
        if existing > 0:
            logger.warning(f"Season {season} already has {existing:,} rows. Use --force to reload.")
            return 0

        # Load in batches using server-side cursor
        inserted = 0
        cur.execute(
            """
            DECLARE pitch_cursor CURSOR FOR
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
                s.release_speed::numeric as start_speed,
                s.spin_rate_deprecated::numeric as spin_rate,
                s.des as pitch_result,
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
                s.hit_distance_sc::numeric as hit_distance
            FROM raw_mlb.statcast s
            WHERE s.game_year = %s
              AND s.plate_x IS NOT NULL
              AND s.plate_z IS NOT NULL
        """,
            (season,),
        )

        while True:
            cur.execute("FETCH %s FROM pitch_cursor", (batch_size,))
            rows = cur.fetchall()

            if not rows:
                break

            # Insert batch
            execute_values(
                cur,
                """
                INSERT INTO features_pitch.locations (
                    game_year, game_pk, batter_id, pitcher_id, pitch_type,
                    plate_x, plate_z, sz_top, sz_bot, pfx_x, pfx_z,
                    start_speed, spin_rate, pitch_result, zone, balls, strikes,
                    inning, inning_topbot, hc_x, hc_y, hit_location, bb_type,
                    launch_speed, launch_angle, hit_distance
                ) VALUES %s
            """,
                rows,
            )

            conn.commit()
            inserted += len(rows)
            logger.info(f"  Loaded {inserted:,} / {total_rows:,} pitches...")

        cur.execute("CLOSE pitch_cursor")

        # Update geometry for the loaded season
        logger.info(f"Updating PostGIS geometry for season {season}...")
        cur.execute(
            """
            UPDATE features_pitch.locations 
            SET location = ST_SetSRID(ST_MakePoint(plate_x, plate_z), 4326)
            WHERE game_year = %s
              AND plate_x IS NOT NULL 
              AND plate_z IS NOT NULL
              AND location IS NULL
        """,
            (season,),
        )

        conn.commit()

        logger.info(f"✓ Season {season} complete: {inserted:,} pitches loaded")
        return inserted


def main():
    parser = argparse.ArgumentParser(
        description="Load Statcast pitch data into features_pitch.locations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --seasons 2024                    # Load single season
    %(prog)s --seasons 2015-2025               # Load range
    %(prog)s --seasons 2015,2016,2020-2025     # Load multiple ranges
    %(prog)s --all                             # Load all available seasons
    %(prog)s --dry-run                         # Show what would be loaded
        """,
    )

    parser.add_argument("--seasons", type=str, help="Seasons to load (e.g., 2015-2025, 2020,2024)")
    parser.add_argument("--all", action="store_true", help="Load all available seasons")
    parser.add_argument("--force", action="store_true", help="Force reload even if data exists")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be loaded without loading"
    )
    parser.add_argument(
        "--batch-size", type=int, default=50000, help="Batch size for inserts (default: 50000)"
    )

    args = parser.parse_args()

    if not args.seasons and not args.all and not args.dry_run:
        parser.print_help()
        sys.exit(1)

    conn = get_connection()

    try:
        # Get available seasons
        available_seasons = get_season_counts(conn)
        loaded_seasons = get_loaded_season_counts(conn)

        logger.info("=" * 60)
        logger.info("Statcast Pitch Data Loader")
        logger.info("=" * 60)

        # Display status
        logger.info("\nAvailable seasons in raw_mlb.statcast:")
        for year, count in available_seasons:
            loaded = next((c for y, c in loaded_seasons if y == year), 0)
            status = "✓" if loaded > 0 else "○"
            logger.info(f"  {status} {year}: {count:,} pitches available, {loaded:,} loaded")

        if args.dry_run:
            logger.info("\nDry run complete. No data was loaded.")
            return

        # Parse seasons argument
        seasons_to_load = []
        if args.all:
            seasons_to_load = [year for year, _ in available_seasons]
        elif args.seasons:
            for part in args.seasons.split(","):
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    seasons_to_load.extend(range(start, end + 1))
                else:
                    seasons_to_load.append(int(part))

        # Filter to available seasons
        available_years = {year for year, _ in available_seasons}
        seasons_to_load = [s for s in seasons_to_load if s in available_years]

        if not seasons_to_load:
            logger.error("No valid seasons to load")
            sys.exit(1)

        logger.info(f"\nLoading {len(seasons_to_load)} season(s): {seasons_to_load}")
        logger.info("-" * 60)

        # Load each season
        total_loaded = 0
        for season in seasons_to_load:
            count = load_season(conn, season, args.batch_size)
            total_loaded += count

        logger.info("-" * 60)
        logger.info(f"Total pitches loaded: {total_loaded:,}")

        # Final summary
        loaded_seasons = get_loaded_season_counts(conn)
        logger.info("\nFinal status:")
        for year, count in loaded_seasons:
            logger.info(f"  {year}: {count:,} pitches")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
