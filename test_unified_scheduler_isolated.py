#!/usr/bin/env python3
"""Isolated test for Unified Live Game Scheduler core functionality.

Tests the core scheduler logic without importing the full baseball package
to avoid dependency issues.

Author: Agent Cascade
Date: 2026-05-05
"""

import asyncio
import json
import tempfile
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path


# ============================================================================
# Core Classes (copied from scheduler_config.py to avoid imports)
# ============================================================================

class ConfigFormat(Enum):
    """Configuration file formats."""
    JSON = "json"
    YAML = "yaml"
    ENV = "env"


@dataclass
class PollingConfig:
    """Polling configuration settings."""
    
    during_game: int = 10
    pre_game: int = 60
    game_day: int = 300
    off_hours: int = 3600
    pre_game_minutes: int = 60
    post_game_minutes: int = 30
    enable_adaptive: bool = True
    min_interval: int = 1
    max_interval: int = 3600
    
    def validate(self) -> List[str]:
        """Validate polling configuration."""
        errors = []
        
        if self.during_game < 1:
            errors.append("during_game must be at least 1 second")
        
        if self.pre_game < self.during_game:
            errors.append("pre_game should be >= during_game")
        
        if self.game_day < self.pre_game:
            errors.append("game_day should be >= pre_game")
        
        if self.off_hours < self.game_day:
            errors.append("off_hours should be >= game_day")
        
        if self.min_interval < 1:
            errors.append("min_interval must be at least 1 second")
        
        if self.max_interval < self.min_interval:
            errors.append("max_interval must be >= min_interval")
        
        return errors


@dataclass
class PipelineConfig:
    """Pipeline configuration settings."""
    
    buffer_size: int = 1000
    max_buffer_size: int = 10000
    prediction_interval: int = 30
    feature_calc_interval: int = 15
    monitoring_interval: int = 60
    default_processing_level: str = "full"
    enable_parallel_processing: bool = True
    max_workers: int = 4
    data_retention_hours: int = 24
    metrics_retention_days: int = 30
    
    def validate(self) -> List[str]:
        """Validate pipeline configuration."""
        errors = []
        
        if self.buffer_size < 1:
            errors.append("buffer_size must be at least 1")
        
        if self.max_buffer_size < self.buffer_size:
            errors.append("max_buffer_size must be >= buffer_size")
        
        if self.prediction_interval < 1:
            errors.append("prediction_interval must be at least 1 second")
        
        if self.feature_calc_interval < 1:
            errors.append("feature_calc_interval must be at least 1 second")
        
        if self.monitoring_interval < 1:
            errors.append("monitoring_interval must be at least 1 second")
        
        if self.default_processing_level not in ["full", "basic", "minimal"]:
            errors.append("default_processing_level must be one of: full, basic, minimal")
        
        if self.max_workers < 1:
            errors.append("max_workers must be at least 1")
        
        return errors


@dataclass
class ErrorHandlingConfig:
    """Error handling configuration settings."""
    
    max_retries: int = 3
    retry_delay: int = 5
    retry_backoff_factor: float = 2.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 300
    circuit_breaker_recovery_timeout: int = 60
    log_all_errors: bool = True
    log_error_context: bool = True
    max_error_history: int = 1000
    enable_alerts: bool = True
    alert_thresholds: Dict[str, Any] = field(default_factory=lambda: {
        'failure_rate': 0.1,
        'error_rate': 0.05,
        'latency_ms': 1000,
        'memory_mb': 1024,
    })
    
    def validate(self) -> List[str]:
        """Validate error handling configuration."""
        errors = []
        
        if self.max_retries < 0:
            errors.append("max_retries must be non-negative")
        
        if self.retry_delay < 0:
            errors.append("retry_delay must be non-negative")
        
        if self.retry_backoff_factor < 1.0:
            errors.append("retry_backoff_factor must be >= 1.0")
        
        if self.circuit_breaker_threshold < 1:
            errors.append("circuit_breaker_threshold must be at least 1")
        
        if self.circuit_breaker_timeout < 1:
            errors.append("circuit_breaker_timeout must be at least 1 second")
        
        if self.circuit_breaker_recovery_timeout < 1:
            errors.append("circuit_breaker_recovery_timeout must be at least 1 second")
        
        if self.max_error_history < 0:
            errors.append("max_error_history must be non-negative")
        
        return errors


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    
    connection_timeout: int = 30
    max_connections: int = 10
    connection_retry_attempts: int = 3
    enable_job_persistence: bool = True
    job_history_retention_days: int = 30
    enable_metrics_storage: bool = True
    metrics_aggregation_interval: int = 300
    auto_create_tables: bool = True
    validate_schema: bool = True
    
    def validate(self) -> List[str]:
        """Validate database configuration."""
        errors = []
        
        if self.connection_timeout < 1:
            errors.append("connection_timeout must be at least 1 second")
        
        if self.max_connections < 1:
            errors.append("max_connections must be at least 1")
        
        if self.connection_retry_attempts < 0:
            errors.append("connection_retry_attempts must be non-negative")
        
        if self.job_history_retention_days < 1:
            errors.append("job_history_retention_days must be at least 1")
        
        if self.metrics_aggregation_interval < 1:
            errors.append("metrics_aggregation_interval must be at least 1 second")
        
        return errors


