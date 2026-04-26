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


# Import from existing mlb_predict infrastructure


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
                    runs_table.add_row(run[0], f'[{status_color}]{run[1]}[/{status_color}]', str(run[2]))

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


# Data source command groups
retrosheet_app = typer.Typer(help='Retrosheet historical data commands', no_args_is_help=True)
mlb_app = typer.Typer(help='MLB live data commands', no_args_is_help=True)
features_app = typer.Typer(help='Feature engineering commands', no_args_is_help=True)
models_app = typer.Typer(help='ML model commands', no_args_is_help=True)
chatbot_app = typer.Typer(help='Natural language chatbot interface', no_args_is_help=True)


# Chatbot commands


@chatbot_app.command(name='chat')
def chatbot_chat(
    message: str = typer.Option(None, '--message', '-m', help='Single message to send'),
    interactive: bool = typer.Option(False, '--interactive', '-i', help='Interactive chat mode'),
):
    """Chat with the baseball prediction bot."""
    try:
        from baseball.chatbot import Chatbot
    except ImportError as e:
        console.print(f'[red]Chatbot module not available: {e}[/red]')
        raise typer.Exit(code=1)

    bot = Chatbot()

    if message:
        # Single message mode
        response = bot.chat(message)
        console.print(f'[cyan]You:[/cyan] {message}')
        console.print(f'[green]Bot:[/green] {response}')
    elif interactive:
        # Interactive mode
        console.print('[bold blue]Baseball Chatbot[/bold blue]')
        console.print('[dim]Type "help" for examples, "quit" to exit[/dim]\n')

        while True:
            try:
                user_input = console.input('[cyan]You:[/cyan] ').strip()

                if not user_input:
                    continue

                if user_input.lower() in ('quit', 'exit', 'bye'):
                    console.print('[green]Bot:[/green] Goodbye!')
                    break

                if user_input.lower() == 'help':
                    console.print('\n[bold]Example queries:[/bold]')
                    for cmd in bot.get_supported_commands():
                        console.print(f'  • {cmd}')
                    console.print()
                    continue

                response = bot.chat(user_input)
                console.print(f'[green]Bot:[/green] {response}\n')

            except KeyboardInterrupt:
                console.print('\n[yellow]Goodbye![/yellow]')
                break
    else:
        console.print('[yellow]Use --message for single query or --interactive for chat mode[/yellow]')
        console.print('[dim]Examples:[/dim]')
        console.print('  baseball chatbot chat -m "What is the Yankees win probability?"')
        console.print('  baseball chatbot chat --interactive')


@chatbot_app.command(name='demo')
def chatbot_demo():
    """Run a demo conversation with the chatbot."""
    try:
        from baseball.chatbot import Chatbot
    except ImportError as e:
        console.print(f'[red]Chatbot module not available: {e}[/red]')
        raise typer.Exit(code=1)

    bot = Chatbot()

    demo_queries = [
        "Hello!",
        "What's the Yankees win probability?",
        "How about the Red Sox?",
        "What's Aaron Judge's batting average?",
        "Who's pitching for the Dodgers?",
        "How do predictions work?",
        "Thanks, bye!",
    ]

    console.print('[bold blue]Chatbot Demo[/bold blue]\n')

    for query in demo_queries:
        console.print(f'[cyan]You:[/cyan] {query}')
        response = bot.chat(query)
        console.print(f'[green]Bot:[/green] {response}\n')

    # Show conversation summary
    summary = bot.get_conversation_summary()
    console.print('[dim]Conversation summary:[/dim]')
    console.print(f"  Messages: {summary['session_info']['message_count']}")
    console.print(f"  Active team: {summary['context']['team'] or 'None'}")
    console.print(f"  Active player: {summary['context']['player'] or 'None'}")


# MLB data ingestion commands
@mlb_app.command(name='download')
def mlb_download(
    date_str: str = typer.Option(None, '--date', '-d', help='Date to download (YYYY-MM-DD, default: today)'),
    season: int = typer.Option(None, '--season', '-s', help='Download full season'),
    game_pk: int = typer.Option(None, '--game', '-g', help='Specific game ID'),
    force: bool = typer.Option(False, '--force', '-f', help='Force re-download'),
):
    """Download MLB data from Stats API."""
    from datetime import date as dt_date

    from mlb_predict.sources import MlbSource

    source = MlbSource()

    if game_pk:
        result = source.download(game_pks=[game_pk], force=force)
    elif season:
        result = source.fetch_season(season)
    else:
        target_date = dt_date.today() if date_str is None else dt_date.fromisoformat(date_str)
        result = source.download(start_date=target_date, end_date=target_date, force=force)

    if result.success:
        console.print(f'[green]Downloaded {result.rows_downloaded} items[/green]')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@mlb_app.command(name='ingest')
