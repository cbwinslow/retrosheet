# Extensible Framework Design - Pydantic-Based Model System

**Status**: Design Document  
**Purpose**: Maximize utility through extensible, type-safe Python wrappers  
**Approach**: Thin layer over existing infrastructure with rich interfaces

---

## Core Philosophy

**Every operation should return a rich result object** that includes:
- Model artifacts
- Residuals/errors
- Metadata
- Access to underlying data
- Reproducibility info

**Example**:
```python
result = trainer.train()
result.model_id          # Registered model ID
result.residuals         # Training residuals
result.validation_curves # Loss curves
result.feature_importance# Feature scores
result.config            # Full config used
result.to_dataframe()    # Convert to pandas
result.save_report()     # Save full report
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INTERFACE LAYER                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ CLI          │  │ Python API   │  │ Config Files │        │
│  │ mlb-predict  │  │ ModelTrainer │  │ YAML         │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
└─────────┼────────────────┼────────────────┼──────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│              PYDANTIC INTERFACE LAYER (Rich Types)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ ModelConfig  │  │ TrainResult  │  │ PredictResult│        │
│  │ Experiment   │  │ Validation   │  │ Residuals    │        │
│  │ FeatureSet   │  │ Metrics      │  │ Artifacts    │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
└─────────┼────────────────┼────────────────┼──────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│              WRAPPER LAYER (Calls Existing Scripts)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ ModelTrainer │  │ Experiment   │  │ FeatureLoader│        │
│  │   .train()   │  │   .run()     │  │   .load()    │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
└─────────┼────────────────┼────────────────┼──────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│              EXISTING INFRASTRUCTURE (Unchanged)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ train_models │  │ SQL          │  │ Model        │        │
│  │     .py      │  │ Features     │  │ Registry     │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Pydantic Schema Design

### 1. Configuration Classes

```python
# mlb_predict/config/schemas.py
from pydantic import BaseModel, Field, validator
from enum import Enum
from typing import List, Dict, Optional, Any, Literal
from datetime import date

class ModelFamily(str, Enum):
    """Supported model families."""
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    CATBOOST = "catboost"
    SKLEARN_GBM = "sklearn_histgradient"
    LOGISTIC = "logistic_regression"
    CUSTOM = "custom"

class TargetVariable(str, Enum):
    """Available prediction targets."""
    SWING_DECISION = "swing_decision"      # Swing or take
    CONTACT_MADE = "contact_made"          # Contact (given swing)
    HIT_OUTCOME = "hit_outcome"            # Hit or out (given contact)
    PA_OUTCOME = "pa_outcome"              # Full PA distribution
    WIN_PROBABILITY = "win_probability"    # Game state win prob

class FeatureSet(str, Enum):
    """Pre-defined feature sets."""
    BASIC = "basic"              # 20 core features
    PHYSICS = "physics"          # 50 physics features
    CONTEXT = "context"          # 40 context features
    ADVANCED = "advanced"        # 150 features
    COMPLETE = "complete"        # 220+ features
    CUSTOM = "custom"            # User-defined

class ValidationStrategy(str, Enum):
    """Cross-validation strategies."""
    TEMPORAL = "temporal"        # Time-based split
    RANDOM = "random"            # Random split
    K_FOLD = "k_fold"            # K-fold CV
    GROUP = "group"              # Group-based (e.g., by game)

class SplitConfig(BaseModel):
    """Data splitting configuration."""
    strategy: ValidationStrategy = ValidationStrategy.TEMPORAL
    train_ratio: float = Field(0.7, ge=0.0, le=1.0)
    val_ratio: float = Field(0.15, ge=0.0, le=1.0)
    test_ratio: float = Field(0.15, ge=0.0, le=1.0)
    test_seasons: Optional[List[int]] = None  # If temporal
    random_seed: int = 42
    
    @validator('train_ratio', 'val_ratio', 'test_ratio')
    def ratios_sum_to_one(cls, v, values):
        total = sum([values.get('train_ratio', 0), 
                    values.get('val_ratio', 0), 
                    values.get('test_ratio', 0)])
        if total != 1.0:
            raise ValueError(f'Ratios must sum to 1.0, got {total}')
        return v

class XGBoostConfig(BaseModel):
    """XGBoost hyperparameters."""
    max_depth: int = Field(6, ge=1, le=20)
    n_estimators: int = Field(200, ge=10, le=2000)
    learning_rate: float = Field(0.05, ge=0.001, le=1.0)
    subsample: float = Field(0.8, ge=0.1, le=1.0)
    colsample_bytree: float = Field(0.8, ge=0.1, le=1.0)
    min_child_weight: int = Field(3, ge=1, le=20)
    gamma: float = Field(0, ge=0, le=10)
    reg_alpha: float = Field(0, ge=0, le=10)
    reg_lambda: float = Field(1, ge=0, le=10)
    scale_pos_weight: Optional[float] = None
    tree_method: str = "hist"  # "hist", "gpu_hist", "approx", "exact"
    
