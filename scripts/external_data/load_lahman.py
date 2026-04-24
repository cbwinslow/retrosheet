#!/usr/bin/env python3
"""
Load Lahman CSV files into the raw_lahman schema.

The script follows a robust staging‑then‑upsert pattern:
1. Create a temporary staging table (all columns TEXT).
2. COPY the CSV into the staging table.
3. INSERT … SELECT with explicit casts into the final table,
   using ON CONFLICT to make the load idempotent.
4. Drop the staging table.

Usage:
    python scripts/external_data/load_lahman.py --dir /path/to/lahman_csv
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg2

DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/retrosheet")


def get_conn():
    return psycopg2.connect(DB_URL)


# Mapping of CSV filename → (target table, column list)
TABLES = {
    "People.csv": (
        "people",
        [
            "playerID",
            "birthYear",
            "birthMonth",
            "birthDay",
            "birthCountry",
            "birthState",
            "birthCity",
            "deathYear",
            "deathMonth",
            "deathDay",
            "deathCountry",
            "deathState",
            "deathCity",
            "nameFirst",
            "nameLast",
            "nameGiven",
            "weight",
            "height",
            "bats",
            "throws",
            "debut",
            "finalGame",
            "retroID",
            "bbrefID",
        ],
    ),
    "Teams.csv": (
        "teams",
        [
            "yearID",
            "lgID",
            "teamID",
            "franchID",
            "divID",
            "Rank",
            "G",
            "Ghome",
            "W",
            "L",
            "DivWin",
            "WCWin",
            "LgWin",
            "WSWin",
            "R",
            "AB",
            "H",
            "_2B",
            "_3B",
            "HR",
            "BB",
            "SO",
            "SB",
            "CS",
            "HBP",
            "SF",
            "RA",
            "ER",
            "ERA",
            "CG",
            "SHO",
            "SV",
            "IPouts",
            "HAA",
            "HA",
            "BAA",
            "OAA",
            "OBA",
            "leagueID",
            "parkID",
            "attendance",
            "teamIDBR",
            "teamIDlahman45",
            "teamIDretro",
        ],
    ),
    "Salaries.csv": ("salaries", ["yearID", "teamID", "playerID", "salary"]),
    "Pitching.csv": (
        "pitching",
        [
            "yearID",
            "lgID",
            "teamID",
            "playerID",
            "W",
            "L",
            "G",
            "GS",
            "CG",
            "SHO",
            "SV",
            "IPouts",
            "H",
            "ER",
            "HR",
            "BB",
            "SO",
            "BAOpp",
            "ERA",
            "IBB",
            "WP",
            "HBP",
            "BK",
            "BFP",
            "GF",
            "R",
            "SH",
            "SF",
            "GIDP",
        ],
    ),
    "Batting.csv": (
        "batting",
        [
            "yearID",
            "lgID",
            "teamID",
            "playerID",
            "G",
            "AB",
            "R",
            "H",
            "_2B",
            "_3B",
            "HR",
            "RBI",
            "SB",
            "CS",
            "BB",
            "SO",
            "IBB",
            "HBP",
            "SH",
            "SF",
            "GIDP",
        ],
    ),
}


def create_staging(cur, table, columns):
    cur.execute(f"DROP TABLE IF EXISTS raw_lahman.stg_{table}")
    col_defs = ", ".join([f"{c} TEXT" for c in columns])
    cur.execute(f"CREATE TABLE raw_lahman.stg_{table} ({col_defs})")


def copy_to_staging(cur, csv_path, table):
    with open(csv_path, "r", newline="") as f:
        cur.copy_expert(f"COPY raw_lahman.stg_{table} FROM STDIN WITH CSV HEADER", f)


def upsert(cur, table, columns):
    # Define column groups for proper casting
    int_cols = {
        "birthYear",
        "birthMonth",
        "birthDay",
        "deathYear",
        "deathMonth",
        "deathDay",
        "weight",
        "height",
        "yearID",
        "Rank",
        "G",
        "Ghome",
        "W",
        "L",
        "AB",
        "H",
        "_2B",
        "_3B",
        "HR",
        "BB",
        "SO",
        "SB",
        "CS",
        "HBP",
        "SF",
        "RA",
        "ER",
        "CG",
        "SHO",
        "SV",
        "IPouts",
        "HAA",
        "HA",
        "attendance",
        "salary",
        "R",
        "GIDP",
        "GS",
        "IBB",
        "WP",
        "BK",
        "BFP",
        "GF",
        "SH",
        "RBI",
    }
    numeric_cols = {"ERA", "BAOpp", "BAA", "OAA", "OBA", "AVG", "OBP", "SLG", "OPS"}
    date_cols = {"debut", "finalGame"}

    # Cast each column to the appropriate type
    cast_expressions = []
    for c in columns:
        if c in (
            "playerID",
            "teamID",
            "franchID",
            "lgID",
            "divID",
            "parkID",
            "leagueID",
            "retroID",
            "bbrefID",
        ):
            cast_expressions.append(c)  # keep as TEXT
        elif c in int_cols:
            # Use NULLIF to treat empty strings as NULL before casting to INT
            cast_expressions.append(f"NULLIF({c}, '')::INT")
        elif c in numeric_cols:
            cast_expressions.append(f"{c}::NUMERIC")
        elif c in date_cols:
            cast_expressions.append(f"{c}::DATE")
        else:
            cast_expressions.append(f"{c}::TEXT")

    # Determine primary‑key columns for each table
    if table == "people":
        pk_cols = ["playerID"]
    elif table == "teams":
        pk_cols = ["yearID", "teamID"]
    elif table == "salaries":
        pk_cols = ["yearID", "teamID", "playerID"]
    elif table in ("pitching", "batting"):
        pk_cols = ["yearID", "playerID", "teamID"]
    else:
        pk_cols = [columns[0]]  # fallback

    # Build SET clause for all non‑PK columns
    set_clause = ", ".join([f"{c}=EXCLUDED.{c}" for c in columns if c not in pk_cols])

    # Use ON CONFLICT ON CONSTRAINT <table>_pkey for safety
    cur.execute(
        f"""
        INSERT INTO raw_lahman.{table} ({", ".join(columns)})
        SELECT {", ".join(cast_expressions)} FROM raw_lahman.stg_{table}
        ON CONFLICT ON CONSTRAINT {table}_pkey DO UPDATE SET {set_clause}
        """
    )


def process_file(csv_dir: Path, filename: str, table: str, columns: list):
    csv_path = csv_dir / filename
    if not csv_path.is_file():
        print(f"⚠️  {filename} not found, skipping.", file=sys.stderr)
        return
    conn = get_conn()
    try:
        cur = conn.cursor()
        create_staging(cur, table, columns)
        copy_to_staging(cur, csv_path, table)
        upsert(cur, table, columns)
        conn.commit()
        print(f"✅ Loaded {filename} into raw_lahman.{table}")
    finally:
        cur.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Load Lahman CSVs")
    parser.add_argument("--dir", type=Path, required=True, help="Directory containing Lahman CSVs")
    args = parser.parse_args()
    for filename, (table, cols) in TABLES.items():
        process_file(args.dir, filename, table, cols)


if __name__ == "__main__":
    main()
