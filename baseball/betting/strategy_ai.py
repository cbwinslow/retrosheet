"""AI-powered betting strategy generator and bet explainer.

Uses LLM (Letta-compatible) for:
- Strategy generation based on constraints
- Bet explanation and rationale
- Stake optimization reasoning
- Market analysis summaries

Author: Agent Cascade
Date: 2026-04-30
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from baseball.betting.schemas import (
    BettingStrategy, BetOpportunity, PlacedBet,
    StrategyConstraints, BetRecommendation
)

logger = logging.getLogger(__name__)


class BettingStrategyAI:
    """AI-powered strategy generator and bet explainer.
    
    This class provides AI capabilities for betting without requiring
    Letta specifically. It uses a pluggable LLM interface that can
    work with:
    - Letta (if available)
    - OpenAI GPT
    - Anthropic Claude
    - Local models (Llama, etc.)
    
    The LLM is used for:
    1. Strategy generation from natural language constraints
    2. Bet explanations (why this edge exists)
    3. Stake optimization reasoning
    4. Market analysis summaries
    
    Example:
        >>> ai = BettingStrategyAI(llm_client=openai_client)
        >>> 
        >>> # Generate strategy from natural language
        >>> strategy = ai.generate_strategy(
        ...     name="Aggressive Value",
        ...     description="Focus on high edges, accept higher risk"
        ... )
        >>> 
        >>> # Explain a bet
        >>> explanation = ai.explain_bet(opportunity, sim_details)
        >>> print(explanation.rationale)
    """
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        on_strategy_generated: Optional[Callable] = None,
        on_explanation_created: Optional[Callable] = None
    ):
        """Initialize AI strategy generator.
        
        Args:
            llm_client: LLM client (OpenAI, Anthropic, or Letta-compatible)
            model: Model name to use
            temperature: LLM temperature (creativity)
            max_tokens: Max response tokens
            on_strategy_generated: Event hook for new strategies
            on_explanation_created: Event hook for explanations
        """
        self.llm_client = llm_client
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Event hooks (Event Pattern)
        self._on_strategy_generated = on_strategy_generated or (lambda s: None)
        self._on_explanation_created = on_explanation_created or (lambda e: None)
        
        logger.info(f"BettingStrategyAI initialized (model: {model})")
    
    # ===================================================================
    # Strategy Generation
    # ===================================================================
    
    def generate_strategy(
        self,
        name: str,
        description: str,
        constraints: Optional[StrategyConstraints] = None,
        risk_profile: str = "moderate",
        target_sports: List[str] = None,
        prompt_template: Optional[str] = None
    ) -> Optional[BettingStrategy]:
        """Generate a betting strategy from natural language description.
        
        Args:
            name: Strategy name
            description: Natural language strategy description
            constraints: Optional hard constraints
            risk_profile: conservative, moderate, or aggressive
            target_sports: List of sports to focus on
            prompt_template: Custom prompt override
            
        Returns:
            Generated BettingStrategy or None if no LLM
            
        Example:
            >>> strategy = ai.generate_strategy(
            ...     name="MLB Underdog Hunter",
            ...     description="Focus on underdogs with model edges >5%, 
            ...                  avoid heavy favorites, max 2% bankroll per bet"
            ... )
        """
        if not self.llm_client:
            logger.warning("No LLM client available, using default strategy")
            return self._create_default_strategy(name, description, constraints)
        
        # Build prompt
        if prompt_template:
            prompt = prompt_template
        else:
            prompt = self._build_strategy_prompt(
                name, description, constraints, risk_profile, target_sports
            )
        
        try:
            # Call LLM
            response = self._call_llm(prompt)
            
            # Parse response into strategy parameters
            strategy_params = self._parse_strategy_response(response)
            
            # Create strategy
            strategy = BettingStrategy(
                strategy_id=f"ai_{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}",
                name=name,
                description=description,
                constraints=strategy_params.get('constraints', constraints or StrategyConstraints()),
                min_edge=Decimal(str(strategy_params.get('min_edge', 0.05))),
                max_bet_pct=Decimal(str(strategy_params.get('max_bet_pct', 0.02))),
                kelly_fraction=Decimal(str(strategy_params.get('kelly_fraction', 0.25))),
                target_markets=strategy_params.get('target_markets', ['moneyline']),
                stake_method=strategy_params.get('stake_method', 'kelly'),
                filters=strategy_params.get('filters', {}),
                is_active=True,
                created_at=datetime.now(),
                ai_generated=True,
                ai_prompt=prompt,
                ai_rationale=strategy_params.get('rationale', '')
            )
            
            # Emit event (Event Pattern)
            self._on_strategy_generated(strategy)
            
            logger.info(f"Generated AI strategy: {name}")
            return strategy
            
        except Exception as e:
            logger.error(f"Strategy generation failed: {e}")
            return self._create_default_strategy(name, description, constraints)
    
    def _build_strategy_prompt(
        self,
        name: str,
        description: str,
        constraints: Optional[StrategyConstraints],
        risk_profile: str,
        target_sports: List[str]
    ) -> str:
        """Build LLM prompt for strategy generation."""
        return f"""You are an expert sports betting strategist. Create a betting strategy based on the following description.

