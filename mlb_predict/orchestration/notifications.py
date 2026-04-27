"""Notification system for pipeline events.

Supports multiple notification channels: console, webhook, email (future).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests


logger = logging.getLogger(__name__)


@dataclass
class NotificationEvent:
    """Event data for notifications."""

    event_type: str  # validation_failed, operation_completed, error_occurred
    operation_id: str
    operation_type: str
    timestamp: datetime
    message: str
    details: dict[str, Any]
    severity: str = 'info'  # info, warning, error, critical


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""

    @abstractmethod
    def send(self, event: NotificationEvent) -> bool:
        """Send a notification. Returns True if successful."""


class ConsoleNotifier(NotificationChannel):
    """Print notifications to console."""

    def send(self, event: NotificationEvent) -> bool:
        """Print event to console with formatting."""
        severity_icons = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'critical': '🚨',
        }
        icon = severity_icons.get(event.severity, 'ℹ️')

        print(f'\n{"=" * 70}')
        print(f'{icon} NOTIFICATION: {event.event_type.upper()}')
        print(f'{"=" * 70}')
        print(f'Operation: {event.operation_type} ({event.operation_id})')
        print(f'Time: {event.timestamp.isoformat()}')
        print(f'Severity: {event.severity.upper()}')
        print(f'\nMessage: {event.message}')

        if event.details:
            print('\nDetails:')
            for key, value in event.details.items():
                print(f'  {key}: {value}')

        print(f'{"=" * 70}\n')
        return True


class WebhookNotifier(NotificationChannel):
    """Send notifications to a webhook URL (e.g., Slack, Discord)."""

    def __init__(self, webhook_url: str, timeout: int = 30):
        self.webhook_url = webhook_url
        self.timeout = timeout

    def send(self, event: NotificationEvent) -> bool:
        """Send event to webhook."""
        payload = {
            'text': f'{event.severity.upper()}: {event.event_type}',
            'operation_id': event.operation_id,
            'operation_type': event.operation_type,
            'timestamp': event.timestamp.isoformat(),
            'message': event.message,
            'details': event.details,
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f'Failed to send webhook notification: {e}')
            return False


class NotificationManager:
    """Manages multiple notification channels."""

    def __init__(self):
        self.channels: list[NotificationChannel] = []
        self.enabled_events: set[str] = set()  # Empty = all events
        self.min_severity: str = 'info'

    def add_channel(self, channel: NotificationChannel) -> NotificationManager:
        """Add a notification channel."""
        self.channels.append(channel)
        return self

    def enable_console(self) -> NotificationManager:
        """Enable console notifications."""
        self.channels.append(ConsoleNotifier())
        return self

    def enable_webhook(self, webhook_url: str) -> NotificationManager:
        """Enable webhook notifications."""
        self.channels.append(WebhookNotifier(webhook_url))
        return self

    def filter_events(self, event_types: list[str]) -> NotificationManager:
        """Only notify for specific event types."""
        self.enabled_events = set(event_types)
        return self

    def set_min_severity(self, severity: str) -> NotificationManager:
        """Set minimum severity level for notifications."""
        self.min_severity = severity
        return self

    def _should_notify(self, event: NotificationEvent) -> bool:
        """Check if event should trigger notification."""
        # Check severity
        severity_levels = ['info', 'warning', 'error', 'critical']
        event_level = severity_levels.index(event.severity)
        min_level = severity_levels.index(self.min_severity)

        if event_level < min_level:
            return False

        # Check event type filter
        if self.enabled_events and event.event_type not in self.enabled_events:
            return False

        return True

    def notify(self, event: NotificationEvent) -> list[bool]:
        """Send notification to all channels."""
        if not self._should_notify(event):
            return []

        results = []
        for channel in self.channels:
            try:
                success = channel.send(event)
                results.append(success)
            except Exception as e:
                logger.error(f'Notification channel failed: {e}')
                results.append(False)

        return results

    def notify_validation_failed(
        self,
        operation_id: str,
        operation_type: str,
        errors: list[str],
        details: dict[str, Any] | None = None,
    ) -> list[bool]:
        """Convenience method for validation failure notification."""
        event = NotificationEvent(
            event_type='validation_failed',
            operation_id=operation_id,
            operation_type=operation_type,
            timestamp=datetime.now(),
            message=f'Validation failed with {len(errors)} errors',
            details={'errors': errors, **(details or {})},
            severity='error',
        )
        return self.notify(event)

    def notify_operation_completed(
        self,
        operation_id: str,
        operation_type: str,
        success: bool,
        duration_seconds: float,
        records_processed: int,
        details: dict[str, Any] | None = None,
    ) -> list[bool]:
        """Convenience method for operation completion notification."""
        event = NotificationEvent(
            event_type='operation_completed',
            operation_id=operation_id,
            operation_type=operation_type,
            timestamp=datetime.now(),
            message=f'Operation {"succeeded" if success else "failed"} in {duration_seconds:.1f}s',
            details={
                'success': success,
                'duration_seconds': duration_seconds,
                'records_processed': records_processed,
                **(details or {}),
            },
            severity='info' if success else 'error',
        )
        return self.notify(event)

    def notify_circuit_breaker_open(
        self,
        operation_id: str,
        operation_type: str,
        failure_count: int,
        details: dict[str, Any] | None = None,
    ) -> list[bool]:
        """Convenience method for circuit breaker open notification."""
        event = NotificationEvent(
            event_type='circuit_breaker_open',
            operation_id=operation_id,
            operation_type=operation_type,
            timestamp=datetime.now(),
            message=f'Circuit breaker opened after {failure_count} failures',
            details={'failure_count': failure_count, **(details or {})},
            severity='critical',
        )
        return self.notify(event)

    def notify_error(
        self,
        operation_id: str,
        operation_type: str,
        error: Exception,
        stage: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> list[bool]:
        """Convenience method for error notification."""
        event = NotificationEvent(
            event_type='error_occurred',
            operation_id=operation_id,
            operation_type=operation_type,
            timestamp=datetime.now(),
            message=f'Error in {stage or "unknown stage"}: {error!s}',
            details={
                'error': str(error),
                'error_type': type(error).__name__,
                'stage': stage,
                **(details or {}),
            },
            severity='error',
        )
        return self.notify(event)


def create_default_notifier() -> NotificationManager:
    """Create a notification manager with console enabled."""
    return NotificationManager().enable_console().set_min_severity('warning')
