# Live Agent Instructions

## Purpose

Handle real-time and near-real-time baseball ingestion and prediction workflows.

## Source Priority

- MLB Stats API live feed is primary
- ESPN is secondary/fallback

## Live Ingestion Rules

Every live ingest cycle should:
- Fetch raw payloads
- Persist raw payloads
- Identify changed events if possible
- Update canonical live tables
- Update live features
- Trigger model scoring when needed
- Persist outputs

## Required Canonical Live Tables

- core.live_games
- core.live_events
- core.live_pitch_events
- core.live_plate_appearances
- core.game_state_snapshots

## Performance Rules

- Minimize unnecessary full reprocessing.
- Support checkpointing and incremental updates.
- Favor predictable low-latency reads in serving tables.
- Keep websocket future compatibility in mind.

## Avoid

- Making ESPN the only live truth
- Rebuilding the entire warehouse for every live poll
- Mixing live serving logic directly into raw ingestion code