Strategy Name: {name}
Description: {description}
Risk Profile: {risk_profile}
Target Sports: {', '.join(target_sports or ['MLB'])}

Please provide the strategy parameters in this exact format:

MIN_EDGE: [decimal between 0.01 and 0.15]
MAX_BET_PCT: [decimal between 0.01 and 0.10]
KELLY_FRACTION: [decimal between 0.1 and 1.0]
TARGET_MARKETS: [comma-separated list: moneyline, spread, total, team_total]
STAKE_METHOD: [kelly, flat, or confidence]
FILTERS: {{
    "min_odds": [positive integer for min odds],
    "max_odds": [positive integer for max odds],
    "avoid_teams": [list of teams to avoid or empty],
    "prefer_underdogs": [true or false]
}}

RATIONALE: [2-3 sentence explanation of why this strategy should work]

Constraints:
{self._format_constraints(constraints) if constraints else 'None specified'}

Respond ONLY with the parameters above, no additional text."""

    def _format_constraints(self, constraints: StrategyConstraints) -> str:
        """Format constraints for prompt."""
        lines = []
        if constraints.max_bets_per_day:
            lines.append(f"- Max {constraints.max_bets_per_day} bets per day")
        if constraints.max_exposure_pct:
            lines.append(f"- Max {constraints.max_exposure_pct:.1%} bankroll exposure")
        if constraints.min_odds:
            lines.append(f"- Minimum odds: +{constraints.min_odds}")
        if constraints.max_odds:
            lines.append(f"- Maximum odds: {constraints.max_odds}")
        if constraints.avoid_teams:
            lines.append(f"- Avoid teams: {', '.join(constraints.avoid_teams)}")
        return '\n'.join(lines) if lines else 'No hard constraints'

    def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt."""
        # This would call the actual LLM client
        # Placeholder for now
        if hasattr(self.llm_client, 'chat'):
            # Letta-style interface
            return self.llm_client.chat(prompt)
        elif hasattr(self.llm_client, 'completions'):
            # OpenAI-style interface
            response = self.llm_client.completions.create(
                model=self.model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            return response.choices[0].text
        else:
            raise RuntimeError("Unknown LLM client interface")

    def _parse_strategy_response(self, response: str) -> Dict:
        """Parse LLM response into strategy parameters."""
        params = {}
        
        for line in response.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key == 'filters':
                    # Parse JSON-like filters
                    try:
                        import json
                        params[key] = json.loads(value)
                    except:
                        params[key] = {}
                elif key == 'target_markets':
                    params[key] = [m.strip() for m in value.split(',')]
                elif key == 'rationale':
                    params[key] = value
                else:
                    try:
                        params[key] = float(value)
                    except:
                        params[key] = value
        
        return params

    def _create_default_strategy(
        self,
        name: str,
        description: str,
        constraints: Optional[StrategyConstraints]
    ) -> BettingStrategy:
        """Create a default strategy when LLM is unavailable."""
        return BettingStrategy(
            strategy_id=f"default_{name.lower().replace(' ', '_')}",
            name=name,
            description=description,
            constraints=constraints or StrategyConstraints(),
            min_edge=Decimal("0.05"),
            max_bet_pct=Decimal("0.02"),
            kelly_fraction=Decimal("0.25"),
            target_markets=['moneyline'],
            stake_method='kelly',
            filters={},
            is_active=True,
            created_at=datetime.now(),
            ai_generated=False
        )

    # ===================================================================
    # Bet Explanation
    # ===================================================================
    
    def explain_bet(
        self,
        opportunity: BetOpportunity,
        sim_details: Dict[str, Any],
        market_context: Optional[Dict] = None,
        include_numbers: bool = True
    ) -> str:
        """Generate AI explanation for a bet opportunity.
        
        Args:
            opportunity: The betting opportunity
            sim_details: Simulation details (features, probabilities)
            market_context: Market context (line movement, sharp action)
            include_numbers: Include specific odds/edges in explanation
            
        Returns:
            Natural language explanation of why this is a good bet
            
        Example:
            >>> explanation = ai.explain_bet(
            ...     opportunity=opp,
            ...     sim_details={
            ...         'home_prob': 0.58,
            ...         'key_factors': ['bullpen_advantage', 'weather_favorable']
            ...     },
            ...     market_context={'sharp_line': -120, 'retail_line': -110}
            ... )
            >>> print(explanation)
            "The model sees value in the home team due to bullpen fatigue..."
        """
        if not self.llm_client:
            return self._generate_simple_explanation(opportunity, include_numbers)
        
        prompt = f"""Explain why this is a good betting opportunity:

Game: {opportunity.market.home_team} vs {opportunity.market.away_team}
Bet: {opportunity.market.side} {opportunity.market.market_type.value}
Odds: {opportunity.market.odds}
Edge: {opportunity.edge:.1%}
Model Probability: {opportunity.model_probability:.1%}
Market Probability: {opportunity.market_probability:.1%}

Simulation Details:
{self._format_sim_details(sim_details)}

Market Context:
{self._format_market_context(market_context) if market_context else 'No additional context'}

Provide a concise 2-3 sentence explanation suitable for a bettor. Focus on:
1. Why the edge exists
2. Key factors driving the model's confidence
3. Any market inefficiencies being exploited

{'Include specific numbers and percentages.' if include_numbers else 'Keep it conceptual, minimize numbers.'}"""

        try:
            return self._call_llm(prompt)
        except Exception as e:
            logger.error(f"Bet explanation failed: {e}")
            return self._generate_simple_explanation(opportunity, include_numbers)

    def _generate_simple_explanation(
        self,
        opportunity: BetOpportunity,
        include_numbers: bool
    ) -> str:
        """Generate simple explanation without LLM."""
        if include_numbers:
            return (
                f"The model estimates a {opportunity.model_probability:.1%} chance of winning, "
                f"while the market implies only {opportunity.market_probability:.1%}. "
                f"This {opportunity.edge:.1%} edge represents value."
            )
        else:
            return (
                f"The model sees more value in this bet than the market price suggests. "
                f"Key factors likely include team matchups, recent form, and situational advantages."
            )

    def _format_sim_details(self, details: Dict) -> str:
        """Format simulation details for prompt."""
        lines = []
        for key, value in details.items():
            if isinstance(value, list):
                lines.append(f"- {key}: {', '.join(str(v) for v in value)}")
            elif isinstance(value, float):
                lines.append(f"- {key}: {value:.1%}" if value < 1 else f"- {key}: {value:.1f}")
            else:
                lines.append(f"- {key}: {value}")
        return '\n'.join(lines)

    def _format_market_context(self, context: Dict) -> str:
        """Format market context for prompt."""
        lines = []
        if 'sharp_line' in context:
            lines.append(f"Sharp book line: {context['sharp_line']}")
        if 'retail_line' in context:
            lines.append(f"Retail book line: {context['retail_line']}")
        if 'line_movement' in context:
            lines.append(f"Line moved {context['line_movement']:.1%} toward this side")
        return '\n'.join(lines) if lines else 'Basic market pricing'

    # ===================================================================
    # Stake Optimization Reasoning
    # ===================================================================
    
    def explain_stake(
        self,
        opportunity: BetOpportunity,
        stake: Decimal,
        bankroll: Decimal,
        method: str = "kelly"
    ) -> str:
        """Generate explanation for stake size.
        
        Args:
            opportunity: The bet
            stake: Recommended stake
            bankroll: Current bankroll
            method: Stake calculation method
            
        Returns:
            Explanation of why this stake size
        """
        pct = stake / bankroll
        
        if not self.llm_client:
            return (
                f"Based on {method} criterion with a {opportunity.edge:.1%} edge, "
                f"the optimal stake is ${stake:.2f} ({pct:.1%} of bankroll)."
            )
        
        prompt = f"""Explain the stake sizing for this bet:

Bet: {opportunity.market.side}
Edge: {opportunity.edge:.1%}
Recommended Stake: ${stake:.2f}
Bankroll: ${bankroll:.2f}
Stake as % of bankroll: {pct:.1%}
Method: {method} criterion

Explain why this stake size is appropriate in 1-2 sentences. Consider:
- The edge size
- Risk of ruin
- Bankroll preservation
- Opportunity cost

Keep it concise and focused on the bettor's risk management."""

        try:
            return self._call_llm(prompt)
        except:
            return f"Full Kelly would suggest {pct*4:.1%}, but using fractional Kelly ({pct:.1%}) for risk management."

    # ===================================================================
    # Market Analysis
    # ===================================================================
    
    def analyze_market_efficiency(
        self,
        game_id: str,
        markets: List[Dict[str, Any]],
        sim_result: Dict[str, Any]
    ) -> str:
        """Generate AI analysis of market efficiency for a game.
        
        Args:
            game_id: Game identifier
            markets: List of market odds from multiple books
            sim_result: Simulation probabilities
            
        Returns:
            Market efficiency analysis
        """
        if not self.llm_client:
            return "Market efficiency analysis requires LLM client."
        
        prompt = f"""Analyze the market efficiency for this game:

Game ID: {game_id}

Model Probabilities:
{self._format_sim_details(sim_result)}

Market Odds:
{self._format_market_summary(markets)}

Provide a brief analysis:
1. Is the market efficient or are there clear edges?
2. Which book(s) appear most accurate vs the model?
3. Any signs of public bias (heavy favorite, etc.)?
4. Recommendation: bet, no bet, or monitor?

Keep to 3-4 sentences."""

        try:
            return self._call_llm(prompt)
        except Exception as e:
            logger.error(f"Market analysis failed: {e}")
            return "Unable to generate market analysis."

    def _format_market_summary(self, markets: List[Dict]) -> str:
        """Format market summary for prompt."""
        lines = []
        for m in markets:
            lines.append(f"- {m.get('book', 'Unknown')}: {m.get('odds', 'N/A')} ({m.get('side', 'Unknown')})")
        return '\n'.join(lines[:10])  # Limit to first 10
