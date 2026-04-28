# File Inventory

## Issue Links
- Issue #5: Documentation & Issue Linking – completed. See [#53](https://github.com/cbwinslow/retrosheet/issues/53)
- Issue #1: Core LLM Integration – ongoing. See [#49](https://github.com/cbwinslow/retrosheet/issues/49)
- Issue #2: Tool Execution Engine – ongoing. See [#50](https://github.com/cbwinslow/retrosheet/issues/50)
- Issue #3: Model Orchestration – ongoing. See [#51](https://github.com/cbwinslow/retrosheet/issues/51)
- Issue #4: Security & Safety – ongoing. See [#52](https://github.com/cbwinslow/retrosheet/issues/52)
- Issue #6: Model Training Pipeline – ongoing. See [#55](https://github.com/cbwinslow/retrosheet/issues/55)
- Issue #7: Advanced Features – ongoing. See [#56](https://github.com/cbwinslow/retrosheet/issues/56)
- Issue #8: ESPN MLB Data Integration – completed. See [#59](https://github.com/cbwinslow/retrosheet/issues/59)
- Issue #9: Comprehensive Retrosheet Data Acquisition – completed. See [#57](https://github.com/cbwinslow/retrosheet/issues/57)
- Issue #10: Statcast Pitch-Level Data Ingestion – completed. See [#58](https://github.com/cbwinslow/retrosheet/issues/58)
- Issue #11: Pitch-Level Model Pipeline (Epic #78) – **in progress**. See [#78](https://github.com/cbwinslow/retrosheet/issues/78)
- Issue #11.1: Flexible Feature Mart Schema (Sub-Issue #79) – **in progress**. See [#79](https://github.com/cbwinslow/retrosheet/issues/79)
- Issue #12: Extensible MLB Prediction Framework (Epic #80) – **ready to implement**. See [#80](https://github.com/cbwinslow/retrosheet/issues/80)
  - #81: Phase 1.1 - Pydantic Configuration Schemas
  - #82: Phase 1.2 - Rich Result Classes
  - #83: Phase 1.3 - Test Infrastructure
  - #84: Phase 2.1 - ModelTrainer Class
  - #85: Phase 2.2 - Plugin Registry
  - #86: Phase 2.3 - FeatureLoader
  - #87: Phase 2.4 - Experiment Runner
  - #88: Phase 3.1 - Unified CLI
  - #89: Phase 3.2 - Database Triggers
  - #90: Phase 3.3 - Documentation

This inventory tells agents what each important file does and which workflows own it. Files may appear in multiple sections when they serve multiple goals.

## Top-Level Docs

| File | Purpose | Owners / Workflows |
|---|---|---|
| `AGENTS.md` | Main operating guide and routing map. Keep short; link to this folder for detail. | All agents |
| `README.md` | User-facing setup, rebuild, modeling, interface, and attribution instructions. | Reproducibility, onboarding |
| `research_report.md` | Paper-style running research report with abstract, methodology, empirical results, limitations, and next experiments. | Research record, manuscript drafting |
| `docs/agents/CURRENT_SNAPSHOT.md` | Short current-state handoff for architecture, validated counts, best model status, blockers, compute notes, and next steps. | Agent handoff, token-loss recovery |
| `docs/PROJECT_LOG.md` | Running build log with validation counts, model results, and major decisions. | All significant changes |
| `docs/WAREHOUSE_PLAN.md` | Warehouse normalization plan. | Warehouse |
| `docs/CORE_SCHEMA.md` | Typed core schema details. | Warehouse, data-quality |
| `docs/PREDICTION_ENGINE_PLAN.md` | High-level prediction architecture. | Modeling, agents, live, markets |
| `docs/LIVE_DATA_ARCHITECTURE.md` | Complete live data ingestion architecture and procedures. | Live bridge, analysis |
| `docs/RESEARCH_METHODOLOGY.md` | Formal CRISP-DM methodology, notation, objective functions, and modeling assumptions. | Research framing, modeling, evaluation |
| `docs/TEMPORAL_MODEL_SELECTION.md` | Temporal weighting, era segmentation, window-size math, and recency-policy selection for non-stationary baseball data. | Modeling, evaluation, concept-drift handling |
| `docs/EDGEFORGE_TRIAGE.md` | Triage and classification of the unintegrated EdgeForge / MLB-enhanced files. Defines what is experimental versus canonical. | Architecture governance, cleanup |
| `docs/FEATURE_AUDIT.md` | Field/feature status audit: what is understood, what is operationalized, and what should be built before deeper tuning. | Modeling, feature engineering |
| `docs/AT_BAT_OUTCOME_MODEL_REVIEW.md` | Maps the at-bat outcome spec to actual warehouse assets and next steps. | Multiclass PA modeling |
| `docs/PA_BASELINE_MODEL_SPEC.md` | Exact baseline PA modeling contract: grouped taxonomy, feature set, SQL object plan, and validation policy. | Multiclass PA modeling, implementation planning |
| `docs/ab_outcome.md` | User-provided spec for at-bat/pitch outcome modeling. Treat as requirements guidance, not direct implementation. | Multiclass PA and pitch-model roadmap |
| `docs/retrosheet_key.md` | Retrosheet documentation index and external reference map. | Retrosheet parsing/reference |
| `docs/ARCHIVED_DOCUMENTATION.md` | Inventory of archived documentation with reasons and replacements. | Documentation governance |
| `docs/BRIDGE_TABLE_IMPLEMENTATION.md` | Comprehensive documentation for bridge table design, ID formats, implementation strategies, and monitoring. | Bridge table reference |
| `docs/ID_RECONCILIATION.md` | Documentation on ID reconciliation methods for baseball data sources, crosswalk sources, and best practices. | ID mapping reference |
| `docs/DATA_MODELS.md` | Comprehensive data model documentation for Retrosheet, MLB Stats API, ESPN MLB API, Statcast, Lahman database, Baseball Reference, and Chadwick Bureau. | Data source reference |
| `docs/ESPN_BRIDGE_REQUIREMENTS.md` | Requirements for ESPN bridge table integration, including dependencies, implementation status, and validation. | ESPN bridge reference |
| `docs/CONFIDENCE_SCORING.md` | Confidence scoring framework documentation for bridge table mappings, including score levels, usage, and monitoring. | Bridge data quality reference |
| `docs/agents/ZSH_SQL_MANGLING_FIX.md` | Documentation of the zsh globsubst bug that was silently corrupting SQL commands and the fix applied (removing /etc/zsh/zshenv). | Shell configuration reference |
| `docs/agents/REPRODUCIBILITY_AUDIT_PROMPT.md` | **CRITICAL** - Comprehensive prompt for another agent to audit and fill all documentation gaps to make project reproducible. | All agents must follow |
| `CHATBOT_INTERFACE_DESIGN.md` | Current/future web command-center design notes. | Interface, agents |
| `docs/WORKFLOW_VALIDATION_REPORT.md` | Complete infrastructure audit, redundancy analysis, architecture diagrams. | Framework planning |
| `docs/USER_MANUAL.md` | Comprehensive user guide with all features, procedures, and examples. | User onboarding |
| `docs/PROCEDURES_DETAILED.md` | 25 detailed step-by-step procedures for all operations. | Operations reference |
| `docs/MASTER_INDEX.md` | Master documentation index and navigation guide. | Documentation hub |
| `docs/EXTENSIBLE_FRAMEWORK_DESIGN.md` | Pydantic schemas, result classes, plugin architecture, examples. | Framework implementation |
| `docs/FRAMEWORK_CONFIRMATION.md` | Proof architecture will work, risk analysis, success criteria. | Architecture validation |
| `docs/IMPLEMENTATION_ROADMAP.md` | 22-hour implementation plan with phases and deliverables. | Implementation tracking |
| `docs/DEPLOYMENT_PLAN.md` | Complete deployment guide for agents, handoff checklist, rollback plan. | Agent handoff |
| `docs/GITHUB_PROJECT_GUIDE.md` | GitHub Project board setup, workflow, tracking for issues #80-#90. | GitHub project management |
| `docs/dev/TOOL_SETUP_GUIDE.md` | **NEW** - Comprehensive guide for all development tools: pgTAP, pytest, CodeQL, FAISS, Sourcegraph, Graphviz. Installation and usage. | Dev environment setup |
| `docs/dev/SOURCEGRAPH_SETUP.md` | **NEW** - Sourcegraph self-hosted setup, configuration, and usage patterns. | Code search tooling |
| `docs/vector/FAISS_INTEGRATION.md` | **NEW** - FAISS vector similarity search integration: building player embeddings, pgvector storage, CLI usage. | ML feature embeddings |
| `docs/dev/GRAPHVIZ_AST_VISUALIZATION.md` | **NEW** - Graphviz and AST analysis guide: schema diagrams, dependency graphs, query plan visualization. | Codebase visualization |

## Configuration

| File | Purpose | Notes |
|---|---|---|
| `config/chadwick_event_columns.txt` | Chadwick event-column reference used to avoid hand-invented mappings. | Check before changing raw event parsing. |
| `config/ai_providers.example.json` | Example provider configuration for OpenRouter, Groq, and Codex/OpenAI-compatible inference. | Never commit real keys. |
| `.env.example` | Safe local environment variable template. | Keep secrets out of git. |

## CI/CD & Tooling Configuration

| File | Purpose | Notes |
|---|---|---|
| `.github/workflows/ci.yml` | Main CI pipeline: ruff+biome+sqlfluff linting, SQL header validation, pytest unit/integration/e2e tests, feature mart row count verification. Triggers: push/PR to main branches. | Core automation |
| `.github/workflows/codeql-analysis.yml` | **NEW** - Security scanning: CodeQL (Python/JS), Bandit (Python security), pip-audit (dependency vulnerabilities). Weekly scheduled run + on push/PR. | Security |
| `.github/workflows/sourcegraph-code-intel.yml` | **NEW** - Uploads LSIF code intelligence to Sourcegraph for precise code navigation and reference finding. | Code search |
| `.github/codeql/codeql-config.yml` | **NEW** - CodeQL configuration: disabled queries, excluded paths (data/, .venv/, docs/, node_modules/). | Security config |
| `docker-compose.sourcegraph.yml` | **NEW** - Self-hosted Sourcegraph instance (PostgreSQL, Redis, Sourcegraph server). Local dev setup via Docker Compose. | Optional tool |
| `pyproject.toml` | Python project configuration: dependencies, dev tools (ruff, pytest, uv), scripts entry points. | Build config |
| `pytest.ini` | pytest configuration: test discovery patterns, markers (unit, integration, e2e, slow), timeout, warning filters. | Test config |
| `biome.json` | Biome configuration for JavaScript/TypeScript/JSON/YAML linting and formatting. | Frontend linting |
| `.sqlfluff` | SQLFluff configuration: dialect (postgres), rule exclusions, formatting rules. | SQL linting |
| `.github/CODEOWNERS` | Code ownership for automatic review assignment (if present). | Review routing |

## Retrosheet Data Files

Downloaded April 18, 2026 (1,748.81 MB total). All stored in `data/` directory.

| File | Purpose | Size |
|---|---|---|
| `data/retrosheet_alldata.zip` | Traditional Retrosheet data (event files, box-score files, game logs, etc.) | 326 MB |
| `data/retrosheet_biodata.zip` | Biographical data (biofile0.csv, relatives.csv, coaches0.csv, ballparks0.csv, managers0.csv, teams0.csv, umpires0.csv) | 1.3 MB |
| `data/retrosheet_csv_downloads.zip` | CSV parsed data (allplayers.csv, gameinfo.csv, teamstats.csv, batting.csv, pitching.csv, fielding.csv, plays.csv) | 710 MB |
| `data/retrosheet_allstar.zip` | All-Star game data (1933-2025) | 630 KB |
| `data/retrosheet_postseason.zip` | Postseason game data (1903-2025) | 7.3 MB |
| `data/retrosheet_negroleagues.zip` | Negro Leagues data (1903-1962) | 6.9 MB |
| `data/retrosheet_regular.zip` | Regular season games (1898-2025, includes tiebreaker playoffs) | 696 MB |
| `data/retrosheet_tiebreakers.zip` | Tiebreaker playoff games (1946-2018) | 127 KB |

Monitoring records stored in `raw_retrosheet.ingest_runs` with run IDs 27-34.

## Data Source Status

**Completed:**
- Retrosheet reference tables (ballparks_reference: 656, biofile: 26,961, coaches: 12,501, ejections: 19,730, relatives: 1,320, teams_reference: 292)
- Lahman database tables (batting: 110,495, pitching: 49,430, fielding: 147,080, people: 20,673, teams: 2,985)
- Baseball Databank data (same as Lahman - already loaded in lahman schema)
- Statcast data (raw_mlb.statcast: 7,797,034 rows, 118 fields, seasons 2015-2025, 24,079+ games, 4,229+ batters, 3,251+ pitchers)
- ESPN MLB data (game_snapshots: 71,739, plays_snapshots: 1,271, schedule_snapshots: 5,212; seasons 2000-2025; play-by-play data only available for 2024-2026; 21 failures out of 71,739 games, 0.03% failure rate)
- Bridge table population via SQL procedures (game_xref: 59,191, team_xref: 294, park_xref: 656, coach_xref: 1,903, umpire_xref: 2,368, player_xref: 128,925)
- Confidence scoring framework applied to all bridge tables

**Outstanding:**
- ESPN player_stats_snapshots and team_stats_snapshots (0 rows - not yet loaded)

