# Agent Operating Guide

This project builds a reproducible baseball prediction warehouse from free/open data sources.

## Mission

- Build a PostgreSQL warehouse from Retrosheet historical data.
- Use Chadwick tools as the authoritative parser layer for Retrosheet event files.
- Add MLB Stats API / GUMBO live data ingestion for real-time prediction.
- Build ML-ready features that can train on historical game states and score live games.
- Later, compare model probabilities with public prediction-market prices such as Kalshi and Polymarket. Treat any market-related work as research tooling, not financial advice.

## Non-Negotiables

- Before creating new SQL, scripts, models, routes, or docs, check `docs/agents/FILE_INVENTORY.md` and `docs/agents/PROCEDURES.md` to see whether an existing workflow already owns the job.
- Keep source-preserved raw data. Do not overwrite or discard raw Retrosheet, Chadwick, or MLB API payloads.
- Prefer additive migrations and views over destructive schema changes.
- Keep `README.md` current when commands, setup, or workflow changes.
- Keep this `AGENTS.md` current when project conventions change.
- Add and maintain backup procedures for database objects. See `scripts/utility/backup_procedures.sh`.
- Keep `docs/agents/` current when file purposes, modeling goals, or canonical procedures change.
- Keep `docs/PROJECT_LOG.md` current with significant completed work, validation counts, and next-step decisions.
- Treat unintegrated `EdgeForge` / `mlb_features` / `mlb_models` / `mlb_enhanced` files as experimental until they are explicitly merged into the canonical warehouse layers and documented in `docs/agents/FILE_INVENTORY.md`. See `docs/EDGEFORGE_TRIAGE.md`.
- Use Chadwick-generated headers and documented field names instead of hand-invented column mappings.
- Put database typing, constraints, foreign keys, indexes, and reusable ML features in `core`, `features`, `models`, and `predictions`, not in raw landing tables.
- Maintain reproducibility: scripts should run from a clean checkout with documented dependencies.
- Default database target is the local PostgreSQL database named `retrosheet` on port `5432`, unless `DATABASE_URL` or `PG*` environment variables override it.
- Do not require Git LFS. Keep generated data and model binaries out of git; scripts and database metadata must be enough to regenerate artifacts.

## REPRODUCIBILITY MANDATE (CRITICAL)

**Every action must leave a paper trail. This is not optional.**

### SQL-First Development Rule

**ALL database operations must be stored in .sql files under version control.**

- **NEVER execute ad-hoc SQL against the database without saving it first.**
- **NEVER use database GUI tools or CLI to make schema changes.**
- **ALWAYS write SQL to a file, commit it, then execute the file.**

**Workflow:**
```
1. Create/edit .sql file in appropriate sql/ subdirectory
2. Add header comment with purpose, date, author
3. Test the SQL file: psql -f sql/path/to/file.sql
4. Commit the SQL file with descriptive message
5. Update docs/agents/FILE_INVENTORY.md with the new file
6. Update docs/agents/PROCEDURES.md if it creates a canonical workflow
```

### Script Wrapper Requirement

**All data pipelines must have wrapper scripts that call more granular procedures.**

- Create orchestrator scripts like `update_all_pitch_data.sh` that call:
  - `load_statcast_season_2025.sql`
  - `refresh_pitch_features.sql`
  - `update_pitcher_arsenals.sql`
- Each granular script must be independently runnable
- Wrapper scripts must log what they call and in what order

### Documentation Requirements

**Every SQL file must include at the top:**
```sql
/*
File: sql/features/010_pitcher_arsenal_features.sql
Purpose: Build pitcher arsenal features from Statcast pitch data
Author: Agent [identifier]
Date: 2026-04-24
Depends On: features_pitch.locations, features_pitch.base_features
Called By: scripts/pitch_data/update_all_pitch_features.sh

Tables Created:
- features.pitcher_arsenals (pitcher-level aggregated metrics)
- features.pitcher_repertoire (pitch-type breakdowns)

Notes:
- Uses 30-day rolling windows
- Excludes pitches with null release_speed
*/
```

**Every table must have COMMENT ON statements:**
```sql
COMMENT ON TABLE features.pitcher_arsenals IS 'Aggregated pitcher arsenal metrics by season';
COMMENT ON COLUMN features.pitcher_arsenals.fastball_pct IS 'Percentage of fastballs thrown (FF, FT, FC, SI)';
```

### The Paper Trail Checklist

Before completing ANY task, verify:

- [ ] All SQL saved in version-controlled .sql files
- [ ] All scripts saved in version-controlled files
- [ ] Table/column comments added for new schema objects
- [ ] FILE_INVENTORY.md updated with new files
- [ ] PROCEDURES.md updated with new workflows
- [ ] PROJECT_LOG.md updated with what was accomplished
- [ ] Row counts/validation metrics recorded
- [ ] Git commit made with descriptive message
- [ ] E2E tests pass (`scripts/test/e2e_test_runner.sh` or similar)

### Scientific Reproducibility Standard

This project must be reproducible by other researchers. Every number we report must be traceable to:

1. **Source data**: Which raw table and fetch date
2. **Transformation**: Which SQL file performed the transformation
3. **Model training**: Which script, with what hyperparameters
4. **Evaluation**: Which validation set, what metrics

**When publishing results, we must show our work.**

### E2E Testing Environment (Free Local Setup)

**Yes, you can run E2E tests for free on your PC.** No Docker, no cloud, no additional cost.

