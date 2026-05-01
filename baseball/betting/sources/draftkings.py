"""DraftKings source adapter for US retail lines.

DraftKings is one of the largest US sportsbooks with:
- Wide market availability
- Retail pricing (higher vig than sharp books)
- Good for finding public bias

API: DraftKings doesn't have a public API. We use their internal
API endpoints (undocumented but publicly accessible).

Author: Agent Cascade
Date: 2026-04-30
"""

import logging
from datetime import datetime
from decimal import Decimal

import requests

from baseball.betting.schemas import BettingMarket, BookRegion, MarketStatus, MarketType, Sport
from baseball.betting.sources.base import BaseOddsSource


logger = logging.getLogger(__name__)


class DraftKingsSource(BaseOddsSource):
    """DraftKings API implementation for US retail lines.

    Uses DraftKings' internal API endpoints. These are publicly
    accessible but may change without notice.

    Characteristics of DK lines:
    - Higher vig than sharp books (good for finding public bias)
    - Heavy promo/marketing adjustments
    - Often slow to adjust to sharp action
    - Popular with recreational bettors

    Example:
        >>> dk = DraftKingsSource()
        >>> pinnacle = PinnacleSource(api_key="xxx")
        >>>
        >>> # Compare retail vs sharp
        >>> dk_lines = dk.get_live_odds(Sport.MLB, MarketType.MONEYLINE)
        >>> sharp_lines = pinnacle.get_live_odds(Sport.MLB, MarketType.MONEYLINE)
        >>>
        >>> # Find where DK is off from market
        >>> for dk_line in dk_lines:
        ...     sharp_line = find_matching(sharp_lines, dk_line.game_id)
        ...     if dk_line.odds > sharp_line.odds:  # DK offering better price
        ...         print(f"Value on {dk_line.side}")
    """

    # DraftKings category IDs
    CATEGORY_IDS = {
        Sport.MLB: 8426,      # MLB
        Sport.NBA: 426548,    # NBA
        Sport.NFL: 88808,     # NFL
        Sport.NHL: 34956,     # NHL
    }

    def __init__(
        self,
        base_url: str | None = None,
        **kwargs,
    ) -> None:
        """Initialize DraftKings source.

        Args:
            base_url: Override default API endpoint
        """
        # DraftKings doesn't require API key for basic endpoints
        super().__init__(api_key=None, base_url=base_url, **kwargs)

        self._session = requests.Session()
        self._session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })

        logger.info('Initialized DraftKingsSource')

    def _default_url(self) -> str:
        return 'https://sportsbook.draftkings.com'

    def _make_request(self, endpoint: str, params: dict | None = None) -> dict:
        """Make API request to DraftKings."""
        url = f'{self.base_url}/sites/US-SB/api/v5/{endpoint}'

        try:
            response = self._session.get(
                url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.exception(f'DraftKings API request failed: {e}')
            raise

    def get_live_odds(
        self,
        sport: Sport,
        market_type: MarketType,
        region: BookRegion = BookRegion.US,
        odds_format: str = 'american',
    ) -> list[BettingMarket]:
        """Fetch current odds from DraftKings.

        Args:
            sport: Sport to query
            market_type: Market type
            region: Only US supported
            odds_format: Only american supported

        Returns:
            List of BettingMarket objects
        """
        category_id = self.CATEGORY_IDS.get(sport)
        if not category_id:
            msg = f'Sport {sport} not supported by DraftKings'
            raise ValueError(msg)

        # Fetch events for category
        data = self._make_request(
            'eventgroups',
            {'group': category_id, 'includePromotions': 'true'},
        )

        markets = []

        for event_group in data.get('eventGroup', {}).get('events', []):
            game_id = str(event_group.get('eventId'))
            home_team = event_group.get('teamHome', 'Unknown')
            away_team = event_group.get('teamAway', 'Unknown')
            game_time = datetime.fromisoformat(
                event_group.get('startDate', '').replace('Z', '+00:00'),
            )

            # Get offer categories (markets)
            for offer_category in event_group.get('offerCategories', []):
                category_name = offer_category.get('name', '').lower()

                # Moneyline
                if market_type == MarketType.MONEYLINE and 'moneyline' in category_name:
                    for offer in offer_category.get('offerSubcategoryDescriptors', []):
                        for sub_offer in offer.get('offerSubcategory', {}).get('offers', []):
                            for outcome in sub_offer.get('outcomes', []):
                                side = outcome.get('label', 'Unknown')
                                odds = outcome.get('oddsAmerican', 0)

                                market = BettingMarket(
                                    market_id=f'{game_id}_dk_ml_{side}',
                                    game_id=game_id,
                                    sport=sport,
                                    market_type=market_type,
                                    book='draftkings',
                                    book_region=region,
                                    odds=Decimal(str(odds)),
                                    odds_format='american',
                                    line=None,
                                    side=side,
                                    timestamp=datetime.now(),
                                    game_time=game_time,
                                    status=MarketStatus.OPEN,
                                    home_team=home_team,
                                    away_team=away_team,
                                    is_live=False,
                                    volume=None,
                                    max_bet=None,
                                )
                                markets.append(market)

                # Spread
                elif market_type == MarketType.SPREAD and 'spread' in category_name:
                    for offer in offer_category.get('offerSubcategoryDescriptors', []):
                        for sub_offer in offer.get('offerSubcategory', {}).get('offers', []):
                            for outcome in sub_offer.get('outcomes', []):
                                side = outcome.get('label', 'Unknown')
                                odds = outcome.get('oddsAmerican', 0)
                                line = outcome.get('line', 0)

                                market = BettingMarket(
                                    market_id=f'{game_id}_dk_spread_{side}',
                                    game_id=game_id,
                                    sport=sport,
                                    market_type=market_type,
                                    book='draftkings',
                                    book_region=region,
                                    odds=Decimal(str(odds)),
                                    odds_format='american',
                                    line=Decimal(str(line)) if line else None,
                                    side=side,
                                    timestamp=datetime.now(),
                                    game_time=game_time,
                                    status=MarketStatus.OPEN,
                                    home_team=home_team,
                                    away_team=away_team,
                                    is_live=False,
                                    volume=None,
                                    max_bet=None,
                                )
                                markets.append(market)

                # Total
                elif market_type == MarketType.TOTAL and 'total' in category_name:
                    for offer in offer_category.get('offerSubcategoryDescriptors', []):
                        for sub_offer in offer.get('offerSubcategory', {}).get('offers', []):
                            for outcome in sub_offer.get('outcomes', []):
                                side = outcome.get('label', 'Unknown')  # Over/Under
                                odds = outcome.get('oddsAmerican', 0)
                                line = outcome.get('line', 0)

                                market = BettingMarket(
                                    market_id=f'{game_id}_dk_total_{side}',
                                    game_id=game_id,
                                    sport=sport,
                                    market_type=market_type,
                                    book='draftkings',
                                    book_region=region,
                                    odds=Decimal(str(odds)),
                                    odds_format='american',
                                    line=Decimal(str(line)) if line else None,
                                    side=side,
                                    timestamp=datetime.now(),
                                    game_time=game_time,
                                    status=MarketStatus.OPEN,
                                    home_team=home_team,
                                    away_team=away_team,
                                    is_live=False,
                                    volume=None,
                                    max_bet=None,
                                )
                                markets.append(market)

        logger.info(f'Fetched {len(markets)} markets from DraftKings')
        return self._apply_transforms(markets)

    def get_game_odds(
        self,
        game_id: str,
        market_types: list[MarketType] | None = None,
    ) -> list[BettingMarket]:
        """Fetch odds for specific game."""
        # DraftKings API doesn't have direct game lookup
        # We fetch all and filter
        market_types = market_types or [MarketType.MONEYLINE]
        all_markets = []

        for mt in market_types:
            markets = self.get_live_odds(Sport.MLB, mt)  # Default to MLB
            game_markets = [m for m in markets if m.game_id == game_id]
            all_markets.extend(game_markets)

        return all_markets

    def get_line_movement(
        self,
        game_id: str,
        market_type: MarketType,
        hours: int = 24,
    ) -> list[BettingMarket]:
        """Fetch historical line movements."""
        cache_key = f'dk_history_{game_id}_{market_type.value}'
        return self._cache.get(cache_key, [])

    def get_sharp_lines(
        self,
        sport: Sport,
        market_type: MarketType,
    ) -> list[BettingMarket]:
        """Get sharp lines (DraftKings is retail, not sharp)."""
        # DraftKings is a retail book, not sharp
        # Return empty or raise error
        logger.warning('DraftKings is a retail book, not sharp lines')
        return []

    def health_check(self) -> bool:
        """Check DraftKings API status."""
        try:
            data = self._make_request('eventgroups', {'group': 8426})
            return 'eventGroup' in data
        except Exception as e:
            logger.exception(f'DraftKings health check failed: {e}')
            return False
