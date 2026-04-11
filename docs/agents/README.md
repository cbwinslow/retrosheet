# Agent Knowledge Map

This folder is the durable project map for humans and AI agents. Read these files before creating new SQL, scripts, models, or interface routes.

## Routing

- `PROJECT_OBJECTIVES.md`: what the prediction engine is trying to accomplish and which modeling goals matter.
- `FILE_INVENTORY.md`: what each major file/script/migration/view is for, grouped by purpose.
- `PROCEDURES.md`: canonical workflows for rebuilding data, adding features, training models, and updating the interface.
- `MODELING_WORKFLOWS.md`: model families, target definitions, feature sources, evaluation expectations, and next-model priorities.
- `RESEARCH_METHODOLOGY.md`: CRISP-DM framing, math notation, objective functions, and modeling assumptions.
- `TEMPORAL_MODEL_SELECTION.md`: recency weighting, era features, fixed-window benchmarks, and the model-selection procedure for non-stationary seasons.
- `FEATURE_AUDIT.md`: which fields/features are trusted now, which are only preserved raw, and where feature work still beats hyperparameter work.

## Operating Rule

Before adding a new file, first check whether one of these already owns the job:

- Warehouse ingestion and Chadwick extraction: `scripts/warehouse.py`
- Canonical rebuild order: `scripts/rebuild_warehouse.sh`
- Core historical schema: `sql/010_core_games_events.sql`, `sql/020_plate_appearances.sql`
- Feature marts: `sql/050_feature_marts.sql`, `sql/060_advanced_feature_marts.sql`, `sql/070_temporal_and_production_marts.sql`, `sql/076_plate_appearance_outcome_model.sql`
- General binary model training: `scripts/train_models.py`
- Multiclass at-bat outcome training: `scripts/train_pa_outcome_distribution.py`
- Multiclass at-bat outcome scoring: `scripts/predict_pa_outcome_distribution.py`
- Model promotion: `scripts/promote_best_models.py`
- Live MLB ingestion and canonical transform: `scripts/warehouse.py`, `scripts/ingest_live_games.py`, `scripts/transform_live_game.py`
- Web command center: `baseball-chatbot-ui/`

If none of those fits, add the new file and update `FILE_INVENTORY.md` in the same change.