#### Test Infrastructure

- **Test Schema**: `test` schema in existing PostgreSQL database - isolated from production
- **Test Fixtures**: Small, fast datasets (100 games instead of 62,000)
- **Test Scripts**: Bash scripts in `scripts/test/` that validate everything works
- **Validation**: Automated checks for headers, comments, row counts

#### Running Tests

```bash
# Quick validation (5 minutes)
./scripts/test/validate_sql_files.sh

# Run E2E test suite
./scripts/test/e2e_test_runner.sh --quick

# Full rebuild verification (30+ minutes)
./scripts/test/verify_rebuild.sh
```

#### AI Agent Gap-Fill Loop

When another agent fills documentation gaps, they use this loop:

1. **RUN** `validate_sql_files.sh` to find missing headers
2. **CREATE** missing SQL files/scripts to close gaps
3. **ADD** headers, comments, documentation
4. **TEST** with `e2e_test_runner.sh`
5. **COMMIT** when tests pass
6. **REPEAT** until all tests pass

#### Test Files (Created by Audit Agent)

- `sql/test/001_create_test_schema.sql` - Test schema setup
- `sql/test/002_test_fixtures.sql` - Test data fixtures
- `scripts/test/e2e_test_runner.sh` - Main test runner
- `scripts/test/validate_sql_files.sh` - SQL validation
- `scripts/test/verify_rebuild.sh` - Rebuild verification

### Never Again List

**NEVER do these things:**
- Execute SQL in psql/pgAdmin/DBeaver without saving to a file first
- Make "quick fixes" directly to the database
- Create scripts that aren't committed
- Leave tables without documentation
- Assume "I'll document it later" (document NOW)
- Use hardcoded values without explanation
- Skip validation/verification steps

### For Live Data Operations

When updating models with live data:
1. Save the query that extracts features as .sql
2. Save the model scoring script
3. Save the results validation query
4. Create a wrapper procedure that runs the full pipeline
5. Document the expected inputs/outputs

## Python Environment Standard

This project uses **uv** as the official package manager with **Python 3.10** as the standard runtime. Environment activates automatically when cd'ing into the project directory via direnv.

### Setup
```bash
# On first checkout
direnv allow .

# Install all dependencies
uv sync --all-extras
```

### Usage
```bash
# Run scripts
uv run python scripts/your_script.py

# Manage dependencies
uv add <package>
uv add --dev <package>
uv sync
uv lock
```

All project scripts, CI, and environments use Python 3.10. Legacy `requirements.txt` is archived and no longer maintained.

## Data Layers

- `raw_retrosheet`: source-preserved Chadwick extracts and Retrosheet reference tables.
- `raw_mlb`: source-preserved MLB Stats API / GUMBO schedules, live game feeds, reference endpoint snapshots, and Statcast pitch-level tracking data.
  - `raw_mlb.statcast`: 7.8M pitch-level Statcast records (2015-2025) with plate_x/plate_z coordinates, launch_speed, spin_rate
- `raw_espn`: source-preserved ESPN API data for MLB games, schedules, and statistics.
- `bridge`: cross-reference tables between Retrosheet IDs, MLB IDs, Lahman IDs, ESPN IDs, and other public IDs. Includes player_xref, team_xref, game_xref, park_xref, coach_xref, umpire_xref, external_player_xref, external_team_xref.
- `core`: canonical baseball entities, typed MLB reference views, and game-state views shared by historical and live sources.
  - `core.games`: 62,598 historical games
  - `core.events`: 4.9M play-level events
  - `core.plate_appearances`: 4.8M plate appearance outcomes
- `features`: ML-ready training and inference tables.
  - `features_pitch.locations`: PostGIS-enabled pitch location table with geometry column
- `predictions`: model outputs, backtests, and live prediction snapshots.

### Pitch-Level Data Access

**Raw Source Data:**
- `raw_mlb.statcast`: Source-preserved Statcast data from Baseball Savant
  - **Count**: 7,797,034 pitch-level records (2015-2025 seasons)
  - **Fields**: 118 Statcast columns including pitch metrics, physics, expected stats, win probability

**Feature Table (Complete Load):**
- `features_pitch.locations`: 7,661,992 pitches (2015-2025) with ALL Statcast fields
  - **Core**: game_year, game_pk, game_date, batter_id, pitcher_id, player_name
  - **Pitch**: pitch_type, pitch_name, pitch_number, pitch_result, description, events
  - **Count/State**: balls, strikes, outs_when_up, inning, on_1b, on_2b, on_3b
  - **Release/Physics**: start_speed, effective_speed, release_spin_rate, spin_axis, release_pos_x/y/z, release_extension
  - **Movement/Location**: pfx_x, pfx_z, plate_x, plate_z, zone, sz_top, sz_bot, **PostGIS geometry**
  - **Physics Components**: vx0, vy0, vz0, ax, ay, az
  - **Hit Data**: hc_x, hc_y, hit_location, bb_type, launch_speed, launch_angle, hit_distance
  - **Expected Stats**: estimated_ba, estimated_woba, estimated_slg, woba_value, woba_denom
  - **Scoring**: home_score, away_score, bat_score, fld_score, post_* variants
  - **Win Probability**: delta_home_win_exp, delta_run_exp, home_win_exp, bat_win_exp
  - **Fielding**: fielder_2-9, if_fielding_alignment, of_fielding_alignment

