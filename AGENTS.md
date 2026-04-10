# Agent Operating Guide

This project builds a reproducible baseball prediction warehouse from free/open data sources.

## Mission

- Build a PostgreSQL warehouse from Retrosheet historical data.
- Use Chadwick tools as the authoritative parser layer for Retrosheet event files.
- Add MLB Stats API / GUMBO live data ingestion for real-time prediction.
- Build ML-ready features that can train on historical game states and score live games.
- Later, compare model probabilities with public prediction-market prices such as Kalshi and Polymarket. Treat any market-related work as research tooling, not financial advice.

## Non-Negotiables

- Keep source-preserved raw data. Do not overwrite or discard raw Retrosheet, Chadwick, or MLB API payloads.
- Prefer additive migrations and views over destructive schema changes.
- Keep `README.md` current when commands, setup, or workflow changes.
- Keep this `AGENTS.md` current when project conventions change.
- Keep `docs/PROJECT_LOG.md` current with significant completed work, validation counts, and next-step decisions.
- Use Chadwick-generated headers and documented field names instead of hand-invented column mappings.
- Put database typing, constraints, foreign keys, indexes, and reusable ML features in `core`, `features`, `models`, and `predictions`, not in raw landing tables.
- Maintain reproducibility: scripts should run from a clean checkout with documented dependencies.
- Default database target is the local PostgreSQL database named `retrosheet` on port `5432`, unless `DATABASE_URL` or `PG*` environment variables override it.

## Data Layers

- `raw_retrosheet`: source-preserved Chadwick extracts and Retrosheet reference tables.
- `raw_mlb`: source-preserved MLB Stats API / GUMBO live snapshots.
- `bridge`: cross-reference tables between Retrosheet IDs, MLB IDs, and other public IDs.
- `core`: canonical baseball entities and game-state views shared by historical and live sources.
- `features`: ML-ready training and inference tables.
- `predictions`: model outputs, backtests, and live prediction snapshots.

## Chadwick Procedure

Use the installed Chadwick command-line tools:

- `cwevent`: event/play-level rows.
- `cwgame`: game metadata, lineups, final scores, linescores, managers, umpires.
- `cwdaily`: player game-by-game batting, pitching, and fielding summaries.
- `cwsub`: substitutions.
- `cwcomment`: comments, ejections, and umpire changes.
- `cwbox`: boxscore rendering; useful later, but not the first normalized-table path.

Always include `-n` for new extracts so the first row has official Chadwick column names.

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