def mlb_ingest(
    validate: bool = typer.Option(True, '--validate', help='Validate after ingest'),
):
    """Ingest downloaded MLB data into database."""
    from mlb_predict.sources import MlbSource

    source = MlbSource()
    result = source.ingest(validate=validate)

    if result.success:
        console.print(f'[green]Ingested {result.rows_inserted} rows[/green]')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@mlb_app.command(name='validate')
def mlb_validate():
    """Validate MLB data quality."""
    from mlb_predict.sources import MlbSource

    source = MlbSource()
    result = source.validate()

    if result.success:
        console.print(f'[green]Validation passed ({len(result.issues)} issues)[/green]')
    else:
        console.print(f'[red]Validation failed: {result.error_count} errors[/red]')
        raise typer.Exit(code=1)


@mlb_app.command(name='today')
def mlb_today(
    download: bool = typer.Option(True, '--download/--no-download', help="Download today's data"),
    predict: bool = typer.Option(False, '--predict', '-p', help='Run predictions after download'),
):
    """Fetch and process today's MLB data."""
    from mlb_predict.sources import MlbSource

    source = MlbSource()

    if download:
        result = source.fetch_today()
        console.print(f'[dim]Downloaded {result.rows_downloaded} games[/dim]')

    # TODO: Add prediction workflow
    if predict:
        console.print('[dim]Running predictions...[/dim]')

    console.print("[green]Today's MLB data ready[/green]")


# Retrosheet data ingestion commands
@retrosheet_app.command(name='download')
def retrosheet_download(
    year: int = typer.Option(None, '--year', '-y', help='Specific year to download'),
    start_year: int = typer.Option(1916, '--start', help='Start year (default: 1916)'),
    end_year: int = typer.Option(None, '--end', help='End year (default: current)'),
    force: bool = typer.Option(False, '--force', '-f', help='Force re-download'),
):
    """Download Retrosheet event files."""
    from datetime import date as dt_date

    from mlb_predict.sources import RetrosheetSource

    source = RetrosheetSource()

    if year:
        start = dt_date(year, 1, 1)
        end = dt_date(year, 12, 31)
    else:
        end_year = end_year or dt_date.today().year
        start = dt_date(start_year, 1, 1)
        end = dt_date(end_year, 12, 31)

    result = source.download(start_date=start, end_date=end, force=force)

    if result.success:
        console.print(f'[green]Downloaded {result.rows_downloaded} seasons[/green]')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@retrosheet_app.command(name='ingest')
def retrosheet_ingest(
    validate: bool = typer.Option(True, '--validate', help='Validate after ingest'),
):
    """Ingest Retrosheet data using Chadwick tools."""
    from mlb_predict.sources import RetrosheetSource

    source = RetrosheetSource()
    result = source.ingest(validate=validate)

    if result.success:
        console.print('[green]Ingestion complete[/green]')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@retrosheet_app.command(name='validate')
def retrosheet_validate():
    """Validate Retrosheet data quality."""
    from mlb_predict.sources import RetrosheetSource

    source = RetrosheetSource()
    result = source.validate()

    if result.success:
        console.print(f'[green]Validation passed ({len(result.issues)} issues)[/green]')
    else:
        console.print(f'[red]Validation failed: {result.error_count} errors[/red]')
        raise typer.Exit(code=1)


@retrosheet_app.command(name='seasons')
def retrosheet_seasons():
    """List available seasons in Retrosheet."""
    from mlb_predict.sources import RetrosheetSource

    source = RetrosheetSource()
    seasons = source.get_seasons_available()

    console.print(f'[bold]Available seasons:[/bold] {len(seasons)} total')
    console.print(f'Range: {min(seasons)} - {max(seasons)}')
    console.print(f"Recent: {', '.join(str(s) for s in seasons[-5:])}")


# Predict command group
predict_app = typer.Typer(help='Run prediction workflows', no_args_is_help=True)


