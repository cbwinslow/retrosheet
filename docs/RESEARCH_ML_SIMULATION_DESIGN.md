# Research: ML Simulation Architecture for Sabermetrics

## Sabermetric Research Findings

### 1. Markov Chain Baseball Models (Academic Consensus)

**Source:** Analytics Vidhya, Lehigh University (APBA analysis), r/Sabermetrics

**Key Findings:**
- Baseball is naturally a **Markov process** - game state depends ONLY on current base/out state, not history
- **24 base-out states** (0-3 outs × 8 base configurations) form the state space
- **Transition matrix** 24×24 captures probability of moving from state A to state B
- **Absorbing states:** 3 outs ends the inning (runs scored determined)

**Mathematical Model:**
```
RE(state) = Σ P(transition) × [runs_now + RE(next_state)]
```

**PostgreSQL Implication:**
- Store transition probabilities in a matrix table
- Use matrix multiplication for multi-inning projections
- Simulation = repeated state transitions with random sampling

### 2. Run Expectancy vs ML-Based Simulation

| Approach | Speed | Accuracy | Best For |
|----------|-------|----------|----------|
| **RE24 Tables** | Instant | 85% | Quick estimates, lineup optimization |
| **Markov Chains** | Fast | 90% | Inning-by-inning simulation |
| **ML Models (PAOutcome)** | Medium | 95% | Context-aware predictions |
| **Full Monte Carlo** | Slow | 95%+ | Playoff scenarios, game theory |

**r/Sabermetrics Insight:**
> "Simple stuff like OBP×SLG×PA probably gets you 85% of the way, Base Runs is ~90%, Markov is 95% etc."

### 3. MLflow-Style Registry Pattern

**From MLflow Research:**
- **Backend Store:** PostgreSQL for metadata (models, versions, metrics)
- **Artifact Store:** S3/MinIO/local filesystem for model files
- **Tracking:** Parameters, metrics, tags in SQL; artifacts in object storage
- **Registry:** Staging → Production → Archived lifecycle

**Our Adaptation:**
```
models.registry      → MLflow "experiments"
models.versions      → MLflow "runs"  
models.artifacts     → MLflow artifact storage
models.predictions   → Custom (MLflow doesn't store predictions)
models.simulation_runs → Custom for Monte Carlo
```

### 4. PostgreSQL-Specific Optimizations for Simulation

**Pattern from Research:**

**A. State Persistence Table**
```sql
CREATE TABLE simulation_states (
    simulation_id UUID PRIMARY KEY,
    iteration INTEGER,
    inning INTEGER,
    bases INTEGER,  -- Bitmask: 1=1B, 2=2B, 4=3B
    outs INTEGER,
    home_score INTEGER,
    away_score INTEGER,
    batter_position INTEGER,
    -- Allows parallel simulations
    created_at TIMESTAMP DEFAULT NOW()
);
```

**B. Transition Probability Matrix**
```sql
CREATE TABLE transition_matrix (
    from_state INTEGER,  -- 0-23 (base-out encoding)
    to_state INTEGER,
    event_type VARCHAR,  -- 'out', 'walk', 'single', 'double', etc.
    probability NUMERIC,
    runs_scored INTEGER DEFAULT 0,
    PRIMARY KEY (from_state, to_state, event_type)
);
```

**C. Materialized View for Fast Feature Access**
```sql
CREATE MATERIALIZED VIEW plate_appearance_features AS
-- Pre-computed features for every PA in database
-- Refreshed after new data ingestion
```

### 5. Simulation Design Patterns

**A. Discrete Event Simulation (DES)**
- Events: PA outcomes (not pitch-by-pitch)
- Time steps: Plate appearances
- State: Base-out, score, inning, batting order position

**B. Variance Reduction Techniques**
- **Common random numbers:** Same seed for comparing lineups
- **Antithetic variates:** Pair simulations for faster convergence
- **Importance sampling:** Weight rare events (grand slams)

**C. Parallelization Strategy**
- Each simulation iteration = independent
- Use PostgreSQL temp tables for state isolation
- Pool of workers, each with unique simulation_id prefix

## Recommended Architecture

### Class Hierarchy

```python
# Layer 1: Core Abstractions
BaseModel                    # Abstract: train(), predict(), save(), load()
├── SklearnBaseModel         # scikit-learn wrapper
├── MarkovModel              # Transition matrix operations
└── SimulationModel          # Monte Carlo base

# Layer 2: Specific Implementations
PAOutcomeModel               # Multi-class: H/2B/3B/HR/BB/SO/Out
NextRunProbabilityModel      # Binary: will run score?
WinProbabilityModel          # Binary: home team wins?
RunExpectancyModel           # RE24 lookup + interpolation

# Layer 3: Simulation Engines
MarkovChainSimulator         # Fast: transition matrices
MonteCarloSimulator          # Accurate: ML model sampling
HybridSimulator              # RE24 early, ML late innings

# Layer 4: Orchestration
BacktestEngine               # Walk-forward validation
SimulationService            # Parallel sim management
PredictionService            # Batch/online inference
ModelComparison              # A/B testing framework
```

### SQL Schema Design

**Schema: models** (ML Registry - exists)
- registry, versions, training_runs, artifacts, predictions