class LightGBMConfig(BaseModel):
    """LightGBM hyperparameters."""
    num_leaves: int = Field(31, ge=2, le=256)
    n_estimators: int = Field(200, ge=10, le=2000)
    learning_rate: float = Field(0.05, ge=0.001, le=1.0)
    feature_fraction: float = Field(0.8, ge=0.1, le=1.0)
    bagging_fraction: float = Field(0.8, ge=0.1, le=1.0)
    bagging_freq: int = Field(5, ge=0, le=100)
    min_child_samples: int = Field(20, ge=1, le=100)
    reg_alpha: float = Field(0, ge=0, le=10)
    reg_lambda: float = Field(0, ge=0, le=10)
    
class ModelConfig(BaseModel):
    """Complete model configuration."""
    family: ModelFamily
    target: TargetVariable
    features: FeatureSet = FeatureSet.ADVANCED
    custom_features: Optional[List[str]] = None
    exclude_features: Optional[List[str]] = None
    
    # Model-specific configs (only one should be set)
    xgboost: Optional[XGBoostConfig] = None
    lightgbm: Optional[LightGBMConfig] = None
    sklearn: Optional[Dict[str, Any]] = None
    custom_params: Optional[Dict[str, Any]] = None
    
    # Data config
    seasons: List[int] = Field(default_factory=lambda: [2023, 2024, 2025])
    split: SplitConfig = SplitConfig()
    
    # Training config
    early_stopping_rounds: int = Field(50, ge=5, le=500)
    batch_size: Optional[int] = None  # None = all data
    sample_weight: Optional[str] = None  # Column name for weights
    
    # Output config
    calibration: bool = True
    compute_shap: bool = False
    save_predictions: bool = True
    
    @validator('xgboost', 'lightgbm', 'sklearn', 'custom_params')
    def validate_model_config(cls, v, values):
        family = values.get('family')
        if family == ModelFamily.XGBOOST and not v:
            return XGBoostConfig()
        elif family == ModelFamily.LIGHTGBM and not v:
            return LightGBMConfig()
        return v
```

### 2. Result Classes (Rich Return Objects)

```python
# mlb_predict/core/results.py
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Callable
import pandas as pd
import numpy as np
from datetime import datetime

class MetricValue(BaseModel):
    """Single metric with confidence interval."""
    value: float
    std: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    
    def __float__(self):
        return self.value

