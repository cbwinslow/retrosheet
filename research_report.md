# Research Report

## Title

Toward a Reproducible Baseball Probability Engine: Historical Plate-Appearance Modeling with Retrosheet, Chadwick, and MLB Stats API Data

## Abstract

This report documents the current research state of a reproducible baseball analytics warehouse and probability engine built from free and open data sources. The system combines historical Retrosheet event data parsed through Chadwick with source-preserved MLB Stats API snapshots for live and recent game-state acquisition. The first formal modeling objective is the estimation of a calibrated probability distribution over terminal plate-appearance outcomes conditional on pre-outcome game state, count, handedness, and historical priors. The present warehouse spans `2000-2025` and contains `4,779,662` historical plate appearances. A complete practical MLB raw backfill for `2000-2025` has also been assembled, with only seven unresolved exhibition-game snapshots failing upstream at the MLB API layer. Current benchmark results show that histogram gradient boosting is materially stronger than multinomial logistic regression for grouped plate-appearance outcome modeling. A targeted count-state feature family, built from batter, pitcher, and context prior rates split by ball-strike count, now yields modest aggregate improvement and clearer subgroup improvement in the two-strike states that were previously the main reliability defect. Calibration and bootstrap evidence are now stored as durable warehouse artifacts tied directly to registered model versions and prediction-run records, and reusable isotonic calibration artifacts can be loaded during inference.

## 1. Research Objective

The research objective is to construct a reusable baseball probability engine that can:

- learn from historical play-by-play data,
- transform live MLB game states into the same canonical state space,
- produce calibrated probabilities for baseball events of practical interest,
- support later simulation, backtesting, and model-versus-market research.

The first statistically coherent core problem is the plate-appearance outcome distribution. For each completed plate appearance \(i\), define a pre-outcome information set

\[
\mathcal{I}_i = \{\text{all information available strictly before plate appearance } i\}.
\]

We seek a model

\[
f_\theta : \mathcal{I}_i \rightarrow \Delta^{K-1},
\]

where \(\Delta^{K-1}\) is the \((K-1)\)-simplex over \(K\) mutually exclusive plate-appearance outcome classes. For a target space \(\Omega_{\text{PA}}\), the model returns

\[
\hat{\pi}_{ik} = P_\theta(Y_i = k \mid \mathcal{I}_i), \qquad \sum_{k \in \Omega_{\text{PA}}} \hat{\pi}_{ik} = 1.
\]

These probabilities can then be aggregated into operational quantities such as hit probability, on-base probability, expected total bases, or scenario-level simulation inputs. For example,

\[
P(\text{hit}) = P(1B) + P(2B) + P(3B) + P(HR),
\]

and

\[
\mathbb{E}[\text{total bases}] = 1P(1B) + 2P(2B) + 3P(3B) + 4P(HR).
\]

## 2. Research Framework
## 2. Research Framework (CRISP‑DM)

The project adheres to the **CRISP‑DM** (Cross‑Industry Standard Process for Data Mining) methodology, which provides a disciplined, repeatable workflow for data‑driven research.  The six phases are:

1. **Business Understanding** – Define the problem (probability engine for baseball), success metrics, and constraints.
2. **Data Understanding** – Explore Retrosheet, Chadwick, and MLB Stats API sources; assess completeness and quality (see Section 4).
3. **Data Preparation** – Preserve raw layers, build bridge tables, and generate canonical `core` tables; apply the new validation script (`scripts/validate_mlb_ingestion.py`).
4. **Modeling** – Train plate‑appearance outcome models, experiment with gradient‑boosted trees, and incorporate advanced feature families (Section 5).
5. **Evaluation** – Use calibrated log‑loss, Brier score, and out‑of‑sample temporal splits (2023‑2025) to assess predictive performance.
6. **Deployment** – Export models to `models/model_registry`, serve via `fast_prediction_service.py`, and integrate with the LLM‑driven chatbot.

This explicit CRISP‑DM framing clarifies hand‑offs between the data‑engineering and ML‑engineering teams and ensures that each iteration is documented, reproducible, and auditable.

