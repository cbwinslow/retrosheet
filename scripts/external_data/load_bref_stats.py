#!/usr/bin/env python3
"""
Load Baseball Reference style stats (from pybaseball) into raw_bref schema.

This script loads player-level seasonal statistics downloaded from pybaseball
(batting_stats_bref, pitching_stats_bref) into the database.

Usage:
    python3 scripts/external_data/load_bref_stats.py --file /path/to/batting_stats_2024.csv
    python3 scripts/external_data/load_bref_stats.py --dir data/statcast
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/retrosheet")


def get_conn():
    return psycopg2.connect(DB_URL)


def load_bref_batting(csv_path: Path) -> bool:
    """Load Baseball Reference batting stats."""
    print(f"Loading batting stats from {csv_path}")
    
    try:
        df = pd.read_csv(csv_path)
        print(f"  Read {len(df)} rows")
        
        conn = get_conn()
        cur = conn.cursor()
        
        # Create table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_bref.batting_stats (
                season INT,
                player_id TEXT,
                player_name TEXT,
                age INT,
                team TEXT,
                league TEXT,
                games INT,
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
                batting_avg REAL,
                on_base_pct REAL,
                slugging_pct REAL,
                ops REAL,
                UNIQUE (season, player_id, team)
            )
        """)
        
        # Prepare data for insertion
        data = []
        for _, row in df.iterrows():
            # Map columns based on pybaseball batting_stats_bref output
            data.append((
                row.get('Season'),
                row.get('player_id', ''),
                row.get('Name', ''),
                row.get('Age'),
                row.get('Tm', ''),
                row.get('Lg', ''),
                row.get('G'),
                row.get('AB'),
                row.get('R'),
                row.get('H'),
                row.get('2B'),
                row.get('3B'),
                row.get('HR'),
                row.get('RBI'),
                row.get('SB'),
                row.get('CS'),
                row.get('BB'),
                row.get('SO'),
                row.get('BA'),
                row.get('OBP'),
                row.get('SLG'),
                row.get('OPS'),
            ))
        
        # Insert data
        execute_values(
            cur,
            """
            INSERT INTO raw_bref.batting_stats 
            (season, player_id, player_name, age, team, league, games, at_bats, runs, hits, 
             doubles, triples, home_runs, rbi, stolen_bases, caught_stealing, walks, strikeouts,
             batting_avg, on_base_pct, slugging_pct, ops)
            VALUES %s
            ON CONFLICT (season, player_id, team) DO UPDATE SET
                player_name = EXCLUDED.player_name,
                age = EXCLUDED.age,
                league = EXCLUDED.league,
                games = EXCLUDED.games,
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
                ops = EXCLUDED.ops
            """,
            data
        )
        
        conn.commit()
        print(f"  ✅ Loaded {len(data)} rows")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()


def load_bref_pitching(csv_path: Path) -> bool:
    """Load Baseball Reference pitching stats."""
    print(f"Loading pitching stats from {csv_path}")
    
    try:
        df = pd.read_csv(csv_path)
        print(f"  Read {len(df)} rows")
        
        conn = get_conn()
        cur = conn.cursor()
        
        # Create table if not exists with TEXT columns to handle any data format
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_bref.pitching_stats (
                season TEXT,
                player_id TEXT,
                player_name TEXT,
                age TEXT,
                team TEXT,
                league TEXT,
                games TEXT,
                games_started TEXT,
                wins TEXT,
                losses TEXT,
                saves TEXT,
                innings_pitched TEXT,
                hits TEXT,
                runs TEXT,
                earned_runs TEXT,
                home_runs TEXT,
                walks TEXT,
                strikeouts TEXT,
                era TEXT,
                whip TEXT,
                UNIQUE (season, player_id, team)
            )
        """)
        
        # Prepare data for insertion
        data = []
        for _, row in df.iterrows():
            # Convert all values to strings to handle any data format
            data.append((
                str(row.get('Season', '')) if pd.notna(row.get('Season')) else None,
                str(row.get('player_id', '')) if pd.notna(row.get('player_id')) else None,
                str(row.get('Name', '')) if pd.notna(row.get('Name')) else None,
                str(row.get('Age', '')) if pd.notna(row.get('Age')) else None,
                str(row.get('Tm', '')) if pd.notna(row.get('Tm')) else None,
                str(row.get('Lg', '')) if pd.notna(row.get('Lg')) else None,
                str(row.get('G', '')) if pd.notna(row.get('G')) else None,
                str(row.get('GS', '')) if pd.notna(row.get('GS')) else None,
                str(row.get('W', '')) if pd.notna(row.get('W')) else None,
                str(row.get('L', '')) if pd.notna(row.get('L')) else None,
                str(row.get('SV', '')) if pd.notna(row.get('SV')) else None,
                str(row.get('IP', '')) if pd.notna(row.get('IP')) else None,
                str(row.get('H', '')) if pd.notna(row.get('H')) else None,
                str(row.get('R', '')) if pd.notna(row.get('R')) else None,
                str(row.get('ER', '')) if pd.notna(row.get('ER')) else None,
                str(row.get('HR', '')) if pd.notna(row.get('HR')) else None,
                str(row.get('BB', '')) if pd.notna(row.get('BB')) else None,
                str(row.get('SO', '')) if pd.notna(row.get('SO')) else None,
                str(row.get('ERA', '')) if pd.notna(row.get('ERA')) else None,
                str(row.get('WHIP', '')) if pd.notna(row.get('WHIP')) else None,
            ))
        
        # Insert data
        execute_values(
            cur,
            """
            INSERT INTO raw_bref.pitching_stats 
            (season, player_id, player_name, age, team, league, games, games_started, wins, losses,
             saves, innings_pitched, hits, runs, earned_runs, home_runs, walks, strikeouts, era, whip)
            VALUES %s
            """,
            data
        )
        
        conn.commit()
        print(f"  ✅ Loaded {len(data)} rows")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Load Baseball Reference stats from pybaseball"
    )
    parser.add_argument("--file", type=Path, help="Single CSV file to load")
    parser.add_argument("--dir", type=Path, help="Directory containing CSV files")
    args = parser.parse_args()
    
    # Create schema
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("CREATE SCHEMA IF NOT EXISTS raw_bref")
    conn.commit()
    conn.close()
    
    files_to_load = []
    
    if args.file:
        files_to_load.append(args.file)
    elif args.dir:
        files_to_load.extend(args.dir.glob("*.csv"))
    else:
        print("Error: Must specify --file or --dir")
        sys.exit(1)
    
    results = {}
    for csv_path in files_to_load:
        if 'batting' in csv_path.name:
            success = load_bref_batting(csv_path)
            results[csv_path.name] = success
        elif 'pitching' in csv_path.name:
            success = load_bref_pitching(csv_path)
            results[csv_path.name] = success
    
    print("\n" + "="*60)
    print("LOAD SUMMARY")
    print("="*60)
    for file_name, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {file_name}")
    print("="*60)


if __name__ == "__main__":
    main()
