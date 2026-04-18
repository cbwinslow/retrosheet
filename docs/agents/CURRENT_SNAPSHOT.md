# Current Snapshot

This file is the shortest durable handoff for another agent. Read this first when resuming work after context loss.

Last updated: `2026-04-18`

## Current Objective

The project is currently focused on the historical plate-appearance probability engine first, with live MLB bridge work staged behind it.

Priority order:

1. historical PA outcome model quality
2. calibration and reliability
3. live feature parity and live scoring
4. simulation and market-comparison layers

## Canonical Architecture

Use these layers and do not invent parallel ones:

- `raw_retrosheet`: source-preserved Chadwick/Retrosheet outputs
- `raw_mlb`: source-preserved MLB schedules, live feeds, and reference snapshots
- `bridge`: MLB ↔ Retrosheet identifiers
- `core`: typed baseball entities and canonical facts
- `features`: model-ready examples and marts
- `models`: model registry and metadata
- `predictions`: stored outputs, reports, backtests
- `analysis`: historical + live combined read layer

Do not treat `mlb_features`, `mlb_models`, `mlb_enhanced`, or EdgeForge prototype schemas as canonical.

## Prediction Serving Status

**Default Calibration:** All PA outcome predictions now default to calibrated output (apply_calibration=True).
- Historical scorer: `scripts/predict_pa_outcome_distribution.py`
- Live scorer: `scripts/predict_live_pa_outcome_distribution.py`
- API route: `baseball-chatbot-ui/app/api/predict/route.ts`

**Override:** Pass `apply_calibration=false` to request raw probabilities.

**API Contract:** TypeScript types defined in `baseball-chatbot-ui/lib/types/predict.ts` with stable error contracts.

## Current Data State

Historical warehouse:

- `features.plate_appearance_outcome_examples`: `4,779,662` rows across `2000-2025`
- grouped layer exists in `features.plate_appearance_outcome_grouped_examples`
- pitch-sequence normalization exists in `sql/077_pitch_sequence_model.sql`

MLB raw coverage:

- `raw_mlb.schedule_snapshots`: `9,286`
- `raw_mlb.live_feed_snapshots`: `72,199`
- successful `raw_mlb.live_feed_snapshots`: `72,184`
- `raw_mlb.reference_snapshots`: `2,405`

MLB transformed coverage:

- `core.live_games`: `67,913`
- `core.live_events`: `5,172,275`

Residual MLB exceptions:

- `243297`
- `243298`
- `243313`
- `243314`
- `308207`
- `764834`
- `764836`

These are upstream MLB API `HTTP 500` exhibition-game holes, not local pipeline bugs.

## Current Best Historical PA Model

Target:

- `pa_outcome_distribution`
- grouped taxonomy
- advanced feature set

Current best base model:

- model family: `hist_gradient_boosting_multiclass`
- feature set: `advanced_count`
- policy: full-history training through `2022`, no temporal decay
- validation: `2023-2025`

Current best uncalibrated validation metrics:

- log loss: `1.5089213670264499`
- multiclass Brier score: `0.7145995102201933`
- accuracy: `0.41305275131522823`
- top-3 accuracy: `0.8202402957486137`

Why this policy won:

- shorter windows were worse
- tested half-life decay policies were also slightly worse
- the best competing policies were:
  - `half_life = 10`
  - `15-year window`
  - `half_life = 7`

## Calibration Status

The first serious calibration and subgroup pass is done.

Main findings on validation `2023-2025`:

- strongest class-level defect: `strikeout` overconfidence
- strongest subgroup defect: two-strike count overconfidence

Examples:

- `strikeout` ECE: `0.0152`
- confidence gaps:
  - `0-2`: `0.0351`
  - `1-2`: `0.0341`
  - `2-2`: `0.0386`

Held-out post-hoc isotonic calibration result:

- fit calibration on `2023-2024`
- evaluate on held-out `2025`

Held-out `2025` improvement:

- log loss: `1.5078` -> `1.5047`
- multiclass Brier score: `0.7138` -> `0.7125`
- `strikeout` ECE: `0.0179` -> `0.0036`

Reusable calibration artifact status:

- `sql/081_probability_calibration_artifacts.sql` is applied
- first registered calibration artifact:
  - `20260412T045759Z_isotonic_artifact`
  - `artifact_uri = data/models/calibration/pa_outcome_distribution/20260412T045759Z_isotonic_artifact.joblib`
- calibrated scoring is now available through:
  - `scripts/predict_pa_outcome_distribution.py --apply-calibration`
  - the Next.js `/api/predict` route with `apply_calibration`

Interpretation:

- the model is a valid research baseline
- calibration should be a first-class layer
- the model is still not promoted as a production-style probability engine

## Current Script Inventory For PA Modeling

Use these scripts instead of creating ad hoc ones:

