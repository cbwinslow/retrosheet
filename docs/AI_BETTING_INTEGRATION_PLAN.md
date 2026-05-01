# AI Integration Plan: Betting Strategy & Bet Generation

## Overview

Leverage AI (LLMs + ML models) to generate betting insights, strategies, and recommendations based on Monte Carlo simulation results and historical data.

**Date:** 2026-04-30
**Status:** Planning Phase

---

## Architecture

### New Typer Sub-App: `betting_app`

```python
# baseball/cli.py additions
betting_app = typer.Typer(help='AI-powered betting analysis and strategy', no_args_is_help=True)
app.add_typer(betting_app, name='bet')
```

### CLI Commands

| Command | Purpose | AI Integration |
|---------|---------|----------------|
| `bet analyze <game>` | Analyze betting markets for a game | LLM interprets sim results + market odds |
| `bet strategy <strategy_name>` | Run custom betting strategy | AI optimizes stake sizing, bankroll management |
| `bet generate` | Generate bet recommendations | LLM ranks opportunities by edge + confidence |
| `bet backtest-strategy` | Backtest strategy historically | ML evaluates strategy performance |
| `bet track` | Track bet outcomes and ROI | AI learns from results, adjusts strategy |
| `bet explain <bet_id>` | Explain why a bet was recommended | LLM generates reasoning from data |

---

## Components

### 1. Bet Analysis Engine (`baseball/betting/analyzer.py`)

**Purpose:** Convert Monte Carlo outputs into betting insights.

```python
from pydantic import BaseModel
from decimal import Decimal

class BettingMarket(BaseModel):
    """Represents a betting market (moneyline, run line, total)."""
    market_type: str  # moneyline, spread, total
    odds: Decimal     # American odds (+150, -110)
    line: float | None  # Spread or total line
    book: str         # Sportsbook
    timestamp: datetime

class BetOpportunity(BaseModel):
    """Identified betting opportunity with edge calculation."""
    game_id: str
    market: BettingMarket
    our_probability: float  # From Monte Carlo simulation
    implied_probability: float  # From odds
    edge: float  # Our prob - implied prob
    expected_value: float  # EV calculation
    kelly_fraction: float  # Kelly criterion stake
    confidence_score: float  # AI confidence 0-1
    recommendation: str  # "strong_buy", "buy", "neutral", "avoid"

class BettingAnalyzer:
    """Analyzes games for betting opportunities."""
    
    def analyze_game(
        self,
        game_id: str,
        sim_result: AggregatedSimulationResult,
        markets: list[BettingMarket]
    ) -> list[BetOpportunity]:
        """Compare simulation results against market odds."""
        
    def find_edges(self, min_edge: float = 0.05) -> list[BetOpportunity]:
        """Find all bets with positive edge above threshold."""
        
    def calculate_kelly_stake(
        self,
        bankroll: Decimal,
        opportunity: BetOpportunity
    ) -> Decimal:
        """Calculate optimal stake using Kelly criterion."""
```

### 2. AI Strategy Generator (`baseball/betting/strategy_ai.py`)

**Purpose:** Use LLM to generate and optimize betting strategies.

