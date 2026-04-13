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
- **Documentation**: [Next Steps](../docs/agents/next_steps.md)
- **SQL Migration**: [MLB Data Completeness](../sql/150_mlb_data_completeness.sql)
- **Related Issue**: #05_documentation_and_issue_linking