- `scripts/train_pa_outcome_distribution.py`
- `scripts/sweep_pa_outcome_temporal.py`
- `scripts/analyze_pa_outcome_calibration.py`
- `scripts/calibrate_pa_outcome_model.py`
- `scripts/persist_pa_outcome_reports.py`
- `scripts/register_pa_outcome_calibration.py`
- `scripts/predict_pa_outcome_distribution.py`

Experimental but not yet optimized:

- `scripts/bootstrap_pa_outcome_evaluation.py`

## Bootstrap Status

The bootstrap evaluation workflow is now working in a practical form.

Current design:

- season-stratified bootstrap
- cluster resampling by whole game
- validation-time metric uncertainty estimation
- per-game cached sufficient statistics to keep replicate costs low

Current 50-replicate result for the winning grouped advanced HGB model:

- log loss mean: `1.5127`
- log loss 5th-95th percentile: `1.5108` to `1.5155`
- multiclass Brier mean: `0.7148`
- Brier 5th-95th percentile: `0.7138` to `0.7156`
- accuracy mean: `0.4138`
- accuracy 5th-95th percentile: `0.4125` to `0.4151`

Interpretation:

- the current historical baseline is reasonably stable under season-stratified game-cluster resampling
- bootstrap uncertainty is now available as an evaluation layer
- durable report storage now exists in:
  - `predictions.calibration_reports`
  - `predictions.bootstrap_reports`
  - via `scripts/persist_pa_outcome_reports.py`

## Live MLB Work Status

Live/raw ingestion is complete enough to model against, and the bridge layer has partially caught up.

Done:

- raw MLB backfill complete for practical purposes
- canonical live raw tables exist
- live transform path preserves provenance and upserts correctly
- `scripts/populate_bridge_tables.py` now populates:
  - `bridge.player_xref`
  - `bridge.team_xref`
  - `bridge.park_xref`
- active bridge counts now include:
  - `bridge.team_xref`: `30` mapped MLB team ids
  - `bridge.park_xref`: `45` mapped MLB venue ids
- `sql/122_live_pa_feature_parity.sql` now joins park priors and team rolling-form marts for bridged rows
- `scripts/replay_live_bridge_backfill.py` now exists for controlled replay of stored latest-successful MLB snapshots through the repaired bridge-aware transform path

Validated spot-check:

- `python3 scripts/transform_live_game.py --game-pk 599374`
- canonical row lands as:
  - `game_id = WAS201910260`
  - `home_team_id = WAS`
  - `away_team_id = HOU`
  - `park_id = WAS11`
- live parity row for that game now includes:
  - `park_prior_total_runs_per_game = 9.585`
  - `batting_team_rolling_30_win_rate = 0.6667`
  - `fielding_team_rolling_30_win_rate = 0.7333`

Still not done:

- robust `game_xref` reconciliation
- season-aware team bridge semantics for historical franchise moves
- broad replay of pre-repair `core.live_*` rows through the repaired bridge
- durable live prediction logging

Important limitation:

- `bridge.team_xref` is still seasonless, so franchise-move cases are resolved to one current/canonical Retrosheet id for live scoring:
  - `WSH/MON -> WAS`
  - `MIA/FLA -> MIA`
  - `ATH/OAK -> OAK`
- park reconciliation is still intentionally regular-season-oriented; spring-training/non-regular-season venues may still remain as `MLB###` fallback park ids after replay
- This is acceptable for current live scoring, but not a complete historical MLB-team replay design.

## Model Registry Status

114 models registered in `models.model_registry`:
- Active models: 2 (both half-inning models)
  - `half_inning_any_run` (logistic_regression)
  - `half_inning_lhb_any_hit` (logistic_regression)
- Active PA model: 1 (hist_gradient_boosting_multiclass, model_id 101)
- Inactive models: 111 (other PA outcome distribution models)
- Best PA model: `hist_gradient_boosting_multiclass` (model_id 101)
  - Train accuracy: 44.3%, log_loss: 1.39
  - Validation accuracy: 41.3%, log_loss: 1.51
  - Top-3 accuracy: 84.1% (train), 82.0% (validation)
  - Trained on 2000-2022 data (211K training rows)
- Predictions table `predictions.pa_predictions` exists (created 2026-04-18)
- No predictions generated yet

## Recent Bug Fixes (2026-04-18)

- Fixed data quality validation script (column_name undefined error)
- Fixed baseball state engine bugs (dataclass mutable default, double transition, sacrifice fly, out transition)
- All unit tests now passing

## Recent Infrastructure Work (2026-04-18)

- Created `predictions.pa_predictions` table for historical PA predictions
- Activated best PA model (model_id 101) for PA outcome distribution
- Created `scripts/generate_historical_pa_predictions.py` for bulk prediction generation
- Resolved PostgreSQL MCP server conflicts using multi-database approach

## MCP Server Status

- PostgreSQL MCP servers resolved using `multi-postgres-mcp-server` approach
- Single `postgres` server supports multiple databases (epstein, letta, retrosheet, cbw_rag)
- Full read-write access to all databases through MCP server
- Docker compose approach no longer needed

