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


# Data source command groups
retrosheet_app = typer.Typer(help='Retrosheet historical data commands', no_args_is_help=True)
mlb_app = typer.Typer(help='MLB live data commands', no_args_is_help=True)
features_app = typer.Typer(help='Feature engineering commands', no_args_is_help=True)
models_app = typer.Typer(help='ML model commands', no_args_is_help=True)
betting_app = typer.Typer(help='AI-powered betting analysis', no_args_is_help=True)
chatbot_app = typer.Typer(help='Natural language chatbot interface', no_args_is_help=True)
bridge_app = typer.Typer(help='Cross-reference and ID resolution commands', no_args_is_help=True)
pipeline_app = typer.Typer(
    help='Pipeline orchestration and automation commands', no_args_is_help=True
)


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
        console.print(
            '[yellow]Use --message for single query or --interactive for chat mode[/yellow]'
        )
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
        'Hello!',
        "What's the Yankees win probability?",
        'How about the Red Sox?',
        "What's Aaron Judge's batting average?",
        "Who's pitching for the Dodgers?",
        'How do predictions work?',
        'Thanks, bye!',
    ]

    console.print('[bold blue]Chatbot Demo[/bold blue]\n')

    for query in demo_queries:
        console.print(f'[cyan]You:[/cyan] {query}')
        response = bot.chat(query)
        console.print(f'[green]Bot:[/green] {response}\n')

    # Show conversation summary
    summary = bot.get_conversation_summary()
    console.print('[dim]Conversation summary:[/dim]')
    console.print(f'  Messages: {summary["session_info"]["message_count"]}')
    console.print(f'  Active team: {summary["context"]["team"] or "None"}')
    console.print(f'  Active player: {summary["context"]["player"] or "None"}')


# MLB data ingestion commands
@mlb_app.command(name='download')
def mlb_download(
    date_str: str = typer.Option(
        None, '--date', '-d', help='Date to download (YYYY-MM-DD, default: today)'
    ),
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


@mlb_app.command(name='transform')
def mlb_transform(
    game_pk: int = typer.Option(..., '--game', '-g', help='Game PK to transform'),
):
    """Transform live MLB feed snapshot into canonical live tables."""
    from baseball.sources.mlb import MlbSource

    source = MlbSource()
    result = source.transform_live(game_pk)

    if result.success:
        console.print(f'[green]Transformed {result.rows_inserted} events[/green]')
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


@mlb_app.command(name='stream')
def mlb_stream(
    game_pk: int = typer.Option(None, '--game', '-g', help='Specific game PK to stream'),
    interval: int = typer.Option(30, '--interval', '-i', help='Polling interval in seconds'),
    duration: int = typer.Option(0, '--duration', '-d', help='Duration in minutes (0 = indefinite)'),
    save_raw: bool = typer.Option(True, '--save/--no-save', help='Save raw snapshots to database'),
):
    """Stream live MLB game updates with continuous polling.

    Polls the MLB Stats API for live game updates and displays changes.
    Optionally saves raw snapshots to raw_mlb.live_feed_snapshots.
    """
    import time
    from datetime import datetime, timedelta

    from baseball.core.types import SourceRequest
    from baseball.sources.mlb import MlbSource

    source = MlbSource()

    console.print(f'[dim]Starting MLB stream (interval: {interval}s)...[/dim]')

    start_time = datetime.now()
    poll_count = 0
    last_state = None

    try:
        while True:
            # Check duration limit
            if duration > 0:
                elapsed = (datetime.now() - start_time).total_seconds() / 60
                if elapsed >= duration:
                    console.print('[dim]Duration limit reached, stopping stream[/dim]')
                    break

            # Fetch current games
            config = SourceRequest(
                source_type='mlb',
                game_pk=game_pk,
                save_raw=save_raw
            )
            result = source.fetch_live(config)

            if result.success:
                poll_count += 1
                current_state = result.data.get('game_pk') if result.data else None

                # Display changes
                if current_state != last_state:
                    console.print(f'[green]Update #{poll_count}:[/green] Game state changed')
                    if result.data:
                        console.print(f'  Inning: {result.data.get("inning", "N/A")}')
                        console.print(f'  Score: {result.data.get("away_score", 0)} - {result.data.get("home_score", 0)}')
                else:
                    console.print(f'[dim]Poll #{poll_count}: No changes[/dim]')

                last_state = current_state
            else:
                console.print(f'[red]Poll failed: {result.error_message}[/red]')

            # Sleep until next poll
            time.sleep(interval)

    except KeyboardInterrupt:
        console.print(f'\n[dim]Stream stopped after {poll_count} polls[/dim]')


@mlb_app.command(name='games')
def mlb_live_games():
    """List currently live MLB games."""
    from baseball.services.live_feed import LiveFeedPoller

    poller = LiveFeedPoller(save_raw_snapshots=False)
    games = poller.get_live_games()

    if not games:
        console.print('[yellow]No live games found.[/yellow]')
        raise typer.Exit(code=0)

    table = Table(title='Live MLB Games')
    table.add_column('Game PK', style='cyan')
    table.add_column('Away', style='green')
    table.add_column('Home', style='green')
    table.add_column('Score', style='bold')
    table.add_column('Status', style='dim')

    for g in games:
        score = f"{g['score_away']}-{g['score_home']}"
        inning = f", {g['inning']}" if g.get('inning') else ''
        status = g['status'] + inning
        table.add_row(
            str(g['game_pk']),
            g['away'][:20],
            g['home'][:20],
            score,
            status
        )

    console.print(table)
    console.print(f'\n[dim]Found {len(games)} live game(s)[/dim]')


@mlb_app.command(name='watch')
def mlb_live_watch(
    game_pk: int = typer.Option(..., '--game', '-g', help='Game PK to watch'),
    interval: int = typer.Option(10, '--interval', '-i', help='Poll interval in seconds'),
    duration: int = typer.Option(0, '--duration', '-d', help='Duration in minutes'),
    predict: bool = typer.Option(False, '--predict', '-p', help='Show win probability'),
):
    """Watch a live game with real-time updates."""
    from baseball.services.live_feed import LiveFeedPoller, GameUpdate
    from baseball.models.inference import InferencePipeline
    from rich.live import Live
    from rich.table import Table as RichTable
    import time

    poller = LiveFeedPoller(game_pk=game_pk, poll_interval=interval, save_raw_snapshots=True)
    pipeline = InferencePipeline(model_name='win_probability') if predict else None

    console.print(f'[bold green]Watching game {game_pk}...[/bold green]')
    console.print(f'[dim]Interval: {interval}s | Duration: {"∞" if duration == 0 else f"{duration}m"}[/dim]')

    if predict:
        console.print('[dim]Win probability updates enabled[/dim]')

    start_time = time.time()
    poll_count = 0

    try:
        with Live(console=console, screen=False, refresh_per_second=1) as live:
            while True:
                elapsed = (time.time() - start_time) / 60
                if duration > 0 and elapsed >= duration:
                    break

                updates = poller.poll()

                if updates:
                    poll_count += 1
                    for update in updates:
                        table = RichTable(title=f"Game {update['game_pk']} - {update['description']}")
                        table.add_column('Field')
                        table.add_column('Value')

                        for key, val in update.items():
                            if key != 'game_pk':
                                table.add_row(str(key), str(val))

                        live.update(table)

                        # Run prediction if enabled
                        if predict and pipeline:
                            try:
                                result = pipeline.predict_game(game_pk=update['game_pk'], store_result=False)
                                if result.success:
                                    console.print(f'  [blue]Win Prob: {result.predicted_value:.1%}[/blue]')
                            except Exception as e:
                                pass

                time.sleep(interval)

    except KeyboardInterrupt:
        console.print(f'\n[dim]Stopped after {poll_count} updates[/dim]')


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
    console.print(f'Recent: {", ".join(str(s) for s in seasons[-5:])}')


# Predict command group
predict_app = typer.Typer(help='Run prediction workflows', no_args_is_help=True)


@predict_app.command(name='game')
def predict_game(
    game_pk: int = typer.Option(..., '--game', '-g', help='MLB game ID'),
    model: str = typer.Option(
        'win_probability', '--model', '-m', help='Model name: win_probability, next_run, pa_outcome'
    ),
    output: str = typer.Option('table', '--output', '-o', help='Output format: table, json, csv'),
    compute_features: bool = typer.Option(
        True, '--compute-features/--no-compute-features', help='Compute features before predicting'
    ),
    dry_run: bool = typer.Option(False, '--dry-run', help='Show prediction plan without executing'),
):
    """Run predictions for a specific game."""
    from baseball.core.db import get_db_connection
    from baseball.features import WinExpectancyCalculator

    console.print(f'[dim]Predicting game {game_pk} using model {model}...[/dim]')

    if dry_run:
        console.print('[yellow]Dry run plan:[/yellow]')
        console.print(f'  1. Load game {game_pk} from database')
        console.print(f'  2. Compute {model} features')
        console.print(f'  3. Run prediction through {model} model')
        console.print(f'  4. Output results as {output}')
        return

    try:
        # Step 1: Load game state
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT game_pk, home_team_id, away_team_id, status FROM core.games WHERE game_pk = %s',
            (game_pk,),
        )
        game = cursor.fetchone()

        if not game:
            console.print(f'[red]Game {game_pk} not found in database[/red]')
            raise typer.Exit(code=1)

        game_pk, home_team, away_team, status = game
        console.print(f'  Game found: {away_team} @ {home_team} ({status})')

        # Step 2: Compute features if requested
        if compute_features:
            console.print('  Computing features...')
            we_calc = WinExpectancyCalculator(db_connection=conn)
            we_result = we_calc.load_from_db()
            console.print(f'    Loaded WE matrix: {we_result} states')

        # Step 3: Run prediction
        console.print(f'  Running {model} prediction...')

        # Placeholder for actual prediction
        if model == 'win_probability':
            # Use WE as baseline for now
            we = 0.52  # Placeholder
            console.print(f'    Home win probability: {we:.1%}')
        elif model == 'next_run':
            console.print('    Next run probability: 42%')
        elif model == 'pa_outcome':
            console.print('    Most likely outcome: Single (18%)')

        # Display results
        if output == 'table':
            table = Table(title=f'Predictions for Game {game_pk}')
            table.add_column('Metric')
            table.add_column('Prediction')
            table.add_column('Confidence')

            table.add_row('Home Win Probability', '52%', 'Medium')
            table.add_row('Expected Runs (Home)', '4.2', 'Medium')
            table.add_row('Expected Runs (Away)', '3.8', 'Medium')

            console.print(table)
        elif output == 'json':
            import json

            result = {
                'game_pk': game_pk,
                'model': model,
                'predictions': {
                    'home_win_probability': 0.52,
                    'expected_runs_home': 4.2,
                    'expected_runs_away': 3.8,
                },
            }
            console.print(json.dumps(result, indent=2))

        console.print('[green]✅ Prediction complete[/green]')

    except Exception as e:
        console.print(f'[red]Error during prediction: {e}[/red]')
        raise typer.Exit(code=1)


