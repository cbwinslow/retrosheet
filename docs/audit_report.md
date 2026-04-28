# Phase 1 Audit Report

**Date**: 2026-04-28  
**Auditor**: Cascade Agent  
**Repository**: cbwinslow/retrosheet  

---

## Executive Summary

The baseball prediction warehouse is **75-80% complete** with solid foundations but several key gaps in feature calculators, models, and CLI commands.

| Component | Status | Coverage |
|-----------|--------|----------|
| Source Adapters | ✅ Complete | 5/5 working |
| Pipelines | ✅ Complete | 7/7 configured |
| Feature Calculators | ⚠️ Partial | 5/6 working, 1 missing |
| CLI Commands | ⚠️ Partial | Core working, many stubs |
| Models | ⚠️ Partial | 2/3 working, 1 missing |
| SQL Schema | ✅ Complete | All layers present |

---

## 1. Feature Calculators Audit

### Current State

| Calculator | File | Status | SQL Table | CLI Wired | Notes |
|------------|------|--------|-----------|-----------|-------|
| WinExpectancyCalculator | win_expectancy.py | ✅ Full | features.win_expectancy_matrix | ✅ | Working |
| LeverageIndexCalculator | leverage_index.py | ✅ Full | features.leverage_index_matrix | ✅ | Working |
| MatchupCalculator | matchup.py | ✅ Full | features.matchup_features | ✅ | Working |
| RollingFormCalculator | rolling_form.py | ✅ Full | features.rolling_form | ✅ | Working |
| BullpenCalculator | bullpen.py | ✅ Full | features.bullpen_features | ✅ | Working |
| **RunExpectancyCalculator** | **N/A** | ❌ **Missing** | **N/A** | **❌** | **Documented but not implemented** |

### Key Findings

**Finding 1.1**: RunExpectancyCalculator is mentioned in `features/__init__.py` docstring (line 6: "Run Expectancy (RE) matrix") but **no file exists**.

**Finding 1.2**: BullpenCalculator exists and has stress/fatigue metrics. It may need renaming to BullpenStressCalculator for clarity, but functionality is present.

**Finding 1.3**: All 5 existing calculators inherit from FeatureStore base class and follow consistent patterns.

### Gaps

1. **Run Expectancy Calculator**: Complete missing implementation
2. **BullpenStress naming**: Consider renaming BullpenCalculator → BullpenStressCalculator

---

## 2. CLI Commands Audit

### Current State

| Command | Type | Status | Notes |
|---------|------|--------|-------|
| doctor | Core | ✅ Full | Database, directories, checks |
| status | Core | ✅ Full | Pipeline runs, system status |
| version | Core | ✅ Full | Version display |
| **bridge resolve** | Bridge | ❌ **Stub** | NotImplementedError @ line 1079 |
| **bridge match** | Bridge | ❌ **Stub** | NotImplementedError @ line 1093 |
| **bridge lookup** | Bridge | ❌ **Stub** | NotImplementedError @ line 1106 |
| pipeline run | Pipeline | ✅ Full | Working with PipelineService |
| pipeline list | Pipeline | ✅ Full | Lists 7 pipelines |
| pipeline status | Pipeline | ✅ Full | Shows recent runs |
| mlb download/ingest/validate/today | Data | ✅ Full | Source adapter integration |
| retrosheet download/ingest/validate/seasons | Data | ✅ Full | Source adapter integration |
| statcast download/ingest/validate/seasons | Data | ✅ Full | Source adapter integration |
| espn download/ingest/validate | Data | ✅ Full | Source adapter integration |
| features list | Features | ✅ Full | Lists 5 calculators |
| features compute | Features | ⚠️ Partial | Works but limited error handling |
| features show | Features | ⚠️ Partial | Basic implementation |
| predict game | Predict | ✅ Full | Working with mock data |
| **predict today** | Predict | ❌ **Stub** | TODO comment @ line 542 |
| **predict live** | Predict | ❌ **Stub** | TODO comment @ line 553 |
| **predict batch** | Predict | ❌ **Stub** | TODO comment @ line 565 |
| models list | Models | ⚠️ Partial | Shows table but queries nothing @ line 715 |
| **models info** | Models | ❌ **Stub** | Raises typer.Exit @ line 726 |
| **models download** | Models | ❌ **Stub** | Raises typer.Exit @ line 738 |
| **models archive** | Models | ❌ **Stub** | Raises typer.Exit @ line 749 |
| **models compare** | Models | ❌ **Stub** | Raises typer.Exit @ line 760 |
| **models export** | Models | ❌ **Stub** | Raises typer.Exit @ line 772 |
| **models train** | Models | ⚠️ Partial | Has logic but not fully implemented @ line 775+ |
| chatbot chat | Chatbot | ✅ Full | Working |
| chatbot demo | Chatbot | ✅ Full | Working |

