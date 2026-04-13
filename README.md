# Retrosheet Warehouse

PostgreSQL-first warehouse tooling for historical Retrosheet play-by-play data and live MLB game feeds.

The goal is to train models on historical play-by-play states, then run the same feature pipeline against live MLB data.

For the paper-style running research narrative, see [research_report.md](research_report.md).

## Architecture

- `raw_retrosheet`: source-preserved Retrosheet/Chadwick extracts.
- `raw_mlb`: source-preserved MLB Stats API / GUMBO payloads.
- `bridge`: cross-reference tables for player, team, park, and game IDs.
- `core`: canonical views/tables that will make Retrosheet and MLB live data look the same.
- `features`: ML-ready training and inference tables.
- `predictions`: live and backtest model outputs.

## Database

These scripts use your existing PostgreSQL server on port `5432`. Configure connection details with either `DATABASE_URL` or standard `PG*` variables.

Example:

```bash
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=retrosheet
export PGUSER=postgres
```

Then initialize schemas:

```bash
python3 scripts/warehouse.py init-db
```

Full reproducible rebuild order:

```bash
YEARS=2000-2025 PGDATABASE=retrosheet scripts/rebuild_warehouse.sh
```

The rebuild script now includes:
- Core schema setup (games, events, plate appearances)
- MLB live data infrastructure (raw_mlb, bridge tables, live core tables)
- Reference and auxiliary metadata loading
- Feature marts (basic, advanced, temporal, half-inning)
- Model training data preparation

