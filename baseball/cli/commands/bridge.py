"""Cross-reference and ID resolution commands."""

import typer
from rich.console import Console
from rich.table import Table

console = Console()

bridge_app = typer.Typer(help='Cross-reference and ID resolution commands', no_args_is_help=True)


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
    limit: int = typer.Option(50, '--limit', '-l', help='Maximum number of matches to return'),
    min_confidence: float = typer.Option(0.5, '--min-confidence', '-c', help='Minimum confidence threshold'),
):
    """Find matches between two source systems."""
    from baseball.services.bridge import BridgeService

    console.print(f'[dim]Finding {entity_type} matches between {source_a} and {source_b}...[/dim]')

    try:
        bridge = BridgeService()
        matches = bridge.find_matches(source_a, source_b, entity_type, limit, min_confidence)

        if matches and matches.get('matches'):
            console.print(f'[green]✓ Found {len(matches["matches"])} matches:[/green]')

            table = Table(title=f'{entity_type.title()} Matches: {source_a} ↔ {source_b}')
            table.add_column(f'{source_a.title()} ID')
            table.add_column(f'{source_b.title()} ID')
            table.add_column('Canonical ID')
            table.add_column('Confidence')
            table.add_column('Name/Info')

            for match in matches['matches']:
                # Format name based on entity type
                name_info = ''
                if entity_type == 'player' and 'name' in match:
                    name_info = f"{match.get('first_name', '')} {match.get('last_name', '')}".strip()
                elif entity_type == 'team' and 'name' in match:
                    name_info = match['name']
                elif entity_type == 'game' and 'date' in match:
                    name_info = match['date']
                
                table.add_row(
                    match.get(f'{source_a}_id', 'N/A'),
                    match.get(f'{source_b}_id', 'N/A'),
                    match.get('canonical_id', 'N/A'),
                    f"{match.get('confidence', 0):.2f}",
                    name_info
                )
            console.print(table)

            # Show summary stats
            stats = matches.get('stats', {})
            if stats:
                console.print(f'\n[dim]Summary:[/dim]')
                console.print(f"  Total {source_a} records: {stats.get(f'{source_a}_total', 0)}")
                console.print(f"  Total {source_b} records: {stats.get(f'{source_b}_total', 0)}")
                console.print(f"  Matches found: {len(matches['matches'])}")
                console.print(f"  Match rate: {stats.get('match_rate', 0):.1%}")
        else:
            console.print(f'[yellow]⚠ No matches found between {source_a} and {source_b}[/yellow]')
            if matches and 'error' in matches:
                console.print(f'[red]Error: {matches["error"]}[/red]')
            raise typer.Exit(code=1)

    except Exception as e:
        console.print(f'[red]✗ Error: {e}[/red]')
        raise typer.Exit(code=1)


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
            console.print(f'[yellow]⚠ No source mappings found for canonical ID {canonical_id}[/yellow]')
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
        console.print(f'[red]Error: {stats["error"]}[/red]')
        raise typer.Exit(code=1)

    # Display coverage stats
    table = Table(title='Bridge Table Coverage')
    table.add_column('Entity')
    table.add_column('Total Records')
    table.add_column('Coverage %')
    table.add_column('Status')

    for entity_name, data in stats.items():
        if entity_name != 'error' and isinstance(data, dict):
            total = data.get('total', 0)
            coverage = data.get('coverage', 0)
            status = '✓' if coverage >= min_coverage else '✗'
            table.add_row(entity_name, str(total), f'{coverage:.1f}%', status)

    console.print(table)

    # Check if all meet minimum coverage
    all_pass = all(
        data.get('coverage', 0) >= min_coverage
        for entity_name, data in stats.items()
        if entity_name != 'error' and isinstance(data, dict)
    )

    if all_pass:
        console.print(f'\n[green]✓ All entities meet {min_coverage}% coverage threshold[/green]')
    else:
        console.print(f'\n[yellow]⚠ Some entities below {min_coverage}% coverage threshold[/yellow]')
        raise typer.Exit(code=1)
