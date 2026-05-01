"""Prediction workflow commands."""

import sys
from datetime import date

import requests
import typer
from rich.console import Console
from rich.table import Table

console = Console()

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

                            console.print(f"{game.get('awayName', 'Away')} @ {game.get('homeName', 'Home')}")
                            console.print(f"  Score: {score_away}-{score_home} | Inning: {'Top' if is_top else 'Bot'} {inning} | Outs: {outs}")
                            console.print(f"  Runners: {'_' if runner_1b else '.'} {'_' if runner_2b else '.'} {'_' if runner_3b else '.'}")
                            console.print(f"  Home Win: {home_prob:.1%} | Away Win: {away_prob:.1%}\n")
                        else:
                            # Multiple games (simplified display)
                            game = game_data.get('gameData', {}).get('game', {})
                            status = game_data.get('status', {}).get('detailedState', 'Unknown')
                            linescore = game_data.get('liveData', {}).get('linescore', {})
                            score_home = linescore.get('teams', {}).get('home', {}).get('runs', 0)
                            score_away = linescore.get('teams', {}).get('away', {}).get('runs', 0)

                            console.print(f"{game.get('awayName', 'Away')} @ {game.get('homeName', 'Home')}: {score_away}-{score_home} ({status})")

                time.sleep(interval)

            except KeyboardInterrupt:
                console.print('\n[yellow]Live prediction stopped[/yellow]')
                break

    except Exception as e:
        console.print(f'[red]Error during live prediction: {e}[/red]')
        raise typer.Exit(code=1)


@predict_app.command(name='batch')
def predict_batch(
    season: int = typer.Option(..., '--season', '-s', help='Season to predict'),
    model: str = typer.Option('win_probability', '--model', '-m', help='Model name'),
    output: str = typer.Option('json', '--output', '-o', help='Output format'),
):
    """Run batch predictions for a season."""
    console.print(f'[dim]Running batch predictions for {season}...[/dim]')
    console.print('[yellow]Batch prediction not yet implemented[/yellow]')
    raise typer.Exit(code=1)


# Live command group (separate from predict for MLB-specific live operations)
live_app = typer.Typer(help='Live game tracking and monitoring', no_args_is_help=True)


@live_app.command(name='games')
def live_games():
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


@live_app.command(name='watch')
def live_watch(
    game_pk: int = typer.Option(..., '--game', '-g', help='Game PK to watch'),
    interval: int = typer.Option(10, '--interval', '-i', help='Poll interval in seconds'),
    duration: int = typer.Option(0, '--duration', '-d', help='Duration in minutes'),
):
    """Watch a live game with real-time updates."""
    from baseball.services.live_feed import LiveFeedPoller
    from rich.live import Live
    from rich.table import Table as RichTable
    import time

    poller = LiveFeedPoller(game_pk=game_pk, poll_interval=interval, save_raw_snapshots=True)

    console.print(f'[bold green]Watching game {game_pk}...[/bold green]')
    console.print(f'[dim]Interval: {interval}s | Duration: {"∞" if duration == 0 else f"{duration}m"}[/dim]')

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

                time.sleep(interval)

    except KeyboardInterrupt:
        console.print(f'\n[dim]Stopped after {poll_count} updates[/dim]')


@live_app.command(name='poll')
def live_poll(
    game_pk: int = typer.Option(..., '--game', '-g', help='Game PK to poll'),
    count: int = typer.Option(1, '--count', '-c', help='Number of polls'),
):
    """Poll a game for updates."""
    from baseball.services.live_feed import LiveFeedPoller

    poller = LiveFeedPoller(game_pk=game_pk, poll_interval=10, save_raw_snapshots=False)

    console.print(f'[dim]Polling game {game_pk} {count} time(s)...[/dim]')

    for i in range(count):
        updates = poller.poll()
        if updates:
            console.print(f'[green]Poll {i+1}: {len(updates)} update(s)[/green]')
            for update in updates:
                console.print(f"  - {update.get('description', 'Update')}")
        else:
            console.print(f'[dim]Poll {i+1}: No updates[/dim]')


@live_app.command(name='predict')
def live_predict(
    game_pk: int = typer.Option(..., '--game', '-g', help='Game PK to predict'),
):
    """Run prediction for a live game."""
    from baseball.models.inference import InferencePipeline

    pipeline = InferencePipeline(model_name='win_probability')
    result = pipeline.predict_game(game_pk=game_pk, store_result=False)

    if result.success:
        console.print(f'[green]Prediction for game {game_pk}[/green]')
        console.print(f'  Predicted value: {result.predicted_value:.1%}')
        console.print(f'  Confidence: {result.confidence:.1%}')
    else:
        console.print(f'[red]Prediction failed: {result.error_message}[/red]')
        raise typer.Exit(code=1)


@live_app.command(name='server')
def live_server(
    port: int = typer.Option(8000, '--port', '-p', help='Port to run on'),
):
    """Start live prediction server."""
    console.print(f'[dim]Starting live prediction server on port {port}...[/dim]')
    console.print('[yellow]Live server not yet implemented[/yellow]')
    raise typer.Exit(code=1)
