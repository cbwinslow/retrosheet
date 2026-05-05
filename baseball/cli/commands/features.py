"""Feature engineering commands."""

from typing import Optional
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


@features_app.command(name='refresh-live')
def refresh_live_features(
    watch: bool = typer.Option(
        False,
        '--watch', '-w',
        help='Continuously refresh every 30 seconds'
    ),
    interval: int = typer.Option(
        30,
        '--interval', '-i',
        help='Refresh interval in seconds (default: 30)'
    )
):
    """Refresh live pitch feature cache for real-time inference."""
    from baseball.features.live_inference import LiveFeatureMapper
    from time import sleep
    
    mapper = LiveFeatureMapper()
    
    console.print('[dim]Refreshing live pitch features...[/dim]')
    
    while True:
        try:
            result = mapper.refresh_live_cache()
            
            console.print(
                f'[green]✓[/green] Refreshed: {result["rows_after"]} pitches '
                f'(+{result["new_rows"]} new) | '
                f'Latest: {result["latest_timestamp"]}'
            )
            
            # Show active games
            games = mapper.get_active_games()
            if games:
                console.print(f'[dim]Active games: {len(games)}[/dim]')
                for g in games[:3]:  # Show top 3
                    console.print(
                        f'  • Game {g["game_pk"]}: {g["pitch_count"]} pitches'
                    )
            
            if not watch:
                break
                
            sleep(interval)
            
        except KeyboardInterrupt:
            console.print('\n[yellow]Stopped.[/yellow]')
            break
        except Exception as e:
            console.print(f'[red]Error: {e}[/red]')
            if not watch:
                raise typer.Exit(code=1)
            sleep(interval)


@features_app.command(name='refresh-players')
def refresh_player_context(
    batter_id: Optional[str] = typer.Option(
        None,
        '--batter', '-b',
        help='Show context for specific batter'
    ),
    pitcher_id: Optional[str] = typer.Option(
        None,
        '--pitcher', '-p',
        help='Show context for specific pitcher'
    ),
    matchup: bool = typer.Option(
        False,
        '--matchup', '-m',
        help='Show head-to-head matchup (requires both --batter and --pitcher)'
    ),
    refresh: bool = typer.Option(
        False,
        '--refresh', '-r',
        help='Refresh materialized views'
    )
):
    """Refresh and display player context features (30-day rolling stats)."""
    from baseball.features.player_context import PlayerContextStore
    
    store = PlayerContextStore()
    
    if refresh:
        console.print('[dim]Refreshing player context tables...[/dim]')
        results = store.refresh_context_tables()
        
        for table, stats in results.items():
            console.print(
                f'[green]✓[/green] {table}: {stats["rows_after"]} rows '
                f'(+{stats["new_rows"]} new)'
            )
        console.print()
    
    if batter_id:
        context = store.get_batter_context(batter_id)
        if context:
            console.print(f'[bold]Batter {batter_id} (30-day)[/bold]')
            console.print(f'  PA: {context.pa_30d} (7d: {context.pa_7d})')
            console.print(f'  AVG: {context.avg_30d:.3f}')
            console.print(f'  K%: {context.k_rate_30d:.1f}% (7d: {context.k_rate_7d:.1f}%)')
            console.print(f'  BB%: {context.bb_rate_30d:.1f}% (7d: {context.bb_rate_7d:.1f}%)')
            console.print(f'  HR%: {context.hr_rate_30d:.1f}%')
            if context.avg_ev_30d:
                console.print(f'  Avg EV: {context.avg_ev_30d:.1f} mph')
        else:
            console.print(f'[yellow]No context found for batter {batter_id}[/yellow]')
        console.print()
    
    if pitcher_id:
        context = store.get_pitcher_context(pitcher_id)
        if context:
            console.print(f'[bold]Pitcher {pitcher_id} (30-day)[/bold]')
            console.print(f'  BF: {context.bf_30d}')
            console.print(f'  K%: {context.k_rate_30d:.1f}%')
            console.print(f'  BB%: {context.bb_rate_30d:.1f}%')
            console.print(f'  HR%: {context.hr_rate_30d:.1f}%')
            console.print(f'  Velo: {context.avg_velo_30d:.1f} mph')
            console.print(f'  Arsenal: {context.arsenal_depth:.1f} pitch types')
        else:
            console.print(f'[yellow]No context found for pitcher {pitcher_id}[/yellow]')
        console.print()
    
    if matchup and batter_id and pitcher_id:
        history = store.get_matchup_history(pitcher_id, batter_id)
        if history:
            console.print(f'[bold]Matchup History (Last 3 years)[/bold]')
            console.print(f'  PAs: {history.total_pas}')
            console.print(f'  AVG: {history.matchup_avg:.3f} ({history.hits} hits)')
            console.print(f'  K%: {history.matchup_k_rate:.1f}% ({history.strikeouts} Ks)')
            if history.last_matchup_date:
                console.print(f'  Last: {history.last_matchup_date}')
        else:
            console.print(f'[dim]No matchup history found[/dim]')


@features_app.command(name='stars')
def star_players(
    refresh: bool = typer.Option(
        False,
        '--refresh', '-r',
        help='Refresh star player materialized views'
    ),
    top: int = typer.Option(
        10,
        '--top', '-t',
        help='Show top N players'
    ),
    team_id: Optional[str] = typer.Option(
        None,
        '--team',
        help='Filter by team ID'
    ),
    active: bool = typer.Option(
        False,
        '--active', '-a',
        help='Show only active players for today'
    )
):
    """Display star player rankings and active roster."""
    from baseball.features.star_players import StarPlayerStore
    
    store = StarPlayerStore()
    
    if refresh:
        console.print('[dim]Refreshing star player views...[/dim]')
        results = store.refresh_star_views()
        for view, status in results.items():
            console.print(f'[green]✓[/green] {view}: {status}')
        console.print()
    
    if active:
        # Show active roster
        players = store.get_active_stars(team_id=team_id)
        
        if team_id:
            console.print(f'[bold]Active Star Players (Team {team_id})[/bold]')
        else:
            console.print(f'[bold]Active Star Players - All Teams[/bold]')
        
        from rich.table import Table
        table = Table()
        table.add_column('Rank', style='cyan', justify='right')
        table.add_column('Player', style='green')
        table.add_column('Team', style='yellow')
        table.add_column('Type', style='magenta')
        table.add_column('Position', style='dim')
        
        for i, player in enumerate(players[:top], 1):
            table.add_row(
                str(player.star_rank or '-'),
                player.player_name,
                player.team_abbreviation,
                player.player_type,
                player.position
            )
        
        console.print(table)
        console.print(f'\n[dim]Showing {min(top, len(players))} of {len(players)} active stars[/dim]')
    else:
        # Show top batters and pitchers
        console.print(f'[bold]Top {top} Star Batters[/bold]')
        batters = store.list_top_batters(limit=top)
        
        for b in batters:
            console.print(
                f'  #{b.star_rank} [cyan]{b.player_id}[/cyan] '
                f'WAR: {b.war_estimate:.1f} | '
                f'AVG: {b.avg_30d:.3f} | '
                f'K%: {b.k_rate_30d:.1f}'
            )
        
        console.print(f'\n[bold]Top {top} Star Pitchers[/bold]')
        pitchers = store.list_top_pitchers(limit=top)
        
        for p in pitchers:
            console.print(
                f'  #{p.star_rank} [cyan]{p.player_id}[/cyan] '
                f'WAR: {p.war_estimate:.1f} | '
                f'K%: {p.k_rate_30d:.1f} | '
                f'Velo: {p.avg_velo_30d:.1f}'
            )