## 3. Data Sources And Canonical Warehouse Design

### 3.1 Source Systems

The project currently uses two primary baseball data systems.

1. Retrosheet plus Chadwick
   - historical play-by-play and game metadata,
   - parsed with Chadwick command-line tools,
   - preserved in `raw_retrosheet`,
   - normalized into `core` and `features`.

2. MLB Stats API / GUMBO
   - live and historical API snapshots,
   - preserved in `raw_mlb`,
   - reconciled through `bridge`,
   - transformed into `core.live_games` and `core.live_events`.

The governing data-model rule is that raw source layers are never reshaped destructively for modeling convenience. Historical and live data are merged only in typed canonical or analysis layers.

### 3.2 Warehouse Layers

The canonical warehouse is organized into:

- `raw_retrosheet`
- `raw_mlb`
- `bridge`
- `core`
- `features`
- `models`
- `predictions`
- `analysis`

This separation is necessary to keep source preservation, reproducibility, and model-facing feature construction distinct.

## 4. Data Coverage

### 4.1 Historical Plate-Appearance Coverage

The current canonical historical plate-appearance outcome layer is `features.plate_appearance_outcome_examples`.

Validated coverage:

- seasons: `2000-2025`
- rows: `4,779,662`
- exact join coverage to `features.plate_appearance_advanced_examples`: `4,779,662`
- pitch-sequence coverage: `4,779,662 / 4,779,662`
- batted-ball type coverage: `3,372,283 / 4,779,662`
- batted-ball location coverage: `3,277,405 / 4,779,662`

The full raw multiclass outcome distribution currently includes `17` observed terminal classes, with the largest classes being `ground_out`, `strikeout`, `fly_out`, `single`, and `walk`.

### 4.2 MLB Raw Backfill Coverage

The MLB raw ingestion layer is now practically complete for `2000-2025`.

Validated raw counts:

- `raw_mlb.schedule_snapshots`: `9,286`
- `raw_mlb.live_feed_snapshots`: `72,199`
- successful `raw_mlb.live_feed_snapshots`: `72,184`
- `raw_mlb.reference_snapshots`: `2,405`

Validated transformed live counts at the same checkpoint:

- `core.live_games`: `67,913`
- `core.live_events`: `5,172,275`

Successful live-feed coverage spans every season from `2000` through `2025`. Reference snapshot coverage spans all `26` seasons for `teams`, `rosters`, `people`, `venues`, and `standings`.

Seven unresolved game-feed failures remain:

- `243297`
- `243298`
- `243313`
- `243314`
- `308207`
- `764834`
- `764836`

All seven still return upstream MLB Stats API `HTTP 500` responses and correspond to exhibition or special-event games with `gameType = 'E'`. The conclusion is that the MLB raw layer is complete enough for continued research and that these residual failures represent upstream API holes rather than local ingestion defects.

## 5. State Representation And Feature Contract

For plate appearance \(i\), the current state representation can be written as

\[
x_i = [g_i, c_i, h_i, b_i, p_i, t_i, m_i],
\]

where:

- \(g_i\) denotes game-state variables,
- \(c_i\) denotes count-state variables,
- \(h_i\) denotes handedness variables,
- \(b_i\) denotes batter historical priors,
- \(p_i\) denotes pitcher historical priors,
- \(t_i\) denotes team and park context,
- \(m_i\) denotes matchup and coarse-context priors.

More explicitly,

\[
g_i = (\text{inning}_i, \text{bottom}_i, \text{outs}_i, \text{bases}_i, \Delta \text{score}_i),
\]

\[
c_i = (\text{balls}_i, \text{strikes}_i),
\]

\[
h_i = (\text{batter\_hand}_i, \text{pitcher\_hand}_i).
\]

The current baseline feature contract includes:

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

The advanced feature set additionally includes:

- batter career-prior volume and rate features,
- pitcher career-prior volume and rate features,
- prior batter-pitcher matchup summaries,
- coarse-context prior rates,
- park prior environment,
- rolling 30-game team form,
- `park_id`.

