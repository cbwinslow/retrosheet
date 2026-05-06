"""Betting analytics and market analysis for baseball prediction."""

from .analyzer import BettingAnalyzer
from .integration import SimulationBackedAnalyzer
from .market_comparison import (
    MarketComparator,
    EdgeCalculator,
    OddsConverter,
    EdgeOpportunity,
    MarketLine,
    MarketType,
    find_moneyline_edges,
    calculate_stake,
)
from .paper_trading import PaperTradingAccount
from .sources import BaseOddsSource, DraftKingsSource, PinnacleSource, TheOddsApiSource


__all__ = [
    'BaseOddsSource',
    'BettingAnalyzer',
    'DraftKingsSource',
    'PaperTradingAccount',
    'PinnacleSource',
    'SimulationBackedAnalyzer',
    'TheOddsApiSource',
    # Market Comparison
    'MarketComparator',
    'EdgeCalculator',
    'OddsConverter',
    'EdgeOpportunity',
    'MarketLine',
    'MarketType',
    'find_moneyline_edges',
    'calculate_stake',
]
