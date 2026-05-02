"""
Telemetry CLI Commands

Commands for analyzing and viewing telemetry data:
- events: View application events
- metrics: View time-series metrics
- queries: Analyze query performance
- jobs: Monitor batch job execution
- errors: View error reports
- dashboard: Live telemetry dashboard
"""

from datetime import datetime, timedelta
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.layout import Layout
from rich.syntax import Syntax

from baseball.core.db import get_db_connection

console = Console()
telemetry_app = typer.Typer(help="Telemetry and observability commands")


@telemetry_app.command(name='events')
def view_events(
    event_type: Optional[str] = typer.Option(None, '--type', '-t', help='Filter by event type'),
    severity: Optional[str] = typer.Option(None, '--severity', '-s', help='Filter by severity'),
    source: Optional[str] = typer.Option(None, '--source', help='Filter by source'),
    limit: int = typer.Option(50, '--limit', '-n', help='Number of events to show'),
    since: Optional[str] = typer.Option('1h', '--since', help='Time window (e.g., 1h, 30m, 1d)'),
    watch: bool = typer.Option(False, '--watch', '-w', help='Continuously update'),
    json_output: bool = typer.Option(False, '--json', help='Output as JSON'),
):
    """View application events."""
    if watch:
        with Live(console=console, refresh_per_second=0.5) as live:
            while True:
                table = _build_events_table(event_type, severity, source, limit, since)
                live.update(table)
                import time
                time.sleep(2)
    else:
        table = _build_events_table(event_type, severity, source, limit, since)
        console.print(table)