## Warehouse SQL
| File | Purpose | Canonical Position |
|---|---|---|
| `sql/001_init.sql` | Initial schemas/raw table scaffolding. | Early bootstrap and legacy compatibility. |
| `sql/010_core_games_events.sql` | Creates typed `core.games`, `core.events`, seed targets, model/prediction/chat/market tables. | Core foundation. |
| `sql/020_plate_appearances.sql` | Creates `core.plate_appearances`, `features.plate_appearance_examples`, binary PA targets. | PA foundation. |
| `sql/030_reference_metadata.sql` | Source-preserved Retrosheet bio/team/park reference tables and metadata joins. | Reference metadata. |
| `sql/040_auxiliary_retrosheet.sql` | Auxiliary Retrosheet raw tables and normalized core views for rosters, schedules, umpires, coaches, ejections, relatives. | Auxiliary metadata. |
| `sql/050_feature_marts.sql` | Prior-season batter, pitcher, team, context, and half-inning summary marts. | First ML feature marts. |
| `sql/060_advanced_feature_marts.sql` | Career-prior, matchup, park, coarse context, and rolling team features. | Advanced ML features. |
| `sql/070_temporal_and_production_marts.sql` | Team rest/travel, player production, pitcher production, temporal examples. | Reporting and time context. |
| `sql/075_interface_workflows.sql` | Persists Sim Lab runs and extends chat logs for interface workflow auditability. | Web command center. |
| `sql/076_plate_appearance_outcome_model.sql` | Creates granular multiclass PA outcome examples, season/rules era columns, and target `pa_outcome_distribution`. | Multiclass PA modeling, temporal features. |
| `sql/077_pitch_sequence_model.sql` | Normalizes `pitch_seq_tx` into one row per Retrosheet sequence symbol with official symbol semantics and coarse pitch/result groupings. | Pitch-sequence normalization, future pitch-level modeling. |
| `sql/078_plate_appearance_outcome_grouped.sql` | Adds grouped PA outcome training examples and validation summary on top of the canonical granular PA outcome layer. | Baseline PA modeling, grouped target infrastructure. |
| `sql/079_probability_evaluation_reports.sql` | Adds durable calibration and bootstrap report tables plus recent-report views in `predictions`. | Probability evaluation persistence. |
| `sql/081_probability_calibration_artifacts.sql` | Extends calibration reports with persisted artifact support for reusable calibrated scoring. | Calibrated inference infrastructure. |
| `sql/082_count_state_feature_marts.sql` | Adds batter/pitcher/context prior-rate marts split by ball-strike count and a count-state-enhanced advanced PA view. | Targeted feature improvement for PA reliability defects. |
| `sql/040_coach_umpire_bridge_tables.sql` | Creates `bridge.coach_xref` and `bridge.umpire_xref` tables for cross-source ID mapping of coaches and umpires. | Coach/umpire bridge tables. |
| `sql/mlb/100_bridge_tables.sql` | Creates core bridge tables: `bridge.player_xref`, `bridge.team_xref`, `bridge.park_xref`, `bridge.game_xref`. | Core bridge infrastructure. |
| `sql/bridge/900_bridge_monitoring_views.sql` | Creates monitoring views for bridge table health checks, coverage statistics, and data quality. | Bridge monitoring and validation. |
| `sql/bridge/910_confidence_scoring.sql` | Adds confidence scoring framework to bridge tables with confidence_score and confidence_source columns, plus monitoring views. | Bridge data quality tracking. |
| `sql/bridge/920_game_xref_procedure.sql` | SQL procedure `bridge.populate_game_xref()` for populating game cross-reference by matching Retrosheet and MLB games using date, team IDs, and game number. | Game cross-reference population. |
| `sql/bridge/930_season_aware_team_xref_procedure.sql` | SQL procedure `bridge.populate_season_aware_team_xref()` for populating season-aware team mappings to handle franchise moves (MON→WAS, FLO→MIA). | Team season coverage. |
| `sql/bridge/940_coach_umpire_xref_procedures.sql` | SQL procedures `bridge.populate_coach_xref()` and `bridge.populate_umpire_xref()` for populating coach and umpire cross-references with biofile_legacy name resolution. | Coach/umpire bridge table population. |
| `sql/bridge/950_park_xref_procedure.sql` | SQL procedure `bridge.populate_park_xref()` for populating park cross-reference using static MLB venue ID to Retrosheet park ID mappings. | Park cross-reference population. |
| `sql/bridge/960_player_xref_procedure.sql` | SQL procedure `bridge.populate_player_xref()` for populating player cross-reference from temp_table.chadwick_player_data (hybrid: Python downloads Chadwick data, SQL inserts). | Player cross-reference population. |
| `sql/bridge/970_bridge_validation_functions.sql` | SQL validation functions that return boolean true/false for use in scripting: validate_bridge_tables_have_data(), validate_no_duplicate_ids(), validate_no_orphaned_external_ids(), validate_cross_reference_consistency(), validate_no_season_coverage_gaps(), validate_player_id_coverage(), validate_team_id_coverage(), validate_park_id_coverage(), validate_data_quality(), validate_all_bridge_tables(), validate_bridge_tables_quick(). | Bridge table validation and health checks. |
| `sql/bridge/980_player_xref_schema_enhancement.sql` | Schema enhancement for bridge.player_xref to add bbref_id, fangraphs_id, mlb_played_first, birth_year columns from Chadwick Bureau Register. | Player cross-reference schema enhancement. |
| `sql/bridge/985_player_xref_population_procedure.sql` | SQL procedure `bridge.populate_player_xref_from_chadwick()` and `bridge.populate_player_xref_full()` for populating player cross-reference from Chadwick CSV files using COPY command (pure SQL approach). | Player cross-reference population (SQL-based). |
| `sql/bridge/999_master_bridge_population_procedure.sql` | Master orchestrator `bridge.populate_all_bridge_tables()` that calls all bridge population procedures in correct dependency order. Now uses SQL-based player_xref population by default. | Complete bridge table population. |
| `sql/bridge/930_chadwick_register_bridge.sql` | **CHADWICK REGISTER BRIDGE** - Creates staging table, upsert procedure, and views for Chadwick Bureau Register data. **FIXED (2026-04-25)**: Added `NULLIF(key_retro, '')` filtering to handle 485,034 empty string values that were causing duplicate key violations. Staging table with all 58 ID fields, `bridge.upsert_chadwick_to_player_xref()` procedure, coverage monitoring views. | Chadwick-based player cross-reference population. |
| `sql/bridge/931_lahman_bridge_population.sql` | **LAHMAN GAP-FILL BRIDGE** - Staging table and procedures for Lahman People table gap-filling. `bridge.load_lahman_to_staging()` and `bridge.gap_fill_player_xref_from_lahman()` for name-based ID matching. | Secondary ID source for players missing from Chadwick. |
| `sql/bridge/940_bridge_validation_tests.sql` | **BRIDGE VALIDATION TESTS** - Comprehensive test suite for ID coverage: MLB coverage, Retrosheet coverage, uniqueness tests, pitch data linkage. Functions: `bridge.test_player_xref_mlb_coverage()`, `bridge.test_pitch_data_player_coverage()`, `bridge.run_all_bridge_tests()`, `bridge.get_bridge_test_summary()`. | Bridge data quality validation.
| `sql/200_external_data.sql` | Defines schemas and tables for supplemental free data sources (Statcast, Baseball‑Data.com, Gameday XML) and bridge tables. | External data marts. |
| `sql/220_espn_schema.sql` | Defines `raw_espn` schema and tables for ESPN API data (game snapshots, schedule snapshots, player stats, team stats). | ESPN external data ingestion. |
| `sql/225_ingest_run_tracking.sql` | Expands `raw_retrosheet.ingest_runs` table with script metadata, adds helper functions for run logging, triggers for auto-timestamps, and monitoring views. | Ingest run tracking and reproducibility. |

## Staging Layer SQL

**Data transformation between raw and core schemas (Phase 2.4).**

| File | Purpose | Components |
|---|---|---|
| `sql/20_staging/2000_staging_schema.sql` | **STAGING SCHEMA** - Creates `staging` schema with tables for cleaned/validated data: `stg_retrosheet_events`, `stg_retrosheet_games`, `stg_retrosheet_player_appearances`. | SQL |
| `sql/20_staging/2001_stg_retrosheet_transform.sql` | **TRANSFORM FUNCTIONS** - `staging.transform_chadwick_event()`, `staging.load_events_for_season()`, validation trigger, and `v_event_validation_summary` view. | SQL |
| `sql/20_staging/2002_staging_checkpoints.sql` | **CHECKPOINT TABLE** - `staging.source_checkpoints` for resumable downloads. Functions: `start_checkpoint()`, `complete_checkpoint()`, `fail_checkpoint()`, `get_resumable_checkpoints()`. View: `v_checkpoint_summary`. | SQL |

## Maintenance SQL

| File | Purpose | Canonical Position |
|---|---|---|
| `sql/maintenance/001_check_extensions.sql` | Check currently installed PostgreSQL extensions. | Extension monitoring. |
| `sql/maintenance/002_install_pg_cron.sql` | Install pg_cron extension for job scheduling (critical for automation). | Automation infrastructure. |
| `sql/maintenance/003_install_pg_stat_statements.sql` | Install pg_stat_statements extension for query performance monitoring. | Performance monitoring. |
| `sql/maintenance/004_install_pl_python3u.sql` | Install PL/Python3u extension for Python integration within PostgreSQL. | Advanced ML integration. |
| `sql/maintenance/005_install_pgvector.sql` | Install pgvector extension for vector similarity search and embeddings. | Player similarity search. |
| `sql/maintenance/010_array_types.sql` | Implement PostgreSQL array types for multi-value features (pitch sequences, injury history). | Advanced data structures. |
| `sql/maintenance/011_custom_types.sql` | Implement PostgreSQL custom types (domains) for baseball-specific data validation. | Data integrity. |
| `sql/maintenance/012_partial_indexes.sql` | Implement PostgreSQL partial indexes for conditional query optimization. | Query performance. |
| `sql/maintenance/020_game_hours_scheduler.sql` | Game-hours-aware polling scheduler functions (is_mlb_season, is_game_hours, should_poll_games). | Smart live data polling. |
| `sql/maintenance/021_update_cron_game_hours.sql` | Updates cron jobs to use conditional polling wrappers. | Cron job optimization. |
| `sql/maintenance/030_kb_vector_schema.sql` | KB vector schema: `kb.document_chunks` with pgvector embeddings, indexes, semantic search functions, ingestion tracking. | RAG infrastructure. Run after pgvector is installed. |
| `sql/vector/001_faiss_schema.sql` | **NEW** - Schema for storing vector embeddings compatible with faiss-cpu: player_embeddings, pitch_embeddings, team_embeddings tables with pgvector columns, indexes, and helper functions (upsert, similarity search). | FAISS/pgvector integration. |
| `sql/maintenance/999_master_installation.sql` | Master orchestrator for installing all PostgreSQL extensions and advanced features. | Complete extension installation. |

## Warehouse Orchestration SQL

| File | Purpose | Canonical Position |
|---|---|---|
| `sql/warehouse/001_warehouse_schema.sql` | Warehouse rebuild orchestration schema: `warehouse.rebuild_runs`, `warehouse.rebuild_log`, helper functions. | Master rebuild infrastructure. |
| `sql/warehouse/002_phase_procedures.sql` | Phase-level procedures: `phase_raw_load()`, `phase_core_build()`, `phase_bridge_sync()`, `phase_feature_build()`, `phase_model_prep()`. | Individual rebuild phases. |
| `sql/warehouse/003_rebuild_orchestrator.sql` | Main orchestrator: `warehouse.rebuild(mode, seasons)` procedure with per-phase commit and resume capability. | Master rebuild entry point. |
| `sql/warehouse/004_batch_operations.sql` | Resume-capable batch processing: `warehouse.batch_operations` table with progress tracking and resume functions. | Long-running operation tracking. |
| `sql/warehouse/005_feature_population_procedures.sql` | **FEATURE POPULATION ORCHESTRATION** - SQL procedures: `populate_features_phase()`, `verify_features_populated()`, `get_feature_stats()`, `estimate_batch_completion()`. | Feature population automation with warehouse integration. |
| `sql/analysis/001_feature_importance.sql` | Feature importance storage: `analysis.feature_importance` table for XGBoost/SHAP scores, with top features view. | Feature selection and interaction analysis. |
| `sql/framework/001_framework_schema_DEPRECATED.sql` | **DEPRECATED** - Redundant with existing warehouse/models/features_pitch schemas. Do not apply. | [DEPRECATED] |

## Test SQL (E2E Testing Infrastructure)

| File | Purpose | Canonical Position |
|---|---|---|
| `sql/test/001_create_test_schema.sql` | Creates isolated `test` schema with test tracking tables. | E2E test setup. Run first before tests. |
| `sql/test/002_test_fixtures.sql` | Creates small test datasets (100 games) from real data for fast testing. | E2E test data setup. Run after test schema. |
| `sql/test/003_install_pgtap.sql` | **NEW** - Install pgTAP extension (PostgreSQL unit testing framework) and helper functions. | pgTAP setup. |
| `sql/test/010_pgtap_core_tables.sql` | **NEW** - pgTAP tests for core.games table: column presence, types, NOT NULL, PK, indexes, view existence. | Core schema validation. |
| `sql/test/020_pgtap_functions.sql` | **NEW** - pgTAP tests for database functions and procedures: bridge validation, population procedures, feature functions. | Procedure validation. |

## Metadata SQL (Database Documentation)

| File | Purpose | Canonical Position |
|---|---|---|
| `sql/metadata/001_add_table_comments.sql` | **TABLE COMMENTS** - Adds COMMENT ON statements for all 150+ database tables and views. Documents purpose, row counts, data sources, and key relationships per AGENTS.md standards. | Run after all tables created. |
| `sql/metadata/002_add_procedure_comments.sql` | **PROCEDURE/FUNCTION COMMENTS** - Adds COMMENT ON statements for all 87 database functions and procedures. Documents arguments, return values, and usage. | Run after all procedures created. |
| `docs/DATABASE_CATALOG.md` | **COMPLETE DATABASE CATALOG** - Comprehensive documentation of all 36 schemas, 152 tables, 85 views, and 87 functions/procedures. Includes row counts, sizes, and descriptions. | Reference document for all database objects. |

**Documentation Standards (per AGENTS.md):**
- All tables must have COMMENT ON TABLE statements
- All procedures must have COMMENT ON FUNCTION/PROCEDURE statements
- Comments must include: purpose, row counts (where applicable), source data, and relationships
- Metadata schema (`metadata.table_dictionary`, `metadata.column_dictionary`) tracks all objects