**Schema: simulation** (NEW)
```sql
-- Core simulation tracking
simulation_runs
  - run_id UUID PRIMARY KEY
  - model_id INTEGER REFERENCES models.registry
  - version_id INTEGER REFERENCES models.versions
  - simulation_type VARCHAR  -- 'markov', 'monte_carlo', 'hybrid'
  - num_iterations INTEGER
  - status VARCHAR           -- 'pending', 'running', 'completed'
  - created_at, started_at, completed_at

-- State at each iteration (for resume/debugging)
simulation_states
  - state_id BIGSERIAL
  - run_id UUID REFERENCES simulation_runs
  - iteration INTEGER
  - inning, is_bottom, outs, bases
  - home_score, away_score
  - batter_id, pitcher_id
  - batting_order_position

-- Results aggregated by iteration
simulation_results
  - result_id BIGSERIAL
  - run_id UUID
  - iteration INTEGER
  - final_home_score, final_away_score
  - home_won BOOLEAN
  - total_pas INTEGER
  - innings_played INTEGER

-- Transition log (for Markov analysis)
transition_log
  - log_id BIGSERIAL
  - run_id UUID
  - from_state INTEGER  -- 0-23 base-out encoding
  - to_state INTEGER
  - event_type VARCHAR
  - runs_scored INTEGER
  - timestamp
```

**Schema: backtest** (NEW)
```sql
backtest_runs
  - run_id SERIAL PRIMARY KEY
  - model_id INTEGER
  - version_id INTEGER
  - config JSONB           -- Full configuration
  - status VARCHAR
  - total_iterations INTEGER
  - completed_iterations INTEGER

backtest_iterations
  - iteration_id BIGSERIAL
  - run_id INTEGER
  - train_start, train_end DATE
  - test_start, test_end DATE
  - train_samples, test_samples INTEGER
  - metrics JSONB          -- accuracy, log_loss, auc, etc.

backtest_predictions
  - prediction_id BIGSERIAL
  - iteration_id INTEGER
  - game_pk, play_id
  - predicted_value, actual_value
  - probability JSONB
```

### GitHub Issues Structure

**Epic: ML Model Layer (Milestone 11)**
├── Issue #1: Model Registry CLI Commands ✅
│   ├── Sub: list command
│   ├── Sub: promote command
│   └── Sub: archive command
├── Issue #2: Backtesting Framework ✅
│   ├── Sub: BacktestEngine class
│   ├── Sub: Progress tracking & event hooks
│   ├── Sub: Calibration analysis
│   └── Sub: models backtest CLI
├── Issue #3: Monte Carlo Simulation 🔄 CURRENT
│   ├── Sub: Simulation SQL schema
│   ├── Sub: MarkovChainSimulator
│   ├── Sub: MonteCarloSimulator
│   ├── Sub: models simulate CLI
│   └── Sub: Parallel simulation support
├── Issue #4: Batch Prediction Service ⏳
│   ├── Sub: BatchPredictionService class
│   └── Sub: models predict-batch CLI
├── Issue #5: SQL Schema Migration ⏳
│   ├── Sub: 6009_backtest_schema.sql
│   ├── Sub: 6010_simulation_schema.sql
│   └── Sub: 6011_batch_prediction_schema.sql
└── Issue #6: Integration & Testing ⏳
    ├── Sub: End-to-end test: train → backtest → simulate → predict
    └── Sub: Documentation update

## Design Decisions

### 1. State Encoding
**Base-Out State (0-23):**
```
state = outs * 8 + base_encoding
base_encoding: 0=empty, 1=1B, 2=2B, 3=1B+2B, 4=3B, 5=1B+3B, 6=2B+3B, 7=loaded
```

**Benefits:**
- Single integer index for matrix lookup
- Memory efficient
- Fast PostgreSQL indexing

### 2. Transition Matrix Storage
**Option A:** Dense 24×24 matrix in PostgreSQL array
```sql
CREATE TABLE transition_matrix_dense (
    model_id INTEGER,
    matrix NUMERIC[][]  -- 24×24 array
);
```

**Option B:** Sparse edge list (chosen)
```sql
CREATE TABLE transition_matrix (
    model_id INTEGER,
    from_state INTEGER,
    to_state INTEGER,
    probability NUMERIC,
    event_type VARCHAR
);
```

**Rationale:** Sparse is more flexible for custom events (sac flies, errors).

### 3. Feature Storage
**Pre-computed vs On-Demand:**
- **Pre-computed MV:** Fast but stale until refresh
- **On-demand function:** Always fresh, slower

**Decision:** Both. Use MV for batch, function for live.

### 4. Parallelization
**Level 1:** Multiple simulations (parallel iterations)
**Level 2:** Multiple games (parallel game simulation)
**Level 3:** Multiple seasons (parallel backtesting)

**Decision:** Level 1 only for now. Use Python multiprocessing.

## Implementation Priorities

### Phase 3: Monte Carlo (Current)
1. **SQL Schema** (30 min)
   - Create 6010_simulation_schema.sql
   - simulation_runs, simulation_states, simulation_results

2. **MarkovChainSimulator** (1 hour)
   - Use RE24 + transition probabilities
   - Fast baseline for comparison

3. **MonteCarloSimulator** (2 hours)
   - Use PAOutcomeModel for sampling
   - Store state in PostgreSQL

4. **CLI Commands** (30 min)
   - models simulate
   - models simulate-batch

### Phase 4: Batch Service
- Build BatchPredictionService
- Focus on throughput (vectorized prediction)
- Streaming results to PostgreSQL

### Future Enhancements
- **Model drift detection:** Track prediction distribution over time
- **A/B testing:** Compare models head-to-head
- **Feature importance tracking:** Monitor which features matter
- **Ensemble builder:** Stack multiple models
- **Async jobs:** Celery/RQ integration

## References

1. Medium: "Markov Chain Baseball Models" (analytics-vidhya)
2. Lehigh University: "APBA Baseball Simulation Analysis"
3. r/Sabermetrics: Lineup run expectancy discussion
4. MLflow Documentation: Model Registry architecture
5. sabRmetrics R package: MLB API data structures
