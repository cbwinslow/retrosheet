"""
Query Monitoring FastAPI Application

Provides HTTP endpoints for monitoring active database queries.
"""

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from baseball.monitoring.progress import QueryProgressTracker, QueryProgress


def create_monitoring_app() -> FastAPI:
    """Create FastAPI application for query monitoring."""
    app = FastAPI(
        title="Query Monitoring API",
        description="Real-time query progress monitoring",
        version="1.0.0",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    tracker = QueryProgressTracker()
    
    @app.get("/")
    async def root() -> Dict[str, str]:
        """Root endpoint."""
        return {"message": "Query Monitoring API", "version": "1.0.0"}
    
    @app.get("/queries/active")
    async def get_active_queries(
        include_idle: bool = False,
        database: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get currently active queries from pg_stat_activity."""
        queries = tracker.get_active_queries(
            include_idle=include_idle,
            database=database
        )
        
        return {
            "count": len(queries),
            "queries": [q.to_dict() for q in queries]
        }
    
    @app.get("/queries/tracked")
    async def get_tracked_queries() -> Dict[str, Any]:
        """Get all tracked queries with their progress."""
        queries = tracker.list_tracked_queries()
        
        return {
            "count": len(queries),
            "queries": queries
        }
    
    @app.get("/queries/tracked/{query_id}")
    async def get_tracked_query(query_id: str) -> Dict[str, Any]:
        """Get specific tracked query."""
        query = tracker.get_tracked_query(query_id)
        
        if query is None:
            return {"error": f"Query {query_id} not found"}
        
        return query
    
    @app.post("/queries/track/{query_id}")
    async def start_tracking(
        query_id: str,
        description: str = "Tracked query",
        total_steps: int = 100
    ) -> Dict[str, Any]:
        """Start tracking a query."""
        tracker.start_tracking(
            query_id=query_id,
            description=description,
            total_steps=total_steps
        )
        
        return {
            "status": "started",
            "query_id": query_id,
            "description": description
        }
    
    @app.post("/queries/track/{query_id}/progress")
    async def update_progress(
        query_id: str,
        current_step: Optional[int] = None,
        progress: Optional[float] = None,
        estimated_remaining: Optional[float] = None
    ) -> Dict[str, Any]:
        """Update progress for a tracked query."""
        tracker.update_progress(
            query_id=query_id,
            current_step=current_step,
            progress=progress,
            estimated_remaining=estimated_remaining
        )
        
        return {
            "status": "updated",
            "query_id": query_id,
            "progress": progress or current_step
        }
    
    @app.post("/queries/track/{query_id}/complete")
    async def complete_query(query_id: str) -> Dict[str, Any]:
        """Mark a tracked query as complete."""
        tracker.complete(query_id)
        
        return {
            "status": "completed",
            "query_id": query_id
        }
    
    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}
    
    return app


# Create default app instance
app = create_monitoring_app()
