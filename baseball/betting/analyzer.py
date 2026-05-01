"""Betting analysis engine with edge detection.

Compares simulation probabilities to market odds to identify
value betting opportunities.

Author: Agent Cascade
Date: 2026-04-30
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from baseball.betting.schemas import (
    BetOpportunity,
    BetRecommendation,
    BettingMarket,
    MarketType,
    PlacedBet,
    RiskMetrics,
)
from baseball.betting.sources.base import BaseOddsSource
from baseball.core.cache import cached_odds


logger = logging.getLogger(__name__)


class BettingAnalyzer:
    """Analyze betting markets for value opportunities.

    Compares model probabilities to market implied probabilities,
    identifying edges where simulation differs from market pricing.

    Uses delegate pattern for flexible edge calculation:
    - Standard: edge = model_prob - market_prob
    - Kelly: edge = (model_prob * odds - 1) / (odds - 1)
    - Custom: User-provided formula

    Example:
        >>> analyzer = BettingAnalyzer(odds_source=TheOddsApiSource(api_key="xxx"))
        >>> sim_result = run_simulation(game_id)
        >>> opportunities = analyzer.find_edges(sim_result, min_edge=0.05)
        >>> stakes = [analyzer.kelly_criterion(opp, bankroll=10000) for opp in opportunities]
    """

    def __init__(
        self,
        odds_source: BaseOddsSource,
        edge_calculator: Callable[[Decimal, Decimal], Decimal] | None = None,
        min_edge: Decimal = Decimal('0.03'),
        max_bet_pct: Decimal = Decimal('0.05'),
        kelly_fraction: Decimal = Decimal('0.25'),
    ) -> None:
        """Initialize analyzer with source and strategy.

        Args:
            odds_source: Source for market odds (any BaseOddsSource)
            edge_calculator: Delegate for edge calculation
            min_edge: Minimum edge threshold for opportunities
            max_bet_pct: Maximum bet as % of bankroll (risk management)
            kelly_fraction: Fractional Kelly (0.25 = quarter Kelly)
        """
        self.odds_source = odds_source
        self.min_edge = min_edge
        self.max_bet_pct = max_bet_pct
        self.kelly_fraction = kelly_fraction

        # Delegate pattern for edge calculation
        self.edge_calculator = edge_calculator or self._standard_edge

        logger.info(f'Initialized BettingAnalyzer with source: {type(odds_source).__name__}')

    @staticmethod
    def _standard_edge(model_prob: Decimal, market_prob: Decimal) -> Decimal:
        """Standard edge calculation: model - market."""
        return model_prob - market_prob

    @staticmethod
    def _kelly_edge(model_prob: Decimal, market_prob: Decimal, odds: Decimal) -> Decimal:
        """Kelly criterion edge calculation."""
        # (bp - q) / b where b = odds - 1, p = prob, q = 1-p
        b = odds - Decimal('1')
        q = Decimal('1') - model_prob
        return (b * model_prob - q) / b if b > 0 else Decimal('0')

    def analyze_game(
        self,
        game_id: str,
        sim_probabilities: dict[str, Decimal],
        market_types: list[MarketType] | None = None,
    ) -> list[BetOpportunity]:
        """Analyze all markets for a game against simulation results.

        Args:
            game_id: Game identifier
            sim_probabilities: Dict of {outcome: probability} from simulation
                Example: {"Home": 0.58, "Away": 0.42} for moneyline
            market_types: Which markets to analyze (default: all)

        Returns:
            List of betting opportunities with edges
        """
        opportunities = []
        market_types = market_types or [MarketType.MONEYLINE, MarketType.SPREAD, MarketType.TOTAL]

        for market_type in market_types:
            try:
                markets = self.odds_source.get_game_odds(game_id, [market_type])
                market_opps = self._analyze_markets(markets, sim_probabilities)
                opportunities.extend(market_opps)
            except Exception as e:
                logger.exception(f'Failed to analyze {market_type} for {game_id}: {e}')

        # Sort by edge descending using lambda
        return sorted(opportunities, key=lambda opp: opp.edge, reverse=True)

    def _analyze_markets(
        self,
        markets: list[BettingMarket],
        sim_probabilities: dict[str, Decimal],
    ) -> list[BetOpportunity]:
        """Analyze specific markets for edges."""
        opportunities = []

        # Group markets by side (home/away, over/under)
        by_side: dict[str, list[BettingMarket]] = {}
        for m in markets:
            side = m.side or 'Unknown'
            by_side.setdefault(side, []).append(m)

        # Analyze each side
        for side, side_markets in by_side.items():
            sim_prob = sim_probabilities.get(side)
            if sim_prob is None:
                continue

            # Find best market (highest odds = lowest implied prob)
            best_market = max(side_markets, key=lambda m: m.odds if m.odds > 0 else Decimal('-999'))

            # Calculate implied probability
            market_prob = self.odds_source.calculate_implied_probability(best_market.odds)

            # Calculate edge using delegate
            edge = self.edge_calculator(sim_prob, market_prob)

            if edge >= self.min_edge:
                opportunity = BetOpportunity(
                    opportunity_id=f'{best_market.game_id}_{best_market.market_type.value}_{side}',
                    market=best_market,
                    model_probability=sim_prob,
                    market_probability=market_prob,
                    edge=edge,
                    expected_value=self._calculate_ev(sim_prob, best_market.odds),
                    confidence_score=self._calculate_confidence(edge, sim_prob),
                    recommendation=BetRecommendation.STRONG_BET if edge > Decimal('0.08') else BetRecommendation.BET,
                    analysis_timestamp=datetime.now(),
                    model_version='simulation_v1',
                    key_factors=['simulation_edge', 'market_inefficiency'],
                )
                opportunities.append(opportunity)

        return opportunities

    def find_edges(
        self,
        sport,
        sim_results: list[tuple[str, dict[str, Decimal]]],
        min_edge: Decimal | None = None,
    ) -> list[BetOpportunity]:
        """Batch find edges across multiple games.

        Args:
            sport: Sport to analyze
            sim_results: List of (game_id, probabilities) tuples
            min_edge: Override default min edge threshold

        Returns:
            All opportunities meeting edge threshold
        """
        min_edge = min_edge or self.min_edge
        all_opportunities = []

        for game_id, probabilities in sim_results:
            try:
                opps = self.analyze_game(game_id, probabilities)
                # Filter by edge using lambda
                filtered = list(filter(lambda o: o.edge >= min_edge, opps))
                all_opportunities.extend(filtered)
            except Exception as e:
                logger.warning(f'Skipping game {game_id}: {e}')

        # Sort by edge descending
        return sorted(all_opportunities, key=lambda o: o.edge, reverse=True)

    def calculate_stake(
        self,
        opportunity: BetOpportunity,
        bankroll: Decimal,
        method: str = 'kelly',
    ) -> Decimal:
        """Calculate optimal bet size.

        Methods:
        - "kelly": Fractional Kelly criterion
        - "flat": Flat betting (1-2% of bankroll)
        - "confidence": Stake proportional to edge * confidence

        Args:
            opportunity: The bet opportunity
            bankroll: Current bankroll
            method: Stake calculation method

        Returns:
            Recommended bet amount
        """
        if method == 'kelly':
            return self._kelly_stake(opportunity, bankroll)
        if method == 'flat':
            return bankroll * Decimal('0.01')  # 1% flat
        if method == 'confidence':
            return bankroll * opportunity.edge * opportunity.confidence_score
        msg = f'Unknown stake method: {method}'
        raise ValueError(msg)

    def _kelly_stake(
        self,
        opportunity: BetOpportunity,
        bankroll: Decimal,
    ) -> Decimal:
        """Calculate fractional Kelly stake."""
        p = opportunity.model_probability
        q = Decimal('1') - p

        # Convert odds to decimal if needed
        odds = opportunity.market.odds
        if opportunity.market.odds_format == 'american':
            if odds > 0:
                decimal_odds = (odds / Decimal('100')) + Decimal('1')
            else:
                decimal_odds = (Decimal('100') / abs(odds)) + Decimal('1')
        else:
            decimal_odds = odds

        # Kelly formula: (bp - q) / b
        b = decimal_odds - Decimal('1')
        if b <= 0:
            return Decimal('0')

        kelly_pct = (b * p - q) / b

        # Apply fractional Kelly and max bet limit
        stake_pct = min(
            kelly_pct * self.kelly_fraction,
            self.max_bet_pct,
        )

        return bankroll * stake_pct

    def _calculate_ev(self, prob: Decimal, odds: Decimal) -> Decimal:
        """Calculate expected value of a bet."""
        # EV = (prob * win_amount) - ((1-prob) * lose_amount)
        # Assuming unit bet
        if odds > 0:  # American +odds
            win_amount = odds / Decimal('100')
        else:  # American -odds
            win_amount = Decimal('100') / abs(odds)

        return (prob * win_amount) - ((Decimal('1') - prob) * Decimal('1'))

    def _calculate_confidence(self, edge: Decimal, prob: Decimal) -> Decimal:
        """Calculate confidence score (0-1) based on edge and model certainty."""
        # Higher edge = higher confidence
        # Probability closer to 0.5 = less certainty
        edge_factor = min(edge * Decimal('10'), Decimal('1'))  # Scale edge
        certainty = Decimal('1') - abs(prob - Decimal('0.5')) * Decimal('2')
        return edge_factor * certainty

    def detect_reverse_line_movement(
        self,
        game_id: str,
        market_type: MarketType,
        hours: int = 6,
    ) -> BetOpportunity | None:
        """Detect reverse line movement (sharp money indicator).

        RLM occurs when:
        - Public is betting one side (high volume)
        - Line moves opposite direction (sharp money other side)

        Args:
            game_id: Game to check
            market_type: Market type
            hours: How far back to look

        Returns:
            Opportunity if RLM detected, None otherwise
        """
        try:
            history = self.odds_source.get_line_movement(game_id, market_type, hours)
            if len(history) < 2:
                return None

            # Get opening and current lines
            opening = history[0]
            current = history[-1]

            # Check for significant movement
            opening_prob = self.odds_source.calculate_implied_probability(opening.odds)
            current_prob = self.odds_source.calculate_implied_probability(current.odds)

            movement = abs(current_prob - opening_prob)

            # If movement > 3%, flag as RLM
            if movement > Decimal('0.03'):
                logger.info(f'RLM detected for {game_id}: {movement:.1%} movement')
                # Would create opportunity here with RLM factor
                return None  # Placeholder

            return None
        except Exception as e:
            logger.exception(f'RLM detection failed: {e}')
            return None

    @cached_odds(ttl=120)
    async def get_best_lines(
        self,
        game_id: str,
        market_type: MarketType,
        side: str,
    ) -> list[BettingMarket]:
        """Find best available lines across all books.

        Args:
            game_id: Game to check
            market_type: Market type
            side: Which side (team name, "Over", "Under")

        Returns:
            Markets sorted by odds (best first)
        
        Cached for 2 minutes.
        """
        markets = self.odds_source.get_game_odds(game_id, [market_type])

        # Filter to side and sort by odds
        side_markets = [m for m in markets if m.side == side]
        return sorted(side_markets, key=lambda m: m.odds, reverse=True)

    def create_bet(
        self,
        opportunity: BetOpportunity,
        bankroll: Decimal,
        strategy_id: str | None = None,
    ) -> PlacedBet:
        """Create a PlacedBet from an opportunity.

        Args:
            opportunity: The betting opportunity
            bankroll: Current bankroll
            strategy_id: Optional strategy identifier

        Returns:
            PlacedBet ready for tracking
        """
        stake = self.calculate_stake(opportunity, bankroll)

        return PlacedBet(
            bet_id=f"bet_{datetime.now().strftime('%Y%m%d%H%M%S')}_{opportunity.market.game_id}",
            opportunity=opportunity,
            placed_timestamp=datetime.now(),
            odds_placed=opportunity.market.odds,
            stake=stake,
            book=opportunity.market.book,
            strategy_id=strategy_id,
            risk_metrics=RiskMetrics(
                kelly_fraction=self.kelly_fraction,
                bet_to_bankroll_pct=stake / bankroll,
                expected_roi=opportunity.expected_value,
                sharpe_ratio=None,  # Requires historical data
                max_drawdown_risk=None,
                confidence_adjusted_stake=stake * opportunity.confidence_score,
            ),
            status='pending',
            notes=None,
        )
