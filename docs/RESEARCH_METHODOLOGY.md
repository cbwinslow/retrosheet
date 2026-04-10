# Research Methodology

This document states the project as a formal research and engineering program. It is intentionally written closer to a methods section than to a task list.

The framework follows **CRISP-DM**:

1. Business Understanding
2. Data Understanding
3. Data Preparation
4. Modeling
5. Evaluation
6. Deployment

## 1. Business Understanding

### Research Objective

The objective is to construct a reproducible baseball probability engine that learns from historical Retrosheet play-by-play data, maps live MLB game states into the same canonical state space, and produces calibrated probabilities for baseball outcomes of practical interest.

The system is not restricted to one target. The initial target families are:

- full-game win probability
- plate-appearance outcome probability
- half-inning scenario probability
- live state scoring
- eventual model-vs-market research comparisons

The first statistically coherent core problem is the **plate-appearance outcome distribution**. That problem is granular enough to support downstream simulation, but still simple enough to build on top of historical Retrosheet observations without requiring a fully normalized pitch-by-pitch event system on day one.

### Formal Decision Problem

For each plate appearance \(i\), define a pre-outcome information set

\[
\mathcal{I}_i = \{ \text{all information available strictly before PA } i \}.
\]

We seek a model

\[
f_\theta: \mathcal{I}_i \rightarrow \Delta^{K-1},
\]

where \(\Delta^{K-1}\) is the \((K-1)\)-simplex over \(K\) mutually exclusive terminal plate-appearance outcomes.

For the current multiclass target,

\[
Y_i \in \Omega_{\text{PA}},
\]

with

\[
\Omega_{\text{PA}} =
\{
\text{single}, \text{double}, \text{triple}, \text{home\_run},
\text{walk}, \text{intentional\_walk}, \text{hit\_by\_pitch},
\text{strikeout}, \text{ground\_out}, \text{fly\_out}, \text{line\_out}, \text{pop\_out},
\text{fielders\_choice}, \text{error\_on\_batter},
\text{sacrifice\_hit}, \text{sacrifice\_fly}, \text{interference}
\}.
\]

The model returns

\[
\hat{\pi}_{ik} = P_\theta(Y_i = k \mid \mathcal{I}_i), \qquad \sum_{k \in \Omega_{\text{PA}}} \hat{\pi}_{ik} = 1.
\]

This distribution is then collapsed into derived probabilities for operational questions such as hit probability, reach-base probability, extra-base-hit probability, and expected total bases.

## 2. Data Understanding

### Source Systems

The project operates on two primary baseball data sources:

1. **Retrosheet + Chadwick**
   - historical, authoritative, normalized through Chadwick CLI tools
   - stored source-preserved in `raw_retrosheet`
   - promoted into typed `core` and ML-ready `features`

2. **MLB Stats API / GUMBO**
   - live and near-live game state
   - stored source-preserved in `raw_mlb`
   - reconciled through `bridge`
   - normalized into `core.live_games` and `core.live_events`

The research rule is:

- do not mutate raw source layers to make modeling easier
- do not merge raw historical and raw live data
- combine historical and live sources only in canonical or analysis layers

### Canonical Data Model

The current warehouse is organized as:

- `raw_retrosheet`: source-preserved Chadwick extracts and Retrosheet reference tables
- `raw_mlb`: source-preserved MLB API snapshots with fetch provenance
- `bridge`: cross-source identifiers
- `core`: typed baseball facts
- `features`: ML-ready examples and marts
- `models`: registry and metadata
- `predictions`: outputs and backtests
- `analysis`: historical + live combined views/materialized views

### State Representation

For a plate appearance \(i\), define the observed pre-PA state as

\[
x_i = [g_i, c_i, h_i, b_i, p_i, t_i, m_i],
\]

where:

- \(g_i\) = game-state variables
- \(c_i\) = count-state variables
- \(h_i\) = handedness variables
- \(b_i\) = batter history variables
- \(p_i\) = pitcher history variables
- \(t_i\) = team and park context variables
- \(m_i\) = matchup and coarse-context variables

More explicitly,

\[
g_i = (\text{inning}_i, \text{bottom}_i, \text{outs}_i, \text{bases}_i, \Delta \text{score}_i),
\]

\[
c_i = (\text{balls}_i, \text{strikes}_i),
\]

\[
h_i = (\text{batter\_hand}_i, \text{pitcher\_hand}_i),
\]

\[
b_i = \text{batter prior-season or career-prior rates},
\]

\[
p_i = \text{pitcher prior-season or career-prior rates},
\]

\[
t_i = \text{team quality, rolling form, park environment},
\]

