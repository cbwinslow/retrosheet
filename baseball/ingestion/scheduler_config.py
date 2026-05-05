"""Scheduler Configuration Management.

Provides configuration management for the unified live game scheduler,
including validation, persistence, and dynamic updates.

Author: Agent Cascade
Date: 2026-05-05
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from baseball.core.db import get_db_connection

logger = logging.getLogger(__name__)


class ConfigFormat(Enum):
    """Configuration file formats."""
    JSON = "json"
    YAML = "yaml"
    ENV = "env"


@dataclass
class PollingConfig:
    """Polling configuration settings."""
    
    # Interval settings (seconds)
    during_game: int = 10
    pre_game: int = 60
    game_day: int = 300
    off_hours: int = 3600
    
    # Window definitions
    pre_game_minutes: int = 60
    post_game_minutes: int = 30
    
    # Adaptive settings
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
    
    # Buffer settings
    buffer_size: int = 1000
    max_buffer_size: int = 10000
    
    # Processing intervals (seconds)
    prediction_interval: int = 30
    feature_calc_interval: int = 15
    monitoring_interval: int = 60
    
    # Processing levels
    default_processing_level: str = "full"  # full, basic, minimal
    enable_parallel_processing: bool = True
    max_workers: int = 4
    
    # Data retention
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
    
    # Retry settings
    max_retries: int = 3
    retry_delay: int = 5
    retry_backoff_factor: float = 2.0
    
    # Circuit breaker settings
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 300
    circuit_breaker_recovery_timeout: int = 60
    
    # Error logging
    log_all_errors: bool = True
    log_error_context: bool = True
    max_error_history: int = 1000
    
    # Alerting
    enable_alerts: bool = True
    alert_thresholds: Dict[str, Union[int, float]] = field(default_factory=lambda: {
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
    
    # Connection settings
    connection_timeout: int = 30
    max_connections: int = 10
    connection_retry_attempts: int = 3
    
    # Job persistence
    enable_job_persistence: bool = True
    job_history_retention_days: int = 30
    
    # Metrics storage
    enable_metrics_storage: bool = True
    metrics_aggregation_interval: int = 300  # 5 minutes
    
    # Schema settings
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
    
    # Metrics collection
    enable_metrics: bool = True
    metrics_interval: int = 60
    enable_performance_metrics: bool = True
    enable_business_metrics: bool = True
    
    # Health checks
    enable_health_checks: bool = True
    health_check_interval: int = 30
    health_check_timeout: int = 10
    
    # Alerting
    enable_alerting: bool = True
    alert_webhook_url: Optional[str] = None
    alert_email_recipients: List[str] = field(default_factory=list)
    
    # Dashboard
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
    
    # Component configurations
    polling: PollingConfig = field(default_factory=PollingConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    error_handling: ErrorHandlingConfig = field(default_factory=ErrorHandlingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # Global settings
    scheduler_name: str = "unified_live_scheduler"
    environment: str = "production"  # development, staging, production
    debug: bool = False
    log_level: str = "INFO"
    
    # Coordination settings
    max_concurrent_operations: int = 5
    coordination_timeout: int = 30
    enable_coordination: bool = True
    
    # Feed management
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
        return asdict(self)
    
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


class ConfigManager:
    """Manages scheduler configuration with persistence and validation."""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file, uses default if None
        """
        if config_path is None:
            config_path = Path.home() / '.baseball' / 'scheduler_config.json'
        
        self.config_path = Path(config_path)
        self._config: Optional[UnifiedSchedulerConfig] = None
        self._format = ConfigFormat.JSON
        
        # Ensure config directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> UnifiedSchedulerConfig:
        """Load configuration from file.
        
        Returns:
            Loaded configuration
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not self.config_path.exists():
            logger.info(f"Config file not found at {self.config_path}, creating default")
            self._config = UnifiedSchedulerConfig()
            self.save_config()
            return self._config
        
        try:
            with open(self.config_path, 'r') as f:
                if self._format == ConfigFormat.JSON:
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported format: {self._format}")
            
            self._config = UnifiedSchedulerConfig.from_dict(data)
            
            # Validate configuration
            errors = self._config.validate()
            if errors:
                raise ValueError(f"Invalid configuration: {'; '.join(errors)}")
            
            logger.info(f"Configuration loaded from {self.config_path}")
            return self._config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def save_config(self, config: Optional[UnifiedSchedulerConfig] = None) -> None:
        """Save configuration to file.
        
        Args:
            config: Configuration to save, uses current if None
        """
        if config is not None:
            self._config = config
        
        if self._config is None:
            raise ValueError("No configuration to save")
        
        # Validate before saving
        errors = self._config.validate()
        if errors:
            raise ValueError(f"Cannot save invalid configuration: {'; '.join(errors)}")
        
        try:
            data = self._config.to_dict()
            
            with open(self.config_path, 'w') as f:
                if self._format == ConfigFormat.JSON:
                    json.dump(data, f, indent=2, sort_keys=True)
                else:
                    raise ValueError(f"Unsupported format: {self._format}")
            
            logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def get_config(self) -> UnifiedSchedulerConfig:
        """Get current configuration.
        
        Returns:
            Current configuration, loads from file if not already loaded
        """
        if self._config is None:
            return self.load_config()
        
        return self._config
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values.
        
        Args:
            updates: Dictionary of updates to apply
        """
        if self._config is None:
            self.load_config()
        
        # Convert current config to dict and apply updates
        current_dict = self._config.to_dict()
        
        # Deep merge updates
        self._deep_merge(current_dict, updates)
        
        # Create new config from updated dict
        self._config = UnifiedSchedulerConfig.from_dict(current_dict)
        
        # Validate updated config
        errors = self._config.validate()
        if errors:
            raise ValueError(f"Invalid configuration updates: {'; '.join(errors)}")
        
        logger.info("Configuration updated")
    
    def _deep_merge(self, base: Dict[str, Any], updates: Dict[str, Any]) -> None:
        """Deep merge updates into base dictionary."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self._config = UnifiedSchedulerConfig()
        self.save_config()
        logger.info("Configuration reset to defaults")
    
    def export_config(self, export_path: Union[str, Path], format: ConfigFormat = ConfigFormat.JSON) -> None:
        """Export configuration to specified path.
        
        Args:
            export_path: Path to export configuration
            format: Export format
        """
        if self._config is None:
            self.load_config()
        
        export_path = Path(export_path)
        
        try:
            data = self._config.to_dict()
            
            with open(export_path, 'w') as f:
                if format == ConfigFormat.JSON:
                    json.dump(data, f, indent=2, sort_keys=True)
                else:
                    raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Configuration exported to {export_path}")
            
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            raise
    
    def import_config(self, import_path: Union[str, Path], format: ConfigFormat = ConfigFormat.JSON) -> None:
        """Import configuration from specified path.
        
        Args:
            import_path: Path to import configuration from
            format: Import format
        """
        import_path = Path(import_path)
        
        if not import_path.exists():
            raise FileNotFoundError(f"Import file not found: {import_path}")
        
        try:
            with open(import_path, 'r') as f:
                if format == ConfigFormat.JSON:
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported import format: {format}")
            
            self._config = UnifiedSchedulerConfig.from_dict(data)
            
            # Validate imported config
            errors = self._config.validate()
            if errors:
                raise ValueError(f"Invalid imported configuration: {'; '.join(errors)}")
            
            self.save_config()
            logger.info(f"Configuration imported from {import_path}")
            
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            raise


# Convenience functions

def get_default_config() -> UnifiedSchedulerConfig:
    """Get default scheduler configuration.
    
    Returns:
        Default configuration
    """
    return UnifiedSchedulerConfig()


def load_config_from_file(config_path: Union[str, Path]) -> UnifiedSchedulerConfig:
    """Load configuration from specified file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Loaded configuration
    """
    manager = ConfigManager(config_path)
    return manager.load_config()


def save_config_to_file(config: UnifiedSchedulerConfig, config_path: Union[str, Path]) -> None:
    """Save configuration to specified file.
    
    Args:
        config: Configuration to save
        config_path: Path to save configuration
    """
    manager = ConfigManager(config_path)
    manager.save_config(config)


def validate_config(config: UnifiedSchedulerConfig) -> List[str]:
    """Validate configuration.
    
    Args:
        config: Configuration to validate
        
    Returns:
        List of validation errors
    """
    return config.validate()