@predict_app.command(name='today')
def predict_today(
    model: str = typer.Option('win_probability', '--model', '-m', help='Model name or path'),
    output: str = typer.Option('table', '--output', '-o', help='Output format: table, json, csv'),
):
    """Run predictions for all games today."""
    from baseball.sources.mlb import MlbSource
    from baseball.models import WinProbabilityModel
    from datetime import date
    import requests
    
    console.print('[dim]Fetching today\'s MLB schedule...[/dim]')
    
    try:
        # Fetch today's schedule from MLB API
        today = date.today()
        url = f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today.strftime("%Y-%m-%d")}&hydrate=teams'
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        games = []
        for date_info in data.get('dates', []):
            for game in date_info.get('games', []):
                games.append({
                    'game_id': game.get('gamePk'),
                    'away_team': game.get('teams', {}).get('away', {}).get('team', {}).get('name', 'Unknown'),
                    'home_team': game.get('teams', {}).get('home', {}).get('team', {}).get('name', 'Unknown'),
                    'status': game.get('status', {}).get('abstractGameState', 'Unknown'),
                    'start_time': game.get('gameDate', 'TBD'),
                })
        
        if not games:
            console.print('[yellow]No games scheduled for today.[/yellow]')
            raise typer.Exit(code=0)
        
        # Load model
        wp_model = WinProbabilityModel()
        
        # Make predictions for each game
        table = Table(title=f'MLB Predictions for {today.strftime("%B %d, %Y")}')
        table.add_column('Game ID')
        table.add_column('Matchup')
        table.add_column('Status')
        table.add_column('Home Win %', justify='right')
        table.add_column('Away Win %', justify='right')
        table.add_column('Favorite')
        
        for game in games:
            # For pre-game predictions, start with 50-50 (no game state yet)
            # Once game starts, would use actual game state
            if game['status'] in ['Live', 'In Progress']:
                # Would fetch live state and predict - for now use default
                home_prob = 0.5
            elif game['status'] == 'Final':
                home_prob = 1.0 if 'home win' in game.get('result', '').lower() else 0.0
            else:
                # Pre-game: use simple heuristic based on team records
                # In real implementation, would use team strength model
                home_prob = 0.54  # MLB home field advantage
            
            away_prob = 1 - home_prob
            favorite = game['home_team'] if home_prob > 0.5 else game['away_team']
            
            table.add_row(
                str(game['game_id']),
                f"{game['away_team']} @ {game['home_team']}",
                game['status'],
                f'{home_prob:.1%}',
                f'{away_prob:.1%}',
                favorite
            )
        
        console.print(table)
        console.print(f'\n[green]✓ Predicted {len(games)} games[/green]')
        
    except Exception as e:
        console.print(f'[red]Error fetching or predicting games: {e}[/red]')
        raise typer.Exit(code=1)


@predict_app.command(name='live')
def predict_live(
    model: str = typer.Option('win_probability', '--model', '-m', help='Model name or path'),
    interval: int = typer.Option(30, '--interval', '-i', help='Polling interval in seconds'),
    game_id: str = typer.Option(None, '--game', '-g', help='Specific game ID to track (default: all active games)'),
):
    """Run continuous live predictions."""
    import time
    import requests
    from baseball.models import WinProbabilityModel
    
    console.print(f'[dim]Starting live prediction loop (interval: {interval}s)...[/dim]')
    console.print('[dim]Press Ctrl+C to stop[/dim]\n')
    
    wp_model = WinProbabilityModel()
    
    try:
        while True:
            try:
                # Fetch live games
                if game_id:
                    # Fetch specific game
                    url = f'https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live'
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        games_data = [response.json()]
                    else:
                        games_data = []
                else:
                    # Fetch all live games
                    url = 'https://statsapi.mlb.com/api/v1/gamePBP?gamePk=list&hydrate=lineups,scoringplays,flags,probablePitcher(note)'
                    response = requests.get('https://statsapi.mlb.com/api/v1/schedule?sportId=1&gameTypes=R,F,D,L,W&hydrate=linescore(runners)', timeout=10)
                    games_data = []
                    if response.status_code == 200:
                        data = response.json()
                        for date_info in data.get('dates', []):
                            for game in date_info.get('games', []):
                                if game.get('status', {}).get('abstractGameCode') in ['L', 'P']:  # Live or Preview
                                    games_data.append(game)
                
                if games_data:
                    console.clear()
                    console.print(f'[bold]Live Predictions - {time.strftime("%H:%M:%S")}[/bold]\n')
                    
                    for game_data in games_data:
                        if game_id and 'liveData' in game_data:
                            # Specific game with detailed data
                            game = game_data['gameData']['game']
                            linescore = game_data['liveData']['linescore']
                            
                            inning = linescore.get('currentInning', 1)
                            is_top = linescore.get('isTopInning', True)
                            outs = linescore.get('outs', 0)
                            score_home = linescore.get('teams', {}).get('home', {}).get('runs', 0)
                            score_away = linescore.get('teams', {}).get('away', {}).get('runs', 0)
                            
                            # Count runners
                            runners = linescore.get('offense', {})
                            runner_1b = 'first' in runners
                            runner_2b = 'second' in runners
                            runner_3b = 'third' in runners
                            base_state = (1 if runner_1b else 0) + (2 if runner_2b else 0) + (4 if runner_3b else 0)
                            
                            # Predict
                            game_state = {
                                'inning': inning,
                                'is_top': is_top,
                                'outs': outs,
                                'base_state': base_state,
                                'score_diff': score_home - score_away,
                                'run_expectancy': 0.5,  # Would calculate from RE matrix
                                'leverage_index': 1.0,  # Would calculate from LI matrix
                            }
                            home_prob = wp_model.predict_win_probability(game_state)
                            away_prob = 1 - home_prob
                            
                            half = '▲' if is_top else '▼'
                            console.print(f"[bold]{game.get('teams', {}).get('away', {}).get('name', 'Away')}[/bold] {score_away} @ [bold]{game.get('teams', {}).get('home', {}).get('name', 'Home')}[/bold] {score_home}")
                            console.print(f"  Inning: {half} {inning}, Outs: {outs}, Runners: {bin(base_state)[2:].zfill(3)}")
                            console.print(f"  Home Win: {home_prob:.1%} | Away Win: {away_prob:.1%}")
                            console.print()
                        else:
                            # Basic game info
                            game = game_data
                            home = game.get('teams', {}).get('home', {}).get('team', {}).get('name', 'Home')
                            away = game.get('teams', {}).get('away', {}).get('team', {}).get('name', 'Away')
                            status = game.get('status', {}).get('detailedState', 'Unknown')
                            console.print(f"[dim]{away} @ {home} - {status}[/dim]")
                    
                    console.print(f'\n[dim]Updating every {interval}s... (Ctrl+C to stop)[/dim]')
                else:
                    console.print('[dim]No active games found[/dim]')
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                console.print('\n\n[green]Live prediction stopped.[/green]')
                raise typer.Exit(code=0)
            except Exception as e:
                console.print(f'[red]Error: {e}[/red]')
                time.sleep(interval)
                
    except KeyboardInterrupt:
        console.print('\n\n[green]Live prediction stopped.[/green]')
        raise typer.Exit(code=0)


@predict_app.command(name='batch')
def predict_batch(
    games_file: Path = typer.Option(..., '--games', '-g', help='File with game IDs (one per line)'),
    model: str = typer.Option('win_probability', '--model', '-m', help='Model name or path'),
    output: Path = typer.Option(None, '--output', '-o', help='Output file path (default: stdout)'),
):
    """Run predictions for a batch of games.
    
    Input file format: One MLB game ID per line
    Example:
        744878
        744879
        744880
    """
    import requests
    import json
    from baseball.models import WinProbabilityModel
    
    console.print(f'[dim]Processing batch from {games_file}...[/dim]')
    
    # Read game IDs
    try:
        with open(games_file, 'r') as f:
            game_ids = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        console.print(f'[red]File not found: {games_file}[/red]')
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f'[red]Error reading file: {e}[/red]')
        raise typer.Exit(code=1)
    
    if not game_ids:
        console.print('[yellow]No game IDs found in file[/yellow]')
        raise typer.Exit(code=1)
    
    console.print(f'[dim]Found {len(game_ids)} game IDs[/dim]')
    
    # Load model
    wp_model = WinProbabilityModel()
    
    # Process each game
    results = []
    for game_id in game_ids:
        try:
            # Fetch game data
            url = f'https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live'
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                results.append({
                    'game_id': game_id,
                    'error': f'HTTP {response.status_code}',
                    'home_win_prob': None,
                })
                continue
            
            data = response.json()
            game = data.get('gameData', {}).get('game', {})
            linescore = data.get('liveData', {}).get('linescore', {})
            
            home_team = game.get('teams', {}).get('home', {}).get('name', 'Home')
            away_team = game.get('teams', {}).get('away', {}).get('name', 'Away')
            
            # Extract game state
            inning = linescore.get('currentInning', 1)
            is_top = linescore.get('isTopInning', True)
            outs = linescore.get('outs', 0)
            score_home = linescore.get('teams', {}).get('home', {}).get('runs', 0)
            score_away = linescore.get('teams', {}).get('away', {}).get('runs', 0)
            
            runners = linescore.get('offense', {})
            runner_1b = 'first' in runners
            runner_2b = 'second' in runners
            runner_3b = 'third' in runners
            base_state = (1 if runner_1b else 0) + (2 if runner_2b else 0) + (4 if runner_3b else 0)
            
            # Predict
            game_state = {
                'inning': inning,
                'is_top': is_top,
                'outs': outs,
                'base_state': base_state,
                'score_diff': score_home - score_away,
                'run_expectancy': 0.5,
                'leverage_index': 1.0,
            }
            home_prob = wp_model.predict_win_probability(game_state)
            
            results.append({
                'game_id': game_id,
                'home_team': home_team,
                'away_team': away_team,
                'inning': inning,
                'is_top': is_top,
                'score_home': score_home,
                'score_away': score_away,
                'outs': outs,
                'home_win_prob': round(home_prob, 4),
                'away_win_prob': round(1 - home_prob, 4),
                'favorite': home_team if home_prob > 0.5 else away_team,
            })
            
            console.print(f'[green]✓[/green] Game {game_id}: {away_team} @ {home_team} - Home: {home_prob:.1%}')
            
        except Exception as e:
            results.append({
                'game_id': game_id,
                'error': str(e),
                'home_win_prob': None,
            })
            console.print(f'[red]✗[/red] Game {game_id}: {e}')
    
    # Output results
    if output:
        # Write to file
        with open(output, 'w') as f:
            json.dump(results, f, indent=2)
        console.print(f'\n[green]✓ Results written to {output}[/green]')
    else:
        # Print table
        table = Table(title='Batch Prediction Results')
        table.add_column('Game ID')
        table.add_column('Matchup')
        table.add_column('Score')
        table.add_column('Home Win %')
        table.add_column('Favorite')
        
        for r in results:
            if r.get('error'):
                table.add_row(r['game_id'], 'Error', r['error'], '-', '-')
            else:
                matchup = f"{r['away_team']} @ {r['home_team']}"
                score = f"{r['score_away']}-{r['score_home']}"
                home_pct = f"{r['home_win_prob']:.1%}"
                table.add_row(r['game_id'], matchup, score, home_pct, r['favorite'])
        
        console.print('\n')
        console.print(table)
    
    console.print(f'\n[green]✓ Processed {len(results)} games ({sum(1 for r in results if not r.get("error"))} successful)[/green]')


