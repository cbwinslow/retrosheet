# OpenAI Codex Prompt: Baseball Prediction Warehouse - Major Update Implementation

## Context

You are working on the `cbwinslow/retrosheet` repository - a baseball prediction warehouse that ingests data from multiple sources (Retrosheet, MLB Stats API, ESPN, Statcast, Lahman) and builds ML-ready features for real-time game predictions.

**Current State**: The project has completed Milestones 0-9 and has working:
- `baseball` CLI framework with 5 source adapters (MLB, Retrosheet, Statcast, ESPN, Lahman)
- Pipeline orchestration with 7 pipeline configurations
- Feature calculators (Win Expectancy, Leverage Index, Matchup, Rolling Form)
- Testing infrastructure (160+ tests)
- Bridge consolidation (XrefManager)

**Goal**: Implement the remaining work from `major_update.md` planning document.

---

## Current Implementation Status (From AGENTS.md)

### ✅ Complete (Milestones 0-9)
- Phase 0: Migration planning documents
- Phase 1: `baseball` CLI framework, source adapter pattern, admin SQL tables
- Phase 2: All 5 historical source adapters (MLB, Retrosheet, Statcast, ESPN, Lahman)
- Phase 3: Live data source adapter (`LiveMlbSource`), real-time prediction pipeline
- Phase 5: Bridge layer (`XrefManager`, `player_xref.py`, `team_xref.py`, `game_xref.py`)
- Phase 6-7: WE/LI features, Model Registry SQL, feature calculators
- Phase 7a: Testing Infrastructure (unit, integration, E2E tests)
- Phase 8: Pipeline orchestration with 7 pipelines
- Phase 9: Legacy script migration

### 🔄 In Progress / Partial
- Live MLB WebSocket server (`baseball live server` command - placeholder)
- Some CLI stubs return `NotImplementedError`
- Missing feature calculators: RunExpectancy, BullpenStress
- `baseball doctor` and `baseball status` are stubs

---

## Implementation Plan (From major_update.md)

You are to implement the remaining milestones. Work through them in order, validating each before moving to the next.

### Milestone 10 — Sabermetric Feature Layer (Priority: High)

**Goal**: Create reproducible feature builders and feature tables.

**Tasks**:

1. **Create `baseball/features/run_expectancy.py`**
   - Implement `RunExpectancyCalculator` class
   - Calculate run expectancy by base-out state (24 states)
   - Store results in `features.run_expectancy_matrix` table
   - Support both historical calculation and live lookup
   - Required methods: `calculate()`, `get_re_state(base_state, outs)`, `build_matrix()`

2. **Create `baseball/features/bullpen_stress.py`**
   - Implement `BullpenStressCalculator` class
   - Calculate bullpen fatigue metrics:
     - Pitch count over last 3 days
     - Days rest for each reliever
     - Leverage index faced
     - Times through order penalty
   - Store in `features.bullpen_stress` table
   - Required methods: `calculate(team_id, date)`, `get_stress_score(team_id, date)`

3. **Create SQL files in `sql/50_features/`**:
   - `501_features_run_expectancy.sql`: Run expectancy matrix table
   - `502_features_bullpen_stress.sql`: Bullpen stress metrics table
   - Add proper indexes for fast lookups

4. **Wire into CLI**:
   - `baseball features build --calculator run_expectancy`
   - `baseball features build --calculator bullpen_stress`
   - Add to pipeline config: `feature_building` pipeline should include these

**Validation**:
```bash
python -c "from baseball.features.run_expectancy import RunExpectancyCalculator; print('RE OK')"
python -c "from baseball.features.bullpen_stress import BullpenStressCalculator; print('Bullpen OK')"
baseball features build --calculator run_expectancy --dry-run
```

---

### Milestone 11 — ML Model Layer (Priority: High)

**Goal**: Add a reproducible model registry and first live-serving model.

**Tasks**:

1. **Complete `baseball/models/base.py`** (if partial)
   - Ensure `BaseModel` abstract class has:
     - `train()` method
     - `predict()` method
     - `evaluate()` method
     - `save()` / `load()` methods
     - `get_feature_importance()` method

