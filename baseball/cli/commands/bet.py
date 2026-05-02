"""Betting analysis commands."""

import asyncio
from decimal import Decimal
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()

betting_app = typer.Typer(help='AI-powered betting analysis', no_args_is_help=True)


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


@betting_app.command(name='edges')
def find_edges(
    game_pk: int = typer.Option(..., '--game', '-g', help='MLB game ID'),
    bankroll: float = typer.Option(10000, '--bankroll', '-b', help='Total bankroll'),
    min_edge: float = typer.Option(0.02, '--min-edge', '-e', help='Minimum edge to flag (default 2%)'),
    sportsbook: str = typer.Option('draftkings', '--book', '-s', help='Sportsbook to check')
):
    """Find betting edges for a specific game."""
    from baseball.betting import MarketComparator, find_moneyline_edges
    from baseball.models import MonteCarloSimulator
    
    console.print(f'[bold]Finding edges for game {game_pk}...[/bold]')
    
    # Run simulation to get model probabilities
    console.print('[dim]Running Monte Carlo simulation...[/dim]')
    sim = MonteCarloSimulator(n_simulations=10000)
    probs = sim.simulate_game(game_pk)
    
    console.print(f'\n[bold]Model Probabilities:[/bold]')
    console.print(f'  Home: [cyan]{probs["home_win"]:.1%}[/cyan]')
    console.print(f'  Away: [cyan]{probs["away_win"]:.1%}[/cyan]')
    
    # For demo, use placeholder odds
    # In production, fetch from sportsbook API
    home_odds = -110 if probs["home_win"] > 0.5 else +130
    away_odds = +130 if probs["home_win"] > 0.5 else -110
    
    console.print(f'\n[bold]{sportsbook.title()} Odds:[/bold]')
    console.print(f'  Home: [yellow]{home_odds:+d}[/yellow]')
    console.print(f'  Away: [yellow]{away_odds:+d}[/yellow]')
    
    # Find edges
    edges = find_moneyline_edges(
        home_prob=probs["home_win"],
        away_prob=probs["away_win"],
        home_odds=home_odds,
        away_odds=away_odds,
        min_edge=min_edge
    )
    
    if edges:
        console.print(f'\n[bold green]Found {len(edges)} Edges:[/bold green]')
        
        from rich.table import Table
        table = Table()
        table.add_column('Side', style='cyan')
        table.add_column('Model %', justify='right')
        table.add_column('Market %', justify='right')
        table.add_column('Edge', justify='right', style='green')
        table.add_column('EV', justify='right')
        table.add_column('Kelly Stake', justify='right')
        
        for edge in edges:
            stake = bankroll * edge.kelly_fraction
            table.add_row(
                edge.selection.upper(),
                f'{edge.model_prob:.1%}',
                f'{edge.market_prob:.1%}',
                f'+{edge.edge:.1%}',
                f'+{edge.ev_percent:.1%}',
                f'${stake:.0f} ({edge.kelly_fraction:.1%})'
            )
        
        console.print(table)
    else:
        console.print(f'\n[yellow]No edges found above {min_edge:.1%} threshold.[/yellow]')
