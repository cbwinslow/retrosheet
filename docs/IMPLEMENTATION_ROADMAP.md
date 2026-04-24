# Implementation Roadmap - Extensible Framework

**Status**: Ready to Implement  
**Estimated Time**: 22 hours  
**Risk Level**: Low  
**Shippable Phases**: 3

---

## Phase 1: Foundation (6 hours) - CRITICAL PATH

### 1.1 Pydantic Configuration Schemas (2 hours)

**Files to Create**:
```
mlb_predict/config/schemas.py       # Core config classes
mlb_predict/config/loader.py        # YAML/JSON loading
mlb_predict/config/defaults.py      # Default values
```

**Classes to Implement**:
- `ModelFamily` (Enum): XGBOOST, LIGHTGBM, CATBOOST, SKLEARN, CUSTOM
- `TargetVariable` (Enum): SWING_DECISION, CONTACT_MADE, HIT_OUTCOME, PA_OUTCOME
- `FeatureSet` (Enum): BASIC, PHYSICS, CONTEXT, ADVANCED, COMPLETE, CUSTOM
- `ValidationStrategy` (Enum): TEMPORAL, RANDOM, K_FOLD, GROUP
- `XGBoostConfig`: max_depth, n_estimators, learning_rate, etc.
- `LightGBMConfig`: num_leaves, n_estimators, etc.
- `SplitConfig`: train/val/test ratios, strategy
- `ModelConfig`: Complete model specification

**Validation Examples**:
```python
# Should raise ValidationError immediately
ModelConfig(family="invalid")  # ❌ Not a valid ModelFamily
ModelConfig(xgboost={'max_depth': 50})  # ❌ max_depth > 20
```

**Deliverable**: Can load and validate configs from YAML

---

### 1.2 Rich Result Classes (3 hours)

**Files to Create**:
```
mlb_predict/core/results.py         # Result classes
mlb_predict/core/metrics.py         # Metrics calculations
```

**Classes to Implement**:
- `MetricValue`: value + std + confidence intervals
- `Metrics`: roc_auc, log_loss, accuracy, precision, recall, f1, calibration
- `ValidationCurve`: train/val curves with plotting
- `FeatureImportance`: feature name, score, rank, method
- `Residuals`: y_true, y_pred, residuals + analysis methods
- `TrainResult`: Complete training output
  - model_id, config, metrics (train/val/test)
  - validation_curves, feature_importance, residuals
  - save_to_registry(), to_dataframe(), get_best_features()
  - compare_to(), generate_report()

**Methods to Implement**:
```python
# Residuals analysis
residuals.analyze() -> Dict[str, float]  # mean, std, skewness
residuals.to_dataframe() -> pd.DataFrame
residuals.plot_residuals() -> matplotlib.Figure

# Model comparison
result.compare_to(other_result) -> Dict[str, Any]

# Feature importance
result.get_best_features(n=20) -> List[FeatureImportance]

# Reporting
result.generate_report(path) -> str  # HTML/Markdown
```

**Deliverable**: Can create, manipulate, and save rich results

---

### 1.3 Test Infrastructure (1 hour)

**Files to Create**:
```
tests/test_config.py               # Config validation tests
tests/test_results.py              # Result class tests
```

**Tests to Write**:
- Config validation (valid/invalid cases)
- Enum constraint checking
- Result serialization/deserialization
- Metric calculations

**Deliverable**: `pytest tests/test_config.py` passes

---

## Phase 2: Core Wrappers (10 hours) - CRITICAL PATH

### 2.1 ModelTrainer Class (4 hours)

**Files to Create/Update**:
```
mlb_predict/core/trainer.py        # Main trainer class
```

**Interface**:
```python
class ModelTrainer:
    def train(self, config: ModelConfig) -> TrainResult:
        """Train model and return rich result."""
        pass
    
    def load_result(self, model_id: int) -> TrainResult:
        """Load previous training result."""
        pass
    
    def list_models(self, target: Optional[str] = None) -> pd.DataFrame:
        """List models from registry."""
        pass
```

