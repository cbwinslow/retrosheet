# Project Log

## 2026-04-24 (Deployment Plan & GitHub Issue #80)

### Implementation Ready - Issue #80 Created

**GitHub Issue**: [#80 - Extensible MLB Prediction Framework](https://github.com/cbwinslow/retrosheet/issues/80)

**Status**: Ready for Implementation  
**Estimated**: 22 hours (3 weeks)  
**Priority**: High  
**Risk**: Low  

### Documents Created

| Document | Purpose | Size |
|----------|---------|------|
| **DEPLOYMENT_PLAN.md** | Complete implementation guide with phases | 400+ lines |
| **EXTENSIBLE_FRAMEWORK_DESIGN.md** | Pydantic schemas, architecture, examples | 600+ lines |
| **FRAMEWORK_CONFIRMATION.md** | Proof this will work, risk analysis | 400+ lines |
| **IMPLEMENTATION_ROADMAP.md** | 22-hour task breakdown by week | 500+ lines |

### Implementation Phases

**Phase 1: Foundation (Week 1)** - 6 hours
- Pydantic Configuration Schemas (2 hrs)
- Rich Result Classes (3 hrs)  
- Test Infrastructure (1 hr)

**Phase 2: Core Wrappers (Week 2)** - 10 hours
- ModelTrainer Class (4 hrs)
- Plugin Registry (2 hrs)
- FeatureLoader (2 hrs)
- Experiment Runner (2 hrs)

**Phase 3: Polish (Week 3)** - 6 hours
- Unified CLI (2 hrs)
- Database Triggers (1 hr)
- Documentation (2 hrs)
- Final Tests (1 hr)

### GitHub Tracking

- ✅ Issue #80 (Epic) created with deployment plan
- ✅ 10 Phase Issues (#81-#90) created and linked
- ✅ Detailed comments with task lists
- 🔄 Project board columns: Backlog → In Progress → Review → Done
- 🔄 Recommended labels: `enhancement`, `framework`, `pydantic`, `phase-1`, `phase-2`, `phase-3`

### GitHub Issues Structure
```
#80  Epic: Extensible MLB Prediction Framework
├── #81  Phase 1.1: Pydantic Configuration Schemas (2 hrs)
├── #82  Phase 1.2: Rich Result Classes (3 hrs)
├── #83  Phase 1.3: Test Infrastructure (1 hr)
├── #84  Phase 2.1: ModelTrainer Class (4 hrs)
├── #85  Phase 2.2: Plugin Registry (2 hrs)
├── #86  Phase 2.3: FeatureLoader (2 hrs)
├── #87  Phase 2.4: Experiment Runner (2 hrs)
├── #88  Phase 3.1: Unified CLI (2 hrs)
├── #89  Phase 3.2: Database Triggers (1 hr)
└── #90  Phase 3.3: Documentation (2 hrs)
```

### GitHub Project Guide Created
**File**: `docs/GITHUB_PROJECT_GUIDE.md`
- Project board setup instructions
- Labels and milestones recommendations
- Daily standup and weekly review templates
- Workflow automation suggestions
- Handoff checklist for agents

### Recommended GitHub Actions
1. Create Project Board: "Framework Implementation"
2. Add labels: `phase-1`, `phase-2`, `phase-3`, `framework`, `pydantic`
3. Create milestones: Phase 1/2/3 Complete
4. Pin issue #80
5. Add issues #81-#90 to Backlog column

### ✅ Phase 1.1 Complete - Pydantic Configuration Schemas

**Status**: COMPLETE ✅  
**Issue**: #81  
**Hours**: 2 hours (as planned)  
**Closed**: April 24, 2026

**Files Created**:
- ✅ `mlb_predict/config/schemas.py` (775 lines) - Complete Pydantic schemas
- ✅ `mlb_predict/config/loader.py` (250+ lines) - YAML/JSON loading with env var substitution
- ✅ `mlb_predict/config/__init__.py` - Package exports
- ✅ `tests/test_config.py` (500+ lines) - Comprehensive test suite

**Classes Implemented**:
- `ModelFamily`, `TargetVariable`, `FeatureSet`, `ValidationStrategy` (enums)
- `XGBoostConfig`, `LightGBMConfig`, `CatBoostConfig` (model hyperparameters)
- `SplitConfig`, `EarlyStoppingConfig`, `CalibrationConfig`, `FeatureImportanceConfig`
- `ModelConfig` (main config with validation and serialization)
- `ExperimentConfig` (multi-model experiments)

**Features Working**:
- ✅ Type-safe validation with Pydantic
- ✅ YAML serialization with `to_yaml()` / `from_yaml()`
- ✅ JSON serialization with `to_json()` / `from_json()`
- ✅ Environment variable substitution in configs
- ✅ Default configs for quick start
- ✅ ConfigManager for organizing configs

**Example**:
```python
from mlb_predict.config import ModelConfig, ModelFamily, TargetVariable

config = ModelConfig(
    family=ModelFamily.XGBOOST,
    target=TargetVariable.SWING_DECISION
)
config.to_yaml("my_experiment.yaml")
loaded = ModelConfig.from_yaml("my_experiment.yaml")
```

**Next**: Phase 1.2 (#82) - Rich Result Classes (TrainResult, Residuals, Metrics)

---

### ✅ Phase 1.2 Complete - Rich Result Classes

**Status**: COMPLETE ✅  
**Issue**: #82  
**Hours**: 3 hours (as planned)  
**Closed**: April 24, 2026

**Files Created**:
- ✅ `mlb_predict/core/results.py` (750+ lines) - Complete result classes
- ✅ `mlb_predict/core/__init__.py` - Package exports
- ✅ `tests/test_results.py` (300+ lines) - Comprehensive test suite
- ✅ Updated `mlb_predict/__init__.py` - Main package exports

**Classes Implemented**:
- `MetricValue` - Single metric with confidence intervals
- `Metrics` - Complete metrics collection (ROC AUC, log loss, accuracy, etc.)
- `ValidationCurve` - Training curves with plotting
- `FeatureImportance` - Feature importance scores
- `Residuals` - Residuals analysis with diagnostic plots
- `TrainResult` - Complete training result with all artifacts
- `PredictResult` - Prediction results with calibration

**Features Working**:
- ✅ Comprehensive metrics tracking
- ✅ Residual analysis (stats, plots, subgroup analysis)
- ✅ Feature importance access
- ✅ Model comparison (`compare_to()`, `is_better_than()`)
- ✅ Report generation
- ✅ Validation curve plotting
- ✅ Summary methods

**Example**:
```python
from mlb_predict import TrainResult, Residuals, Metrics, MetricValue

result = TrainResult(
    model_id=123,
    model_name="my_model",
    config=config,
    train_metrics=Metrics(roc_auc=MetricValue(value=0.85)),
    val_metrics=Metrics(roc_auc=MetricValue(value=0.83)),
    residuals=Residuals(y_true=[...], y_pred=[...], y_prob=[...])
)

# Analyze residuals
stats = result.residuals.analyze()
result.residuals.plot_residuals()

# Get top features
top_features = result.get_best_features(n=20)

# Compare models
comparison = result.compare_to(other_result)
```

**Next**: Phase 1.3 (#83) - Test Infrastructure (Integration tests)

---

### ✅ Phase 2.1 Complete - ModelTrainer Class

**Status**: COMPLETE ✅  
**Issue**: #84  
**Hours**: 4 hours (as planned)  
**Closed**: April 24, 2026

**Files Updated**:
- ✅ `mlb_predict/core/trainer.py` (570+ lines) - Refactored with Pydantic config
- ✅ `mlb_predict/core/__init__.py` - Updated exports
- ✅ `mlb_predict/__init__.py` - Main package exports

**Features Implemented**:
- ✅ Takes `ModelConfig` (Pydantic) instead of dict
- ✅ Returns `TrainResult` with rich data (metrics, residuals, feature importance)
- ✅ `from_config()` class method loads from YAML
- ✅ `register_plugin()` for custom models
- ✅ `train()` method with mock fallback for testing
- ✅ Integrates with existing `models.model_registry`

**Example**:
```python
from mlb_predict import ModelTrainer, ModelConfig, ModelFamily, TargetVariable

config = ModelConfig(
    family=ModelFamily.XGBOOST,
    target=TargetVariable.SWING_DECISION
)

trainer = ModelTrainer(config)
result = trainer.train()

# Access rich results
print(result.summary())
print(f"Val AUC: {result.val_metrics.roc_auc.value:.4f}")

# Analyze residuals
if result.val_residuals:
    stats = result.val_residuals.analyze()
```

**Next**: Phase 2.2 (#85) - Plugin Registry

---

## 2026-04-24 (Workflow Validation & Documentation Overhaul)

### Critical Finding: Framework Schema Redundancy

**Problem**: Created `sql/framework/001_framework_schema.sql` without checking existing infrastructure. Found that 5 of 6 tables duplicate existing schemas.

**Redundancy Analysis**:
| Framework Table | Existing Equivalent | Status |
|----------------|---------------------|--------|
| `framework.log` | `warehouse.rebuild_log` | ❌ Redundant |
| `framework.experiments` | `warehouse.rebuild_runs` | ❌ Redundant |
| `framework.plugins` | Python plugin registry | ❌ Not needed |
| `framework.model_registry` | `models.model_registry` | ❌ Redundant |
| `framework.feature_registry` | `features_pitch.feature_registry` | ❌ Redundant |
| `framework.batches` | None | ✅ Keep as `warehouse.batch_operations` |

**Action Taken**:
- Marked `sql/framework/001_framework_schema.sql` as **DEPRECATED**
- Created `sql/warehouse/004_batch_operations.sql` (unique capability only)
- Created `sql/analysis/001_feature_importance.sql` (for analysis scripts)
- Fixed `scripts/analysis/feature_interaction_explorer.py` framework reference

### Documentation Created

**Comprehensive User Manual**: `docs/USER_MANUAL.md`
- Complete system architecture with data flow diagrams
- Step-by-step guides for every feature
- Quick start guide (5 minutes to first prediction)
- Troubleshooting procedures
- Custom model integration examples

**Detailed Procedures Guide**: `docs/PROCEDURES_DETAILED.md`
- 25 detailed procedures covering:
  - Data ingestion (ESPN, MLB, Retrosheet)
  - Warehouse rebuild (full, quick, resume)
  - Feature engineering
  - Model training (binary & multiclass)
  - Inference (historical & live)
  - Analysis tools
  - Maintenance & troubleshooting

**Workflow Validation Report**: `docs/WORKFLOW_VALIDATION_REPORT.md`
- Complete infrastructure audit
- Architecture diagrams (PlantUML)
- Gap analysis
- Revised integration plan

**Architecture Diagrams**:
- `docs/diagrams/WORKFLOW_ARCHITECTURE.puml` - Full data flow
- `docs/diagrams/INTEGRATION_LAYER.puml` - Proposed Python integration

### Key Insight

The warehouse is **85% complete and working**. What's needed:
1. ✅ Thin Python integration layer (wrappers, not new infrastructure)
2. ❌ NOT redundant SQL schemas

### Updated FILE_INVENTORY.md

Added entries for:
- `sql/warehouse/004_batch_operations.sql`
- `sql/analysis/001_feature_importance.sql`
- `sql/framework/001_framework_schema_DEPRECATED.sql`

---

## 2026-04-24 (Reproducibility Mandate - CRITICAL)

### Problem Identified
User identified critical gap: we have NOT been following proper reproducibility standards. No paper trail exists for much of our work, making it impossible for other researchers to reproduce our analysis.

### Changes Made

#### 1. AGENTS.md Updated
- Added **REPRODUCIBILITY MANDATE (CRITICAL)** section
- SQL-First Development Rule: ALL database operations must be in version-controlled .sql files
- Script Wrapper Requirement: All pipelines must have orchestrator scripts
- Documentation Requirements: Every SQL file must have header comments, every table/column must have COMMENT ON
- The Paper Trail Checklist: 8-point checklist before completing ANY task
- Scientific Reproducibility Standard: Every number must be traceable to source/transformation/model/evaluation
- Never Again List: Explicit prohibitions (no ad-hoc SQL, no direct DB changes, etc.)

#### 2. Audit Prompt Created
- Created `docs/agents/REPRODUCIBILITY_AUDIT_PROMPT.md`
- Comprehensive 4-phase audit plan for another agent to execute:
  - Phase 1: Audit Current State (inventory SQL, scripts, table comments)
  - Phase 2: Fix Documentation Gaps (add headers, comments, wrapper scripts)
  - Phase 3: Create Missing Documentation (Table Dictionary, Data Lineage)
  - Phase 4: Validation & Verification

### Deliverables for Follow-up Agent
- Must document all SQL files with headers
- Must add COMMENT ON for all tables/columns
- Must create wrapper scripts for all pipelines
- Must create docs/TABLE_DICTIONARY.md
- Must create docs/DATA_LINEAGE.md
- Must update FILE_INVENTORY.md and PROCEDURES.md

### Git Commit
- Commit message: "Add REPRODUCIBILITY MANDATE to AGENTS.md and create comprehensive audit prompt"

#### 3. E2E Testing Infrastructure Created
- Created `sql/test/001_create_test_schema.sql` - Test schema setup with test.runs tracking table
- Created `sql/test/002_test_fixtures.sql` - Test data fixtures (100 games from 2024)
- Created `scripts/test/e2e_test_runner.sh` - Main E2E test runner (executable)
- Created `scripts/test/validate_sql_files.sh` - SQL file header validation (executable)
- Created `scripts/test/verify_rebuild.sh` - Warehouse rebuild verification (executable)

**Test Infrastructure Features:**
- Free local setup - uses existing PostgreSQL instance (no Docker, no cloud)
- Test schema `test` isolated from production data
- Small test fixtures for fast execution (100 games vs 62,000)
- Automated validation of SQL headers, table comments, row counts
- AI Agent Gap-Fill Loop: Run tests → find gaps → create missing files → re-run

**Usage:**
```bash
./scripts/test/validate_sql_files.sh      # 5 minutes - check headers
./scripts/test/e2e_test_runner.sh --quick # 10 minutes - full suite
./scripts/test/verify_rebuild.sh           # 30 minutes - full rebuild
```

#### 4. Warehouse Orchestration System Created (PostgreSQL Procedures)
Following user's preference for database-native orchestration:

**SQL Files Created:**
| File | Purpose |
|------|---------|
| `sql/warehouse/001_warehouse_schema.sql` | Orchestration schema: `warehouse.rebuild_runs`, `warehouse.rebuild_log`, helper functions |
| `sql/warehouse/002_phase_procedures.sql` | 5 phase procedures: raw_load, core_build, bridge_sync, feature_build, model_prep |
| `sql/warehouse/003_rebuild_orchestrator.sql` | Main `warehouse.rebuild(mode, seasons)` procedure with per-phase commits |

**Architecture:**
- **Hybrid approach**: Bash wrapper discovers environment, PostgreSQL handles orchestration
- **Per-phase commits**: Allows resume from failure (raw → core → bridge → features → models)
- **Table-based logging**: `warehouse.rebuild_log` survives RAISE NOTICE for audit trail
- **Resumable**: `warehouse.get_last_successful_phase()` for resume mode

**Bash Wrapper Updated:**
- `scripts/rebuild_warehouse.sh` now calls `warehouse.rebuild()` procedure
- New CLI: `--mode full|resume|quick`, `--seasons YYYY,YYYY`, `--legacy` for old behavior
- Runs E2E tests first, loads warehouse schema, executes procedure, reports results

**Usage:**
```bash
./scripts/rebuild_warehouse.sh --mode quick                    # Skip expensive phases
./scripts/rebuild_warehouse.sh --mode full --seasons 2024,2025  # Specific seasons
./scripts/rebuild_warehouse.sh --resume                        # Resume from failure
./scripts/rebuild_warehouse.sh --legacy                      # Old Python-based approach
```

#### 5. Updated REPRODUCIBILITY_AUDIT_PROMPT.md
- Added Phase 4: E2E Testing Environment Setup (2 hours)
- Added CRITICAL REQUIREMENT clause requiring creation of scripts/SQL files
- Added E2E Testing Environment FAQ section
- Added AI Agent Gap-Fill Procedure section with explicit loop
- Updated deliverables checklist with E2E requirements

#### 6. Updated AGENTS.md
- Added E2E testing to Paper Trail Checklist
- Added E2E Testing Environment section with free local setup instructions
- Documented AI Agent Gap-Fill Loop

## 2026-04-23 (Sabermetrics Knowledge Base Expansion)

### Ingested Research
- Massively expanded `docs/KNOWLEDGE_BASE_SABERMETRICS.md` with 7 extracted PDFs + 3 fetched web resources
- Created `docs/SABERMETRICS_LINK_INVENTORY.md` tracking 40+ research links with status

### Papers Extracted
| Paper | Source | Key Finding |
|-------|--------|-------------|
| Jim Albert - Sabermetrics Overview | ASA 2010 | OPS explains 89% run variance; DICE formula; PITCHf/x applications |
| Pavitt - Bibliography Explainer | Retrosheet | 4,153-entry taxonomy with 19 macrocode categories |
| Tobin - Steroids Physics | AJP 2008 | 10% muscle → 50-100% HR increase; HRBiP analysis |
| Beneventano et al. - Run Production | IJBHT 2012 | Runs model R²=95.3% (wOBA+K%+SLG+OBP); ERA model R²=98.8% |
| Gopal et al. - Baseball MDP/RL | SMU 2024 | Feedforward NN 58% pitch outcome accuracy; RE288 framework |
| CMU - Neural Sabermetrics LLM | arXiv 2026 | Llama-3.2 3B world model; 63.7% pitch type, 76.6% swing IZ accuracy |
| Birnbaum - Book Review | BTN 2006 | Leverage index optimal closer usage; clutch hitting ≈0.008 OBP SD |

### Web Resources Fetched
- Swing Probability (Towards Data Science): LightGBM 80.5% accuracy
- Retrosheet Fall 2025 Updates: 2025 season, 1910 deduced, 1935 Negro Leagues
- Retrosheet DB Tutorial: MySQL schema guidance
- CareerKarma Sabermetrics Courses: Training resource catalog
- Syracuse Grad Program Blog: Analytics education overview

### Additional Sources Fetched (2026-04-23 Extended Session)
| Source | Type | Size | Status |
|--------|------|------|--------|
| Practicing Sabermetrics (Costa, Huber, Saccoman) | Book PDF | 14,227 lines / 2.5MB | **Extracted** → `docs/kb/sources/books/` |
| FanGraphs Sabermetrics Library | Reference | 21,469 chars | **Fetched** → `docs/kb/sources/reference/` |
| SABR Guide to Sabermetric Research | Reference | 6,710 chars | **Fetched** → `docs/kb/sources/reference/` |
| PMC - Current State of Baseball Analytics | Review Paper | 45,401 chars | **Fetched** → `docs/kb/sources/papers/` |
| SABR - Tobin Steroids Review (Nathan) | Article | 10,870 chars | **Fetched** → `docs/kb/sources/articles/` |
| SABR - PEDs and Career Length (Gordon) | Article | 31,149 chars | **Fetched** → `docs/kb/sources/articles/` |

### Blocked Sources (Documented)
- MDPI journals: Akamai/EdgeSuite access denied (3 papers)
- Beyond the Box Score: Fastly domain error (site dead)
- Reddit r/Sabermetrics: JS-required/bot detection
- Hilaris Publisher steroid PDF: Returns HTML instead of PDF
- Scribd: Paywall blocked Birnbaum guide

### Pavitt Bibliography Loaded
- **4,153 entries** from `https://www.retrosheet.org/resources/BBREF.xls`
- Top categories: WAR (88), Run Differentials (73), Postseasons (67), Home Advantage (67)
- Covers journals: Baseball Analyst, Baseball Research Journal, JQAS, JoSE, etc.
- Journals span 1982-2025 research

### KB File Updated
- `docs/KNOWLEDGE_BASE_SABERMETRICS.md`: Added sections on Advanced Research Findings, Retrosheet Bibliography, Source Documents
- New metrics documented: DICE, RF/9, xWOBA, RE288, leverage index
- New modeling approaches: Swing probability (LightGBM), Pitch outcome prediction (Feedforward NN), LLM world models (Llama-3.2)

---

## 2026-04-12 (Team/Park Bridge Repair And Live Priors Activation)

### Built

- Extended `scripts/populate_bridge_tables.py` so it now populates:
  - `bridge.player_xref`
  - `bridge.team_xref`
  - `bridge.park_xref`
- Added `scripts/replay_live_bridge_backfill.py` so stored latest-successful MLB raw snapshots can be replayed through the repaired transform path in a controlled, additive way.
- Added canonical MLB abbreviation-to-Retrosheet team mapping for the active seasonless `bridge.team_xref` schema.
- Added canonical MLB venue-id-to-Retrosheet park mapping for MLB venues observed across `2000-2025`.
- Updated `sql/122_live_pa_feature_parity.sql` so live parity rows can now join:
  - `features.park_prior_season_run_environment`
  - `features.team_rolling_30_game_summary`

### Validation

- Syntax validation:
  - `python3 -m py_compile scripts/populate_bridge_tables.py`
- Bridge population run succeeded:
  - `python3 scripts/populate_bridge_tables.py`
- Updated bridge counts:
  - `bridge.team_xref`: `30 / 292` rows now have `mlb_team_id`
  - `bridge.park_xref`: `45 / 656` rows now have `mlb_venue_id`
- The only currently unmapped MLB venue id surfaced by the script is:
  - `2529 | Sutter Health Park`
- Spot-check after re-transform:
  - `python3 scripts/transform_live_game.py --game-pk 599374`
  - canonical row now lands as:
    - `game_id = WAS201910260`
    - `home_team_id = WAS`
    - `away_team_id = HOU`
    - `park_id = WAS11`
- Replay utility smoke test:
  - `python3 -m py_compile scripts/replay_live_bridge_backfill.py`
  - `python3 scripts/replay_live_bridge_backfill.py --season-from 2019 --season-to 2019 --limit 1`
  - selected `1` stored game and replayed `game_pk 564721 -> ANA201903010`
- Live parity reapply succeeded:
  - `psql -h localhost -p 5432 -d retrosheet -v ON_ERROR_STOP=1 -f sql/122_live_pa_feature_parity.sql`
- Spot-check of the repaired live parity row for `WAS201910260` now shows:
  - `park_prior_total_runs_per_game = 9.585`
  - `batting_team_rolling_30_win_rate = 0.6667`
  - `fielding_team_rolling_30_win_rate = 0.7333`

### Limitation

- `bridge.team_xref` is still seasonless.
- That means franchise-move/name-change MLB ids are currently mapped to one current/canonical Retrosheet team id for live scoring:
  - `MON/WSH -> WAS`
  - `FLA/MIA -> MIA`
  - `ATH/OAK -> OAK`
- The current park crosswalk intentionally covers the observed regular-season MLB venue surface from `2000-2025`; spring-training or other non-regular-season venues may still remain as `MLB###` fallback park ids after replay.
- This is acceptable for the current live-scoring objective, but it is not a complete historical MLB-team reconciliation design for replaying all `2000-2025` raw MLB feeds.
- Most existing `core.live_*` rows were transformed before the bridge repair, so overall live-parity counts for park/team priors remain near zero until those stored snapshots are replayed through the repaired transform path.

### Decision

- Team/park bridge repair is now good enough to unblock the next live step.
- The next live-data task is a controlled replay/backfill of stored `raw_mlb.live_feed_snapshots` into `core.live_*` so the repaired bridge and the new park/team live priors apply broadly instead of only to newly transformed games.

## 2026-04-12 (First Live `advanced_count` Parity View And Scorer)

### Built

- Added `sql/122_live_pa_feature_parity.sql` to create `features.live_plate_appearance_advanced_count_examples`.
- Added `scripts/predict_live_pa_outcome_distribution.py` so stored live MLB plate appearances can be scored with the registered `advanced_count` PA model and optional isotonic calibration artifact.
- Updated `scripts/rebuild_warehouse.sh` so the canonical rebuild now applies `sql/122_live_pa_feature_parity.sql`.

### Validation

- Applied:
  - `psql -h localhost -p 5432 -d retrosheet -v ON_ERROR_STOP=1 -f sql/122_live_pa_feature_parity.sql`
- Syntax validation:
  - `python3 -m py_compile scripts/predict_live_pa_outcome_distribution.py`
- Live parity coverage:
  - `features.live_plate_appearance_advanced_count_examples`: `5,172,187` live PA rows
  - with batter career priors: `4,568,784`
  - with pitcher career priors: `4,425,839`
  - with batter count-state priors: `3,169,510`
  - with pitcher count-state priors: `3,017,181`
- Live calibrated scoring succeeded:
  - `python3 scripts/predict_live_pa_outcome_distribution.py --game-id MLB117201910300 --plate-appearance-id 79 --model-version 20260412T045759Z --apply-calibration`
- Example live scoring result:
  - event text: `Michael Brantley strikes out swinging.`
  - raw `P(strikeout)`: `0.1652`
  - calibrated `P(strikeout)`: `0.1307`
  - calibrated `P(walk)`: `0.3262`

### Limitation

- The live parity view currently leaves these features nullable:
  - park prior environment
  - batting-team rolling form
  - fielding-team rolling form
- That is intentional for now because `bridge.team_xref.mlb_team_id` and `bridge.park_xref.mlb_venue_id` are still unpopulated in the active database.

### Decision

- The historical best PA model can now score stored live MLB plate appearances through a documented additive live parity layer.
- The next live-data task is bridge completion for team/park/game reconciliation so the remaining null live priors can be filled instead of imputed.

## 2026-04-12 (Count-State Feature Marts For PA Reliability)

### Built

- Added `sql/082_count_state_feature_marts.sql` to create:
  - `features.batter_count_state_prior_pa_summary`
  - `features.pitcher_count_state_prior_pa_summary`
  - `features.pa_count_state_context_prior_season_rates`
  - `features.plate_appearance_count_state_advanced_examples`
  - `features.count_state_feature_mart_validation_summary`
- Extended `scripts/train_pa_outcome_distribution.py` with `--feature-set advanced_count`.
- Extended `scripts/predict_pa_outcome_distribution.py` so the scorer can load rows from the count-state-enhanced advanced PA view.
- Extended `scripts/analyze_pa_outcome_calibration.py` so the evaluation path supports the new feature set.
- Updated `scripts/rebuild_warehouse.sh` so the canonical rebuild now applies `sql/082_count_state_feature_marts.sql`.

### Validation

- Applied:
  - `psql -h localhost -p 5432 -d retrosheet -v ON_ERROR_STOP=1 -f sql/082_count_state_feature_marts.sql`
- Validation summary:
  - `features.batter_count_state_prior_pa_summary`: `214,174`
  - `features.pitcher_count_state_prior_pa_summary`: `207,345`
  - `features.pa_count_state_context_prior_season_rates`: `44,327`
  - `features.plate_appearance_count_state_advanced_examples`: `4,779,662`
- Grouped 5% benchmark:
  - `python3 scripts/train_pa_outcome_distribution.py --feature-set advanced_count --target-taxonomy grouped --sample-rate 0.05 --train-through 2022 --no-activate`
  - HGB validation metrics:
    - log loss `1.5089213670264499`
    - Brier `0.7145995102201933`
    - accuracy `0.41305275131522823`
    - top-3 accuracy `0.8202402957486137`
- Subgroup reliability improvements versus the earlier grouped advanced baseline:
  - `0-2` top-probability gap: `0.0449` -> `0.0351`
  - `1-2` top-probability gap: `0.0405` -> `0.0341`
  - `2-2` top-probability gap: `0.0438` -> `0.0386`
- Raw class-level improvement:
  - strikeout ECE: about `0.0181` -> `0.0152`
- Registered calibration artifact for the new model version:
  - `20260412T045759Z_isotonic_artifact`
  - `data/models/calibration/pa_outcome_distribution/20260412T045759Z_isotonic_artifact.joblib`
  - held-out `2025` calibrated log loss `1.5049255969621713`

### Decision

- Count-state prior features are a useful additive improvement. They improve the targeted two-strike reliability problem and slightly improve the grouped HGB objective.
- The current best research direction is now:
  - grouped HGB
  - count-state-enhanced advanced features
  - reusable isotonic calibration artifact

## 2026-04-12 (Reusable Calibration Artifacts And Calibrated Scoring)

### Built

- Added `sql/081_probability_calibration_artifacts.sql` to extend `predictions.calibration_reports` with `artifact_uri` and refresh the recent-report view.
- Added `scripts/register_pa_outcome_calibration.py` to fit, persist, and register reusable isotonic calibration artifacts for `pa_outcome_distribution`.
- Extended `scripts/predict_pa_outcome_distribution.py` to support:
  - `--apply-calibration`
  - `--calibration-report-name`
- Extended `baseball-chatbot-ui/app/api/predict/route.ts` to pass optional calibrated-scoring controls through to the Python scorer.
- Updated `scripts/rebuild_warehouse.sh` so the canonical rebuild now applies `sql/081_probability_calibration_artifacts.sql`.

### Validation

- Applied:
  - `psql -h localhost -p 5432 -d retrosheet -v ON_ERROR_STOP=1 -f sql/081_probability_calibration_artifacts.sql`
- Syntax validation:
  - `python3 -m py_compile scripts/register_pa_outcome_calibration.py scripts/predict_pa_outcome_distribution.py`
- Registered one real isotonic calibration artifact:
  - `python3 scripts/register_pa_outcome_calibration.py --model-name hist_gradient_boosting_multiclass --model-version 20260411T230512Z --notes 'first persisted isotonic calibration artifact'`
- Registration result:
  - `artifact_uri = data/models/calibration/pa_outcome_distribution/20260411T230512Z_isotonic_artifact.joblib`
  - `predictions.prediction_runs.prediction_run_id = 2`
  - `predictions.calibration_reports.report_name = 20260411T230512Z_isotonic_artifact`
- Calibrated scoring now works:
  - `python3 scripts/predict_pa_outcome_distribution.py --game-id ANA202506060 --plate-appearance-id 30 --model-version 20260411T230512Z --apply-calibration`
- Example calibrated PA result:
  - actual outcome: `walk`
  - raw `P(walk)`: `0.4613`
  - calibrated `P(walk)`: `0.4260`

### Decision

- Calibrated scoring is no longer only a read-only experiment. The project now has a reusable calibration-artifact path that can be loaded at inference time without changing the underlying registered base model.
- The next question is policy, not mechanics: whether calibrated scoring should become the default served path for historical and later live inference.

## 2026-04-12 (Durable Probability Evaluation Reports)

### Built

- Added `sql/079_probability_evaluation_reports.sql` to create:
  - `predictions.calibration_reports`
  - `predictions.bootstrap_reports`
  - `predictions.recent_calibration_reports`
  - `predictions.recent_bootstrap_reports`
- Added `scripts/persist_pa_outcome_reports.py` to persist canonical PA outcome evaluation artifacts for a registered model version.
- Updated `scripts/rebuild_warehouse.sh` so the canonical rebuild now applies:
  - `sql/075_interface_workflows.sql`
  - `sql/079_probability_evaluation_reports.sql`

### Validation

- Applied:
  - `psql -h localhost -p 5432 -d retrosheet -v ON_ERROR_STOP=1 -f sql/079_probability_evaluation_reports.sql`
- Syntax validation:
  - `python3 -m py_compile scripts/persist_pa_outcome_reports.py`
- Persisted one real evaluation-report run:
  - `python3 scripts/persist_pa_outcome_reports.py --model-name hist_gradient_boosting_multiclass --model-version 20260411T230512Z --bootstrap-replicates 20 --notes 'initial durable evaluation report persistence'`
- Stored artifacts created successfully:
  - `predictions.prediction_runs.prediction_run_id = 1`
  - one raw validation calibration report
  - one held-out isotonic calibration report
  - one bootstrap summary report

### Decision

- Calibration and bootstrap evidence are now durable warehouse artifacts tied to a registered model version and prediction run.
- The next modeling decision is whether calibrated probabilities themselves should become first-class registered prediction artifacts rather than remaining evaluation-only outputs.

## 2026-04-12 (Current Snapshot And Handoff Docs)

### Built

- Added `docs/agents/CURRENT_SNAPSHOT.md` as the shortest durable handoff document for:
  - canonical architecture
  - current warehouse status
  - current best historical PA model
  - calibration status
  - active blockers
  - compute notes
  - recommended next move
- Updated:
  - `AGENTS.md`
  - `docs/agents/README.md`
  - `docs/agents/FILE_INVENTORY.md`
  - `docs/agents/PROCEDURES.md`
- The procedures now explicitly define a resume flow after context loss and point agents at `CURRENT_SNAPSHOT.md` first.

### Decision

- The project now has a dedicated handoff layer separate from the longer historical log and the manuscript.
- Another agent should be able to recover project state from:
  1. `docs/agents/CURRENT_SNAPSHOT.md`
  2. `docs/PROJECT_LOG.md`
  3. `docs/agents/MODELING_WORKFLOWS.md`
  4. the linked GitHub issues

### Next

1. Mirror the same state into the active GitHub issues.
2. Optimize the bootstrap evaluator before treating bootstrap uncertainty as a standard workflow.
3. Continue with calibrated-output handling and live feature parity after the bootstrap/reporting layer is stable.

## 2026-04-12 (Optimized Bootstrap Evaluation)

### Built

- Reworked `scripts/bootstrap_pa_outcome_evaluation.py` to use season-stratified cluster bootstrap with cached per-game sufficient statistics instead of row-level metric recomputation on every replicate.
- Cached per-game bootstrap contributions now include:
  - row count
  - summed log-loss contribution
  - summed multiclass Brier contribution
  - exact-correct count
  - top-3-correct count
  - confusion matrix

### Validation

- Smoke validation:
  - `python3 -m py_compile scripts/bootstrap_pa_outcome_evaluation.py`
  - 10-replicate run finished successfully in about `1:08.90`
- Full validation:
  - `python3 scripts/bootstrap_pa_outcome_evaluation.py --model-name hist_gradient_boosting_multiclass --model-version 20260411T230512Z --replicates 50 --output-json data/reports/pa_outcome_bootstrap_20260411T230512Z.json`
- 50-replicate season-stratified game-cluster bootstrap summary for the winning grouped advanced HGB model:
  - log loss mean `1.5126657511688808`, p05 `1.5108156698991362`, p95 `1.5155488052002872`
  - multiclass Brier mean `0.7147813509752445`, p05 `0.7137519854821855`, p95 `0.7156254209444188`
  - accuracy mean `0.41377036716524146`, p05 `0.41249056512030724`, p95 `0.4150872475294815`
  - macro F1 mean `0.17791156672767003`, p05 `0.17688164429547665`, p95 `0.17868857715135572`
  - weighted F1 mean `0.3252916679974539`, p05 `0.3240275273391974`, p95 `0.32660157389683137`
  - top-3 accuracy mean `0.8187160954493463`, p05 `0.8175555438624159`, p95 `0.8196167974638292`

### Decision

- Bootstrap uncertainty evaluation is now operational for the historical grouped PA baseline.
- The current grouped advanced HGB model appears reasonably stable under dependence-aware season-stratified game-cluster resampling.
- The next step is no longer “make bootstrap work.” It is “decide how bootstrap summaries and calibrated outputs should be stored and surfaced.”

## 2026-04-11 (Grouped PA Trainer Support)

### Built

- Extended `scripts/train_pa_outcome_distribution.py` to support:
  - `--target-taxonomy granular`
  - `--target-taxonomy grouped`
- The trainer now reads from:
  - `features.plate_appearance_outcome_examples` for granular training
  - `features.plate_appearance_outcome_grouped_examples` for grouped training
- Updated modeling workflow and procedure docs to show the grouped baseline training path.

### Decision

- Grouped and granular PA outcome training should stay in the same trainer so model registration, temporal-policy controls, and evaluation remain consistent.

### Next

1. Validate the trainer with a grouped-taxonomy smoke run.
2. Compare grouped `basic` versus `advanced` benchmarks.
3. Use grouped-model diagnostics to decide whether the first promoted PA distribution model should remain grouped or move back to granular classes.

## 2026-04-11 (MLB Historical Raw Acquisition Complete)

### Built

- Completed the canonical historical MLB raw backfill across the project target range `2000-2025`.
- Restarted the bulk historical downloader with the idempotent downloader logic and faster settings:
  - `--workers 8`
  - `--delay 0.25`
- Verified full historical season coverage in `raw_mlb.live_feed_snapshots`.

### Validation

- `raw_mlb.schedule_snapshots`: `9,286`
- `raw_mlb.live_feed_snapshots`: `72,199`
- `raw_mlb.live_feed_snapshots` with `http_status = 200`: `72,184`
- `raw_mlb.reference_snapshots`: `2,405`
- `core.live_games`: `67,913`
- `core.live_events`: `5,172,275`
- Successful live-feed season coverage now spans every season from `2000` through `2025` with zero missing seasons.
- Reference endpoint coverage spans all `26` seasons from `2000-2025`.

### Residual Issues

- There are `7` distinct `game_pk` values with no successful raw live-feed snapshot after targeted retry:
  - `243297`
  - `243298`
  - `243313`
  - `243314`
  - `308207`
  - `764834`
  - `764836`
- A targeted retry through the canonical fetch path on `2026-04-11` confirmed that all `7` still return MLB API `HTTP 500` with a JSON error body:
  - `{"messageNumber":1,"message":"Internal error occurred", ...}`
- Schedule metadata shows that all `7` unresolved games are `gameType = 'E'` exhibition/special-event games:
  - four Tokyo Dome exhibition games in `2004`
  - one exhibition game in `2011`
  - two Gocheok Sky Dome exhibition games in `2024`
- These should therefore be treated as upstream MLB API exhibition-game exceptions rather than uncertain regular-season data gaps.

### Decision

- The historical MLB raw acquisition layer is complete for practical modeling purposes.
- The unresolved set should be tracked as a small exception list rather than blocking downstream warehouse and modeling work.

### Next

1. Log the unresolved `game_pk` exceptions in GitHub and the runbook.
2. Move back to bridge reconciliation, live feature parity, and PA outcome modeling on top of the now-complete historical raw MLB layer.

## 2026-04-11 (Idempotent MLB Raw Acquisition)

### Built

- Updated `scripts/download_mlb_bulk.py` so successful raw MLB schedule and game-feed inserts are logically idempotent on rerun.
- Updated `scripts/fetch_mlb_reference_data.py` so successful raw MLB reference endpoint inserts are logically idempotent on rerun.

### Decision

- The canonical raw acquisition rule is now:
  - preserve source rows
  - allow append-only history
  - but do not append another successful row once a successful snapshot already exists for the same logical resource
- Logical resource keys are:
  - schedules: `snapshot_date`
  - game feeds: `game_pk`
  - reference snapshots: `endpoint_family + resource_key + season`

### Next

1. Validate the patched downloaders with syntax checks and targeted rerun behavior.
2. If needed, stop and restart the bulk downloader with faster settings now that successful reruns are idempotent.

## 2026-04-11 (Grouped PA Outcome Infrastructure)

### Built

- Added `sql/078_plate_appearance_outcome_grouped.sql` as the additive grouped target layer for baseline PA modeling.
- Created:
  - `features.plate_appearance_outcome_grouped_examples`
  - `features.plate_appearance_outcome_grouped_validation_summary`
- The grouped taxonomy preserves the existing granular canonical outcome rows while exposing a more stable first-pass modeling target:
  - `single`
  - `double`
  - `triple`
  - `home_run`
  - `walk`
  - `hit_by_pitch`
  - `strikeout`
  - `ground_out`
  - `air_or_other_out`
  - `reach_on_error_or_fc`
  - `productive_out`
  - `other_rare`

### Decision

- The grouped PA layer is the correct next additive modeling object because it improves target stability without replacing the granular canonical PA outcome layer.
- This should be the first target layer used for baseline direct multiclass PA benchmarks.

### Next

1. Apply `sql/078_plate_appearance_outcome_grouped.sql` and validate grouped class counts.
2. Extend the PA trainer to support grouped-taxonomy training directly.
3. Benchmark grouped `basic` versus `advanced` models under the existing temporal-policy controls.

## 2026-04-11 (Canonical MLB Backfill Status Utility)

### Built

- Added `scripts/raw_mlb_backfill_status.py` as the canonical read-only status utility for the ongoing MLB raw backfill.
- The script reports:
  - `raw_mlb.schedule_snapshots`
  - `raw_mlb.live_feed_snapshots`
  - `raw_mlb.reference_snapshots`
  - `core.live_games`
  - `core.live_events`
  - live-feed coverage by season
  - reference coverage by endpoint family
- Updated `docs/agents/FILE_INVENTORY.md` and `docs/agents/PROCEDURES.md` so contributors have one canonical way to monitor download progress without depending on the experimental EdgeForge scripts.

### Decision

- The raw MLB backfill should be monitored through a canonical read-only script that only depends on the current documented warehouse layers.
- Experimental monitoring scripts tied to `mlb_enhanced` or other non-canonical schemas remain outside the main runbook.

### Next

1. Let the current 2000-2025 backfills finish.
2. Use `scripts/raw_mlb_backfill_status.py` for the completion audit.
3. Continue with additive warehouse/modeling infrastructure only after the raw acquisition baseline is settled.

## 2026-04-11 (Baseline PA Modeling Specification)

### Built

- Added `docs/PA_BASELINE_MODEL_SPEC.md` as the implementation-grade baseline design for the plate appearance probability engine.
- Converted the broader at-bat modeling discussion into a concrete v1 plan:
  - preserve the current granular canonical outcome taxonomy
  - train the first operational model on a grouped multiclass taxonomy
  - keep feature engineering in PostgreSQL and model training in the existing Python stack
  - defer pitch-level recursive simulation and third-source pitch enrichments until after the direct PA model is stable

### Validation

- Confirmed `features.plate_appearance_outcome_examples` spans `2000-2025` with `4,779,662` rows.
- Confirmed exact join coverage from `features.plate_appearance_outcome_examples` to `features.plate_appearance_advanced_examples`: `4,779,662`.
- Confirmed coverage in the current PA outcome layer:
  - pitch sequence: `4,779,662 / 4,779,662`
  - batted-ball type: `3,372,283 / 4,779,662`
  - batted-ball location: `3,277,405 / 4,779,662`
- Recomputed current raw class counts from the warehouse and used those counts to define the grouped v1 modeling taxonomy.

### Decision

- The first production-style PA model should remain a direct multiclass model, not a recursive pitch model.
- The first operational taxonomy should group the sparsest terminal classes for calibration stability while preserving the raw canonical classes in the warehouse.
- The next additive SQL object should be a grouped training layer under `features`, not a rewrite of the current raw outcome layer.

### Next

1. Add `features.plate_appearance_outcome_grouped_examples`.
2. Extend the PA trainer to support grouped-taxonomy training directly.
3. Run grouped `basic` versus `advanced` benchmarks with temporal-policy variants.

## 2026-04-11 (Typed MLB Reference Views)

### Built

- Added `sql/095_mlb_reference_views.sql` as the canonical typed transform layer over `raw_mlb.reference_snapshots`.
- Created `core` views for the main MLB reference families:
  - `core.mlb_api_teams`
  - `core.mlb_api_team_rosters`
  - `core.mlb_api_players`
  - `core.mlb_api_venues`
  - `core.mlb_api_standings`
- Updated `scripts/rebuild_warehouse.sh` so the typed MLB reference layer is part of the canonical rebuild path.
- Updated the agent inventory and procedures so contributors know the raw-to-typed MLB reference workflow.

### Validation

- Applied `sql/095_mlb_reference_views.sql` successfully to the local `retrosheet` database.
- Current typed row counts from the stored 2025 reference backfill:
  - `core.mlb_api_teams`: `30`
  - `core.mlb_api_team_rosters`: `1,691`
  - `core.mlb_api_players`: `1,470`
  - `core.mlb_api_venues`: `30`
  - `core.mlb_api_standings`: `0`
- Verified that the zero-row standings result is caused by the current raw snapshot payload containing `records: []`, not by a SQL parsing error.

### Decision

- The canonical MLB reference workflow is now:
  - fetch source-preserved endpoint payloads into `raw_mlb.reference_snapshots`
  - build typed `core.mlb_api_*` views from the latest successful snapshots
  - keep bridge/reconciliation and downstream enrichment out of the raw schema
- Empty MLB standings snapshots are acceptable raw outcomes and should be preserved as-is until a richer standings acquisition strategy is explicitly adopted.

### Next

1. Use the typed MLB reference views to improve `bridge` reconciliation and MLB-to-Retrosheet entity linking.
2. Decide whether standings need broader endpoint coverage or alternate query parameters for better historical completeness.
3. Continue with the temporal sweep and live feature-parity work once the reference path is stable.

## 2026-04-11 (Expanded MLB Source Coverage)

### Built

- Extended the canonical raw MLB schema so source preservation is no longer limited to live game feeds.
- Updated `sql/090_mlb_live_data.sql` so `raw_mlb.schedule_snapshots` is part of the canonical raw schema, not just an incidental table from older work.
- Added `sql/091_mlb_reference_raw.sql` creating `raw_mlb.reference_snapshots` for source-preserved MLB reference endpoint payloads.
- Added `scripts/fetch_mlb_reference_data.py` as the canonical fetcher for the main non-game MLB endpoint families:
  - `teams`
  - `rosters`
  - `people`
  - `venues`
  - `standings`
- Updated rebuild/docs/procedures so the broad MLB source-coverage policy is explicit.

### Validation

- `python3 -m py_compile scripts/fetch_mlb_reference_data.py` passed.
- `python3 scripts/fetch_mlb_reference_data.py --help` passed.
- Reapplied:
  - `sql/090_mlb_live_data.sql`
  - `sql/091_mlb_reference_raw.sql`
- Confirmed canonical raw MLB tables now include:
  - `raw_mlb.schedule_snapshots`
  - `raw_mlb.live_feed_snapshots`
  - `raw_mlb.reference_snapshots`

### Decision

- For project purposes, “download all MLB source data” now means preserving the full required MLB source families for modeling and reconciliation:
  - schedules
  - live game feeds
  - teams
  - rosters
  - people
  - venues
  - standings
- This is the canonical MLB raw coverage scope until an explicit architecture change expands it further.

### Next

1. Use `scripts/fetch_mlb_reference_data.py` to backfill the reference endpoint families across the target season range.
2. Define the canonical typed transform path from `raw_mlb.reference_snapshots` into bridge/core/reference layers.
3. Continue with the temporal sweep and live feature-parity work after the source-preservation layer is settled.

## 2026-04-11 (Canonical Historical MLB Backfill)

### Built

- Promoted `scripts/download_mlb_bulk.py` to the canonical historical MLB raw backfill utility.
- Updated the script to match the raw-ingestion provenance standard:
  - store `payload_checksum` for successful game-feed fetches
  - persist failed game-feed fetch attempts into `raw_mlb.live_feed_snapshots`
  - preserve request/status/error metadata consistently
- Updated `README.md`, `docs/agents/PROCEDURES.md`, `docs/agents/FILE_INVENTORY.md`, and `docs/EDGEFORGE_TRIAGE.md` to reflect that decision.

### Validation

- `python3 -m py_compile scripts/download_mlb_bulk.py` passed.
- `python3 scripts/download_mlb_bulk.py --help` passed.
- Confirmed the script writes to the canonical raw tables:
  - `raw_mlb.schedule_snapshots`
  - `raw_mlb.live_feed_snapshots`
- Confirmed the active raw schema includes:
  - request params
  - HTTP status
  - response time
  - error text
  - payload checksum
  - game date / season on game feeds

### Decision

- `scripts/download_mlb_bulk.py` is now the official historical MLB raw backfill path.
- Historical MLB raw acquisition should feed the same canonical downstream transform path used by the rest of the project.
- The remaining EdgeForge / MLB-enhanced scripts still remain experimental unless explicitly merged into canonical layers.

### Next

1. Decide the canonical follow-on transform/backfill procedure after raw MLB bulk download.
2. Extract useful MLB-enhanced feature ideas into one canonical design path.
3. Run the formal temporal sweep for `pa_outcome_distribution`.

## 2026-04-11 (EdgeForge Triage)

### Built

- Reviewed the newly appeared `EdgeForge` / MLB-enhanced files against the documented warehouse architecture.
- Added `docs/EDGEFORGE_TRIAGE.md` as the durable classification note for those files.
- Updated `AGENTS.md`, `README.md`, and `docs/agents/*` to make the architectural rule explicit:
  - `EdgeForge` / `mlb_features` / `mlb_models` / `mlb_enhanced` files remain experimental until explicitly merged into the canonical warehouse layers.

### Decision

- Keep a single canonical warehouse path:
  - `raw_retrosheet -> core -> features`
  - `raw_mlb -> bridge -> core.live_* -> analysis/features`
- Do not adopt a second parallel stack built around:
  - `mlb_features`
  - `mlb_models`
  - `mlb_enhanced`
- Treat `docs/agents/EdgeForge.agent.md` as a product-direction note, not as a source-of-truth architecture document.
- Mine the experimental files for useful ideas, but rewrite those ideas into canonical schemas and workflows instead of promoting the prototypes directly.

### Validation

- Confirmed that the untracked file set includes:
  - product-direction docs
  - experimental MLB bulk-ingestion scripts
  - experimental feature-engineering and training scripts
  - dashboard/alert/status prototypes
- Confirmed those files depend on parallel schemas and orchestration paths not currently owned by the canonical project map.

### Next

1. Decide whether `scripts/download_mlb_bulk.py` should become part of the canonical historical MLB backfill workflow.
2. Extract the useful MLB-enhanced feature ideas into one canonical design/migration path under existing schemas.
3. Run the formal temporal sweep for `pa_outcome_distribution`.

## 2026-04-10 (Temporal Policy Training Controls)

### Built

- Extended `scripts/train_pa_outcome_distribution.py` with direct temporal-policy controls:
  - `--recent-window`
  - `--season-half-life`
  - `--exclude-2020`
  - `--downweight-2020`
- Added reusable era columns to `features.plate_appearance_outcome_examples`:
  - `season_era`
  - `rules_context_era`
- Included the era columns in the multiclass trainer feature set.
- Registered temporal-policy metadata in both `feature_spec` and `metrics` for `models.model_registry`.
- Updated user-facing docs and procedures to show temporal-policy training commands.

### Validation

- `python3 -m py_compile scripts/train_pa_outcome_distribution.py` passed.
- Rebuilt `sql/076_plate_appearance_outcome_model.sql` and `sql/077_pitch_sequence_model.sql` serially after adding era columns to the PA outcome layer.
- Test training run completed successfully:
  - `python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.01 --train-through 2022 --recent-window 7 --season-half-life 5 --downweight-2020 0.5 --no-activate`
- Registered model version `20260410T211408Z` stores:
  - `recent_window = 7`
  - `season_half_life = 5.0`
  - `downweight_2020 = 0.5`
- `features.plate_appearance_outcome_examples` now exposes `season_era` and `rules_context_era`.
- Validation metrics from that smoke test:
  - `hist_gradient_boosting_multiclass`: log loss `1.8108`, top-3 accuracy `0.7133`, accuracy `0.3768`, validation rows `5,448`
  - `multinomial_logistic_regression`: log loss `2.1386`, top-3 accuracy `0.4855`, accuracy `0.2676`, validation rows `5,448`

### Next

1. Add era-feature columns to the PA training views.
2. Run a formal temporal sweep across recent windows and half-lives.
3. Compare policies on `2023-2025` log loss, Brier score, calibration, and subgroup drift.

## 2026-04-10 (Temporal Model Selection)

### Built

- Added `docs/TEMPORAL_MODEL_SELECTION.md` to define how the project should handle non-stationarity across seasons.
- Documented a formal training-policy recommendation:
  - primary production-style policy: exponential recency weighting
  - benchmark policy: fixed recent windows
  - structural-feature policy: explicit era indicators for known regime changes
- Added exact warehouse support for the policy using `features.plate_appearance_outcome_examples`.

### Validation

- Confirmed current multiclass PA layer spans `2000-2025` with `4,779,662` rows.
- Computed fixed-window sample sizes ending in `2025`:
  - 3 years: `559,688`
  - 5 years: `929,476`
  - 7 years: `1,189,370`
  - 10 years: `1,752,609`
  - 15 years: `2,688,466`
  - full span: `4,779,662`
- Confirmed clear season-environment shifts in the warehouse:
  - hit rate `0.2375` in `2000` versus `0.2191` in `2025`
  - home-run rate trough `0.0228` in `2014`
  - home-run rate peak `0.0363` in `2019`
  - shortened `2020` season remains structurally abnormal

### Decision

- Do not equally weight all seasons from `2000-2025` in the main PA outcome model.
- Use fixed windows only as benchmarks, not as the default production policy.
- Use `2023-2025` out-of-time validation to choose between:
  - fixed windows `W ∈ {3,5,7,10,15,all}`
  - exponential half-lives `h ∈ {3,5,7,10}`
- Add era indicators for:
  - `2000-2009`
  - `2010-2014`
  - `2015-2019`
  - `2020`
  - `2021-2022`
  - `2023+`

### Sources

- Concept-drift support:
  - Lu et al., *Learning under Concept Drift: A Review* (2020)
  - Zaidi et al., *On the Inter-relationships among Drift rate, Forgetting rate, Bias/variance profile and Error* (2018)
- Baseball regime-change support:
  - MLB foreign-substance enforcement guidance (2021)
  - MLB 2023 rule-change announcement (2022)

## 2026-04-10 (Pitch Sequence Normalization)

### Built

- Added `sql/077_pitch_sequence_model.sql` as the first formal pitch-sequence normalization layer.
- Created `features.pitch_sequence_symbol_reference` with official Retrosheet pitch-sequence symbols and coarse semantics.
- Created `features.pitch_sequence_examples` with one row per `pitch_seq_tx` symbol, anchored to `features.plate_appearance_outcome_examples`.
- Added `features.pitch_sequence_validation_summary` for coverage and parsing sanity checks.
- Updated the canonical rebuild order in `scripts/rebuild_warehouse.sh`.
- Updated `README.md` and `docs/agents/PROCEDURES.md` to make the new layer reproducible and discoverable.

### Modeling Decisions

- This layer intentionally stops at normalized sequence symbols and coarse symbol groups.
- It does not yet claim to reconstruct every intermediate count transition. That should come after validation against official Retrosheet semantics and the current warehouse state.
- The purpose of this step is to avoid inventing a parallel pitch parser later and to give same-PA temporal feature work a canonical source.

### Validation

- Successfully applied `sql/077_pitch_sequence_model.sql` to the local `retrosheet` database.
- `features.pitch_sequence_examples`: 20,121,849 sequence-symbol rows across 4,779,662 plate appearances.
- Unknown-symbol rows: 0.
- Top symbol groups:
  - `ball`: 6,592,285
  - `in_play`: 3,394,108
  - `foul`: 3,122,551
  - `called_strike`: 3,089,666
  - `swinging_strike`: 1,763,610
  - `marker`: 1,213,190
- Confirmed `pitch_seq_tx` coverage for loaded modern seasons remains complete in `features.plate_appearance_outcome_examples`:
  - 2025: 186,640 / 186,640
  - 2024: 185,783 / 185,783
  - 2023: 187,265 / 187,265
  - 2022: 185,121 / 185,121
- Sampled live warehouse values show the expected Retrosheet symbol mix, including examples such as `BCBBCB`, `CCBX`, `SFBX`, `..CFFBS`, and `CBSBBFX`.

### Next

1. Apply `sql/077_pitch_sequence_model.sql` and validate symbol counts plus unknown-symbol frequency.
2. Add inferred within-PA temporal state columns only after the symbol layer is verified.
3. Build same-PA temporal features on top of `features.pitch_sequence_examples`.

## 2026-04-10 (Research Methodology And Feature Audit)

### Built

- Added `docs/RESEARCH_METHODOLOGY.md` as the formal CRISP-DM methods document for the project.
- Defined the project in research-program terms rather than only implementation terms:
  - business objective and decision problem
  - canonical data layers and source-system separation
  - mathematical state representation for plate appearances
  - multiclass PA outcome notation and objective functions
  - derived baseball probability functionals
  - run expectancy and win-probability notation
  - time-aware evaluation, calibration, and deployment rules
- Added `docs/FEATURE_AUDIT.md` to classify fields and features into:
  - understood and already used
  - understood but not yet fully operationalized
  - preserved raw but not yet reliable enough for direct modeling

### Methodological Decisions

- The warehouse should be treated as a reproducible research system following CRISP-DM:
  - Business Understanding
  - Data Understanding
  - Data Preparation
  - Modeling
  - Evaluation
  - Deployment
- The first coherent direct probabilistic target remains the multiclass plate-appearance outcome distribution.
- Historical/live source merging should continue to happen only after source-preserved raw landing and canonical normalization.
- Hyperparameter search is not the current bottleneck. Expected return is still higher from feature work and calibration work.

### Validation

- Confirmed that the formal methodology is consistent with the current implemented stack:
  - historical path: `raw_retrosheet -> core -> features`
  - live path: `raw_mlb -> bridge -> core.live_* -> analysis`
  - multiclass target: `predictions.prediction_targets.target_id = 'pa_outcome_distribution'`
- Confirmed modern-season `pitch_seq_tx` coverage remains effectively complete in the current warehouse and is therefore viable for the next feature-engineering phase.

### Next

1. Normalize `pitch_seq_tx` into one pitch per row.
2. Add same-game temporal features for PA models.
3. Build live feature parity for `pa_outcome_distribution`.
4. Add calibration and backtest diagnostics for multiclass PA outcomes.
5. Expand hyperparameter search only after the feature/calibration layer is stronger.

## 2026-04-10 (Live Data Integration)

### Built

- **MLB Live Data Ingestion Pipeline**: Complete end-to-end system for ingesting real-time MLB game data alongside historical Retrosheet data
- **Database Objects**:
  - `analysis.combined_games` - Union view of historical + live games
  - `analysis.combined_events` - Union view of historical + live events
  - `analysis.combined_plate_appearances` - Materialized view combining PA data
  - `analysis.get_data_source_stats()` - Function for data source statistics
  - `analysis.get_recent_games()` - Function for recent games across sources
  - `analysis.refresh_combined_data()` - Function to refresh materialized views
- **Scripts**:
  - `scripts/fetch_mlb_schedule.py` - Discovers active MLB games
  - `scripts/populate_bridge_tables.py` - Downloads Chadwick Register for ID mapping
  - `scripts/ingest_live_games.py` - Orchestrates batch live data ingestion
  - `scripts/transform_live_game.py` - Transforms MLB API to core schema (enhanced with ID mapping)
- **Bridge Tables**: Populated `bridge.player_xref` with 127,341 MLB ↔ Retrosheet ID mappings
- **Architecture**: Maintained clean separation between `core.*` (historical) and `core.live_*` (live) data
- **Documentation**: Created comprehensive architecture diagrams and procedure documentation

### Validation Counts

- **Bridge Table Population**: 127,341 player ID mappings loaded
- **Live Game Ingestion**: Successfully ingested 1 MLB game with 79 events
- **Combined Data**: 62,599 total games, 4,933,766 total events across historical + live sources
- **Data Sources**: Historical (62,598 games), Live (1 game), Combined analysis views working

### Architecture Decisions

- **Separation Maintained**: Historical Retrosheet data in `core.games/events`, live MLB data in `core.live_games/events`
- **ID Mapping**: Live data uses Retrosheet IDs via bridge tables, falls back to MLB prefixed IDs when mapping unavailable
- **Analysis Layer**: New `analysis` schema provides unified querying without mixing storage
- **No Table Renames**: Existing architecture already supported clean separation

## 2026-04-10 (Original)

### Built

- Created a reproducible PostgreSQL-first Retrosheet warehouse project.
- Installed/validated Chadwick CLI usage through project scripts.
- Loaded Retrosheet/Chadwick seasons 2000-2025 into `raw_retrosheet`.
- Created source-preserved Chadwick tables:
  - `raw_retrosheet.chadwick_events`
  - `raw_retrosheet.chadwick_games`
  - `raw_retrosheet.chadwick_daily`
  - `raw_retrosheet.chadwick_substitutions`
  - `raw_retrosheet.chadwick_comments`
- Created typed `core` tables:
  - `core.teams`
  - `core.parks`
  - `core.players`
  - `core.games`
  - `core.events`
- Created model-ready feature seed:
  - `features.game_outcome_examples`
- Created modeling, prediction, market, and chat metadata schemas/tables.
- Seeded initial reusable prediction targets.
- Added first ML training script for game-home-win models.
- Added OpenRouter, Groq, and Codex/OpenAI-compatible provider configuration scaffolding.

### Validation

- `raw_retrosheet.chadwick_events`: 4,933,687 rows, 62,598 games.
- `raw_retrosheet.chadwick_games`: 62,598 rows, 62,598 games.
- `core.games`: 62,598 rows, 62,598 games.
- `core.events`: 4,933,687 rows, 62,598 games.
- `features.game_outcome_examples`: 4,779,034 rows, 62,589 games.
- `core.events` has validated primary key, check constraints, and foreign keys.

### Next

- Add market intelligence and prediction-market comparison.
- Add GitHub issues for roadmap tracking.

### Added Later

- Created `core.plate_appearances`.
- Created `features.plate_appearance_examples`.
- Added plate-appearance prediction targets for all outcomes: hit, walk, strikeout, home run, reach-base, extra-base-hit.
- Extended training script to support plate appearance model training.
- Trained all plate appearance prediction models (5% sample, train through 2022):
  - **Walk**: Best ROC AUC 0.959, accuracy 0.936 (most predictable outcome)
  - **Strikeout**: Best ROC AUC 0.841, accuracy 0.779 (highly predictable)
  - **Reach Base**: Best ROC AUC 0.680, accuracy 0.721 (moderately predictable)
  - **Home Run**: Best ROC AUC 0.659, accuracy 0.969 (good accuracy, needs discrimination improvement)
  - **Extra-base Hit**: Best ROC AUC 0.642, accuracy 0.923 (good accuracy, moderate discrimination)
  - **Hit**: Best ROC AUC 0.636, accuracy 0.783 (needs most improvement)
- All models trained with both logistic regression and histogram gradient boosting algorithms.
- Gradient boosting models consistently outperform logistic regression across all targets.
- Model improvement opportunities identified for hit, extra-base hit, and home run predictions.
- Created `scripts/predict_plate_appearance.py` for model inference and real-time predictions.
- Created `scripts/analyze_pa_models.py` for comprehensive model evaluation and comparison.
- Created `scripts/simulate_half_inning.py` for Monte Carlo simulation of half-inning outcomes using trained plate appearance models.
- Implemented comprehensive inference performance optimizations:
  - `inference.plate_appearance_features`: Materialized view with pre-joined enriched features (4.8M rows)
  - `inference.get_plate_appearance_features()`: Fast PostgreSQL function for feature computation
  - `inference.simulation_states`: Table for maintaining simulation state in database
  - Optimized indexes on game state lookups for sub-10ms query performance
- Created `scripts/fast_prediction_service.py`: High-performance service with model caching and batch predictions
- Created `scripts/test_inference_performance.py`: Performance benchmarking tools
- Validated plate appearance coverage:
  - `core.plate_appearances`: 4,779,662 rows, 62,598 games.
  - `features.plate_appearance_examples`: 4,779,662 rows, 62,598 games.
  - `features.half_inning_examples`: 1,118,579 rows, 62,598 games.
  - `inference.plate_appearance_features`: 4,779,662 rows with pre-computed enriched features.
- Loaded Retrosheet reference metadata:
  - `raw_retrosheet.biofile`: 26,961 rows.
  - `raw_retrosheet.teams_reference`: 292 rows.
  - `raw_retrosheet.ballparks_reference`: 656 rows.
- Backfilled core metadata:
  - `core.players`: 7,165 players, 7,165 populated bats values, 7,164 populated throws values.
  - `features.plate_appearance_examples`: 4,779,662 rows with populated batter handedness and pitcher handedness.
- Retrained all active plate-appearance models after handedness enrichment (5% sample, train through 2022):
  - **Walk**: Best ROC AUC 0.959, log loss 0.121.
  - **Strikeout**: Best ROC AUC 0.840, log loss 0.353.
  - **Reach Base**: Best ROC AUC 0.678, log loss 0.565.
  - **Home Run**: Best ROC AUC 0.657, log loss 0.133.
  - **Extra-base Hit**: Best ROC AUC 0.643, log loss 0.262.
  - **Hit**: Best ROC AUC 0.637, log loss 0.501.
- Added broader Retrosheet auxiliary metadata ingestion with `scripts/load_auxiliary_retrosheet.py` and `sql/040_auxiliary_retrosheet.sql`.
- Loaded source-preserved auxiliary tables:
  - `raw_retrosheet.biofile_legacy`: 26,961 rows.
  - `raw_retrosheet.coaches`: 12,501 rows.
  - `raw_retrosheet.ejections`: 19,730 rows.
  - `raw_retrosheet.relatives`: 1,320 rows.
  - `raw_retrosheet.season_rosters`: 138,020 rows.
  - `raw_retrosheet.season_teams`: 3,986 rows.
  - `raw_retrosheet.season_schedules`: 233,953 rows.
  - `raw_retrosheet.season_umpires`: 9,700 rows.
  - `raw_retrosheet.special_gamelog_lines`: 1,973 rows.
- Added normalized auxiliary views:
  - `core.roster_entries`: 138,020 rows.
  - `core.allstar_roster_entries`: 6,528 rows.
  - `core.allstar_games`: 25 rows.
  - `core.scheduled_games`, `core.umpires`, `core.coach_assignments`, `core.ejections`, and `core.player_relatives`.
- Expanded `core.players` from Retrosheet roster metadata to 24,588 players with 24,070 first names, 21,511 batting-hand values, and 22,145 throwing-hand values.
- Added first indexed feature marts with `sql/050_feature_marts.sql`:
  - `features.batter_prior_season_pa_summary`: 23,534 rows.
  - `features.pitcher_prior_season_pa_summary`: 18,574 rows.
  - `features.team_prior_season_summary`: 830 rows.
  - `features.pa_context_prior_season_rates`: 612,126 rows.
  - `features.half_inning_outcome_summary`: 1,118,579 rows.
- Kept prior-season marts keyed by `feature_season = season + 1` so model training can join historical performance without same-season leakage.
- Added enriched model training support in `scripts/train_models.py` and active-model promotion in `scripts/promote_best_models.py`.
- Updated plate-appearance inference to load the enriched feature shape from Postgres before scoring.
- Trained and activated enriched 5% sample models. Active validation ROC AUC:
  - `game_home_win`: 0.850 gradient boosting, 0.843 logistic regression.
  - `pa_batter_walk`: 0.961 logistic regression, 0.960 gradient boosting.
  - `pa_batter_strikeout`: 0.854 gradient boosting, 0.851 logistic regression.
  - `pa_batter_reach_base`: 0.683 gradient boosting, 0.676 logistic regression.
  - `pa_batter_home_run`: 0.683 logistic regression, 0.675 gradient boosting.
  - `pa_batter_extra_base_hit`: 0.646 gradient boosting, 0.639 logistic regression.
  - `pa_batter_hit`: 0.643 gradient boosting, 0.634 logistic regression.
- Verified enriched plate-appearance inference on `ANA202506060` plate appearance `30`.
- Noted future feature work: add coarser context-rate fallbacks because exact inning/base/count/hand context joins can be sparse.
- Added canonical rebuild script `scripts/rebuild_warehouse.sh` so contributors can recreate the warehouse in order without Git LFS or checked-in model binaries.
- Added advanced feature marts with `sql/060_advanced_feature_marts.sql`:
  - `features.pa_context_coarse_prior_season_rates`: 3,744 rows.
  - `features.batter_career_prior_pa_summary`: 81,018 rows.
  - `features.pitcher_career_prior_pa_summary`: 56,553 rows.
  - `features.batter_pitcher_prior_matchup_summary`: 1,155,128 rows.
  - `features.park_prior_season_run_environment`: 818 rows.
  - `features.team_rolling_30_game_summary`: 125,196 rows.
- Added advanced example views for plate-appearance and game-win training.
- Added `scripts/sweep_hyperparameters.py` for reproducible model grid searches. A smoke sweep for `pa_batter_hit` with `--feature-set advanced --sample-rate 0.005 --max-candidates 3` completed and registered candidates.
- Added temporal and production marts with `sql/070_temporal_and_production_marts.sql`:
  - `features.team_game_context`: 125,196 rows.
  - `features.player_production_season`: 23,534 rows.
  - `features.pitcher_production_season`: 18,574 rows.
  - `features.game_outcome_temporal_examples`: 186,562 rows for 2025.
  - `features.plate_appearance_temporal_examples`: 186,640 rows for 2025.
- Spot-checked 2025 player production leaders, pitcher production leaders, and team rest/doubleheader counts.
- Implemented complete AI Baseball Analytics Chatbot:
  - `scripts/baseball_chatbot.py`: Core LLM integration with tool calling and conversation memory
  - `scripts/llm_client.py`: Abstraction layer for OpenAI, local LLMs, and mock clients
  - `scripts/tool_registry.py`: Tool discovery, validation, and execution registry
  - Support for 5 major tools: plate appearance prediction, half-inning simulation, live odds, player analysis, database queries
  - End-to-end natural language processing with real ML model integration
  - Successfully demonstrated tool calling, prediction execution, and response synthesis
  - Cross-validation infrastructure with `scripts/cross_validate_models.py` and `scripts/auto_promote_models.py`
- Added inference performance optimizations:
  - `inference.plate_appearance_features`: Pre-computed feature views (4.8M rows)
  - `inference.get_plate_appearance_features()`: Fast PostgreSQL feature computation
  - `scripts/fast_prediction_service.py`: In-memory model caching and batch predictions
  - Sub-10ms prediction latency improvements
- Added comprehensive testing framework:
  - `scripts/test_baseball_analytics.py`: Schema and data integrity validation
  - `scripts/benchmark_queries.py`: Query performance benchmarking
  - `scripts/simple_perf_test.py`: Performance demonstration tools
- Built the first Next.js web command center in `baseball-chatbot-ui/`:
  - Chat Analyst view with rule-based warehouse/tool routing.
  - Sim Lab view backed by `features.half_inning_outcome_summary`.
  - Models & Backtests view backed by `models.model_registry`, sweep metadata, and production marts.
  - Workbench view with allow-listed local workflow commands rather than arbitrary shell execution.
  - Spreadsheet-style result tables with CSV export.
- Added web API routes:
  - `/api/status`
  - `/api/analytics`
  - `/api/backtests`
  - `/api/chat`
  - `/api/simulate`
  - `/api/terminal`
  - `/api/predict`
  - `/api/live-odds`
- Validated the web command center:
  - `npm run build` completed successfully in `baseball-chatbot-ui/`.
  - `/api/status` returned warehouse/model summary JSON.
  - `/api/analytics` returned active model metrics and 2025 production leaders.
  - `/api/chat` returned active model data for "show active models".
  - `/api/simulate` for 2025 top-first left-handed-only historical states returned 10,538 half-innings, 0.499 expected runs, 28.1% run probability, and 8.1% probability that all left-handed batters in the inning got a hit.
- Added interface persistence with `sql/075_interface_workflows.sql`:
  - `predictions.simulation_runs` records Sim Lab filters, summaries, run distributions, and sample sizes.
  - `predictions.recent_simulation_runs` provides a dashboard-friendly read view.
  - `chat.query_logs` now records tools used and result row counts from web chat requests.
- Reviewed `docs/ab_outcome.md` against the current warehouse and added `docs/AT_BAT_OUTCOME_MODEL_REVIEW.md`.
- Added `sql/076_plate_appearance_outcome_model.sql` with `features.plate_appearance_outcome_examples`, validation summary, and the `pa_outcome_distribution` prediction target for future multiclass PA modeling.

### Next
- Add market intelligence and prediction-market comparison.
- Add GitHub issues for roadmap tracking.
- Added `docs/agents/` as the durable project map for AI agents and humans:
  - `PROJECT_OBJECTIVES.md` defines prediction-engine objectives and modeling goals.
  - `FILE_INVENTORY.md` maps docs, SQL, scripts, feature marts, interface routes, and generated artifacts to their purposes.
  - `PROCEDURES.md` documents canonical warehouse, modeling, simulation, live bridge, interface, and issue workflows.
  - `MODELING_WORKFLOWS.md` inventories targets/models and defines evaluation, leakage, and promotion rules.

## 2026-04-10

### At-Bat Outcome Modeling

- Added GitHub execution issues for the PA outcome and MLB live bridge roadmap:
  - #24 advanced PA outcome distribution training/evaluation.
  - #25 PA outcome distribution prediction API and derived aggregate outputs.
  - #26 pitch-sequence normalization for later next-pitch modeling.
  - #27 raw MLB Stats API schedule/live snapshot logging.
  - #28 MLB-to-Retrosheet ID bridge reconciliation.
  - #29 MLB live feed to canonical live PA/event transforms.
  - #30 live PA feature parity for model inference.
  - #31 live PA outcome scoring and prediction logging.
- Made `sql/076_plate_appearance_outcome_model.sql` rerunnable by dropping `features.plate_appearance_outcome_validation_summary` before rebuilding `features.plate_appearance_outcome_examples`.
- Rebuilt `features.plate_appearance_outcome_examples` successfully:
  - 4,779,662 plate-appearance examples.
  - 62,598 games.
  - 17 raw outcome classes.
  - Pitch-sequence coverage: 1.0000.
  - Batted-ball coverage: 0.7055.
- Trained inactive 5% advanced-feature `pa_outcome_distribution` candidates with:
  - `python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.05 --train-through 2022 --no-activate`
  - Training rows: 211,593.
  - Validation rows: 28,132.
  - Trained classes: 16. `interference` was excluded by the current `--min-class-rows 100` threshold in this sample.
- Candidate metrics:
  - `hist_gradient_boosting_multiclass` version `20260410T172129Z`: validation log loss 1.7720, top-3 accuracy 0.7248, accuracy 0.3854, macro F1 0.1756, weighted F1 0.2858, multiclass Brier score 0.7585.
  - `multinomial_logistic_regression` version `20260410T172129Z`: validation log loss 2.2205, top-3 accuracy 0.4404, accuracy 0.2675, macro F1 0.1453, weighted F1 0.1951, multiclass Brier score 0.8577.
- Decision: do not promote yet. The gradient boosting candidate is materially stronger than logistic and should be the next benchmark, but it still needs calibration, subgroup diagnostics, and either rare-class policy or a larger sample/full run before production-like use.
- Added `scripts/predict_pa_outcome_distribution.py` for reusable multiclass PA scoring from registered model artifacts.
- Extended `/api/predict` so callers can request `target_id: "pa_outcome_distribution"` and receive class probabilities plus derived aggregates.
- Validated historical scoring on `ANA202506060` plate appearance `30` using model version `20260410T172129Z`; probabilities summed to 0.9999999999999999 and returned actual outcome `walk`.
- Ran `npm run build` in `baseball-chatbot-ui/`; the Next.js production build completed successfully.

### Live MLB Pipeline Repair

- Reviewed the live pipeline against the warehouse design goal: keep source-preserved MLB payloads in `raw_mlb`, keep ID reconciliation in `bridge`, upsert canonical live state into `core.live_*`, and use `analysis.*` views/materialized views as the combined analysis layer.
- Extended `sql/090_mlb_live_data.sql` with additive provenance columns for future MLB fetches:
  - `request_params`
  - `http_status`
  - `error_text`
  - `payload_checksum`
  - `game_date`
  - `season`
- Extended `sql/110_live_core_tables.sql` with additive live-state/provenance columns and compatibility indexes so existing warehouses can be upgraded in place:
  - `core.live_games`: `raw_payload`, `created_at`, `updated_at`, `mlb_game_pk`, `snapshot_id`, `snapshot_fetched_at`, `status_code`, `detailed_state`, `venue_name`
  - `core.live_events`: `raw_play`, `created_at`, `updated_at`, `mlb_game_pk`, `snapshot_id`, `plate_appearance_index`, `mlb_event_type`, `event_type_description`, `trajectory`, `home_score_after`, `away_score_after`
- Reworked `scripts/transform_live_game.py` to:
  - read the latest stored snapshot with provenance
  - tolerate the current legacy `bridge.player_xref` column names in the active database
  - preserve `raw_payload` and `raw_play`
  - extract batter/pitcher handedness from `matchup.batSide` and `matchup.pitchHand`
  - map event codes from structured MLB `eventType`/trajectory instead of free-text only
  - upsert `core.live_games` and `core.live_events` instead of replacing whole tables
  - clean up stale legacy live rows for the same game when a canonical bridged game id is available
- Updated `scripts/warehouse.py fetch-live-game` so new raw MLB snapshots store request params, HTTP status, checksum, game date, and season.
- Updated `scripts/ingest_live_games.py` to use environment-driven Postgres settings and a correct recency filter expression.
- Updated `scripts/populate_bridge_tables.py` to tolerate both the canonical bridge schema in SQL and the currently active legacy bridge schema in the database.
- Validation:
  - Fetched fresh snapshots for MLB game `823884`; newest raw rows now include `http_status = 200`, `game_date = 2026-04-09`, `season = 2026`, checksum, and request params.
  - Re-transformed stored snapshot `823884` successfully into canonical game `MLB146202604090` with 79 live events.
  - `core.live_games` for `823884` now shows `is_complete = true`, `status_code = 'F'`, `detailed_state = 'Final'`, and preserved `raw_payload`.
  - All 79 live events for `823884` now preserve `raw_play`.
  - All 79 live events for `823884` now have known batter/pitcher handedness instead of `U`.
  - `analysis.combined_games` now reports 1 live game row and `analysis.combined_events` 79 live event rows for the repaired sample after refresh/cleanup.
  - Refreshed `analysis.combined_plate_appearances`; it now reports 79 live rows.
- Decision: the warehouse design is still correct. Raw MLB should stay separate in `raw_mlb`, and the historical/live merge should happen in `analysis` views/materialized views and later feature-parity views, not by collapsing the raw layers together.
- Documentation sync:
  - Updated `AGENTS.md`, `README.md`, `docs/agents/README.md`, `docs/agents/FILE_INVENTORY.md`, `docs/agents/PROCEDURES.md`, and `docs/LIVE_DATA_ARCHITECTURE.md` so the written live-ingestion procedure now matches the repaired source-preserved/raw-separate design and the canonical upsert-based transform path.

### Feature Audit

- Reviewed the current field reference set:
  - `docs/retrosheet_key.md`
  - `docs/ab_outcome.md`
  - `docs/AT_BAT_OUTCOME_MODEL_REVIEW.md`
  - `docs/CORE_SCHEMA.md`
  - `config/chadwick_event_columns.txt`
- Added `docs/FEATURE_AUDIT.md` to classify current data/feature status into:
  - fields we understand and actively use
  - fields we understand but have not fully operationalized
  - fields preserved raw but not yet reliable enough for modeling
- Decision: feature generation is not “done.” Current historical PA/game models are good enough for baseline modeling and moderate tuning, but the highest-return work before deeper hyperparameter sweeps is still:
  - pitch-level normalization from `pitch_seq_tx`
  - same-game temporal PA features
  - live feature parity for `pa_outcome_distribution`
  - better contact/batted-ball derived features
  - explicit rare-class policy for multiclass outcome modeling

### MLB Raw Backfill Completion And PA Grouped Baseline

- Completed the canonical MLB raw acquisition for the target historical range `2000-2025`.
- Final raw MLB counts after the full backfill:
  - `raw_mlb.schedule_snapshots`: `9,286`
  - `raw_mlb.live_feed_snapshots`: `72,199`
  - successful `raw_mlb.live_feed_snapshots`: `72,184`
  - `raw_mlb.reference_snapshots`: `2,405`
- Final transformed live counts at the same checkpoint:
  - `core.live_games`: `67,913`
  - `core.live_events`: `5,172,275`
- Verified successful live-feed season coverage for every season from `2000` through `2025`.
- Verified reference coverage across all `26` seasons for the tracked endpoint families (`teams`, `rosters`, `people`, `venues`, `standings`).
- Investigated the residual failed MLB game-feed fetches and confirmed they are upstream Stats API `HTTP 500` responses for seven exhibition/special-event games:
  - `243297`
  - `243298`
  - `243313`
  - `243314`
  - `308207`
  - `764834`
  - `764836`
- Decision: the MLB raw layer is current and complete enough to continue. The unresolved failures are upstream exhibition-game holes, not a local ingestion bug.

- Added `sql/078_plate_appearance_outcome_grouped.sql` to create an additive grouped PA target layer on top of the canonical granular layer:
  - `features.plate_appearance_outcome_grouped_examples`
  - `features.plate_appearance_outcome_grouped_validation_summary`
- Validation for the grouped layer:
  - `4,779,662` rows
  - `62,598` distinct games
  - `12` grouped classes
  - pitch-sequence coverage `1.0000`
  - batted-ball coverage `0.7055`
- Extended `scripts/train_pa_outcome_distribution.py` with `--target-taxonomy granular|grouped`.
- Grouped recent-window benchmark setup:
  - `train_through = 2022`
  - `recent_window = 7`
  - validation seasons `2023-2025`
  - `sample_rate = 0.05`
- Full grouped class coverage over the recent window:
  - all `12` grouped classes are present in both training and validation before sparse-class filtering
  - sampled runs retain `11` classes because `other_rare` falls below `--min-class-rows 100`
- Benchmarks at `sample_rate = 0.05`:
  - grouped `basic` logistic: log loss `2.0809`, accuracy `0.2821`, top-3 accuracy `0.4821`
  - grouped `basic` HGB: log loss `1.5253`, accuracy `0.4066`, top-3 accuracy `0.8194`
  - grouped `advanced` logistic: log loss `2.1086`, accuracy `0.2864`, top-3 accuracy `0.4973`
  - grouped `advanced` HGB: log loss `1.5242`, accuracy `0.4081`, top-3 accuracy `0.8176`
- Decision: for the grouped target, histogram gradient boosting is the only viable current model family. The present advanced mart yields only marginal lift over basic on log loss (`1.5242` vs `1.5253`), so the next high-value work is temporal-policy comparison and feature-quality improvements rather than model-family churn.

- Added `scripts/sweep_pa_outcome_temporal.py` as the canonical temporal-policy sweep runner for `pa_outcome_distribution`.
- The sweep runner reuses the existing trainer, emits one JSON row per policy/model pair, and can optionally write a consolidated JSON report for reproducible comparisons.
- Smoke validation:
  - `python3 -m py_compile scripts/sweep_pa_outcome_temporal.py`
  - `python3 scripts/sweep_pa_outcome_temporal.py --feature-set advanced --target-taxonomy grouped --sample-rate 0.01 --recent-windows 7 --season-half-lives 5 --output-json data/reports/temporal_sweep_smoke.json`
- Smoke sweep result for grouped `advanced` HGB:
  - fixed `window = 7`: log loss `1.5816`
  - full-history `half_life = 5`: log loss `1.5748`
- Decision: the temporal sweep runner is working and the early smoke signal supports continuing with a larger grouped HGB policy comparison before changing feature marts or promotion rules.

### Research Report Draft

- Added `research_report.md` at the repository root as the paper-style running research manuscript.
- The report consolidates:
  - research objective and CRISP-DM framing
  - canonical warehouse design
  - historical and MLB raw-data coverage
  - state representation and leakage constraints
  - grouped PA target design
  - statistical objective and temporal weighting equations
  - grouped PA benchmark results
  - limitations and next experiments
- Decision: use `research_report.md` as the evolving manuscript draft while keeping `docs/RESEARCH_METHODOLOGY.md`, `docs/TEMPORAL_MODEL_SELECTION.md`, `docs/PA_BASELINE_MODEL_SPEC.md`, and `docs/FEATURE_AUDIT.md` as supporting technical appendices/source documents.

### Full Grouped PA Temporal Sweep

- Ran the full grouped advanced temporal-policy sweep with:
  - `python3 scripts/sweep_pa_outcome_temporal.py --feature-set advanced --target-taxonomy grouped --sample-rate 0.05 --include-all-window --output-json data/reports/pa_grouped_temporal_sweep.json`
- Sweep scope:
  - fixed windows `3, 5, 7, 10, 15, all`
  - half-lives `3, 5, 7, 10`
  - training through `2022`
  - validation on `2023-2025`
- Ranked HGB results by validation log loss:
  - `all seasons, no decay`: `1.5094`
  - `all seasons, half_life = 10`: `1.5122`
  - `15-year window`: `1.5123`
  - `all seasons, half_life = 7`: `1.5129`
  - `all seasons, half_life = 5`: `1.5144`
  - `10-year window`: `1.5168`
  - `all seasons, half_life = 3`: `1.5201`
  - `7-year window`: `1.5234`
  - `5-year window`: `1.5287`
  - `3-year window`: `1.5429`
- Best current grouped advanced policy:
  - `window_all__half_life_none__keep_2020`
  - validation log loss `1.50943420932027`
  - validation accuracy `0.41184416323048484`
  - validation top-3 accuracy `0.8209512299161098`
  - validation rows `28,132`
- Decision:
  - for the current grouped advanced HGB benchmark, equal-weight full-history training beats shorter windows and beats the tested recency-decay policies
  - temporal policy still matters, but the current evidence does not support aggressive forgetting for this target
  - the next modeling work should shift toward calibration, subgroup diagnostics, and feature-quality improvements

### Grouped PA Calibration And Subgroup Diagnostics

- Added `scripts/analyze_pa_outcome_calibration.py` as a read-only calibration and subgroup analysis runner for registered `pa_outcome_distribution` models.
- Validation command:
  - `python3 -m py_compile scripts/analyze_pa_outcome_calibration.py`
  - `python3 scripts/analyze_pa_outcome_calibration.py --model-name hist_gradient_boosting_multiclass --model-version 20260411T230512Z --output-json data/reports/pa_outcome_calibration_20260411T230512Z.json`
- Scope:
  - winning grouped advanced HGB candidate
  - validation seasons `2023-2025`
  - `559,688` validation rows
- Aggregate registered validation metrics:
  - log loss `1.50943420932027`
  - multiclass Brier score `0.7151476390866868`
  - accuracy `0.41184416323048484`
  - top-3 accuracy `0.8209512299161098`
- Per-class calibration highlights:
  - best ECE values:
    - `triple`: `0.0002`
    - `reach_on_error_or_fc`: `0.0003`
    - `double`: `0.0004`
    - `hit_by_pitch`: `0.0007`
    - `productive_out`: `0.0011`
    - `home_run`: `0.0011`
  - moderate ECE values:
    - `walk`: `0.0026`
    - `ground_out`: `0.0058`
    - `single`: `0.0079`
    - `air_or_other_out`: `0.0092`
  - worst current class:
    - `strikeout`: `ECE = 0.0181`
    - mean predicted probability `0.2415`
    - observed rate `0.2253`
- Subgroup reliability highlights using top-class confidence versus realized top-class accuracy:
  - two-strike counts are the main overconfidence pocket:
    - `0-2`: gap `0.0449`
    - `1-2`: gap `0.0405`
    - `2-2`: gap `0.0438`
  - outs-based gaps are smaller, roughly `0.020-0.024`
  - several occupied-base states widen the gap, including `start_bases = 6` at `0.0406`
  - handedness gaps are moderate; largest observed `RvR` gap is `0.0252`
  - season-level gap is stable across `2023-2025`, roughly `0.021-0.022`
- Decision:
  - the grouped advanced HGB model is a valid research baseline but not yet promotable as a production-style probability engine
  - next work should prioritize calibration correction, subgroup-specific reliability reporting, and feature work around strikeout-heavy/two-strike states

### Held-Out Isotonic Calibration For Grouped PA Model

- Added `scripts/calibrate_pa_outcome_model.py` for read-only post-hoc calibration experiments on registered `pa_outcome_distribution` models.
- Current calibration procedure:
  - fit one-vs-rest isotonic calibrators on validation-era seasons `2023-2024`
  - evaluate calibrated probabilities on held-out `2025`
  - renormalize per-class isotonic outputs back to the multiclass simplex
- Validation command:
  - `python3 -m py_compile scripts/calibrate_pa_outcome_model.py`
  - `python3 scripts/calibrate_pa_outcome_model.py --model-name hist_gradient_boosting_multiclass --model-version 20260411T230512Z --output-json data/reports/pa_outcome_isotonic_20260411T230512Z.json`
- Held-out `2025` results for the winning grouped advanced HGB model:
  - raw log loss `1.5077587730803081`
  - calibrated log loss `1.5047021152352906`
  - raw multiclass Brier score `0.7138235869159922`
  - calibrated multiclass Brier score `0.7124996244921831`
  - raw accuracy `0.4142544706033706`
  - calibrated accuracy `0.4143670397529911`
  - raw top-3 accuracy `0.8207952742398902`
  - calibrated top-3 accuracy `0.8206076589905228`
- Key per-class ECE improvements on held-out `2025`:
  - `strikeout`: `0.0179` -> `0.0036`
  - `single`: `0.0082` -> `0.0018`
  - `air_or_other_out`: `0.0092` -> `0.0049`
  - `ground_out`: `0.0057` -> `0.0035`
  - `home_run`: `0.0015` -> `0.0005`
- Decision:
  - post-hoc isotonic calibration improves held-out probability quality without materially harming classification behavior
  - this is the first concrete result supporting a calibration layer for `pa_outcome_distribution`
  - next work should turn this experimental calibration pass into a repeatable report and decide whether calibrated outputs should be stored separately from raw model probabilities
### Completed ✅
2026-04-22: Feature engineering phases 1, 2, and 3 fully implemented. 135 total features across 4.78M training rows. All feature marts materialized, indexed, and committed.

## 2026-04-23 (KB RAG Infrastructure + Source Ingestion)

### Built
- Created `docs/kb/` RAG-ready directory structure:
  - `docs/kb/AGENTS.md` - Agent guide for KB operations, chunking strategy, LlamaIndex recommendation
  - `docs/kb/sources/` - Organized extracted sources: books/, papers/, articles/, reference/
  - `docs/kb/chunks/` - Chunked documents for RAG (by_source/ and by_topic/)
  - `docs/kb/indices/` - Vector index metadata
  - `docs/kb/metadata/` - Source tracking and ingestion logs
- Created `scripts/kb/chunk_sources.py` - Paragraph-aware chunking script with metadata enrichment
  - Outputs JSONL files organized by source and by topic
  - 9 source files chunked into 9 chunks (4 fundamentals, 2 steroid_era, 3 modeling)
- Created `sql/maintenance/030_kb_vector_schema.sql` - pgvector schema for RAG:
  - `kb.document_chunks` table with VECTOR(1536) embeddings
  - ivfflat similarity index + B-tree filters on topic/source_type
  - `kb.similar_chunks()` function for semantic search with topic filtering
  - `kb.keyword_search()` function for text fallback
  - `kb.chunk_summary` view for validation
- Ingested 6 additional web sources via curl (previously blocked by 402):
  - FanGraphs Library (21K chars) - fundamentals
  - SABR Basics (6.7K chars) - fundamentals
  - PMC Baseball Analytics (45K chars) - modeling
  - Tobin Steroids SABR review (10K chars) - steroid_era
  - PED Career Length (31K chars) - steroid_era
  - Practicing Sabermetrics PDF extracted (14,227 lines / 2.5MB)

### RAG Framework Recommendation
- **Primary: LlamaIndex** over Haystack
  - Native pgvector integration (we already have it installed)
  - Simple ingestion: SimpleDirectoryReader + VectorStoreIndex
  - SQL Query Engine for structured + unstructured hybrid queries
  - Built-in agent tooling (QueryEngineTool, OpenAIAgent, ReActAgent)
  - Better observability with TokenCountingHandler
- Implementation phases documented in `docs/kb/AGENTS.md`

### Blocked Sources Documented
- MDPI journals (3 papers): Akamai/EdgeSuite access denied
- Beyond the Box Score: Fastly domain error (site dead)
- Reddit r/Sabermetrics: JS-required/bot detection
- Hilaris Publisher steroid PDF: Returns HTML instead of PDF
- Scribd: Paywall blocked Birnbaum guide

### Updated Files
- `docs/SABERMETRICS_LINK_INVENTORY.md` - Updated all fetch statuses with locations
- `docs/agents/FILE_INVENTORY.md` - Added KB files, chunk script, vector schema SQL
- `docs/PROJECT_LOG.md` - This entry

## 2026-04-23 (KB Organization + Modular Framework Research)

### Built

- Created `docs/KNOWLEDGE_BASE_MARKOV_CHAIN.md`:
  - Research synthesis: Stanford CS229 softmax, UT Austin Markov, KCL expected runs
  - mlb-win-probability repo: Ensemble Brier 0.1605, Bayesian 90% CI
  - Run expectancy matrix (24 base-out states) with era tables
  - Implementation approaches: uninformed, informed, hybrid, softmax
  - Model selection guidance by target type

- Created `docs/KNOWLEDGE_BASE_FRAMEWORK.md`:
  - Strategy/Registry pattern for flexible predictions
  - Target contract: target_id, features, supported_models
  - Model contract: fit, predict, predict_proba
  - Current targets: PA outcome, inning runs, next state, pitcher K rate, no-hit inning
  - Model families: Markov, HGB, Softmax, baseline

- Created `docs/MODEL_SELECTION_GUIDE.md`:
  - Decision tree for model selection
  - Model family details with research backing
  - Feature requirements by model type
  - Validation requirements (per model type)

- Updated `docs/agents/FILE_INVENTORY.md`:
  - Added KB entries for new knowledge base documents

- Updated `docs/agents/CURRENT_SNAPSHOT.md`:
  - Added Markov chain workstream to "Best Move Right Now"
  - Links to new KB documents

### Created Issues

- #63: Build Modular Prediction Framework: Strategy/Registry Pattern + Markov Chain
- #64: Add Run Expectancy Matrix Feature Mart For Markov Chain Models
- #65: Update Knowledge Base: Add Markov Chain Research and Framework Documentation

### Research Sources Added

- Stanford CS229: Softmax regression for transitions (beat Vegas over/under)
- UT Austin (2016): Markov chain for run/win probability
- KCL Expected Runs: RE matrix from 700+ at-bats
- mlb-win-probability: Ensemble with 165 features
- Korean paper (2025): Deep learning + Markov, 64.48% accuracy

### Decision

- The modular framework approach is research-backed and provides the flexibility needed for granular predictions
- Markov chain models are well-established in sabermetrics (UT Austin, Stanford, KCL)
- Next work is to build the framework structure and add run expectancy matrix feature mart
