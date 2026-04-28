# Audit Report: Baseball Prediction Warehouse

**Date**: 2026-04-28
**Agent**: Jules
**Status**: Discovery Phase Complete

## 1. Component Audit

### A. Feature Calculators
| Calculator | File | Implementation Status | SQL Backing | Notes |
|------------|------|-----------------------|-------------|-------|
| WinExpectancy | `win_expectancy.py` | FULL | `features.win_expectancy_matrix` | Uses 24-state matrix + score diff |
| LeverageIndex | `leverage_index.py` | FULL | `features.leverage_index_matrix` | Computes LI from WE matrix |
| Matchup | `matchup.py` | FULL | `features.matchup_features` | Batter vs Pitcher history |
| RollingForm | `rolling_form.py` | FULL | `features.rolling_form` | 7/14/30 day windows |
| Bullpen | `bullpen.py` | FULL | `features.bullpen_status` | Fatigue and depth metrics |
| RunExpectancy | MISSING | MISSING | `features.run_expectancy_matrix` | Referenced in `__init__.py` but no file exists |

**Findings**:
- `RunExpectancyCalculator` is missing from `baseball/features/` despite being documented.
- All existing calculators inherit from `FeatureStore` and have `compute()` methods.
- Most calculators rely on materialized views or tables in the `features` schema.

### B. CLI Commands (`baseball/cli.py`)
| Command Group | Command | Status | Notes |
|---------------|---------|--------|-------|
| `doctor` | `doctor` | FULL | Checks DB and directories |
| `status` | `status` | FULL | Shows recent pipeline runs |
| `retrosheet` | `download/ingest/validate` | FULL | Wraps `RetrosheetSource` |
| `mlb` | `download/ingest/validate/today` | FULL | Wraps `MlbSource` |
| `live` | `games/watch/poll/predict` | PARTIAL | `predict` logic is placeholder |
| `live` | `server` | STUB | WebSocket server logic missing |
| `bridge` | `resolve/match/lookup` | STUB | Raises `NotImplementedError` |
| `pipeline` | `run/list/status` | FULL | Integrated with `PipelineService` |
| `models` | `list/info/train` | PARTIAL | Registry queries are TODOs |

**Findings**:
- The `bridge` group is entirely stubbed, which is a critical gap for live-to-historical ID resolution.
- The `live server` command is a stub.

### C. Models
| Model | File | Status | Notes |
|-------|------|--------|-------|
| Base | `base.py` | FULL | `BaseModel` and `SklearnBaseModel` |
| PA Outcome | `pa_outcome_model.py` | FULL | XGBoost multi-class classifier |
| Next Run | `next_run_model.py` | FULL | Binary classifier for run-in-inning |
| Win Prob | MISSING | MISSING | Documented but no file exists |

**Findings**:
- `PAOutcomeModel` and `NextRunProbabilityModel` are well-implemented with database integration for features.
- `WinProbabilityModel` is missing; currently `cli.py` uses WE as a placeholder.

### D. SQL Schema
- **Layer Count**:
    - `00_admin`: 1 file
    - `10_raw`: 19 files
    - `30_core`: 23 files
    - `40_bridge`: 15 files
    - `50_features`: 36 files
    - `60_models`: 4 files
    - `70_serving`: 1 file
- **Key Tables**:
    - `features.win_expectancy_matrix`: EXISTS (created in `5032`)
    - `features.leverage_index_matrix`: EXISTS (created in `5033`)
    - `features.bullpen_status`: EXISTS (created in `5036`)
    - `features.run_expectancy_matrix`: MISSING (Not found in `schema_dump.sql`)

---

## 2. Demo Script Output (`--mode quick`)
```
======================================================================
              BASEBALL PREDICTION WAREHOUSE - SYSTEM DEMO
======================================================================

Mode: quick | Time: 2026-04-28T05:43:37.164957
Project: /app

──────────────────────────────────────────────────
 Baseball CLI Discovery
──────────────────────────────────────────────────
❌ Baseball CLI not available - trying Python module

──────────────────────────────────────────────────
 Core Modules
──────────────────────────────────────────────────
✅ baseball.core.types
❌ baseball.core.db: No module named 'psycopg2'
❌ baseball.core.benchmark: No module named 'psutil'
✅ baseball.core.registry
❌ baseball.cli: No module named 'typer'
❌ baseball.services.pipeline: No module named 'psycopg2'
❌ baseball.services.bridge: No module named 'psycopg2'

──────────────────────────────────────────────────
 Source Adapters
──────────────────────────────────────────────────
✅ MlbSource: Importable
✅ RetrosheetSource: Importable
✅ StatcastSource: Importable
✅ EspnSource: Importable
✅ LahmanSource: Importable

──────────────────────────────────────────────────
 Pipeline Configurations
──────────────────────────────────────────────────
❌ Pipeline service error: No module named 'psycopg2'

──────────────────────────────────────────────────
 Feature Calculators
──────────────────────────────────────────────────
✅ WinExpectancyCalculator: Available
✅ LeverageIndexCalculator: Available
❌ RunExpectancyCalculator: Module not found
✅ MatchupCalculator: Available
✅ RollingFormCalculator: Available
❌ BullpenStressCalculator: Module not found

──────────────────────────────────────────────────
 Configuration Files
──────────────────────────────────────────────────
✅ sources.yml: Present
✅ pipelines.yml: Present
✅ models.yml: Present
```

