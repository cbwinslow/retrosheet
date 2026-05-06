"""
Metrics Collector for Multi-Model Ensemble System

Provides real-time model performance tracking, confidence distribution analysis,
feature importance drift detection, and model comparison metrics.
"""

import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import statistics
from collections import defaultdict, deque

from baseball.models.base import BaseModel
from baseball.models.registry import ModelRegistry


class MetricType(Enum):
    """Types of metrics collected"""
    ACCURACY = "accuracy"
    LATENCY = "latency"
    CONFIDENCE = "confidence"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"
    FEATURE_IMPORTANCE = "feature_importance"
    PREDICTION_DISTRIBUTION = "prediction_distribution"


@dataclass
class MetricValue:
    """Individual metric value with timestamp"""
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


@dataclass
class ModelPerformanceMetrics:
    """Comprehensive performance metrics for a model"""
    model_name: str
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    avg_confidence: float = 0.0
    avg_latency_ms: float = 0.0
    throughput_per_second: float = 0.0
    error_rate: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    last_updated: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['last_updated'] = self.last_updated.isoformat() if self.last_updated else None
        return result


class MetricsCollector:
    """
    Comprehensive metrics collection and analysis system
    """
    
    def __init__(self, model_registry: ModelRegistry, history_hours: int = 24):
        self.model_registry = model_registry
        self.history_hours = history_hours
        self.metrics_history: Dict[str, Dict[MetricType, deque]] = defaultdict(lambda: defaultdict(deque))
        self.performance_metrics: Dict[str, ModelPerformanceMetrics] = {}
        self.prediction_buffer: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.logger = logging.getLogger(__name__)
        self._running = False
        self._collection_task = None
        
        # Initialize performance metrics for all models
        self._initialize_model_metrics()
        
    def _initialize_model_metrics(self):
        """Initialize performance metrics for all registered models"""
        models = self.model_registry.get_all_models()
        for model_name in models.keys():
            self.performance_metrics[model_name] = ModelPerformanceMetrics(model_name=model_name)
            
    async def start_collection(self):
        """Start continuous metrics collection"""
        if self._running:
            self.logger.warning("Metrics collection already running")
            return
            
        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        self.logger.info("Metrics collection started")
        
    async def stop_collection(self):
        """Stop metrics collection"""
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Metrics collection stopped")
        
    async def _collection_loop(self):
        """Main collection loop"""
        while self._running:
            try:
                await self._collect_model_metrics()
                await self._cleanup_old_data()
                await asyncio.sleep(60)  # Collect every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(60)
                
    async def _collect_model_metrics(self):
        """Collect metrics from all models"""
        models = self.model_registry.get_all_models()
        
        for model_name, model_info in models.items():
            try:
                model_instance = self.model_registry.get_model(model_name)
                if model_instance and hasattr(model_instance, 'get_performance_metrics'):
                    perf_metrics = model_instance.get_performance_metrics()
                    
                    # Update performance metrics
                    current_metrics = self.performance_metrics[model_name]
                    current_metrics.accuracy = perf_metrics.accuracy
                    current_metrics.avg_confidence = perf_metrics.confidence
                    current_metrics.last_updated = datetime.now()
                    
                    # Record metric values
                    self._record_metric(model_name, MetricType.ACCURACY, perf_metrics.accuracy)
                    self._record_metric(model_name, MetricType.CONFIDENCE, perf_metrics.confidence)
                    
            except Exception as e:
                self.logger.error(f"Failed to collect metrics for {model_name}: {e}")
                
    def _record_metric(self, model_name: str, metric_type: MetricType, value: float, metadata: Optional[Dict[str, Any]] = None):
        """Record a metric value"""
        metric_value = MetricValue(
            value=value,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.metrics_history[model_name][metric_type].append(metric_value)
        
        # Keep only recent history
        cutoff_time = datetime.now() - timedelta(hours=self.history_hours)
        while (self.metrics_history[model_name][metric_type] and
               self.metrics_history[model_name][metric_type][0].timestamp < cutoff_time):
            self.metrics_history[model_name][metric_type].popleft()
            
    def record_prediction(self, model_name: str, prediction_result: Dict[str, Any]):
        """Record a prediction result"""
        prediction_data = {
            'timestamp': datetime.now(),
            'success': prediction_result.get('success', True),
            'confidence': prediction_result.get('confidence', 0.0),
            'latency_ms': prediction_result.get('latency_ms', 0.0),
            'predicted_class': prediction_result.get('predicted_class'),
            'actual_class': prediction_result.get('actual_class'),
            'features': prediction_result.get('features', {})
        }
        
        self.prediction_buffer[model_name].append(prediction_data)
        
        # Update performance metrics
        self._update_performance_from_predictions(model_name)
        
    def _update_performance_from_predictions(self, model_name: str):
        """Update performance metrics from prediction buffer"""
        predictions = list(self.prediction_buffer[model_name])
        if not predictions:
            return
            
        # Calculate basic metrics
        recent_predictions = predictions[-100:]  # Last 100 predictions
        
        # Accuracy
        correct_predictions = sum(1 for p in recent_predictions 
                                if p.get('actual_class') and p.get('predicted_class') == p.get('actual_class'))
        total_predictions = len([p for p in recent_predictions if p.get('actual_class')])
        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.0
        
        # Average confidence
        confidences = [p.get('confidence', 0.0) for p in recent_predictions]
        avg_confidence = statistics.mean(confidences) if confidences else 0.0
        
        # Average latency
        latencies = [p.get('latency_ms', 0.0) for p in recent_predictions]
        avg_latency = statistics.mean(latencies) if latencies else 0.0
        
        # Error rate
        errors = sum(1 for p in recent_predictions if not p.get('success', True))
        error_rate = errors / len(recent_predictions) if recent_predictions else 0.0
        
        # Throughput (predictions per second over last minute)
        one_minute_ago = datetime.now() - timedelta(minutes=1)
        recent_predictions_minute = [p for p in recent_predictions if p['timestamp'] > one_minute_ago]
        throughput = len(recent_predictions_minute) / 60.0 if recent_predictions_minute else 0.0
        
        # Update metrics
        metrics = self.performance_metrics[model_name]
        metrics.accuracy = accuracy
        metrics.avg_confidence = avg_confidence
        metrics.avg_latency_ms = avg_latency
        metrics.error_rate = error_rate
        metrics.throughput_per_second = throughput
        metrics.last_updated = datetime.now()
        
        # Record metrics for trend analysis
        self._record_metric(model_name, MetricType.ACCURACY, accuracy)
        self._record_metric(model_name, MetricType.CONFIDENCE, avg_confidence)
        self._record_metric(model_name, MetricType.LATENCY, avg_latency)
        self._record_metric(model_name, MetricType.ERROR_RATE, error_rate)
        self._record_metric(model_name, MetricType.THROUGHPUT, throughput)
        
    def get_model_metrics(self, model_name: str) -> Optional[ModelPerformanceMetrics]:
        """Get current metrics for a specific model"""
        return self.performance_metrics.get(model_name)
        
    def get_comprehensive_report(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive metrics report"""
        timestamp = datetime.now()
        
        if model_name:
            # Single model report
            metrics = self.performance_metrics.get(model_name)
            if not metrics:
                return {'error': f'Model {model_name} not found'}
                
            report = {
                'model_name': model_name,
                'timestamp': timestamp.isoformat(),
                'current_metrics': metrics.to_dict(),
                'prediction_distribution': self.get_prediction_distribution(model_name)
            }
                    
        else:
            # All models report
            report = {
                'timestamp': timestamp.isoformat(),
                'models': {},
                'system_overview': {
                    'total_models': len(self.performance_metrics),
                    'active_models': len([m for m in self.performance_metrics.values() if m.last_updated]),
                    'total_predictions': sum(len(buffer) for buffer in self.prediction_buffer.values())
                }
            }
            
            # Add individual model reports
            for model_name in self.performance_metrics.keys():
                model_report = self.get_comprehensive_report(model_name)
                if 'error' not in model_report:
                    report['models'][model_name] = model_report
                    
        return report
        
    def get_prediction_distribution(self, model_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get prediction distribution analysis"""
        predictions = list(self.prediction_buffer[model_name])
        
        if not predictions:
            return {}
            
        # Filter by time period
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_predictions = [p for p in predictions if p['timestamp'] > cutoff_time]
        
        if not recent_predictions:
            return {}
            
        # Analyze confidence distribution
        confidences = [p.get('confidence', 0.0) for p in recent_predictions]
        
        # Calculate statistics
        distribution_stats = {
            'total_predictions': len(recent_predictions),
            'confidence_stats': {
                'mean': statistics.mean(confidences) if confidences else 0.0,
                'median': statistics.median(confidences) if confidences else 0.0,
                'std': statistics.stdev(confidences) if len(confidences) > 1 else 0.0,
                'min': min(confidences) if confidences else 0.0,
                'max': max(confidences) if confidences else 0.0
            },
            'time_period_hours': hours,
            'timestamp': datetime.now().isoformat()
        }
        
        return distribution_stats
        
    async def _cleanup_old_data(self):
        """Clean up old data to prevent memory leaks"""
        cutoff_time = datetime.now() - timedelta(hours=self.history_hours)
        
        # Clean up metrics history
        for model_name in list(self.metrics_history.keys()):
            for metric_type in list(self.metrics_history[model_name].keys()):
                history = self.metrics_history[model_name][metric_type]
                while history and history[0].timestamp < cutoff_time:
                    history.popleft()
                    
                if not history:
                    del self.metrics_history[model_name][metric_type]
                    
            if not self.metrics_history[model_name]:
                del self.metrics_history[model_name]
