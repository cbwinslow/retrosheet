"""
CLI commands for Redis cache management.

Usage:
    baseball cache status              # Check Redis health
    baseball cache clear --predictions # Clear prediction cache
    baseball cache clear --players     # Clear player context cache
    baseball cache stats               # Show cache statistics
"""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

cache_app = typer.Typer()
console = Console()


@cache_app.command(name='status')
def cache_status():
    """Check Redis cache health status."""
    import asyncio
    from baseball.core.cache import cache_manager
    
    async def check():
        health = await cache_manager.health_check()
        
        if health['connected']:
            console.print(f'[green]✓[/green] Redis is healthy')
            console.print(f'  Version: [cyan]{health["version"]}[/cyan]')
            console.print(f'  Memory: [cyan]{health["used_memory"]}[/cyan]')
            console.print(f'  Clients: [cyan]{health["clients_connected"]}[/cyan]')
        else:
            console.print(f'[red]✗[/red] Redis is unhealthy')
            console.print(f'  Error: [red]{health.get("error", "Unknown")}[/red]')
            raise typer.Exit(code=1)
    
    asyncio.run(check())


@cache_app.command(name='clear')
def clear_cache(
    predictions: bool = typer.Option(
        False,
        '--predictions', '-p',
        help='Clear prediction cache'
    ),
    players: bool = typer.Option(
        False,
        '--players', '-pl',
        help='Clear player context cache'
    ),
    games: bool = typer.Option(
        False,
        '--games', '-g',
        help='Clear live game cache'
    ),
    all_cache: bool = typer.Option(
        False,
        '--all', '-a',
        help='Clear all cache'
    ),
    pattern: Optional[str] = typer.Option(
        None,
        '--pattern',
        help='Clear keys matching pattern (e.g., "pred:*")'
    )
):
    """Clear specific cache entries or patterns."""
    import asyncio
    from baseball.core.cache import cache_manager
    
    async def do_clear():
        client = await cache_manager.connect()
        
        cleared = 0
        
        if all_cache or pattern:
            # Clear by pattern
            match_pattern = pattern or '*'
            keys = await client.keys(match_pattern)
            if keys:
                await client.delete(*keys)
                cleared = len(keys)
            console.print(f'[green]✓[/green] Cleared {cleared} keys matching "{match_pattern}"')
        else:
            # Clear specific types
            if predictions:
                keys = await client.keys('pred:*')
                if keys:
                    await client.delete(*keys)
                    cleared += len(keys)
                console.print(f'[green]✓[/green] Cleared {len(keys)} prediction cache entries')
            
            if players:
                keys = await client.keys('player_ctx:*')
                if keys:
                    await client.delete(*keys)
                    cleared += len(keys)
                console.print(f'[green]✓[/green] Cleared {len(keys)} player context entries')
            
            if games:
                keys = await client.keys('live_game:*')
                if keys:
                    await client.delete(*keys)
                    cleared += len(keys)
                console.print(f'[green]✓[/green] Cleared {len(keys)} live game entries')
            
            if not any([predictions, players, games]):
                console.print('[yellow]⚠[/yellow] No cache type specified. Use --all or specific flags.')
                console.print('  --predictions, --players, --games, --all')
    
    asyncio.run(do_clear())


@cache_app.command(name='stats')
def cache_stats():
    """Show detailed cache statistics."""
    import asyncio
    from baseball.core.cache import cache_manager
    
    async def get_stats():
        client = await cache_manager.connect()
        info = await client.info()
        
        table = Table(title='Redis Cache Statistics')
        table.add_column('Metric', style='cyan')
        table.add_column('Value', style='green')
        
        table.add_row('Redis Version', info.get('redis_version', 'unknown'))
        table.add_row('Used Memory', info.get('used_memory_human', 'unknown'))
        table.add_row('Connected Clients', str(info.get('connected_clients', 0)))
        table.add_row('Total Keys', str(info.get('db0', {}).get('keys', 0) if 'db0' in info else 'unknown'))
        table.add_row('Keyspace Hits', str(info.get('keyspace_hits', 0)))
        table.add_row('Keyspace Misses', str(info.get('keyspace_misses', 0)))
        
        hit_rate = 0
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        if hits + misses > 0:
            hit_rate = hits / (hits + misses) * 100
        table.add_row('Hit Rate', f'{hit_rate:.1f}%')
        
        console.print(table)
        
        # Count specific key types
        pred_keys = len(await client.keys('pred:*'))
        player_keys = len(await client.keys('player_ctx:*'))
        game_keys = len(await client.keys('live_game:*'))
        
        console.print(f'\n[bold]Cache Contents:[/bold]')
        console.print(f'  Predictions: [cyan]{pred_keys}[/cyan]')
        console.print(f'  Player Context: [cyan]{player_keys}[/cyan]')
        console.print(f'  Live Games: [cyan]{game_keys}[/cyan]')
    
    asyncio.run(get_stats())


@cache_app.command(name='warmup')
def warmup_cache(
    model: str = typer.Option(
        'pitch_level',
        '--model', '-m',
        help='Model to warmup predictions for'
    ),
    player_id: Optional[str] = typer.Option(
        None,
        '--player', '-p',
        help='Specific player ID to warmup'
    ),
    game_pk: Optional[int] = typer.Option(
        None,
        '--game', '-g',
        help='Specific game to warmup'
    )
):
    """Pre-warm cache with common predictions/features."""
    import asyncio
    from baseball.core.cache import FeatureCache
    from baseball.features import PlayerContextStore
    
    async def do_warmup():
        cache = FeatureCache()
        store = PlayerContextStore()
        
        warmed = 0
        
        if player_id:
            # Warmup specific player
            context = store.get_batter_context(player_id)
            if context:
                await cache.set_player_context(player_id, context.__dict__)
                warmed += 1
                console.print(f'[green]✓[/green] Warmed player {player_id}')
        
        if game_pk:
            # Warmup specific game
            # This would fetch live game state and cache it
            console.print(f'[dim]Game warmup for {game_pk} (requires live data fetch)[/dim]')
        
        if not player_id and not game_pk:
            # General warmup - could load common players, recent games, etc.
            console.print('[dim]General warmup not implemented. Use --player or --game.[/dim]')
        
        console.print(f'\n[green]✓[/green] Warmed {warmed} cache entries')
    
    asyncio.run(do_warmup())