def _build_events_table(
    event_type: Optional[str],
    severity: Optional[str],
    source: Optional[str],
    limit: int,
    since: str
) -> Table:
    """Build table of recent events."""
    table = Table(title=f"Recent Events (last {since})")
    table.add_column("Time", style="cyan", width=20)
    table.add_column("Type", style="green", width=30)
    table.add_column("Severity", style="yellow", width=10)
    table.add_column("Source", style="blue", width=15)
    table.add_column("Payload", style="white", max_width=50)
    
    # Parse since parameter
    interval = _parse_interval(since)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
        SELECT created_at, event_type, severity, source, payload
        FROM telemetry.events
        WHERE created_at > NOW() - %s::INTERVAL
    """
    params = [interval]
    
    if event_type:
        query += " AND event_type = %s"
        params.append(event_type)
    if severity:
        query += " AND severity = %s"
        params.append(severity.upper())
    if source:
        query += " AND source = %s"
        params.append(source)
    
    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    if not rows:
        table.add_row("—", "No events found", "—", "—", "")
        return table
    
    for row in rows:
        ts, et, sev, src, payload = row
        
        # Format timestamp
        ts_str = ts.strftime("%H:%M:%S") if isinstance(ts, datetime) else str(ts)[:19]
        
        # Severity with color
        sev_color = {
            'CRITICAL': 'red',
            'ERROR': 'red',
            'WARN': 'yellow',
            'INFO': 'green',
            'DEBUG': 'dim'
        }.get(sev, 'white')
        
        # Truncate payload
        import json
        payload_str = json.dumps(payload) if payload else "{}"
        if len(payload_str) > 45:
            payload_str = payload_str[:42] + "..."
        
        table.add_row(
            ts_str,
            et,
            f"[{sev_color}]{sev}[/{sev_color}]",
            src or "—",
            payload_str
        )
    
    return table


@telemetry_app.command(name='metrics')
def view_metrics(
    metric_name: Optional[str] = typer.Option(None, '--name', '-m', help='Filter by metric name'),
    since: str = typer.Option('1h', '--since', help='Time window'),
    aggregate: bool = typer.Option(False, '--aggregate', '-a', help='Show aggregated stats'),
):
    """View time-series metrics."""
    interval = _parse_interval(since)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    if aggregate:
        # Show aggregated statistics
        query = """
            SELECT 
                metric_name,
                COUNT(*) as count,
                AVG(value) as avg,
                MIN(value) as min,
                MAX(value) as max,
                unit
            FROM telemetry.metrics
            WHERE recorded_at > NOW() - %s::INTERVAL
        """
        params = [interval]
        
        if metric_name:
            query += " AND metric_name = %s"
            params.append(metric_name)
        
        query += " GROUP BY metric_name, unit ORDER BY metric_name"
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        table = Table(title=f"Metric Statistics (last {since})")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green", justify="right")
        table.add_column("Avg", style="yellow", justify="right")
        table.add_column("Min", style="blue", justify="right")
        table.add_column("Max", style="magenta", justify="right")
        table.add_column("Unit", style="dim")
        
        for row in rows:
            name, count, avg, min_val, max_val, unit = row
            table.add_row(
                name,
                str(count),
                f"{avg:.2f}",
                f"{min_val:.2f}",
                f"{max_val:.2f}",
                unit or "—"
            )
    else:
        # Show recent individual metrics
        query = """
            SELECT recorded_at, metric_name, value, unit, labels
            FROM telemetry.metrics
            WHERE recorded_at > NOW() - %s::INTERVAL
        """
        params = [interval]
        
        if metric_name:
            query += " AND metric_name = %s"
            params.append(metric_name)
        
        query += " ORDER BY recorded_at DESC LIMIT 50"
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        table = Table(title=f"Recent Metrics (last {since})")
        table.add_column("Time", style="cyan", width=20)
        table.add_column("Metric", style="green", width=30)
        table.add_column("Value", style="yellow", justify="right")
        table.add_column("Unit", style="dim")
        table.add_column("Labels", style="white", max_width=30)
        
        for row in rows:
            ts, name, value, unit, labels = row
            ts_str = ts.strftime("%H:%M:%S") if isinstance(ts, datetime) else str(ts)[:19]
            
            import json
            labels_str = json.dumps(labels) if labels else ""
            if len(labels_str) > 27:
                labels_str = labels_str[:24] + "..."
            
            table.add_row(ts_str, name, f"{value:.2f}", unit or "—", labels_str)
    
    cur.close()
    conn.close()
    
    console.print(table)


@telemetry_app.command(name='queries')
def view_queries(
    slow_only: bool = typer.Option(False, '--slow', '-s', help='Show only slow queries'),
    since: str = typer.Option('1h', '--since', help='Time window'),
    limit: int = typer.Option(20, '--limit', '-n', help='Number of queries'),
):
    """View query performance logs."""
    interval = _parse_interval(since)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
        SELECT 
            recorded_at,
            duration_ms,
            rows_returned,
            rows_affected,
            was_slow,
            LEFT(query_text, 80)
        FROM telemetry.query_logs
        WHERE recorded_at > NOW() - %s::INTERVAL
    """
    params = [interval]
    
    if slow_only:
        query += " AND was_slow = TRUE"
    
    query += " ORDER BY duration_ms DESC LIMIT %s"
    params.append(limit)
    
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    table = Table(title=f"Query Performance (last {since})")
    table.add_column("Time", style="cyan", width=12)
    table.add_column("Duration", style="yellow", justify="right")
    table.add_column("Rows", style="green", justify="right")
    table.add_column("Slow", style="red", width=6)
    table.add_column("Query", style="white", max_width=50)
    
    if not rows:
        table.add_row("—", "No queries logged", "", "", "")
    else:
        for row in rows:
            ts, dur, rows_ret, rows_aff, is_slow, qtext = row
            ts_str = ts.strftime("%H:%M:%S") if isinstance(ts, datetime) else str(ts)[:8]
            
            dur_str = f"{dur:.1f}ms" if dur < 1000 else f"{dur/1000:.2f}s"
            slow_marker = "[red]YES[/red]" if is_slow else "—"
            
            table.add_row(
                ts_str,
                dur_str,
                str(rows_ret or rows_aff or "—"),
                slow_marker,
                qtext or ""
            )
    
    console.print(table)


