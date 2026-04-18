# Procedures

These are the canonical workflows. Use them before creating new ad hoc scripts.

## Canonical Data Path Enforcement

**Non-negotiable data flow rules:**

### Historical Training Path (Only)
```
raw_retrosheet → core → features → models → predictions
```

- All historical Retrosheet/Chadwick data MUST flow through this path
- Do NOT create alternative historical data pipelines
- Do NOT mix raw_retrosheet data directly into features or models
- Use `scripts/rebuild_warehouse.sh` as the only canonical historical rebuild mechanism

### Live Inference Path (Only)
```
raw_mlb → bridge → core.live_* → features.live_* → predictions
```

- All live MLB data MUST flow through this path
- Do NOT score raw MLB JSON directly in production paths
- Do NOT merge raw MLB rows into historical raw layers
- Historical/live combination belongs in `analysis.*` views only
- Use `scripts/fetch_mlb_schedule.py` and `scripts/ingest_live_games.py` for live ingestion

### Prototype Schema Freeze

The following schemas/directories are EXPERIMENTAL until explicitly merged into canonical layers:
- `EdgeForge` files
- `mlb_features` files  
- `mlb_models` files
- `mlb_enhanced` files

**Rule:** Do NOT use these in production workflows. They remain experimental until:
1. Merged into canonical warehouse layers (raw_retrosheet, raw_mlb, bridge, core, features, models, predictions)
2. Documented in `docs/agents/FILE_INVENTORY.md`
3. Added to canonical rebuild procedures in `scripts/rebuild_warehouse.sh`

### Violation Detection

Before creating new SQL, scripts, models, routes, or docs:
1. Check `docs/agents/FILE_INVENTORY.md` - does an existing workflow already own this job?
2. Check this PROCEDURES.md - is there a canonical procedure for this?
3. If creating new schema/table - does it fit into canonical layers above?
4. If creating new data pipeline - does it follow the canonical path enforcement rules?

If you cannot answer YES to all checks, either:
- Use the existing canonical workflow, OR
- Document the gap and get approval before creating a new path

## Resume After Context Loss

Purpose: recover the current project state quickly before adding new code or changing direction.

Read in this order:

1. `docs/agents/CURRENT_SNAPSHOT.md`
2. `docs/PROJECT_LOG.md`
3. `docs/agents/MODELING_WORKFLOWS.md`
4. the relevant GitHub issues listed in `docs/agents/CURRENT_SNAPSHOT.md`

Rule:

- update `docs/agents/CURRENT_SNAPSHOT.md` whenever the current best model, main blocker, live-data status, or recommended next move changes materially

## Full Warehouse Rebuild

Purpose: recreate the historical warehouse and feature layers from source data.

Command:

```bash
YEARS=2000-2025 PGDATABASE=retrosheet scripts/rebuild_warehouse.sh
```

Expected order:

1. Check Chadwick dependencies.
2. Fetch Retrosheet archives.
3. Initialize schemas.
4. Extract Chadwick outputs with headers.
5. Load raw Chadwick tables.
6. Build `core.games` and `core.events`.
7. Build `core.plate_appearances`.
8. Load reference metadata.
9. Load auxiliary metadata.
10. Build typed MLB reference views.
11. Build feature marts.
12. Build interface persistence.
13. Build multiclass PA outcome examples.
14. Build pitch-sequence normalization examples.
15. Build grouped PA outcome examples.
16. Build probability evaluation report tables.
17. Build count-state PA feature marts.

When adding a required SQL migration, add it to `scripts/rebuild_warehouse.sh` and document it in `README.md`.

## Prediction Serving

### Default Calibration

**Rule:** All PA outcome predictions default to calibrated output.

- Historical scorer (`scripts/predict_pa_outcome_distribution.py`): `apply_calibration=True` by default
- Live scorer (`scripts/predict_live_pa_outcome_distribution.py`): `apply_calibration=True` by default
- API route (`baseball-chatbot-ui/app/api/predict/route.ts`): `DEFAULT_APPLY_CALIBRATION = true`