```python
from letta import create_client  # Or OpenAI client

class BettingStrategyAI:
    """AI-powered betting strategy generator."""
    
    def __init__(self, client=None):
        self.client = client or create_client(base_url="http://localhost:8283")
    
    async def generate_strategy(
        self,
        strategy_name: str,
        constraints: StrategyConstraints,
        historical_performance: pd.DataFrame | None = None
    ) -> BettingStrategy:
        """Generate a new betting strategy using AI.
        
        Args:
            strategy_name: Name for the strategy
            constraints: Bankroll, risk tolerance, bet types allowed
            historical_performance: Past bets for learning
        """
        
    async def explain_bet(
        self,
        opportunity: BetOpportunity,
        sim_details: dict
    ) -> str:
        """Generate human-readable explanation for a bet recommendation.
        
        Returns reasoning like:
        "The model gives the Yankees a 62% win probability vs 
         market implied 55%, giving us a 7% edge. The starting 
         pitcher matchup favors Cole's strikeout rate against 
         this lineup..."
        """
        
    async def optimize_stakes(
        self,
        opportunities: list[BetOpportunity],
        bankroll: Decimal,
        risk_profile: str  # conservative, moderate, aggressive
    ) -> list[PlacedBet]:
        """Optimize stake sizes across multiple opportunities.
        
        Uses AI to balance Kelly criterion with diversification
        and correlation risk between bets.
        """
        
    async def detect_market_bias(
        self,
        historical_markets: pd.DataFrame
    ) -> dict:
        """Detect sportsbook biases (e.g., home team overvalued, 
        popular teams overbet, etc.) using pattern analysis."""
```

### 3. Strategy Backtester (`baseball/betting/strategy_backtest.py`)

**Purpose:** Backtest betting strategies historically.

```python
class StrategyBacktest:
    """Backtest betting strategies against historical data."""
    
    def run_backtest(
        self,
        strategy: BettingStrategy,
        start_date: date,
        end_date: date,
        initial_bankroll: Decimal
    ) -> StrategyBacktestResult:
        """Run walk-forward backtest on historical games."""
        
    def monte_carlo_simulation(
        self,
        historical_results: list[BetResult],
        num_sims: int = 10000
    ) -> RiskMetrics:
        """Run Monte Carlo on bankroll trajectory."""
```

### 4. Pydantic Schemas (`baseball/betting/schemas.py`)

```python
class BettingStrategy(BaseModel):
    """Complete betting strategy definition."""
    name: str
    description: str
    created_by: str  # 'ai' or 'user'
    
    # Rules
    min_edge: float = 0.03
    min_confidence: float = 0.6
    max_bet_size_percent: float = 5.0  # Max 5% of bankroll
    allowed_markets: list[str] = ['moneyline', 'total']
    
    # AI-generated components
    selection_criteria: str  # Natural language rules
    stake_sizing_logic: str  # How to size bets
    correlation_rules: str  # How to handle correlated bets
    
    # Performance tracking
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    roi_percent: float = 0.0
    
class PlacedBet(BaseModel):
    """Record of a placed bet."""
    bet_id: UUID
    opportunity: BetOpportunity
    stake: Decimal
    actual_stake: Decimal  # May differ from Kelly
    placed_at: datetime
    book: str
    
    # Outcome (filled later)
    outcome: str | None = None  # win, loss, push
    profit_loss: Decimal | None = None
    settled_at: datetime | None = None
    
class StrategyBacktestResult(BaseModel):
    """Results from strategy backtest."""
    strategy_name: str
    start_date: date
    end_date: date
    initial_bankroll: Decimal
    final_bankroll: Decimal
    
    total_bets: int
    win_rate: float
    roi_percent: float
    
    # Risk metrics
    max_drawdown_percent: float
    sharpe_ratio: float
    
    # AI-generated insights
    ai_summary: str
    recommended_adjustments: list[str]
```

---

## AI Integration Points

### 1. Letta Integration (Memory)

```python
# Store betting strategies in Letta memory
letta_client.send_message(
    agent_id="betting_strategy_agent",
    message=f"Create strategy for: {constraints}",
    memory_type="archival"
)

# Retrieve past strategies for learning
past_strategies = letta_client.get_archival_memory(
    query="successful baseball betting strategies high ROI"
)
```

### 2. LLM Prompts for Bet Explanation

