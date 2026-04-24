#!/usr/bin/env python3
"""
Populate features_pitch.base_features from features_pitch.locations

This script migrates all 7.66M pitches with full Statcast data
from the locations table to the base_features table for model training.

Column mappings account for schema differences:
- locations.id -> not mapped (base_features has auto-generated pitch_id)
- locations.pitch_result -> not in base_features (use description instead)
- locations.hit_distance -> not in base_features (use hit_distance_sc from base_features default)
- locations.spin_rate -> maps to release_spin_rate
- locations.on_1b/2b/3b (int) -> cast to boolean
- Extra columns in base_features use defaults (created_at, data_version, etc.)

Usage:
    python populate_base_features.py --all
    python populate_base_features.py --seasons 2020 2021 2022
    python populate_base_features.py --dry-run
    python populate_base_features.py --verify

Author: AI Agent
Date: 2026-04-24
"""

import argparse
import sys
from datetime import datetime

import psycopg2


def get_connection():
    """Get database connection."""
    return psycopg2.connect(host='localhost', database='retrosheet', port=5432)


def get_row_count(conn, table: str, schema: str = 'features_pitch') -> int:
    """Get row count for a table."""
    with conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM {schema}.{table}')
        return cur.fetchone()[0]


def populate_all_seasons(conn, dry_run: bool = False) -> int:
    """Populate base_features for all seasons."""
    # Columns common to both tables with proper type casting
    query = """
        INSERT INTO features_pitch.base_features (
            game_year, game_pk, game_date, sv_id,
            batter_id, pitcher_id, player_name,
            pitch_type, pitch_name, pitch_number,
            description, events,
            balls, strikes, outs_when_up, inning, inning_topbot,
            on_1b, on_2b, on_3b,
            stand, p_throws, home_team, away_team, type,
            start_speed, effective_speed, release_spin_rate,
            release_pos_x, release_pos_y, release_pos_z, release_extension,
            pfx_x, pfx_z, spin_axis,
            plate_x, plate_z, zone, sz_top, sz_bot,
            vx0, vy0, vz0,
            ax, ay, az,
            hc_x, hc_y, hit_location, bb_type,
            launch_speed, launch_angle, launch_speed_angle,
            estimated_ba, estimated_woba, estimated_slg,
            woba_value, woba_denom, babip_value, iso_value,
            home_score, away_score, bat_score, fld_score,
            post_home_score, post_away_score, post_bat_score, post_fld_score,
            at_bat_number,
            fielder_2, fielder_3, fielder_4, fielder_5, fielder_6,
            fielder_7, fielder_8, fielder_9,
            delta_home_win_exp, delta_run_exp, home_win_exp, bat_win_exp,
            if_fielding_alignment, of_fielding_alignment,
            spin_rate_deprecated,
            location, quality_flag,
            source_table, source_row_id, created_at
        )
        SELECT
            game_year::smallint, game_pk, game_date, sv_id,
            batter_id, pitcher_id, player_name,
            pitch_type, pitch_name, pitch_number::smallint,
            description, events,
            balls::smallint, strikes::smallint, outs_when_up::smallint,
            inning::smallint, inning_topbot,
            on_1b::boolean, on_2b::boolean, on_3b::boolean,
            stand, p_throws, home_team, away_team, type,
            start_speed::real, effective_speed::real, release_spin_rate::real,
            release_pos_x::real, release_pos_y::real, release_pos_z::real,
            release_extension::real,
            pfx_x::real, pfx_z::real, spin_axis::real,
            plate_x::real, plate_z::real, zone::smallint, sz_top::real, sz_bot::real,
            vx0::real, vy0::real, vz0::real,
            ax::real, ay::real, az::real,
            hc_x::real, hc_y::real, hit_location::smallint, bb_type,
            launch_speed::real, launch_angle::real, launch_speed_angle::real,
            estimated_ba::real, estimated_woba::real, estimated_slg::real,
            woba_value::real, woba_denom::real, babip_value::real, iso_value::real,
            home_score::smallint, away_score::smallint,
            bat_score::smallint, fld_score::smallint,
            post_home_score::smallint, post_away_score::smallint,
            post_bat_score::smallint, post_fld_score::smallint,
            at_bat_number,
            fielder_2, fielder_3, fielder_4, fielder_5, fielder_6,
            fielder_7, fielder_8, fielder_9,
            delta_home_win_exp::real, delta_run_exp::real,
            home_win_exp::real, bat_win_exp::real,
            if_fielding_alignment, of_fielding_alignment,
            spin_rate_deprecated::real,
            location, quality_flag,
            'locations'::varchar, id, NOW()
        FROM features_pitch.locations l
        WHERE NOT EXISTS (
            SELECT 1 FROM features_pitch.base_features bf
            WHERE bf.game_pk = l.game_pk
            AND bf.sv_id = l.sv_id
        )
    """

    if dry_run:
        count_query = """
            SELECT COUNT(*)
            FROM features_pitch.locations l
            WHERE NOT EXISTS (
                SELECT 1 FROM features_pitch.base_features bf
                WHERE bf.game_pk = l.game_pk AND bf.sv_id = l.sv_id
            )
        """
        with conn.cursor() as cur:
            cur.execute(count_query)
            count = cur.fetchone()[0]
            print(f'[DRY RUN] Would insert {count:,} rows into base_features')
            return count

    print('Populating base_features from locations...')
    start_time = datetime.now()

    with conn.cursor() as cur:
        cur.execute(query)
        rows_inserted = cur.rowcount

    conn.commit()
    elapsed = (datetime.now() - start_time).total_seconds()

    print(f'✓ Inserted {rows_inserted:,} rows in {elapsed:.1f}s')
    print(f'  Rate: {rows_inserted / elapsed:,.0f} rows/sec')

    return rows_inserted