@telemetry_app.command(name='slow-queries')
def view_slow_query_summary(
    since: str = typer.Option('24h', '--since', help='Time window'),
    min_count: int = typer.Option(2, '--min-count', help='Minimum occurrences'),
):
    """View aggregated slow query analysis."""
    interval = _parse_interval(since)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM telemetry.slow_queries_summary
        WHERE last_seen > NOW() - %s::INTERVAL
    """, [interval])
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    table = Table(title=f"Slow Query Summary (last {since})")
    table.add_column("Hash", style="cyan", width=16)
    table.add_column("Preview", style="white", max_width=40)
    table.add_column("Count", style="green", justify="right")
    table.add_column("Avg (ms)", style="yellow", justify="right")
    table.add_column("Max (ms)", style="red", justify="right")
    
    if not rows:
        table.add_row("—", "No slow queries found", "", "", "")
    else:
        for row in rows:
            hash_val, preview, count, avg, max_dur, _ = row
            table.add_row(
                hash_val[:16] if hash_val else "—",
                preview or "",
                str(count),
                f"{avg:.1f}",
                f"{max_dur:.1f}"
            )
    
    console.print(table)


@telemetry_app.command(name='jobs')
def view_jobs(
    status: Optional[str] = typer.Option(None, '--status', '-s', help='Filter by status'),
    job_name: Optional[str] = typer.Option(None, '--name', '-n', help='Filter by job name'),
    watch: bool = typer.Option(False, '--watch', '-w', help='Continuously update'),
    since: str = typer.Option('24h', '--since', help='Time window'),
):
    """View batch job execution status."""
    interval = _parse_interval(since)
    
    if watch:
        with Live(console=console, refresh_per_second=0.5) as live:
            while True:
                table = _build_jobs_table(status, job_name, interval)
                live.update(table)
                import time
                time.sleep(2)
    else:
        table = _build_jobs_table(status, job_name, interval)
        console.print(table)


def _build_jobs_table(
    status: Optional[str],
    job_name: Optional[str],
    interval: str
) -> Table:
    """Build jobs table."""
    table = Table(title=f"Job Executions (last {interval})")
    table.add_column("ID", style="cyan", width=8)
    table.add_column("Name", style="green", width=25)
    table.add_column("Group", style="blue", width=12)
    table.add_column("Status", style="yellow", width=12)
    table.add_column("Progress", style="magenta", width=10)
    table.add_column("Duration", style="cyan", width=12)
    table.add_column("Started", style="dim", width=16)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    query = """
        SELECT 
            job_id, job_name, job_group, status, 
            completed_steps, total_steps, progress_pct,
            started_at, completed_at,
            EXTRACT(EPOCH FROM (COALESCE(completed_at, NOW()) - started_at)) * 1000 as duration_ms
        FROM telemetry.jobs
        WHERE created_at > NOW() - %s::INTERVAL
    """
    params = [interval]
    
    if status:
        query += " AND status = %s"
        params.append(status)
    if job_name:
        query += " AND job_name = %s"
        params.append(job_name)
    
    query += " ORDER BY created_at DESC LIMIT 50"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    if not rows:
        table.add_row("—", "No jobs found", "—", "—", "—", "—", "—")
        return table
    
    for row in rows:
        jid, name, group, stat, completed, total, progress, started, completed, dur_ms = row
        
        # Status color
        stat_color = {
            'completed': 'green',
            'running': 'yellow',
            'failed': 'red',
            'pending': 'dim',
            'cancelled': 'red'
        }.get(stat, 'white')
        
        # Progress bar
        if progress is not None:
            filled = int(progress / 10)
            bar = "█" * filled + "░" * (10 - filled)
            progress_str = f"{bar} {progress:.0f}%"
        else:
            progress_str = "—"
        
        # Duration
        if dur_ms is not None:
            if dur_ms < 1000:
                dur_str = f"{dur_ms:.0f}ms"
            elif dur_ms < 60000:
                dur_str = f"{dur_ms/1000:.1f}s"
            else:
                dur_str = f"{dur_ms/60000:.1f}m"
        else:
            dur_str = "—"
        
        # Started time
        started_str = started.strftime("%m-%d %H:%M") if isinstance(started, datetime) else str(started)[:16]
        
        table.add_row(
            str(jid),
            name,
            group or "—",
            f"[{stat_color}]{stat}[/{stat_color}]",
            progress_str,
            dur_str,
            started_str
        )
    
    return table


@telemetry_app.command(name='errors')
def view_errors(
    status: str = typer.Option('open', '--status', '-s', help='Filter by status'),
    since: str = typer.Option('24h', '--since', help='Time window'),
    limit: int = typer.Option(20, '--limit', '-n', help='Number of errors'),
    group: bool = typer.Option(True, '--group/--no-group', help='Group by error type'),
):
    """View error tracking."""
    interval = _parse_interval(since)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    if group:
        cur.execute("""
            SELECT * FROM telemetry.error_summary
            WHERE last_seen > NOW() - %s::INTERVAL
            AND status = %s
            ORDER BY total_occurrences DESC
            LIMIT %s
        """, [interval, status, limit])
        
        table = Table(title=f"Error Summary (last {since})")
        table.add_column("Type", style="red", width=30)
        table.add_column("Message", style="white", max_width=40)
        table.add_column("Count", style="yellow", justify="right")
        table.add_column("First Seen", style="dim", width=16)
        table.add_column("Last Seen", style="dim", width=16)
        table.add_column("Status", style="cyan", width=10)
    else:
        cur.execute("""
            SELECT 
                created_at, error_type, error_message, 
                source, operation, occurrence_count, status
            FROM telemetry.errors
            WHERE created_at > NOW() - %s::INTERVAL
            AND status = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, [interval, status, limit])
        
        table = Table(title=f"Recent Errors (last {since})")
        table.add_column("Time", style="dim", width=16)
        table.add_column("Type", style="red", width=25)
        table.add_column("Message", style="white", max_width=35)
        table.add_column("Source", style="cyan", width=15)
        table.add_column("Operation", style="blue", width=15)
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    if not rows:
        table.add_row("No errors found", "", "", "", "", "")
    else:
        for row in rows:
            if group:
                err_type, msg, count, first, last, stat = row[:6]
                first_str = first.strftime("%m-%d %H:%M") if isinstance(first, datetime) else str(first)[:16]
                last_str = last.strftime("%m-%d %H:%M") if isinstance(last, datetime) else str(last)[:16]
                table.add_row(err_type, msg or "", str(count), first_str, last_str, stat)
            else:
                ts, err_type, msg, src, op, count, _ = row
                ts_str = ts.strftime("%m-%d %H:%M") if isinstance(ts, datetime) else str(ts)[:16]
                table.add_row(ts_str, err_type, msg or "", src or "—", op or "—")
    
    console.print(table)