2. **Create `baseball/models/training.py`**
   - Implement `ModelTrainer` class
   - Support train/validation/test splits
   - Cross-validation support
   - Hyperparameter tracking
   - Integration with model registry SQL

3. **Create `baseball/models/inference.py`**
   - Implement `ModelInference` class
   - Batch prediction support
   - Single game prediction
   - Feature vector assembly from database
   - Prediction persistence to `serving.predictions`

4. **Implement first model: `win_probability`**
   - Create `baseball/models/win_probability.py`
   - Model: Logistic Regression or XGBoost (start simple)
   - Features: game state (inning, score diff, base state, outs, pitcher/batter matchup)
   - Target: home team wins (0/1)
   - Training data: historical games from core schema
   - Inference: real-time game state scoring

5. **Wire into CLI**:
   - `baseball models train --model win_probability --seasons 2020-2024`
   - `baseball models list`
   - `baseball models status --model win_probability`

**Validation**:
```bash
baseball models train --model win_probability --dry-run
baseball models list  # Should show win_probability
```

---

### Milestone 12 — Serving and Performance Layer (Priority: Medium)

**Goal**: Add low-latency read models and performance-oriented structures.

**Tasks**:

1. **Create serving materialized views**:
   - `serving.mv_current_standings`: Team standings with derived stats
   - `serving.mv_player_form_30d`: 30-day rolling player performance
   - `serving.mv_pitcher_arsenal`: Pitcher pitch-type breakdowns
   - All views must have <100ms query time target

2. **Add indexes for performance**:
   - Review existing tables for missing indexes
   - Add composite indexes for common query patterns
   - Document index strategy

3. **Create `baseball/core/performance.py`**
   - Query timing utilities
   - Slow query detection
   - Index usage monitoring

4. **Wire `baseball status` command** (currently stub):
   - Show database connection status
   - Show table row counts
   - Show last ingestion timestamps
   - Show model performance metrics
   - Show cache status

**Validation**:
```bash
baseball status  # Should show real data, not NotImplementedError
psql -c "EXPLAIN ANALYZE SELECT * FROM serving.mv_current_standings"  # Should be fast
```

---

### Milestone 13 — Documentation and Cleanup (Priority: Medium)

**Goal**: Finalize project docs and deprecate legacy paths safely.

**Tasks**:

1. **Complete `baseball doctor` command** (currently stub):
   - Check database connectivity
   - Check required extensions (hstore, pg_stat_statements, etc.)
   - Check Chadwick installation
   - Check disk space for data directories
   - Validate config files (YAML syntax)
   - Report issues with fix suggestions

2. **Update README.md**:
   - Current CLI workflow examples
   - Updated setup instructions
   - Quick start guide
   - Architecture diagram

3. **Create `docs/architecture.md`** (referenced in AGENTS.md but may be incomplete):
   - Data flow diagrams (ASCII or Mermaid)
   - Component interaction matrix
   - Source-to-feature-to-model pipeline
   - Decision records for key architectural choices

4. **Create `docs/keys_and_grains.md`** (referenced but may need completion):
   - All entity keys documented
   - Table grains defined
   - Surrogate key strategy
   - Natural key to surrogate mapping

5. **Finalize agent guidance**:
   - `docs/agents/architecture_agent.md`
   - `docs/agents/python_agent.md`
   - `docs/agents/sql_agent.md`
   - `docs/agents/ml_agent.md`

6. **Move remaining legacy scripts**:
   - Identify scripts in `scripts/` that should be in `scripts_legacy/`
   - Update any references
   - Add migration notes

---

## Critical Concerns (Must Address)

### 1. **SQL-First Development Rule**
**ALL database operations must be stored in .sql files under version control.**
- NEVER execute ad-hoc SQL against the database without saving it first
- NEVER use database GUI tools for schema changes
- ALWAYS write SQL to a file, commit it, then execute