## 6. Leakage Constraints

For every supervised training row \(i\), the feature vector must be generated only from information strictly prior to the target plate appearance:

\[
x_i = f(D_{<i}),
\]

never from any data that encode the current or future outcome. Operationally, this means:

- prior-season features must not leak target-season information,
- career-prior features must be truncated before the target season,
- matchup features must exclude the current plate appearance,
- rolling features must end before the current game or current event,
- evaluation splits must be temporal rather than random.

This rule is fundamental because baseball data are explicitly time-ordered and non-stationary.

## 7. Label Taxonomy

The warehouse preserves the granular multiclass target in `features.plate_appearance_outcome_examples`. However, the first stable modeling target is a grouped taxonomy designed to reduce rare-class instability while preserving baseball meaning.

The grouped classes are:

- `single`
- `double`
- `triple`
- `home_run`
- `walk`
- `hit_by_pitch`
- `strikeout`
- `ground_out`
- `air_or_other_out`
- `reach_on_error_or_fc`
- `productive_out`
- `other_rare`

The grouped training layer `features.plate_appearance_outcome_grouped_examples` has:

- `4,779,662` rows,
- `62,598` distinct games,
- `12` grouped classes,
- pitch-sequence coverage `1.0000`,
- batted-ball coverage `0.7055`.

Grouped class counts are:

- `air_or_other_out`: `1,101,085`
- `ground_out`: `1,082,774`
- `strikeout`: `937,040`
- `single`: `716,788`
- `walk`: `402,431`
- `double`: `217,565`
- `home_run`: `136,691`
- `productive_out`: `64,835`
- `reach_on_error_or_fc`: `51,779`
- `hit_by_pitch`: `46,050`
- `triple`: `21,635`
- `other_rare`: `989`

## 8. Statistical Objective

The direct plate-appearance model is a multiclass classifier optimized under log loss:

\[
\mathcal{L}(\theta) =
- \sum_{i=1}^{n} \sum_{k=1}^{K}
\mathbf{1}(Y_i = k)\log \hat{p}_{ik}.
\]

This objective is preferable to fitting separate unrelated binary models because it preserves probability coherence across mutually exclusive terminal outcomes.

The current model families are:

- multinomial logistic regression,
- histogram gradient boosting multiclass.

## 9. Temporal Non-Stationarity And Recency Weighting

Baseball outcomes are not generated by a stable stationary process over `2000-2025`. Run environment, home-run environment, enforcement priorities, and formal rules change materially over time.

If \(s(i)\) is the season associated with training example \(i\), standard empirical risk minimization assumes equal weighting:

\[
\hat{\theta}_{\text{ERM}}
=
\arg\min_{\theta}
\frac{1}{N}
\sum_{i=1}^{N}\ell(y_i, f_\theta(x_i)).
\]

That assumption is weak for this setting. The current project therefore treats temporal policy as a first-class modeling decision.

For a target scoring season \(T\), recency weighting is defined as

\[
w_s = 2^{-(T-s)/h},
\]

where \(h\) is the half-life in seasons. The weighted estimator is then

\[
\hat{\theta}(h)
=
\arg\min_{\theta}
\frac{\sum_{i=1}^{N} w_{s(i)} \, \ell(y_i, f_\theta(x_i))}
{\sum_{i=1}^{N} w_{s(i)}}.
\]

Candidate half-lives are currently

\[
h \in \{3, 5, 7, 10\}.
\]

Fixed recent-window baselines are also used:

\[
W \in \{3, 5, 7, 10, 15, \text{all}\}.
\]

The temporal policy is selected by out-of-time validation on `2023-2025`, not by intuition alone.

## 10. Empirical Warehouse Evidence For Temporal Drift

The current warehouse provides direct evidence that the run environment shifts meaningfully across the covered period.

Selected season-level summaries from `features.plate_appearance_outcome_examples`:

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

These shifts justify both explicit era indicators and formal temporal-policy testing.

## 11. Experimental Design

The current grouped plate-appearance benchmark uses:

