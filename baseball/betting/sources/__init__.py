"""Betting odds sources package.

Provides flexible, pluggable odds sources using super class pattern.
"""

from baseball.betting.sources.base import BaseOddsSource
from baseball.betting.sources.draftkings import DraftKingsSource
from baseball.betting.sources.pinnacle import PinnacleSource
from baseball.betting.sources.the_odds_api import TheOddsApiSource


__all__ = [
    'BaseOddsSource',
    'DraftKingsSource',
    'PinnacleSource',
    'TheOddsApiSource',
]
