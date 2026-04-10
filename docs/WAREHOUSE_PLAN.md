# Warehouse Plan

## Why Normalize In Stages

Retrosheet event files are compact scorekeeping logs. Chadwick expands them into relational CSV-style outputs with official field names. We should not hand-parse Retrosheet event syntax when Chadwick can produce stable relational tables for us.

The right design is staged normalization:

1. Load source-preserved data.
2. Load Chadwick relational extracts with official headers.
3. Build typed `core` views/tables from those extracts.
4. Build ML features from `core`.
5. Bridge live MLB data into the same `core` game-state model.

## Chadwick Extracts

The warehouse uses these Chadwick procedures:

- `cwevent -q -n -y <year> -f 0-96 -x 0-62`: one row per event/play, including extended game-state fields.
- `cwgame -q -n -y <year> -f 0-83 -x 0-94`: one row per game with game metadata, scores, lineups, team totals, managers, and umpires.
- `cwdaily -q -n -y <year>`: player game-by-game batting, pitching, and fielding summaries.
- `cwsub -q -n -y <year>`: substitutions.
- `cwcomment -q -n -y <year>`: comments, ejections, and umpire changes.

These mirror the approach used by Boxball, with local adaptation for the current Chadwick Bureau Retrosheet repository layout under `seasons/<year>/`.

## Current Tables

- `raw_retrosheet.chadwick_events`: labeled event/play rows from `cwevent`.
- `raw_retrosheet.chadwick_games`: labeled game rows from `cwgame`.
- `raw_retrosheet.chadwick_daily`: labeled player-game rows from `cwdaily`.
- `raw_retrosheet.chadwick_substitutions`: labeled substitution rows from `cwsub`.
- `raw_retrosheet.chadwick_comments`: labeled comment/ejection/umpire-change rows from `cwcomment`.
- `raw_mlb.live_feed_snapshots`: source-preserved MLB live game JSON payloads.

## Next Core Tables

Build typed views or materialized tables in this order:

1. `core.games`: from `chadwick_games`.
2. `core.events`: from `chadwick_events`.
3. `core.player_game_stats`: from `chadwick_daily`.
4. `core.substitutions`: from `chadwick_substitutions`.
5. `core.event_comments`: from `chadwick_comments`.
6. `core.game_states`: event-level state rows for ML training.

## Bridge Tables

Bridge tables should connect historical Retrosheet IDs to live MLB IDs:

- `bridge.player_xref`
- `bridge.team_xref`
- `bridge.park_xref`
- `bridge.game_xref`

The player bridge should eventually ingest MLB player metadata and Chadwick/Register IDs.

## ML Feature Direction

The first ML-ready table should be event-level win probability training data:

- Current inning and half inning.
- Outs, balls, strikes.
- Score differential.
- Base state before and after event.
- Batter and pitcher IDs.
- Team IDs.
- Park.
- Event number and plate appearance indicators.
- Final game winner target from `core.games`.

Live MLB data should be transformed into the same feature columns for real-time inference.