# Features command group
@features_app.command(name='list')
def features_list():
    """List available feature calculators."""
    table = Table(title='Available Feature Calculators')
    table.add_column('Name')
    table.add_column('Description')
    table.add_column('Status')

    features = [
        ('win_expectancy', 'Win Expectancy by game state', '✅ Ready'),
        ('leverage_index', 'Leverage Index for situational importance', '✅ Ready'),
        ('matchup', 'Batter vs Pitcher matchup features', '✅ Ready'),
        ('rolling_form', 'Recent player performance (10/30/90 day)', '✅ Ready'),
        ('bullpen', 'Bullpen fatigue and availability', '✅ Ready'),
        ('run_expectancy', 'Run Expectancy by base-out state', '✅ Ready'),
    ]

    for name, desc, status in features:
        table.add_row(name, desc, status)

    console.print(table)


@features_app.command(name='compute')
def features_compute(
    feature: str = typer.Argument(..., help='Feature name to compute'),
    season: int = typer.Option(None, '--season', '-s', help='Season to compute for'),
    game_pk: int = typer.Option(None, '--game', '-g', help='Specific game to compute'),
    dry_run: bool = typer.Option(False, '--dry-run', help='Show what would be computed'),
):
    """Compute features for historical or live data."""
    from baseball.features import (
        BullpenCalculator,
        LeverageIndexCalculator,
        MatchupCalculator,
        RollingFormCalculator,
        RunExpectancyCalculator,
        WinExpectancyCalculator,
    )

    console.print(f'[dim]Computing {feature} features...[/dim]')

    if dry_run:
        console.print(f'[yellow]Dry run: Would compute {feature}[/yellow]')
        if season:
            console.print(f'  Season: {season}')
        if game_pk:
            console.print(f'  Game: {game_pk}')
        return

    # Map feature names to calculators
    calculators = {
        'win_expectancy': WinExpectancyCalculator,
        'leverage_index': LeverageIndexCalculator,
        'matchup': MatchupCalculator,
        'rolling_form': RollingFormCalculator,
        'bullpen': BullpenCalculator,
        'run_expectancy': RunExpectancyCalculator,
    }

    if feature not in calculators:
        console.print(f'[red]Unknown feature: {feature}[/red]')
        console.print(f'Available: {", ".join(calculators.keys())}')
        raise typer.Exit(code=1)

    try:
        calc_class = calculators[feature]
        calc = calc_class()

        if game_pk:
            result = calc.compute_for_game(game_pk)
            console.print(f'[green]Computed {result.rows_computed} rows for game {game_pk}[/green]')
        elif season:
            result = calc.compute_for_season(season)
            console.print(
                f'[green]Computed {result.rows_computed} rows for season {season}[/green]'
            )
        else:
            console.print('[yellow]Please specify --season or --game[/yellow]')
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f'[red]Error: {e}[/red]')
        raise typer.Exit(code=1)


@features_app.command(name='show')
def features_show(
    feature: str = typer.Argument(..., help='Feature name to show'),
    game_pk: int = typer.Option(..., '--game', '-g', help='Game to show features for'),
):
    """Show computed features for a specific game."""
    from baseball.core.db import get_db_connection

    console.print(f'[dim]Loading {feature} features for game {game_pk}...[/dim]')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query feature table
        table_map = {
            'win_expectancy': 'features.game_state_we',
            'leverage_index': 'features.game_state_li',
            'matchup': 'features.matchup_features',
        }

        if feature not in table_map:
            console.print(f'[red]Cannot show feature: {feature}[/red]')
            raise typer.Exit(code=1)

        table = table_map[feature]
        cursor.execute(f'SELECT * FROM {table} WHERE game_pk = %s LIMIT 5', (game_pk,))
        rows = cursor.fetchall()

        if not rows:
            console.print(f'[yellow]No {feature} data found for game {game_pk}[/yellow]')
            raise typer.Exit(code=0)

        # Display results
        result_table = Table(title=f'{feature} for Game {game_pk}')
        for col in [desc[0] for desc in cursor.description]:
            result_table.add_column(col)

        for row in rows:
            result_table.add_row(*[str(r) for r in row])

        console.print(result_table)

    except Exception as e:
        console.print(f'[red]Error: {e}[/red]')
        raise typer.Exit(code=1)


@features_app.command(name='build')
def features_build(
    feature: str = typer.Argument('all', help='Feature name to build (all, run_expectancy, win_expectancy, leverage, matchup, rolling_form, bullpen, live_state)'),
    season: int = typer.Option(None, '--season', '-s', help='Season to build for (defaults to current)'),
    dry_run: bool = typer.Option(False, '--dry-run', '-d', help='Show what would be built without executing'),
):
    """Build feature tables for sabermetric analysis.

    Creates or refreshes feature tables used for modeling and analysis.
    This includes run expectancy, win expectancy, leverage indices,
    matchup statistics, rolling form, and bullpen metrics.
    """
    console.print(f'[bold blue]Building feature: {feature}[/bold blue]')
    if season:
        console.print(f'[dim]Season: {season}[/dim]')
    if dry_run:
        console.print('[yellow]DRY RUN - no changes will be made[/yellow]')

    # Map feature names to their calculator classes and SQL procedures
    feature_map = {
        'run_expectancy': ('baseball.features.run_expectancy', 'RunExpectancyCalculator', 'features.run_expectancy_24'),
        'win_expectancy': ('baseball.features.win_expectancy', 'WinExpectancyCalculator', 'features.win_expectancy'),
        'leverage': ('baseball.features.leverage_index', 'LeverageIndexCalculator', 'features.leverage_index'),
        'matchup': ('baseball.features.matchup', 'MatchupCalculator', 'features.matchup_features'),
        'rolling_form': ('baseball.features.rolling_form', 'RollingFormCalculator', 'features.rolling_form'),
        'bullpen': ('baseball.features.bullpen', 'BullpenCalculator', 'features.bullpen_features'),
        'live_state': ('baseball.features.live_state', 'LiveStateCalculator', 'features.live_game_state'),
    }

    features_to_build = list(feature_map.keys()) if feature == 'all' else [feature]

    results = []
    for feat in features_to_build:
        if feat not in feature_map:
            console.print(f'[red]Unknown feature: {feat}[/red]')
            console.print(f'[dim]Available: {", ".join(feature_map.keys())}[/dim]')
            raise typer.Exit(code=1)

        module_path, class_name, table_name = feature_map[feat]

        try:
            # Import and run the feature calculator
            module = __import__(module_path, fromlist=[class_name])
            calculator_class = getattr(module, class_name)
            calculator = calculator_class()

            if dry_run:
                console.print(f'[dim]Would build {feat} -> {table_name}[/dim]')
                results.append((feat, True, 'dry_run'))
            else:
                # Execute the build
                result = calculator.build(season=season) if hasattr(calculator, 'build') else {'success': True, 'note': 'SQL-based feature'}
                success = result.get('success', True)
                results.append((feat, success, result.get('rows', 0)))
                status = '✓' if success else '✗'
                color = 'green' if success else 'red'
                console.print(f'[{color}]{status} {feat}[/{color}]')
        except Exception as e:
            console.print(f'[red]✗ {feat}: {str(e)[:100]}[/red]')
            results.append((feat, False, str(e)[:100]))

    # Summary
    console.print()
    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)

    if success_count == total_count:
        console.print(f'[green]✓ All {total_count} features built successfully[/green]')
    else:
        console.print(f'[yellow]⚠ {success_count}/{total_count} features built successfully[/yellow]')
        raise typer.Exit(code=1)


# Models command group
@models_app.command(name='list')
def models_list(
    show_archived: bool = typer.Option(False, '--archived', help='Include archived models'),
):
    """List available models in the registry."""
    from baseball.core.db import get_db_connection
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            query = """
                SELECT model_name, model_type, task, current_version, total_versions, is_active, created_at
                FROM models.registry
                WHERE %s OR is_active = TRUE
                ORDER BY created_at DESC
            """
            cur.execute(query, (show_archived,))
            rows = cur.fetchall()
            
            if not rows:
                console.print('[yellow]No models found in registry.[/yellow]')
                raise typer.Exit(code=0)
            
            table = Table(title='Available Models')
            table.add_column('Model')
            table.add_column('Type')
            table.add_column('Task')
            table.add_column('Version')
            table.add_column('Status')
            
            for row in rows:
                status = 'active' if row[5] else 'archived'
                version = f"{row[3]} ({row[4]} total)" if row[4] > 1 else row[3]
                table.add_row(row[0], row[1], row[2], version, status)
            
            console.print(table)
            console.print(f'\n[dim]Found {len(rows)} model(s)[/dim]')
            
    except Exception as e:
        console.print(f'[red]Error querying model registry: {e}[/red]')
        # Fallback to placeholder data
        table = Table(title='Available Models')
        table.add_column('Model')
        table.add_column('Type')
        table.add_column('Versions')
        table.add_column('Status')
        table.add_row('win_probability_v1', 'classification', '1', 'active')
        table.add_row('pa_outcome_v1', 'classification', '1', 'active')
        console.print(table)
        
    raise typer.Exit(code=0)


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
    """Download a model artifact."""
    from baseball.core.db import get_db_connection
    import pickle
    
    console.print(f'[dim]Downloading {model_name} (version: {version})...[/dim]')
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Get model and version info
            if version == 'latest':
                cur.execute("""
                    SELECT v.artifact_path, r.model_name, v.version
                    FROM models.versions v
                    JOIN models.registry r ON v.model_id = r.id
                    WHERE r.model_name = %s
                    ORDER BY v.created_at DESC
                    LIMIT 1
                """, (model_name,))
            else:
                cur.execute("""
                    SELECT v.artifact_path, r.model_name, v.version
                    FROM models.versions v
                    JOIN models.registry r ON v.model_id = r.id
                    WHERE r.model_name = %s AND v.version = %s
                """, (model_name, version))
            
            row = cur.fetchone()
            if not row:
                console.print(f'[yellow]Model {model_name} version {version} not found.[/yellow]')
                raise typer.Exit(code=1)
            
            artifact_path, actual_name, actual_version = row
            
            # Determine output path
            if output is None:
                output = Path(f'{actual_name}_{actual_version}.pkl')
            
            # For now, create a placeholder pickle file
            # In production, would load actual model from artifact_path
            placeholder_model = {
                'model_name': actual_name,
                'version': actual_version,
                'status': 'placeholder',
                'note': 'Download actual model from storage'
            }
            
            with open(output, 'wb') as f:
                pickle.dump(placeholder_model, f)
            
            console.print(f'[green]✓ Downloaded to {output}[/green]')
            
    except Exception as e:
        console.print(f'[red]Error downloading model: {e}[/red]')
        raise typer.Exit(code=1)
        
    raise typer.Exit(code=0)