### 2. **Reproducibility Mandate**
Every action must leave a paper trail:
- All SQL saved in version-controlled .sql files
- All scripts saved and documented
- Table/column comments added for new schema objects
- FILE_INVENTORY.md updated with new files
- PROJECT_LOG.md updated with what was accomplished
- Row counts/validation metrics recorded

### 3. **Source-Preserved Raw Data**
Do not overwrite or discard raw data from any source.
- Retrosheet event files: keep original
- MLB API payloads: store in `raw_mlb.live_feed_snapshots`
- ESPN data: store in `raw_espn.*_snapshots`
- Statcast: store in `raw_mlb.statcast`

### 4. **Grain-Aware Modeling**
Every table must have documented grain:
- What makes a row unique?
- What is the primary key?
- Are there slowly changing dimensions?

---

## Questions I Have (Please Answer/Address)

1. **Feature Calculator Architecture**: Should `RunExpectancyCalculator` calculate from scratch each time or use pre-computed lookup tables? Historical data can compute RE matrix once per season; live games need fast lookups.

2. **Model Storage**: Where should trained model artifacts be stored? Options:
   - PostgreSQL (bytea column in models.artifacts)
   - Filesystem (versioned directory like `models/win_probability/v1/model.pkl`)
   - External storage (S3-compatible, but adds complexity)

3. **Feature Store**: Should we implement a proper feature store pattern with:
   - Online features (for live inference, <10ms)
   - Offline features (for training, batch computed)
   - Or keep it simple with materialized views?

4. **Inference Latency**: Target latency for live predictions? Options:
   - <50ms (requires aggressive caching)
   - <100ms (reasonable with good indexes)
   - <500ms (current state, acceptable for now)

5. **WebSocket Server**: The `baseball live server` command exists but is a stub. Should it:
   - Stream predictions for active games only?
   - Support client subscriptions to specific games?
   - Use FastAPI + WebSockets or aiohttp?

---

## Files to Reference

Before implementing, read these files:
1. `AGENTS.md` - Project conventions and current status
2. `docs/migration_map.md` - File organization
3. `docs/migration_backlog.md` - Detailed task list
4. `docs/PROJECT_LOG.md` - Recent completed work
5. `docs/agents/FILE_INVENTORY.md` - File purposes
6. `baseball/features/win_expectancy.py` - Reference implementation pattern
7. `baseball/services/pipeline.py` - Pipeline orchestration
8. `config/pipelines.yml` - Pipeline definitions

---

## Success Criteria

For each milestone, these must pass:
1. All new Python modules import without error
2. All new SQL files execute without error
3. Tests pass (run `python -m pytest tests/ -v`)
4. CLI commands execute without error (may be dry-run for destructive ops)
5. Documentation updated (AGENTS.md, PROJECT_LOG.md, FILE_INVENTORY.md)
6. File organization matches migration_map.md

---

## Implementation Order (Recommended)

**Phase 1: Foundation (Week 1)**
1. Milestone 10: Run Expectancy calculator
2. Milestone 10: Bullpen Stress calculator
3. Milestone 12: `baseball status` command
4. Milestone 13: `baseball doctor` command

**Phase 2: Models (Week 2)**
1. Milestone 11: Model training infrastructure
2. Milestone 11: Win Probability model
3. Milestone 12: Serving materialized views

**Phase 3: Polish (Week 3)**
1. Milestone 13: Documentation
2. Milestone 13: Architecture docs
3. Milestone 13: Legacy cleanup

---

## Starting Point

Current working directory: `/home/cbwinslow/workspace/retrosheet`

Test current state:
```bash
python scripts/demo_full_system.py --mode quick
```

This will show you what's currently working vs what's missing.

---

## Communication

When you complete work:
1. Update this prompt file with what you accomplished
2. Update `docs/PROJECT_LOG.md` with detailed entry
3. Update `docs/agents/FILE_INVENTORY.md` with new files
4. Run the demo script to validate

**Ask for clarification if**: Requirements are ambiguous, conflicting with existing code, or if you discover a better approach than what's documented.

**Do NOT start work on**: Milestones before completing the ones listed above in order. Do NOT skip validation steps.

Good luck! Let's build a production-ready baseball prediction system.
