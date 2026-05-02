"""
Market Comparison and Edge Detection

Compares model probabilities against sportsbook odds to find +EV betting opportunities.

Usage:
    from baseball.betting.market_comparison import MarketComparator, EdgeCalculator
    
    comparator = MarketComparator()
    
    # Compare model vs market
    edges = comparator.find_edges(
        model_probs={'home': 0.58, 'away': 0.42},
        market_odds={'home': -110, 'away': -110}
    )
    
    # Calculate Kelly stake
    stake = EdgeCalculator.kelly_stake(
        bankroll=10000,
        edge=0.05,
        odds=-110
    )
"""

from decimal import Decimal
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum


class MarketType(Enum):
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    TOTAL = "total"
    PROP = "prop"


@dataclass
class EdgeOpportunity:
    """A betting edge opportunity."""
    market_type: MarketType
    selection: str  # e.g., "home", "over", "team_a_spread"
    model_prob: float  # 0-1
    market_prob: float  # 0-1 implied from odds
    edge: float  # model_prob - market_prob
    odds_american: int  # e.g., -110, +150
    odds_decimal: float  # e.g., 1.91, 2.50
    kelly_fraction: float  # Optimal bet size as % of bankroll
    ev_percent: float  # Expected value as %
    confidence: str  # "high", "medium", "low" based on edge magnitude


@dataclass
class MarketLine:
    """Sportsbook line data."""
    sportsbook: str  # e.g., "draftkings", "pinnacle"
    market_type: MarketType
    selection: str
    odds_american: int
    odds_decimal: float
    line: Optional[float] = None  # For spreads/totals
    timestamp: Optional[str] = None


class OddsConverter:
    """Convert between odds formats and calculate implied probabilities."""
    
    @staticmethod
    def american_to_decimal(american_odds: int) -> float:
        """Convert American odds to decimal."""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
    
    @staticmethod
    def decimal_to_american(decimal_odds: float) -> int:
        """Convert decimal odds to American."""
        if decimal_odds >= 2.0:
            return int((decimal_odds - 1) * 100)
        else:
            return int(-100 / (decimal_odds - 1))
    
    @staticmethod
    def american_to_probability(american_odds: int) -> float:
        """Convert American odds to implied probability (accounting for vig)."""
        decimal = OddsConverter.american_to_decimal(american_odds)
        return 1 / decimal
    
    @staticmethod
    def remove_vig(prob1: float, prob2: float) -> tuple:
        """Remove vig from implied probabilities."""
        total = prob1 + prob2
        if total > 1.0:
            return prob1 / total, prob2 / total
        return prob1, prob2


class EdgeCalculator:
    """Calculate betting edges and optimal stakes."""
    
    MIN_EDGE = 0.02  # 2% minimum edge to consider
    HIGH_EDGE = 0.05  # 5% for high confidence
    
    @staticmethod
    def calculate_edge(model_prob: float, market_prob: float) -> float:
        """
        Calculate edge: model probability minus market-implied probability.
        
        Positive edge means model thinks it's more likely than market.
        """
        return model_prob - market_prob
    
    @staticmethod
    def calculate_ev(model_prob: float, decimal_odds: float) -> float:
        """
        Calculate expected value as percentage of stake.
        
        EV = (prob * win_amount) - ((1 - prob) * stake)
        Returns EV as percentage (e.g., 0.05 = 5% expected profit)
        """
        win_amount = decimal_odds - 1  # Net profit per unit stake
        prob_win = model_prob
        prob_lose = 1 - model_prob
        
        ev = (prob_win * win_amount) - (prob_lose * 1)
        return ev
    
    @staticmethod
    def kelly_stake(
        bankroll: float,
        model_prob: float,
        decimal_odds: float,
        fraction: float = 0.25  # Quarter Kelly for safety
    ) -> float:
        """
        Calculate Kelly criterion optimal bet size.
        
        f* = (bp - q) / b
        where b = odds - 1, p = win prob, q = lose prob
        
        Args:
            bankroll: Total bankroll
            model_prob: Model's estimated win probability
            decimal_odds: Decimal odds (e.g., 2.10 for +110)
            fraction: Kelly fraction (0.25 = quarter Kelly)
        
        Returns:
            Recommended stake amount
        """
        b = decimal_odds - 1  # Net odds received on win
        p = model_prob
        q = 1 - p
        
        kelly = (b * p - q) / b if b > 0 else 0
        kelly = max(0, min(kelly, 0.5))  # Cap at 50% bankroll
        
        return bankroll * kelly * fraction
    
    @staticmethod
    def confidence_level(edge: float) -> str:
        """Determine confidence level based on edge magnitude."""
        if edge >= EdgeCalculator.HIGH_EDGE:
            return "high"
        elif edge >= EdgeCalculator.MIN_EDGE:
            return "medium"
        else:
            return "low"


