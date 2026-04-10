# Web Command Center Design

This project now uses a Next.js command center as the primary interface for model steering, simulation, backtesting, and warehouse exploration.

## Current Implementation

The interface lives in `baseball-chatbot-ui/` and runs against the local PostgreSQL warehouse on `localhost:5432/retrosheet` by default.

Primary views:

- `Chat Analyst`: asks the warehouse questions through curated tool routes and returns narrative answers plus tables.
- `Sim Lab`: filters historical half-inning situations and summarizes run distributions, expected runs, and specialized scenarios such as all left-handed batters recording hits.
- `Models & Backtests`: surfaces active model registrations, validation metrics, sweep candidates, and player/pitcher production leaderboards.
- `Workbench`: provides safe buttons for common local workflows without exposing raw shell access in the browser.

API route boundary:

- `/api/status`: warehouse validation summaries, ingest counts, active model snapshot.
- `/api/analytics`: active model metrics and production leaderboards.
- `/api/backtests`: registry overview, leaderboard, and sweep candidates.
- `/api/chat`: local tool-routed assistant response.
- `/api/simulate`: historical scenario simulation from feature marts.
- `/api/simulation-runs`: recent saved simulation runs for reproducible model-room workflows.
- `/api/terminal`: allow-listed workflow commands.
- `/api/predict`: plate-appearance prediction script bridge.
- `/api/live-odds`: placeholder dashboard feed until true live odds/markets are integrated.

## Spreadsheet Strategy

Start with exportable tables. This keeps the interface useful immediately without building a fragile spreadsheet clone too early.

Recommended progression:

1. Render API results in consistent tables with CSV export.
2. Add saved query presets for recurring analysis views.
3. Add a dedicated grid component for richer sorting, filtering, grouping, and pinning.
4. Add controlled imports/write-backs only after authentication, audit logging, and schema validation exist.

Reasonable grid candidates later are AG Grid Community, Glide Data Grid, and Handsontable. The first two are better fits for analysis-heavy read workflows; Handsontable is more spreadsheet-like if editing becomes important.

## Terminal Strategy

Do not expose a raw shell through the web app by default. The current approach is intentionally safer:

1. The user clicks a named workflow action.
2. The API route validates that the action is allow-listed.
3. The backend runs one known command from the project root.
4. The UI displays captured stdout, stderr, and exit code.

A true embedded terminal is possible later with `node-pty`, `xterm.js`, and WebSockets, but it should only be added with authentication, session expiration, command restrictions, and project-root isolation.

## Next Interface Milestones

- Add provider-backed LLM tool calling through OpenRouter, Groq, and Codex/OpenAI-compatible providers.
- Expand persisted chat sessions beyond first-pass `chat.query_logs` records.
- Add saved simulation runs and named backtest reports.
- Add calibration plots, rolling-origin backtests, and model comparison cards.
- Add a live-game bridge panel once MLB Stats API ingestion is wired into the same core event shape.
- Add market comparison panels only after odds/market ingestion tables are normalized and timestamped.
