"""Pydantic schemas for AI-powered betting module.

Provides type-safe betting strategy management, bet opportunity tracking,
and performance analysis. Used by the betting CLI and AI strategy generator.

Author: Agent Cascade
Date: 2026-04-30
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# Enums
# ============================================================================

class MarketType(str, Enum):
    """Types of betting markets."""
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    TOTAL = "total"
    TEAM_TOTAL = "team_total"
    FIRST_INNING = "first_inning"
    RUN_LINE = "run_line"


class BetOutcome(str, Enum):
    """Outcome of a placed bet."""
    PENDING = "pending"
    WIN = "win"
    LOSS = "loss"
    PUSH = "push"
    VOID = "void"


class BetRecommendation(str, Enum):
    """AI-generated recommendation level."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    AVOID = "avoid"


class RiskProfile(str, Enum):
    """Risk tolerance for bankroll management."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


# ============================================================================
# Base Schemas
# ============================================================================

class BaseBettingState(BaseModel):
    """Base class for all betting schemas."""
    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        extra="forbid",
    )


# ============================================================================
# Betting Strategy
# ============================================================================

class StrategyConstraints(BaseBettingState):
    """Input parameters for AI strategy generation."""
    bankroll: Decimal = Field(..., gt=0, description="Starting bankroll in USD")
    risk_profile: RiskProfile = Field(default=RiskProfile.MODERATE)
    
    # Betting limits
    min_edge: float = Field(default=0.03, ge=0.01, le=0.20, description="Minimum edge threshold")
    min_confidence: float = Field(default=0.6, ge=0.5, le=0.95, description="Minimum model confidence")
    max_bet_size_percent: float = Field(default=5.0, ge=1.0, le=20.0, description="Max % of bankroll per bet")
    
    # Allowed markets
    allowed_markets: List[MarketType] = Field(
        default_factory=lambda: [MarketType.MONEYLINE, MarketType.TOTAL]
    )
    
    # Sport/league filters
    allowed_sports: List[str] = Field(default_factory=lambda: ["MLB"])
    
    @field_validator("max_bet_size_percent")
    @classmethod
    def validate_max_bet(cls, v: float) -> float:
        if v > 10.0 and cls.risk_profile != RiskProfile.AGGRESSIVE:
            raise ValueError("Max bet >10% requires aggressive risk profile")
        return v


class BettingStrategy(BaseBettingState):
    """Complete betting strategy definition.
    
    Can be AI-generated or user-defined. Tracks performance over time.
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "value_mlb_underdogs",
            "description": "Focus on moneyline dogs with 5%+ edge",
            "created_by": "ai",
            "min_edge": 0.05,
            "max_bet_size_percent": 3.0,
        }
    })
    
    # Identity
    strategy_id: Optional[int] = Field(None, description="Database ID")
    name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10)
    created_by: str = Field(default="ai", pattern="^(ai|user)$")
    
    # Strategy parameters
    min_edge: float = Field(default=0.03, ge=0.01, le=0.20)
    min_confidence: float = Field(default=0.6, ge=0.5, le=0.95)
    max_bet_size_percent: float = Field(default=5.0, ge=1.0, le=20.0)
    allowed_markets: List[MarketType] = Field(
        default_factory=lambda: [MarketType.MONEYLINE, MarketType.TOTAL]
    )
    
    # AI-generated rules (natural language)
    selection_criteria: str = Field(
        default="Select bets with edge > threshold and model confidence > min_confidence",
        description="Rules for identifying opportunities"
    )
    stake_sizing_logic: str = Field(
        default="Kelly criterion with half-Kelly fraction for safety",
        description="How to size individual bets"
    )
    correlation_rules: str = Field(
        default="Avoid correlated bets on same game",
        description="How to handle correlated opportunities"
    )
    
    # Performance tracking
    total_bets: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    pushes: int = Field(default=0)
    roi_percent: float = Field(default=0.0)
    
    # Status
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate (excluding pushes)."""
        decided = self.wins + self.losses
        return self.wins / decided if decided > 0 else 0.0
    
    @property
    def profit_factor(self) -> float:
        """Profit factor (wins / |losses|)."""
        # Approximate using ROI as we don't have actual amounts
        return 1.0 + (self.roi_percent / 100) if self.roi_percent > 0 else 0.0


# ============================================================================
# Betting Markets & Opportunities
# ============================================================================

class BettingMarket(BaseBettingState):
    """Represents a betting market at a specific moment."""
    book: str = Field(..., description="Sportsbook (e.g., draftkings, fanduel)")
    market_type: MarketType = Field(...)
    
    # Odds
    odds: int = Field(..., description="American odds (+150, -110)")
    line: Optional[float] = Field(None, description="Spread or total line")
    
    # Line movement tracking
    odds_open: Optional[int] = Field(None, description="Opening odds")
    line_open: Optional[float] = Field(None, description="Opening line")
    
    # Metadata
    game_id: str = Field(...)
    game_date: date = Field(...)
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def implied_probability(self) -> float:
        """Convert American odds to implied probability."""
        if self.odds > 0:
            return 100.0 / (100.0 + self.odds)
        else:
            return abs(self.odds) / (abs(self.odds) + 100.0)
    
    @property
    def decimal_odds(self) -> float:
        """Convert American to decimal odds."""
        if self.odds > 0:
            return 1 + (self.odds / 100.0)
        else:
            return 1 + (100.0 / abs(self.odds))
    
    @property
    def is_favorite(self) -> bool:
        """True if betting on favorite (negative odds)."""
        return self.odds < 0


class BetOpportunity(BaseBettingState):
    """Identified betting opportunity with edge calculation.
    
    Created by analyzing Monte Carlo simulation results against market odds.
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "game_id": "716190",
            "market": {
                "book": "draftkings",
                "market_type": "moneyline",
                "odds": -110,
            },
            "our_probability": 0.52,
            "implied_probability": 0.5238,
            "edge": -0.0038,
            "recommendation": "avoid"
        }
    })
    
    # Identity
    opportunity_id: Optional[UUID] = Field(None)
    strategy_id: Optional[int] = Field(None)
    
    # Game context
    game_id: str = Field(...)
    season: Optional[int] = Field(None)
    game_date: Optional[date] = Field(None)
    
    # Market info
    market: BettingMarket = Field(...)
    
    # Our analysis (from Monte Carlo + features)
    our_probability: float = Field(..., ge=0.0, le=1.0, description="Model win probability")
    model_confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence score")
    
    # Edge calculation
    implied_probability: float = Field(..., ge=0.0, le=1.0)
    edge: float = Field(..., description="our_prob - implied_prob")
    
    # Value metrics
    expected_value: Decimal = Field(..., description="EV per $100 wagered")
    kelly_fraction: float = Field(..., ge=0.0, le=1.0, description="Optimal bet fraction")
    recommended_stake: Decimal = Field(..., description="Recommended stake in USD")
    
    # Recommendation
    recommendation: BetRecommendation = Field(...)
    
    # Context factors affecting this opportunity
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    
    # Weather and environmental
    temperature_f: Optional[float] = Field(None)
    wind_speed_mph: Optional[float] = Field(None)
    home_bullpen_fatigue: Optional[float] = Field(None, ge=0.0, le=1.0)
    away_bullpen_fatigue: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # AI explanation
    ai_explanation: Optional[str] = Field(None, description="Natural language reasoning")
    key_factors: List[str] = Field(default_factory=list, description="Key factors in decision")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def is_positive_ev(self) -> bool:
        """True if expected value is positive."""
        return self.expected_value > 0
    
    @field_validator("recommended_stake")
    @classmethod
    def validate_stake_positive(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Stake must be positive")
        return v


# ============================================================================
# Placed Bets
# ============================================================================

class PlacedBet(BaseBettingState):
    """Record of a placed bet with outcome tracking."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "bet_id": "550e8400-e29b-41d4-a716-446655440000",
            "opportunity_id": "550e8400-e29b-41d4-a716-446655440001",
            "stake": Decimal("100.00"),
            "book": "draftkings",
            "odds_at_placement": -110,
        }
    })
    
    # Identity
    bet_id: UUID = Field(default_factory=UUID)
    opportunity_id: Optional[UUID] = Field(None)
    
    # Placement details
    stake: Decimal = Field(..., gt=0)
    book: str = Field(...)
    placed_at: datetime = Field(default_factory=datetime.utcnow)
    placed_by: str = Field(default="system", description="system, user, or auto")
    
    # Market snapshot at placement
    odds_at_placement: int = Field(...)
    line_at_placement: Optional[float] = Field(None)
    
    # Outcome (filled later)
    outcome: BetOutcome = Field(default=BetOutcome.PENDING)
    profit_loss: Optional[Decimal] = Field(None)
    settled_at: Optional[datetime] = Field(None)
    
    # Settlement source
    settled_by: Optional[str] = Field(None)
    settlement_source: Optional[str] = Field(None, description="api, manual, feed")
    
    # Notes
    notes: Optional[str] = Field(None)
    
    @property
    def is_settled(self) -> bool:
        """True if bet has been settled."""
        return self.outcome in [BetOutcome.WIN, BetOutcome.LOSS, BetOutcome.PUSH, BetOutcome.VOID]
    
    @property
    
    def roi_percent(self) -> Optional[float]:
        """Calculate ROI if settled."""
        if self.profit_loss is not None and self.stake > 0:
            return float(self.profit_loss / self.stake) * 100
        return None


# ============================================================================
# Strategy Backtesting
# ============================================================================

class RiskMetrics(BaseBettingState):
    """Risk-adjusted performance metrics."""
    max_drawdown_percent: float = Field(..., ge=0)
    sharpe_ratio: Optional[float] = Field(None)
    sortino_ratio: Optional[float] = Field(None)
    calmar_ratio: Optional[float] = Field(None)
    win_rate: float = Field(..., ge=0, le=1)
    profit_factor: float = Field(..., ge=0)
    
    # Bet distribution
    avg_bet_size: Decimal = Field(...)
    max_bet_size: Decimal = Field(...)
    total_bets: int = Field(...)
    bets_per_day: float = Field(...)


class StrategyBacktestResult(BaseBettingState):
    """Results from strategy backtest with AI insights."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "strategy_name": "value_mlb_underdogs",
            "initial_bankroll": Decimal("1000.00"),
            "final_bankroll": Decimal("1200.00"),
            "total_bets": 50,
            "roi_percent": 20.0,
        }
    })
    
    # Identity
    backtest_id: Optional[int] = Field(None)
    strategy_id: int = Field(...)
    strategy_name: str = Field(...)
    
    # Period
    backtest_period: str = Field(..., description="e.g., '2024-season', 'last-30-days'")
    start_date: date = Field(...)
    end_date: date = Field(...)
    
    # Bankroll
    initial_bankroll: Decimal = Field(...)
    final_bankroll: Decimal = Field(...)
    
    # Performance
    total_bets: int = Field(...)
    win_rate: float = Field(..., ge=0, le=1)
    roi_percent: float = Field(...)
    
    # Risk metrics
    risk_metrics: RiskMetrics = Field(...)
    
    # AI-generated insights
    ai_summary: str = Field(..., description="Human-readable summary of results")
    recommended_adjustments: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def profit_loss(self) -> Decimal:
        """Calculate total P&L."""
        return self.final_bankroll - self.initial_bankroll
    
    @property
    def is_profitable(self) -> bool:
        """True if strategy was profitable."""
        return self.final_bankroll > self.initial_bankroll


# ============================================================================
# API Response Schemas
# ============================================================================

class BettingResponse(BaseBettingState):
    """API response for betting operations."""
    success: bool = Field(...)
    message: str = Field(...)
    
    # Data (varies by endpoint)
    strategy: Optional[BettingStrategy] = Field(None)
    opportunity: Optional[BetOpportunity] = Field(None)
    opportunities: List[BetOpportunity] = Field(default_factory=list)
    bet: Optional[PlacedBet] = Field(None)
    
    # Error tracking
    error_code: Optional[str] = Field(None)
    error_details: Optional[str] = Field(None)