@predict_app.command(name='game')
def predict_game(
    game_pk: int = typer.Option(..., '--game', '-g', help='MLB game ID'),
    model: str = typer.Option(..., '--model', '-m', help='Model name or path'),
    output: str = typer.Option('table', '--output', '-o', help='Output format: table, json, csv'),
):
    """Run predictions for a specific game."""
    console.print(f'[dim]Predicting game {game_pk} using model {model}...[/dim]')
    # TODO: Load game state, run feature pipeline, predict
    raise typer.Exit(code=0)


@predict_app.command(name='today')
def predict_today(
    model: str = typer.Option(..., '--model', '-m', help='Model name or path'),
    output: str = typer.Option('table', '--output', '-o', help='Output format'),
):
    """Run predictions for all games today."""
    console.print("[dim]Fetching today's games and running predictions...[/dim]")
    # TODO: Fetch today's schedule, run batch predictions
    raise typer.Exit(code=0)


@predict_app.command(name='live')
def predict_live(
    model: str = typer.Option(..., '--model', '-m', help='Model name or path'),
    interval: int = typer.Option(30, '--interval', '-i', help='Polling interval in seconds'),
):
    """Run continuous live predictions."""
    console.print(f'[dim]Starting live prediction loop (interval: {interval}s)...[/dim]')
    # TODO: Poll MLB API, predict when game state changes, display results
    raise typer.Exit(code=0)


@predict_app.command(name='batch')
def predict_batch(
    games_file: Path = typer.Option(..., '--games', '-g', help='File with game IDs (one per line)'),
    model: str = typer.Option(..., '--model', '-m', help='Model name or path'),
    output: Path = typer.Option(None, '--output', '-o', help='Output file path'),
):
    """Run predictions for a batch of games."""
    console.print(f'[dim]Processing {games_file} with model {model}...[/dim]')
    # TODO: Read game IDs, fetch states, batch predict, write output
    raise typer.Exit(code=0)


# Models command group
@models_app.command(name='list')
def models_list(
    show_archived: bool = typer.Option(False, '--archived', help='Include archived models'),
):
    """List available models in the registry."""
    table = Table(title='Available Models')
    table.add_column('Name')
    table.add_column('Family')
    table.add_column('Target')
    table.add_column('Trained')
    table.add_column('Status')

    # TODO: Query model registry
    console.print(table)


@models_app.command(name='info')
def models_info(
    model_name: str = typer.Argument(..., help='Model name or ID'),
):
    """Show detailed info about a model."""
    console.print(f'[dim]Loading info for model: {model_name}...[/dim]')
    # TODO: Load model metadata, show config, metrics, features
    raise typer.Exit(code=0)


@models_app.command(name='download')
def models_download(
    model_name: str = typer.Argument(..., help='Model name or ID'),
    version: str = typer.Option('latest', '--version', '-v', help='Model version'),
    output: Path = typer.Option(None, '--output', '-o', help='Download path'),
):
    """Download a model from the registry."""
    console.print(f'[dim]Downloading {model_name}@{version}...[/dim]')
    # TODO: Fetch model artifact, save to output or models/
    raise typer.Exit(code=0)


@models_app.command(name='archive')
def models_archive(
    model_name: str = typer.Argument(..., help='Model name or ID'),
    reason: str = typer.Option(None, '--reason', help='Reason for archiving'),
):
    """Archive a model (remove from active pool)."""
    console.print(f'[dim]Archiving model: {model_name}...[/dim]')
    # TODO: Update model status in registry
    raise typer.Exit(code=0)


@models_app.command(name='compare')
def models_compare(
    models: list[str] = typer.Argument(..., help='Model names or IDs to compare'),
    metric: str = typer.Option('logloss', '--metric', '-m', help='Metric for comparison'),
):
    """Compare multiple models on validation metrics."""
    console.print(f'[dim]Comparing {len(models)} models...[/dim]')
    # TODO: Load metrics, generate comparison table/chart
    raise typer.Exit(code=0)


@models_app.command(name='export')
def models_export(
    model_name: str = typer.Argument(..., help='Model name or ID'),
    format: str = typer.Option('onnx', '--format', '-f', help='Export format: onnx, pmml, json'),
    output: Path = typer.Option(None, '--output', '-o', help='Output path'),
):
    """Export model to external format."""
    console.print(f'[dim]Exporting {model_name} to {format}...[/dim]')
    # TODO: Convert model, save to output
    raise typer.Exit(code=0)


