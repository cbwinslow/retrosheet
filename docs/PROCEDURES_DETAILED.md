# Detailed Procedures Guide

**Purpose**: Step-by-step procedures for all warehouse operations  
**Prerequisites**: PostgreSQL running, database `retrosheet` exists, Python environment active

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Data Ingestion Procedures](#data-ingestion-procedures)
3. [Warehouse Rebuild Procedures](#warehouse-rebuild-procedures)
4. [Feature Engineering Procedures](#feature-engineering-procedures)
5. [Model Training Procedures](#model-training-procedures)
6. [Inference Procedures](#inference-procedures)
7. [Analysis Procedures](#analysis-procedures)
8. [Maintenance Procedures](#maintenance-procedures)
9. [Troubleshooting Procedures](#troubleshooting-procedures)

---

## Getting Started

### First-Time Setup

#### Step 1: Environment Setup

```bash
# Navigate to project
cd /home/cbwinslow/workspace/retrosheet

# Allow direnv (auto-activates Python environment)
direnv allow .

# Verify environment
which python  # Should show .venv path
python --version  # Should be 3.10.x

# Install dependencies
uv sync --all-extras
```

#### Step 2: Database Connection Test

```bash
# Test connection
psql -d retrosheet -c "SELECT version();"

# Verify schemas exist
psql -d retrosheet -c "\dn"

# Expected output includes:
# - core
# - bridge
# - features
# - features_pitch
# - models
# - raw_retrosheet
# - raw_mlb
# - raw_espn
# - warehouse
```

#### Step 3: Verify Data Exists

```sql
-- Check core tables have data
SELECT 'games' as table_name, COUNT(*) as rows FROM core.games
UNION ALL SELECT 'events', COUNT(*) FROM core.events
UNION ALL SELECT 'plate_appearances', COUNT(*) FROM core.plate_appearances;

-- Expected: 62K games, 4.9M events, 4.8M PAs
```

---

## Data Ingestion Procedures

### Procedure 1: ESPN Data Ingestion

**Purpose**: Fetch live scores and schedules from ESPN API

**Prerequisites**: ESPN API access (no key required for basic endpoints)

**Step-by-Step**:

```bash
# Step 1: Fetch today's games
uv run python scripts/fetch_espn_mlb.py --date today

# Step 2: Fetch specific date range
uv run python scripts/fetch_espn_mlb.py --start-date 2025-04-01 --end-date 2025-04-30

# Step 3: Verify ingestion
psql -d retrosheet -c "
SELECT 
    DATE(fetched_at) as date,
    COUNT(*) as games_fetched
FROM raw_espn.game_snapshots
GROUP BY DATE(fetched_at)
ORDER BY date DESC
LIMIT 5;
"
```

**What It Does**:
1. Calls ESPN API endpoints
2. Stores JSON responses in `raw_espn.game_snapshots`
3. Computes checksum for deduplication
4. Logs request metadata

**Validation**:
```sql
-- Check for recent data
SELECT MAX(fetched_at) as latest_fetch
FROM raw_espn.game_snapshots;

-- Should be within last 24 hours if running regularly
```

---

### Procedure 2: MLB Stats API Data Ingestion

**Purpose**: Fetch Statcast pitch-level data and live game feeds

**Step-by-Step**:

```bash
# Step 1: Fetch schedule for date range
uv run python scripts/fetch_mlb_schedule.py --start-date 2025-04-01 --end-date 2025-04-30

# Step 2: Ingest live games from schedule
uv run python scripts/ingest_live_games.py --schedule

# Step 3: Fetch Statcast data for specific season
uv run python scripts/data_ingestion/download_baseball_savant.py --season 2025

# Step 4: Load into database
uv run python scripts/pitch_data/load_all_statcast_full.py --seasons 2025
```

**Verification**:
```sql
-- Check Statcast data
SELECT 
    game_year,
    COUNT(*) as pitch_count
FROM raw_mlb.statcast
GROUP BY game_year
ORDER BY game_year DESC;

-- Expected: 2015-2025 with 500K-1M pitches per year
```

---

### Procedure 3: Retrosheet Historical Data

**Purpose**: Load historical play-by-play data from Retrosheet

**Step-by-Step**:

```bash
# Step 1: Download Retrosheet event files (one-time or annual)
./scripts/download_retrosheet.sh 2023 2024 2025

# Step 2: Parse with Chadwick tools
./scripts/parse_retrosheet_events.sh

# Step 3: Load to database
psql -d retrosheet -f sql/core/010_core_games_events.sql
```

**Validation**:
```sql
-- Check data coverage by year
SELECT 
    EXTRACT(YEAR FROM game_date) as year,
    COUNT(*) as games
FROM core.games
GROUP BY year
ORDER BY year DESC
LIMIT 10;
```

---

## Warehouse Rebuild Procedures

### Procedure 4: Full Warehouse Rebuild

**Purpose**: Complete rebuild of all warehouse layers from source data

**When to Use**:
- First-time setup
- After schema changes
- Data corruption recovery
- Annual refresh

**Time Required**: 30-90 minutes depending on data volume

**Step-by-Step**:

```bash
# Pre-rebuild checks
psql -d retrosheet -c "SELECT COUNT(*) FROM core.games;"  # Baseline count

# Run full rebuild
./scripts/rebuild_warehouse.sh --mode full

# Expected phases (with row counts):
# [Phase 1] Raw load: 4.9M events loaded
# [Phase 2] Core build: 62K games, 4.8M PAs
# [Phase 3] Bridge sync: 128K player mappings
# [Phase 4] Feature build: 7.6M pitches with 220 features
# [Phase 5] Model prep: Training sets created
```

**Monitoring**:
```sql
-- Watch rebuild progress
SELECT 
    phase,
    status,
    rows_affected,
    execution_time_ms / 1000.0 as seconds
FROM warehouse.rebuild_log
WHERE run_id = (SELECT MAX(run_id) FROM warehouse.rebuild_runs)
ORDER BY phase_order;
```

**Validation**:
```sql
-- Post-rebuild row counts
SELECT 'core.games' as table_name, COUNT(*) FROM core.games
UNION ALL SELECT 'core.plate_appearances', COUNT(*) FROM core.plate_appearances
UNION ALL SELECT 'features_pitch.engineered_features', COUNT(*) FROM features_pitch.engineered_features
UNION ALL SELECT 'bridge.player_xref', COUNT(*) FROM bridge.player_xref;

-- All should match expected counts
```

---

### Procedure 5: Quick Rebuild (Skip Expensive Operations)

**Purpose**: Fast rebuild for development/testing

**When to Use**:
- Testing schema changes
- Development iterations
- CI/CD pipelines

**Time Required**: 5-15 minutes

```bash
./scripts/rebuild_warehouse.sh --mode quick
```

**What It Skips**:
- Full Statcast reload (uses existing data)
- Feature engineering (refreshes only)
- Model training set rebuild (incremental)

---

### Procedure 6: Resume From Failure

**Purpose**: Continue rebuild after interruption

**When to Use**:
- Network failure during download
- Out of memory error
- Manual interruption

```bash
# Automatically resumes from last successful phase
./scripts/rebuild_warehouse.sh --mode resume
```

**How It Works**:
1. Queries `warehouse.rebuild_log` for last completed phase
2. Skips already-completed phases
3. Continues from failure point

**Manual Resume (if automatic fails)**:
```sql
-- Check failed phase
SELECT phase, error_message
FROM warehouse.rebuild_log
WHERE run_id = (SELECT MAX(run_id) FROM warehouse.rebuild_runs)
  AND status = 'failed';

-- Re-run specific phase manually
psql -d retrosheet -f sql/core/020_specific_phase.sql
```

---

## Feature Engineering Procedures

### Procedure 7: Build Pitch-Level Features

**Purpose**: Create 220+ engineered features from raw Statcast data

**Step-by-Step**:

```bash
# Step 1: Ensure base features exist
psql -d retrosheet -c "SELECT COUNT(*) FROM features_pitch.base_features;"

# Step 2: Build engineered features
psql -d retrosheet -f sql/features/001_pitch_features.sql

# Step 3: Verify feature registry
psql -d retrosheet -c "SELECT COUNT(*) FROM features_pitch.feature_registry;"

# Step 4: Update feature registry metadata
psql -d retrosheet -f sql/features/002_feature_registry_update.sql
```

**Validation**:
```sql
-- Check feature coverage
SELECT 
    feature_category,
    COUNT(*) as feature_count
FROM features_pitch.feature_registry
GROUP BY feature_category
ORDER BY feature_count DESC;

-- Expected categories:
-- physics: ~30 features
-- location: ~20 features
-- context: ~40 features
-- batter: ~50 features
-- pitcher: ~50 features
```

---

### Procedure 8: Feature Importance Analysis

**Purpose**: Identify most predictive features

**Step-by-Step**:

```bash
# Step 1: Run PCA analysis
uv run python scripts/analysis/pca_feature_analysis.py \
    --explained-variance 0.95 \
    --output-dir models/pca_analysis

# Step 2: Run stepwise feature selection
uv run python scripts/analysis/stepwise_feature_selection.py \
    --target swing_decision \
    --max-features 50 \
    --output-file models/selected_features.json

# Step 3: Store results in database
psql -d retrosheet -f sql/analysis/001_feature_importance.sql
```

**Viewing Results**:
```sql
-- Top features by importance
SELECT 
    feature_name,
    importance_score,
    analysis_method
FROM analysis.feature_importance
WHERE analysis_method = 'xgboost_gain'
ORDER BY importance_score DESC
LIMIT 20;

-- Top features by target
SELECT * FROM analysis.top_features_by_target
WHERE target_id = 'swing_decision'
LIMIT 20;
```

---

### Procedure 9: Feature Interaction Discovery

**Purpose**: Find feature pairs that work better together

**Step-by-Step**:

```bash
# Step 1: Run interaction explorer
uv run python scripts/analysis/feature_interaction_explorer.py \
    --top-features 20 \
    --sample-size 50000 \
    --output-dir models/interaction_analysis

# Step 2: Review results
cat models/interaction_analysis/interactions_*.json | jq '.top_interactions[:5]'
```

**What It Finds**:
- Feature pairs with synergy (interaction > individual)
- Category groupings (velocity+movement, location+count, etc.)
- XGBoost improvement from adding interactions

---

## Model Training Procedures

### Procedure 10: Train Binary Classification Model

**Purpose**: Train models for swing/take, hit/out predictions

**Step-by-Step**:

```bash
# Step 1: Train swing decision model
uv run python scripts/model_training/train_models.py \
    --target swing_decision \
    --model-type xgboost \
    --seasons 2023 2024 2025 \
    --test-season 2025

# Step 2: Note the model_id from output
# Model saved as models/swing_decision_xgboost_YYYYMMDD_HHMMSS.pkl

# Step 3: Verify in registry
psql -d retrosheet -c "
SELECT model_id, model_name, target_id, created_at
FROM models.model_registry
WHERE target_id = 'swing_decision'
ORDER BY created_at DESC
LIMIT 1;
"
```

**What Happens**:
1. Loads training data from `features_pitch.model_training_set`
2. Splits train/val/test by season (2025 = test)
3. Trains XGBoost with hyperparameters
4. Evaluates with ROC-AUC, log loss, calibration
5. Saves model artifact to `models/`
6. Registers in `models.model_registry`

**Validation**:
```sql
-- Check model metrics
SELECT 
    model_id,
    target_id,
    metrics->>'roc_auc' as roc_auc,
    metrics->>'log_loss' as log_loss,
    metrics->>'calibration_error' as calibration
FROM models.model_registry
WHERE target_id = 'swing_decision'
ORDER BY created_at DESC
LIMIT 1;

-- Expected: ROC-AUC > 0.70 for swing decision
```

---

### Procedure 11: Train Multiclass PA Outcome Model

**Purpose**: Train model predicting full PA outcome distribution

**Step-by-Step**:

```bash
# Step 1: Train multiclass model
uv run python scripts/model_training/train_pa_outcome_distribution.py \
    --feature-set advanced \
    --model-type xgboost \
    --calibrate \
    --seasons 2023 2024 2025

# Step 2: Model outputs probability distribution:
# P(single), P(double), P(triple), P(homer), P(walk), P(strikeout), etc.
```

**Feature Sets**:
- `basic`: 20 features (fast training, lower accuracy)
- `advanced`: 150 features (balanced)
- `count`: Adds count-state features
- `complete`: 220+ features (slowest, highest accuracy)

---

### Procedure 12: Cross-Validation

**Purpose**: Robust model evaluation with confidence intervals

**Step-by-Step**:

```bash
# Step 1: Run cross-validation
uv run python scripts/model_training/cross_validate_models.py \
    --model-id <MODEL_ID> \
    --folds 5 \
    --seasons 2023 2024 2025

# Step 2: View results
psql -d retrosheet -c "
SELECT 
    fold_number,
    train_auc,
    val_auc,
    test_auc
FROM predictions.cross_validation_results
WHERE model_id = <MODEL_ID>
ORDER BY fold_number;
"
```

---

## Inference Procedures

### Procedure 13: Historical Batch Prediction

**Purpose**: Score historical games with trained model

**Step-by-Step**:

```bash
# Step 1: Find active model
psql -d retrosheet -c "
SELECT model_id, model_name, target_id
FROM models.model_registry
WHERE is_active = TRUE AND target_id = 'swing_decision'
ORDER BY created_at DESC
LIMIT 1;
"

# Step 2: Run predictions
uv run python scripts/model_inference/predict_plate_appearance.py \
    --model-id <MODEL_ID> \
    --seasons 2025 \
    --output-table predictions.swing_decision_2025

# Step 3: Verify predictions
psql -d retrosheet -c "
SELECT 
    game_pk,
    COUNT(*) as pa_count,
    AVG(predicted_prob) as avg_prob
FROM predictions.swing_decision_2025
GROUP BY game_pk
LIMIT 5;
"
```

---

### Procedure 14: Live Game Prediction

**Purpose**: Real-time predictions for in-progress games

**Step-by-Step**:

```bash
# Step 1: Ingest live game data
uv run python scripts/ingest_live_games.py --game-pk 745555

# Step 2: Run live prediction
uv run python scripts/model_inference/predict_live_pa_outcome_distribution.py \
    --game-pk 745555 \
    --model-id <MODEL_ID>

# Step 3: View live predictions
psql -d retrosheet -c "
SELECT 
    inning,
    batter_id,
    pitcher_id,
    predicted_outcome,
    win_probability_added
FROM predictions.live_scores
WHERE game_pk = 745555
ORDER BY inning, pa_number;
"
```

---

### Procedure 15: Calibration Check

**Purpose**: Verify model predictions match actual outcomes

**Step-by-Step**:

```bash
# Step 1: Analyze calibration
uv run python scripts/analysis/analyze_pa_outcome_calibration.py \
    --model-id <MODEL_ID>

# Step 2: View calibration report
psql -d retrosheet -c "
SELECT 
    bin_number,
    predicted_prob_low,
    predicted_prob_high,
    actual_frequency,
    calibration_error
FROM predictions.calibration_reports
WHERE model_id = <MODEL_ID>
ORDER BY bin_number;
"
```

**Perfect Calibration**: predicted_prob ≈ actual_frequency

---

## Analysis Procedures

### Procedure 16: Plate Appearance Outcome Analysis

**Purpose**: Deep dive into PA outcome distributions

**Step-by-Step**:

```bash
# Step 1: Run analysis
uv run python scripts/analysis/analyze_pa_outcome_distribution.py \
    --season 2025 \
    --output analysis/pa_outcomes_2025.json

# Step 2: Review summary
cat analysis/pa_outcomes_2025.json | jq '.summary'
```

---

### Procedure 17: Pitch Clustering

**Purpose**: Discover natural pitch groupings

**Step-by-Step**:

```bash
# Step 1: Run clustering
uv run python scripts/analysis/pitch_clustering_analysis.py \
    --n-clusters 8 \
    --method kmeans \
    --output-dir models/pitch_clusters

# Step 2: View cluster profiles
cat models/pitch_clusters/kmeans_8_clusters.json
```

**What It Does**:
- Groups similar pitches (velocity, movement, location)
- Discovers pitch "types" beyond manual classification
- Useful for arsenal analysis

---

### Procedure 18: Player Performance Analysis

**Purpose**: Analyze batter/pitcher performance

```sql
-- Batter performance by zone
SELECT 
    batter_id,
    zone,
    COUNT(*) as pitches_seen,
    AVG(CASE WHEN outcome_tier1 = 'hit' THEN 1.0 ELSE 0.0 END) as hit_rate
FROM features_pitch.engineered_features
WHERE game_year = 2025
GROUP BY batter_id, zone
HAVING COUNT(*) > 50
ORDER BY batter_id, hit_rate DESC;

-- Pitcher arsenal
SELECT 
    pitcher_id,
    pitch_type,
    COUNT(*) as pitches_thrown,
    AVG(release_speed) as avg_velocity,
    AVG(pfx_x) as avg_movement_x,
    AVG(pfx_z) as avg_movement_z
FROM features_pitch.base_features
WHERE game_year = 2025
GROUP BY pitcher_id, pitch_type
HAVING COUNT(*) > 100
ORDER BY pitcher_id, pitches_thrown DESC;
```

---

## Maintenance Procedures

### Procedure 19: Database Maintenance

**Purpose**: Keep database healthy and performant

**Weekly**:
```bash
# Vacuum and analyze
psql -d retrosheet -c "VACUUM ANALYZE;"

# Check table sizes
psql -d retrosheet -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname IN ('features_pitch', 'raw_mlb')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
"
```

**Monthly**:
```bash
# Reindex
psql -d retrosheet -c "REINDEX DATABASE retrosheet;"

# Check for bloat
psql -d retrosheet -c "
SELECT 
    schemaname, tablename, 
    n_tup_ins, n_tup_upd, n_tup_del,
    n_live_tup, n_dead_tup
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC;
"
```

---

### Procedure 20: Backup Procedures

**Purpose**: Ensure data safety

**Automated Backup**:
```bash
# Run backup script
./scripts/backup_procedures.sh

# Or manual backup
cd /home/cbwinslow/workspace/retrosheet
pg_dump -d retrosheet -f backups/retrosheet_$(date +%Y%m%d).sql
```

**Key Tables to Backup**:
```bash
# Critical tables only
pg_dump -d retrosheet \
    --table=models.model_registry \
    --table=features_pitch.feature_registry \
    --table=warehouse.rebuild_runs \
    -f backups/critical_$(date +%Y%m%d).sql
```

---

## Troubleshooting Procedures

### Procedure 21: Diagnose Data Pipeline Issues

**Symptom**: Missing or stale data

**Diagnosis Steps**:

```bash
# Step 1: Check raw data freshness
psql -d retrosheet -c "
SELECT 
    'raw_mlb.statcast' as source,
    MAX(game_date) as latest_date,
    COUNT(*) FILTER (WHERE game_date >= CURRENT_DATE - 7) as recent_rows
UNION ALL
SELECT 
    'raw_espn.game_snapshots',
    MAX((response_json->>'date')::date),
    COUNT(*) FILTER (WHERE fetched_at >= NOW() - INTERVAL '7 days')
FROM raw_espn.game_snapshots;
"

# Step 2: Check feature freshness
psql -d retrosheet -c "
SELECT 
    MAX(game_year) as latest_year,
    MAX(created_at) as latest_feature_build
FROM features_pitch.engineered_features;
"

# Step 3: Check for data gaps
psql -d retrosheet -c "
SELECT 
    game_year,
    COUNT(*) as pitch_count
FROM features_pitch.engineered_features
GROUP BY game_year
ORDER BY game_year DESC
LIMIT 5;
"
```

**Resolution**:
- If raw data stale: Re-run ingestion scripts
- If features stale: Run `sql/features/001_pitch_features.sql`
- If gaps exist: Check `warehouse.rebuild_log` for failures

---

### Procedure 22: Fix Model Registry Issues

**Symptom**: Model not found or wrong model used

**Diagnosis**:
```sql
-- List all models
SELECT 
    model_id,
    model_name,
    target_id,
    is_active,
    created_at,
    metrics->>'roc_auc' as auc
FROM models.model_registry
ORDER BY target_id, created_at DESC;

-- Check for orphaned models (no artifact file)
SELECT 
    mr.model_id,
    mr.artifact_uri,
    EXISTS(SELECT 1 FROM pg_stat_file(mr.artifact_uri)) as file_exists
FROM models.model_registry mr
WHERE mr.is_active = TRUE;
```

**Resolution**:
```sql
-- Activate correct model
UPDATE models.model_registry
SET is_active = TRUE
WHERE model_id = <CORRECT_MODEL_ID>;

-- Deactivate old models
UPDATE models.model_registry
SET is_active = FALSE
WHERE target_id = 'swing_decision'
  AND model_id != <CORRECT_MODEL_ID>;
```

---

### Procedure 23: Performance Troubleshooting

**Symptom**: Slow queries or timeouts

**Diagnosis**:
```sql
-- Check slow queries
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check missing indexes
SELECT 
    schemaname,
    tablename,
    attname as column,
    n_tup_read,
    n_tup_fetch
FROM pg_stats
WHERE schemaname = 'features_pitch'
  AND n_tup_read > 1000000
  AND NOT EXISTS (
      SELECT 1 FROM pg_indexes 
      WHERE indexname LIKE '%' || attname || '%'
  )
LIMIT 20;
```

**Resolution**:
```sql
-- Add index for slow queries
CREATE INDEX CONCURRENTLY idx_engineered_features_training 
ON features_pitch.engineered_features(game_year, is_valid_for_training);

-- Vacuum table
VACUUM ANALYZE features_pitch.engineered_features;
```

---

## Advanced Procedures

### Procedure 24: Custom Feature Engineering

**Purpose**: Add domain-specific features

**Step-by-Step**:

```sql
-- Step 1: Add new feature to engineered_features
ALTER TABLE features_pitch.engineered_features
ADD COLUMN IF NOT EXISTS my_custom_feature NUMERIC;

-- Step 2: Populate with calculation
UPDATE features_pitch.engineered_features
SET my_custom_feature = release_speed * release_spin_rate / 1000
WHERE my_custom_feature IS NULL;

-- Step 3: Register in feature_registry
INSERT INTO features_pitch.feature_registry (
    feature_name,
    feature_category,
    feature_type,
    description,
    is_active
) VALUES (
    'my_custom_feature',
    'physics',
    'numeric',
    'Custom feature: velocity * spin rate / 1000',
    TRUE
);
```

---

### Procedure 25: Batch Processing with Resume

**Purpose**: Handle long-running operations with failure recovery

**Step-by-Step**:

```sql
-- Step 1: Start batch operation
INSERT INTO warehouse.batch_operations (
    batch_name,
    operation_type,
    target_schema,
    target_table,
    total_rows,
    batch_params
) VALUES (
    'populate_my_features',
    'feature_engineering',
    'features_pitch',
    'my_features',
    (SELECT COUNT(*) FROM features_pitch.engineered_features),
    '{"custom_param": "value"}'::jsonb
) RETURNING batch_id;

-- Step 2: Process in chunks (Python or PL/pgSQL)
-- Update progress periodically:
SELECT warehouse.update_batch_progress(
    <BATCH_ID>,
    <LAST_PROCESSED_ID>,
    <PROCESSED_COUNT>
);

-- Step 3: Resume if interrupted
SELECT * FROM warehouse.active_batches;

-- Get resume point
SELECT last_processed_id 
FROM warehouse.batch_operations 
WHERE batch_id = <BATCH_ID>;
```

---

## Quick Command Reference

### Database
```bash
# Connect
psql -d retrosheet

# Run SQL file
psql -d retrosheet -f sql/file.sql

# Export query to CSV
psql -d retrosheet -c "COPY (SELECT * FROM table) TO STDOUT CSV HEADER" > output.csv
```

### Python Scripts
```bash
# Run with uv
uv run python scripts/script.py

# Run with logging
uv run python scripts/script.py --verbose 2>&1 | tee logs/run_$(date +%Y%m%d_%H%M%S).log
```

### Warehouse Rebuild
```bash
# Full
./scripts/rebuild_warehouse.sh --mode full

# Quick
./scripts/rebuild_warehouse.sh --mode quick

# Resume
./scripts/rebuild_warehouse.sh --mode resume
```

### Model Operations
```bash
# Train
uv run python scripts/model_training/train_models.py --target swing_decision

# Predict
uv run python scripts/model_inference/predict_plate_appearance.py --model-id <ID>

# Evaluate
uv run python scripts/analysis/analyze_pa_models.py --model-id <ID>
```

---

**End of Detailed Procedures Guide**

For additional information:
- `docs/USER_MANUAL.md` - User-focused guide
- `docs/agents/FILE_INVENTORY.md` - File reference
- `docs/WORKFLOW_VALIDATION_REPORT.md` - Architecture analysis
