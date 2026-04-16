# Issue 6 – EdgeForge Model Training Pipeline

**Goal**: Build, validate, and version the ensemble model that powers EdgeForge.

## Tasks
1. Refactor `scripts/train_edgeforge_model.py` to accept config files.
2. Add hyper‑parameter sweep (`scripts/sweep_hyperparameters.py`).
3. Store trained artifacts in `data/models/` and register them in `models.model_registry`.
4. Implement back‑testing (`scripts/edgeforge_backtest.py`) and store results in `features.backtest_results`.
5. Create a stored procedure `ml.edgeforge_predict(season int, game_id int)` that returns win probabilities.
6. Write CI tests that ensure the pipeline runs end‑to‑end on a small sample dataset.

## Definition of Done
- Model artifacts are reproducibly generated and versioned.
- Back‑test results are persisted and can be queried via a view.
- CI pipeline passes all steps.

## Links & Context
-- **Documentation**: [Next Steps](../docs/agents/next_steps.md)
-- **SQL Migration**: [MLB Data Completeness](../sql/150_mlb_data_completeness.sql)
-- **Related Issue**: #05_documentation_and_issue_linking

### Recent Update

*Added team‑game‑context features to the enriched numeric feature list in `scripts/train_models.py`.*

- **File modified**: `scripts/train_models.py`
- **Features added**: `days_since_previous_game`, `played_yesterday`, `doubleheader_same_day`, `same_park_as_previous_game`, `changed_home_road_status`, `same_opponent_as_previous_game`
- **Purpose**: Incorporate temporal context from `features.team_game_context` into the model training pipeline.

### New Back‑test View

*Created materialized view `features.backtest_results` (SQL file `sql/080_backtest_results.sql`).*

- **File added**: `sql/080_backtest_results.sql`
- **Purpose**: Joins model predictions (from `predictions.win_probabilities`) with actual outcomes in `core.games` to provide per‑game error metrics for CI back‑testing.
- **Usage**: Run `psql -f sql/080_backtest_results.sql` after the model training step to materialize the view, then query `SELECT * FROM features.backtest_results LIMIT 5;`.

These results can be used by the CI test (to be added) to verify that the model’s Brier score improves after the enriched feature set.

### CI Back‑test Workflow

*Added GitHub Actions workflow ` .github/workflows/backtest.yml` to run the model training on a sample season and verify that the `features.backtest_results` view is populated.*

- **File added**: `.github/workflows/backtest.yml`
- **Purpose**: Automated CI validation of the enriched model pipeline.

The workflow will be triggered on pushes and pull requests to the `setup-complete` branch.

---

**Status:** ✅ Completed

The hyper‑parameter sweep for the binary plate‑appearance hit model (`pa_batter_hit`) has been executed via `scripts/sweep_hyperparameters.py`. Five candidate models were trained, evaluated, and persisted under `data/models/`. Their metadata—including ROC‑AUC, log‑loss, and feature specifications—has been recorded in `models.model_registry` (see `sql/150_model_registry.sql`).

**Next actions:**
* Run the CI back‑test workflow (`.github/workflows/backtest.yml`) to ensure the `features.backtest_results` view is populated and model performance meets expectations.
* Review the top‑performing sweep candidates and activate the preferred model by setting `is_active = true` in the registry.
* Update the documentation links in `docs/agents/next_steps.md` to reflect the completed training pipeline.

These changes support the **Model Training Pipeline** task by enriching the feature set used for model training and validation.
