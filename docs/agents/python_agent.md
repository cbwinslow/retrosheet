# Python Agent Instructions

## Purpose

Write clean, reusable Python that supports a public CLI and a long-lived data platform.

## Rules

- Use classes for source adapters, feature builders, and models.
- Centralize HTTP, DB, SQL, config, checkpoint, and filesystem logic.
- Use snake_case for modules/functions and PascalCase for classes.
- Keep modules small and focused.
- Use docstrings for public classes and important functions.
- Use logging, not stray prints.
- **Write comprehensive tests for ALL code** - See Testing section below.

## Testing Requirements

### Mandatory Test Coverage
Every module must have corresponding tests. No exceptions.

**Test File Naming:**
- Module: `baseball/betting/analyzer.py`
- Tests: `tests/betting/test_analyzer.py`

**Required Test Types:**

#### 1. Unit Tests (pytest)
Test individual functions/classes in isolation:
```python
# tests/betting/test_analyzer.py
def test_calculate_edge_positive_odds():
    """Edge calculation for +150 odds."""
    from baseball.betting.analyzer import standard_edge_calculator
    from decimal import Decimal

    prob = Decimal("0.45")
    odds = Decimal("150")
    edge = standard_edge_calculator(prob, odds)

    assert edge > 0  # Positive value bet
    assert edge == Decimal("0.125")  # Exact value


def test_calculate_edge_negative_odds():
    """Edge calculation for -120 odds."""
    prob = Decimal("0.55")
    odds = Decimal("-120")
    edge = standard_edge_calculator(prob, odds)

    assert edge < 0  # Negative EV
```

#### 2. Mock/Stub Tests (unittest.mock)
Test without external dependencies:
```python
from unittest.mock import Mock, patch

@patch('baseball.betting.sources.the_odds_api.requests.get')
def test_fetch_live_odds(mock_get):
    """Test API fetch with mocked response."""
    mock_get.return_value.json.return_value = {
        "data": [{"id": "test", "odds": 150}]
    }
    mock_get.return_value.status_code = 200

    source = TheOddsApiSource(api_key="test")
    markets = source.get_live_odds(Sport.MLB, MarketType.MONEYLINE)

    assert len(markets) > 0
    assert markets[0].odds == Decimal("150")
```

#### 3. Property-Based Tests (hypothesis)
Test edge cases and invariants:
```python
from hypothesis import given, strategies as st
from decimal import Decimal

@given(
    st.decimals(min_value=0.01, max_value=0.99, places=2),
    st.integers(min_value=-500, max_value=500)
)
def test_edge_calculation_invariants(prob, odds):
    """Edge calculation properties should always hold."""
    from baseball.betting.analyzer import standard_edge_calculator

    edge = standard_edge_calculator(Decimal(str(prob)), Decimal(str(odds)))

    # Invariants
    assert isinstance(edge, Decimal)
    assert edge > -1  # Edge can't be less than -100%
```

#### 4. Integration Tests
Test component interactions:
```python
@pytest.mark.integration
def test_analyzer_with_live_source():
    """Test analyzer works with actual odds source."""
    source = TheOddsApiSource(api_key="test_key")
    analyzer = BettingAnalyzer(odds_source=source)

    opportunities = analyzer.find_edges(
        game_id="test_123",
        model_probs={'home_win': 0.6, 'away_win': 0.4}
    )

    assert isinstance(opportunities, list)
```

#### 5. Event/Hook Tests
Test event-driven code:
```python
def test_event_hooks_fire():
    """Event handlers should be called."""
    from baseball.ingestion.base import BaseIngestionSource

    events_triggered = []

    class TestSource(BaseIngestionSource):
        def fetch(self, params): return {"test": "data"}
        def transform(self, data): return [data]
        def load(self, records): return len(records)

    source = TestSource("test", "rest")
    source.on('post_fetch', lambda d, ctx: events_triggered.append('post_fetch'))

    source.ingest()

    assert 'post_fetch' in events_triggered
```

#### 6. Async Tests (pytest-asyncio)
Test async code properly:
```python
import pytest

@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection handling."""
    service = LiveDataIngestionService()

    # Mock WebSocket
    with patch('websockets.connect') as mock_ws:
        mock_ws.return_value.__aenter__ = AsyncMock()
        mock_ws.return_value.__aenter__.return_value = AsyncMock()

        await service.start_feed('test', 'wss://test.com')
        assert service.is_connected('test')
```

#### 7. Error/Edge Case Tests
Test failure modes:
```python
def test_invalid_odds_handling():
    """Graceful handling of invalid odds."""
    with pytest.raises(ValueError):
        american_to_decimal(Decimal("invalid"))

def test_empty_market_list():
    """Analyzer handles empty markets."""
    analyzer = BettingAnalyzer(odds_source=Mock())
    result = analyzer.find_edges("game123", {})
    assert result == []
```

#### 8. CLI Tests (Typer testing)
Test CLI commands:
```python
from typer.testing import CliRunner
from baseball.cli import app

runner = CliRunner()

def test_bet_analyze_cli():
    """Test bet analyze command."""
    result = runner.invoke(app, ['bet', 'analyze', '--game', '716190'])
    assert result.exit_code == 0
    assert 'Analyzing' in result.output
```

#### 9. Performance Tests (pytest-benchmark)
Ensure code performs:
```python
def test_edge_calculation_performance(benchmark):
    """Edge calc should be fast."""
    from baseball.betting.analyzer import standard_edge_calculator

    result = benchmark(
        standard_edge_calculator,
        Decimal("0.55"),
        Decimal("-110")
    )

    assert result is not None
```