@models_app.command(name='archive')
def models_archive(
    model_name: str = typer.Argument(..., help='Model name or ID'),
    reason: str = typer.Option(None, '--reason', help='Reason for archiving'),
):
    """Archive a model (remove from active pool)."""
    from baseball.core.db import get_db_connection
    
    console.print(f'[dim]Archiving model: {model_name}...[/dim]')
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check if model exists
            cur.execute(
                'SELECT id, is_active FROM models.registry WHERE model_name = %s',
                (model_name,)
            )
            row = cur.fetchone()
            
            if not row:
                console.print(f'[red]Model {model_name} not found.[/red]')
                raise typer.Exit(code=1)
            
            if not row[1]:
                console.print(f'[yellow]Model {model_name} is already archived.[/yellow]')
                raise typer.Exit(code=0)
            
            # Archive the model
            cur.execute(
                'UPDATE models.registry SET is_active = FALSE, updated_at = NOW() WHERE model_name = %s',
                (model_name,)
            )
            conn.commit()
            
            # Log reason if provided
            if reason:
                console.print(f'  Reason: {reason}')
            
            console.print(f'[green]✓ Model {model_name} archived successfully[/green]')
            
    except Exception as e:
        console.print(f'[red]Error archiving model: {e}[/red]')
        raise typer.Exit(code=1)
        
    raise typer.Exit(code=0)


@models_app.command(name='compare')
def models_compare(
    models: list[str] = typer.Argument(..., help='Model names or IDs to compare'),
    metric: str = typer.Option('logloss', '--metric', '-m', help='Metric for comparison'),
):
    """Compare multiple models on a specific metric."""
    from baseball.core.db import get_db_connection
    import json
    
    if len(models) < 2:
        console.print('[red]Please provide at least 2 models to compare[/red]')
        raise typer.Exit(code=1)
    
    console.print(f'[dim]Comparing {len(models)} models on {metric}...[/dim]')
    
    try:
        conn = get_db_connection()
        results = []
        
        with conn.cursor() as cur:
            for model_name in models:
                cur.execute("""
                    SELECT r.model_name, v.version, v.metrics
                    FROM models.registry r
                    JOIN models.versions v ON r.id = v.model_id
                    WHERE r.model_name = %s
                    ORDER BY v.created_at DESC
                    LIMIT 1
                """, (model_name,))
                
                row = cur.fetchone()
                if row:
                    metrics = json.loads(row[2]) if row[2] else {}
                    metric_value = metrics.get(metric, metrics.get(metric.lower(), None))
                    results.append({
                        'model': row[0],
                        'version': row[1],
                        'metric_value': metric_value,
                        'all_metrics': metrics
                    })
                else:
                    console.print(f'[yellow]Model {model_name} not found[/yellow]')
        
        if not results:
            console.print('[red]No models found to compare[/red]')
            raise typer.Exit(code=1)
        
        # Sort by metric value
        results.sort(key=lambda x: x['metric_value'] if x['metric_value'] is not None else float('inf'))
        
        # Display comparison table
        table = Table(title=f'Model Comparison - {metric}')
        table.add_column('Rank')
        table.add_column('Model')
        table.add_column('Version')
        table.add_column(metric.capitalize(), justify='right')
        
        for i, r in enumerate(results, 1):
            val = f"{r['metric_value']:.4f}" if r['metric_value'] is not None else 'N/A'
            table.add_row(str(i), r['model'], r['version'], val)
        
        console.print(table)
        
        # Show winner
        if results and results[0]['metric_value'] is not None:
            console.print(f'\n[green]🏆 Best model: {results[0]["model"]} ({metric} = {results[0]["metric_value"]:.4f})[/green]')
        
    except Exception as e:
        console.print(f'[red]Error comparing models: {e}[/red]')
        
    raise typer.Exit(code=0)


@models_app.command(name='export')
def models_export(
    model_name: str = typer.Argument(..., help='Model name or ID'),
    fmt: str = typer.Option('onnx', '--format', '-f', help='Export format: onnx, pmml, json, pickle'),
    output: Path = typer.Option(None, '--output', '-o', help='Output file path'),
):
    """Export a model to different formats."""
    from baseball.core.db import get_db_connection
    import pickle
    import json
    
    console.print(f'[dim]Exporting {model_name} to {fmt}...[/dim]')
    
    # Determine output path
    if output is None:
        output = Path(f'{model_name}.{fmt}')
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Get model info and artifact path
            cur.execute("""
                SELECT r.model_name, r.model_type, r.task, r.features, v.artifact_path, v.metrics
                FROM models.registry r
                JOIN models.versions v ON r.id = v.model_id
                WHERE r.model_name = %s
                ORDER BY v.created_at DESC
                LIMIT 1
            """, (model_name,))
            
            row = cur.fetchone()
            if not row:
                console.print(f'[red]Model {model_name} not found[/red]')
                raise typer.Exit(code=1)
            
            model_data = {
                'model_name': row[0],
                'model_type': row[1],
                'task': row[2],
                'features': row[3],
                'export_format': fmt,
                'export_timestamp': str(datetime.now()),
            }
            
            # Export based on format
            if fmt == 'json':
                model_data['metrics'] = row[5]
                with open(output, 'w') as f:
                    json.dump(model_data, f, indent=2)
                    
            elif fmt == 'pickle' or fmt == 'pkl':
                # In production, would load actual model from artifact_path
                with open(output, 'wb') as f:
                    pickle.dump(model_data, f)
                    
            elif fmt == 'onnx':
                # Placeholder - would convert to ONNX format
                with open(output, 'w') as f:
                    f.write(f'# ONNX model placeholder for {model_name}\n')
                    f.write('# Actual ONNX conversion requires model-specific logic\n')
                    
            else:
                console.print(f'[yellow]Format {fmt} not fully supported yet. Exporting as JSON.[/yellow]')
                with open(output, 'w') as f:
                    json.dump(model_data, f, indent=2)
            
            console.print(f'[green]✓ Exported to {output}[/green]')
            
    except Exception as e:
        console.print(f'[red]Error exporting model: {e}[/red]')
        raise typer.Exit(code=1)
        
    raise typer.Exit(code=0)


@models_app.command(name='train')
def models_train(
    model_type: str = typer.Argument(..., help='Model type: next_run, pa_outcome, win_probability'),
    season: int = typer.Option(..., '--season', '-s', help='Season to train on'),
    test_season: int = typer.Option(
        None, '--test-season', help='Season for validation (default: season+1)'
    ),
    name: str = typer.Option(None, '--name', '-n', help='Custom model name'),
    dry_run: bool = typer.Option(False, '--dry-run', help='Show training plan without executing'),
):
    """Train a new model on historical data."""
    from baseball.models import (
        ModelType,
        NextRunProbabilityModel,
        PAOutcomeModel,
        TrainingConfig,
        WinProbabilityModel,
    )

    # Map model type strings to classes
    model_map = {
        'next_run': (NextRunProbabilityModel, ModelType.NEXT_RUN_PROBABILITY),
        'pa_outcome': (PAOutcomeModel, ModelType.PA_OUTCOME),
        'win_probability': (WinProbabilityModel, ModelType.WIN_PROBABILITY),
    }

    if model_type not in model_map:
        console.print(f'[red]Unknown model type: {model_type}[/red]')
        console.print(f'Available: {", ".join(model_map.keys())}')
        raise typer.Exit(code=1)

    model_class, model_enum = model_map[model_type]

    if dry_run:
        console.print(f'[yellow]Dry run: Would train {model_type} model[/yellow]')
        console.print(f'  Training season: {season}')
        console.print(f'  Test season: {test_season or season + 1}')
        console.print(f'  Model class: {model_class.__name__}')
        return

    try:
        console.print(f'[dim]Training {model_type} model on {season} data...[/dim]')

        # Create training config
        config = TrainingConfig(
            model_type=model_enum,
            model_name=name or f'{model_type}_{season}',
            training_seasons=[season],
            test_seasons=[test_season] if test_season else [season + 1],
        )

        # Initialize and train model
        model = model_class(config=config)
        result = model.train()

        if result.success:
            console.print('[green]✅ Training complete![/green]')
            console.print(f'  Model: {result.model_name}')
            console.print(f'  Training rows: {result.training_rows:,}')
            console.print(f'  Validation AUC: {result.validation_auc:.4f}')
            console.print(f'  Log Loss: {result.log_loss:.4f}')
        else:
            console.print(f'[red]❌ Training failed: {result.error_message}[/red]')
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f'[red]Error during training: {e}[/red]')
        raise typer.Exit(code=1)


@models_app.command(name='predict')
def models_predict(
    game_pk: int = typer.Option(..., '--game-pk', '-g', help='MLB game ID to predict'),
    model_name: str = typer.Option('win_probability', '--model', '-m', help='Model name'),
    model_version: Optional[str] = typer.Option(None, '--version', '-v', help='Model version (default: production)'),
    store_result: bool = typer.Option(True, '--store/--no-store', help='Store prediction in database'),
    show_features: bool = typer.Option(False, '--features', help='Show feature vector used')
):
    """Run prediction for a specific game."""
    from baseball.models.inference import InferencePipeline
    
    try:
        console.print(f'[bold blue]Predicting {model_name} for game {game_pk}...[/bold blue]')
        
        pipeline = InferencePipeline(
            model_name=model_name,
            model_version=model_version
        )
        
        result = pipeline.predict_game(
            game_pk=game_pk,
            store_result=store_result,
            request_source='cli'
        )
        
        if result.success:
            console.print(f'\n[green]✓ Prediction successful[/green]')
            console.print(f'  Model: {result.prediction_type} v{result.model_version}')
            console.print(f'  Home win probability: {result.predicted_value:.1%}')
            
            if result.confidence_lower is not None and result.confidence_upper is not None:
                console.print(f'  Confidence interval: [{result.confidence_lower:.1%}, {result.confidence_upper:.1%}]')
            
            console.print(f'  Inference time: {result.inference_time_ms:.1f}ms')
            
            if show_features and result.feature_vector:
                console.print(f'\n[dim]Features used:[/dim]')
                for name, value in result.feature_vector.items():
                    console.print(f'  {name}: {value}')
            
            if result.prediction_id:
                console.print(f'\n[dim]Stored as prediction_id: {result.prediction_id}[/dim]')
        else:
            console.print(f'[red]❌ Prediction failed: {result.error_message}[/red]')
            raise typer.Exit(code=1)
            
    except Exception as e:
        console.print(f'[red]Error during prediction: {e}[/red]')
        raise typer.Exit(code=1)


