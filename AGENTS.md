# Agent Operating Guide

This project builds a reproducible baseball prediction warehouse from free/open data sources.

## Mission

- Build a PostgreSQL warehouse from Retrosheet historical data.
- Use Chadwick tools as the authoritative parser layer for Retrosheet event files.
- Add MLB Stats API / GUMBO live data ingestion for real-time prediction.
- Build ML-ready features that can train on historical game states and score live games.
- Later, compare model probabilities with public prediction-market prices such as Kalshi and Polymarket. Treat any market-related work as research tooling, not financial advice.

## Non-Negotiables

- Before creating new SQL, scripts, models, routes, or docs, check `docs/agents/FILE_INVENTORY.md` and `docs/agents/PROCEDURES.md` to see whether an existing workflow already owns the job.
- Keep source-preserved raw data. Do not overwrite or discard raw Retrosheet, Chadwick, or MLB API payloads.
- Prefer additive migrations and views over destructive schema changes.
- Keep `README.md` current when commands, setup, or workflow changes.
- Keep this `AGENTS.md` current when project conventions change.
- Keep `docs/agents/` current when file purposes, modeling goals, or canonical procedures change.
- Keep `docs/PROJECT_LOG.md` current with significant completed work, validation counts, and next-step decisions.
- Use Chadwick-generated headers and documented field names instead of hand-invented column mappings.
- Put database typing, constraints, foreign keys, indexes, and reusable ML features in `core`, `features`, `models`, and `predictions`, not in raw landing tables.
- Maintain reproducibility: scripts should run from a clean checkout with documented dependencies.
- Default database target is the local PostgreSQL database named `retrosheet` on port `5432`, unless `DATABASE_URL` or `PG*` environment variables override it.
- Do not require Git LFS. Keep generated data and model binaries out of git; scripts and database metadata must be enough to regenerate artifacts.

## Data Layers

- `raw_retrosheet`: source-preserved Chadwick extracts and Retrosheet reference tables.
- `raw_mlb`: source-preserved MLB Stats API / GUMBO live snapshots.
- `bridge`: cross-reference tables between Retrosheet IDs, MLB IDs, and other public IDs.
- `core`: canonical baseball entities and game-state views shared by historical and live sources.
- `features`: ML-ready training and inference tables.
- `predictions`: model outputs, backtests, and live prediction snapshots.

## Required Agent References

Use these docs as the project map:

- `docs/agents/PROJECT_OBJECTIVES.md`: prediction-engine objectives, modeling goals, and non-goals.
- `docs/agents/FILE_INVENTORY.md`: inventory of SQL, scripts, docs, interface routes, generated artifacts, and ownership.
- `docs/agents/PROCEDURES.md`: canonical workflows for warehouse rebuilds, target creation, feature marts, model training, simulation, live bridge work, interface changes, and GitHub issues.
- `docs/agents/MODELING_WORKFLOWS.md`: target/model inventory, evaluation priorities, Moneyball-style modeling goals, leakage checklist, and promotion rules.

If a file is not listed there and you make it important, update the inventory in the same change.

## Chadwick Procedure

Use the installed Chadwick command-line tools:

- `cwevent`: event/play-level rows.
- `cwgame`: game metadata, lineups, final scores, linescores, managers, umpires.
- `cwdaily`: player game-by-game batting, pitching, and fielding summaries.
- `cwsub`: substitutions.
- `cwcomment`: comments, ejections, and umpire changes.
- `cwbox`: boxscore rendering; useful later, but not the first normalized-table path.

Always include `-n` for new extracts so the first row has official Chadwick column names.

## Live Data Ingestion Procedure

The system supports real-time MLB game data ingestion alongside historical Retrosheet data, maintaining clean separation between data sources.

### Data Separation Architecture

- **Historical Data**: `core.games`, `core.events`, `core.plate_appearances` (Retrosheet/Chadwick sourced)
- **Live Data**: `core.live_games`, `core.live_events` (MLB Stats API sourced)
- **Analysis Layer**: `analysis.*` views combine both sources for unified querying
- **Bridge Tables**: `bridge.player_xref`, `bridge.team_xref` map IDs between systems

### Live Data Ingestion Workflow

1. **Schedule Discovery**: `python3 scripts/fetch_mlb_schedule.py --yesterday`
   - Discovers active/completed MLB games
   - Identifies games available for ingestion

2. **Game Ingestion**: `python3 scripts/warehouse.py fetch-live-game --game-pk <GAME_PK>`
   - Downloads live game feed from MLB Stats API
   - Stores raw JSON in `raw_mlb.live_feed_snapshots`

3. **Data Transformation**: `python3 scripts/transform_live_game.py --game-pk <GAME_PK>`
   - Transforms MLB API JSON to core schema
   - Applies ID mapping via bridge tables
   - Populates `core.live_games` and `core.live_events`

4. **Batch Processing**: `python3 scripts/ingest_live_games.py --schedule`
   - Orchestrates discovery and ingestion for multiple games
   - Includes duplicate detection and error handling