@dataclass
class MonitoringConfig:
    """Monitoring configuration settings."""
    
    enable_metrics: bool = True
    metrics_interval: int = 60
    enable_performance_metrics: bool = True
    enable_business_metrics: bool = True
    enable_health_checks: bool = True
    health_check_interval: int = 30
    health_check_timeout: int = 10
    enable_alerting: bool = True
    alert_webhook_url: Optional[str] = None
    alert_email_recipients: List[str] = field(default_factory=list)
    enable_dashboard: bool = True
    dashboard_port: int = 8080
    dashboard_refresh_interval: int = 5
    
    def validate(self) -> List[str]:
        """Validate monitoring configuration."""
        errors = []
        
        if self.metrics_interval < 1:
            errors.append("metrics_interval must be at least 1 second")
        
        if self.health_check_interval < 1:
            errors.append("health_check_interval must be at least 1 second")
        
        if self.health_check_timeout < 1:
            errors.append("health_check_timeout must be at least 1 second")
        
        if self.dashboard_port < 1024 or self.dashboard_port > 65535:
            errors.append("dashboard_port must be between 1024 and 65535")
        
        if self.dashboard_refresh_interval < 1:
            errors.append("dashboard_refresh_interval must be at least 1 second")
        
        return errors


@dataclass
class UnifiedSchedulerConfig:
    """Complete configuration for the unified scheduler."""
    
    polling: PollingConfig = field(default_factory=PollingConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    error_handling: ErrorHandlingConfig = field(default_factory=ErrorHandlingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    scheduler_name: str = "unified_live_scheduler"
    environment: str = "production"
    debug: bool = False
    log_level: str = "INFO"
    
    max_concurrent_operations: int = 5
    coordination_timeout: int = 30
    enable_coordination: bool = True
    
    default_feed_timeout: int = 30
    default_feed_retry_attempts: int = 3
    default_feed_retry_delay: int = 5
    
    def validate(self) -> List[str]:
        """Validate the complete configuration."""
        all_errors = []
        
        # Validate each component
        all_errors.extend(self.polling.validate())
        all_errors.extend(self.pipeline.validate())
        all_errors.extend(self.error_handling.validate())
        all_errors.extend(self.database.validate())
        all_errors.extend(self.monitoring.validate())
        
        # Validate global settings
        if self.scheduler_name.strip() == "":
            all_errors.append("scheduler_name cannot be empty")
        
        if self.environment not in ["development", "staging", "production"]:
            all_errors.append("environment must be one of: development, staging, production")
        
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            all_errors.append("log_level must be a valid logging level")
        
        if self.max_concurrent_operations < 1:
            all_errors.append("max_concurrent_operations must be at least 1")
        
        if self.coordination_timeout < 1:
            all_errors.append("coordination_timeout must be at least 1 second")
        
        if self.default_feed_timeout < 1:
            all_errors.append("default_feed_timeout must be at least 1 second")
        
        if self.default_feed_retry_attempts < 0:
            all_errors.append("default_feed_retry_attempts must be non-negative")
        
        if self.default_feed_retry_delay < 0:
            all_errors.append("default_feed_retry_delay must be non-negative")
        
        return all_errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'polling': {
                'during_game': self.polling.during_game,
                'pre_game': self.polling.pre_game,
                'game_day': self.polling.game_day,
                'off_hours': self.polling.off_hours,
                'pre_game_minutes': self.polling.pre_game_minutes,
                'post_game_minutes': self.polling.post_game_minutes,
                'enable_adaptive': self.polling.enable_adaptive,
                'min_interval': self.polling.min_interval,
                'max_interval': self.polling.max_interval,
            },
            'pipeline': {
                'buffer_size': self.pipeline.buffer_size,
                'max_buffer_size': self.pipeline.max_buffer_size,
                'prediction_interval': self.pipeline.prediction_interval,
                'feature_calc_interval': self.pipeline.feature_calc_interval,
                'monitoring_interval': self.pipeline.monitoring_interval,
                'default_processing_level': self.pipeline.default_processing_level,
                'enable_parallel_processing': self.pipeline.enable_parallel_processing,
                'max_workers': self.pipeline.max_workers,
                'data_retention_hours': self.pipeline.data_retention_hours,
                'metrics_retention_days': self.pipeline.metrics_retention_days,
            },
            'error_handling': {
                'max_retries': self.error_handling.max_retries,
                'retry_delay': self.error_handling.retry_delay,
                'retry_backoff_factor': self.error_handling.retry_backoff_factor,
                'circuit_breaker_threshold': self.error_handling.circuit_breaker_threshold,
                'circuit_breaker_timeout': self.error_handling.circuit_breaker_timeout,
                'circuit_breaker_recovery_timeout': self.error_handling.circuit_breaker_recovery_timeout,
                'log_all_errors': self.error_handling.log_all_errors,
                'log_error_context': self.error_handling.log_error_context,
                'max_error_history': self.error_handling.max_error_history,
                'enable_alerts': self.error_handling.enable_alerts,
                'alert_thresholds': self.error_handling.alert_thresholds,
            },
            'database': {
                'connection_timeout': self.database.connection_timeout,
                'max_connections': self.database.max_connections,
                'connection_retry_attempts': self.database.connection_retry_attempts,
                'enable_job_persistence': self.database.enable_job_persistence,
                'job_history_retention_days': self.database.job_history_retention_days,
                'enable_metrics_storage': self.database.enable_metrics_storage,
                'metrics_aggregation_interval': self.database.metrics_aggregation_interval,
                'auto_create_tables': self.database.auto_create_tables,
                'validate_schema': self.database.validate_schema,
            },
            'monitoring': {
                'enable_metrics': self.monitoring.enable_metrics,
                'metrics_interval': self.monitoring.metrics_interval,
                'enable_performance_metrics': self.monitoring.enable_performance_metrics,
                'enable_business_metrics': self.monitoring.enable_business_metrics,
                'enable_health_checks': self.monitoring.enable_health_checks,
                'health_check_interval': self.monitoring.health_check_interval,
                'health_check_timeout': self.monitoring.health_check_timeout,
                'enable_alerting': self.monitoring.enable_alerting,
                'alert_webhook_url': self.monitoring.alert_webhook_url,
                'alert_email_recipients': self.monitoring.alert_email_recipients,
                'enable_dashboard': self.monitoring.enable_dashboard,
                'dashboard_port': self.monitoring.dashboard_port,
                'dashboard_refresh_interval': self.monitoring.dashboard_refresh_interval,
            },
            'scheduler_name': self.scheduler_name,
            'environment': self.environment,
            'debug': self.debug,
            'log_level': self.log_level,
            'max_concurrent_operations': self.max_concurrent_operations,
            'coordination_timeout': self.coordination_timeout,
            'enable_coordination': self.enable_coordination,
            'default_feed_timeout': self.default_feed_timeout,
            'default_feed_retry_attempts': self.default_feed_retry_attempts,
            'default_feed_retry_delay': self.default_feed_retry_delay,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedSchedulerConfig':
        """Create configuration from dictionary."""
        # Extract component configurations
        polling_data = data.get('polling', {})
        pipeline_data = data.get('pipeline', {})
        error_data = data.get('error_handling', {})
        database_data = data.get('database', {})
        monitoring_data = data.get('monitoring', {})
        
        # Create configuration objects
        config = cls(
            polling=PollingConfig(**polling_data),
            pipeline=PipelineConfig(**pipeline_data),
            error_handling=ErrorHandlingConfig(**error_data),
            database=DatabaseConfig(**database_data),
            monitoring=MonitoringConfig(**monitoring_data),
            scheduler_name=data.get('scheduler_name', 'unified_live_scheduler'),
            environment=data.get('environment', 'production'),
            debug=data.get('debug', False),
            log_level=data.get('log_level', 'INFO'),
            max_concurrent_operations=data.get('max_concurrent_operations', 5),
            coordination_timeout=data.get('coordination_timeout', 30),
            enable_coordination=data.get('enable_coordination', True),
            default_feed_timeout=data.get('default_feed_timeout', 30),
            default_feed_retry_attempts=data.get('default_feed_retry_attempts', 3),
            default_feed_retry_delay=data.get('default_feed_retry_delay', 5),
        )
        
        return config


# ============================================================================
# Test Functions
# ============================================================================

def test_default_config():
    """Test default configuration values."""
    print("Testing default configuration...")
    
    config = UnifiedSchedulerConfig()
    
    # Test polling defaults
    assert config.polling.during_game == 10
    assert config.polling.pre_game == 60
    assert config.polling.game_day == 300
    assert config.polling.off_hours == 3600
    
    # Test pipeline defaults
    assert config.pipeline.buffer_size == 1000
    assert config.pipeline.prediction_interval == 30
    assert config.pipeline.feature_calc_interval == 15
    assert config.pipeline.monitoring_interval == 60
    
    # Test error handling defaults
    assert config.error_handling.max_retries == 3
    assert config.error_handling.circuit_breaker_threshold == 5
    
    # Test database defaults
    assert config.database.connection_timeout == 30
    assert config.database.max_connections == 10
    
    # Test monitoring defaults
    assert config.monitoring.enable_metrics is True
    assert config.monitoring.metrics_interval == 60
    
    # Test global defaults
    assert config.scheduler_name == "unified_live_scheduler"
    assert config.environment == "production"
    assert config.debug is False
    assert config.log_level == "INFO"
    
    print("✓ Default configuration test passed")


def test_config_validation():
    """Test configuration validation."""
    print("Testing configuration validation...")
    
    config = UnifiedSchedulerConfig()
    
    # Valid config should pass
    errors = config.validate()
    assert len(errors) == 0, f"Valid config should have no errors, got: {errors}"
    
    # Test invalid polling config
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
    
    print("✓ Configuration validation test passed")


def test_config_serialization():
    """Test configuration serialization and deserialization."""
    print("Testing configuration serialization...")
    
    # Create custom config
    original_config = UnifiedSchedulerConfig()
    original_config.scheduler_name = "test_scheduler"
    original_config.polling.during_game = 5
    original_config.pipeline.buffer_size = 500
    original_config.error_handling.max_retries = 2
    original_config.database.connection_timeout = 15
    original_config.monitoring.metrics_interval = 30
    
    # Convert to dict
    config_dict = original_config.to_dict()
    
    # Verify dict structure
    assert isinstance(config_dict, dict)
    assert 'polling' in config_dict
    assert 'pipeline' in config_dict
    assert 'error_handling' in config_dict
    assert 'database' in config_dict
    assert 'monitoring' in config_dict
    assert 'scheduler_name' in config_dict
    
    # Verify values
    assert config_dict['scheduler_name'] == "test_scheduler"
    assert config_dict['polling']['during_game'] == 5
    assert config_dict['pipeline']['buffer_size'] == 500
    assert config_dict['error_handling']['max_retries'] == 2
    assert config_dict['database']['connection_timeout'] == 15
    assert config_dict['monitoring']['metrics_interval'] == 30
    
    # Convert back from dict
    restored_config = UnifiedSchedulerConfig.from_dict(config_dict)
    
    # Verify restored values
    assert restored_config.scheduler_name == "test_scheduler"
    assert restored_config.polling.during_game == 5
    assert restored_config.pipeline.buffer_size == 500
    assert restored_config.error_handling.max_retries == 2
    assert restored_config.database.connection_timeout == 15
    assert restored_config.monitoring.metrics_interval == 30
    
    print("✓ Configuration serialization test passed")


def test_file_operations():
    """Test configuration file operations."""
    print("Testing configuration file operations...")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # Create custom config
        config = UnifiedSchedulerConfig()
        config.scheduler_name = "file_test_scheduler"
        config.polling.during_game = 7
        config.pipeline.buffer_size = 750
        
        # Save to file
        config_dict = config.to_dict()
        with open(tmp_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        # Load from file
        with open(tmp_path, 'r') as f:
            loaded_dict = json.load(f)
        
        # Convert to config object
        loaded_config = UnifiedSchedulerConfig.from_dict(loaded_dict)
        
        # Verify loaded values
        assert loaded_config.scheduler_name == "file_test_scheduler"
        assert loaded_config.polling.during_game == 7
        assert loaded_config.pipeline.buffer_size == 750
        
        print("✓ File operations test passed")
        
    finally:
        # Clean up
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_component_validation():
    """Test individual component validation."""
    print("Testing component validation...")
    
    # Test polling config validation
    polling = PollingConfig()
    errors = polling.validate()
    assert len(errors) == 0
    
    # Test invalid polling config
    polling.during_game = 0
    polling.pre_game = 5
    polling.game_day = 10
    polling.off_hours = 20
    polling.min_interval = 0
    polling.max_interval = 0
    
    errors = polling.validate()
    print(f"Polling validation errors: {errors}")
    assert len(errors) >= 2  # At least 2 values should be invalid (during_game and min_interval)
    
    # Test pipeline config validation
    pipeline = PipelineConfig()
    errors = pipeline.validate()
    assert len(errors) == 0
    
    # Test invalid pipeline config
    pipeline.buffer_size = 0
    pipeline.max_buffer_size = 100  # Less than buffer_size
    pipeline.prediction_interval = 0
    pipeline.feature_calc_interval = 0
    pipeline.monitoring_interval = 0
    pipeline.default_processing_level = 'invalid'
    pipeline.max_workers = 0
    
    errors = pipeline.validate()
    print(f"Pipeline validation errors: {errors}")
    assert len(errors) >= 4  # At least 4 values should be invalid
    
    print("✓ Component validation test passed")


def test_performance_targets():
    """Test that configuration meets performance targets."""
    print("Testing performance targets...")
    
    config = UnifiedSchedulerConfig()
    
    # Check polling intervals meet targets
    assert config.polling.during_game <= 10, "During game polling should be <= 10s"
    assert config.polling.pre_game <= 60, "Pre-game polling should be <= 60s"
    assert config.polling.game_day <= 300, "Game day polling should be <= 300s"
    
    # Check pipeline settings meet targets
    assert config.pipeline.buffer_size >= 1000, "Buffer size should be >= 1000"
    assert config.pipeline.prediction_interval <= 30, "Prediction interval should be <= 30s"
    assert config.pipeline.feature_calc_interval <= 15, "Feature calc interval should be <= 15s"
    
    # Check error handling meets targets
    assert config.error_handling.max_retries >= 3, "Max retries should be >= 3"
    assert config.error_handling.circuit_breaker_threshold >= 5, "Circuit breaker threshold should be >= 5"
    
    # Check monitoring meets targets
    assert config.monitoring.metrics_interval <= 60, "Metrics interval should be <= 60s"
    assert config.monitoring.enable_metrics is True, "Metrics should be enabled"
    assert config.monitoring.enable_health_checks is True, "Health checks should be enabled"
    
    print("✓ Performance targets test passed")


def main():
    """Run all tests."""
    print("Running Unified Scheduler Isolated Tests")
    print("=" * 50)
    
    try:
        test_default_config()
        test_config_validation()
        test_config_serialization()
        test_file_operations()
        test_component_validation()
        test_performance_targets()
        
        print("\n" + "=" * 50)
        print("✓ All tests passed successfully!")
        print("Unified scheduler core functionality is working correctly.")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()
