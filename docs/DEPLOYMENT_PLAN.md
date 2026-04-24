# Deployment Plan - Extensible MLB Prediction Framework

**Status**: Ready for Implementation  
**Priority**: High  
**Estimated Duration**: 3 weeks (22 hours work)  
**Target Completion**: May 15, 2026  
**Created**: April 24, 2026  
**Owner**: Agent Cascade → Next Agent

---

## Executive Summary

**What**: Implement Pydantic-based extensible framework for baseball prediction research  
**Why**: Enable researchers to easily add custom models, access rich results (residuals, curves), run experiments  
**How**: Thin Python wrappers over existing working infrastructure  
**Risk**: Low - leverages 100% existing code, adds only interface layer  

---

## Prerequisites (Verify Before Starting)

### System Requirements
- [ ] PostgreSQL 14+ running on port 5432
- [ ] Database `retrosheet` exists and is populated
- [ ] Python 3.10+ with `uv` package manager
- [ ] 50GB+ disk space for models and data
- [ ] Git repository cloned at `/home/cbwinslow/workspace/retrosheet`

### Verification Commands
```bash
# Check PostgreSQL
psql -d retrosheet -c "SELECT version();"  # Should return PostgreSQL version

# Check data exists
psql -d retrosheet -c "SELECT COUNT(*) FROM core.games;"  # Should be ~62,000

# Check Python environment
cd /home/cbwinslow/workspace/retrosheet && uv --version  # Should show uv version
direnv allow . && which python  # Should show .venv path

# Check repository
git status  # Should be clean working tree or known changes
```

### Required Reading
Before starting implementation, read these files in order:
1. `docs/WORKFLOW_VALIDATION_REPORT.md` - Understand current infrastructure
2. `docs/EXTENSIBLE_FRAMEWORK_DESIGN.md` - Understand target architecture  
3. `docs/FRAMEWORK_CONFIRMATION.md` - Confirm approach is correct
4. `docs/IMPLEMENTATION_ROADMAP.md` - Detailed implementation steps
5. `docs/DEPLOYMENT_PLAN.md` - This file

---

## Phase 1: Foundation (Week 1) - 6 hours

### 1.1 Create Pydantic Configuration Schemas (2 hours)

**Goal**: Type-safe configuration system with validation

**Files to Create**:
```
mlb_predict/
├── __init__.py                    # Package exports
├── config/
│   ├── __init__.py
│   ├── schemas.py                 # Core Pydantic models
│   ├── loader.py                  # YAML/JSON loading
│   └── defaults.py                # Default values
```

**Implementation Details**:

`mlb_predict/config/schemas.py`:
```python
from pydantic import BaseModel, Field, validator
from enum import Enum
from typing import List, Dict, Optional, Any, Literal
from datetime import date

class ModelFamily(str, Enum):
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    CATBOOST = "catboost"
    SKLEARN_GBM = "sklearn_histgradient"
    LOGISTIC = "logistic_regression"
    CUSTOM = "custom"

class TargetVariable(str, Enum):
    SWING_DECISION = "swing_decision"
    CONTACT_MADE = "contact_made"
    HIT_OUTCOME = "hit_outcome"
    PA_OUTCOME = "pa_outcome"
    WIN_PROBABILITY = "win_probability"

class FeatureSet(str, Enum):
    BASIC = "basic"
    PHYSICS = "physics"
    CONTEXT = "context"
    ADVANCED = "advanced"
    COMPLETE = "complete"
    CUSTOM = "custom"

class XGBoostConfig(BaseModel):
    max_depth: int = Field(6, ge=1, le=20)
    n_estimators: int = Field(200, ge=10, le=2000)
    learning_rate: float = Field(0.05, ge=0.001, le=1.0)
    subsample: float = Field(0.8, ge=0.1, le=1.0)
    colsample_bytree: float = Field(0.8, ge=0.1, le=1.0)
    min_child_weight: int = Field(3, ge=1, le=20)
    gamma: float = Field(0, ge=0, le=10)
    reg_alpha: float = Field(0, ge=0, le=10)
    reg_lambda: float = Field(1, ge=0, le=10)
    tree_method: str = "hist"

class ModelConfig(BaseModel):
    family: ModelFamily
    target: TargetVariable
    features: FeatureSet = FeatureSet.ADVANCED
    custom_features: Optional[List[str]] = None
    exclude_features: Optional[List[str]] = None
    xgboost: Optional[XGBoostConfig] = None
    seasons: List[int] = Field(default_factory=lambda: [2023, 2024, 2025])
    calibration: bool = True
    compute_shap: bool = False
```