\[
m_i = \text{batter-pitcher prior matchup and prior context rates}.
\]

### Field Semantics

The project does not assume that every raw Chadwick field is already operationalized. The field status is:

- **understood and used now**
- **understood but not yet fully operationalized**
- **preserved raw but not yet reliable enough for modeling**

That classification is maintained in [FEATURE_AUDIT.md](./FEATURE_AUDIT.md).

The current field references are:

- [retrosheet_key.md](./retrosheet_key.md)
- [ab_outcome.md](./ab_outcome.md)
- [AT_BAT_OUTCOME_MODEL_REVIEW.md](./AT_BAT_OUTCOME_MODEL_REVIEW.md)
- [CORE_SCHEMA.md](./CORE_SCHEMA.md)
- `config/chadwick_event_columns.txt`

## 3. Data Preparation

### Historical Preparation

Historical preparation proceeds:

\[
\text{Retrosheet archive} \rightarrow \text{Chadwick CLI output} \rightarrow \text{raw\_retrosheet} \rightarrow \text{core} \rightarrow \text{features}.
\]

The important current historical objects are:

- `core.games`
- `core.events`
- `core.plate_appearances`
- `features.plate_appearance_examples`
- `features.plate_appearance_advanced_examples`
- `features.plate_appearance_outcome_examples`

### Live Preparation

Live preparation proceeds:

\[
\text{MLB API snapshot} \rightarrow \text{raw\_mlb.live\_feed\_snapshots} \rightarrow \phi_{\text{bridge}} \rightarrow \text{core.live\_*} \rightarrow \text{analysis/live feature parity}.
\]

where the bridge operator

\[
\phi_{\text{bridge}} = (\phi_{\text{player}}, \phi_{\text{team}}, \phi_{\text{park}}, \phi_{\text{game}})
\]

maps MLB identifiers into canonical Retrosheet-compatible identifiers when available.

### Leakage Rule

For every supervised training row \(i\), features must be generated from information strictly prior to the target event:

\[
x_i = f(D_{<i}),
\]

never

\[
x_i = f(D_{\le i}) \text{ if } D_i \text{ contains the target outcome}.
\]

Operationally, this means:

- prior-season features use \(s-1\) or earlier for feature season \(s\)
- career-prior features use seasons strictly earlier than the current season
- rolling features end before the current game or current event
- matchup features exclude the current PA
- live scoring never uses post-outcome play state as a predictor

## 4. Modeling

### 4.1 Plate-Appearance Outcome Distribution

The primary direct model is multiclass classification:

\[
\hat{\pi}_{ik} = P_\theta(Y_i = k \mid x_i), \qquad k \in \Omega_{\text{PA}}.
\]

The current candidate model families are:

- multinomial logistic regression
- histogram gradient boosting

The optimization target is multiclass log loss:

\[
\mathcal{L}_{\text{log}}(\theta)
=
-\frac{1}{N}
\sum_{i=1}^{N}
\sum_{k=1}^{K}
\mathbf{1}(Y_i = k)\log \hat{\pi}_{ik}.
\]

This is preferred to raw accuracy because the system is intended to support simulation, decision support, and comparative probability analysis. Probability quality matters more than class-label hit rate.

### 4.2 Derived Probability Functionals

From the granular PA distribution, define:

\[
P(\text{Hit}) =
P(\text{single}) + P(\text{double}) + P(\text{triple}) + P(\text{home\_run}),
\]

\[
P(\text{XBH}) =
P(\text{double}) + P(\text{triple}) + P(\text{home\_run}),
\]

\[
P(\text{OnBase}_{\text{traditional}})
=
P(\text{single}) + P(\text{double}) + P(\text{triple}) + P(\text{home\_run})
+ P(\text{walk}) + P(\text{intentional\_walk}) + P(\text{hit\_by\_pitch}),
\]

\[
P(\text{ReachBase}_{\text{any}})
=
P(\text{OnBase}_{\text{traditional}})
+ P(\text{error\_on\_batter}) + P(\text{interference}),
\]

\[
P(\text{BallInPlay})
=
P(\text{single}) + P(\text{double}) + P(\text{triple}) + P(\text{home\_run})
+ P(\text{ground\_out}) + P(\text{fly\_out}) + P(\text{line\_out}) + P(\text{pop\_out})
+ P(\text{error\_on\_batter}) + P(\text{fielders\_choice})
+ P(\text{sacrifice\_hit}) + P(\text{sacrifice\_fly}),
\]

\[
E[\text{TB}]
=
1 \cdot P(\text{single})
+ 2 \cdot P(\text{double})
+ 3 \cdot P(\text{triple})
+ 4 \cdot P(\text{home\_run}).
\]

