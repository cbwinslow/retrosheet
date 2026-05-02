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

## Python Namespace Rules

**All Python code MUST exist under the `baseball` namespace.** This ensures:
- Unified imports: `from baseball import X` or `from baseball.module import Y`
- Clean CLI integration: `python -m baseball command`
- No orphaned modules or scattered scripts

### Required Structure

```
baseball/
├── __init__.py          # Exports key classes/functions
├── __main__.py          # CLI entry point
├── core/                # Database, config, logging
├── features/            # Feature engineering
├── models/              # ML models and calibration
├── predictions/         # Live prediction engine
├── ingestion/           # Data ingestion services
└── cli/                 # Typer CLI commands
```

### Creating New Modules

When creating new functionality, always:

1. **Place code in `baseball/` package**, not standalone scripts:
   ```python
   # CORRECT: baseball/features/new_feature.py
   class NewFeatureEngine:
       pass
   ```

2. **Export from module `__init__.py`**:
   ```python
   # baseball/features/__init__.py
   from .new_feature import NewFeatureEngine
   
   __all__ = ['NewFeatureEngine', ...]
   ```

3. **Export from root `baseball/__init__.py`** for top-level access:
   ```python
   # baseball/__init__.py
   from baseball.features import NewFeatureEngine
   
   __all__ = [..., 'NewFeatureEngine']
   ```

4. **Add CLI commands in `baseball/cli/commands/`**:
   ```python
   # baseball/cli/commands/feature.py
   import typer
   
   feature_app = typer.Typer()
   
   @feature_app.command(name='extract')
   def extract_features(...):
       from baseball.features import NewFeatureEngine
       ...
   ```

5. **Register CLI in `baseball/cli/main.py`**:
   ```python
   from baseball.cli.commands.feature import feature_app
   app.add_typer(feature_app, name='feature', help='Feature commands')
   ```

### What NOT to Do

```python
# WRONG: Standalone script outside baseball/
# scripts/new_feature.py
def do_something():
    pass

# WRONG: No __init__.py exports
# baseball/features/new_feature.py exists but can't be imported

# WRONG: Importing from scripts/
from scripts.new_feature import do_something  # Never do this
```

### Scripts Directory Usage

The `scripts/` directory is for **executable entry points only**, not core logic:

```python
# CORRECT: scripts/run_feature_pipeline.py
#!/usr/bin/env python3
from baseball.features import NewFeatureEngine

if __name__ == '__main__':
    engine = NewFeatureEngine()
    engine.run()
```

All reusable logic belongs in `baseball/` package. Scripts should be thin wrappers.

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

---

## Project Architecture Overview

This is a unified baseball prediction platform with a universal CLI tool (`baseball`) that serves as the single entry point for all operations.

### Intended Use

The `baseball` namespace provides a Typer-based CLI that encapsulates the entire project:

```bash
# Data Ingestion (Raw Layer)
baseball ingest retrosheet --seasons 2020-2024 --download --ingest
baseball ingest mlb --seasons 2024 --live
baseball ingest espn --date 2024-05-01
baseball ingest statcast --start 2024-04-01 --end 2024-10-01

# Feature Engineering (Features Layer)
baseball features build --seasons 2020-2024 --pitch-level
baseball features build --seasons 2020-2024 --pa-level

# Model Training (Models Layer)
baseball models train --type pitch-xgboost --seasons 2015-2023
baseball models train --type pa-outcome --seasons 2015-2023
baseball models calibrate --model models/pitch_level/tier1_*.pkl

# Predictions (Predictions Layer)
baseball predict game --game-pk 12345 --monte-carlo --iterations 10000
baseball predict pitch --game-pk 12345 --at-bat 5
baseball predict live --watch --game-pk 12345

# Betting Analysis (Betting Layer)
baseball bet analyze --game 12345 --sportsbook draftkings
baseball bet paper-trade --strategy closing-line-value

# Testing & Quality
baseball test run --all
baseball test run --module features
baseball lint check
```

