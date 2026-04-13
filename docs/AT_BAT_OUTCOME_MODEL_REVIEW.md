# At-Bat Outcome Model Review

This note reviews `docs/ab_outcome.md` against the current Retrosheet warehouse and turns it into a reusable implementation path.

## Bottom Line

The document is useful as a specification, but it is broader than what we should build in one jump. The right path is:

1. Keep the existing binary plate-appearance models.
2. Add a granular multiclass plate-appearance outcome layer.
3. Train a calibrated direct PA outcome model first.
4. Add pitch-level recursive simulation later, after the normalized pitch-sequence layer is validated and extended into same-PA temporal state features.

This reuses the current `core`, `features`, `models`, and `predictions` infrastructure instead of creating a separate modeling stack.

## Discovery Findings

- `core.plate_appearances` has 4,779,662 rows from 2000-2025.
- Every `core.plate_appearances` row joins back to `raw_retrosheet.chadwick_events` by `game_id` and `event_id`.
- PA-level count coverage is 100% for 2000-2025.
- Raw Chadwick has `pitch_seq_tx`, `battedball_cd`, `battedball_loc_tx`, `sh_fl`, and `sf_fl`.
- `pitch_seq_tx` is present for every PA in the loaded 2000-2025 seasons, and `sql/077_pitch_sequence_model.sql` now normalizes it into one row per Retrosheet sequence symbol.
- Batted-ball type is available for 3,372,283 PA rows.
- Generic outs with event code `2` split cleanly into ground, fly, line, and pop outs through `battedball_cd`.

Terminal PA event distribution:

| Event code | Outcome | Rows | Share |
|---:|---|---:|---:|
| 2 | Generic out | 2,246,595 | 47.003% |
| 3 | Strikeout | 937,040 | 19.605% |
| 20 | Single | 716,788 | 14.997% |
| 14 | Walk | 375,676 | 7.860% |
| 21 | Double | 217,565 | 4.552% |
| 23 | Home run | 136,691 | 2.860% |
| 16 | Hit by pitch | 46,050 | 0.963% |
| 18 | Error | 39,601 | 0.829% |
| 15 | Intentional walk | 26,755 | 0.560% |
| 22 | Triple | 21,635 | 0.453% |
| 19 | Fielder choice | 14,277 | 0.299% |
| 17 | Interference | 989 | 0.021% |

## What We Added

`sql/076_plate_appearance_outcome_model.sql` adds:

- `features.plate_appearance_outcome_examples`
- `features.plate_appearance_outcome_validation_summary`
- prediction target `pa_outcome_distribution`

The outcome view maps terminal PA rows into granular classes:

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
- `generic_out`
- `fielders_choice`
- `error_on_batter`
- `sacrifice_hit`
- `sacrifice_fly`
- `interference`
- `other`

It also provides reusable aggregate labels:

- `on_base_traditional`
- `reach_base_any`
- `is_hit_outcome`
- `is_extra_base_hit_outcome`
- `is_ball_in_play`
- `outcome_total_bases`

## Reuse Map

Existing useful infrastructure:

- `core.plate_appearances`: canonical PA table.
- `features.plate_appearance_examples`: current binary PA targets.
- `features.plate_appearance_advanced_examples`: career, matchup, context, park, and rolling-team features.
- `features.batter_prior_season_pa_summary`: prior-season batter rates.
- `features.pitcher_prior_season_pa_summary`: prior-season pitcher rates.
- `features.pa_context_prior_season_rates`: exact prior context rates.
- `features.pa_context_coarse_prior_season_rates`: coarser fallback context rates.
- `features.batter_pitcher_prior_matchup_summary`: head-to-head matchup history.
- `models.model_registry`: model artifact and metrics registry.
- `predictions.prediction_targets`: target registry.

## Recommended Modeling Sequence

1. Train a baseline empirical multiclass model from `features.plate_appearance_outcome_examples`, grouped by season, count, base/out state, and handedness.
2. Use `scripts/train_pa_outcome_distribution.py` for the first reusable multiclass trainer. It writes artifacts to ignored `data/models/` and registers metrics in `models.model_registry` under `pa_outcome_distribution`.
3. Start with multinomial logistic regression and histogram gradient boosting because they already fit our dependency footprint.
4. Use time-aware splits: train through 2022, validate 2023-2025.
5. Optimize log loss and calibration first; classification accuracy is secondary.
6. Add calibration tables/reports before using model probabilities in simulations.
7. Only after the direct PA distribution model works and the normalized pitch-sequence layer is validated, evaluate recursive pitch simulation.

## Leakage Notes

The current feature marts are mostly safe because prior-season and career-prior features use seasons strictly before the feature season. Some future feature work should be explicit:

- Season-to-date and rolling PA features must stop before the current game or current PA.
- Batter-pitcher matchup features must exclude the current PA.
- Game-to-date features must use only events before the current PA.
- If player ID target encoding is added, it must be fold-aware or leave-one-out to avoid leakage.

## Known Limitations

- Retrosheet does not include Statcast pitch velocity, spin, movement, defensive positioning, or catcher framing.
- `pitch_seq_tx` is present in loaded seasons and is now normalized into one row per Retrosheet sequence symbol, but full pitch-state reconstruction is still incomplete.
- Switch-hitter handling currently relies on Chadwick-resolved `batter_hand`; that is good for observed historical PAs, but live inference needs a deterministic handedness resolver.
- Rare classes such as interference and triples may need grouping or hierarchical smoothing for stable calibrated probabilities.