### 4.3 Run Expectancy and Win Probability

For a base-out-count-score state \(s\), define run expectancy as

\[
RE(s) = E[R_{\text{remain}} \mid s],
\]

and home-team win probability as

\[
WP(s) = P(\text{Home team wins} \mid s).
\]

For an event transition \(s_{\text{before}} \rightarrow s_{\text{after}}\),

\[
\Delta RE = RE(s_{\text{after}}) - RE(s_{\text{before}}),
\]

\[
\Delta WP = WP(s_{\text{after}}) - WP(s_{\text{before}}).
\]

These objects are downstream modeling targets and analysis quantities. They also provide principled ways to collapse plate-appearance outcome distributions into more global game-value measures.

### 4.4 Future Pitch-Level Model

If pitch-level rows are normalized, then the pitch process can be written as

\[
Z_{ij} \in \Omega_{\text{pitch}},
\]

where \(Z_{ij}\) is pitch \(j\) in PA \(i\), and

\[
P(Z_{ij} = z \mid x_{ij})
\]

describes the next-pitch distribution given the current within-PA state \(x_{ij}\).

The recursive simulation formulation is then:

\[
P(Y_i = k \mid x_i)

=
\sum_{\text{all admissible pitch paths } \gamma}
P(\gamma \mid x_i)\mathbf{1}(Y(\gamma)=k).
\]

This is more expressive, but only worth doing once `pitch_seq_tx` is normalized and validated.

## 5. Evaluation

### Temporal Evaluation

Model evaluation is explicitly time-aware. For training seasons \( \{s_{\min}, \dots, s_T\} \) and validation seasons \( \{s_{T+1}, \dots, s_{\max}\} \),

\[
\mathcal{D}_{\text{train}} = \{ i : \text{season}_i \le T \},
\qquad
\mathcal{D}_{\text{valid}} = \{ i : \text{season}_i > T \}.
\]

The current operational split is:

- train through 2022
- validate on 2023-2025

### Primary Metrics

For multiclass PA modeling, priority is:

1. multiclass log loss
2. calibration
3. multiclass Brier score
4. top-\(k\) accuracy
5. macro and weighted \(F_1\)

The multiclass Brier score is

\[
\text{Brier}_{\text{multi}}
=
\frac{1}{N}
\sum_{i=1}^{N}
\sum_{k=1}^{K}
(\hat{\pi}_{ik} - y_{ik})^2,
\]

where \(y_{ik}\) is the one-hot encoding of the observed class.

### Calibration

For any reported probability \(p\), calibration requires

\[
P(Y=1 \mid \hat{P}=p) \approx p.
\]

In practice, this is checked with reliability diagrams, bin-based summaries, and subgroup diagnostics.

For scalar summaries, one useful diagnostic is expected calibration error:

\[
\operatorname{ECE}
=
\sum_{m=1}^{M}
\frac{|B_m|}{N}
\left|
\operatorname{acc}(B_m) - \operatorname{conf}(B_m)
\right|,
\]

where \(B_m\) is a confidence bin.

### Subgroup Analysis

Evaluation should be stratified by:

- count state
- base/out state
- handedness matchup
- season
- common outcome groups such as hit, on-base, strikeout, and ball-in-play

The project is intended to support real probabilities, not just point classifications. Poor subgroup calibration is a deployment blocker.

## 6. Deployment

### Reproducibility

Every accepted model must satisfy:

- training data regenerates from warehouse state
- feature specification is stored in `models.model_registry`
- artifacts live under ignored `data/models/`
- the promotion path is script-driven, not manual

### Live Scoring Principle

Live inference should be treated as:

\[
\text{raw MLB snapshot}
\rightarrow
\text{canonical live state}
\rightarrow
\text{historical-compatible live feature row}
\rightarrow
\text{registered model}
\rightarrow
\text{prediction log}.
\]

The model should never score raw JSON directly.

### Research Posture

This project is explicitly a research and analytics system. Market-comparison work is downstream and must remain clearly separated from any notion of automated trading or financial advice.

## Methodological Status

The current system is methodologically strong enough to support:

- direct historical PA distribution modeling
- historical binary PA modeling
- historical win-probability modeling
- early historical/live warehouse bridging

It is not yet complete enough to support a final research-grade pitch-process model or a final production-grade live PA inference layer.

## Immediate Next Steps

Under this methodology, the highest-return next implementation steps are:

1. normalize `pitch_seq_tx` into one pitch per row
2. add same-game temporal features for PA models
3. build live feature parity for `pa_outcome_distribution`
4. add calibration/backtest reporting for multiclass PA outcomes
5. only then increase hyperparameter search breadth materially
