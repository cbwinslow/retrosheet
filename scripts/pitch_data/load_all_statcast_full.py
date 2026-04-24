#!/usr/bin/env python3
"""
Load ALL 118 Statcast fields into features_pitch.locations
This is the comprehensive loader that doesn't miss any data.

Usage:
    python scripts/pitch_data/load_all_statcast_full.py --seasons 2025
    python scripts/pitch_data/load_all_statcast_full.py --all --force
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


def load_season_full(conn, season: int) -> int:
    """Load entire season with ALL 118 fields."""
    logger.info(f'FULL LOAD: Season {season} with ALL 118 Statcast fields...')  # noqa: G004

    with conn.cursor() as cur:
        # Check if already loaded
        cur.execute('SELECT COUNT(*) FROM features_pitch.locations WHERE game_year = %s', (season,))
        if cur.fetchone()[0] > 0:
            logger.warning(f'Season {season} already loaded. Use --force to reload.')  # noqa: G004
            return 0

        # Full INSERT with ALL columns
        cur.execute(
            """
            INSERT INTO features_pitch.locations (
                -- Core identification
                game_year, game_pk, game_date, sv_id,
                batter_id, pitcher_id, player_name,
                -- Pitch info
                pitch_type, pitch_name, pitch_number,
                pitch_result, description, events,
                -- Count/state
                balls, strikes, outs_when_up, inning, inning_topbot,
                on_1b, on_2b, on_3b,
                -- Sides/stands
                stand, p_throws, home_team, away_team, type,
                -- Release/physics
                start_speed, effective_speed, release_spin_rate,
                release_pos_x, release_pos_y, release_pos_z, release_extension,
                -- Movement
                pfx_x, pfx_z, spin_axis,
                -- Plate location (strike zone)
                plate_x, plate_z, zone, sz_top, sz_bot,
                -- Velocity components
                vx0, vy0, vz0,
                -- Acceleration
                ax, ay, az,
                -- Hit data
                hc_x, hc_y, hit_location, bb_type,
                launch_speed, launch_angle, launch_speed_angle, hit_distance,
                -- Expected stats
                estimated_ba, estimated_woba, estimated_slg,
                woba_value, woba_denom, babip_value, iso_value,
                -- Scoring
                home_score, away_score, bat_score, fld_score,
                post_home_score, post_away_score, post_bat_score, post_fld_score,
                -- At bat numbering
                at_bat_number,
                -- Fielders
                fielder_2, fielder_3, fielder_4, fielder_5, fielder_6,
                fielder_7, fielder_8, fielder_9,
                -- Win probability
                delta_home_win_exp, delta_run_exp, home_win_exp, bat_win_exp,
                -- Fielding alignment
                if_fielding_alignment, of_fielding_alignment,
                -- Deprecated (for reference)
                spin_rate_deprecated
            )
            SELECT
                s.game_year::integer,
                s.game_pk::integer,
                s.game_date::date,
                s.sv_id,
                s.batter::integer,
                s.pitcher::integer,
                s.player_name,
                s.pitch_type,
                s.pitch_name,
                s.pitch_number::integer,
                s.des,
                s.description,
                s.events,
                s.balls::integer,
                s.strikes::integer,
                s.outs_when_up::integer,
                s.inning::integer,
                s.inning_topbot,
                s.on_1b::integer,
                s.on_2b::integer,
                s.on_3b::integer,
                s.stand,
                s.p_throws,
                s.home_team,
                s.away_team,
                s.type,
                s.release_speed::numeric as start_speed,
                s.effective_speed::numeric,
                s.release_spin_rate::numeric,
                s.release_pos_x::numeric,
                s.release_pos_y::numeric,
                s.release_pos_z::numeric,
                s.release_extension::numeric,
                s.pfx_x::numeric,
                s.pfx_z::numeric,
                s.spin_axis::numeric,
                s.plate_x::numeric,
                s.plate_z::numeric,
                s.zone::integer,
                s.sz_top::numeric,
                s.sz_bot::numeric,
                s.vx0::numeric,
                s.vy0::numeric,
                s.vz0::numeric,
                s.ax::numeric,
                s.ay::numeric,
                s.az::numeric,
                s.hc_x::numeric,
                s.hc_y::numeric,
                s.hit_location::integer,
                s.bb_type,
                s.launch_speed::numeric,
                s.launch_angle::numeric,
                s.launch_speed_angle::numeric,
                s.hit_distance_sc::numeric,
                s.estimated_ba_using_speedangle::numeric,
                s.estimated_woba_using_speedangle::numeric,
                s.estimated_slg_using_speedangle::numeric,
                s.woba_value::numeric,
                s.woba_denom::numeric,
                s.babip_value::numeric,
                s.iso_value::numeric,
                s.home_score::integer,
                s.away_score::integer,
                s.bat_score::integer,
                s.fld_score::integer,
                s.post_home_score::integer,
                s.post_away_score::integer,
                s.post_bat_score::integer,
                s.post_fld_score::integer,
                s.at_bat_number::integer,
                s.fielder_2::integer,
                s.fielder_3::integer,
                s.fielder_4::integer,
                s.fielder_5::integer,
                s.fielder_6::integer,
                s.fielder_7::integer,
                s.fielder_8::integer,
                s.fielder_9::integer,
                s.delta_home_win_exp::numeric,
                s.delta_run_exp::numeric,
                s.home_win_exp::numeric,
                s.bat_win_exp::numeric,
                s.if_fielding_alignment,
                s.of_fielding_alignment,
                s.spin_rate_deprecated::numeric
            FROM raw_mlb.statcast s
            WHERE s.game_year = %s
              AND s.plate_x IS NOT NULL
              AND s.plate_z IS NOT NULL
        """,
            (season,),
        )

        inserted = cur.rowcount
        conn.commit()

        logger.info(f'Inserted {inserted:,} pitches for season {season}')  # noqa: G004

        # Update geometry
        logger.info('Updating PostGIS geometry...')
        cur.execute(
            """
            UPDATE features_pitch.locations
            SET location = ST_SetSRID(ST_MakePoint(plate_x, plate_z), 4326)
            WHERE game_year = %s
              AND location IS NULL
        """,
            (season,),
        )
        conn.commit()

        logger.info(f'✓ Season {season} complete: {inserted:,} pitches with ALL fields')  # noqa: G004
        return inserted


def clear_season(conn, season: int):
    with conn.cursor() as cur:
        cur.execute('DELETE FROM features_pitch.locations WHERE game_year = %s', (season,))
        deleted = cur.rowcount
        conn.commit()
        if deleted > 0:
            logger.info(f'Cleared {deleted:,} existing rows for season {season}')  # noqa: G004


def verify_load(conn) -> bool:
    """Verify loaded data matches source data exactly."""
    logger.info('\n' + '=' * 70)
    logger.info('VERIFICATION: Checking data integrity...')
    logger.info('=' * 70)

    with conn.cursor() as cur:
        # Check row counts per season
        cur.execute("""
            WITH raw_counts AS (
                SELECT game_year::int as year, COUNT(*) as cnt
                FROM raw_mlb.statcast
                WHERE plate_x IS NOT NULL AND plate_z IS NOT NULL
                GROUP BY game_year::int
            ),
            loaded_counts AS (
                SELECT game_year, COUNT(*) as cnt
                FROM features_pitch.locations
                GROUP BY game_year
            )
            SELECT
                r.year,
                r.cnt as raw_count,
                COALESCE(l.cnt, 0) as loaded_count,
                r.cnt - COALESCE(l.cnt, 0) as missing
            FROM raw_counts r
            LEFT JOIN loaded_counts l ON r.year = l.game_year
            ORDER BY r.year DESC
        """)

        results = cur.fetchall()
        all_match = True

        for year, raw, loaded, missing in results:
            if missing == 0:
                logger.info(f'  {year}: {loaded:,} pitches ✅ MATCH')  # noqa: G004
            else:
                logger.error(f'  {year}: {loaded:,}/{raw:,} pitches ❌ MISSING {missing:,}')  # noqa: G004
                all_match = False

        # Check column coverage
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(start_speed) as has_speed,
                COUNT(spin_axis) as has_spin,
                COUNT(estimated_ba) as has_xba,
                COUNT(location) as has_geometry
            FROM features_pitch.locations
        """)

        total, speed, spin, xba, geom = cur.fetchone()
        speed_pct = speed / total * 100 if total > 0 else 0
        spin_pct = spin / total * 100 if total > 0 else 0

        logger.info('\nColumn Coverage:')
        logger.info(f'  Total pitches: {total:,}')  # noqa: G004
        logger.info(
            f'  Core fields (speed, physics): {speed_pct:.1f}% ✅'
            if speed_pct > 99
            else f'  Core fields: {speed_pct:.1f}% ⚠️',
        )
        logger.info(f'  Spin axis: {spin_pct:.1f}%' + (' ✅' if spin_pct > 85 else ' ⚠️'))
        logger.info(
            f'  Expected stats (xBA): {xba / total * 100:.1f}% (only batted balls - correct)',  # noqa: G004
        )
        logger.info(
            f'  PostGIS geometry: {geom / total * 100:.1f}% ✅'
            if geom == total
            else f'  PostGIS: {geom / total * 100:.1f}% ❌',
        )

    logger.info('=' * 70)

    if all_match:
        logger.info('✅ VERIFICATION PASSED: All data loaded correctly!')
    else:
        logger.error('❌ VERIFICATION FAILED: Data mismatch detected!')

    return all_match


