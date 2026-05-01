# AGENTS

## Project Mission

Refactor cbwinslow/retrosheet into a clean, extensible baseball data platform with:

- unified CLI
- layered SQL
- source adapters
- bridge/xref resolution
- sabermetric features
- ML modeling
- real-time prediction support

## Absolute Rules

- Preserve working logic before rewriting.
- Do not create orphan scripts.
- Reuse existing repo code whenever possible.
- Keep Python modular and class-based.
- Keep SQL layered and purpose-specific.
- Document file moves in docs/migration_map.md.
- Document table grains and keys in docs/keys_and_grains.md.
- MLB live feed is the primary live source; ESPN is secondary/fallback.
- Build for real-time prediction, but keep the architecture general and reusable.

## Where to Look Next

- Architecture rules: docs/agents/architecture_agent.md
- Python rules: docs/agents/python_agent.md
- SQL rules: docs/agents/sql_agent.md
- ML rules: docs/agents/ml_agent.md
- Live ingestion rules: docs/agents/live_agent.md
- Documentation rules: docs/agents/docs_agent.md

## Repo-Specific Priority

This repo already contains important working assets:

- retrosheet/ package for historical parsing
- scripts/bridge/ for xref workflows
- scripts/data_ingestion/ for live and source-specific ingestion
- scripts/external_data/ for enrichment loads
- sql/live, sql/external, sql/bridge for warehouse behavior

Wrap and reorganize these. Do not discard them casually.