5. **Bridge Table Management**: `python3 scripts/populate_bridge_tables.py`
   - Downloads Chadwick Bureau Register (comprehensive player/team ID mappings)
   - Populates `bridge.player_xref` and `bridge.team_xref` tables
   - Enables seamless ID translation between MLB and Retrosheet systems

### Analysis & Combined Queries

Use `analysis.*` views for unified access to both historical and live data:

- `analysis.combined_games`: Union of historical + live games
- `analysis.combined_events`: Union of historical + live events
- `analysis.combined_plate_appearances`: Combined plate appearance data
- `analysis.get_data_source_stats()`: Statistics across data sources
- `analysis.get_recent_games(days_back)`: Recent games from both sources

### Live Data Maintenance

- Live data tables are additive - no historical data is modified
- Bridge tables enable ID mapping without data duplication
- Analysis views provide transparent access to combined datasets
- Separate ingestion scripts prevent accidental mixing of data sources

## Recommended Workflow

1. `python3 scripts/warehouse.py check-deps`
2. `python3 scripts/warehouse.py fetch-retrosheet`
3. `python3 scripts/warehouse.py init-db`
4. `python3 scripts/warehouse.py extract-chadwick --years 2000-2025 --outputs all`
5. `python3 scripts/warehouse.py load-chadwick --years 2000-2025 --outputs all`

For fast iteration, pass a smaller year range or selected outputs.

## Modeling Direction

The ML target should start as win probability from a game state. Historical examples come from Retrosheet/Chadwick. Live inference examples will come from MLB Stats API / GUMBO transformed into the same `core` game-state shape.

For the broader reusable probability engine, follow `docs/PREDICTION_ENGINE_PLAN.md`. New work should preserve the separation between raw ingestion, typed `core` tables, ML features, model outputs, market comparisons, and chat/agent logs.

Use `scripts/train_models.py` for first-pass model training. Store model artifacts under `data/models/`, register metrics in `models.model_registry`, and keep AI inference providers configured through environment variables rather than hard-coded secrets.

When creating GitHub issues, include concrete links to relevant docs, scripts, migrations, and tables. Issues should be written as durable project records, not vague reminders.

Load Retrosheet reference metadata with `scripts/load_reference_metadata.py` after rebuilding `core.games`, `core.events`, and `core.plate_appearances`; it backfills player handedness and refreshes feature materialized views.

Load broader Retrosheet auxiliary metadata with `scripts/load_auxiliary_retrosheet.py` after the reference metadata step. It preserves source rows in `raw_retrosheet` and exposes normalized `core` views for rosters, All-Star rosters/games, schedules, umpires, coaches, ejections, and player relatives. Keep raw auxiliary tables source-preserved; add typed joins/views in `core` instead of reshaping the raw layer destructively.

Build indexed ML feature marts with `sql/050_feature_marts.sql` after auxiliary metadata is loaded. Prior-season feature marts should use `feature_season = source season + 1` to avoid leaking same-season labels into training rows.

Train candidate models with `scripts/train_models.py --feature-set enriched` once feature marts exist. Promote best registered versions with `scripts/promote_best_models.py` instead of hand-editing `models.model_registry.is_active`.

Use `scripts/rebuild_warehouse.sh` as the canonical rebuild order for contributors. It runs ingestion, core migrations, reference/auxiliary loaders, and feature marts in sequence.

Use `sql/060_advanced_feature_marts.sql` for higher-signal feature generation: career-prior player rates, coarse context fallbacks, batter-pitcher matchup history, park run environment, and rolling team form. Train stronger candidates with `--feature-set advanced` and explore grids with `scripts/sweep_hyperparameters.py`.

Use `sql/070_temporal_and_production_marts.sql` for team rest/travel context and reporting marts. It currently provides `features.team_game_context`, `features.player_production_season`, `features.pitcher_production_season`, and temporal training views. Treat WAR-like outputs as experimental until replacement level, positional adjustments, and park/run-environment adjustments are explicitly modeled.

## Interface Direction

The web command center lives in `baseball-chatbot-ui/`. Keep generated frontend artifacts out of git: `node_modules/` and `.next/` must stay ignored.

Use Next.js API routes as the interface boundary between the browser, PostgreSQL, and local Python scripts. API routes may query read-oriented warehouse views and may launch documented scripts through explicit allow-lists. Do not add a browser endpoint that executes arbitrary shell commands, arbitrary SQL writes, or unvalidated model paths.

Prefer exportable tables and typed JSON payloads for early spreadsheet workflows. If a richer spreadsheet is needed, add a client-side grid over read-only API data first, then design explicit import/write-back flows separately.

For chat/agent work, start with tool-routed answers over curated SQL and scripts. Provider-backed LLM tool calling can be layered in later through the configured OpenRouter, Groq, and Codex/OpenAI-compatible providers, but tool schemas, SQL guardrails, conversation logging, and auth should come before broad natural-language SQL access.

The safe terminal/workbench pattern is: browser button -> named API action -> allow-listed local command -> captured stdout/stderr. A full embedded terminal requires authentication, `node-pty`, WebSocket session controls, command restrictions, and project-root isolation.

Persist interface activity when practical. Chat prompts should write to `chat.query_logs`, and simulation/backtest workflows should write reproducible filters and summaries to tables under `predictions`.
