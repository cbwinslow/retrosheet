# Procedures

These are the canonical workflows. Use them before creating new ad hoc scripts.

## Full Warehouse Rebuild

Purpose: recreate the historical warehouse and feature layers from source data.

Command:

```bash
YEARS=2000-2025 PGDATABASE=retrosheet scripts/rebuild_warehouse.sh
```

Expected order:

1. Check Chadwick dependencies.
2. Fetch Retrosheet archives.
3. Initialize schemas.
4. Extract Chadwick outputs with headers.
5. Load raw Chadwick tables.
6. Build `core.games` and `core.events`.
7. Build `core.plate_appearances`.
8. Load reference metadata.
9. Load auxiliary metadata.
10. Build feature marts.
11. Build interface persistence.
12. Build multiclass PA outcome examples.

When adding a required SQL migration, add it to `scripts/rebuild_warehouse.sh` and document it in `README.md`.

## Add A New Prediction Target

Purpose: add a precise target that can be trained, scored, logged, and explained.

Steps:

1. Define the target in words first.
2. Identify the label source in `core` or `features`.
3. Add or update a `features.*_examples` view/materialized view.
4. Insert a row into `predictions.prediction_targets`.
5. Add training support to the right trainer.
6. Add validation counts.
7. Add model registry output.
8. Update `docs/agents/MODELING_WORKFLOWS.md`.

Do not add ambiguous targets such as “left-handed batters get hits” without a settlement rule.

## Add A Feature Mart

Purpose: add reusable feature columns without leaking future information.

Rules:

- Keep raw source rows unchanged.
- Put reusable ML features under `features`.
- Prefer materialized views when joins are expensive and rows are stable.
- Add indexes for target/training joins.
- Name season-forward features as `feature_season = source_season + 1` when using prior-season summaries.
- For rolling features, use windows ending before the current event/game.
- Document leakage assumptions.

## Train Binary Game/PA Models

Use `scripts/train_models.py`.

Examples:

```bash
python3 scripts/train_models.py --target-id game_home_win --feature-set advanced --sample-rate 0.10 --train-through 2022
python3 scripts/train_models.py --target-id pa_batter_hit --feature-set advanced --sample-rate 0.05 --train-through 2022
```

Outputs:

- Serialized model under ignored `data/models/`.
- Registry row in `models.model_registry`.
- Metrics JSON in `models.model_registry.metrics`.

Promotion:

```bash
python3 scripts/promote_best_models.py --target-prefix 'pa_%' --min-validation-rows 10000
```

Do not hand-edit `models.model_registry.is_active`.

## Train Multiclass PA Outcome Distribution

Use `scripts/train_pa_outcome_distribution.py`.

Example:

```bash
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.05 --train-through 2022
```

Target:

- `pa_outcome_distribution`

Feature source:

- `features.plate_appearance_outcome_examples`
- `features.plate_appearance_advanced_examples` for advanced features

Evaluation priority:

1. Log loss.
2. Calibration / reliability by class.
3. Brier score.
4. Top-k accuracy.
5. Macro/weighted F1 as secondary diagnostics.

Do not promote this model until calibration reporting exists.

## Build Scenario Simulations

Current baseline:

- Historical lookup through `features.half_inning_outcome_summary`.
- Saved runs in `predictions.simulation_runs`.

Future model-driven procedure:

1. Score each simulated PA with `pa_outcome_distribution`.
2. Sample terminal PA outcome.
3. Apply correct base/out/run transition.
4. Stop at three outs.
5. Repeat for bounded simulation count.
6. Save filters, model versions, run distribution, summary, and assumptions.

Critical warning: incorrect baseball state transitions make simulation results look precise and wrong. Prefer fewer classes or slower code over incorrect state updates.

## Add Live MLB Bridge Work

Purpose: transform live MLB data into the same canonical shapes as Retrosheet history.

Procedure:

1. Store raw payload in `raw_mlb.live_feed_snapshots`.
2. Map MLB IDs to Retrosheet IDs through `bridge`.
3. Transform live game/play state into `core.live_games` and `core.live_events`.
4. Build live feature rows with the same columns used by historical training.
5. Score with active registered models.
6. Store predictions with model ID, timestamp, and input features.

Do not score raw MLB JSON directly in production paths.

## Update Web Command Center

Purpose: expose warehouse/model workflows safely.

Rules:

- Use API routes as the only browser-to-backend boundary.
- Query curated views or call allow-listed scripts.
- Do not expose arbitrary shell.
- Do not expose arbitrary SQL writes.
- Persist meaningful chat/simulation/backtest workflows.
- Run `npm run build` before committing.

## Create Or Update GitHub Issues

Use issues as durable project records.

Each issue should include:

- Goal.
- Current state.
- Scope.
- Non-goals.
- Acceptance criteria.
- Relevant files/tables.
- Validation expectations.
- Parent roadmap issue if applicable.

Comment on existing parent issues when work advances a goal.