# Statcast command group
statcast_app = typer.Typer(help='Statcast/Baseball Savant data commands', no_args_is_help=True)


@statcast_app.command(name='download')
def statcast_download(
    season: int = typer.Option(..., '--season', '-s', help='Season to download'),
    force: bool = typer.Option(False, '--force', '-f', help='Force re-download'),
):
    """Download Statcast data for a season."""
    from mlb_predict.sources import StatcastSource

    source = StatcastSource()
    result = source.download(start_date=date(season, 1, 1), end_date=date(season, 12, 31), force=force)

    if result.success:
        console.print(f'[green]Downloaded Statcast data for {season}[/green]')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@statcast_app.command(name='ingest')
def statcast_ingest(
    validate: bool = typer.Option(True, '--validate', help='Validate after ingest'),
):
    """Ingest downloaded Statcast data."""
    from mlb_predict.sources import StatcastSource

    source = StatcastSource()
    result = source.ingest(validate=validate)

    if result.success:
        console.print(f'[green]Ingested {result.rows_inserted} rows[/green]')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@statcast_app.command(name='validate')
def statcast_validate():
    """Validate Statcast data quality."""
    from mlb_predict.sources import StatcastSource

    source = StatcastSource()
    result = source.validate()

    if result.success:
        console.print('[green]Validation passed[/green]')
    else:
        console.print(f'[red]Validation failed: {result.error_count} errors[/red]')
        raise typer.Exit(code=1)


@statcast_app.command(name='seasons')
def statcast_seasons():
    """List seasons with Statcast data (2015+)."""
    from mlb_predict.sources import StatcastSource

    source = StatcastSource()
    seasons = source.get_available_seasons()

    console.print(f'[bold]Statcast available seasons:[/bold] {len(seasons)} total')
    console.print(f'Range: {min(seasons)} - {max(seasons)}')


# ESPN command group
espn_app = typer.Typer(help='ESPN data commands', no_args_is_help=True)


@espn_app.command(name='download')
def espn_download(
    season: int = typer.Option(..., '--season', '-s', help='Season to download'),
    force: bool = typer.Option(False, '--force', '-f', help='Force re-download'),
):
    """Download ESPN schedule, boxscores, and stats."""
    from mlb_predict.sources import EspnSource

    source = EspnSource()
    result = source.download(season=season, force=force)

    if result.success:
        console.print(f'[green]Downloaded ESPN data for {season}[/green]')
        if result.metadata:
            console.print(f"  Games: {result.metadata.get('games', 'N/A')}")
            console.print(f"  Plays: {result.metadata.get('plays', 'N/A')}")
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@espn_app.command(name='ingest')
def espn_ingest(
    validate: bool = typer.Option(True, '--validate', help='Validate after ingest'),
):
    """Validate ESPN data in database."""
    from mlb_predict.sources import EspnSource

    source = EspnSource()
    result = source.ingest(validate=validate)

    if result.success:
        console.print('[green]ESPN data validated[/green]')
        if result.metadata and 'table_counts' in result.metadata:
            for table, count in result.metadata['table_counts'].items():
                console.print(f'  {table}: {count} rows')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@espn_app.command(name='validate')
def espn_validate():
    """Validate ESPN data quality."""
    from mlb_predict.sources import EspnSource

    source = EspnSource()
    result = source.validate()

    if result.success:
        console.print('[green]ESPN validation passed[/green]')
    else:
        console.print(f'[red]ESPN validation failed: {result.error_count} errors[/red]')
        if result.issues:
            for issue in result.issues:
                console.print(f'  - {issue}')
        raise typer.Exit(code=1)


@espn_app.command(name='seasons')
def espn_seasons():
    """List seasons with ESPN data (2005+)."""
    from mlb_predict.sources import EspnSource

    source = EspnSource()
    seasons = source.get_available_seasons()

    console.print(f'[bold]ESPN available seasons:[/bold] {len(seasons)} total')
    console.print(f'Range: {min(seasons)} - {max(seasons)}')


# Lahman command group
lahman_app = typer.Typer(help='Lahman Baseball Databank commands', no_args_is_help=True)


