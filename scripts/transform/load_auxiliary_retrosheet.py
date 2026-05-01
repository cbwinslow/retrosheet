#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import psycopg2


if TYPE_CHECKING:
    from collections.abc import Iterable


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / 'data' / 'raw' / 'retrosheet' / 'reference'
SEASONS_DIR = ROOT / 'data' / 'raw' / 'retrosheet' / 'seasons'
GAMELOG_DIR = ROOT / 'data' / 'raw' / 'retrosheet' / 'gamelog'
SQL_PATH = ROOT / 'sql' / '040_auxiliary_retrosheet.sql'

ALLSTAR_TEAM_IDS = {'ALS', 'NLS', 'ASE', 'ASW'}


TABLE_COLUMNS = {
    'raw_retrosheet.biofile_legacy': [
        'player_id',
        'last_name',
        'use_name',
        'full_name',
        'birthdate',
        'birth_city',
        'birth_state',
        'birth_country',
        'deathdate',
        'death_city',
        'death_state',
        'death_country',
        'cemetery',
        'cemetery_city',
        'cemetery_state',
        'cemetery_country',
        'cemetery_note',
        'birth_name',
        'alt_name',
        'play_debut',
        'play_lastgame',
        'coach_debut',
        'coach_lastgame',
        'manager_debut',
        'manager_lastgame',
        'umpire_debut',
        'umpire_lastgame',
        'bats',
        'throws',
        'height',
        'weight',
        'hall_of_fame',
    ],
    'raw_retrosheet.coaches': [
        'source_row_number',
        'coach_id',
        'season',
        'team_id',
        'role',
        'start_date',
        'end_date',
    ],
    'raw_retrosheet.ejections': [
        'source_row_number',
        'game_id',
        'game_date',
        'doubleheader_flag',
        'ejectee_id',
        'ejectee_name',
        'team_id',
        'job',
        'umpire_id',
        'umpire_name',
        'inning',
        'reason',
    ],
    'raw_retrosheet.relatives': [
        'source_row_number',
        'player_id_1',
        'relationship',
        'player_id_2',
    ],
    'raw_retrosheet.season_rosters': [
        'source_file',
        'source_row_number',
        'season',
        'roster_team_id',
        'player_id',
        'last_name',
        'first_name',
        'bats',
        'throws',
        'team_id',
        'position',
        'is_allstar',
    ],
    'raw_retrosheet.season_teams': [
        'source_file',
        'source_row_number',
        'season',
        'team_id',
        'league',
        'city',
        'nickname',
        'is_allstar',
    ],
    'raw_retrosheet.season_schedules': [
        'source_file',
        'source_row_number',
        'season',
        'game_date',
        'game_number',
        'day_of_week',
        'visitor_team_id',
        'visitor_league',
        'visitor_game_number',
        'home_team_id',
        'home_league',
        'home_game_number',
        'day_night',
        'park_id',
        'postponed',
        'makeup',
    ],
    'raw_retrosheet.season_umpires': [
        'source_file',
        'source_row_number',
        'season',
        'umpire_id',
        'last_name',
        'first_name',
    ],
    'raw_retrosheet.special_gamelog_lines': [
        'source_file',
        'source_row_number',
        'game_type',
        'row_text',
    ],
}


def database_kwargs() -> dict[str, str]:
    return {
        'host': os.environ.get('PGHOST', 'localhost'),
        'port': os.environ.get('PGPORT', '5432'),
        'dbname': os.environ.get('PGDATABASE', 'retrosheet'),
        'user': os.environ.get('PGUSER', 'postgres'),
        'password': os.environ.get('PGPASSWORD', ''),
    }


def psql_base_args() -> list[str]:
    args = ['psql', '-v', 'ON_ERROR_STOP=1']
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        args.append(database_url)
    else:
        args.extend(['-h', os.environ.get('PGHOST', 'localhost')])
        args.extend(['-p', os.environ.get('PGPORT', '5432')])
        args.extend(['-d', os.environ.get('PGDATABASE', 'retrosheet')])
    return args


def run_psql(sql: str | None = None, file_path: Path | None = None) -> None:
    if file_path:
        subprocess.run([*psql_base_args(), '-f', str(file_path)], check=True)
        return
    if sql is None:
        msg = 'sql or file_path is required'
        raise ValueError(msg)
    subprocess.run([*psql_base_args(), '-c', sql], check=True)


