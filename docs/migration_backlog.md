# Migration Backlog

How to use this file
This file is the implementation backlog for refactoring cbwinslow/retrosheet into a unified baseball CLI platform. Work should proceed in milestone order. Each milestone should be completed in a reviewable batch before moving to the next one .

Rules
Do not skip milestones without documenting why.

Do not begin large code refactors before the planning/docs milestones are complete.

Do not delete existing working logic before wrappers or migration targets exist.

Every task should update docs/migration_map.md if files move or responsibilities change.

Every milestone should end with a short validation checklist and notes on regressions, if any.

---

## Milestone 0 — Planning and contracts

Goals
Freeze the migration plan.

Document architecture, sources, grains, and file moves.

Create persistent agent instructions.

Tasks
Create docs/migration_plan.md

Create docs/migration_backlog.md

Create docs/migration_map.md

Create docs/architecture.md

Create docs/sources.md

Create docs/keys_and_grains.md

Create docs/models.md

Create root AGENTS.md

Create docs/agents/architecture_agent.md

Create docs/agents/python_agent.md

Create docs/agents/sql_agent.md

Create docs/agents/ml_agent.md

Create docs/agents/live_agent.md

Create docs/agents/docs_agent.md

Exit criteria
Architecture is documented.

Source priorities are documented.

Grain/key strategy has a first pass.

Agent instructions are split by function.

---

## Milestone 1 — Package and CLI foundation

Goals
Introduce the new baseball/ Python package.

Add an installable CLI without changing ingestion logic yet.

Tasks
Create baseball/__init__.py

Create baseball/cli.py

Create baseball/app.py

Create baseball/settings.py

Create baseball/logging.py

Add package entry point in pyproject.toml for baseball

Add Typer root app with command groups:

doctor

status

retrosheet

mlb

espn

statcast

bridge

features

models

pipeline

Add placeholder implementations that raise clear NotImplementedError or route to wrappers

Add minimal CLI tests

Exit criteria
uv run baseball --help works

uv run baseball doctor executes

uv run baseball status executes

---

## Milestone 2 — Shared core services

Goals
Eliminate duplicated connection, SQL execution, and filesystem logic.

Tasks
Create baseball/core/db.py

Create baseball/core/sql_runner.py

Create baseball/core/checkpoints.py

Create baseball/core/filesystem.py

Create baseball/core/http.py

Create baseball/core/types.py

Create baseball/core/registry.py

Add config loading from config/sources.yml

Add config loading from config/pipelines.yml

Add shared logging setup

Add tests for DB/config/SQL runner

Exit criteria
SQL files can be executed from one shared service.

HTTP fetch helpers are centralized.

Request/parameter objects are shared.

---

## Milestone 3 — Administrative SQL and control plane

Goals
Introduce run tracking, checkpoints, and error capture.

Tasks
Create sql/00_admin/001_pipeline_runs.sql

Create sql/00_admin/002_pipeline_checkpoints.sql

Create sql/00_admin/003_pipeline_errors.sql

Create sql/00_admin/004_system_metadata.sql

Create Python helpers to log pipeline runs

Wire run logging into CLI commands

Exit criteria
Every command can register a run record.

Checkpoints can be read and updated.

Errors are persisted and surfaced.

---

## Milestone 4 — Retrosheet historical adapter

Goals
Wrap current historical Retrosheet logic behind the new source adapter interface.

Tasks
Create baseball/sources/base.py

Create baseball/sources/retrosheet.py

Wrap current retrosheet/archive.py logic

Wrap current retrosheet/parser.py logic

Define raw/staging/core SQL path for Retrosheet

Add CLI commands:

baseball retrosheet download

baseball retrosheet ingest

baseball retrosheet validate

Add compatibility wrappers for old Retrosheet scripts if needed

Exit criteria
Historical download and ingest work through the new CLI.

Existing Retrosheet parsing is preserved.

---

## Milestone 5 — MLB live source vertical slice

Goals
Create the first end-to-end real-time-capable ingestion path.

Tasks
Create baseball/sources/mlb.py

Add MLB schedule fetch

Add MLB live feed fetch by gamePk

Add raw payload persistence

Create:

sql/10_raw/121_raw_mlb_live_feed.sql

sql/20_staging/221_stg_mlb_live_events.sql

sql/30_core/321_core_live_games.sql

sql/30_core/322_core_live_events.sql

sql/30_core/323_core_live_pitch_events.sql

sql/30_core/324_core_live_plate_appearances.sql

sql/30_core/325_core_game_state_snapshots.sql

Add CLI commands:

baseball mlb download

baseball mlb ingest

baseball mlb stream