**Override:** Pass `apply_calibration=false` to request raw (uncalibrated) model probabilities.

**Rationale:** Calibration improves probability reliability for decision-making and market comparison. Raw probabilities remain available for debugging and model evaluation.

## Live Data Ingestion

Purpose: ingest real-time MLB game data alongside historical Retrosheet data.

### One-Time Setup (Bridge Tables)

Command:

```bash
python3 scripts/populate_bridge_tables.py
```

Expected order:

1. Download Chadwick Bureau Register CSV files.
2. Parse player register rows.
3. Populate `bridge.player_xref` with MLB ↔ Retrosheet player ID mappings.
4. Populate `bridge.team_xref` with current/canonical MLB franchise mappings from `core.mlb_api_teams`.
5. Populate `bridge.park_xref` with MLB venue-id mappings covering the observed `2000-2025` MLB venue surface.

Limitation:

- `bridge.team_xref` is currently seasonless.
- Franchise-move cases are therefore mapped to a current/canonical Retrosheet id for live scoring rather than a season-specific historical id.
- Do not treat that as a complete replay-grade historical MLB team bridge until a season-aware bridge design exists.

### Ongoing Live Data Ingestion

Command:

```bash
python3 scripts/fetch_mlb_schedule.py --yesterday
python3 scripts/ingest_live_games.py --schedule
```

Expected order:

1. Query MLB Stats API for recent game schedules.
2. Identify active/completed games for ingestion.
3. For each game:
   - Fetch live game feed JSON from MLB API.
   - Store source-preserved JSON plus request/status/checksum provenance in `raw_mlb.live_feed_snapshots`.
   - Transform the latest stored snapshot to canonical live schema using bridge table lookups.
   - Upsert into `core.live_games` and `core.live_events`.
4. Refresh `analysis.combined_plate_appearances` when live rows change and downstream combined PA analysis depends on current live state.

Important operational note:

- rows transformed before the April 2026 team/park bridge repair may still carry `MLB###` fallback ids in `core.live_*`
- the repaired bridge only applies automatically to newly transformed or replayed snapshots
- if park priors or team rolling features are unexpectedly null for older live rows, replay those stored snapshots through `scripts/transform_live_game.py`

Controlled replay command:

```bash
python3 scripts/replay_live_bridge_backfill.py --season-from 2019 --season-to 2019 --limit 50
```

Replay guidance:

1. Start with a bounded season slice and a small `--limit`.
2. Prefer regular-season slices first; spring-training and other non-regular-season venues may still remain as `MLB###` park fallbacks.
3. Validate a sample of replayed `core.live_games` rows and the matching `features.live_plate_appearance_advanced_count_examples` priors before scaling up.

### Analysis with Combined Data

Use `analysis.*` views for unified queries across historical and live data:

```sql
-- Check data source statistics
SELECT * FROM analysis.get_data_source_stats();

-- Query combined games
SELECT * FROM analysis.combined_games
WHERE game_date >= CURRENT_DATE - INTERVAL '7 days';

-- Query combined events
SELECT ce.*
FROM analysis.combined_events ce
JOIN analysis.combined_games cg USING (game_id)
WHERE ce.source_type = 'mlb_live';
```

## Data Quality Validation

Purpose: validate warehouse data quality against defined SLAs.

Command:

```bash
python3 scripts/validate_data_quality.py
```

Optional output:

```bash
python3 scripts/validate_data_quality.py --output validation_report.json
```

Expected checks:

1. Schema validation: verify all expected tables and columns exist
2. Null rate monitoring: check null rates against SLAs (5% for non-critical, 0% for critical)
3. Value range validation: verify values are within expected ranges
4. Referential integrity: check for orphan records in foreign key relationships
5. Temporal consistency: verify dates align with seasons

When to run:

- After warehouse rebuild
- After data ingestion
- Before model training
- Regularly in production (daily/weekly)

If checks fail:

1. Review failed checks in output
2. Investigate root cause
3. Fix data or schema issues
4. Re-run validation
5. Document findings in `docs/PROJECT_LOG.md`

## Testing Workflows

### Unit Tests

Purpose: validate individual functions and modules.

Command:

```bash
# PA prediction service tests
pytest retrosheet/prediction/test_pa_service.py -v

# Calibration tests
pytest retrosheet/prediction/test_calibration.py -v

# Feature engineering tests
pytest retrosheet/prediction/test_feature_engineering.py -v

# Data transformation tests
pytest retrosheet/prediction/test_data_transformation.py -v

# Baseball state transition tests
pytest retrosheet/simulation/test_baseball_state.py -v

# Reproducibility tests
pytest retrosheet/simulation/test_reproducibility.py -v
```

When to run:

- Before committing code changes
- In CI/CD pipeline on pull requests
- After refactoring code

### Integration Tests

Purpose: validate end-to-end workflows with warehouse data.

Command:

```bash
# Prediction serving integration tests
pytest scripts/test_integration_prediction.py -v
```

When to run:

- After code changes that affect data flow
- Before deploying to production
- In CI/CD pipeline on main branch

### Validation Tests

Purpose: validate model predictions and simulation outputs against historical data.

Command:

```bash
# Model prediction validation tests
pytest scripts/test_validation_model_predictions.py -v

# Simulation validation tests
pytest scripts/test_validation_simulation.py -v
```

When to run:

- After model training
- After calibration
- Before model promotion
- Regularly in production to detect drift

## Model Calibration

Purpose: improve probability reliability through post-hoc calibration.

Command:

```bash
python3 scripts/calibrate_pa_outcome_model.py \
    --model-id <MODEL_ID> \
    --calibration-years 2023-2024 \
    --validation-years 2025 \
    --calibration-type isotonic
```

Expected order:

1. Load registered model
2. Extract probabilities on calibration years
3. Fit isotonic regression calibrator
4. Apply calibration to validation years
5. Compare raw vs calibrated metrics
6. Save calibration artifact

When to run:

- After training a new model
- Before promoting to production
- When calibration quality degrades

Calibration types:

- `isotonic`: non-parametric isotonic regression (recommended)
- `sigmoid`: parametric sigmoid regression
- `beta`: beta calibration (for small datasets)

## Baseball Simulation

Purpose: simulate game state transitions for odds calculation and analysis.

State machine implementation:

- `retrosheet/simulation/baseball_state.py`: BaseballState class with state transition logic
- `apply_event()`: apply event type to state to get new state
- State includes: bases, outs, score, inning, batting order

Command for simulation:

```python
from retrosheet.simulation.baseball_state import BaseballState, apply_event

# Create initial state
state = BaseballState(
    bases=0,
    outs=0,
    home_score=0,
    away_score=0,
    inning=1,
    is_bottom_inning=False,
)

# Apply event
new_state = apply_event(state, event_type='single')
```

When to use:

- Monte Carlo simulation for game outcomes
- Odds calculation for betting markets
- What-if scenario analysis
- Validation of state transition logic

## Historical MLB Raw Backfill

Purpose: bulk backfill source-preserved historical MLB schedule and game-feed snapshots into `raw_mlb` without bypassing the raw provenance rules.

Command:

```bash
python3 scripts/download_mlb_bulk.py --start-season 2000 --end-season 2025 --mode schedules
python3 scripts/download_mlb_bulk.py --start-season 2000 --end-season 2025 --mode games --workers 4 --delay 1.0
```

Expected order:

1. Backfill `raw_mlb.schedule_snapshots` by date range.
2. Discover completed games from stored schedule payloads.
3. Backfill `raw_mlb.live_feed_snapshots` for those game PKs.
4. Preserve request parameters, HTTP status, response time, error text, and payload checksum in the raw layer.
5. Transform raw backfilled games only through documented follow-on canonical scripts; do not create a second historical MLB warehouse path.
6. Reruns are logically idempotent for successful resources:
   - schedule success rows are skipped once a successful row already exists for the date
   - game-feed success rows are skipped once a successful row already exists for the game

