# MLB Live Data Ingestion Architecture & Procedures

Current rule set:

- Keep MLB payloads source-preserved in `raw_mlb.live_feed_snapshots`.
- Keep ID reconciliation in `bridge.*`.
- Upsert canonical live state into `core.live_games` and `core.live_events`.
- Preserve `raw_payload` and `raw_play` in the canonical live layer for replay/debugging.
- Combine historical and live data in `analysis.*` views/materialized views, not by merging raw layers.

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DATA SOURCES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐         │
│  │   RETROSHEET    │    │      MLB LIVE     │    │    ANALYSIS     │         │
│  │   (Historical)  │    │    (Real-time)    │    │   (Combined)    │         │
│  └─────────────────┘    └──────────────────┘    └─────────────────┘         │
│           │                        │                        │              │
│           ▼                        ▼                        ▼              │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐         │
│  │ raw_retrosheet.*│    │ raw_mlb.live_feed│    │   analysis.*    │         │
│  │   (Raw files)   │    │  _snapshots       │    │   views/tables  │         │
│  └─────────────────┘    │   (JSON API)      │    └─────────────────┘         │
│           │             └──────────────────┘             │                  │
│           ▼                        │                     │                  │
│  ┌─────────────────┐    ┌──────────────────┐             │                  │
│  │ core.games      │    │ live.games       │             │                  │
│  │ core.events     │    │ live.events      │             │                  │
│  │ core.players    │    └──────────────────┘             │                  │
│  │ core.teams      │             │                        │                  │
│  │ core.parks      │             │                        │                  │
│  └─────────────────┘             │                        │                  │
│           │                        │                        │                  │
│           └────────────────────────┼────────────────────────┘                  │
│                                 ▼                                             │
│                    ┌──────────────────┐                                       │
│                    │   bridge.*       │                                       │
│                    │  (ID mapping)    │                                       │
│                    └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Detailed Ingestion Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LIVE DATA INGESTION PIPELINE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  Schedule   │───▶│   Fetch    │───▶│ Transform  │───▶│   Store     │     │
│  │ Discovery   │    │ Live Game  │    │   Data     │    │   Results   │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                                             │
│  Command:                                                                   │
│  python3 scripts/fetch_mlb_schedule.py --yesterday                          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                    ACTIVE GAMES FOUND                               │     │
│  │  ⚫ 823884: Cincinnati Reds @ Miami Marlins (1-8)                  │     │
│  │  ⚫ 823565: Athletics @ New York Yankees (1-0)                     │     │
│  │  🔴 823724: Detroit Tigers @ Minnesota Twins (1-3)                │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                      │
│  │Fetch Game   │───▶│Store Raw   │───▶│Transform   │                      │
│  │Feed JSON    │    │JSON in DB  │    │to Schema   │                      │
│  └─────────────┘    └─────────────┘    └─────────────┘                      │
│                                                                             │
│  Command:                                                                   │
│  python3 scripts/warehouse.py fetch-live-game --game-pk 823884             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                    RAW DATA STORAGE                                │     │
│  │  INSERT INTO raw_mlb.live_feed_snapshots (game_pk, payload)        │     │
│  │  VALUES (823884, '{...MLB API JSON...}')                          │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │Parse JSON   │───▶│Map IDs     │───▶│Normalize   │───▶│Store in     │     │
│  │Extract      │    │via Bridge  │    │Schema      │    │core.live_* │     │
│  │Events       │    │Tables      │    │            │    │Tables       │     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                                             │
│  Command:                                                                   │
│  python3 scripts/transform_live_game.py --game-pk 823884                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                    NORMALIZED STORAGE                              │     │
│  │  INSERT INTO core.live_games (game_id, season, ...)               │     │
│  │  INSERT INTO core.live_events (game_id, event_id, ...)            │     │
│  │  Player IDs: MLB IDs → Retrosheet IDs via bridge.player_xref     │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## ML Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ML TRAINING & PREDICTION                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐           │
│  │   Historical    │    │   Live Data     │    │   Combined      │           │
│  │   Training      │    │   Inference     │    │   Analysis      │           │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘           │
│           │                        │                        │              │
│           ▼                        ▼                        ▼              │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐         │
│  │ core.games      │    │ core.live_games  │    │ analysis.views  │         │
│  │ core.events     │    │ core.live_events │    │                 │         │
│  └─────────────────┘    └──────────────────┘    └─────────────────┘         │
│           │                        │                        │              │
│           ▼                        ▼                        ▼              │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐         │
│  │ features.*      │    │  features.*      │    │   features.*    │         │
│  │ (materialized)  │    │  (computed)      │    │   (combined)    │         │
│  └─────────────────┘    └──────────────────┘    └─────────────────┘         │
│           │                        │                        │              │
│           ▼                        ▼                        ▼              │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐         │
│  │  Train Models   │    │   Load Models    │    │   Load Models   │         │
│  │  (Historical)   │    │   (Pre-trained)  │    │   (Pre-trained)  │         │
│  └─────────────────┘    └──────────────────┘    └─────────────────┘         │
│           │                        │                        │              │
│           ▼                        ▼                        ▼              │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐         │
│  │ Model Registry  │    │   Predictions    │    │   Analysis      │         │
│  │ (models.model_  │    │   (predictions.  │    │   (predictions. │         │
│  │   registry)     │    │     live_preds)  │    │     analysis)   │         │
│  └─────────────────┘    └──────────────────┘    └─────────────────┘         │
│                                                                             │
│  Commands:                                                                  │
│  python3 scripts/train_models.py --feature-set enriched                    │
│  python3 scripts/train_live_models.py --model win_probability              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Bridge Table Population Process

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      BRIDGE TABLE POPULATION                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐           │
│  │  Download       │───▶│   Parse CSV     │───▶│   Insert into   │           │
│  │  Chadwick       │    │   Records       │    │   Database      │           │
│  │  Register       │    │                 │    │                 │           │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘           │
│                                                                             │
│  Command:                                                                   │
│  python3 scripts/populate_bridge_tables.py                                 │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                 CHADWICK REGISTER STRUCTURE                         │     │
│  │  key_person: UUID identifier                                        │     │
│  │  key_mlbam: MLB Advanced Media ID                                   │     │
│  │  key_retro: Retrosheet player ID                                    │     │
│  │  key_bbref: Baseball Reference ID                                   │     │
│  │  key_fangraphs: FanGraphs ID                                        │     │
│  │  name_first, name_last: Player names                                │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                   BRIDGE TABLE MAPPINGS                             │     │
│  │  bridge.player_xref:                                               │     │
│  │    - retrosheet_id → Retrosheet player ID                           │     │
│  │    - mlb_id → MLB API player ID                                     │     │
│  │    - baseball_reference_id → BBRef ID                               │     │
│  │    - name_first, name_last → Player names                           │     │
│  │                                                                     │     │
│  │  bridge.team_xref:                                                 │     │
│  │    - retrosheet_team_id → Retrosheet team ID                        │     │
│  │    - mlb_team_id → MLB API team ID                                  │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Analysis Layer Usage

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ANALYSIS QUERIES                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  -- Get data source statistics                                             │
│  SELECT * FROM analysis.get_data_source_stats();                          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                SAMPLE OUTPUT                                        │     │
│  │ data_source | games_count | events_count | latest_game_date         │     │
│  │ ────────────┼─────────────┼──────────────┼─────────────────         │     │
│  │ historical  |       62598 |      4933687 | 2025-11-01               │     │
│  │ live        |           1 |           79 | 2026-04-09               │     │
│  │ combined    |       62599 |      4933766 | 2026-04-09               │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  -- Query combined games across all sources                                │
│  SELECT * FROM analysis.combined_games                                    │
│  WHERE game_date >= CURRENT_DATE - INTERVAL '7 days';                     │
│                                                                             │
│  -- Query combined events with player info                                 │
│  SELECT ce.*, p.name_first, p.name_last                                   │
│  FROM analysis.combined_events ce                                         │
│  LEFT JOIN core.players p ON ce.batter_id = p.retrosheet_player_id;       │
│                                                                             │
│  -- Get recent games from both sources                                     │
│  SELECT * FROM analysis.get_recent_games(7);                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Complete Workflow Summary

```
WAREHOUSE REBUILD (Historical + Live Setup):
1. python3 scripts/warehouse.py check-deps
2. python3 scripts/warehouse.py fetch-retrosheet
3. python3 scripts/warehouse.py init-db
4. python3 scripts/warehouse.py extract-chadwick --years 2000-2025 --outputs all
5. python3 scripts/warehouse.py load-chadwick --years 2000-2025 --outputs all
6. python3 scripts/populate_bridge_tables.py
7. psql -f sql/130_analysis_views.sql

LIVE DATA INGESTION (Ongoing):
1. python3 scripts/fetch_mlb_schedule.py --yesterday
2. python3 scripts/ingest_live_games.py --schedule
3. SELECT * FROM analysis.get_data_source_stats();

ML MODEL TRAINING:
1. python3 scripts/train_models.py --feature-set enriched
2. python3 scripts/promote_best_models.py

LIVE PREDICTIONS:
1. Load pre-trained models
2. Query live game states from analysis.combined_games
3. Generate predictions
4. Store in predictions.live_preds
```
