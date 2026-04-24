# Current State Review & Integration Plan

**Date**: April 24, 2026  
**Purpose**: Comprehensive inventory of what exists and plan for integration

---

## Executive Summary

The warehouse is **functionally complete** with working data pipelines, feature engineering, model training, and inference. What's missing is a **unified interface** that makes it easy for researchers to:
1. Discover available features and models
2. Plug in custom models that integrate with existing infrastructure
3. Run experiments with consistent configuration
4. Reproduce results across the full stack

**Status**: ~85% Complete, ~15% Integration Layer Needed

---

## Layer 1: Data Sources (✅ COMPLETE)

### What's Built
| Source | Schema | Rows | Status |
|--------|--------|------|--------|
| Retrosheet Historical | `raw_retrosheet` | 62,598 games, 4.9M events | ✅ |
| MLB Stats API | `raw_mlb` | 7.8M Statcast pitches, schedules, live feeds | ✅ |
| ESPN API | `raw_espn` | 71K game snapshots, 1.3M plays | ✅ |
| Lahman/Baseball Databank | `lahman` | 110K batting, 49K pitching records | ✅ |
| Baseball Reference | `raw_external` | Park factors, rosters | ✅ |
| Fangraphs | `raw_external` | Player stats | ✅ |

### Key Tables
- `raw_retrosheet.events`: 4.9M play-level events
- `raw_mlb.statcast`: 7,797,034 pitches (2015-2025, 118 fields)
- `raw_espn.game_snapshots`: 71,739 games
- `lahman.people`: 20,673 player bios

### Scripts
- `scripts/warehouse.py` - Main CLI for Retrosheet fetch/extract/load
- `scripts/download_mlb_bulk.py` - MLB historical backfill
- `scripts/fetch_espn_mlb.py` - ESPN data with deduplication
- `scripts/pitch_data/load_all_statcast_full.py` - Complete Statcast loader

---

## Layer 2: Bridge Tables (✅ COMPLETE)

### What's Built
| Table | Rows | Purpose |
|-------|------|---------|
| `bridge.player_xref` | 128,925 | Player ID crosswalk (Retrosheet ↔ MLB ↔ ESPN ↔ BBRef) |
| `bridge.team_xref` | 294 | Team ID mappings with season awareness |
| `bridge.game_xref` | 59,191 | Game ID matching |
| `bridge.park_xref` | 656 | Park/stadium IDs |
| `bridge.coach_xref` | 1,903 | Coach ID mappings |
| `bridge.umpire_xref` | 2,368 | Umpire ID mappings |

### Confidence Scoring
- All bridge tables have `confidence_score` and `confidence_source`
- Monitoring views for data quality
- SQL procedures for population with name resolution

### Scripts
- `sql/bridge/999_master_bridge_population_procedure.sql` - Master orchestrator
- `scripts/populate_bridge_tables.py` - Python wrapper

---

## Layer 3: Core Schema (✅ COMPLETE)

### What's Built
| Table | Rows | Purpose |
|-------|------|---------|
| `core.games` | 62,598 | Canonical game records |
| `core.events` | 4.9M | Play-level events |
| `core.plate_appearances` | 4.8M | PA outcomes with targets |
| `core.parks` | 656 | Park metadata |
| `core.teams` | 292 | Team history |

### Key Features
- Typed schemas with constraints
- Game state tracking (bases, outs, score)
- Handedness, matchup data
- Temporal fields (season, era)

### Scripts
- `sql/core/010_core_games_events.sql` - Foundation schema
- `sql/core/020_plate_appearances.sql` - PA table with targets

---

## Layer 4: Feature Marts (✅ COMPLETE)

### Traditional Feature Marts
| Mart | Schema | Features | Status |
|------|--------|----------|--------|
| Prior Season | `features` | Batter/pitcher/team prior rates | ✅ |
| Career Prior | `features` | Career-level statistics | ✅ |
| Matchup | `features` | Batter-pitcher history | ✅ |
| Context | `features` | Park, game situation | ✅ |
| Rolling | `features` | 30-day team form | ✅ |
| Count State | `features` | Ball-strike specific rates | ✅ |

