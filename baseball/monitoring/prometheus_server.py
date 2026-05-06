"""
Prometheus Metrics Server for Multi-Model Ensemble System

Provides comprehensive metrics collection and exposure for production monitoring
including model performance, system resources, and business metrics.
"""

import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
from prometheus_client import REGISTRY, Gauge, Histogram, Counter, start_http_server
from prometheus_client.core import CollectorRegistry

from baseball.models.base import BaseModel
from baseball.models.registry import ModelRegistry


@dataclass
class ModelMetrics:
    """Metrics for individual model performance"""
    model_name: str
    prediction_count: int = 0
    accuracy: float = 0.0
    latency_ms: float = 0.0
    error_count: int = 0
    confidence_avg: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    last_updated: datetime = None


@dataclass
class SystemMetrics:
    """System-level performance metrics"""
    total_requests: int = 0
    active_models: int = 0
    system_uptime_seconds: float = 0.0
    memory_total_mb: float = 0.0
    memory_available_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    disk_usage_percent: float = 0.0
    network_io_bytes: int = 0


class PrometheusMetricsCollector:
    """
    Prometheus collector for baseball model metrics
    """
    
    def __init__(self, model_registry: ModelRegistry = None):
        self.model_registry = model_registry or ModelRegistry()
        self.model_metrics: Dict[str, ModelMetrics] = {}
        self.system_metrics = SystemMetrics()
        self.start_time = time.time()
        
        # Initialize Prometheus metrics
        self._init_prometheus_metrics()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metric objects"""
        
        # Model performance metrics
        self.model_prediction_count = Gauge(
            'baseball_model_predictions_total',
            'Total number of predictions per model',
            ['model_name']
        )
        
        self.model_accuracy = Gauge(
            'baseball_model_accuracy',
            'Model accuracy percentage',
            ['model_name']
        )
        
        self.model_latency = Histogram(
            'baseball_model_prediction_duration_seconds',
            'Time spent on model predictions',
            ['model_name'],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        self.model_error_count = Counter(
            'baseball_model_prediction_errors_total',
            'Total number of model prediction errors',
            ['model_name']
        )
        
        self.model_confidence = Gauge(
            'baseball_model_confidence_avg',
            'Average prediction confidence per model',
            ['model_name']
        )
        
        self.model_memory_usage = Gauge(
            'baseball_model_memory_usage_bytes',
            'Memory usage per model in bytes',
            ['model_name']
        )
        
        self.model_cpu_usage = Gauge(
            'baseball_model_cpu_usage_percent',
            'CPU usage per model in percent',
            ['model_name']
        )
        
        # System metrics
        self.system_requests_total = Counter(
            'baseball_system_requests_total',
            'Total number of system requests'
        )
        
        self.system_active_models = Gauge(
            'baseball_system_active_models',
            'Number of active models'
        )
        
        self.system_uptime = Gauge(
            'baseball_system_uptime_seconds',
            'System uptime in seconds'
        )
        
        self.system_memory_total = Gauge(
            'baseball_system_memory_total_bytes',
            'Total system memory in bytes'
        )
        
        self.system_memory_available = Gauge(
            'baseball_system_memory_available_bytes',
            'Available system memory in bytes'
        )
        
        self.system_cpu_usage = Gauge(
            'baseball_system_cpu_usage_percent',
            'System CPU usage in percent'
        )
        
        self.system_disk_usage = Gauge(
            'baseball_system_disk_usage_percent',
            'System disk usage in percent'
        )
        
        self.system_network_io = Counter(
            'baseball_system_network_io_bytes_total',
            'Total network I/O in bytes',
            ['direction']
        )
        
    def collect(self):
        """Collect metrics for Prometheus"""
        
        # Update system metrics
        self._update_system_metrics()
        
        # Update model metrics
        self._update_model_metrics()
        
        # Yield all metrics
        yield from self._collect_model_metrics()
        yield from self._collect_system_metrics()
        
    def _update_system_metrics(self):
        """Update system-level metrics"""
        try:
            import psutil
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.system_metrics.memory_total_mb = memory.total / (1024 * 1024)
            self.system_metrics.memory_available_mb = memory.available / (1024 * 1024)
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            self.system_metrics.cpu_usage_percent = cpu_percent
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            self.system_metrics.disk_usage_percent = disk.percent
            
            # Network metrics
            net_io = psutil.net_io_counters()
            self.system_metrics.network_io_bytes = net_io.bytes_sent + net_io.bytes_recv
            
            # Uptime
            self.system_metrics.system_uptime_seconds = time.time() - self.start_time
            
        except Exception as e:
            self.logger.error(f"Error updating system metrics: {e}")
            
    def _update_model_metrics(self):
        """Update model-specific metrics"""
        try:
            models = self.model_registry.get_all_models()
            
            for model_name, model_info in models.items():
                if model_name not in self.model_metrics:
                    self.model_metrics[model_name] = ModelMetrics(model_name=model_name)
                
                # Get model instance if available
                model_instance = self.model_registry.get_model(model_name)
                
                if model_instance and hasattr(model_instance, 'get_performance_metrics'):
                    perf_metrics = model_instance.get_performance_metrics()
                    
                    self.model_metrics[model_name].accuracy = perf_metrics.accuracy
                    self.model_metrics[model_name].confidence_avg = perf_metrics.confidence
                    self.model_metrics[model_name].last_updated = datetime.now()
                    
        except Exception as e:
            self.logger.error(f"Error updating model metrics: {e}")
            
    def _collect_model_metrics(self):
        """Yield model metrics for Prometheus"""
        for model_name, metrics in self.model_metrics.items():
            # Prediction count
            self.model_prediction_count.labels(model_name=model_name).set(metrics.prediction_count)
            yield self.model_prediction_count.labels(model_name=model_name)
            
            # Accuracy
            self.model_accuracy.labels(model_name=model_name).set(metrics.accuracy)
            yield self.model_accuracy.labels(model_name=model_name)
            
            # Latency histogram
            self.model_latency.labels(model_name=model_name).observe(metrics.latency_ms / 1000.0)
            yield self.model_latency.labels(model_name=model_name)
            
            # Error count
            self.model_error_count.labels(model_name=model_name).inc(metrics.error_count)
            yield self.model_error_count.labels(model_name=model_name)
            
            # Confidence
            self.model_confidence.labels(model_name=model_name).set(metrics.confidence_avg)
            yield self.model_confidence.labels(model_name=model_name)
            
            # Memory usage
            self.model_memory_usage.labels(model_name=model_name).set(int(metrics.memory_usage_mb * 1024 * 1024))
            yield self.model_memory_usage.labels(model_name=model_name)
            
            # CPU usage
            self.model_cpu_usage.labels(model_name=model_name).set(metrics.cpu_usage_percent)
            yield self.model_cpu_usage.labels(model_name=model_name)
            
    def _collect_system_metrics(self):
        """Yield system metrics for Prometheus"""
        # Total requests
        self.system_requests_total.inc(self.system_metrics.total_requests)
        yield self.system_requests_total
        
        # Active models
        self.system_active_models.set(self.system_metrics.active_models)
        yield self.system_active_models
        
        # Uptime
        self.system_uptime.set(self.system_metrics.system_uptime_seconds)
        yield self.system_uptime
        
        # Memory
        self.system_memory_total.set(int(self.system_metrics.memory_total_mb * 1024 * 1024))
        yield self.system_memory_total
        
        self.system_memory_available.set(int(self.system_metrics.memory_available_mb * 1024 * 1024))
        yield self.system_memory_available
        
        # CPU
        self.system_cpu_usage.set(self.system_metrics.cpu_usage_percent)
        yield self.system_cpu_usage
        
        # Disk
        self.system_disk_usage.set(self.system_metrics.disk_usage_percent)
        yield self.system_disk_usage
        
        # Network I/O
        self.system_network_io.labels(direction='sent').inc(self.system_metrics.network_io_bytes // 2)
        yield self.system_network_io.labels(direction='sent')
        self.system_network_io.labels(direction='received').inc(self.system_metrics.network_io_bytes // 2)
        yield self.system_network_io.labels(direction='received')
        
    def record_prediction(self, model_name: str, prediction_success: bool, 
                      latency_ms: float, confidence: float = 0.0):
        """Record a prediction event"""
        if model_name not in self.model_metrics:
            self.model_metrics[model_name] = ModelMetrics(model_name=model_name)
            
        metrics = self.model_metrics[model_name]
        metrics.prediction_count += 1
        metrics.last_updated = datetime.now()
        
        if not prediction_success:
            metrics.error_count += 1
        else:
            # Update running average confidence
            total_predictions = metrics.prediction_count
            current_avg_confidence = metrics.confidence_avg
            new_avg_confidence = ((current_avg_confidence * (total_predictions - 1)) + confidence) / total_predictions
            metrics.confidence_avg = new_avg_confidence
            
        # Update latency (running average)
        current_avg_latency = metrics.latency_ms
        new_avg_latency = ((current_avg_latency * (total_predictions - 1)) + latency_ms) / total_predictions
        metrics.latency_ms = new_avg_latency
        
        self.logger.info(f"Recorded prediction for {model_name}: success={prediction_success}, latency={latency_ms:.2f}ms")
        
    def record_model_load(self, model_name: str, memory_mb: float, cpu_percent: float):
        """Record model resource usage"""
        if model_name not in self.model_metrics:
            self.model_metrics[model_name] = ModelMetrics(model_name=model_name)
            
        metrics = self.model_metrics[model_name]
        metrics.memory_usage_mb = memory_mb
        metrics.cpu_usage_percent = cpu_percent
        metrics.last_updated = datetime.now()
        
    def get_model_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all model metrics"""
        return {
            'timestamp': datetime.now().isoformat(),
            'models': {name: asdict(metrics) for name, metrics in self.model_metrics.items()},
            'system': asdict(self.system_metrics)
        }
        
    def reset_metrics(self, model_name: Optional[str] = None):
        """Reset metrics for specific model or all models"""
        if model_name:
            if model_name in self.model_metrics:
                self.model_metrics[model_name] = ModelMetrics(model_name=model_name)
        else:
            self.model_metrics.clear()
            
        self.logger.info(f"Reset metrics for model: {model_name or 'all'}")


class PrometheusMetricsServer:
    """
    Prometheus metrics server for baseball model monitoring
    """
    
    def __init__(self, port: int = 8000, model_registry: Optional[ModelRegistry] = None):
        self.port = port
        self.model_registry = model_registry
        self.collector = None
        self.app = None
        self.logger = logging.getLogger(__name__)
        
    def start(self, model_registry: ModelRegistry):
        """Start the Prometheus metrics server"""
        try:
            self.model_registry = model_registry
            self.collector = PrometheusMetricsCollector(model_registry)
            
            # Create custom registry
            registry = CollectorRegistry()
            registry.register(self.collector)
            
            # Start HTTP server
            start_http_server(self.port, registry)
            self.logger.info(f"Prometheus metrics server started on port {self.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start Prometheus server: {e}")
            raise
            
    def stop(self):
        """Stop the Prometheus metrics server"""
        # Note: prometheus_client doesn't provide a clean stop method
        # In production, you'd typically use a proper WSGI server
        self.logger.info("Prometheus metrics server stopped")
        
    def get_metrics_collector(self) -> PrometheusMetricsCollector:
        """Get the metrics collector instance"""
        return self.collector
