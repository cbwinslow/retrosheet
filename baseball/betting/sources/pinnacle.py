"""Pinnacle source adapter for sharp lines.

Pinnacle offers:
- Industry-leading low vig lines
- High limits (indicates sharp action)
- Fast line movements
- Best for model calibration

API Documentation: https://github.com/pinnacleapi/API-reference
Note: Pinnacle API requires approval and has geographic restrictions

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


class PinnacleSource(BaseOddsSource):
    """Pinnacle API implementation for sharp lines.

    Pinnacle is the gold standard for "true" market prices because:
    - Lowest vig (1-2% vs 5-7% at retail books)
    - Accepts sharp action without limiting
    - Lines adjust quickly to new information

    Example:
        >>> source = PinnacleSource(api_key="xxx")
        >>>
        >>> # Get sharp moneyline
        >>> markets = source.get_sharp_lines(Sport.MLB, MarketType.MONEYLINE)
        >>>
        >>> # Use as calibration for retail lines
        >>> sharp_prob = source.calculate_implied_probability(markets[0].odds)
    """

    # Pinnacle sport IDs
    SPORT_IDS = {
        Sport.MLB: 246,      # Baseball - MLB
        Sport.NBA: 487,      # Basketball - NBA
        Sport.NFL: 879,      # Football - NFL
        Sport.NHL: 1456,     # Hockey - NHL
        Sport.NCAAB: 493,    # Basketball - NCAAB
        Sport.NCAAF: 889,   # Football - NCAAF
    }

    def __init__(
        self,
        api_key: str,
        username: str,
        password: str,
        base_url: str | None = None,
        **kwargs,
    ) -> None:
        """Initialize Pinnacle source.

        Args:
            api_key: Pinnacle API key
            username: Pinnacle account username
            password: Pinnacle account password
            base_url: Override default API endpoint
        """
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self.username = username
        self.password = password

        self._session = requests.Session()
        self._auth_token: str | None = None

        logger.info('Initialized PinnacleSource')

    def _default_url(self) -> str:
        return 'https://api.pinnacle.com'

    def _authenticate(self) -> bool:
        """Authenticate with Pinnacle API."""
        try:
            response = self._session.post(
                f'{self.base_url}/v1/customers/authenticate',
                json={
                    'username': self.username,
                    'password': self.password,
                },
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                self._auth_token = data.get('token')
                self._session.headers.update({
                    'Authorization': f'Bearer {self._auth_token}',
                })
                logger.info('Pinnacle authentication successful')
                return True
            logger.error(f'Pinnacle auth failed: {response.status_code}')
            return False

        except Exception as e:
            logger.exception(f'Pinnacle auth error: {e}')
            return False

    def _make_request(self, endpoint: str, params: dict | None = None) -> dict:
        """Make authenticated API request."""
        if not self._auth_token and not self._authenticate():
            msg = 'Failed to authenticate with Pinnacle'
            raise RuntimeError(msg)

        url = f'{self.base_url}{endpoint}'

        try:
            response = self._session.get(
                url,
                params=params,
                timeout=self.timeout,
            )

            # Handle token expiration
            if response.status_code == 401:
                logger.info('Token expired, re-authenticating...')
                if self._authenticate():
                    response = self._session.get(url, params=params, timeout=self.timeout)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.exception(f'Pinnacle API request failed: {e}')
            raise

    def get_live_odds(
        self,
        sport: Sport,
        market_type: MarketType,
        region: BookRegion = BookRegion.US,
        odds_format: str = 'american',
    ) -> list[BettingMarket]:
        """Fetch current odds from Pinnacle.

        Args:
            sport: Sport to query
            market_type: Market type
            region: Ignored (Pinnacle is global)
            odds_format: american, decimal, or malay

        Returns:
            List of BettingMarket objects
        """
        sport_id = self.SPORT_IDS.get(sport)
        if not sport_id:
            msg = f'Sport {sport} not supported by Pinnacle'
            raise ValueError(msg)

        # Map market type to Pinnacle API
        if market_type == MarketType.MONEYLINE or market_type == MarketType.SPREAD or market_type == MarketType.TOTAL:
            endpoint = f'/v1/odds?sportId={sport_id}&oddsFormat={odds_format}'
        else:
            msg = f'Market type {market_type} not supported'
            raise ValueError(msg)

        data = self._make_request(endpoint)

        markets = []
        for event in data.get('leagues', []):
            for game in event.get('events', []):
                game_id = str(game.get('id'))
                home_team = game.get('homeTeam', 'Unknown')
                away_team = game.get('awayTeam', 'Unknown')

                # Parse period (0 = full game, 1 = 1st half, etc.)
                for period in game.get('periods', []):
                    period_num = period.get('number', 0)
                    if period_num != 0:  # Skip non-full-game lines
                        continue

                    # Moneyline
                    if market_type == MarketType.MONEYLINE:
                        for line in period.get('moneyline', {}).get('lines', []):
                            for price in line.get('prices', []):
                                side = 'Home' if price.get('designation') == 'home' else 'Away'

                                market = BettingMarket(
                                    market_id=f'{game_id}_pinnacle_ml_{side}',
                                    game_id=game_id,
                                    sport=sport,
                                    market_type=market_type,
                                    book='pinnacle',
                                    book_region=BookRegion.US,
                                    odds=Decimal(str(price.get('price', 0))),
                                    odds_format=odds_format,
                                    line=None,
                                    side=side,
                                    timestamp=datetime.now(),
                                    game_time=datetime.fromtimestamp(game.get('startTime', 0)),
                                    status=MarketStatus.OPEN,
                                    home_team=home_team,
                                    away_team=away_team,
                                    is_live=False,
                                    volume=None,
                                    max_bet=None,
                                )
                                markets.append(market)

                    # Spreads
                    elif market_type == MarketType.SPREAD:
                        for line in period.get('spreads', {}).get('lines', []):
                            for price in line.get('prices', []):
                                side = 'Home' if price.get('designation') == 'home' else 'Away'

                                market = BettingMarket(
                                    market_id=f'{game_id}_pinnacle_spread_{side}',
                                    game_id=game_id,
                                    sport=sport,
                                    market_type=market_type,
                                    book='pinnacle',
                                    book_region=BookRegion.US,
                                    odds=Decimal(str(price.get('price', 0))),
                                    odds_format=odds_format,
                                    line=Decimal(str(line.get('spread', 0))),
                                    side=side,
                                    timestamp=datetime.now(),
                                    game_time=datetime.fromtimestamp(game.get('startTime', 0)),
                                    status=MarketStatus.OPEN,
                                    home_team=home_team,
                                    away_team=away_team,
                                    is_live=False,
                                    volume=None,
                                    max_bet=None,
                                )
                                markets.append(market)

                    # Totals
                    elif market_type == MarketType.TOTAL:
                        for line in period.get('totals', {}).get('lines', []):
                            for price in line.get('prices', []):
                                side = 'Over' if price.get('designation') == 'over' else 'Under'

                                market = BettingMarket(
                                    market_id=f'{game_id}_pinnacle_total_{side}',
                                    game_id=game_id,
                                    sport=sport,
                                    market_type=market_type,
                                    book='pinnacle',
                                    book_region=BookRegion.US,
                                    odds=Decimal(str(price.get('price', 0))),
                                    odds_format=odds_format,
                                    line=Decimal(str(line.get('points', 0))),
                                    side=side,
                                    timestamp=datetime.now(),
                                    game_time=datetime.fromtimestamp(game.get('startTime', 0)),
                                    status=MarketStatus.OPEN,
                                    home_team=home_team,
                                    away_team=away_team,
                                    is_live=False,
                                    volume=None,
                                    max_bet=None,
                                )
                                markets.append(market)

        logger.info(f'Fetched {len(markets)} markets from Pinnacle')
        return self._apply_transforms(markets)

    def get_game_odds(
        self,
        game_id: str,
        market_types: list[MarketType] | None = None,
    ) -> list[BettingMarket]:
        """Fetch odds for specific game.

        Note: Pinnacle API doesn't have direct game lookup.
        We fetch all and filter.
        """
        market_types = market_types or [MarketType.MONEYLINE]
        all_markets = []

        for mt in market_types:
            try:
                # Determine sport from game_id (or require sport param)
                markets = self.get_live_odds(Sport.MLB, mt)  # Default to MLB
                game_markets = [m for m in markets if m.game_id == game_id]
                all_markets.extend(game_markets)
            except Exception as e:
                logger.exception(f'Failed to fetch {mt} for game {game_id}: {e}')

        return all_markets

    def get_line_movement(
        self,
        game_id: str,
        market_type: MarketType,
        hours: int = 24,
    ) -> list[BettingMarket]:
        """Fetch historical line movements.

        Pinnacle API doesn't provide historical data.
        We cache locally and return from cache.
        """
        cache_key = f'pinnacle_history_{game_id}_{market_type.value}'
        return self._cache.get(cache_key, [])

    def get_sharp_lines(
        self,
        sport: Sport,
        market_type: MarketType,
    ) -> list[BettingMarket]:
        """Get sharp lines (Pinnacle is the sharp book)."""
        # All Pinnacle lines are sharp
        return self.get_live_odds(sport, market_type)

    def health_check(self) -> bool:
        """Check Pinnacle API status."""
        try:
            return self._authenticate()
        except Exception as e:
            logger.exception(f'Pinnacle health check failed: {e}')
            return False
