# Workflow Validation Report

**Date**: April 24, 2026  
**Purpose**: Critical analysis of current workflow, identify duplication, assess framework value

---

## Executive Summary

**FINDING**: The `framework` schema I created is **mostly redundant** with existing infrastructure. The warehouse already has comprehensive logging and tracking.

**RECOMMENDATION**: Do NOT apply `sql/framework/001_framework_schema.sql`. Instead, build Python wrappers that use existing SQL infrastructure.

---

## Database Schema Audit

### What Actually Exists

| Schema | Tables | Status |
|--------|--------|--------|
| `warehouse` | `rebuild_runs`, `rebuild_log` | ✅ Logging exists |
| `models` | `model_registry` | ✅ Model tracking exists |
| `features_pitch` | `feature_registry` | ✅ Feature metadata exists |
| `framework` | **NONE** | ❌ Not applied (and shouldn't be) |

### Redundancy Analysis

| Framework Table (Not Applied) | Existing Equivalent | Verdict |
|------------------------------|---------------------|---------|
| `framework.log` | `warehouse.rebuild_log` | REDUNDANT |
| `framework.experiments` | `warehouse.rebuild_runs` + metadata column | REDUNDANT |
| `framework.plugins` | Python package registry | NOT NEEDED |
| `framework.batches` | None (unique capability) | **USEFUL** |
| `framework.model_registry` | `models.model_registry` | REDUNDANT |
| `framework.feature_registry` | `features_pitch.feature_registry` | REDUNDANT |

**Conclusion**: 5 of 6 framework tables are redundant. Only `framework.batches` would add unique value.

---

## Current Workflow Analysis

### Data Flow Diagram (Actual State)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA SOURCES                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Retrosheet  │  │ MLB Stats   │  │ ESPN        │  │ Lahman      │        │
│  │ Historical  │  │ API         │  │ API         │  │ Database    │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │             │
└─────────┼────────────────┼────────────────┼────────────────┼─────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RAW LAYER                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │raw_retroshee│  │raw_mlb      │  │raw_espn     │  │lahman       │        │
│  │t.events    │  │.statcast    │  │.game_snaps  │  │.people      │        │
│  │62K games   │  │7.8M pitches │  │71K games    │  │20K players  │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
└─────────┼────────────────┼────────────────┼────────────────┼─────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BRIDGE LAYER (ID Mappings)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────┐        │
│  │ bridge.player_xref (128K rows) - Player ID crosswalk             │        │
│  │ bridge.team_xref (294 rows) - Team mappings                      │        │
│  │ bridge.game_xref (59K rows) - Game matching                      │        │
│  │ bridge.park_xref (656 rows) - Stadium IDs                        │        │
│  └─────────────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CORE LAYER (Canonical Data)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │core.games   │  │core.events  │  │core.plate_  │  │core.parks   │        │
│  │62K rows     │  │4.9M rows    │  │appearances  │  │656 rows     │        │
│  └──────┬──────┘  └──────┬──────┘  │4.8M rows     │  └─────────────┘        │
│         │                │        └──────┬──────┘                           │
│         │                │                │                                │
└─────────┼────────────────┼────────────────┼────────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FEATURE LAYER (ML-Ready)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ TRADITIONAL FEATURES (features schema)                              │   │
│  │ • Prior season marts (batter/pitcher/team rates)                    │   │
│  │ • Career prior statistics                                           │   │
│  │ • Matchup history                                                   │   │
│  │ • Context (park, game situation)                                    │   │
│  │ • Rolling team form                                                 │   │
│  │ • Count-state specific rates                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PITCH-LEVEL FEATURES (features_pitch schema) - 7.66M rows           │   │
│  │ • base_features - 118 Statcast fields                               │   │
│  │ • engineered_features - 220+ derived features                       │   │
│  │ • feature_registry - 220+ feature metadata                          │   │
│  │ • model_training_set - versioned training data                      │   │
│  │ • player_context - rolling player stats                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MODEL LAYER                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Training Scripts:                                                          │
│  ┌──────────────────────────┐  ┌─────────────────────────────────────────┐ │
│  │ train_models.py          │  │ train_pa_outcome_distribution.py        │ │
│  │ • Binary targets         │  │ • Multiclass PA outcomes                │ │
│  │ • Logistic Regression    │  │ • XGBoost/LightGBM/CatBoost             │ │
│  │ • HistGradientBoosting   │  │ • Feature sets: basic/advanced/count    │ │
│  └───────────┬──────────────┘  └───────────────────┬─────────────────────┘ │
│              │                                      │                       │
│              └──────────────────┬───────────────────┘                       │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ models.model_registry (versioned models with metrics)               │    │
│  │ • target_id, model_name, model_family, model_version               │    │
│  │ • artifact_uri, feature_spec, metrics (JSONB)                      │    │
│  │ • is_active flag for model promotion                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PREDICTION & EVALUATION LAYER                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Prediction Scripts:                                                        │
│  • predict_plate_appearance.py (historical binary)                            │
│  • predict_pa_outcome_distribution.py (historical multiclass)               │
│  • predict_live_pa_outcome_distribution.py (live scoring)                 │
│                                                                             │
│  Evaluation Scripts:                                                        │
│  • analyze_pa_models.py                                                     │
│  • analyze_pa_outcome_calibration.py                                      │
│  • calibrate_pa_outcome_model.py                                           │
│  • bootstrap_pa_outcome_evaluation.py                                      │
│  • cross_validate_models.py                                                │
│                                                                             │
│  Prediction Tables:                                                         │
│  • predictions.calibration_reports                                         │
│  • predictions.evaluation_reports                                          │
│  • predictions.bootstrap_summaries                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Workflow Gap Analysis

### GAP 1: Orchestration Logging (PARTIALLY ADDRESSED)

**Status**: ✅ `warehouse.rebuild_runs` and `warehouse.rebuild_log` exist

**Gap**: No per-experiment tracking beyond warehouse rebuilds

**Solution**: Add experiment_type column to warehouse schema rather than new table

```sql
-- Instead of framework.experiments, extend warehouse.rebuild_runs:
ALTER TABLE warehouse.rebuild_runs 
ADD COLUMN run_type VARCHAR(20) DEFAULT 'warehouse_rebuild' 
CHECK (run_type IN ('warehouse_rebuild', 'model_training', 'feature_discovery'));
```

### GAP 2: Batch Processing Resume (NOT ADDRESSED)

**Status**: ❌ No existing solution for resumable batch operations

**Gap**: Feature engineering scripts need to resume if interrupted

**Solution**: Create minimal `warehouse.batch_operations` table

```sql
-- ONLY the unique capability from framework schema:
CREATE TABLE warehouse.batch_operations (
    batch_id SERIAL PRIMARY KEY,
    operation_name TEXT NOT NULL,  -- 'populate_engineered_features'
    table_name TEXT NOT NULL,      -- 'features_pitch.engineered_features'
    last_processed_id BIGINT,      -- Resume point
    total_rows BIGINT,
    status TEXT DEFAULT 'running',
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

### GAP 3: Configuration Management (NOT ADDRESSED)

**Status**: ❌ Hardcoded parameters in scripts

**Gap**: No standardized way to share configs between scripts

**Solution**: YAML configs + Pydantic models (Python layer, not SQL)

### GAP 4: Plugin Discovery (NOT ADDRESSED)

**Status**: ❌ No registry for custom models

**Gap**: Researchers can't easily plug in models

**Solution**: Python plugin registry (in-memory + filesystem), NOT database table

### GAP 5: Unified CLI (NOT ADDRESSED)

**Status**: ❌ Multiple scripts with different args

**Gap**: No single entry point

**Solution**: `mlb-predict` CLI that dispatches to existing scripts

---

## Feature Interaction Explorer Analysis

Looking at `scripts/analysis/feature_interaction_explorer.py`:

**Issue**: References `framework.feature_importance` table which DOESN'T EXIST

```python
# Line 47-49:
SELECT feature_name
FROM framework.feature_importance  -- ❌ Table doesn't exist
WHERE analysis_method = 'xgboost_gain'
```

**Solutions**:
1. Create `analysis.feature_importance` table (not framework schema)
2. Or query from existing XGBoost model artifacts
3. Or compute on-the-fly from training data

**Recommended Fix**:
```sql
-- Create in analysis schema instead:
CREATE TABLE analysis.feature_importance (
    importance_id SERIAL PRIMARY KEY,
    model_id BIGINT REFERENCES models.model_registry(model_id),
    feature_name TEXT NOT NULL,
    importance_score NUMERIC,
    analysis_method TEXT,  -- 'xgboost_gain', 'shap', 'permutation'
    computed_at TIMESTAMP DEFAULT NOW()
);
```

---

## Pitch Clustering Analysis

Looking at `scripts/analysis/pitch_clustering_analysis.py` (referenced in FILE_INVENTORY):

**Status**: File exists but not yet reviewed

**Purpose**: K-Means/GMM clustering to discover natural pitch groupings

**Integration Point**: Should write results to `features_pitch.pitch_clusters` table

```sql
-- Add to features_pitch schema:
CREATE TABLE features_pitch.pitch_clusters (
    cluster_id SERIAL PRIMARY KEY,
    cluster_method TEXT,  -- 'kmeans', 'gmm'
    n_clusters INT,
    pitch_type_mast TEXT,  -- Most common pitch type in cluster
    avg_velocity NUMERIC,
    avg_movement_x NUMERIC,
    avg_movement_z NUMERIC,
    cluster_center JSONB  -- Full centroid vector
);
```

---

## Revised Integration Plan

### Phase 1: Fix Existing Scripts (1 day)
- [ ] Fix `feature_interaction_explorer.py` to use existing tables
- [ ] Add `analysis.feature_importance` table (NOT framework schema)
- [ ] Remove framework schema dependency

### Phase 2: Add Unique Capabilities (2 days)
- [ ] Add `warehouse.batch_operations` table for resume capability
- [ ] Add `features_pitch.pitch_clusters` for clustering results
- [ ] Extend `warehouse.rebuild_runs` with `run_type` column

### Phase 3: Python Integration Layer (3 days)
- [ ] Config system (YAML + Pydantic)
- [ ] ModelTrainer wrapper (uses existing scripts)
- [ ] Plugin registry (Python-based, no SQL)
- [ ] Unified CLI

### Phase 4: Remove Redundancy (1 day)
- [ ] Delete `sql/framework/001_framework_schema.sql`
- [ ] Update documentation
- [ ] Verify all scripts work

---

## Decision: Is The Framework Worth It?

### YES - But Different Approach

**Worth doing**: Python integration layer that wraps existing scripts  
**NOT worth doing**: Redundant SQL schema

### Value Assessment

| Component | Value | Effort | Recommendation |
|-----------|-------|--------|----------------|
| Unified CLI | HIGH | 2 days | ✅ DO IT |
| Config System | HIGH | 1 day | ✅ DO IT |
| Plugin Registry | MEDIUM | 2 days | ✅ DO IT (Python only) |
| Batch Resume | MEDIUM | 1 day | ✅ DO IT (warehouse table) |
| Feature Importance | MEDIUM | 0.5 day | ✅ DO IT (analysis table) |
| framework SQL schema | LOW | - | ❌ DELETE |

---

## Immediate Actions Required

### Critical Fix (Do Now)
1. **Delete or archive `sql/framework/001_framework_schema.sql`** - It's redundant
2. **Fix `feature_interaction_explorer.py`** - Remove framework dependency
3. **Create `analysis.feature_importance` table** for the script to use

### Before Next Steps
Confirm this approach with user:
- ✅ Keep existing SQL infrastructure
- ✅ Build thin Python wrappers
- ✅ Focus on unique capabilities (batch resume, CLI, config)
- ❌ Don't create parallel schema

---

## Updated Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     PYTHON INTEGRATION LAYER (New)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ mlb-predict  │  │ Config       │  │ Plugin       │          │
│  │ CLI          │  │ (YAML)       │  │ Registry     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼────────────────┼────────────────┼────────────────────┘
          │                │                │
          │  ┌─────────────┘                │
          │  │  ┌───────────────────────────┘
          │  │  │
          ▼  ▼  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     EXISTING SCRIPTS (Unchanged)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │train_models  │  │train_pa_out  │  │predict_...   │            │
│  │    .py       │  │ come_dist    │  │              │            │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘            │
└─────────┼────────────────┼────────────────┼────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     EXISTING SQL INFRASTRUCTURE                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │warehouse     │  │models        │  │features_pitch│            │
│  │.rebuild_runs │  │.model_registr│  │.feature_regis│            │
│  │              │  │y             │  │try           │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │warehouse     │  │analysis      │  │predictions   │            │
│  │.batch_ops    │  │.feature_impor│  │.*_reports    │            │
│  │ (NEW)        │  │tance (NEW)   │  │              │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
└──────────────────────────────────────────────────────────────────┘
```

---

## Files to Modify/Create

### Delete/Archive
| File | Action |
|------|--------|
| `sql/framework/001_framework_schema.sql` | DELETE (redundant) |
| `framework/` directory | DELETE (parallel structure) |
| `mlb_predict/` directory | KEEP but refactor |

### Fix
| File | Fix |
|------|-----|
| `scripts/analysis/feature_interaction_explorer.py` | Remove framework.feature_importance reference |

### Create (Minimal SQL)
| File | Purpose |
|------|---------|
| `sql/analysis/001_feature_importance.sql` | Store XGBoost/SHAP importance scores |
| `sql/warehouse/004_batch_operations.sql` | Resume capability for long operations |

### Create (Python Integration)
| File | Purpose |
|------|---------|
| `mlb_predict/config/schema.py` | Pydantic config models |
| `mlb_predict/core/trainer.py` | ModelTrainer wrapper |
| `mlb_predict/cli/main.py` | Unified CLI |
| `scripts/mlb-predict` | CLI entry point |

---

## Success Criteria (Revised)

1. ✅ All existing scripts work unchanged
2. ✅ No redundant SQL schema created
3. ✅ New tables only add unique capabilities
4. ✅ Researchers can add custom models in 5 lines
5. ✅ Single CLI command for common workflows
6. ✅ E2E tests pass

---

## Next Decision

**Question**: Should I proceed with the revised plan (delete framework SQL, fix scripts, create minimal additions)?

Or do you want to:
- A) Review the analysis first
- B) Adjust the approach
- C) Focus on a specific component
- D) Something else