**Validation Tests**:
```python
# These should raise ValidationError
try:
    ModelConfig(family="invalid")
except ValidationError:
    pass  # ✅ Correct

try:
    ModelConfig(xgboost={'max_depth': 50})
except ValidationError:
    pass  # ✅ Correct
```

**Deliverable**: 
- [ ] All config classes implemented
- [ ] Validation working
- [ ] Can load/save YAML configs
- [ ] Tests pass: `pytest tests/test_config.py -v`

---

### 1.2 Create Rich Result Classes (3 hours)

**Goal**: Return objects with full analysis capabilities

**Files to Create**:
```
mlb_predict/core/
├── __init__.py
├── results.py                     # TrainResult, PredictResult
└── metrics.py                     # Metrics calculations
```

**Key Classes**:

`TrainResult` must have:
```python
class TrainResult(BaseModel):
    # Identity
    model_id: int
    model_name: str
    
    # Config
    config: ModelConfig
    created_at: datetime
    
    # Metrics
    train_metrics: Metrics
    val_metrics: Metrics
    test_metrics: Optional[Metrics]
    
    # Deep analysis
    residuals: Optional[Residuals]
    validation_curves: List[ValidationCurve]
    feature_importance: List[FeatureImportance]
    
    # Methods
    def to_dataframe(self) -> pd.DataFrame
    def save_to_registry(self) -> None
    def get_best_features(self, n: int) -> List[FeatureImportance]
    def compare_to(self, other: 'TrainResult') -> Dict[str, Any]
    def generate_report(self, path: str) -> str
```

`Residuals` must have:
```python
class Residuals(BaseModel):
    y_true: List[float]
    y_pred: List[float]
    residuals: List[float]
    
    def to_dataframe(self) -> pd.DataFrame
    def analyze(self) -> Dict[str, float]  # mean, std, skew, kurtosis
    def plot_residuals(self) -> matplotlib.Figure
```

**Deliverable**:
- [ ] All result classes implemented
- [ ] Analysis methods working
- [ ] Plotting functions working
- [ ] Tests pass: `pytest tests/test_results.py -v`

---

### 1.3 Test Infrastructure (1 hour)

**Files to Create**:
```
tests/
├── __init__.py
├── test_config.py                 # Config validation tests
└── test_results.py                # Result class tests
```

**Test Coverage**:
- [ ] Config validation (valid and invalid cases)
- [ ] Enum constraint checking  
- [ ] Result serialization/deserialization
- [ ] Metric calculations

**Deliverable**:
- [ ] Test files created
- [ ] All tests pass

---

## Phase 2: Core Wrappers (Week 2) - 10 hours

### 2.1 ModelTrainer Class (4 hours)

**Goal**: Wrap existing training scripts with rich interface

**File**: `mlb_predict/core/trainer.py`

**Interface**:
```python
class ModelTrainer:
    @staticmethod
    def train(config: ModelConfig) -> TrainResult:
        """Train model using existing scripts."""
        pass
    
    @staticmethod
    def load_result(model_id: int) -> TrainResult:
        """Load previous training result from registry."""
        pass
    
    @staticmethod
    def list_models(target: Optional[str] = None) -> pd.DataFrame:
        """List models from registry."""
        pass
```

**Implementation Steps**:
1. Convert ModelConfig to command-line args for `train_models.py`
2. Call `scripts/model_training/train_models.py` via subprocess
3. Parse stdout/stderr for training progress
4. Query database for model_id and metrics
5. Load predictions to compute residuals
6. Extract validation curves from XGBoost output
7. Build TrainResult with all data
8. Return rich result

**Key Integration Points**:
- Calls: `scripts/model_training/train_models.py`
- Reads: `features_pitch.model_training_set`
- Writes: `models.model_registry`
- Saves: `models/*.pkl`

**Error Handling**:
- If training fails, capture error message in result
- Return partial result with error details
- Log to `framework.log` table

**Deliverable**:
- [ ] ModelTrainer implemented
- [ ] Can train XGBoost model
- [ ] Returns TrainResult with all fields populated
- [ ] Tests pass: `pytest tests/test_trainer.py -v`

---

### 2.2 Plugin Registry (2 hours)

**Goal**: Enable any model to plug into framework

**Files**:
```
mlb_predict/core/
├── plugin.py                      # PluginModel base class
└── registry.py                    # PluginRegistry
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
    _plugins: Dict[str, Type[PluginModel]] = {}
    
    @classmethod
    def register(cls, name: str, plugin_class: Type[PluginModel]) -> None:
        cls._plugins[name] = plugin_class
    
    @classmethod
    def get(cls, name: str) -> Type[PluginModel]:
        return cls._plugins[name]
    
    @classmethod
    def list_plugins(cls) -> Dict[str, Type[PluginModel]]:
        return cls._plugins.copy()
```

