"""Database-driven job scheduler for data ingestion.

Manages ingestion jobs stored in PostgreSQL with:
- Cron-based scheduling
- Job execution tracking
- WebSocket connection monitoring

Author: Agent Cascade
Date: 2026-04-30
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class DatabaseScheduler:
    """Scheduler that uses PostgreSQL for job persistence.
    
    Reads jobs from scheduler.jobs table and executes them.
    Supports both cron-style and interval-based scheduling.
    
    Example:
        >>> scheduler = DatabaseScheduler(db_pool)
        >>> await scheduler.start()
        >>> 
        >>> # Jobs are defined in database
        >>> # scheduler.jobs table drives execution
    """
    
    def __init__(
        self,
        db_pool,
        check_interval: int = 10,
        max_concurrent_jobs: int = 5
    ):
        """Initialize database scheduler.
        
        Args:
            db_pool: Async database connection pool
            check_interval: Seconds between job checks
            max_concurrent_jobs: Max parallel jobs
        """
        self.db_pool = db_pool
        self.check_interval = check_interval
        self.max_concurrent_jobs = max_concurrent_jobs
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._job_handlers: Dict[str, Callable] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        
        logger.info("DatabaseScheduler initialized")
    
    def register_job_handler(self, job_type: str, handler: Callable) -> None:
        """Register a handler for a job type.
        
        Args:
            job_type: Job type from jobs table
            handler: Async function to execute job
        """
        self._job_handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type}")
    
    async def start(self) -> None:
        """Start the scheduler loop."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Database scheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Database scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                # Get due jobs from database
                jobs = await self._get_due_jobs()
                
                # Execute each job
                for job in jobs:
                    async with self._semaphore:
                        asyncio.create_task(self._execute_job(job))
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    async def _get_due_jobs(self) -> List[Dict]:
        """Query database for jobs ready to run.
        
        Returns:
            List of job dictionaries from scheduler.jobs
        """
        if not self.db_pool:
            return []
        
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM scheduler.get_due_jobs()
                    """
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to load jobs: {e}")
            return []
    
    async def _execute_job(self, job: Dict) -> None:
        """Execute a single job with logging."""
        job_id = job['job_id']
        job_name = job['job_name']
        job_type = job['job_type']
        
        logger.info(f"Executing job: {job_name} (type: {job_type})")
        
        try:
            # Log job start
            run_id = await self._log_job_start(job_id)
            
            # Get handler
            handler = self._job_handlers.get(job_type)
            if not handler:
                raise ValueError(f"No handler for job type: {job_type}")
            
            # Execute handler
            result = await handler(job)
            
            # Log success
            await self._log_job_complete(
                run_id, 'success',
                result.get('records', 0) if isinstance(result, dict) else 0
            )
            
        except Exception as e:
            logger.error(f"Job {job_name} failed: {e}")
            await self._log_job_complete(job_id, 'failed', 0, str(e))
    
    async def _log_job_start(self, job_id: int) -> int:
        """Log job start to database."""
        if not self.db_pool:
            return 0
        
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT scheduler.log_job_start($1)",
                    job_id
                )
                return result
        except Exception as e:
            logger.warning(f"Failed to log job start: {e}")
            return 0
    
    async def _log_job_complete(
        self,
        run_id: int,
        status: str,
        records: int,
        error: str = None
    ) -> None:
        """Log job completion to database."""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "SELECT scheduler.log_job_complete($1, $2, $3, $4)",
                    run_id, status, records, error
                )
        except Exception as e:
            logger.warning(f"Failed to log job completion: {e}")
    
    # Convenience methods for job management
    
    async def add_job(self, job_config: Dict) -> int:
        """Add a new job to the scheduler.
        
        Args:
            job_config: Job configuration dict
            
        Returns:
            New job_id
        """
        if not self.db_pool:
            raise RuntimeError("Database pool required")
        
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval(
                """
                INSERT INTO scheduler.jobs (
                    job_name, job_type, source_type, schedule_type,
                    schedule_expression, sport, data_types, enabled,
                    description
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING job_id
                """,
                job_config['job_name'],
                job_config['job_type'],
                job_config.get('source_type', 'the_odds_api'),
                job_config.get('schedule_type', 'interval'),
                job_config.get('schedule_expression', '1 minute'),
                job_config.get('sport', 'mlb'),
                job_config.get('data_types', ['odds']),
                job_config.get('enabled', True),
                job_config.get('description', '')
            )
            return result
    
    async def enable_job(self, job_id: int) -> None:
        """Enable a job."""
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE scheduler.jobs SET enabled = TRUE WHERE job_id = $1",
                    job_id
                )
    
    async def disable_job(self, job_id: int) -> None:
        """Disable a job."""
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE scheduler.jobs SET enabled = FALSE WHERE job_id = $1",
                    job_id
                )
    
    async def get_job_status(self) -> List[Dict]:
        """Get status of all jobs."""
        if not self.db_pool:
            return []
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM scheduler.job_status")
            return [dict(row) for row in rows]