## Test Scripts (E2E Validation)

| File | Purpose | Notes |
|---|---|---|
| `scripts/test/e2e_test_runner.sh` | Main E2E test runner. Validates SQL headers, table comments, row counts. | Executable. Usage: `./scripts/test/e2e_test_runner.sh --quick` |
| `scripts/test/validate_sql_files.sh` | Validates all SQL files have proper headers. | Executable. Fast check (5 minutes). |
| `scripts/test/verify_rebuild.sh` | Validates warehouse rebuild procedures work correctly. | Executable. Full check (30 minutes). |
| `scripts/rebuild_warehouse.sh` | **Master rebuild orchestrator** using PostgreSQL procedures. | New approach: calls `warehouse.rebuild()`. Usage: `./scripts/rebuild_warehouse.sh --mode full`. Legacy mode: `--legacy` flag. |

**Test Infrastructure Notes:**
- Free local setup - uses existing PostgreSQL (no Docker, no cloud)
- Test schema `test` is isolated from production data
- Small test fixtures (100 games vs 62,000) for fast execution
- AI Agent Gap-Fill Loop: Run tests → find gaps → create missing files → re-run
- All scripts must be executable: `chmod +x scripts/test/*.sh`

## Python Unit Tests (Milestone 7a: Testing Infrastructure)

**Comprehensive test suite with 160+ tests covering unit, integration, E2E, compatibility, and functionality testing.**

| File | Purpose | Test Count |
|---|---|---|
| `tests/conftest.py` | **SHARED FIXTURES** - pytest fixtures: temp_dir, mock_db_connection, sample_game_state_data, sample_we_matrix, sample_li_matrix, db_available, benchmark_logger, project_root, sql_files, script_files. Hooks: pytest_configure, pytest_collection_modifyitems. | Fixtures |
| `tests/pytest.ini` | **PYTEST CONFIG** - Test markers: unit, integration, e2e, slow, database, benchmark, compatibility, scripts, queries, functionality. Warning filters, coverage options, console output style. | Config |
| `tests/run_tests.py` | **TEST RUNNER** - Comprehensive test orchestration with JSON reports. Runs unit, integration, E2E tests. Supports --quick, --e2e, --unit, --benchmark flags. | Orchestrator |

### Unit Tests (`tests/unit/`)

| File | Purpose | Test Count |
|---|---|---|
| `tests/unit/test_features_base.py` | **FEATURE BASE TESTS** - FeatureConfig, GameState, FeatureResult, FeatureScope, FeatureStatus, InvalidGameStateError, Serialization/deserialization, FeatureStore base class. | 15+ |
| `tests/unit/test_win_expectancy.py` | **WE CALCULATOR TESTS** - WinExpectancyCalculator initialization, matrix loading, game state lookup, save/load, build from historical, score differential capping. | 12+ |
| `tests/unit/test_leverage_index.py` | **LI CALCULATOR TESTS** - LeverageIndexCalculator initialization, matrix loading, leverage computation, base states, score differentials, extra innings. | 10+ |
| `tests/unit/test_pipeline.py` | **PIPELINE SERVICE TESTS** - PipelineService config loading, database operations, execution flow, checkpoint/resume, singleton pattern. Milestone 8. | 20+ |
| `tests/unit/test_compatibility.py` | **COMPATIBILITY TESTS** - Python version (3.10+), OS compatibility, database features (PostgreSQL 14+), dependency versions. | 15+ |
| `tests/unit/test_scripts.py` | **SCRIPT VALIDATION TESTS** - Shell script syntax, Python script syntax, SQL script validation, shebang checks, CLI command validation, import tests. | 20+ |
| `tests/unit/test_queries.py` | **SQL QUERY TESTS** - Query syntax validation, naming conventions, performance checks, security checks, migration order. | 10+ |

### Integration Tests (`tests/integration/`)

| File | Purpose | Test Count |
|---|---|---|
| `tests/integration/test_functionality.py` | **FUNCTIONALITY TESTS** - Data flow, component integration, E2E workflows, error handling, edge cases, data quality, concurrency, performance, reliability, security, monitoring. | 25+ |
| `tests/integration/conftest.py` | Integration test fixtures. | Fixtures |

### E2E Tests (`tests/e2e/`)

| File | Purpose | Test Count |
|---|---|---|
| `tests/e2e/test_features_e2e.py` | **FEATURE E2E TESTS** - End-to-end feature pipeline with database, data loading, calculator integration, verification. | 15+ |
| `tests/e2e/conftest.py` | E2E test fixtures. | Fixtures |

### Running Tests

```bash
# Run all tests
uv run python -m pytest tests/ -v

# Run by category
uv run python -m pytest tests/unit/ -v
uv run python -m pytest tests/integration/ -v
uv run python -m pytest tests/e2e/ -v

# Run by marker
uv run python -m pytest -m unit -v
uv run python -m pytest -m integration -v
uv run python -m pytest -m e2e -v
uv run python -m pytest -m benchmark -v

# Run comprehensive test runner
uv run python tests/run_tests.py --all --verbose
```

## Knowledge Base Documents

| File | Purpose | Canonical Position |
|---|---|---|
| `docs/KNOWLEDGE_BASE_SABERMETRICS.md` | Research findings on sabermetrics, baseball modeling, and prediction approaches. | Modeling reference. |
| `docs/KNOWLEDGE_BASE_MODELS_REPOS.md` | Research on useful baseball models and GitHub repositories for ML and sabermetrics. | Model research. |
| `docs/TABLE_ASSESSMENT_SABERMETRICS.md` | Assessment of current table structure for sabermetrics and baseball modeling requirements. | Schema assessment. |
| `docs/POSTGRESQL_EXTENSIONS_RESEARCH.md` | Research-backed recommendations for PostgreSQL extensions and features for baseball analytics. | Extension reference. |
| `docs/LIVE_BETTING_PIPELINE_STATUS.md` | Comprehensive status assessment for live betting and prediction infrastructure. | Live betting reference. |
| `docs/KNOWLEDGE_BASE_MARKOV_CHAIN.md` | Research synthesis: Markov chain models, RE matrix, Stanford/UT Austin papers, implementation approaches. | Markov chain reference. |
| `docs/KNOWLEDGE_BASE_FRAMEWORK.md` | Modular prediction framework architecture: Strategy/Registry pattern, target/model contracts, implementation status. | Framework design reference. |
| `docs/KNOWLEDGE_BASE_GIS_PITCH.md` | Research: PostGIS pitch location mapping, strike zone coordinates, visualization approaches. | GIS mapping reference. |
| `docs/SABERMETRICS_LINK_INVENTORY.md` | Comprehensive inventory of 40+ sabermetrics research links with ingestion tracking. | Knowledge base reference. |
| `docs/MODEL_SELECTION_GUIDE.md` | Research-backed model selection by target type with decision tree and feature requirements. | Model choice reference. |
| `docs/kb/AGENTS.md` | RAG setup guide: directory structure, chunking strategy, LlamaIndex recommendation, agent usage patterns. | KB agent operations. |
| `docs/kb/sources/` | Organized extracted sources: books/, papers/, articles/, reference/ (9 files, ~2.7MB text). | RAG source corpus. |
| `docs/kb/chunks/` | Chunked documents for RAG ingestion (by_source/ and by_topic/). | RAG chunk storage. |
| `docs/kb/indices/` | Vector index metadata and configs. | RAG index config. |
| `docs/kb/metadata/` | Source tracking, ingestion logs. | KB metadata. |

| File | Purpose | Canonical Position |
|---|---|---|
| `sql/001_init.sql` | Initial schemas/raw table scaffolding. | Early bootstrap and legacy compatibility. |
| `sql/010_core_games_events.sql` | Creates typed `core.games`, `core.events`, seed targets, model/prediction/chat/market tables. | Core foundation. |
| `sql/020_plate_appearances.sql` | Creates `core.plate_appearances`, `features.plate_appearance_examples`, binary PA targets. | PA foundation. |
| `sql/030_reference_metadata.sql` | Source-preserved Retrosheet bio/team/park reference tables and metadata joins. | Reference metadata. |
| `sql/040_auxiliary_retrosheet.sql` | Auxiliary Retrosheet raw tables and normalized core views for rosters, schedules, umpires, coaches, ejections, relatives. | Auxiliary metadata. |
| `sql/050_feature_marts.sql` | Prior-season batter, pitcher, team, context, and half-inning summary marts. | First ML feature marts. |
| `sql/060_advanced_feature_marts.sql` | Career-prior, matchup, park, coarse context, and rolling team features. | Advanced ML features. |
| `sql/070_temporal_and_production_marts.sql` | Team rest/travel, player production, pitcher production, temporal examples. | Reporting and time context. |
| `sql/075_interface_workflows.sql` | Persists Sim Lab runs and extends chat logs for interface workflow auditability. | Web command center. |
| `sql/076_plate_appearance_outcome_model.sql` | Creates granular multiclass PA outcome examples, season/rules era columns, and target `pa_outcome_distribution`. | Multiclass PA modeling, temporal features. |
| `sql/077_pitch_sequence_model.sql` | Normalizes `pitch_seq_tx` into one row per Retrosheet sequence symbol with official symbol semantics and coarse pitch/result groupings. | Pitch-sequence normalization, future pitch-level modeling. |
| `sql/078_plate_appearance_outcome_grouped.sql` | Adds grouped PA outcome training examples and validation summary on top of the canonical granular PA outcome layer. | Baseline PA modeling, grouped target infrastructure. |
| `sql/079_probability_evaluation_reports.sql` | Adds durable calibration and bootstrap report tables plus recent-report views in `predictions`. | Probability evaluation persistence. |
| `sql/081_probability_calibration_artifacts.sql` | Extends calibration reports with persisted artifact support for reusable calibrated scoring. | Calibrated inference infrastructure. |
| `sql/082_count_state_feature_marts.sql` | Adds batter/pitcher/context prior-rate marts split by ball-strike count and a count-state-enhanced advanced PA view. | Targeted feature improvement for PA reliability defects. |

## Live And Inference SQL

These files may be present as active development work. Treat them as live-bridge/inference candidates unless committed and documented in the rebuild path.

| File | Purpose | Status Guidance |
|---|---|---|
| `sql/080_half_inning_examples.sql` | Half-inning training examples beyond summary distribution. | Scenario modeling; verify before relying on it. |
| `sql/080_mlb_pbp.sql` | Stores detailed MLB play‑by‑play data from StatsAPI & Statcast. | Added to warehouse rebuild after core tables.
| `sql/090_mlb_live_data.sql` | Raw MLB live snapshot tables with source-preserved payloads and fetch provenance. | Live bridge. |
| `sql/091_mlb_reference_raw.sql` | Raw MLB reference endpoint snapshots for teams, rosters, people, venues, and standings. | MLB source coverage, raw reference ingestion. |
| `sql/095_mlb_reference_views.sql` | Typed `core` views over MLB reference snapshots for teams, rosters, players, venues, and standings. | MLB reference transforms, bridge/core enrichment. |
| `sql/122_live_pa_feature_parity.sql` | Creates `features.live_plate_appearance_advanced_count_examples`, the live feature-parity view for the historical `advanced_count` PA model contract. It now joins park priors and rolling team-form features for rows transformed through the repaired bridge path. | Live inference parity for `pa_outcome_distribution`. |
| `sql/092_live_odds_views.sql` | Live odds/market-adjacent views. | Market/live candidate. |
| `sql/100_bridge_tables.sql` | Player/team/park/game crosswalks. | Live bridge and metadata reconciliation. |
| `sql/110_live_core_tables.sql` | `core.live_games` and `core.live_events` canonical live tables with snapshot/raw-play provenance. | Live bridge. |
| `sql/120_inference_optimization.sql` | Precomputed inference feature layer. | Performance candidate. |
| `sql/121_inference_functions.sql` | Fast DB functions and simulation state tables. | Performance/simulation candidate. |
| `sql/130_analysis_views.sql` | Combined analysis views for historical + live data queries. | Live bridge and analysis. |

## Warehouse Scripts
| File | Purpose | Use When |
|---|---|---|
| `scripts/warehouse.py` | Main CLI for dependency checks, Retrosheet fetch, Chadwick extract/load, and live feed fetch with raw snapshot provenance. | Ingestion and raw landing. |
| `scripts/rebuild_warehouse.sh` | Canonical full rebuild order. | Reproducibility. Update when adding required SQL. |
| `scripts/check_extensions.py` | **NEW** - Python helper to verify PostgreSQL extension installation status. Reports required/optional extensions with versions. | Setup validation, CI checks. |
| `scripts/install_chadwick.sh` | Chadwick installation helper. | Environment setup. |
| `scripts/load_reference_metadata.py` | Loads Retrosheet bio/team/park metadata. | After `020`. |
| `scripts/load_auxiliary_retrosheet.py` | Loads broader Retrosheet auxiliary files. | After reference metadata. |
| `scripts/fetch_mlb_schedule.py` | Discovers active MLB games for live ingestion. | Live bridge work. |
| `scripts/download_mlb_bulk.py` | Canonical historical MLB bulk raw backfill into `raw_mlb.schedule_snapshots` and `raw_mlb.live_feed_snapshots` with request/status/error provenance. | Historical MLB raw backfill. |
| `scripts/fetch_mlb_reference_data.py` | Canonical MLB reference endpoint fetcher for teams, rosters, people, venues, and standings into `raw_mlb.reference_snapshots`. | MLB source coverage, raw reference backfill. |
| `scripts/raw_mlb_backfill_status.py` | Canonical status report for raw MLB backfill progress across schedules, live feeds, reference endpoints, and transformed live rows. | Backfill monitoring, runbook support. |
| `scripts/populate_bridge_tables.py` | Downloads Chadwick Register and populates player mappings plus canonical team/park bridge mappings from the typed MLB reference views. Tolerates current bridge-schema variations in the active database. | Live bridge setup and reconciliation refresh. |
| `scripts/ingest_live_games.py` | Orchestrates batch live game ingestion using environment-driven Postgres settings. | Live bridge work. |
| `scripts/transform_live_game.py` | Transforms stored MLB live snapshots into canonical `core.live_games` / `core.live_events` with upserts and raw JSON preservation. | Live bridge work. |
| `scripts/demo_full_system.py` | **Interactive system evaluation tool**. Demonstrates all components: source adapters, pipelines, feature calculators, CLI, database. | System discovery, onboarding, health checks. |

