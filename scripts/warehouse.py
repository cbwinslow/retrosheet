#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
RETROSHEET_REPO = DATA / 'raw' / 'retrosheet'
PROCESSED_RETROSHEET = DATA / 'processed' / 'retrosheet'
EVENT_OUT = PROCESSED_RETROSHEET / 'chadwick_event'
RETROSHEET_GIT_URL = 'https://github.com/chadwickbureau/retrosheet.git'
MLB_LIVE_ENDPOINT = 'https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live'
EVENT_COLUMNS = [f'c{i:03d}' for i in range(1, 161)]
CHADWICK_EVENT_COLUMNS_PATH = ROOT / 'config' / 'chadwick_event_columns.txt'
CHADWICK_OUTPUTS = {
    'events': {
        'tool': 'cwevent',
        'table': 'chadwick_events',
        'out_dir': EVENT_OUT,
        'args': ['-f', '0-96', '-x', '0-62'],
    },
    'games': {
        'tool': 'cwgame',
        'table': 'chadwick_games',
        'out_dir': PROCESSED_RETROSHEET / 'chadwick_game',
        # Mirrors Boxball: base game fields plus extended game/team/umpire/manager fields.
        'args': ['-f', '0-83', '-x', '0-94'],
    },
    'daily': {
        'tool': 'cwdaily',
        'table': 'chadwick_daily',
        'out_dir': PROCESSED_RETROSHEET / 'chadwick_daily',
        'args': [],
    },
    'substitutions': {
        'tool': 'cwsub',
        'table': 'chadwick_substitutions',
        'out_dir': PROCESSED_RETROSHEET / 'chadwick_substitution',
        'args': [],
    },
    'comments': {
        'tool': 'cwcomment',
        'table': 'chadwick_comments',
        'out_dir': PROCESSED_RETROSHEET / 'chadwick_comment',
        'args': [],
    },
}


def run(cmd: list[str], *, cwd: Path | None = None, stdout=None) -> None:
    print('+ ' + ' '.join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True, stdout=stdout)


def psql_base_args() -> list[str]:
    args = ['psql', '-v', 'ON_ERROR_STOP=1']
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        args.append(database_url)
    elif not os.environ.get('PGDATABASE'):
        args.extend(['-h', os.environ.get('PGHOST', 'localhost')])
        args.extend(['-p', os.environ.get('PGPORT', '5432')])
        args.extend(['-d', 'retrosheet'])
    return args


def run_psql_file(path: Path) -> None:
    run([*psql_base_args(), '-f', str(path)])


