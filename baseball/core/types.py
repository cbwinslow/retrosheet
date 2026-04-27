"""Shared type definitions for the baseball platform.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SourceRequest:
    """Request object for source adapter operations."""

    source: str
    params: dict[str, Any]


@dataclass(frozen=True)
class SourceResult:
    """Result object for source adapter operations."""

    success: bool
    rows_downloaded: int = 0
    rows_inserted: int = 0
    error_message: str = ''
    metadata: dict[str, Any] | None = None