## Legacy Scripts Archive (`scripts_legacy/`)

**Milestone 9: Scripts that have been superseded by the `baseball` CLI and moved to archive.**

These scripts are **NOT actively maintained** but preserved for reference.

| File | Purpose | Migration Path |
|---|---|---|
| `scripts_legacy/complete_mlb_ingestion.sh` | End-to-end MLB historical ingestion. | Replaced by `baseball mlb download/ingest` |
| `scripts_legacy/ingest_all_mlb_parallel.sh` | Parallel MLB data ingestion. | Replaced by `baseball mlb ingest --parallel` |
| `scripts_legacy/ingest_all_external.sh` | External data ingestion (Lahman, ESPN, etc.). | Replaced by `baseball lahman/espn/statcast` |
| `scripts_legacy/monitor_mlb_ingestion.sh` | Monitor ingestion progress. | Replaced by `baseball status` |
| `scripts_legacy/demo_advanced_modeling.py` | Demo script for advanced modeling. | Replaced by `baseball models train` |
| `scripts_legacy/demo_chatbot_integration.py` | Demo script for chatbot integration. | Replaced by `baseball chatbot` |
| `scripts_legacy/fix_repo_issues.sh` | One-time repository cleanup script. | Archived |
| `scripts_legacy/data_ingestion/ingest_all_mlb_data.py` | Legacy MLB data ingestion. | Replaced by `MlbSource` adapter |
| `scripts_legacy/data_ingestion/download_missing_2023.py` | One-time fix for 2023 data gaps. | Archived |
| `scripts_legacy/README.md` | Archive documentation with migration guide. | Reference |

**Migration Examples:**

```bash
# Old way (in scripts_legacy/)
./scripts/complete_mlb_ingestion.sh

# New way (using baseball CLI)
baseball mlb download --years 2000-2024
baseball mlb ingest --years 2000-2024

# Old way
./scripts/rebuild_warehouse.sh --mode full

# New way
baseball pipeline run --pipeline historical --year 2024
```

## Bridge Table Population (Fill Empty Tables)

| File | Purpose | Critical For |
|---|---|---|
| `scripts/populate_all_missing_data.sh` | **MASTER SCRIPT** - Runs all population scripts in correct order. Populates ALL empty tables. | One-command data fix. |
| `scripts/bridge/populate_mlb_players_venues_complete.py` | **NEW** - Populates mlb.players and mlb.venues from MLB API. Links venues to Retrosheet parks. | **CRITICAL**: features_pitch.mv_park_context needs venues! |
| `scripts/bridge/populate_live_plate_appearances.py` | **NEW** - Populates core.live_plate_appearances from raw_mlb.live_feed_snapshots. | Fills 0-row table. |

## External Data Ingestion (Complete Coverage)

| File | Purpose | Use When |
|---|---|---|
| `sql/external/210_lahman_complete.sql` | **NEW** - Complete Lahman Baseball Database schema with ALL 28 tables and ALL columns (replaces partial 210_lahman_raw.sql). | After downloading Lahman CSVs. |
| `sql/external/220_mlb_api_complete.sql` | **NEW** - Complete MLB Stats API schema with ALL endpoints (boxscore, play-by-play, pitch metrics, win probability, Gameday XML, etc.). | Before fetching MLB API data. |
| `scripts/external_data/load_lahman_complete.py` | **NEW** - Dynamic Lahman loader that reads CSV headers to discover ALL columns. Loads ALL 28 tables with 100% field coverage. Replaces selective load_lahman.py. | Loading Lahman data. |
| `scripts/data_ingestion/fetch_mlb_stats_api_complete.py` | **NEW** - Fetches ALL MLB Stats API endpoints (boxscore, PBP, pitch metrics, WP, Gameday XML, rosters, standings). Stores source-preserved JSONB. | Fetching MLB API data. |
| `docs/DATA_INGESTION_FIX_REPORT.md` | **NEW** - Detailed report on data ingestion gaps and fixes applied. | Understanding the fix. |
| `scripts/data_ingestion/fetch_espn_complete.py` | **NEW** - Fetches ALL ESPN data: player stats, team stats, plays. Fills empty raw_espn tables. | ESPN data population. |
| `scripts/data_ingestion/fetch_baseball_reference_complete.py` | **NEW** - Fetches Baseball-Reference game logs using pybaseball. Fills empty raw_baseball_reference.game_logs. | BR data population. |
| `scripts/replay_live_bridge_backfill.py` | Replays stored latest-successful MLB raw snapshots through `scripts/transform_live_game.py`, optionally targeting only rows that still carry `MLB###` fallback ids. | Controlled live bridge refresh after mapping or transform fixes. |
| `scripts/backup_sql_files.sh` | Copies all `.sql` files from the `sql/` directory into a timestamped backup folder for Git versioning. | Backup of schema definitions. |
| `scripts/backup_procedures.sh` | Backs up all database objects (functions, procedures, views, materialized views) to a timestamped SQL dump. | Database maintenance, disaster recovery. |
| `scripts/record_retrosheet_downloads.py` | Records comprehensive Retrosheet data downloads in monitoring table with file sizes, checksums, and metadata. | Retrosheet data acquisition tracking. |
| `scripts/load_statcast.py` | Loads free Statcast CSV data into `raw_mlb.statcast` and updates bridge tables. | Supplemental pitch-level data ingestion. |
| `scripts/load_baseballdata.py` | Loads Baseball-Data.com play-by-play CSV into `raw_external.baseball_data_com` and creates placeholder player bridge entries. | Supplemental historical PBP ingestion. |
| `scripts/fetch_espn_mlb.py` | Fetches MLB schedule and game data from ESPN API and stores source-preserved JSON in `raw_espn`. | ESPN external data ingestion. |
| `scripts/populate_coach_umpire_bridge.py` | Populates `bridge.coach_xref` and `bridge.umpire_xref` from Retrosheet auxiliary data with biofile_legacy name resolution and confidence scoring. | Coach/umpire bridge table population. |
| `scripts/bridge/populate_game_xref.py` | Populates `bridge.game_xref` by matching games between Retrosheet and MLB using date and team IDs. | Game cross-reference mapping. |
| `scripts/bridge/populate_season_aware_team_xref.py` | Populates season-aware team mappings in `bridge.team_xref` to handle historical franchise moves. | Team season coverage. |
| `scripts/bridge/populate_external_bridge.py` | Populates `bridge.external_player_xref` for Statcast, Baseball Reference, and Lahman data sources using player_xref as source of truth. | External player ID mappings. |
| `scripts/bridge/populate_espn_bridge.py` | Populates `bridge.external_player_xref` and `bridge.external_team_xref` for ESPN IDs using MLBAM ID cross-references. | ESPN ID mappings. |
| `scripts/bridge/investigate_coach_names.py` | Investigates whether coach names can be resolved using biofile_legacy data (coach_id matches player_id). | Coach name resolution research. |
| `scripts/bridge/investigate_umpire_ids.py` | Investigates umpire MLB ID mapping options using available data sources. | Umpire ID mapping research. |
| `scripts/bridge/ingest_chadwick_register.py` | **CHADWICK REGISTER INGESTION** - Downloads and ingests Chadwick Bureau Register CSV files (16 files: people-0-9,a-f). Parses 58 ID fields, loads to staging table, upserts to player_xref. Supports --dry-run, --validate-only, --suffixes flags. | Chadwick-based player ID cross-reference population. |
| `scripts/bridge/run_bridge_ingestion.py` | **ORCHESTRATED BRIDGE INGESTION** - New orchestrator with validation layer, error handling (retry + circuit breaker), and checkpointing. CLI interface with --skip-download, --skip-validation, --no-checkpoints flags. Replaces populate_all_bridge_tables.sh for Python-based workflows. | Production bridge population with full error handling. |
| `scripts/bridge/view_metrics.py` | **VIEW OPERATION METRICS** - CLI to view collected metrics and generate reports. Supports --days, --operation-type, --json flags. | Pipeline observability and monitoring. |
| `scripts/bridge/populate_all_bridge_tables.sh` | **MASTER BRIDGE ORCHESTRATOR** - Complete bridge table population in 6 stages: (1) SQL procedures, (2) Chadwick data, (3) Lahman gap-fill, (4) External bridges, (5) Validation tests, (6) Summary report. Idempotent, supports --validate-only, --skip-* flags. | Complete bridge table population workflow. |
| `scripts/download_statcast_pitch_level.py` | Downloads Statcast pitch-level data using pybaseball.statcast() for date ranges or seasons. | Statcast pitch-level data download. |
| `scripts/ingest_espn_plays.py` | Ingests ESPN play-by-play data into `raw_espn.plays` table. | ESPN external data ingestion |
| `scripts/kb/chunk_sources.py` | Chunks sabermetrics source documents into JSONL files with metadata for RAG ingestion. Organizes by source and by topic. | KB chunking pipeline. |
| `scripts/check_extensions.py` | **NEW** - Verify PostgreSQL extension status; prints installed/missing extensions with install commands. | Setup validation, CI checks. |
| `scripts/test/run_pgtap.sh` | **NEW** - PostgreSQL unit test runner for pgTAP. Discovers test_* functions across schemas, executes with TAP output, aggregates results. | Database regression testing. |
| `scripts/test/run_bandit_security_scan.py` | **NEW** - Run Bandit security scanner on Python code, generate HTML/JSON reports with severity filtering. | Security scanning, CI integration. |
| `scripts/test/run_vulnerability_scan.py` | **NEW** - Dependency vulnerability scanner using pip-audit. Checks pyproject.toml/requirements.txt for CVEs. | Dependency security, CI. |

## Pitch Data Scripts (Statcast Complete Loader)

| File | Purpose | Notes |
|---|---|---|
| `scripts/pitch_data/README.md` | Comprehensive documentation for Statcast pitch data loading. | Required reading before loading pitch data. |
| `scripts/pitch_data/load_all_statcast_full.py` | **PRIMARY LOADER** - Loads ALL 118 Statcast fields into `features_pitch.locations`. Includes verification, supports --all, --seasons, --force, --dry-run, --verify flags. | Always use this for complete pitch data loads. Never use partial loaders for production work. |
| `scripts/pitch_data/bulk_load_all_pitches.py` | Simplified bulk loader with basic fields only. | Use only for quick tests, not production. |
| `scripts/pitch_data/load_all_pitch_seasons.py` | Original batch loader with cursor. | Legacy - use load_all_statcast_full.py instead. |
| `sql/eda/030_gis_pitch_views.sql` | PostGIS analysis views for pitch location data: strike zone classification, heatmaps, batter zones, movement analysis, density maps, matchup patterns. | Run after pitch data load for analysis capabilities. |
| `sql/maintenance/022_migrate_full_statcast.sql` | Migration script to add missing columns to `features_pitch.locations`. | Run if schema needs updating. |

## Pitch-Level Feature Mart (Epic #78)

**CRISP-DM Phase 3: Data Preparation** | **GitHub Issues: #78 (Epic), #79 (Schema)** | **Branch: `feature/pitch-mart-schema`**