**Deliverable**:
- [ ] PluginModel ABC implemented
- [ ] PluginRegistry implemented
- [ ] Can register custom model
- [ ] Tests pass: `pytest tests/test_plugins.py -v`

---

### 2.3 FeatureLoader (2 hours)

**Goal**: Load features from database with simple interface

**File**: `mlb_predict/data/feature_loader.py`

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
        """Get metadata for a feature from registry."""
        pass
```

**Implementation**:
- Query `features_pitch.feature_registry` for feature definitions
- Query `features_pitch.engineered_features` for data
- Handle train/val/test splits
- Return pandas DataFrame

**Deliverable**:
- [ ] FeatureLoader implemented
- [ ] Can load any feature set
- [ ] Returns properly formatted DataFrame

---

### 2.4 Experiment Runner (2 hours)

**Goal**: Run multi-model experiments with tracking

**File**: `mlb_predict/core/experiment.py`

**Interface**:
```python
class Experiment:
    @staticmethod
    def run(config: ExperimentConfig) -> ExperimentResult:
        """Run full experiment with multiple models."""
        pass
    
    @staticmethod
    def compare_models(model_ids: List[int]) -> pd.DataFrame:
        """Compare multiple models."""
        pass
```

**Features**:
- Run multiple model configs in sequence
- Track progress of each step
- Generate comparison table
- Save experiment metadata

**Deliverable**:
- [ ] Experiment class implemented
- [ ] Can run multi-model experiments
- [ ] Generates comparison reports

---

## Phase 3: Polish (Week 3) - 6 hours

### 3.1 Unified CLI (2 hours)

**Goal**: Single command-line interface for all operations

**Files**:
```
mlb_predict/cli/
├── __init__.py
└── main.py                        # CLI implementation
scripts/mlb-predict                # Shell wrapper
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

**Implementation**:
- Use `click` or `typer` for CLI framework
- Load configs and dispatch to appropriate classes
- Format output nicely (tables, progress bars)
- Handle errors gracefully

**Deliverable**:
- [ ] CLI implemented
- [ ] All commands working
- [ ] Help text complete
- [ ] Tests pass: `pytest tests/test_cli.py -v`

---

### 3.2 Database Triggers (1 hour)

**Goal**: Auto-log training events to database

**File**: `sql/framework/010_training_triggers.sql`

**Triggers**:
```sql
-- Auto-log training start
CREATE OR REPLACE FUNCTION framework.log_training_start()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO framework.log (log_level, component, operation, message, details)
    VALUES ('INFO', 'model', 'train_start', 
            'Started training model: ' || NEW.model_name,
            jsonb_build_object('model_id', NEW.model_id, 
                              'target', NEW.target_id));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER log_training_start_trigger
    BEFORE INSERT ON models.model_registry
    FOR EACH ROW
    EXECUTE FUNCTION framework.log_training_start();
```

**Deliverable**:
- [ ] Triggers created
- [ ] Auto-logging working
- [ ] Tests verify logging

---

### 3.3 Documentation (2 hours)

**Goal**: Complete documentation for users

**Files to Create/Update**:
```
docs/
├── PYTHON_API.md                  # API reference
├── PLUGIN_GUIDE.md                # How to add custom models
├── CLI_REFERENCE.md               # CLI command reference
└── EXAMPLES.md                    # Example notebooks
```

**Deliverable**:
- [ ] API documentation complete
- [ ] Plugin guide with examples
- [ ] CLI reference with all commands
- [ ] Example notebooks working

---

## Testing Strategy

### Unit Tests (4 hours total)

```bash
# Config tests
pytest tests/test_config.py -v

# Result tests  
pytest tests/test_results.py -v

# Trainer tests (mocked)
pytest tests/test_trainer.py -v

# Plugin tests
pytest tests/test_plugins.py -v

# CLI tests
pytest tests/test_cli.py -v
```

### Integration Tests (2 hours total)

```bash
# Real training (small data)
pytest tests/integration/test_training.py -v

# Real predictions
pytest tests/integration/test_inference.py -v

# Plugin integration
pytest tests/integration/test_plugins.py -v
```

### E2E Tests (2 hours total)

```bash
# Full pipeline
pytest tests/e2e/test_pipeline.py -v

# Full experiment
pytest tests/e2e/test_experiment.py -v
```

---

## Documentation Updates Required

### Files to Update After Implementation

1. **docs/agents/FILE_INVENTORY.md**
   - Add new Python files
   - Add new test files
   - Mark implementation status

2. **docs/USER_MANUAL.md**
   - Update examples to use new API
   - Add CLI examples
   - Add plugin examples

