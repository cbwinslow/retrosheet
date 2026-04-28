# Phase 1: Audit & Critical Questions

## Task for Codex

Before writing any code, audit the current codebase and answer these critical architectural questions. This phase is about **discovery and planning**.

## Deliverables

1. **Audit Report** (`docs/audit_report.md`) documenting:
   - What feature calculators exist vs what's documented
   - What CLI commands are stubs vs implemented
   - What models exist vs planned
   - Database table coverage

2. **Answer 10 Critical Questions** below

3. **Revised Implementation Plan** based on audit findings

---

## Critical Questions to Answer

### Q1: Run Expectancy Calculator
The `features/__init__.py` mentions `Run Expectancy (RE) matrix` but there's no `run_expectancy.py` file. 
- **Should we implement RE calculator?** YES/NO
- **Approach**: (A) Compute from scratch using historical data, or (B) Use static 24-state matrix from Baseball Prospectus?
- **Priority**: P0 (blocker) / P1 (important) / P2 (nice to have)

### Q2: Model Storage Strategy
Current model base is abstract. Where should trained models be stored?
- **Option A**: PostgreSQL bytea column (versioned in DB)
- **Option B**: Filesystem (`models/{model_name}/v{N}/model.pkl`)
- **Option C**: Both (DB for metadata, filesystem for artifacts)
- **Consider**: Model size (GB?), team access, CI/CD integration

### Q3: Feature Store Pattern
Current feature calculators use FeatureStore base class but no centralized feature store.
- **Should we implement**: Online feature store for <10ms inference lookups?
- **Or**: Keep materialized views + calculator methods?
- **Target latency**: <50ms / <100ms / <500ms for live predictions?

### Q4: WebSocket Server Scope
The `baseball live server` command exists but is a stub.
- **Scope**: Stream predictions for ALL active games or client subscribes to specific games?
- **Protocol**: WebSocket for real-time + HTTP for REST?
- **Clients**: Web dashboard, mobile app, or just internal?

### Q5: Inference Pipeline Integration
Live prediction flow needs clarity:
- **Input**: game_pk + inning + score + base state + pitcher/batter IDs
- **Features**: Query from `serving.mv_*` or compute on-demand?
- **Model**: Load once at startup or per-request?
- **Output**: Just win probability % or full prediction object?

### Q6: Bridge CLI Commands
Three bridge commands are stubs (`resolve`, `match`, `lookup`).
- **Use case priority**: Which is most important for live prediction?
- **Implementation**: Direct DB queries in CLI or call `BridgeService` methods?

### Q7: Missing Models
`pa_outcome_model.py` exists but `win_probability` model is stubbed in CLI.
- **Model priority**: 1) Win Probability, 2) PA Outcome, 3) Pitch Outcome, 4) Next Run?
- **Training cadence**: Daily retrain or only when new data arrives?

### Q8: Data Quality Monitoring
How should we monitor data quality?
- **Option A**: Per-source validation tables
- **Option B**: Centralized `admin.data_quality` table
- **Metrics**: Row counts, null %, freshness, checksums
- **Alerts**: Log warnings or raise errors?

### Q9: Historical vs Live Feature Parity
Features for training (historical) vs inference (live) must match.
- **Strategy A**: Same calculators, different data sources
- **Strategy B**: Separate historical/live calculators
- **Risk**: Feature drift between training and inference

### Q10: Testing Strategy
Current tests exist but may not cover new features.
- **Unit test coverage target**: 80% / 90% / 100% of new code?
- **Integration tests**: Test with real DB or mock?
- **E2E tests**: Full pipeline from download to prediction?

---

## Audit Checklist

Go through the codebase and document:

### Feature Calculators
- [ ] List all files in `baseball/features/`
- [ ] Check which are imported in `__init__.py`
- [ ] Check which have `calculate()` method implemented
- [ ] Check which have SQL tables backing them
- [ ] Document gaps

### CLI Commands
- [ ] List all commands in `baseball/cli.py`
- [ ] Mark which are stubs (TODO/NotImplementedError)
- [ ] Mark which are fully implemented
- [ ] Document gaps

### Models
- [ ] List all files in `baseball/models/`
- [ ] Check which models are concrete vs abstract
- [ ] Check training pipeline status
- [ ] Document gaps

### Database Schema
- [ ] List all schemas in database
- [ ] Check `features.*` tables exist
- [ ] Check `serving.*` views exist
- [ ] Check `models.*` tables exist
- [ ] Document gaps

### Configuration Files
- [ ] Check `config/sources.yml` completeness
- [ ] Check `config/pipelines.yml` completeness
- [ ] Check `config/models.yml` completeness
- [ ] Document gaps

---

## Validation Steps

Before submitting this phase:
1. Run `python scripts/demo_full_system.py --mode quick` - capture output
2. Document all TODO/FIXME comments found in codebase
3. Check test coverage: `pytest --collect-only | wc -l`
4. Verify all imports work: `python -c "import baseball"`

---

## Success Criteria

- [ ] Audit report created at `docs/audit_report.md`
- [ ] All 10 questions answered with reasoning
- [ ] Revised plan accounts for current state vs desired state
- [ ] No code changes in this phase - only discovery

---

## Output Format

Provide your answers in this format:

```markdown
## Audit Findings

### Feature Calculators
- Existing: WinExpectancyCalculator, LeverageIndexCalculator, MatchupCalculator, RollingFormCalculator, BullpenCalculator
- Missing: RunExpectancyCalculator (documented but not implemented)

### CLI Commands
- Implemented: doctor, status, pipeline list/run/status, features list/compute
- Stubs: bridge resolve/match/lookup, predict today/live/batch, models info/download/archive/compare/export

[... more findings ...]

## Answers to Critical Questions

### Q1: Run Expectancy Calculator
**Answer**: YES, implement using Approach A (compute from historical data)
**Reasoning**: [your reasoning]
**Priority**: P1

### Q2: Model Storage Strategy
**Answer**: Option C (DB + filesystem)
**Reasoning**: [your reasoning]

[... more answers ...]

## Revised Implementation Plan

Based on audit, here is the actual sequence:

1. **Milestone X** (was 10): [revised based on findings]
2. **Milestone Y** (was 11): [revised based on findings]
```

---

## Time Estimate

2-3 hours for thorough audit and analysis.