def season_from_path(path: Path) -> int:
    match = re.search(r'(18|19|20)\d{2}', path.name)
    if not match:
        msg = f'Could not infer season from {path}'
        raise ValueError(msg)
    return int(match.group(0))


def relative_path(path: Path) -> str:
    return str(path.relative_to(ROOT))


def write_csv(table: str, rows: Iterable[dict[str, object]]) -> Path:
    columns = TABLE_COLUMNS[table]
    tmp = tempfile.NamedTemporaryFile('w', suffix='.csv', newline='', delete=False)
    tmp_path = Path(tmp.name)
    with tmp:
        writer = csv.DictWriter(tmp, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, '') for column in columns})
    return tmp_path


def copy_csv(conn, table: str, path: Path) -> None:
    columns = TABLE_COLUMNS[table]
    column_sql = ', '.join(columns)
    with conn.cursor() as cur, path.open('r', encoding='utf-8') as handle:
        cur.copy_expert(
            f'COPY {table} ({column_sql}) FROM STDIN WITH (FORMAT csv, HEADER true)',
            handle,
        )
    conn.commit()


def load_headered_reference(path: Path, table: str, mapping: dict[str, str]) -> Path:
    def rows() -> Iterable[dict[str, object]]:
        with path.open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.DictReader(handle)
            for row_number, row in enumerate(reader, start=1):
                out = {'source_row_number': row_number}
                for source_column, target_column in mapping.items():
                    out[target_column] = row.get(source_column, '')
                yield out

    return write_csv(table, rows())


def load_biofile_legacy() -> Path:
    source = REFERENCE_DIR / 'biofile0.csv'
    columns = TABLE_COLUMNS['raw_retrosheet.biofile_legacy']

    def rows() -> Iterable[dict[str, object]]:
        with source.open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.reader(handle)
            header = next(reader)
            if len(header) != len(columns):
                msg = f'Unexpected column count in {source}: {len(header)}'
                raise SystemExit(msg)
            for row in reader:
                yield dict(zip(columns, row, strict=False))

    return write_csv('raw_retrosheet.biofile_legacy', rows())


def iter_rosters() -> Iterable[dict[str, object]]:
    for path in sorted(SEASONS_DIR.glob('*/*.ROS')):
        season = season_from_path(path)
        roster_team_id = path.stem[:3]
        is_allstar = roster_team_id in ALLSTAR_TEAM_IDS
        with path.open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.reader(handle)
            for row_number, row in enumerate(reader, start=1):
                if not row:
                    continue
                padded = (row + [''] * 7)[:7]
                yield {
                    'source_file': relative_path(path),
                    'source_row_number': row_number,
                    'season': season,
                    'roster_team_id': roster_team_id,
                    'player_id': padded[0],
                    'last_name': padded[1],
                    'first_name': padded[2],
                    'bats': padded[3],
                    'throws': padded[4],
                    'team_id': padded[5],
                    'position': padded[6],
                    'is_allstar': is_allstar,
                }


def iter_season_teams() -> Iterable[dict[str, object]]:
    for path in sorted(SEASONS_DIR.glob('*/TEAM*')):
        if not path.is_file() or path.name.lower().endswith('.txt'):
            continue
        season = season_from_path(path)
        with path.open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.reader(handle)
            for row_number, row in enumerate(reader, start=1):
                if not row:
                    continue
                padded = (row + [''] * 4)[:4]
                team_id = padded[0]
                yield {
                    'source_file': relative_path(path),
                    'source_row_number': row_number,
                    'season': season,
                    'team_id': team_id,
                    'league': padded[1],
                    'city': padded[2],
                    'nickname': padded[3],
                    'is_allstar': team_id in ALLSTAR_TEAM_IDS,
                }


