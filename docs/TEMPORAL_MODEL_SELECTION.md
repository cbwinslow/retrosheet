# Temporal Model Selection

This document defines how the project should handle non-stationarity across baseball seasons.

The practical problem is simple: a model trained on `2000-2025` as if every season were equally informative is implicitly assuming stationarity. The warehouse data does not support that assumption.

## Why This Matters

Let \(s(i)\) be the season attached to training example \(i\). Standard empirical risk minimization treats every example equally:

\[
\hat{\theta}_{\text{ERM}}
=
\arg\min_{\theta}
\frac{1}{N}
\sum_{i=1}^{N}
\ell(y_i, f_\theta(x_i)).
\]

That is only appropriate when the data-generating process is sufficiently stable over time. In baseball, that assumption is weak because the run environment, home-run environment, enforcement priorities, and formal playing rules change across seasons.

The concept-drift literature supports this concern. Lu et al. write that learning under concept drift will yield "poor learning results if the drift is not addressed." Zaidi et al. state that "as drift rate increases, the forgetting rate ... will also increase." Those statements are aligned with the problem we see in baseball data: recent examples should usually matter more than older examples, but older examples are still useful for rare outcomes and long-run priors.

## Warehouse Evidence

The current `features.plate_appearance_outcome_examples` layer spans `2000-2025` and contains `4,779,662` plate appearances.

Selected season-level environment summaries from the warehouse:

| Season | PA Rows | Hit Rate | HR Rate | Runs per PA |
|---:|---:|---:|---:|---:|
| 2000 | 192,765 | 0.2375 | 0.0298 | 0.1290 |
| 2006 | 190,368 | 0.2395 | 0.0286 | 0.1234 |
| 2014 | 186,468 | 0.2260 | 0.0228 | 0.1054 |
| 2017 | 188,199 | 0.2274 | 0.0330 | 0.1196 |
| 2019 | 189,375 | 0.2251 | 0.0363 | 0.1236 |
| 2020 | 70,519 | 0.2165 | 0.0349 | 0.1230 |
| 2023 | 187,265 | 0.2217 | 0.0319 | 0.1196 |
| 2025 | 186,640 | 0.2191 | 0.0309 | 0.1160 |

The magnitude and direction of those shifts are not trivial:

- hit rate falls materially from the early-2000s environment to the 2020s
- home-run rate bottoms out in the low-offense `2014` season and then surges again by `2019`
- `2020` is structurally abnormal because it is a shortened season
- `2023+` is a real rule-change era, not just another ordinary season

For fixed recent-history windows ending in `2025`, the warehouse provides:

| Window | Seasons | PA Rows |
|---:|---|---:|
| 3 years | 2023-2025 | 559,688 |
| 5 years | 2021-2025 | 929,476 |
| 7 years | 2019-2025 | 1,189,370 |
| 10 years | 2016-2025 | 1,752,609 |
| 15 years | 2011-2025 | 2,688,466 |
| Full span | 2000-2025 | 4,779,662 |

This tells us two things:

1. A recent-only training set is already large enough for common outcomes.
2. Rare outcomes still benefit from borrowing strength from older seasons.

## Exogenous Regime Changes

Not every boundary should be discovered purely from the data. Some regime breaks are externally justified.

Official MLB sources support at least two modern breaks:

- MLB announced enhanced foreign-substance enforcement in June 2021, calling it "an unfair competitive advantage" that "has changed the game." Source: [MLB press release, June 15, 2021](https://www.mlb.com/press-release/press-release-mlb-new-guidance-against-use-of-foreign-substances).
- MLB announced major 2023 rules changes including pitch timer, shift restrictions, and larger bases. Source: [MLB press release, September 9, 2022](https://www.mlb.com/press-release/press-release-mlb-announces-rule-changes-for-2023-season).

That means `2021` and `2023` should be treated as candidate regime boundaries even before formal drift detection.

## Recommended Training Policy

Do not train the primary production-style PA model by equally weighting all seasons from `2000-2025`.

Use three temporal mechanisms together:

1. **Recency weighting** for the main supervised loss.
2. **Era indicators** for known regime changes.
3. **Fixed-window benchmarks** for validation and model selection.

### 1. Recency Weighting

For a model trained to score season \(T\), assign season-level weights

\[
w_s = \exp\{-\lambda (T-s)\}
\]

or equivalently in half-life form

\[
w_s = 2^{-(T-s)/h},
\]

where \(h\) is the half-life in seasons.

Then optimize the weighted loss

\[
\hat{\theta}(h)
=
\arg\min_{\theta}
\frac{\sum_{i=1}^{N} w_{s(i)} \, \ell(y_i, f_\theta(x_i))}
{\sum_{i=1}^{N} w_{s(i)}}.
\]

Interpretation:

- smaller \(h\): forget old seasons faster
- larger \(h\): retain more long-run information

Candidate half-lives for this project:

\[
h \in \{3, 5, 7, 10\}.
\]

### 2. Era Indicators

Let \(e(s)\) be an era mapping. The era variables should be added as model inputs or interaction candidates, not used as the sole modeling device.

Current recommended era map for the loaded warehouse:

- `2000-2009`: early high-offense / steroid-tail environment
- `2010-2014`: lower-offense environment
- `2015-2019`: home-run surge environment
- `2020`: pandemic-shortened anomaly
- `2021-2022`: enforcement / transition period
- `2023+`: rule-change era

This is a modeling convenience, not a claim that baseball changed only at those boundaries.

### 3. Fixed-Window Benchmarks

Fit benchmark models on:

\[
W \in \{3, 5, 7, 10, 15, \text{all}\}
\]

recent seasons and compare them with recency-weighted models.

The purpose is not to permanently commit to a single arbitrary window. The purpose is to establish whether a hard cutoff ever beats a smooth forgetting curve on the validation period that matters.

## How To Choose The Window Or Half-Life

Choose the temporal policy by out-of-time validation, not intuition.

Define the candidate policy set

\[
\mathcal{P}
=
\{
\text{recent-}W : W \in \{3,5,7,10,15,\text{all}\}
\}
\cup
\{
\text{decay-}h : h \in \{3,5,7,10\}
\}.
\]

For each policy \(p \in \mathcal{P}\), train on seasons up to \(2022\) with that weighting/window rule and evaluate on `2023-2025`.

Select

\[
p^\star
=
\arg\min_{p \in \mathcal{P}}
\operatorname{LogLoss}_{2023:2025}(p)
\]

subject to calibration constraints such as:

\[
\operatorname{ECE}_{2023:2025}(p) \le \tau
\]

and acceptable subgroup performance over count, base/out state, and handedness matchups.

In practice, the model-selection order should be:

1. lowest validation log loss
2. acceptable calibration
3. acceptable subgroup stability
4. then secondary diagnostics such as top-3 accuracy or macro \(F_1\)

## Why Seven Years Is Reasonable But Not Sufficient

A 7-year window is a sensible benchmark because it balances recency and sample size.

For the current warehouse:

\[
N_{7\text{-year}} = 1{,}189{,}370 \text{ PA}.
\]

If a rare class occurs at rate \(r\), the expected number of observations is

\[
E[n_r] = N_{7\text{-year}} \cdot r.
\]

For a class near \(0.021\%\), this gives

\[
1{,}189{,}370 \times 0.00021 \approx 250
\]

rows, which is usable. A 3-year window would be much weaker for rare events. That makes 7 years a strong benchmark window, but not automatically the best production policy.

## Project Decision

The current project decision is:

- **Primary modeling policy**: recent-history training with exponential recency weighting.
- **Default benchmark window**: 7 years.
- **Required era indicators**: `2020`, `2021-2022`, and `2023+`, with broader environment buckets available as optional features.
- **Do not discard old data globally**: older seasons should still support priors, rare-class stability, and calibration analysis.

## Immediate Implementation Work

1. Temporal-policy support is now implemented in `scripts/train_pa_outcome_distribution.py`:
   - `--recent-window`
   - `--season-half-life`
   - `--exclude-2020`
   - `--downweight-2020`
2. Add era-feature columns to the PA training views.
3. Run a temporal sweep over:
   - `W ∈ {3,5,7,10,15,all}`
   - `h ∈ {3,5,7,10}`
4. Compare by `2023-2025` multiclass log loss, Brier score, calibration, and subgroup drift.

## Sources

- Lu, Liu, Dong, Gu, Gama, Zhang. *Learning under Concept Drift: A Review* (2020). arXiv summary page: https://arxiv.org/abs/2004.05785
- Zaidi, Webb, Petitjean, Forestier. *On the Inter-relationships among Drift rate, Forgetting rate, Bias/variance profile and Error* (2018). https://arxiv.org/abs/1801.09354
- MLB. *MLB announces new guidance to crack down against use of foreign substances, effective June 21* (June 15, 2021). https://www.mlb.com/press-release/press-release-mlb-new-guidance-against-use-of-foreign-substances
- MLB. *MLB announces rule changes for 2023 season* (September 9, 2022). https://www.mlb.com/press-release/press-release-mlb-announces-rule-changes-for-2023-season