- target taxonomy: grouped,
- training seasons up to `2022`,
- validation seasons `2023-2025`,
- recent-window baseline: `7` seasons,
- sample rate for the substantive benchmark: `0.05`,
- sparse-class filter: `min_class_rows = 100`.

The recent-window sampled class distribution remains healthy. All `12` grouped classes exist in both training and validation over the full `2016-2025` window; sampled training runs retain `11` classes because `other_rare` falls below the `min_class_rows = 100` filter.

### 11.1 Algorithmic Direction

The current project adopts a staged modeling program rather than attempting a single final model family immediately.

The near-term production-style direction is:

1. direct multiclass plate-appearance modeling,
2. histogram gradient boosting as the primary predictive baseline,
3. grouped target taxonomy for class stability,
4. post-hoc calibration as a distinct probability-quality layer.

This choice is pragmatic. It captures the terminal plate-appearance distribution directly, produces useful probabilities without requiring a fully reconstructed pitch-by-pitch state machine, and integrates cleanly with the present warehouse and live-feature roadmap.

The medium-term research direction is:

- hierarchical multinomial or hierarchical Bayesian matchup models with partial pooling across players, handedness contexts, and parks.

This direction is statistically attractive because it should handle sparse batter-pitcher matchups and player-level data scarcity more gracefully than purely discriminative tree-based models.

The longer-term simulation direction is:

- count-transition or pitch-transition Markov models built on normalized within-PA sequence state.

That direction is the most natural path for next-pitch prediction and recursive inning/game simulation, but it depends on a stronger pitch-state layer than is currently available.

### 11.2 Calibration Design

Because this project aims to produce usable probabilities rather than only class labels, calibration is treated as a first-class modeling layer.

For any predicted scalar probability \(p\), calibration requires:

\[
P(Y = 1 \mid \hat{P} = p) \approx p.
\]

For the multiclass setting, the project currently evaluates calibration using:

- per-class expected calibration error,
- bin-based reliability tables,
- multiclass Brier score,
- subgroup confidence-versus-accuracy gaps.

Post-hoc calibration is implemented experimentally with one-vs-rest isotonic regression followed by row-wise renormalization to restore the multiclass simplex.

### 11.3 Bootstrap And Stratified Sampling Design

Naive independent bootstrap over individual plate appearances is not appropriate for this problem because plate appearances within a game are dependent through lineup order, pitcher usage, count-state evolution, and local game context.

The current recommended uncertainty-estimation design is therefore:

1. **cluster bootstrap by game**,
2. **season-stratified resampling** of games,
3. **subgroup-stratified reporting** rather than subgroup-stratified training resampling.

Let season \(s\) contain game clusters \(G_s = \{g_{s1}, \dots, g_{sn_s}\}\). A season-stratified cluster bootstrap replicate samples games with replacement within each season:

\[
G_s^{\ast} \sim \text{Multinomial sample of size } n_s \text{ from } G_s.
\]

The bootstrap dataset is then

\[
\mathcal{D}^{\ast} = \bigcup_s \bigcup_{g \in G_s^{\ast}} \mathcal{D}_g.
\]

This preserves within-game dependence while keeping the season mix fixed.

The main reason for stratifying by season is that baseball is non-stationary. A bootstrap that freely reshuffles across seasons would distort the era composition and produce misleading uncertainty intervals.

The main reason for clustering by game is that treating sequential plate appearances as independent would understate uncertainty.

### 11.4 Subgroup Evaluation Design

The project should explicitly report subgroup behavior across:

- balls-strikes count,
- base/out state,
- handedness matchup,
- season and era,
- eventually, pitcher-role and lineup-turn context.

This is not a cosmetic reporting choice. The earlier calibration pass already showed that the dominant deployment defect is concentrated in two-strike counts rather than uniformly across the state space.

### 11.5 Current Bootstrap Implementation

The current bootstrap implementation uses season-stratified game-cluster resampling with cached per-game sufficient statistics. For each game \(g\), the system caches:

- total row count,
- summed log-loss contribution,
- summed multiclass Brier contribution,
- total exact-correct predictions,
- total top-3-correct predictions,
- per-game confusion matrix.