**Key Fields for GIS Mapping:**
- `plate_x`: Horizontal position (-17 to +17 inches, 0 = center of plate)
- `plate_z`: Vertical position (feet from ground)
- `sz_top`: Top of strike zone for batter
- `sz_bot`: Bottom of strike zone for batter
- `location`: PostGIS geometry column (ST_SetSRID(ST_MakePoint(plate_x, plate_z), 4326))

**Verification Status**: ✅ All 11 seasons loaded (2015-2025), 7.66M pitches, 90 columns, row counts verified against raw_mlb.statcast

**Loading Script:**
```bash
# Load all seasons with verification
python scripts/pitch_data/load_all_statcast_full.py --all

# Verify existing data
python scripts/pitch_data/load_all_statcast_full.py --verify

# Load specific season
python scripts/pitch_data/load_all_statcast_full.py --seasons 2025
```

**Linking to Plate Appearances:**
```sql
-- Link pitches to retrosheet games via bridge
SELECT p.*, gx.retrosheet_game_id, e.event_id
FROM features_pitch.locations p
JOIN bridge.game_xref gx ON p.game_pk::text = gx.mlb_game_pk::text
JOIN core.events e ON gx.retrosheet_game_id = e.game_id
WHERE p.game_pk = <GAME_PK>;
```

### Pitch-Level Feature Engineering (Epic #78)

**Feature Mart Tables:**
| Table | Rows | Purpose | Status |
|-------|------|---------|--------|
| `features_pitch.base_features` | 7,661,992 | 118 Statcast fields preserved | ✅ Populated |
| `features_pitch.engineered_features` | 7,661,992 | Derived ML features | ✅ Built |
| `features_pitch.player_context` | - | Rolling player statistics | 🔄 Schema ready |

**Engineered Features (ALL Research-Backed, No Dropping):**

| Category | Features | Research Source |
|----------|----------|-----------------|
| **Velocity** | `velocity_percentile`, `velocity_diff_from_avg`, `velocity_bucket`, `velocity_change_from_prev` | SMU/CMU pitch papers |
| **Strike Zone** | `distance_from_center`, `zone_region`, `is_in_zone`, `is_shadow`, `is_chase`, `pitch_distance_from_heart` | Zone judgment models |
| **Movement** | `horizontal_break`, `vertical_break`, `approach_angle`, `spin_efficiency`, `induced_vertical_break`, `spin_axis_quadrant`, `is_backspin`, `is_topspin`, `is_gyro_spin` | Pitch physics |
| **Game Context** | `score_diff`, `is_late_game`, `is_high_leverage`, `base_state_code`, `run_expectancy_24`, `win_probability_added`, `inning_phase`, `is_save_situation` | Win probability |
| **Count** | `is_full_count`, `is_two_strike`, `is_three_ball`, `count_leverage_index`, `is_payoff_pitch`, `is_pitcher_ahead`, `is_hitter_ahead` | Count dynamics |
| **Sequential** | `prev_pitch_type`, `prev_pitch_result`, `consecutive_same_type`, `pitches_since_last_swing` | Pitch sequencing research |
| **TTOP** | `times_through_order_detailed`, `is_first_time_seeing_pitcher`, `ttop_penalty_applies` | Times Through Order Penalty |
| **Matchup** | `is_same_handed_matchup`, `is_platoon_advantage_pitcher`, `prior_matchup_count` | Platoon advantage |
| **Pitch Quality** | `pitch_quality_score`, `is_primary_pitch_type`, `pitch_type_family` | Pitch quality models |
| **Environmental** | `is_day_game`, `game_month`, `is_opening_series` | Environmental effects |
| **Pressure** | `pa_pressure_index`, `is_high_pressure_pa`, `is_walk_off_situation`, `leverage_index_bracket` | High-leverage performance |

**Outcome Labels (Two-Tier Hierarchy):**
- **Tier 1** (Coarse): S (Strike, 69.9%), X (Ball-in-Play, 26.9%), B (Ball, 3.2%)
- **Tier 2** (Fine): Strikeout, Walk, Single, Double, Triple, HR, Out, HBP, Foul, Ball, Strike, Other

**Training Data:**
- Valid Pitches: 5,072,278 (excludes 'U' unknown outcomes)
- Stratified sampling for balanced class representation
- **110+ engineered features** across 11 categories, all research-backed
- **118 raw Statcast fields** preserved in base_features
- **Total feature space: 230+ columns** for maximum model coverage

**Scripts:**
```bash
# Populate base features from locations
python scripts/pitch_data/populate_base_features.py

# Build engineered features (run in order)
psql -f sql/features/005_build_engineered_features.sql

# Populate additional features (run batches until complete)
for i in {1..80}; do
    psql -f sql/features/008_populate_additional_features_batch.sql
done

# Populate more features from KB research (run batches until complete)
for i in {1..80}; do
    psql -f sql/features/011_populate_more_features_batch.sql
done

# Train Tier-1 XGBoost model
python scripts/pitch_models/train_tier1_xgboost.py
```

**GitHub Issues:**
- Epic #78: Pitch-Level Model Pipeline (Phase 4 In Progress)
- Sub-Issue #79: Flexible Feature Mart Schema (✅ Complete)

## PostgreSQL Extensions and Features

### Researched Extensions