Use this workflow for historical MLB raw acquisition. Use `scripts/fetch_mlb_schedule.py` and `scripts/ingest_live_games.py` for ongoing near-live ingestion.

Status check:

```bash
python3 scripts/raw_mlb_backfill_status.py
```

## Historical MLB Data Transformation (Pitch-Level)

Purpose: Transform the 72,830+ stored live feed snapshots into pitch-level data that supplements Retrosheet events.

**Prerequisites**: 
- `raw_mlb.live_feed_snapshots` populated (via Historical MLB Raw Backfill)
- `bridge.*` tables populated (via Bridge Population above)

### Option A: Play-by-Play CSV Path (Current)

Command:

```bash
# Collect via pybaseball + MLB Stats API to CSV
python3 scripts/mlb_pbp_collector.py --season 2024 --output-csv data/mlb_pbp/mlb_pbp_2024.csv

# Ingest CSV to core.mlb_pbp
python3 scripts/ingest_mlb_pbp.py --csv data/mlb_pbp/mlb_pbp_2024.csv

# Or ingest entire directory
python3 scripts/ingest_mlb_pbp.py --dir data/mlb_pbp/
```

Expected order:

1. `mlb_pbp_collector.py` queries MLB Stats API play-by-play endpoint.
2. Merges with Statcast data via pybaseball for pitch metrics.
3. Outputs CSV with one row per plate appearance (pitch sequence as string).
4. `ingest_mlb_pbp.py` loads CSV into `core.mlb_pbp`.

Limitations:

- One row per PA, not per individual pitch.
- Pitch sequence stored as string (e.g., "CBSBFC"), not broken out.
- Pitch metrics only for last pitch of each PA.

Data destination: `core.mlb_pbp`

### Option B: Live Feed Snapshot Extraction (Future)

Purpose: Extract individual pitch rows from stored `raw_mlb.live_feed_snapshots`.

Status: **NOT YET IMPLEMENTED** - Requires new script `scripts/extract_pitches_from_snapshots.py`.

Proposed command:

```bash
python3 scripts/extract_pitches_from_snapshots.py --season-from 2000 --season-to 2025 --batch-size 100
```

Expected behavior:

1. Query `raw_mlb.live_feed_snapshots` for unextracted games.
2. Parse `liveData.plays.allPlays[].playEvents[]` JSON.
3. Filter events where `isPitch = true`.
4. Extract per-pitch fields: speed, spin, location, break, etc.
5. Insert into `mlb.pitches` with link to `mlb.play_events`.

Data destination: `mlb.pitches` (one row per pitch)

Advantages over Option A:

- True pitch-level granularity.
- All pitches have metrics, not just last pitch of PA.
- Uses already-downloaded snapshots (72,830 games).
- No additional API calls required.

### Linking to Retrosheet

After transformation, link MLB data to Retrosheet events via bridge tables:

```sql
-- Validate linking capability
SELECT 
    r.game_id,
    r.event_id,
    p.game_pk,
    p.pitch_number,
    p.pitch_type_code,
    p.release_speed
FROM core.events r
JOIN bridge.game_xref gx ON r.game_id = gx.retrosheet_game_id
JOIN mlb.pitches p ON gx.mlb_game_pk = p.game_pk
WHERE r.bat_id = p.batter_id
  AND r.pit_id = p.pitcher_id
  AND r.inning = p.inning;
```

See `docs/MLB_PBP_PIPELINE.md` for full pipeline documentation.

## MLB Reference Endpoint Backfill

Purpose: preserve the non-game MLB source families needed for roster, player, venue, and standings enrichment.

Command:

```bash
python3 scripts/fetch_mlb_reference_data.py --start-season 2000 --end-season 2025
```

Coverage:

- `teams`
- `rosters`
- `people`
- `venues`
- `standings`

Outputs:

- `raw_mlb.reference_snapshots`

