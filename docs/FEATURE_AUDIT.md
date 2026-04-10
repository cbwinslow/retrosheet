# Feature Audit

This document answers three practical questions:

1. Which fields do we understand well enough to trust in modeling now?
2. Which fields are preserved raw but not yet fully operationalized?
3. Where should effort go next: feature generation or hyperparameter tuning?

## Bottom Line

The current warehouse is strong enough for:

- historical game-state modeling
- binary plate-appearance modeling
- first-pass multiclass plate-appearance outcome modeling

It is not yet feature-complete for:

- next-pitch modeling
- same-game rolling state features
- live feature parity with historical PA models
- richer park/defense/lineup-aware inference

Conclusion:

- We should continue some model tuning, but the highest-return work right now is still feature work, not large hyperparameter sweeps.
- The most valuable next feature investments are pitch-level normalization, same-game temporal features, live feature parity, and a few carefully chosen baseball-specific derived features.

## Field Understanding Status

### Tier 1: Well Understood And Actively Used

These fields are well-defined, mapped into typed/core layers, and already used in models or feature marts.

Game / count / state:

- `inning`
- `is_bottom_inning`
- `outs_before`
- `balls`
- `strikes`
- `start_bases`
- `home_score_diff`
- `away_score_before`
- `home_score_before`

Core participant identity:

- `game_id`
- `batter_id`
- `pitcher_id`
- `batting_team_id`
- `fielding_team_id`
- `home_team_id`
- `away_team_id`

Observed handedness:

- `batter_hand`
- `pitcher_hand`

Observed PA outcome labels:

- `is_hit`
- `is_walk`
- `is_strikeout`
- `is_home_run`
- `is_reach_base`
- `is_extra_base_hit`
- `runs_on_play`
- `rbi`
- multiclass `outcome_class`

Prior-season / career / matchup / context features:

- batter prior-season rates
- pitcher prior-season rates
- team prior-season rates
- exact prior context rates
- coarse prior context rates
- batter career-prior rates
- pitcher career-prior rates
- batter-pitcher prior matchup rates
- park prior run environment
- rolling 30-game team form

These are the features currently carrying most of the signal in the historical models.

### Tier 2: Understood, Preserved, But Not Fully Exploited

These fields have clear baseball meaning, but we are not yet using their full value.

From Chadwick/Retrosheet event extracts:

- `pitch_seq_tx`
- `battedball_cd`
- `battedball_loc_tx`
- `sh_fl`
- `sf_fl`
- `dp_fl`
- `tp_fl`
- `wp_fl`
- `pb_fl`
- `err_ct`
- `err*_fld_cd`
- `fld_cd`
- `bat_dest_id`
- `run*_dest_id`
- `start_bases_cd`
- `end_bases_cd`
- `pa_ball_ct`
- `pa_strike_ct`
- pitch-type/count subtype summaries such as called balls, intentional balls, swinging-miss strikes, foul strikes, in-play strikes

These are useful, but not all of them are yet translated into robust model features.

Examples:

- `battedball_cd` is already used to split generic outs, but `battedball_loc_tx` is not yet turned into directional/contact features.
- `pitch_seq_tx` is preserved and coverage is strong, and `sql/077_pitch_sequence_model.sql` now normalizes it into one row per Retrosheet sequence symbol, but count-state reconstruction and richer same-PA features are still not finished.
- error/advance/destination fields are preserved, but not yet used to create richer baserunner-state transition or defensive-pressure features.

### Tier 3: Preserved Raw, Not Yet Reliable For Modeling

These are fields or concepts we have, or can fetch, but they are not yet normalized enough to trust broadly in models.

- full pitch-by-pitch sequence state from `pitch_seq_tx`
- live MLB `playEvents` pitch details aligned to historical pitch rows
- full batter-side resolution logic for live switch-hitter inference
- lineup slot / lineup-turn effects
- substitution-aware live role context
- umpire effects
- weather/environment effects as model features
- park dimensions / altitude style park traits
- defensive alignment / fielding quality proxies