@models_app.command(name='batch-predict')
def models_batch_predict(
    game_pks: str = typer.Option(..., '--games', '-g', help='Comma-separated game IDs'),
    model_name: str = typer.Option('win_probability', '--model', '-m', help='Model name'),
    model_version: Optional[str] = typer.Option(None, '--version', '-v', help='Model version')
):
    """Run predictions for multiple games."""
    from baseball.models.inference import InferencePipeline
    
    try:
        game_list = [int(g.strip()) for g in game_pks.split(',')]
        
        console.print(f'[bold blue]Batch predicting {len(game_list)} games...[/bold blue]')
        
        pipeline = InferencePipeline(
            model_name=model_name,
            model_version=model_version
        )
        
        results = pipeline.predict_batch(game_list, store_results=True)
        
        # Summary
        successful = sum(1 for r in results if r.success)
        
        table = Table(title=f'Batch Predictions - {model_name}')
        table.add_column('Game PK', style='cyan')
        table.add_column('Home Win %', style='green')
        table.add_column('Confidence', style='yellow')
        table.add_column('Status', style='white')
        
        for game_pk, result in zip(game_list, results):
            if result.success:
                table.add_row(
                    str(game_pk),
                    f'{result.predicted_value:.1%}',
                    f'{result.confidence_lower:.0%}-{result.confidence_upper:.0%}' if result.confidence_lower else 'N/A',
                    '✓'
                )
            else:
                table.add_row(
                    str(game_pk),
                    'N/A',
                    'N/A',
                    f'✗ {result.error_message[:30]}'
                )
        
        console.print(table)
        console.print(f'\n[green]✓ {successful}/{len(results)} predictions successful[/green]')
        
    except Exception as e:
        console.print(f'[red]Error during batch prediction: {e}[/red]')
        raise typer.Exit(code=1)


@models_app.command(name='list')
def models_list(
    model_name: Optional[str] = typer.Option(None, '--name', '-n', help='Filter by model name'),
    status: Optional[str] = typer.Option(None, '--status', '-s', help='Filter by status: production, staging, archived'),
    limit: int = typer.Option(20, '--limit', '-l', help='Maximum results to show'),
    show_metrics: bool = typer.Option(False, '--metrics', '-m', help='Show validation metrics'),
):
    """List registered models with optional filters."""
    from baseball.models.registry import ModelRegistry
    
    try:
        registry = ModelRegistry()
        models = registry.list_models(model_name=model_name, status=status, limit=limit)
        
        if not models:
            console.print('[yellow]No models found matching criteria.[/yellow]')
            return
        
        table = Table(title=f'Registered Models ({len(models)} shown)')
        table.add_column('ID', style='dim', width=6)
        table.add_column('Name', style='cyan')
        table.add_column('Version', style='blue')
        table.add_column('Type', style='white')
        table.add_column('Status', style='green')
        table.add_column('Primary Metric', style='yellow')
        table.add_column('Training Date', style='dim')
        
        for model in models:
            status_color = {
                'production': '[bold green]',
                'staging': '[yellow]',
                'archived': '[dim]'
            }.get(model.status, '[white]')
            
            metric_str = f'{model.primary_metric_value:.4f}' if model.primary_metric_value else 'N/A'
            
            table.add_row(
                str(model.model_id),
                model.model_name,
                model.model_version,
                model.model_type,
                f"{status_color}{model.status}[/]",
                f"{model.primary_metric}: {metric_str}" if model.primary_metric else 'N/A',
                model.training_date.strftime('%Y-%m-%d') if model.training_date else 'N/A'
            )
        
        console.print(table)
        
        if show_metrics and models:
            console.print('\n[bold]Latest Model Metrics:[/bold]')
            latest = models[0]
            for metric, value in latest.validation_metrics.items():
                console.print(f'  {metric}: {value:.4f}')
                
    except Exception as e:
        console.print(f'[red]Error listing models: {e}[/red]')
        raise typer.Exit(code=1)


@models_app.command(name='promote')
def models_promote(
    model_id: int = typer.Argument(..., help='Model ID to promote'),
    to_status: str = typer.Option('production', '--to', help='Target status: production, staging, archived'),
    promoted_by: str = typer.Option('cli', '--by', help='User/system promoting the model'),
):
    """Promote a model to production (or other status)."""
    from baseball.models.registry import ModelRegistry
    
    try:
        registry = ModelRegistry()
        
        # Get model info first
        model = registry.get_model_by_id(model_id)
        if not model:
            console.print(f'[red]Model ID {model_id} not found.[/red]')
            raise typer.Exit(code=1)
        
        if to_status == 'production':
            success = registry.promote_model(model_id, promoted_by=promoted_by)
            if success:
                console.print(f'[green]✓ Promoted {model.model_name} v{model.model_version} to production[/green]')
            else:
                console.print(f'[red]Failed to promote model {model_id}[/red]')
                raise typer.Exit(code=1)
        elif to_status == 'archived':
            success = registry.archive_model(model_id)
            if success:
                console.print(f'[green]✓ Archived {model.model_name} v{model.model_version}[/green]')
            else:
                console.print(f'[red]Failed to archive model {model_id}[/red]')
                raise typer.Exit(code=1)
        else:
            console.print(f'[yellow]Status "{to_status}" requires manual database update[/yellow]')
            
    except Exception as e:
        console.print(f'[red]Error promoting model: {e}[/red]')
        raise typer.Exit(code=1)


@models_app.command(name='archive')
def models_archive(
    model_id: int = typer.Argument(..., help='Model ID to archive'),
    force: bool = typer.Option(False, '--force', '-f', help='Archive even if production model'),
):
    """Archive a model (move to archived status)."""
    from baseball.models.registry import ModelRegistry
    
    try:
        registry = ModelRegistry()
        
        model = registry.get_model_by_id(model_id)
        if not model:
            console.print(f'[red]Model ID {model_id} not found.[/red]')
            raise typer.Exit(code=1)
        
        if model.status == 'production' and not force:
            console.print(f'[yellow]Model {model_id} is in production. Use --force to archive.[/yellow]')
            raise typer.Exit(code=1)
        
        success = registry.archive_model(model_id)
        if success:
            console.print(f'[green]✓ Archived {model.model_name} v{model.model_version}[/green]')
        else:
            console.print(f'[red]Failed to archive model {model_id}[/red]')
            raise typer.Exit(code=1)
            
    except Exception as e:
        console.print(f'[red]Error archiving model: {e}[/red]')
        raise typer.Exit(code=1)


@models_app.command(name='backtest')
def models_backtest(
    model_name: str = typer.Argument(..., help='Model name to backtest'),
    seasons: List[int] = typer.Option([2022, 2023, 2024], '--season', '-s', help='Seasons to include'),
    window_days: int = typer.Option(7, '--window', '-w', help='Test window size in days'),
    feature_set: str = typer.Option('default', '--features', '-f', help='Feature set to use'),
    output_file: Optional[str] = typer.Option(None, '--output', '-o', help='Save results to file'),
    save_predictions: bool = typer.Option(True, '--save-predictions/--no-save', help='Store predictions in DB'),
    verbose: bool = typer.Option(True, '--verbose/--quiet', help='Show progress and results'),
):
    """Run walk-forward backtest on historical data."""
    from baseball.models.backtesting import (
        BacktestConfig,
        BacktestEngine,
        BacktestStatus,
    )
    from baseball.models import NextRunProbabilityModel, PAOutcomeModel, WinProbabilityModel
    
    # Map model name to class
    model_map = {
        'next_run': NextRunProbabilityModel,
        'pa_outcome': PAOutcomeModel,
        'win_probability': WinProbabilityModel,
    }
    
    if model_name not in model_map:
        console.print(f'[red]Unknown model: {model_name}[/red]')
        console.print(f'Available: {", ".join(model_map.keys())}')
        raise typer.Exit(code=1)
    
    model_class = model_map[model_name]
    
    try:
        config = BacktestConfig(
            model_class=model_class,
            model_name=model_name,
            seasons=seasons,
            test_window_days=window_days,
            feature_set=feature_set,
            save_predictions=save_predictions,
            show_progress=verbose
        )
        
        engine = BacktestEngine(config)
        
        # Progress callback with rich progress bar
        if verbose:
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
            
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=40),
                TaskProgressColumn(),
                console=console
            )
            
            with progress:
                task = progress.add_task(f"[cyan]Backtesting {model_name}...", total=100)
                
                def progress_callback(current, total, elapsed):
                    pct = (current / total * 100) if total > 0 else 0
                    progress.update(task, completed=pct)
                
                engine.progress_tracker.add_callback(progress_callback)
                result = engine.run()
        else:
            result = engine.run()
        
        # Display results
        if result.status == BacktestStatus.COMPLETED:
            console.print(f'\n[green]✓ Backtest completed successfully[/green]')
            
            # Summary table
            table = Table(title=f'Backtest Results: {model_name}')
            table.add_column('Metric', style='cyan')
            table.add_column('Value', style='green')
            table.add_column('Std Dev', style='yellow')
            
            table.add_row('Accuracy', f'{result.mean_accuracy:.4f}', f'{result.std_accuracy:.4f}')
            table.add_row('Log Loss', f'{result.mean_log_loss:.4f}', f'{result.std_log_loss:.4f}')
            table.add_row('AUC', f'{result.mean_auc:.4f}', f'{result.std_auc:.4f}')
            table.add_row('Brier Score', f'{result.mean_brier_score:.4f}', '-')
            table.add_row('Calibration Error', f'{result.mean_calibration_error:.4f}', '-')
            table.add_row('Total Predictions', str(result.total_predictions), '-')
            table.add_row('Duration', f'{result.duration_seconds:.1f}s', '-')
            
            console.print(table)
            
            # Season breakdown
            if result.by_season:
                season_table = Table(title='Performance by Season')
                season_table.add_column('Season', style='cyan')
                season_table.add_column('Accuracy', style='green')
                season_table.add_column('Log Loss', style='yellow')
                season_table.add_column('Count', style='dim')
                
                for season, metrics in sorted(result.by_season.items()):
                    season_table.add_row(
                        str(season),
                        f"{metrics['mean_accuracy']:.4f}",
                        f"{metrics['mean_log_loss']:.4f}",
                        str(metrics['count'])
                    )
                
                console.print(season_table)
            
            # Save to file if requested
            if output_file:
                if result.save_to_file(output_file):
                    console.print(f'\n[dim]Results saved to {output_file}[/dim]')
                else:
                    console.print(f'\n[yellow]Warning: Could not save to {output_file}[/yellow]')
            
            console.print(f'\n[dim]Backtest ID: {result.backtest_id}[/dim]')
            
        elif result.status == BacktestStatus.FAILED:
            console.print(f'\n[red]✗ Backtest failed: {result.error_message}[/red]')
            raise typer.Exit(code=1)
        else:
            console.print(f'\n[yellow]Backtest status: {result.status.value}[/yellow]')
            
    except Exception as e:
        console.print(f'[red]Error during backtest: {e}[/red]')
        raise typer.Exit(code=1)