### Layered Architecture

**Data flows through strict layers:**

```
┌─────────────────────────────────────────────────────────────┐
│  RAW DATA LAYER (Source-Preserved)                           │
│  ├── raw_retrosheet (download → ingest, checksum dedup)     │
│  ├── raw_mlb (live API snapshots)                            │
│  ├── raw_statcast (Statcast pitch-level data)                │
│  ├── raw_espn (supplemental scores/odds)                     │
│  ├── raw_lahman (historical reference)                      │
│  ├── raw_fangraphs (advanced metrics)                        │
│  └── raw_weather (meteorological data)                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  BRIDGE LAYER (Xref Resolution)                              │
│  ├── bridge.player_ids (map external → internal IDs)       │
│  ├── bridge.team_ids (map external → internal IDs)          │
│  └── bridge.game_ids (map external → internal IDs)          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  CORE LAYER (Canonical Data)                                 │
│  ├── core.games (canonical game records)                    │
│  ├── core.events (play-by-play events)                      │
│  ├── core.players (player profiles)                         │
│  ├── core.teams (team profiles)                             │
│  ├── core.live_games (real-time game state)                 │
│  └── core.live_events (real-time play-by-play)              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  FEATURES LAYER (ML-Ready)                                 │
│  ├── features_pitch.* (pitch-level engineered features)      │
│  ├── features_pa.* (plate appearance features)               │
│  ├── features_game.* (game-level features)                   │
│  └── features_player.* (player profile features)             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  MODELS LAYER (Predictions)                                  │
│  ├── baseball/models/pitch_model.py (XGBoost Two-Tier)      │
│  ├── baseball/models/pa_outcome_model.py (PA outcomes)      │
│  ├── baseball/models/win_probability.py (WP model)          │
│  └── baseball/models/calibration.py (ECE, Brier, scaling)    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  PREDICTIONS LAYER (Live Inference)                          │
│  ├── baseball/predictions/live_predictor.py                │
│  ├── baseball/predictions/markov_model.py                  │
│  └── predictions.prediction_log (accuracy tracking)         │
└─────────────────────────────────────────────────────────────┘
```

### Polymorphism & Abstraction

All components use consistent interfaces:

```python
# Base classes enable polymorphism
from baseball.base import BaseSource, BaseModel, BaseFeature

# Any data source can be ingested the same way
source = RetrosheetSource()  # or MLBSource(), ESPNSource()
source.download(config)
source.ingest(config)

# Any model can be trained/evaluated the same way
model = PitchXGBoostModel()  # or PAOutcomeModel(), MarkovPitchModel()
model.train(X, y)
model.evaluate(X_val, y_val)
predictions = model.predict(X_new)

# Any feature set can be built the same way
features = PitchFeatureEngine()  # or PAFeatureEngine(), GameFeatureEngine()
features.build(seasons=[2024])
features.materialize()
```

---

## GitHub Workflow & Project Management

### Milestones

Organize work using GitHub Milestones:

- **Phase 1: Foundation** (Data ingestion, core schema)
- **Phase 2: Features** (Feature engineering pipeline)
- **Phase 3: Models** (ML model training)
- **Phase 4: Live** (Real-time prediction)
- **Phase 5: Betting** (Odds integration, paper trading)

### Issue Hierarchy

```
Milestone: Phase 3 - Models
├── #133: [MODEL-FIRST] Train First Batch of Models: Pitch-Level [IN PROGRESS]
│   └── Sub-tasks (add as sub-issues):
│       - Populate base_features from locations (7.66M pitches)
│       - Build engineered features (tiered targets)
│       - Train Two-Tier XGBoost model
│       - Model calibration (ECE, Brier, temperature scaling)
├── #134: [MODEL-SERVE] Build Model Serving Layer [PENDING]
├── #135: [NL-ROUTER] Natural Language Query Router [PENDING]
└── #136: [MV-PLAYERS] Materialized Views for Star Player Predictions [PENDING]
```