@telemetry_app.command(name='dashboard')
def telemetry_dashboard(
    refresh: int = typer.Option(5, '--refresh', '-r', help='Refresh interval in seconds'),
):
    """Live telemetry dashboard."""
    with Live(console=console, refresh_per_second=1) as live:
        while True:
            layout = _build_dashboard()
            live.update(layout)
            import time
            time.sleep(refresh)


def _build_dashboard() -> Layout:
    """Build live dashboard layout."""
    layout = Layout()
    
    # Split into sections
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3)
    )
    
    # Header
    header_text = f"[bold]Telemetry Dashboard[/bold] - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    layout["header"].update(Panel(header_text, border_style="blue"))
    
    # Main section split into columns
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    
    # Recent events
    events_table = _build_events_table(None, None, None, 10, "1h")
    layout["left"].update(Panel(events_table, title="Recent Events", border_style="green"))
    
    # Active jobs
    jobs_table = _build_jobs_table('running', None, "24h")
    layout["right"].update(Panel(jobs_table, title="Active Jobs", border_style="yellow"))
    
    # Footer with summary
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get counts
    cur.execute("SELECT COUNT(*) FROM telemetry.events WHERE created_at > NOW() - INTERVAL '1 hour'")
    events_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM telemetry.jobs WHERE status = 'running'")
    running_jobs = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM telemetry.errors WHERE status = 'open' AND created_at > NOW() - INTERVAL '24 hours'")
    open_errors = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    footer_text = (
        f"Events (1h): {events_count} | "
        f"Running Jobs: {running_jobs} | "
        f"Open Errors (24h): {open_errors}"
    )
    layout["footer"].update(Panel(footer_text, border_style="dim"))
    
    return layout