def populate_seasons(conn, seasons: list[int], dry_run: bool = False) -> int:
    """Populate base_features for specific seasons."""
    total_inserted = 0

    for season in seasons:
        query = """
            INSERT INTO features_pitch.base_features (
                game_year, game_pk, game_date, sv_id,
                batter_id, pitcher_id, player_name,
                pitch_type, pitch_name, pitch_number,
                description, events,
                balls, strikes, outs_when_up, inning, inning_topbot,
                on_1b, on_2b, on_3b,
                stand, p_throws, home_team, away_team, type,
                start_speed, effective_speed, release_spin_rate,
                release_pos_x, release_pos_y, release_pos_z, release_extension,
                pfx_x, pfx_z, spin_axis,
                plate_x, plate_z, zone, sz_top, sz_bot,
                vx0, vy0, vz0,
                ax, ay, az,
                hc_x, hc_y, hit_location, bb_type,
                launch_speed, launch_angle, launch_speed_angle,
                estimated_ba, estimated_woba, estimated_slg,
                woba_value, woba_denom, babip_value, iso_value,
                home_score, away_score, bat_score, fld_score,
                post_home_score, post_away_score, post_bat_score, post_fld_score,
                at_bat_number,
                fielder_2, fielder_3, fielder_4, fielder_5, fielder_6,
                fielder_7, fielder_8, fielder_9,
                delta_home_win_exp, delta_run_exp, home_win_exp, bat_win_exp,
                if_fielding_alignment, of_fielding_alignment,
                spin_rate_deprecated,
                location, quality_flag,
                source_table, source_row_id, created_at
            )
            SELECT
                game_year::smallint, game_pk, game_date, sv_id,
                batter_id, pitcher_id, player_name,
                pitch_type, pitch_name, pitch_number::smallint,
                description, events,
                balls::smallint, strikes::smallint, outs_when_up::smallint,
                inning::smallint, inning_topbot,
                on_1b::boolean, on_2b::boolean, on_3b::boolean,
                stand, p_throws, home_team, away_team, type,
                start_speed::real, effective_speed::real, release_spin_rate::real,
                release_pos_x::real, release_pos_y::real, release_pos_z::real,
                release_extension::real,
                pfx_x::real, pfx_z::real, spin_axis::real,
                plate_x::real, plate_z::real, zone::smallint, sz_top::real, sz_bot::real,
                vx0::real, vy0::real, vz0::real,
                ax::real, ay::real, az::real,
                hc_x::real, hc_y::real, hit_location::smallint, bb_type,
                launch_speed::real, launch_angle::real, launch_speed_angle::real,
                estimated_ba::real, estimated_woba::real, estimated_slg::real,
                woba_value::real, woba_denom::real, babip_value::real, iso_value::real,
                home_score::smallint, away_score::smallint,
                bat_score::smallint, fld_score::smallint,
                post_home_score::smallint, post_away_score::smallint,
                post_bat_score::smallint, post_fld_score::smallint,
                at_bat_number,
                fielder_2, fielder_3, fielder_4, fielder_5, fielder_6,
                fielder_7, fielder_8, fielder_9,
                delta_home_win_exp::real, delta_run_exp::real,
                home_win_exp::real, bat_win_exp::real,
                if_fielding_alignment, of_fielding_alignment,
                spin_rate_deprecated::real,
                location, quality_flag,
                'locations'::varchar, id, NOW()
            FROM features_pitch.locations l
            WHERE game_year = %s
            AND NOT EXISTS (
                SELECT 1 FROM features_pitch.base_features bf
                WHERE bf.game_pk = l.game_pk AND bf.sv_id = l.sv_id
            )
        """

        if dry_run:
            count_query = """
                SELECT COUNT(*)
                FROM features_pitch.locations l
                WHERE l.game_year = %s
                AND NOT EXISTS (
                    SELECT 1 FROM features_pitch.base_features bf
                    WHERE bf.game_pk = l.game_pk AND bf.sv_id = l.sv_id
                )
            """
            with conn.cursor() as cur:
                cur.execute(count_query, (season,))
                count = cur.fetchone()[0]
                print(f'[DRY RUN] Season {season}: would insert {count:,} rows')
                total_inserted += count
            continue

        print(f'Processing season {season}...')
        start_time = datetime.now()

        with conn.cursor() as cur:
            cur.execute(query, (season,))
            rows_inserted = cur.rowcount

        conn.commit()
        elapsed = (datetime.now() - start_time).total_seconds()

        print(f'  ✓ Inserted {rows_inserted:,} rows in {elapsed:.1f}s')
        total_inserted += rows_inserted

    return total_inserted