```python
BET_EXPLAIN_PROMPT = """
You are a professional sports betting analyst. Explain this betting 
recommendation in clear, confident language:

Game: {home_team} vs {away_team}
Market: {market_type} - {line} @ {odds}

Model Analysis:
- Our win probability: {our_prob:.1%}
- Market implied probability: {implied_prob:.1%}
- Edge: {edge:.1%}
- Expected Value: ${ev:.2f} per $100 bet

Simulation Details:
- Monte Carlo iterations: {n_sims:,}
- Home win probability: {home_win_prob:.1%}
- Expected runs: {exp_runs_home:.1f} - {exp_runs_away:.1f}
- Most common final score: {common_score}

Key Factors:
{key_factors}

Write 2-3 sentences explaining why this is a good bet. Be specific 
about the edge and what the simulation reveals that the market 
may be missing. Don't use hedging language like "might" or "could".
"""
```

### 3. AI Strategy Generation Prompt

```python
STRATEGY_GENERATION_PROMPT = """
Create a baseball betting strategy given these constraints:

Bankroll: ${bankroll}
Risk Tolerance: {risk_profile}
Allowed Bet Types: {allowed_markets}
Historical Performance: {historical_summary}

Your task:
1. Define minimum edge threshold (typically 3-8%)
2. Define confidence threshold (0.6-0.8)
3. Create stake sizing rules (fractional Kelly)
4. Define when to avoid bets (correlation, line movement)
5. Suggest specific filters (e.g., avoid heavy favorites)

Return a structured strategy definition that can be implemented
programmatically.
"""
```

---

## SQL Schema

```sql
-- betting schema
CREATE SCHEMA IF NOT EXISTS betting;

-- Betting strategies
CREATE TABLE betting.strategies (
    strategy_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_by TEXT DEFAULT 'ai', -- 'ai' or 'user'
    
    -- Strategy parameters
    min_edge NUMERIC(5,4) DEFAULT 0.03,
    min_confidence NUMERIC(5,4) DEFAULT 0.6,
    max_bet_size_percent NUMERIC(5,2) DEFAULT 5.0,
    allowed_markets TEXT[] DEFAULT ARRAY['moneyline', 'total'],
    
    -- AI-generated logic
    selection_criteria TEXT,
    stake_sizing_logic TEXT,
    correlation_rules TEXT,
    
    -- Performance (updated by tracking)
    total_bets INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    pushes INTEGER DEFAULT 0,
    roi_percent NUMERIC(10,4) DEFAULT 0,
    
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Betting opportunities identified
CREATE TABLE betting.opportunities (
    opportunity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id INTEGER REFERENCES betting.strategies(strategy_id),
    
    game_id TEXT NOT NULL,
    season INTEGER,
    
    -- Market info
    market_type TEXT NOT NULL,
    book TEXT,
    odds NUMERIC(10,2),
    line NUMERIC(6,2),
    
    -- Analysis
    our_probability NUMERIC(5,4),
    implied_probability NUMERIC(5,4),
    edge NUMERIC(5,4),
    expected_value NUMERIC(10,4),
    kelly_fraction NUMERIC(5,4),
    confidence_score NUMERIC(5,4),
    recommendation TEXT, -- strong_buy, buy, neutral, avoid
    
    -- AI explanation
    ai_explanation TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    market_timestamp TIMESTAMP
);

-- Placed bets
CREATE TABLE betting.bets (
    bet_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID REFERENCES betting.opportunities(opportunity_id),
    
    -- Placement
    stake NUMERIC(12,2),
    book TEXT,
    placed_at TIMESTAMP DEFAULT NOW(),
    
    -- Outcome
    outcome TEXT, -- win, loss, push, pending
    profit_loss NUMERIC(12,2),
    settled_at TIMESTAMP,
    
    -- Tracking
    tracked BOOLEAN DEFAULT false
);

-- Strategy backtest results
CREATE TABLE betting.backtest_results (
    backtest_id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES betting.strategies(strategy_id),
    
    start_date DATE,
    end_date DATE,
    initial_bankroll NUMERIC(12,2),
    final_bankroll NUMERIC(12,2),
    
    total_bets INTEGER,
    win_rate NUMERIC(5,4),
    roi_percent NUMERIC(10,4),
    max_drawdown_percent NUMERIC(5,2),
    sharpe_ratio NUMERIC(10,4),
    
    ai_summary TEXT,
    recommended_adjustments TEXT[],
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Market odds history (for analysis)
CREATE TABLE betting.market_odds (
    odds_id SERIAL PRIMARY KEY,
    game_id TEXT NOT NULL,
    book TEXT,
    market_type TEXT,
    odds NUMERIC(10,2),
    line NUMERIC(6,2),
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_opportunities_game ON betting.opportunities(game_id);
CREATE INDEX idx_opportunities_strategy ON betting.opportunities(strategy_id);
CREATE INDEX idx_opportunities_recommendation ON betting.opportunities(recommendation);
CREATE INDEX idx_bets_outcome ON betting.bets(outcome);
CREATE INDEX idx_bets_placed ON betting.bets(placed_at);
```

