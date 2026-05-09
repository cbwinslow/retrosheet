"""Database bootstrap commands for layered SQL installation."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

import os
import psycopg2

bootstrap_app = typer.Typer(help='Database bootstrap and SQL migration commands', no_args_is_help=True)
console = Console()

SQL_LAYER_DIRS = [
    '00_admin',
    '10_raw',
    '20_staging',
    '30_core',
    '40_bridge',
    '50_features',
    '60_models',
    'maintenance',
]


def _collect_sql_files(sql_root: Path, include_maintenance: bool) -> list[Path]:
    layers = SQL_LAYER_DIRS if include_maintenance else [layer for layer in SQL_LAYER_DIRS if layer != 'maintenance']
    files: list[Path] = []
    for layer in layers:
        layer_path = sql_root / layer
        if not layer_path.exists():
            continue
        files.extend(sorted(layer_path.glob('*.sql')))
    return files


def _get_database_url() -> str:
    return os.getenv(
        'DATABASE_URL',
        f'postgresql://{os.getenv("PGUSER", "retrosheet")}:{os.getenv("PGPASSWORD", "")}@{os.getenv("PGHOST", "localhost")}:{os.getenv("PGPORT", "5432")}/{os.getenv("PGDATABASE", "retrosheet")}',
    )


@bootstrap_app.command('plan')
def bootstrap_plan(
    sql_root: Path = typer.Option(Path('sql'), '--sql-root', help='Root directory containing layered SQL folders'),
    include_maintenance: bool = typer.Option(False, '--include-maintenance', help='Include sql/maintenance scripts'),
) -> None:
    """Show the SQL bootstrap execution plan."""
    files = _collect_sql_files(sql_root, include_maintenance)
    if not files:
        console.print(f'[yellow]No SQL files found under {sql_root}[/yellow]')
        raise typer.Exit(code=1)

    console.print(f'[bold]Bootstrap plan:[/bold] {len(files)} SQL files')
    for sql_file in files:
        console.print(f' - {sql_file}')


@bootstrap_app.command('run')
def bootstrap_run(
    sql_root: Path = typer.Option(Path('sql'), '--sql-root', help='Root directory containing layered SQL folders'),
    include_maintenance: bool = typer.Option(False, '--include-maintenance', help='Include sql/maintenance scripts'),
    dry_run: bool = typer.Option(False, '--dry-run', help='Print plan but do not execute SQL'),
    stop_on_error: bool = typer.Option(True, '--stop-on-error/--continue-on-error', help='Stop at first SQL failure'),
) -> None:
    """Execute layered SQL bootstrap against the configured database."""
    files = _collect_sql_files(sql_root, include_maintenance)
    if not files:
        console.print(f'[yellow]No SQL files found under {sql_root}[/yellow]')
        raise typer.Exit(code=1)

    if dry_run:
        console.print('[blue]Dry run enabled: no SQL will be executed.[/blue]')
        for sql_file in files:
            console.print(f' - {sql_file}')
        return

    try:
        conn = psycopg2.connect(_get_database_url())
    except Exception:
        console.print('[red]Database connection failed. Set DATABASE_URL/PG* environment variables.[/red]')
        raise typer.Exit(code=1)

    executed = 0
    failures: list[tuple[Path, str]] = []

    try:
        with conn:
            with conn.cursor() as cur:
                for sql_file in files:
                    sql_text = sql_file.read_text(encoding='utf-8')
                    try:
                        cur.execute(sql_text)
                        executed += 1
                        console.print(f'[green]Executed[/green] {sql_file}')
                    except Exception as exc:  # noqa: BLE001
                        conn.rollback()
                        failures.append((sql_file, str(exc)))
                        console.print(f'[red]Failed[/red] {sql_file}: {exc}')
                        if stop_on_error:
                            raise
        if failures:
            raise RuntimeError(f'{len(failures)} SQL file(s) failed')
    except Exception:
        conn.close()
        raise typer.Exit(code=1)

    conn.close()
    console.print(f'[bold green]Bootstrap complete.[/bold green] Executed {executed} SQL files.')
