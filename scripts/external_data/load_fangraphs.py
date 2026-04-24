#!/usr/bin/env python3
"""
Load Fangraphs player-season and team-season CSVs into the raw_fangraphs schema.

Both CSVs are loaded via a staging table (all TEXT) and then upserted with
proper type casts. The primary keys are (player_id, season) and (team_id, season).

Usage:
    python scripts/external_data/load_fangraphs.py --player /path/player.csv --team /path/team.csv
"""

import argparse
import os
from pathlib import Path

import psycopg2


DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/retrosheet')


def get_conn():
    return psycopg2.connect(DB_URL)


def create_staging(cur, name, columns):
    cur.execute(f'DROP TABLE IF EXISTS raw_fangraphs.stg_{name}')
    col_defs = ', '.join([f'{c} TEXT' for c in columns])
    cur.execute(f'CREATE TABLE raw_fangraphs.stg_{name} ({col_defs})')


def copy_to_staging(cur, csv_path, name):
    # Read the CSV and filter out any completely empty lines that can break COPY
    # Detect and skip HTML content that may be mistakenly named .csv
    with open(csv_path, newline='') as raw_f:
        first_line = raw_f.readline()
        if first_line.lstrip().startswith('<'):
            print(f'Skipping HTML file for {name}: {csv_path}')
            return False
        # Reset to start and filter empty lines
        raw_f.seek(0)
        lines = [line for line in raw_f if line.strip()]
    # Use a temporary in-memory file-like object for COPY
    from io import StringIO

    filtered = StringIO(''.join(lines))
    cur.copy_expert(f"COPY raw_fangraphs.stg_{name} FROM STDIN WITH CSV HEADER NULL ''", filtered)
    return True


def upsert_player(cur):
    cur.execute("""
        INSERT INTO raw_fangraphs.player_season (
            player_id, season, team_id, age, g, pa, ab, r, h, double, triple,
            hr, rbi, sb, cs, bb, ibb, hbp, so, avg, obp, slg, ops, woba,
            woba_plus, wrc_plus, war
        )
        SELECT
            player_id,
            NULLIF(season, '')::INT,
            team_id,
            NULLIF(age, '')::INT,
            NULLIF(g, '')::INT,
            NULLIF(pa, '')::INT,
            NULLIF(ab, '')::INT,
            NULLIF(r, '')::INT,
            NULLIF(h, '')::INT,
            NULLIF(double, '')::INT,
            NULLIF(triple, '')::INT,
            NULLIF(hr, '')::INT,
            NULLIF(rbi, '')::INT,
            NULLIF(sb, '')::INT,
            NULLIF(cs, '')::INT,
            NULLIF(bb, '')::INT,
            NULLIF(ibb, '')::INT,
            NULLIF(hbp, '')::INT,
            NULLIF(so, '')::INT,
            NULLIF(avg, '')::NUMERIC,
            NULLIF(obp, '')::NUMERIC,
            NULLIF(slg, '')::NUMERIC,
            NULLIF(ops, '')::NUMERIC,
            NULLIF(woba, '')::NUMERIC,
            NULLIF(woba_plus, '')::INT,
            NULLIF(wrc_plus, '')::INT,
            NULLIF(war, '')::NUMERIC
        FROM raw_fangraphs.stg_player_season
        ON CONFLICT (player_id, season) DO UPDATE SET
            team_id = EXCLUDED.team_id,
            age = EXCLUDED.age,
            g = EXCLUDED.g,
            pa = EXCLUDED.pa,
            ab = EXCLUDED.ab,
            r = EXCLUDED.r,
            h = EXCLUDED.h,
            double = EXCLUDED.double,
            triple = EXCLUDED.triple,
            hr = EXCLUDED.hr,
            rbi = EXCLUDED.rbi,
            sb = EXCLUDED.sb,
            cs = EXCLUDED.cs,
            bb = EXCLUDED.bb,
            ibb = EXCLUDED.ibb,
            hbp = EXCLUDED.hbp,
            so = EXCLUDED.so,
            avg = EXCLUDED.avg,
            obp = EXCLUDED.obp,
            slg = EXCLUDED.slg,
            ops = EXCLUDED.ops,
            woba = EXCLUDED.woba,
            woba_plus = EXCLUDED.woba_plus,
            wrc_plus = EXCLUDED.wrc_plus,
            war = EXCLUDED.war;
    """)


def upsert_team(cur):
    cur.execute("""
        INSERT INTO raw_fangraphs.team_season (
            team_id, season, g, w, l, r, ra, era, woba, woba_plus, wrc_plus, war
        )
        SELECT
            team_id,
            NULLIF(season, '')::INT,
            NULLIF(g, '')::INT,
            NULLIF(w, '')::INT,
            NULLIF(l, '')::INT,
            NULLIF(r, '')::INT,
            NULLIF(ra, '')::INT,
            NULLIF(era, '')::NUMERIC,
            NULLIF(woba, '')::NUMERIC,
            NULLIF(woba_plus, '')::INT,
            NULLIF(wrc_plus, '')::INT,
            NULLIF(war, '')::NUMERIC
        FROM raw_fangraphs.stg_team_season
        ON CONFLICT (team_id, season) DO UPDATE SET
            g = EXCLUDED.g,
            w = EXCLUDED.w,
            l = EXCLUDED.l,
            r = EXCLUDED.r,
            ra = EXCLUDED.ra,
            era = EXCLUDED.era,
            woba = EXCLUDED.woba,
            woba_plus = EXCLUDED.woba_plus,
            wrc_plus = EXCLUDED.wrc_plus,
            war = EXCLUDED.war;
    """)


def main():
    parser = argparse.ArgumentParser(description='Load Fangraphs CSVs')
    parser.add_argument('--player', type=Path, required=True, help='Player season CSV')
    parser.add_argument('--team', type=Path, required=True, help='Team season CSV')
    args = parser.parse_args()

    player_cols = [
        'player_id',
        'season',
        'team_id',
        'age',
        'g',
        'pa',
        'ab',
        'r',
        'h',
        'double',
        'triple',
        'hr',
        'rbi',
        'sb',
        'cs',
        'bb',
        'ibb',
        'hbp',
        'so',
        'avg',
        'obp',
        'slg',
        'ops',
        'woba',
        'woba_plus',
        'wrc_plus',
        'war',
    ]
    team_cols = [
        'team_id',
        'season',
        'g',
        'w',
        'l',
        'r',
        'ra',
        'era',
        'woba',
        'woba_plus',
        'wrc_plus',
        'war',
    ]

    conn = get_conn()
    try:
        cur = conn.cursor()
        # Player season
        create_staging(cur, 'player_season', player_cols)
        if str(args.player).lower().endswith('.csv'):
            if copy_to_staging(cur, args.player, 'player_season'):
                upsert_player(cur)
        else:
            print(f'Skipping non-CSV player file: {args.player}')

        # Team season
        create_staging(cur, 'team_season', team_cols)
        if str(args.team).lower().endswith('.csv'):
            if copy_to_staging(cur, args.team, 'team_season'):
                upsert_team(cur)
        else:
            print(f'Skipping non-CSV team file: {args.team}')

        conn.commit()
        print('✅ Loaded Fangraphs player and team season data')
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()
