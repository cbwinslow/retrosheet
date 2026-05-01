# ML Layer Implementation Plan

## Research: Sabermetric Modeling Patterns

### Key Findings
1. **Monte Carlo Simulation** - Store state in PostgreSQL, not memory (Tallavarjula 2026)
2. **MCMC** - PostgreSQL chains for walk-forward validation (Williams College)
3. **Bayesian Regression** - Store posterior distributions in JSONB (MDPI)
4. **PostgreSQL Pattern** - Raw → Staging → Features → Models → Predictions

## Existing Infrastructure

### SQL (sql/60_models/)
- `6001_models_registry.sql` - Registry, versions, training_runs, artifacts, predictions
- `6008_inference_functions.sql` - `predict_plate_appearance_batch()`, `init_simulation()`, `get_simulation_state()`
- `inference.simulation_states` table - Monte Carlo state persistence
- `inference.plate_appearance_features` MV - Pre-computed features

### Python (baseball/models/)
- `base.py` - BaseModel, SklearnBaseModel, ModelConfig
- `next_run_model.py` - NextRunProbabilityModel
- `pa_outcome_model.py` - PAOutcomeModel  
- `win_probability_model.py` - WinProbabilityModel
- `training.py` - TrainingPipeline
- `registry.py` - ModelRegistry
- `inference.py` - InferencePipeline

## Implementation Plan

### Phase 1: CLI Enhancements
```python
@models_app.command("list")
def models_list(model_name=None, status=None, season=None, limit=20)

@models_app.command("promote")
def models_promote(model_name: str, version: str, to_status: str = "production")

@models_app.command("archive")
def models_archive(model_name: str, version: str)
```

### Phase 2: Backtesting
```python
# baseball/models/backtesting.py
@dataclass
class BacktestResult:
    model_name: str
    accuracy: float
    log_loss: float
    calibration_error: float
    roi: Optional[float]
    by_season: Dict[int, dict]

class BacktestEngine:
    def run_backtest(self, model_params, feature_set) -> BacktestResult
    def evaluate_calibration(self, predictions) -> Dict

# CLI:
@models_app.command("backtest")
def models_backtest(model_name, seasons, window_days=7)
```

### Phase 3: Monte Carlo Simulation ✓ COMPLETE

**Design Document:** `docs/RESEARCH_ML_SIMULATION_DESIGN.md`

**Implementation:**
```python
# baseball/models/schemas.py - Pydantic schemas
class SimulationConfig(BaseModel):
    simulation_type: SimulationType  # MARKOV, MONTE_CARLO, HYBRID
    num_iterations: int
    starting_state: GameState
    home_lineup: LineupConfig
    away_lineup: LineupConfig

class GameState(BaseModel):
    inning: int
    is_bottom: bool
    home_score: int
    away_score: int
    outs: int
    bases: int  # Bitmask: 1=1B, 2=2B, 4=3B
    batter_id: Optional[str]
    pitcher_id: Optional[str]

class BaseOutState(BaseModel):
    """24 base-out states (outs: 0-2, base_encoding: 0-7)"""
    outs: int
    base_encoding: int
    @property
    def state_id(self) -> int: return self.outs * 8 + self.base_encoding

# baseball/models/simulation.py - Simulators
class BaseSimulator(ABC):
    def simulate_game(self, config: SimulationConfig) -> SimulationResult
    def simulate_inning(self, state: GameState, lineup: List[str]) -> Tuple[GameState, int]
    def simulate_pa(self, state: GameState, batter_id, pitcher_id) -> Tuple[EventType, int, GameState]

class MarkovChainSimulator(BaseSimulator):
    """Fast simulation using pre-computed transition matrices (~90% accuracy)"""
    def _load_transition_matrix(self) -> Dict[int, List[Tuple]]

class MonteCarloSimulator(BaseSimulator):
    """ML-based simulation using PAOutcomeModel (~95% accuracy)"""
    def __init__(self, pa_model: PAOutcomeModel)
    def _get_pa_features(self, state, batter_id, pitcher_id) -> Dict[str, Any]

class SimulationService:
    """High-level service with PostgreSQL persistence and progress tracking"""
    def run_simulation(self, config: SimulationConfig) -> SimulationResponse
    def run_parallel_simulation(self, config: SimulationConfig, max_workers: int) -> SimulationResponse

# CLI (pending):
@models_app.command("simulate")
def models_simulate(game_id, season, inning, is_bottom, home_score, away_score, iterations)

@models_app.command("simulate-batch")
def models_simulate_batch(games_file, iterations, parallel)
```

