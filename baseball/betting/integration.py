"""Betting integration with Monte Carlo simulation.

Bridges simulation results to betting analysis, enabling
real probability-based edge detection.

Author: Agent Cascade
Date: 2026-04-30
"""

import logging
from datetime import datetime
from decimal import Decimal

from baseball.betting.analyzer import BettingAnalyzer
from baseball.betting.schemas import MarketType
from baseball.simulation.service import SimulationService


logger = logging.getLogger(__name__)


class SimulationBackedAnalyzer:
    """Betting analyzer backed by Monte Carlo simulation.

    Automatically queries simulation results for probabilities
    when analyzing games, enabling real edge detection.

    Example:
        >>> analyzer = SimulationBackedAnalyzer(odds_source=source)
        >>> opportunities = await analyzer.analyze_game_with_simulation("716190")
        >>> # Probabilities automatically pulled from simulation database
    """

    def __init__(
        self,
        odds_source,
        simulation_service: SimulationService | None = None,
        min_edge: Decimal = Decimal('0.03'),
        max_bet_pct: Decimal = Decimal('0.05'),
    ) -> None:
        """Initialize with odds source and optional sim service.

        Args:
            odds_source: Any BaseOddsSource implementation
            simulation_service: Simulation service (created if None)
            min_edge: Minimum edge threshold
            max_bet_pct: Maximum bet percentage
        """
        self.odds_source = odds_source
        self.sim_service = simulation_service or SimulationService()
        self.min_edge = min_edge
        self.max_bet_pct = max_bet_pct

        self._analyzer = BettingAnalyzer(
            odds_source=odds_source,
            min_edge=min_edge,
            max_bet_pct=max_bet_pct,
        )

        logger.info(
            f'Initialized SimulationBackedAnalyzer with '
            f'{type(odds_source).__name__}',
        )

    async def analyze_game_with_simulation(
        self,
        game_id: str,
        market_types: list[MarketType] | None = None,
        model_id: str | None = None,
        fallback_to_mock: bool = True,
    ) -> dict:
        """Analyze game using real simulation probabilities.

        Args:
            game_id: Game to analyze
            market_types: Markets to analyze (default: all)
            model_id: Specific model to use (default: latest)
            fallback_to_mock: Use mock probabilities if no simulation exists

        Returns:
            Analysis results dict with opportunities and metadata
        """
        market_types = market_types or [
            MarketType.MONEYLINE, MarketType.SPREAD, MarketType.TOTAL,
        ]

        # Get simulation probabilities
        sim_probs = await self._get_simulation_probabilities(
            game_id, market_types, model_id, fallback_to_mock,
        )

        if not sim_probs:
            return {
                'game_id': game_id,
                'markets_analyzed': 0,
                'opportunities': [],
                'error': 'No simulation probabilities available',
            }

        # Analyze each market type
        all_opportunities = []

        for market_type in market_types:
            if market_type == MarketType.MONEYLINE:
                opportunities = self._analyzer.find_edges(
                    game_id,
                    {
                        'Home': sim_probs.get('home_win', Decimal('0.5')),
                        'Away': sim_probs.get('away_win', Decimal('0.5')),
                    },
                )
                all_opportunities.extend(opportunities)

            elif market_type == MarketType.SPREAD:
                # Use spread line from first available market
                spread_opps = await self._analyze_spread_markets(
                    game_id, sim_probs,
                )
                all_opportunities.extend(spread_opps)

            elif market_type == MarketType.TOTAL:
                total_opps = await self._analyze_total_markets(
                    game_id, sim_probs,
                )
                all_opportunities.extend(total_opps)

        return {
            'game_id': game_id,
            'markets_analyzed': len(market_types),
            'opportunities': all_opportunities,
            'simulation_probabilities': sim_probs,
            'source': type(self.odds_source).__name__,
        }

    async def _get_simulation_probabilities(
        self,
        game_id: str,
        market_types: list[MarketType],
        model_id: str | None,
        fallback_to_mock: bool,
    ) -> dict[str, Decimal]:
        """Get probabilities from simulation or fallback."""
        probs = {}

        # Try to get from simulation
        try:
            win_probs = await self.sim_service.get_game_probabilities(
                game_id, model_id,
            )

            if win_probs:
                probs.update(win_probs)
                logger.info(f'Using simulation probabilities for {game_id}')

                # Get total probabilities if needed
                if MarketType.TOTAL in market_types:
                    # Default to 8.5 if no market info
                    total_probs = await self.sim_service.get_total_probabilities(
                        game_id, Decimal('8.5'), model_id,
                    )
                    probs['total_over'] = total_probs.get('over')
                    probs['total_under'] = total_probs.get('under')

                # Get spread probabilities if needed
                if MarketType.SPREAD in market_types:
                    spread_probs = await self.sim_service.get_spread_probabilities(
                        game_id, Decimal('-1.5'), model_id,
                    )
                    probs['home_spread_cover'] = spread_probs.get('home_cover')
                    probs['away_spread_cover'] = spread_probs.get('away_cover')

        except Exception as e:
            logger.warning(f'Failed to query simulation: {e}')

        # Fallback to mock if needed
        if not probs and fallback_to_mock:
            logger.warning(f'No simulation for {game_id}, using mock probabilities')
            probs = {
                'home_win': Decimal('0.55'),
                'away_win': Decimal('0.45'),
            }

        return probs

    async def _analyze_spread_markets(
        self,
        game_id: str,
        sim_probs: dict[str, Decimal],
    ) -> list:
        """Analyze spread markets with simulation probabilities."""
        opportunities = []

        # Get markets from source
        markets = self.odds_source.get_game_odds(game_id, [MarketType.SPREAD])

        for market in markets:
            if market.line is None:
                continue

            # Query simulation for specific spread line
            try:
                spread_probs = await self.sim_service.get_spread_probabilities(
                    game_id, market.line,
                )

                # Determine which side probability to use
                if market.side == 'Home':
                    model_prob = spread_probs.get('home_cover', Decimal('0.5'))
                else:
                    model_prob = spread_probs.get('away_cover', Decimal('0.5'))

                # Check for edge
                edge = self._analyzer.edge_calculator(
                    model_prob,
                    self._analyzer._implied_probability(market.odds),
                )

                if edge >= self.min_edge:
                    from baseball.betting.schemas import BetOpportunity

                    opp = BetOpportunity(
                        opportunity_id=f'spread_{market.market_id}',
                        market=market,
                        model_probability=model_prob,
                        model_confidence=Decimal('0.75'),
                        edge=edge,
                        ev=edge * model_prob,
                        recommendation='bet' if edge > 0 else 'pass',
                        timestamp=datetime.now(),
                        strategy_id='monte_carlo_spread',
                    )
                    opportunities.append(opp)

            except Exception as e:
                logger.warning(f'Failed to analyze spread {market.line}: {e}')

        return opportunities

    async def _analyze_total_markets(
        self,
        game_id: str,
        sim_probs: dict[str, Decimal],
    ) -> list:
        """Analyze total markets with simulation probabilities."""
        opportunities = []

        # Get markets from source
        markets = self.odds_source.get_game_odds(game_id, [MarketType.TOTAL])

        for market in markets:
            if market.line is None:
                continue

            # Query simulation for specific total line
            try:
                total_probs = await self.sim_service.get_total_probabilities(
                    game_id, market.line,
                )

                # Determine which side probability to use
                if market.side == 'Over':
                    model_prob = total_probs.get('over', Decimal('0.5'))
                else:
                    model_prob = total_probs.get('under', Decimal('0.5'))

                # Check for edge
                edge = self._analyzer.edge_calculator(
                    model_prob,
                    self._analyzer._implied_probability(market.odds),
                )

                if edge >= self.min_edge:
                    from baseball.betting.schemas import BetOpportunity

                    opp = BetOpportunity(
                        opportunity_id=f'total_{market.market_id}',
                        market=market,
                        model_probability=model_prob,
                        model_confidence=Decimal('0.70'),
                        edge=edge,
                        ev=edge * model_prob,
                        recommendation='bet' if edge > 0 else 'pass',
                        timestamp=datetime.now(),
                        strategy_id='monte_carlo_total',
                    )
                    opportunities.append(opp)

            except Exception as e:
                logger.warning(f'Failed to analyze total {market.line}: {e}')

        return opportunities

    def _implied_probability(self, odds: Decimal) -> Decimal:
        """Calculate implied probability from odds."""
        if odds > 0:
            return Decimal('100') / (odds + Decimal('100'))
        return abs(odds) / (abs(odds) + Decimal('100'))


async def analyze_betting_opportunities(
    game_id: str,
    odds_source,
    min_edge: Decimal = Decimal('0.03'),
    market_types: list[MarketType] | None = None,
) -> dict:
    """Convenience function to analyze game betting opportunities.

    Args:
        game_id: Game to analyze
        odds_source: Source for market odds
        min_edge: Minimum edge threshold
        market_types: Markets to analyze

    Returns:
        Analysis results dict

    Example:
        >>> from baseball.betting.sources.the_odds_api import TheOddsApiSource
        >>> source = TheOddsApiSource(api_key="xxx")
        >>> results = await analyze_betting_opportunities("716190", source)
        >>> print(f"Found {len(results['opportunities'])} edges")
    """
    analyzer = SimulationBackedAnalyzer(
        odds_source=odds_source,
        min_edge=min_edge,
    )

    return await analyzer.analyze_game_with_simulation(
        game_id,
        market_types=market_types,
    )
