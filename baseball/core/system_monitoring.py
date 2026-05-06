"""
System-wide monitoring and benchmarking for baseball namespace.

Provides:
- Comprehensive performance monitoring
- System health tracking
- Resource usage monitoring
- Metrics collection and aggregation
- Alert generation and notification
"""

import asyncio
import time
import psutil
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from baseball.core.error_architecture import EncapsulatedComponent, BenchmarkingMixin
from baseball.core.intelligent_recovery import intelligent_recovery


class MetricType(Enum):
    """Types of metrics to collect"""
    PERFORMANCE = "performance"
    SYSTEM_HEALTH = "system_health"
    RESOURCE_USAGE = "resource_usage"
    ERROR_RATES = "error_rates"
    THROUGHPUT = "throughput"
    LATENCY = "latency"
    AVAILABILITY = "availability"


@dataclass
class SystemMetrics:
    """System-wide metrics collection"""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    disk_usage_mb: float = 0.0
    network_io_mb: float = 0.0
    active_connections: int = 0
    queue_depth: int = 0
    error_count: int = 0
    success_rate: float = 0.0
    uptime_seconds: float = 0.0
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations"""
    operation_name: str
    duration_ms: float = 0.0
    rows_processed: int = 0
    throughput_per_second: float = 0.0
    error_count: int = 0
    success_rate: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0


@dataclass
class HealthStatus:
    """System health status"""
    component_name: str
    status: str  # HEALTHY, DEGRADED, UNHEALTHY
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    uptime_seconds: float = 0.0
    error_rate: float = 0.0
    response_time_ms: float = 0.0
    alerts: List[str] = field(default_factory=list)


class SystemMonitor(EncapsulatedComponent):
    """System-wide monitoring with intelligent error handling"""
    
    def __init__(self, name: str = "system_monitor"):
        super().__init__(name)
        self.metrics_history: List[SystemMetrics] = []
        self.performance_history: Dict[str, List[PerformanceMetrics]] = {}
        self.health_status: Dict[str, HealthStatus] = {}
        self.alert_thresholds: Dict[str, float] = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'error_rate': 5.0,
            'response_time': 5000.0  # 5 seconds
        }
        self.collection_interval: float = 30.0  # seconds
        self.max_history_size: int = 1000
    
    async def start_monitoring(self):
        """Start system monitoring"""
        self.set_config('monitoring_active', True)
        self.set_config('collection_interval', self.collection_interval)
        
        # Start background monitoring task
        asyncio.create_task(self._monitoring_loop())
        
        return True
    
    async def stop_monitoring(self):
        """Stop system monitoring"""
        self.set_config('monitoring_active', False)
        return True
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.get_config('monitoring_active', False):
            try:
                await self._collect_system_metrics()
                await self._check_system_health()
                await self._analyze_performance_trends()
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                await intelligent_recovery.handle_error_intelligently(
                    e,
                    self.error_context,
                    "system_monitoring_loop"
                )
    
    async def _collect_system_metrics(self):
        """Collect current system metrics"""
        self.start_benchmark("system_metrics_collection")
        
        try:
            metrics = SystemMetrics()
            
            # CPU usage
            metrics.cpu_usage_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            metrics.memory_usage_mb = memory.used / 1024 / 1024
            
            # Disk usage
            disk = psutil.disk_usage('/')
            metrics.disk_usage_mb = disk.used / 1024 / 1024
            
            # Network I/O
            net_io = psutil.net_io_counters()
            metrics.network_io_mb = (net_io.bytes_sent + net_io.bytes_recv) / 1024 / 1024
            
            # System-specific metrics
            metrics.active_connections = len(psutil.net_connections())
            metrics.uptime_seconds = time.time() - psutil.boot_time()
            
            # Calculate custom metrics
            metrics.custom_metrics = await self._collect_custom_metrics()
            
            self.metrics_history.append(metrics)
            
            # Keep history size manageable
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history = self.metrics_history[-self.max_history_size:]
            
            self.end_benchmark("system_metrics_collection")
            
        except Exception as e:
            await intelligent_recovery.handle_error_intelligently(
                e,
                self.error_context,
                "collect_system_metrics"
            )
    
    async def _collect_custom_metrics(self) -> Dict[str, Any]:
        """Collect custom application-specific metrics"""
        custom_metrics = {}
        
        try:
            # Database connection pool metrics
            from baseball.core.db import get_db_connection
            test_conn = get_db_connection()
            custom_metrics['db_connection_pool_size'] = 1  # Would be actual pool size
            test_conn.close()
            
            # Active operations count
            custom_metrics['active_data_sources'] = len(self._get_active_data_sources())
            custom_metrics['active_models'] = len(self._get_active_models())
            
            # Queue depths
            custom_metrics['data_ingestion_queue'] = self._get_queue_depth('data_ingestion')
            custom_metrics['prediction_queue'] = self._get_queue_depth('prediction')
            
        except Exception as e:
            await intelligent_recovery.handle_error_intelligently(
                e,
                self.error_context,
                "collect_custom_metrics"
            )
        
        return custom_metrics
    
    def _get_active_data_sources(self) -> List[str]:
        """Get list of active data sources"""
        # This would integrate with actual data source registry
        return ['retrosheet', 'mlb', 'statcast', 'espn']
    
    def _get_active_models(self) -> List[str]:
        """Get list of active models"""
        # This would integrate with actual model registry
        return ['xgboost_hierarchical', 'lstm_sequence', 'markov_chain']
    
    def _get_queue_depth(self, queue_name: str) -> int:
        """Get queue depth for a specific queue"""
        # This would integrate with actual queue monitoring
        return 0
    
    async def _check_system_health(self):
        """Check overall system health"""
        self.start_benchmark("health_check")
        
        try:
            health_status = HealthStatus(
                component_name="baseball_system",
                status="HEALTHY",
                uptime_seconds=time.time() - psutil.boot_time()
            )
            
            # Check resource thresholds
            current_metrics = self.metrics_history[-1] if self.metrics_history else SystemMetrics()
            
            if current_metrics.cpu_usage_percent > self.alert_thresholds['cpu_usage']:
                health_status.status = "DEGRADED"
                health_status.alerts.append(f"High CPU usage: {current_metrics.cpu_usage_percent:.1f}%")
            
            if current_metrics.memory_usage_mb > self.alert_thresholds['memory_usage']:
                health_status.status = "DEGRADED"
                health_status.alerts.append(f"High memory usage: {current_metrics.memory_usage_mb:.1f}MB")
            
            if current_metrics.disk_usage_mb > self.alert_thresholds['disk_usage']:
                health_status.status = "DEGRADED"
                health_status.alerts.append(f"High disk usage: {current_metrics.disk_usage_mb:.1f}MB")
            
            # Calculate error rate
            if len(self.metrics_history) > 10:
                recent_metrics = self.metrics_history[-10:]
                error_count = sum(1 for m in recent_metrics if m.error_count > 0)
                error_rate = error_count / 10.0
                
                if error_rate > self.alert_thresholds['error_rate']:
                    health_status.status = "UNHEALTHY"
                    health_status.alerts.append(f"High error rate: {error_rate:.1%}")
                
                health_status.error_rate = error_rate
            
            self.health_status['baseball_system'] = health_status
            self.end_benchmark("health_check")
            
        except Exception as e:
            await intelligent_recovery.handle_error_intelligently(
                e,
                self.error_context,
                "check_system_health"
            )
    
    async def _analyze_performance_trends(self):
        """Analyze performance trends and generate insights"""
        self.start_benchmark("trend_analysis")
        
        try:
            if len(self.metrics_history) < 5:
                self.end_benchmark("trend_analysis")
                return
            
            recent_metrics = self.metrics_history[-10:]
            
            # Analyze CPU trend
            cpu_values = [m.cpu_usage_percent for m in recent_metrics]
            cpu_trend = self._calculate_trend(cpu_values)
            
            # Analyze memory trend
            memory_values = [m.memory_usage_mb for m in recent_metrics]
            memory_trend = self._calculate_trend(memory_values)
            
            # Analyze error rate trend
            error_values = [m.error_count for m in recent_metrics]
            error_trend = self._calculate_trend(error_values)
            
            # Store trend analysis
            trend_insights = {
                'cpu_trend': cpu_trend,
                'memory_trend': memory_trend,
                'error_trend': error_trend,
                'period_minutes': len(recent_metrics) * self.collection_interval,
                'analysis_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self.set_config('latest_trends', trend_insights)
            self.end_benchmark("trend_analysis")
            
        except Exception as e:
            await intelligent_recovery.handle_error_intelligently(
                e,
                self.error_context,
                "analyze_performance_trends"
            )
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend from values"""
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear regression to determine trend
        n = len(values)
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        if n * sum_x2 - sum_x ** 2 == 0:
            return "stable"
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"
    
    async def record_operation_performance(self, operation_name: str, duration_ms: float, 
                                   rows_processed: int = 0, error_count: int = 0):
        """Record performance metrics for an operation"""
        self.start_benchmark(f"operation_{operation_name}")
        
        performance_metric = PerformanceMetrics(
            operation_name=operation_name,
            duration_ms=duration_ms,
            rows_processed=rows_processed,
            throughput_per_second=rows_processed / (duration_ms / 1000) if duration_ms > 0 else 0,
            error_count=error_count,
            success_rate=1.0 - (error_count / max(1, rows_processed)) if rows_processed > 0 else 1.0
        )
        
        if operation_name not in self.performance_history:
            self.performance_history[operation_name] = []
        
        self.performance_history[operation_name].append(performance_metric)
        
        # Keep only recent performance history
        if len(self.performance_history[operation_name]) > 100:
            self.performance_history[operation_name] = self.performance_history[operation_name][-100:]
        
        self.end_benchmark(f"operation_{operation_name}")
    
    def get_system_metrics(self, limit: int = 100) -> List[SystemMetrics]:
        """Get recent system metrics"""
        return self.metrics_history[-limit:] if self.metrics_history else []
    
    def get_performance_metrics(self, operation_name: str, limit: int = 50) -> List[PerformanceMetrics]:
        """Get performance metrics for an operation"""
        return self.performance_history.get(operation_name, [])[-limit:] if operation_name in self.performance_history else []
    
    def get_health_status(self, component_name: Optional[str] = None) -> Optional[HealthStatus]:
        """Get health status for a component"""
        if component_name:
            return self.health_status.get(component_name)
        elif self.health_status:
            # Return overall system health
            return list(self.health_status.values())[0]
        return None
    
    def get_performance_summary(self, operation_name: str) -> Dict[str, Any]:
        """Get performance summary for an operation"""
        if operation_name not in self.performance_history:
            return {}
        
        metrics = self.performance_history[operation_name]
        if not metrics:
            return {}
        
        recent_metrics = metrics[-10:] if len(metrics) > 10 else metrics
        
        if not recent_metrics:
            return {}
        
        durations = [m.duration_ms for m in recent_metrics]
        throughputs = [m.throughput_per_second for m in recent_metrics]
        success_rates = [m.success_rate for m in recent_metrics]
        
        return {
            'operation_name': operation_name,
            'total_operations': len(metrics),
            'avg_duration_ms': sum(durations) / len(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'avg_throughput': sum(throughputs) / len(throughputs),
            'max_throughput': max(throughputs),
            'avg_success_rate': sum(success_rates) / len(success_rates),
            'min_success_rate': min(success_rates),
            'max_success_rate': max(success_rates),
            'last_operation': recent_metrics[-1].timestamp.isoformat() if recent_metrics else None
        }
    
    def get_trend_analysis(self) -> Dict[str, Any]:
        """Get latest trend analysis"""
        return self.get_config('latest_trends', {})
    
    async def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        self.start_benchmark("health_report_generation")
        
        try:
            current_metrics = self.metrics_history[-1] if self.metrics_history else SystemMetrics()
            current_health = self.get_health_status()
            
            report = {
                'report_timestamp': datetime.now(timezone.utc).isoformat(),
                'system_metrics': {
                    'cpu_usage_percent': current_metrics.cpu_usage_percent,
                    'memory_usage_mb': current_metrics.memory_usage_mb,
                    'disk_usage_mb': current_metrics.disk_usage_mb,
                    'network_io_mb': current_metrics.network_io_mb,
                    'active_connections': current_metrics.active_connections,
                    'uptime_seconds': current_metrics.uptime_seconds
                },
                'health_status': {
                    'overall_status': current_health.status if current_health else 'unknown',
                    'component_health': {
                        name: {
                            'status': status.status,
                            'uptime_seconds': status.uptime_seconds,
                            'alerts': status.alerts,
                            'last_check': status.last_check.isoformat()
                        }
                        for name, status in self.health_status.items()
                    } if current_health else {}
                },
                'performance_summary': {
                    op_name: self.get_performance_summary(op_name)
                    for op_name in self.performance_history.keys()
                },
                'trend_analysis': self.get_trend_analysis(),
                'alert_thresholds': self.alert_thresholds,
                'monitoring_config': {
                    'collection_interval_seconds': self.collection_interval,
                    'max_history_size': self.max_history_size,
                    'monitoring_active': self.get_config('monitoring_active', False)
                }
            }
            
            self.end_benchmark("health_report_generation")
            return report
            
        except Exception as e:
            await intelligent_recovery.handle_error_intelligently(
                e,
                self.error_context,
                "generate_health_report"
            )
            return {}


# Global system monitor instance
system_monitor = SystemMonitor()
