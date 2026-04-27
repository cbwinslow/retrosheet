"""HTTP client with retry/backoff for the baseball platform.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from dataclasses import dataclass


@dataclass
class HttpClient:
    """HTTP client with configurable timeout."""
    timeout_seconds: int = 30
