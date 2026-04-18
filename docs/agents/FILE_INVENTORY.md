# File Inventory

## Issue Links

- Issue #5: Documentation & Issue Linking – completed. See [github_issues/issue_05_documentation_and_issue_linking.md](../github_issues/issue_05_documentation_and_issue_linking.md)
- Issue #1: Core LLM Integration – ongoing. See [github_issues/issue_01_core_llm_integration.md](../github_issues/issue_01_core_llm_integration.md)
- Issue #2: Tool Execution Engine – ongoing. See [github_issues/issue_02_tool_execution_engine.md](../github_issues/issue_02_tool_execution_engine.md)
- Issue #3: Model Orchestration – ongoing. See [github_issues/issue_03_model_orchestration.md](../github_issues/issue_03_model_orchestration.md)
- Issue #4: Security & Safety – ongoing. See [github_issues/issue_04_security_safety.md](../github_issues/issue_04_security_safety.md)
- Issue #6: Model Training Pipeline – ongoing. See [github_issues/issue_06_model_training_pipeline.md](../github_issues/issue_06_model_training_pipeline.md)
- Issue #7: Advanced Features – ongoing. See [github_issues/issue_07_advanced_features.md](../github_issues/issue_07_advanced_features.md)

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
| `CHATBOT_INTERFACE_DESIGN.md` | Current/future web command-center design notes. | Interface, agents |

## Configuration

| File | Purpose | Notes |
|---|---|---|
| `config/chadwick_event_columns.txt` | Chadwick event-column reference used to avoid hand-invented mappings. | Check before changing raw event parsing. |
| `config/ai_providers.example.json` | Example provider configuration for OpenRouter, Groq, and Codex/OpenAI-compatible inference. | Never commit real keys. |
| `.env.example` | Safe local environment variable template. | Keep secrets out of git. |
| `docker-compose.yml` | MCP gateway configuration for multi-database PostgreSQL access. | MCP server orchestration. |

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
| `sql/200_external_data.sql` | Defines schemas and tables for supplemental free data sources (Statcast, Baseball‑Data.com, Gameday XML) and bridge tables. | External data marts. |

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
| `sql/083_live_prediction_logging.sql` | Durable storage for live plate appearance predictions and API request tracking with feature snapshots, state snapshots, and prediction provenance. | Live prediction logging, monitoring, and calibration tracking. |
| `sql/084_pa_predictions_table.sql` | Historical PA predictions table with indexes for game_id, plate_appearance_id, model_id, prediction_run_id, prediction_timestamp. | Historical predictions storage. |

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
| `scripts/load_reference_metadata.py` | Loads Retrosheet bio/team/park metadata. | After `020`. |
| `scripts/load_auxiliary_retrosheet.py` | Loads broader Retrosheet auxiliary files. | After reference metadata. |
| `scripts/fetch_mlb_schedule.py` | Discovers active MLB games for live ingestion. | Live bridge work. |
| `scripts/download_mlb_bulk.py` | Canonical historical MLB bulk raw backfill into `raw_mlb.schedule_snapshots` and `raw_mlb.live_feed_snapshots`. | Historical MLB raw backfill . |
| `scripts/populate_bridge_tables.py` | Downloads Chadwick Register and populates player mappings and canonical team / park bridge mappings . ? ? ? ? ? ? ? ? ? ? ? ? … … … … … … … … … … … … … … … … … … … … … … … … … … … …  … … … … … … … … … … … … … …  … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … … …
| `scripts/ingest_all_mlb_data.py` |  ??  ?  …  



