"""Unified Live Game Scheduler.

Combines SmartScheduler's adaptive polling with EnhancedLivePipeline's
advanced processing capabilities for a single, cohesive live data
ingestion system.

Author: Agent Cascade
Date: 2026-05-05
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from baseball.core.db import get_db_connection
from baseball.ingestion.smart_scheduler import SmartScheduler, PollingSchedule
from baseball.ingestion.enhanced_live_pipeline import EnhancedLivePipeline
from baseball.ingestion.scheduler import DatabaseScheduler
from baseball.ingestion.error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class SchedulerStatus(Enum):
    """Status of the unified scheduler."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class SchedulerConfig:
    """Unified scheduler configuration."""
    
    # Polling intervals (seconds)
    during_game: int = 10
    pre_game: int = 60
    game_day: int = 300
    off_hours: int = 3600
    
    # Pipeline settings
    buffer_size: int = 1000
    prediction_interval: int = 30
    feature_calc_interval: int = 15
    
    # Error handling
    max_retries: int = 3
    circuit_breaker_threshold: int = 5
    
    # Monitoring
    monitoring_interval: int = 60
    alert_thresholds: Dict[str, int] = field(default_factory=dict)
    
    # Coordination settings
    max_concurrent_operations: int = 5
    coordination_timeout: int = 30
    
    # Database settings
    job_persistence: bool = True
    metrics_retention_days: int = 30


@dataclass
class FeedConfig:
    """Configuration for a live data feed."""
    
    name: str
    url: str
    feed_type: str  # 'mlb', 'espn', 'statcast', etc.
    enabled: bool = True
    priority: int = 5  # 1-10, higher = more important
    
    # Feed-specific settings
    polling_interval: Optional[int] = None  # Override default
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5
    
    # Processing settings
    processing_level: str = 'full'  # 'full', 'basic', 'minimal'
    buffer_size: Optional[int] = None


@dataclass
class SchedulerStatusInfo:
    """Comprehensive status information for the scheduler."""
    
    status: SchedulerStatus
    uptime_seconds: float
    start_time: Optional[str]
    last_error: Optional[str]
    
    # Component status
    smart_scheduler: Dict[str, Any]
    enhanced_pipeline: Dict[str, Any]
    database_scheduler: Dict[str, Any]
    error_handler: Dict[str, Any]
    
    # Performance metrics
    total_polls: int
    successful_polls: int
    failed_polls: int
    average_poll_time: float
    
    # Active feeds
    active_feeds: List[str]
    total_feeds: int


class SchedulerCoordination:
    """Manages coordination between scheduler components."""
    
    def __init__(self, config: SchedulerConfig):
        self.config = config
        self._component_status: Dict[str, Dict[str, Any]] = {}
        self._active_operations: Dict[str, asyncio.Task] = {}
        self._coordination_lock = asyncio.Lock()
        
    async def register_component(self, name: str, component: Any) -> None:
        """Register a component for coordination."""
        self._component_status[name] = {
            'component': component,
            'status': 'registered',
            'last_update': None,
            'error_count': 0,
        }
        logger.info(f"Component {name} registered for coordination")
    
    async def update_component_status(self, name: str, status: Dict[str, Any]) -> None:
        """Update component status."""
        async with self._coordination_lock:
            if name in self._component_status:
                self._component_status[name].update(status)
                self._component_status[name]['last_update'] = asyncio.get_event_loop().time()
    
    async def get_component_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get component status."""
        return self._component_status.get(name)
    
    async def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all components."""
        return self._component_status.copy()
    
    async def coordinate_operation(self, name: str, operation: Callable, *args, **kwargs) -> Any:
        """Coordinate an operation across components."""
        async with self._coordination_lock:
            if name in self._active_operations:
                logger.warning(f"Operation {name} already active")
                return None
            
            task = asyncio.create_task(operation(*args, **kwargs))
            self._active_operations[name] = task
            
            try:
                result = await asyncio.wait_for(task, timeout=self.config.coordination_timeout)
                return result
            except asyncio.TimeoutError:
                logger.error(f"Operation {name} timed out")
                task.cancel()
                raise
            finally:
                self._active_operations.pop(name, None)