---

## Typer CLI Implementation

```python
# baseball/cli.py additions

betting_app = typer.Typer(help='AI-powered betting analysis', no_args_is_help=True)
app.add_typer(betting_app, name='bet')


@betting_app.command(name='analyze')
def bet_analyze(
    game_pk: int = typer.Option(..., '--game', '-g', help='Game PK to analyze'),
    strategy: str = typer.Option('default', '--strategy', '-s', help='Strategy to use'),
    show_odds: bool = typer.Option(True, '--odds/--no-odds', help='Show market odds'),
):
    """Analyze betting markets for a game using AI."""
    from baseball.betting.analyzer import BettingAnalyzer
    from baseball.models.simulation import SimulationService, SimulationConfig
    
    # Run simulation
    service = SimulationService()
    config = SimulationConfig(game_id=str(game_pk), num_iterations=10000)
    sim_result = service.run_simulation(config, show_progress=True)
    
    # Analyze markets
    analyzer = BettingAnalyzer(strategy_name=strategy)
    opportunities = analyzer.analyze_game(game_pk, sim_result.results)
    
    # AI explanation
    if opportunities:
        ai = BettingStrategyAI()
        for opp in opportunities:
            explanation = ai.explain_bet(opp, sim_result.results.model_dump())
            console.print(f"\n[bold green]{opp.market.market_type} @ {opp.market.odds}[/bold green]")
            console.print(f"Edge: {opp.edge:.1%} | Confidence: {opp.confidence_score:.0%}")
            console.print(f"\n[dim]{explanation}[/dim]")


@betting_app.command(name='strategy')
def bet_strategy(
    name: str = typer.Argument(..., help='Strategy name'),
    generate: bool = typer.Option(False, '--generate', help='Use AI to generate strategy'),
    bankroll: float = typer.Option(1000, '--bankroll', '-b', help='Starting bankroll'),
    risk: str = typer.Option('moderate', '--risk', '-r', help='Risk profile'),
):
    """Create or run a betting strategy."""
    if generate:
        from baseball.betting.strategy_ai import BettingStrategyAI
        
        ai = BettingStrategyAI()
        strategy = ai.generate_strategy(
            name,
            constraints=StrategyConstraints(
                bankroll=bankroll,
                risk_profile=risk
            )
        )
        
        console.print(f"[green]✓ Generated strategy: {strategy.name}[/green]")
        console.print(f"\n{strategy.description}")
        console.print(f"\nMin edge: {strategy.min_edge:.1%}")
        console.print(f"Max bet: {strategy.max_bet_size_percent}% of bankroll")


@betting_app.command(name='recommend')
def bet_recommend(
    date: str = typer.Option('today', '--date', '-d', help='Date to find bets'),
    min_edge: float = typer.Option(0.05, '--min-edge', '-e', help='Minimum edge threshold'),
    strategy: str = typer.Option('default', '--strategy', '-s', help='Strategy to use'),
    ai_explain: bool = typer.Option(True, '--explain/--no-explain', help='AI explains each bet'),
):
    """Generate AI-recommended bets for today."""
    # Find all opportunities above edge threshold
    # Generate AI explanations
    # Output ranked list with confidence scores


@betting_app.command(name='backtest-strategy')
def bet_backtest_strategy(
    strategy: str = typer.Argument(..., help='Strategy name'),
    start_date: str = typer.Option(..., '--start', '-s', help='Start date (YYYY-MM-DD)'),
    end_date: str = typer.Option(..., '--end', '-e', help='End date (YYYY-MM-DD)'),
    bankroll: float = typer.Option(1000, '--bankroll', '-b', help='Initial bankroll'),
):
    """Backtest a betting strategy historically."""
    # Run walk-forward backtest
    # Show P&L curve
    # AI generates summary and recommendations


@betting_app.command(name='track')
def bet_track(
    bet_id: str = typer.Argument(..., help='Bet ID to update'),
    outcome: str = typer.Option(..., '--outcome', '-o', help='win, loss, or push'),
):
    """Track outcome of a placed bet."""
    # Update bet record
    # Update strategy performance stats
    # Trigger AI learning if significant deviation


@betting_app.command(name='performance')
def bet_performance(
    strategy: str = typer.Option(None, '--strategy', '-s', help='Filter by strategy'),
    days: int = typer.Option(30, '--days', '-d', help='Lookback period'),
):
    """Show betting performance dashboard."""
    # ROI by strategy
    # Win rate
    # Current bankroll
    # AI insights on what's working


@betting_app.command(name='explain')
def bet_explain(
    bet_id: str = typer.Argument(..., help='Bet ID or opportunity ID'),
):
    """Get AI explanation for a bet recommendation."""
    # Retrieve opportunity
    # Generate explanation using context
    # Show reasoning chain
```

