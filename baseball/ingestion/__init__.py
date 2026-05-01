"""Data ingestion services for live feeds and scheduled jobs.

This package provides:
- BaseIngestionSource: Super class for all data sources
- LiveDataIngestionService: WebSocket-based live feeds
- OddsIngestionService: Cron-based odds fetching
- MlbLiveIngestionSource: MLB Stats API live game adapter
- MlbScheduleIngestionSource: MLB schedule/discovery adapter
- Database-driven job scheduling

All services use event hooks for extensibility.

Author: Agent Cascade
Date: 2026-04-30
"""

from baseball.ingestion.base import BaseIngestionSource, IngestionHook
from baseball.ingestion.live_service import LiveDataIngestionService
from baseball.ingestion.odds_service import OddsIngestionService
from baseball.ingestion.scheduler import DatabaseScheduler
from baseball.ingestion.mlb_live_adapter import (
    MlbLiveIngestionSource,
    MlbScheduleIngestionSource
)

__all__ = [
    "BaseIngestionSource",
    "IngestionHook",
    "LiveDataIngestionService",
    "OddsIngestionService",
    "DatabaseScheduler",
    "MlbLiveIngestionSource",
    "MlbScheduleIngestionSource"
]
