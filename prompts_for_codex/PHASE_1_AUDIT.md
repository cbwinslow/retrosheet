# Phase 1: Comprehensive Audit & Critical Questions

## Your Task

Before writing ANY code, conduct a thorough audit of the baseball prediction warehouse codebase. This phase is purely about **discovery, analysis, and planning**.

## Deliverables Checklist

- [ ] Create `docs/audit_report.md` with detailed findings
- [ ] Answer all 12 Critical Questions below
- [ ] Provide Revised Implementation Plan based on actual state
- [ ] List all gaps between current state and desired state

---

## Step 1: Audit Feature Calculators

### Instructions
1. Read `baseball/features/__init__.py` - see what's exported
2. List all files in `baseball/features/` directory
3. For each calculator, check:
   - Does it inherit from `FeatureStore`?
   - Does it have `calculate()` method implemented (not just pass/NotImplementedError)?
   - Does it have corresponding SQL table?
   - Is it wired to CLI (`baseball features` command)?

### Document in audit_report.md:
```markdown
## Feature Calculators Audit

| Calculator | File | Implemented | SQL Table | CLI Wired | Notes |
|------------|------|-------------|-----------|-----------|-------|
| WinExpectancyCalculator | win_expectancy.py | ✅/❌ | features.we_matrix | ✅ | ... |
| ... | ... | ... | ... | ... | ... |

### Gaps Found:
- RunExpectancyCalculator: Documented in __init__.py but no file exists
- BullpenStressCalculator: [describe gap]
```

---

## Step 2: Audit CLI Commands

### Instructions
1. Read `baseball/cli.py` completely
2. Identify every `@app.command()` and subcommand
3. Check if implementation is:
   - **Full**: Real logic, database calls, error handling
   - **Stub**: TODO comments, NotImplementedError, pass statements
   - **Partial**: Some parts work, others don't

### Document:
```markdown
## CLI Commands Audit

| Command | Type | Status | Notes |
|---------|------|--------|-------|
| doctor | Core | ✅ Full | Already implemented |
| status | Core | ✅ Full | Already implemented |
| bridge resolve | Bridge | ❌ Stub | Raises NotImplementedError |
| bridge match | Bridge | ❌ Stub | Raises NotImplementedError |
| bridge lookup | Bridge | ❌ Stub | Raises NotImplementedError |
| predict today | Predict | ❌ Stub | TODO comment |
| predict live | Predict | ❌ Stub | TODO comment |
| models train | Models | ⚠️ Partial | Only dry-run mode |
| ... | ... | ... | ... |
```

---

## Step 3: Audit Models

### Instructions
1. Read `baseball/models/__init__.py`
2. List all files in `baseball/models/`
3. Check each model:
   - Does it inherit from `BaseModel`?
   - Is `train()` implemented?
   - Is `predict()` implemented?
   - Is it registered in model map?
   - Does it have SQL backing tables?

### Document:
```markdown
## Models Audit

| Model | File | Status | Training | Inference | Registry | Notes |
|-------|------|--------|----------|-----------|----------|-------|
| NextRunProbabilityModel | pa_outcome_model.py | ✅ Full | ✅ | ✅ | ✅ | ... |
| PAOutcomeModel | pa_outcome_model.py | ✅ Full | ✅ | ✅ | ✅ | ... |
| WinProbabilityModel | ??? | ❌ Missing | - | - | - | Referenced in CLI but no file |
```

---

## Step 4: Audit SQL Schema

### Instructions
1. List all directories in `sql/`
2. Count SQL files per directory
3. Check for key expected tables:
   - `sql/50_features/` - Should have feature tables
   - `sql/60_models/` - Should have model registry
   - `sql/70_serving/` - Should have serving views

### Document:
```markdown
## SQL Schema Audit

| Directory | File Count | Key Files | Status |
|-----------|------------|-----------|--------|
| sql/00_admin/ | 1 | pipeline control | ✅ |
| sql/10_raw/ | 19 | raw data schemas | ✅ |
| sql/50_features/ | 36 | feature tables | [check contents] |
| sql/60_models/ | 4 | model registry | [check if complete] |
| sql/70_serving/ | 1 | serving views | ⚠️ Only 1 file |
```

---

## Step 5: Run Demo Script

### Instructions
```bash
python scripts/demo_full_system.py --mode quick --output /tmp/audit_demo.md
```

Copy the output into your audit report.

---

## Step 6: Answer Critical Questions

Based on your audit, answer these with specific reasoning:

### Q1: Run Expectancy Calculator
**Current State**: Mentioned in `__init__.py` docstring but no file exists.  
**Question**: Should we implement it?  
**Options**:
- A) Compute from historical data (needs SQL + Python calculator)
- B) Use static lookup table (24 states × innings)
- C) Skip it (not critical for win probability)

**Your Answer**: [A/B/C]  
**Reasoning**: [Why? What does current codebase suggest?]

---

### Q2: Bullpen Stress vs Bullpen Calculator
**Current State**: `bullpen.py` has `BullpenCalculator` with fatigue metrics.  
**Question**: Is this what we need, or do we need separate `BullpenStressCalculator`?  
**Options**:
- A) Rename/extend existing BullpenCalculator
- B) Create separate BullpenStressCalculator
- C) Current implementation is sufficient

