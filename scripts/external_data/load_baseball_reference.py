#!/usr/bin/env python3
"""
Load Baseball-Reference game-log CSVs into the raw_baseball_reference schema.

The loader expects one or more CSV files in a directory. Each file is
processed with a staging table (all TEXT) and then upserted into the final
table `game_logs`. The primary key is a composite of (game_id, player_id).

Usage:
    python scripts/external_data/load_baseball_reference.py --dir /path/to/br_logs
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg2


DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/retrosheet')


def get_conn():
    return psycopg2.connect(DB_URL)


def create_staging(cur):
    cur.execute('DROP TABLE IF EXISTS raw_baseball_reference.stg_game_logs')
    # All columns as TEXT - we will cast later
    cur.execute("""
        CREATE TABLE raw_baseball_reference.stg_game_logs (
            game_id TEXT,
            player_id TEXT,
            team_id TEXT,
            GmDate TEXT,
            Age TEXT,
            Tm TEXT,
            Lg TEXT,
            W TEXT,
            L TEXT,
            G TEXT,
            GS TEXT,
            MP TEXT,
            AB TEXT,
            R TEXT,
            H TEXT,
            _2B TEXT,
            _3B TEXT,
            HR TEXT,
            RBI TEXT,
            SB TEXT,
            CS TEXT,
            BB TEXT,
            SO TEXT,
            BA TEXT,
            OBP TEXT,
            SLG TEXT,
            OPS TEXT,
            ISO TEXT,
            HBP TEXT,
            SH TEXT,
            SF TEXT,
            GIDP TEXT
        )
    """)


def copy_to_staging(cur, csv_path):
    with open(csv_path, newline='') as f:
        cur.copy_expert('COPY raw_baseball_reference.stg_game_logs FROM STDIN WITH CSV HEADER', f)


def upsert(cur):
    # Ensure target table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS raw_baseball_reference.game_logs (
            game_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            team_id TEXT,
            game_date DATE,
            age INT,
            team TEXT,
            league TEXT,
            wins INT,
            losses INT,
            games INT,
            games_started INT,
            minutes_played NUMERIC,
            at_bats INT,
            runs INT,
            hits INT,
            doubles INT,
            triples INT,
            home_runs INT,
            rbi INT,
            stolen_bases INT,
            caught_stealing INT,
            walks INT,
            strikeouts INT,
            batting_avg NUMERIC,
            on_base_pct NUMERIC,
            slugging_pct NUMERIC,
            ops NUMERIC,
            iso NUMERIC,
            hit_by_pitch INT,
            sacrifice_hits INT,
            sacrifice_flies INT,
            gidp INT,
            PRIMARY KEY (game_id, player_id)
        );
    """)
    # Cast columns to appropriate types
    cur.execute("""
        INSERT INTO raw_baseball_reference.game_logs (
            game_id, player_id, team_id, game_date, age, team, league,
            wins, losses, games, games_started, minutes_played,
            at_bats, runs, hits, doubles, triples, home_runs, rbi,
            stolen_bases, caught_stealing, walks, strikeouts,
            batting_avg, on_base_pct, slugging_pct, ops, iso,
            hit_by_pitch, sacrifice_hits, sacrifice_flies, gidp
        )
        SELECT
            game_id,
            player_id,
            team_id,
            to_date(GmDate, 'YYYY-MM-DD')::date,
            NULLIF(Age, '')::INT,
            Tm,
            Lg,
            NULLIF(W, '')::INT,
            NULLIF(L, '')::INT,
            NULLIF(G, '')::INT,
            NULLIF(GS, '')::INT,
            NULLIF(MP, '')::NUMERIC,
            NULLIF(AB, '')::INT,
            NULLIF(R, '')::INT,
            NULLIF(H, '')::INT,
            NULLIF(_2B, '')::INT,
            NULLIF(_3B, '')::INT,
            NULLIF(HR, '')::INT,
            NULLIF(RBI, '')::INT,
            NULLIF(SB, '')::INT,
            NULLIF(CS, '')::INT,
            NULLIF(BB, '')::INT,
            NULLIF(SO, '')::INT,
            NULLIF(BA, '')::NUMERIC,
            NULLIF(OBP, '')::NUMERIC,
            NULLIF(SLG, '')::NUMERIC,
            NULLIF(OPS, '')::NUMERIC,
            NULLIF(ISO, '')::NUMERIC,
            NULLIF(HBP, '')::INT,
            NULLIF(SH, '')::INT,
            NULLIF(SF, '')::INT,
            NULLIF(GIDP, '')::INT
        FROM raw_baseball_reference.stg_game_logs
        ON CONFLICT (game_id, player_id) DO UPDATE SET
            team_id = EXCLUDED.team_id,
            game_date = EXCLUDED.game_date,
            age = EXCLUDED.age,
            team = EXCLUDED.team,
            league = EXCLUDED.league,
            wins = EXCLUDED.wins,
            losses = EXCLUDED.losses,
            games = EXCLUDED.games,
            games_started = EXCLUDED.games_started,
            minutes_played = EXCLUDED.minutes_played,
            at_bats = EXCLUDED.at_bats,
            runs = EXCLUDED.runs,
            hits = EXCLUDED.hits,
            doubles = EXCLUDED.doubles,
            triples = EXCLUDED.triples,
            home_runs = EXCLUDED.home_runs,
            rbi = EXCLUDED.rbi,
            stolen_bases = EXCLUDED.stolen_bases,
            caught_stealing = EXCLUDED.caught_stealing,
            walks = EXCLUDED.walks,
            strikeouts = EXCLUDED.strikeouts,
            batting_avg = EXCLUDED.batting_avg,
            on_base_pct = EXCLUDED.on_base_pct,
            slugging_pct = EXCLUDED.slugging_pct,
            ops = EXCLUDED.ops,
            iso = EXCLUDED.iso,
            hit_by_pitch = EXCLUDED.hit_by_pitch,
            sacrifice_hits = EXCLUDED.sacrifice_hits,
            sacrifice_flies = EXCLUDED.sacrifice_flies,
            gidp = EXCLUDED.gidp;
    """)


def main():
    parser = argparse.ArgumentParser(description='Load Baseball-Reference game logs')
    parser.add_argument('--dir', type=Path, required=True, help='Directory with CSV files')
    args = parser.parse_args()
    csv_files = list(Path(args.dir).glob('*.csv'))
    if not csv_files:
        print('⚠️  No CSV files found in the directory.', file=sys.stderr)
        sys.exit(1)

    conn = get_conn()
    try:
        cur = conn.cursor()
        create_staging(cur)
        for csv_path in csv_files:
            copy_to_staging(cur, csv_path)
        upsert(cur)
        conn.commit()
        print(f'✅ Loaded {len(csv_files)} Baseball-Reference game-log files')
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()