| File | Purpose | Status |
|---|---|---|
| `sql/features/003_pitch_flexible_mart.sql` | **PRIMARY SCHEMA** - Flexible feature mart with ALL 118 Statcast fields preserved. Creates 7 tables: base_features, feature_registry, engineered_features, sequential_features, player_context, model_training_set, pitch_sequences. Includes vw_xgboost_base view and dynamic feature selection functions. | ✅ Complete - All tables created |
| `sql/features/004_alter_base_features_types.sql` | Schema fix: Extend of_fielding_alignment to varchar(50) to prevent truncation errors. | ✅ Complete |
| `sql/features/005_build_engineered_features.sql` | **FEATURE ENGINE** - Populates engineered_features with ALL research-backed derived features. 22KB script with velocity percentiles, strike zone regions, pitch movement, game context, count features, two-tier outcome labels. | ✅ Complete - 7.66M rows populated |
| `sql/features/006_additional_engineered_features.sql` | **ADDITIONAL FEATURES SCHEMA** - Adds 25+ advanced engineered features including pitch tunneling, spin characteristics, platoon indicators, fatigue metrics, pressure metrics, timing features, situational indicators. | ✅ Schema added |
| `sql/features/007_populate_additional_features.sql` | Single-pass population script for additional features. | Ready (use 008 for batching) |
| `sql/features/008_populate_additional_features_batch.sql` | **BATCHED POPULATION** - Processes additional features in 100k row batches for 7.66M rows. Run multiple times until complete. | 🔄 In Progress |
| `sql/features/009_more_engineered_features.sql` | **MORE FEATURES SCHEMA** - Adds 40+ research-backed features from KB analysis: pitch quality score, count leverage, TTOP (times through order), RE24, WPA, payoff pitch, game situation, environmental. | ✅ Schema added |
| `sql/features/010_populate_more_features.sql` | Single-pass population for more features (RE24, WPA, TTOP, pitch quality). | Ready |
| `sql/features/011_populate_more_features_batch.sql` | **BATCHED POPULATION** - Processes more features in 100k row batches. | 🔄 Ready |
| `sql/features/012_context_features_schema.sql` | **CONTEXT FEATURES SCHEMA** - Adds 60+ weather, momentum, umpire, attendance, park factors, fatigue features from FEATURE_ENGINEERING_PLAN.md Categories 2,3,4,7,8. | ✅ Schema added |
| `sql/features/013_populate_context_features.sql` | Population script for context features with game/park/umpire joins. | Ready (legacy - use 013a instead) |
| `sql/features/013a_optimized_context_features_mv.sql` | **OPTIMIZED** - Materialized views approach replacing slow UPDATEs. Creates 5 MVs: mv_game_context, mv_park_context, mv_team_momentum, mv_pitcher_fatigue, mv_all_context_features. Drops 1.6GB unused indexes. | ✅ **NEW - April 2025** |
| `sql/features/013b_refresh_context_features_procedure.sql` | Stored procedures for refreshing MVs with audit logging. Includes refresh_context_features() and refresh_context_features_with_audit(). | ✅ **NEW - April 2025** |
| `sql/features/014_populate_context_features_batch.sql` | **BATCHED POPULATION** - Processes context features in batches. | 🔄 Ready (legacy) |
| `scripts/pitch_data/populate_context_features_optimized.sh` | **OPTIMIZED ORCHESTRATION** - Shell wrapper for MV-based feature population. 5-15min vs 1-3 hours. Integrates with pg_cron for scheduled refresh. | ✅ **NEW - April 2025** |
| `sql/features/015_final_features_schema.sql` | **FINAL FEATURES SCHEMA** - Adds 50+ Markov chains, matchup history, postseason, sequence patterns, platoon splits, rookie/veteran classification. Completes FEATURE_ENGINEERING_PLAN.md. | ✅ Schema added |
| `sql/features/016_populate_final_features.sql` | Population script for final features with Markov calculations. | Ready |
| `sql/features/017_populate_final_features_batch.sql` | **BATCHED POPULATION** - Processes final features in batches. | 🔄 Ready |
| `sql/features/018_swing_model_schema.sql` | **SWING MODEL SCHEMA** - Tables for swing probability predictions, performance tracking, calibration curves. | ✅ Ready |
| `scripts/pitch_models/train_swing_probability.py` | **SWING PROBABILITY MODEL** - Binary classifier for P(swing). Research-backed features. | 🔄 Ready to train |
| `scripts/pitch_models/feature_ablation_study.py` | **FEATURE ABLATION STUDY** - Tests which feature groups actually improve predictions (Option A). | 🔄 Ready to run |
| `scripts/analysis/post_hoc_feature_selection.py` | **POST-HOC FEATURE SELECTION** - 3-phase workflow: 1) Train full model, 2) Test feature subsets (20-200 features), 3) Retrain optimal. Tests PAST 50 features with `--subset-sizes`. | Feature optimization |
| `sql/framework/002_feature_discovery_schema.sql` | **FEATURE DISCOVERY FRAMEWORK** - Schema for PCA, stepwise selection, correlations, optimal feature subsets. | ✅ Ready |
| `scripts/analysis/pca_feature_analysis.py` | **PCA ANALYSIS** - Dimensionality reduction, variance explained, component interpretation. | 🔄 Ready |
| `scripts/analysis/stepwise_feature_selection.py` | **STEPWISE SELECTION** - Forward/backward feature selection with performance tracking. | 🔄 Ready |
| `scripts/analysis/feature_discovery_master.py` | **FEATURE DISCOVERY ORCHESTRATOR** - Coordinates PCA, correlations, stepwise selection. | 🔄 Ready |
| `scripts/analysis/pitch_clustering_analysis.py` | **PITCH CLUSTERING** - K-Means/GMM unsupervised learning to discover natural pitch groupings. | 🔄 Ready |
| `scripts/analysis/feature_interaction_explorer.py` | **FEATURE INTERACTIONS** - Discover non-linear feature pairs that predict outcomes better together. | 🔄 Ready |
| `scripts/analysis/generate_schema_diagram.py` | **NEW** - Generate ERD diagrams of database schemas (Graphviz). Automated schema visualization for documentation. | Tooling |
| `scripts/analysis/visualize_dependencies.py` | **NEW** - Generate code dependency graphs (Python imports, SQL execution order) using AST parsing. | Tooling |
| `scripts/analysis/analyze_query_plan.py` | **NEW** - Visualize PostgreSQL query execution plans as Graphviz trees with cost/row estimates. | Tooling |
| `scripts/analysis/code_complexity_analyzer.py` | **NEW** - AST-based complexity analyzer: cyclomatic complexity, function length, class metrics. | Quality metrics |
| `scripts/test/run_pgtap.sh` | **NEW** - PostgreSQL unit test runner for pgTAP (already added earlier). | Testing |
| `docs/PITCH_FEATURE_MART_SCHEMA.md` | Comprehensive schema documentation. Table reference, usage patterns, design principles, data lineage, performance considerations. | Complete |
| `docs/diagrams/PITCH_FEATURE_MART_ERD.puml` | Entity relationship diagram showing all 7 tables and relationships. | Complete |
| `docs/diagrams/PITCH_DATA_FLOW.puml` | Data flow architecture diagram from sources through processing to models with CRISP-DM labels. | Complete |
| `sql/features/001_pitch_data_quality.sql` | Data quality flags and clean/strict views for pitch data. | Existing |
| `sql/features/002_player_profile_mart.sql` | Player profile mart schema for pitcher arsenals and batter zones. | Existing |
| `docs/PITCH_PLAYER_ANALYSIS_ARCHITECTURE.md` | Architecture document for pitch-to-player attribution and feature engineering. | Existing |
| `docs/STATCAST_MODELS_RESEARCH_REPORT.md` | Research on external Statcast pitch modeling repositories and architectures. | Existing |
| `docs/research_paper.md` | **PRIMARY RESEARCH DOC** - Mathematical formulations for pitch-level models. Includes equations for Two-Tier, LSTM, Multi-Task, and Swing Probability models. Loss functions, evaluation metrics, research alignment. | **NEW - April 2026** |
| `docs/CRISP_DM_IMPLEMENTATION_PLAN.md` | Updated with Phase 3 completion (100%) and pitch-level milestones. Phase progress, next actions, milestones. | **Updated April 2026** |
| `docs/agents/CURRENT_SNAPSHOT.md` | Updated with pitch-level data state and current objectives. | **Updated April 2026** |
| `AGENTS.md` | Added AI Agent Documentation Update Protocol section. Instructions for maintaining CRISP-DM docs, research paper, and GitHub issue updates. | **Updated April 2026** |

### Status: Epic #78 Phase 4 In Progress 🔄