3. **docs/PROCEDURES_DETAILED.md**
   - Add procedures for using framework
   - Update model training procedures

4. **docs/PROJECT_LOG.md**
   - Log implementation progress
   - Note any issues or changes

---

## GitHub Project Tracking

### Milestones

**Milestone 1: Foundation Complete** (Week 1)
- [ ] Pydantic configs implemented
- [ ] Result classes implemented
- [ ] Tests passing

**Milestone 2: Core Wrappers Complete** (Week 2)
- [ ] ModelTrainer working
- [ ] Plugin system working
- [ ] FeatureLoader working
- [ ] Experiment runner working

**Milestone 3: Polish Complete** (Week 3)
- [ ] CLI implemented
- [ ] Triggers created
- [ ] Documentation complete
- [ ] All tests passing

### GitHub Issues to Create

1. **Issue #1**: Implement Pydantic Configuration Schemas
   - Priority: High
   - Milestone: Foundation
   - Labels: `enhancement`, `config`, `pydantic`

2. **Issue #2**: Implement Rich Result Classes
   - Priority: High
   - Milestone: Foundation
   - Labels: `enhancement`, `results`, `analysis`

3. **Issue #3**: Implement ModelTrainer Class
   - Priority: High
   - Milestone: Core Wrappers
   - Labels: `enhancement`, `training`, `wrapper`

4. **Issue #4**: Implement Plugin Registry
   - Priority: High
   - Milestone: Core Wrappers
   - Labels: `enhancement`, `plugin`, `extensibility`

5. **Issue #5**: Implement Unified CLI
   - Priority: Medium
   - Milestone: Polish
   - Labels: `enhancement`, `cli`, `ux`

6. **Issue #6**: Create Database Triggers
   - Priority: Medium
   - Milestone: Polish
   - Labels: `enhancement`, `database`, `logging`

7. **Issue #7**: Write Documentation
   - Priority: Medium
   - Milestone: Polish
   - Labels: `documentation`, `help wanted`

---

## Handoff Checklist

### If Another Agent Takes Over:

- [ ] Read all documents in `docs/` directory
- [ ] Verify prerequisites (PostgreSQL, data, environment)
- [ ] Run existing tests: `pytest tests/ -v`
- [ ] Review current implementation status
- [ ] Check GitHub issues for assigned work
- [ ] Update PROJECT_LOG.md with status

### Daily Standup Questions:

1. What did you complete yesterday?
2. What are you working on today?
3. Any blockers or issues?
4. Need to update documentation?

### Weekly Review:

- [ ] Milestone deliverables complete?
- [ ] Tests passing?
- [ ] Documentation updated?
- [ ] GitHub issues closed/updated?
- [ ] PROJECT_LOG.md updated?

---

## Rollback Plan

If implementation needs to be aborted:

1. **Revert SQL**:
   ```sql
   DROP TRIGGER IF EXISTS log_training_start_trigger ON models.model_registry;
   DROP FUNCTION IF EXISTS framework.log_training_start();
   ```

2. **Revert Python**:
   ```bash
   rm -rf mlb_predict/
   rm -rf tests/
   ```

3. **Preserve Data**:
   - All models remain in `models.model_registry`
   - All artifacts remain in `models/`
   - Direct script access still works

**Zero data loss, zero breaking changes**

---

## Success Criteria

### Technical Metrics

- [ ] All configs validate correctly (>95% error catch rate)
- [ ] All results serialize/deserialize without data loss
- [ ] Residuals accessible on every training run
- [ ] Feature importance computed for all models
- [ ] Custom models can be registered and used
- [ ] CLI all commands work without errors
- [ ] 100% test pass rate

### User Experience Metrics

- [ ] New researcher productive in <15 minutes
- [ ] Custom model added in <30 minutes
- [ ] Experiment re-runs in <5 minutes
- [ ] Error messages are helpful and actionable
- [ ] Documentation answers all common questions

---

## Contact & Support

### Documentation
- Architecture: `docs/EXTENSIBLE_FRAMEWORK_DESIGN.md`
- Implementation: `docs/IMPLEMENTATION_ROADMAP.md`
- User guide: `docs/USER_MANUAL.md`
- Procedures: `docs/PROCEDURES_DETAILED.md`

### GitHub
- Issues: Create issues for each milestone
- Project: Add to GitHub project board
- Wiki: Update with implementation notes

---

**Ready to Begin Implementation**

This plan provides everything needed to implement the extensible framework:
- Clear phases with deliverables
- Specific files to create
- Implementation details
- Testing strategy
- Documentation updates
- GitHub tracking
- Rollback procedures

**Next Action**: Start Phase 1.1 (Pydantic Configuration Schemas)

**End of Deployment Plan**