---

## Integration with Existing Components

### Monte Carlo → Betting Pipeline

```
SimulationService.run_simulation()
    ↓
AggregatedSimulationResult
    ↓
BettingAnalyzer.find_edges()
    ↓
BetOpportunity list
    ↓
BettingStrategyAI.optimize_stakes()
    ↓
PlacedBet recommendations
    ↓
User confirmation → bet placed
    ↓
betting.bets table
```

### Letta Memory Integration

```python
# Store successful strategies
letta_client.create_memory(
    content=f"Strategy '{strategy.name}' achieved {strategy.roi_percent:.1f}% ROI",
    tags=["betting", "strategy", "high_performer" if strategy.roi_percent > 10 else "average"]
)

# Query for similar situations
similar = letta_client.search_memory(
    query="high ROI betting strategies moneyline underdogs",
    limit=5
)
```

---

## Implementation Phases

### Phase 1: Core Betting (This Session)
1. Create `baseball/betting/schemas.py` - Pydantic models
2. Create `baseball/betting/analyzer.py` - Edge calculation
3. Add `bet analyze` CLI command
4. Create SQL schema (`sql/70_betting/7001_betting_schema.sql`)

### Phase 2: AI Integration (Next)
1. Create `baseball/betting/strategy_ai.py`
2. Add `bet strategy --generate` command
3. Add `bet explain` command
4. Letta memory integration

### Phase 3: Strategy Management (Future)
1. `bet backtest-strategy` command
2. Strategy comparison framework
3. Auto-strategy optimization

### Phase 4: Live Tracking (Future)
1. Odds API integration
2. Auto-bet placement (paper trading)
3. Real-time line movement alerts

---

## Value Proposition

**For Users:**
- Turn Monte Carlo outputs into actionable bets
- AI explains *why* a bet is recommended
- Automated bankroll management
- Learn from historical performance

**For the Platform:**
- New revenue stream (bet tracking, strategy marketplace)
- Differentiation through AI explanations
- Data flywheel: more bets → better models → better bets

---

**Next Step:** Create the core betting module and `bet analyze` command?