@lahman_app.command(name='download')
def lahman_download(
    force: bool = typer.Option(False, '--force', '-f', help='Force re-download'),
):
    """Download Lahman Baseball Databank (1871-2023)."""
    from mlb_predict.sources import LahmanSource

    source = LahmanSource()
    result = source.download(force=force)

    if result.success:
        console.print('[green]Downloaded Lahman Baseball Databank[/green]')
        if result.metadata and 'files' in result.metadata:
            console.print(f"  Files: {len(result.metadata['files'])}")
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@lahman_app.command(name='ingest')
def lahman_ingest(
    validate: bool = typer.Option(True, '--validate', help='Validate after ingest'),
):
    """Ingest Lahman CSV files into database."""
    from mlb_predict.sources import LahmanSource

    source = LahmanSource()
    result = source.ingest(validate=validate)

    if result.success:
        console.print('[green]Lahman data ingested[/green]')
        if result.metadata and 'files_found' in result.metadata:
            console.print(f"  Files found: {len(result.metadata['files_found'])}")
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@lahman_app.command(name='validate')
def lahman_validate():
    """Validate Lahman data quality."""
    from mlb_predict.sources import LahmanSource

    source = LahmanSource()
    result = source.validate()

    if result.success:
        console.print('[green]Lahman validation passed[/green]')
    else:
        console.print(f'[red]Lahman validation failed: {result.error_count} errors[/red]')
        if result.issues:
            for issue in result.issues:
                console.print(f'  - {issue}')
        raise typer.Exit(code=1)


@lahman_app.command(name='tables')
def lahman_tables():
    """Show Lahman table row counts."""
    from mlb_predict.sources import LahmanSource

    source = LahmanSource()
    counts = source.get_table_counts()

    console.print('[bold]Lahman Databank Tables:[/bold]')
    for table, count in counts.items():
        if table != 'error':
            console.print(f'  {table}: {count:,} rows')


# Live command group
live_app = typer.Typer(help='Live MLB game tracking and real-time predictions', no_args_is_help=True)


@live_app.command(name='games')
def live_games(
    active: bool = typer.Option(True, '--active/--all', help='Show only active games'),
):
    """Show currently live MLB games."""
    from mlb_predict.sources import LiveMlbSource

    source = LiveMlbSource()
    games = source.get_active_games()

    if not games:
        console.print('[yellow]No live games found[/yellow]')
        return

    console.print(f'[bold]Live Games ({len(games)}):[/bold]\n')
    for g in games:
        status_icon = '🔴' if g.is_in_progress else '⚫'
        inning_str = f"{'Top' if g.is_top else 'Bot'} {g.inning}"
        console.print(
            f'{status_icon} Game {g.game_pk}: '
            f'{g.away_team_id} {g.away_score} @ {g.home_team_id} {g.home_score} | '
            f'{inning_str}, {g.outs} outs',
        )


@live_app.command(name='watch')
def live_watch(
    game_pk: int = typer.Option(..., '--game', '-g', help='Game PK to watch'),
    interval: int = typer.Option(10, '--interval', '-i', help='Polling interval in seconds'),
    predict: bool = typer.Option(False, '--predict', '-p', help='Run predictions on state changes'),
    model: str = typer.Option('xgboost_v1', '--model', '-m', help='Model to use for predictions'),
):
    """Watch a live game with real-time updates."""
    from mlb_predict.sources import LiveMlbSource

    source = LiveMlbSource()

    console.print(f'[bold]Watching game {game_pk}[/bold] (interval: {interval}s, predict: {predict})')
    console.print('[dim]Press Ctrl+C to stop[/dim]\n')

    # Define callback for state changes
    def on_state_change(state):
        inning_str = f"{'Top' if state.is_top else 'Bot'} {state.inning}"
        console.print(
            f'[cyan]{inning_str}[/cyan] | '
            f'{state.away_score}-{state.home_score} | '
            f'{state.outs} outs',
        )
        if predict:
            console.print(f'  [dim]Running prediction with {model}...[/dim]')

    source.on_state_change(on_state_change)

    try:
        while True:
            state = source.poll_game(game_pk)
            if state and state.is_complete:
                console.print(f'[green]Game complete! Final: {state.away_score}-{state.home_score}[/green]')
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print('\n[yellow]Stopped watching[/yellow]')


