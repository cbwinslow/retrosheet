# Unified Live Game Scheduler Guide

## Overview

The Unified Live Game Scheduler is a comprehensive system that combines multiple live data ingestion components into a single, cohesive scheduler. It integrates SmartScheduler (adaptive polling), EnhancedLivePipeline (play-by-play processing and predictions), DatabaseScheduler (job persistence), and ErrorHandler (robust error handling) with a coordination layer for seamless operation.

## Architecture

### Core Components

1. **UnifiedLiveGameScheduler** - Main orchestrator that coordinates all components
2. **SmartScheduler** - Adaptive polling based on game schedules and states
3. **EnhancedLivePipeline** - Real-time data processing and prediction generation
4. **DatabaseScheduler** - PostgreSQL-based job scheduling and persistence
5. **ErrorHandler** - Circuit breaker pattern with retry logic and alerting
6. **SchedulerCoordination** - Component lifecycle management and coordination

### Data Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Smart Scheduler│───►│   Coordination   │───►│ Enhanced Pipeline│
│   (Polling)      │    │   Layer          │    │   (Processing)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Database Scheduler│    │   Error Handler  │    │   Predictions   │
│   (Persistence)  │    │   (Reliability)  │    │   (ML Models)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Configuration

### Default Configuration

The scheduler uses sensible defaults optimized for performance:

```python
# Polling Intervals
during_game: 10s     # During active games
pre_game: 60s        # Before games start
game_day: 300s       # On game days
off_hours: 3600s     # During off-hours

# Pipeline Settings
buffer_size: 1000     # Game state buffer
prediction_interval: 30s  # Between predictions
feature_interval: 15s      # Between feature calculations
monitoring_interval: 60s   # System health checks

# Error Handling
max_retries: 3
circuit_breaker_threshold: 5
retry_delay: 5s
```

### Configuration File

Create a JSON configuration file at `~/.baseball/scheduler_config.json`:

```json
{
  "scheduler_name": "production_scheduler",
  "environment": "production",
  "polling": {
    "during_game": 10,
    "pre_game": 60,
    "game_day": 300,
    "off_hours": 3600,
    "enable_adaptive": true
  },
  "pipeline": {
    "buffer_size": 1000,
    "prediction_interval": 30,
    "feature_calc_interval": 15,
    "monitoring_interval": 60,
    "enable_parallel_processing": true,
    "max_workers": 4
  },
  "error_handling": {
    "max_retries": 3,
    "retry_delay": 5,
    "circuit_breaker_threshold": 5,
    "circuit_breaker_timeout": 300,
    "enable_alerts": true
  },
  "database": {
    "connection_timeout": 30,
    "max_connections": 10,
    "enable_job_persistence": true
  },
  "monitoring": {
    "enable_metrics": true,
    "metrics_interval": 60,
    "enable_health_checks": true,
    "enable_dashboard": true,
    "dashboard_port": 8080
  }
}
```

## CLI Usage

### Starting the Unified Scheduler

```bash
# Start with default configuration
baseball live start --unified

# Start with custom configuration file
baseball live start --unified --config /path/to/config.json

# Start with feed configurations
baseball live start --unified --feeds feeds.json

# Start with live monitoring
baseball live start --unified --watch
```

### Feed Configuration

Create a feeds configuration file:

```json
[
  {
    "name": "mlb_primary",
    "url": "wss://ws.mlb.com/live",
    "type": "mlb",
    "enabled": true,
    "priority": 10,
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 5,
    "processing_level": "full"
  },
  {
    "name": "espn_secondary",
    "url": "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb",
    "type": "espn",
    "enabled": true,
    "priority": 5,
    "timeout": 30,
    "processing_level": "basic"
  }
]
```

### Status Monitoring

```bash
# Check unified scheduler status
baseball live status --unified

# Detailed status with performance metrics
baseball live status --unified --detailed

# Legacy pipeline status
baseball live status
```

### Running Predictions