| File | Purpose | Use When |
|---|---|---|
| `scripts/warehouse.py` | Main CLI for dependency checks, Retrosheet fetch, Chadwick extract/load, and live feed fetch with raw snapshot provenance. | Ingestion and raw landing. |
| `scripts/rebuild_warehouse.sh` | Canonical full rebuild order. | Reproducibility. Update when adding required SQL. |
| `scripts/install_chadwick.sh` | Chadwick installation helper. | Environment setup. |
| `scripts/load_reference_metadata.py` | Loads Retrosheet bio/team/park metadata. | After `020`. |
| `scripts/load_auxiliary_retrosheet.py` | Loads broader Retrosheet auxiliary files. | After reference metadata. |
| `scripts/fetch_mlb_schedule.py` | Discovers active MLB games for live ingestion. | Live bridge work. |
| `scripts/download_mlb_bulk.py` | Canonical historical MLB bulk raw backfill into `raw_mlb.schedule_snapshots` and `raw_mlb.live_feed_snapshots` with request/status/error provenance. | Historical MLB raw backfill. |
| `scripts/populate_bridge_tables.py` | Downloads Chadwick Register and populates player mappings plus canonical team/park bridge mappings from the typed MLB reference views. | Live bridge setup and reconciliation refresh. |
| `scripts/ingest_live_games.py` | Orchestrates batch live game ingestion using environment-driven Postgres settings. | Live bridge work. |
| `scripts/transform_live_game.py` | Transforms stored MLB live snapshots into canonical `core.live_games` / `core.live_events` with upserts and raw JSON preservation. | Live bridge work. |
| `scripts/transform_live_comprehensive.py` | Enhanced transform creating Retrosheet-compatible `core.live_games` and `core.live_events` with extended field coverage. | Live bridge work, detailed Retrosheet alignment. |
| `scripts/mlb_pbp_collector.py` | Collects MLB play-by-play data via MLB-StatsAPI and pybaseball Statcast, outputs CSV with pitch metrics. | Historical MLB PBP CSV generation. |
| `scripts/ingest_mlb_pbp.py` | Ingests MLB PBP CSV files into `core.mlb_pbp` table. | CSV to database loader for MLB PBP. |
| `scripts/load_statcast.py` | Loads free Statcast CSV data into `raw_mlb.statcast` and updates bridge tables. | Supplemental pitch‑level data ingestion. |
| `scripts/load_baseballdata.py` | Loads Baseball‑Data.com play‑by‑play CSV into `raw_external.baseball_data_com` and creates placeholder player bridge entries. | Supplemental historical PBP ingestion. |