The following PostgreSQL extensions have been researched for in-database ML and analytics:
- **pg_cron**: Job scheduling for automated pipeline (critical for automation) - [docs/POSTGRESQL_EXTENSIONS_RESEARCH.md](docs/POSTGRESQL_EXTENSIONS_RESEARCH.md)
- **pg_stat_statements**: Query performance monitoring - [docs/POSTGRESQL_EXTENSIONS_RESEARCH.md](docs/POSTGRESQL_EXTENSIONS_RESEARCH.md)
- **pl/python3u**: Python integration for advanced ML - [docs/POSTGRESQL_EXTENSIONS_RESEARCH.md](docs/POSTGRESQL_EXTENSIONS_RESEARCH.md)
- **pgvector**: Vector similarity search for embeddings and AI/ML applications (recommended first) - [docs/POSTGRESQL_EXTENSIONS_RESEARCH.md](docs/POSTGRESQL_EXTENSIONS_RESEARCH.md)
- **MADlib**: Open-source library for scalable in-database analytics and traditional ML
- **PostgresML**: In-database ML/AI with GPU acceleration and LLM integration
- **TimescaleDB**: Time-series data analysis for player performance over seasons

### Installation Scripts

SQL maintenance scripts have been created for extension installation:
- `sql/maintenance/001_check_extensions.sql` - Check currently installed extensions
- `sql/maintenance/002_install_pg_cron.sql` - Install pg_cron with validation
- `sql/maintenance/003_install_pg_stat_statements.sql` - Install pg_stat_statements
- `sql/maintenance/004_install_pl_python3u.sql` - Install PL/Python3u with test function
- `sql/maintenance/005_install_pgvector.sql` - Install pgvector with similarity search test
- `sql/maintenance/010_array_types.sql` - Implement array types for pitch sequences
- `sql/maintenance/011_custom_types.sql` - Implement domain types for data validation
- `sql/maintenance/012_partial_indexes.sql` - Implement partial indexes for optimization
- `sql/maintenance/999_master_installation.sql` - Master orchestrator for all installations

### Advanced PostgreSQL Features

- **Array Types**: For multi-value features (pitch sequences, injury history, recent performance)
- **Custom Types (Domains)**: For baseball-specific data validation (pitch types, event types, hand types)
- **Partial Indexes**: For conditional query optimization (recent games, active players, high-leverage situations)
- **Expression Indexes**: For computed columns (OPS, wOBA, derived features)

See [docs/POSTGRESQL_EXTENSIONS_RESEARCH.md](docs/POSTGRESQL_EXTENSIONS_RESEARCH.md) for detailed research and implementation plan.

## Required Agent References

Use these docs as the project map:

- `docs/agents/PROJECT_OBJECTIVES.md`: prediction-engine objectives, modeling goals, and non-goals.
- `docs/agents/CURRENT_SNAPSHOT.md`: shortest handoff doc for current architecture, model status, blockers, and next steps.
- `docs/agents/FILE_INVENTORY.md`: inventory of SQL, scripts, docs, interface routes, generated artifacts, and ownership.
- `docs/agents/PROCEDURES.md`: canonical workflows for warehouse rebuilds, target creation, feature marts, model training, simulation, live bridge work, interface changes, and GitHub issues.
- `docs/agents/MODELING_WORKFLOWS.md`: target/model inventory, evaluation priorities, Moneyball-style modeling goals, leakage checklist, and promotion rules.

### Knowledge Base Documents

Research-backed knowledge base for sabermetrics, modeling, and PostgreSQL features:
- `docs/KNOWLEDGE_BASE_SABERMETRICS.md`: Research findings on sabermetrics, baseball modeling, and prediction approaches
- `docs/KNOWLEDGE_BASE_MODELS_REPOS.md`: Research on useful baseball models and GitHub repositories for ML and sabermetrics
- `docs/TABLE_ASSESSMENT_SABERMETRICS.md`: Assessment of current table structure for sabermetrics and baseball modeling requirements
- `docs/POSTGRESQL_EXTENSIONS_RESEARCH.md`: Research-backed recommendations for PostgreSQL extensions and features for baseball analytics
- `docs/LIVE_BETTING_PIPELINE_STATUS.md`: Comprehensive status assessment for live betting and prediction infrastructure
- `docs/BRIDGE_TABLE_RESEARCH.md`: Research on authoritative baseball ID mapping sources and bridge table schema details

If a file is not listed there and you make it important, update the inventory in the same change.

## GitHub Organization

### Project Board
Main project board for tracking retrosheet warehouse development work:
- **URL**: https://github.com/users/cbwinslow/projects/22
- **Title**: Retrosheet Warehouse Roadmap
- **Owner**: cbwinslow (user-level project)

### Project Items
The project board contains items tracking key work areas:
- PostgreSQL Extensions Installation
- Sabermetrics Integration
- Maintenance Schema Implementation
- Issue #60: PostgreSQL Maintenance Schema
- Issue #61: PostgreSQL Extensions Installation
- Issue #62: Sabermetrics Integration
- Issue #31: Live PA Outcome Scoring
- Issue #59: ESPN MLB Data Integration
- Issue #30: Live PA Feature Parity

### Labels
The repository uses 50 labels for organizing work by type, domain, and priority:

**Work Type Labels:**
- enhancement (default)
- bug
- documentation
- duplicate
- good first issue
- help wanted
- invalid
- question
- wontfix

**Domain Labels:**
- warehouse - Database warehouse and schema work
- ml - Machine learning models and features
- live-data - MLB live feed ingestion and bridging
- data-quality - Data validation, identity resolution, and quality checks
- data - Data-related tasks
- agents - AI agent and chat workflows
- docs - Documentation and reproducibility
- markets - Prediction market ingestion and edge analysis
- ci - Continuous integration and reproducibility automation
- automation - Automation tasks
- bridge-tables - Bridge table work
- data-ingestion - Data ingestion tasks
- statcast - Statcast-specific work

