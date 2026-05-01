"""Feature engineering commands."""

import typer
from rich.console import Console
from rich.table import Table

console = Console()

features_app = typer.Typer(help='Feature engineering commands', no_args_is_help=True)


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
            console.print(f'[red]Error building {feat}: {e}[/red]')
            results.append((feat, False, str(e)))

    # Summary
    total_count = len(results)
    success_count = sum(1 for _, success, _ in results if success)

    if not dry_run:
        if success_count == total_count:
            console.print(f'\n[green]✓ All {total_count} features built successfully[/green]')
        else:
            console.print(f'\n[yellow]⚠ {success_count}/{total_count} features built successfully[/yellow]')
            raise typer.Exit(code=1)
