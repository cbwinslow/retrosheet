#!/usr/bin/env python3
"""
Load a Statcast CSV file (full season) into raw_statcast.events.

Because a full-season Statcast file can be > 1 GB, the script supports
optional chunked loading. If the file size exceeds 500 MB, it is split
into 5 M-row chunks before being copied.

The loader uses a staging table (all TEXT) and then upserts into the
final `raw_statcast.events` table with proper numeric casts.

Usage:
    python scripts/external_data/load_statcast.py --file /path/to/statcast.csv
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import psycopg2


DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/retrosheet')
CHUNK_ROWS = 5_000_000  # rows per chunk for very large files


def get_conn():
    return psycopg2.connect(DB_URL)


def create_staging(cur):
    cur.execute('DROP TABLE IF EXISTS raw_mlb.stg_statcast')
    cur.execute("""
        CREATE TABLE raw_mlb.stg_statcast (
            pitch_type TEXT,
            game_date TEXT,
            release_speed TEXT,
            release_pos_x TEXT,
            release_pos_z TEXT,
            player_name TEXT,
            batter TEXT,
            pitcher TEXT,
            events TEXT,
            description TEXT,
            spin_dir TEXT,
            spin_rate_deprecated TEXT,
            break_angle_deprecated TEXT,
            break_length_deprecated TEXT,
            zone TEXT,
            des TEXT,
            game_type TEXT,
            stand TEXT,
            p_throws TEXT,
            home_team TEXT,
            away_team TEXT,
            type TEXT,
            hit_location TEXT,
            bb_type TEXT,
            balls TEXT,
            strikes TEXT,
            game_year TEXT,
            pfx_x TEXT,
            pfx_z TEXT,
            plate_x TEXT,
            plate_z TEXT,
            on_3b TEXT,
            on_2b TEXT,
            on_1b TEXT,
            outs_when_up TEXT,
            inning TEXT,
            inning_topbot TEXT,
            hc_x TEXT,
            hc_y TEXT,
            tfs_deprecated TEXT,
            tfs_zulu_deprecated TEXT,
            umpire TEXT,
            sv_id TEXT,
            vx0 TEXT,
            vy0 TEXT,
            vz0 TEXT,
            ax TEXT,
            ay TEXT,
            az TEXT,
            sz_top TEXT,
            sz_bot TEXT,
            hit_distance_sc TEXT,
            launch_speed TEXT,
            launch_angle TEXT,
            effective_speed TEXT,
            release_spin_rate TEXT,
            release_extension TEXT,
            game_pk TEXT,
            fielder_2 TEXT,
            fielder_3 TEXT,
            fielder_4 TEXT,
            fielder_5 TEXT,
            fielder_6 TEXT,
            fielder_7 TEXT,
            fielder_8 TEXT,
            fielder_9 TEXT,
            release_pos_y TEXT,
            estimated_ba_using_speedangle TEXT,
            estimated_woba_using_speedangle TEXT,
            woba_value TEXT,
            woba_denom TEXT,
            babip_value TEXT,
            iso_value TEXT,
            launch_speed_angle TEXT,
            at_bat_number TEXT,
            pitch_number TEXT,
            pitch_name TEXT,
            home_score TEXT,
            away_score TEXT,
            bat_score TEXT,
            fld_score TEXT,
            post_away_score TEXT,
            post_home_score TEXT,
            post_bat_score TEXT,
            post_fld_score TEXT,
            if_fielding_alignment TEXT,
            of_fielding_alignment TEXT,
            spin_axis TEXT,
            delta_home_win_exp TEXT,
            delta_run_exp TEXT,
            bat_speed TEXT,
            swing_length TEXT,
            estimated_slg_using_speedangle TEXT,
            delta_pitcher_run_exp TEXT,
            hyper_speed TEXT,
            home_score_diff TEXT,
            bat_score_diff TEXT,
            home_win_exp TEXT,
            bat_win_exp TEXT,
            age_pit_legacy TEXT,
            age_bat_legacy TEXT,
            age_pit TEXT,
            age_bat TEXT,
            n_thruorder_pitcher TEXT,
            n_priorpa_thisgame_player_at_bat TEXT,
            pitcher_days_since_prev_game TEXT,
            batter_days_since_prev_game TEXT,
            pitcher_days_until_next_game TEXT,
            batter_days_until_next_game TEXT,
            api_break_z_with_gravity TEXT,
            api_break_x_arm TEXT,
            api_break_x_batter_in TEXT,
            arm_angle TEXT,
            attack_angle TEXT,
            attack_direction TEXT,
            swing_path_tilt TEXT,
            intercept_ball_minus_batter_pos_x_inches TEXT,
            intercept_ball_minus_batter_pos_y_inches TEXT
        )
    """)


def copy_to_staging(cur, csv_path):
    with open(csv_path, newline='') as f:
        cur.copy_expert('COPY raw_mlb.stg_statcast FROM STDIN WITH CSV HEADER', f)


def upsert(cur):
    # Deduplicate staging table first to handle duplicate rows within the same CSV
    cur.execute("""
        DELETE FROM raw_mlb.stg_statcast s1
        USING raw_mlb.stg_statcast s2
        WHERE s1.ctid < s2.ctid
        AND s1.game_pk = s2.game_pk
        AND s1.at_bat_number = s2.at_bat_number
        AND s1.pitch_number = s2.pitch_number;
    """)

    cur.execute("""
        INSERT INTO raw_mlb.statcast (
            pitch_type, game_date, release_speed, release_pos_x, release_pos_z, player_name,
            batter, pitcher, events, description, spin_dir, spin_rate_deprecated,
            break_angle_deprecated, break_length_deprecated, zone, des, game_type, stand,
            p_throws, home_team, away_team, type, hit_location, bb_type, balls, strikes,
            game_year, pfx_x, pfx_z, plate_x, plate_z, on_3b, on_2b, on_1b, outs_when_up,
            inning, inning_topbot, hc_x, hc_y, tfs_deprecated, tfs_zulu_deprecated, umpire,
            sv_id, vx0, vy0, vz0, ax, ay, az, sz_top, sz_bot, hit_distance_sc, launch_speed,
            launch_angle, effective_speed, release_spin_rate, release_extension, game_pk,
            fielder_2, fielder_3, fielder_4, fielder_5, fielder_6, fielder_7, fielder_8,
            fielder_9, release_pos_y, estimated_ba_using_speedangle, estimated_woba_using_speedangle,
            woba_value, woba_denom, babip_value, iso_value, launch_speed_angle, at_bat_number,
            pitch_number, pitch_name, home_score, away_score, bat_score, fld_score,
            post_away_score, post_home_score, post_bat_score, post_fld_score, if_fielding_alignment,
            of_fielding_alignment, spin_axis, delta_home_win_exp, delta_run_exp, bat_speed,
            swing_length, estimated_slg_using_speedangle, delta_pitcher_run_exp, hyper_speed,
            home_score_diff, bat_score_diff, home_win_exp, bat_win_exp, age_pit_legacy,
            age_bat_legacy, age_pit, age_bat, n_thruorder_pitcher, n_priorpa_thisgame_player_at_bat,
            pitcher_days_since_prev_game, batter_days_since_prev_game, pitcher_days_until_next_game,
            batter_days_until_next_game, api_break_z_with_gravity, api_break_x_arm,
            api_break_x_batter_in, arm_angle, attack_angle, attack_direction, swing_path_tilt,
            intercept_ball_minus_batter_pos_x_inches, intercept_ball_minus_batter_pos_y_inches
        )
        SELECT
            pitch_type, game_date,
            NULLIF(release_speed, '')::REAL,
            NULLIF(release_pos_x, '')::REAL,
            NULLIF(release_pos_z, '')::REAL,
            player_name,
            NULLIF(batter, '')::INT,
            NULLIF(pitcher, '')::INT,
            events, description,
            NULLIF(spin_dir, '')::REAL,
            NULLIF(spin_rate_deprecated, '')::REAL,
            NULLIF(break_angle_deprecated, '')::REAL,
            NULLIF(break_length_deprecated, '')::REAL,
            zone, des, game_type, stand, p_throws, home_team, away_team, type, hit_location, bb_type,
            NULLIF(balls, '')::INT,
            NULLIF(strikes, '')::INT,
            NULLIF(game_year, '')::INT,
            NULLIF(pfx_x, '')::REAL,
            NULLIF(pfx_z, '')::REAL,
            NULLIF(plate_x, '')::REAL,
            NULLIF(plate_z, '')::REAL,
            NULLIF(on_3b, '')::INT,
            NULLIF(on_2b, '')::INT,
            NULLIF(on_1b, '')::INT,
            NULLIF(outs_when_up, '')::INT,
            NULLIF(inning, '')::INT,
            inning_topbot,
            NULLIF(hc_x, '')::REAL,
            NULLIF(hc_y, '')::REAL,
            tfs_deprecated, tfs_zulu_deprecated, umpire, sv_id,
            NULLIF(vx0, '')::REAL,
            NULLIF(vy0, '')::REAL,
            NULLIF(vz0, '')::REAL,
            NULLIF(ax, '')::REAL,
            NULLIF(ay, '')::REAL,
            NULLIF(az, '')::REAL,
            NULLIF(sz_top, '')::REAL,
            NULLIF(sz_bot, '')::REAL,
            NULLIF(hit_distance_sc, '')::REAL,
            NULLIF(launch_speed, '')::REAL,
            NULLIF(launch_angle, '')::REAL,
            NULLIF(effective_speed, '')::REAL,
            NULLIF(release_spin_rate, '')::REAL,
            NULLIF(release_extension, '')::REAL,
            NULLIF(game_pk, '')::BIGINT,
            NULLIF(fielder_2, '')::INT,
            NULLIF(fielder_3, '')::INT,
            NULLIF(fielder_4, '')::INT,
            NULLIF(fielder_5, '')::INT,
            NULLIF(fielder_6, '')::INT,
            NULLIF(fielder_7, '')::INT,
            NULLIF(fielder_8, '')::INT,
            NULLIF(fielder_9, '')::INT,
            NULLIF(release_pos_y, '')::REAL,
            NULLIF(estimated_ba_using_speedangle, '')::REAL,
            NULLIF(estimated_woba_using_speedangle, '')::REAL,
            NULLIF(woba_value, '')::REAL,
            NULLIF(woba_denom, '')::REAL,
            NULLIF(babip_value, '')::REAL,
            NULLIF(iso_value, '')::REAL,
            NULLIF(launch_speed_angle, '')::REAL,
            NULLIF(at_bat_number, '')::INT,
            NULLIF(pitch_number, '')::INT,
            pitch_name,
            NULLIF(home_score, '')::INT,
            NULLIF(away_score, '')::INT,
            NULLIF(bat_score, '')::INT,
            NULLIF(fld_score, '')::INT,
            NULLIF(post_away_score, '')::INT,
            NULLIF(post_home_score, '')::INT,
            NULLIF(post_bat_score, '')::INT,
            NULLIF(post_fld_score, '')::INT,
            if_fielding_alignment, of_fielding_alignment,
            NULLIF(spin_axis, '')::REAL,
            NULLIF(delta_home_win_exp, '')::REAL,
            NULLIF(delta_run_exp, '')::REAL,
            NULLIF(bat_speed, '')::REAL,
            NULLIF(swing_length, '')::REAL,
            NULLIF(estimated_slg_using_speedangle, '')::REAL,
            NULLIF(delta_pitcher_run_exp, '')::REAL,
            NULLIF(hyper_speed, '')::REAL,
            NULLIF(home_score_diff, '')::INT,
            NULLIF(bat_score_diff, '')::INT,
            NULLIF(home_win_exp, '')::REAL,
            NULLIF(bat_win_exp, '')::REAL,
            NULLIF(age_pit_legacy, '')::INT,
            NULLIF(age_bat_legacy, '')::INT,
            NULLIF(age_pit, '')::INT,
            NULLIF(age_bat, '')::INT,
            NULLIF(n_thruorder_pitcher, '')::INT,
            NULLIF(n_priorpa_thisgame_player_at_bat, '')::INT,
            NULLIF(pitcher_days_since_prev_game, '')::INT,
            NULLIF(batter_days_since_prev_game, '')::INT,
            NULLIF(pitcher_days_until_next_game, '')::INT,
            NULLIF(batter_days_until_next_game, '')::INT,
            NULLIF(api_break_z_with_gravity, '')::REAL,
            NULLIF(api_break_x_arm, '')::REAL,
            NULLIF(api_break_x_batter_in, '')::REAL,
            NULLIF(arm_angle, '')::REAL,
            NULLIF(attack_angle, '')::REAL,
            NULLIF(attack_direction, '')::REAL,
            NULLIF(swing_path_tilt, '')::REAL,
            NULLIF(intercept_ball_minus_batter_pos_x_inches, '')::REAL,
            NULLIF(intercept_ball_minus_batter_pos_y_inches, '')::REAL
        FROM raw_mlb.stg_statcast
        ON CONFLICT (game_pk, at_bat_number, pitch_number) DO UPDATE SET
            pitch_type = EXCLUDED.pitch_type,
            game_date = EXCLUDED.game_date,
            release_speed = EXCLUDED.release_speed,
            release_pos_x = EXCLUDED.release_pos_x,
            release_pos_z = EXCLUDED.release_pos_z,
            player_name = EXCLUDED.player_name,
            batter = EXCLUDED.batter,
            pitcher = EXCLUDED.pitcher,
            events = EXCLUDED.events,
            description = EXCLUDED.description,
            spin_dir = EXCLUDED.spin_dir,
            spin_rate_deprecated = EXCLUDED.spin_rate_deprecated,
            break_angle_deprecated = EXCLUDED.break_angle_deprecated,
            break_length_deprecated = EXCLUDED.break_length_deprecated,
            zone = EXCLUDED.zone,
            des = EXCLUDED.des,
            game_type = EXCLUDED.game_type,
            stand = EXCLUDED.stand,
            p_throws = EXCLUDED.p_throws,
            home_team = EXCLUDED.home_team,
            away_team = EXCLUDED.away_team,
            type = EXCLUDED.type,
            hit_location = EXCLUDED.hit_location,
            bb_type = EXCLUDED.bb_type,
            balls = EXCLUDED.balls,
            strikes = EXCLUDED.strikes,
            game_year = EXCLUDED.game_year,
            pfx_x = EXCLUDED.pfx_x,
            pfx_z = EXCLUDED.pfx_z,
            plate_x = EXCLUDED.plate_x,
            plate_z = EXCLUDED.plate_z,
            on_3b = EXCLUDED.on_3b,
            on_2b = EXCLUDED.on_2b,
            on_1b = EXCLUDED.on_1b,
            outs_when_up = EXCLUDED.outs_when_up,
            inning = EXCLUDED.inning,
            inning_topbot = EXCLUDED.inning_topbot,
            hc_x = EXCLUDED.hc_x,
            hc_y = EXCLUDED.hc_y,
            tfs_deprecated = EXCLUDED.tfs_deprecated,
            tfs_zulu_deprecated = EXCLUDED.tfs_zulu_deprecated,
            umpire = EXCLUDED.umpire,
            sv_id = EXCLUDED.sv_id,
            vx0 = EXCLUDED.vx0,
            vy0 = EXCLUDED.vy0,
            vz0 = EXCLUDED.vz0,
            ax = EXCLUDED.ax,
            ay = EXCLUDED.ay,
            az = EXCLUDED.az,
            sz_top = EXCLUDED.sz_top,
            sz_bot = EXCLUDED.sz_bot,
            hit_distance_sc = EXCLUDED.hit_distance_sc,
            launch_speed = EXCLUDED.launch_speed,
            launch_angle = EXCLUDED.launch_angle,
            effective_speed = EXCLUDED.effective_speed,
            release_spin_rate = EXCLUDED.release_spin_rate,
            release_extension = EXCLUDED.release_extension,
            fielder_2 = EXCLUDED.fielder_2,
            fielder_3 = EXCLUDED.fielder_3,
            fielder_4 = EXCLUDED.fielder_4,
            fielder_5 = EXCLUDED.fielder_5,
            fielder_6 = EXCLUDED.fielder_6,
            fielder_7 = EXCLUDED.fielder_7,
            fielder_8 = EXCLUDED.fielder_8,
            fielder_9 = EXCLUDED.fielder_9,
            release_pos_y = EXCLUDED.release_pos_y,
            estimated_ba_using_speedangle = EXCLUDED.estimated_ba_using_speedangle,
            estimated_woba_using_speedangle = EXCLUDED.estimated_woba_using_speedangle,
            woba_value = EXCLUDED.woba_value,
            woba_denom = EXCLUDED.woba_denom,
            babip_value = EXCLUDED.babip_value,
            iso_value = EXCLUDED.iso_value,
            launch_speed_angle = EXCLUDED.launch_speed_angle,
            pitch_name = EXCLUDED.pitch_name,
            home_score = EXCLUDED.home_score,
            away_score = EXCLUDED.away_score,
            bat_score = EXCLUDED.bat_score,
            fld_score = EXCLUDED.fld_score,
            post_away_score = EXCLUDED.post_away_score,
            post_home_score = EXCLUDED.post_home_score,
            post_bat_score = EXCLUDED.post_bat_score,
            post_fld_score = EXCLUDED.post_fld_score,
            if_fielding_alignment = EXCLUDED.if_fielding_alignment,
            of_fielding_alignment = EXCLUDED.of_fielding_alignment,
            spin_axis = EXCLUDED.spin_axis,
            delta_home_win_exp = EXCLUDED.delta_home_win_exp,
            delta_run_exp = EXCLUDED.delta_run_exp,
            bat_speed = EXCLUDED.bat_speed,
            swing_length = EXCLUDED.swing_length,
            estimated_slg_using_speedangle = EXCLUDED.estimated_slg_using_speedangle,
            delta_pitcher_run_exp = EXCLUDED.delta_pitcher_run_exp,
            hyper_speed = EXCLUDED.hyper_speed,
            home_score_diff = EXCLUDED.home_score_diff,
            bat_score_diff = EXCLUDED.bat_score_diff,
            home_win_exp = EXCLUDED.home_win_exp,
            bat_win_exp = EXCLUDED.bat_win_exp,
            age_pit_legacy = EXCLUDED.age_pit_legacy,
            age_bat_legacy = EXCLUDED.age_bat_legacy,
            age_pit = EXCLUDED.age_pit,
            age_bat = EXCLUDED.age_bat,
            n_thruorder_pitcher = EXCLUDED.n_thruorder_pitcher,
            n_priorpa_thisgame_player_at_bat = EXCLUDED.n_priorpa_thisgame_player_at_bat,
            pitcher_days_since_prev_game = EXCLUDED.pitcher_days_since_prev_game,
            batter_days_since_prev_game = EXCLUDED.batter_days_since_prev_game,
            pitcher_days_until_next_game = EXCLUDED.pitcher_days_until_next_game,
            batter_days_until_next_game = EXCLUDED.batter_days_until_next_game,
            api_break_z_with_gravity = EXCLUDED.api_break_z_with_gravity,
            api_break_x_arm = EXCLUDED.api_break_x_arm,
            api_break_x_batter_in = EXCLUDED.api_break_x_batter_in,
            arm_angle = EXCLUDED.arm_angle,
            attack_angle = EXCLUDED.attack_angle,
            attack_direction = EXCLUDED.attack_direction,
            swing_path_tilt = EXCLUDED.swing_path_tilt,
            intercept_ball_minus_batter_pos_x_inches = EXCLUDED.intercept_ball_minus_batter_pos_x_inches,
            intercept_ball_minus_batter_pos_y_inches = EXCLUDED.intercept_ball_minus_batter_pos_y_inches;
    """)


def split_file(csv_path: Path):
    """Split a large CSV into smaller files with a header line preserved."""
    prefix = f'{csv_path}_part_'
    # Use GNU split - keep header in each part
    subprocess.run(
        f'head -n 1 {csv_path} > {prefix}header && tail -n +2 {csv_path} | split -l {CHUNK_ROWS} - {prefix}',
        shell=True,
        check=True,
    )
    parts = sorted(Path('.').glob(f'{prefix}*'))
    for part in parts:
        with open(part) as src, open(part, 'w') as dst:
            header = open(f'{prefix}header').read()
            dst.write(header)
            dst.write(src.read())
    os.remove(f'{prefix}header')
    return parts


def main():
    parser = argparse.ArgumentParser(description='Load Statcast CSV')
    parser.add_argument('--file', type=Path, required=True, help='Statcast CSV file')
    args = parser.parse_args()

    if not args.file.is_file():
        print(f'❌ File not found: {args.file}', file=sys.stderr)
        sys.exit(1)

    # If file > 500 MB, split into chunks
    if args.file.stat().st_size > 500 * 1024 * 1024:
        print('⚠️  Large Statcast file detected - splitting into chunks...')
        parts = split_file(args.file)
    else:
        parts = [args.file]

    conn = get_conn()
    try:
        cur = conn.cursor()
        for part in parts:
            create_staging(cur)
            copy_to_staging(cur, part)
            upsert(cur)
            conn.commit()
            print(f'✅ Loaded chunk {part.name}')
        print(f'✅ Completed Statcast load ({len(parts)} chunk(s))')
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()