#### 10. Database Tests
Test SQL integration:
```python
@pytest.fixture
def db_conn():
    """Provide test database connection."""
    # Setup test DB
    conn = create_test_connection()
    yield conn
    # Teardown
    conn.execute("ROLLBACK")


def test_scheduler_job_persistence(db_conn):
    """Jobs persist to database."""
    scheduler = DatabaseScheduler(db_pool=db_conn)
    job_id = scheduler.add_job({
        'job_name': 'test_job',
        'job_type': 'odds_fetch'
    })

    jobs = scheduler.get_job_status()
    assert any(j['job_id'] == job_id for j in jobs)
```

### Test Organization
```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── betting/
│   │   ├── test_sources.py  # All source adapters
│   │   ├── test_analyzer.py
│   │   ├── test_paper_trading.py
│   │   └── test_schemas.py
│   ├── ingestion/
│   │   ├── test_base.py
│   │   ├── test_live_service.py
│   │   └── test_scheduler.py
│   └── models/
│       └── test_simulation.py
├── integration/
│   ├── test_betting_flow.py
│   └── test_ingestion_flow.py
├── e2e/
│   └── test_cli_commands.py
└── fixtures/
    ├── mock_odds_responses/
    └── mock_mlb_feeds/
```

### Test Requirements Checklist
Before marking any task complete:
- [ ] Unit tests for all public methods
- [ ] Mock tests for external API calls
- [ ] Edge case tests (empty inputs, errors, boundaries)
- [ ] Event/hook tests for event-driven code
- [ ] Async tests for async functions
- [ ] Integration tests for component interactions
- [ ] CLI tests for new commands
- [ ] All tests pass (`pytest`)
- [ ] Coverage report shows >80% for new code

### Running Tests
```bash
# All tests
pytest

# Specific module
pytest tests/betting/test_analyzer.py

# With coverage
pytest --cov=baseball --cov-report=html

# Integration tests only
pytest -m integration

# Fast unit tests only
pytest -m "not integration and not slow"
```

## Preferred Patterns

- BaseSource with download, ingest, validate
- BaseFeatureBuilder with build
- BaseModel with train, predict, backtest
- Dependency injection of DB/sql/settings/logger where reasonable

## Architectural Principles

### Super Classes for Abstraction
Use abstract base classes (ABC) to define common interfaces across variants:
- `BaseOddsSource` for multiple sportsbook APIs (TheOddsApi, Pinnacle, DraftKings)
- `BaseBettingStrategy` for different strategy types (value, arbitrage, trend)
- `BaseOddsConverter` for American/Decimal/Fractional/Probability conversions

Benefits: Plug-and-play source switching, testable mocks, shared validation logic.

### Delegate Functions for Flexibility
Pass behavior as callable parameters instead of hardcoding:
- `edge_calculator: Callable[[float, float], float]` - different edge formulas
- `odds_transform: Callable[[float], float]` - vig removal strategies
- `market_filter: Callable[[Market], bool]` - which markets to analyze

Benefits: Same analyzer works with different calculations, user-customizable strategies.

### Lambda Expressions for Simple Transformations
Use lambdas for one-line data transforms in pipelines:
- `map(lambda x: american_to_decimal(x.odds), markets)`
- `filter(lambda m: m.edge > threshold, opportunities)`
- `sorted(markets, key=lambda m: m.timestamp, reverse=True)`

Benefits: Concise inline operations, functional style for data processing.

### When to Use Each
- **Super Class**: Multiple implementations of same concept (sources, strategies)
- **Delegate**: Configurable behavior within same class (calculation methods)
- **Lambda**: Simple, one-off transformations in data pipelines

### Event Programming and Hooks
Use event-driven patterns for decoupled, extensible systems:

**Event Emitter Pattern**:
```python
class DataIngestionService:
    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {}
    
    def on(self, event: str, handler: Callable):
        """Register event handler."""
        self._hooks.setdefault(event, []).append(handler)
    
    def emit(self, event: str, data: Any):
        """Trigger all handlers for event."""
        for handler in self._hooks.get(event, []):
            handler(data)
```

**Hook Points for Data Pipelines**:
- `pre_fetch`: Before API call (for request signing, rate limiting)
- `post_fetch`: After raw data received (for validation, caching)
- `pre_transform`: Before data normalization (for custom parsing)
- `post_transform`: After schema conversion (for enrichment)
- `pre_load`: Before database insert (for deduplication)
- `on_error`: Error handling (for retries, alerts)

**Use Cases**:
- Live data ingestion with multiple downstream consumers
- Odds line movement alerts to multiple strategies
- Pre-bet validation hooks (bankroll check, exposure limits)
- Post-bet settlement hooks (P&L tracking, notifications)

**Benefits**: Decoupled components, easy to extend, testable in isolation.

### Quick Decision Guide
| Pattern | Use When | Example |
|---------|----------|---------|
| **Super Class** | Multiple similar implementations | Odds sources, ML models |
| **Delegate** | Pluggable behavior in one class | Edge calc, stake sizing |
| **Lambda** | One-off data transforms | Filter, map, sort operations |
| **Event/Hook** | Multiple listeners to same action | Live data, bet settlement |

## Avoid

- One-use scripts
- Duplicated request code
- Duplicated SQL execution code
- Hidden global state
- Huge files containing download + transform + DB load + CLI logic all together

## Migration Rule

If there is working logic in current repo files, wrap it first. Rewriting is allowed only when the current logic is unmaintainable or duplicated beyond repair.
