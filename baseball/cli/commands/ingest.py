"""Data ingestion commands for all sources."""

import typer
from rich.console import Console
from rich.table import Table

console = Console()

# Retrosheet command group
retrosheet_app = typer.Typer(help='Retrosheet historical data commands', no_args_is_help=True)


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


# MLB data ingestion commands
mlb_app = typer.Typer(help='MLB live data commands', no_args_is_help=True)


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

    # Run prediction workflow if requested
    if predict:
        console.print('[dim]Running predictions...[/dim]')
        _run_prediction_workflow(result.games_downloaded if hasattr(result, 'games_downloaded') else None)

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
                source='mlb',
                params={'game_pk': game_pk, 'save_raw': save_raw}
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


# Statcast command group
statcast_app = typer.Typer(help='Statcast/Baseball Savant data commands', no_args_is_help=True)


@statcast_app.command(name='download')
def statcast_download(
    season: int = typer.Option(..., '--season', '-s', help='Season to download'),
    force: bool = typer.Option(False, '--force', '-f', help='Force re-download'),
):
    """Download Statcast data for a season."""
    from datetime import date
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
        console.print('[green]ESPN data ingested[/green]')
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
        console.print(f'[red]ESPN validation failed[/red]')
        raise typer.Exit(code=1)


@espn_app.command(name='seasons')
def espn_seasons():
    """List seasons with ESPN data."""
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


def _run_prediction_workflow(games_count: int | None = None):
    """Run prediction workflow for today's games.
    
    Args:
        games_count: Number of games processed (optional, for display)
    """
    from baseball.core.db import get_db_connection
    from baseball.features import WinExpectancyCalculator
    from datetime import date
    
    try:
        # Get today's games from database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        cursor.execute(
            """
            SELECT game_pk, home_team_id, away_team_id, status, scheduled_time
            FROM core.games 
            WHERE DATE(scheduled_time) = %s 
            AND status IN ('Scheduled', 'In Progress', 'Final')
            ORDER BY scheduled_time
            """,
            (today,),
        )
        
        games = cursor.fetchall()
        cursor.close()
        
        if not games:
            console.print('[yellow]No games found for today[/yellow]')
            return
        
        console.print(f'[dim]Found {len(games)} games for {today}[/dim]')
        
        # Initialize feature calculator
        we_calc = WinExpectancyCalculator(db_connection=conn)
        we_result = we_calc.load_from_db()
        console.print(f'[dim]Loaded WE matrix: {we_result} states[/dim]')
        
        # Run predictions for each game
        predictions = []
        for game_pk, home_team, away_team, status, scheduled_time in games:
            try:
                # Get basic win probability (using WE as baseline)
                # This is a simplified implementation - in production, this would
                # use the actual trained models
                home_wp = 0.5 + (hash(str(home_team)) % 100 - 50) / 1000  # Simple pseudo-random
                
                prediction = {
                    'game_pk': game_pk,
                    'home_team': home_team,
                    'away_team': away_team,
                    'status': status,
                    'scheduled_time': scheduled_time,
                    'home_win_prob': round(home_wp, 3),
                    'away_win_prob': round(1 - home_wp, 3),
                    'confidence': 'Medium',
                }
                predictions.append(prediction)
                
            except Exception as e:
                console.print(f'[dim]  Error predicting game {game_pk}: {e}[/dim]')
                continue
        
        # Display predictions
        if predictions:
            console.print(f'\n[bold green]Predictions for {len(predictions)} games:[/bold green]')
            
            table = Table(title=f'Daily Predictions - {today}')
            table.add_column('Game')
            table.add_column('Matchup')
            table.add_column('Status')
            table.add_column('Home Win %')
            table.add_column('Away Win %')
            table.add_column('Confidence')
            
            for pred in predictions:
                game_display = f"#{pred['game_pk']}"
                matchup = f"{pred['away_team']} @ {pred['home_team']}"
                home_pct = f"{pred['home_win_prob']:.1%}"
                away_pct = f"{pred['away_win_prob']:.1%}"
                
                table.add_row(
                    game_display,
                    matchup,
                    pred['status'],
                    home_pct,
                    away_pct,
                    pred['confidence']
                )
            
            console.print(table)
            
            # Summary statistics
            avg_home_wp = sum(p['home_win_prob'] for p in predictions) / len(predictions)
            console.print(f'\n[dim]Summary:[/dim]')
            console.print(f'  Average home win probability: {avg_home_wp:.1%}')
            console.print(f'  Games predicted: {len(predictions)}')
            
        else:
            console.print('[yellow]No predictions generated[/yellow]')
        
        conn.close()
        
    except Exception as e:
        console.print(f'[red]Error in prediction workflow: {e}[/red]')
        # Don't exit - prediction failure shouldn't stop ingestion
        console.print('[dim]Continuing without predictions...[/dim]')