**Your Answer**: [A/B/C]  
**Reasoning**: [What does the existing code do? What's missing?]

---

### Q3: Model Storage
**Current State**: `BaseModel` abstract class exists. Model registry SQL in `sql/60_models/`.  
**Question**: Where should trained model artifacts be stored?  
**Options**:
- A) PostgreSQL bytea column (models.artifacts table)
- B) Filesystem: `models/{name}/v{N}/model.pkl`
- C) Hybrid: DB for metadata, filesystem for binary

**Your Answer**: [A/B/C]  
**Reasoning**: [What does current model registry SQL expect?]

---

### Q4: Inference Latency Target
**Current State**: Materialized views exist in `sql/70_serving/` but only 1 file.  
**Question**: What's the target latency for live predictions?  
**Options**:
- A) <50ms (aggressive caching, Redis-like)
- B) <100ms (materialized views + indexes)
- C) <500ms (current state acceptable)

**Your Answer**: [A/B/C]  
**Reasoning**: [What do existing serving views suggest?]

---

### Q5: Bridge CLI Commands
**Current State**: Three bridge commands are stubs (resolve, match, lookup).  
**Question**: Which is most critical to implement?  
**Options**:
- A) resolve: Convert source IDs to canonical
- B) match: Find matches between sources
- C) lookup: Get all source IDs for canonical

**Your Answer**: [A/B/C priority order]  
**Reasoning**: [What does live prediction workflow need?]

---

### Q6: WebSocket Server
**Current State**: `baseball live server` command is stub.  
**Question**: Should we implement real-time streaming?  
**Options**:
- A) Full WebSocket server with client subscriptions
- B) HTTP polling endpoint (simpler)
- C) Skip for now, focus on batch predictions

**Your Answer**: [A/B/C]  
**Reasoning**: [What does current live data architecture support?]

---

### Q7: Feature Store Pattern
**Current State**: Calculators use `FeatureStore` base class.  
**Question**: Do we need proper Feature Store (online/offline) or keep current pattern?  
**Options**:
- A) Implement Tecton-style Feature Store
- B) Keep current calculator pattern + materialized views
- C) Hybrid: Feature Store for online, calculators for offline

**Your Answer**: [A/B/C]  
**Reasoning**: [What does current FeatureStore base class suggest?]

---

### Q8: Missing SQL Files
**Current State**: `sql/20_staging/` and `sql/80_quality/` are empty directories.  
**Question**: Do we need to populate these?  
**Options**:
- A) Yes, staging layer is critical for ETL
- B) No, current 10_raw → 30_core flow works
- C) Partial: Add only if specific need arises

**Your Answer**: [A/B/C]  
**Reasoning**: [What does migration_map.md say?]

---

### Q9: Testing Coverage
**Current State**: Tests exist in `tests/unit/`, `tests/integration/`, `tests/e2e/`.  
**Question**: What's the target coverage for new code?  
**Options**:
- A) 100% unit test coverage
- B) 80%+ coverage, focus on integration
- C) Test only critical paths

**Your Answer**: [A/B/C]  
**Reasoning**: [What does existing test structure suggest?]

---

### Q10: Historical vs Live Feature Parity
**Current State**: Calculators have `build()` for batch and `get_*()` for live.  
**Question**: How to ensure training features match inference features?  
**Options**:
- A) Same code path, different data sources
- B) Validate feature distributions match
- C) Trust the calculator abstraction

**Your Answer**: [A/B/C]  
**Reasoning**: [What patterns do existing calculators use?]

---

### Q11: Model Priority Order
**Current State**: `pa_outcome_model.py` exists, `win_probability` referenced but missing.  
**Question**: Which model to implement first?  
**Options**:
- A) Win Probability (most valuable for live)
- B) PA Outcome (building block for WP)
- C) Pitch Outcome (fine-grained)

**Your Answer**: [A/B/C priority order]  
**Reasoning**: [What does models/base.py suggest?]

---

### Q12: Documentation Gaps
**Current State**: Many docs exist but some referenced in AGENTS.md are incomplete.  
**Question**: Which docs are most critical to complete?  
**Options**:
- A) architecture.md, keys_and_grains.md (core reference)
- B) USER_MANUAL.md, README.md (user-facing)
- C) Agent guidance files (AI assistant workflow)

**Your Answer**: [A/B/C priority]  
**Reasoning**: [What does current doc structure suggest?]

---

## Step 7: Revised Implementation Plan

Based on audit findings, provide a realistic sequence:

```markdown
## Revised Implementation Plan

### Phase 1: Foundation (Week 1)
[Based on actual stub count, what can we realistically complete?]

### Phase 2: Features (Week 2)
[Which calculators are actually missing vs just need wiring?]

### Phase 3: Models (Week 3)
[What's the actual path given existing model infrastructure?]

### Phase 4: Serving (Week 4)
[What serving layer actually exists vs needs building?]
```

---

## Validation Checklist

Before submitting this phase as complete:

- [ ] `docs/audit_report.md` exists and is comprehensive
- [ ] All 12 questions answered with specific reasoning
- [ ] Revised plan accounts for actual codebase state
- [ ] Gaps between current and desired state clearly documented
- [ ] No code changes made (this is audit-only phase)

---

## Success Criteria

This phase is successful when:
1. We know exactly what's implemented vs stubbed
2. We have clear answers to architectural questions
3. We have realistic implementation plan
4. We know which SQL files exist and their purpose
5. We know which calculators exist and what's missing

---

## Time Estimate

3-4 hours for thorough audit and analysis.

**Do not rush this phase. Good planning prevents rework.**
