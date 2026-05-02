"""
Query Progress Tracking Module

Tracks active queries and their progress through pg_stat_activity.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from baseball.core.db import get_db_connection


@dataclass
class QueryProgress:
    """Represents the progress of a query."""
    pid: int
    query_id: Optional[str]
    query: str
    state: str  # active, idle, idle in transaction, etc.
    wait_event: Optional[str]
    wait_event_type: Optional[str]
    backend_start: Optional[datetime]
    query_start: Optional[datetime]
    state_change: Optional[datetime]
    usename: Optional[str]
    datname: Optional[str]
    progress: Optional[float] = None  # 0-100 if available
    estimated_remaining: Optional[float] = None  # seconds

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'pid': self.pid,
            'query_id': self.query_id,
            'query': self.query[:200] if self.query else '',  # Truncate for display
            'state': self.state,
            'wait_event': self.wait_event,
            'wait_event_type': self.wait_event_type,
            'backend_start': self.backend_start.isoformat() if self.backend_start else None,
            'query_start': self.query_start.isoformat() if self.query_start else None,
            'state_change': self.state_change.isoformat() if self.state_change else None,
            'usename': self.usename,
            'datname': self.datname,
            'progress': self.progress,
            'estimated_remaining': self.estimated_remaining,
        }


class QueryProgressTracker:
    """
    Tracks query progress for long-running database operations.
    
    Usage:
        tracker = QueryProgressTracker()
        active_queries = tracker.get_active_queries()
        
        # Track a specific query
        tracker.start_tracking(query_id='my_query', description='Training model')
        # ... run query ...
        tracker.update_progress(query_id='my_query', progress=50)
        # ... complete ...
        tracker.complete(query_id='my_query')
    """
    
    def __init__(self):
        """Initialize the progress tracker."""
        self._tracked_queries: Dict[str, Dict[str, Any]] = {}
    
    def get_active_queries(
        self,
        include_idle: bool = False,
        database: Optional[str] = None
    ) -> List[QueryProgress]:
        """
        Get list of currently active queries from pg_stat_activity.
        
        Args:
            include_idle: Whether to include idle connections
            database: Filter to specific database
        
        Returns:
            List of QueryProgress objects
        """
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT 
                pid,
                query_id,
                query,
                state,
                wait_event,
                wait_event_type,
                backend_start,
                query_start,
                state_change,
                usename,
                datname
            FROM pg_stat_activity
            WHERE state != 'idle'
                AND pid != pg_backend_pid()
                AND query NOT LIKE '%pg_stat_activity%'
        """
        
        if not include_idle:
            query += " AND state = 'active'"
        
        if database:
            query += " AND datname = %s"
            cur.execute(query, (database,))
        else:
            cur.execute(query)
        
        results = []
        for row in cur.fetchall():
            progress = QueryProgress(
                pid=row[0],
                query_id=row[1],
                query=row[2] or '',
                state=row[3],
                wait_event=row[4],
                wait_event_type=row[5],
                backend_start=row[6],
                query_start=row[7],
                state_change=row[8],
                usename=row[9],
                datname=row[10],
            )
            
            # Calculate progress if we have tracked info
            if progress.query_id and progress.query_id in self._tracked_queries:
                tracked = self._tracked_queries[progress.query_id]
                progress.progress = tracked.get('progress', 0)
                progress.estimated_remaining = tracked.get('estimated_remaining')
            
            results.append(progress)
        
        cur.close()
        conn.close()
        
        return results
    
    def start_tracking(
        self,
        query_id: str,
        description: str,
        total_steps: int = 100
    ) -> None:
        """
        Start tracking a query for progress reporting.
        
        Args:
            query_id: Unique identifier for this query
            description: Human-readable description
            total_steps: Total number of steps (default 100 for percentage)
        """
        self._tracked_queries[query_id] = {
            'query_id': query_id,
            'description': description,
            'total_steps': total_steps,
            'current_step': 0,
            'progress': 0.0,
            'started_at': datetime.now(),
            'estimated_remaining': None,
            'status': 'running',
        }
    
    def update_progress(
        self,
        query_id: str,
        current_step: Optional[int] = None,
        progress: Optional[float] = None,
        estimated_remaining: Optional[float] = None
    ) -> None:
        """
        Update progress for a tracked query.
        
        Args:
            query_id: Query identifier
            current_step: Current step number (optional)
            progress: Progress percentage 0-100 (optional)
            estimated_remaining: Estimated seconds remaining (optional)
        """
        if query_id not in self._tracked_queries:
            return
        
        tracked = self._tracked_queries[query_id]
        
        if current_step is not None:
            tracked['current_step'] = current_step
            tracked['progress'] = (current_step / tracked['total_steps']) * 100
        
        if progress is not None:
            tracked['progress'] = progress
        
        if estimated_remaining is not None:
            tracked['estimated_remaining'] = estimated_remaining
        elif tracked['progress'] > 0:
            # Calculate estimated remaining based on elapsed time
            elapsed = (datetime.now() - tracked['started_at']).total_seconds()
            estimated_total = elapsed / (tracked['progress'] / 100)
            tracked['estimated_remaining'] = estimated_total - elapsed
    
    def complete(self, query_id: str) -> None:
        """Mark a query as complete."""
        if query_id in self._tracked_queries:
            self._tracked_queries[query_id]['status'] = 'completed'
            self._tracked_queries[query_id]['progress'] = 100.0
    
    def fail(self, query_id: str, error: str) -> None:
        """Mark a query as failed."""
        if query_id in self._tracked_queries:
            self._tracked_queries[query_id]['status'] = 'failed'
            self._tracked_queries[query_id]['error'] = error
    
    def get_tracked_query(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Get tracked query info."""
        return self._tracked_queries.get(query_id)
    
    def list_tracked_queries(self) -> List[Dict[str, Any]]:
        """List all tracked queries."""
        return list(self._tracked_queries.values())
    
    def cleanup_old_queries(self, max_age_seconds: int = 3600) -> None:
        """Remove old completed queries from tracking."""
        now = datetime.now()
        to_remove = []
        
        for query_id, info in self._tracked_queries.items():
            if info['status'] in ('completed', 'failed'):
                age = (now - info['started_at']).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(query_id)
        
        for query_id in to_remove:
            del self._tracked_queries[query_id]


def get_active_queries(
    include_idle: bool = False,
    database: Optional[str] = None
) -> List[QueryProgress]:
    """Convenience function to get active queries without creating a tracker."""
    tracker = QueryProgressTracker()
    return tracker.get_active_queries(include_idle=include_idle, database=database)


def get_query_progress(query_id: str) -> Optional[Dict[str, Any]]:
    """Get progress for a specific tracked query."""
    tracker = QueryProgressTracker()
    return tracker.get_tracked_query(query_id)
