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

- Build half-inning examples and scenario simulation.
- Add cross-validation and hyperparameter tuning for model improvement.
- Bridge MLB live feed states into the same feature shape.
- Add GitHub issues for roadmap tracking.

### Added Later

- Created `core.plate_appearances`.
- Created `features.plate_appearance_examples`.
- Added plate-appearance prediction targets for all outcomes: hit, walk, strikeout, home run, reach-base, extra-base-hit.
- Extended training script to support plate appearance model training.
- Trained all plate appearance prediction models (5% sample, train through 2022):
  - **Walk**: Best ROC AUC 0.959, accuracy 0.936 (most predictable outcome)
  - **Strikeout**: Best ROC AUC 0.841, accuracy 0.779 (highly predictable)
  - **Reach Base**: Best ROC AUC 0.680, accuracy 0.721 (moderately predictable)
  - **Home Run**: Best ROC AUC 0.659, accuracy 0.969 (good accuracy, needs discrimination improvement)
  - **Extra-base Hit**: Best ROC AUC 0.642, accuracy 0.923 (good accuracy, moderate discrimination)
  - **Hit**: Best ROC AUC 0.636, accuracy 0.783 (needs most improvement)
- All models trained with both logistic regression and histogram gradient boosting algorithms.
- Gradient boosting models consistently outperform logistic regression across all targets.
- Model improvement opportunities identified for hit, extra-base hit, and home run predictions.
- Created `scripts/predict_plate_appearance.py` for model inference and real-time predictions.
- Created `scripts/analyze_pa_models.py` for comprehensive model evaluation and comparison.
- Validated plate appearance coverage:
  - `core.plate_appearances`: 4,779,662 rows, 62,598 games.
  - `features.plate_appearance_examples`: 4,779,662 rows, 62,598 games.
- Loaded Retrosheet reference metadata:
  - `raw_retrosheet.biofile`: 26,961 rows.
  - `raw_retrosheet.teams_reference`: 292 rows.
  - `raw_retrosheet.ballparks_reference`: 656 rows.
- Backfilled core metadata:
  - `core.players`: 7,165 players, 7,165 populated bats values, 7,164 populated throws values.
  - `features.plate_appearance_examples`: 4,779,662 rows with populated batter handedness and pitcher handedness.
- Retrained all active plate-appearance models after handedness enrichment (5% sample, train through 2022):
  - **Walk**: Best ROC AUC 0.959, log loss 0.121.
  - **Strikeout**: Best ROC AUC 0.840, log loss 0.353.
  - **Reach Base**: Best ROC AUC 0.678, log loss 0.565.
  - **Home Run**: Best ROC AUC 0.657, log loss 0.133.
  - **Extra-base Hit**: Best ROC AUC 0.643, log loss 0.262.
  - **Hit**: Best ROC AUC 0.637, log loss 0.501.
