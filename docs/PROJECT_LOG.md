# Project Log

## 2026-04-10 (Temporal Policy Training Controls)

### Built

- Extended `scripts/train_pa_outcome_distribution.py` with direct temporal-policy controls:
  - `--recent-window`
  - `--season-half-life`
  - `--exclude-2020`
  - `--downweight-2020`
- Added reusable era columns to `features.plate_appearance_outcome_examples`:
  - `season_era`
  - `rules_context_era`
- Included the era columns in the multiclass trainer feature set.
- Registered temporal-policy metadata in both `feature_spec` and `metrics` for `models.model_registry`.
- Updated user-facing docs and procedures to show temporal-policy training commands.

### Validation

- `python3 -m py_compile scripts/train_pa_outcome_distribution.py` passed.
- Rebuilt `sql/076_plate_appearance_outcome_model.sql` and `sql/077_pitch_sequence_model.sql` serially after adding era columns to the PA outcome layer.
- Test training run completed successfully:
  - `python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.01 --train-through 2022 --recent-window 7 --season-half-life 5 --downweight-2020 0.5 --no-activate`
- Registered model version `20260410T211408Z` stores:
  - `recent_window = 7`
  - `season_half_life = 5.0`
  - `downweight_2020 = 0.5`
- `features.plate_appearance_outcome_examples` now exposes `season_era` and `rules_context_era`.
- Validation metrics from that smoke test:
  - `hist_gradient_boosting_multiclass`: log loss `1.8108`, top-3 accuracy `0.7133`, accuracy `0.3768`, validation rows `5,448`
  - `multinomial_logistic_regression`: log loss `2.1386`, top-3 accuracy `0.4855`, accuracy `0.2676`, validation rows `5,448`

### Next

1. Add era-feature columns to the PA training views.
2. Run a formal temporal sweep across recent windows and half-lives.
3. Compare policies on `2023-2025` log loss, Brier score, calibration, and subgroup drift.

## 2026-04-10 (Temporal Model Selection)

### Built

- Added `docs/TEMPORAL_MODEL_SELECTION.md` to define how the project should handle non-stationarity across seasons.
- Documented a formal training-policy recommendation:
  - primary production-style policy: exponential recency weighting
  - benchmark policy: fixed recent windows
  - structural-feature policy: explicit era indicators for known regime changes
- Added exact warehouse support for the policy using `features.plate_appearance_outcome_examples`.

### Validation

- Confirmed current multiclass PA layer spans `2000-2025` with `4,779,662` rows.
- Computed fixed-window sample sizes ending in `2025`:
  - 3 years: `559,688`
  - 5 years: `929,476`
  - 7 years: `1,189,370`
  - 10 years: `1,752,609`
  - 15 years: `2,688,466`
  - full span: `4,779,662`
- Confirmed clear season-environment shifts in the warehouse:
  - hit rate `0.2375` in `2000` versus `0.2191` in `2025`
  - home-run rate trough `0.0228` in `2014`
  - home-run rate peak `0.0363` in `2019`
  - shortened `2020` season remains structurally abnormal

### Decision

- Do not equally weight all seasons from `2000-2025` in the main PA outcome model.
- Use fixed windows only as benchmarks, not as the default production policy.
- Use `2023-2025` out-of-time validation to choose between:
  - fixed windows `W ∈ {3,5,7,10,15,all}`
  - exponential half-lives `h ∈ {3,5,7,10}`
- Add era indicators for:
  - `2000-2009`
  - `2010-2014`
  - `2015-2019`
  - `2020`
  - `2021-2022`
  - `2023+`

### Sources

- Concept-drift support:
  - Lu et al., *Learning under Concept Drift: A Review* (2020)
  - Zaidi et al., *On the Inter-relationships among Drift rate, Forgetting rate, Bias/variance profile and Error* (2018)
- Baseball regime-change support:
  - MLB foreign-substance enforcement guidance (2021)
  - MLB 2023 rule-change announcement (2022)

## 2026-04-10 (Pitch Sequence Normalization)

### Built

- Added `sql/077_pitch_sequence_model.sql` as the first formal pitch-sequence normalization layer.
- Created `features.pitch_sequence_symbol_reference` with official Retrosheet pitch-sequence symbols and coarse semantics.
- Created `features.pitch_sequence_examples` with one row per `pitch_seq_tx` symbol, anchored to `features.plate_appearance_outcome_examples`.
- Added `features.pitch_sequence_validation_summary` for coverage and parsing sanity checks.
- Updated the canonical rebuild order in `scripts/rebuild_warehouse.sh`.
- Updated `README.md` and `docs/agents/PROCEDURES.md` to make the new layer reproducible and discoverable.