**Completed April 24, 2026 (Sub-Issue #79):**
- ✅ Schema created: 7 tables in database
- ✅ Base features: 7,661,992 rows populated (2015-2025, 118 Statcast fields)
- ✅ Engineered features: 7,661,992 rows with **46+** (original) + **25** + **40** + **60+** + **50+ final** = **220+ total features**
- ✅ Feature registry: 220+ features documented across 17 SQL files
- ✅ Outcome labels: Tier 1 {S,B,X}, Tier 2 {12 classes}
- ✅ Documentation: AGENTS.md, PITCH_MODEL_PROGRESS.md updated
- ✅ GitHub: Epic #78 and Sub-Issue #79 updated with progress
- ✅ Validation: SQL headers fixed, tests passing
- CRISP-DM Phase 3: 100% Complete

**Phase 4: Modeling (In Progress):**
- Tier-1 XGBoost baseline training
- Tier-2 XGBoost fine-grained outcomes
- Model evaluation and calibration

**Scripts:**
- `scripts/pitch_data/populate_base_features.py` - Data migration from locations to base_features with column mapping. | Population |
- `scripts/pitch_data/orchestrate_feature_population.py` - **MASTER ORCHESTRATOR** - Runs all 13 phases of feature population in correct order. Phase 0-12 with verification and resume capability. Usage: `--all`, `--phase N`, `--verify`. | Feature population orchestration |
- `scripts/pitch_data/batch_feature_runner.sh` - **BATCH RUNNER** - Runs batch SQL files in a loop until complete. Progress tracking, resume capability, stall detection. Usage: `--sql-file <path>`, `--max-iterations N`. | Repeatable batch population |
- `scripts/train_models.py` - Tier-1 model training

### Feature Mart Schema Design

The flexible feature mart follows the principle: **"All fields available, selective inclusion"**

**Tables:**
- `features_pitch.base_features` - All 118 Statcast fields preserved
- `features_pitch.feature_registry` - Metadata catalog for dynamic feature selection
- `features_pitch.engineered_features` - Derived metrics (NULL-free storage)
- `features_pitch.sequential_features` - LSTM/Transformer sequences with JSONB windows
- `features_pitch.player_context` - Rolling statistics (30day/season/career windows)
- `features_pitch.model_training_set` - Versioned training data with SHA-256 data_hash
- `features_pitch.pitch_sequences` - PA-level aggregation with full pitch arrays

**Key Capabilities:**
- Metadata-driven queries: `SELECT features WHERE 'xgboost' = ANY(model_usage)`
- Versioned training data with exact reproducibility via data_hash
- Additive schema - new features without migrations
- JSONB for variable-length LSTM sequences

## Diagnostic and Workaround Scripts

| File | Purpose | Notes |
|---|---|---|
| `tmp/diagnose_sql_mangling.sh` | Diagnostic script to identify zsh globsubst SQL mangling issues and configuration sources. | Shell configuration debugging |
| `tmp/bash_tool_sql_mangling_issue_prompt.md` | Comprehensive prompt documenting bash tool SQL mangling issue for other AI agents. | Shell configuration reference |
| `tmp/apply_confidence_scoring.sh` | Bash script to apply confidence scoring migration (works around SQL mangling in bash tool). | Bridge table setup |
| `tmp/run_coach_umpire_procedures.sh` | Bash script to run coach_xref and umpire_xref procedures (works around SQL mangling in bash tool). | Bridge table population |

## Modeling Scripts

| File | Purpose | Targets / Outputs |
|---|---|---|
| `scripts/train_models.py` | General binary model trainer for game, PA, and some half-inning targets. | `game_home_win`, `pa_batter_*`, `half_inning_*`; writes `data/models/`, registers `models.model_registry`. |
| `scripts/model_training/run_model_training_campaign.py` | **MASTER TRAINING ORCHESTRATOR** - Trains all production models (swing, contact, hit, win). Supports --all, --compare, --target. Uses LegacyCompatibleTrainer. | All targets; writes `models/production/`, saves metadata JSON. |
| `scripts/model_training/train_with_framework.py` | **FRAMEWORK INTEGRATION** - Production wrapper bridging legacy scripts with new ModelTrainer framework. Supports legacy args and YAML configs. | Single model training with framework integration. |
| `scripts/demo_advanced_modeling.py` | **DEMONSTRATION** - Complete demo of multinomial models, Markov simulation, EV betting. Showcases all 8 model types from ChatGPT spec. | Demo outputs, no artifacts. |
| `scripts/train_pa_outcome_distribution.py` | Dedicated multiclass PA outcome distribution trainer. Supports `basic`, `advanced`, and `advanced_count` feature sets. | `pa_outcome_distribution`; writes `data/models/`, registers `models.model_registry`. |
| `scripts/sweep_pa_outcome_temporal.py` | Runs reproducible temporal-policy sweeps against the PA outcome distribution trainer and emits comparable benchmark rows. | Recent-window and recency-weighting policy selection for `pa_outcome_distribution`. |
| `scripts/analyze_pa_outcome_calibration.py` | Runs read-only calibration bins, per-class ECE summaries, and subgroup reliability diagnostics for a registered multiclass PA outcome model. | Probability-quality evaluation for `pa_outcome_distribution`. |
| `scripts/calibrate_pa_outcome_model.py` | Runs read-only post-hoc isotonic calibration experiments on a registered multiclass PA outcome model and compares held-out raw vs calibrated metrics. | Calibration-layer experiments for `pa_outcome_distribution`. |
| `scripts/bootstrap_pa_outcome_evaluation.py` | Runs season-stratified cluster bootstrap evaluation using cached per-game sufficient statistics for a registered multiclass PA outcome model. | Uncertainty estimation for `pa_outcome_distribution`. |
| `scripts/persist_pa_outcome_reports.py` | Persists raw calibration diagnostics, held-out isotonic comparisons, and bootstrap summaries for a registered multiclass PA outcome model into warehouse report tables. | Durable evaluation artifacts for `pa_outcome_distribution`. |
| `scripts/register_pa_outcome_calibration.py` | Fits, saves, and registers a reusable isotonic calibration artifact for a registered multiclass PA outcome model. | Calibrated inference path for `pa_outcome_distribution`. |
| `scripts/predict_pa_outcome_distribution.py` | Scores a historical PA with the registered multiclass outcome model and returns class + derived probabilities. | Historical multiclass inference path. |
| `scripts/predict_live_pa_outcome_distribution.py` | Scores a stored live MLB plate appearance from the live parity view using the registered multiclass PA outcome model and optional calibration artifact. | Live multiclass inference path. |
| `scripts/sweep_hyperparameters.py` | Deterministic candidate grid/sweep training. | Candidate model registry rows. |
| `scripts/promote_best_models.py` | Promotes best registered model versions based on thresholds. | Updates `models.model_registry.is_active`. |
| `scripts/auto_promote_models.py` | Candidate automation for model promotion. | Verify policy before using. |
| `scripts/cross_validate_models.py` | Cross-validation workflow. | Model quality and stability. |
| `scripts/analyze_pa_models.py` | Plate-appearance model comparison report. | Current binary PA model health. |
| `scripts/train_live_models.py` | Live-oriented model training candidate. | Verify against live schema before using. |

## Inference, Simulation, And Testing Scripts

| File | Purpose | Notes |
|---|---|---|
| `scripts/predict_plate_appearance.py` | Scores binary PA targets for a known historical PA using active models. | Current inference path for `pa_batter_*`. |
| `scripts/simulate_half_inning.py` | Monte Carlo half-inning simulator candidate. | Must use correct baseball state transitions before production use. |
| `scripts/fast_prediction_service.py` | Model caching and batch prediction service candidate. | Useful for simulation/live latency. |
| `scripts/test_inference_performance.py` | Inference benchmark tests. | Performance validation. |
| `scripts/test_baseball_analytics.py` | Data/schema/model smoke test suite candidate. | CI candidate. |
| `scripts/benchmark_queries.py` | SQL/query benchmark runner. | Warehouse performance. |
| `scripts/benchmark_report.py` | Benchmark reporting helper. | Query-performance reports. |
| `scripts/performance_test.py` | Performance experiment script. | Verify syntax/status before relying on it. |
| `scripts/simple_perf_test.py` | Simple performance demonstration. | Local investigation. |

## MLB Predict Framework (Python Library)

**Modular, Pydantic-based prediction framework with plugins, experiments, and simulations.**

### Configuration & Core (`mlb_predict/`)

| File | Purpose | Components |
|---|---|---|
| `mlb_predict/__init__.py` | Package exports. Exports ModelConfig, TrainResult, ModelTrainer, ExperimentRunner, etc. | Public API |
| `mlb_predict/config/schemas.py` | **PYDANTIC CONFIGURATION** - ModelConfig, ExperimentConfig, ModelFamily, TargetVariable, FeatureSet enums. YAML serialization, validation. | Config classes |
| `mlb_predict/config/__init__.py` | Config module exports. | load_config, save_config |
| `mlb_predict/core/trainer.py` | **MODEL TRAINER** - ModelTrainer class wrapping sklearn/xgboost/lightgbm. Plugin system integration, TrainResult generation. | ModelTrainer |
| `mlb_predict/core/experiment.py` | **EXPERIMENT RUNNER** - ExperimentRunner, ExperimentRun, ExperimentSummary classes. Multi-model comparison, hyperparameter sweeps. | ExperimentRunner |
| `mlb_predict/core/feature_loader.py` | **FEATURE LOADER** - FeatureLoader class for PostgreSQL feature marts. Train/val/test splits, DataSplit enum. | FeatureLoader |
| `mlb_predict/core/results.py` | **RICH RESULTS** - TrainResult, Metrics, MetricValue, Residuals, FeatureImportance dataclasses. | Result classes |
| `mlb_predict/core/registry.py` | **PLUGIN REGISTRY** - PluginRegistry, BasePluginModel, SklearnPluginModel. Model registration and discovery. | Plugin system |
| `mlb_predict/core/plugin_models.py` | Plugin model implementations. XGBoost, LightGBM, CatBoost, sklearn wrappers. | Plugin models |
| `mlb_predict/cli/main.py` | **UNIFIED CLI** - Command-line interface with train, experiment, sweep, info subcommands. argparse dispatch. | CLI entry point |
| `mlb_predict/cli/__init__.py` | CLI module exports. | create_parser, main |

### Source Adapters (`mlb_predict/sources/`)

**Unified data ingestion adapters implementing the BaseSource interface.**

| File | Purpose | Components |
|---|---|---|
| `mlb_predict/sources/__init__.py` | Source module exports. Exports BaseSource, all adapter classes, result dataclasses. | Public API |
| `mlb_predict/sources/base.py` | **BASE SOURCE INTERFACE** - BaseSource abstract base class with download(), ingest(), validate() methods. DownloadResult, IngestResult, ValidationResult dataclasses. | BaseSource, result classes |
| `mlb_predict/sources/mlb.py` | **MLB STATS API ADAPTER** - MlbSource class wrapping MLB Stats API scripts. Supports date ranges, seasons, individual games. fetch_today(), fetch_season() methods. | MlbSource |
| `mlb_predict/sources/retrosheet.py` | **RETROSHEET ADAPTER** - RetrosheetSource class wrapping Chadwick tools. Year range downloads, Chadwick event file parsing. get_seasons_available() for year discovery. | RetrosheetSource |
| `mlb_predict/sources/statcast.py` | **STATCAST ADAPTER** - StatcastSource class wrapping pybaseball. Season downloads, pitch-level data. get_available_seasons() (2015+). | StatcastSource |
| `mlb_predict/sources/espn.py` | **ESPN ADAPTER** - EspnSource class wrapping ESPN API scripts. Schedule, boxscores, player/team stats. Season-based downloads. | EspnSource |
| `mlb_predict/sources/lahman.py` | **LAHMAN ADAPTER** - LahmanSource class for Lahman Baseball Databank. CSV archive download, multi-table ingestion. get_table_counts() for row statistics. | LahmanSource |
| `mlb_predict/sources/live.py` | **LIVE ADAPTER** - LiveMlbSource class for real-time MLB game tracking. State polling, change detection, callbacks. Integration with existing ingest scripts. | LiveMlbSource, GameState |

**CLI Integration**: All adapters accessible via `baseball <source> <command>`:
```bash
baseball mlb {download,ingest,validate,today}
baseball retrosheet {download,ingest,validate,seasons}
baseball statcast {download,ingest,validate,seasons}
baseball espn {download,ingest,validate,seasons}
baseball lahman {download,ingest,validate,tables}
baseball live {games,watch,poll,predict,server}
```

### Live Pipeline (`mlb_predict/pipeline/`)

**Real-time prediction pipeline for live MLB games. Phase 3 implementation.**

| File | Purpose | Components |
|---|---|---|
| `mlb_predict/pipeline/__init__.py` | Pipeline module exports. | LivePredictionPipeline, LiveGameContext, PredictionResult, LiveModelManager |
| `mlb_predict/pipeline/live_prediction.py` | **LIVE PREDICTION PIPELINE** - Real-time prediction engine. `LivePredictionPipeline` class integrates `LiveFeatureStore` and `LiveModelManager`. Prediction caching, streaming predictions generator. Performance metrics (latency, cache hit rate). WebSocket-ready. | LivePredictionPipeline, LiveGameContext, PredictionResult |
| `mlb_predict/pipeline/model_manager.py` | **MODEL MANAGER** - `LiveModelManager` class. Loads trained models from disk/database (joblib/pickle). Lazy loading, model caching, fallback to heuristic. Feature validation. Prediction with confidence scoring. Integrates with existing model registry. | LiveModelManager, ModelMetadata |

**Key Features**:
- Incremental feature computation (only recompute changed features)
- Prediction caching with configurable TTL (default 5s)
- Sub-100ms latency target
- Real model loading (disk or database registry)
- Automatic fallback to heuristic when models unavailable
- State change callbacks for reactive updates
- Streaming predictions generator for WebSocket

**CLI Commands**:
```bash
baseball live games                    # Show active games
baseball live watch --game 123         # Watch single game with updates
baseball live poll --interval 30       # Poll all games
baseball live predict --game 123       # Real-time predictions
baseball live server                   # Start WebSocket server
```

### Streaming (`mlb_predict/streaming/`)

**WebSocket infrastructure for real-time prediction streaming. Phase 3 implementation.**

| File | Purpose | Components |
|---|---|---|
| `mlb_predict/streaming/__init__.py` | Streaming module exports. | PredictionWebSocketServer, PredictionStreamClient |
| `mlb_predict/streaming/server.py` | **WEBSOCKET SERVER** - `PredictionWebSocketServer` class. Multi-client support, per-game subscriptions, automatic polling, heartbeat/ping-pong, JSON message protocol. | PredictionWebSocketServer |
| `mlb_predict/streaming/client.py` | **WEBSOCKET CLIENT** - `PredictionStreamClient` class. Async client for consuming prediction streams. Callback-based API (on_prediction, on_connect, on_disconnect). Subscribe/unsubscribe to games. | PredictionStreamClient |

**WebSocket Protocol**:
```json
// Client -> Server
{"command": "subscribe", "game_pk": 12345}
{"command": "unsubscribe", "game_pk": 12345}
{"command": "games"}
{"command": "ping"}

// Server -> Client
{"type": "connected", "message": "...", "commands": [...]}
{"type": "prediction", "game_pk": 12345, "game_state": {...}, "prediction": {...}}
{"type": "subscribed", "game_pk": 12345}
{"type": "pong"}
```

**Usage**:
```bash
# Start server
baseball live server --port 8765

# Python client
from mlb_predict.streaming import PredictionStreamClient
client = PredictionStreamClient("ws://localhost:8765")
await client.connect()
await client.subscribe(12345)
```

### Features (`mlb_predict/features/`)

**Incremental feature computation for live predictions. Phase 3 implementation.**

| File | Purpose | Components |
|---|---|---|
| `mlb_predict/features/__init__.py` | Features module exports. | LiveFeatureStore, FeatureComputation, GameStateFeatures |
| `mlb_predict/features/live_features.py` | **INCREMENTAL FEATURE COMPUTATION** - `LiveFeatureStore` class with feature caching and partial updates. `GameStateFeatures` dataclass with feature vector generation. Change detection, hash-based cache invalidation, LRU eviction. Feature computation metadata tracking. | LiveFeatureStore, GameStateFeatures, FeatureComputation |

**Key Features**:
- Incremental feature computation (only recompute changed features)
- Hash-based cache keys for fast lookup
- LRU cache eviction (configurable size)
- Feature change tracking
- Sub-millisecond compute time for cache hits

**Usage**:
```python
from mlb_predict.features import LiveFeatureStore, LiveGameContext

store = LiveFeatureStore(max_cache_size=1000)
result = store.compute_features(context)

# Check what changed
print(f"Changed: {result.features_changed}")
print(f"Cache hit: {result.cache_hit}")
print(f"Compute time: {result.compute_time_ms:.2f}ms")
```

### Models (`mlb_predict/models/`)

| File | Purpose | Components |
|---|---|---|
| `mlb_predict/models/multinomial.py` | **MULTINOMIAL MODELS** - Implements all 8 model types from ChatGPT spec: MultinomialLogisticRegression, MultinomialXGBoost, MultinomialLightGBM, SimpleMLP, PlattScaler, MulticlassCalibration. Softmax outputs, probability calibration, ECE metrics. | Multinomial models |

### Simulation (`mlb_predict/simulation/`)

| File | Purpose | Components |
|---|---|---|
| `mlb_predict/simulation/markov_chain.py` | **MARKOV CHAIN SIMULATOR** - GameState, BaseState enums, MarkovChainSimulator. Plate appearance transitions, half-inning simulation, full game simulation, Monte Carlo win probability. | Markov simulator |

### Betting (`mlb_predict/betting/`)

| File | Purpose | Components |
|---|---|---|
| `mlb_predict/betting/ev_calculator.py` | **EV BETTING CALCULATOR** - Odds conversion, vig calculations, Kelly criterion, portfolio management, backtesting. MoneylineBet, RunLineBet, TotalBet, BettingOpportunity classes. EV calculator matching ChatGPT spec. | EV betting |

### Orchestration (`mlb_predict/orchestration/`)

| File | Purpose | Components |
|---|---|---|
| `mlb_predict/orchestration/__init__.py` | Orchestration module exports. | DatabaseOrchestrator, all configs, all engines |
| `mlb_predict/orchestration/config.py` | **PYDANTIC CONFIG MODELS** - Type-safe configuration for all DB operations. OperationConfig (base), FeaturePopulationConfig, BridgePopulationConfig, IngestOperationConfig, ValidationConfig, ModelTrainingConfig. All with validation and defaults. | 6 config classes |
| `mlb_predict/orchestration/results.py` | **RESULT MODELS** - Typed results for all operations. OperationResult (base), FeaturePopulationResult, BridgePopulationResult, IngestResult, ValidationResult, ModelTrainingResult, PhaseResult, BatchResult. | 8 result classes |
| `mlb_predict/orchestration/engines.py` | **OPERATION ENGINES** - Core logic for each operation type. BaseOperationEngine (ABC), FeaturePopulationEngine, BridgePopulationEngine, IngestionEngine, ValidationEngine, ModelTrainingEngine. Wrap SQL procedures with Pydantic interfaces. | 6 engine classes |
| `mlb_predict/orchestration/orchestrator.py` | **MAIN ORCHESTRATOR** - DatabaseOrchestrator class. Central controller that routes configs to engines. Unified entry point for all DB operations. Integrates with MLB Predict Framework. | DatabaseOrchestrator |
| `mlb_predict/orchestration/validation.py` | **VALIDATION LAYER** - Pre-flight and post-flight data quality checks. ValidationRule, ValidationResult, ValidationReport, ChadwickValidationRules, Validator classes. 6 validation checks for empty strings, duplicates, constraints. | Data quality validation |
| `mlb_predict/orchestration/error_handling.py` | **ERROR HANDLING LAYER** - Retry logic, circuit breakers, graceful degradation. RetryConfig, CircuitBreaker, OperationResult, DatabaseOperation classes. Exponential backoff, fault isolation. | Resilient operation execution |
| `mlb_predict/orchestration/checkpoints.py` | **CHECKPOINT MODELS** - Resumable operation tracking. Checkpoint, FeaturePhaseCheckpoint, BridgeTableCheckpoint, BatchProgressCheckpoint dataclasses. | Operation progress persistence |
| `mlb_predict/orchestration/adapter.py` | **SQL ADAPTER** - SQL file execution with parameter binding. SQLProcedureAdapter class for dynamic SQL loading and execution. | SQL procedure execution |
| `mlb_predict/orchestration/bridge_orchestrator.py` | **BRIDGE ORCHESTRATOR** - Complete bridge population pipeline with all abstraction layers. BridgeOrchestrator, CheckpointManager, StageResult classes. 5-stage pipeline with validation and error handling. | Production bridge population |
| `mlb_predict/orchestration/metrics.py` | **METRICS COLLECTION** - Track operation timing, success rates, row counts. OperationMetrics, MetricsCollector, MetricsReporter classes. JSON file persistence with optional DB storage. | Pipeline observability |
| `mlb_predict/orchestration/notifications.py` | **NOTIFICATION SYSTEM** - Multi-channel notifications for pipeline events. NotificationManager, ConsoleNotifier, WebhookNotifier classes. Event types: validation_failed, operation_completed, circuit_breaker_open. | Alerting and monitoring |

### Integration (`mlb_predict/integration/`)

| File | Purpose | Components |
|---|---|---|
| `mlb_predict/integration/legacy_bridge.py` | **LEGACY BRIDGE** - Bridges legacy train_models.py with new framework. create_config_from_legacy_args(), LegacyCompatibleTrainer, convert_legacy_metrics_to_framework(). Gradual migration support. | Legacy bridge |
| `mlb_predict/integration/__init__.py` | Integration module exports. | LegacyCompatibleTrainer, etc. |

### Configuration Examples (`configs/`)

| File | Purpose |
|---|---|
| `configs/xgboost_swing_decision.yaml` | Example XGBoost config for swing prediction. |
| `configs/lightgbm_contact_made.yaml` | Example LightGBM config for contact prediction. |

## Agent And Interface Scripts

| File | Purpose | Notes |
|---|---|---|
| `scripts/baseball_chatbot.py` | CLI/chatbot prototype with tools. | Prototype; web command center is current interface path. |
| `baseball-chatbot-ui/` | Next.js command center. | Human UI for chat, simulations, backtests, safe workbench. |
| `baseball-chatbot-ui/app/api/*` | API boundary between UI, Postgres, and allow-listed scripts. | Do not expose arbitrary shell or SQL writes. |

## Generated / Ignored Artifacts

| Path | Purpose | Rule |
|---|---|---|
| `data/raw/` | Downloaded raw Retrosheet/MLB data. | Do not commit. |
| `data/processed/` | Extracted/intermediate generated data. | Do not commit. |
| `data/models/` | Serialized model artifacts. | Do not commit; regenerate or store externally later. |
| `baseball-chatbot-ui/node_modules/` | Frontend dependencies. | Do not commit. |
| `baseball-chatbot-ui/.next/` | Frontend build output. | Do not commit. |
| `__pycache__/`, `.mypy_cache/`, `.ruff_cache/` | Python/tool caches. | Do not commit. |

## Unified CLI (baseball)

**Unified Typer CLI entry point for all data operations.**

| File | Purpose | Commands |
|---|---|---|
| `baseball/__init__.py` | Package version info. | Version constant |
| `baseball/__main__.py` | Module entry point (`python -m baseball`). | CLI launcher |
| `baseball/cli.py` | **UNIFIED CLI** - Typer app with all command groups. 600+ lines. System commands (doctor, status, version), data source commands (mlb, retrosheet, statcast, espn, lahman), ML commands (train, experiment), skeleton commands (predict, models, features). | All `baseball` commands |

**CLI Entry Point**:
```bash
baseball --help                    # Show all commands
baseball doctor                    # Check system health
baseball status                    # Show pipeline runs
baseball version                   # Show version info

# Data sources
baseball mlb {download,ingest,validate,today}
baseball retrosheet {download,ingest,validate,seasons}
baseball statcast {download,ingest,validate,seasons}
baseball espn {download,ingest,validate,seasons}
baseball lahman {download,ingest,validate,tables}

# ML workflow
baseball train --config configs/xgboost.yaml
baseball experiment --target swing_decision

# Pipeline orchestration
baseball pipeline list
baseball pipeline run --pipeline daily
baseball pipeline status
```

## Pipeline Service (`baseball/services/`)

**Pipeline execution and orchestration service. Milestone 8 implementation.**

| File | Purpose | Components |
|---|---|---|
| `baseball/services/pipeline.py` | **PIPELINE SERVICE** - `PipelineService`, `PipelineConfig`, `PipelineRun`, `PipelineStatus`, `StepStatus`. Configuration loading from YAML, step execution, checkpointing, resume support. Database integration with admin.pipeline_runs and admin.pipeline_checkpoints. | 507 lines |
| `config/pipelines.yml` | **PIPELINE CONFIGS** - 7 pipeline definitions (daily, historical, live, retrosheet_ingest, mlb_live_ingest, statcast_ingest, feature_building). Steps, checkpoint tables, poll intervals, parameters. | YAML config |

### Pipeline Commands

```bash
# List available pipelines
baseball pipeline list

# Run a pipeline
baseball pipeline run --pipeline historical --year 2024
baseball pipeline run --pipeline daily
baseball pipeline run --pipeline live --date 2026-04-27

# Resume from checkpoint
baseball pipeline run --pipeline daily --resume

# Check status
baseball pipeline status
baseball pipeline status --pipeline daily --limit 5
```

### Key Features

- **Configuration Loading**: Loads from `config/pipelines.yml`
- **Checkpointing**: Saves progress to `admin.pipeline_checkpoints`
- **Resume Support**: `--resume` flag restarts from last successful step
- **Database Logging**: All runs tracked in `admin.pipeline_runs`
- **Parameter Support**: `--year`, `--date` for pipeline parameters

## Admin SQL Tables

**Pipeline control and monitoring tables.**

| File | Purpose | Tables |
|---|---|---|
| `sql/00_admin/000_admin_pipeline_control.sql` | **ADMIN TABLES** - Pipeline tracking, checkpoints, error logging. Run once to create admin schema. | `admin.pipeline_runs`, `admin.pipeline_checkpoints`, `admin.pipeline_errors`, `admin.v_recent_pipeline_runs` |

**Table Descriptions**:
- `admin.pipeline_runs` - Tracks every pipeline execution with UUID, command, status, timing, metadata
- `admin.pipeline_checkpoints` - Resume capability with phase/position tracking
- `admin.pipeline_errors` - Error logging with stack traces and context
- `admin.v_recent_pipeline_runs` - Summary view with duration calculation

**Usage**:
```sql
-- View recent pipeline runs
SELECT * FROM admin.v_recent_pipeline_run ORDER BY started_at DESC LIMIT 10;

-- Check for failed runs
SELECT * FROM admin.pipeline_runs WHERE status = 'failed' ORDER BY started_at DESC;
```

## Live Dashboard (`dashboard/`)

**Real-time WebSocket-based dashboard for MLB predictions. Phase 3 implementation.**

| File | Purpose | Technology |
|---|---|---|
| `dashboard/index.html` | **LIVE DASHBOARD UI** - Single-page application for real-time game visualization. WebSocket client, auto-discovery of active games, win probability visualization, game situation display, connection status, debug logging. Pure HTML/CSS/JavaScript - no build step required. | HTML5, CSS3, JavaScript (ES6+) |
| `dashboard/README.md` | Dashboard documentation - setup, usage, troubleshooting. | Markdown |

**Features**:
- Real-time WebSocket connection to prediction server
- Auto-discovery of active MLB games
- Visual win probability bar (green = home, red = away)
- Live game situation (inning, outs, count, runners)
- Confidence scores and latency metrics
- Connection status with debug log
- Responsive dark mode UI

**Usage**:
```bash
# 1. Start WebSocket server
baseball live server --port 8765

# 2. Open dashboard
python3 -m http.server 8080 --directory dashboard
# Open http://localhost:8080

# 3. Connect to WebSocket
# Enter ws://localhost:8765 and click Connect
```

**Browser Compatibility**: Chrome 80+, Firefox 75+, Safari 13.1+, Edge 80+

## Deployment (`docs/deployment/`)

**Production deployment artifacts for Phase 3 live server.**

| File | Purpose |
|---|---|
| `docs/deployment/live_server.md` | **DEPLOYMENT GUIDE** - Complete documentation for production deployment. Systemd service setup, Docker containerization, PM2 process management, Nginx reverse proxy, SSL/TLS with Let's Encrypt, monitoring, performance tuning, troubleshooting. | Markdown |
| `docs/deployment/systemd/mlb-live-server.service` | **SYSTEMD SERVICE** - Production systemd service unit file. Security hardening, auto-restart, logging, environment variables. Ready for `systemctl enable mlb-live-server`. | systemd unit |
| `docs/deployment/nginx/mlb-live-server.conf` | **NGINX CONFIG** - WebSocket-enabled reverse proxy configuration. SSL/TLS, rate limiting, upstream backend, health checks, security headers. | nginx conf |
| `Dockerfile.live` | **DOCKER IMAGE** - Multi-stage Dockerfile for containerized deployment. Python 3.10 slim base, virtual environment, non-root user, health check. | Dockerfile |
| `ecosystem.config.js` | **PM2 CONFIG** - Process manager configuration. Auto-restart, memory limits, log rotation, deployment hooks. | PM2 config |

**Deployment Options**:

**1. Systemd Service (Recommended for Linux)**:
```bash
cp docs/deployment/systemd/mlb-live-server.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable mlb-live-server
systemctl start mlb-live-server
```

**2. Docker Container**:
```bash
docker build -f Dockerfile.live -t mlb-live-server .
docker run -p 8765:8765 \
  -e PGHOST=host.docker.internal \
  -e PGPASSWORD=secret \
  mlb-live-server
```

**3. PM2 Process Manager**:
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

**4. Nginx Reverse Proxy**:
```bash
cp docs/deployment/nginx/mlb-live-server.conf /etc/nginx/sites-available/
ln -s /etc/nginx/sites-available/mlb-live-server.conf /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

**SSL/TLS with Let's Encrypt**:
```bash
certbot --nginx -d cloudcurio.cc -d www.cloudcurio.cc -d predictions.cloudcurio.cc
```

**Production URLs**:
- Dashboard: `https://cloudcurio.cc/dashboard`
- WebSocket: `wss://cloudcurio.cc/ws`
- API: `https://predictions.cloudcurio.cc`

## Bridge Layer (`baseball/bridge/`)

**Phase 5: Cross-source ID resolution service. Maps entity IDs between MLB API, Retrosheet, ESPN, Lahman.**

| File | Purpose | Components |
|---|---|---|
| `baseball/bridge/__init__.py` | Bridge module exports. | PlayerXrefService, TeamXrefService, GameXrefService, XrefManager |
| `baseball/bridge/player_xref.py` | **PLAYER ID RESOLUTION** - Maps player IDs across MLB API (mlb_id), Retrosheet (retro_id), ESPN (espn_id), Lahman (lahman_id), Baseball-Reference (bbref_id), FanGraphs (fg_id). PlayerXref dataclass, lookup by any source, merge records. | PlayerXref, PlayerXrefService |
| `baseball/bridge/team_xref.py` | **TEAM ID RESOLUTION** - Maps team IDs across data sources. Canonical MLB team mappings loaded by default. 30 MLB teams with league/division info. | TeamXref, TeamXrefService |
| `baseball/bridge/game_xref.py` | **GAME ID RESOLUTION** - Maps game IDs between MLB API (game_pk), Retrosheet (YYYYMMDDTHH format), ESPN. Date-based indexing for range queries. | GameXref, GameXrefService |
| `baseball/bridge/xref_manager.py` | **COORDINATOR** - Unified manager for all xref services. High-level resolve methods, find games by matchup, load for season. | XrefManager |
| `sql/300_bridge_schema.sql` | **DATABASE SCHEMA** - bridge.player_xref, bridge.team_xref, bridge.game_xref tables with constraints and indexes. Helper functions for name/date lookups. | SQL DDL |

**Features**:
- Canonical ID resolution across 5+ data sources
- Bidirectional lookup (any source → canonical → all sources)
- Record merging with source priority
- In-memory caching + database persistence
- Date range queries for games
- Team matchup search

**Usage**:
```python
from baseball.bridge import XrefManager

manager = XrefManager(db_connection=conn)
manager.load_all()

# Resolve player by MLB ID
player = manager.resolve_player('mlb', 12345)
print(player.retro_id, player.espn_id)

# Look up team by code
team = manager.teams.lookup_by_code('NYY')

# Find games by Retrosheet ID
game = manager.games.lookup_by_retro('202604040NYY01')
```

## Phase 6: Features (`sql/`, `baseball/features/`)

**ML-ready feature computation layer.**

### Feature SQL Schema

| File | Purpose | Components |
|---|---|---|
| `sql/500_features_win_expectancy.sql` | **WIN EXPECTANCY** - WE matrix table, functions, views. Tables: `win_expectancy_matrix`, `game_state_we`, `win_expectancy_history`. | SQL |
| `sql/501_features_leverage_index.sql` | **LEVERAGE INDEX** - LI matrix, clutch stats. Tables: `leverage_index_matrix`, `game_state_li`, `player_clutch_stats`. | SQL |
| `sql/502_features_matchup.sql` | **MATCHUP** - Batter vs pitcher features. Tables: `batter_vs_pitcher_matchups`, `platoon_splits`, `matchup_features`. Functions: `get_matchup_features()`, `calculate_platoon_advantage()`. | SQL |
| `sql/503_features_rolling_form.sql` | **ROLLING FORM** - Recent performance. Tables: `batter_rolling_form`, `pitcher_rolling_form`, `rolling_form_features`. Views: `hot_batters`, `hot_pitchers`, `cold_batters`, `cold_pitchers`. | SQL |
| `sql/504_features_bullpen.sql` | **BULLPEN** - Fatigue and depth. Tables: `bullpen_status`, `reliever_fatigue`, `bullpen_features`. Functions: `calculate_reliever_fatigue_score()`, `calculate_team_bullpen_fatigue()`. | SQL |

### Feature Python Classes

| File | Purpose | Components |
|---|---|---|
| `baseball/features/__init__.py` | Module exports. | All calculators and dataclasses |
| `baseball/features/base.py` | **BASE CLASSES** - `FeatureStore`, `FeatureConfig`, `FeatureResult`, `GameState`. Enums: `FeatureScope`, `FeatureStatus`. | 300+ lines |
| `baseball/features/win_expectancy.py` | **WE CALCULATOR** - `WinExpectancyCalculator`. Win probability, WPA, game series. | 300+ lines |
| `baseball/features/leverage_index.py` | **LI CALCULATOR** - `LeverageIndexCalculator`. Leverage ratings, clutch tracking. | 350+ lines |
| `baseball/features/matchup.py` | **MATCHUP CALCULATOR** - `MatchupCalculator`, `MatchupHistory`, `PlatoonSplit`. Head-to-head history, platoon advantage, matchup scores. | 350+ lines |
| `baseball/features/rolling_form.py` | **FORM CALCULATOR** - `RollingFormCalculator`, `BatterForm`, `PitcherForm`. 7/14/30 day windows, hot/cold detection, trends. | 400+ lines |
| `baseball/features/bullpen.py` | **BULLPEN CALCULATOR** - `BullpenCalculator`, `TeamBullpenStatus`, `RelieverFatigue`. Fatigue scoring, availability, bullpen advantage. | 450+ lines |
| `baseball/features/run_expectancy.py` | **RUN EXPECTANCY CALCULATOR** - `RunExpectancyCalculator`. 24 base-out states, RE24 matrix, expected runs by game state. | 200+ lines |

### Key Features

**Win Expectancy (WE)**:
- Probability of home team winning from any game state
- 24 base states (outs × base runners) × innings × score differentials
- WPA (Win Probability Added) for play-by-play analysis

**Leverage Index (LI)**:
- Situational importance (1.0 = average, 2.0+ = high leverage)
- Categorical ratings: low, medium, high, very_high
- Clutch performance tracking by player

**Matchup Features**:
- Career head-to-head history (batter vs pitcher)
- Platoon splits (lefty/righty performance)
- Combined matchup score (0-1)
- `features.hot_batters` and `features.hot_pitchers` views

**Rolling Form**:
- 7/14/30 day performance windows
- Hot/cold detection with thresholds
- Trend direction (improving/declining/stable)
- Form advantage calculations

**Bullpen Features**:
- Individual reliever fatigue scores
- Team bullpen availability counts
- Fatigue and depth scores (0-1)
- Comparative bullpen advantage

**Run Expectancy (RE)**:
- Expected runs for remainder of inning from any base-out state
- 24 base states (3 outs × 8 runner combinations)
- RE24 value: run expectancy change from play
- Built from historical data, stored in `features.run_expectancy_matrix`

**Usage**:
```python
from baseball.features import (
    WinExpectancyCalculator, LeverageIndexCalculator, RunExpectancyCalculator,
    MatchupCalculator, RollingFormCalculator, BullpenCalculator,
    GameState
)

# Win Expectancy
calc = WinExpectancyCalculator(db_connection=conn)
calc.load_from_db(season=2026)
state = GameState(inning=9, is_top=False, outs=2, runner_1b=True)
we = calc.compute(state)

# Matchup
calc = MatchupCalculator(db_connection=conn)
score = calc.compute_matchup_score(batter_id=123, pitcher_id=456, season=2026)
is_advantage = calc.is_platoon_advantage(batter_id=123, pitcher_id=456)

# Rolling Form
calc = RollingFormCalculator(db_connection=conn)
form = calc.get_batter_form(player_id=123, season=2026)
if form.is_hot:
    print(f"Hot batter! L14 OPS: {form.l14_ops:.3f}")

# Bullpen
calc = BullpenCalculator(db_connection=conn)
advantage = calc.get_bullpen_advantage(home_id=147, away_id=118, game_pk=777777, season=2026)
print(advantage['narrative'])
```

## Phase 6.4/6.5: Models (`sql/`, `baseball/models/`)

**Prediction models for next-run probability and PA outcomes.**

### Model SQL Schema

| File | Purpose | Components |
|---|---|---|
| `sql/601_models_next_run.sql` | **NEXT-RUN MODEL** - Binary classification (will a run score?). Tables: `next_run_training_data`, `next_run_features`, `next_run_predictions`. Functions: `populate_next_run_training()`, `compute_next_run_features()`. Views: `next_run_calibration`, `next_run_performance`. | SQL |
| `sql/602_models_pa_outcome.sql` | **PA OUTCOME MODEL** - Multi-class classification (out/walk/single/double/triple/HR). Tables: `pa_outcome_training_data`, `pa_outcome_features`, `pa_outcome_predictions`. Type: `pa_outcome_category`. Views: `pa_outcome_accuracy`, `batter_prediction_summary`. | SQL |
| `sql/6001_models_registry.sql` | **MODEL REGISTRY** - `models.registry`, `models.versions` tables. Model metadata, versioning, deployment tracking. | SQL |
| `sql/601_run_expectancy.sql` | **RUN EXPECTANCY** - `features.run_expectancy_matrix` table. 24 base-out states, expected runs calculation. | SQL |

### Model Python Classes

| File | Purpose | Components |
|---|---|---|
| `baseball/models/__init__.py` | Module exports. | BaseModel, ModelConfig, NextRunProbabilityModel, PAOutcomeModel |
| `baseball/models/base.py` | **BASE CLASSES** - `BaseModel` (abstract), `SklearnBaseModel`, `ModelConfig`, `TrainingConfig`, `ModelResult`, `ModelVersion`. Enums: `ModelType`, `ModelStatus`. | 400+ lines |
| `baseball/models/next_run_model.py` | **NEXT-RUN MODEL** - `NextRunProbabilityModel`. Binary classifier (XGBoost/RF/LogReg) predicting P(run scores). Features: game state, WE, LI, matchup, form. | 350+ lines |
| `baseball/models/pa_outcome_model.py` | **PA OUTCOME MODEL** - `PAOutcomeModel`. Multi-class classifier for 6 outcome categories. Class probabilities, expected bases, expected runs. | 400+ lines |
| `baseball/models/win_probability_model.py` | **WIN PROBABILITY MODEL** - `WinProbabilityModel`. XGBoost binary classifier predicting home team win probability from game state. | 300+ lines |

### Key Model Features

**Next-Run Probability Model**:
- Binary classification: will at least one run score in remainder of inning?
- Features: game state, win expectancy, leverage index, matchup, form
- Target: `did_run_score` from training data
- Evaluation: accuracy, precision, recall, ROC-AUC, Brier score

**PA Outcome Model**:
- Multi-class: out, walk, single, double, triple, home run
- Class probabilities sum to 1.0
- Derived metrics: P(hit), P(on base), expected bases, expected runs
- Per-class precision/recall tracking

**Usage**:
```python
from baseball.models import NextRunProbabilityModel, PAOutcomeModel, WinProbabilityModel

# Win Probability Model
model = WinProbabilityModel(db_connection=conn)
config = TrainingConfig(train_seasons=[2024, 2025], test_seasons=[2026])
result = model.train(config)
print(f"Training accuracy: {result.metrics['val_accuracy']:.3f}")

# Next-Run Model
model = NextRunProbabilityModel(db_connection=conn)
config = TrainingConfig(train_seasons=[2024, 2025], test_seasons=[2026])
result = model.train(config)
print(f"Training accuracy: {result.metrics['val_accuracy']:.3f}")

# Predict
prob = model.predict_run_probability({
    'inning': 7, 'outs': 1, 'base_state': 5,
    'run_diff': 2, 'matchup_score': 0.6
})
print(f"Run probability: {prob:.1%}")

# PA Outcome Model
model = PAOutcomeModel(db_connection=conn)
result = model.train(config)

# Predict class probabilities
probs = model.predict_class_probabilities({
    'inning': 5, 'outs': 1, 'base_state': 1,
    'matchup_score': 0.6, 'batter_l14_ops': 0.920
})
print(f"HR probability: {probs['home_run']:.1%}")

# Full prediction with derived metrics
pred = model.predict_pa(features)
print(f"Expected bases: {pred['expected_bases']:.2f}")
print(f"Expected runs: {pred['expected_runs']:.3f}")
```

## Model Training (`scripts/models/`)

**Training pipeline for prediction models.**

| File | Purpose |
|---|---|---|
| `scripts/models/train_models.py` | **TRAINING PIPELINE** - Complete training workflow. Populates training data, computes features, trains Next-Run and PA Outcome models, evaluates, saves models, generates predictions. 400+ lines with CLI args for seasons, models, sampling. | Python CLI |

**Usage**:
```bash
# Train both models (2024-2025 train, 2026 test)
uv run python scripts/models/train_models.py \\
    --train-seasons 2024 2025 \\
    --test-seasons 2026 \\
    --models all

# Train only Next-Run model
uv run python scripts/models/train_models.py \\
    --train-seasons 2023 2024 2025 \\
    --test-seasons 2026 \\
    --models next_run

# Quick test mode (10% sample)
uv run python scripts/models/train_models.py \\
    --train-seasons 2025 \\
    --test-seasons 2026 \\
    --sample-rate 0.1

# Skip data prep (use existing training data)
uv run python scripts/models/train_models.py \\
    --train-seasons 2024 2025 \\
    --test-seasons 2026 \\
    --skip-data-prep
```

## Phase 7: Model Serving (`baseball/serving/`)

**Production model serving infrastructure.**

### Model Serving Components

| File | Purpose | Components |
|---|---|---|
| `baseball/serving/__init__.py` | Module exports. | ModelServer, ModelCache, PredictionAPI, WebSocketServer |
| `baseball/serving/model_server.py` | **MODEL SERVER** - `ModelServer` class. Loads models from disk, manages versions, prediction caching, hot-reloading. `ModelCache` LRU cache with TTL. | 400+ lines |
| `baseball/serving/prediction_api.py` | **REST API** - `PredictionAPI` Flask app. Endpoints: health, models, predict, batch, cache management. CORS enabled. | 300+ lines |
| `baseball/serving/websocket_server.py` | **WEBSOCKET** - `WebSocketServer` for real-time updates. Game subscriptions, client management, prediction streaming. | 350+ lines |

### Key Features

**ModelServer**:
- Load models: `latest`, `production`, specific version
- LRU prediction cache with configurable TTL
- Health checks and statistics
- Hot model reloading

**PredictionAPI (REST)**:
- `GET /health` - Health check
- `GET /models` - List loaded models
- `GET /models/<name>` - Model info
- `POST /models/<name>/load` - Load model
- `POST /predict/<model>` - Single prediction
- `POST /predict/<model>/batch` - Batch predictions
- `GET /cache/stats` - Cache statistics
- `POST /cache/clear` - Clear cache
- `GET /stats` - Server statistics
- `POST /reload` - Reload all models

**WebSocketServer**:
- Real-time prediction streaming
- Game-specific subscriptions
- Client management with ping/pong
- Message types: `subscribe`, `unsubscribe`, `predict`, `ping`

**Usage**:
```python
from baseball.serving import ModelServer, create_app, WebSocketServer

# Model Server
server = ModelServer(model_dir='models')
server.load_model('next_run', 'latest')
server.load_model('pa_outcome', 'latest')

# REST API
app = create_app(model_dir='models')
app.run(host='0.0.0.0', port=5000)

# WebSocket
ws = WebSocketServer(model_server=server, host='0.0.0.0', port=8765)
await ws.start()

# Make prediction
result = server.predict('next_run', {
    'inning': 7, 'outs': 1, 'base_state': 5,
    'we': 0.65, 'li': 1.8
})
print(f"Run probability: {result['run_probability']:.1%}")
```

## Phase 8: Chatbot (`baseball/chatbot/`)

**Natural language interface for baseball queries.**

### Chatbot Components

| File | Purpose | Components |
|---|---|---|
| `baseball/chatbot/__init__.py` | Module exports. | Chatbot, IntentParser, EntityExtractor, etc. |
| `baseball/chatbot/intent_parser.py` | **INTENT PARSING** - `IntentParser` class. Pattern matching for intents: prediction, game_info, player_stats, standings, schedule, comparison, explanation, greeting, help. | 300+ lines |
| `baseball/chatbot/entity_extractor.py` | **ENTITY EXTRACTION** - `EntityExtractor` class. Extracts teams (30 MLB teams), players, dates, numbers, stats from text. | 350+ lines |
| `baseball/chatbot/conversation_manager.py` | **CONVERSATION STATE** - `ConversationManager` class. Tracks history, context (active game/team/player), user preferences. `Message` and `ConversationContext` dataclasses. | 300+ lines |
| `baseball/chatbot/response_generator.py` | **RESPONSE GENERATION** - `ResponseGenerator` class. Natural language templates for each intent type. Handles greetings, help, predictions, stats, standings, schedules. | 350+ lines |
| `baseball/chatbot/chatbot.py` | **MAIN ORCHESTRATOR** - `Chatbot` class. Combines all components. Query handlers for each intent. `chat()` method for single interaction. | 400+ lines |

### Supported Intents

| Intent | Examples |
|---|---|
| `prediction` | "What's the win probability?", "Will the Yankees win?", "Run probability?" |
| `game_info` | "Who's pitching?", "What's the score?", "Current inning?" |
| `player_stats` | "Judge's batting average?", "Ohtani's ERA?", "Trout's OPS?" |
| `standings` | "Where are the Red Sox?", "Division standings?", "Wildcard race?" |
| `schedule` | "When do the Cubs play?", "Next game?", "Upcoming schedule?" |
| `comparison` | "Compare Judge and Ohtani", "Who's better, Trout or Betts?" |
| `explanation` | "How do predictions work?", "Why is the probability 65%?" |
| `greeting` | "Hello", "Hi", "Hey there" |
| `help` | "What can you do?", "Help", "Commands?" |

### Usage

```python
from baseball.chatbot import Chatbot

# Create chatbot
bot = Chatbot(model_server=ms, db_connection=conn)

# Single interaction
response = bot.chat("What's the Yankees win probability?")
print(response)

# Contextual conversation
bot.chat("What's the win probability for the Yankees?")
response = bot.chat("How about the Red Sox?")  # Remembers context
print(response)

# Get conversation summary
summary = bot.get_conversation_summary()
print(f"Messages: {summary['session_info']['message_count']}")

# Reset conversation
bot.reset_conversation()

# Get supported commands
commands = bot.get_supported_commands()
for cmd in commands:
    print(f"• {cmd}")
```

### CLI Usage

```bash
# Interactive chat mode
baseball chatbot chat --interactive

# Single query
baseball chatbot chat -m "What's the Yankees win probability?"

# Run demo conversation
baseball chatbot demo
```

**Interactive Mode Commands:**
- Type `help` to see example queries
- Type `quit`, `exit`, or `bye` to exit

## Testing (`scripts/`)

**End-to-end testing for Phase 3 components.**

| File | Purpose |
|---|---|---|
| `scripts/test_live_pipeline.py` | **E2E TEST SUITE** - Validates all Phase 3 components. Tests LiveMlbSource, LiveFeatureStore, LiveModelManager, LivePredictionPipeline, WebSocket server/client. 400+ lines of comprehensive tests. | Python CLI |

**Usage**:
```bash
# Quick tests (5 seconds)
uv run python scripts/test_live_pipeline.py --quick

# Full tests (30 seconds)
uv run python scripts/test_live_pipeline.py

# Start server for manual testing
uv run python scripts/test_live_pipeline.py --server
```

## If You Are About To Add A New File

Use this checklist:

- Can it be an additive section in an existing SQL migration instead?
- Can it be a new view in `features` rather than a new raw table?
- Can `scripts/train_models.py` or `scripts/train_pa_outcome_distribution.py` already train this target?
- Can the web API call an existing script or view?
- Did you update this inventory, `README.md`, `AGENTS.md`, and `docs/PROJECT_LOG.md` if the workflow changed?