| File | Purpose | Use When |
|---|---|---|
| `scripts/warehouse.py` | Main CLI for dependency checks, Retrosheet fetch, Chadwick extract/load, and live feed fetch with raw snapshot provenance. | Ingestion and raw landing. |
| `scripts/rebuild_warehouse.sh` | Canonical full rebuild order. | Reproducibility. Update when adding required SQL. |
| `scripts/load_reference_metadata.py` | Loads Retrosheet bio/team/park metadata. | After `020`. |
| `scripts/load_auxiliary_retrosheet.py` | Loads broader Retrosheet auxiliary files. | After reference metadata. |
| `scripts/fetch_mlb_schedule.py` | Discovers active MLB games for live ingestion. | Live bridge work. |
| `scripts/download_mlb_bulk.py` | Canonical historical MLB bulk raw backfill into `raw_mlb.schedule_snapshots` and `raw_mlb.live_feed_snapshots` with request/status/error provenance. | Historical MLB raw backfill. |
| `scripts/fetch_mlb_reference_data.py` | Canonical MLB reference endpoint fetcher for teams, rosters, people, venues, and standings into `raw_mlb.reference_snapshots`. | MLB source coverage, raw reference backfill. |
| `scripts/raw_mlb_backfill_status.py` | Canonical status report for raw MLB backfill progress across schedules, live feeds, reference endpoints, and transformed live rows. | Backfill monitoring, runbook support. |
| `scripts/populate_bridge_tables.py` | Downloads Chadwick Register and populates player mappings plus canonical team/park bridge mappings from the typed MLB reference views. Tolerates current bridge-schema variations in the active database. | Live bridge setup and reconciliation refresh. |
| `scripts/ingest_live_games.py` | Orchestrates batch live game ingestion using environment-driven Postgres settings. | Live bridge work. |
| `scripts/transform_live_game.py` | Transforms stored MLB live snapshots into canonical `core.live_games` / `core.live_events` with upserts and raw JSON preservation. | Live bridge work. |
| `scripts/transform_live_comprehensive.py` | Enhanced transform creating Retrosheet-compatible `core.live_games` and `core.live_events` with extended field coverage. | Live bridge work, detailed Retrosheet alignment. |
| `scripts/mlb_pbp_collector.py` | Collects MLB play-by-play data via MLB-StatsAPI and pybaseball Statcast, outputs CSV with pitch metrics. | Historical MLB PBP CSV generation. |
| `scripts/ingest_mlb_pbp.py` | Ingests MLB PBP CSV files into `core.mlb_pbp` table. | CSV to database loader for MLB PBP. |
| `scripts/replay_live_bridge_backfill.py` | Replays stored latest-successful MLB raw snapshots through `scripts/transform_live_game.py`, optionally targeting only rows that still carry `MLB###` fallback ids. | Controlled live bridge refresh after mapping or transform fixes. |
| `scripts/backup_sql_files.sh` | Copies all `.sql` files from the `sql/` directory into a timestamped backup folder for Git versioning. | Backup of schema definitions.
 | `scripts/backup_procedures.sh` | Backs up all database objects (functions, procedures, views, materialized views) to a timestamped SQL dump. | Database maintenance, disaster recovery. |

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
| `scripts/check_model_status.py` | Checks model registry and predictions table status. | Model monitoring. |
| `scripts/generate_historical_pa_predictions.py` | Generates historical PA outcome predictions in bulk and stores in predictions.pa_predictions. | Batch historical prediction generation. |
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
| `scripts/test_inference_performance.py` | Inference benchmark tests. | Performance validation. |
| `scripts/test_baseball_analytics.py` | Data/schema/model smoke test suite candidate. | CI candidate. |
| `scripts/benchmark_queries.py` | SQL/query benchmark runner. | Warehouse performance. |
| `scripts/benchmark_report.py` | Benchmark reporting helper. | Query-performance reports. |
| `scripts/performance_test.py` | Performance experiment script. | Verify syntax/status before relying on it. |
| `scripts/simple_perf_test.py` | Simple performance demonstration. | Local investigation. |

## Archived Prototype Scripts

| File | Purpose | Archival Reason |
|---|---|---|
| `scripts/archive/simulate_half_inning.py` | Monte Carlo half-inning simulator candidate. | Unvalidated baseball state transitions; frozen per AGENTS.md until validated and integrated into canonical layers. |
| `scripts/archive/fast_prediction_service.py` | Model caching and batch prediction service candidate. | Predates canonical live prediction logging infrastructure; must integrate with `predictions.live_pa_predictions` before reactivation. |
| `retrosheet/event.py` | Legacy event parsing module. | Not imported anywhere in codebase; predates canonical Retrosheet/Chadwick-based ingestion pipeline; deleted 2026-04-17. |

## Archived SQL Files

| File | Purpose | Archival Reason |
|---|---|---|
| `sql/archive/121_inference_functions_legacy.sql` | Legacy inference functions with placeholder mock data. | Placeholder SQL functions predating canonical Python prediction path; archived 2026-04-17. |
| `sql/archive/092_live_odds_views.sql` | Legacy live odds/market-adjacent views. | Predates canonical market integration schema; archived 2026-04-17. |

| File | Purpose | Archival Reason |
|---|---|---|
| `sql/archive/092_live_odds_views.sql` | Materialized views for hit and strikeout odds derived from features.play_snapshot. | Prototype odds views; must be validated against canonical market comparison architecture before reactivation. |
| `sql/archive/121_inference_functions_legacy.sql` | Placeholder inference functions for fast batch predictions and simulation state management. | Returns mock data instead of real predictions; must integrate with canonical Python prediction serving path before reactivation. |

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
