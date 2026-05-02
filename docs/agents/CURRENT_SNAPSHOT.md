# Current Snapshot

This file is the shortest durable handoff for another agent. Read this first when resuming work after context loss.

**Last updated:** `2026-05-02`  
**CRISP-DM Phase:** 3 → 4 Transition (Data Preparation → Modeling)  
**Current Focus:** Infrastructure & Tooling (Training Pipeline, NL Router, Query Monitoring)

## Current Objective

**PRIMARY:** Build pitch-level prediction models using the newly completed flexible feature mart schema.  
**SECONDARY:** Continue historical plate-appearance probability engine improvements.

The project has transitioned from PA-level to pitch-level modeling with a complete schema supporting 4 model families: Two-Tier XGBoost, LSTM Sequential, Multi-Task Network, and Swing Probability.

**Key Achievements:**
- **May 2, 2026:** Query Progress Monitoring system with FastAPI endpoints (`baseball monitor queries/server`)
- **May 2, 2026:** Training Pipeline Framework with experiment tracking (`baseball train run/list/compare`)
- **May 1, 2026:** Natural Language Query Router (`baseball chatbot route`)
- **May 1, 2026:** Market Comparison & Edge Detection (`baseball bet edges`)
- **April 24, 2026:** Flexible Feature Mart Schema (#79) with 7 tables, 118 Statcast fields

**Priority Order:**

1. First batch of pitch-level models (#133) - swing, contact, type
2. Model serving layer (#134) - load from registry
3. Content Monetisation Studio (#137) - automated content generation
4. Historical PA outcome model quality & calibration
5. Live feature parity and real-time scoring

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

## Current Data State

### Pitch-Level Data (NEW - April 24, 2026)

**Feature Mart Schema (`features_pitch` schema):**

| Table | Rows | Status | Description |
|-------|------|--------|-------------|
| `features_pitch.locations` | 7,661,992 | ✅ Populated | Full Statcast data 2015-2025 (118 fields) |
| `features_pitch.base_features` | TBD | ⏳ Ready to populate | Mirrors locations with versioning |
| `features_pitch.feature_registry` | 37 | ✅ Populated | Metadata catalog for feature selection |
| `features_pitch.engineered_features` | TBD | ⏳ Schema ready | Derived metrics + model targets |
| `features_pitch.sequential_features` | TBD | ⏳ Schema ready | LSTM/GRU sequence windows |
| `features_pitch.player_context` | TBD | ⏳ Schema ready | Rolling player statistics |
| `features_pitch.model_training_set` | TBD | ⏳ Schema ready | Versioned training data |
| `features_pitch.pitch_sequences` | TBD | ⏳ Schema ready | PA-level pitch aggregations |

**Data Quality:**
- 98.2% completeness on Statcast data
- Quality flags implemented (normal, outlier, passed_ball, wild_pitch)
- PostGIS geometry enabled for spatial queries
- All 118 Statcast fields preserved (release_speed, spin_rate, plate_x, plate_z, etc.)

### Historical warehouse:

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

## Best Move Right Now

**PRIORITY 1: Pitch-Level Model Pipeline (Epic #78)**

The flexible feature mart schema is complete. Now execute the modeling phase:

### Immediate Actions (This Week)

1. **Populate base_features** from `features_pitch.locations`
   - Migrate 7.66M pitches (2015-2025)
   - Preserve all 118 Statcast fields
   - Verify row counts match exactly

2. **Build engineered_features** table
   - Create `outcome_tier1`: {Ball, Strike, Ball-in-Play}
   - Create `outcome_tier2`: {Single, Double, Triple, HR, Out, Walk, K}
   - Add derived physics features (break magnitude, approach angle)
   - Add score differential and leverage index

3. **Train Tier-1 XGBoost baseline**
   - Target: >80% coarse outcome accuracy
   - Validate against SMU benchmark (58%)
   - Document log loss, Brier score, calibration error

### Secondary Priority (Next 2 Weeks)

4. **Implement remaining pitch-level models**
   - LSTM Sequential (Epic #78, Sub-Issue #81)
   - Multi-Task Network (Epic #78, Sub-Issue #82)
   - Swing Probability (Epic #78, Sub-Issue #83)

5. **Build player context features**
   - 30-day rolling averages for all pitchers
   - Batter zone discipline profiles
   - Pitcher arsenal composition (% FB, BB, OS)

### Key Documentation

**Pitch-Level Research:**
- [docs/research_paper.md](docs/research_paper.md) — Mathematical formulations, loss functions, evaluation metrics
- [docs/STATCAST_MODELS_RESEARCH_REPORT.md](docs/STATCAST_MODELS_RESEARCH_REPORT.md) — SMU, CMU, Penn State research alignment
- [docs/PITCH_FEATURE_MART_SCHEMA.md](docs/PITCH_FEATURE_MART_SCHEMA.md) — Schema documentation

**SQL Schema:**
- `sql/features/003_pitch_flexible_mart.sql` — 7 table definitions
- `sql/features/001_pitch_data_quality.sql` — Quality flags and views

**Legacy PA Model (still valid, lower priority):**
- HGB + advanced_count (log loss 1.5089)
- Calibration artifact registered
- Available via existing scripts

### Do Not Do Yet

- GPU migration (stay CPU-first for reproducibility)
- PA-level Markov chain (deprioritized behind pitch-level)
- EdgeForge prototype integration
- Live prediction triggers (wait for models)
- broad interface expansion before probability/reporting layers settle

## Compute Notes

Current main environment:

- Dell R720 server

Available but not integrated into the canonical workflow:

- server GPUs: `K40`, `K80`
- separate Windows machine with `RTX 3060`

Current canonical modeling path is CPU-first and reproducible. GPU work is optional and should remain an additive alternate training path when introduced.

## GitHub Issues To Read First

### Pitch-Level Model Pipeline (NEW - Active)

Resume from Epic #78 and sub-issues:

- `#78` **Epic:** Pitch-Level Model Pipeline — Master tracking issue
- `#79` **Sub-Issue:** Flexible Feature Mart Schema — ✅ **COMPLETE**
- `#80` **Sub-Issue:** Two-Tier XGBoost Implementation — ⏳ Ready to start
- `#81` **Sub-Issue:** LSTM Sequential Model — ⏳ Schema ready
- `#82` **Sub-Issue:** Multi-Task Network — ⏳ Schema ready
- `#83` **Sub-Issue:** Swing Probability Model — ⏳ Schema ready

### Legacy PA Model Issues (Active but lower priority)

- `#10` Improve model quality with richer features, calibration, and backtesting
- `#24` Train and evaluate full advanced PA outcome distribution model
- `#27` Log MLB Stats API schedule and live feed snapshots with provenance
- `#28` Build MLB-to-Retrosheet bridge reconciliation for games, teams, players, and parks
- `#30` Create live PA outcome feature parity view for model inference
- `#31` Add live PA outcome scoring workflow and prediction logging
- `#22` Add pipeline runbook and warehouse health panel