baseball mlb validate

Exit criteria
Live MLB raw payloads persist.

Canonical live tables populate.

At least one active game can be processed end-to-end.

---

## Milestone 6 — ESPN secondary live source

Goals
Add ESPN as a secondary/fallback enrichment source.

Tasks
Create baseball/sources/espn.py

Add ESPN raw download

Add ESPN raw persistence

Create sql/10_raw/220_raw_espn.sql

Create sql/20_staging/222_stg_espn_events.sql

Define bridge path from ESPN IDs to canonical entities

Add CLI commands:

baseball espn download

baseball espn ingest

baseball espn validate

Exit criteria
ESPN data lands in raw.

ESPN data can enrich live state or bridge data.

---

## Milestone 7 — SQL reorganization

Goals
Reorganize current SQL files into the target layer structure.

Tasks
Create new SQL layer folders

Move sql/live/* into 10_raw, 20_staging, 30_core, 80_quality as appropriate

Move sql/external/* into 10_raw, 20_staging, 80_quality as appropriate

Move sql/bridge/* into 40_bridge and 80_quality

Update references in scripts and docs

Update docs/migration_map.md for every file move

Exit criteria
New SQL structure exists.

File purposes are clearer than before.

No SQL functionality is lost.

---

## Milestone 8 — Bridge consolidation

Goals
Move bridge logic to a shared service and consistent SQL layer.

Tasks
Create baseball/services/bridge.py

Wrap existing bridge scripts from scripts/bridge/

Standardize build/validate command flow

Add CLI commands:

baseball bridge build

baseball bridge validate

Create or migrate:

sql/40_bridge/401_bridge_games.sql

sql/40_bridge/402_bridge_teams.sql

sql/40_bridge/403_bridge_staff.sql

sql/40_bridge/404_bridge_parks.sql

sql/40_bridge/405_bridge_players.sql

sql/40_bridge/406_bridge_confidence.sql

sql/40_bridge/499_bridge_master.sql

Exit criteria
Bridge workflows run through one shared service.

Validation and monitoring still work.

---

## Milestone 9 — External and enrichment sources

Goals
Wrap external sources behind the same source adapter framework.

Tasks
Create baseball/sources/statcast.py

Create baseball/sources/lahman.py

Create baseball/sources/fangraphs.py

Create baseball/sources/bref.py

Create baseball/sources/weather.py

Create baseball/sources/park_factors.py

Reuse or wrap loaders from scripts/external_data/

Standardize raw landing + staging flow

Exit criteria
At least Statcast and Lahman are running through adapters.

External-source duplication is reduced.

---

## Milestone 10 — Sabermetric feature layer

Goals
Create reproducible feature builders and feature tables.

Tasks
Create baseball/features/base.py

Create baseball/features/run_expectancy.py

Create baseball/features/win_expectancy.py

Create baseball/features/leverage.py

Create baseball/features/matchup.py

Create baseball/features/rolling_form.py

Create baseball/features/bullpen.py

Create baseball/features/live_state.py

Create SQL files in sql/50_features/

Add baseball features build command

Exit criteria
Live and historical feature builds are supported.

Run expectancy, win expectancy, and leverage state are implemented.

---

## Milestone 11 — ML model layer

Goals
Add a reproducible model registry and first live-serving model.

Tasks
Create baseball/models/base.py

Create baseball/models/registry.py

Create baseball/models/training.py

Create baseball/models/inference.py

Create baseball/models/backtest.py

Create SQL tables:

sql/60_models/601_models_registry.sql

sql/60_models/602_models_training_runs.sql

sql/60_models/603_models_artifacts.sql

sql/70_serving/701_predictions_game_live.sql

sql/70_serving/702_predictions_plate_appearance_live.sql

sql/70_serving/703_predictions_pitch_live.sql

Implement first model:

win_probability

Exit criteria
Model registry exists.

First live model can score and persist predictions.

---

## Milestone 12 — Serving and performance layer

Goals
Add low-latency read models and performance-oriented structures.

Tasks
Create serving tables/views

Add selective materialized views where justified

Add indexes and performance checks

Add query-plan review notes

Add status surfaces for live predictions

Exit criteria
Live prediction reads are fast.

Serving layer is ready for future API/websocket use.

---

## Milestone 13 — Documentation and cleanup

Goals
Finalize project docs and deprecate legacy paths safely.

Tasks
Update README with new CLI workflow

Finalize source docs

Finalize model docs

Finalize AGENTS hierarchy

Move old scripts to scripts_legacy/

Add deprecation notes to wrappers

Exit criteria
New users can understand and run the project.

Legacy paths are documented, not silently broken.
