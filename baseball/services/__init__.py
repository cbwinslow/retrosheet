"""Baseball services package.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26

This package contains services that WRAP existing scripts,
preserving working logic while adding the new baseball CLI interface.
"""

from baseball.services.bridge import BridgeService

__all__ = ['BridgeService']
