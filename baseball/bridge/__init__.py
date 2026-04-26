"""Bridge layer for cross-source ID resolution and entity mapping.

This module provides xref services that map entity IDs between different data sources:
- MLB Stats API (mlb_id)
- Retrosheet (retro_id)
- ESPN (espn_id)
- Statcast (mlb_id, but with Statcast-specific fields)
- Lahman (lahman_id)

The bridge enables combining data from multiple sources by providing
canonical entity resolution.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

from .game_xref import GameXref, GameXrefService
from .player_xref import PlayerXref, PlayerXrefService
from .team_xref import TeamXref, TeamXrefService
from .xref_manager import XrefManager


__all__ = [
    'GameXref',
    'GameXrefService',
    'PlayerXref',
    'PlayerXrefService',
    'TeamXref',
    'TeamXrefService',
    'XrefManager',
]