class Metrics(BaseModel):
    """Complete metrics collection."""
    roc_auc: Optional[MetricValue] = None
    log_loss: Optional[MetricValue] = None
    accuracy: Optional[MetricValue] = None
    precision: Optional[MetricValue] = None
    recall: Optional[MetricValue] = None
    f1: Optional[MetricValue] = None
    calibration_error: Optional[MetricValue] = None
    brier_score: Optional[MetricValue] = None
    
    # Custom metrics
    custom: Dict[str, MetricValue] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to flat dict for serialization."""
        result = {}
        for field, metric in self.__dict__.items():
            if isinstance(metric, MetricValue):
                result[field] = metric.value
        result.update({k: v.value for k, v in self.custom.items()})
        return result

class ValidationCurve(BaseModel):
    """Training/validation curves."""
    metric_name: str
    train_values: List[float]
    val_values: List[float]
    iterations: List[int]
    best_iteration: Optional[int] = None
    
    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame({
            'iteration': self.iterations,
            'train': self.train_values,
            'val': self.val_values
        })
    
    def plot(self):
        """Plot using matplotlib/plotly."""
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot(self.iterations, self.train_values, label='Train')
        ax.plot(self.iterations, self.val_values, label='Validation')
        ax.set_xlabel('Iteration')
        ax.set_ylabel(self.metric_name)
        ax.legend()
        return fig

class FeatureImportance(BaseModel):
    """Feature importance scores."""
    feature_name: str
    importance_score: float
    importance_rank: int
    method: str  # 'gain', 'weight', 'cover', 'shap'
    std: Optional[float] = None
    
class Residuals(BaseModel):
    """Model residuals for analysis."""
    y_true: List[float]
    y_pred: List[float]
    y_prob: List[float]
    residuals: List[float]  # y_true - y_pred
    sample_ids: Optional[List[int]] = None
    
    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame({
            'y_true': self.y_true,
            'y_pred': self.y_pred,
            'y_prob': self.y_prob,
            'residual': self.residuals,
            'sample_id': self.sample_ids
        })
    
    def analyze(self) -> Dict[str, float]:
        """Compute residual statistics."""
        res = np.array(self.residuals)
        return {
            'mean': np.mean(res),
            'std': np.std(res),
            'max_abs': np.max(np.abs(res)),
            'skewness': float(pd.Series(res).skew()),
            'kurtosis': float(pd.Series(res).kurtosis())
        }
    
    def plot_residuals(self):
        """Plot residual analysis."""
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Residual vs fitted
        axes[0, 0].scatter(self.y_prob, self.residuals, alpha=0.5)
        axes[0, 0].axhline(y=0, color='r', linestyle='--')
        axes[0, 0].set_xlabel('Predicted Probability')
        axes[0, 0].set_ylabel('Residual')
        
        # Q-Q plot
        from scipy import stats
        stats.probplot(self.residuals, dist="norm", plot=axes[0, 1])
        
        # Histogram
        axes[1, 0].hist(self.residuals, bins=50, edgecolor='black')
        axes[1, 0].set_xlabel('Residual')
        axes[1, 0].set_ylabel('Frequency')
        
        # Residuals by predicted class
        # ...
        
        return fig

class TrainResult(BaseModel):
    """Complete training result with all artifacts."""
    
    # Identity
    model_id: int
    model_name: str
    experiment_id: Optional[int] = None
    
    # Config
    config: ModelConfig
    git_commit: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Paths
    artifact_path: str
    report_path: Optional[str] = None
    
    # Metrics
    train_metrics: Metrics
    val_metrics: Metrics
    test_metrics: Optional[Metrics] = None
    
    # Detailed results
    validation_curves: List[ValidationCurve] = Field(default_factory=list)
    feature_importance: List[FeatureImportance] = Field(default_factory=list)
    residuals: Optional[Residuals] = None
    
    # Cross-validation results
    cv_results: Optional[List[Metrics]] = None
    cv_folds: Optional[int] = None
    
    # Calibration
    calibration_data: Optional[Dict[str, Any]] = None
    
    # SHAP values (if computed)
    shap_values: Optional[Any] = None  # Stored separately due to size
    
    # Metadata
    training_time_seconds: float
    n_samples_train: int
    n_samples_val: int
    n_samples_test: Optional[int] = None
    n_features: int
    
    # Database integration
    def save_to_registry(self) -> None:
        """Save result to models.model_registry."""
        import psycopg2
        conn = psycopg2.connect("dbname=retrosheet")
        cur = conn.cursor()
        cur.execute("""
            UPDATE models.model_registry
            SET metrics = %s,
                feature_spec = %s
            WHERE model_id = %s
        """, (
            self.test_metrics.to_dict() if self.test_metrics else {},
            {'n_features': self.n_features, 'features': self.config.features.value},
            self.model_id
        ))
        conn.commit()
        conn.close()
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame summary."""
        return pd.DataFrame({
            'model_id': [self.model_id],
            'model_name': [self.model_name],
            'family': [self.config.family.value],
            'target': [self.config.target.value],
            'train_auc': [self.train_metrics.roc_auc.value if self.train_metrics.roc_auc else None],
            'val_auc': [self.val_metrics.roc_auc.value if self.val_metrics.roc_auc else None],
            'test_auc': [self.test_metrics.roc_auc.value if self.test_metrics and self.test_metrics.roc_auc else None],
            'training_time': [self.training_time_seconds],
            'n_features': [self.n_features]
        })
    
    def get_best_features(self, n: int = 20) -> List[FeatureImportance]:
        """Get top N features by importance."""
        return sorted(
            self.feature_importance,
            key=lambda x: x.importance_score,
            reverse=True
        )[:n]
    
    def compare_to(self, other: 'TrainResult') -> Dict[str, Any]:
        """Compare this result to another model."""
        return {
            'model_a': self.model_name,
            'model_b': other.model_name,
            'val_auc_diff': (self.val_metrics.roc_auc.value - 
                           other.val_metrics.roc_auc.value),
            'test_auc_diff': ((self.test_metrics.roc_auc.value if self.test_metrics else 0) - 
                            (other.test_metrics.roc_auc.value if other.test_metrics else 0)),
            'training_time_ratio': self.training_time_seconds / other.training_time_seconds
        }
    
    def generate_report(self, output_path: str) -> str:
        """Generate HTML/Markdown report."""
        # Implementation...
        pass

