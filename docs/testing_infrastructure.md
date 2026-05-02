# Testing Infrastructure

## Current Test Structure

```
tests/
├── conftest.py           # Shared fixtures and configuration
├── unit/                 # Unit tests (no external dependencies)
│   ├── test_compatibility.py
│   ├── test_features_base.py
│   ├── test_leverage_index.py
│   ├── test_pgtap_integration.py
│   ├── test_pipeline.py
│   ├── test_queries.py
│   ├── test_scripts.py
│   └── test_win_expectancy.py
├── integration/          # Integration tests (with DB, external APIs)
│   ├── test_betting_flow.py      # ✅ Betting flow tests
│   ├── test_functionality.py     # ✅ General functionality
│   ├── test_maintenance_schema.py # ✅ Database schema
│   └── test_mlb_live_api.py      # ✅ MLB API integration
├── core/                 # Core module tests
│   └── test_cache.py     # ✅ Redis caching tests (927 lines)
├── betting/              # Betting module tests
│   ├── test_analyzer.py
│   ├── test_arbitrage.py
│   ├── test_lineage.py
│   └── test_paper_trading.py
├── e2e/                  # End-to-end tests
│   ├── test_bridge_service.py
│   ├── test_features_e2e.py
│   └── test_source_adapters.py
├── ingestion/            # Ingestion tests
│   └── test_ingestion.py
└── test_train_models.py  # Model training tests
```

## Current Test Coverage

### ✅ Well Covered
- **Caching layer** (`tests/core/test_cache.py`) - 927 lines
  - CacheManager connection management
  - All decorator types (@cached, @cached_simulation, @cached_odds, @cached_sync)
  - TTL expiration
  - Error handling
  - Health checking
  - Key generation and invalidation

- **Betting flow** (`tests/integration/test_betting_flow.py`) - 395 lines
  - End-to-end betting flow
  - Paper trading integration
  - Multiple sources

- **Database schema** (`tests/integration/test_maintenance_schema.py`) - 53258 lines
  - Comprehensive schema tests
  - pgTap integration

- **Unit tests** - Various coverage for:
  - Feature engineering
  - Win expectancy
  - Leverage index
  - Pipeline operations

### 🔄 Partial Coverage
- **Model training** - Basic tests exist
- **MLB live API** - Integration tests present
- **Bridge service** - E2E tests exist

### ❌ Missing Coverage

#### 1. Cache Integration Tests
**What's missing:** Tests verifying caching works in real workflow

Needed tests:
```python
# tests/integration/test_cache_integration.py
- test_simulation_caching_in_workflow
- test_odds_caching_in_betting_analyzer
- test_feature_caching_in_inference
- test_cache_hit_performance_improvement
- test_cache_invalidation_on_data_update
```

#### 2. End-to-End Betting Workflow
**What's missing:** Full pipeline test with real components

Needed tests:
```python
# tests/e2e/test_full_betting_workflow.py
- test_ingest_live_data → run_simulation → compare_odds → find_bets
- test_model_training → inference → betting
- test_live_game_state_change → cache_invalidation → recompute
```

#### 3. Async/Await Tests
**What's missing:** Tests for async operations

Needed tests:
```python
# tests/core/test_async_operations.py
- test_async_simulation_execution
- test_concurrent_cache_access
- test_async_betting_analysis
- test_event_loop_handling_in_sync_decorator
```

#### 4. Redis Failure Handling
**What's missing:** Tests for when Redis is unavailable

Needed tests:
```python
# tests/core/test_cache_resilience.py
- test_fallback_when_redis_down
- test_graceful_degradation_on_cache_error
- test_cache_reconnection_after_failure
```

#### 5. Performance Tests
**What's missing:** Performance benchmarks

Needed tests:
```python
# tests/benchmarks/test_performance.py
- test_simulation_time_with_and_without_cache
- test_odds_fetch_time_with_and_without_cache
- test_inference_time_with_and_without_cache
- test_concurrent_request_handling
```

## Testing Gaps Summary

| Component | Unit Tests | Integration Tests | E2E Tests | Performance |
|-----------|------------|-------------------|-----------|-------------|
| Cache Layer | ✅ Complete | ❌ Missing | ❌ Missing | ❌ Missing |
| Simulation | ✅ Good | ✅ Good | 🔄 Partial | ❌ Missing |
| Betting | ✅ Good | ✅ Good | 🔄 Partial | ❌ Missing |
| Ingestion | 🔄 Partial | ✅ Good | ✅ Good | ❌ Missing |
| Models | 🔄 Partial | 🔄 Partial | ❌ Missing | ❌ Missing |
| CLI Commands | ❌ Missing | ❌ Missing | ❌ Missing | ❌ Missing |

## Recommended Test Additions

### Priority 1: Critical Path Tests
1. **Cache Integration Test** - Verify caching works in real workflow
2. **CLI Command Tests** - Test all `baseball` commands work end-to-end
3. **Async Safety Tests** - Ensure async/await works correctly

### Priority 2: Resilience Tests
4. **Redis Failure Tests** - Graceful degradation when cache unavailable
5. **Database Failure Tests** - Handle DB connection issues
6. **API Failure Tests** - Handle external API errors

### Priority 3: Performance Tests
7. **Cache Performance Benchmarks** - Measure speed improvements
8. **Load Tests** - Handle multiple concurrent users
9. **Memory Usage Tests** - Ensure no memory leaks

## Test Commands

```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v
python -m pytest tests/e2e/ -v
python -m pytest tests/core/ -v

# Run with coverage
python -m pytest tests/ --cov=baseball --cov-report=html

# Run specific test file
python -m pytest tests/core/test_cache.py -v

# Run benchmarks
python -m pytest tests/benchmarks/ --benchmark-only
```

## CI/CD Integration

Recommended CI configuration should run:
1. Unit tests on every commit
2. Integration tests on PRs
3. E2E tests before releases
4. Performance benchmarks weekly

## Next Steps

1. Add cache integration tests (verify decorators work in real flow)
2. Add CLI command tests (test all `baseball` subcommands)
3. Add async safety tests
4. Add Redis failure resilience tests
5. Add performance benchmarks
