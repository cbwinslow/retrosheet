# Docs Agent Instructions

## Purpose

Keep repo documentation accurate, operational, and useful to both humans and coding agents.

## Rules

- Write docs imperatively and operationally.
- Do not repeat large amounts of README content unnecessarily.
- Update docs when code structure or file locations change.
- Keep migration docs current during refactor.
- Keep AGENTS docs concise and modular.

## Required Doc Updates

When relevant, update:
- docs/architecture.md
- docs/sources.md
- docs/keys_and_grains.md
- docs/migration_map.md
- docs/models.md

## AGENTS Strategy

Keep AGENTS.md short. Put specialized instructions in docs/agents/*.md, since nested or grouped agent guidance scales better for large repos.
