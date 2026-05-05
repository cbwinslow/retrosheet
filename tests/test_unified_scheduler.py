"""Tests for Unified Live Game Scheduler.

Integration tests to verify the unified scheduler combines
SmartScheduler and EnhancedLivePipeline correctly.

Author: Agent Cascade
Date: 2026-05-05
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from baseball.ingestion.unified_scheduler import (
    UnifiedLiveGameScheduler,
    SchedulerConfig,
    FeedConfig,
    SchedulerStatus,
    SchedulerCoordination,
)
from baseball.ingestion.scheduler_config import (
    UnifiedSchedulerConfig,
    ConfigManager,
)


class TestUnifiedScheduler:
    """Test cases for UnifiedLiveGameScheduler."""
    
    @pytest.fixture
    def scheduler_config(self) -> SchedulerConfig:
        """Create test scheduler configuration."""
        return SchedulerConfig(
            during_game=5,
            pre_game=30,
            game_day=150,
            off_hours=1800,
            buffer_size=500,
            prediction_interval=15,
            feature_calc_interval=10,
            monitoring_interval=30,
            max_retries=2,
            circuit_breaker_threshold=3,
        )
    
    @pytest.fixture
    def unified_scheduler(self, scheduler_config: SchedulerConfig) -> UnifiedLiveGameScheduler:
        """Create unified scheduler for testing."""
        return UnifiedLiveGameScheduler(scheduler_config)
    
    def test_scheduler_initialization(self, scheduler_config: SchedulerConfig) -> None:
        """Test scheduler initialization."""
        scheduler = UnifiedLiveGameScheduler(scheduler_config)
        
        assert scheduler.config == scheduler_config
        assert scheduler._status == SchedulerStatus.STOPPED
        assert scheduler._start_time is None
        assert scheduler._last_error is None
        assert scheduler._total_polls == 0
        assert scheduler._successful_polls == 0
        assert scheduler._failed_polls == 0
        assert len(scheduler._feeds) == 0
        assert len(scheduler._active_feeds) == 0
    
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, unified_scheduler: UnifiedLiveGameScheduler) -> None:
        """Test scheduler start and stop lifecycle."""
        # Mock the components to avoid actual network calls
        with patch.object(unified_scheduler.smart_scheduler, 'start', new_callable=AsyncMock), \
             patch.object(unified_scheduler.enhanced_pipeline, 'start', new_callable=AsyncMock), \
             patch.object(unified_scheduler.database_scheduler, 'start', new_callable=AsyncMock), \
             patch.object(unified_scheduler.error_handler, 'start', new_callable=AsyncMock):
            
            # Test start
            await unified_scheduler.start()
            
            assert unified_scheduler._status == SchedulerStatus.RUNNING
            assert unified_scheduler._start_time is not None
            
            # Test stop
            with patch.object(unified_scheduler.smart_scheduler, 'stop', new_callable=AsyncMock), \
                 patch.object(unified_scheduler.enhanced_pipeline, 'stop', new_callable=AsyncMock), \
                 patch.object(unified_scheduler.database_scheduler, 'stop', new_callable=AsyncMock), \
                 patch.object(unified_scheduler.error_handler, 'stop', new_callable=AsyncMock):
                
                await unified_scheduler.stop()
                
                assert unified_scheduler._status == SchedulerStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_add_feed(self, unified_scheduler: UnifiedLiveGameScheduler) -> None:
        """Test adding a feed to the scheduler."""
        # Start scheduler first
        with patch.object(unified_scheduler.smart_scheduler, 'start', new_callable=AsyncMock), \
             patch.object(unified_scheduler.enhanced_pipeline, 'start', new_callable=AsyncMock), \
             patch.object(unified_scheduler.enhanced_pipeline, 'add_feed', new_callable=AsyncMock), \
             patch.object(unified_scheduler.enhanced_pipeline, 'start_feed', new_callable=AsyncMock):
            
            await unified_scheduler.start()
            
            # Create test feed
            feed_config = FeedConfig(
                name="test_feed",
                url="wss://test.example.com/live",
                feed_type="test",
                enabled=True,
                priority=5,
            )
            
            # Add feed
            await unified_scheduler.add_feed(feed_config)
            
            # Verify feed was added
            assert "test_feed" in unified_scheduler._feeds
            assert unified_scheduler._feeds["test_feed"] == feed_config
            assert "test_feed" in unified_scheduler._active_feeds
    
    @pytest.mark.asyncio
    async def test_remove_feed(self, unified_scheduler: UnifiedLiveGameScheduler) -> None:
        """Test removing a feed from the scheduler."""
        # Start scheduler first
        with patch.object(unified_scheduler.smart_scheduler, 'start', new_callable=AsyncMock), \
             patch.object(unified_scheduler.enhanced_pipeline, 'start', new_callable=AsyncMock), \
             patch.object(unified_scheduler.enhanced_pipeline, 'add_feed', new_callable=AsyncMock), \
             patch.object(unified_scheduler.enhanced_pipeline, 'start_feed', new_callable=AsyncMock), \
             patch.object(unified_scheduler.enhanced_pipeline, 'stop_feed', new_callable=AsyncMock), \
             patch.object(unified_scheduler.enhanced_pipeline, 'remove_feed', new_callable=AsyncMock):
            
            await unified_scheduler.start()
            
            # Add feed first
            feed_config = FeedConfig(
                name="test_feed",
                url="wss://test.example.com/live",
                feed_type="test",
                enabled=True,
                priority=5,
            )
            
            await unified_scheduler.add_feed(feed_config)
            assert "test_feed" in unified_scheduler._feeds
            
            # Remove feed
            await unified_scheduler.remove_feed("test_feed")
            
            # Verify feed was removed
            assert "test_feed" not in unified_scheduler._feeds
            assert "test_feed" not in unified_scheduler._active_feeds
    
    def test_get_status(self, unified_scheduler: UnifiedLiveGameScheduler) -> None:
        """Test getting scheduler status."""
        status = unified_scheduler.get_status()
        
        assert status.status == SchedulerStatus.STOPPED
        assert status.uptime_seconds == 0.0
        assert status.start_time is None
        assert status.last_error is None
        assert status.total_polls == 0
        assert status.successful_polls == 0
        assert status.failed_polls == 0
        assert status.average_poll_time == 0.0
        assert len(status.active_feeds) == 0
        assert status.total_feeds == 0
    
    @pytest.mark.asyncio
    async def test_run_predictions(self, unified_scheduler: UnifiedLiveGameScheduler) -> None:
        """Test running predictions through the scheduler."""
        # Start scheduler first
        with patch.object(unified_scheduler.smart_scheduler, 'start', new_callable=AsyncMock), \
             patch.object(unified_scheduler.enhanced_pipeline, 'start', new_callable=AsyncMock), \
             patch.object(unified_scheduler.enhanced_pipeline, 'run_live_predictions', new_callable=AsyncMock) as mock_predict:
            
            await unified_scheduler.start()
            
            # Mock prediction results
            mock_predict.return_value = {
                'games': [12345, 12346],
                'predictions': {
                    12345: {'home_win_prob': 0.6, 'away_win_prob': 0.4},
                    12346: {'home_win_prob': 0.45, 'away_win_prob': 0.55},
                },
                'timestamp': datetime.now().isoformat(),
            }
            
            # Run predictions
            results = await unified_scheduler.run_predictions([12345, 12346])
            
            # Verify predictions were called
            mock_predict.assert_called_once_with([12345, 12346])
            assert 'games' in results
            assert 'predictions' in results
    
    def test_add_duplicate_feed(self, unified_scheduler: UnifiedLiveGameScheduler) -> None:
        """Test adding a duplicate feed raises an error."""
        feed_config = FeedConfig(
            name="test_feed",
            url="wss://test.example.com/live",
            feed_type="test",
        )
        
        # Add feed to internal dict directly (simulating previous addition)
        unified_scheduler._feeds["test_feed"] = feed_config
        
        # Attempting to add again should raise ValueError
        with pytest.raises(ValueError, match="Feed test_feed already exists"):
            asyncio.run(unified_scheduler.add_feed(feed_config))
    
    def test_remove_nonexistent_feed(self, unified_scheduler: UnifiedLiveGameScheduler) -> None:
        """Test removing a non-existent feed raises an error."""
        with pytest.raises(ValueError, match="Feed nonexistent_feed not found"):
            asyncio.run(unified_scheduler.remove_feed("nonexistent_feed"))
    
    @pytest.mark.asyncio
    async def test_run_predictions_not_running(self, unified_scheduler: UnifiedLiveGameScheduler) -> None:
        """Test running predictions when scheduler is not running."""
        with pytest.raises(RuntimeError, match="Cannot run predictions in stopped state"):
            await unified_scheduler.run_predictions()
    
    @pytest.mark.asyncio
    async def test_add_feed_not_running(self, unified_scheduler: UnifiedLiveGameScheduler) -> None:
        """Test adding a feed when scheduler is not running."""
        feed_config = FeedConfig(
            name="test_feed",
            url="wss://test.example.com/live",
            feed_type="test",
        )
        
        with pytest.raises(RuntimeError, match="Cannot add feed to scheduler in stopped state"):
            await unified_scheduler.add_feed(feed_config)


class TestSchedulerCoordination:
    """Test cases for SchedulerCoordination."""
    
    @pytest.fixture
    def coordination(self) -> SchedulerCoordination:
        """Create coordination layer for testing."""
        config = SchedulerConfig()
        return SchedulerCoordination(config)
    
    def test_coordination_initialization(self, coordination: SchedulerCoordination) -> None:
        """Test coordination initialization."""
        assert coordination.config == config
        assert len(coordination._component_status) == 0
        assert len(coordination._active_operations) == 0
    
    @pytest.mark.asyncio
    async def test_register_component(self, coordination: SchedulerCoordination) -> None:
        """Test component registration."""
        mock_component = Mock()
        
        await coordination.register_component("test_component", mock_component)
        
        assert "test_component" in coordination._component_status
        status = coordination._component_status["test_component"]
        assert status["component"] == mock_component
        assert status["status"] == "registered"
        assert status["error_count"] == 0
    
    @pytest.mark.asyncio
    async def test_update_component_status(self, coordination: SchedulerCoordination) -> None:
        """Test updating component status."""
        # Register component first
        mock_component = Mock()
        await coordination.register_component("test_component", mock_component)
        
        # Update status
        await coordination.update_component_status("test_component", {
            "status": "running",
            "last_update": 1234567890,
        })
        
        status = await coordination.get_component_status("test_component")
        assert status["status"] == "running"
        assert status["last_update"] == 1234567890
    
    @pytest.mark.asyncio
    async def test_coordinate_operation(self, coordination: SchedulerCoordination) -> None:
        """Test coordinating an operation."""
        mock_operation = AsyncMock(return_value="success")
        
        result = await coordination.coordinate_operation(
            "test_operation",
            mock_operation,
            "arg1",
            kwarg1="value1"
        )
        
        assert result == "success"
        assert "test_operation" not in coordination._active_operations
    
    @pytest.mark.asyncio
    async def test_coordinate_operation_timeout(self, coordination: SchedulerCoordination) -> None:
        """Test operation timeout handling."""
        # Create a slow operation
        async def slow_operation():
            await asyncio.sleep(10)  # Longer than timeout
            return "success"
        
        # Set short timeout
        coordination.config.coordination_timeout = 1
        
        with pytest.raises(asyncio.TimeoutError):
            await coordination.coordinate_operation("slow_operation", slow_operation)


class TestSchedulerConfig:
    """Test cases for scheduler configuration."""
    
    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = SchedulerConfig()
        
        assert config.during_game == 10
        assert config.pre_game == 60
        assert config.game_day == 300
        assert config.off_hours == 3600
        assert config.buffer_size == 1000
        assert config.prediction_interval == 30
        assert config.feature_calc_interval == 15
        assert config.monitoring_interval == 60
        assert config.max_retries == 3
        assert config.circuit_breaker_threshold == 5
    
    def test_feed_config_validation(self) -> None:
        """Test feed configuration."""
        feed = FeedConfig(
            name="test_feed",
            url="wss://test.example.com",
            feed_type="test",
            enabled=True,
            priority=5,
        )
        
        assert feed.name == "test_feed"
        assert feed.url == "wss://test.example.com"
        assert feed.feed_type == "test"
        assert feed.enabled is True
        assert feed.priority == 5


class TestConfigManager:
    """Test cases for configuration management."""
    
    @pytest.mark.asyncio
    async def test_config_manager_default_path(self) -> None:
        """Test config manager with default path."""
        manager = ConfigManager()
        
        # Should create default config if file doesn't exist
        config = manager.load_config()
        
        assert isinstance(config, UnifiedSchedulerConfig)
        assert config.polling.during_game == 10
        assert config.pipeline.buffer_size == 1000
    
    def test_config_validation(self) -> None:
        """Test configuration validation."""
        config = UnifiedSchedulerConfig()
        
        # Valid config should pass
        errors = config.validate()
        assert len(errors) == 0
        
        # Invalid config should fail
        config.polling.during_game = 0  # Invalid
        errors = config.validate()
        assert len(errors) > 0
        assert any("during_game must be at least 1 second" in error for error in errors)


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
