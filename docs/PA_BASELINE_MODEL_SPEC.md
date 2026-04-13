# Baseline Plate Appearance Model Specification

This document defines the first production-grade plate appearance modeling layer for the warehouse.

The objective is to estimate a calibrated probability distribution over plate appearance outcomes using the historical Retrosheet warehouse first, then reuse the same feature contract for live MLB inference.

## Objective

For each completed plate appearance \(i\), define a state vector \(X_i\) available before the terminal event and estimate:

\[
P(Y_i = k \mid X_i), \quad k \in \mathcal{K}
\]

where \(Y_i\) is the terminal plate appearance outcome class.

The first model should optimize multiclass log loss:

\[
\mathcal{L}(\theta) = -\sum_{i=1}^{n}\sum_{k=1}^{K}\mathbf{1}(Y_i=k)\log \hat{p}_{ik}
\]

Derived probabilities and expectations are then computed from the granular class probabilities, not trained as separate primary targets.

Examples:

\[
P(\text{hit}) = P(1B) + P(2B) + P(3B) + P(HR)
\]

\[
P(\text{on\_base\_traditional}) = P(1B)+P(2B)+P(3B)+P(HR)+P(BB)+P(HBP)
\]

\[
E(\text{total bases}) = 1P(1B)+2P(2B)+3P(3B)+4P(HR)
\]

## Current Warehouse Reality

The existing canonical training source is:

- `features.plate_appearance_outcome_examples`

Current validated coverage:

- seasons: `2000-2025`
- rows: `4,779,662`
- exact join coverage to `features.plate_appearance_advanced_examples`: `4,779,662`
- pitch-sequence coverage: `4,779,662 / 4,779,662`
- batted-ball type coverage: `3,372,283 / 4,779,662`
- batted-ball location coverage: `3,277,405 / 4,779,662`

Current class counts:

| Outcome class | Rows |
|---|---:|
| `ground_out` | 1,082,774 |
| `strikeout` | 937,040 |
| `fly_out` | 729,713 |
| `single` | 716,788 |
| `walk` | 375,676 |
| `double` | 217,565 |
| `line_out` | 203,821 |
| `pop_out` | 167,551 |
| `home_run` | 136,691 |
| `hit_by_pitch` | 46,050 |
| `error_on_batter` | 38,341 |
| `sacrifice_fly` | 33,214 |
| `sacrifice_hit` | 31,621 |
| `intentional_walk` | 26,755 |
| `triple` | 21,635 |
| `fielders_choice` | 13,438 |
| `interference` | 989 |

## Recommended Label Strategy

The warehouse should preserve the full raw outcome taxonomy, but the first operational model should use a grouped modeling taxonomy for stability.

### Raw canonical taxonomy

Keep the current granular classes from `features.plate_appearance_outcome_examples`:

- `single`
- `double`
- `triple`
- `home_run`
- `walk`
- `intentional_walk`
- `hit_by_pitch`
- `strikeout`
- `ground_out`
- `fly_out`
- `line_out`
- `pop_out`
- `fielders_choice`
- `error_on_batter`
- `sacrifice_hit`
- `sacrifice_fly`
- `interference`
- `other`

### Baseline modeling taxonomy (v1)

For the first stable model, train on these grouped classes:

- `single`
- `double`
- `triple`
- `home_run`
- `walk`
- `hit_by_pitch`
- `strikeout`
- `ground_out`
- `air_out`
- `reach_on_error_or_fc`
- `productive_out`
- `other_rare`

where:

- `air_out = fly_out + line_out + pop_out`
- `reach_on_error_or_fc = error_on_batter + fielders_choice`
- `productive_out = sacrifice_hit + sacrifice_fly`
- `other_rare = intentional_walk + interference + other`

This keeps the model multiclass and interpretable while reducing instability from very sparse classes.

## Baseline Feature Contract

The baseline model should use only features available before the PA resolves.

### Core state features

These should be treated as required in every PA model:

- `inning`
- `is_bottom_inning`
- `outs_before`
- `start_bases`
- `balls`
- `strikes`
- `home_score_diff`
- `batter_hand`
- `pitcher_hand`
- `season_era`
- `rules_context_era`

These already exist in `features.plate_appearance_outcome_examples`.

### Baseline advanced features

These should form the first reusable predictive layer:

- batter career-prior volume and rate features
- pitcher career-prior volume and rate features
- batter-pitcher prior matchup summary
- coarse context prior rates
- park prior run environment
- batting team rolling-30 performance
- fielding team rolling-30 performance
- `park_id`

These are already wired through `features.plate_appearance_advanced_examples` and the current trainer.

### Features intentionally deferred

Do not make these part of the first operational baseline:

- recursive pitch-sequence state transitions
- pitch-level Markov simulation
- Statcast / pitch movement / velocity features
- defensive alignment or catcher framing proxies
- market or betting features

Those should be layered on only after the direct PA model is stable and calibrated.

## SQL Infrastructure Plan

The recommended warehouse pattern is:

1. Preserve raw terminal classes in `features.plate_appearance_outcome_examples`.
2. Add one additive grouped training object for v1 model training.
3. Keep prior/career/context feature marts separate and reusable.
4. Build a later live feature-parity view that matches the grouped training contract.

### Recommended SQL objects

No destructive changes are needed.

Additive next objects:

- `features.plate_appearance_outcome_grouped_examples`
  - one row per PA
  - same joins as the existing advanced layer
  - grouped target for the first stable production candidate

- `features.live_plate_appearance_outcome_feature_parity`
  - view over `core.live_events` plus bridge/reference layers
  - same columns as the grouped historical training view wherever possible

### Materialized view versus view

Use a materialized view for the historical grouped training set because it is reused by training, diagnostics, and backtests.

Use a standard view for the live feature-parity layer first because the live data changes frequently and the bridge layer is still evolving.

## Baseline Statistical Models

Use the current Python training stack:

- `pandas`
- `numpy`
- `scikit-learn`

First candidate models:

- multinomial logistic regression
- histogram gradient boosting multiclass

This is enough for the baseline. Do not migrate to R or another modeling stack yet.

## Training / Validation Policy

Use the existing temporal-policy support:

- fixed recent-window benchmarks
- optional exponential recency weighting
- optional 2020 downweighting

Recommended initial comparison:

- train through `2022`
- validate on `2023-2025`
- compare grouped-taxonomy models by:
  - multiclass log loss
  - calibration by class
  - Brier-style aggregate diagnostics
  - top-3 accuracy as a secondary metric

## Derived Outputs To Expose

The scoring interface should expose at least:

- `p_single`
- `p_double`
- `p_triple`
- `p_home_run`
- `p_walk`
- `p_hit_by_pitch`
- `p_strikeout`
- `p_ground_out`
- `p_air_out`
- `p_reach_on_error_or_fc`
- `p_productive_out`
- `p_other_rare`

Plus derived aggregates:

- `p_hit`
- `p_extra_base_hit`
- `p_on_base_traditional`
- `p_reach_base_any`
- `p_ball_in_play`
- `expected_total_bases`

## Immediate Implementation Order

1. Keep `features.plate_appearance_outcome_examples` as the raw canonical outcome layer.
2. Add `features.plate_appearance_outcome_grouped_examples` as the first stable modeling target.
3. Extend `scripts/train_pa_outcome_distribution.py` with a target-taxonomy mode or create a thin grouped wrapper.
4. Run a baseline grouped-taxonomy benchmark with:
   - `basic`
   - `advanced`
   - recent-window and half-life comparisons
5. Add calibration diagnostics before promotion.
6. Build live feature parity only after the grouped historical model is validated.

## Decision

The quickest safe path is not a new stack and not a pitch-level simulator.

The quickest safe path is:

- preserve the current granular outcome layer
- train a grouped direct PA multiclass model
- expose derived probabilities from that model
- add live parity after the historical direct model is stable
