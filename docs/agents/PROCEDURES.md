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
13. Build pitch-sequence normalization examples.

When adding a required SQL migration, add it to `scripts/rebuild_warehouse.sh` and document it in `README.md`.

## Live Data Ingestion

Purpose: ingest real-time MLB game data alongside historical Retrosheet data.

### One-Time Setup (Bridge Tables)

Command:

```bash
python3 scripts/populate_bridge_tables.py
```

Expected order:

1. Download Chadwick Bureau Register CSV files.
2. Parse player and team ID mappings.
3. Populate `bridge.player_xref` with MLB ↔ Retrosheet ID mappings.
4. Populate `bridge.team_xref` with team ID mappings.
5. Create indexes for fast lookups.

### Ongoing Live Data Ingestion

Command:

```bash
python3 scripts/fetch_mlb_schedule.py --yesterday
python3 scripts/ingest_live_games.py --schedule
```

Expected order:

1. Query MLB Stats API for recent game schedules.
2. Identify active/completed games for ingestion.
3. For each game:
   - Fetch live game feed JSON from MLB API.
   - Store source-preserved JSON plus request/status/checksum provenance in `raw_mlb.live_feed_snapshots`.
   - Transform the latest stored snapshot to canonical live schema using bridge table lookups.
   - Upsert into `core.live_games` and `core.live_events`.
4. Refresh `analysis.combined_plate_appearances` when live rows change and downstream combined PA analysis depends on current live state.

### Analysis with Combined Data

Use `analysis.*` views for unified queries across historical and live data:

```sql
-- Check data source statistics
SELECT * FROM analysis.get_data_source_stats();

-- Query combined games
SELECT * FROM analysis.combined_games
WHERE game_date >= CURRENT_DATE - INTERVAL '7 days';

-- Query combined events
SELECT ce.*
FROM analysis.combined_events ce
JOIN analysis.combined_games cg USING (game_id)
WHERE ce.source_type = 'mlb_live';
```

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
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.05 --train-through 2022 --no-activate
```

Temporal-policy examples:

```bash
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.05 --train-through 2022 --recent-window 7 --no-activate
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.05 --train-through 2022 --season-half-life 5 --downweight-2020 0.5 --no-activate
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

Scoring:

```bash
python3 scripts/predict_pa_outcome_distribution.py --game-id ANA202506060 --plate-appearance-id 30
```

The scorer returns class probabilities plus derived aggregates such as hit, extra-base hit, traditional on-base, reach-base-any, ball-in-play, and expected total bases. API consumers can request the same path through `/api/predict` with `target_id: "pa_outcome_distribution"`.

## Normalize Pitch Sequences

Purpose: preserve Retrosheet `pitch_seq_tx` at one-row-per-symbol granularity without inventing a separate raw parsing pipeline.

Command:

```bash
psql -h localhost -p 5432 -d retrosheet -v ON_ERROR_STOP=1 -f sql/077_pitch_sequence_model.sql
```

Outputs:

- `features.pitch_sequence_symbol_reference`
- `features.pitch_sequence_examples`
- `features.pitch_sequence_validation_summary`

Use this layer before attempting same-PA temporal features or any direct next-pitch model. It preserves official Retrosheet pitch-sequence symbols, coarse symbol groupings, and terminal-pitch flags while staying anchored to `features.plate_appearance_outcome_examples`.

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

1. Store raw payload in `raw_mlb.live_feed_snapshots` with fetch provenance.
2. Map MLB IDs to Retrosheet IDs through `bridge`.
3. Transform live game/play state into `core.live_games` and `core.live_events` by upsert, not destructive table replacement.
4. Preserve `raw_payload` and `raw_play` in the canonical live layer for replay/debugging.
5. Build live feature rows with the same columns used by historical training.
6. Score with active registered models.
7. Store predictions with model ID, timestamp, and input features.

Do not score raw MLB JSON directly in production paths.
Do not merge raw MLB rows into historical raw layers. Historical/live combination belongs in `analysis.*` views/materialized views and later feature-parity views.

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