class PredictResult(BaseModel):
    """Complete prediction result."""
    
    model_id: int
    prediction_id: Optional[int] = None
    
    # Data
    predictions: pd.DataFrame  # Contains: game_pk, pa_id, probs, etc.
    
    # Metadata
    n_predictions: int
    prediction_time_seconds: float
    
    # If ground truth available
    actual_outcomes: Optional[List[str]] = None
    accuracy: Optional[float] = None
    log_loss: Optional[float] = None
    
    def to_sql(self, table_name: str) -> None:
        """Save predictions to SQL table."""
        from sqlalchemy import create_engine
        engine = create_engine("postgresql://localhost:5432/retrosheet")
        self.predictions.to_sql(table_name, engine, if_exists='append', index=False)
    
    def get_calibration(self, n_bins: int = 10):
        """Compute calibration curve."""
        if self.actual_outcomes is None:
            raise ValueError("No actual outcomes provided")
        # Implementation...
        pass
    
    def analyze_by_feature(self, feature_name: str) -> pd.DataFrame:
        """Analyze predictions grouped by feature."""
        return self.predictions.groupby(feature_name).agg({
            'predicted_prob': ['mean', 'std', 'count'],
            'actual_outcome': 'mean'  # If available
        })
```

### 3. Experiment Classes

```python
# mlb_predict/core/experiment.py
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class ExperimentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ExperimentStep(BaseModel):
    """Single step in experiment pipeline."""
    step_name: str
    step_order: int
    status: ExperimentStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    result: Optional[Any] = None
    error_message: Optional[str] = None

class ExperimentResult(BaseModel):
    """Complete experiment with all steps."""
    
    experiment_id: int
    experiment_name: str
    status: ExperimentStatus
    
    config: Dict[str, Any]  # Full experiment config
    
    steps: List[ExperimentStep]
    
    # Aggregate results
    models: List[TrainResult] = Field(default_factory=list)
    predictions: List[PredictResult] = Field(default_factory=list)
    
    # Comparisons
    model_comparison: Optional[pd.DataFrame] = None
    
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_duration_seconds: Optional[float] = None
    
    def get_best_model(self, metric: str = "val_auc") -> TrainResult:
        """Get best model by metric."""
        return max(self.models, key=lambda m: getattr(m.val_metrics, metric).value)
    
    def to_report(self) -> str:
        """Generate experiment report."""
        lines = [
            f"# Experiment: {self.experiment_name}",
            f"Status: {self.status.value}",
            f"Duration: {self.total_duration_seconds:.1f}s" if self.total_duration_seconds else "Duration: N/A",
            "",
            "## Models Trained",
        ]
        for model in self.models:
            lines.append(f"- {model.model_name}: Val AUC = {model.val_metrics.roc_auc.value:.4f}")
        
        lines.append("\n## Steps")
        for step in self.steps:
            lines.append(f"- {step.step_name}: {step.status.value} ({step.duration_seconds:.1f}s)" if step.duration_seconds else f"- {step.step_name}: {step.status.value}")
        
        return "\n".join(lines)
```

---

## Usage Examples

### Example 1: Basic Training with Rich Results

```python
from mlb_predict import ModelTrainer, ModelConfig, ModelFamily, TargetVariable

# Create config
config = ModelConfig(
    family=ModelFamily.XGBOOST,
    target=TargetVariable.SWING_DECISION,
    xgboost={'max_depth': 8, 'n_estimators': 300},
    calibration=True,
    compute_shap=True
)

# Train
result = ModelTrainer.train(config)

# Access everything
print(f"Model ID: {result.model_id}")
print(f"Val AUC: {result.val_metrics.roc_auc.value:.4f}")
print(f"Training time: {result.training_time_seconds:.1f}s")

# Analyze residuals
residual_stats = result.residuals.analyze()
print(f"Residual std: {residual_stats['std']:.4f}")

# Get top features
top_features = result.get_best_features(n=10)
for f in top_features:
    print(f"  {f.feature_name}: {f.importance_score:.4f}")

# Plot validation curve
fig = result.validation_curves[0].plot()
fig.savefig('validation_curve.png')

# Compare to baseline
baseline = ModelTrainer.load_result(model_id=123)  # Previous model
comparison = result.compare_to(baseline)
print(f"AUC improvement: {comparison['val_auc_diff']:+.4f}")

# Save to registry
result.save_to_registry()

# Generate full report
report_path = result.generate_report('reports/my_model.html')
```

### Example 2: Experiment with Multiple Models

```python
from mlb_predict import Experiment, ExperimentConfig

