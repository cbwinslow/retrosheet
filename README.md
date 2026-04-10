# Retrosheet Warehouse

PostgreSQL-first warehouse tooling for historical Retrosheet play-by-play data and live MLB game feeds.

The goal is to train models on historical play-by-play states, then run the same feature pipeline against live MLB data.

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
```

`load_reference_metadata.py` loads Retrosheet `biofile.csv`, `teams.csv`, and `ballparks.csv`, backfills player handedness, and refreshes the materialized feature views.

`load_auxiliary_retrosheet.py` loads the broader Retrosheet-provided auxiliary files: `biofile0.csv`, coaches, ejections, relatives, season rosters, season team files, schedules, umpires, and special gamelog lines. It also exposes normalized `core` views for roster entries, All-Star rosters/games, schedules, umpires, coaches, ejections, and player relatives.

`sql/050_feature_marts.sql` builds indexed materialized views for prior-season batter, pitcher, team, context, and half-inning scenario features. These are the first fast feature marts for ML training and live inference joins.

`sql/060_advanced_feature_marts.sql` adds career-prior batter/pitcher features, coarse context fallbacks, batter-pitcher matchup history, park run environment, team rolling-30 form, and advanced example views.

`sql/070_temporal_and_production_marts.sql` adds team rest/travel context, player season production, pitcher season production, and temporal example views for future model training.

`sql/076_plate_appearance_outcome_model.sql` adds a granular multiclass plate-appearance outcome feature layer and registers the `pa_outcome_distribution` prediction target. See [docs/AT_BAT_OUTCOME_MODEL_REVIEW.md](docs/AT_BAT_OUTCOME_MODEL_REVIEW.md) for how this maps the at-bat outcome design spec onto the current warehouse.

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

See [docs/CORE_SCHEMA.md](docs/CORE_SCHEMA.md) for the typed database layer, constraints, indexes, and feature seed.

See [docs/PROJECT_LOG.md](docs/PROJECT_LOG.md) for a running build log of major warehouse, modeling, and planning steps.

See [docs/agents/README.md](docs/agents/README.md) for the project inventory, modeling objectives, canonical procedures, and agent operating map.

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
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.05 --train-through 2022
```

Run a reproducible hyperparameter sweep without committing model binaries:

```bash
python3 scripts/sweep_hyperparameters.py --target-id pa_batter_hit --feature-set advanced --sample-rate 0.05 --max-candidates 12
```

Compare trained plate-appearance models:

```bash
python3 scripts/analyze_pa_models.py
```

Promote the best registered model versions after candidate training:

```bash
python3 scripts/promote_best_models.py --target-prefix 'pa_%' --min-validation-rows 10000
python3 scripts/promote_best_models.py --target-id game_home_win --min-validation-rows 10000
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
psql -h localhost -p 5432 -d retrosheet -f sql/076_plate_appearance_outcome_model.sql
```

## MLB Live Feed

Store a source-preserved snapshot of MLB's live game feed:

```bash
python3 scripts/warehouse.py fetch-live-game --game-pk 748555
```

The live feed endpoint used is:

```text
https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live
```

## Notes

Retrosheet data attribution:

```text
The information used here was obtained free of
charge from and is copyrighted by Retrosheet. Interested
parties may contact Retrosheet at "www.retrosheet.org".
```