These belong in future feature work, not in current large-scale hyperparameter optimization.

## What The Current Models Actually Use

### Binary PA Models

Base feature families:

- inning / outs / bases / count / score state
- batter and pitcher handedness

Enriched layer adds:

- prior-season batter rates
- prior-season pitcher rates
- prior-season team quality
- exact prior context rates

Advanced layer adds:

- career-prior batter and pitcher rates
- batter-pitcher matchup history
- coarse fallback context
- park prior environment
- rolling 30-game team form

### Multiclass PA Outcome Model

Currently uses:

- all basic PA state features
- all advanced historical features listed above
- `park_id` as a categorical feature

Not yet included:

- same-game batter or pitcher form before the current PA
- pitch-sequence-derived features
- batted-ball-location priors
- defensive-position context
- catcher / umpire context

## Do We Understand Every Field?

No. Not every Chadwick field is fully operationalized, and we should not pretend otherwise.

The correct statement is:

- we understand the meaning and modeling role of the current core historical features well enough to train useful models
- we understand the baseball semantics of many additional Chadwick fields, but we have not yet converted them into validated reusable marts
- we do not yet have a complete field-by-field operational data dictionary for every raw Chadwick column

That is normal for a warehouse of this size. What matters is making the status explicit.

## Highest-Value Feature Gaps

### 1. Pitch-Level Normalization

Why it matters:

- required for next-pitch modeling
- enables within-PA sequence features
- improves direct PA modeling with richer count-path context

Raw sources:

- `pitch_seq_tx`
- MLB live `playEvents`

### 2. Same-Game Temporal Features

Why it matters:

- batter/pitcher performance within the current game can move probabilities materially
- avoids relying only on prior-season and career priors

Examples:

- pitcher pitch count so far
- times through order
- batter prior PA results earlier in game
- bullpen vs starter indicator

### 3. Live Feature Parity

Why it matters:

- historical models are currently ahead of live inference
- the direct PA outcome model cannot be trusted on live states until feature parity is explicit

### 4. Better Batted-Ball And Contact Features

Why it matters:

- direct PA outcome classes like ground out / fly out / line out / pop out are contact-shape sensitive

Examples:

- historical directional contact buckets from `battedball_loc_tx`
- batter/pitcher contact-shape priors
- park-adjusted contact environment

### 5. Better Rare-Class Policy

Why it matters:

- rare outcomes such as interference and triples are currently unstable
- better grouping / smoothing matters more than tuning tree depth

## Hyperparameter Guidance

### What Is Worth Doing Now

- compare current logistic vs histogram gradient boosting systematically
- calibration-focused tuning
- moderate grid search on the multiclass model
- subgroup diagnostics by count/base-out/handedness/season

### What Is Not The Best Use Of Time Yet

- large blind hyperparameter sweeps
- many model families before live feature parity
- trying to squeeze tiny gains from the current feature set while major baseball signal is still unused

## Recommended Next Order

1. Finish the feature audit mindset: treat raw fields by status, not by wishful thinking.
2. Build pitch-level normalization from `pitch_seq_tx`.
3. Add same-game temporal features for PA models.
4. Build live feature parity for `pa_outcome_distribution`.
5. Then run more serious hyperparameter and calibration work.

## Raw Field Reference Notes

Use these files as the primary reference set when a field meaning is unclear:

- `config/chadwick_event_columns.txt`
- `docs/retrosheet_key.md`
- `docs/ab_outcome.md`
- `docs/AT_BAT_OUTCOME_MODEL_REVIEW.md`
- `docs/CORE_SCHEMA.md`

If a raw field becomes important to modeling, promote it by:

1. verifying meaning against the reference docs
2. exposing it through `core` or `features`
3. documenting the leakage rule
4. validating coverage and null behavior
5. only then adding it to training