Rules:

1. Keep responses source-preserved in `raw_mlb.reference_snapshots`.
2. Build typed `core` views from the latest successful snapshots with `sql/095_mlb_reference_views.sql`.
3. Treat the snapshots as raw source data; put typing and joins in `core`, not back into `raw_mlb`.
4. Use this workflow alongside `scripts/download_mlb_bulk.py` if the goal is broad MLB source preservation rather than only game feeds.
5. Reruns are logically idempotent for successful resources:
   - successful `teams`, `standings`, `rosters`, `people`, and `venues` snapshots are skipped once a successful row already exists for the same endpoint family/resource/season key

Status check:

```bash
python3 scripts/raw_mlb_backfill_status.py
```

Typed outputs:

- `core.mlb_api_teams`
- `core.mlb_api_team_rosters`
- `core.mlb_api_players`
- `core.mlb_api_venues`
- `core.mlb_api_standings`

## ESPN Data Ingestion

Purpose: ingest MLB data from ESPN API as an additional external data source.

### Setup

Command:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/220_espn_schema.sql
```

Expected order:

1. Create `raw_espn` schema
2. Create tables: `raw_espn.game_snapshots`, `raw_espn.schedule_snapshots`, `raw_espn.player_stats_snapshots`, `raw_espn.team_stats_snapshots`
3. Create indexes for common queries

### Ongoing ESPN Data Ingestion

Command:

```bash
# Fetch schedule for a specific date
python3 scripts/fetch_espn_mlb.py schedule --date 2024-04-15

# Fetch specific game data
python3 scripts/fetch_espn_mlb.py game --game-id 401434845
```

Expected order:

1. Query ESPN API for schedule or game data
2. Compute checksum for deduplication
3. Store source-preserved JSON with fetch provenance in `raw_espn.*_snapshots`
4. Preserve request parameters, HTTP status, response time, and checksum

Rules:

1. Keep responses source-preserved in `raw_espn`.
2. Use checksum-based deduplication to avoid duplicate fetches.
3. ESPN data is supplemental to Retrosheet and MLB Stats API data.
4. Future work: create bridge tables for ESPN IDs and transform to canonical shapes if needed.

Use this workflow for ESPN data acquisition. Transform and integration decisions should be documented in separate procedures once use cases are identified.

## Ingest Run Tracking

Purpose: track all data ingestion runs with script metadata, progress, and error tracking for reproducibility and debugging.

### Setup

Command:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/225_ingest_run_tracking.sql
```

Expected order:

1. Expand `raw_retrosheet.ingest_runs` table with script tracking columns
2. Create helper functions for run logging (start_ingest_run, update_ingest_run_progress, complete_ingest_run, fail_ingest_run)
3. Add triggers for auto-updating timestamps on bridge tables
4. Create monitoring views (recent_ingest_runs, ingest_run_stats_by_script)

### Script Integration Pattern

Ingestion scripts should follow this pattern:

```python
from scripts.fetch_espn_mlb import start_run, update_run_progress, complete_run, fail_run

# Start run logging
script_name = os.path.basename(__file__)
command_args = vars(args)
run_id = start_run("source_name", script_name, command_args)

try:
    # Fetch data
    update_run_progress(run_id, records_downloaded=1)
    
    # Store data
    if store_data(data):
        update_run_progress(run_id, records_ingested=1)
    else:
        update_run_progress(run_id, records_failed=1)
    
    # Complete run
    complete_run(run_id, {"command": args.command})
except Exception as e:
    fail_run(run_id, str(e), {"exception_type": type(e).__name__})
    sys.exit(1)
```

### Monitoring Queries

```sql
-- Recent runs
SELECT * FROM raw_retrosheet.recent_ingest_runs;

-- Stats by script
SELECT * FROM raw_retrosheet.ingest_run_stats_by_script;

-- Failed runs
SELECT * FROM raw_retrosheet.ingest_runs WHERE status = 'failed' ORDER BY started_at DESC;
```

### Design Decisions