### Modeling Decisions

- This layer intentionally stops at normalized sequence symbols and coarse symbol groups.
- It does not yet claim to reconstruct every intermediate count transition. That should come after validation against official Retrosheet semantics and the current warehouse state.
- The purpose of this step is to avoid inventing a parallel pitch parser later and to give same-PA temporal feature work a canonical source.

### Validation

- Successfully applied `sql/077_pitch_sequence_model.sql` to the local `retrosheet` database.
- `features.pitch_sequence_examples`: 20,121,849 sequence-symbol rows across 4,779,662 plate appearances.
- Unknown-symbol rows: 0.
- Top symbol groups:
  - `ball`: 6,592,285
  - `in_play`: 3,394,108
  - `foul`: 3,122,551
  - `called_strike`: 3,089,666
  - `swinging_strike`: 1,763,610
  - `marker`: 1,213,190
- Confirmed `pitch_seq_tx` coverage for loaded modern seasons remains complete in `features.plate_appearance_outcome_examples`:
  - 2025: 186,640 / 186,640
  - 2024: 185,783 / 185,783
  - 2023: 187,265 / 187,265
  - 2022: 185,121 / 185,121
- Sampled live warehouse values show the expected Retrosheet symbol mix, including examples such as `BCBBCB`, `CCBX`, `SFBX`, `..CFFBS`, and `CBSBBFX`.

### Next

1. Apply `sql/077_pitch_sequence_model.sql` and validate symbol counts plus unknown-symbol frequency.
2. Add inferred within-PA temporal state columns only after the symbol layer is verified.
3. Build same-PA temporal features on top of `features.pitch_sequence_examples`.

## 2026-04-10 (Research Methodology And Feature Audit)

### Built

- Added `docs/RESEARCH_METHODOLOGY.md` as the formal CRISP-DM methods document for the project.
- Defined the project in research-program terms rather than only implementation terms:
  - business objective and decision problem
  - canonical data layers and source-system separation
  - mathematical state representation for plate appearances
  - multiclass PA outcome notation and objective functions
  - derived baseball probability functionals
  - run expectancy and win-probability notation
  - time-aware evaluation, calibration, and deployment rules
- Added `docs/FEATURE_AUDIT.md` to classify fields and features into:
  - understood and already used
  - understood but not yet fully operationalized
  - preserved raw but not yet reliable enough for direct modeling

### Methodological Decisions

- The warehouse should be treated as a reproducible research system following CRISP-DM:
  - Business Understanding
  - Data Understanding
  - Data Preparation
  - Modeling
  - Evaluation
  - Deployment
- The first coherent direct probabilistic target remains the multiclass plate-appearance outcome distribution.
- Historical/live source merging should continue to happen only after source-preserved raw landing and canonical normalization.
- Hyperparameter search is not the current bottleneck. Expected return is still higher from feature work and calibration work.

### Validation

- Confirmed that the formal methodology is consistent with the current implemented stack:
  - historical path: `raw_retrosheet -> core -> features`
  - live path: `raw_mlb -> bridge -> core.live_* -> analysis`
  - multiclass target: `predictions.prediction_targets.target_id = 'pa_outcome_distribution'`
- Confirmed modern-season `pitch_seq_tx` coverage remains effectively complete in the current warehouse and is therefore viable for the next feature-engineering phase.

### Next

1. Normalize `pitch_seq_tx` into one pitch per row.
2. Add same-game temporal features for PA models.
3. Build live feature parity for `pa_outcome_distribution`.
4. Add calibration and backtest diagnostics for multiclass PA outcomes.
5. Expand hyperparameter search only after the feature/calibration layer is stronger.

## 2026-04-10 (Live Data Integration)

### Built

- **MLB Live Data Ingestion Pipeline**: Complete end-to-end system for ingesting real-time MLB game data alongside historical Retrosheet data
- **Database Objects**:
  - `analysis.combined_games` - Union view of historical + live games
  - `analysis.combined_events` - Union view of historical + live events
  - `analysis.combined_plate_appearances` - Materialized view combining PA data
  - `analysis.get_data_source_stats()` - Function for data source statistics
  - `analysis.get_recent_games()` - Function for recent games across sources
  - `analysis.refresh_combined_data()` - Function to refresh materialized views
