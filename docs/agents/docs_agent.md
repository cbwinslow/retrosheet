# Documentation Agent Guidance

**Role**: Documentation, comments, FILE_INVENTORY maintenance, PROJECT_LOG updates, and knowledge management.

---

## Scope

You are responsible for:
- `README.md` maintenance
- `docs/agents/FILE_INVENTORY.md` updates
- `docs/agents/PROCEDURES.md` maintenance
- `docs/PROJECT_LOG.md` updates
- Code comments and docstrings
- SQL file headers
- Migration documentation
- API documentation (future)

---

## Key Documents

| Document | When to Use |
|----------|-------------|
| `AGENTS.md` | Top-level agent guidance |
| `docs/migration_map.md` | File reorganization tracking |
| `docs/agents/FILE_INVENTORY.md` | File ownership and status |

---

## Documentation Principles

1. **Write as you go** - Never defer documentation
2. **Single source of truth** - FILE_INVENTORY owns the file list
3. **Version controlled** - All docs in git
4. **Searchable** - Use clear headings and structure
5. **Actionable** - Include examples and commands

---

## FILE_INVENTORY.md

### Purpose

Central registry of all files in the repository with:
- File purpose and ownership
- Current status (active, deprecated, experimental)
- Dependencies and relationships
- Migration status (for migration phase)

### Format

```markdown
## Section: Data Ingestion

| File | Purpose | Status | Owner | Notes |
|------|---------|--------|-------|-------|
| `scripts/data_ingestion/fetch_mlb_schedule.py` | MLB schedule fetcher | ACTIVE | Live Agent | Wrap into MlbSource |
| `scripts/data_ingestion/fetch_espn_complete.py` | ESPN data fetcher | ACTIVE | Live Agent | Wrap into EspnSource |
| `baseball/sources/mlb.py` | MLB source adapter | NEW | Live Agent | Phase 3 |
```

### Update Triggers

Update FILE_INVENTORY.md when:
- New file created
- File moved or renamed
- File deprecated
- File ownership changes
- Migration status changes

---

## PROJECT_LOG.md

### Purpose

Chronological log of significant work completed with:
- What was done
- Why it was done
- Validation metrics
- Row counts, performance numbers
- Next steps decided

### Format

```markdown
## 2026-04-26: Migration Planning Complete

**What**: Created Phase 0 planning documents
**Why**: Establish clear migration path for baseball CLI
**Files Created**:
- `docs/migration_plan.md` - 40 tasks across 7 phases
- `docs/migration_map.md` - 162 file mappings
- `docs/migration_backlog.md` - Detailed backlog
- `docs/architecture.md` - Target architecture
- `docs/keys_and_grains.md` - Entity keys

**Metrics**:
- Planning docs: 5 complete
- Total tasks identified: 162
- Est. effort: 8 weeks

**Decisions**:
- Typer for CLI framework
- Layered SQL folders (00-80)
- Pydantic for settings

**Next**: Begin Phase 1 implementation
```

### Entry Template

```markdown
## YYYY-MM-DD: Brief Description

**What**: 
**Why**: 
**Files Changed**: 
**Metrics**: 
**Decisions**: 
**Next**: 
```

---

## README.md

### Structure

```markdown
# Project Name

## Quick Start

## Installation

## Usage

## Architecture

## Development

## Contributing
```

### Migration Updates

During migration, add a "Migration Status" section:

```markdown
## Migration Status

We are migrating to a unified `baseball` CLI.

| Phase | Status | Description |
|-------|--------|-------------|
| 0 - Planning | ✅ Complete | Docs created |
| 1 - Foundation | 🔄 In Progress | Package skeleton |
| 2 - Retrosheet | ⏳ Pending | Historical adapter |

### Legacy Commands (Still Work)
- `make pipeline` - Run full pipeline
- `scripts/warehouse.py` - Warehouse operations

### New Commands (Partial)
- `baseball doctor` - Health check ✅
- `baseball mlb download` - Live download ⏳
```

---

## SQL File Headers

Every SQL file must have this exact format:

```sql
/*
File: sql/30_core/301_core_teams.sql
Purpose: Create core teams table
Author: Agent [identifier]
Date: 2026-04-26
Depends On: 000_admin_database_init.sql
Called By: scripts/migrate_core_tables.sh

Tables Created:
- core.teams (canonical team entities)

Notes:
- One row per franchise per season
- Includes both retrosheet and mlb identifiers
*/
```