```bash
# Run predictions for all active games
baseball live predict --unified

# Run predictions for specific games
baseball live predict --unified --games 12345 12346

# Use specific model
baseball live predict --unified --model win_probability

# Output in JSON format
baseball live predict --unified --format json
```

### Configuration Management

```bash
# Show current configuration
baseball live config show

# Validate configuration
baseball live config validate

# Export configuration
baseball live config export --export backup_config.json

# Import configuration
baseball live config import --import new_config.json
```

### Testing

```bash
# Test unified scheduler components
baseball live test unified

# Test with stress load
baseball live test unified --type stress

# Test integration
baseball live test unified --type integration
```

## Feed Management

### Adding Feeds

Feeds can be added dynamically to the running scheduler:

```python
from baseball.ingestion.unified_scheduler import UnifiedLiveGameScheduler, FeedConfig

# Create feed configuration
feed_config = FeedConfig(
    name="new_feed",
    url="wss://example.com/live",
    feed_type="custom",
    enabled=True,
    priority=5,
    timeout=30,
    retry_attempts=3,
    processing_level="full"
)

# Add to running scheduler
await scheduler.add_feed(feed_config)
```

### Feed Types

- **mlb** - MLB Stats API live feed
- **espn** - ESPN API supplemental data
- **statcast** - Statcast pitch-level data
- **custom** - Custom WebSocket or REST feeds

### Processing Levels

- **full** - Complete processing with predictions and features
- **basic** - Data ingestion and storage only
- **minimal** - Raw data capture only

## Performance Optimization

### Adaptive Polling

The scheduler automatically adjusts polling intervals based on:

- Game schedules and states
- Data freshness requirements
- System load and performance
- Error rates and reliability

### Parallel Processing

Enable parallel processing for improved throughput:

```json
{
  "pipeline": {
    "enable_parallel_processing": true,
    "max_workers": 4
  }
}
```

### Buffer Management

Configure buffer sizes based on expected load:

```json
{
  "pipeline": {
    "buffer_size": 1000,
    "max_buffer_size": 10000,
    "data_retention_hours": 24
  }
}
```

## Error Handling

### Circuit Breaker Pattern

The scheduler uses circuit breakers to prevent cascade failures:

- **Threshold**: Number of failures before opening circuit
- **Timeout**: How long to keep circuit open
- **Recovery**: Gradual recovery with health checks

### Retry Logic

Configurable retry strategies:

```json
{
  "error_handling": {
    "max_retries": 3,
    "retry_delay": 5,
    "retry_backoff_factor": 2.0,
    "circuit_breaker_threshold": 5,
    "circuit_breaker_timeout": 300
  }
}
```

### Alerting

Configure alerts for critical failures:

```json
{
  "error_handling": {
    "enable_alerts": true,
    "alert_thresholds": {
      "failure_rate": 0.1,
      "error_rate": 0.05,
      "latency_ms": 1000,
      "memory_mb": 1024
    }
  }
}
```

## Monitoring

### Metrics Collection

The scheduler collects comprehensive metrics:

- **Performance**: Latency, throughput, error rates
- **Business**: Games processed, predictions generated
- **System**: Memory usage, CPU utilization, connection counts

### Health Checks

Built-in health checks for all components:

```bash
# Check scheduler health
baseball live status --unified --detailed
```

### Dashboard

Web dashboard for real-time monitoring:

```json
{
  "monitoring": {
    "enable_dashboard": true,
    "dashboard_port": 8080,
    "dashboard_refresh_interval": 5
  }
}
```

Access at: `http://localhost:8080`

## Troubleshooting

### Common Issues

#### Scheduler Won't Start

1. Check configuration validity:
   ```bash
   baseball live config validate
   ```

2. Verify database connectivity:
   ```bash
   baseball live test unified
   ```

3. Check log files for errors:
   ```bash
   tail -f ~/.baseball/logs/scheduler.log
   ```

#### High Error Rates

