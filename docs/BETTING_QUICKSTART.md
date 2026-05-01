# Betting System Quickstart Guide

Complete guide to getting started with the AI-powered baseball betting analysis system.

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ (with simulation schema loaded)
- API key from [The Odds API](https://the-odds-api.com) (free tier available)

## Installation

### 1. Clone and Setup

```bash
git clone https://github.com/cbwinslow/retrosheet.git
cd retrosheet
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

**Required variables:**
- `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` - Database connection
- `THE_ODDS_API_KEY` - Get free key at https://the-odds-api.com

**Optional variables:**
- `OPENROUTER_API_KEY` - For AI strategy explanations
- `PINNACLE_API_KEY` - For sharp odds (requires approval)

### 3. Initialize Database

```bash
# Load simulation schema
psql -d retrosheet -f sql/60_models/6010_simulation_schema.sql

# Verify schema loaded
psql -d retrosheet -c "\dt simulation.*"
```

## First Betting Analysis

### Run a Simulation First

Before analyzing bets, run a Monte Carlo simulation for your target game:

```bash
# Simulate a game (example game PK 716190)
python -c "
from baseball.simulation.runners import MonteCarloRunner
from baseball.models.schemas import GameState
import asyncio

async def run():
    runner = MonteCarloRunner(num_iterations=10000)
    result = await runner.run_for_game('716190')
    print(f'Run ID: {result.run_id}')
    print(f'Home win prob: {result.summary.home_win_probability:.1%}')

asyncio.run(run())
"
```

### Analyze a Game

```bash
# Analyze with simulation probabilities (default)
baseball bet analyze --game 716190 --min-edge 0.05

# Output:
# Analyzing betting opportunities for game 716190
# Using simulation probabilities:
#   Home win: 58.2%
#   Away win: 41.8%
# Found 3 opportunities with edge > 5.0%
```

### View Paper Trading Account

```bash
# View current performance
baseball bet paper-report

# Output:
# Paper Trading Account: Analysis_716190
# Open Bets: 2 | Settled: 5 | Win Rate: 60.0%
# ROI: +8.5% | Profit: $850.00
```

## CLI Commands Reference

### `baseball bet analyze`

Analyze betting opportunities for a game.

```bash
baseball bet analyze \
  --game 716190 \
  --min-edge 0.05 \
  --source the_odds_api \
  --bankroll 10000 \
  --paper \
  --explain
```

**Flags:**
- `--game, -g` (required): Game PK to analyze
- `--min-edge, -e`: Minimum edge threshold (default: 0.05)
- `--source`: Odds source (`the_odds_api`, `pinnacle`, `draftkings`)
- `--bankroll, -b`: Bankroll for stake calculation
- `--paper/--real`: Use paper trading (default: paper)
- `--explain/--no-explain`: AI explanations (default: explain)
- `--simulation/--mock`: Use simulation or mock probabilities

### `baseball bet paper-report`

View paper trading performance.

```bash
baseball bet paper-report --account Analysis_716190
```

## Advanced Usage

### Multiple Source Analysis

Compare odds across sources for best prices:

```python
from baseball.betting.multi_source import MultiSourceAnalyzer
from baseball.betting.sources import TheOddsApiSource, PinnacleSource

async def find_best_prices():
    analyzer = MultiSourceAnalyzer([
        TheOddsApiSource(api_key="xxx"),
        PinnacleSource(api_key="yyy")
    ])
    
    opportunities = await analyzer.find_best_opportunities("716190")
    for opp in opportunities:
        print(f"{opp.market.side}: {opp.edge:.1%} edge at {opp.market.odds}")
```

### Custom Strategy

Define custom edge calculation and stake sizing:

```python
from baseball.betting.analyzer import BettingAnalyzer
from decimal import Decimal

# Custom edge calculator (delegate function)
def conservative_edge(model_prob, implied_prob):
    raw_edge = model_prob - implied_prob
    # Discount edges > 15% as potentially mispriced
    return min(raw_edge, Decimal("0.15"))

# Custom stake function (delegate)
def half_kelly(prob, odds, bankroll, edge):
    kelly = (prob * odds - (1 - prob)) / odds
    return bankroll * kelly * Decimal("0.5")  # Half Kelly

analyzer = BettingAnalyzer(
    odds_source=source,
    edge_calculator=conservative_edge,  # Delegate
    stake_calculator=half_kelly         # Delegate
)
```

### Event Hooks

Register callbacks for betting events:

```python
from baseball.betting.paper_trading import PaperTradingManager

manager = PaperTradingManager()

# Hook: Log when bet placed
@manager.on_bet_placed
async def log_bet(bet):
    print(f"Bet placed: {bet.stake} on {bet.market.selection}")

# Hook: Alert on large wins
@manager.on_bet_settled
async def alert_big_win(bet, result):
    if result.pnl > 1000:
        await send_alert(f"Big win: +${result.pnl}")
```

## Database Queries

### View Recent Simulations

```sql
SELECT 
    game_id,
    model_id,
    num_iterations,
    home_win_probability,
    avg_total_score,
    created_at
FROM simulation.runs_summary
WHERE status = 'completed'
ORDER BY created_at DESC
LIMIT 10;
```

### View Paper Trading Performance

```sql
SELECT 
    account_name,
    bets_settled,
    win_rate,
    roi_percent,
    total_profit
FROM paper_trading.accounts_summary;
```

### Find Best Edges

```sql
-- View all current opportunities
SELECT * FROM betting.current_opportunities
WHERE edge >= 0.05
ORDER BY edge DESC;
```

## Troubleshooting

### No simulation found for game

```bash
# Run simulation first
baseball simulate run --game 716190 --iterations 10000

# Or use mock probabilities
baseball bet analyze --game 716190 --mock
```

### Odds API rate limit

```bash
# Check API usage
curl "https://api.the-odds-api.com/v4/sports/?apiKey=$THE_ODDS_API_KEY"

# Response header: X-Requests-Remaining shows quota
```

### Database connection error

```bash
# Verify connection
psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -c "SELECT 1"

# Check simulation schema
psql -d retrosheet -c "SELECT COUNT(*) FROM simulation.runs"
```

## API Reference

### The Odds API

Free tier: 500 requests/month
- Docs: https://the-odds-api.com
- Sports: `baseball_mlb`, `baseball_mlb_preseason`
- Markets: `h2h` (moneyline), `spreads`, `totals`

### Pinnacle API

Requires approval. Sharp prices, low limits.
- Docs: https://www.pinnacle.com/en/api
- Markets: Full offering including derivatives

### DraftKings API

Requires partnership. Retail prices, promotional odds.
- Contact: sportsbook-partnerships@draftkings.com

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Betting System                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  CLI → BettingAnalyzer → SimulationService → simulation DB │
│         ↓                           ↓                       │
│    BaseOddsSource (TheOddsApiSource/Pinnacle/DraftKings)   │
│         ↓                                                   │
│    PaperTradingManager → Bet Lifecycle                       │
│         ↓                                                   │
│    Event Hooks (logging, alerts, analytics)                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Patterns:**
- **Super Classes:** `BaseOddsSource`, `BaseIngestionSource`
- **Delegate Functions:** `edge_calculator`, `stake_calculator`, `transform_fn`
- **Event Hooks:** `@on_bet_placed`, `@on_bet_settled`
- **Async/Await:** All I/O operations (DB, API, WebSocket)

## Next Steps

1. **Backtest strategies:** Run historical analysis on past games
2. **Add sources:** Integrate additional sportsbooks for price shopping
3. **Live betting:** Use WebSocket feeds for in-game opportunities
4. **ML enhancement:** Train models on paper trading results

## Support

- Issues: https://github.com/cbwinslow/retrosheet/issues
- Docs: https://github.com/cbwinslow/retrosheet/tree/main/docs
- Architecture: See `docs/agents/ARCHITECTURE.md`