Apply the typed core/modeling migration after loading Chadwick data:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/010_core_games_events.sql
psql -h localhost -p 5432 -d retrosheet -f sql/020_plate_appearances.sql
python3 scripts/load_reference_metadata.py
python3 scripts/load_auxiliary_retrosheet.py
psql -h localhost -p 5432 -d retrosheet -f sql/050_feature_marts.sql
psql -h localhost -p 5432 -d retrosheet -f sql/060_advanced_feature_marts.sql
psql -h localhost -p 5432 -d retrosheet -f sql/070_temporal_and_production_marts.sql
psql -h localhost -p 5432 -d retrosheet -f sql/075_interface_workflows.sql
psql -h localhost -p 5432 -d retrosheet -f sql/076_plate_appearance_outcome_model.sql
psql -h localhost -p 5432 -d retrosheet -f sql/077_pitch_sequence_model.sql
psql -h localhost -p 5432 -d retrosheet -f sql/078_plate_appearance_outcome_grouped.sql
psql -h localhost -p 5432 -d retrosheet -f sql/079_probability_evaluation_reports.sql
psql -h localhost -p 5432 -d retrosheet -f sql/081_probability_calibration_artifacts.sql
```

`load_reference_metadata.py` loads Retrosheet `biofile.csv`, `teams.csv`, and `ballparks.csv`, backfills player handedness, and refreshes the materialized feature views.

`load_auxiliary_retrosheet.py` loads the broader Retrosheet-provided auxiliary files: `biofile0.csv`, coaches, ejections, relatives, season rosters, season team files, schedules, umpires, and special gamelog lines. It also exposes normalized `core` views for roster entries, All-Star rosters/games, schedules, umpires, coaches, ejections, and player relatives.

`sql/050_feature_marts.sql` builds indexed materialized views for prior-season batter, pitcher, team, context, and half-inning scenario features. These are the first fast feature marts for ML training and live inference joins.

`sql/060_advanced_feature_marts.sql` adds career-prior batter/pitcher features, coarse context fallbacks, batter-pitcher matchup history, park run environment, team rolling-30 form, and advanced example views.

`sql/070_temporal_and_production_marts.sql` adds team rest/travel context, player season production, pitcher season production, and temporal example views for future model training.

`sql/076_plate_appearance_outcome_model.sql` adds a granular multiclass plate-appearance outcome feature layer, reusable season-era / rules-era columns, and registers the `pa_outcome_distribution` prediction target. See [docs/AT_BAT_OUTCOME_MODEL_REVIEW.md](docs/AT_BAT_OUTCOME_MODEL_REVIEW.md) for how this maps the at-bat outcome design spec onto the current warehouse.

`sql/077_pitch_sequence_model.sql` normalizes `pitch_seq_tx` into one row per Retrosheet pitch-sequence symbol, preserves official symbol semantics, and exposes reusable pitch-sequence features for future same-PA and pitch-level modeling.

`sql/078_plate_appearance_outcome_grouped.sql` adds the grouped PA outcome layer used by the first stable direct multiclass PA benchmarks.

`sql/079_probability_evaluation_reports.sql` adds durable calibration and bootstrap report storage in `predictions`.

`sql/081_probability_calibration_artifacts.sql` extends calibration reports with persisted artifact support so calibrated multiclass scorers can load a registered isotonic artifact by report name or latest report.

`sql/082_count_state_feature_marts.sql` adds batter, pitcher, and context prior-rate marts split by ball-strike count plus `features.plate_appearance_count_state_advanced_examples` for count-state-enhanced PA modeling.

`sql/122_live_pa_feature_parity.sql` adds the first live `advanced_count` parity view, `features.live_plate_appearance_advanced_count_examples`, so the current best historical PA model can score stored MLB live plate appearances. Player/count/context priors are wired, and park/team rolling priors now populate for rows transformed through the repaired bridge path. Older `core.live_*` rows that were transformed before the bridge repair still need a replay/backfill pass if you want those priors populated historically.

## Retrosheet Play-By-Play

Install Chadwick tools first. The warehouse uses Chadwick as the official parser layer for Retrosheet event files.

```bash
python3 scripts/warehouse.py check-deps
python3 scripts/warehouse.py fetch-retrosheet
python3 scripts/warehouse.py init-db
python3 scripts/warehouse.py extract-chadwick --years 2023 --outputs all
python3 scripts/warehouse.py load-chadwick --years 2023 --outputs all
```

For a range:

```bash
python3 scripts/warehouse.py extract-chadwick --years 2000-2025 --outputs all
python3 scripts/warehouse.py load-chadwick --years 2000-2025 --outputs all
```

The Chadwick outputs loaded today are:

- `raw_retrosheet.chadwick_events` from `cwevent`
- `raw_retrosheet.chadwick_games` from `cwgame`
- `raw_retrosheet.chadwick_daily` from `cwdaily`
- `raw_retrosheet.chadwick_substitutions` from `cwsub`
- `raw_retrosheet.chadwick_comments` from `cwcomment`

See [docs/WAREHOUSE_PLAN.md](docs/WAREHOUSE_PLAN.md) for the staged normalization plan.

See [docs/PREDICTION_ENGINE_PLAN.md](docs/PREDICTION_ENGINE_PLAN.md) for the reusable ML, agent, live-data, and market-intelligence architecture.

See [docs/RESEARCH_METHODOLOGY.md](docs/RESEARCH_METHODOLOGY.md) for the formal CRISP-DM methodology, notation, objective functions, and evaluation logic.

See [docs/TEMPORAL_MODEL_SELECTION.md](docs/TEMPORAL_MODEL_SELECTION.md) for the recency-weighting policy, era segmentation, fixed-window benchmarks, and validation procedure for choosing how much history to train on.

See [docs/EDGEFORGE_TRIAGE.md](docs/EDGEFORGE_TRIAGE.md) for the current status of the unintegrated EdgeForge / MLB-enhanced files. Those files are experimental until they are merged into the documented warehouse architecture.

See [docs/CORE_SCHEMA.md](docs/CORE_SCHEMA.md) for the typed database layer, constraints, indexes, and feature seed.

See [docs/PROJECT_LOG.md](docs/PROJECT_LOG.md) for a running build log of major warehouse, modeling, and planning steps.

See [docs/agents/README.md](docs/agents/README.md) for the project inventory, modeling objectives, canonical procedures, and agent operating map.

## Live MLB Data Ingestion

The warehouse supports real-time MLB game data ingestion alongside historical Retrosheet data. The intended live shape is:

- `raw_mlb`: source-preserved MLB API payloads plus fetch provenance
- `bridge`: MLB ↔ Retrosheet ID reconciliation
- `core.live_games` / `core.live_events`: canonical live state
- `analysis.*`: historical + live union layer for combined querying

Raw MLB data stays separate from Retrosheet raw data. Cross-source analysis happens in `analysis` views/materialized views, not by merging raw layers together.

### One-Time Setup

Populate bridge tables for ID mapping between MLB and Retrosheet systems:

```bash
python3 scripts/populate_bridge_tables.py
```

This downloads the Chadwick Bureau Register and populates:

- `bridge.player_xref`
- `bridge.team_xref`
- `bridge.park_xref`

Important limitation: `bridge.team_xref` is currently seasonless. Current/canonical MLB franchise ids are mapped for live scoring, but franchise-move cases such as `MON -> WAS` and `FLA -> MIA` still need a future season-aware bridge design if you want perfect historical MLB-team reconciliation across the entire `2000-2025` raw MLB archive.

### Ongoing Live Data Ingestion

Discover and ingest recent MLB games:

```bash
# Discover active games
python3 scripts/fetch_mlb_schedule.py --yesterday

