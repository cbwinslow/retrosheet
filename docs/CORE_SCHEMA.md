# Core Schema

The raw Chadwick tables intentionally preserve source data as text. The `core` schema is the typed, constrained layer for analytics, ML features, live-data bridging, and prediction targets.

## Tables

- `core.teams`: Retrosheet team identifiers observed in Chadwick game/event data.
- `core.parks`: Retrosheet park identifiers observed in Chadwick game data.
- `core.players`: Retrosheet player identifiers observed in events, with best-effort name, batting hand, throwing hand, and season coverage.
- `core.games`: one typed row per game with team, park, score, pitcher, date, weather, and winner fields.
- `core.events`: one typed row per event/play with game state, batter/pitcher, outcome flags, scores before/after, and plate-appearance flags.
- `core.plate_appearances`: one typed row per completed plate appearance with batter/pitcher matchup context and common PA outcome labels.
- `core.game_states`: model-friendly view joining events to games and final game outcomes.
- `features.game_outcome_examples`: materialized training examples for baseline win-probability models.
- `features.plate_appearance_examples`: materialized training examples for hit, walk, strikeout, reach-base, home-run, and extra-base-hit models.
- `raw_retrosheet.biofile`, `raw_retrosheet.teams_reference`, and `raw_retrosheet.ballparks_reference`: source-preserved Retrosheet reference metadata loaded from the cloned Retrosheet repository.

## Constraints And Indexes

- `core.games.game_id` is the primary key.
- `core.events` uses `(game_id, event_id)` as the primary key.
- `core.events.game_id` references `core.games`.
- Team, park, batter, pitcher, and pitcher-decision fields use foreign keys where source IDs are available.
- Common query paths are indexed by season/date, team/date, game sequence, game state, batter, pitcher, and plate appearance.

## Raw-To-Core Rule

Do not mutate raw Chadwick tables to make modeling easier. Add typed columns, constraints, and derived feature logic in `core`, `features`, `models`, and `predictions`.

## Refresh

After raw Chadwick tables are loaded, apply:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/010_core_games_events.sql
psql -h localhost -p 5432 -d retrosheet -f sql/020_plate_appearances.sql
python3 scripts/load_reference_metadata.py
```

Then refresh the materialized feature table after future core changes:

```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY features.game_outcome_examples;
```