def verify_population(conn) -> bool:
    """Verify that base_features matches locations."""
    print('\n=== Verification ===')

    # Check row counts
    locations_count = get_row_count(conn, 'locations')
    base_count = get_row_count(conn, 'base_features')

    print(f'locations:     {locations_count:,} rows')
    print(f'base_features: {base_count:,} rows')

    if locations_count == base_count:
        print('✓ Row counts match')
    else:
        print(f'✗ Mismatch: {locations_count - base_count:,} rows missing')
        return False

    # Check season distribution
    with conn.cursor() as cur:
        cur.execute("""
            SELECT game_year, COUNT(*) as cnt
            FROM features_pitch.base_features
            GROUP BY game_year
            ORDER BY game_year
        """)
        seasons = cur.fetchall()

        print('\nSeason distribution in base_features:')
        for year, count in seasons:
            print(f'  {year}: {count:,} rows')

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Populate features_pitch.base_features from locations',
    )
    parser.add_argument('--all', action='store_true', help='Populate all seasons at once')
    parser.add_argument(
        '--seasons', nargs='+', type=int, help='Specific seasons to populate (e.g., 2020 2021 2022)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be inserted without actually inserting',
    )
    parser.add_argument(
        '--verify', action='store_true', help='Verify population by comparing row counts',
    )

    args = parser.parse_args()

    if not any([args.all, args.seasons, args.verify]):
        parser.print_help()
        sys.exit(1)

    conn = get_connection()

    try:
        if args.verify:
            success = verify_population(conn)
            sys.exit(0 if success else 1)

        if args.all:
            rows = populate_all_seasons(conn, dry_run=args.dry_run)
            print(f"\n{'Would insert' if args.dry_run else 'Inserted'} {rows:,} total rows")

            if not args.dry_run:
                verify_population(conn)

        elif args.seasons:
            rows = populate_seasons(conn, args.seasons, dry_run=args.dry_run)
            print(f"\n{'Would insert' if args.dry_run else 'Inserted'} {rows:,} total rows")

            if not args.dry_run:
                verify_population(conn)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