class UnifiedLiveGameScheduler:
    """Unified scheduler for live games with enhanced pipeline integration.
    
    This class combines the SmartScheduler's adaptive polling with the
    EnhancedLivePipeline's advanced processing capabilities to provide
    a single, cohesive live data ingestion system.
    
    Example:
        >>> config = SchedulerConfig(during_game=5, buffer_size=2000)
        >>> scheduler = UnifiedLiveGameScheduler(config)
        >>> await scheduler.start()
        >>> 
        >>> # Add a feed
        >>> feed_config = FeedConfig(
        ...     name="mlb_primary",
        ...     url="wss://mlb.com/live",
        ...     feed_type="mlb"
        ... )
        >>> await scheduler.add_feed(feed_config)
        >>> 
        >>> # Get status
        >>> status = scheduler.get_status()
        >>> print(f"Status: {status.status}")
        >>> 
        >>> # Stop scheduler
        >>> await scheduler.stop()
    """
    
    def __init__(self, config: Optional[SchedulerConfig] = None) -> None:
        """Initialize the unified scheduler.
        
        Args:
            config: Scheduler configuration, uses defaults if None
        """
        self.config = config or SchedulerConfig()
        
        # Initialize components
        self.smart_scheduler = SmartScheduler()
        self.enhanced_pipeline = EnhancedLivePipeline()
        self.database_scheduler = DatabaseScheduler()
        self.error_handler = ErrorHandler()
        self.coordination = SchedulerCoordination(self.config)
        
        # Scheduler state
        self._status = SchedulerStatus.STOPPED
        self._start_time: Optional[float] = None
        self._last_error: Optional[str] = None
        
        # Performance tracking
        self._total_polls = 0
        self._successful_polls = 0
        self._failed_polls = 0
        self._poll_times: List[float] = []
        
        # Feed management
        self._feeds: Dict[str, FeedConfig] = {}
        self._active_feeds: Dict[str, Any] = {}
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._coordination_task: Optional[asyncio.Task] = None
        
        logger.info("UnifiedLiveGameScheduler initialized")
    
    async def start(self) -> None:
        """Start the unified scheduler and all components."""
        if self._status != SchedulerStatus.STOPPED:
            logger.warning(f"Scheduler already {self._status.value}")
            return
        
        self._status = SchedulerStatus.STARTING
        self._start_time = asyncio.get_event_loop().time()
        
        try:
            # Register components with coordination layer
            await self._register_components()
            
            # Start components in order
            await self._start_components()
            
            # Start background tasks
            await self._start_background_tasks()
            
            self._status = SchedulerStatus.RUNNING
            logger.info("UnifiedLiveGameScheduler started successfully")
            
        except Exception as e:
            self._status = SchedulerStatus.ERROR
            self._last_error = str(e)
            logger.exception(f"Failed to start scheduler: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the unified scheduler and all components."""
        if self._status == SchedulerStatus.STOPPED:
            return
        
        self._status = SchedulerStatus.STOPPING
        
        try:
            # Stop background tasks
            await self._stop_background_tasks()
            
            # Stop components in reverse order
            await self._stop_components()
            
            # Cleanup
            await self._cleanup()
            
            self._status = SchedulerStatus.STOPPED
            logger.info("UnifiedLiveGameScheduler stopped successfully")
            
        except Exception as e:
            self._status = SchedulerStatus.ERROR
            self._last_error = str(e)
            logger.exception(f"Error during shutdown: {e}")
            raise
    
    async def add_feed(self, feed_config: FeedConfig) -> None:
        """Add a new live data feed.
        
        Args:
            feed_config: Configuration for the feed
        """
        if self._status != SchedulerStatus.RUNNING:
            raise RuntimeError(f"Cannot add feed to scheduler in {self._status.value} state")
        
        if feed_config.name in self._feeds:
            raise ValueError(f"Feed {feed_config.name} already exists")
        
        try:
            # Store feed configuration
            self._feeds[feed_config.name] = feed_config
            
            # Add feed to pipeline
            await self.enhanced_pipeline.add_feed({
                'name': feed_config.name,
                'url': feed_config.url,
                'type': feed_config.feed_type,
                'enabled': feed_config.enabled,
                'priority': feed_config.priority,
                'timeout': feed_config.timeout,
                'retry_attempts': feed_config.retry_attempts,
                'retry_delay': feed_config.retry_delay,
            })
            
            # Start feed if enabled
            if feed_config.enabled:
                await self.enhanced_pipeline.start_feed(feed_config.name)
                self._active_feeds[feed_config.name] = feed_config
            
            logger.info(f"Added feed {feed_config.name}")
            
        except Exception as e:
            # Cleanup on failure
            self._feeds.pop(feed_config.name, None)
            logger.exception(f"Failed to add feed {feed_config.name}: {e}")
            raise
    
    async def remove_feed(self, feed_name: str) -> None:
        """Remove a live data feed.
        
        Args:
            feed_name: Name of the feed to remove
        """
        if feed_name not in self._feeds:
            raise ValueError(f"Feed {feed_name} not found")
        
        try:
            # Stop feed if active
            if feed_name in self._active_feeds:
                await self.enhanced_pipeline.stop_feed(feed_name)
                self._active_feeds.pop(feed_name, None)
            
            # Remove from pipeline
            await self.enhanced_pipeline.remove_feed(feed_name)
            
            # Remove configuration
            self._feeds.pop(feed_name, None)
            
            logger.info(f"Removed feed {feed_name}")
            
        except Exception as e:
            logger.exception(f"Failed to remove feed {feed_name}: {e}")
            raise
    
    def get_status(self) -> SchedulerStatusInfo:
        """Get comprehensive status information.
        
        Returns:
            Detailed status information for the scheduler
        """
        uptime = 0.0
        if self._start_time:
            uptime = asyncio.get_event_loop().time() - self._start_time
        
        # Get component statuses
        smart_status = self._get_smart_scheduler_status()
        pipeline_status = self._get_pipeline_status()
        db_status = self._get_database_scheduler_status()
        error_status = self._get_error_handler_status()
        
        # Calculate performance metrics
        avg_poll_time = 0.0
        if self._poll_times:
            avg_poll_time = sum(self._poll_times) / len(self._poll_times)
        
        return SchedulerStatusInfo(
            status=self._status,
            uptime_seconds=uptime,
            start_time=self._start_time,
            last_error=self._last_error,
            smart_scheduler=smart_status,
            enhanced_pipeline=pipeline_status,
            database_scheduler=db_status,
            error_handler=error_status,
            total_polls=self._total_polls,
            successful_polls=self._successful_polls,
            failed_polls=self._failed_polls,
            average_poll_time=avg_poll_time,
            active_feeds=list(self._active_feeds.keys()),
            total_feeds=len(self._feeds),
        )
    
    async def run_predictions(self, games: Optional[List[int]] = None) -> Dict[str, Any]:
        """Run predictions for specified games or all active games.
        
        Args:
            games: List of game PKs, if None runs for all active games
            
        Returns:
            Prediction results and statistics
        """
        if self._status != SchedulerStatus.RUNNING:
            raise RuntimeError(f"Cannot run predictions in {self._status.value} state")
        
        try:
            # Run predictions through pipeline
            results = await self.enhanced_pipeline.run_live_predictions(games)
            
            logger.info(f"Ran predictions for {len(results.get('games', []))} games")
            return results
            
        except Exception as e:
            logger.exception(f"Failed to run predictions: {e}")
            raise
    
    # Private methods
    
    async def _register_components(self) -> None:
        """Register components with coordination layer."""
        await self.coordination.register_component('smart_scheduler', self.smart_scheduler)
        await self.coordination.register_component('enhanced_pipeline', self.enhanced_pipeline)
        await self.coordination.register_component('database_scheduler', self.database_scheduler)
        await self.coordination.register_component('error_handler', self.error_handler)
    
    async def _start_components(self) -> None:
        """Start all scheduler components."""
        # Start error handler first
        await self.error_handler.start()
        
        # Start database scheduler
        if self.config.job_persistence:
            await self.database_scheduler.start()
        
        # Start enhanced pipeline
        await self.enhanced_pipeline.start()
        
        # Start smart scheduler (modified to use pipeline)
        await self._start_smart_scheduler()
    
    async def _start_smart_scheduler(self) -> None:
        """Start smart scheduler with pipeline integration."""
        # Replace the ingestion method with pipeline integration
        original_execute = self.smart_scheduler._execute_ingestion
        self.smart_scheduler._execute_ingestion = self._execute_pipeline_ingestion
        
        await self.smart_scheduler.start()
    
    async def _execute_pipeline_ingestion(self) -> None:
        """Execute ingestion through enhanced pipeline (no subprocess)."""
        start_time = asyncio.get_event_loop().time()
        self._total_polls += 1
        
        try:
            # Ensure pipeline is running
            if not self.enhanced_pipeline.is_running():
                await self.enhanced_pipeline.start()
            
            # Run live predictions
            await self.enhanced_pipeline.run_live_predictions()
            
            # Update metrics
            poll_time = asyncio.get_event_loop().time() - start_time
            self._poll_times.append(poll_time)
            self._successful_polls += 1
            
            # Keep only last 100 poll times
            if len(self._poll_times) > 100:
                self._poll_times = self._poll_times[-100:]
            
            logger.debug(f"Pipeline ingestion completed in {poll_time:.2f}s")
            
        except Exception as e:
            self._failed_polls += 1
            self._last_error = str(e)
            
            # Handle error through error handler
            await self.error_handler.handle_error(e, context={
                'component': 'unified_scheduler',
                'operation': 'pipeline_ingestion',
                'poll_count': self._total_polls,
            })
            
            raise
    
    async def _stop_components(self) -> None:
        """Stop all scheduler components."""
        # Stop smart scheduler
        await self.smart_scheduler.stop()
        
        # Stop enhanced pipeline
        await self.enhanced_pipeline.stop()
        
        # Stop database scheduler
        if self.config.job_persistence:
            await self.database_scheduler.stop()
        
        # Stop error handler
        await self.error_handler.stop()
    
    async def _start_background_tasks(self) -> None:
        """Start background monitoring and coordination tasks."""
        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Start coordination task
        self._coordination_task = asyncio.create_task(self._coordination_loop())
    
    async def _stop_background_tasks(self) -> None:
        """Stop background tasks."""
        tasks = [self._monitoring_task, self._coordination_task]
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self._monitoring_task = None
        self._coordination_task = None
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self._status == SchedulerStatus.RUNNING:
            try:
                # Update component statuses
                await self._update_component_statuses()
                
                # Check for alerts
                await self._check_alerts()
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self.config.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    async def _coordination_loop(self) -> None:
        """Background coordination loop."""
        while self._status == SchedulerStatus.RUNNING:
            try:
                # Coordinate component operations
                await self._coordinate_components()
                
                # Wait for next coordination cycle
                await asyncio.sleep(30)  # Coordinate every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Coordination loop error: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    async def _update_component_statuses(self) -> None:
        """Update status of all components."""
        try:
            # Update smart scheduler status
            await self.coordination.update_component_status(
                'smart_scheduler',
                {'status': 'running', 'last_poll': asyncio.get_event_loop().time()}
            )
            
            # Update pipeline status
            pipeline_status = self.enhanced_pipeline.get_pipeline_status()
            await self.coordination.update_component_status(
                'enhanced_pipeline',
                pipeline_status
            )
            
        except Exception as e:
            logger.exception(f"Error updating component statuses: {e}")
    
    async def _check_alerts(self) -> None:
        """Check for alert conditions."""
        try:
            # Check failure rate
            if self._total_polls > 0:
                failure_rate = self._failed_polls / self._total_polls
                threshold = self.config.alert_thresholds.get('failure_rate', 0.1)
                
                if failure_rate > threshold:
                    await self.error_handler.handle_error(
                        Exception(f"High failure rate: {failure_rate:.2%}"),
                        context={'component': 'unified_scheduler', 'metric': 'failure_rate'}
                    )
            
        except Exception as e:
            logger.exception(f"Error checking alerts: {e}")
    
    async def _coordinate_components(self) -> None:
        """Coordinate between components."""
        try:
            # Get all component statuses
            statuses = await self.coordination.get_all_status()
            
            # Check for component issues
            for name, status in statuses.items():
                if status.get('error_count', 0) > self.config.circuit_breaker_threshold:
                    logger.warning(f"Component {name} has high error count: {status['error_count']}")
            
        except Exception as e:
            logger.exception(f"Error coordinating components: {e}")
    
    async def _cleanup(self) -> None:
        """Cleanup resources."""
        self._feeds.clear()
        self._active_feeds.clear()
        self._poll_times.clear()
        
        # Reset metrics
        self._total_polls = 0
        self._successful_polls = 0
        self._failed_polls = 0
    
    def _get_smart_scheduler_status(self) -> Dict[str, Any]:
        """Get smart scheduler status."""
        return {
            'running': self.smart_scheduler._running,
            'current_interval': self.smart_scheduler.get_current_interval(),
            'game_windows': len(self.smart_scheduler._game_windows),
        }
    
    def _get_pipeline_status(self) -> Dict[str, Any]:
        """Get enhanced pipeline status."""
        return self.enhanced_pipeline.get_pipeline_status()
    
    def _get_database_scheduler_status(self) -> Dict[str, Any]:
        """Get database scheduler status."""
        return {
            'running': self.database_scheduler._running,
            'max_concurrent': self.database_scheduler.max_concurrent_jobs,
        }
    
    def _get_error_handler_status(self) -> Dict[str, Any]:
        """Get error handler status."""
        return {
            'running': self.error_handler._running,
            'error_count': len(self.error_handler._error_history),
        }
