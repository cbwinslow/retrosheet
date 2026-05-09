"""Baseball CLI entry point using Typer.

Unified CLI that wraps and extends mlb_predict functionality.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
Usage: baseball [command]
"""

import importlib
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    help='Baseball data ingestion and prediction platform',
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main(
    verbose: bool = typer.Option(False, '--verbose', '-v', help='Enable verbose output'),
):
    """Baseball data ingestion and prediction platform."""
    if verbose:
        console.print('[dim]Verbose mode enabled[/dim]')


@app.command()
def doctor():
    """Check system health and configuration."""
    console.print('\n[bold blue]Baseball CLI Doctor[/bold blue]\n')

    checks = []

    # Check database connection
    try:
        import psycopg2

        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='retrosheet',
        )
        checks.append(('Database Connection', '✅ OK', 'green'))
        conn.close()
    except Exception as e:
        checks.append(('Database Connection', f'⚠️ {e}', 'yellow'))

    # Check directories
    for dir_name, path in [('Data', 'data'), ('SQL', 'sql'), ('Models', 'models')]:
        p = Path(path)
        if p.exists():
            checks.append((f'{dir_name} Directory', f'✅ OK ({path})', 'green'))
        else:
            checks.append((f'{dir_name} Directory', f'⚠️ Missing ({path})', 'yellow'))

    # Display results
    table = Table(show_header=True, header_style='bold magenta')
    table.add_column('Component')
    table.add_column('Status')

    for component, status, color in checks:
        table.add_row(component, f'[{color}]{status}[/{color}]')

    console.print(table)

    failed = [c for c in checks if '❌' in c[1]]
    if failed:
        console.print(f'\n[red]❌ {len(failed)} check(s) failed[/red]')
        sys.exit(1)
    else:
        console.print('\n[green]✅ All checks passed[/green]')


@app.command()
def status():
    """Show system status and recent activity."""
    console.print('\n[bold blue]Baseball Platform Status[/bold blue]\n')

    # Show recent pipeline runs
    try:
        import psycopg2

        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='retrosheet',
        )

        with conn.cursor() as cur:
            cur.execute(
                'SELECT command, status, started_at FROM admin.pipeline_runs '
                'ORDER BY started_at DESC LIMIT 5',
            )
            runs = cur.fetchall()

            if runs:
                runs_table = Table(title='Recent Pipeline Runs')
                runs_table.add_column('Command')
                runs_table.add_column('Status')
                runs_table.add_column('Started')

                for run in runs:
                    status_color = 'green' if run[1] == 'completed' else 'red'
                    runs_table.add_row(
                        run[0], f'[{status_color}]{run[1]}[/{status_color}]', str(run[2])
                    )

                console.print(runs_table)
            else:
                console.print('[dim]No recent pipeline runs found[/dim]')

        conn.close()
    except Exception as e:
        console.print(f'[yellow]Could not fetch pipeline status: {e}[/yellow]')

    console.print()


@app.command()
def version():
    """Show version information."""
    from baseball import __version__

    console.print(f'\n[bold blue]Baseball Platform[/bold blue] v{__version__}\n')


# Import mlb_predict CLI commands


@app.command(name='train')
def train(config: str = typer.Option(..., '--config', '-c', help='Path to config YAML file')):
    """Train a model (wrapper for mlb-predict train)."""
    import subprocess

    result = subprocess.run(['mlb-predict', 'train', '--config', config])
    sys.exit(result.returncode)


@app.command(name='experiment')
def experiment(
    target: str = typer.Option(..., '--target', '-t', help='Target variable'),
    compare_families: list[str] = typer.Option(None, '--compare-families', help='Model families'),
):
    """Run comparison experiments (wrapper for mlb-predict experiment)."""
    import subprocess

    cmd = ['mlb-predict', 'experiment', '--target', target]
    if compare_families:
        cmd.extend(['--compare-families'] + compare_families)
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


# Register sub-apps
def _safe_add_typer(module_name: str, attr_name: str, cli_name: str, help_text: str | None = None) -> None:
    """Register a Typer sub-app while tolerating optional dependency failures."""
    try:
        module = importlib.import_module(module_name)
        sub_app = getattr(module, attr_name)
        app.add_typer(sub_app, name=cli_name, help=help_text)
    except Exception as exc:  # noqa: BLE001
        console.print(f'[yellow]Skipping "{cli_name}" commands: {exc}[/yellow]')


_safe_add_typer('baseball.cli.commands.ingest', 'retrosheet_app', 'retrosheet')
_safe_add_typer('baseball.cli.commands.ingest', 'mlb_app', 'mlb')
_safe_add_typer('baseball.cli.commands.ingest', 'statcast_app', 'statcast')
_safe_add_typer('baseball.cli.commands.ingest', 'espn_app', 'espn')
_safe_add_typer('baseball.cli.commands.ingest', 'lahman_app', 'lahman')
_safe_add_typer('baseball.cli.commands.ingest', 'fangraphs_app', 'fangraphs')
_safe_add_typer('baseball.cli.commands.ingest', 'bref_app', 'bref')
_safe_add_typer('baseball.cli.commands.ingest', 'weather_app', 'weather')
_safe_add_typer('baseball.cli.commands.ingest', 'park_app', 'park')
_safe_add_typer('baseball.cli.commands.bet', 'betting_app', 'bet')
_safe_add_typer('baseball.cli.commands.predict', 'predict_app', 'predict')
_safe_add_typer('baseball.cli.commands.live', 'live_app', 'live')
_safe_add_typer('baseball.cli.commands.models', 'models_app', 'models')
_safe_add_typer('baseball.cli.commands.features', 'features_app', 'features')
_safe_add_typer('baseball.cli.commands.bridge', 'bridge_app', 'bridge', 'Bridge/Xref workflows')
_safe_add_typer('baseball.cli.commands.bootstrap', 'bootstrap_app', 'bootstrap', 'Database bootstrap and SQL migration workflows')
_safe_add_typer('baseball.cli.commands.serve', 'serve_app', 'serve', 'Model serving and inference')
_safe_add_typer('baseball.cli.commands.cache', 'cache_app', 'cache', 'Redis cache management')
_safe_add_typer('baseball.cli.commands.train', 'train_app', 'train', 'Model training and experiments')
_safe_add_typer('baseball.cli.commands.pitch_models', 'pitch_app', 'pitch-models', 'Pitch-level model training and evaluation')
_safe_add_typer('baseball.cli.commands.monitor', 'monitor_app', 'monitor', 'Query and system monitoring')
_safe_add_typer('baseball.cli.commands.telemetry', 'telemetry_app', 'telemetry', 'Telemetry and observability')
_safe_add_typer('baseball.cli.commands.ensemble', 'ensemble_app', 'ensemble', 'Ensemble model training and management')

if __name__ == '__main__':
    app()