### Header Fields

| Field | Required | Description |
|-------|----------|-------------|
| File | Yes | Full path from repo root |
| Purpose | Yes | One sentence description |
| Author | Yes | Agent identifier |
| Date | Yes | ISO format (YYYY-MM-DD) |
| Depends On | No | Prerequisites |
| Called By | No | What calls this |
| Tables Created | Yes | List of objects |
| Notes | No | Special considerations |

---

## Python Docstrings

### Module Docstrings

```python
"""
MLB Stats API source adapter.

This module provides the MlbSource class for ingesting live and historical
data from the official MLB Stats API.

Classes:
    MlbSource: Main adapter implementing BaseSource interface
    MlbConfig: Configuration for MLB API connections

Examples:
    >>> from baseball.sources.mlb import MlbSource
    >>> source = MlbSource(config)
    >>> result = source.download(DownloadConfig(date="2024-04-01"))
"""
```

### Function Docstrings (Google Style)

```python
def download(self, config: DownloadConfig) -> SourceResult:
    """Download games from MLB API for a date.
    
    Args:
        config: Download configuration with date and optional team filter
        
    Returns:
        SourceResult with count of games downloaded and file paths
        
    Raises:
        DownloadError: If API request fails
        RateLimitError: If rate limit exceeded
        
    Example:
        >>> config = DownloadConfig(date="2024-04-01", team="ATL")
        >>> result = source.download(config)
        >>> print(f"Downloaded {result.count} games")
    """
```

---

## Comment Guidelines

### When to Comment

- **Always**: Complex algorithms, business rules, non-obvious logic
- **Never**: Obvious code (e.g., `x = x + 1  # increment x`)
- **Consider**: Workarounds, known issues, TODO items

### Comment Format

```python
# TODO(2026-05-01): Remove this workaround when MLB API v2 is available

# NOTE: Chadwick uses 0-indexed innings, MLB uses 1-indexed
# We standardize on 1-indexed in the warehouse

# WARNING: This query is slow on large date ranges
# Consider using the materialized view instead
```

---

## PROCEDURES.md

### Purpose

Canonical procedures for common workflows:
- Adding a new data source
- Building features
- Training models
- Deploying changes

### Format

```markdown
## Procedure: Adding a New Data Source

### Prerequisites
- Source API documentation
- Database access
- Python environment set up

### Steps
1. Create source adapter in `baseball/sources/`
2. Add SQL for raw tables in `sql/10_raw/`
3. Implement download method
4. Implement ingest method
5. Add CLI command in `baseball/cli.py`
6. Write tests
7. Update FILE_INVENTORY.md

### Validation
```bash
baseball doctor
baseball <source> download --date 2024-04-01
baseball <source> ingest --date 2024-04-01
```

### Troubleshooting
- If download fails: Check API credentials
- If ingest fails: Check SQL file exists
```

---

## Migration Documentation

### Migration Plan Files

| File | Purpose | Audience |
|------|---------|----------|
| `docs/migration_plan.md` | Overall strategy | All agents |
| `docs/migration_map.md` | File mappings | Implementation agents |
| `docs/migration_backlog.md` | Task list | Project tracking |
| `docs/architecture.md` | Target design | Architecture agent |
| `docs/keys_and_grains.md` | Data model | SQL/ML agents |

### Migration Status Tracking

Use emoji status in all docs:

| Status | Emoji | Meaning |
|--------|-------|---------|
| Complete | ✅ | Done, tested, merged |
| In Progress | 🔄 | Being worked on |
| Pending | ⏳ | Not started, ready |
| Blocked | 🚫 | Waiting on dependency |
| Deprecated | ❌ | Old, being removed |

---

## Review Checklist

Before considering documentation complete:

- [ ] FILE_INVENTORY.md updated with new files
- [ ] PROJECT_LOG.md entry for significant work
- [ ] README.md updated if commands changed
- [ ] SQL headers present on all new SQL files
- [ ] Python docstrings on all public functions
- [ ] Code comments for complex logic
- [ ] PROCEDURES.md updated if workflow changed
- [ ] Links between docs work (no broken refs)
- [ ] Markdown linting passes

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Migration Agent | Initial docs agent guidance |