@live_app.command(name='poll')
def live_poll(
    interval: int = typer.Option(30, '--interval', '-i', help='Polling interval in seconds'),
    once: bool = typer.Option(False, '--once', help='Poll once and exit'),
):
    """Poll all active games for updates."""
    from mlb_predict.sources import LiveMlbSource

    source = LiveMlbSource()

    if once:
        console.print('[dim]Polling active games once...[/dim]')
        games = source.get_active_games()
        for g in games:
            source.poll_game(g.game_pk)
        console.print(f'[green]Polled {len(games)} games[/green]')
        return

    console.print(f'[bold]Polling all active games every {interval}s[/bold]')
    console.print('[dim]Press Ctrl+C to stop[/dim]\n')

    try:
        while True:
            games = source.get_active_games()
            if games:
                console.print(f'[dim]Polling {len(games)} active games...[/dim]')
                for g in games:
                    source.poll_game(g.game_pk)
            else:
                console.print('[dim]No active games[/dim]')
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print('\n[yellow]Stopped polling[/yellow]')


@live_app.command(name='predict')
def live_predict(
    game_pk: int = typer.Option(..., '--game', '-g', help='Game PK to predict'),
    model: str = typer.Option('xgboost_v1', '--model', '-m', help='Model to use'),
    continuous: bool = typer.Option(False, '--continuous', '-c', help='Continuous prediction mode'),
):
    """Run real-time prediction for a live game."""
    from mlb_predict.sources import LiveMlbSource

    source = LiveMlbSource()
    state = source.get_game_state(game_pk)

    if not state:
        console.print(f'[red]Game {game_pk} not found[/red]')
        raise typer.Exit(code=1)

    if not state.is_in_progress:
        console.print(f'[yellow]Game is not in progress (status: {state.status})[/yellow]')
        if not continuous:
            return

    # Get current game situation
    inning_str = f"{'Top' if state.is_top else 'Bot'} {state.inning}"
    console.print(f'[bold]Game {game_pk}[/bold]')
    console.print(f'Score: {state.away_score} @ {state.home_score}')
    console.print(f'Situation: {inning_str}, {state.outs} outs')

    # TODO: Compute features and run prediction
    console.print(f'[dim]Computing features for {model}...[/dim]')
    console.print('[green]Win probability: TBD (feature computation pending)[/green]')

    if continuous:
        console.print('\n[dim]Continuous mode: watching for state changes...[/dim]')
        try:
            while True:
                new_state = source.poll_game(game_pk)
                if new_state and source._state_changed(state, new_state):
                    console.print('[cyan]State changed - recomputing...[/cyan]')
                    state = new_state
                if state.is_complete:
                    console.print('[green]Game complete![/green]')
                    break
                time.sleep(10)
        except KeyboardInterrupt:
            console.print('\n[yellow]Stopped[/yellow]')


@live_app.command(name='server')
def live_server(
    host: str = typer.Option('localhost', '--host', '-h', help='Server host'),
    port: int = typer.Option(8765, '--port', '-p', help='Server port'),
    interval: float = typer.Option(10.0, '--interval', '-i', help='Polling interval in seconds'),
):
    """Start WebSocket server for live prediction streaming."""
    import asyncio

    try:
        from mlb_predict.streaming import PredictionWebSocketServer
    except ImportError as e:
        console.print(f'[red]Streaming module not available: {e}[/red]')
        console.print('[yellow]Install with: uv add websockets[/yellow]')
        raise typer.Exit(code=1)

    console.print('[bold]Starting WebSocket server[/bold]')
    console.print(f'Host: {host}')
    console.print(f'Port: {port}')
    console.print(f'Poll interval: {interval}s')
    console.print(f'[dim]Connect clients to ws://{host}:{port}[/dim]\n')

    server = PredictionWebSocketServer(
        host=host,
        port=port,
        poll_interval=interval,
    )

    try:
        asyncio.run(server.start())
        console.print('[green]Server running. Press Ctrl+C to stop.[/green]')

        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print('\n[yellow]Stopping server...[/yellow]')
        asyncio.run(server.stop())
        console.print('[green]Server stopped.[/green]')


app.add_typer(retrosheet_app, name='retrosheet')
app.add_typer(mlb_app, name='mlb')
app.add_typer(statcast_app, name='statcast')
app.add_typer(espn_app, name='espn')
app.add_typer(lahman_app, name='lahman')
app.add_typer(live_app, name='live')
app.add_typer(features_app, name='features')
app.add_typer(models_app, name='models')
app.add_typer(predict_app, name='predict')
app.add_typer(chatbot_app, name='chatbot')

if __name__ == '__main__':
    app()
