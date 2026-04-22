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
| `CHATBOT_INTERFACE_DESIGN.md` | Current/future web command-center design notes. | Interface, agents |

## Configuration

| File | Purpose | Notes |
|---|---|---|
| `config/chadwick_event_columns.txt` | Chadwick event-column reference used to avoid hand-invented mappings. | Check before changing raw event parsing. |
| `config/ai_providers.example.json` | Example provider configuration for OpenRouter, Groq, and Codex/OpenAI-compatible inference. | Never commit real keys. |
| `.env.example` | Safe local environment variable template. | Keep secrets out of git. |

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
| `sql/200_external_data.sql` | Defines schemas and tables for supplemental free data sources (Statcast, Baseball‑Data.com, Gameday XML) and bridge tables. | External data marts. |
| `sql/220_espn_schema.sql` | Defines `raw_espn` schema and tables for ESPN API data (game snapshots, schedule snapshots, player stats, team stats). | ESPN external data ingestion. |
| `sql/225_ingest_run_tracking.sql` | Expands `raw_retrosheet.ingest_runs` table with script metadata, adds helper functions for run logging, triggers for auto-timestamps, and monitoring views. | Ingest run tracking and reproducibility. |

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
| `sql/maintenance/999_master_installation.sql` | Master orchestrator for installing all PostgreSQL extensions and advanced features. | Complete extension installation. |

## Knowledge Base Documents

| File | Purpose | Canonical Position |
|---|---|---|
| `docs/KNOWLEDGE_BASE_SABERMETRICS.md` | Research findings on sabermetrics, baseball modeling, and prediction approaches. | Modeling reference. |
| `docs/KNOWLEDGE_BASE_MODELS_REPOS.md` | Research on useful baseball models and GitHub repositories for ML and sabermetrics. | Model research. |
| `docs/TABLE_ASSESSMENT_SABERMETRICS.md` | Assessment of current table structure for sabermetrics and baseball modeling requirements. | Schema assessment. |
| `docs/POSTGRESQL_EXTENSIONS_RESEARCH.md` | Research-backed recommendations for PostgreSQL extensions and features for baseball analytics. | Extension reference. |
| `docs/LIVE_BETTING_PIPELINE_STATUS.md` | Comprehensive status assessment for live betting and prediction infrastructure. | Live betting reference. |

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
| `scripts/download_statcast_pitch_level.py` | Downloads Statcast pitch-level data using pybaseball.statcast() for date ranges or seasons. | Statcast pitch-level data download. |
| `scripts/ingest_espn_plays.py` | Ingests ESPN play-by-play data into `raw_espn.plays` table. | ESPN external data ingestion |

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

## If You Are About To Add A New File

Use this checklist:

- Can it be an additive section in an existing SQL migration instead?
- Can it be a new view in `features` rather than a new raw table?
- Can `scripts/train_models.py` or `scripts/train_pa_outcome_distribution.py` already train this target?
- Can the web API call an existing script or view?
- Did you update this inventory, `README.md`, `AGENTS.md`, and `docs/PROJECT_LOG.md` if the workflow changed?