### Pitch-Level Feature Mart (Epic #78 - ✅ COMPLETE)
| Table | Rows | Features |
|-------|------|----------|
| `features_pitch.base_features` | 7,661,992 | 118 Statcast fields |
| `features_pitch.engineered_features` | 7,661,992 | 220+ derived features |
| `features_pitch.feature_registry` | 220+ | Feature metadata catalog |
| `features_pitch.model_training_set` | - | Versioned training data |
| `features_pitch.player_context` | - | Rolling player stats |

### Feature Categories
- **Pitch Physics**: Velocity, spin, movement, location
- **Game Context**: Inning, score, bases, outs, count
- **Player Context**: Rolling averages, career stats, matchup history
- **Environmental**: Park factors, weather, attendance
- **Sequential**: Pitch sequences, TTOP (times through order)
- **Outcome Labels**: Tier 1 (S/B/X), Tier 2 (12 classes)

### Scripts
- `sql/features/003_pitch_flexible_mart.sql` - Primary schema
- `sql/features/005_build_engineered_features.sql` - Feature population
- `sql/features/012_context_features_schema.sql` - Context features
- `sql/features/015_final_features_schema.sql` - Final 50+ features

---

## Layer 5: Model Training (✅ COMPLETE)

### Training Scripts
| Script | Target Type | Models | Status |
|--------|-------------|--------|--------|
| `train_models.py` | Binary | Logistic Regression, HistGradientBoosting | ✅ |
| `train_pa_outcome_distribution.py` | Multiclass | XGBoost, LightGBM, CatBoost, Logistic | ✅ |
| `train_win_probability_model.py` | Binary | Game-level WP | ✅ |
| `train_tier1_xgboost.py` | Binary (Pitch) | Tier-1 outcomes (S/B/X) | 🔄 In Progress |

### Available Targets
**Binary (game/PA level):**
- `game_home_win` - Game outcome
- `pa_batter_hit`, `pa_batter_walk`, `pa_batter_strikeout`, `pa_batter_home_run`, `pa_batter_reach_base`

**Multiclass (PA outcome distribution):**
- `pa_outcome_distribution` - 12 outcome classes

**Pitch-level (in progress):**
- `pitch_tier1_outcome` - {S, B, X}
- `pitch_tier2_outcome` - {strike, ball, foul, single, double, triple, hr, out, ...}

### Model Registry
| Table | Purpose |
|-------|---------|
| `models.model_registry` | Versioned models with metrics, artifact paths, activation |
| `models.active_model_versions` | View of currently active models |

### Model Features
- Feature specs stored in registry
- Train/validation metrics
- Automatic activation on training completion
- Artifact versioning with timestamps

---

## Layer 6: Model Inference (✅ COMPLETE)

### Prediction Scripts
| Script | Use Case | Status |
|--------|----------|--------|
| `predict_plate_appearance.py` | Historical PA binary targets | ✅ |
| `predict_pa_outcome_distribution.py` | Historical PA multiclass | ✅ |
| `predict_live_pa_outcome_distribution.py` | Live PA scoring | ✅ |
| `train_live_models.py` | Live-oriented training | ✅ |

### Inference Features
- Feature parity between historical and live views
- Calibration artifact support
- Batch prediction service candidate
- Fast prediction caching

---

## Layer 7: Evaluation & Calibration (✅ COMPLETE)

### Scripts
| Script | Purpose |
|--------|---------|
| `analyze_pa_models.py` | PA model comparison |
| `analyze_pa_outcome_calibration.py` | Calibration diagnostics |
| `calibrate_pa_outcome_model.py` | Isotonic calibration experiments |
| `bootstrap_pa_outcome_evaluation.py` | Bootstrap uncertainty |
| `persist_pa_outcome_reports.py` | Persist evaluation artifacts |
| `register_pa_outcome_calibration.py` | Register calibration artifacts |
| `cross_validate_models.py` | Cross-validation |
| `sweep_hyperparameters.py` | Grid search |
| `sweep_pa_outcome_temporal.py` | Temporal policy sweeps |
| `promote_best_models.py` | Auto-promote based on thresholds |

