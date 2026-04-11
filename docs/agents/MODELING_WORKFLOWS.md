# Modeling Workflows

## Model Inventory

| Target | Family | Trainer | Feature Source | Status |
|---|---|---|---|---|
| `game_home_win` | Game outcome | `scripts/train_models.py` | `features.game_outcome_examples`, `features.game_outcome_advanced_examples`, `features.game_outcome_temporal_examples` | Active baseline and enriched/advanced candidates exist. |
| `pa_batter_hit` | Binary PA | `scripts/train_models.py` | `features.plate_appearance_examples`, `features.plate_appearance_advanced_examples` | Active binary PA model family. |
| `pa_batter_walk` | Binary PA | `scripts/train_models.py` | Same PA feature sources | Strong current binary target. |
| `pa_batter_strikeout` | Binary PA | `scripts/train_models.py` | Same PA feature sources | Strong current binary target. |
| `pa_batter_home_run` | Binary PA | `scripts/train_models.py` | Same PA feature sources | Rare-event target; calibration matters. |
| `pa_batter_reach_base` | Binary PA | `scripts/train_models.py` | Same PA feature sources | Useful aggregate target. |
| `pa_batter_extra_base_hit` | Binary PA | `scripts/train_models.py` | Same PA feature sources | Rare-ish aggregate target. |
| `pa_outcome_distribution` | Multiclass PA | `scripts/train_pa_outcome_distribution.py` | `features.plate_appearance_outcome_examples`, advanced PA view | Inactive 5% advanced candidate exists; needs calibration/subgroup diagnostics before promotion. |
| `half_inning_any_run` | Scenario | `scripts/train_models.py` where `features.half_inning_examples` exists | Half-inning examples | Candidate target. |
| `half_inning_lhb_any_hit` | Scenario | `scripts/train_models.py` where `features.half_inning_examples` exists | Half-inning examples | Candidate target; target definition must be precise. |

## Current Production-Oriented Workflow

1. Build warehouse and feature marts.
2. Train binary target candidates with `scripts/train_models.py`.
3. Register artifacts in `models.model_registry`.
4. Promote using `scripts/promote_best_models.py`.
5. Score known historical PAs with `scripts/predict_plate_appearance.py` and `scripts/predict_pa_outcome_distribution.py`.
6. Expose model registry and scenario baselines in the web command center.

## Near-Term Modeling Roadmap

### Temporal Policy

The project should treat season history as non-stationary. Use [docs/TEMPORAL_MODEL_SELECTION.md](../TEMPORAL_MODEL_SELECTION.md) as the canonical policy for:

- recent-window benchmarks
- exponential season weighting
- explicit era indicators
- `2023-2025` out-of-time validation for choosing the best policy

Do not assume that equal weighting from `2000-2025` is the correct default.

### Priority 1: Multiclass PA Outcome Model

Why it matters:

- It produces a coherent probability distribution over terminal PA outcomes.
- It supports derived probabilities like hit, extra-base hit, on-base, ball-in-play, and expected total bases.
- It is the clean foundation for Monte Carlo simulation.

Use:

```bash
psql -h localhost -p 5432 -d retrosheet -f sql/076_plate_appearance_outcome_model.sql
python3 scripts/train_pa_outcome_distribution.py --feature-set advanced --sample-rate 0.05 --train-through 2022 --no-activate
```

Do before promotion:

- Larger advanced-feature training run beyond the current 5% inactive benchmark.
- Calibration curves per class.
- Log-loss comparison against empirical baselines.
- Subgroup metrics by count, base/out state, handedness matchup, and season.
- Rare-class policy for outcomes like interference, or a larger/full sample that keeps all classes.
- Model card.

### Priority 2: Calibration And Backtest Reports

Why it matters:

- Moneyball-style decisions need reliable probabilities, not just high accuracy.
- Rare outcomes like triple, HBP, and interference can produce misleading confidence.

Needed assets:

- Backtest report tables.
- Calibration bins.
- Reliability plots.
- Rolling-origin validation.
- Report UI in command center.

### Priority 3: Model-Driven Half-Inning Monte Carlo

Why it matters:

- Scenario questions are central to the product.
- Historical distributions are useful but cannot handle arbitrary live game states.

Recommended source model:

- Start with `pa_outcome_distribution`.
- Fall back to binary PA models only for aggregate scenario questions.

### Priority 4: Pitch-Level Model

Why it matters:

- It can answer next-pitch questions and recursively simulate count transitions.

Why not first:

- `features.pitch_sequence_examples` now normalizes `pitch_seq_tx` into one row per Retrosheet sequence symbol, but not every intermediate count transition has been validated yet.
- Same-PA temporal state reconstruction and pitch-level transition logic still need careful validation.
- Direct PA outcome modeling is simpler and useful sooner.

## Moneyball-Style Modeling Goals

These are common analytical goals the engine should eventually support:

- Estimate true player talent independent of noisy small samples.
- Quantify platoon advantages by batter/pitcher handedness.
- Identify undervalued skills such as walks, contact, strikeout avoidance, and power.
- Estimate run expectancy changes by base/out/count state.
- Estimate win probability from game state.
- Simulate lineup, bullpen, and pinch-hit decisions.
- Compare current market prices to calibrated model probabilities.
- Detect when public prices overreact to recent events.
- Explain which features moved a probability estimate.

## Leakage Checklist

Apply this before trusting a model:

- Prior-season features do not include the target season.
- Career-prior features only include seasons before the feature season.
- Rolling features end before the current game or event.
- Same-game features only include prior events.
- Matchup features exclude the current PA.
- Target encodings, if added, are fold-aware.
- Test seasons are strictly after training seasons.
- Raw event text is not used as a predictive feature when it encodes the outcome.

## Promotion Rules

Do not promote a model unless:

- Validation rows are large enough for the target.
- Metrics beat a documented baseline.
- Calibration is acceptable for the intended use.
- Feature spec is stored in `models.model_registry`.
- Artifact path is under ignored `data/models/`.
- The model can be regenerated from scripts and warehouse state.

For production-like use, promotion must be through `scripts/promote_best_models.py` or a documented successor.
