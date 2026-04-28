# Models Strategy

Model layer design and implementation patterns for baseball prediction warehouse.

**Author**: Agent cbwinslow/retrosheet  
**Date**: 2026-04-28  
**Status**: Phase 2 - Core Implementation  

---

## Model Types

| Type | Purpose | Target | Algorithm |
|------|---------|--------|-----------|
| `win_probability` | Predict home team win probability | Binary (0/1) | XGBoost classifier |
| `pa_outcome` | Predict plate appearance outcome | Multi-class | RandomForest |
| `next_run` | Predict if run scores this inning | Binary | Logistic Regression |
| `run_total` | Predict total runs in game | Regression | XGBoost regressor |

---

## Model Lifecycle

```
UNTRAINED → TRAINING → TRAINED → EVALUATING → DEPLOYED → ARCHIVED
                ↓           ↓
             FAILED      RETRAINING
```

Status transitions managed via `models.registry` table.

---

## Directory Structure

```
baseball/models/
├── __init__.py           # Exports: BaseModel, ModelType, ModelStatus, etc.
├── base.py              # Abstract base classes and lifecycle enums
├── win_probability_model.py    # XGBoost win probability
├── pa_outcome_model.py         # PA outcome multi-class
├── next_run_model.py           # Next run probability
└── registry.py          # Model registry DB integration

sql/60_models/
├── 6000_models_schema.sql           # Core model tables
├── 6001_models_registry.sql         # Registry + versions
├── 6002_models_training_tables.sql  # Training data marts
├── 6003_models_feature_store.sql    # Feature store tables
└── 6004_models_automation.sql       # Triggers/functions

data/models/
├── win_probability/
│   ├── v1.0.0.joblib
│   ├── v1.0.0_metadata.json
│   └── v1.0.0_metrics.json
└── pa_outcome/
    └── ...
```

---

## Base Classes

### `BaseModel` (Abstract)

All models must implement:
- `train(config: TrainingConfig) -> ModelResult`
- `predict(data: pd.DataFrame) -> pd.DataFrame`
- `evaluate(config: EvaluationConfig) -> EvaluationResult`
- `save(path: Path) -> None`
- `load(path: Path) -> None`

### `SklearnBaseModel` (Mixin)

Provides `save()`/`load()` using `joblib` for scikit-learn models.

---

## Database Schema

### `models.registry`

| Column | Type | Description |
|--------|------|-------------|
| model_id | UUID PK | Unique identifier |
| model_name | VARCHAR(100) | Human-readable name |
| model_type | VARCHAR(50) | win_probability, pa_outcome, etc. |
| version | VARCHAR(20) | Semver (1.0.0) |
| status | VARCHAR(20) | Current lifecycle status |
| features_hash | VARCHAR(64) | Hash of feature set used |
| training_start | TIMESTAMP | When training began |
| training_end | TIMESTAMP | When training completed |
| metrics | JSONB | Performance metrics |
| artifact_path | TEXT | Path to saved model file |
| deployed_at | TIMESTAMP | When promoted to production |

### `models.versions`

Tracks all model versions with diff tracking for feature/pipeline changes.

---

## Feature Store Integration

Models consume features from `features.*` tables:
- `features.win_expectancy` - WE/LI features
- `features.run_expectancy` - RE24 matrix
- `features.matchup` - Batter/pitcher matchups
- `features.rolling_form` - 30-day rolling stats
- `features.bullpen` - Bullpen strength metrics

Feature set hashed and stored in `registry.features_hash`.

---

## Training Pipeline

```bash
# Train specific model
baseball models train --type win_probability --seasons 2020-2024

# Batch train all models
baseball models train --all
```

Training workflow:
1. Load training data from `features.*` tables
2. Split train/test (80/20)
3. Train with hyperparameters from config
4. Evaluate and compute metrics
5. Save artifact to `data/models/`
6. Register in `models.registry`

---

## Model Registry CLI

```bash
# List models
baseball models list

# Get model info
baseball models info --model-id <uuid>

# Download artifact
baseball models download --model-id <uuid> --output ./model.joblib

# Archive old version
baseball models archive --model-id <uuid>

# Compare versions
baseball models compare --v1 <uuid1> --v2 <uuid2>

# Export metadata
baseball models export --model-id <uuid> --format json
```

---

## Inference

```python
from baseball.models import WinProbabilityModel

model = WinProbabilityModel()
model.load(path)

# Single prediction
game_state = {
    'inning': 5,
    'outs': 2,
    'score_diff': -1,
    'runners': [1, 0, 1],  # 1B, 2B, 3B
}
prob = model.predict_single(game_state)

# Batch prediction
df = pd.DataFrame([...])
results = model.predict(df)
```

---

## Monitoring

### Metrics Tracked
- Accuracy / AUC-ROC / LogLoss
- Calibration error
- Prediction drift over time
- Feature importance stability

### Alerts
- Performance degradation (>5% accuracy drop)
- Feature drift (distribution changes)
- Training pipeline failures

---

## Best Practices

1. **Version everything**: Every training run gets a unique version
2. **Hash features**: Track exactly which features were used
3. **Immutable artifacts**: Never modify saved models
4. **A/B testing**: Deploy new models alongside old for comparison
5. **Rollback ready**: Keep last 3 versions deployed and ready

---

## Future Work

- [ ] Automated retraining triggers
- [ ] Model explainability (SHAP values)
- [ ] Online learning for live games
- [ ] Ensemble models
- [ ] Hyperparameter optimization