## Best Move Right Now

Do this next:

1. Generate historical predictions using `scripts/generate_historical_pa_predictions.py`
2. Set up live prediction pipeline for real-time scoring
3. Backtest and evaluate model performance on historical predictions
4. Implement calibration if needed

Do not do this yet:

- GPU migration
- new model-family churn
- EdgeForge prototype integration
- broad interface expansion before probability/reporting layers settle

## Compute Notes

Current main environment:

- Dell R720 server

Available but not integrated into the canonical workflow:

- server GPUs: `K40`, `K80`
- separate Windows machine with `RTX 3060`

Current canonical modeling path is CPU-first and reproducible. GPU work is optional and should remain an additive alternate training path when introduced.

## GitHub Issues To Read First

Resume from these issues before starting new work:

- `#10` Improve model quality with richer features, calibration, and backtesting
- `#24` Train and evaluate full advanced PA outcome distribution model
- `#27` Log MLB Stats API schedule and live feed snapshots with provenance
- `#28` Build MLB-to-Retrosheet bridge reconciliation for games, teams, players, and parks
- `#30` Create live PA outcome feature parity view for model inference
- `#31` Add live PA outcome scoring workflow and prediction logging
- `#22` Add pipeline runbook and warehouse health panel

## Recent Work Completed (2026-04-17)

### Phase 4.2: Baseball State Transition Engine
- Created `retrosheet/simulation/baseball_state.py` with state machine for base occupancy, outs, scoring
- Created comprehensive unit tests in `retrosheet/simulation/test_baseball_state.py`
- Created reproducibility tests in `retrosheet/simulation/test_reproducibility.py`
- Documented state machine rules in `docs/MLB_SIMULATION.md`

### Phase 6: Market Comparison Layer (Design)
- Archived `sql/092_live_odds_views.sql` to `sql/archive/`
- Archived `sql/121_inference_functions.sql` to `sql/archive/`
- Created `sql/125_market_snapshot_tables.sql` for market data schema
- Created `sql/126_model_edge_comparison.sql` for edge analysis views
- Created `docs/MARKET_INTEGRATION.md` documenting market integration architecture

### Phase 7: Refactor and Consolidate
- Created `retrosheet/prediction/__init__.py` shared module for common prediction logic
- Refactored `scripts/predict_pa_outcome_distribution.py` to use shared module
- Refactored `scripts/predict_live_pa_outcome_distribution.py` to use shared module
- Deleted unused `retrosheet/event.py` (legacy event parser)
- Created `docs/FEATURE_STORE_ARCHITECTURE.md` for feature store design

### Phase 8: Quality and Monitoring (Design)
- Created `docs/RELIABILITY_DASHBOARD.md` for dashboard design
- Created `scripts/validate_data_quality.py` for data quality validation
- Created `docs/DATA_QUALITY_SLAs.md` for data quality SLAs
- Created `docs/PERFORMANCE_OPTIMIZATION.md` for performance optimization strategies

### Phase 9.1: Update Documentation
- Updated `docs/agents/CURRENT_SNAPSHOT.md` with recent work
- Created `docs/CONTRIBUTOR_ONBOARDING.md` for contributor onboarding guide

### Phase 9.2: Training and Onboarding
- Created `docs/TRAINING_WAREHOUSE_REBUILD.md` for warehouse rebuild training
- Created `docs/TRAINING_MODEL_TRAINING.md` for model training training
- Created `docs/TRAINING_PREDICTION_SERVING.md` for prediction serving training
- Created `docs/TROUBLESHOOTING.md` for troubleshooting procedures
- Created `docs/FAQ.md` for frequently asked questions

### Phase 10: Testing and Validation
- Created unit tests in `retrosheet/prediction/test_pa_service.py` for PA prediction service
- Created unit tests in `retrosheet/prediction/test_calibration.py` for calibration logic
- Created unit tests in `retrosheet/prediction/test_feature_engineering.py` for feature engineering
- Created unit tests in `retrosheet/prediction/test_data_transformation.py` for data transformation
- Created integration tests in `scripts/test_integration_prediction.py` for prediction serving
- Created validation tests in `scripts/test_validation_model_predictions.py` for model predictions
- Created validation tests in `scripts/test_validation_simulation.py` for simulation outputs
- Created `docs/VALIDATION_REPORT_TEMPLATES.md` for validation report templates

### Phase 11: Deployment and Operations (Design)
- Created `docs/PRODUCTION_REQUIREMENTS.md` for production environment requirements
- Created `docs/OPERATIONS_RUNBOOKS.md` for operations runbooks
- Created `docs/CICD_PIPELINE.md` for CI/CD pipeline design
- Created `docs/SCALING_PREPARATION.md` for scaling strategies

### Archive and Documentation
- Archived legacy SQL files to `sql/archive/`
- Deleted unused `retrosheet/event.py`
- Updated `docs/agents/FILE_INVENTORY.md` with 28 new files
