# Procedures

These are the canonical workflows. Use them before creating new ad hoc scripts.

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

## Live Data Ingestion

Purpose: ingest real-time MLB game data alongside historical Retrosheet data.

### One-Time Setup (Bridge Tables)

Command:

```bash
# Step 1: Populate core bridge tables (players, teams, parks)
python3 scripts/bridge/populate_bridge_tables.py

# Step 2: Populate season-aware team_xref with franchise moves
python3 scripts/bridge/populate_season_aware_team_xref.py

# Step 3: Populate external player ID mappings (Statcast, Baseball Reference, Lahman)
python3 scripts/bridge/populate_external_bridge.py

# Step 4: Populate coach and umpire bridge tables
python3 scripts/bridge/populate_coach_umpire_bridge.py

# Step 5: Create monitoring views
psql -f sql/bridge/900_bridge_monitoring_views.sql
```

Expected order:

1. Download Chadwick Bureau Register CSV files.
2. Parse player register rows.
3. Populate `bridge.player_xref` with MLB ↔ Retrosheet player ID mappings.
4. Populate `bridge.team_xref` with current/canonical MLB franchise mappings from `core.mlb_api_teams`.
5. Populate `bridge.park_xref` with MLB venue-id mappings covering the observed `2000-2025` MLB venue surface.
6. Add `valid_from_season` and `valid_to_season` columns to `bridge.team_xref` for season-aware franchise moves (e.g., MON→WAS, FLO→MIA).
7. Populate `bridge.external_player_xref` with Statcast, Baseball Reference, and Lahman ID mappings using `bridge.player_xref` as source of truth.
8. Populate `bridge.coach_xref` and `bridge.umpire_xref` from Retrosheet data.
9. Create monitoring views for bridge table health checks and coverage statistics.

Notes:

- `bridge.team_xref` is now season-aware with `valid_from_season` and `valid_to_season` columns.
- Franchise-move cases are correctly represented with separate entries for each franchise period.
- `bridge.external_player_xref` uses text columns for IDs to match Retrosheet ID formats (e.g., "aaronh101").
- Monitoring views in `bridge.bridge_table_counts`, `bridge.external_player_coverage`, and `bridge.bridge_data_quality` provide health checks.

### Complete Bridge Population with Validation (Recommended)

Purpose: Achieve 100% player ID coverage across all data sources using Chadwick Register, Lahman gap-fill, and comprehensive validation.

Command:

```bash
# Full population with all stages
./scripts/bridge/populate_all_bridge_tables.sh

# Validation only (skip population)
./scripts/bridge/populate_all_bridge_tables.sh --validate-only

# Dry run (no database changes)
./scripts/bridge/populate_all_bridge_tables.sh --dry-run

# Skip specific stages
./scripts/bridge/populate_all_bridge_tables.sh --skip-lahman
```

Expected order:

1. **Create/Update SQL Procedures**: Deploy `930_chadwick_register_bridge.sql`, `931_lahman_bridge_population.sql`, `940_bridge_validation_tests.sql`.
2. **Load Chadwick Register Data**: Download 16 CSV files from Chadwick Bureau, parse 58 ID fields, load to staging table.
3. **Upsert to player_xref**: Merge Chadwick data into `bridge.player_xref` with conflict resolution.
4. **Lahman Gap-Fill**: Load Lahman People data, match by name to fill missing Retrosheet IDs.
5. **Populate External Bridges**: Run `populate_external_bridge.py` for Statcast, BBRef, Lahman mappings.
6. **Validation Testing**: Execute `bridge.run_all_bridge_tests()` to verify coverage.
7. **Generate Report**: Summary statistics for all bridge tables and pitch data coverage.

Key validation tests:

- `bridge.test_player_xref_mlb_coverage(95.0)`: ≥95% of players have MLB IDs
- `bridge.test_player_xref_retrosheet_coverage(20.0)`: ≥20% have Retrosheet IDs
- `bridge.test_pitch_data_player_coverage(100.0)`: 100% of pitch data players linked
- `bridge.test_player_xref_mlb_id_unique()`: No duplicate MLB IDs
- `bridge.test_game_xref_complete_coverage()`: All games have both MLB and Retrosheet IDs

Notes:

- Uses Chadwick Bureau Register as primary source (20,000+ players, most comprehensive)
- Uses Lahman People table for secondary gap-filling (name-based matching)
- All procedures are idempotent - safe to re-run
- Logs saved to `logs/bridge_population_YYYYMMDD_HHMMSS.log`
- Validation functions return BOOLEAN for CI/CD integration

### Orchestrated Bridge Ingestion (New - Python-Based)

Purpose: Production-grade bridge population with validation layer, error handling, checkpointing, and detailed reporting. Replaces `populate_all_bridge_tables.sh` for Python-based workflows.

Command:

```bash
# Full orchestrated ingestion with all layers
python scripts/bridge/run_bridge_ingestion.py

# Skip download (use existing staging data)
python scripts/bridge/run_bridge_ingestion.py --skip-download

# Skip validation (faster, but no pre-flight checks)
python scripts/bridge/run_bridge_ingestion.py --skip-validation

# Disable checkpointing (no resume capability)
python scripts/bridge/run_bridge_ingestion.py --no-checkpoints

# Dry run mode - preview what would change
python scripts/bridge/run_bridge_ingestion.py --dry-run

# Combined flags
python scripts/bridge/run_bridge_ingestion.py --skip-download --skip-validation --output-json results.json
```

What the orchestrator provides:

1. **Validation Layer** (6 pre-flight checks):
   - Staging table existence
   - Empty string ID detection
   - Duplicate ID detection
   - Constraint integrity verification
   - Foreign key relationship checks
   - Data type validation

2. **Error Handling Layer**:
   - Automatic retry with exponential backoff (3 attempts, 2s base delay)
   - Circuit breaker pattern prevents cascade failures
   - Graceful degradation on non-critical errors

3. **Checkpointing**:
   - Saves progress after each stage to `/tmp/bridge_checkpoints/`
   - Resumes from last successful stage on restart
   - 5 stages: create_procedures → download_and_load → run_upsert → post_validation → cleanup

4. **Detailed Reporting**:
   - Stage-by-stage timing and status
   - Validation results with pass/fail counts
   - Row counts processed
   - JSON output option for automation

Key files:

- `scripts/bridge/run_bridge_ingestion.py` - CLI entry point
- `mlb_predict/orchestration/bridge_orchestrator.py` - Orchestration logic
- `mlb_predict/orchestration/validation.py` - Validation rules
- `mlb_predict/orchestration/error_handling.py` - Retry and circuit breaker
- `mlb_predict/orchestration/checkpoints.py` - Progress persistence

Notes:

- Default: checkpoints enabled, validation enabled
- `--skip-download` uses existing data in `bridge._staging_chadwick_register`
- `--skip-validation` runs faster but skips all data quality checks
- Logs saved to `logs/bridge_orchestrator_YYYYMMDD_HHMMSS.log`
- Returns exit code 0 on success, 1 on failure (suitable for CI/CD)

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

# Fetch historical games for a date range
python3 scripts/fetch_espn_mlb.py ingest-historical --start-date YYYY-MM-DD --end-date YYYY-MM-DD --workers 10
```

Expected order:

1. Query ESPN API for schedule or game data
2. Compute checksum for deduplication
3. Store source-preserved JSON with fetch provenance in `raw_espn.*_snapshots`
4. Preserve request parameters, HTTP status, response time, and checksum

### ESPN Play-by-Play Data Ingestion

Command:

```bash
# Ingest play-by-play data for games that don't have it yet
python3 scripts/ingest_espn_plays.py
```

Expected order:

1. Query ESPN summary endpoint for plays data (not Core API v2 endpoint)
2. Extract plays array from summary response
3. Extract game_date and season from summary response
4. Store source-preserved JSON with fetch provenance in `raw_espn.plays_snapshots`
5. Skip games with empty plays arrays or no game data available

Rules:

1. Keep responses source-preserved in `raw_espn`.
2. Use checksum-based deduplication to avoid duplicate fetches.
3. ESPN play-by-play data is only available for recent games (2024-2026).
4. Historical play-by-play data (2000-2015) is not available via ESPN API - use Retrosheet/Chadwick or MLB Stats API instead.
5. ESPN data is supplemental to Retrosheet and MLB Stats API data.
6. Future work: create bridge tables for ESPN IDs and transform to canonical shapes if needed.

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
