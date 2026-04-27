"""Pipeline checkpoint logic for the baseball platform.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from dataclasses import dataclass


@dataclass
class Checkpoint:
    """Checkpoint data structure for pipeline state tracking."""
    source: str
    key: str
    value: str