This allows bootstrap replicates to aggregate game-level statistics rather than rescoring or recomputing row-level metrics from scratch.

## 12. Results

### 12.1 Grouped Recent-Window Benchmark

On the grouped target with a 7-season recent window and a `5%` sample:

| Model | Log Loss | Accuracy | Top-3 Accuracy |
|---|---:|---:|---:|
| Basic multinomial logistic | `2.0809` | `0.2821` | `0.4821` |
| Basic HGB | `1.5253` | `0.4066` | `0.8194` |
| Advanced multinomial logistic | `2.1086` | `0.2864` | `0.4973` |
| Advanced HGB | `1.5242` | `0.4081` | `0.8176` |

### 12.2 Interpretation

Three conclusions follow from these results.

First, histogram gradient boosting is materially stronger than multinomial logistic regression for the grouped plate-appearance problem under the current feature contracts.

Second, the current advanced feature mart provides only marginal lift over the grouped basic baseline on log loss:

\[
1.5253 - 1.5242 = 0.0011.
\]

That difference is too small to support a claim that the present advanced mart has fundamentally changed the modeling frontier for this grouped target.

Third, the grouped taxonomy is operationally viable. It preserves baseball semantics, avoids the worst rare-class instability, and produces a coherent baseline that can now support temporal-policy sweeps, calibration work, and later live feature-parity mapping.

### 12.3 Temporal Sweep Smoke Test

A preliminary temporal-policy smoke test was run for the grouped advanced feature set at a `1%` sample, comparing:

- fixed `window = 7`,
- full-history recency weighting with `half_life = 5`.

For histogram gradient boosting:

- `window = 7`: log loss `1.5816`
- `half_life = 5`: log loss `1.5748`

This is only a smoke test, not the final production-policy decision, but it is directionally consistent with the project hypothesis that explicit temporal policy matters and should be selected empirically.

### 12.4 Full Temporal Sweep

A substantive temporal-policy sweep was then run for the grouped advanced feature set with:

- `sample_rate = 0.05`
- training seasons through `2022`
- validation seasons `2023-2025`
- fixed windows \(W \in \{3,5,7,10,15,\text{all}\}\)
- decay half-lives \(h \in \{3,5,7,10\}\)

Ranking the histogram gradient boosting candidates by validation log loss gives:

| Policy | Log Loss | Accuracy | Top-3 Accuracy |
|---|---:|---:|---:|
| `all seasons, no decay` | `1.5094` | `0.4118` | `0.8210` |
| `all seasons, half_life = 10` | `1.5122` | `0.4132` | `0.8204` |
| `15-year window` | `1.5123` | `0.4138` | `0.8205` |
| `all seasons, half_life = 7` | `1.5129` | `0.4137` | `0.8203` |
| `all seasons, half_life = 5` | `1.5144` | `0.4112` | `0.8207` |
| `10-year window` | `1.5168` | `0.4120` | `0.8188` |
| `all seasons, half_life = 3` | `1.5201` | `0.4094` | `0.8186` |
| `7-year window` | `1.5234` | `0.4075` | `0.8170` |
| `5-year window` | `1.5287` | `0.4090` | `0.8185` |
| `3-year window` | `1.5429` | `0.4067` | `0.8165` |

The best current policy is therefore:

\[
p^\star = \text{all seasons, no decay}
\]

for the grouped advanced HGB benchmark under the current feature contract and validation regime.

### 12.5 Interpretation Of The Temporal Sweep

This result is important because it rejects the naive assumption that more aggressive recency weighting must help. For the current grouped plate-appearance target, the evidence indicates that the historical signal from older seasons is still valuable enough to outweigh moderate concept drift.

The strongest practical interpretation is:

- short recent windows are too aggressive and lose useful information,
- finite long windows such as `10` and `15` years are competitive,
- smooth forgetting with half-lives `3-10` does not currently beat equal-weight full history,
- temporal policy still matters, but the correct policy for the present grouped target is broader historical retention than initially expected.

