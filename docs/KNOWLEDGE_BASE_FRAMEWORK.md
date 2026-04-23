# Modular Prediction Framework Architecture

**Date:** 2026-04-22
**Purpose:** Research-backed flexible framework for multi-target baseball predictions

## Design Philosophy

The framework follows a **Strategy/Registry pattern** that ensures:

1. **Flexibility**: Each prediction target is independent — adding `no_hit_inning` doesn't require changes to `pa_outcome_distribution`
2. **Pluggable models**: Model families can be swapped per target without modifying targets
3. **Clear contracts**: Each target/model declares its required features, no hidden dependencies
4. **Research-backed**: Model selection follows documented research findings

## Architecture

```
predictions/
├── registry.py              # What targets and models are available
├── base.py                 # Base target and model classes
│
├── targets/                # Prediction targets (independent)
│   ├── __init__.py
│   ├── target_registry.py   # Target registration
│   ├── pa_outcome.py      # PA outcome distribution
│   ├── inning_runs.py     # Inning runs distribution
│   ├── next_state.py     # Next base-out state
│   ├── pitcher_k_rate.py  # Pitcher strikeout rate
│   └── no_hit_inning.py   # No-hit inning probability
│
├── models/                 # Model families (pluggable)
│   ├── __init__.py
│   ├── model_registry.py   # Model registration
│   ├── markov_chain.py    # Uninformed Markov chain
│   ├── markov_informed.py # Feature-conditioned Markov
│   ├── hgb.py          # HistGradientBoosting
│   ├── softmax.py       # Multinomial logistic
│   └── baseline.py     # Empirical baseline
│
└── features/              # Feature definitions (target-specific)
    ├── __init__.py
    ├── pa_features.py
    ├── inning_features.py
    └── state_features.py
```

## Core Contracts

### Target Contract

Each target must define:

```python
class BaseTarget(ABC):
    target_id: str              # Unique identifier (e.g., "pa_outcome_distribution")
    target_name: str           # Human-readable name
    target_type: str           # "multiclass" | "binary" | "regression" | "distribution"
    variable_definition: str   # Precise variable definition
    required_features: List[str]  # Features this target needs
    supported_models: List[str]     # Model families that work for this target
    training_seasons: Tuple[int, int]  # Min/max training seasons
    
    @abstractmethod
    def get_training_query(self) -> str:
        """SQL query to fetch training data."""
        pass
    
    @abstractmethod
    def get_features_query(self, game_state: dict) -> str:
        """SQL query to fetch features for prediction."""
        pass
```

### Model Contract

Each model must define:

```python
class BaseModel(ABC):
    model_id: str              # Unique identifier
    model_name: str           # Human-readable name
    model_family: str          # "markov_chain", "hgb", "softmax", "baseline"
    model_type: str           # "discriminative" | "generative" | "empirical"
    supported_targets: List[str]  # Which targets can use this model
    
    @abstractmethod
    def fit(self, X: pd.DataFrame, y: np.ndarray) -> None:
        """Fit the model."""
        pass
    
    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Return predictions."""
        pass
    
    @abstractmethod
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return probability distribution."""
        pass
```

## Target Definitions

### 1. pa_outcome_distribution
- **Variable**: Full probability distribution over PA outcomes
- **Taxonomy**: grouped (strikeout, walk, single, double, HR, ground_out, air_out, etc.)
- **Current model**: HGB + advanced_count (log loss 1.5089)
- **Research**: See KNOWLEDGE_BASE_SABERMETRICS.md

### 2. inning_runs_distribution
- **Variable**: How many runs in this half-inning?
- **States**: 0, 1, 2, 3, 4+ runs
- **Best model**: Uninformed Markov (empirical RE matrix)
- **Research**: See KNOWLEDGE_BASE_MARKOV_CHAIN.md

### 3. next_state_distribution
- **Variable**: Next base-out state probability
- **States**: 24 base-out states + inning-end
- **Best model**: Softmax regression, informed Markov
- **Research**: Stanford CS229, UT Austin

### 4. pitcher_strikeout_rate
- **Variable**: P(strikeout | pitcher, batter, count, context)
- **Type**: Binary
- **Best model**: HGB + pitcher features

### 5. no_hit_inning_X
- **Variable**: P(runs=0 | inning X, team context)
- **Type**: Binary
- **Best model**: Informed Markov + ML hybrid
- **Example**: "no hits in 3rd inning with runner on 3rd"

## Model Selection Matrix

| Target Type | Target | Recommended Models | Alternative |
|------------|--------|-------------------|-------------|
| Multi-class | pa_outcome | HGB, Softmax | Ensemble |
| Distribution | inning_runs | Markov uninformed | Empirical baseline |
| Discrete state | next_state | Softmax, Markov informed | HGB (discretized) |
| Binary | pitcher_k_rate | HGB, Logistic | Baseline |
| Binary | no_hit_inning | Markov + ML hybrid | HGB |
| Regression | total_runs | Markov + ML hybrid | HGB regression |

## Research Backing

### From KNOWLEDGE_BASE_MARKOV_CHAIN.md
- Stanford CS229: Softmax regression beats Vegas over/under
- UT Austin: Markov chain for run/win probability
- mlb-win-probability: Ensemble achieves Brier 0.1605

### From KNOWLEDGE_BASE_SABERMETRICS.md
- Game outcome prediction: 59-60% accuracy with ML + sabermetrics
- Feature selection critical for model performance
- Interpretability + ML combination recommended

### Model Selection Heuristics
1. **Start simple**: Empirical baseline → Markov → ML
2. **Add features incrementally**: Uninformed → Informed → ML
3. **Ensemble for production**: Combine multiple models
4. **Calibrate always**: Isotonic, Platt for probability outputs

## Implementation Status

### To Be Built
- [ ] predictions/registry.py (base registry)
- [ ] predictions/base.py (base classes)
- [ ] predictions/targets/pa_outcome.py (port existing)
- [ ] predictions/models/markov_chain.py (first new model)
- [ ] predictions/features/run_expectancy.py (RE matrix features)

### Research Gaps
- [x] Markov chain research ✓
- [ ] Softmax regression implementation
- [ ] Hit projection (tango-style)
- [ ] Win probability (RE24-based)

## Related Docs

- [docs/KNOWLEDGE_BASE_MARKOV_CHAIN.md](docs/KNOWLEDGE_BASE_MARKOV_CHAIN.md) — Markov research
- [docs/KNOWLEDGE_BASE_SABERMETRICS.md](docs/KNOWLEDGE_BASE_SABERMETRICS.md) — Sabermetrics
- [docs/agents/MODELING_WORKFLOWS.md](docs/agents/MODELING_WORKFLOWS.md) — Current workflows
- [docs/PREDICTION_ENGINE_PLAN.md](docs/PREDICTION_ENGINE_PLAN.md)