- **Script storage in DB**: Not storing full script content in separate table (overkill). Git is canonical source.
- **Metadata only**: Track script_name, script_version (git commit), command_args - sufficient for reproducibility.
- **Progress tracking**: Update counters as data flows through download → ingest pipeline.
- **Error handling**: Always fail_run on exceptions with error message and exception type.

### Helper Functions

- `raw_retrosheet.start_ingest_run(source_name, script_name, git_commit, command_args)`: Start new run, returns run_id
- `raw_retrosheet.update_ingest_run_progress(run_id, records_downloaded, records_ingested, records_failed)`: Update counters
- `raw_retrosheet.complete_ingest_run(run_id, final_details)`: Mark as completed
- `raw_retrosheet.fail_ingest_run(run_id, error_message, error_details)`: Mark as failed

## Add A New Prediction Target

Purpose: add a precise target that can be trained, scored, logged, and explained.

Steps:

1. Define the target in words first.
2. Identify the label source in `core` or `features`.
3. Add or update a `features.*_examples` view/materialized view.
4. Insert a row into `predictions.prediction_targets`.
5. Add training support to the right trainer.
6. Add validation counts.
7. Add model registry output.
8. Update `docs/agents/MODELING_WORKFLOWS.md`.

Do not add ambiguous targets such as “left-handed batters get hits” without a settlement rule.

## Add A Feature Mart

Purpose: add reusable feature columns without leaking future information.

Rules:

- Keep raw source rows unchanged.
- Put reusable ML features under `features`.
- Prefer materialized views when joins are expensive and rows are stable.
- Add indexes for target/training joins.
- Name season-forward features as `feature_season = source_season + 1` when using prior-season summaries.
- For rolling features, use windows ending before the current event/game.
- Document leakage assumptions.

## Train Binary Game/PA Models

Use `scripts/train_models.py`.

Examples:

```bash
python3 scripts/train_models.py --target-id game_home_win --feature-set advanced --sample-rate 0.10 --train-through 2022
python3 scripts/train_models.py --target-id pa_batter_hit --feature-set advanced --sample-rate 0.05 --train-through 2022
```

Outputs:

- Serialized model under ignored `data/models/`.
- Registry row in `models.model_registry`.
- Metrics JSON in `models.model_registry.metrics`.

Promotion:

```bash
python3 scripts/promote_best_models.py --target-prefix 'pa_%' --min-validation-rows 10000
```

Do not hand-edit `models.model_registry.is_active`.

## Train Multiclass PA Outcome Distribution

Use `scripts/train_pa_outcome_distribution.py`.

Example:

```bash
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.05 --train-through 2022 --no-activate
```

Grouped baseline example:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/078_plate_appearance_outcome_grouped.sql
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --target-taxonomy grouped --sample-rate 0.05 --train-through 2022 --no-activate
```

Temporal-policy examples:

```bash
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.05 --train-through 2022 --recent-window 7 --no-activate
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.05 --train-through 2022 --season-half-life 5 --downweight-2020 0.5 --no-activate
```

Count-state-enhanced feature example:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/082_count_state_feature_marts.sql
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced_count --target-taxonomy grouped --sample-rate 0.05 --train-through 2022 --no-activate
```

## Persist PA Probability Evaluation Reports

Purpose: store calibration and bootstrap evidence as durable warehouse artifacts tied to a registered model version.

