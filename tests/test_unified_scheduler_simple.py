"""Simple tests for Unified Live Game Scheduler.

Basic tests to verify core functionality without complex imports.

Author: Agent Cascade
Date: 2026-05-05
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

# Test the core classes directly without importing the full module
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import only what we need for basic testing
from baseball.ingestion.scheduler_config import (
    UnifiedSchedulerConfig,
    ConfigManager,
    PollingConfig,
    PipelineConfig,
    ErrorHandlingConfig,
    DatabaseConfig,
    MonitoringConfig,
)


class TestSchedulerConfig:
    """Test cases for scheduler configuration."""
    
    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = UnifiedSchedulerConfig()
        
        assert config.polling.during_game == 10
        assert config.polling.pre_game == 60
        assert config.polling.game_day == 300
        assert config.polling.off_hours == 3600
        assert config.pipeline.buffer_size == 1000
        assert config.pipeline.prediction_interval == 30
        assert config.pipeline.feature_calc_interval == 15
        assert config.pipeline.monitoring_interval == 60
        assert config.error_handling.max_retries == 3
        assert config.error_handling.circuit_breaker_threshold == 5
        assert config.database.connection_timeout == 30
        assert config.database.max_connections == 10
        assert config.monitoring.enable_metrics is True
        assert config.monitoring.metrics_interval == 60
    
    def test_config_validation(self) -> None:
        """Test configuration validation."""
        config = UnifiedSchedulerConfig()
        
        # Valid config should pass
        errors = config.validate()
        assert len(errors) == 0
        
        # Invalid polling config should fail
        config.polling.during_game = 0  # Invalid
        errors = config.validate()
        assert len(errors) > 0
        assert any("during_game must be at least 1 second" in error for error in errors)
        
        # Reset and test invalid pipeline config
        config = UnifiedSchedulerConfig()
        config.pipeline.buffer_size = 0  # Invalid
        errors = config.validate()
        assert len(errors) > 0
        assert any("buffer_size must be at least 1" in error for error in errors)
        
        # Reset and test invalid error handling config
        config = UnifiedSchedulerConfig()
        config.error_handling.max_retries = -1  # Invalid
        errors = config.validate()
        assert len(errors) > 0
        assert any("max_retries must be non-negative" in error for error in errors)
    
    def test_config_to_dict(self) -> None:
        """Test configuration serialization."""
        config = UnifiedSchedulerConfig()
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert 'polling' in config_dict
        assert 'pipeline' in config_dict
        assert 'error_handling' in config_dict
        assert 'database' in config_dict
        assert 'monitoring' in config_dict
        assert 'scheduler_name' in config_dict
        assert 'environment' in config_dict
        
        # Check nested config structure
        polling = config_dict['polling']
        assert 'during_game' in polling
        assert 'pre_game' in polling
        assert 'game_day' in polling
        assert 'off_hours' in polling
    
    def test_config_from_dict(self) -> None:
        """Test configuration deserialization."""
        config_dict = {
            'polling': {
                'during_game': 5,
                'pre_game': 30,
                'game_day': 150,
                'off_hours': 1800,
                'pre_game_minutes': 60,
                'post_game_minutes': 30,
                'enable_adaptive': True,
                'min_interval': 1,
                'max_interval': 3600,
            },
            'pipeline': {
                'buffer_size': 500,
                'max_buffer_size': 5000,
                'prediction_interval': 15,
                'feature_calc_interval': 10,
                'monitoring_interval': 30,
                'default_processing_level': 'full',
                'enable_parallel_processing': True,
                'max_workers': 2,
                'data_retention_hours': 12,
                'metrics_retention_days': 15,
            },
            'error_handling': {
                'max_retries': 2,
                'retry_delay': 3,
                'retry_backoff_factor': 1.5,
                'circuit_breaker_threshold': 3,
                'circuit_breaker_timeout': 150,
                'circuit_breaker_recovery_timeout': 30,
                'log_all_errors': True,
                'log_error_context': True,
                'max_error_history': 500,
                'enable_alerts': True,
                'alert_thresholds': {'failure_rate': 0.05},
            },
            'database': {
                'connection_timeout': 15,
                'max_connections': 5,
                'connection_retry_attempts': 2,
                'enable_job_persistence': True,
                'job_history_retention_days': 15,
                'enable_metrics_storage': True,
                'metrics_aggregation_interval': 150,
                'auto_create_tables': True,
                'validate_schema': True,
            },
            'monitoring': {
                'enable_metrics': True,
                'metrics_interval': 30,
                'enable_performance_metrics': True,
                'enable_business_metrics': True,
                'enable_health_checks': True,
                'health_check_interval': 15,
                'health_check_timeout': 5,
                'enable_alerting': True,
                'alert_webhook_url': None,
                'alert_email_recipients': [],
                'enable_dashboard': True,
                'dashboard_port': 8080,
                'dashboard_refresh_interval': 3,
            },
            'scheduler_name': 'test_scheduler',
            'environment': 'development',
            'debug': True,
            'log_level': 'DEBUG',
            'max_concurrent_operations': 3,
            'coordination_timeout': 15,
            'enable_coordination': True,
            'default_feed_timeout': 15,
            'default_feed_retry_attempts': 2,
            'default_feed_retry_delay': 3,
        }
        
        config = UnifiedSchedulerConfig.from_dict(config_dict)
        
        assert config.polling.during_game == 5
        assert config.polling.pre_game == 30
        assert config.pipeline.buffer_size == 500
        assert config.pipeline.prediction_interval == 15
        assert config.error_handling.max_retries == 2
        assert config.database.connection_timeout == 15
        assert config.monitoring.metrics_interval == 30
        assert config.scheduler_name == 'test_scheduler'
        assert config.environment == 'development'
        assert config.debug is True
        assert config.log_level == 'DEBUG'
    
    def test_polling_config_validation(self) -> None:
        """Test polling configuration validation."""
        config = PollingConfig()
        
        # Valid config should pass
        errors = config.validate()
        assert len(errors) == 0
        
        # Test invalid values
        config.during_game = 0
        config.pre_game = 5
        config.game_day = 10
        config.off_hours = 20
        config.min_interval = 0
        config.max_interval = 0
        
        errors = config.validate()
        assert len(errors) == 6  # All 6 values should be invalid
    
    def test_pipeline_config_validation(self) -> None:
        """Test pipeline configuration validation."""
        config = PipelineConfig()
        
        # Valid config should pass
        errors = config.validate()
        assert len(errors) == 0
        
        # Test invalid values
        config.buffer_size = 0
        config.max_buffer_size = 100  # Less than buffer_size
        config.prediction_interval = 0
        config.feature_calc_interval = 0
        config.monitoring_interval = 0
        config.default_processing_level = 'invalid'
        config.max_workers = 0
        
        errors = config.validate()
        assert len(errors) == 7  # All 7 values should be invalid
    
    def test_error_handling_config_validation(self) -> None:
        """Test error handling configuration validation."""
        config = ErrorHandlingConfig()
        
        # Valid config should pass
        errors = config.validate()
        assert len(errors) == 0
        
        # Test invalid values
        config.max_retries = -1
        config.retry_delay = -1
        config.retry_backoff_factor = 0.5
        config.circuit_breaker_threshold = 0
        config.circuit_breaker_timeout = 0
        config.circuit_breaker_recovery_timeout = 0
        config.max_error_history = -1
        
        errors = config.validate()
        assert len(errors) == 7  # All 7 values should be invalid
    
    def test_database_config_validation(self) -> None:
        """Test database configuration validation."""
        config = DatabaseConfig()
        
        # Valid config should pass
        errors = config.validate()
        assert len(errors) == 0
        
        # Test invalid values
        config.connection_timeout = 0
        config.max_connections = 0
        config.connection_retry_attempts = -1
        config.job_history_retention_days = 0
        config.metrics_aggregation_interval = 0
        
        errors = config.validate()
        assert len(errors) == 5  # All 5 values should be invalid
    
    def test_monitoring_config_validation(self) -> None:
        """Test monitoring configuration validation."""
        config = MonitoringConfig()
        
        # Valid config should pass
        errors = config.validate()
        assert len(errors) == 0
        
        # Test invalid values
        config.metrics_interval = 0
        config.health_check_interval = 0
        config.health_check_timeout = 0
        config.dashboard_port = 80  # Below 1024
        config.dashboard_refresh_interval = 0
        
        errors = config.validate()
        assert len(errors) == 5  # All 5 values should be invalid


class TestConfigManager:
    """Test cases for configuration management."""
    
    def test_config_manager_initialization(self) -> None:
        """Test config manager initialization."""
        import tempfile
        import json
        
        # Test with default path
        manager = ConfigManager()
        assert manager.config_path.name == 'scheduler_config.json'
        
        # Test with custom path
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            custom_manager = ConfigManager(tmp.name)
            assert custom_manager.config_path == tmp.name
    
    def test_default_config_creation(self) -> None:
        """Test default configuration creation."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            manager = ConfigManager(tmp.name)
            
            # Load config (should create default)
            config = manager.load_config()
            
            assert isinstance(config, UnifiedSchedulerConfig)
            assert config.polling.during_game == 10
            assert config.pipeline.buffer_size == 1000
            assert config.scheduler_name == 'unified_live_scheduler'
            assert config.environment == 'production'
            
            # Verify file was created
            assert tmp.name and manager.config_path.exists()
    
    def test_config_save_load_cycle(self) -> None:
        """Test saving and loading configuration."""
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            manager = ConfigManager(tmp.name)
            
            # Create custom config
            config = UnifiedSchedulerConfig()
            config.scheduler_name = 'test_scheduler'
            config.polling.during_game = 5
            config.pipeline.buffer_size = 500
            
            # Save config
            manager.save_config(config)
            
            # Load and verify
            loaded_config = manager.load_config()
            assert loaded_config.scheduler_name == 'test_scheduler'
            assert loaded_config.polling.during_game == 5
            assert loaded_config.pipeline.buffer_size == 500
    
    def test_config_update(self) -> None:
        """Test configuration updates."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            manager = ConfigManager(tmp.name)
            
            # Load default config
            config = manager.load_config()
            original_name = config.scheduler_name
            
            # Update config
            updates = {
                'scheduler_name': 'updated_scheduler',
                'polling': {
                    'during_game': 15,
                },
                'pipeline': {
                    'buffer_size': 2000,
                },
            }
            
            manager.update_config(updates)
            
            # Verify updates
            updated_config = manager.get_config()
            assert updated_config.scheduler_name == 'updated_scheduler'
            assert updated_config.polling.during_game == 15
            assert updated_config.pipeline.buffer_size == 2000
            
            # Verify other values unchanged
            assert updated_config.polling.pre_game == config.polling.pre_game
    
    def test_config_export_import(self) -> None:
        """Test configuration export and import."""
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_source, \
             tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp_export:
            
            source_manager = ConfigManager(tmp_source.name)
            export_manager = ConfigManager(tmp_export.name)
            
            # Create custom config
            config = UnifiedSchedulerConfig()
            config.scheduler_name = 'export_test_scheduler'
            config.polling.during_game = 7
            config.pipeline.buffer_size = 750
            
            # Save to source
            source_manager.save_config(config)
            
            # Export from source
            source_manager.export_config(tmp_export.name)
            
            # Import to export manager
            export_manager.import_config(tmp_export.name)
            
            # Verify imported config
            imported_config = export_manager.get_config()
            assert imported_config.scheduler_name == 'export_test_scheduler'
            assert imported_config.polling.during_game == 7
            assert imported_config.pipeline.buffer_size == 750


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