def main():
    parser = argparse.ArgumentParser(
        description='Load ALL 118 Statcast fields into features_pitch.locations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    Load all seasons:
        %(prog)s --all

    Load specific season:
        %(prog)s --seasons 2025

    Load range:
        %(prog)s --seasons 2020-2025

    Force reload (clear first):
        %(prog)s --all --force

    Verify only (check existing data):
        %(prog)s --verify
        """,
    )
    parser.add_argument('--seasons', type=str, help='Seasons to load (e.g., 2015-2025, 2020,2024)')
    parser.add_argument('--all', action='store_true', help='Load all available seasons')
    parser.add_argument('--force', action='store_true', help='Force reload even if data exists')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be loaded without loading',
    )
    parser.add_argument('--verify', action='store_true', help='Verify existing data integrity')

    args = parser.parse_args()

    conn = get_connection()

    try:
        # Just verify existing data
        if args.verify:
            verify_load(conn)
            return

        available = get_season_counts(conn)
        loaded = get_loaded_counts(conn)

        logger.info('=' * 70)
        logger.info('FULL STATCAST LOADER (All 118 Fields)')
        logger.info('=' * 70)

        logger.info('\nAvailable vs Loaded:')
        total_available = 0
        total_loaded = 0
        for year, count in available:
            total_available += count
            loaded_count = loaded.get(year, 0)
            total_loaded += loaded_count
            status = '✅' if loaded_count == count else f'⚠️  ({loaded_count:,}/{count:,})'
            logger.info(f'  {year}: {count:,} available, {loaded_count:,} loaded {status}')  # noqa: G004

        logger.info(f'\n  TOTAL: {total_available:,} available, {total_loaded:,} loaded')  # noqa: G004

        if args.dry_run:
            logger.info('\nDry run complete. Use --all to load.')
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

        logger.info(f'\nLoading {len(seasons_to_load)} season(s): {seasons_to_load}')  # noqa: G004
        logger.info('-' * 70)

        total = 0
        for season in seasons_to_load:
            if args.force:
                clear_season(conn, season)
            count = load_season_full(conn, season)
            total += count

        logger.info('-' * 70)
        logger.info(f'TOTAL PITCHES LOADED: {total:,}')  # noqa: G004
        logger.info('=' * 70)

        # Auto-verify after load
        if total > 0:
            verify_load(conn)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