Setup:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/079_probability_evaluation_reports.sql
psql -h localhost -p 5432 -d retrosheet -f sql/081_probability_calibration_artifacts.sql
```

Command:

```bash
python3 scripts/persist_pa_outcome_reports.py --model-name hist_gradient_boosting_multiclass --model-version 20260411T230512Z
```

Expected order:

1. Look up the registered `pa_outcome_distribution` model in `models.model_registry`.
2. Run:
   - `scripts/analyze_pa_outcome_calibration.py`
   - `scripts/calibrate_pa_outcome_model.py`
   - `scripts/bootstrap_pa_outcome_evaluation.py`
3. Insert one `predictions.prediction_runs` row with `run_context = 'evaluation_report'`.
4. Persist:
   - raw validation calibration diagnostics in `predictions.calibration_reports`
   - held-out isotonic calibration comparison in `predictions.calibration_reports`
   - bootstrap summary metrics in `predictions.bootstrap_reports`

Use this workflow when a PA outcome benchmark becomes important enough to preserve as a durable warehouse record instead of transient JSON output.

## Register A Calibrated PA Scoring Artifact

Purpose: persist a reusable isotonic calibration artifact so the PA scorer and API can return calibrated probabilities instead of only raw model outputs.

Setup:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/081_probability_calibration_artifacts.sql
```

Command:

```bash
python3 scripts/register_pa_outcome_calibration.py --model-name hist_gradient_boosting_multiclass --model-version 20260411T230512Z
```

What it does:

1. Loads the registered `pa_outcome_distribution` model.
2. Fits one-vs-rest isotonic calibrators on the configured holdout calibration window.
3. Saves the calibration artifact under ignored `data/models/calibration/`.
4. Inserts:
   - one `predictions.prediction_runs` row with `run_context = 'calibration_artifact'`
   - one `predictions.calibration_reports` row with `artifact_uri`

Use the calibrated scorer:

```bash
python3 scripts/predict_pa_outcome_distribution.py --game-id ANA202506060 --plate-appearance-id 30 --model-version 20260411T230512Z --apply-calibration
python3 scripts/predict_pa_outcome_distribution.py --game-id ANA202506060 --plate-appearance-id 30 --model-version 20260411T230512Z --calibration-report-name 20260411T230512Z_isotonic_artifact
```

API consumers can pass the same controls through `/api/predict` for `target_id: "pa_outcome_distribution"`.

## Score A Stored Live PA

Purpose: score a stored MLB live plate appearance using the same historical `advanced_count` PA model contract.