**Status Labels:**
- completed - Completed work records

**Priority Labels:**
- priority:high - High priority items
- priority:medium - Medium priority items

**Other Labels:**
- infrastructure - Infrastructure and setup tasks
- repo-admin - Repository setup and governance
- security - Security-related tasks
- validation - Validation tasks
- audit - Audit tasks
- real-time - Real-time processing tasks
- orchestration - Orchestration tasks
- tools - Tool-related tasks
- ai - AI-related tasks
- llm - LLM-related tasks
- core - Core functionality
- monitoring - Monitoring tasks
- ui - UI-related tasks
- analytics - Analytics tasks
- feature-mart - Feature mart work
- predictions - Prediction-related tasks
- model-activation - Model activation work
- mcp - MCP-related tasks
- research - Research tasks
- milestone - Milestone markers
- size:XS, size:XXL - PR size indicators

### Issue Organization
Issues are organized using:
- Labels for categorization by domain, type, and priority
- Project board for tracking work items
- Comments linking related issues and documentation
- Parent/child issue relationships for large tasks

### Milestones
Milestone creation via GitHub API is currently blocked by 404 errors. Milestones should be created via the GitHub web interface or investigated for API access issues.

### GitHub Issue Linking Policy
When creating or updating GitHub issues:
- Link to relevant documentation in docs/agents/
- Link to related GitHub issues using #issue-number format
- Link to relevant SQL files, scripts, and code
- Add comments to track decisions and rationale
- Use labels consistently with existing conventions
- Add items to the project board for tracking
- Reference knowledge base documents when applicable

## AI Agent Documentation Update Protocol

**CRITICAL: After every significant conversation, AI agents MUST update documentation to maintain project continuity.**

### Required Documentation Updates

After completing work, AI agents must update:

1. **CRISP-DM Implementation Plan** (`docs/CRISP_DM_IMPLEMENTATION_PLAN.md`)
   - Update phase completion percentages
   - Add milestone achievements with dates
   - Update "Next Phase Actions" with completed items
   - Link to relevant GitHub issues

2. **Research Paper** (`docs/research_paper.md`)
   - Add experimental results from model training
   - Document mathematical formulations for new models
   - Include equations, loss functions, and evaluation metrics
   - Reference external research papers

3. **Current Snapshot** (`docs/agents/CURRENT_SNAPSHOT.md`)
   - Update "Current Objective" section
   - Refresh "Current Data State" with row counts
   - Update "Best Move Right Now" recommendations
   - Document any blockers or dependencies

4. **Agent Operating Guide** (this file, `AGENTS.md`)
   - Update data layer descriptions when schema changes
   - Add new procedures for completed work
   - Document pitch-level features and table structures
   - Update "Non-Negotiables" if conventions change

5. **File Inventory** (`docs/agents/FILE_INVENTORY.md`)
   - Add new SQL files, scripts, and documentation
   - Update ownership and status for modified files
   - Link to related GitHub issues
   - Document deprecated or experimental files

6. **GitHub Issues and Comments**
   - Add progress comments to epics and sub-issues
   - Include specific details: row counts, metrics, file paths
   - Update issue status (open → in progress → closed)
   - Link commits and PRs to issues

### Documentation Update Template

When updating documentation, include:

```markdown
**Date:** YYYY-MM-DD  
**CRISP-DM Phase:** [Current Phase]  
**Epic/Issue:** #[number]  
**Agent:** [AI agent identifier]

### Changes Made
- [Specific change 1]
- [Specific change 2]

### Metrics/Results
- Rows affected: [count]
- Performance: [metrics]
- Accuracy: [if applicable]

### Next Steps
1. [Action item 1]
2. [Action item 2]
```

### Paper Trail Requirements

Every significant work session must leave:

1. **Commit messages** with detailed descriptions
2. **GitHub issue comments** with technical details
3. **Documentation updates** showing what changed and why
4. **Research paper updates** for model/math work
5. **CRISP-DM plan updates** showing phase progress

### Examples of "Significant Work"

**MUST document:**
- Schema changes (new tables, columns, indexes)
- Model training runs (accuracies, loss values, metrics)
- Feature engineering (new derived features, rolling averages)
- Data migrations (row counts, data quality issues)
- Research findings (equations, literature review)
- Bug fixes (root cause, solution, prevention)

**MAY skip:**
- Typo fixes
- Minor formatting changes
- Configuration tweaks without data impact
- Read-only queries for exploration

### Documentation Quality Standards

All documentation must include:

- **Specific numbers:** Row counts, percentages, timestamps
- **File paths:** Absolute paths to relevant files
- **Equations:** LaTeX formatting for mathematical concepts
- **Code snippets:** SQL queries, Python functions
- **Research citations:** Author, year, paper/repo links
- **Decision rationale:** Why this approach was chosen

## Chadwick Procedure

Use the installed Chadwick command-line tools:

- `cwevent`: event/play-level rows.
- `cwgame`: game metadata, lineups, final scores, linescores, managers, umpires.
- `cwdaily`: player game-by-game batting, pitching, and fielding summaries.
- `cwsub`: substitutions.
- `cwcomment`: comments, ejections, and umpire changes.
- `cwbox`: boxscore rendering; useful later, but not the first normalized-table path.