**SQL Schema:** `sql/60_models/6010_simulation_schema.sql`
```sql
simulation.runs              -- Top-level tracking
simulation.states            -- Per-iteration state
simulation.results           -- Final outcomes
simulation.transitions       -- Markov chain log
simulation.transition_matrix  -- Transition probabilities
simulation.re24              -- Run expectancy MV (24 states)
```

**GitHub Issues:** Epic #108 with sub-issues #109-#113

### Phase 4: Batch Predictions
```python
# baseball/models/batch_inference.py
class BatchPredictionService:
    def predict_games(self, game_pks, save_to_db) -> pd.DataFrame
    def predict_season(self, season, start_date, end_date) -> pd.DataFrame

# CLI:
@models_app.command("predict-batch")
def models_predict_batch(model_name, games_file, season, output_file)
```

## SQL Additions
```sql
-- Backtest results
CREATE TABLE models.backtest_results (
    backtest_id SERIAL PRIMARY KEY,
    model_name TEXT, model_version TEXT,
    accuracy NUMERIC(5,4), log_loss NUMERIC(10,6),
    calibration_error NUMERIC(10,6), roi NUMERIC(10,2),
    metadata JSONB
);

-- Simulation results
CREATE TABLE models.simulation_results (
    simulation_id TEXT PRIMARY KEY,
    game_id TEXT, season INTEGER, num_iterations INTEGER,
    home_win_probability NUMERIC(5,4),
    expected_runs_home NUMERIC(6,3),
    run_distribution_home JSONB
);

-- Batch jobs
CREATE TABLE models.batch_prediction_jobs (
    job_id SERIAL PRIMARY KEY,
    model_name TEXT, total_games INTEGER,
    processed_games INTEGER, status TEXT,
    output_file TEXT
);
```

## Integration Points

| SQL Function | Python Method |
|--------------|---------------|
| `inference.get_plate_appearance_features()` | `FeatureExtractor.get_features()` |
| `inference.init_simulation()` | `MonteCarloSimulator._init_state()` |
| `register_model()` | `ModelRegistry.register_model()` |
| `promote_to_production()` | `ModelRegistry.promote_to_production()` |

## File Structure
```
baseball/models/
├── __init__.py         # Exports all model classes and schemas
├── base.py             # BaseModel, ModelConfig (existing)
├── backtesting.py      # BacktestEngine ✓ NEW
├── schemas.py          # Pydantic schemas ✓ NEW
├── simulation.py       # BaseSimulator, MarkovChainSimulator, MonteCarloSimulator ✓ NEW
├── next_run_model.py   # NextRunProbabilityModel (existing)
├── pa_outcome_model.py # PAOutcomeModel (existing)
├── win_probability_model.py # WinProbabilityModel (existing)
└── batch_inference.py  # BatchPredictionService (pending)

sql/60_models/
├── 6001_models_registry.sql      # Registry tables (existing)
├── 6008_inference_functions.sql  # Inference functions (existing)
├── 6009_backtest_schema.sql      # Backtest tables (pending)
├── 6010_simulation_schema.sql    # Simulation tables ✓ NEW
└── 6011_batch_prediction_schema.sql # Batch job tables (pending)

baseball/cli.py:
├── models train           # Train models (existing)
├── models predict         # Single game prediction (existing)
├── models batch-predict   # Batch predictions (existing)
├── models list            # List models ✓ NEW
├── models promote         # Promote to production ✓ NEW
├── models archive         # Archive model ✓ NEW
├── models backtest        # Walk-forward validation ✓ NEW
├── models simulate        # Monte Carlo simulation (pending)
└── models simulate-batch  # Batch simulation (pending)
```

## Next Steps
1. ✅ Create backtesting.py with BacktestEngine (COMPLETED)
2. ✅ Create simulation.py with MarkovChainSimulator + MonteCarloSimulator (COMPLETED)
3. ✅ Create Pydantic schemas.py for type-safe configuration (COMPLETED)
4. ✅ Create SQL schema for simulation (6010_simulation_schema.sql) (COMPLETED)
5. ✅ Create design document (RESEARCH_ML_SIMULATION_DESIGN.md) (COMPLETED)
6. ✅ Update migration_map.md (COMPLETED)
7. ✅ Create GitHub Epic and sub-issues for tracking (COMPLETED)
8. ⏳ Add models simulate CLI command (NEXT)
9. ⏳ Add models simulate-batch CLI command (NEXT)
10. ⏳ Create backtest schema (6009_backtest_schema.sql)