- **Scripts**:
  - `scripts/fetch_mlb_schedule.py` - Discovers active MLB games
  - `scripts/populate_bridge_tables.py` - Downloads Chadwick Register for ID mapping
  - `scripts/ingest_live_games.py` - Orchestrates batch live data ingestion
  - `scripts/transform_live_game.py` - Transforms MLB API to core schema (enhanced with ID mapping)
- **Bridge Tables**: Populated `bridge.player_xref` with 127,341 MLB ↔ Retrosheet ID mappings
- **Architecture**: Maintained clean separation between `core.*` (historical) and `core.live_*` (live) data
- **Documentation**: Created comprehensive architecture diagrams and procedure documentation

### Validation Counts

- **Bridge Table Population**: 127,341 player ID mappings loaded
- **Live Game Ingestion**: Successfully ingested 1 MLB game with 79 events
- **Combined Data**: 62,599 total games, 4,933,766 total events across historical + live sources
- **Data Sources**: Historical (62,598 games), Live (1 game), Combined analysis views working

### Architecture Decisions

- **Separation Maintained**: Historical Retrosheet data in `core.games/events`, live MLB data in `core.live_games/events`
- **ID Mapping**: Live data uses Retrosheet IDs via bridge tables, falls back to MLB prefixed IDs when mapping unavailable
- **Analysis Layer**: New `analysis` schema provides unified querying without mixing storage
- **No Table Renames**: Existing architecture already supported clean separation

## 2026-04-10 (Original)

### Built

- Created a reproducible PostgreSQL-first Retrosheet warehouse project.
- Installed/validated Chadwick CLI usage through project scripts.
- Loaded Retrosheet/Chadwick seasons 2000-2025 into `raw_retrosheet`.
- Created source-preserved Chadwick tables:
  - `raw_retrosheet.chadwick_events`
  - `raw_retrosheet.chadwick_games`
  - `raw_retrosheet.chadwick_daily`
  - `raw_retrosheet.chadwick_substitutions`
  - `raw_retrosheet.chadwick_comments`
- Created typed `core` tables:
  - `core.teams`
  - `core.parks`
  - `core.players`
  - `core.games`
  - `core.events`
- Created model-ready feature seed:
  - `features.game_outcome_examples`
- Created modeling, prediction, market, and chat metadata schemas/tables.
- Seeded initial reusable prediction targets.
- Added first ML training script for game-home-win models.
- Added OpenRouter, Groq, and Codex/OpenAI-compatible provider configuration scaffolding.

### Validation

- `raw_retrosheet.chadwick_events`: 4,933,687 rows, 62,598 games.
- `raw_retrosheet.chadwick_games`: 62,598 rows, 62,598 games.
- `core.games`: 62,598 rows, 62,598 games.
- `core.events`: 4,933,687 rows, 62,598 games.
- `features.game_outcome_examples`: 4,779,034 rows, 62,589 games.
- `core.events` has validated primary key, check constraints, and foreign keys.

### Next

- Add market intelligence and prediction-market comparison.
- Add GitHub issues for roadmap tracking.

### Added Later

- Created `core.plate_appearances`.
- Created `features.plate_appearance_examples`.
- Added plate-appearance prediction targets for all outcomes: hit, walk, strikeout, home run, reach-base, extra-base-hit.
- Extended training script to support plate appearance model training.
- Trained all plate appearance prediction models (5% sample, train through 2022):
  - **Walk**: Best ROC AUC 0.959, accuracy 0.936 (most predictable outcome)
  - **Strikeout**: Best ROC AUC 0.841, accuracy 0.779 (highly predictable)
  - **Reach Base**: Best ROC AUC 0.680, accuracy 0.721 (moderately predictable)
  - **Home Run**: Best ROC AUC 0.659, accuracy 0.969 (good accuracy, needs discrimination improvement)
  - **Extra-base Hit**: Best ROC AUC 0.642, accuracy 0.923 (good accuracy, moderate discrimination)
  - **Hit**: Best ROC AUC 0.636, accuracy 0.783 (needs most improvement)
