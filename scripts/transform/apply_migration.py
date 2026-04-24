#!/usr/bin/env python3
"""
Apply SQL migration files to the database.
Usage: python3 scripts/apply_migration.py <sql_file>
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def apply_migration(sql_file):
    conn = psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        database=os.getenv("PGDATABASE", "retrosheet"),
        user=os.getenv("PGUSER", os.getenv("USER")),
        password=os.getenv("PGPASSWORD"),
    )

    with open(sql_file, "r") as f:
        sql = f.read()

    with conn.cursor() as cur:
        cur.execute(sql)

    conn.commit()
    print(f"Migration applied successfully: {sql_file}")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/apply_migration.py <sql_file>")
        sys.exit(1)

    apply_migration(sys.argv[1])