class MarketComparator:
    """
    Compare model probabilities against market odds.
    
    Finds +EV (positive expected value) betting opportunities.
    """
    
    def __init__(self, min_edge: float = 0.02):
        """
        Initialize comparator.
        
        Args:
            min_edge: Minimum edge to flag as opportunity (default 2%)
        """
        self.min_edge = min_edge
        self.converter = OddsConverter()
    
    def find_edges(
        self,
        model_probs: Dict[str, float],
        market_odds: Dict[str, int],
        market_type: MarketType = MarketType.MONEYLINE,
        sportsbook: str = "unknown"
    ) -> List[EdgeOpportunity]:
        """
        Find betting edges by comparing model to market.
        
        Args:
            model_probs: Dict of selection -> probability (0-1)
            market_odds: Dict of selection -> American odds (-110, +150)
            market_type: Type of market
            sportsbook: Sportsbook name
        
        Returns:
            List of EdgeOpportunity objects with positive edges
        """
        opportunities = []
        
        for selection, model_prob in model_probs.items():
            if selection not in market_odds:
                continue
            
            american_odds = market_odds[selection]
            decimal_odds = self.converter.american_to_decimal(american_odds)
            market_prob = self.converter.american_to_probability(american_odds)
            
            # Remove vig if two-way market
            if len(model_probs) == 2:
                other = [k for k in model_probs.keys() if k != selection][0]
                other_market_prob = self.converter.american_to_probability(market_odds[other])
                market_prob, _ = self.converter.remove_vig(market_prob, other_market_prob)
            
            edge = EdgeCalculator.calculate_edge(model_prob, market_prob)
            
            if edge >= self.min_edge:
                ev = EdgeCalculator.calculate_ev(model_prob, decimal_odds)
                kelly = EdgeCalculator.kelly_stake(1000, model_prob, decimal_odds)
                confidence = EdgeCalculator.confidence_level(edge)
                
                opp = EdgeOpportunity(
                    market_type=market_type,
                    selection=selection,
                    model_prob=model_prob,
                    market_prob=market_prob,
                    edge=edge,
                    odds_american=american_odds,
                    odds_decimal=decimal_odds,
                    kelly_fraction=kelly / 1000,
                    ev_percent=ev,
                    confidence=confidence
                )
                opportunities.append(opp)
        
        # Sort by edge magnitude (descending)
        opportunities.sort(key=lambda x: x.edge, reverse=True)
        return opportunities
    
    def compare_multiple_books(
        self,
        model_probs: Dict[str, float],
        book_lines: Dict[str, Dict[str, int]]
    ) -> Dict[str, List[EdgeOpportunity]]:
        """
        Compare model against multiple sportsbooks.
        
        Args:
            model_probs: Model probabilities
            book_lines: Dict of sportsbook -> selection -> odds
        
        Returns:
            Dict of sportsbook -> list of edges
        """
        results = {}
        for book, odds in book_lines.items():
            edges = self.find_edges(model_probs, odds, sportsbook=book)
            if edges:
                results[book] = edges
        return results
    
    def best_line(
        self,
        selection: str,
        book_lines: Dict[str, int]
    ) -> tuple:
        """
        Find the best odds for a selection across books.
        
        Args:
            selection: The selection to find
            book_lines: Dict of sportsbook -> odds
        
        Returns:
            (best_book, best_odds)
        """
        best_book = None
        best_odds = float('-inf')
        
        for book, odds in book_lines.items():
            # For American odds, higher is better (both + and -)
            if odds > best_odds:
                best_odds = odds
                best_book = book
        
        return best_book, best_odds


# Convenience functions
def find_moneyline_edges(
    home_prob: float,
    away_prob: float,
    home_odds: int,
    away_odds: int,
    min_edge: float = 0.02
) -> List[EdgeOpportunity]:
    """Quick function to find moneyline edges."""
    comparator = MarketComparator(min_edge=min_edge)
    return comparator.find_edges(
        model_probs={'home': home_prob, 'away': away_prob},
        market_odds={'home': home_odds, 'away': away_odds},
        market_type=MarketType.MONEYLINE
    )


def calculate_stake(
    bankroll: float,
    model_prob: float,
    american_odds: int,
    kelly_fraction: float = 0.25
) -> float:
    """Quick function to calculate recommended stake."""
    decimal = OddsConverter.american_to_decimal(american_odds)
    return EdgeCalculator.kelly_stake(bankroll, model_prob, decimal, kelly_fraction)
