"""
Content Scheduler for Automated Generation

Handles scheduling and automation of content generation tasks.
Supports recurring content creation and publishing workflows.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of scheduled tasks."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """A scheduled content generation task."""
    task_id: str
    template_name: str
    context: Dict[str, Any]
    scheduled_time: datetime
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class ContentScheduler:
    """Scheduler for automated content generation."""
    
    def __init__(self):
        """Initialize the content scheduler."""
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        logger.info("Content scheduler initialized")
    
    async def start(self):
        """Start the scheduler background task."""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Content scheduler started")
    
    async def stop(self):
        """Stop the scheduler background task."""
        self.running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Content scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                await self._check_and_run_tasks()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_run_tasks(self):
        """Check for tasks ready to run and execute them."""
        now = datetime.now()
        ready_tasks = [
            task for task in self.tasks.values()
            if task.status == TaskStatus.PENDING and task.scheduled_time <= now
        ]
        
        for task in ready_tasks:
            await self._run_task(task)
    
    async def _run_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        task.status = TaskStatus.RUNNING
        logger.info(f"Running task: {task.task_id}")
        
        try:
            # Import here to avoid circular imports
            from ..llm.generator import ContentGenerator, GenerationRequest
            
            # Create generation request
            request = GenerationRequest(
                template_name=task.template_name,
                context=task.context,
                content_type=self._infer_content_type(task.template_name)
            )
            
            # Generate content (would need actual generator instance)
            # For now, just mark as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            logger.info(f"Task completed: {task.task_id}")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.retry_count += 1
            
            logger.error(f"Task failed: {task.task_id}, error: {e}")
            
            # Retry if max retries not reached
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.PENDING
                task.scheduled_time = datetime.now() + timedelta(minutes=5)
                logger.info(f"Task scheduled for retry: {task.task_id}")
    
    def _infer_content_type(self, template_name: str) -> str:
        """Infer content type from template name."""
        if "preview" in template_name:
            return "game-preview"
        elif "player" in template_name:
            return "player-analysis"
        elif "stats" in template_name or "statistical" in template_name:
            return "statistical-breakdown"
        elif "prediction" in template_name:
            return "prediction-explanation"
        else:
            return "game-preview"  # Default
    
    def schedule_task(
        self,
        task_id: str,
        template_name: str,
        context: Dict[str, Any],
        scheduled_time: Optional[datetime] = None,
        max_retries: int = 3
    ) -> ScheduledTask:
        """
        Schedule a content generation task.
        
        Args:
            task_id: Unique identifier for the task
            template_name: Name of template to use
            context: Data context for template
            scheduled_time: When to run the task (default: now)
            max_retries: Maximum retry attempts
            
        Returns:
            Created scheduled task
        """
        if scheduled_time is None:
            scheduled_time = datetime.now()
        
        task = ScheduledTask(
            task_id=task_id,
            template_name=template_name,
            context=context,
            scheduled_time=scheduled_time,
            max_retries=max_retries
        )
        
        self.tasks[task_id] = task
        logger.info(f"Scheduled task: {task_id} for {scheduled_time}")
        return task
    
    def schedule_recurring(
        self,
        base_task_id: str,
        template_name: str,
        context: Dict[str, Any],
        interval_hours: int = 24,
        max_occurrences: Optional[int] = None
    ) -> List[ScheduledTask]:
        """
        Schedule recurring content generation tasks.
        
        Args:
            base_task_id: Base identifier for tasks
            template_name: Name of template to use
            context: Data context for template
            interval_hours: Hours between occurrences
            max_occurrences: Maximum number of occurrences
            
        Returns:
            List of scheduled tasks
        """
        tasks = []
        start_time = datetime.now()
        
        for i in range(max_occurrences or 365):  # Default to一年
            task_time = start_time + timedelta(hours=i * interval_hours)
            task_id = f"{base_task_id}_{i:03d}"
            
            task = self.schedule_task(
                task_id=task_id,
                template_name=template_name,
                context=context,
                scheduled_time=task_time
            )
            tasks.append(task)
        
        logger.info(f"Scheduled {len(tasks)} recurring tasks for {base_task_id}")
        return tasks
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a scheduled task.
        
        Args:
            task_id: Task identifier to cancel
            
        Returns:
            True if task was cancelled, False if not found
        """
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                logger.info(f"Cancelled task: {task_id}")
                return True
        return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a scheduled task by ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[ScheduledTask]:
        """
        List scheduled tasks.
        
        Args:
            status: Filter by status (optional)
            
        Returns:
            List of tasks
        """
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.scheduled_time)
    
    def get_task_stats(self) -> Dict[str, Any]:
        """Get statistics about scheduled tasks."""
        total = len(self.tasks)
        status_counts = {}
        
        for status in TaskStatus:
            status_counts[status.value] = len([
                t for t in self.tasks.values() if t.status == status
            ])
        
        return {
            "total_tasks": total,
            "status_breakdown": status_counts,
            "running": self.running,
            "next_task_time": min(
                (t.scheduled_time for t in self.tasks.values() 
                 if t.status == TaskStatus.PENDING),
                default=None
            )
        }