- All models trained with both logistic regression and histogram gradient boosting algorithms.
- Gradient boosting models consistently outperform logistic regression across all targets.
- Model improvement opportunities identified for hit, extra-base hit, and home run predictions.
- Created `scripts/predict_plate_appearance.py` for model inference and real-time predictions.
- Created `scripts/analyze_pa_models.py` for comprehensive model evaluation and comparison.
- Created `scripts/simulate_half_inning.py` for Monte Carlo simulation of half-inning outcomes using trained plate appearance models.
- Implemented comprehensive inference performance optimizations:
  - `inference.plate_appearance_features`: Materialized view with pre-joined enriched features (4.8M rows)
  - `inference.get_plate_appearance_features()`: Fast PostgreSQL function for feature computation
  - `inference.simulation_states`: Table for maintaining simulation state in database
  - Optimized indexes on game state lookups for sub-10ms query performance
- Created `scripts/fast_prediction_service.py`: High-performance service with model caching and batch predictions
- Created `scripts/test_inference_performance.py`: Performance benchmarking tools
- Validated plate appearance coverage:
  - `core.plate_appearances`: 4,779,662 rows, 62,598 games.
  - `features.plate_appearance_examples`: 4,779,662 rows, 62,598 games.
  - `features.half_inning_examples`: 1,118,579 rows, 62,598 games.
  - `inference.plate_appearance_features`: 4,779,662 rows with pre-computed enriched features.
- Loaded Retrosheet reference metadata:
  - `raw_retrosheet.biofile`: 26,961 rows.
  - `raw_retrosheet.teams_reference`: 292 rows.
  - `raw_retrosheet.ballparks_reference`: 656 rows.
- Backfilled core metadata:
  - `core.players`: 7,165 players, 7,165 populated bats values, 7,164 populated throws values.
  - `features.plate_appearance_examples`: 4,779,662 rows with populated batter handedness and pitcher handedness.
- Retrained all active plate-appearance models after handedness enrichment (5% sample, train through 2022):
  - **Walk**: Best ROC AUC 0.959, log loss 0.121.
  - **Strikeout**: Best ROC AUC 0.840, log loss 0.353.
  - **Reach Base**: Best ROC AUC 0.678, log loss 0.565.
  - **Home Run**: Best ROC AUC 0.657, log loss 0.133.
  - **Extra-base Hit**: Best ROC AUC 0.643, log loss 0.262.
  - **Hit**: Best ROC AUC 0.637, log loss 0.501.
- Added broader Retrosheet auxiliary metadata ingestion with `scripts/load_auxiliary_retrosheet.py` and `sql/040_auxiliary_retrosheet.sql`.
- Loaded source-preserved auxiliary tables:
  - `raw_retrosheet.biofile_legacy`: 26,961 rows.
  - `raw_retrosheet.coaches`: 12,501 rows.
  - `raw_retrosheet.ejections`: 19,730 rows.
  - `raw_retrosheet.relatives`: 1,320 rows.
  - `raw_retrosheet.season_rosters`: 138,020 rows.
  - `raw_retrosheet.season_teams`: 3,986 rows.
  - `raw_retrosheet.season_schedules`: 233,953 rows.
  - `raw_retrosheet.season_umpires`: 9,700 rows.
  - `raw_retrosheet.special_gamelog_lines`: 1,973 rows.
- Added normalized auxiliary views:
  - `core.roster_entries`: 138,020 rows.
  - `core.allstar_roster_entries`: 6,528 rows.
  - `core.allstar_games`: 25 rows.
  - `core.scheduled_games`, `core.umpires`, `core.coach_assignments`, `core.ejections`, and `core.player_relatives`.
- Expanded `core.players` from Retrosheet roster metadata to 24,588 players with 24,070 first names, 21,511 batting-hand values, and 22,145 throwing-hand values.
- Added first indexed feature marts with `sql/050_feature_marts.sql`:
  - `features.batter_prior_season_pa_summary`: 23,534 rows.
  - `features.pitcher_prior_season_pa_summary`: 18,574 rows.
  - `features.team_prior_season_summary`: 830 rows.
  - `features.pa_context_prior_season_rates`: 612,126 rows.
  - `features.half_inning_outcome_summary`: 1,118,579 rows.
