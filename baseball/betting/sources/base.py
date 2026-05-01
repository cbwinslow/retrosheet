"""Base class for betting odds sources.

This module defines the abstract interface that all odds sources must implement,
providing a flexible, pluggable architecture for betting market data.

Author: Agent Cascade
Date: 2026-04-30
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from decimal import Decimal
from typing import TYPE_CHECKING

from baseball.betting.schemas import BettingMarket, BookRegion, MarketType, Sport


if TYPE_CHECKING:
    from datetime import datetime


logger = logging.getLogger(__name__)


class BaseOddsSource(ABC):
    """Abstract base class for sportsbook odds sources.

    This class defines the common interface for all odds providers,
    enabling plug-and-play source switching and testable mocks.

    Implementations:
    - TheOddsApiSource: odds-api.com (covers multiple books)
    - DraftKingsSource: Direct DK API
    - PinnacleSource: Pinnacle API (sharp lines)
    - FanDuelSource: FanDuel API
    - MockOddsSource: For testing without API calls

    Example:
        >>> source = TheOddsApiSource(api_key="xxx")
        >>> markets = source.get_live_odds("mlb", MarketType.MONEYLINE)
        >>> lines = [m for m in markets if m.book == "draftkings"]
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 30,
        cache_ttl: int = 60,
        odds_transform: Callable[[Decimal], Decimal] | None = None,
        market_filter: Callable[[BettingMarket], bool] | None = None,
    ) -> None:
        """Initialize the odds source.

        Args:
            api_key: API authentication key
            base_url: Override default API endpoint
            timeout: Request timeout in seconds
            cache_ttl: Cache time-to-live in seconds
            odds_transform: Delegate function for odds normalization
            market_filter: Delegate function for market filtering
        """
        self.api_key = api_key
        self.base_url = base_url or self._default_url()
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._cache: dict = {}
        self._last_fetch: datetime | None = None

        # Delegate functions for flexibility
        self.odds_transform = odds_transform or (lambda x: x)
        self.market_filter = market_filter or (lambda m: True)

        logger.info(f'Initialized {self.__class__.__name__}')

    @abstractmethod
    def _default_url(self) -> str:
        """Return the default API base URL."""

    @abstractmethod
    def get_live_odds(
        self,
        sport: Sport,
        market_type: MarketType,
        region: BookRegion = BookRegion.US,
        odds_format: str = 'american',
    ) -> list[BettingMarket]:
        """Fetch current odds for a sport/market combination.

        Args:
            sport: Sport enum (MLB, NBA, NFL, etc.)
            market_type: Market enum (MONEYLINE, SPREAD, TOTAL)
            region: Bookmaker region filter
            odds_format: "american", "decimal", or "fractional"

        Returns:
            List of normalized BettingMarket objects
        """

    @abstractmethod
    def get_game_odds(
        self,
        game_id: str,
        market_types: list[MarketType] | None = None,
    ) -> list[BettingMarket]:
        """Fetch all odds for a specific game.

        Args:
            game_id: Provider-specific game identifier
            market_types: Optional filter for specific markets

        Returns:
            List of BettingMarket objects for the game
        """

    @abstractmethod
    def get_line_movement(
        self,
        game_id: str,
        market_type: MarketType,
        hours: int = 24,
    ) -> list[BettingMarket]:
        """Fetch historical line movements.

        Args:
            game_id: Game identifier
            market_type: Market to track
            hours: How far back to fetch

        Returns:
            Chronological list of market snapshots
        """

    @abstractmethod
    def get_sharp_lines(
        self,
        sport: Sport,
        market_type: MarketType,
    ) -> list[BettingMarket]:
        """Fetch lines from sharp books (Pinnacle, Circa) for calibration.

        Args:
            sport: Sport to query
            market_type: Market type

        Returns:
            Markets from known sharp bookmakers
        """

    def _apply_transforms(self, markets: list[BettingMarket]) -> list[BettingMarket]:
        """Apply delegate transforms to fetched markets.

        Pipeline:
        1. Filter markets via market_filter delegate
        2. Transform odds via odds_transform delegate
        3. Return processed list

        Args:
            markets: Raw markets from API

        Returns:
            Transformed and filtered markets
        """
        # Filter using delegate
        filtered = filter(self.market_filter, markets)

        # Transform using delegate (for vig removal, normalization, etc.)
        transformed = []
        for m in filtered:
            try:
                transformed_odds = self.odds_transform(m.odds)
                # Create copy with transformed odds
                new_market = m.model_copy(update={'odds': transformed_odds})
                transformed.append(new_market)
            except Exception as e:
                logger.warning(f'Transform failed for {m}: {e}')
                transformed.append(m)  # Keep original on failure

        return transformed

    def calculate_implied_probability(
        self,
        odds: Decimal,
        odds_format: str = 'american',
    ) -> Decimal:
        """Convert odds to implied probability (0-1 scale).

        Uses delegate pattern - can be overridden per source
        for different vig handling strategies.

        Args:
            odds: The odds value
            odds_format: american, decimal, or fractional

        Returns:
            Implied probability as Decimal
        """
        if odds_format == 'american':
            if odds > 0:
                return Decimal('100') / (odds + Decimal('100'))
            return abs(odds) / (abs(odds) + Decimal('100'))
        if odds_format == 'decimal':
            return Decimal('1') / odds
        msg = f'Unsupported odds format: {odds_format}'
        raise ValueError(msg)

    def remove_vig(
        self,
        markets: list[BettingMarket],
        method: str = 'proportional',
    ) -> list[BettingMarket]:
        """Remove bookmaker vig from market lines.

        Methods:
        - "proportional": Remove vig proportional to implied probs
        - "equal": Split vig equally between sides
        - "wisdom": Use sharp line as "true" probability

        Args:
            markets: List of markets (should have both sides)
            method: Vig removal strategy

        Returns:
            Markets with vig removed
        """
        if len(markets) < 2:
            return markets

        # Calculate total implied probability (includes vig)
        implied_probs = [
            self.calculate_implied_probability(m.odds) for m in markets
        ]
        total_overround = sum(implied_probs)

        # Vig removal strategies as lambda functions
        vig_strategies = {
            'proportional': lambda p: p / total_overround,
            'equal': lambda p: p - (total_overround - 1) / len(implied_probs),
            'wisdom': lambda p: p,  # Placeholder - would use sharp calibration
        }

        strategy = vig_strategies.get(method, vig_strategies['proportional'])

        # Apply to markets
        devigged = []
        for m, prob in zip(markets, implied_probs, strict=False):
            true_prob = strategy(prob)
            # Convert back to odds
            true_odds = Decimal('1') / true_prob if true_prob > 0 else m.odds
            devigged.append(m.model_copy(update={'odds': true_odds}))

        return devigged

    def health_check(self) -> bool:
        """Verify source connectivity and API status.

        Returns:
            True if source is operational
        """
        try:
            # Try to fetch a minimal dataset
            _ = self.get_live_odds(Sport.MLB, MarketType.MONEYLINE)
            return True
        except Exception as e:
            logger.exception(f'Health check failed for {self.__class__.__name__}: {e}')
            return False
