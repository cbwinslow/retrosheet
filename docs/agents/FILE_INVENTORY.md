# File Inventory

This inventory tells agents what each important file does and which workflows own it. Files may appear in multiple sections when they serve multiple goals.

## Top-Level Docs

| File | Purpose | Owners / Workflows |
|---|---|---|
| `AGENTS.md` | Main operating guide and routing map. Keep short; link to this folder for detail. | All agents |
| `README.md` | User-facing setup, rebuild, modeling, interface, and attribution instructions. | Reproducibility, onboarding |
| `docs/PROJECT_LOG.md` | Running build log with validation counts, model results, and major decisions. | All significant changes |
| `docs/WAREHOUSE_PLAN.md` | Warehouse normalization plan. | Warehouse |
| `docs/CORE_SCHEMA.md` | Typed core schema details. | Warehouse, data-quality |
| `docs/PREDICTION_ENGINE_PLAN.md` | High-level prediction architecture. | Modeling, agents, live, markets |
| `docs/LIVE_DATA_ARCHITECTURE.md` | Complete live data ingestion architecture and procedures. | Live bridge, analysis |
| `docs/RESEARCH_METHODOLOGY.md` | Formal CRISP-DM methodology, notation, objective functions, and modeling assumptions. | Research framing, modeling, evaluation |
| `docs/TEMPORAL_MODEL_SELECTION.md` | Temporal weighting, era segmentation, window-size math, and recency-policy selection for non-stationary baseball data. | Modeling, evaluation, concept-drift handling |
| `docs/FEATURE_AUDIT.md` | Field/feature status audit: what is understood, what is operationalized, and what should be built before deeper tuning. | Modeling, feature engineering |
| `docs/AT_BAT_OUTCOME_MODEL_REVIEW.md` | Maps the at-bat outcome spec to actual warehouse assets and next steps. | Multiclass PA modeling |
| `docs/ab_outcome.md` | User-provided spec for at-bat/pitch outcome modeling. Treat as requirements guidance, not direct implementation. | Multiclass PA and pitch-model roadmap |
| `docs/retrosheet_key.md` | Retrosheet documentation index and external reference map. | Retrosheet parsing/reference |
| `CHATBOT_INTERFACE_DESIGN.md` | Current/future web command-center design notes. | Interface, agents |

## Configuration

| File | Purpose | Notes |
|---|---|---|
| `config/chadwick_event_columns.txt` | Chadwick event-column reference used to avoid hand-invented mappings. | Check before changing raw event parsing. |
| `config/ai_providers.example.json` | Example provider configuration for OpenRouter, Groq, and Codex/OpenAI-compatible inference. | Never commit real keys. |
| `.env.example` | Safe local environment variable template. | Keep secrets out of git. |

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

## Live And Inference SQL

These files may be present as active development work. Treat them as live-bridge/inference candidates unless committed and documented in the rebuild path.

| File | Purpose | Status Guidance |
|---|---|---|
| `sql/080_half_inning_examples.sql` | Half-inning training examples beyond summary distribution. | Scenario modeling; verify before relying on it. |
| `sql/090_mlb_live_data.sql` | Raw MLB live snapshot tables with source-preserved payloads and fetch provenance. | Live bridge. |
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
| `scripts/populate_bridge_tables.py` | Downloads Chadwick Register and populates ID mapping tables. Tolerates current bridge-schema variations in the active database. | Live bridge setup. |
| `scripts/ingest_live_games.py` | Orchestrates batch live game ingestion using environment-driven Postgres settings. | Live bridge work. |
| `scripts/transform_live_game.py` | Transforms stored MLB live snapshots into canonical `core.live_games` / `core.live_events` with upserts and raw JSON preservation. | Live bridge work. |

## Modeling Scripts

| File | Purpose | Targets / Outputs |
|---|---|---|
| `scripts/train_models.py` | General binary model trainer for game, PA, and some half-inning targets. | `game_home_win`, `pa_batter_*`, `half_inning_*`; writes `data/models/`, registers `models.model_registry`. |
| `scripts/train_pa_outcome_distribution.py` | Dedicated multiclass PA outcome distribution trainer. | `pa_outcome_distribution`; writes `data/models/`, registers `models.model_registry`. |
| `scripts/predict_pa_outcome_distribution.py` | Scores a historical PA with the registered multiclass outcome model and returns class + derived probabilities. | Historical multiclass inference path. |
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