- Kept prior-season marts keyed by `feature_season = season + 1` so model training can join historical performance without same-season leakage.
- Added enriched model training support in `scripts/train_models.py` and active-model promotion in `scripts/promote_best_models.py`.
- Updated plate-appearance inference to load the enriched feature shape from Postgres before scoring.
- Trained and activated enriched 5% sample models. Active validation ROC AUC:
  - `game_home_win`: 0.850 gradient boosting, 0.843 logistic regression.
  - `pa_batter_walk`: 0.961 logistic regression, 0.960 gradient boosting.
  - `pa_batter_strikeout`: 0.854 gradient boosting, 0.851 logistic regression.
  - `pa_batter_reach_base`: 0.683 gradient boosting, 0.676 logistic regression.
  - `pa_batter_home_run`: 0.683 logistic regression, 0.675 gradient boosting.
  - `pa_batter_extra_base_hit`: 0.646 gradient boosting, 0.639 logistic regression.
  - `pa_batter_hit`: 0.643 gradient boosting, 0.634 logistic regression.
- Verified enriched plate-appearance inference on `ANA202506060` plate appearance `30`.
- Noted future feature work: add coarser context-rate fallbacks because exact inning/base/count/hand context joins can be sparse.
- Added canonical rebuild script `scripts/rebuild_warehouse.sh` so contributors can recreate the warehouse in order without Git LFS or checked-in model binaries.
- Added advanced feature marts with `sql/060_advanced_feature_marts.sql`:
  - `features.pa_context_coarse_prior_season_rates`: 3,744 rows.
  - `features.batter_career_prior_pa_summary`: 81,018 rows.
  - `features.pitcher_career_prior_pa_summary`: 56,553 rows.
  - `features.batter_pitcher_prior_matchup_summary`: 1,155,128 rows.
  - `features.park_prior_season_run_environment`: 818 rows.
  - `features.team_rolling_30_game_summary`: 125,196 rows.
- Added advanced example views for plate-appearance and game-win training.
- Added `scripts/sweep_hyperparameters.py` for reproducible model grid searches. A smoke sweep for `pa_batter_hit` with `--feature-set advanced --sample-rate 0.005 --max-candidates 3` completed and registered candidates.
- Added temporal and production marts with `sql/070_temporal_and_production_marts.sql`:
  - `features.team_game_context`: 125,196 rows.
  - `features.player_production_season`: 23,534 rows.
  - `features.pitcher_production_season`: 18,574 rows.
  - `features.game_outcome_temporal_examples`: 186,562 rows for 2025.
  - `features.plate_appearance_temporal_examples`: 186,640 rows for 2025.
- Spot-checked 2025 player production leaders, pitcher production leaders, and team rest/doubleheader counts.
- Implemented complete AI Baseball Analytics Chatbot:
  - `scripts/baseball_chatbot.py`: Core LLM integration with tool calling and conversation memory
  - `scripts/llm_client.py`: Abstraction layer for OpenAI, local LLMs, and mock clients
  - `scripts/tool_registry.py`: Tool discovery, validation, and execution registry
  - Support for 5 major tools: plate appearance prediction, half-inning simulation, live odds, player analysis, database queries
  - End-to-end natural language processing with real ML model integration
  - Successfully demonstrated tool calling, prediction execution, and response synthesis
  - Cross-validation infrastructure with `scripts/cross_validate_models.py` and `scripts/auto_promote_models.py`
- Added inference performance optimizations:
  - `inference.plate_appearance_features`: Pre-computed feature views (4.8M rows)
  - `inference.get_plate_appearance_features()`: Fast PostgreSQL feature computation
  - `scripts/fast_prediction_service.py`: In-memory model caching and batch predictions
  - Sub-10ms prediction latency improvements
- Added comprehensive testing framework:
  - `scripts/test_baseball_analytics.py`: Schema and data integrity validation
  - `scripts/benchmark_queries.py`: Query performance benchmarking
  - `scripts/simple_perf_test.py`: Performance demonstration tools
- Built the first Next.js web command center in `baseball-chatbot-ui/`:
  - Chat Analyst view with rule-based warehouse/tool routing.
  - Sim Lab view backed by `features.half_inning_outcome_summary`.
  - Models & Backtests view backed by `models.model_registry`, sweep metadata, and production marts.
  - Workbench view with allow-listed local workflow commands rather than arbitrary shell execution.
  - Spreadsheet-style result tables with CSV export.
- Added web API routes:
  - `/api/status`
  - `/api/analytics`
  - `/api/backtests`
  - `/api/chat`
  - `/api/simulate`
  - `/api/terminal`
  - `/api/predict`
  - `/api/live-odds`
