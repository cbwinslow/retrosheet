"""
Health Check System for Multi-Model Ensemble

Provides comprehensive health monitoring for models, database connectivity,
external dependencies, and automated failover capabilities.
"""

import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import aiohttp
import psutil

from baseball.models.base import BaseModel
from baseball.models.registry import ModelRegistry


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time_ms: float
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['status'] = self.status.value
        result['timestamp'] = self.timestamp.isoformat()
        return result


@dataclass
class ComponentHealth:
    """Health status for a component"""
    component_name: str
    current_status: HealthStatus
    last_check: datetime
    consecutive_failures: int = 0
    last_success: Optional[datetime] = None
    failure_threshold: int = 3
    recovery_threshold: int = 2
    
    def is_healthy(self) -> bool:
        """Check if component is considered healthy"""
        return (self.current_status == HealthStatus.HEALTHY and 
                self.consecutive_failures < self.failure_threshold)
                
    def should_failover(self) -> bool:
        """Check if failover should be triggered"""
        return self.consecutive_failures >= self.failure_threshold


class HealthChecker:
    """
    Comprehensive health checking system for baseball model ensemble
    """
    
    def __init__(self, model_registry: ModelRegistry, check_interval_seconds: int = 30):
        self.model_registry = model_registry
        self.check_interval = check_interval_seconds
        self.component_health: Dict[str, ComponentHealth] = {}
        self.health_checks: Dict[str, Callable] = {}
        self.failover_handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger(__name__)
        self._running = False
        self._check_task = None
        
        # Register default health checks
        self._register_default_checks()
        
    def _register_default_checks(self):
        """Register default health checks"""
        self.health_checks.update({
            'model_registry': self._check_model_registry,
            'database': self._check_database,
            'external_apis': self._check_external_apis,
            'system_resources': self._check_system_resources,
            'individual_models': self._check_individual_models
        })
        
        # Initialize component health tracking
        for component in self.health_checks.keys():
            self.component_health[component] = ComponentHealth(
                component_name=component,
                current_status=HealthStatus.UNKNOWN,
                last_check=datetime.now()
            )
            
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        if self._running:
            self.logger.warning("Health monitoring already running")
            return
            
        self._running = True
        self._check_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Health monitoring started")
        
    async def stop_monitoring(self):
        """Stop continuous health monitoring"""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Health monitoring stopped")
        
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._run_health_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
                
    async def _run_health_checks(self):
        """Run all registered health checks"""
        tasks = []
        for component, check_func in self.health_checks.items():
            task = asyncio.create_task(self._run_single_check(component, check_func))
            tasks.append(task)
            
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle failovers
            for i, result in enumerate(results):
                component = list(self.health_checks.keys())[i]
                if isinstance(result, Exception):
                    self.logger.error(f"Health check failed for {component}: {result}")
                    await self._handle_check_failure(component, str(result))
                else:
                    await self._process_health_result(component, result)
                    
    async def _run_single_check(self, component: str, check_func: Callable) -> HealthCheckResult:
        """Run a single health check"""
        start_time = time.time()
        try:
            result = await check_func()
            response_time = (time.time() - start_time) * 1000
            
            if isinstance(result, HealthCheckResult):
                result.response_time_ms = response_time
                return result
            else:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.HEALTHY,
                    message="Health check passed",
                    timestamp=datetime.now(),
                    response_time_ms=response_time
                )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                timestamp=datetime.now(),
                response_time_ms=response_time
            )
            
    async def _process_health_result(self, component: str, result: HealthCheckResult):
        """Process health check result"""
        health = self.component_health[component]
        previous_status = health.current_status
        
        # Update health status
        health.current_status = result.status
        health.last_check = result.timestamp
        
        # Update failure counts
        if result.status == HealthStatus.HEALTHY:
            health.consecutive_failures = 0
            health.last_success = result.timestamp
        else:
            health.consecutive_failures += 1
            
        # Check for status changes
        if previous_status != result.status:
            self.logger.info(f"Health status changed for {component}: {previous_status.value} -> {result.status.value}")
            
        # Check for failover conditions
        if health.should_failover():
            await self._trigger_failover(component, result)
            
        # Check for recovery
        elif (previous_status in [HealthStatus.UNHEALTHY, HealthStatus.DEGRADED] and 
              result.status == HealthStatus.HEALTHY and 
              health.consecutive_failures == 0):
            await self._trigger_recovery(component, result)
            
    async def _handle_check_failure(self, component: str, error_message: str):
        """Handle health check execution failure"""
        health = self.component_health[component]
        health.consecutive_failures += 1
        health.last_check = datetime.now()
        
        result = HealthCheckResult(
            component=component,
            status=HealthStatus.UNHEALTHY,
            message=f"Health check failed: {error_message}",
            timestamp=datetime.now(),
            response_time_ms=0.0
        )
        
        await self._trigger_failover(component, result)
        
    async def _trigger_failover(self, component: str, result: HealthCheckResult):
        """Trigger failover for unhealthy component"""
        self.logger.error(f"Triggering failover for {component}: {result.message}")
        
        if component in self.failover_handlers:
            try:
                await self.failover_handlers[component](result)
            except Exception as e:
                self.logger.error(f"Failover handler failed for {component}: {e}")
                
    async def _trigger_recovery(self, component: str, result: HealthCheckResult):
        """Trigger recovery for recovered component"""
        self.logger.info(f"Component {component} recovered: {result.message}")
        
        # Could implement recovery handlers here
        # For now, just log the recovery
        
    async def _check_model_registry(self) -> HealthCheckResult:
        """Check model registry health"""
        try:
            models = self.model_registry.get_all_models()
            active_count = len([m for m in models.values() if m.get('healthy', True)])
            total_count = len(models)
            
            if active_count == 0:
                return HealthCheckResult(
                    component='model_registry',
                    status=HealthStatus.UNHEALTHY,
                    message="No active models in registry",
                    timestamp=datetime.now(),
                    response_time_ms=0.0,
                    details={'active_models': active_count, 'total_models': total_count}
                )
            elif active_count < total_count * 0.8:  # Less than 80% active
                return HealthCheckResult(
                    component='model_registry',
                    status=HealthStatus.DEGRADED,
                    message=f"Only {active_count}/{total_count} models active",
                    timestamp=datetime.now(),
                    response_time_ms=0.0,
                    details={'active_models': active_count, 'total_models': total_count}
                )
            else:
                return HealthCheckResult(
                    component='model_registry',
                    status=HealthStatus.HEALTHY,
                    message=f"{active_count}/{total_count} models active",
                    timestamp=datetime.now(),
                    response_time_ms=0.0,
                    details={'active_models': active_count, 'total_models': total_count}
                )
        except Exception as e:
            return HealthCheckResult(
                component='model_registry',
                status=HealthStatus.UNHEALTHY,
                message=f"Registry check failed: {str(e)}",
                timestamp=datetime.now(),
                response_time_ms=0.0
            )
            
    async def _check_database(self) -> HealthCheckResult:
        """Check database connectivity"""
        try:
            # This would be implemented based on your database setup
            # For now, simulate a database check
            start_time = time.time()
            
            # Simulate database query
            await asyncio.sleep(0.01)  # Simulate 10ms query time
            
            response_time = (time.time() - start_time) * 1000
            
            if response_time > 1000:  # > 1 second
                status = HealthStatus.DEGRADED
                message = f"Database response slow: {response_time:.2f}ms"
            else:
                status = HealthStatus.HEALTHY
                message = f"Database responsive: {response_time:.2f}ms"
                
            return HealthCheckResult(
                component='database',
                status=status,
                message=message,
                timestamp=datetime.now(),
                response_time_ms=response_time,
                details={'response_time_ms': response_time}
            )
        except Exception as e:
            return HealthCheckResult(
                component='database',
                status=HealthStatus.UNHEALTHY,
                message=f"Database check failed: {str(e)}",
                timestamp=datetime.now(),
                response_time_ms=0.0
            )
            
    async def _check_external_apis(self) -> HealthCheckResult:
        """Check external API dependencies"""
        try:
            # Check MLB API, ESPN API, etc.
            apis_to_check = [
                {'name': 'MLB API', 'url': 'https://statsapi.mlb.com/api/v1/schedule'},
                {'name': 'ESPN API', 'url': 'https://site.web.api.espn.com/apis/config'}
            ]
            
            results = []
            total_response_time = 0
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                for api in apis_to_check:
                    start_time = time.time()
                    try:
                        async with session.get(api['url']) as response:
                            response_time = (time.time() - start_time) * 1000
                            total_response_time += response_time
                            
                            if response.status == 200:
                                results.append({'name': api['name'], 'status': 'healthy', 'response_time': response_time})
                            else:
                                results.append({'name': api['name'], 'status': 'unhealthy', 'response_time': response_time})
                    except Exception as e:
                        results.append({'name': api['name'], 'status': 'error', 'error': str(e)})
                        
            avg_response_time = total_response_time / len(apis_to_check) if apis_to_check else 0
            
            healthy_count = len([r for r in results if r['status'] == 'healthy'])
            
            if healthy_count == 0:
                status = HealthStatus.UNHEALTHY
                message = "All external APIs unavailable"
            elif healthy_count < len(apis_to_check):
                status = HealthStatus.DEGRADED
                message = f"{healthy_count}/{len(apis_to_check)} APIs available"
            else:
                status = HealthStatus.HEALTHY
                message = "All external APIs available"
                
            return HealthCheckResult(
                component='external_apis',
                status=status,
                message=message,
                timestamp=datetime.now(),
                response_time_ms=avg_response_time,
                details={'api_results': results, 'healthy_count': healthy_count}
            )
        except Exception as e:
            return HealthCheckResult(
                component='external_apis',
                status=HealthStatus.UNHEALTHY,
                message=f"External API check failed: {str(e)}",
                timestamp=datetime.now(),
                response_time_ms=0.0
            )
            
    async def _check_system_resources(self) -> HealthCheckResult:
        """Check system resource usage"""
        try:
            # Memory check
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage('/')
            
            issues = []
            
            if memory.percent > 90:
                issues.append(f"High memory usage: {memory.percent:.1f}%")
            elif memory.percent > 80:
                issues.append(f"Elevated memory usage: {memory.percent:.1f}%")
                
            if cpu_percent > 90:
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            elif cpu_percent > 80:
                issues.append(f"Elevated CPU usage: {cpu_percent:.1f}%")
                
            if disk.percent > 90:
                issues.append(f"High disk usage: {disk.percent:.1f}%")
            elif disk.percent > 80:
                issues.append(f"Elevated disk usage: {disk.percent:.1f}%")
                
            if not issues:
                status = HealthStatus.HEALTHY
                message = "System resources normal"
            elif len(issues) == 1 and "Elevated" in issues[0]:
                status = HealthStatus.DEGRADED
                message = issues[0]
            else:
                status = HealthStatus.UNHEALTHY
                message = "; ".join(issues)
                
            return HealthCheckResult(
                component='system_resources',
                status=status,
                message=message,
                timestamp=datetime.now(),
                response_time_ms=0.0,
                details={
                    'memory_percent': memory.percent,
                    'cpu_percent': cpu_percent,
                    'disk_percent': disk.percent,
                    'issues': issues
                }
            )
        except Exception as e:
            return HealthCheckResult(
                component='system_resources',
                status=HealthStatus.UNHEALTHY,
                message=f"System resource check failed: {str(e)}",
                timestamp=datetime.now(),
                response_time_ms=0.0
            )
            
    async def _check_individual_models(self) -> HealthCheckResult:
        """Check individual model health"""
        try:
            models = self.model_registry.get_all_models()
            model_results = []
            
            for model_name, model_info in models.items():
                try:
                    model_instance = self.model_registry.get_model(model_name)
                    if model_instance:
                        # Simulate model health check
                        # In real implementation, this would call model.health_check()
                        model_results.append({
                            'name': model_name,
                            'status': 'healthy',
                            'type': model_info.get('type', 'unknown')
                        })
                    else:
                        model_results.append({
                            'name': model_name,
                            'status': 'unavailable',
                            'type': model_info.get('type', 'unknown')
                        })
                except Exception as e:
                    model_results.append({
                        'name': model_name,
                        'status': 'error',
                        'error': str(e),
                        'type': model_info.get('type', 'unknown')
                    })
                    
            healthy_count = len([r for r in model_results if r['status'] == 'healthy'])
            total_count = len(model_results)
            
            if healthy_count == 0:
                status = HealthStatus.UNHEALTHY
                message = "No models healthy"
            elif healthy_count < total_count * 0.8:
                status = HealthStatus.DEGRADED
                message = f"{healthy_count}/{total_count} models healthy"
            else:
                status = HealthStatus.HEALTHY
                message = f"{healthy_count}/{total_count} models healthy"
                
            return HealthCheckResult(
                component='individual_models',
                status=status,
                message=message,
                timestamp=datetime.now(),
                response_time_ms=0.0,
                details={
                    'model_results': model_results,
                    'healthy_count': healthy_count,
                    'total_count': total_count
                }
            )
        except Exception as e:
            return HealthCheckResult(
                component='individual_models',
                status=HealthStatus.UNHEALTHY,
                message=f"Model health check failed: {str(e)}",
                timestamp=datetime.now(),
                response_time_ms=0.0
            )
            
    def register_health_check(self, component: str, check_func: Callable):
        """Register a custom health check"""
        self.health_checks[component] = check_func
        
        if component not in self.component_health:
            self.component_health[component] = ComponentHealth(
                component_name=component,
                current_status=HealthStatus.UNKNOWN,
                last_check=datetime.now()
            )
            
    def register_failover_handler(self, component: str, handler_func: Callable):
        """Register a failover handler for a component"""
        self.failover_handlers[component] = handler_func
        
    async def run_health_check(self, component: str) -> HealthCheckResult:
        """Run a specific health check"""
        if component not in self.health_checks:
            raise ValueError(f"Unknown health check component: {component}")
            
        return await self._run_single_check(component, self.health_checks[component])
        
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        component_statuses = {name: health.current_status.value 
                            for name, health in self.component_health.items()}
        
        # Determine overall status
        if all(status == HealthStatus.HEALTHY.value for status in component_statuses.values()):
            overall_status = HealthStatus.HEALTHY.value
        elif any(status == HealthStatus.UNHEALTHY.value for status in component_statuses.values()):
            overall_status = HealthStatus.UNHEALTHY.value
        else:
            overall_status = HealthStatus.DEGRADED.value
            
        return {
            'overall_status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'components': component_statuses,
            'component_details': {
                name: {
                    'status': health.current_status.value,
                    'last_check': health.last_check.isoformat(),
                    'consecutive_failures': health.consecutive_failures,
                    'last_success': health.last_success.isoformat() if health.last_success else None,
                    'is_healthy': health.is_healthy()
                }
                for name, health in self.component_health.items()
            }
        }
        
    def get_health_summary(self) -> str:
        """Get a human-readable health summary"""
        overall_health = self.get_overall_health()
        status = overall_health['overall_status'].upper()
        
        summary_lines = [f"System Status: {status}"]
        summary_lines.append(f"Checked at: {overall_health['timestamp']}")
        summary_lines.append("")
        
        for component, health in self.component_health.items():
            status_icon = "✓" if health.is_healthy() else "✗"
            summary_lines.append(f"{status_icon} {component}: {health.current_status.value}")
            
            if health.consecutive_failures > 0:
                summary_lines.append(f"   Failures: {health.consecutive_failures}")
                
        return "\n".join(summary_lines)
