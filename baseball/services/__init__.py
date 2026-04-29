"""Baseball services package.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-29

This package contains services that WRAP existing scripts,
preserving working logic while adding the new baseball CLI interface.

Available services:
- BridgeService: Entity resolution and cross-reference management
- LiveFeedPoller: Real-time MLB game data polling with database persistence
"""

from baseball.services.bridge import BridgeService
from baseball.services.live_feed import GameUpdate, LiveFeedPoller


__all__ = ['BridgeService', 'GameUpdate', 'LiveFeedPoller']