- Validated the web command center:
  - `npm run build` completed successfully in `baseball-chatbot-ui/`.
  - `/api/status` returned warehouse/model summary JSON.
  - `/api/analytics` returned active model metrics and 2025 production leaders.
  - `/api/chat` returned active model data for "show active models".
  - `/api/simulate` for 2025 top-first left-handed-only historical states returned 10,538 half-innings, 0.499 expected runs, 28.1% run probability, and 8.1% probability that all left-handed batters in the inning got a hit.
- Added interface persistence with `sql/075_interface_workflows.sql`:
  - `predictions.simulation_runs` records Sim Lab filters, summaries, run distributions, and sample sizes.
  - `predictions.recent_simulation_runs` provides a dashboard-friendly read view.
  - `chat.query_logs` now records tools used and result row counts from web chat requests.
- Reviewed `docs/ab_outcome.md` against the current warehouse and added `docs/AT_BAT_OUTCOME_MODEL_REVIEW.md`.
- Added `sql/076_plate_appearance_outcome_model.sql` with `features.plate_appearance_outcome_examples`, validation summary, and the `pa_outcome_distribution` prediction target for future multiclass PA modeling.

### Next
- Add market intelligence and prediction-market comparison.
- Add GitHub issues for roadmap tracking.
- Added `docs/agents/` as the durable project map for AI agents and humans:
  - `PROJECT_OBJECTIVES.md` defines prediction-engine objectives and modeling goals.
  - `FILE_INVENTORY.md` maps docs, SQL, scripts, feature marts, interface routes, and generated artifacts to their purposes.
  - `PROCEDURES.md` documents canonical warehouse, modeling, simulation, live bridge, interface, and issue workflows.
  - `MODELING_WORKFLOWS.md` inventories targets/models and defines evaluation, leakage, and promotion rules.

## 2026-04-10

### At-Bat Outcome Modeling

- Added GitHub execution issues for the PA outcome and MLB live bridge roadmap:
  - #24 advanced PA outcome distribution training/evaluation.
  - #25 PA outcome distribution prediction API and derived aggregate outputs.
  - #26 pitch-sequence normalization for later next-pitch modeling.
  - #27 raw MLB Stats API schedule/live snapshot logging.
  - #28 MLB-to-Retrosheet ID bridge reconciliation.
  - #29 MLB live feed to canonical live PA/event transforms.
  - #30 live PA feature parity for model inference.
  - #31 live PA outcome scoring and prediction logging.
- Made `sql/076_plate_appearance_outcome_model.sql` rerunnable by dropping `features.plate_appearance_outcome_validation_summary` before rebuilding `features.plate_appearance_outcome_examples`.
- Rebuilt `features.plate_appearance_outcome_examples` successfully:
  - 4,779,662 plate-appearance examples.
  - 62,598 games.
  - 17 raw outcome classes.
  - Pitch-sequence coverage: 1.0000.
  - Batted-ball coverage: 0.7055.
- Trained inactive 5% advanced-feature `pa_outcome_distribution` candidates with:
  - `python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.05 --train-through 2022 --no-activate`
  - Training rows: 211,593.
  - Validation rows: 28,132.
  - Trained classes: 16. `interference` was excluded by the current `--min-class-rows 100` threshold in this sample.
- Candidate metrics:
  - `hist_gradient_boosting_multiclass` version `20260410T172129Z`: validation log loss 1.7720, top-3 accuracy 0.7248, accuracy 0.3854, macro F1 0.1756, weighted F1 0.2858, multiclass Brier score 0.7585.
  - `multinomial_logistic_regression` version `20260410T172129Z`: validation log loss 2.2205, top-3 accuracy 0.4404, accuracy 0.2675, macro F1 0.1453, weighted F1 0.1951, multiclass Brier score 0.8577.
- Decision: do not promote yet. The gradient boosting candidate is materially stronger than logistic and should be the next benchmark, but it still needs calibration, subgroup diagnostics, and either rare-class policy or a larger sample/full run before production-like use.
- Added `scripts/predict_pa_outcome_distribution.py` for reusable multiclass PA scoring from registered model artifacts.
- Extended `/api/predict` so callers can request `target_id: "pa_outcome_distribution"` and receive class probabilities plus derived aggregates.
- Validated historical scoring on `ANA202506060` plate appearance `30` using model version `20260410T172129Z`; probabilities summed to 0.9999999999999999 and returned actual outcome `walk`.
- Ran `npm run build` in `baseball-chatbot-ui/`; the Next.js production build completed successfully.

### Live MLB Pipeline Repair

