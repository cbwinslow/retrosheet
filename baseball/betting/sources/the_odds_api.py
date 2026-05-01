"""The Odds API source adapter.

Real-time odds from odds-api.com covering multiple sportsbooks.
Supports MLB, NBA, NFL, NHL, soccer, and more.

API Documentation: https://the-odds-api.com/liveapi/guides/v4/
Pricing: $29/mo for 500 requests/day

Author: Agent Cascade
Date: 2026-04-30
"""

import requests
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
import logging

from baseball.betting.sources.base import BaseOddsSource
from baseball.betting.schemas import (
    BettingMarket, MarketType, Sport, BookRegion,
    MarketStatus
)

logger = logging.getLogger(__name__)


class TheOddsApiSource(BaseOddsSource):
    """The Odds API implementation for real-time betting lines.
    
    Covers 20+ sportsbooks including:
    - DraftKings, FanDuel, BetMGM (US retail)
    - Pinnacle, Betfair (sharp)
    - Bovada, BetOnline (offshore)
    
    Example:
        >>> source = TheOddsApiSource(api_key="your_key")
        >>> markets = source.get_live_odds(Sport.MLB, MarketType.MONEYLINE)
        >>> game_lines = source.get_game_odds("716190")
    """
    
    SPORT_MAP = {
        Sport.MLB: "baseball_mlb",
        Sport.NBA: "basketball_nba",
        Sport.NFL: "americanfootball_nfl",
        Sport.NHL: "icehockey_nhl",
        Sport.NCAAB: "basketball_ncaab",
        Sport.NCAAF: "americanfootball_ncaaf"
    }
    
    MARKET_MAP = {
        MarketType.MONEYLINE: "h2h",
        MarketType.SPREAD: "spreads",
        MarketType.TOTAL: "totals"
    }
    
    REGION_MAP = {
        BookRegion.US: "us",
        BookRegion.UK: "uk",
        BookRegion.EU: "eu",
        BookRegion.AU: "au"
    }
    
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: int = 30,
        **kwargs
    ):
        super().__init__(api_key=api_key, base_url=base_url, timeout=timeout, **kwargs)
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})
    
    def _default_url(self) -> str:
        return "https://api.the-odds-api.com/v4"
    
    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        url = f"{self.base_url}/{endpoint}"
        params = params or {}
        params["apiKey"] = self.api_key
        
        logger.debug(f"API request: {url}")
        
        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    def get_live_odds(
        self,
        sport: Sport,
        market_type: MarketType,
        region: BookRegion = BookRegion.US,
        odds_format: str = "american"
    ) -> List[BettingMarket]:
        sport_key = self.SPORT_MAP.get(sport)
        if not sport_key:
            raise ValueError(f"Sport {sport} not supported")
        
        markets_key = self.MARKET_MAP.get(market_type, "h2h")
        region_code = self.REGION_MAP.get(region, "us")
        
        endpoint = f"sports/{sport_key}/odds"
        params = {
            "regions": region_code,
            "markets": markets_key,
            "oddsFormat": odds_format
        }
        
        data = self._make_request(endpoint, params)
        
        markets = []
        for game in data:
            game_id = str(game.get("id"))
            home_team = game.get("home_team", "Unknown")
            away_team = game.get("away_team", "Unknown")
            commence_time = datetime.fromisoformat(
                game.get("commence_time", "").replace("Z", "+00:00")
            )
            
            for book in game.get("bookmakers", []):
                book_key = book.get("key", "unknown")
                
                for market in book.get("markets", []):
                    market_key = market.get("key", markets_key)
                    last_update = datetime.fromisoformat(
                        market.get("last_update", "").replace("Z", "+00:00")
                    )
                    
                    for outcome in market.get("outcomes", []):
                        market_obj = BettingMarket(
                            market_id=f"{game_id}_{book_key}_{market_key}_{outcome.get('name', 'unknown')}",
                            game_id=game_id,
                            sport=sport,
                            market_type=market_type,
                            book=book_key,
                            book_region=region,
                            odds=Decimal(str(outcome.get("price", 0))),
                            odds_format=odds_format,
                            line=Decimal(str(outcome.get("point", 0))) if "point" in outcome else None,
                            side=outcome.get("name"),
                            timestamp=last_update,
                            game_time=commence_time,
                            status=MarketStatus.OPEN,
                            home_team=home_team,
                            away_team=away_team,
                            is_live=False,
                            volume=None,
                            max_bet=None
                        )
                        markets.append(market_obj)
        
        logger.info(f"Fetched {len(markets)} markets from The Odds API")
        return self._apply_transforms(markets)
    
    def get_game_odds(
        self,
        game_id: str,
        market_types: Optional[List[MarketType]] = None
    ) -> List[BettingMarket]:
        endpoint = f"sports/events/{game_id}"
        params = {"oddsFormat": "american"}
        
        if market_types:
            markets = ",".join(
                self.MARKET_MAP.get(mt, "h2h") for mt in market_types
            )
            params["markets"] = markets
        
        try:
            data = self._make_request(endpoint, params)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Game {game_id} not found")
                return []
            raise
        
        markets = []
        sport_key = data.get("sport_key", "")
        sport = self._reverse_sport_map(sport_key)
        
        home_team = data.get("home_team", "Unknown")
        away_team = data.get("away_team", "Unknown")
        commence_time = datetime.fromisoformat(
            data.get("commence_time", "").replace("Z", "+00:00")
        )
        
        for book in data.get("bookmakers", []):
            book_key = book.get("key", "unknown")
            
            for market in book.get("markets", []):
                market_key = market.get("key", "h2h")
                market_type = self._reverse_market_map(market_key)
                
                last_update = datetime.fromisoformat(
                    market.get("last_update", "").replace("Z", "+00:00")
                )
                
                for outcome in market.get("outcomes", []):
                    market_obj = BettingMarket(
                        market_id=f"{game_id}_{book_key}_{market_key}_{outcome.get('name', 'unknown')}",
                        game_id=game_id,
                        sport=sport,
                        market_type=market_type,
                        book=book_key,
                        book_region=BookRegion.US,
                        odds=Decimal(str(outcome.get("price", 0))),
                        odds_format="american",
                        line=Decimal(str(outcome.get("point", 0))) if "point" in outcome else None,
                        side=outcome.get("name"),
                        timestamp=last_update,
                        game_time=commence_time,
                        status=MarketStatus.OPEN,
                        home_team=home_team,
                        away_team=away_team,
                        is_live=False,
                        volume=None,
                        max_bet=None
                    )
                    markets.append(market_obj)
        
        return self._apply_transforms(markets)
    
    def get_line_movement(
        self,
        game_id: str,
        market_type: MarketType,
        hours: int = 24
    ) -> List[BettingMarket]:
        cache_key = f"line_history_{game_id}_{market_type.value}"
        current = self.get_game_odds(game_id, [market_type])
        history = self._cache.get(cache_key, [])
        history.extend(current)
        self._cache[cache_key] = history
        return sorted(history, key=lambda m: m.timestamp)
    
    def get_sharp_lines(
        self,
        sport: Sport,
        market_type: MarketType
    ) -> List[BettingMarket]:
        all_markets = self.get_live_odds(sport, market_type, BookRegion.US)
        sharp_books = {"pinnacle", "betfair", "betcris", "betonline", "circasports"}
        return list(filter(lambda m: m.book.lower() in sharp_books, all_markets))
    
    def _reverse_sport_map(self, sport_key: str) -> Sport:
        reverse = {v: k for k, v in self.SPORT_MAP.items()}
        return reverse.get(sport_key, Sport.MLB)
    
    def _reverse_market_map(self, market_key: str) -> MarketType:
        reverse = {v: k for k, v in self.MARKET_MAP.items()}
        return reverse.get(market_key, MarketType.MONEYLINE)