### Key Findings

**Finding 2.1**: Bridge commands (resolve/match/lookup) are stubs but BridgeService in `services/bridge.py` has working implementations that just need to be wired.

**Finding 2.2**: Predict commands (today/live/batch) are stubs but pipeline infrastructure exists to support them.

**Finding 2.3**: Models commands are mostly stubs - model infrastructure exists but CLI integration incomplete.

### Gaps

1. **Bridge CLI**: Wire BridgeService methods to CLI commands
2. **Predict CLI**: Implement today/live/batch using pipeline infrastructure
3. **Models CLI**: Complete list/info/download/archive/compare/export/train

---

## 3. Models Audit

### Current State

| Model | File | Status | Training | Inference | Registry | Notes |
|-------|------|--------|----------|-----------|----------|-------|
| NextRunProbabilityModel | next_run_model.py | ✅ Full | ✅ | ✅ | ✅ | Working |
| PAOutcomeModel | pa_outcome_model.py | ✅ Full | ✅ | ✅ | ✅ | Working |
| **WinProbabilityModel** | **N/A** | ❌ **Missing** | **-** | **-** | **-** | **Referenced in CLI but no file** |

### Key Findings

**Finding 3.1**: `baseball/models/__init__.py` only exports NextRunProbabilityModel and PAOutcomeModel.

**Finding 3.2**: `baseball/cli.py` line 797 references WinProbabilityModel in model_map but it's None:
```python
'win_probability': (None, ModelType.WIN_PROBABILITY),  # TODO: Implement
```

**Finding 3.3**: SQL layer for models exists:
- `sql/60_models/6001_models_registry.sql` - Model registry
- `sql/60_models/6002_models_next_run.sql` - Next run model tables
- `sql/60_models/6003_models_pa_outcome.sql` - PA outcome model tables
- `sql/60_models/6004_models_model_automation_triggers.sql` - Automation

**Finding 3.4**: Base model infrastructure is solid:
- `BaseModel` abstract class with train/predict interface
- `SklearnBaseModel` for scikit-learn models
- Model registry pattern established

### Gaps

1. **WinProbabilityModel**: Complete missing implementation
2. **Model training pipeline**: Wire CLI to actual training
3. **Model inference service**: For live predictions

---

## 4. SQL Schema Audit

### Current State

| Directory | File Count | Key Files | Status |
|-----------|------------|-----------|--------|
| sql/00_admin/ | 1 | pipeline control | ✅ |
| sql/10_raw/ | 19 | raw data schemas | ✅ |
| sql/20_staging/ | 0 | (empty) | ⚠️ Unused |
| sql/30_core/ | 23 | core tables | ✅ |
| sql/40_bridge/ | 15 | bridge tables | ✅ |
| sql/50_features/ | 36 | feature tables | ✅ |
| sql/60_models/ | 4 | model registry | ✅ |
| sql/70_serving/ | 1 | serving views | ⚠️ Minimal |
| sql/80_quality/ | 0 | (empty) | ⚠️ Unused |

### Key Findings

**Finding 4.1**: Feature tables exist:
- `features.win_expectancy_matrix` ✅
- `features.leverage_index_matrix` ✅
- `features.matchup_features` ✅
- `features.rolling_form` ✅
- `features.bullpen_features` ✅
- `features.run_expectancy_matrix` ❌ Missing (need to create)

