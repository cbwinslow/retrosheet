"""Baseball CLI entry point using Typer.

Unified CLI that wraps and extends mlb_predict functionality.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
Usage: baseball [command]
"""

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

# Import command modules
from baseball.cli.commands.ingest import (
    retrosheet_app,
    mlb_app,
    statcast_app,
    espn_app,
    lahman_app,
    fangraphs_app,
    bref_app,
    weather_app,
    park_app,
)
from baseball.cli.commands.bet import betting_app
from baseball.cli.commands.predict import predict_app, live_app
from baseball.cli.commands.models import models_app
from baseball.cli.commands.features import features_app
from baseball.cli.commands.chatbot import chatbot_app
from baseball.cli.commands.bridge import bridge_app

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
app.add_typer(retrosheet_app, name='retrosheet')
app.add_typer(mlb_app, name='mlb')
app.add_typer(statcast_app, name='statcast')
app.add_typer(espn_app, name='espn')
app.add_typer(lahman_app, name='lahman')
app.add_typer(fangraphs_app, name='fangraphs')
app.add_typer(bref_app, name='bref')
app.add_typer(weather_app, name='weather')
app.add_typer(park_app, name='park')
app.add_typer(betting_app, name='bet')
app.add_typer(predict_app, name='predict')
app.add_typer(live_app, name='live')
app.add_typer(models_app, name='models')
app.add_typer(features_app, name='features')
app.add_typer(chatbot_app, name='chatbot')
app.add_typer(bridge_app, name='bridge')


if __name__ == '__main__':
    app()