**Implementation Steps**:
1. Convert ModelConfig to command-line args for train_models.py
2. Call train_models.py via subprocess
3. Parse stdout/stderr for results
4. Query database for model_id and metrics
5. Compute residuals from predictions
6. Extract validation curves from XGBoost output
7. Build TrainResult with all data
8. Return rich result

**Integration Points**:
- Calls `scripts/model_training/train_models.py`
- Reads from `features_pitch.model_training_set`
- Writes to `models.model_registry`
- Saves artifacts to `models/*.pkl`

**Deliverable**: Can train XGBoost model and get TrainResult

---

### 2.2 Plugin Registry (2 hours)

**Files to Create**:
```
mlb_predict/core/plugin.py         # Plugin base class
mlb_predict/core/registry.py       # Plugin registry
```

**Base Class**:
```python
class PluginModel(ABC):
    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'PluginModel':
        pass
    
    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        pass
    
    @abstractmethod
    def get_feature_importance(self) -> List[FeatureImportance]:
        pass
    
    @abstractmethod
    def save(self, path: str) -> None:
        pass
    
    @classmethod
    @abstractmethod
    def load(cls, path: str) -> 'PluginModel':
        pass
```

**Registry**:
```python
class PluginRegistry:
    @staticmethod
    def register(name: str, cls: Type[PluginModel]) -> None:
        pass
    
    @staticmethod
    def get(name: str) -> Type[PluginModel]:
        pass
    
    @staticmethod
    def list_plugins() -> Dict[str, Type[PluginModel]]:
        pass
```

**Deliverable**: Can register and use custom models

---

### 2.3 FeatureLoader (2 hours)

**Files to Create**:
```
mlb_predict/data/feature_loader.py  # Load features from DB
```

**Interface**:
```python
class FeatureLoader:
    def load_features(
        self,
        feature_set: FeatureSet,
        target: TargetVariable,
        seasons: List[int],
        custom_features: Optional[List[str]] = None,
        exclude_features: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Load feature matrix from database."""
        pass
    
    def get_feature_info(self, feature_name: str) -> Dict[str, Any]:
        """Get metadata for a feature."""
        pass
```

**Deliverable**: Can load any feature set from database

---

### 2.4 Experiment Runner (2 hours)

**Files to Create**:
```
mlb_predict/core/experiment.py      # Experiment orchestration
```

**Interface**:
```python
class Experiment:
    def run(self, config: ExperimentConfig) -> ExperimentResult:
        """Run full experiment with multiple models."""
        pass
    
    def compare_models(self, model_ids: List[int]) -> pd.DataFrame:
        """Compare multiple models."""
        pass
```

**Features**:
- Run multiple models in sequence
- Track progress of each step
- Generate comparison table
- Save experiment metadata

**Deliverable**: Can run multi-model experiments

---

## Phase 3: Polish (6 hours)

### 3.1 Unified CLI (2 hours)

**Files to Create**:
```
mlb_predict/cli/main.py              # CLI entry point
scripts/mlb-predict                  # Shell wrapper
```

**Commands**:
```bash
# Training
mlb-predict train --config experiment.yaml
mlb-predict train --target swing_decision --family xgboost

# Inference
mlb-predict predict --model-id 123 --game-pk 745555

# Experiment
mlb-predict experiment run --config experiment.yaml
mlb-predict experiment compare --ids 123 124 125

# Registry
mlb-predict registry list --target swing_decision
mlb-predict registry show --id 123

# Analysis
mlb-predict analyze residuals --model-id 123
mlb-predict analyze features --model-id 123
```

**Deliverable**: CLI works for all major operations

---

### 3.2 Database Triggers (1 hour)

**Files to Create**:
```
sql/framework/010_training_triggers.sql
```

**Triggers**:
```sql
-- Auto-log training attempts
CREATE TRIGGER log_training_start
    BEFORE INSERT ON models.model_registry
    FOR EACH ROW
    EXECUTE FUNCTION framework.log_training_start();

-- Auto-update experiment status
CREATE TRIGGER update_experiment_status
    AFTER UPDATE ON models.model_registry
    FOR EACH ROW
    EXECUTE FUNCTION framework.update_experiment_status();
```

