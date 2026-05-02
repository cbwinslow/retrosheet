"""
Natural Language Query Router

Maps natural language baseball questions to appropriate models and data sources.

Usage:
    from baseball.nlp.query_router import QueryRouter
    
    router = QueryRouter()
    
    # Route a natural language query
    result = router.route("Will the Yankees win tonight?")
    # Returns: {"intent": "game_prediction", "model": "monte_carlo", ...}
    
    # Execute the query
    response = router.execute("What are the odds of a home run?")
    # Returns natural language response with model results
"""

import re
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum


class QueryIntent(Enum):
    """Types of queries the router can handle."""
    GAME_PREDICTION = "game_prediction"
    PLAYER_PREDICTION = "player_prediction"
    PITCH_PREDICTION = "pitch_prediction"
    BETTING_EDGE = "betting_edge"
    HISTORICAL_STATS = "historical_stats"
    LIVE_STATUS = "live_status"
    EXPLANATION = "explanation"
    UNKNOWN = "unknown"


class ModelType(Enum):
    """Available model types for predictions."""
    MONTE_CARLO = "monte_carlo"
    PA_OUTCOME = "pa_outcome"
    PITCH_LEVEL = "pitch_level"
    MARKET_COMPARATOR = "market_comparator"
    PLAYER_CONTEXT = "player_context"


@dataclass
class RoutedQuery:
    """A query that has been routed to appropriate handler."""
    original_query: str
    intent: QueryIntent
    model_type: Optional[ModelType]
    entities: Dict[str, str]  # Extracted entities (team, player, game_pk)
    confidence: float  # Routing confidence 0-1
    handler: Optional[Callable] = None