# Define experiment
exp_config = {
    'name': 'model_comparison_swing_decision',
    'models': [
        {'family': 'xgboost', 'target': 'swing_decision'},
        {'family': 'lightgbm', 'target': 'swing_decision'},
        {'family': 'catboost', 'target': 'swing_decision'},
    ],
    'evaluation': {
        'cv_folds': 5,
        'metrics': ['roc_auc', 'log_loss', 'calibration_error']
    }
}

# Run experiment
experiment = Experiment.run(exp_config)

# Get results
print(experiment.to_report())

# Best model
best = experiment.get_best_model(metric='val_auc')
print(f"Best model: {best.model_name} (AUC={best.val_metrics.roc_auc.value:.4f})")

# Full comparison table
comparison_df = experiment.model_comparison
print(comparison_df.to_string())

# All models
for model in experiment.models:
    print(f"{model.model_name}: {model.val_metrics.to_dict()}")
```

### Example 3: Custom Model Plugin

```python
from mlb_predict import PluginModel, ModelConfig, TrainResult
from sklearn.ensemble import RandomForestClassifier
import numpy as np

class RandomForestPlugin(PluginModel):
    """Custom Random Forest implementation."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.model = RandomForestClassifier(
            n_estimators=config.custom_params.get('n_estimators', 100),
            max_depth=config.custom_params.get('max_depth', 10),
            n_jobs=-1
        )
        self.feature_names_ = None
    
    def fit(self, X: np.ndarray, y: np.ndarray, 
            feature_names: List[str] = None) -> 'RandomForestPlugin':
        self.model.fit(X, y)
        self.feature_names_ = feature_names
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]
    
    def get_feature_importance(self) -> List[FeatureImportance]:
        """Return feature importance in standard format."""
        importances = self.model.feature_importances_
        return [
            FeatureImportance(
                feature_name=name,
                importance_score=score,
                importance_rank=i+1,
                method='sklearn_importance'
            )
            for i, (name, score) in enumerate(
                sorted(zip(self.feature_names_, importances), 
                      key=lambda x: x[1], reverse=True)
            )
        ]
    
    def save(self, path: str) -> None:
        import joblib
        joblib.dump(self.model, path)
    
    @classmethod
    def load(cls, path: str) -> 'RandomForestPlugin':
        import joblib
        instance = cls(ModelConfig(family='custom', target='swing_decision'))
        instance.model = joblib.load(path)
        return instance

# Register
from mlb_predict import PluginRegistry

PluginRegistry.register('random_forest', RandomForestPlugin)

# Use in config
config = ModelConfig(
    family='custom',
    target='swing_decision',
    custom_params={'n_estimators': 200, 'max_depth': 15}
)

# Train
result = ModelTrainer.train(config, plugin='random_forest')
# Result is still TrainResult with all standard methods
```

---

## Confirmation: This Will Work

### Why This Architecture is Correct

1. **Uses Existing Infrastructure**
   - Calls `train_models.py`, not reimplements it
   - Uses `models.model_registry`, doesn't replace it
   - Leverages all 220+ existing features

2. **Type Safety**
   - Pydantic validates all configs at runtime
   - Enums prevent invalid values
   - IDE autocomplete works perfectly

3. **Rich Results**
   - Every operation returns full result object
   - Access residuals, curves, features, metadata
   - Chain operations: `result.analyze().plot().save()`

4. **Extensibility**
   - Plugin system for custom models
   - Standard interfaces (fit, predict, save, load)
   - Result classes can be extended

5. **Reproducibility**
   - Configs serialize to YAML/JSON
   - Git commit captured in results
   - Full provenance chain

### Testing Strategy

```python
# Unit tests
pytest tests/test_config.py        # Pydantic validation
pytest tests/test_results.py       # Result classes
pytest tests/test_plugins.py       # Plugin system

# Integration tests  
pytest tests/test_trainer.py       # Calls real scripts
pytest tests/test_experiment.py    # Full experiments

# E2E tests
pytest tests/e2e/test_pipeline.py  # Full pipeline
```

### Next Implementation Steps

1. ✅ **This design document** (DONE)
2. **Config schemas** (1-2 hours)
3. **Result classes** (2-3 hours)
4. **ModelTrainer wrapper** (3-4 hours)
5. **Plugin registry** (2-3 hours)
6. **Experiment runner** (2-3 hours)
7. **CLI interface** (2-3 hours)
8. **Tests** (4-6 hours)

**Total**: ~16-24 hours of focused implementation

---

**Decision Point**: 

This design maximizes utility by:
- ✅ Type-safe configs prevent errors
- ✅ Rich results enable deep analysis
- ✅ Plugin system allows any model
- ✅ Uses existing infrastructure
- ✅ Full reproducibility

**Should I proceed with implementing this Pydantic-based framework?**