---

## 3. Critical Questions & Answers

### Q1: Run Expectancy Calculator - Missing file.
**Answer**: **A) Compute from historical data**.
**Reasoning**: We have 4.9M historical events in `core.events`. Computing the RE24 matrix from this data ensures consistency with our `core` layer rather than relying on external static tables which might use different ground truths.

### Q2: Bullpen Stress vs BullpenCalculator.
**Answer**: **BullpenCalculator is sufficient**.
**Reasoning**: `bullpen.py` already implements `RelieverFatigue` and `TeamBullpenStatus` with fatigue scores, days rest, and pitch counts. A separate "Stress" calculator is redundant unless it specifically focuses on "High Leverage Workload" (e.g., warm-ups without entering), which we don't have data for yet.

### Q3: Model Storage - Where should trained model artifacts be stored?
**Answer**: **C) Hybrid**.
**Reasoning**: PostgreSQL `models.model_registry` should store metadata, hyperparameters, and metrics for queryability. The actual model binaries (XGBoost/Sklearn) should stay on the filesystem (or S3) to avoid bloating the DB with BLOBs, with the registry storing the `file_path`.

### Q4: Inference Latency - Target for live predictions?
**Answer**: **B) <100ms**.
**Reasoning**: To provide a "Live" feel in a WebSocket-driven UI, end-to-end latency (polling + feature prep + inference + transmit) must stay under 500ms. Allotting <100ms for the inference step is standard.

### Q5: Bridge CLI Commands - Which is most critical?
**Answer**: **`resolve`**.
**Reasoning**: Without `resolve`, we cannot map a `game_pk` from the MLB Live feed to the canonical IDs required to fetch historical features (batter/pitcher rolling form) from our database. It is the bottleneck for live prediction.

### Q6: WebSocket Server - baseball live server command is stub.
**Answer**: **A) Full WebSocket**.
**Reasoning**: Real-time sports predictions require pushing updates to clients immediately upon state change. HTTP polling (B) is inefficient for the target scale (~45M rows of data foundation).

### Q7: Feature Store - Do we need proper Feature Store or keep calculator pattern?
**Answer**: **Keep current calculator pattern but formalize SQL Materialized Views**.
**Reasoning**: The current pattern of `FeatureStore` classes populating `features.*` tables/MVs is working well and provides a clear path for both batch training and live inference. A full third-party Feature Store adds unnecessary infrastructure complexity.

### Q8: Missing SQL - sql/20_staging/ and sql/80_quality/ are empty.
**Answer**: **Populate**.
**Reasoning**: Data quality is paramount for ML. `sql/80_quality/` should contain the validation views currently scattered in `sql/10_raw/1019`. `20_staging` is needed to clean raw payloads before `core` ingestion.

### Q9: Testing - Target coverage for new code?
**Answer**: **B) 80%+**.
**Reasoning**: Given the complexity of baseball logic and ID bridging, high coverage is required to prevent regressions in feature engineering.

### Q10: Historical vs Live Features - Consistency?
**Answer**: **Unified Feature Calculators**.
**Reasoning**: Ensure that both the historical pipeline and the live `predict` command use the exact same Python classes (`WinExpectancyCalculator`, etc.) to process the `GameState` object, ensuring no training-serving skew.

### Q11: Model Priority - Which model first?
**Answer**: **`pa_outcome_model.py`**.
**Reasoning**: The implementation is already largely complete in Python and SQL. `win_probability` can be derived from PA outcomes or a simpler game-state lookup, but a high-fidelity PA model is the "Holy Grail" of this warehouse.

### Q12: Documentation Gaps - Which docs most critical?
**Answer**: **A) architecture.md/keys_and_grains.md**.
**Reasoning**: In a multi-source system (MLB, Retrosheet, Statcast), understanding the "Identity" of a player/game across layers is the hardest problem. Clear grain documentation is essential for any agent or human developer.

---

## 4. Revised Implementation Plan

1.  **Bridge Layer Completion**: Implement `bridge resolve` and `bridge lookup` in `cli.py` and `services/bridge.py`. This is the top priority for live prediction.
2.  **Run Expectancy implementation**: Create `baseball/features/run_expectancy.py` and compute the RE24 matrix from `core.events`.
3.  **Live Predict Loop**: Replace stubs in `baseball/cli.py`'s `live predict` command with actual logic:
    - Poll `LiveMlbSource` for `GameState`.
    - Resolve IDs via `XrefManager`.
    - Compute features via `PAOutcomeModel.predict_pa`.
4.  **WebSocket Implementation**: Implement `baseball/serving/streaming.py` using `websockets` library to fulfill the `live server` command.
5.  **SQL Quality Layer**: Move validation views from `raw` to `sql/80_quality` and add cross-schema consistency checks (e.g., core.events vs raw_mlb.pitches count).