Setup:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/122_live_pa_feature_parity.sql
```

Command:

```bash
python3 scripts/predict_live_pa_outcome_distribution.py --game-id MLB117201910300 --plate-appearance-id 79 --model-version 20260412T045759Z --apply-calibration
```

Current limitation:

- player, count-state, and coarse context priors are wired
- park prior and team rolling features remain nullable in the live view until team/park bridge reconciliation is completed

Temporal sweep example:

```bash
python3 scripts/sweep_pa_outcome_temporal.py --feature-set advanced --target-taxonomy grouped --sample-rate 0.05 --include-all-window --output-json data/reports/pa_grouped_temporal_sweep.json
```

Calibration and subgroup evaluation example:

```bash
python3 scripts/analyze_pa_outcome_calibration.py --model-name hist_gradient_boosting_multiclass --model-version 20260411T230512Z --output-json data/reports/pa_outcome_calibration_20260411T230512Z.json
```

Held-out post-hoc calibration experiment:

```bash
python3 scripts/calibrate_pa_outcome_model.py --model-name hist_gradient_boosting_multiclass --model-version 20260411T230512Z --output-json data/reports/pa_outcome_isotonic_20260411T230512Z.json
```

Bootstrap uncertainty evaluation:

```bash
python3 scripts/bootstrap_pa_outcome_evaluation.py --model-name hist_gradient_boosting_multiclass --model-version 20260411T230512Z --replicates 50 --output-json data/reports/pa_outcome_bootstrap_20260411T230512Z.json
```

Target:

- `pa_outcome_distribution`

Feature source:

- `features.plate_appearance_outcome_examples`
- `features.plate_appearance_advanced_examples` for advanced features
- `features.plate_appearance_outcome_grouped_examples` when `--target-taxonomy grouped` is used

Evaluation priority:

1. Log loss.
2. Calibration / reliability by class.
3. Subgroup reliability by count, base/out state, handedness matchup, and season.
3. Brier score.
4. Top-k accuracy.
5. Macro/weighted F1 as secondary diagnostics.

Do not promote this model until calibration reporting exists.

Scoring:

```bash
python3 scripts/predict_pa_outcome_distribution.py --game-id ANA202506060 --plate-appearance-id 30
```

The scorer returns class probabilities plus derived aggregates such as hit, extra-base hit, traditional on-base, reach-base-any, ball-in-play, and expected total bases. API consumers can request the same path through `/api/predict` with `target_id: "pa_outcome_distribution"`.

## Build Grouped PA Outcome Layer

Purpose: create the first stable grouped target taxonomy for baseline multiclass PA modeling without replacing the granular canonical outcome layer.

Command:

```bash
psql -h localhost -p 5432 -d retrosheet -v ON_ERROR_STOP=1 -f sql/078_plate_appearance_outcome_grouped.sql
```

Outputs:

- `features.plate_appearance_outcome_grouped_examples`
- `features.plate_appearance_outcome_grouped_validation_summary`

Rules:

1. Keep `features.plate_appearance_outcome_examples` as the raw canonical outcome source.
2. Use the grouped layer for the first stable direct PA multiclass benchmarks.
3. Treat this as additive target infrastructure; do not collapse or overwrite the granular layer.

## Normalize Pitch Sequences

Purpose: preserve Retrosheet `pitch_seq_tx` at one-row-per-symbol granularity without inventing a separate raw parsing pipeline.

Command:

```bash
psql -h localhost -p 5432 -d retrosheet -v ON_ERROR_STOP=1 -f sql/077_pitch_sequence_model.sql
```

Outputs:

- `features.pitch_sequence_symbol_reference`
- `features.pitch_sequence_examples`
- `features.pitch_sequence_validation_summary`

Use this layer before attempting same-PA temporal features or any direct next-pitch model. It preserves official Retrosheet pitch-sequence symbols, coarse symbol groupings, and terminal-pitch flags while staying anchored to `features.plate_appearance_outcome_examples`.

## Build Scenario Simulations

Current baseline:

- Historical lookup through `features.half_inning_outcome_summary`.
- Saved runs in `predictions.simulation_runs`.

Future model-driven procedure:

1. Score each simulated PA with `pa_outcome_distribution`.
2. Sample terminal PA outcome.
3. Apply correct base/out/run transition.
4. Stop at three outs.
5. Repeat for bounded simulation count.
6. Save filters, model versions, run distribution, summary, and assumptions.

Critical warning: incorrect baseball state transitions make simulation results look precise and wrong. Prefer fewer classes or slower code over incorrect state updates.

## Add Live MLB Bridge Work

Purpose: transform live MLB data into the same canonical shapes as Retrosheet history.

Procedure:

1. Store raw payload in `raw_mlb.live_feed_snapshots` with fetch provenance.
2. Map MLB IDs to Retrosheet IDs through `bridge`.
3. Transform live game/play state into `core.live_games` and `core.live_events` by upsert, not destructive table replacement.
4. Preserve `raw_payload` and `raw_play` in the canonical live layer for replay/debugging.
5. Build live feature rows with the same columns used by historical training.
6. Score with active registered models.
7. Store predictions with model ID, timestamp, and input features.

Do not score raw MLB JSON directly in production paths.
Do not merge raw MLB rows into historical raw layers. Historical/live combination belongs in `analysis.*` views/materialized views and later feature-parity views.

## Update Web Command Center

Purpose: expose warehouse/model workflows safely.

Rules:

- Use API routes as the only browser-to-backend boundary.
- Query curated views or call allow-listed scripts.
- Do not expose arbitrary shell.
- Do not expose arbitrary SQL writes.
- Persist meaningful chat/simulation/backtest workflows.
- Run `npm run build` before committing.

## Create Or Update GitHub Issues

Use issues as durable project records.

Each issue should include:

- Goal.
- Current state.
- Scope.
- Non-goals.
- Acceptance criteria.
- Relevant files/tables.
- Validation expectations.
- Parent roadmap issue if applicable.

Comment on existing parent issues when work advances a goal.
