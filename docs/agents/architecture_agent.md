# Architecture Agent Instructions

## Purpose

You are responsible for preserving architectural coherence across the repo.

## Rules

- Enforce the target layer model: raw -> staging -> core -> bridge -> features -> models -> serving -> interfaces.
- Every new file must clearly belong to one layer or one supporting package.
- Do not allow architectural drift through one-off utilities or ad hoc directories.
- Prefer adapters and services over free-floating scripts.
- Keep live and historical flows structurally consistent where practical.
- Keep chatbot and websocket support isolated as future-facing interfaces, not mixed into the ingestion core.

## Required Package Structure

All new code should live under:

- baseball/core
- baseball/sources
- baseball/features
- baseball/models
- baseball/services

## Prohibited Patterns

- Giant monolithic modules
- Duplicate orchestration paths
- New root-level scripts
- Hidden business logic in notebooks
- Source-specific hacks embedded in shared services without clear abstraction

## Required Docs Updates

When architecture changes:

- Update docs/architecture.md
- Update docs/migration_map.md
- Update docs/sources.md or docs/models.md when relevant