# Ingest all discovered games
python3 scripts/ingest_live_games.py --schedule

# Or ingest a specific game
python3 scripts/ingest_live_games.py --game-pk 823884
```

For a single game, the explicit sequence is:

```bash
python3 scripts/warehouse.py fetch-live-game --game-pk 823884
python3 scripts/transform_live_game.py --game-pk 823884
psql -h localhost -p 5432 -d retrosheet -c "REFRESH MATERIALIZED VIEW analysis.combined_plate_appearances;"
```

New raw snapshots store request params, HTTP status, checksum, game date, and season in addition to the full JSON payload.

If you need to reapply bridge/transform fixes to already stored MLB snapshots, use the bounded replay utility:

```bash
python3 scripts/replay_live_bridge_backfill.py --season-from 2019 --season-to 2019 --limit 50
```

Start with regular-season slices. Spring-training and other non-regular-season venues may still remain as `MLB###` park fallbacks until a broader non-regular-season park crosswalk is added.

### Combined Data Analysis

Query across historical and live data using analysis views:

```sql
-- Check data source statistics
SELECT * FROM analysis.get_data_source_stats();

-- Query combined games from both sources
SELECT * FROM analysis.combined_games
WHERE game_date >= CURRENT_DATE - INTERVAL '7 days';

-- Query combined events
SELECT ce.*
FROM analysis.combined_events ce
JOIN analysis.combined_games cg USING (game_id)
WHERE ce.source_type = 'mlb_live'
  AND cg.game_date >= CURRENT_DATE;
```

See [docs/LIVE_DATA_ARCHITECTURE.md](docs/LIVE_DATA_ARCHITECTURE.md) for complete architecture diagrams and procedures.

### Historical MLB Raw Backfill

For bulk historical MLB raw acquisition, use:

```bash
python3 scripts/download_mlb_bulk.py --start-season 2000 --end-season 2025 --mode schedules
python3 scripts/download_mlb_bulk.py --start-season 2000 --end-season 2025 --mode games --workers 4 --delay 1.0
```

This path backfills source-preserved rows into `raw_mlb.schedule_snapshots` and `raw_mlb.live_feed_snapshots` with request/status/error provenance. It is the canonical historical MLB raw backfill utility. Follow it with the documented canonical transform path rather than building a second parallel MLB warehouse.

For broader MLB source coverage beyond schedules and game feeds, also backfill reference endpoints:

```bash
python3 scripts/fetch_mlb_reference_data.py --start-season 2000 --end-season 2025
```

This stores source-preserved snapshots for `teams`, `rosters`, `people`, `venues`, and `standings` in `raw_mlb.reference_snapshots`. In practice, this is the canonical answer to “download all MLB source data” for the project’s modeling scope: game schedules, live feeds, and the main reference endpoint families needed for enrichment and reconciliation.

Build the typed reference layer with:

```bash
psql -h localhost -p 5432 -d retrosheet -v ON_ERROR_STOP=1 -f sql/095_mlb_reference_views.sql
```

This creates:

- `core.mlb_api_teams`
- `core.mlb_api_team_rosters`
- `core.mlb_api_players`
- `core.mlb_api_venues`
- `core.mlb_api_standings`

These views intentionally read from the latest successful raw snapshots. Keep source preservation in `raw_mlb`; put typing and downstream joins in `core`.

## Modeling

Install Python modeling dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Train initial game-win models from the typed feature layer:

```bash
python3 scripts/train_models.py --target-id game_home_win --sample-rate 0.10 --train-through 2022
```

Train a plate-appearance model:

```bash
python3 scripts/train_models.py --target-id pa_batter_hit --sample-rate 0.05 --train-through 2022 --feature-set advanced
```

Train the granular multiclass plate-appearance outcome distribution model:

```bash
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.05 --train-through 2022 --no-activate
```

Train the grouped baseline multiclass plate-appearance outcome model:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/078_plate_appearance_outcome_grouped.sql
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --target-taxonomy grouped --sample-rate 0.05 --train-through 2022 --no-activate
```

Train the same model with explicit temporal policy controls:

```bash
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.05 --train-through 2022 --recent-window 7 --no-activate
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.05 --train-through 2022 --season-half-life 5 --downweight-2020 0.5 --no-activate
```

Train the count-state-enhanced grouped multiclass PA model:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/082_count_state_feature_marts.sql
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced_count --target-taxonomy grouped --sample-rate 0.05 --train-through 2022 --no-activate
```

Score a historical plate appearance with a registered multiclass outcome model:

```bash
python3 scripts/predict_pa_outcome_distribution.py --game-id ANA202506060 --plate-appearance-id 30
```

Persist calibration and bootstrap evidence for a registered multiclass outcome model:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/079_probability_evaluation_reports.sql
python3 scripts/persist_pa_outcome_reports.py --model-name hist_gradient_boosting_multiclass --model-version 20260411T230512Z
```

This stores durable records in:

- `predictions.prediction_runs`
- `predictions.calibration_reports`
- `predictions.bootstrap_reports`

Register a reusable isotonic calibration artifact and score with calibrated probabilities:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/081_probability_calibration_artifacts.sql
python3 scripts/register_pa_outcome_calibration.py --model-name hist_gradient_boosting_multiclass --model-version 20260411T230512Z
python3 scripts/predict_pa_outcome_distribution.py --game-id ANA202506060 --plate-appearance-id 30 --model-name hist_gradient_boosting_multiclass --model-version 20260411T230512Z --apply-calibration
```

The Next.js `/api/predict` route accepts the same optional calibration controls for `target_id = "pa_outcome_distribution"`:

- `apply_calibration`
- `calibration_report_name`