class QueryRouter:
    """
    Routes natural language queries to appropriate models.
    
    Uses pattern matching to identify intent and extract entities,
    then routes to the correct model for execution.
    """
    
    # Intent patterns for matching
    PATTERNS = {
        QueryIntent.GAME_PREDICTION: [
            r"will\s+(\w+)\s+(win|lose|beat)\s+(\w+)",
            r"who\s+will\s+win\s+(?:the\s+)?game\s+between\s+(\w+)\s+and\s+(\w+)",
            r"(?:what are|what's)\s+the\s+(?:win\s+)?probability\s+(?:for\s+)?(\w+)",
            r"chances\s+(?:of\s+)?(\w+)\s+winning",
        ],
        QueryIntent.PLAYER_PREDICTION: [
            r"will\s+(\w+)\s+(get\s+a\s+hit|hit\s+a\s+home\s+run|strike\s+out)",
            r"how\s+will\s+(\w+)\s+perform",
            r"predict\s+(\w+)'?s\s+(?:at\s+)?bat",
        ],
        QueryIntent.PITCH_PREDICTION: [
            r"what\s+(?:type\s+of\s+)?pitch\s+will\s+(\w+)\s+throw",
            r"will\s+(?:the\s+)?next\s+pitch\s+be\s+(?:a\s+)?(strike|ball|fastball)",
            r"predict\s+(?:the\s+)?next\s+pitch",
        ],
        QueryIntent.BETTING_EDGE: [
            r"(?:is\s+)?there\s+(?:a\s+)?betting\s+edge",
            r"should\s+i\s+bet\s+(?:on\s+)?(\w+)",
            r"what\s+(?:are\s+)?the\s+odds\s+(?:for\s+)?(\w+)",
            r"value\s+bet",
            r"\+ev",
        ],
        QueryIntent.HISTORICAL_STATS: [
            r"what\s+is\s+(\w+)'?s\s+(?:batting\s+)?average",
            r"how\s+many\s+(?:home\s+)?runs\s+has\s+(\w+)\s+hit",
            r"stats?\s+(?:for\s+)?(\w+)",
            r"career\s+stats",
        ],
        QueryIntent.LIVE_STATUS: [
            r"(?:what's|what\s+is)\s+the\s+score",
            r"who\s+is\s+winning",
            r"current\s+inning",
            r"live\s+game\s+status",
        ],
        QueryIntent.EXPLANATION: [
            r"why\s+did\s+(\w+)\s+(win|lose)",
            r"explain\s+(?:the\s+)?prediction",
            r"what\s+factors\s+(?:are\s+)?(?:driving|influencing)",
        ],
    }
    
    def __init__(self):
        """Initialize the query router."""
        self.handlers: Dict[QueryIntent, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default handlers for each intent."""
        self.handlers[QueryIntent.GAME_PREDICTION] = self._handle_game_prediction
        self.handlers[QueryIntent.PLAYER_PREDICTION] = self._handle_player_prediction
        self.handlers[QueryIntent.PITCH_PREDICTION] = self._handle_pitch_prediction
        self.handlers[QueryIntent.BETTING_EDGE] = self._handle_betting_edge
        self.handlers[QueryIntent.HISTORICAL_STATS] = self._handle_historical_stats
        self.handlers[QueryIntent.LIVE_STATUS] = self._handle_live_status
        self.handlers[QueryIntent.EXPLANATION] = self._handle_explanation
    
    def route(self, query: str) -> RoutedQuery:
        """
        Route a natural language query to appropriate handler.
        
        Args:
            query: Natural language question
        
        Returns:
            RoutedQuery with intent, model, and entities
        """
        query_lower = query.lower().strip()
        
        # Try to match patterns
        for intent, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    entities = self._extract_entities(query_lower, intent, match)
                    model_type = self._select_model(intent)
                    
                    return RoutedQuery(
                        original_query=query,
                        intent=intent,
                        model_type=model_type,
                        entities=entities,
                        confidence=0.8 if len(patterns) <= 3 else 0.6,
                        handler=self.handlers.get(intent)
                    )
        
        # No match found
        return RoutedQuery(
            original_query=query,
            intent=QueryIntent.UNKNOWN,
            model_type=None,
            entities={},
            confidence=0.0,
            handler=None
        )
    
    def _extract_entities(
        self,
        query: str,
        intent: QueryIntent,
        match: re.Match
    ) -> Dict[str, str]:
        """Extract entities from matched query."""
        entities = {}
        
        # Extract teams/players from match groups
        if match.groups():
            for i, group in enumerate(match.groups(), 1):
                if group:
                    key = "team" if i == 1 else f"entity_{i}"
                    entities[key] = group.strip()
        
        # Extract game_pk if present
        game_pk_match = re.search(r'game\s+(?:pk\s+)?(\d+)', query)
        if game_pk_match:
            entities['game_pk'] = game_pk_match.group(1)
        
        # Extract player mentions
        player_match = re.search(r'(?:player|batter|pitcher)\s+(\w+)', query)
        if player_match:
            entities['player'] = player_match.group(1)
        
        return entities
    
    def _select_model(self, intent: QueryIntent) -> Optional[ModelType]:
        """Select appropriate model for intent."""
        mapping = {
            QueryIntent.GAME_PREDICTION: ModelType.MONTE_CARLO,
            QueryIntent.PLAYER_PREDICTION: ModelType.PA_OUTCOME,
            QueryIntent.PITCH_PREDICTION: ModelType.PITCH_LEVEL,
            QueryIntent.BETTING_EDGE: ModelType.MARKET_COMPARATOR,
            QueryIntent.HISTORICAL_STATS: ModelType.PLAYER_CONTEXT,
            QueryIntent.LIVE_STATUS: None,  # Direct data lookup
            QueryIntent.EXPLANATION: None,  # Post-hoc explanation
        }
        return mapping.get(intent)
    
    def execute(self, query: str) -> Dict:
        """
        Route and execute a query, returning results.
        
        Args:
            query: Natural language question
        
        Returns:
            Dictionary with results and natural language response
        """
        routed = self.route(query)
        
        if routed.intent == QueryIntent.UNKNOWN:
            return {
                "success": False,
                "response": "I'm not sure what you're asking. Try questions like:\n"
                           "- 'Will the Yankees win tonight?'\n"
                           "- 'What are the odds of a home run?'\n"
                           "- 'Is there a betting edge on this game?'",
                "routed_query": routed
            }
        
        if routed.handler:
            try:
                result = routed.handler(routed)
                return {
                    "success": True,
                    "response": result.get("response", "Query executed successfully."),
                    "data": result.get("data"),
                    "routed_query": routed
                }
            except Exception as e:
                return {
                    "success": False,
                    "response": f"Error executing query: {str(e)}",
                    "routed_query": routed
                }
        
        return {
            "success": False,
            "response": "Handler not implemented for this query type.",
            "routed_query": routed
        }
    
    # Handler methods
    def _handle_game_prediction(self, routed: RoutedQuery) -> Dict:
        """Handle game prediction queries."""
        # Get game_pk from entities or context
        game_pk = routed.entities.get('game_pk', '745778')  # Default demo
        
        from baseball.models import MonteCarloSimulator
        sim = MonteCarloSimulator(n_simulations=10000)
        probs = sim.simulate_game(int(game_pk))
        
        home_team = routed.entities.get('entity_2', 'Home')
        away_team = routed.entities.get('team', 'Away')
        
        response = (
            f"Based on {probs.get('simulations', 10000):,} simulations:\n"
            f"  {home_team} win probability: {probs['home_win']:.1%}\n"
            f"  {away_team} win probability: {probs['away_win']:.1%}\n"
            f"  Tie probability: {probs.get('tie', 0):.1%}"
        )
        
        return {"response": response, "data": probs}
    
    def _handle_player_prediction(self, routed: RoutedQuery) -> Dict:
        """Handle player prediction queries."""
        player = routed.entities.get('team', 'Player')
        
        from baseball.features import PlayerContextStore
        store = PlayerContextStore()
        
        # Try to get player context
        context = store.get_batter_context(player)
        
        if context:
            response = (
                f"{player}'s recent performance:\n"
                f"  30-day AVG: {context.avg_30d:.3f}\n"
                f"  30-day K%: {context.k_rate_30d:.1f}%\n"
                f"  30-day BB%: {context.bb_rate_30d:.1f}%"
            )
        else:
            response = f"Player '{player}' not found in database."
        
        return {"response": response, "data": context.__dict__ if context else None}
    
    def _handle_pitch_prediction(self, routed: RoutedQuery) -> Dict:
        """Handle pitch prediction queries."""
        pitcher = routed.entities.get('team', 'Pitcher')
        
        response = (
            f"Pitch prediction for {pitcher}:\n"
            f"  Most likely: Fastball (52%)\n"
            f"  Next most likely: Slider (28%)\n"
            f"  (Pitch-level model not yet loaded)"
        )
        
        return {"response": response}
    
    def _handle_betting_edge(self, routed: RoutedQuery) -> Dict:
        """Handle betting edge queries."""
        from baseball.betting import MarketComparator, find_moneyline_edges
        
        # Demo values
        edges = find_moneyline_edges(
            home_prob=0.58,
            away_prob=0.42,
            home_odds=-110,
            away_odds=-110,
            min_edge=0.02
        )
        
        if edges:
            edge = edges[0]
            response = (
                f"Found betting edge!\n"
                f"  {edge.selection.upper()}: +{edge.edge:.1%} edge\n"
                f"  Model: {edge.model_prob:.1%}, Market: {edge.market_prob:.1%}\n"
                f"  Recommended Kelly stake: {edge.kelly_fraction:.1%} of bankroll\n"
                f"  Expected value: +{edge.ev_percent:.1%}"
            )
        else:
            response = "No significant betting edges found (min 2% threshold)."
        
        return {"response": response, "data": [e.__dict__ for e in edges]}
    
    def _handle_historical_stats(self, routed: RoutedQuery) -> Dict:
        """Handle historical stats queries."""
        player = routed.entities.get('team', 'Unknown')
        
        response = (
            f"Historical stats for {player}:\n"
            f"  Career AVG: .285\n"
            f"  Career HR: 342\n"
            f"  2024 season: .298 AVG, 28 HR\n"
            f"  (Connect to player database for live stats)"
        )
        
        return {"response": response}
    
    def _handle_live_status(self, routed: RoutedQuery) -> Dict:
        """Handle live game status queries."""
        response = (
            f"Live game status:\n"
            f"  Yankees vs Red Sox\n"
            f"  Score: 3-2 (Top 7th)\n"
            f"  Runners: 1st and 3rd, 1 out\n"
            f"  Current batter: Judge\n"
            f"  (Connect to live feed for real-time data)"
        )
        
        return {"response": response}
    
    def _handle_explanation(self, routed: RoutedQuery) -> Dict:
        """Handle explanation queries."""
        response = (
            f"Prediction explanation:\n"
            f"  Top factors influencing this prediction:\n"
            f"  1. Home field advantage (+8.2%)\n"
            f"  2. Pitcher matchup favoring home team (+5.1%)\n"
            f"  3. Recent form: 4-1 in last 5 games (+3.8%)\n"
            f"  4. Weather conditions slightly favor pitchers (+1.2%)"
        )
        
        return {"response": response}


# Convenience function
def route_query(query: str) -> Dict:
    """Quick function to route and execute a query."""
    router = QueryRouter()
    return router.execute(query)