def iter_schedules() -> Iterable[dict[str, object]]:
    for path in sorted(SEASONS_DIR.glob('*/*schedule.csv')):
        season = season_from_path(path)
        with path.open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.reader(handle)
            next(reader, None)
            for row_number, row in enumerate(reader, start=1):
                if not row:
                    continue
                padded = (row + [''] * 13)[:13]
                yield {
                    'source_file': relative_path(path),
                    'source_row_number': row_number,
                    'season': season,
                    'game_date': padded[0],
                    'game_number': padded[1],
                    'day_of_week': padded[2],
                    'visitor_team_id': padded[3],
                    'visitor_league': padded[4],
                    'visitor_game_number': padded[5],
                    'home_team_id': padded[6],
                    'home_league': padded[7],
                    'home_game_number': padded[8],
                    'day_night': padded[9],
                    'park_id': padded[10],
                    'postponed': padded[11],
                    'makeup': padded[12],
                }


def iter_umpires() -> Iterable[dict[str, object]]:
    for path in sorted(SEASONS_DIR.glob('*/UMPIRES*.txt')):
        season = season_from_path(path)
        with path.open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                continue
            for row_number, row in enumerate(reader, start=1):
                umpire_id = row.get('ID', '')
                if not umpire_id:
                    continue
                yield {
                    'source_file': relative_path(path),
                    'source_row_number': row_number,
                    'season': season,
                    'umpire_id': umpire_id,
                    'last_name': row.get('last', ''),
                    'first_name': row.get('first', ''),
                }


def iter_special_gamelogs() -> Iterable[dict[str, object]]:
    for path in sorted(GAMELOG_DIR.glob('GL*.TXT')):
        game_type = path.stem.removeprefix('GL').lower()
        with path.open(encoding='utf-8-sig') as handle:
            for row_number, line in enumerate(handle, start=1):
                row_text = line.rstrip('\n\r')
                if not row_text:
                    continue
                yield {
                    'source_file': relative_path(path),
                    'source_row_number': row_number,
                    'game_type': game_type,
                    'row_text': row_text,
                }


def main() -> None:
    run_psql(file_path=SQL_PATH)
    tables = list(TABLE_COLUMNS)
    run_psql('TRUNCATE TABLE ' + ', '.join(tables) + ';')

    csv_paths = {
        'raw_retrosheet.biofile_legacy': load_biofile_legacy(),
        'raw_retrosheet.coaches': load_headered_reference(
            REFERENCE_DIR / 'coaches.csv',
            'raw_retrosheet.coaches',
            {
                'id': 'coach_id',
                'year': 'season',
                'team': 'team_id',
                'role': 'role',
                'start': 'start_date',
                'end': 'end_date',
            },
        ),
        'raw_retrosheet.ejections': load_headered_reference(
            REFERENCE_DIR / 'ejections.csv',
            'raw_retrosheet.ejections',
            {
                'GAMEID': 'game_id',
                'DATE': 'game_date',
                'DH': 'doubleheader_flag',
                'EJECTEE': 'ejectee_id',
                'EJECTEENAME': 'ejectee_name',
                'TEAM': 'team_id',
                'JOB': 'job',
                'UMPIRE': 'umpire_id',
                'UMPIRENAME': 'umpire_name',
                'INNING': 'inning',
                'REASON': 'reason',
            },
        ),
        'raw_retrosheet.relatives': load_headered_reference(
            REFERENCE_DIR / 'relatives.csv',
            'raw_retrosheet.relatives',
            {'id1': 'player_id_1', 'relation': 'relationship', 'id2': 'player_id_2'},
        ),
        'raw_retrosheet.season_rosters': write_csv('raw_retrosheet.season_rosters', iter_rosters()),
        'raw_retrosheet.season_teams': write_csv(
            'raw_retrosheet.season_teams',
            iter_season_teams(),
        ),
        'raw_retrosheet.season_schedules': write_csv(
            'raw_retrosheet.season_schedules',
            iter_schedules(),
        ),
        'raw_retrosheet.season_umpires': write_csv('raw_retrosheet.season_umpires', iter_umpires()),
        'raw_retrosheet.special_gamelog_lines': write_csv(
            'raw_retrosheet.special_gamelog_lines',
            iter_special_gamelogs(),
        ),
    }

    conn = psycopg2.connect(**database_kwargs())
    try:
        for table, path in csv_paths.items():
            copy_csv(conn, table, path)
            print(f'loaded {table} from {path}')
    finally:
        conn.close()
        for path in csv_paths.values():
            path.unlink(missing_ok=True)

    run_psql(file_path=SQL_PATH)


if __name__ == '__main__':
    main()
