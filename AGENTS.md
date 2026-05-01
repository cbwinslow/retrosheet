# AGENTS

## Project Mission

Refactor cbwinslow/retrosheet into a clean, extensible baseball data platform with:

- unified CLI
- layered SQL
- source adapters
- bridge/xref resolution
- sabermetric features
- ML modeling
- real-time prediction support

## Absolute Rules

- Preserve working logic before rewriting.
- Do not create orphan scripts.
- Reuse existing repo code whenever possible.
- Keep Python modular and class-based.
- Keep SQL layered and purpose-specific.
- Document file moves in docs/migration_map.md.
- Document table grains and keys in docs/keys_and_grains.md.
- MLB live feed is the primary live source; ESPN is secondary/fallback.
- Build for real-time prediction, but keep the architecture general and reusable.
- When dealing with scripts, databases, or data sets, ALWAYS prefer transforming using the WHOLE SET instead of reducing to smaller subsets.
- **ALWAYS create comprehensive tests for all generated code** - Tests must cover all aspects including edge cases, error handling, and integration scenarios. Tests should be complete and thorough, not just surface-level checks.

## GitHub Issue Workflow

**CRITICAL: Always check for existing issues before creating new ones.**

### Issue Creation Guidelines
1. **Search first:** Before creating any issue, search existing issues by:
   - Title keywords (e.g., "maintenance schema", "Redis caching")
   - Labels (e.g., "phase-4", "database", "infrastructure")
   - Related components (e.g., "sql/00_admin", "baseball/core/cache")
2. **Reuse existing issues:** If an issue exists for the work being done:
   - Add a comment documenting progress
   - Update the issue status/checklist
   - Link related files and commits
   - Do NOT create a duplicate issue
3. **Create new issues only when:**
   - No existing issue covers the work
   - The work is substantially different from existing issues
   - A new EPIC or major feature is being started

### Sub-Issue Usage
- Use sub-issues for component breakdown within an EPIC
- Link sub-issues to parent EPIC via issue dependencies
- Document sub-issue completion in parent EPIC
- Close sub-issues when components are complete

### Issue Structure
Every issue must include:
- **Clear title** with component and phase (e.g., "[EPIC] Phase 4: Production Database Infrastructure")
- **Parent EPIC reference** if applicable
- **Status section** (Pending, In Progress, Completed, Blocked)
- **Delivered components** list with file paths
- **Sub-issues** section for component breakdown
- **Technical details** section
- **Testing strategy** section
- **Related files** section
- **Next steps** section

### Progress Documentation
- Document all progress in the original issue
- Use checklist format for deliverables
- Add comments for significant milestones
- Reference commits and pull requests
- Update status as work progresses

### Preventing Duplication
- Never create multiple issues for the same work
- If work spans multiple sessions, update the same issue
- Use comments to document session-by-session progress
- Close issues only when fully complete, not between sessions

## Agent Documentation

### Core Architecture
- **Architecture rules:** docs/agents/architecture_agent.md
- **Python rules:** docs/agents/python_agent.md
- **SQL rules:** docs/agents/sql_agent.md
- **ML rules:** docs/agents/ml_agent.md
- **Live ingestion rules:** docs/agents/live_agent.md
- **Documentation rules:** docs/agents/docs_agent.md

### Project Management
- **Project objectives:** docs/agents/PROJECT_OBJECTIVES.md
- **Current snapshot:** docs/agents/CURRENT_SNAPSHOT.md
- **Next steps:** docs/agents/next_steps.md
- **Procedures:** docs/agents/PROCEDURES.md
- **Feature population:** docs/agents/FEATURE_POPULATION_PROCEDURE.md
- **Modeling workflows:** docs/agents/MODELING_WORKFLOWS.md

### Reference
- **File inventory:** docs/agents/FILE_INVENTORY.md
- **Utility functions:** docs/agents/UTILITY_FUNCTIONS.md
- **Adaptation map:** docs/agents/ADAPTATION_MAP.md
- **Reproducibility audit:** docs/agents/REPRODUCIBILITY_AUDIT_PROMPT.md

### Historical
- **EdgeForge agent:** docs/agents/EdgeForge.agent.md
- **ZSH SQL mangling fix:** docs/agents/ZSH_SQL_MANGLING_FIX.md

## Repo-Specific Priority

This repo already contains important working assets:

- retrosheet/ package for historical parsing
- scripts/bridge/ for xref workflows
- scripts/data_ingestion/ for live and source-specific ingestion
- scripts/external_data/ for enrichment loads
- sql/live, sql/external, sql/bridge for warehouse behavior

Wrap and reorganize these. Do not discard them casually.