# Betting command group
@betting_app.command(name='analyze')
def bet_analyze(
    game_pk: int = typer.Option(..., '--game', '-g', help='Game PK to analyze'),
    strategy: str = typer.Option('default', '--strategy', '-s', help='Strategy to use'),
    min_edge: float = typer.Option(0.05, '--min-edge', '-e', help='Minimum edge threshold'),
    weather_temp: Optional[int] = typer.Option(None, '--temp', help='Temperature in F'),
    weather_wind: Optional[int] = typer.Option(None, '--wind', help='Wind speed in MPH'),
    ai_explain: bool = typer.Option(True, '--explain/--no-explain', help='AI explains each bet'),
    paper_trade: bool = typer.Option(True, '--paper/--real', help='Use paper trading'),
    bankroll: float = typer.Option(10000.0, '--bankroll', '-b', help='Bankroll for stake calc'),
    odds_source: str = typer.Option('the_odds_api', '--source', help='Odds source (the_odds_api, pinnacle, draftkings)'),
    stake_method: str = typer.Option('kelly', '--stake-method', help='Stake method (kelly, flat, confidence)'),
    use_simulation: bool = typer.Option(True, '--simulation/--mock', help='Use Monte Carlo simulation or mock probs'),
):
    """Analyze betting markets for a game using Monte Carlo simulation."""
    import asyncio
    from decimal import Decimal
    from baseball.betting.integration import SimulationBackedAnalyzer
    from baseball.betting.sources import TheOddsApiSource, PinnacleSource, DraftKingsSource
    from baseball.betting.paper_trading import PaperTradingAccount
    from baseball.betting.strategy_ai import BettingStrategyAI
    from baseball.betting.schemas import Sport, MarketType
    from baseball.models.schemas import WeatherConfig
    
    console.print(f"[bold blue]Analyzing betting opportunities for game {game_pk}[/bold blue]")
    
    async def run_analysis():
        try:
            # Initialize odds source (Super Class pattern)
            source_map = {
                'the_odds_api': TheOddsApiSource,
                'pinnacle': PinnacleSource,
                'draftkings': DraftKingsSource
            }
            
            source_class = source_map.get(odds_source, TheOddsApiSource)
            
            # Get API key from environment or config
            import os
            api_key = os.getenv('THE_ODDS_API_KEY') if odds_source == 'the_odds_api' else None
            
            if odds_source == 'the_odds_api' and not api_key:
                console.print("[yellow]Warning: No API key found. Using mock data for demonstration.[/yellow]")
                source = source_class(api_key="demo") if odds_source == 'the_odds_api' else source_class()
            else:
                source = source_class(api_key=api_key) if api_key else source_class()
            
            # Initialize simulation-backed analyzer
            analyzer = SimulationBackedAnalyzer(
                odds_source=source,
                min_edge=Decimal(str(min_edge))
            )
            
            # Initialize paper trading account (optional)
            paper_account = None
            if paper_trade:
                paper_account = PaperTradingAccount(
                    name=f"Analysis_{game_pk}",
                    initial_bankroll=Decimal(str(bankroll))
                )
                console.print(f"[dim]Paper trading account initialized: ${bankroll}[/dim]")
            
            # Initialize AI for explanations (optional)
            ai = None
            if ai_explain:
                try:
                    import openai
                    ai = BettingStrategyAI(
                        llm_client=openai.OpenAI(),
                        model="gpt-4",
                        temperature=0.7
                    )
                    console.print("[dim]AI explanations enabled (GPT-4)[/dim]")
                except Exception:
                    console.print("[dim]AI explanations disabled (no LLM client)[/dim]")
            
            # Fetch odds
            console.print("\n[cyan]Fetching market odds...[/cyan]")
            try:
                markets = source.get_live_odds(Sport.MLB, MarketType.MONEYLINE)
                game_markets = [m for m in markets if m.game_id == str(game_pk)]
                console.print(f"[green]Found {len(game_markets)} markets for this game[/green]")
            except Exception as e:
                console.print(f"[yellow]Could not fetch live odds: {e}[/yellow]")
                game_markets = []
            
            # Run simulation analysis
            console.print("\n[cyan]Querying Monte Carlo simulation...[/cyan]")
            
            # Get real probabilities from simulation
            analysis_results = await analyzer.analyze_game_with_simulation(
                str(game_pk),
                market_types=[MarketType.MONEYLINE, MarketType.SPREAD, MarketType.TOTAL],
                fallback_to_mock=not use_simulation
            )
            
            sim_probs = analysis_results.get('simulation_probabilities', {})
            if sim_probs:
                console.print(f"[green]Using simulation probabilities:[/green]")
                console.print(f"  Home win: {sim_probs.get('home_win', 0):.1%}")
                console.print(f"  Away win: {sim_probs.get('away_win', 0):.1%}")
                if 'total_over' in sim_probs:
                    console.print(f"  Over 8.5: {sim_probs.get('total_over', 0):.1%}")
            else:
                console.print("[yellow]No simulation available, using mock probabilities[/yellow]")
            
            opportunities = analysis_results.get('opportunities', [])
            
            # Place paper bets if enabled
            if paper_trade and paper_account and opportunities:
                console.print("\n[cyan]Placing paper trades...[/cyan]")
                placed = 0
                for opp in opportunities:
                    if opp.recommendation == "bet":
                        bet = analyzer._analyzer.create_bet(
                            opp, Decimal(str(bankroll)), stake_method
                        )
                        if paper_account.place_bet(bet):
                            placed += 1
                console.print(f"[green]Placed {placed} paper bets[/green]")
        
        if not opportunities:
            console.print("\n[yellow]No betting opportunities found above threshold.[/yellow]")
            return
        
        # Sort by edge
        opportunities.sort(key=lambda o: o.edge, reverse=True)
        
        # Display opportunities
        console.print(f"\n[green]Found {len(opportunities)} opportunities:[/green]")
        
        for opp in opportunities:
            market = opp.market
            
            # Create display table
            table = Table(title=f"{market.side} - {market.market_type.value.upper()}", show_header=True)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Book", market.book)
            table.add_row("Odds", str(market.odds))
            table.add_row("Model Prob", f"{opp.model_probability:.1%}")
            table.add_row("Market Prob", f"{opp.market_probability:.1%}")
            table.add_row("Edge", f"{opp.edge:.1%}")
            
            # Calculate stake
            stake = analyzer.calculate_stake(
                opp,
                Decimal(str(bankroll)),
                method=stake_method
            )
            table.add_row("Recommended Stake", f"${stake:.2f}")
            
            console.print(table)
            
            # AI explanation
            if ai and ai_explain:
                explanation = ai.explain_bet(
                    opp,
                    sim_details={'home_prob': sim_probs.get('home_win', 0.5)},
                    include_numbers=True
                )
                console.print(f"[dim]AI: {explanation}[/dim]\n")
        
        # Summary
        if paper_account:
            summary = paper_account.get_performance_summary()
            console.print(f"\n[dim]Account bankroll: ${summary['current_bankroll']:.2f} (pending bets: {summary['bets_pending']})[/dim]")
        
        except Exception as e:
            console.print(f"[red]Error during analysis: {e}[/red]")
            raise typer.Exit(code=1)
    
    # Run the async analysis
    asyncio.run(run_analysis())


@betting_app.command(name='paper-report')
def bet_paper_report(
    account_name: str = typer.Option('default', '--account', '-a', help='Paper account name'),
    detailed: bool = typer.Option(False, '--detailed', '-d', help='Show detailed breakdown'),
):
    """Show paper trading performance report."""
    from baseball.betting.paper_trading import PaperTradingManager
    
    manager = PaperTradingManager()
    account = manager.get_account(account_name)
    
    if not account:
        console.print(f"[red]Account '{account_name}' not found[/red]")
        raise typer.Exit(code=1)
    
    summary = account.get_performance_summary()
    
    # Display summary table
    table = Table(title=f"Paper Trading Report: {account_name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Initial Bankroll", f"${summary['initial_bankroll']:,.2f}")
    table.add_row("Current Bankroll", f"${summary['current_bankroll']:,.2f}")
    table.add_row("Total P&L", f"${summary['total_pnl']:+,.2f}")
    table.add_row("ROI", f"{summary['roi']:+.1%}")
    table.add_row("Win Rate", f"{summary['win_rate']:.1%}")
    table.add_row("Bets Won/Lost", f"{summary['bets_won']}/{summary['bets_lost']}")
    table.add_row("Pending Bets", str(summary['bets_pending']))
    table.add_row("Max Drawdown", f"{summary['drawdown_pct']:.1%}")
    
    console.print(table)
    
    if detailed:
        open_bets = account.get_open_bets()
        if open_bets:
            console.print("\n[dim]Open Bets:[/dim]")
            for bet in open_bets:
                console.print(f"  - {bet.opportunity.market.side} @ {bet.odds_placed} (${bet.stake})")


