# Codex Prompts - Master Index

## How to Use These Prompts

Submit these prompts to OpenAI Codex **one at a time, in order**. Each phase builds on the previous one. Wait for Codex to complete each phase before submitting the next.

**📖 Read First**: `HOW_TO_USE_WITH_CODEX.md` - Detailed guide on submitting to Codex

**📊 Schema Reference**: `docs/SCHEMA_REFERENCE_FOR_CODEX.md` - Table structures for Codex  
**📄 Full Schema**: `docs/schema_dump.sql` - Complete DDL (23,000 lines)

## Submission Order

| Order | Prompt File | Purpose | Est. Time |
|-------|-------------|---------|-----------|
| 1 | `PHASE_1_AUDIT.md` | Audit codebase & answer critical questions | 2-3 hrs |
| 2 | `PHASE_2_FOUNDATION.md` | Complete CLI doctor/status commands | 3-4 hrs |
| 3 | `PHASE_3_FEATURES.md` | Implement Run Expectancy & Bullpen Stress | 4-5 hrs |
| 4 | `PHASE_4_MODELS.md` | Build model training & Win Probability | 5-6 hrs |
| 5 | `PHASE_5_SERVING.md` | Materialized views & performance | 3-4 hrs |
| 6 | `PHASE_6_DOCS.md` | Documentation & final cleanup | 2-3 hrs |

## Before You Start

1. **Ensure Codex has access to:**
   - All Python files in `baseball/`
   - All SQL files in `sql/`
   - Configuration files in `config/`
   - Test files in `tests/`

2. **Tell Codex:**
   - Read the relevant SQL files before making changes
   - Run `python scripts/demo_full_system.py --mode quick` before and after
   - Write tests for all new code
   - Update documentation (AGENTS.md, PROJECT_LOG.md, FILE_INVENTORY.md)

## Validation After Each Phase

After Codex completes a phase, run:
```bash
# Quick validation
python scripts/demo_full_system.py --mode quick

# Test validation  
python -m pytest tests/ -v --tb=short

# Check for new TODOs
grep -r "TODO\|FIXME\|NotImplementedError" baseball/ --include="*.py"
```

## Critical Rules for Codex

1. **SQL-First**: All DB changes must be in `.sql` files, never ad-hoc
2. **Test-First**: Write tests before implementation
3. **Doc-First**: Update docs as you go, not at the end
4. **Import Check**: Ensure `python -c "import baseball"` works after changes
5. **No Stubs**: Replace NotImplementedError with real implementations

## Project Context

**Repository**: `cbwinslow/retrosheet`  
**Goal**: Baseball prediction warehouse with real-time ML inference  
**Current State**: Milestones 0-9 complete, CLI working, 5 source adapters, 7 pipelines  
**Target State**: Fully functional with live predictions, complete feature layer, production-ready

## Questions?

If Codex encounters ambiguity, it should:
1. Document the issue in the output
2. Make a reasonable assumption
3. Flag it for your review

Don't let Codex skip validation steps or leave TODOs behind.

---

## Ready to Start?

Submit `PHASE_1_AUDIT.md` first. It will audit the current state and answer architectural questions before any code changes.

Good luck!