- Reviewed the live pipeline against the warehouse design goal: keep source-preserved MLB payloads in `raw_mlb`, keep ID reconciliation in `bridge`, upsert canonical live state into `core.live_*`, and use `analysis.*` views/materialized views as the combined analysis layer.
- Extended `sql/090_mlb_live_data.sql` with additive provenance columns for future MLB fetches:
  - `request_params`
  - `http_status`
  - `error_text`
  - `payload_checksum`
  - `game_date`
  - `season`
- Extended `sql/110_live_core_tables.sql` with additive live-state/provenance columns and compatibility indexes so existing warehouses can be upgraded in place:
  - `core.live_games`: `raw_payload`, `created_at`, `updated_at`, `mlb_game_pk`, `snapshot_id`, `snapshot_fetched_at`, `status_code`, `detailed_state`, `venue_name`
  - `core.live_events`: `raw_play`, `created_at`, `updated_at`, `mlb_game_pk`, `snapshot_id`, `plate_appearance_index`, `mlb_event_type`, `event_type_description`, `trajectory`, `home_score_after`, `away_score_after`
- Reworked `scripts/transform_live_game.py` to:
  - read the latest stored snapshot with provenance
  - tolerate the current legacy `bridge.player_xref` column names in the active database
  - preserve `raw_payload` and `raw_play`
  - extract batter/pitcher handedness from `matchup.batSide` and `matchup.pitchHand`
  - map event codes from structured MLB `eventType`/trajectory instead of free-text only
  - upsert `core.live_games` and `core.live_events` instead of replacing whole tables
  - clean up stale legacy live rows for the same game when a canonical bridged game id is available
- Updated `scripts/warehouse.py fetch-live-game` so new raw MLB snapshots store request params, HTTP status, checksum, game date, and season.
- Updated `scripts/ingest_live_games.py` to use environment-driven Postgres settings and a correct recency filter expression.
- Updated `scripts/populate_bridge_tables.py` to tolerate both the canonical bridge schema in SQL and the currently active legacy bridge schema in the database.
- Validation:
  - Fetched fresh snapshots for MLB game `823884`; newest raw rows now include `http_status = 200`, `game_date = 2026-04-09`, `season = 2026`, checksum, and request params.
  - Re-transformed stored snapshot `823884` successfully into canonical game `MLB146202604090` with 79 live events.
  - `core.live_games` for `823884` now shows `is_complete = true`, `status_code = 'F'`, `detailed_state = 'Final'`, and preserved `raw_payload`.
  - All 79 live events for `823884` now preserve `raw_play`.
  - All 79 live events for `823884` now have known batter/pitcher handedness instead of `U`.
  - `analysis.combined_games` now reports 1 live game row and `analysis.combined_events` 79 live event rows for the repaired sample after refresh/cleanup.
  - Refreshed `analysis.combined_plate_appearances`; it now reports 79 live rows.
- Decision: the warehouse design is still correct. Raw MLB should stay separate in `raw_mlb`, and the historical/live merge should happen in `analysis` views/materialized views and later feature-parity views, not by collapsing the raw layers together.
- Documentation sync:
  - Updated `AGENTS.md`, `README.md`, `docs/agents/README.md`, `docs/agents/FILE_INVENTORY.md`, `docs/agents/PROCEDURES.md`, and `docs/LIVE_DATA_ARCHITECTURE.md` so the written live-ingestion procedure now matches the repaired source-preserved/raw-separate design and the canonical upsert-based transform path.

### Feature Audit

- Reviewed the current field reference set:
  - `docs/retrosheet_key.md`
  - `docs/ab_outcome.md`
  - `docs/AT_BAT_OUTCOME_MODEL_REVIEW.md`
  - `docs/CORE_SCHEMA.md`
  - `config/chadwick_event_columns.txt`
- Added `docs/FEATURE_AUDIT.md` to classify current data/feature status into:
  - fields we understand and actively use
  - fields we understand but have not fully operationalized
  - fields preserved raw but not yet reliable enough for modeling
- Decision: feature generation is not “done.” Current historical PA/game models are good enough for baseline modeling and moderate tuning, but the highest-return work before deeper hyperparameter sweeps is still:
  - pitch-level normalization from `pitch_seq_tx`
  - same-game temporal PA features
  - live feature parity for `pa_outcome_distribution`
  - better contact/batted-ball derived features
  - explicit rare-class policy for multiclass outcome modeling