### Reports Tables
- `predictions.calibration_reports`
- `predictions.evaluation_reports`
- `predictions.bootstrap_summaries`

---

## Layer 8: Orchestration & Reproducibility (✅ COMPLETE)

### Warehouse Rebuild
| Component | Purpose |
|-----------|---------|
| `warehouse.rebuild_runs` | Run tracking |
| `warehouse.rebuild_log` | Phase-level logging |
| `warehouse.rebuild()` | Main orchestration procedure |
| `scripts/rebuild_warehouse.sh` | CLI wrapper |

### Testing
| Script | Purpose |
|--------|---------|
| `scripts/test/e2e_test_runner.sh` | Full E2E validation |
| `scripts/test/validate_sql_files.sh` | SQL header validation |
| `scripts/test/verify_rebuild.sh` | Rebuild verification |

### Backup
| Script | Purpose |
|--------|---------|
| `scripts/backup_procedures.sh` | Database object backup |
| `scripts/backup_sql_files.sh` | SQL file backup |

---

## What's Missing: Integration Layer (🔄 NEEDED)

### 1. Unified Configuration System
**Current State**: Hardcoded feature lists, scattered config  
**What's Needed**: YAML-based config with inheritance, validation

**Example**:
```yaml
# configs/experiment.yaml
experiment:
  name: pa_outcome_v1
  description: PA outcome with advanced features
  
data:
  target: pa_outcome_distribution
  feature_set: advanced_count
  seasons: [2020, 2021, 2022, 2023, 2024]
  train_through: 2023
  sample_rate: 1.0

model:
  family: xgboost
  params:
    n_estimators: 250
    learning_rate: 0.05
    max_depth: 6
  
evaluation:
  metrics: [log_loss, brier_score, top_3_accuracy]
  calibration: isotonic
  bootstrap: true
```

### 2. Model Plugin System
**Current State**: Scripts have hardcoded model definitions  
**What's Needed**: Plugin registry that outputs to existing `models.model_registry`

**Example**:
```python
# my_custom_model.py
from mlb_predict import PluginModel

class MyXGBoost(PluginModel):
    def fit(self, X, y, **kwargs):
        self.model = xgb.XGBClassifier(**self.config['params'])
        self.model.fit(X, y)
    
    def predict_proba(self, X):
        return self.model.predict_proba(X)
    
    def save(self, path):
        joblib.dump(self.model, path)

# Register and use
trainer = ModelTrainer.from_config('config.yaml')
trainer.register_plugin('my_xgboost', MyXGBoost)
trainer.train(model_type='my_xgboost')
# Automatically registers in models.model_registry
```

### 3. Unified CLI
**Current State**: Multiple scripts with different arguments  
**What's Needed**: Single CLI that dispatches to existing scripts

**Example**:
```bash
# Discover
mlb-predict list-targets
mlb-predict list-feature-sets
mlb-predict list-active-models

# Train
mlb-predict train --config configs/my_experiment.yaml
mlb-predict train --target pa_batter_hit --feature-set advanced

# Evaluate
mlb-predict evaluate --model-id 123
mlb-predict calibrate --model-id 123
mlb-predict promote --model-id 123 --threshold 0.65

# Predict
mlb-predict predict --game-id MLB20240001 --pa-id 1
```

### 4. Experiment Tracking
**Current State**: Manual logging, scattered metadata  
**What's Needed**: Centralized experiment tracking that wraps existing scripts

**Example**:
```python
from mlb_predict import Experiment

exp = Experiment.from_config('configs/my_experiment.yaml')
exp.start()

try:
    result = exp.run_training()
    exp.log_metrics(result['metrics'])
    exp.log_artifact(result['artifact_path'])
    exp.complete(status='success')
except Exception as e:
    exp.complete(status='failed', error=str(e))
```

### 5. Feature Discovery Interface
**Current State**: SQL scripts for PCA, correlation, stepwise selection  
**What's Needed**: Unified feature selection that writes to `features_pitch.feature_registry`