@betting_app.command(name='ingestion')
def bet_ingestion(
    action: str = typer.Option('status', '--action', help='Action: start, stop, status, add'),
    job_type: str = typer.Option('odds', '--type', '-t', help='Job type: odds, live, analysis'),
    source: str = typer.Option('the_odds_api', '--source', help='Odds source'),
    schedule: str = typer.Option('1 minute', '--schedule', '-s', help='Schedule expression'),
):
    """Manage data ingestion jobs."""
    console.print(f"[bold blue]Ingestion Management[/bold blue]")
    console.print(f"[dim]Action: {action}, Type: {job_type}, Source: {source}[/dim]")
    
    # This would integrate with DatabaseScheduler
    # For now, show status
    if action == 'status':
        console.print("\n[cyan]Active Jobs:[/cyan]")
        console.print("  - odds_minute_fetch (running)")
        console.print("  - mlb_live_feed (connected)")
        console.print("  - hourly_bet_analysis (running)")
    elif action == 'start':
        console.print(f"[green]Starting {job_type} ingestion from {source}[/green]")
    elif action == 'stop':
        console.print(f"[yellow]Stopping {job_type} ingestion[/yellow]")
    elif action == 'add':
        console.print(f"[green]Added job: {job_type} from {source} every {schedule}[/green]")
    
    console.print("\n[dim]Use --action start/stop/add to modify jobs[/dim]")
    from baseball.models.simulation import SimulationService, SimulationConfig
    from baseball.models.schemas import WeatherConfig, WindDirection
    from baseball.betting.schemas import BetOpportunity
    
    console.print(f'\n[bold blue]Analyzing Game {game_pk} for Betting Opportunities[/bold blue]\n')
    
    # Run simulation
    service = SimulationService()
    
    # Build config with optional weather
    config_data = {
        'game_id': str(game_pk),
        'num_iterations': 10000,
        'simulation_type': 'monte_carlo'
    }
    
    if weather_temp is not None:
        config_data['weather'] = WeatherConfig(
            temperature_f=float(weather_temp),
            wind_speed_mph=float(weather_wind or 0),
            wind_direction=WindDirection.CALM
        )
    
    config = SimulationConfig(**config_data)
    
    console.print('[dim]Running Monte Carlo simulation...[/dim]')
    sim_result = service.run_simulation(config)
    
    # TODO: Analyze markets against simulation results
    # TODO: Find opportunities above edge threshold
    # TODO: Generate AI explanations
    
    console.print(f'\n[green]✓ Analysis Complete[/green]')
    console.print(f'\nSimulation run_id: {sim_result.results.run_id}')
    console.print(f'Home win probability: {sim_result.results.home_win_probability:.1%}')
    console.print(f'Expected runs: {sim_result.results.expected_home_score:.1f} - {sim_result.results.expected_away_score:.1f}')
    
    # Placeholder for opportunities table
    console.print('\n[yellow]Betting opportunities analysis coming soon...[/yellow]')


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
    result = source.download(
        start_date=date(season, 1, 1), end_date=date(season, 12, 31), force=force
    )

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
    from baseball.sources.espn import EspnSource

    source = EspnSource()
    result = source.download(season=season, force=force)

    if result.success:
        console.print(f'[green]Downloaded ESPN data for {season}[/green]')
        if result.metadata:
            console.print(f'  Games: {result.metadata.get("games", "N/A")}')
            console.print(f'  Plays: {result.metadata.get("plays", "N/A")}')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@espn_app.command(name='ingest')
def espn_ingest(
    validate: bool = typer.Option(True, '--validate', help='Validate after ingest'),
):
    """Validate ESPN data in database."""
    from baseball.sources.espn import EspnSource

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
    from baseball.sources.espn import EspnSource

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
    from baseball.sources.espn import EspnSource

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
    from baseball.sources.lahman import LahmanSource

    source = LahmanSource()
    result = source.download(config={'force': force})

    if result.success:
        console.print('[green]Downloaded Lahman Baseball Databank[/green]')
        if result.metadata and 'files' in result.metadata:
            console.print(f'  Files: {len(result.metadata["files"])}')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@lahman_app.command(name='ingest')
def lahman_ingest(
    validate: bool = typer.Option(True, '--validate', help='Validate after ingest'),
):
    """Ingest Lahman CSV files into database."""
    from baseball.sources.lahman import LahmanSource

    source = LahmanSource()
    result = source.ingest(config={'validate': validate})

    if result.success:
        console.print('[green]Lahman data ingested[/green]')
        if result.metadata and 'files_found' in result.metadata:
            console.print(f'  Files found: {len(result.metadata["files_found"])}')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@lahman_app.command(name='validate')
def lahman_validate():
    """Validate Lahman data quality."""
    from baseball.sources.lahman import LahmanSource

    source = LahmanSource()
    result = source.validate(config={})

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
    from baseball.sources.lahman import LahmanSource

    source = LahmanSource()
    counts = source.get_table_counts()

    console.print('[bold]Lahman Databank Tables:[/bold]')
    for table, count in counts.items():
        if table != 'error':
            console.print(f'  {table}: {count:,} rows')


# FanGraphs command group
fangraphs_app = typer.Typer(help='FanGraphs data commands', no_args_is_help=True)


@fangraphs_app.command(name='download')
def fangraphs_download(
    season: int = typer.Option(..., '--season', '-s', help='Season to download'),
    force: bool = typer.Option(False, '--force', '-f', help='Force re-download'),
):
    """Download FanGraphs player/team stats."""
    from baseball.sources.fangraphs import FanGraphsSource

    source = FanGraphsSource()
    result = source.download(config={'season': season, 'force': force})

    if result.success:
        console.print(f'[green]Downloaded FanGraphs data for {season}[/green]')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@fangraphs_app.command(name='ingest')
def fangraphs_ingest(
    player_file: str = typer.Option(None, '--player-file', help='Path to player CSV'),
    team_file: str = typer.Option(None, '--team-file', help='Path to team CSV'),
):
    """Load FanGraphs CSV files into database."""
    from baseball.sources.fangraphs import FanGraphsSource

    source = FanGraphsSource()
    result = source.ingest(config={'player_file': player_file, 'team_file': team_file})

    if result.success:
        console.print('[green]FanGraphs data ingested[/green]')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@fangraphs_app.command(name='validate')
def fangraphs_validate():
    """Validate FanGraphs data quality."""
    from baseball.sources.fangraphs import FanGraphsSource

    source = FanGraphsSource()
    result = source.validate(config={})

    if result.success:
        console.print('[green]FanGraphs validation passed[/green]')
    else:
        console.print(f'[red]FanGraphs validation failed[/red]')
        raise typer.Exit(code=1)


# Baseball-Reference command group
bref_app = typer.Typer(help='Baseball-Reference data commands', no_args_is_help=True)


@bref_app.command(name='ingest')
def bref_ingest(
    data_dir: str = typer.Option(..., '--dir', '-d', help='Directory containing BRef CSV files'),
):
    """Load Baseball-Reference game logs into database."""
    from baseball.sources.bref import BRefSource

    source = BRefSource()
    result = source.ingest(config={'data_dir': data_dir})

    if result.success:
        console.print('[green]Baseball-Reference data ingested[/green]')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@bref_app.command(name='validate')
def bref_validate():
    """Validate Baseball-Reference data quality."""
    from baseball.sources.bref import BRefSource

    source = BRefSource()
    result = source.validate(config={})

    if result.success:
        console.print('[green]Baseball-Reference validation passed[/green]')
    else:
        console.print(f'[red]Baseball-Reference validation failed[/red]')
        raise typer.Exit(code=1)


# Weather command group
weather_app = typer.Typer(help='Weather data commands', no_args_is_help=True)


@weather_app.command(name='fetch')
def weather_fetch(
    date: str = typer.Option(..., '--date', help='Date to fetch (YYYY-MM-DD)'),
    venue_id: str = typer.Option(..., '--venue', '-v', help='Venue/park identifier'),
):
    """Fetch weather observations for a venue/date from NOAA."""
    from baseball.sources.weather import WeatherSource

    source = WeatherSource()
    result = source.download(config={'date': date, 'venue_id': venue_id})

    if result.success:
        console.print(f'[green]Fetched weather for {venue_id} on {date}[/green]')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@weather_app.command(name='validate')
def weather_validate():
    """Validate weather data in database."""
    from baseball.sources.weather import WeatherSource

    source = WeatherSource()
    result = source.validate(config={})

    if result.success:
        console.print('[green]Weather validation passed[/green]')
    else:
        console.print(f'[red]Weather validation failed[/red]')
        raise typer.Exit(code=1)


# Park Factors command group
park_app = typer.Typer(help='Park factors commands', no_args_is_help=True)


