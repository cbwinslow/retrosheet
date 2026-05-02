# Project Status & Organization

## Core Goal
Build a baseball prediction and betting platform that:
1. Ingests historical and live data
2. Trains predictive models on historical data
3. Runs models against live data
4. Compares predictions to live odds
5. Identifies profitable betting opportunities

## Current CLI Structure (The "Baseball Class Logic")

The project uses a Typer-based CLI that wraps all functionality:

```
baseball
├── ingest (data ingestion)
│   ├── retrosheet
│   ├── mlb
│   ├── statcast
│   ├── espn
│   ├── lahman
│   ├── fangraphs
│   ├── bref
│   ├── weather
│   └── park
├── bet (betting analysis)
│   ├── analyze (Monte Carlo + odds + edge calculation)
│   └── paper-report
├── predict (prediction workflows)
│   ├── game
│   └── live
├── models (model management)
├── features (feature engineering)
├── bridge (cross-reference resolution)
└── chatbot
```

## What's Working

### Data Ingestion
- ✅ Retrosheet parsing (`baseball/retrosheet/` package)
- ✅ MLB live feed ingestion (`baseball/ingestion/mlb_live_adapter.py`)
- ✅ ESPN data integration (`scripts/fetch_espn_mlb.py`)
- ✅ Odds sources (`baseball/betting/sources/`)
- ✅ Bridge resolution system (`baseball/bridge/`)

### Models
- ✅ Base model classes (`baseball/models/base.py`)
- ✅ Model registry (`baseball/models/registry.py`)
- ✅ Win probability model (`baseball/models/win_probability_model.py`)
- ✅ Next run probability model (`baseball/models/next_run_model.py`)
- ✅ PA outcome model (`baseball/models/pa_outcome_model.py`)
- ✅ Training pipeline (`baseball/models/training.py`)
- ✅ Inference pipeline (`baseball/models/inference.py`)
- ✅ Backtesting (`baseball/models/backtesting.py`)

### Simulation
- ✅ Markov chain simulator (`baseball/models/simulation.py`)
- ✅ Monte Carlo simulator (`baseball/models/simulation.py`)
- ✅ Simulation service orchestration

### Betting
- ✅ Betting analyzer (`baseball/betting/analyzer.py`)
- ✅ Odds sources (TheOddsApi, Pinnacle, DraftKings)
- ✅ Paper trading system
- ✅ Edge calculation
- ✅ Kelly criterion sizing

### Caching
- ✅ Redis cache manager (`baseball/core/cache.py`)
- ✅ @cached decorator
- ✅ @cached_simulation decorator
- ✅ @cached_odds decorator
- ✅ @cached_sync decorator

## What Needs Completion

### 1. Redis Caching Integration (Issue #120)
**Status:** Infrastructure complete, integration pending
- Apply @cached_simulation to MonteCarloSimulator.run_simulation
- Apply @cached_odds to BettingAnalyzer.get_best_lines
- Convert methods to async
- Update CLI commands to use async
- Test caching behavior

### 2. Live Data Pipeline (Issue #27)
**Status:** Partially complete
- Complete MLB raw snapshot ingestion
- Implement schedule endpoint ingestion
- Implement boxscore endpoint ingestion
- Add idempotency via checksums
- Document ingestion commands

### 3. Pitch-Level Data (Issue #26)
**Status:** Not started
- Parse Retrosheet pitch sequences
- Create pitch-level warehouse table
- Validate pitch transitions
- Document edge cases

### 4. Model Training Pipeline
**Status:** Infrastructure exists, needs end-to-end testing
- Test training workflow end-to-end
- Verify model registration
- Test model loading
- Validate feature engineering

### 5. Live Inference
**Status:** Infrastructure exists, needs integration
- Connect live data to inference pipeline
- Test real-time predictions
- Integrate with betting analysis
- Add monitoring

### 6. Production Hardening (Issue #117, #121)
**Status:** Advanced features, low priority
- Install PostgreSQL extensions (pgvector, pg_cron)
- Configure scheduled jobs
- Set up monitoring
- Add automated testing

## Proposed GitHub Milestones

### Milestone 1: Core Data Infrastructure
**Goal:** Solid foundation for data ingestion and storage
- Complete retrosheet parsing and warehouse loading
- MLB live feed integration with bridge resolution
- Database schema stabilization
- Data quality checks and validation

**Issues:** #27 (MLB raw snapshots), #26 (pitch sequences), #6 (bridge resolution)

### Milestone 2: Model Training Pipeline
**Goal:** Train and deploy predictive models
- PA outcome distribution model
- Win probability model
- Next run probability model
- Feature engineering pipeline
- Model registry and versioning

**Issues:** #10 (ML models), #16 (feature population)

### Milestone 3: Live Inference & Betting
**Goal:** Real-time predictions and betting analysis
- Live data ingestion pipeline
- Monte Carlo simulation integration
- Odds fetching from multiple sources
- Betting analysis and edge calculation
- Paper trading system

**Issues:** #20 (live inference), #22 (betting integration)

### Milestone 4: Performance & Caching
**Goal:** Optimize for real-time operations
- Redis caching implementation
- Async conversion of bottlenecks
- Query optimization
- Materialized views for common queries

**Issues:** #120 (Redis caching), #119 (async conversion)

### Milestone 5: Production Hardening
**Goal:** Production-ready deployment
- Advanced PostgreSQL features (pgvector, pg_cron)
- Monitoring and alerting
- Automated testing
- Deployment automation
- Documentation and runbooks

**Issues:** #117 (v2.0 hardening), #121 (PostgreSQL features)

## Immediate Next Steps

1. **Complete Redis Caching Integration** (Issue #120)
   - This is the highest priority for live betting performance
   - Infrastructure is complete, just needs integration
   - Will significantly speed up Monte Carlo simulations and odds fetching

2. **Test End-to-End Workflow**
   - Ingest historical data
   - Train a model
   - Run predictions
   - Compare to odds
   - Find profitable bets

3. **Create GitHub Milestones**
   - Organize existing issues into milestones
   - Provide clear roadmap
   - Track progress

## Summary

The project has excellent infrastructure:
- Well-organized CLI with all major components
- Complete model training pipeline
- Simulation engines
- Betting analysis
- Redis caching infrastructure

What's missing:
- Integration of caching with live operations
- End-to-end testing of the full workflow
- Organization via GitHub milestones
- Production hardening (low priority)

The "baseball class logic" is the CLI - it wraps everything in a clean, modular interface. No additional wrapper class needed.
