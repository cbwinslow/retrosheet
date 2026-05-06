"""
Alert Manager for Multi-Model Ensemble System

Provides comprehensive alerting with threshold-based rules,
anomaly detection, and multi-channel notification support.
"""

import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
import statistics

from .health_checks import HealthStatus, HealthCheckResult


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertType(Enum):
    """Alert types"""
    THRESHOLD = "threshold"
    ANOMALY = "anomaly"
    HEALTH_CHECK = "health_check"
    PERFORMANCE = "performance"
    SYSTEM = "system"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    type: AlertType
    severity: AlertSeverity
    component: str
    title: str
    message: str
    timestamp: datetime
    details: Dict[str, Any] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['type'] = self.type.value
        result['severity'] = self.severity.value
        result['timestamp'] = self.timestamp.isoformat()
        if self.acknowledged_at:
            result['acknowledged_at'] = self.acknowledged_at.isoformat()
        if self.resolved_at:
            result['resolved_at'] = self.resolved_at.isoformat()
        return result


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    component: str
    metric: str
    operator: str  # >, <, ==, !=, etc.
    threshold: float
    severity: AlertSeverity
    enabled: bool = True
    consecutive_violations: int = 1
    cooldown_minutes: int = 5
    last_triggered: Optional[datetime] = None
    violation_count: int = 0
    
    def should_trigger(self, current_value: float) -> bool:
        """Check if rule should trigger"""
        if not self.enabled:
            return False
            
        # Check cooldown
        if (self.last_triggered and 
            datetime.now() - self.last_triggered < timedelta(minutes=self.cooldown_minutes)):
            return False
            
        # Check threshold
        if self.operator == '>':
            return current_value > self.threshold
        elif self.operator == '<':
            return current_value < self.threshold
        elif self.operator == '>=':
            return current_value >= self.threshold
        elif self.operator == '<=':
            return current_value <= self.threshold
        elif self.operator == '==':
            return current_value == self.threshold
        elif self.operator == '!=':
            return current_value != self.threshold
        else:
            return False
            
    def trigger(self) -> bool:
        """Mark rule as triggered"""
        self.violation_count += 1
        self.last_triggered = datetime.now()
        return self.violation_count >= self.consecutive_violations
        
    def reset(self):
        """Reset rule violation count"""
        self.violation_count = 0