1. Check feed configurations:
   ```bash
   baseball live status --unified --detailed
   ```

2. Verify network connectivity:
   ```bash
   curl -I https://site.api.espn.com/apis/site/v2/sports/baseball/mlb
   ```

3. Adjust retry settings:
   ```json
   {
     "error_handling": {
       "max_retries": 5,
       "retry_delay": 10
     }
   }
   ```

#### Memory Issues

1. Reduce buffer sizes:
   ```json
   {
     "pipeline": {
       "buffer_size": 500,
       "data_retention_hours": 12
     }
   }
   ```

2. Enable data retention:
   ```json
   {
     "pipeline": {
       "data_retention_hours": 6,
       "metrics_retention_days": 7
     }
   }
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```json
{
  "debug": true,
  "log_level": "DEBUG"
}
```

Or use CLI flag:
```bash
baseball live start --unified --debug
```

## Best Practices

### Configuration

1. **Environment-specific configs**: Use different configurations for dev/staging/prod
2. **Validation**: Always validate configurations before deployment
3. **Backup**: Export and version control configuration files

### Performance

1. **Adaptive polling**: Enable adaptive polling for optimal resource usage
2. **Parallel processing**: Use parallel processing for high-throughput scenarios
3. **Buffer sizing**: Size buffers based on expected peak load

### Reliability

1. **Circuit breakers**: Configure appropriate thresholds for your environment
2. **Retry logic**: Use exponential backoff for external services
3. **Health checks**: Monitor all components continuously

### Security

1. **Feed authentication**: Secure feed connections with proper authentication
2. **Database access**: Use least-privilege database credentials
3. **Network security**: Restrict network access to required endpoints

## API Reference

### UnifiedLiveGameScheduler

Main scheduler class with the following key methods:

```python
class UnifiedLiveGameScheduler:
    async def start(self) -> None
    async def stop(self) -> None
    async def add_feed(self, feed_config: FeedConfig) -> None
    async def remove_feed(self, feed_name: str) -> None
    def get_status(self) -> SchedulerStatusInfo
    async def run_predictions(self, game_pks: Optional[List[int]] = None) -> Dict[str, Any]
```

### FeedConfig

Configuration for data feeds:

```python
@dataclass
class FeedConfig:
    name: str
    url: str
    feed_type: str
    enabled: bool = True
    priority: int = 5
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5
    processing_level: str = "full"
```

### SchedulerStatusInfo

Status information returned by the scheduler:

```python
@dataclass
class SchedulerStatusInfo:
    status: SchedulerStatus
    uptime_seconds: float
    start_time: Optional[datetime]
    last_error: Optional[str]
    total_polls: int
    successful_polls: int
    failed_polls: int
    average_poll_time: float
    active_feeds: List[str]
    total_feeds: int
    smart_scheduler: Dict[str, Any]
    enhanced_pipeline: Dict[str, Any]
    database_scheduler: Dict[str, Any]
    error_handler: Dict[str, Any]
```

## Migration Guide

### From Legacy Pipeline

To migrate from the legacy EnhancedLivePipeline:

1. **Update CLI commands**: Use `--unified` flag
2. **Configuration**: Convert to unified scheduler format
3. **Feeds**: Migrate feed configurations to new format
4. **Monitoring**: Use unified status commands

### Example Migration

**Legacy:**
```bash
baseball live start --feeds legacy_feeds.json --buffer-size 1000
baseball live status
baseball live predict --games 12345
```

**Unified:**
```bash
baseball live start --unified --feeds unified_feeds.json
baseball live status --unified --detailed
baseball live predict --unified --games 12345
```

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review log files for error messages
3. Use the test commands to diagnose issues
4. Enable debug mode for detailed logging

## Version History

- **v1.0.0**: Initial release with unified scheduler
- **v1.1.0**: Added adaptive polling and enhanced monitoring
- **v1.2.0**: Improved error handling and circuit breaker patterns
- **v1.3.0**: Added dashboard and performance optimizations