**Example**:
```bash
# Run feature discovery
mlb-predict discover-features \
  --target pa_outcome_distribution \
  --method stepwise \
  --max-features 50 \
  --output configs/selected_features.yaml

# Then use in training
mlb-predict train \
  --config configs/my_experiment.yaml \
  --features configs/selected_features.yaml
```

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    UNIFIED CLI (mlb-predict)               │
├─────────────────────────────────────────────────────────────┤
│  Commands: train, evaluate, predict, discover, promote     │
├─────────────────────────────────────────────────────────────┤
│              CONFIG SYSTEM (YAML + Pydantic)               │
├─────────────────────────────────────────────────────────────┤
│  Experiment Tracking │ Plugin Registry │ Feature Selector   │
├─────────────────────────────────────────────────────────────┤
│           WRAPPERS (call existing scripts)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ train_models│  │train_pa_out │  │ pitch_models│         │
│  │    .py      │  │ come_dist   │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│              EXISTING INFRASTRUCTURE (unchanged)             │
│  Data → Bridge → Core → Features → Models → Predictions    │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Priority

### Phase 1: Configuration System (2-3 days)
- [ ] Pydantic models for config validation
- [ ] YAML schema for experiments
- [ ] Config inheritance (base → project → experiment)
- [ ] Integration with existing scripts

### Phase 2: Plugin Wrapper (2-3 days)
- [ ] `ModelTrainer` class that wraps existing scripts
- [ ] Plugin registration system
- [ ] Output to existing `models.model_registry`
- [ ] Example plugin (custom XGBoost)

### Phase 3: Unified CLI (2-3 days)
- [ ] Click-based CLI structure
- [ ] `train`, `evaluate`, `predict`, `list` commands
- [ ] Discovery commands for targets/features/models
- [ ] Call existing scripts with config

### Phase 4: Experiment Tracking (1-2 days)
- [ ] `Experiment` class that logs to `framework.experiments`
- [ ] Integration with `warehouse.rebuild_log`
- [ ] Artifact tracking
- [ ] Reproducibility info (git commit, data hash)

### Phase 5: Feature Discovery Integration (2-3 days)
- [ ] Wrap existing PCA/stepwise scripts
- [ ] Output to `features_pitch.feature_registry`
- [ ] Config-based feature selection
- [ ] Feature importance tracking

---

## Files to Create

### Core Framework
| File | Purpose |
|------|---------|
| `mlb_predict/__init__.py` | Package init |
| `mlb_predict/core/trainer.py` | ModelTrainer wrapper |
| `mlb_predict/core/experiment.py` | Experiment tracking |
| `mlb_predict/core/plugin.py` | Plugin base class |
| `mlb_predict/config/schema.py` | Pydantic config models |
| `mlb_predict/config/loader.py` | YAML loading |
| `mlb_predict/data/feature_loader.py` | Feature discovery |
| `mlb_predict/cli/main.py` | Click CLI |
| `scripts/mlb-predict` | CLI entry point |

### SQL Schema
| File | Purpose |
|------|---------|
| `sql/framework/001_framework_schema.sql` | Already created - framework logging tables |

### Examples
| File | Purpose |
|------|---------|
| `examples/configs/basic_experiment.yaml` | Example config |
| `examples/plugins/custom_xgboost.py` | Example plugin |
| `examples/README.md` | Usage examples |

---

## Files to NOT Create (Use Existing)

❌ Don't create parallel:  
- Feature marts (use `sql/features/`)
- Training scripts (use `scripts/model_training/`)
- Model registry (use `models.model_registry`)
- Data loading (use existing loaders)
- Database schema (use existing schemas)

✅ Do wrap and integrate with existing infrastructure.

---

## Success Criteria

1. **Researcher can add custom model in 5 lines of code**
2. **All custom models register in existing `models.model_registry`**
3. **Config-driven experiments reproducible via single command**
4. **Existing scripts continue to work unchanged**
5. **E2E tests pass with new framework layer**

---

## Next Steps

1. **Review this document** - Confirm architecture approach
2. **Create Phase 1** - Configuration system
3. **Test integration** - Ensure existing scripts still work
4. **Iterate** - Add phases incrementally
5. **Document** - Update FILE_INVENTORY.md, AGENTS.md

---

**Key Principle**: Build a thin integration layer that makes existing infrastructure more accessible, not a parallel system that competes with it.