## 13. Methodological Limitations

### 12.6 Calibration And Subgroup Reliability

A calibration and subgroup diagnostic pass was run against the current winning grouped advanced HGB model:

- model version: `20260411T230512Z`
- feature set: `advanced`
- target taxonomy: `grouped`
- validation seasons: `2023-2025`
- validation rows: `559,688`

Registered aggregate validation metrics for this model are:

- log loss: `1.5094`
- multiclass Brier score: `0.7151`
- accuracy: `0.4118`
- top-3 accuracy: `0.8210`

Per-class calibration is mixed rather than uniformly strong.

Best-calibrated grouped classes by expected calibration error (ECE) include:

- `triple`: `0.0002`
- `reach_on_error_or_fc`: `0.0003`
- `double`: `0.0004`
- `hit_by_pitch`: `0.0007`
- `productive_out`: `0.0011`
- `home_run`: `0.0011`

Moderately miscalibrated classes include:

- `walk`: `0.0026`
- `ground_out`: `0.0058`
- `single`: `0.0079`
- `air_or_other_out`: `0.0092`

The worst current class-level issue is:

- `strikeout`: `ECE = 0.0181`

with mean predicted probability `0.2415` against observed frequency `0.2253`, indicating that strikeout probability is systematically too high on average in the validation set.

The subgroup reliability results also show structured confidence gaps. Using top-class confidence versus realized top-class accuracy:

- by count:
  - `0-2`: confidence gap `0.0449`
  - `1-2`: confidence gap `0.0405`
  - `2-2`: confidence gap `0.0438`
- by outs:
  - gaps are smaller and relatively stable, roughly `0.020-0.024`
- by base state:
  - several occupied-base states show wider gaps, including `start_bases = 6` with gap `0.0406`
- by handedness matchup:
  - the largest observed gap is `RvR` at `0.0252`
- by season:
  - the gap is stable across `2023-2025`, roughly `0.021-0.022`

The practical interpretation is that the model is reasonably stable across seasons, but it is overconfident in some high-strike-count situations and in sparse tactical states. Rare grouped classes also show extreme overconfidence in high-probability bins because those bins contain very few observations.

### 12.7 Current Evaluation Conclusion

The current grouped advanced HGB model is a valid research baseline, but it is not yet a production-grade probability model.

The main blockers are:

- overconfidence in the `strikeout` class,
- overconfidence in two-strike count states,
- unstable high-probability bins for sparse grouped classes,
- missing formal calibration correction and report tables.

### 12.8 Post-Hoc Isotonic Calibration On Held-Out 2025

A post-hoc multiclass calibration experiment was then run on the winning grouped advanced HGB model using:

- calibration seasons: `2023-2024`
- held-out evaluation season: `2025`
- one-vs-rest isotonic calibration per class
- row-wise renormalization back to the probability simplex

Held-out `2025` results:

| Metric | Raw | Isotonic-Calibrated |
|---|---:|---:|
| Log loss | `1.5078` | `1.5047` |
| Multiclass Brier score | `0.7138` | `0.7125` |
| Accuracy | `0.4143` | `0.4144` |
| Top-3 accuracy | `0.8208` | `0.8206` |

The most important class-level improvement is strikeout calibration:

- raw `strikeout` ECE: `0.0179`
- calibrated `strikeout` ECE: `0.0036`

Other notable improvements include:

- `single` ECE: `0.0082` to `0.0018`
- `air_or_other_out` ECE: `0.0092` to `0.0049`
- `ground_out` ECE: `0.0057` to `0.0035`
- `home_run` ECE: `0.0015` to `0.0005`

This is the first result that materially strengthens the model as a probability engine rather than just a classifier. The improvement is not cosmetic: it reduces the key probability-quality metrics on held-out data while preserving essentially the same classification performance.

### 12.9 Season-Stratified Cluster Bootstrap

After optimizing the bootstrap evaluator to aggregate cached per-game statistics, a 50-replicate season-stratified cluster bootstrap was run for the winning grouped advanced HGB model over the `2023-2025` validation slice.

