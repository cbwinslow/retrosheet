"""
Monitoring CLI Commands

Commands for monitoring queries and system health.
"""

import time
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn

from baseball.monitoring import QueryProgressTracker, get_active_queries

console = Console()
monitor_app = typer.Typer(help="Monitor queries and system status")


@monitor_app.command(name='queries')
def monitor_queries(
    watch: bool = typer.Option(False, '--watch', '-w', help='Continuously update display'),
    interval: int = typer.Option(2, '--interval', '-i', help='Update interval in seconds'),
    include_idle: bool = typer.Option(False, '--idle', help='Include idle connections'),
    database: Optional[str] = typer.Option(None, '--database', '-d', help='Filter by database'),
):
    """Monitor active database queries."""
    tracker = QueryProgressTracker()
    
    if watch:
        # Continuous monitoring mode
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                table = _build_queries_table(tracker, include_idle, database)
                live.update(table)
                time.sleep(interval)
    else:
        # Single snapshot
        table = _build_queries_table(tracker, include_idle, database)
        console.print(table)


def _build_queries_table(
    tracker: QueryProgressTracker,
    include_idle: bool,
    database: Optional[str]
) -> Table:
    """Build Rich table of active queries."""
    table = Table(title="Active Database Queries")
    table.add_column("PID", style="cyan", width=8)
    table.add_column("Database", style="green", width=12)
    table.add_column("State", style="yellow", width=10)
    table.add_column("User", style="blue", width=12)
    table.add_column("Query", style="white", no_wrap=True, max_width=50)
    table.add_column("Duration", style="magenta", width=12)
    table.add_column("Progress", style="green", width=10)
    
    queries = tracker.get_active_queries(
        include_idle=include_idle,
        database=database
    )
    
    if not queries:
        table.add_row("—", "—", "No active queries", "—", "", "—", "—")
        return table
    
    for q in queries:
        from datetime import datetime
        
        # Calculate duration
        duration = "—"
        if q.query_start:
            elapsed = (datetime.now() - q.query_start).total_seconds()
            if elapsed < 60:
                duration = f"{elapsed:.1f}s"
            elif elapsed < 3600:
                duration = f"{elapsed/60:.1f}m"
            else:
                duration = f"{elapsed/3600:.1f}h"
        
        # Format query (truncate)
        query_text = (q.query or "")[:45] + "..." if len(q.query or "") > 45 else q.query
        
        # Format progress
        progress = "—"
        if q.progress is not None:
            progress = f"{q.progress:.0f}%"
        
        # State with color indicator
        state_display = q.state
        
        table.add_row(
            str(q.pid),
            q.datname or "—",
            state_display,
            q.usename or "—",
            query_text or "",
            duration,
            progress
        )
    
    return table


@monitor_app.command(name='tracked')
def monitor_tracked(
    query_id: Optional[str] = typer.Option(None, '--query', '-q', help='Show specific tracked query'),
    watch: bool = typer.Option(False, '--watch', '-w', help='Continuously update display'),
    interval: int = typer.Option(2, '--interval', '-i', help='Update interval in seconds'),
):
    """Monitor tracked queries with progress."""
    tracker = QueryProgressTracker()
    
    if query_id:
        # Show specific query
        query = tracker.get_tracked_query(query_id)
        if not query:
            console.print(f"[red]Query {query_id} not found[/red]")
            raise typer.Exit(1)
        
        _display_tracked_query(query)
    else:
        # Show all tracked queries
        if watch:
            with Live(console=console, refresh_per_second=1) as live:
                while True:
                    table = _build_tracked_table(tracker)
                    live.update(table)
                    time.sleep(interval)
        else:
            table = _build_tracked_table(tracker)
            console.print(table)


def _build_tracked_table(tracker: QueryProgressTracker) -> Table:
    """Build table of tracked queries."""
    table = Table(title="Tracked Queries")
    table.add_column("Query ID", style="cyan", no_wrap=True)
    table.add_column("Description")
    table.add_column("Status", style="yellow")
    table.add_column("Progress", style="green")
    table.add_column("Started", style="blue")
    table.add_column("ETA", style="magenta")
    
    queries = tracker.list_tracked_queries()
    
    if not queries:
        table.add_row("—", "No tracked queries", "—", "—", "—", "—")
        return table
    
    for q in queries:
        from datetime import datetime
        
        progress_bar = ""
        if q.get('progress') is not None:
            filled = int(q['progress'] / 10)
            bar = "█" * filled + "░" * (10 - filled)
            progress_bar = f"{bar} {q['progress']:.1f}%"
        
        eta = "—"
        if q.get('estimated_remaining') is not None:
            remaining = q['estimated_remaining']
            if remaining < 60:
                eta = f"{remaining:.0f}s"
            elif remaining < 3600:
                eta = f"{remaining/60:.1f}m"
            else:
                eta = f"{remaining/3600:.1f}h"
        
        started = q.get('started_at', '')
        if isinstance(started, datetime):
            started = started.strftime("%H:%M:%S")
        
        status_color = {
            'completed': 'green',
            'running': 'yellow',
            'failed': 'red'
        }.get(q.get('status', ''), 'white')
        
        table.add_row(
            q.get('query_id', '—'),
            q.get('description', ''),
            f"[{status_color}]{q.get('status', 'unknown')}[/{status_color}]",
            progress_bar or "—",
            started,
            eta
        )
    
    return table


def _display_tracked_query(query: dict) -> None:
    """Display detailed info about a tracked query."""
    console.print(f"[bold]Query: {query.get('query_id')}[/bold]")
    console.print(f"  Description: {query.get('description')}")
    console.print(f"  Status: {query.get('status')}")
    console.print(f"  Progress: {query.get('progress', 0):.1f}%")
    
    if query.get('current_step'):
        console.print(f"  Step: {query.get('current_step')} / {query.get('total_steps', 100)}")
    
    if query.get('estimated_remaining'):
        eta = query['estimated_remaining']
        if eta < 60:
            eta_str = f"{eta:.0f} seconds"
        elif eta < 3600:
            eta_str = f"{eta/60:.1f} minutes"
        else:
            eta_str = f"{eta/3600:.1f} hours"
        console.print(f"  Estimated remaining: {eta_str}")
    
    if query.get('error'):
        console.print(f"[red]  Error: {query.get('error')}[/red]")


@monitor_app.command(name='server')
def monitor_server(
    port: int = typer.Option(8000, '--port', '-p', help='Port to run the monitoring server'),
    host: str = typer.Option("0.0.0.0", '--host', '-h', help='Host to bind to'),
):
    """Start the query monitoring API server."""
    import uvicorn
    from baseball.monitoring.api import app
    
    console.print(f"[green]Starting monitoring server on {host}:{port}[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    uvicorn.run(app, host=host, port=port)