Always include `-n` for new extracts so the first row has official Chadwick column names.

## Live Data Ingestion Procedure

The system supports real-time MLB game data ingestion alongside historical Retrosheet data, maintaining clean separation between data sources.

### Data Separation Architecture

- **Historical Data**: `core.games`, `core.events`, `core.plate_appearances` (Retrosheet/Chadwick sourced)
- **Live Data**: `raw_mlb.live_feed_snapshots` -> `core.live_games`, `core.live_events` (MLB Stats API sourced)
- **Analysis Layer**: `analysis.*` views/materialized views combine both sources for unified querying
- **Bridge Tables**: `bridge.player_xref`, `bridge.team_xref` map IDs between systems

### Live Data Ingestion Workflow

1. **Schedule Discovery**: `python3 scripts/fetch_mlb_schedule.py --yesterday`
   - Discovers active/completed MLB games
   - Identifies games available for ingestion

2. **Game Ingestion**: `python3 scripts/warehouse.py fetch-live-game --game-pk <GAME_PK>`
   - Downloads live game feed from MLB Stats API
   - Stores source-preserved JSON in `raw_mlb.live_feed_snapshots`
   - Persists request params, HTTP status, checksum, game date, and season on new fetches

3. **Data Transformation**: `python3 scripts/transform_live_game.py --game-pk <GAME_PK>`
   - Transforms the latest stored MLB API snapshot to canonical live schema
   - Applies ID mapping via bridge tables
   - Upserts `core.live_games` and `core.live_events`
   - Preserves `raw_payload` and `raw_play` in the live canonical layer

4. **Live Automated Ingestion**: PostgreSQL native pg_cron jobs
   - ✅ Running automatically 24/7 inside the database
   - 10 second interval: primary live feed
   - 15 second interval: all additional endpoints (play-by-play, pitch metrics, win probability, boxscore)
   - 24 hour interval: daily schedule refresh
   - No external scripts required
   - Fully idempotent, no duplicates, immutable storage

5. **Batch Processing**: `python3 scripts/ingest_live_games.py --schedule`
   - Orchestrates discovery and ingestion for multiple games
   - Includes duplicate detection and error handling

5. **Bridge Table Management**: `python3 scripts/populate_bridge_tables.py`
   - Downloads Chadwick Bureau Register (comprehensive player/team ID mappings)
   - Populates `bridge.player_xref` and `bridge.team_xref` tables
   - Enables seamless ID translation between MLB and Retrosheet systems

### Bridge Table Improvements

**Confidence Scoring Framework:**
- All bridge tables now include `confidence_score` (0.0-1.0) and `confidence_source` columns
- Confidence levels: 1.0 (direct), 0.9 (high), 0.8 (medium), 0.7 (low), 0.5 (fuzzy), 0.3 (placeholder), 0.1 (unverified)
- Monitoring views: `bridge.confidence_score_distribution`, `bridge.low_confidence_mappings`, `bridge.confidence_summary_by_source`
- SQL migration: `sql/bridge/910_confidence_scoring.sql`
- Documentation: `docs/CONFIDENCE_SCORING.md`

**Coach Name Resolution:**
- 100% of coaches resolved via `raw_retrosheet.biofile_legacy` (coach_id matches player_id)
- Updated `scripts/bridge/populate_coach_umpire_bridge.py` to use biofile_legacy names
- Confidence score: 0.9 (biofile_legacy_name_match)
- Investigation script: `scripts/bridge/investigate_coach_names.py`

**Umpire Name Resolution:**
- Cross-referenced with biofile_legacy for players who became umpires (2,369 players with umpire debut dates)
- Updated `scripts/bridge/populate_coach_umpire_bridge.py` to include biofile_legacy cross-reference
- Confidence score: 0.9 (biofile_legacy_player_match) or 0.7 (retrosheet_name_only)
- Investigation script: `scripts/bridge/investigate_umpire_ids.py`

**Error Handling Improvements:**
- All bridge scripts now use specific `psycopg2.Error` instead of generic `Exception`
- Scripts updated: `populate_game_xref.py`, `populate_season_aware_team_xref.py`, `populate_external_bridge.py`, `populate_coach_umpire_bridge.py`, `populate_espn_bridge.py`

**Validation Views:**
- Added 5 new validation views to `sql/bridge/900_bridge_monitoring_views.sql`:
  - `duplicate_id_detection`: Detects duplicate ID entries
  - `orphaned_external_ids`: Identifies external IDs referencing non-existent Retrosheet IDs
  - `cross_reference_consistency`: Checks consistency between bridge table references
  - `season_coverage_gaps`: Identifies teams with incomplete/invalid season ranges
  - `mapping_completeness`: Overall mapping completeness statistics by entity type

### Analysis & Combined Queries

Use `analysis.*` views for unified access to both historical and live data:

- `analysis.combined_games`: Union of historical + live games
- `analysis.combined_events`: Union of historical + live events
- `analysis.combined_plate_appearances`: Combined plate appearance data
- `analysis.get_data_source_stats()`: Statistics across data sources
- `analysis.get_recent_games(days_back)`: Recent games from both sources

### Live Data Maintenance

- Live data tables are additive - no historical data is modified
- Raw MLB payloads remain separate in `raw_mlb`; do not merge raw live rows into `raw_retrosheet`
- Bridge tables enable ID mapping without data duplication
- Analysis views/materialized views provide transparent access to combined datasets
- Separate ingestion scripts prevent accidental mixing of data sources

