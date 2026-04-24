#!/usr/bin/env python3
"""
Load Baseball Savant total_stats.csv into the database.

This script loads comprehensive Statcast batter metrics from Baseball Savant.
"""

import argparse
import sys

try:
    import pandas as pd
    from psycopg2 import sql
    from psycopg2.extras import execute_values
except ImportError:
    print("Error: Required libraries not installed.")
    print("Install with: pip install pandas psycopg2-binary")
    sys.exit(1)


def get_conn():
    """Get database connection from environment variables."""
    import os
    from urllib.parse import urlparse

    import psycopg2

    # Try DATABASE_URL first, then fall back to PG* variables
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        parsed = urlparse(db_url)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/"),
            user=parsed.username,
            password=parsed.password,
        )

    # Fall back to PG* variables
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", 5432),
        database=os.getenv("PGDATABASE", "retrosheet"),
        user=os.getenv("PGUSER", os.getenv("USER")),
        password=os.getenv("PGPASSWORD", ""),
    )


def load_total_stats(csv_path: str) -> bool:
    """Load total_stats.csv into the database."""
    print(f"Loading total_stats from {csv_path}")

    try:
        df = pd.read_csv(csv_path)
        print(f"  Read {len(df)} rows")

        # Create schema if not exists
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("CREATE SCHEMA IF NOT EXISTS baseball_savant")

        # Drop table if exists
        cur.execute("DROP TABLE IF EXISTS baseball_savant.total_stats")

        # Create table with TEXT columns to handle any data format
        cur.execute("""
            CREATE TABLE baseball_savant.total_stats (
                last_name_first TEXT,
                player_id TEXT,
                year TEXT,
                player_age TEXT,
                ab TEXT,
                pa TEXT,
                hit TEXT,
                single TEXT,
                double TEXT,
                triple TEXT,
                home_run TEXT,
                strikeout TEXT,
                walk TEXT,
                k_percent TEXT,
                bb_percent TEXT,
                batting_avg TEXT,
                slg_percent TEXT,
                on_base_percent TEXT,
                on_base_plus_slg TEXT,
                isolated_power TEXT,
                babip TEXT,
                b_rbi TEXT,
                b_lob TEXT,
                b_total_bases TEXT,
                r_total_caught_stealing TEXT,
                r_total_stolen_base TEXT,
                b_ab_scoring TEXT,
                b_ball TEXT,
                b_called_strike TEXT,
                b_catcher_interf TEXT,
                b_foul TEXT,
                b_foul_tip TEXT,
                b_game TEXT,
                b_gnd_into_dp TEXT,
                b_gnd_into_tp TEXT,
                b_gnd_rule_double TEXT,
                b_hit_by_pitch TEXT,
                b_hit_ground TEXT,
                b_hit_fly TEXT,
                b_hit_into_play TEXT,
                b_hit_line_drive TEXT,
                b_hit_popup TEXT,
                b_out_fly TEXT,
                b_out_ground TEXT,
                b_out_line_drive TEXT,
                b_out_popup TEXT,
                b_intent_ball TEXT,
                b_intent_walk TEXT,
                b_interference TEXT,
                b_pinch_hit TEXT,
                b_pinch_run TEXT,
                b_pitchout TEXT,
                b_played_dh TEXT,
                b_sac_bunt TEXT,
                b_sac_fly TEXT,
                b_swinging_strike TEXT,
                r_caught_stealing_2b TEXT,
                r_caught_stealing_3b TEXT,
                r_caught_stealing_home TEXT,
                r_defensive_indiff TEXT,
                r_interference TEXT,
                r_pickoff_1b TEXT,
                r_pickoff_2b TEXT,
                r_pickoff_3b TEXT,
                r_run TEXT,
                r_stolen_base_2b TEXT,
                r_stolen_base_3b TEXT,
                r_stolen_base_home TEXT,
                b_total_ball TEXT,
                b_total_sacrifices TEXT,
                b_total_strike TEXT,
                b_total_swinging_strike TEXT,
                b_total_pitches TEXT,
                r_stolen_base_pct TEXT,
                r_total_pickoff TEXT,
                b_reached_on_error TEXT,
                b_walkoff TEXT,
                b_reached_on_int TEXT,
                xba TEXT,
                xslg TEXT,
                woba TEXT,
                xwoba TEXT,
                xobp TEXT,
                xiso TEXT,
                wobacon TEXT,
                xwobacon TEXT,
                bacon TEXT,
                xbacon TEXT,
                xbadiff TEXT,
                xslgdiff TEXT,
                wobadiff TEXT,
                avg_swing_speed TEXT,
                fast_swing_rate TEXT,
                blasts_contact TEXT,
                blasts_swing TEXT,
                squared_up_contact TEXT,
                squared_up_swing TEXT,
                avg_swing_length TEXT,
                swords TEXT,
                attack_angle TEXT,
                attack_direction TEXT,
                ideal_angle_rate TEXT,
                vertical_swing_path TEXT,
                exit_velocity_avg TEXT,
                launch_angle_avg TEXT,
                sweet_spot_percent TEXT,
                barrel TEXT,
                barrel_batted_rate TEXT,
                solidcontact_percent TEXT,
                flareburner_percent TEXT,
                poorlyunder_percent TEXT,
                poorlytopped_percent TEXT,
                poorlyweak_percent TEXT,
                hard_hit_percent TEXT,
                avg_best_speed TEXT,
                avg_hyper_speed TEXT,
                z_swing_percent TEXT,
                z_swing_miss_percent TEXT,
                oz_swing_percent TEXT,
                oz_swing_miss_percent TEXT,
                oz_contact_percent TEXT,
                out_zone_swing_miss TEXT,
                out_zone_swing TEXT,
                out_zone_percent TEXT,
                out_zone TEXT,
                meatball_swing_percent TEXT,
                meatball_percent TEXT,
                pitch_count_offspeed TEXT,
                pitch_count_fastball TEXT,
                pitch_count_breaking TEXT,
                pitch_count TEXT,
                iz_contact_percent TEXT,
                in_zone_swing_miss TEXT,
                in_zone_swing TEXT,
                in_zone_percent TEXT,
                in_zone TEXT,
                edge_percent TEXT,
                edge TEXT,
                whiff_percent TEXT,
                swing_percent TEXT,
                pull_percent TEXT,
                straightaway_percent TEXT,
                opposite_percent TEXT,
                batted_ball TEXT,
                f_strike_percent TEXT,
                groundballs_percent TEXT,
                groundballs TEXT,
                flyballs_percent TEXT,
                flyballs TEXT,
                linedrives_percent TEXT,
                linedrives TEXT,
                popups_percent TEXT,
                popups TEXT,
                pop_2b_sba_count TEXT,
                pop_2b_sba TEXT,
                pop_2b_sb TEXT,
                pop_2b_cs TEXT,
                pop_3b_sba_count TEXT,
                pop_3b_sba TEXT,
                pop_3b_sb TEXT,
                pop_3b_cs TEXT,
                exchange_2b_3b_sba TEXT,
                maxeff_arm_2b_3b_sba TEXT,
                n_outs_above_average TEXT,
                n_fieldout_5stars TEXT,
                n_opp_5stars TEXT,
                n_5star_percent TEXT,
                n_fieldout_4stars TEXT,
                n_opp_4stars TEXT,
                n_4star_percent TEXT,
                n_fieldout_3stars TEXT,
                n_opp_3stars TEXT,
                n_3star_percent TEXT,
                n_fieldout_2stars TEXT,
                n_opp_2stars TEXT,
                n_2star_percent TEXT,
                n_fieldout_1stars TEXT,
                n_opp_1stars TEXT,
                n_1star_percent TEXT,
                rel_league_reaction_distance TEXT,
                rel_league_burst_distance TEXT,
                rel_league_routing_distance TEXT,
                rel_league_bootup_distance TEXT,
                f_bootup_distance TEXT,
                n_bolts TEXT,
                hp_to_1b TEXT
            )
        """)

        # Prepare data for insertion
        # Convert all values to strings to handle any data format
        data = []
        for _, row in df.iterrows():
            row_data = [str(val) if pd.notna(val) else None for val in row]
            data.append(tuple(row_data))

        # Get column names from dataframe
        columns = df.columns.tolist()

        # Insert data
        execute_values(
            cur,
            sql.SQL("INSERT INTO baseball_savant.total_stats ({}) VALUES %s").format(
                sql.SQL(", ").join([sql.Identifier(col) for col in columns])
            ),
            data,
        )

        conn.commit()
        print(f"  ✅ Loaded {len(df)} rows")
        return True

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    finally:
        if "conn" in locals():
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="Load Baseball Savant total_stats.csv")
    parser.add_argument("--csv", default="total_stats.csv", help="Path to total_stats.csv")
    args = parser.parse_args()

    success = load_total_stats(args.csv)

    if success:
        print("\n✅ Baseball Savant data loaded successfully")
        sys.exit(0)
    else:
        print("\n❌ Failed to load Baseball Savant data")
        sys.exit(1)


if __name__ == "__main__":
    main()