class NotificationChannel:
    """Base class for notification channels"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert notification"""
        raise NotImplementedError
        
    async def test_connection(self) -> bool:
        """Test notification channel connectivity"""
        raise NotImplementedError


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel"""
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via email"""
        try:
            smtp_server = self.config.get('smtp_server', 'localhost')
            smtp_port = self.config.get('smtp_port', 587)
            username = self.config.get('username', '')
            password = self.config.get('password', '')
            from_email = self.config.get('from_email', '')
            to_emails = self.config.get('to_emails', [])
            
            if not to_emails:
                self.logger.error("No recipient emails configured")
                return False
                
            # Create message
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            
            # Create email body
            body = self._format_email_body(alert)
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Alert sent via email: {alert.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
            return False
            
    def _format_email_body(self, alert: Alert) -> str:
        """Format alert for email"""
        body_lines = [
            f"ALERT: {alert.title}",
            f"Severity: {alert.severity.value.upper()}",
            f"Component: {alert.component}",
            f"Time: {alert.timestamp.isoformat()}",
            f"",
            f"Message: {alert.message}",
            f""
        ]
        
        if alert.details:
            body_lines.append("Details:")
            for key, value in alert.details.items():
                body_lines.append(f"  {key}: {value}")
                
        body_lines.extend([
            f"",
            f"Alert ID: {alert.id}",
            f"---",
            f"Baseball Monitoring System"
        ])
        
        return "\n".join(body_lines)
        
    async def test_connection(self) -> bool:
        """Test email connectivity"""
        try:
            smtp_server = self.config.get('smtp_server', 'localhost')
            smtp_port = self.config.get('smtp_port', 587)
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.quit()
            return True
        except Exception as e:
            self.logger.error(f"Email connection test failed: {e}")
            return False


class SlackNotificationChannel(NotificationChannel):
    """Slack webhook notification channel"""
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via Slack webhook"""
        try:
            webhook_url = self.config.get('webhook_url')
            if not webhook_url:
                self.logger.error("No Slack webhook URL configured")
                return False
                
            # Format message for Slack
            payload = self._format_slack_message(alert)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"Alert sent via Slack: {alert.id}")
                        return True
                    else:
                        self.logger.error(f"Slack webhook failed: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")
            return False
            
    def _format_slack_message(self, alert: Alert) -> Dict[str, Any]:
        """Format alert for Slack"""
        color_map = {
            AlertSeverity.CRITICAL: "danger",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.INFO: "good"
        }
        
        attachment = {
            "color": color_map.get(alert.severity, "warning"),
            "title": alert.title,
            "text": alert.message,
            "fields": [
                {"title": "Component", "value": alert.component, "short": True},
                {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                {"title": "Time", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "short": True},
                {"title": "Alert ID", "value": alert.id, "short": True}
            ],
            "footer": "Baseball Monitoring System",
            "ts": int(alert.timestamp.timestamp())
        }
        
        if alert.details:
            for key, value in alert.details.items():
                attachment["fields"].append({
                    "title": key,
                    "value": str(value),
                    "short": True
                })
                
        return {"attachments": [attachment]}
        
    async def test_connection(self) -> bool:
        """Test Slack webhook connectivity"""
        try:
            webhook_url = self.config.get('webhook_url')
            if not webhook_url:
                return False
                
            test_payload = {
                "text": "🧪 Test message from Baseball Monitoring System",
                "attachments": [{
                    "color": "good",
                    "title": "Connection Test",
                    "text": "Slack notification channel is working correctly"
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=test_payload, timeout=10) as response:
                    return response.status == 200
                    
        except Exception as e:
            self.logger.error(f"Slack connection test failed: {e}")
            return False


class AlertManager:
    """
    Comprehensive alert management system
    """
    
    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.rules: Dict[str, AlertRule] = {}
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self.anomaly_detectors: Dict[str, Callable] = {}
        self.logger = logging.getLogger(__name__)
        self._running = False
        self._alert_task = None
        
        # Initialize default rules
        self._init_default_rules()
        
    def _init_default_rules(self):
        """Initialize default alert rules"""
        default_rules = [
            AlertRule(
                name="model_accuracy_critical",
                component="models",
                metric="accuracy",
                operator="<",
                threshold=60.0,
                severity=AlertSeverity.CRITICAL,
                consecutive_violations=2
            ),
            AlertRule(
                name="model_accuracy_warning",
                component="models",
                metric="accuracy",
                operator="<",
                threshold=70.0,
                severity=AlertSeverity.WARNING,
                consecutive_violations=3
            ),
            AlertRule(
                name="prediction_latency_critical",
                component="models",
                metric="latency_ms",
                operator=">",
                threshold=500.0,
                severity=AlertSeverity.CRITICAL,
                consecutive_violations=2
            ),
            AlertRule(
                name="prediction_latency_warning",
                component="models",
                metric="latency_ms",
                operator=">",
                threshold=200.0,
                severity=AlertSeverity.WARNING,
                consecutive_violations=3
            ),
            AlertRule(
                name="error_rate_critical",
                component="system",
                metric="error_rate",
                operator=">",
                threshold=5.0,
                severity=AlertSeverity.CRITICAL,
                consecutive_violations=1
            ),
            AlertRule(
                name="system_cpu_high",
                component="system",
                metric="cpu_percent",
                operator=">",
                threshold=90.0,
                severity=AlertSeverity.WARNING,
                consecutive_violations=5,
                cooldown_minutes=10
            ),
            AlertRule(
                name="system_memory_high",
                component="system",
                metric="memory_percent",
                operator=">",
                threshold=90.0,
                severity=AlertSeverity.WARNING,
                consecutive_violations=5,
                cooldown_minutes=10
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.name] = rule
            
    def add_notification_channel(self, channel: NotificationChannel):
        """Add a notification channel"""
        self.notification_channels[channel.name] = channel
        self.logger.info(f"Added notification channel: {channel.name}")
        
    def add_alert_rule(self, rule: AlertRule):
        """Add an alert rule"""
        self.rules[rule.name] = rule
        self.logger.info(f"Added alert rule: {rule.name}")
        
    def add_anomaly_detector(self, name: str, detector: Callable):
        """Add an anomaly detector"""
        self.anomaly_detectors[name] = detector
        self.logger.info(f"Added anomaly detector: {name}")
        
    async def start_monitoring(self):
        """Start alert monitoring"""
        if self._running:
            self.logger.warning("Alert monitoring already running")
            return
            
        self._running = True
        self._alert_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Alert monitoring started")
        
    async def stop_monitoring(self):
        """Stop alert monitoring"""
        self._running = False
        if self._alert_task:
            self._alert_task.cancel()
            try:
                await self._alert_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Alert monitoring stopped")
        
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._check_alert_rules()
                await self._run_anomaly_detectors()
                await self._cleanup_old_alerts()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in alert monitoring loop: {e}")
                await asyncio.sleep(30)
                
    async def _check_alert_rules(self):
        """Check all alert rules"""
        # This would be called with current metrics from the metrics collector
        # For now, simulate with some values
        pass
        
    async def _run_anomaly_detectors(self):
        """Run all anomaly detectors"""
        for name, detector in self.anomaly_detectors.items():
            try:
                anomalies = await detector()
                if anomalies:
                    for anomaly in anomalies:
                        await self.create_alert(
                            type=AlertType.ANOMALY,
                            severity=AlertSeverity.WARNING,
                            component=anomaly.get('component', 'unknown'),
                            title=f"Anomaly detected by {name}",
                            message=anomaly.get('message', 'Unknown anomaly'),
                            details=anomaly.get('details', {})
                        )
            except Exception as e:
                self.logger.error(f"Anomaly detector {name} failed: {e}")
                
    async def _cleanup_old_alerts(self):
        """Clean up old resolved alerts"""
        cutoff_time = datetime.now() - timedelta(days=7)
        old_alerts = [
            alert_id for alert_id, alert in self.alerts.items()
            if alert.resolved and alert.resolved_at and alert.resolved_at < cutoff_time
        ]
        
        for alert_id in old_alerts:
            del self.alerts[alert_id]
            self.logger.debug(f"Cleaned up old alert: {alert_id}")
            
    async def create_alert(self, type: AlertType, severity: AlertSeverity,
                        component: str, title: str, message: str,
                        details: Optional[Dict[str, Any]] = None) -> Alert:
        """Create and send a new alert"""
        alert_id = f"{int(time.time())}_{component}_{len(self.alerts)}"
        
        alert = Alert(
            id=alert_id,
            type=type,
            severity=severity,
            component=component,
            title=title,
            message=message,
            timestamp=datetime.now(),
            details=details or {}
        )
        
        self.alerts[alert_id] = alert
        
        # Send notifications
        await self._send_notifications(alert)
        
        # Log alert
        self.logger.warning(f"ALERT CREATED [{severity.value.upper()}] {title}: {message}")
        
        return alert
        
    async def _send_notifications(self, alert: Alert):
        """Send alert to all notification channels"""
        tasks = []
        for channel in self.notification_channels.values():
            task = asyncio.create_task(channel.send_alert(alert))
            tasks.append(task)
            
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = sum(1 for r in results if r is True)
            total_count = len(results)
            
            self.logger.info(f"Alert {alert.id} sent to {success_count}/{total_count} notification channels")
            
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        if alert_id not in self.alerts:
            return False
            
        alert = self.alerts[alert_id]
        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.now()
        
        self.logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return True
        
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id not in self.alerts:
            return False
            
        alert = self.alerts[alert_id]
        alert.resolved = True
        alert.resolved_at = datetime.now()
        
        self.logger.info(f"Alert {alert_id} resolved")
        return True
        
    def get_active_alerts(self) -> List[Alert]:
        """Get all active (unresolved) alerts"""
        return [alert for alert in self.alerts.values() if not alert.resolved]
        
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity level"""
        return [alert for alert in self.alerts.values() 
                if alert.severity == severity and not alert.resolved]
                
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of all alerts"""
        active_alerts = self.get_active_alerts()
        
        severity_counts = {}
        for severity in AlertSeverity:
            severity_counts[severity.value] = len([
                alert for alert in active_alerts if alert.severity == severity
            ])
            
        return {
            'timestamp': datetime.now().isoformat(),
            'total_active_alerts': len(active_alerts),
            'severity_breakdown': severity_counts,
            'recent_alerts': [
                alert.to_dict() for alert in 
                sorted(active_alerts, key=lambda a: a.timestamp, reverse=True)[:10]
            ]
        }
        
    async def check_metric_thresholds(self, metrics: Dict[str, Any]):
        """Check metrics against alert rules"""
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue
                
            component_metrics = metrics.get(rule.component, {})
            current_value = component_metrics.get(rule.metric)
            
            if current_value is None:
                continue
                
            if rule.should_trigger(current_value):
                if rule.trigger():
                    await self.create_alert(
                        type=AlertType.THRESHOLD,
                        severity=rule.severity,
                        component=rule.component,
                        title=f"Threshold violation: {rule.name}",
                        message=f"{rule.metric} {rule.operator} {rule.threshold} (current: {current_value})",
                        details={
                            'rule_name': rule.name,
                            'current_value': current_value,
                            'threshold': rule.threshold,
                            'operator': rule.operator,
                            'violation_count': rule.violation_count
                        }
                    )
            else:
                rule.reset()
