# SQL Agent Instructions

## Purpose

Keep the database layer clean, layered, performant, and understandable.

## Folder Rules

All SQL must live in:

- sql/00_admin
- sql/10_raw
- sql/20_staging
- sql/30_core
- sql/40_bridge
- sql/50_features
- sql/60_models
- sql/70_serving
- sql/80_quality

## Naming Rules

Use: `<order>_<layer>_<purpose>.sql`

Examples:
- 121_raw_mlb_live_feed.sql
- 325_core_game_state_snapshots.sql
- 501_features_run_expectancy.sql

## Content Rules

Every SQL file should start with a short header comment:
- Purpose
- Inputs
- Outputs
- Dependencies
- Whether rerunnable
- Whether it creates tables/views/materialized views/functions

## Database Modeling Rules

- Define grain explicitly.
- Prefer explicit column lists.
- Add indexes intentionally.
- Use constraints when practical.
- Document natural keys and surrogate keys.
- Update docs/keys_and_grains.md when table semantics change.

## Materialized View Rules

Use materialized views only when justified by read-heavy workloads. If using concurrent refresh, ensure unique indexes exist and understand the operational tradeoff. Do not create materialized views as a default shortcut for every expensive query.

## Avoid

- Giant mixed-purpose SQL files
- Undocumented views
- Logic duplicated in Python and SQL
- Ambiguous table names
- Silent file moves without updating docs/migration_map.md
