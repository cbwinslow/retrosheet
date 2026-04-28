# How to Use These Prompts with OpenAI Codex

## Overview

This guide explains how to submit prompts to Codex for maximum effectiveness. Follow this process to get the best results.

---

## What Codex Can See

Codex has access to:
- ✅ All Python files in `baseball/`
- ✅ All SQL files in `sql/`
- ✅ All configuration files in `config/`
- ✅ All test files in `tests/`
- ✅ All documentation in `docs/`

But Codex **needs guidance** on which files to read and when.

---

## The Complete Prompt Package

When submitting to Codex, include:

### 1. Context Files (Always Include)

Attach these files to give Codex context:

```
# Core context (always attach)
/home/cbwinslow/workspace/retrosheet/AGENTS.md
/home/cbwinslow/workspace/retrosheet/docs/migration_map.md
/home/cbwinslow/workspace/retrosheet/docs/SCHEMA_REFERENCE_FOR_CODEX.md
/home/cbwinslow/workspace/retrosheet/docs/schema_dump.sql (or reference it)
```

### 2. Relevant Code Files (Phase-Specific)

Attach files Codex needs to read:

**For Phase 1 (Audit)**:
```
/home/cbwinslow/workspace/retrosheet/baseball/features/__init__.py
/home/cbwinslow/workspace/retrosheet/baseball/cli.py
/home/cbwinslow/workspace/retrosheet/baseball/models/base.py
/home/cbwinslow/workspace/retrosheet/baseball/models/pa_outcome_model.py
/home/cbwinslow/workspace/retrosheet/config/pipelines.yml
/home/cbwinslow/workspace/retrosheet/config/models.yml
```

**For Phase 3 (Features)**:
```
/home/cbwinslow/workspace/retrosheet/baseball/features/base.py
/home/cbwinslow/workspace/retrosheet/baseball/features/win_expectancy.py
/home/cbwinslow/workspace/retrosheet/sql/50_features/5032_features_win_expectancy.sql
/home/cbwinslow/workspace/retrosheet/sql/50_features/5033_features_leverage_index.sql
```

**For Phase 4 (Models)**:
```
/home/cbwinslow/workspace/retrosheet/baseball/models/base.py
/home/cbwinslow/workspace/retrosheet/baseball/models/pa_outcome_model.py
/home/cbwinslow/workspace/retrosheet/baseball/models/registry.py
/home/cbwinslow/workspace/retrosheet/sql/60_models/600_models_registry.sql
```

---

## Submission Format

### Method 1: Full Context (Recommended for First Phase)

```markdown
## System Prompt

You are working on the cbwinslow/retrosheet baseball prediction warehouse. 
This is a PostgreSQL-based data warehouse with ML models for live baseball predictions.

## Your Task

[Insert PHASE_1_AUDIT.md content here]

## Files to Read

Please read these files to understand the current state:
1. /home/cbwinslow/workspace/retrosheet/AGENTS.md
2. /home/cbwinslow/workspace/retrosheet/docs/migration_map.md
3. /home/cbwinslow/workspace/retrosheet/docs/SCHEMA_REFERENCE_FOR_CODEX.md
4. /home/cbwinslow/workspace/retrosheet/baseball/features/__init__.py
5. /home/cbwinslow/workspace/retrosheet/baseball/cli.py
6. /home/cbwinslow/workspace/retrosheet/baseball/models/base.py
7. /home/cbwinslow/workspace/retrosheet/config/pipelines.yml

## Database Schema

The complete schema is in: /home/cbwinslow/workspace/retrosheet/docs/schema_dump.sql
You can reference it to understand table structures.

## Deliverables

1. Create docs/audit_report.md with findings
2. Answer all 12 critical questions
3. Provide revised implementation plan

## Constraints

- Do NOT write code in this phase - audit only
- Do NOT modify existing files
- DO document what you find
- DO ask questions if unclear
```

### Method 2: Iterative (For Later Phases)

After Phase 1 is complete:

```markdown
## System Prompt

Continuing work on cbwinslow/retrosheet baseball prediction warehouse.

## Your Task

[Insert PHASE_3_FEATURES.md content here]

## Context from Previous Phase

The audit found:
- RunExpectancyCalculator: Missing (needs creation)
- BullpenStressCalculator: Exists as BullpenCalculator (may need rename)
- SQL layer: Need to create tables

## Files to Read

[Attach relevant files for this phase]

## Database Schema Reference

/docs/SCHEMA_REFERENCE_FOR_CODEX.md contains table structures.
/docs/schema_dump.sql has complete DDL.

## Deliverables

1. Create baseball/features/run_expectancy.py
2. Create sql/50_features/501_features_run_expectancy.sql
3. Add tests
4. Wire to CLI
5. Update documentation

## Constraints

- MUST read existing SQL files before creating new ones
- MUST match existing patterns (class structure, naming)
- MUST create tests for all new code
- MUST update AGENTS.md and PROJECT_LOG.md
```

---

## Critical Instructions to Give Codex

Always include these instructions:

### 1. SQL-First Rule
```
CRITICAL: All database operations must be in .sql files.
- Create/alter tables: MUST have SQL file
- Add indexes: MUST have SQL file
- Create views: MUST have SQL file
- Never execute ad-hoc SQL in Python
```

### 2. Test Requirement
```
CRITICAL: Write tests for all new code.
- Unit tests in tests/unit/test_*.py
- Integration tests where DB involved
- Test both success and failure cases
```

### 3. Documentation Requirement
```
CRITICAL: Update documentation as you work.
- AGENTS.md: Update status of components
- PROJECT_LOG.md: Add entry for completed work
- FILE_INVENTORY.md: Add new files
```

### 4. Pattern Matching
```
CRITICAL: Match existing patterns.
- Read existing calculators before writing new ones
- Use same class structure
- Use same SQL naming conventions
- Use same error handling
```

---

## Validation Commands

Tell Codex to run these after completing work:

```bash
# 1. Import test
python -c "import baseball; print('✅ Import OK')"

# 2. Feature calculator test
python -c "from baseball.features import RunExpectancyCalculator; print('✅ RE OK')"

# 3. SQL syntax test
psql -c "\dt features.*"  # List feature tables

# 4. Unit tests
python -m pytest tests/unit/test_run_expectancy.py -v

# 5. Demo script
python scripts/demo_full_system.py --mode quick
```

---

## Handling Schema Visibility

### Option A: Schema Dump (23,000 lines)

Pros: Complete DDL, Codex sees everything
Cons: Very large, may use many tokens

Use when: Major schema changes, creating many tables

### Option B: Schema Reference Document

Pros: Summarized, easier to read
Cons: May miss details

Use when: Building on existing tables, minor changes

### Option C: Specific SQL Files

Pros: Precise, targeted
Cons: May miss related tables

Use when: Clear scope, specific feature

**Recommendation**: Use Option B (SCHEMA_REFERENCE_FOR_CODEX.md) + attach specific SQL files for tables being modified.

---

## Common Issues & Solutions

### Issue: Codex Creates Duplicate Tables

**Solution**: Tell Codex explicitly:
```
Before creating any new SQL file, check if table already exists.
Run: grep -r "CREATE TABLE.*features\.run_expectancy" sql/
If found, modify existing file instead of creating new one.
```

### Issue: Codex Uses Wrong Column Types

**Solution**: Reference schema_dump.sql:
```
Check existing column types in docs/schema_dump.sql.
Match the patterns used (e.g., NUMERIC(5,3) for probabilities).
```

### Issue: Codex Forgets Tests

**Solution**: Make it explicit in deliverables:
```
Deliverables:
1. Implementation code
2. Unit tests (MANDATORY - will not accept without tests)
3. Documentation updates
```

### Issue: Codex Doesn't Update Docs

**Solution**: Add to validation:
```
Before submitting:
- [ ] AGENTS.md updated
- [ ] PROJECT_LOG.md updated
- [ ] FILE_INVENTORY.md updated
```

---

## Example Complete Submission (Phase 1)

```markdown
## System Context

You are working on the cbwinslow/retrosheet baseball prediction warehouse.
Repository: /home/cbwinslow/workspace/retrosheet
Database: PostgreSQL retrosheet
Current State: Milestones 0-9 complete, 5 source adapters, 7 pipelines working

## Your Task

[Copy entire PHASE_1_AUDIT.md here]

## Files to Read (CRITICAL)

Read these files in order:
1. /home/cbwinslow/workspace/retrosheet/AGENTS.md
2. /home/cbwinslow/workspace/retrosheet/docs/SCHEMA_REFERENCE_FOR_CODEX.md
3. /home/cbwinslow/workspace/retrosheet/baseball/features/__init__.py
4. /home/cbwinslow/workspace/retrosheet/baseball/cli.py
5. /home/cbwinslow/workspace/retrosheet/baseball/models/base.py
6. /home/cbwinslow/workspace/retrosheet/baseball/models/pa_outcome_model.py
7. /home/cbwinslow/workspace/retrosheet/config/pipelines.yml
8. /home/cbwinslow/workspace/retrosheet/config/models.yml

## Schema Reference

Full schema: /home/cbwinslow/workspace/retrosheet/docs/schema_dump.sql (23,000 lines)
Summary: /home/cbwinslow/workspace/retrosheet/docs/SCHEMA_REFERENCE_FOR_CODEX.md

## What to Do

1. Read all listed files
2. Audit current state vs documented state
3. Identify all gaps and TODOs
4. Answer the 12 critical questions
5. Create docs/audit_report.md
6. Provide revised implementation plan

## What NOT to Do

- Do NOT modify any existing files
- Do NOT create new code files
- Do NOT execute SQL against database
- This is AUDIT phase only

## Questions?

If you find inconsistencies or need clarification:
1. Document what you found
2. State your assumption
3. Flag for review

Begin audit now.
```

---

## Next Steps

1. **Read MASTER_INDEX.md** - Understand the 6 phases
2. **Submit Phase 1** - Get audit results and answers to 12 questions
3. **Review answers** - Confirm or revise the plan
4. **Submit subsequent phases** - One at a time, building on previous

Ready to start with Phase 1?