**Finding 4.2**: Serving layer minimal - only 1 file in `sql/70_serving/`.

**Finding 4.3**: Staging and quality layers empty - may not be needed given current architecture.

### Gaps

1. **run_expectancy_matrix table**: Create SQL
2. **Serving views**: Add materialized views for performance
3. **Quality checks**: Optional - add if needed

---

## 5. Pipeline Configuration Audit

### Current State

```yaml
# From config/pipelines.yml
pipelines:
  - daily: 6 steps ✅
  - historical: 6 steps ✅
  - live: 4 steps ✅
  - retrosheet_ingest: 3 steps ✅
  - mlb_live_ingest: 4 steps ✅
  - statcast_ingest: 3 steps ✅
  - feature_building: 5 steps ✅
```

### Key Findings

**Finding 5.1**: All 7 pipelines configured with proper checkpoint tables.

**Finding 5.2**: `feature_building` pipeline references `run_expectancy` step but calculator doesn't exist.

**Finding 5.3**: PipelineService in `services/pipeline.py` has working implementation.

---

## 6. Demo Script Results

```
System Evaluation Results:
✅ CLI Available: True
✅ Source Adapters: 5/5
✅ Pipelines: 7
⚠️ Feature Calculators: 4/6 (RunExpectancyCalculator, BullpenStressCalculator missing)
⚠️ Database: Not connected (quick mode)
```

---

## Answers to 12 Critical Questions

### Q1: Run Expectancy Calculator
**Answer**: YES, implement using **Approach A** (compute from historical data)

**Reasoning**:
- Documented in `features/__init__.py` but no file exists
- Used by WinExpectancy and LeverageIndex calculators
- Pipeline config references it
- RE is foundational sabermetric - must have for complete feature set

**Priority**: P1 (important)

---

### Q2: Bullpen Stress vs BullpenCalculator
**Answer**: **Option A** - Rename/extend existing BullpenCalculator

**Reasoning**:
- BullpenCalculator already has fatigue metrics, stress index, availability
- Has `calculate_fatigue_score()`, `get_bullpen_advantage()` methods
- Just needs renaming for clarity: `BullpenCalculator` → `BullpenStressCalculator`
- Or update `__init__.py` to export as `BullpenStressCalculator` alias

**Priority**: P2 (nice to have - cosmetic)

---

### Q3: Model Storage Strategy
**Answer**: **Option C** - Hybrid (DB for metadata, filesystem for artifacts)

**Reasoning**:
- SQL layer has `models.registry` and `models.artifacts` tables
- Artifacts table has `file_path` column suggesting filesystem storage
- Binary model files (pickles) can be large - filesystem more efficient
- Metadata in DB enables queries, versioning, lineage tracking

**Priority**: P0 (already implemented - just verify)

---

### Q4: Inference Latency Target
**Answer**: **Option B** - <100ms (materialized views + indexes)

**Reasoning**:
- Current architecture uses materialized views
- 100ms is acceptable for baseball predictions (not high-frequency trading)
- Can optimize with indexes and caching if needed
- PostgreSQL with proper indexing can easily achieve <100ms

**Priority**: P1 (implement serving layer)

---

### Q5: Bridge CLI Commands
**Answer**: Priority: **1) resolve, 2) lookup, 3) match**

**Reasoning**:
- `resolve` most critical - convert source IDs to canonical (needed for predictions)
- `lookup` second - get all source IDs for a canonical ID
- `match` least critical - used for data quality, not runtime
- BridgeService already has working implementations

**Priority**: P1 (wire up resolve first)

---

### Q6: WebSocket Server
**Answer**: **Option C** - Skip for now, focus on batch predictions

**Reasoning**:
- `predict today` and `predict batch` more immediately useful
- HTTP polling sufficient for initial live predictions
- WebSocket adds complexity - implement if user demand
- Can add later without breaking existing architecture

**Priority**: P2 (defer)

