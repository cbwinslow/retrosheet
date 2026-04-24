#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import subprocess
import tempfile
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "data" / "raw" / "retrosheet" / "reference"
SQL_PATH = ROOT / "sql" / "030_reference_metadata.sql"


BIOFILE_COLUMNS = [
    "player_id",
    "last_name",
    "first_name",
    "nickname",
    "birthdate",
    "birth_city",
    "birth_state",
    "birth_country",
    "play_debut",
    "play_lastgame",
    "mgr_debut",
    "mgr_lastgame",
    "coach_debut",
    "coach_lastgame",
    "ump_debut",
    "ump_lastgame",
    "deathdate",
    "death_city",
    "death_state",
    "death_country",
    "bats",
    "throws",
    "height",
    "weight",
    "cemetery",
    "cemetery_city",
    "cemetery_state",
    "cemetery_country",
    "cemetery_note",
    "birth_name",
    "name_change",
    "bat_change",
    "hall_of_fame",
]

TEAMS_COLUMNS = [
    "retrosheet_team_id",
    "league",
    "city",
    "nickname",
    "first_season",
    "last_season",
]

BALLPARKS_COLUMNS = [
    "retrosheet_park_id",
    "name",
    "aka",
    "city",
    "state",
    "start_date",
    "end_date",
    "league",
    "notes",
]


def database_kwargs() -> dict[str, str]:
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": os.environ.get("PGPORT", "5432"),
        "dbname": os.environ.get("PGDATABASE", "retrosheet"),
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", ""),
    }


def psql_base_args() -> list[str]:
    args = ["psql", "-v", "ON_ERROR_STOP=1"]
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        args.append(database_url)
    else:
        args.extend(["-h", os.environ.get("PGHOST", "localhost")])
        args.extend(["-p", os.environ.get("PGPORT", "5432")])
        args.extend(["-d", os.environ.get("PGDATABASE", "retrosheet")])
    return args


def run_psql(sql: str) -> None:
    subprocess.run(psql_base_args() + ["-c", sql], check=True)


def normalize_csv(source: Path, columns: list[str]) -> Path:
    if not source.exists():
        raise SystemExit(f"Missing reference file: {source}")
    tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", newline="", delete=False)
    tmp_path = Path(tmp.name)
    with tmp, source.open(newline="", encoding="utf-8-sig") as fin:
        reader = csv.reader(fin)
        writer = csv.writer(tmp)
        header = next(reader)
        if len(header) != len(columns):
            raise SystemExit(f"Unexpected column count in {source}: {len(header)}")
        writer.writerow(columns)
        for row in reader:
            writer.writerow(row)
    return tmp_path


def copy_csv(conn, table: str, path: Path, columns: list[str]) -> None:
    column_sql = ", ".join(columns)
    with conn.cursor() as cur, path.open("r", encoding="utf-8") as handle:
        cur.execute(f"TRUNCATE TABLE {table};")
        cur.copy_expert(
            f"COPY {table} ({column_sql}) FROM STDIN WITH (FORMAT csv, HEADER true)",
            handle,
        )
    conn.commit()


def main() -> None:
    # First run only the DDL portion indirectly by allowing tables to exist before COPY.
    run_psql(SQL_PATH.read_text().split("ALTER TABLE core.players", 1)[0])

    normalized_files = [
        (
            "raw_retrosheet.biofile",
            normalize_csv(REFERENCE_DIR / "biofile.csv", BIOFILE_COLUMNS),
            BIOFILE_COLUMNS,
        ),
        (
            "raw_retrosheet.teams_reference",
            normalize_csv(REFERENCE_DIR / "teams.csv", TEAMS_COLUMNS),
            TEAMS_COLUMNS,
        ),
        (
            "raw_retrosheet.ballparks_reference",
            normalize_csv(REFERENCE_DIR / "ballparks.csv", BALLPARKS_COLUMNS),
            BALLPARKS_COLUMNS,
        ),
    ]

    conn = psycopg2.connect(**database_kwargs())
    try:
        for table, path, columns in normalized_files:
            copy_csv(conn, table, path, columns)
            print(f"loaded {table} from {path}")
    finally:
        conn.close()
        for _, path, _ in normalized_files:
            path.unlink(missing_ok=True)

    subprocess.run(psql_base_args() + ["-f", str(SQL_PATH)], check=True)


if __name__ == "__main__":
    main()