### Pull Request Requirements

**All code changes must go through PRs with:**

1. **Detailed commit messages:**
   ```
   [#133] Add pitch-level base features population script
   
   - Creates populate_pitch_base_features.py for 7.66M pitch migration
   - Batch processing with 100k row chunks
   - Version tagging for reproducibility
   - Verification with row counts and null checks
   
   Relates to model-first pitch-level training pipeline
   ```

2. **PR description template:**
   ```markdown
   ## Summary
   Brief description of changes

   ## Related Issues
   - Closes #123
   - Relates to #456

   ## Changes Made
   - [ ] Feature A
   - [ ] Feature B

   ## Testing
   - [ ] Unit tests pass
   - [ ] Integration tests pass
   - [ ] Manual testing completed

   ## Checklist
   - [ ] Code follows baseball namespace rules
   - [ ] No orphaned files created
   - [ ] AGENTS.md updated if needed
   - [ ] GitHub issue updated with progress
   ```

3. **CI/CD checks must pass:**
   - Linting (ruff, black)
   - Type checking (mypy)
   - Unit tests (pytest)
   - SQL validation

### Progress Documentation

**Update GitHub issues after every session:**

Add comments to existing issues (like #133) with progress:

```markdown
## Progress Update - 2024-05-02

### Completed
- [x] Created `scripts/populate_pitch_base_features.py`
- [x] Implemented batch processing (100k rows)
- [x] Added version tagging system

### In Progress
- [ ] Running pipeline on 7.66M pitches
- Estimated completion: 45 minutes

### Blockers
None

### Next Steps
- Monitor pipeline completion
- Run calibration evaluation
- Add comment to #133 with results

### Files Changed
- `scripts/populate_pitch_base_features.py` (new)
- `baseball/models/calibration.py` (new)
- `baseball/models/__init__.py` (updated exports)
```

---

## Code Consolidation Rules

### Always Check Existing Code First

Before creating new files:

1. **Search for similar functionality:**
   ```bash
   grep -r "class.*Model" baseball/
   grep -r "def ingest" scripts/
   find scripts -name "*ingest*.py" | head -20
   ```

2. **Evaluate: Update existing vs. create new**
   - If 70%+ overlap → Update existing file
   - If truly new domain → Create new file
   - If variant of existing → Extend existing with parameters

3. **Prevent orphaned files:**
   - ❌ Don't create: `scripts/ingest_mlb_new.py` (variant of existing)
   - ✅ Update: `scripts/data_ingestion/ingest_mlb.py` (add new method)

### Consolidation Examples

```python
# GOOD: Single unified ingestion script
# scripts/data_ingestion/unified_retrosheet.py
class RetrosheetSource(BaseSource):
    def download(self, config): ...
    def ingest(self, config): ...
    def bootstrap(self): ...

# GOOD: Feature engines in one module
# baseball/features/pitch_features.py
class PitchFeatureEngine:
    def build_base(self, seasons): ...
    def build_engineered(self, version): ...
    def materialize(self): ...

# BAD: Scattered feature scripts
# scripts/build_pitch_features_v1.py
# scripts/build_pitch_features_v2.py
# scripts/build_pitch_features_new.py
```

### File Size Guidelines

- **Scripts**: 100-500 lines ideal, <1000 lines max
- **Modules**: 200-800 lines ideal, split if >1500 lines
- **SQL files**: Related tables in one file, <500 lines

---

## CI/CD & GitHub Actions

### Required Workflows

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e .[dev]
      - name: Lint
        run: ruff check baseball/ scripts/
      - name: Type check
        run: mypy baseball/
      - name: Test
        run: pytest tests/ -v --tb=short
```

### Branch Protection

- `main` branch requires PR + 1 review + CI passing
- Feature branches: `feature/epic-80-pitch-model`
- Bugfix branches: `fix/calibration-temperature-scaling`

---

## Data Source Bootstrap Procedures

Each data source has its own bootstrap procedure:

```bash
# Retrosheet bootstrap (historical games)
baseball bootstrap retrosheet --from-scratch

# MLB bootstrap (live feed)
baseball bootstrap mlb --season 2024

# Statcast bootstrap (pitch-level data)
baseball bootstrap statcast --seasons 2015-2025

# ESPN bootstrap (scores/odds)
baseball bootstrap espn --season 2024

# Lahman bootstrap (reference data)
baseball bootstrap lahman --full

# FanGraphs bootstrap (advanced metrics)
baseball bootstrap fangraphs --season 2024

# Weather bootstrap (venue weather)
baseball bootstrap weather --venues all
```

### Bootstrap Pattern

```python
# Each bootstrap creates:
# 1. Raw schema (if not exists)
# 2. Download tables
# 3. Ingest tables
# 4. Checksum tracking tables
# 5. Initial data load (optional)

class BootstrapCommand:
    def run(self, source, **kwargs):
        schema = f"raw_{source}"
        self.create_schema(schema)
        self.create_download_table(schema)
        self.create_ingest_table(schema)
        self.create_checksum_table(schema)
        if kwargs.get('initial_load'):
            self.initial_load(source, kwargs)
```

---

## Testing Integration

All tests accessible via CLI:

```bash
# Run all tests
baseball test run

# Run specific module
baseball test run --module features
baseball test run --module models
baseball test run --module predictions

# Run with coverage
baseball test run --coverage --threshold 80

# Integration tests
baseball test integration --live-feed
baseball test integration --model-prediction

# Performance tests
baseball test performance --query-runtime
baseball test performance --inference-latency
```

### Test Organization

```
tests/
├── unit/
│   ├── test_features.py
│   ├── test_models.py
│   └── test_predictions.py
├── integration/
│   ├── test_ingestion.py
│   ├── test_live_feed.py
│   └── test_end_to_end.py
└── fixtures/
    ├── sample_games.json
    └── sample_pitches.json
```

---

## Documentation Migration to GitHub

Migrate these docs to GitHub issues:

| Document | Migration Strategy |
|----------|-------------------|
| CURRENT_SNAPSHOT.md | Convert Epics to GitHub Issues with sub-issues |
| next_steps.md | Create milestone with prioritized issues |
| MODELING_WORKFLOWS.md | Create discussion thread + linked issues |
| FEATURE_POPULATION_PROCEDURE.md | Keep as wiki, link from issues |

Keep in docs/:
- AGENTS.md (this file)
- FILE_INVENTORY.md (reference)
- PROCEDURES.md (detailed workflows)
- UTILITY_FUNCTIONS.md (code snippets)

---

## Summary: Agent Rules Checklist

When working on this project, always:

- [ ] **Use baseball namespace**: All code under `baseball/` package
- [ ] **CLI integration**: Register commands in `baseball/cli/`
- [ ] **Check existing code**: Search before creating new files
- [ ] **Consolidate**: Update existing files when possible, prevent orphans
- [ ] **Layered data**: Raw → Bridge → Core → Features → Models
- [ ] **Bootstrap pattern**: Separate download/ingest for each source
- [ ] **GitHub workflow**: Use existing issues (#133, #134, etc.) → PRs → Detailed commits
- [ ] **Update issues**: Comment progress on actual GitHub issues after every session
- [ ] **No imaginary issues**: Only reference issue numbers that exist in GitHub
- [ ] **CI/CD**: All PRs must pass tests, linting, type checks
- [ ] **Testing**: Comprehensive tests for all generated code
- [ ] **Polymorphism**: Use base classes for interchangeable components
- [ ] **Documentation**: Update AGENTS.md when patterns change
