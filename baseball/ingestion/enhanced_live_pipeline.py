"""Enhanced live data ingestion pipeline with detailed processing.

Integrates live data sources, processing, predictions, and monitoring
for comprehensive real-time baseball data handling.

Author: Agent Cascade
Date: 2026-05-04
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from baseball.core.db import get_db_connection
from baseball.ingestion.live_service import LiveDataIngestionService
from baseball.ingestion.live_data_processor import LiveGameDataProcessor
from baseball.sources.live_mlb import LiveMlbSource
from baseball.services.pipeline import PipelineService


logger = logging.getLogger(__name__)


class EnhancedLivePipeline:
    """Enhanced live data pipeline with comprehensive processing.
    
    Features:
    - Multi-source live data ingestion
    - Real-time play-by-play processing
    - Automated prediction updates
    - Feature calculation
    - Monitoring and alerting
    - Error recovery and retry logic
    """
    
    def __init__(
        self,
        buffer_size: int = 1000,
        prediction_interval: int = 30,
        feature_calc_interval: int = 15,
        monitoring_interval: int = 60,
        max_retries: int = 3,
        retry_delay: int = 5,
    ) -> None:
        """Initialize enhanced live pipeline.
        
        Args:
            buffer_size: Game state buffer size
            prediction_interval: Seconds between predictions
            feature_calc_interval: Seconds between feature calculations
            monitoring_interval: Seconds between monitoring updates
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries (seconds)
        """
        self.buffer_size = buffer_size
        self.prediction_interval = prediction_interval
        self.feature_calc_interval = feature_calc_interval
        self.monitoring_interval = monitoring_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Core components
        self.live_service: Optional[LiveDataIngestionService] = None
        self.data_processor: Optional[LiveGameDataProcessor] = None
        self.mlb_source: Optional[LiveMlbSource] = None
        self.pipeline_service: Optional[PipelineService] = None
        
        # Pipeline state
        self.is_running = False
        self.active_feeds: Dict[str, Dict] = {}
        self.last_health_check: Optional[datetime] = None
        
        # Statistics and monitoring
        self.stats = {
            'started_at': None,
            'total_games_processed': 0,
            'total_predictions_generated': 0,
            'total_features_calculated': 0,
            'total_errors': 0,
            'feed_disconnections': 0,
            'prediction_failures': 0,
            'feature_failures': 0,
        }
        
        logger.info('EnhancedLivePipeline initialized')
    
    async def start(self, feeds: Optional[List[Dict]] = None) -> None:
        """Start the enhanced live pipeline.
        
        Args:
            feeds: List of feed configurations to start
        """
        if self.is_running:
            logger.warning('Pipeline is already running')
            return
        
        logger.info('Starting enhanced live pipeline')
        
        try:
            # Initialize components
            await self._initialize_components()
            
            # Start monitoring
            monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            # Start feeds
            if feeds:
                await self._start_feeds(feeds)
            else:
                # Start default MLB live feed
                await self._start_default_feeds()
            
            self.is_running = True
            self.stats['started_at'] = datetime.now()
            
            logger.info('Enhanced live pipeline started successfully')
            
        except Exception as e:
            logger.error(f'Failed to start pipeline: {e}')
            await self.shutdown()
            raise
    
    async def _initialize_components(self) -> None:
        """Initialize all pipeline components."""
        logger.info('Initializing pipeline components')
        
        # Initialize live service
        self.live_service = LiveDataIngestionService(
            reconnect_attempts=5,
            reconnect_delay_base=2.0,
            message_buffer_size=self.buffer_size,
        )
        
        # Initialize data processor
        self.data_processor = LiveGameDataProcessor(
            buffer_size=self.buffer_size,
            prediction_interval=self.prediction_interval,
            feature_calc_interval=self.feature_calc_interval,
        )
        
        # Initialize MLB source
        self.mlb_source = LiveMlbSource()
        
        # Initialize pipeline service
        self.pipeline_service = PipelineService()
        
        # Connect processor to live service
        await self.data_processor.start_processing(self.live_service)
        
        logger.info('Pipeline components initialized')
    
    async def _start_default_feeds(self) -> None:
        """Start default live data feeds."""
        default_feeds = [
            {
                'name': 'mlb_live',
                'url': 'wss://ws.example.com/mlb',  # Would use real MLB WebSocket
                'description': 'MLB live game data',
                'priority': 'high',
            },
            {
                'name': 'mlb_scores',
                'url': 'wss://ws.example.com/mlb/scores',  # Would use real MLB scores WebSocket
                'description': 'MLB live scores',
                'priority': 'medium',
            },
        ]
        
        await self._start_feeds(default_feeds)
    
    async def _start_feeds(self, feeds: List[Dict]) -> None:
        """Start specified live data feeds.
        
        Args:
            feeds: List of feed configurations
        """
        logger.info(f'Starting {len(feeds)} feeds')
        
        for feed_config in feeds:
            try:
                feed_name = feed_config['name']
                url = feed_config['url']
                
                # Start feed with retry logic
                await self._start_feed_with_retry(feed_name, url, feed_config)
                
                # Track active feed
                self.active_feeds[feed_name] = {
                    **feed_config,
                    'started_at': datetime.now(),
                    'status': 'active',
                }
                
                logger.info(f'Started feed: {feed_name}')
                
            except Exception as e:
                logger.error(f'Failed to start feed {feed_config.get("name", "unknown")}: {e}')
                self.stats['total_errors'] += 1
    
    async def _start_feed_with_retry(self, feed_name: str, url: str, config: Dict) -> None:
        """Start a feed with retry logic."""
        for attempt in range(self.max_retries):
            try:
                await self.live_service.start_feed(
                    feed_name=feed_name,
                    url=url,
                    headers=config.get('headers'),
                    ping_interval=config.get('ping_interval', 30),
                    auto_reconnect=True,
                )
                return  # Success
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise  # Re-raise on final attempt
                
                logger.warning(f'Feed {feed_name} failed (attempt {attempt + 1}): {e}')
                await asyncio.sleep(self.retry_delay)
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for pipeline health."""
        while self.is_running:
            try:
                await self._perform_health_check()
                await self._update_statistics()
                await self._check_alert_conditions()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f'Monitoring loop error: {e}')
                await asyncio.sleep(self.monitoring_interval)
    
    async def _perform_health_check(self) -> None:
        """Perform health check on all components."""
        self.last_health_check = datetime.now()
        
        # Check live service
        if self.live_service:
            feed_stats = self.live_service._stats
            for feed_name, stats in feed_stats.items():
                if stats.get('errors', 0) > 10:  # Threshold for errors
                    logger.warning(f'Feed {feed_name} has high error count: {stats["errors"]}')
        
        # Check data processor
        if self.data_processor:
            processor_stats = self.data_processor.get_statistics()
            if processor_stats.get('errors', 0) > 5:  # Threshold for errors
                logger.warning(f'Data processor has high error count: {processor_stats["errors"]}')
        
        # Check database connectivity
        try:
            conn = get_db_connection()
            conn.close()
        except Exception as e:
            logger.error(f'Database connectivity issue: {e}')
            self.stats['total_errors'] += 1
    
    async def _update_statistics(self) -> None:
        """Update pipeline statistics."""
        if self.data_processor:
            processor_stats = self.data_processor.get_statistics()
            self.stats.update({
                'total_games_processed': processor_stats.get('games_processed', 0),
                'total_predictions_generated': processor_stats.get('predictions_generated', 0),
                'total_features_calculated': processor_stats.get('features_calculated', 0),
            })
        
        # Update feed statistics
        if self.live_service:
            feed_stats = self.live_service._stats
            total_feed_errors = sum(stats.get('errors', 0) for stats in feed_stats.values())
            self.stats['feed_disconnections'] = total_feed_errors
    
    async def _check_alert_conditions(self) -> None:
        """Check for alert conditions and send notifications."""
        alerts = []
        
        # Check for high error rates
        if self.stats['total_errors'] > 50:
            alerts.append({
                'type': 'high_error_rate',
                'message': f'High error rate: {self.stats["total_errors"]} errors',
                'severity': 'warning',
            })
        
        # Check for feed disconnections
        if self.stats['feed_disconnections'] > 10:
            alerts.append({
                'type': 'feed_disconnections',
                'message': f'Multiple feed disconnections: {self.stats["feed_disconnections"]}',
                'severity': 'critical',
            })
        
        # Check for prediction failures
        if self.stats['prediction_failures'] > 20:
            alerts.append({
                'type': 'prediction_failures',
                'message': f'High prediction failure rate: {self.stats["prediction_failures"]}',
                'severity': 'warning',
            })
        
        # Send alerts
        for alert in alerts:
            await self._send_alert(alert)
    
    async def _send_alert(self, alert: Dict) -> None:
        """Send alert notification."""
        logger.warning(f'ALERT [{alert["severity"].upper()}]: {alert["message"]}')
        
        # Store alert in database
        try:
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO monitoring.pipeline_alerts
                    (alert_type, message, severity, created_at, metadata)
                    VALUES (%s, %s, %s, NOW(), %s)
                """, (
                    alert['type'],
                    alert['message'],
                    alert['severity'],
                    json.dumps(alert),
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f'Failed to store alert: {e}')
    
    async def add_feed(self, feed_config: Dict) -> None:
        """Add a new feed to the running pipeline.
        
        Args:
            feed_config: Feed configuration
        """
        if not self.is_running:
            logger.warning('Cannot add feed to stopped pipeline')
            return
        
        feed_name = feed_config['name']
        url = feed_config['url']
        
        try:
            await self._start_feed_with_retry(feed_name, url, feed_config)
            
            self.active_feeds[feed_name] = {
                **feed_config,
                'started_at': datetime.now(),
                'status': 'active',
            }
            
            logger.info(f'Added feed: {feed_name}')
            
        except Exception as e:
            logger.error(f'Failed to add feed {feed_name}: {e}')
            self.stats['total_errors'] += 1
    
    async def remove_feed(self, feed_name: str) -> None:
        """Remove a feed from the running pipeline.
        
        Args:
            feed_name: Name of feed to remove
        """
        if not self.is_running:
            logger.warning('Cannot remove feed from stopped pipeline')
            return
        
        try:
            await self.live_service.stop_feed(feed_name)
            
            if feed_name in self.active_feeds:
                del self.active_feeds[feed_name]
            
            logger.info(f'Removed feed: {feed_name}')
            
        except Exception as e:
            logger.error(f'Failed to remove feed {feed_name}: {e}')
    
    def get_pipeline_status(self) -> Dict:
        """Get comprehensive pipeline status."""
        status = {
            'is_running': self.is_running,
            'started_at': self.stats['started_at'],
            'uptime': datetime.now() - self.stats['started_at'] if self.stats['started_at'] else None,
            'active_feeds': len(self.active_feeds),
            'feed_details': self.active_feeds.copy(),
            'statistics': self.stats.copy(),
            'last_health_check': self.last_health_check,
        }
        
        # Add processor statistics
        if self.data_processor:
            status['processor_stats'] = self.data_processor.get_statistics()
        
        # Add live service statistics
        if self.live_service:
            status['live_service_stats'] = self.live_service._stats.copy()
        
        return status
    
    async def run_live_predictions(self, game_pks: Optional[List[int]] = None) -> Dict:
        """Run predictions for specific games or all active games.
        
        Args:
            game_pks: Specific game PKs to predict (None for all active)
        """
        try:
            if not self.data_processor:
                return {'error': 'Data processor not initialized'}
            
            # Get games to predict
            if game_pks:
                games_to_predict = game_pks
            else:
                # Get all active games from processor
                games_to_predict = list(self.data_processor.game_states.keys())
            
            results = {}
            for game_pk in games_to_predict:
                try:
                    # Get current game state
                    game_states = self.data_processor.game_states.get(game_pk, [])
                    if not game_states:
                        results[game_pk] = {'error': 'No game state available'}
                        continue
                    
                    current_state = game_states[-1]
                    
                    # Generate prediction
                    await self.data_processor._generate_predictions(current_state)
                    results[game_pk] = {'success': True, 'predicted_at': datetime.now()}
                    
                except Exception as e:
                    results[game_pk] = {'error': str(e)}
                    self.stats['prediction_failures'] += 1
            
            return {
                'success': True,
                'results': results,
                'total_games': len(games_to_predict),
                'successful_predictions': sum(1 for r in results.values() if r.get('success')),
            }
            
        except Exception as e:
            logger.error(f'Error running live predictions: {e}')
            return {'error': str(e)}
    
    async def shutdown(self) -> None:
        """Shutdown the pipeline gracefully."""
        if not self.is_running:
            logger.warning('Pipeline is not running')
            return
        
        logger.info('Shutting down enhanced live pipeline')
        
        self.is_running = False
        
        try:
            # Stop all feeds
            if self.live_service:
                await self.live_service.stop_all()
            
            # Shutdown data processor
            if self.data_processor:
                await self.data_processor.shutdown()
            
            # Clear active feeds
            self.active_feeds.clear()
            
            logger.info('Enhanced live pipeline shutdown complete')
            
        except Exception as e:
            logger.error(f'Error during shutdown: {e}')
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.is_running:
            # Note: In real usage, this would need to be awaited
            logger.warning('Pipeline shutdown in context manager - use async with')