def run_psql_sql(sql: str) -> None:
    with tempfile.NamedTemporaryFile('w', suffix='.sql', delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(sql)
    try:
        run_psql_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def chadwick_event_columns() -> list[str]:
    return [
        line.strip().lower()
        for line in CHADWICK_EVENT_COLUMNS_PATH.read_text().splitlines()
        if line.strip()
    ]


def normalize_column_name(value: str) -> str:
    cleaned = []
    previous_underscore = False
    for char in value.strip().lower():
        if char.isalnum():
            cleaned.append(char)
            previous_underscore = False
        else:
            if not previous_underscore:
                cleaned.append('_')
                previous_underscore = True
    name = ''.join(cleaned).strip('_')
    if not name:
        name = 'column'
    if name[0].isdigit():
        name = f'_{name}'
    return name


def unique_names(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    output = []
    for name in names:
        count = seen.get(name, 0)
        seen[name] = count + 1
        output.append(name if count == 0 else f'{name}_{count + 1}')
    return output


def parse_years(value: str) -> list[int]:
    if '-' in value:
        start, end = value.split('-', 1)
        return list(range(int(start), int(end) + 1))
    return [int(part) for part in value.split(',') if part.strip()]


def check_deps(_: argparse.Namespace) -> None:
    deps = ['psql', 'git', 'cwevent', 'cwgame', 'cwdaily', 'cwsub', 'cwcomment']
    missing = [dep for dep in deps if not shutil.which(dep)]
    for dep in deps:
        status = 'ok' if dep not in missing else 'missing'
        print(f'{dep}: {status}')
    if missing:
        print(
            '\nMissing dependencies. Install Chadwick so its `cw*` tools are on PATH before extracting Retrosheet data.',
        )
        sys.exit(1)


def init_db(_: argparse.Namespace) -> None:
    """Initialize the database schema if it hasn't been set up already.

    The original implementation always executed the full init script, which
    re-creates tables and can be time-consuming.  To avoid unnecessary work we
    first check for the presence of a core table that is created by the
    ``001_init.sql`` migration (e.g., ``core.games``).  If the table exists we
    assume the database has already been initialized and skip the heavy
    operations.  This makes the command safe to run repeatedly during
    development.
    """
    # Quick existence check using a lightweight SELECT.  If the query fails
    # (e.g., table does not exist) we fall back to running the full init.
    try:
        run_psql_sql('SELECT 1 FROM core.games LIMIT 1;')
        # Table exists - skip re-initialization but still ensure the labeled
        # events table is present (it may be added in later revisions).
        ensure_labeled_events_table()
    except Exception:
        # Table missing - run the full init script.
        run_psql_file(ROOT / 'sql' / '001_init.sql')
        ensure_labeled_events_table()


def ensure_labeled_events_table() -> None:
    feature_columns = chadwick_event_columns()
    column_sql = ',\n    '.join(f'{column} text' for column in feature_columns)
    run_psql_sql(
        f"""
CREATE TABLE IF NOT EXISTS raw_retrosheet.chadwick_events (
    season integer NOT NULL,
    source_type text NOT NULL,
    row_number integer NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    {column_sql},
    PRIMARY KEY (season, source_type, row_number)
);

CREATE INDEX IF NOT EXISTS chadwick_events_game_idx
    ON raw_retrosheet.chadwick_events (game_id);

CREATE INDEX IF NOT EXISTS chadwick_events_event_idx
    ON raw_retrosheet.chadwick_events (season, game_id, event_id);

DROP VIEW IF EXISTS core.retrosheet_event_state_seed;

CREATE OR REPLACE VIEW core.retrosheet_event_state_seed AS
SELECT
    season,
    source_type,
    row_number,
    game_id,
    NULLIF(event_id, '')::integer AS event_id,
    NULLIF(inn_ct, '')::integer AS inning,
    bat_home_id AS batting_team_flag,
    bat_id AS batter_retrosheet_id,
    bat_hand_cd AS batter_hand,
    pit_id AS pitcher_retrosheet_id,
    pit_hand_cd AS pitcher_hand,
    event_tx AS event_text,
    NULLIF(event_outs_ct, '')::integer AS outs_on_play,
    NULLIF(event_runs_ct, '')::integer AS runs_on_play,
    NULLIF(start_bases_cd, '')::integer AS start_bases,
    NULLIF(end_bases_cd, '')::integer AS end_bases,
    loaded_at
FROM raw_retrosheet.chadwick_events;
""",
    )


def fetch_retrosheet(_: argparse.Namespace) -> None:
    RETROSHEET_REPO.parent.mkdir(parents=True, exist_ok=True)
    if (RETROSHEET_REPO / '.git').exists():
        run(['git', 'pull', '--ff-only'], cwd=RETROSHEET_REPO)
    else:
        run(['git', 'clone', '--depth', '1', RETROSHEET_GIT_URL, str(RETROSHEET_REPO)])


def year_source_files(year: int, *, include_boxscore: bool = False) -> dict[str, list[Path]]:
    season_dir = RETROSHEET_REPO / 'seasons' / str(year)
    if not season_dir.exists():
        return {}

    groups = {'regular': [], 'postseason': [], 'allstar': [], 'deduced': [], 'boxscore': []}
    for file in sorted(season_dir.glob(f'{year}*.E*')):
        # Chadwick's cwevent is for event-style play-by-play files. EB files are
        # box-score event files and will get their own loader later.
        suffix = file.suffix.upper()
        if suffix.startswith('.EB') and not include_boxscore:
            continue
        if suffix.startswith('.ED'):
            groups['deduced'].append(file)
        elif suffix.startswith('.EB'):
            groups['boxscore'].append(file)
        elif file.name.startswith(f'{year}AS.'):
            groups['allstar'].append(file)
        elif len(file.stem) > 7:
            groups['postseason'].append(file)
        else:
            groups['regular'].append(file)

    return {source_type: files for source_type, files in groups.items() if files}


def extract_events(args: argparse.Namespace) -> None:
    if not (RETROSHEET_REPO / '.git').exists():
        raise SystemExit(
            'Retrosheet data is missing. Run `python3 scripts/warehouse.py fetch-retrosheet` first.',
        )
    if not shutil.which('cwevent'):
        raise SystemExit('`cwevent` is missing. Install Chadwick tools before extracting events.')

    EVENT_OUT.mkdir(parents=True, exist_ok=True)
    for year in parse_years(args.years):
        season_dir = RETROSHEET_REPO / 'seasons' / str(year)
        team_files = sorted(season_dir.glob('TEAM*'))
        for source_type, files in year_source_files(year).items():
            out_file = EVENT_OUT / f'{year}_{source_type}.csv'
            with tempfile.TemporaryDirectory(prefix=f'retrosheet-{year}-{source_type}-') as tmp:
                tmp_dir = Path(tmp)
                for file in files:
                    shutil.copy2(file, tmp_dir / file.name)
                for file in team_files:
                    shutil.copy2(file, tmp_dir / file.name)
                command = ['cwevent', '-q', '-n', '-y', str(year), '-f', '0-96', '-x', '0-62']
                command.extend(file.name for file in files)
                with out_file.open('w', newline='') as fout:
                    run(command, cwd=tmp_dir, stdout=fout)
            print(f'wrote {out_file}')


def extract_chadwick(args: argparse.Namespace) -> None:
    outputs = selected_outputs(args.outputs)
    for output in outputs:
        extract_chadwick_output(output, parse_years(args.years))


def selected_outputs(value: str) -> list[str]:
    if value == 'all':
        return list(CHADWICK_OUTPUTS.keys())
    outputs = [part.strip() for part in value.split(',') if part.strip()]
    unknown = sorted(set(outputs) - set(CHADWICK_OUTPUTS))
    if unknown:
        raise SystemExit(f"Unknown Chadwick output(s): {', '.join(unknown)}")
    return outputs


def extract_chadwick_output(output: str, years: list[int]) -> None:
    spec = CHADWICK_OUTPUTS[output]
    tool = str(spec['tool'])
    if not (RETROSHEET_REPO / '.git').exists():
        raise SystemExit(
            'Retrosheet data is missing. Run `python3 scripts/warehouse.py fetch-retrosheet` first.',
        )
    if not shutil.which(tool):
        raise SystemExit(f'`{tool}` is missing. Install Chadwick tools before extracting {output}.')

    out_dir = Path(spec['out_dir'])
    out_dir.mkdir(parents=True, exist_ok=True)
    for year in years:
        season_dir = RETROSHEET_REPO / 'seasons' / str(year)
        team_files = sorted(season_dir.glob('TEAM*'))
        for source_type, files in year_source_files(year).items():
            out_file = out_dir / f'{year}_{source_type}.csv'
            with tempfile.TemporaryDirectory(
                prefix=f'retrosheet-{output}-{year}-{source_type}-',
            ) as tmp:
                tmp_dir = Path(tmp)
                for file in files:
                    shutil.copy2(file, tmp_dir / file.name)
                for file in team_files:
                    shutil.copy2(file, tmp_dir / file.name)
                command = [tool, '-q', '-n', '-y', str(year), *list(spec['args'])]
                command.extend(file.name for file in files)
                with out_file.open('w', newline='') as fout:
                    run(command, cwd=tmp_dir, stdout=fout)
            print(f'wrote {out_file}')


def load_events(args: argparse.Namespace) -> None:
    init_sql = ROOT / 'sql' / '001_init.sql'
    run_psql_file(init_sql)
    for year in parse_years(args.years):
        for source_type in ('regular', 'postseason', 'allstar', 'deduced'):
            file = EVENT_OUT / f'{year}_{source_type}.csv'
            if file.exists():
                load_event_file(file, year, source_type)


def load_labeled_events(args: argparse.Namespace) -> None:
    init_db(argparse.Namespace())
    for year in parse_years(args.years):
        for source_type in ('regular', 'postseason', 'allstar', 'deduced'):
            file = EVENT_OUT / f'{year}_{source_type}.csv'
            if file.exists():
                load_labeled_event_file(file, year, source_type)


def load_chadwick(args: argparse.Namespace) -> None:
    init_db(argparse.Namespace())
    for output in selected_outputs(args.outputs):
        if output == 'events':
            for year in parse_years(args.years):
                for source_type in ('regular', 'postseason', 'allstar', 'deduced'):
                    file = Path(CHADWICK_OUTPUTS['events']['out_dir']) / f'{year}_{source_type}.csv'
                    if file.exists():
                        load_labeled_event_file(file, year, source_type)
            continue
        for year in parse_years(args.years):
            for source_type in ('regular', 'postseason', 'allstar', 'deduced'):
                file = Path(CHADWICK_OUTPUTS[output]['out_dir']) / f'{year}_{source_type}.csv'
                if file.exists():
                    load_chadwick_csv(output, file, year, source_type)


def load_chadwick_csv(output: str, path: Path, year: int, source_type: str) -> None:
    spec = CHADWICK_OUTPUTS[output]
    table = str(spec['table'])
    normalized = path.with_suffix('.load.csv')
    with path.open(newline='') as fin:
        reader = csv.reader(fin)
        try:
            header = next(reader)
        except StopIteration:
            print(f'skipping empty file {path}')
            return
        columns = unique_names([normalize_column_name(name) for name in header])
        with normalized.open('w', newline='') as fout:
            writer = csv.writer(fout)
            rows = 0
            for row_number, row in enumerate(reader, start=1):
                if len(row) != len(columns):
                    raise ValueError(
                        f'{path}:{row_number + 1} has {len(row)} columns; expected {len(columns)}',
                    )
                writer.writerow([year, source_type, row_number, *row])
                rows += 1

    ensure_chadwick_table(table, columns)
    load_columns = ['season', 'source_type', 'row_number', *columns]
    temp_columns = [
        'season integer',
        'source_type text',
        'row_number integer',
        *[f'{column} text' for column in columns],
    ]
    run_psql_sql(
        "\\set ON_ERROR_STOP on\n"
        "BEGIN;\n"
        f"CREATE TEMP TABLE {table}_load ({', '.join(temp_columns)});\n"
        f"\\copy {table}_load ({', '.join(load_columns)}) FROM '{normalized}' WITH (FORMAT csv, NULL '')\n"
        f"DELETE FROM raw_retrosheet.{table} "
        f"WHERE season = {year} AND source_type = '{source_type}';\n"
        f"INSERT INTO raw_retrosheet.{table} "
        f"({', '.join(load_columns)}) SELECT {', '.join(load_columns)} FROM {table}_load;\n"
        "COMMIT;\n",
    )
    normalized.unlink(missing_ok=True)
    print(f'loaded {rows} {output} rows from {path}')


def ensure_chadwick_table(table: str, columns: list[str]) -> None:
    column_sql = ',\n    '.join(f'{column} text' for column in columns)
    index_sql = ''
    if 'game_id' in columns:
        index_sql += (
            f'\nCREATE INDEX IF NOT EXISTS {table}_game_idx ON raw_retrosheet.{table} (game_id);\n'
        )
    if 'player_id' in columns:
        index_sql += f'\nCREATE INDEX IF NOT EXISTS {table}_player_idx ON raw_retrosheet.{table} (player_id);\n'
    run_psql_sql(
        f"""
CREATE TABLE IF NOT EXISTS raw_retrosheet.{table} (
    season integer NOT NULL,
    source_type text NOT NULL,
    row_number integer NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    {column_sql},
    PRIMARY KEY (season, source_type, row_number)
);
{index_sql}
""",
    )


def load_labeled_event_file(path: Path, year: int, source_type: str) -> None:
    feature_columns = chadwick_event_columns()
    normalized = path.with_suffix('.labeled.load.csv')
    rows = 0
    with path.open(newline='') as fin, normalized.open('w', newline='') as fout:
        reader = csv.reader(fin)
        writer = csv.writer(fout)
        rows = 0
        for input_row_number, row in enumerate(reader, start=1):
            if (
                input_row_number == 1
                and [normalize_column_name(value) for value in row] == feature_columns
            ):
                continue
            if len(row) != len(feature_columns):
                raise ValueError(
                    f'{path}:{input_row_number} has {len(row)} columns; expected {len(feature_columns)}',
                )
            row_number = rows + 1
            writer.writerow([year, source_type, row_number, *row])
            rows += 1

    load_columns = ['season', 'source_type', 'row_number', *feature_columns]
    temp_columns = [
        'season integer',
        'source_type text',
        'row_number integer',
        *[f'{column} text' for column in feature_columns],
    ]
    run_psql_sql(
        "\\set ON_ERROR_STOP on\n"
        "BEGIN;\n"
        f"CREATE TEMP TABLE labeled_event_load ({', '.join(temp_columns)});\n"
        f"\\copy labeled_event_load ({', '.join(load_columns)}) FROM '{normalized}' WITH (FORMAT csv, NULL '')\n"
        "DELETE FROM raw_retrosheet.chadwick_events "
        f"WHERE season = {year} AND source_type = '{source_type}';\n"
        "INSERT INTO raw_retrosheet.chadwick_events "
        f"({', '.join(load_columns)}) SELECT {', '.join(load_columns)} FROM labeled_event_load;\n"
        "COMMIT;\n",
    )
    normalized.unlink(missing_ok=True)
    print(f'loaded {rows} labeled rows from {path}')


def load_event_file(path: Path, year: int, source_type: str) -> None:
    normalized = path.with_suffix('.load.csv')
    rows = 0
    with path.open(newline='') as fin, normalized.open('w', newline='') as fout:
        reader = csv.reader(fin)
        writer = csv.writer(fout)
        for row_number, row in enumerate(reader, start=1):
            padded = (row + [''] * len(EVENT_COLUMNS))[: len(EVENT_COLUMNS)]
            game_id = padded[0] or None
            event_id = padded[96] if len(padded) > 96 else ''
            writer.writerow([year, source_type, row_number, game_id, event_id, *padded])
            rows += 1

    columns = ['season', 'source_type', 'row_number', 'game_id', 'event_id', *EVENT_COLUMNS]
    with tempfile.NamedTemporaryFile('w', suffix='.sql', delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write('\\set ON_ERROR_STOP on\n')
        tmp.write('BEGIN;\n')
        tmp.write(
            'CREATE TEMP TABLE event_load ('
            'season integer, source_type text, row_number integer, game_id text, event_id integer, '
            + ', '.join(f'{column} text' for column in EVENT_COLUMNS)
            + ');\n',
        )
        tmp.write(
            f"\\copy event_load ({', '.join(columns)}) FROM '{normalized}' WITH (FORMAT csv, NULL '')\n",
        )
        tmp.write(
            "DELETE FROM raw_retrosheet.chadwick_event_raw "
            f"WHERE season = {year} AND source_type = '{source_type}';\n",
        )
        tmp.write(
            "INSERT INTO raw_retrosheet.chadwick_event_raw "
            f"({', '.join(columns)}) SELECT {', '.join(columns)} FROM event_load;\n",
        )
        tmp.write('COMMIT;\n')

    try:
        run_psql_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
        normalized.unlink(missing_ok=True)
    print(f'loaded {rows} rows from {path}')


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def fetch_live_game(args: argparse.Namespace) -> None:
    run_psql_file(ROOT / 'sql' / '001_init.sql')
    endpoint = MLB_LIVE_ENDPOINT.format(game_pk=args.game_pk)
    print(f'fetching {endpoint}')
    with urllib.request.urlopen(endpoint, timeout=30) as response:
        http_status = response.status
        payload = json.loads(response.read().decode('utf-8'))
    payload_json = json.dumps(payload, separators=(',', ':'))
    game_data = payload.get('gameData', {})
    request_params = {'game_pk': int(args.game_pk)}
    payload_checksum = hashlib.sha256(payload_json.encode('utf-8')).hexdigest()
    game_date = (game_data.get('datetime', {}).get('originalDate') or '')[:10] or None
    season = game_data.get('game', {}).get('season')
    with tempfile.NamedTemporaryFile('w', suffix='.sql', delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(
            'INSERT INTO raw_mlb.live_feed_snapshots '
            '(game_pk, endpoint, payload, request_params, http_status, payload_checksum, game_date, season) VALUES (\n',
        )
        tmp.write(f'  {int(args.game_pk)},\n')
        tmp.write(f'  {sql_literal(endpoint)},\n')
        tmp.write(f'  {sql_literal(payload_json)}::jsonb,\n')
        tmp.write(f"  {sql_literal(json.dumps(request_params, separators=(',', ':')))}::jsonb,\n")
        tmp.write(f'  {http_status},\n')
        tmp.write(f'  {sql_literal(payload_checksum)},\n')
        tmp.write('  ' + ('NULL' if not game_date else sql_literal(game_date)) + ',\n')
        tmp.write('  ' + ('NULL' if not season else str(int(season))) + '\n')
        tmp.write(');\n')
    try:
        run_psql_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Retrosheet/Postgres warehouse utilities')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('check-deps').set_defaults(func=check_deps)
    sub.add_parser('init-db').set_defaults(func=init_db)
    sub.add_parser('fetch-retrosheet').set_defaults(func=fetch_retrosheet)

    extract = sub.add_parser('extract-events')
    extract.add_argument(
        '--years', required=True, help='Year, comma list, or range. Example: 2023 or 2000-2025',
    )
    extract.set_defaults(func=extract_events)

    load = sub.add_parser('load-events')
    load.add_argument(
        '--years', required=True, help='Year, comma list, or range. Example: 2023 or 2000-2025',
    )
    load.set_defaults(func=load_events)

    labeled = sub.add_parser('load-labeled-events')
    labeled.add_argument(
        '--years', required=True, help='Year, comma list, or range. Example: 2023 or 2000-2025',
    )
    labeled.set_defaults(func=load_labeled_events)

    extract_chadwick_parser = sub.add_parser('extract-chadwick')
    extract_chadwick_parser.add_argument(
        '--years', required=True, help='Year, comma list, or range.',
    )
    extract_chadwick_parser.add_argument(
        '--outputs',
        default='all',
        help='Comma list of events,games,daily,substitutions,comments or all.',
    )
    extract_chadwick_parser.set_defaults(func=extract_chadwick)

    load_chadwick_parser = sub.add_parser('load-chadwick')
    load_chadwick_parser.add_argument('--years', required=True, help='Year, comma list, or range.')
    load_chadwick_parser.add_argument(
        '--outputs',
        default='all',
        help='Comma list of events,games,daily,substitutions,comments or all.',
    )
    load_chadwick_parser.set_defaults(func=load_chadwick)

    live = sub.add_parser('fetch-live-game')
    live.add_argument('--game-pk', required=True, type=int)
    live.set_defaults(func=fetch_live_game)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