Score a stored live MLB plate appearance with the same calibrated `advanced_count` model:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/122_live_pa_feature_parity.sql
python3 scripts/predict_live_pa_outcome_distribution.py --game-id MLB117201910300 --plate-appearance-id 79 --model-version 20260412T045759Z --apply-calibration
```

Run a reproducible hyperparameter sweep without committing model binaries:

```bash
python3 scripts/sweep_hyperparameters.py --target-id pa_batter_hit --feature-set advanced --sample-rate 0.05 --max-candidates 12
```

Evaluate model performance with cross-validation:

```bash
python3 scripts/cross_validate_models.py --target-id pa_batter_hit --sample-rate 0.05 --cv-folds 5
```

Compare trained plate-appearance models:

```bash
python3 scripts/analyze_pa_models.py
```

Run fast inference with model caching:

```bash
python3 scripts/fast_prediction_service.py
```

Test inference performance:

```bash
python3 scripts/test_inference_performance.py
```

Run the AI Baseball Chatbot:

```bash
python3 scripts/baseball_chatbot.py
```

Run comprehensive testing suite:

```bash
python3 scripts/test_baseball_analytics.py --test-type all
```

Promote the best registered model versions after candidate training:

```bash
python3 scripts/promote_best_models.py --target-prefix 'pa_%' --min-validation-rows 10000
python3 scripts/promote_best_models.py --target-id game_home_win --min-validation-rows 10000
```

Automatically promote best models based on cross-validation performance:

```bash
python3 scripts/auto_promote_models.py --target-prefix 'pa_%'  # Promote best PA models
python3 scripts/auto_promote_models.py --dry-run  # Preview changes without applying
```

Artifacts are written under ignored `data/models/` and model metadata is registered in `models.model_registry`. We intentionally do not use Git LFS; models should be regenerated from the scripts and database, or later stored in regular object storage if needed.

AI inference provider configuration is documented in [config/ai_providers.example.json](config/ai_providers.example.json). The intended providers are OpenRouter, Groq, and Codex/OpenAI-compatible agent orchestration.

## Web Command Center

The interactive interface lives in `baseball-chatbot-ui/`. It is a Next.js command center for asking the warehouse questions, running scenario simulations, inspecting active models/backtests, exporting tables to CSV, and launching safe local workflow commands.

Run it locally:

```bash
cd baseball-chatbot-ui
npm install
npm run dev
```

The UI expects PostgreSQL to be available through the same `PG*` settings as the warehouse scripts. By default it connects to `localhost:5432/retrosheet`.

Current cockpit views:

- **Chat Analyst**: a rule-based warehouse assistant that routes natural-language prompts to curated SQL/API tools.
- **Sim Lab**: historical half-inning scenario distributions from `features.half_inning_outcome_summary`, including filters such as season, inning, half-inning, team, and left-handed-only outcomes.
- **Models & Backtests**: active model registry, target metrics, sweep candidates, and production leaderboards.
- **Workbench**: a safe allow-listed command runner for status/model checks and documented script entry points.

The spreadsheet approach is intentionally simple right now: query results render as tables with CSV export. If the workflow needs richer spreadsheet editing later, add a dedicated data-grid component such as Handsontable, AG Grid Community, or Glide Data Grid behind typed API routes. Do not expose arbitrary SQL writes from the browser without authentication and explicit guardrails.

The terminal approach is also intentionally guarded. The browser should call allow-listed API actions first. A true embedded terminal can be added later with `node-pty`, `xterm.js`, WebSockets, authentication, and a restricted project-local shell, but the default web UI must not expose arbitrary shell execution.

Apply the interface persistence schema before running the cockpit against a fresh warehouse:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/075_interface_workflows.sql
```

## MLB Live Feed

Store a source-preserved snapshot of MLB's live game feed and transform it into core schema:

```bash
# Fetch live game data
python3 scripts/warehouse.py fetch-live-game --game-pk 748555

# Transform into core schema for live prediction
python3 scripts/transform_live_game.py --game-pk 748555
```

The live feed endpoint used is:

```text
https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live
```

Live games are stored in `core.live_games` and `core.live_events` as the canonical live layer. Those tables preserve `raw_payload` / `raw_play` for replay and debugging. Historical model training is currently more mature than live feature parity; use the live layer as the bridge into later model-scoring work.

## Notes

Retrosheet data attribution:

```text
The information used here was obtained free of
charge from and is copyrighted by Retrosheet. Interested
parties may contact Retrosheet at "www.retrosheet.org".
```