**Deliverable**: Database auto-logs training events

---

### 3.3 Logging Framework (1 hour)

**Files to Create**:
```
mlb_predict/utils/logging.py         # Structured logging
```

**Features**:
- Log to `framework.log` table
- Log levels: DEBUG, INFO, WARNING, ERROR
- Structured JSONB for parameters
- Per-experiment log isolation

**Deliverable**: All operations are logged

---

### 3.4 Documentation (2 hours)

**Files to Create/Update**:
```
docs/PYTHON_API.md                 # API reference
docs/PLUGIN_GUIDE.md               # How to add custom models
docs/CLI_REFERENCE.md              # CLI command reference
docs/EXAMPLES.md                   # Example notebooks
```

**Deliverable**: Complete documentation for users

---

## Testing Strategy

### Unit Tests (4 hours)

```
tests/test_config.py               # Config validation
tests/test_results.py              # Result classes
tests/test_metrics.py              # Metric calculations
tests/test_trainer.py              # ModelTrainer (mocked)
tests/test_plugins.py              # Plugin registry
```

### Integration Tests (2 hours)

```
tests/integration/test_training.py # Real training (small data)
tests/integration/test_inference.py # Real predictions
tests/integration/test_plugins.py  # Custom model plugin
```

### E2E Tests (2 hours)

```
tests/e2e/test_pipeline.py         # Full pipeline
tests/e2e/test_experiment.py       # Full experiment
```

---

## Implementation Schedule

| Week | Phase | Hours | Deliverable |
|------|-------|-------|-------------|
| **Week 1** | Foundation | 6 | Configs + Results + Tests |
| **Week 2** | Core Wrappers | 10 | Trainer + Registry + Experiments |
| **Week 3** | Polish + Tests | 6 | CLI + Docs + All Tests |

**Total**: 3 weeks, 22 hours focused work

**Milestone 1 (Week 1)**: Can validate configs and create results  
**Milestone 2 (Week 2)**: Can train models with rich results  
**Milestone 3 (Week 3)**: Full CLI, docs, tests passing  

---

## Success Metrics

### Technical

- [ ] All configs validate correctly
- [ ] All results serialize/deserialize
- [ ] All metrics compute correctly
- [ ] Residuals accessible on every run
- [ ] Feature importance available
- [ ] Custom models plugin works
- [ ] CLI all commands work
- [ ] 100% test pass rate

### User Experience

- [ ] New researcher productive in <15 min
- [ ] Custom model added in <30 min
- [ ] Experiment re-runs in <5 min
- [ ] Error messages are helpful
- [ ] Documentation answers all questions

---

## Risk Mitigation

### Risk: Implementation takes longer

**Mitigation**: 
- Phase 1 is shippable alone (configs + results)
- Can use direct script calls while building wrappers
- Incremental value at each milestone

### Risk: Performance overhead

**Mitigation**:
- Profile early in Phase 2
- If >10% overhead, optimize or provide direct mode
- Keep subprocess calls async where possible

### Risk: Database issues

**Mitigation**:
- Minimal schema changes (only triggers)
- Use existing tables exclusively
- Full rollback capability

### Risk: Researchers resist adoption

**Mitigation**:
- Keep direct script access always available
- Provide clear migration examples
- Demonstrate time savings

---

## Rollback Plan

If major issues discovered:

1. **Revert SQL**: Drop trigger tables (doesn't affect core)
2. **Revert Python**: Uninstall mlb_predict package
3. **Direct access**: Scripts still work independently
4. **Data preserved**: All models, predictions remain in DB

**Zero data loss, zero breaking changes**

---

## Approval Required

### Before Starting Implementation:

- [ ] Confirm this roadmap is correct
- [ ] Confirm 22-hour estimate is acceptable
- [ ] Confirm 3-week timeline works
- [ ] Confirm priority order (Foundation → Wrappers → Polish)

### Ready to Begin?

**Start with Phase 1.1: Pydantic Configuration Schemas?**

Yes → Begin implementation
No → Adjust plan as needed

---

**End of Implementation Roadmap**

This is a solid, achievable plan that delivers maximum utility with low risk.