Bootstrap summary:

| Metric | Mean | 5th Percentile | 95th Percentile |
|---|---:|---:|---:|
| Log loss | `1.5127` | `1.5108` | `1.5155` |
| Multiclass Brier | `0.7148` | `0.7138` | `0.7156` |
| Accuracy | `0.4138` | `0.4125` | `0.4151` |
| Macro \(F_1\) | `0.1779` | `0.1769` | `0.1787` |
| Weighted \(F_1\) | `0.3253` | `0.3240` | `0.3266` |
| Top-3 accuracy | `0.8187` | `0.8176` | `0.8196` |

The main interpretation is that the current baseline is reasonably stable under dependence-aware resampling. The uncertainty bands are not degenerate, but they are tight enough to support the claim that the grouped advanced HGB model is a stable historical benchmark rather than an artifact of one lucky validation split.

The current system is not yet feature-complete.

Known limitations include:

- same-game temporal batter and pitcher features are still incomplete,
- pitch-sequence normalization exists, but within-PA state reconstruction is not yet fully operationalized for next-pitch modeling,
- live feature parity with the historical PA model is not complete,
- richer fielding, lineup, umpire, and environmental features are not yet available in a validated reusable mart,
- calibration and subgroup reliability analysis still need to be promoted to first-class reporting artifacts.

Accordingly, the present results should be interpreted as strong baseline research results rather than final production-grade probability estimates.

## 14. Discussion

The main engineering result is that the warehouse is now mature enough to support serious statistical work. Historical Retrosheet data are fully normalized into reusable plate-appearance examples, and the MLB raw layer is sufficiently complete to support future live bridging work.

The main modeling result is narrower: the grouped direct PA outcome approach works, but current progress is constrained less by the model family and more by temporal policy, calibration, and feature quality. This is a useful result because it prevents wasted effort on premature model churn.

In research terms, the project has moved from data acquisition uncertainty into measurable model-selection work.

## 15. Next Experiments

The immediate next research tasks are:

1. Run the full grouped HGB temporal sweep over:
   - \(W \in \{3, 5, 7, 10, 15, \text{all}\}\)
   - \(h \in \{3, 5, 7, 10\}\)
2. Select the temporal policy by `2023-2025` log loss, calibration, and subgroup stability.
3. Add same-game temporal PA features.
4. Build live feature-parity views for the grouped PA model.
5. Add calibration reports and backtest tables as durable warehouse artifacts.

## 16. Sources

- Lu, Liu, Dong, Gu, Gama, Zhang. *Learning under Concept Drift: A Review* (2020). https://arxiv.org/abs/2004.05785
- Zaidi, Webb, Petitjean, Forestier. *On the Inter-relationships among Drift rate, Forgetting rate, Bias/variance profile and Error* (2018). https://arxiv.org/abs/1801.09354
- MLB. *MLB announces new guidance to crack down against use of foreign substances, effective June 21* (June 15, 2021). https://www.mlb.com/press-release/press-release-mlb-new-guidance-against-use-of-foreign-substances
- MLB. *MLB announces rule changes for 2023 season* (September 9, 2022). https://www.mlb.com/press-release/press-release-mlb-announces-rule-changes-for-2023-season
- Internal project methodology and design documents:
  - [docs/RESEARCH_METHODOLOGY.md](/home/cbwinslow/workspace/retrosheet/docs/RESEARCH_METHODOLOGY.md)
  - [docs/TEMPORAL_MODEL_SELECTION.md](/home/cbwinslow/workspace/retrosheet/docs/TEMPORAL_MODEL_SELECTION.md)
  - [docs/PA_BASELINE_MODEL_SPEC.md](/home/cbwinslow/workspace/retrosheet/docs/PA_BASELINE_MODEL_SPEC.md)
  - [docs/FEATURE_AUDIT.md](/home/cbwinslow/workspace/retrosheet/docs/FEATURE_AUDIT.md)
  - [docs/PROJECT_LOG.md](/home/cbwinslow/workspace/retrosheet/docs/PROJECT_LOG.md)
