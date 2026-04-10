# Project Log

## 2026-04-10

### Built

- Created a reproducible PostgreSQL-first Retrosheet warehouse project.
- Installed/validated Chadwick CLI usage through project scripts.
- Loaded Retrosheet/Chadwick seasons 2000-2025 into `raw_retrosheet`.
- Created source-preserved Chadwick tables:
  - `raw_retrosheet.chadwick_events`
  - `raw_retrosheet.chadwick_games`
  - `raw_retrosheet.chadwick_daily`
  - `raw_retrosheet.chadwick_substitutions`
  - `raw_retrosheet.chadwick_comments`
- Created typed `core` tables:
  - `core.teams`
  - `core.parks`
  - `core.players`
  - `core.games`
  - `core.events`
- Created model-ready feature seed:
  - `features.game_outcome_examples`
- Created modeling, prediction, market, and chat metadata schemas/tables.
- Seeded initial reusable prediction targets.
- Added first ML training script for game-home-win models.
- Added OpenRouter, Groq, and Codex/OpenAI-compatible provider configuration scaffolding.

### Validation

- `raw_retrosheet.chadwick_events`: 4,933,687 rows, 62,598 games.
- `raw_retrosheet.chadwick_games`: 62,598 rows, 62,598 games.
- `core.games`: 62,598 rows, 62,598 games.
- `core.events`: 4,933,687 rows, 62,598 games.
- `features.game_outcome_examples`: 4,779,034 rows, 62,589 games.
- `core.events` has validated primary key, check constraints, and foreign keys.

### Next

- Train plate-appearance models for hit, reach-base, strikeout, walk, home run, and extra-base hit.
- Build half-inning examples and scenario simulation.
- Bridge MLB live feed states into the same feature shape.
- Add GitHub issues for roadmap tracking.

### Added Later

- Created `core.plate_appearances`.
- Created `features.plate_appearance_examples`.
- Added plate-appearance prediction targets for reach-base and extra-base-hit.
- Validated plate appearance coverage:
  - `core.plate_appearances`: 4,779,662 rows, 62,598 games.
  - `features.plate_appearance_examples`: 4,779,662 rows, 62,598 games.