---

### Q7: Feature Store Pattern
**Answer**: **Option B** - Keep current calculator pattern + materialized views

**Reasoning**:
- Current pattern works well: calculators for computation, views for serving
- FeatureStore base class provides consistent interface
- No need for heavy Feature Store infrastructure yet
- Can migrate later if scale requires

**Priority**: P2 (keep current)

---

### Q8: Missing SQL Layers
**Answer**: **Option B** - No, current flow works

**Reasoning**:
- `10_raw → 30_core → 50_features` flow is working
- Staging layer adds complexity without clear benefit
- Quality layer can be added as views/functions if needed
- Keep architecture simple

**Priority**: P3 (skip)

---

### Q9: Testing Coverage Target
**Answer**: **Option B** - 80%+ coverage, focus on integration

**Reasoning**:
- Current tests exist in `tests/unit/`, `tests/integration/`, `tests/e2e/`
- Integration tests critical for DB-dependent code
- E2E tests validate full pipeline
- 100% coverage often wastes time on trivial code

**Priority**: P1 (maintain current approach)

---

### Q10: Historical vs Live Feature Parity
**Answer**: **Option A** - Same code path, different data sources

**Reasoning**:
- Current calculators use same `calculate()` method for both
- Feature values computed from same logic
- Just data source differs: historical DB vs live API
- Ensures parity by design

**Priority**: P0 (already implemented)

---

### Q11: Model Priority Order
**Answer**: **1) Win Probability, 2) PA Outcome, 3) Next Run**

**Reasoning**:
- Win Probability most valuable for live predictions
- PA Outcome already exists and working
- Next Run exists but less valuable than WP
- Win Probability is what users want to see

**Priority**: P0 (Win Probability is critical gap)

---

### Q12: Documentation Gaps
**Answer**: Priority: **C) Agent guidance files**

**Reasoning**:
- Architecture docs exist but agent guidance scattered
- FILE_INVENTORY.md, PROCEDURES.md need updating
- AGENTS.md has good foundation but needs completion status
- User docs less critical for development phase

**Priority**: P2 (update as we implement)

---

## Revised Implementation Plan

Based on actual codebase state, here is the realistic sequence:

### Phase 1: Foundation (COMPLETE)
- ✅ Audit complete
- ✅ 12 questions answered

### Phase 2: Critical Gaps (Week 1)
- [ ] Implement RunExpectancyCalculator
- [ ] Create SQL for run_expectancy_matrix table
- [ ] Wire bridge resolve/lookup CLI commands
- [ ] Update pipeline config to include run_expectancy

### Phase 3: Win Probability Model (Week 2)
- [ ] Implement WinProbabilityModel
- [ ] Create SQL for win_prob_predictions table
- [ ] Complete models train CLI
- [ ] Complete models predict CLI
- [ ] Test end-to-end prediction flow

### Phase 4: CLI Completion (Week 3)
- [ ] Complete predict today/live/batch
- [ ] Complete models list/info/download/archive/compare
- [ ] Add validation and error handling
- [ ] Write comprehensive tests

### Phase 5: Serving Layer (Week 4)
- [ ] Create materialized views for fast lookups
- [ ] Add refresh mechanism
- [ ] Optimize query performance
- [ ] Performance testing

### Phase 6: Documentation (Ongoing)
- [ ] Update AGENTS.md with completion status
- [ ] Update PROJECT_LOG.md
- [ ] Update FILE_INVENTORY.md
- [ ] Create user documentation

---

## Summary

**Current State**: Solid foundation, 75-80% complete

**Critical Gaps**:
1. RunExpectancyCalculator (missing)
2. WinProbabilityModel (missing)
3. Bridge CLI commands (stubs)
4. Predict CLI commands (stubs)
5. Models CLI commands (mostly stubs)

**Recommended Priority**:
1. WinProbabilityModel (highest value)
2. RunExpectancyCalculator (foundational)
3. Bridge CLI (enables cross-source workflows)
4. Predict CLI (user-facing feature)
5. Serving layer (performance optimization)
