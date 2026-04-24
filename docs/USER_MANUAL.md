# MLB Prediction Warehouse - Complete User Manual

**Version**: 2.0  
**Last Updated**: April 24, 2026  
**Purpose**: Comprehensive guide for using the baseball prediction warehouse

---

## Table of Contents

1. [Quick Start Guide](#quick-start-guide)
2. [System Architecture](#system-architecture)
3. [Data Layers Explained](#data-layers-explained)
4. [Feature Marts Guide](#feature-marts-guide)
5. [Model Training](#model-training)
6. [Inference & Predictions](#inference--predictions)
7. [Analysis Tools](#analysis-tools)
8. [Adding Custom Models](#adding-custom-models)
9. [Experiment Tracking](#experiment-tracking)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start Guide

### Prerequisites

```bash
# 1. Ensure PostgreSQL is running on port 5432
cd /home/cbwinslow/workspace/retrosheet

# 2. Activate Python environment (uv auto-activates via direnv)
direnv allow .

# 3. Verify database connection
uv run python -c "import psycopg2; conn = psycopg2.connect('postgresql://localhost:5432/retrosheet'); print('Connected!')"
```

### 5-Minute Warehouse Rebuild

```bash
# Full rebuild (30-60 minutes)
./scripts/rebuild_warehouse.sh --mode full

# Quick rebuild (skips expensive operations, 5-10 minutes)
./scripts/rebuild_warehouse.sh --mode quick

# Resume from failure
./scripts/rebuild_warehouse.sh --mode resume
```

### First Prediction in 3 Commands

```bash
# 1. Train a model (or use existing from models/model_registry)
uv run python scripts/model_training/train_models.py --target swing_decision

# 2. Make predictions
uv run python scripts/model_inference/predict_plate_appearance.py --model-id <ID>

# 3. View results
psql -d retrosheet -c "SELECT * FROM predictions.swing_decision LIMIT 10;"
```

---

## System Architecture

### Data Flow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  DATA SOURCES (External APIs & Files)                           │
├─────────────────────────────────────────────────────────────────┤
│  • Retrosheet (Historical events, 4.9M records)                 │
│  • MLB Stats API (Statcast, 7.8M pitches)                       │
│  • ESPN API (Live scores, 71K games)                            │
│  • Lahman Database (Player bios, 20K players)                 │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  RAW LAYER (Source-preserved data)                              │
├─────────────────────────────────────────────────────────────────┤
│  raw_retrosheet.events         4.9M play-level events           │
│  raw_retrosheet.games          62K game records                 │
│  raw_mlb.statcast              7.8M pitch-level records         │
│  raw_espn.game_snapshots       71K game JSON snapshots          │
│  lahman.people                 20K player records               │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  BRIDGE LAYER (ID Cross-referencing)                            │
├─────────────────────────────────────────────────────────────────┤
│  bridge.player_xref            128K player ID mappings        │
│  bridge.team_xref              294 team mappings                │
│  bridge.game_xref              59K game mappings                │
│  bridge.park_xref              656 stadium mappings             │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  CORE LAYER (Canonical baseball entities)                         │
├─────────────────────────────────────────────────────────────────┤
│  core.games                    62K games (canonical)            │
│  core.events                   4.9M play-level events           │
│  core.plate_appearances        4.8M PA outcomes                   │
│  core.parks                    656 stadiums with attributes     │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  FEATURE LAYER (ML-Ready Training Data)                           │
├─────────────────────────────────────────────────────────────────┤
│  TRADITIONAL FEATURES (features schema)                         │
│  • prior_season_marts          Batter/pitcher/team rates        │
│  • career_prior                Career statistics                │
│  • matchup_history             Head-to-head stats               │
│  • context                     Park, weather, situation         │
│                                                                 │
│  PITCH-LEVEL FEATURES (features_pitch schema)                   │
│  • base_features               118 Statcast fields              │
│  • engineered_features         220+ derived features            │
│  • feature_registry            Feature metadata & versioning      │
│  • model_training_set          Versioned train/val/test splits  │
│  • locations                   PostGIS-enabled pitch locations  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  MODEL LAYER (Trained Models & Registry)                        │
├─────────────────────────────────────────────────────────────────┤
│  models.model_registry         Versioned model metadata         │
│  models/*.pkl                  Serialized model artifacts       │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  PREDICTION LAYER (Inference & Evaluation)                      │
├─────────────────────────────────────────────────────────────────┤
│  predictions.calibration_reports Model calibration metrics      │
│  predictions.evaluation_reports Performance reports             │
│  predictions.live_scores         Real-time predictions            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Layers Explained

### Layer 1: Raw Data (Source-Preserved)

**Purpose**: Store original data exactly as received from external sources

**Key Tables**:
```sql
-- Retrosheet historical data
SELECT * FROM raw_retrosheet.events LIMIT 5;
SELECT * FROM raw_retrosheet.games LIMIT 5;

-- MLB Stats API / Statcast
SELECT * FROM raw_mlb.statcast WHERE game_year = 2025 LIMIT 5;

-- ESPN API snapshots (JSON preserved)
SELECT game_pk, fetched_at, response_json->>'name' as game_name
FROM raw_espn.game_snapshots
LIMIT 5;
```

**Row Counts**:
| Table | Rows | Time Span |
|-------|------|-----------|
| raw_retrosheet.events | 4,900,000 | 1921-2023 |
| raw_mlb.statcast | 7,797,034 | 2015-2025 |
| raw_espn.game_snapshots | 71,000 | 2023-2025 |

**Important**: Never modify raw tables. Use additive changes only.

---

### Layer 2: Bridge Tables (ID Crosswalk)

**Purpose**: Map IDs between different data sources

**How It Works**:
```sql
-- Find a player across all sources
SELECT 
    player_name,
    retrosheet_id,
    mlbam_id,
    lahman_id,
    espn_id,
    confidence_score
FROM bridge.player_xref
WHERE player_name ILIKE '%trout%'
LIMIT 5;
```

**Confidence Scoring**:
- `confidence_score` = 1.0: Exact match across all sources
- `confidence_score` < 0.5: Fuzzy match, may need manual review

**Available Crosswalks**:
```sql
-- Player IDs
SELECT * FROM bridge.player_xref WHERE player_name = 'Mike Trout';

-- Game IDs
SELECT * FROM bridge.game_xref 
WHERE retrosheet_game_id = 'ANA202304070';

-- Team IDs
SELECT * FROM bridge.team_xref WHERE team_name = 'Los Angeles Angels';
```

---

### Layer 3: Core (Canonical Entities)

**Purpose**: Clean, typed baseball entities that all sources agree on

**Key Tables**:
```sql
-- Canonical games
SELECT 
    game_id,
    game_date,
    home_team_id,
    away_team_id,
    home_score,
    away_score,
    game_type
FROM core.games
WHERE game_date >= '2025-01-01'
ORDER BY game_date DESC
LIMIT 10;

-- Plate appearances (one row per PA with outcome)
SELECT 
    pa.game_id,
    pa.event_id,
    pa.batter_id,
    pa.pitcher_id,
    pa.event_description,
    pa.runs_scored_on_event
FROM core.plate_appearances pa
JOIN core.games g ON pa.game_id = g.game_id
WHERE g.game_date >= '2025-04-01'
LIMIT 10;
```

---

### Layer 4: Feature Marts (ML-Ready)

#### Traditional Features (features schema)

**Purpose**: Season-level and career-level aggregated statistics

**Key Tables**:
```sql
-- Batter prior season performance
SELECT * FROM features.prior_season_batter_rates 
WHERE player_id = 545361 AND season = 2024;

-- Pitcher career statistics
SELECT * FROM features.career_prior_pitcher_rates 
WHERE player_id = 434378;

-- Matchup history (batter vs pitcher)
SELECT * FROM features.matchup_history 
WHERE batter_id = 545361 AND pitcher_id = 434378;
```

#### Pitch-Level Features (features_pitch schema)

**Purpose**: Every pitch with 220+ engineered features

**Main Tables**:

| Table | Rows | Purpose |
|-------|------|---------|
| locations | 7,661,992 | PostGIS-enabled pitch coordinates |
| base_features | 7,661,992 | 118 raw Statcast fields |
| engineered_features | 7,661,992 | 220+ derived features |
| feature_registry | 220 | Feature metadata |
| model_training_set | 7,661,992 | Versioned train/val/test splits |

**Quick Queries**:
```sql
-- Sample pitches with outcomes
SELECT 
    ef.pitch_id,
    ef.game_year,
    ef.pitch_type,
    ef.release_speed,
    ef.outcome_tier1,
    ef.outcome_tier2
FROM features_pitch.engineered_features ef
WHERE ef.is_valid_for_training = TRUE
  AND ef.game_year = 2025
LIMIT 10;

-- Feature registry (what each feature means)
SELECT 
    feature_name,
    feature_category,
    feature_type,
    description
FROM features_pitch.feature_registry
WHERE feature_category = 'physics'
LIMIT 10;

-- Training set (pre-split for model training)
SELECT 
    split_set,  -- 'train', 'val', 'test'
    COUNT(*) as pitch_count
FROM features_pitch.model_training_set
GROUP BY split_set;
```

---

## Feature Marts Guide

### Understanding features_pitch.engineered_features

**220+ Features Organized by Category**:

```sql
-- See all feature categories
SELECT 
    feature_category,
    COUNT(*) as feature_count
FROM features_pitch.feature_registry
GROUP BY feature_category
ORDER BY feature_count DESC;
```

**Categories**:
1. **physics** (30+ features): velocity, spin, movement
2. **location** (20+ features): plate position, zone, strike zone
3. **context** (40+ features): count, inning, base state, score
4. **batter** (50+ features): rolling averages, pitch type performance
5. **pitcher** (50+ features): arsenal metrics, rolling form
6. **matchup** (20+ features): history-specific features
7. **sequence** (10+ features): pitch sequence patterns

### Using Feature Registry

```sql
-- Find features related to velocity
SELECT feature_name, description
FROM features_pitch.feature_registry
WHERE feature_name ILIKE '%velocity%' 
   OR description ILIKE '%velocity%';

-- Find features for a specific model type
SELECT feature_name, feature_category
FROM features_pitch.feature_registry
WHERE is_active = TRUE
  AND feature_category IN ('physics', 'location')
ORDER BY importance_rank NULLS LAST
LIMIT 20;
```

### Model Training Sets

**Pre-built Training Splits**:
```sql
-- Check available training sets
SELECT 
    training_set_version,
    target_variable,
    split_method,
    COUNT(*) FILTER (WHERE split_set = 'train') as train_rows,
    COUNT(*) FILTER (WHERE split_set = 'val') as val_rows,
    COUNT(*) FILTER (WHERE split_set = 'test') as test_rows
FROM features_pitch.model_training_set
GROUP BY training_set_version, target_variable, split_method;
```

---

## Model Training

### Method 1: Direct Script Execution

```bash
# Train binary classification models (swing/take, hit/out, etc.)
uv run python scripts/model_training/train_models.py \
    --target swing_decision \
    --model-type xgboost \
    --seasons 2023 2024 2025

# Train multiclass models (PA outcome distribution)
uv run python scripts/model_training/train_pa_outcome_distribution.py \
    --feature-set advanced \
    --calibrate
```

### Method 2: Using ModelTrainer Wrapper

```python
from mlb_predict import ModelTrainer, load_config

# Load experiment config
config = load_config('configs/my_experiment.yaml')

# Initialize trainer
trainer = ModelTrainer.from_config(config)

# Train using existing infrastructure
result = trainer.train(
    target='swing_decision',
    model_type='xgboost',
    feature_set='physics_location'
)

# Model is automatically registered in models.model_registry
print(f"Model ID: {result['model_id']}")
print(f"AUC: {result['metrics']['roc_auc']}")
```

### Available Targets

```sql
-- See all trained models and their targets
SELECT DISTINCT target_id 
FROM models.model_registry 
WHERE is_active = TRUE;
```

**Common Targets**:
- `swing_decision`: Will batter swing? (binary)
- `contact_made`: Will contact be made? (binary, given swing)
- `hit_outcome`: Hit or out? (binary, given contact)
- `pa_outcome`: Full PA outcome distribution (multiclass)

### Feature Sets

```sql
-- See available feature sets
SELECT DISTINCT feature_tags 
FROM models.model_registry;
```

**Standard Sets**:
- `basic`: 20 core features (velocity, location, count)
- `physics`: 50 physics features (spin, movement, release)
- `context`: 40 game situation features
- `advanced`: 150+ features (rolling averages, matchup history)
- `complete`: All 220+ features

---

## Inference & Predictions

### Historical Predictions (Batch)

```bash
# Predict on historical data
uv run python scripts/model_inference/predict_plate_appearance.py \
    --model-id <MODEL_ID> \
    --seasons 2025 \
    --output-table predictions.swing_decision_2025
```

### Live Predictions (Real-time)

```bash
# Score live games
uv run python scripts/model_inference/predict_live_pa_outcome_distribution.py \
    --game-pk 745555 \
    --model-id <MODEL_ID>

# Or use the unified CLI (when implemented)
mlb-predict live --game 745555 --model <MODEL_ID>
```

### Viewing Predictions

```sql
-- Historical predictions
SELECT 
    game_pk,
    batter_id,
    pitcher_id,
    predicted_prob,
    actual_outcome,
    confidence
FROM predictions.swing_decision
WHERE game_pk = 745555;

-- Live predictions (with win probability)
SELECT 
    p.game_pk,
    p.inning,
    p.batter_id,
    p.pitcher_id,
    p.home_win_probability,
    p.away_win_probability
FROM predictions.live_scores p
WHERE p.game_pk = 745555
ORDER BY p.inning, p.pa_number;
```

---

## Analysis Tools

### Feature Importance Analysis

```bash
# Analyze which features matter most
uv run python scripts/analysis/pca_feature_analysis.py --explained-variance 0.95

# Stepwise feature selection
uv run python scripts/analysis/stepwise_feature_selection.py \
    --target swing_decision \
    --max-features 50

# Feature interaction discovery
uv run python python scripts/analysis/feature_interaction_explorer.py \
    --top-features 20 \
    --sample-size 50000
```

### Model Evaluation

```bash
# Cross-validation
uv run python scripts/analysis/cross_validate_models.py \
    --model-id <MODEL_ID> \
    --folds 5

# Calibration analysis
uv run python scripts/analysis/analyze_pa_outcome_calibration.py \
    --model-id <MODEL_ID>

# Bootstrap confidence intervals
uv run python scripts/analysis/bootstrap_pa_outcome_evaluation.py \
    --model-id <MODEL_ID> \
    --bootstrap-iterations 1000
```

### Pitch Clustering

```bash
# Discover natural pitch groupings
uv run python scripts/analysis/pitch_clustering_analysis.py \
    --n-clusters 8 \
    --method kmeans
```

---

## Adding Custom Models

### Step-by-Step: Add Your Own Model

#### Step 1: Create Model Class (5 lines)

```python
# my_models/custom_xgboost.py
from mlb_predict import PluginModel
import xgboost as xgb

class MyCustomXGBoost(PluginModel):
    """My custom XGBoost configuration."""
    
    def __init__(self, config):
        self.model = xgb.XGBClassifier(
            max_depth=config.get('max_depth', 6),
            n_estimators=config.get('n_estimators', 100),
            learning_rate=config.get('learning_rate', 0.1)
        )
    
    def train(self, X, y):
        self.model.fit(X, y)
    
    def predict(self, X):
        return self.model.predict_proba(X)[:, 1]
    
    def save(self, path):
        self.model.save_model(path)
```

#### Step 2: Register Model

```python
# configs/register_models.py
from mlb_predict import ModelTrainer
from my_models.custom_xgboost import MyCustomXGBoost

trainer = ModelTrainer()
trainer.register_plugin('my_xgboost', MyCustomXGBoost)

# Now use it like any built-in model
result = trainer.train(model_name='my_xgboost')
```

#### Step 3: Train Your Model

```bash
# Via CLI
mlb-predict train --model my_xgboost --target swing_decision

# Or programmatically
python configs/register_models.py
```

#### Step 4: Model Auto-Registers

Your model automatically appears in:
```sql
SELECT * FROM models.model_registry 
WHERE model_name = 'my_xgboost';
```

### Advanced: Custom Feature Engineering

```python
# my_features/custom_features.py
from mlb_predict import FeaturePlugin
import pandas as pd

class VelocitySpinRatio(FeaturePlugin):
    """Custom feature: velocity to spin rate ratio."""
    
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df['velocity_spin_ratio'] = df['release_speed'] / (df['release_spin_rate'] + 1)
        return df
    
    def get_feature_names(self):
        return ['velocity_spin_ratio']
    
    def get_dependencies(self):
        return ['release_speed', 'release_spin_rate']

# Register and use
trainer.register_feature('velocity_spin_ratio', VelocitySpinRatio)
```

---

## Experiment Tracking

### Creating an Experiment

```yaml
# configs/experiments/my_experiment.yaml
experiment:
  name: "xgboost_swing_physics_v1"
  description: "XGBoost model predicting swing decision using physics features"
  tags: ["swing_decision", "xgboost", "physics_features"]

target:
  variable: "swing_decision"
  task: "binary_classification"
  
model:
  type: "xgboost"
  params:
    max_depth: 6
    n_estimators: 200
    learning_rate: 0.05
    
features:
  set: "physics"
  custom_features: ["velocity_spin_ratio"]
  exclude: ["plate_x", "plate_z"]  # Exclude specific features
  
data:
  seasons: [2023, 2024, 2025]
  train_ratio: 0.7
  val_ratio: 0.15
  test_ratio: 0.15
  
validation:
  method: "temporal"
  test_season: 2025
```

### Running Experiments

```bash
# Run single experiment
mlb-predict experiment run configs/experiments/my_experiment.yaml

# Run all experiments in directory
mlb-predict experiment run-batch configs/experiments/

# Compare experiments
mlb-predict experiment compare exp_123 exp_124 exp_125
```

### Viewing Experiment Results

```sql
-- List all experiments
SELECT 
    experiment_name,
    experiment_type,
    status,
    started_at,
    duration_seconds,
    results->>'roc_auc' as auc
FROM framework.experiments
ORDER BY started_at DESC;

-- Find best experiment by metric
SELECT 
    experiment_name,
    (results->>'roc_auc')::numeric as auc
FROM framework.experiments
WHERE experiment_type = 'training'
ORDER BY auc DESC NULLS LAST
LIMIT 5;
```

---

## Troubleshooting

### Common Issues

#### Issue: "Table does not exist"
```
psql: error: relation "features_pitch.engineered_features" does not exist
```

**Solution**: Run warehouse rebuild
```bash
./scripts/rebuild_warehouse.sh --mode full
```

#### Issue: "Model not found in registry"
```
Error: Model ID 12345 not found in models.model_registry
```

**Solution**: List available models
```sql
SELECT model_id, model_name, target_id, is_active 
FROM models.model_registry 
WHERE is_active = TRUE;
```

#### Issue: "Out of memory during training"

**Solution 1**: Reduce sample size
```python
# In your config
sampler:
  method: "random"
  n_samples: 100000  # Instead of full dataset
```

**Solution 2**: Use batch processing
```bash
# Process in batches with resume capability
uv run python scripts/model_training/train_models.py \
    --batch-size 50000 \
    --resume-from-batch 12
```

#### Issue: "Stale data - predictions seem off"

**Solution**: Check data freshness
```sql
-- Check last data load
SELECT 
    table_schema,
    table_name,
    (SELECT MAX(created_at) FROM raw_mlb.statcast) as last_statcast_load
FROM information_schema.tables
WHERE table_schema = 'raw_mlb';

-- Refresh if needed
./scripts/rebuild_warehouse.sh --mode quick --seasons 2025
```

### Performance Optimization

#### Database Queries

```sql
-- Add index for faster filtering
CREATE INDEX CONCURRENTLY idx_engineered_features_year 
ON features_pitch.engineered_features(game_year)
WHERE is_valid_for_training = TRUE;

-- Vacuum for query performance
VACUUM ANALYZE features_pitch.engineered_features;
```

#### Model Training

```python
# Use GPU if available
model:
  type: "xgboost"
  params:
    tree_method: "gpu_hist"  # Use GPU
    
# Or reduce features
features:
  set: "basic"  # Instead of "complete"
```

### Getting Help

1. **Check logs**: `tail -f logs/warehouse_rebuild.log`
2. **Verify database**: `psql -d retrosheet -c "SELECT version();"`
3. **Check disk space**: `df -h /var/lib/postgresql`
4. **Review documentation**: `docs/agents/PROCEDURES.md`

---

## Quick Reference

### Essential SQL Queries

```sql
-- Row counts by layer
SELECT 
    'raw_retrosheet.events' as table_name, COUNT(*) as rows FROM raw_retrosheet.events
UNION ALL
SELECT 'core.games', COUNT(*) FROM core.games
UNION ALL
SELECT 'features_pitch.engineered_features', COUNT(*) FROM features_pitch.engineered_features
UNION ALL
SELECT 'models.model_registry', COUNT(*) FROM models.model_registry;

-- Recent predictions
SELECT * FROM predictions.swing_decision 
ORDER BY created_at DESC 
LIMIT 10;

-- Active models
SELECT 
    model_id,
    target_id,
    model_name,
    metrics->>'roc_auc' as auc,
    created_at
FROM models.model_registry
WHERE is_active = TRUE
ORDER BY target_id, created_at DESC;
```

### Essential Commands

```bash
# Database status
psql -d retrosheet -c "\dt+"

# Warehouse rebuild
./scripts/rebuild_warehouse.sh --mode full

# Train model
uv run python scripts/model_training/train_models.py --target swing_decision

# Make predictions
uv run python scripts/model_inference/predict_plate_appearance.py --model-id <ID>

# Feature analysis
uv run python scripts/analysis/pca_feature_analysis.py
```

---

**End of User Manual**

For more details, see:
- `docs/agents/PROCEDURES.md` - Detailed procedures
- `docs/agents/FILE_INVENTORY.md` - File reference
- `docs/WORKFLOW_VALIDATION_REPORT.md` - Architecture analysis