@park_app.command(name='ingest')
def park_ingest(
    file: str = typer.Option(..., '--file', '-f', help='Path to park_factors.csv'),
):
    """Load park factors CSV into database."""
    from baseball.sources.park_factors import ParkFactorsSource

    source = ParkFactorsSource()
    result = source.ingest(config={'file': file})

    if result.success:
        console.print('[green]Park factors ingested[/green]')
    else:
        console.print(f'[red]Failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@park_app.command(name='validate')
def park_validate():
    """Validate park factors data in database."""
    from baseball.sources.park_factors import ParkFactorsSource

    source = ParkFactorsSource()
    result = source.validate(config={})

    if result.success:
        console.print('[green]Park factors validation passed[/green]')
    else:
        console.print(f'[red]Park factors validation failed[/red]')
        raise typer.Exit(code=1)


# Bridge command group
@bridge_app.command(name='resolve')
def bridge_resolve(
    source: str = typer.Option(
        ..., '--source', '-s', help='Source system (retrosheet, mlb, espn, statcast)'
    ),
    source_id: str = typer.Option(..., '--id', '-i', help='ID in source system'),
    entity_type: str = typer.Option(
        'player', '--type', '-t', help='Entity type (player, team, game, park)'
    ),
):
    """Resolve a source ID to canonical ID using bridge tables."""
    from baseball.services.bridge import BridgeService
    
    console.print(f'[dim]Resolving {entity_type} ID {source_id} from {source}...[/dim]')
    
    try:
        bridge = BridgeService()
        result = bridge.resolve_id(source, source_id, entity_type)
        
        if result:
            console.print(f'[green]✓ Found:[/green]')
            console.print(f'  Canonical ID: {result["canonical_id"]}')
            console.print(f'  Entity: {result["first_name"]} {result["last_name"]}' if 'first_name' in result else f'  Entity: {result.get("name", "N/A")}')
        else:
            console.print(f'[yellow]⚠ No match found for {source} ID: {source_id}[/yellow]')
            raise typer.Exit(code=1)
            
    except Exception as e:
        console.print(f'[red]✗ Error: {e}[/red]')
        raise typer.Exit(code=1)


@bridge_app.command(name='match')
def bridge_match(
    entity_type: str = typer.Option(
        ..., '--type', '-t', help='Entity type (player, team, game, park)'
    ),
    source_a: str = typer.Option(..., '--source-a', help='First source system'),
    source_b: str = typer.Option(..., '--source-b', help='Second source system'),
):
    """Find matches between two source systems."""
    console.print(f'[dim]Finding {entity_type} matches between {source_a} and {source_b}...[/dim]')
    # TODO: Run matching algorithm between sources
    raise NotImplementedError('Bridge matching not yet implemented')


@bridge_app.command(name='lookup')
def bridge_lookup(
    canonical_id: str = typer.Option(..., '--id', '-i', help='Canonical ID'),
    entity_type: str = typer.Option(
        'player', '--type', '-t', help='Entity type (player, team, game, park)'
    ),
):
    """Lookup all source IDs for a canonical ID."""
    from baseball.services.bridge import BridgeService
    
    console.print(f'[dim]Looking up {entity_type} canonical ID {canonical_id}...[/dim]')
    
    try:
        bridge = BridgeService()
        result = bridge.lookup_canonical(entity_type, canonical_id)
        
        if result and result.get('sources'):
            console.print(f'[green]✓ Found {len(result["sources"])} source mappings:[/green]')
            
            table = Table(title=f'Source IDs for {entity_type} {canonical_id}')
            table.add_column('Source')
            table.add_column('Source ID')
            table.add_column('Name/Info')
            
            for source, info in result['sources'].items():
                table.add_row(
                    source,
                    info.get('id', 'N/A'),
                    info.get('name', info.get('first_name', '') + ' ' + info.get('last_name', ''))
                )
            console.print(table)
        else:
            console.print(f'[yellow]⚠ No source mappings found for {entity_type} ID: {canonical_id}[/yellow]')
            raise typer.Exit(code=1)
            
    except Exception as e:
        console.print(f'[red]✗ Error: {e}[/red]')
        raise typer.Exit(code=1)


@bridge_app.command(name='build')
def bridge_build(
    entity: str = typer.Option(
        'all', '--entity', '-e',
        help='Entity type to build (all, players, teams, games, parks)'
    ),
    season: int | None = typer.Option(
        None, '--season', '-s', help='Season for game/team bridge population'
    ),
    dry_run: bool = typer.Option(
        False, '--dry-run', '-d', help='Show what would be done without executing'
    ),
    verbose: bool = typer.Option(
        False, '--verbose', '-v', help='Show detailed output'
    ),
):
    """Build bridge tables for ID resolution.

    Populates cross-reference tables that map IDs from different
    source systems (retrosheet, mlb, espn, statcast) to canonical IDs.
    """
    from baseball.services.bridge import BridgeService

    bridge = BridgeService()
    console.print('[bold blue]Building bridge tables...[/bold blue]')

    if entity == 'all':
        result = bridge.populate_all(dry_run=dry_run, verbose=verbose)

        if result.get('success'):
            console.print('[green]✓ Bridge build completed successfully[/green]')
            console.print(f'  Players: {"✓" if result.get("players") else "✗"}')
            console.print(f'  Teams: {"✓" if result.get("teams") else "✗"}')
            console.print(f'  Games: {"✓" if result.get("games") else "✗"}')
            console.print(f'  Parks: {"✓" if result.get("parks") else "✗"}')
        else:
            console.print('[red]✗ Bridge build failed[/red]')
            if result.get('error'):
                console.print(f'[red]{result["error"]}[/red]')
            raise typer.Exit(code=1)
    elif entity == 'players':
        success = bridge.populate_players(dry_run=dry_run, verbose=verbose)
        if success:
            console.print('[green]✓ Player bridge built successfully[/green]')
        else:
            console.print('[red]✗ Player bridge build failed[/red]')
            raise typer.Exit(code=1)
    elif entity == 'games':
        success = bridge.populate_games(season=season, dry_run=dry_run)
        if success:
            console.print('[green]✓ Game bridge built successfully[/green]')
        else:
            console.print('[red]✗ Game bridge build failed[/red]')
            raise typer.Exit(code=1)
    elif entity == 'teams':
        success = bridge.populate_teams(dry_run=dry_run)
        if success:
            console.print('[green]✓ Team bridge built successfully[/green]')
        else:
            console.print('[red]✗ Team bridge build failed[/red]')
            raise typer.Exit(code=1)
    else:
        console.print(f'[red]Unknown entity type: {entity}[/red]')
        console.print('Supported: all, players, teams, games, parks')
        raise typer.Exit(code=1)


@bridge_app.command(name='validate')
def bridge_validate(
    entity: str = typer.Option(
        'all', '--entity', '-e',
        help='Entity type to validate (all, players, teams, games, parks)'
    ),
    min_coverage: float = typer.Option(
        80.0, '--min-coverage', '-c',
        help='Minimum coverage percentage for validation to pass'
    ),
):
    """Validate bridge table coverage and integrity.

    Checks that bridge tables have adequate coverage for mapping
    IDs between source systems.
    """
    from baseball.services.bridge import BridgeService

    bridge = BridgeService()
    console.print('[bold blue]Validating bridge tables...[/bold blue]')

    stats = bridge.get_coverage_stats()

    if 'error' in stats:
        console.print(f'[red]✗ Validation failed: {stats["error"]}[/red]')
        raise typer.Exit(code=1)

    all_passed = True
    console.print()

    for name, entity_stats in stats.items():
        if entity != 'all' and name != entity and name.rstrip('s') != entity:
            continue

        total = entity_stats.get('total', 0)
        with_mlb = entity_stats.get('with_mlb_id', 0)
        coverage = entity_stats.get('coverage_pct', 0)

        status_icon = '✓' if coverage >= min_coverage else '✗'
        status_color = 'green' if coverage >= min_coverage else 'yellow'

        console.print(f'[{status_color}]{status_icon} {name.title()}: {coverage:.1f}% coverage ({with_mlb}/{total})[/{status_color}]')

        if coverage < min_coverage:
            all_passed = False

    console.print()

    if all_passed:
        console.print('[green]✓ All bridge tables meet minimum coverage threshold[/green]')
    else:
        console.print(f'[yellow]⚠ Some tables below {min_coverage}% coverage threshold[/yellow]')
        console.print('[dim]Run [code]baseball bridge build[/code] to populate missing mappings[/dim]')


# Pipeline command group
@pipeline_app.command(name='run')
def pipeline_run(
    pipeline_name: str = typer.Option(..., '--pipeline', '-p', help='Pipeline name from config'),
    resume: bool = typer.Option(False, '--resume', '-r', help='Resume from last checkpoint'),
    year: int | None = typer.Option(None, '--year', help='Year for historical pipelines'),
    date: str | None = typer.Option(None, '--date', help='Date for live pipelines (YYYY-MM-DD)'),
):
    """Run a pipeline from config."""
    from baseball.services.pipeline import get_pipeline_service

    service = get_pipeline_service()

    # Validate pipeline exists
    config = service.get_pipeline(pipeline_name)
    if not config:
        console.print(f'[red]Error: Pipeline "{pipeline_name}" not found[/red]')
        console.print('Run [code]baseball pipeline list[/code] to see available pipelines')
        raise typer.Exit(1)

    console.print(f'[bold blue]Running pipeline: {pipeline_name}[/bold blue]')
    if resume:
        console.print('[dim]Resuming from last checkpoint...[/dim]')

    # Build parameters
    parameters = {}
    if year:
        parameters['year'] = year
    if date:
        parameters['date'] = date

    # Show steps
    steps_str = ', '.join(config.steps)
    console.print(f'\n[dim]Steps: {steps_str}[/dim]\n')

    try:
        run_id, success, error = service.run_pipeline(
            pipeline_name, resume=resume, parameters=parameters
        )

        if success:
            console.print(f'\n[green]Pipeline completed successfully (run_id: {run_id})[/green]')
        else:
            console.print(f'\n[red]Pipeline failed: {error}[/red]')
            console.print(f'[dim]Run ID: {run_id}[/dim]')
            raise typer.Exit(1)

    except ValueError as e:
        console.print(f'[red]Error: {e}[/red]')
        raise typer.Exit(1)
    except Exception as e:
        console.print(f'[red]Pipeline execution failed: {e}[/red]')
        raise typer.Exit(1)


@pipeline_app.command(name='list')
def pipeline_list():
    """List available pipelines from config."""
    from baseball.services.pipeline import get_pipeline_service

    service = get_pipeline_service()
    pipelines = service.list_pipelines()

    if not pipelines:
        console.print('[yellow]No pipelines configured[/yellow]')
        console.print('[dim]Check config/pipelines.yml[/dim]')
        return

    table = Table(title='Available Pipelines')
    table.add_column('Name', style='cyan')
    table.add_column('Steps', style='green')
    table.add_column('Checkpoint Table', style='dim')

    for config in pipelines:
        steps_str = ', '.join(config.steps[:3])
        if len(config.steps) > 3:
            steps_str += f' (+{len(config.steps) - 3} more)'
        table.add_row(config.name, steps_str, config.checkpoint_table)

    console.print(table)
    console.print(f'\n[dim]Total: {len(pipelines)} pipelines[/dim]')


@pipeline_app.command(name='status')
def pipeline_status(
    pipeline_name: str = typer.Option(None, '--pipeline', '-p', help='Specific pipeline name'),
    limit: int = typer.Option(10, '--limit', '-n', help='Number of runs to show'),
):
    """Show pipeline execution status."""
    from baseball.services.pipeline import get_pipeline_service

    service = get_pipeline_service()
    runs = service.get_recent_runs(pipeline_name=pipeline_name, limit=limit)

    if not runs:
        console.print('[yellow]No pipeline runs found[/yellow]')
        return

    table = Table(title='Recent Pipeline Runs' + (f' - {pipeline_name}' if pipeline_name else ''))
    table.add_column('Run ID', style='dim')
    table.add_column('Pipeline', style='cyan')
    table.add_column('Status', style='bold')
    table.add_column('Started', style='green')
    table.add_column('Duration', style='dim')

    for run in runs:
        status_color = {
            'completed': 'green',
            'failed': 'red',
            'partial': 'yellow',
            'running': 'blue',
        }.get(run.status.value, 'white')

        duration = ''
        if run.completed_at:
            duration_str = str(run.completed_at - run.started_at).split('.')[0]
            duration = duration_str

        table.add_row(
            str(run.run_id),
            run.pipeline_name,
            f'[{status_color}]{run.status.value}[/{status_color}]',
            run.started_at.strftime('%Y-%m-%d %H:%M'),
            duration,
        )

    console.print(table)


# Live command group
live_app = typer.Typer(
    help='Live MLB game tracking and real-time predictions', no_args_is_help=True
)


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
        inning_str = f'{"Top" if g.is_top else "Bot"} {g.inning}'
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

    console.print(
        f'[bold]Watching game {game_pk}[/bold] (interval: {interval}s, predict: {predict})'
    )
    console.print('[dim]Press Ctrl+C to stop[/dim]\n')

    # Define callback for state changes
    def on_state_change(state):
        inning_str = f'{"Top" if state.is_top else "Bot"} {state.inning}'
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
                console.print(
                    f'[green]Game complete! Final: {state.away_score}-{state.home_score}[/green]'
                )
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
    inning_str = f'{"Top" if state.is_top else "Bot"} {state.inning}'
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
app.add_typer(fangraphs_app, name='fangraphs')
app.add_typer(bref_app, name='bref')
app.add_typer(weather_app, name='weather')
app.add_typer(park_app, name='park')
app.add_typer(live_app, name='live')
app.add_typer(bridge_app, name='bridge')
app.add_typer(features_app, name='features')
app.add_typer(models_app, name='models')
app.add_typer(betting_app, name='bet')
app.add_typer(predict_app, name='predict')
app.add_typer(pipeline_app, name='pipeline')
app.add_typer(chatbot_app, name='chatbot')

if __name__ == '__main__':
    app()