## Recommended Workflow

### Full Warehouse Rebuild (Historical + Live Setup)

1. `python3 scripts/warehouse.py check-deps`
2. `python3 scripts/warehouse.py fetch-retrosheet`
3. `python3 scripts/record_retrosheet_downloads.py` (record comprehensive Retrosheet data downloads in monitoring table)
4. `python3 scripts/warehouse.py init-db`
5. `python3 scripts/warehouse.py extract-chadwick --years 2000-2025 --outputs all`
6. `python3 scripts/warehouse.py load-chadwick --years 2000-2025 --outputs all`
7. `python3 scripts/external_data/load_lahman.py` (load Lahman database tables)
8. `python3 scripts/populate_bridge_tables.py` (populate ID mappings)
9. `python3 scripts/download_statcast_pitch_level.py --season 2015` (download Statcast for each season 2015-2025)
10. `python3 scripts/external_data/load_statcast.py --file data/statcast/statcast_2015.csv` (load each season)
11. `psql -f sql/130_analysis_views.sql` (create combined analysis views)

### Live Data Ingestion (Ongoing)

1. `python3 scripts/fetch_mlb_schedule.py --yesterday` (discover games)
2. `python3 scripts/ingest_live_games.py --schedule` (ingest live games)
3. `SELECT * FROM analysis.get_data_source_stats();` (check ingestion status)

For fast iteration, pass a smaller year range or selected outputs.

### ESPN Historical Data Ingestion

1. `python3 scripts/fetch_espn_mlb.py ingest-historical --start-date YYYY-MM-DD --end-date YYYY-MM-DD --workers 10`
   - Fetches all games for the date range from ESPN API
   - Stores game snapshots in raw_espn schema
   - Uses parallel downloads with ThreadPoolExecutor
   - Tracks progress in raw_retrosheet.ingest_runs table
2. `python3 scripts/ingest_espn_plays.py` (ingest play-by-play data for available years)
   - Fetches play-by-play data from ESPN summary endpoint
   - ESPN only has play-by-play data for recent games (2024-2026)
   - Historical games (2000-2015) have empty plays arrays
3. `SELECT COUNT(*) FROM raw_espn.game_snapshots;` (verify game ingestion)
4. `SELECT COUNT(*) FROM raw_espn.plays_snapshots;` (verify plays ingestion)
5. `SELECT * FROM raw_retrosheet.ingest_runs WHERE source_name = 'espn_api' ORDER BY started_at DESC;` (check run history)

**Current ESPN Data Status:**
- 71,739 games ingested (seasons 2000-2025)
- Game snapshots: 100% completeness for game_date and season
- Play-by-play data: Available only for 2024-2026 (ESPN API limitation)
  - ESPN summary endpoint contains plays array for recent games
  - Historical games (2000-2015) return empty plays arrays
  - ESPN Core API v2 plays endpoint returns 404 (incorrect endpoint)
- 5,212 schedule snapshots
- 21 failures out of 71,739 games (0.03% failure rate)
- All runs tracked in raw_retrosheet.ingest_runs (run IDs 1-56)

**ESPN Play-by-Play Data Limitations:**
- ESPN API only provides play-by-play data for recent games (2024-2026)
- Historical play-by-play data (2000-2015) not available via ESPN API
- For historical play-by-play data, use Retrosheet/Chadwick or MLB Stats API
- ESPN data is supplemental to Retrosheet and MLB Stats API data sources

## Prediction Framework

The project uses a modular Strategy pattern for predictions:

### Files
- `scripts/prediction_framework/base.py` - Base classes (Predictor, PredictionTarget, ModelMetadata, PredictorRegistry)
- `scripts/prediction_framework/pa_predictor.py` - PAOutcomeDistributionPredictor implementation
- `scripts/prediction_framework/__init__.py` - PredictionEngine unified interface
- `scripts/prediction_framework/db.py` - Database configuration

### Usage
```python
from prediction_framework import PredictionEngine

engine = PredictionEngine()
predictor = engine.get_predictor('pa_outcome_distribution')
result = predictor.predict(features_df)
```

### Database Functions
- `models.register_model()` - Register trained model
- `models.register_calibration()` - Register calibration artifact
- `models.promote_model(id)` - Set active model
- `models.get_active_model(target_id)` - Get active model

### Active Models (2026-04-23)
| Target | Model | Version |
|--------|-------|---------|
| pa_outcome_distribution | hist_gradient_boosting_multiclass | 20260412T045759Z |
| game_home_win | hist_gradient_boosting | 20260416T085327Z |
| half_inning_any_run | hist_gradient_boosting | 20260410T090317Z |
| half_inning_lhb_any_hit | hist_gradient_boosting | 20260410T090325Z |

## Modeling Direction

The ML target should start as win probability from a game state. Historical examples come from Retrosheet/Chadwick. Live inference examples will come from MLB Stats API / GUMBO transformed into the same `core` game-state shape.

For the broader reusable probability engine, follow `docs/PREDICTION_ENGINE_PLAN.md`. New work should preserve the separation between raw ingestion, typed `core` tables, ML features, model outputs, market comparisons, and chat/agent logs.

Use `scripts/train_models.py` for first-pass model training. Store model artifacts under `data/models/`, register metrics in `models.model_registry`, and keep AI inference providers configured through environment variables rather than hard-coded secrets.

When creating or updating GitHub issues, always include concrete markdown links to relevant documentation, scripts, migrations, and tables, and provide detailed comments describing progress, decisions, and next steps.