@telemetry_app.command(name='stats')
def telemetry_stats(
    since: str = typer.Option('24h', '--since', help='Time window'),
):
    """Show telemetry statistics summary."""
    interval = _parse_interval(since)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    console.print(f"[bold]Telemetry Statistics (last {since})[/bold]\n")
    
    # Event counts by severity
    cur.execute("""
        SELECT severity, COUNT(*)
        FROM telemetry.events
        WHERE created_at > NOW() - %s::INTERVAL
        GROUP BY severity
        ORDER BY COUNT(*) DESC
    """, [interval])
    
    console.print("[cyan]Events by Severity:[/cyan]")
    for sev, count in cur.fetchall():
        console.print(f"  {sev}: {count}")
    
    # Job statistics
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'failed') as failed,
            COUNT(*) FILTER (WHERE status = 'running') as running,
            AVG(duration_ms) FILTER (WHERE status = 'completed') as avg_duration
        FROM telemetry.jobs
        WHERE created_at > NOW() - %s::INTERVAL
    """, [interval])
    
    row = cur.fetchone()
    if row:
        total, completed, failed, running, avg_dur = row
        console.print(f"\n[cyan]Job Statistics:[/cyan]")
        console.print(f"  Total: {total}")
        console.print(f"  Completed: {completed or 0}")
        console.print(f"  Failed: {failed or 0}")
        console.print(f"  Running: {running or 0}")
        if avg_dur:
            console.print(f"  Avg Duration: {avg_dur/1000:.2f}s")
    
    # Query statistics
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE was_slow) as slow,
            AVG(duration_ms) as avg_duration,
            MAX(duration_ms) as max_duration
        FROM telemetry.query_logs
        WHERE recorded_at > NOW() - %s::INTERVAL
    """, [interval])
    
    row = cur.fetchone()
    if row:
        total, slow, avg_dur, max_dur = row
        console.print(f"\n[cyan]Query Statistics:[/cyan]")
        console.print(f"  Total: {total}")
        console.print(f"  Slow: {slow or 0}")
        if avg_dur:
            console.print(f"  Avg Duration: {avg_dur:.2f}ms")
        if max_dur:
            console.print(f"  Max Duration: {max_dur:.2f}ms")
    
    # Error summary
    cur.execute("""
        SELECT 
            COUNT(DISTINCT error_hash) as unique_errors,
            SUM(occurrence_count) as total_occurrences
        FROM telemetry.errors
        WHERE created_at > NOW() - %s::INTERVAL
        AND status = 'open'
    """, [interval])
    
    row = cur.fetchone()
    if row:
        unique, total = row
        console.print(f"\n[cyan]Open Errors:[/cyan]")
        console.print(f"  Unique: {unique or 0}")
        console.print(f"  Total Occurrences: {total or 0}")
    
    cur.close()
    conn.close()


def _parse_interval(since: str) -> str:
    """Parse interval string to PostgreSQL interval."""
    # Convert shorthand to full interval
    if since.endswith('m'):
        return since
    elif since.endswith('h'):
        return since
    elif since.endswith('d'):
        return since
    elif since.endswith('s'):
        return since
    else:
        # Default to hours if just a number
        try:
            int(since)
            return f"{since}h"
        except ValueError:
            return since