### Documentation & Issue Linking Policy
- **Comprehensive Updates**: Every issue must contain a detailed comment thread that records the rationale, implementation details, and any open questions.
- **Linking**: Include markdown links (`[doc](path/to/doc.md)`) to all related documents (e.g., `docs/agents/*.md`), code files, SQL migrations, and other GitHub issues or sub‑issues.
- **Cross‑Reference**: When an issue resolves or depends on another, reference the related issue number (e.g., `#42`) and add a comment linking back.
- **Sub‑issues**: For large tasks, create sub‑issues and link them in the parent issue description and comments.
- **Review Cycle**: Before closing, ensure the issue thread fully captures the work performed and all relevant artifacts are linked.
- **Automation**: Use the repository's issue templates to enforce these fields where possible.

Load Retrosheet reference metadata with `scripts/load_reference_metadata.py` after rebuilding `core.games`, `core.events`, and `core.plate_appearances`; it backfills player handedness and refreshes feature materialized views.

Load broader Retrosheet auxiliary metadata with `scripts/load_auxiliary_retrosheet.py` after the reference metadata step. It preserves source rows in `raw_retrosheet` and exposes normalized `core` views for rosters, All-Star rosters/games, schedules, umpires, coaches, ejections, and player relatives. Keep raw auxiliary tables source-preserved; add typed joins/views in `core` instead of reshaping the raw layer destructively.

Build indexed ML feature marts with `sql/050_feature_marts.sql` after auxiliary metadata is loaded. Prior-season feature marts should use `feature_season = source season + 1` to avoid leaking same-season labels into training rows.

Train candidate models with `scripts/train_models.py --feature-set enriched` once feature marts exist. Promote best registered versions with `scripts/promote_best_models.py` instead of hand-editing `models.model_registry.is_active`.

Use `scripts/rebuild_warehouse.sh` as the canonical rebuild order for contributors. It runs ingestion, core migrations, reference/auxiliary loaders, and feature marts in sequence.

Use `sql/060_advanced_feature_marts.sql` for higher-signal feature generation: career-prior player rates, coarse context fallbacks, batter-pitcher matchup history, park run environment, and rolling team form. Train stronger candidates with `--feature-set advanced` and explore grids with `scripts/sweep_hyperparameters.py`.

Use `sql/070_temporal_and_production_marts.sql` for team rest/travel context and reporting marts. It currently provides `features.team_game_context`, `features.player_production_season`, `features.pitcher_production_season`, and temporal training views. Treat WAR-like outputs as experimental until replacement level, positional adjustments, and park/run-environment adjustments are explicitly modeled.

## Interface Direction

The web command center lives in `baseball-chatbot-ui/`. Keep generated frontend artifacts out of git: `node_modules/` and `.next/` must stay ignored.

Use Next.js API routes as the interface boundary between the browser, PostgreSQL, and local Python scripts. API routes may query read-oriented warehouse views and may launch documented scripts through explicit allow-lists. Do not add a browser endpoint that executes arbitrary shell commands, arbitrary SQL writes, or unvalidated model paths.

Prefer exportable tables and typed JSON payloads for early spreadsheet workflows. If a richer spreadsheet is needed, add a client-side grid over read-only API data first, then design explicit import/write-back flows separately.

For chat/agent work, start with tool-routed answers over curated SQL and scripts. Provider-backed LLM tool calling can be layered in later through the configured OpenRouter, Groq, and Codex/OpenAI-compatible providers, but tool schemas, SQL guardrails, conversation logging, and auth should come before broad natural-language SQL access.

The safe terminal/workbench pattern is: browser button -> named API action -> allow-listed local command -> captured stdout/stderr. A full embedded terminal requires authentication, `node-pty`, WebSocket session controls, command restrictions, and project-root isolation.

Persist interface activity when practical. Chat prompts should write to `chat.query_logs`, and simulation/backtest workflows should write reproducible filters and summaries to tables under `predictions`.
## 📚 Letta Log Hook (automatic)

All Hermes agents (including Kilocode) now run with the following hooks:

```json
{
  "pre_prompt_hook":  "~/dotfiles/ai/shared/skills/letta_log/scripts/hermes_hook.py prompt",
  "post_response_hook": "~/dotfiles/ai/shared/skills/letta_log/scripts/hermes_hook.py response",
  "error_hook": "~/dotfiles/ai/shared/skills/letta_log/scripts/hermes_hook.py error"
}
```

**What this does**

* **Prompt** → Logged as an archival memory entry with tags `hermes,prompt,YYYY‑MM‑DD`.
* **Response** → Logged with tags `hermes,response,YYYY‑MM‑DD`.
* **Error** → Logged with tags `hermes,error,YYYY‑MM‑DD`.

All entries are attached to the persistent **`agent‑log`** conversation and include:
- LLM and model name (`HERMIT_LLM`, `HERMIT_MODEL`),
- environment metadata (hostname, OS, user),
- optional `turn_id` for linking prompt ↔ response (enable via `HERMIT_LINK_TURN=1`),
- rate‑limiting to avoid duplicate records.

> **Tip:** Enable a dry‑run globally during development:
> ```bash
> export HERMIT_HOOK_DRY_RUN=1
> ```
> The hooks will then just print the JSON payload without inserting anything into Letta.

The hooks are active for **every** Hermes turn, ensuring a complete, searchable audit trail in the Letta memory system.
