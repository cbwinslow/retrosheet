# Pitch-Level Prediction: A Research Framework for Baseball Outcome Modeling

**Date:** 2026-04-24  
**Authors:** Retrosheet Warehouse Research Team  
**CRISP-DM Phase:** 3. Data Preparation → 4. Modeling Transition  
**Epic:** #78 - Pitch-Level Model Pipeline  

---

## Abstract

This document presents a comprehensive research framework for pitch-level outcome prediction in Major League Baseball using Statcast data (2015-2025, n=7,797,034 pitches). We establish mathematical foundations for four model families: (1) Two-Tier Hierarchical Classification, (2) LSTM Sequential Modeling, (3) Multi-Task Learning, and (4) Swing Probability Estimation. Our flexible feature mart schema preserves all 118 Statcast fields while enabling metadata-driven feature selection, supporting reproducible research and model comparison.

---

## 1. Introduction

### 1.1 Research Objectives

The primary research objective is to develop calibrated probability distributions for pitch-level outcomes using high-resolution Statcast tracking data. Unlike traditional plate-appearance-level models that treat each PA as an atomic unit, pitch-level models leverage the sequential nature of baseball, enabling:

- **Early-outcome prediction:** Predict PA outcome after first pitch
- **Swing decision modeling:** Estimate batter swing probability given pitch characteristics
- **Pitch sequencing effects:** Model how prior pitches influence current pitch outcomes
- **Real-time prediction:** Generate predictions within <50ms for live scoring

### 1.2 Research Questions

1. **RQ1:** Can we predict the coarse outcome (ball/strike/ball-in-play) with >80% accuracy using only pitch physics and count state?

2. **RQ2:** Does sequential modeling (LSTM/GRU) improve prediction accuracy compared to feedforward architectures when modeling pitch sequences within plate appearances?

3. **RQ3:** Can multi-task learning simultaneously predict pitch type and location with better calibration than separate models?

4. **RQ4:** What is the upper bound on swing probability prediction accuracy, and which features contribute most to this decision?

---

## 2. Mathematical Framework

### 2.1 Notation and Definitions

Let a pitch be indexed by $i$, belonging to plate appearance $j$, within game $k$.

**Pitch-Level Information Set:**

$$
\mathcal{I}_i^{(pitch)} = \left\{ \mathbf{x}_i^{(physics)}, \mathbf{x}_i^{(context)}, \mathbf{x}_i^{(sequential)}, \mathbf{x}_i^{(player)} \right\}
$$

where:
- $\mathbf{x}_i^{(physics)} \in \mathbb{R}^{d_p}$: Pitch physics (velocity, spin, movement, location)
- $\mathbf{x}_i^{(context)} \in \mathbb{R}^{d_c}$: Game state (count, base state, score, inning)
- $\mathbf{x}_i^{(sequential)} \in \mathbb{R}^{d_s \times L}$: Sequence of previous $L$ pitches in PA
- $\mathbf{x}_i^{(player)} \in \mathbb{R}^{d_u}$: Player-specific features (rolling averages)

**Target Spaces:**

$$
\begin{aligned}
\Omega_{coarse} &= \{ \text{Ball}, \text{Strike}, \text{Ball-in-Play} \} \\
\Omega_{fine} &= \{ \text{Single}, \text{Double}, \text{Triple}, \text{HR}, \text{Out}, \text{Walk}, \text{K} \} \\
\Omega_{swing} &= \{ \text{Swing}, \text{Take} \}
\end{aligned}
$$

### 2.2 Two-Tier Hierarchical Classification

**Tier 1: Coarse Outcome Prediction**

Given pitch information $\mathcal{I}_i$, predict coarse outcome:

$$
f_\theta^{(1)}: \mathcal{I}_i \rightarrow \Delta^{2}, \quad \hat{\pi}_{ic}^{(1)} = P(Y_i^{(coarse)} = c \mid \mathcal{I}_i)
$$

**Tier 2: Fine-Grained Outcome (Conditional)**

Given ball-in-play prediction from Tier 1, predict detailed outcome:

$$
f_\phi^{(2)}: \mathcal{I}_i \times \{Y_i^{(coarse)} = \text{BIP}\} \rightarrow \Delta^{|Y_{fine}| - 1}
$$

**Combined Probability:**

$$
P(Y_i = y \mid \mathcal{I}_i) = \begin{cases}
\hat{\pi}_{i,\text{BIP}}^{(1)} \cdot \hat{\pi}_{i,y}^{(2)} & \text{if } y \in \Omega_{fine} \\
\hat{\pi}_{i,y}^{(1)} & \text{if } y \in \{\text{Ball}, \text{Strike}\}
\end{cases}
$$

**Loss Function:**

$$
\mathcal{L}_{two-tier} = \underbrace{-\sum_{i} \sum_{c \in \Omega_{coarse}} \mathbb{1}[y_i^{(coarse)} = c] \log \hat{\pi}_{ic}^{(1)}}_{\text{Tier 1 Loss}} + \underbrace{\lambda \cdot \mathbb{1}[y_i^{(coarse)} = \text{BIP}] \cdot \mathcal{L}_{fine}}_{\text{Tier 2 Loss (conditional)}}
$$

### 2.3 LSTM Sequential Model

**Sequence Encoding:**

For pitch $i$ at position $t$ in plate appearance $j$, define the sequence:

$$
\mathbf{S}_{j,t} = [\mathbf{x}_{j,1}, \mathbf{x}_{j,2}, \ldots, \mathbf{x}_{j,t-1}]
$$

where each $\mathbf{x}_{j,\tau} \in \mathbb{R}^d$ is the feature vector for pitch $\tau$.

**LSTM Forward Pass:**

$$
\begin{aligned}
\mathbf{h}_t &= \text{LSTM}(\mathbf{x}_t, \mathbf{h}_{t-1}, \mathbf{c}_{t-1}) \\
\mathbf{o}_t &= \text{softmax}(\mathbf{W}_o \mathbf{h}_t + \mathbf{b}_o)
\end{aligned}
$$

**Attention Mechanism (Optional Enhancement):**

$$
\begin{aligned}
\alpha_t &= \text{softmax}(\mathbf{q}^T \tanh(\mathbf{W}_h \mathbf{h}_t + \mathbf{b}_h)) \\
\mathbf{c}_{attn} &= \sum_{t=1}^{T} \alpha_t \mathbf{h}_t
\end{aligned}
$$

**Sequential Loss:**

$$
\mathcal{L}_{seq} = -\sum_{j} \sum_{t=1}^{T_j} \sum_{k \in \Omega} \mathbb{1}[y_{j,t} = k] \log \hat{\pi}_{j,t,k}
$$

### 2.4 Multi-Task Learning

**Multi-Task Architecture:**

Shared encoder with task-specific heads:

$$
\begin{aligned}
\mathbf{z} &= \text{Encoder}(\mathcal{I}_i) \\
\hat{y}_{type} &= \text{softmax}(\mathbf{W}_{type} \mathbf{z} + \mathbf{b}_{type}) \\
\hat{y}_{location} &= [\hat{plate}_x, \hat{plate}_z] = \mathbf{W}_{loc} \mathbf{z} + \mathbf{b}_{loc}
\end{aligned}
$$

**Multi-Task Loss:**

$$
\mathcal{L}_{MTL} = \lambda_1 \underbrace{\mathcal{L}_{CE}(\hat{y}_{type}, y_{type})}_{\text{Pitch Type}} + \lambda_2 \underbrace{\mathcal{L}_{MSE}(\hat{y}_{location}, y_{location})}_{\text{Location}} + \lambda_3 \underbrace{\mathcal{L}_{CE}(\hat{y}_{outcome}, y_{outcome})}_{\text{Outcome}}
$$

where $\lambda_1 + \lambda_2 + \lambda_3 = 1$ are task weights determined via validation.

### 2.5 Swing Probability Model

**Binary Classification:**

$$
f_\psi: \mathcal{I}_i \rightarrow [0, 1], \quad \hat{s}_i = P(\text{Swing} \mid \mathcal{I}_i)
$$

**Logistic Formulation:**

$$
\hat{s}_i = \sigma(\mathbf{w}^T \phi(\mathcal{I}_i) + b)
$$

where $\phi(\cdot)$ is a feature transformation (e.g., polynomial, spline, or neural embedding).

**Log Loss (Binary Cross-Entropy):**

$$
\mathcal{L}_{swing} = -\sum_{i} \left[ s_i \log \hat{s}_i + (1 - s_i) \log (1 - \hat{s}_i) \right]
$$

**Zone-Based Calibration:**

For pitches in strike zone $\mathcal{Z}$:

$$
\mathbb{E}[\hat{s}_i \mid plate_x, plate_z \in \mathcal{Z}] \approx \frac{\text{swings in zone}}{\text{pitches in zone}}
$$

---

## 3. Feature Engineering

### 3.1 Pitch Physics Features

**Velocity Components:**

$$
v_{release} = \sqrt{vx_0^2 + vy_0^2 + vz_0^2}
$$

**Movement Magnitude:**

$$
\text{break} = \sqrt{pfx_x^2 + pfx_z^2}
$$

**Effective Velocity:**

$$
v_{eff} = v_{release} - 1.5 \cdot \text{release_extension}
$$

**Approach Angle:**

$$
\theta_{approach} = \arctan2(vz_0, vy_0)
$$

### 3.2 Context Features

**Score Differential:**

$$
\Delta_{score} = \begin{cases}
\text{bat_score} - \text{fld_score} & \text{if batting} \\
\text{fld_score} - \text{bat_score} & \text{if fielding}
\end{cases}
$$

**Leverage Index Proxy:**

$$
LI_{proxy} = \frac{|\Delta_{score}|}{9 - \text{inning}} \times \frac{\text{runners_on}}{3}
$$

**Count State Encoding:**

One-hot or learned embedding of $(balls, strikes)$ pair.

### 3.3 Sequential Features

**Pitch Type Sequence:**

$$
\mathbf{e}_{type}^{(t)} = \text{Embedding}(pitch\_type^{(t)})
$$

**Cumulative Pitch Count:**

$$
n_{seq} = \text{pitch\_number within PA}
$$

**Previous Pitch Effect:**

$$
\Delta_{prev} = \text{result}_{t-1} \in \{\text{strike}, \text{ball}, \text{foul}, \text{hit}\}
$$

### 3.4 Player Context Features

**Rolling Averages (30-day, 90-day, season, career):**

For player $p$ at time $t$:

$$
\bar{x}_p^{(\tau)}(t) = \frac{1}{|P_{p,t}^{(\tau)}|} \sum_{i \in P_{p,t}^{(\tau)}} x_i
$$

where $P_{p,t}^{(\tau)}$ is the set of pitches by player $p$ in window $\tau$ ending at $t$.

**Times Through Order (TTO):**

$$
TTO = \left\lfloor \frac{\text{pitcher\_pitch\_count}}{25} \right\rfloor + 1
$$

---

## 4. Model Evaluation

### 4.1 Evaluation Metrics

**Multi-Class Log Loss:**

$$
\mathcal{L}_{log} = -\frac{1}{N} \sum_{i=1}^{N} \sum_{k=1}^{K} y_{ik} \log \hat{\pi}_{ik}
$$

**Brier Score (Multi-Class):**

$$
BS = \frac{1}{N} \sum_{i=1}^{N} \sum_{k=1}^{K} (\hat{\pi}_{ik} - y_{ik})^2
$$

**Expected Calibration Error (ECE):**

$$
ECE = \sum_{m=1}^{M} \frac{|B_m|}{N} \left| \text{acc}(B_m) - \text{conf}(B_m) \right|
$$

where $B_m$ are confidence bins.

**Top-K Accuracy:**

$$
\text{Top-K Acc} = \frac{1}{N} \sum_{i=1}^{N} \mathbb{1}[y_i \in \text{top-k}(\hat{\pi}_i)]
$$

### 4.2 Validation Strategy

**Season-Stratified Cross-Validation:**

$$
\mathcal{D}_{train} = \{ i : \text{year}_i \in [2015, 2022] \} \\
\mathcal{D}_{val} = \{ i : \text{year}_i = 2023 \} \\
\mathcal{D}_{test} = \{ i : \text{year}_i \in [2024, 2025] \}
$$

**Bootstrap Confidence Intervals:**

For metric $M$ with $B$ bootstrap samples:

$$
CI_{95\%}(M) = [Q_{0.025}(M^{(b)}), Q_{0.975}(M^{(b)})]
$$

---

## 5. Implementation Architecture

### 5.1 Flexible Feature Mart Schema

Our schema implements the "all fields available, selective inclusion" principle:

```
features_pitch.base_features        → 118 raw Statcast fields
features_pitch.engineered_features  → Derived metrics + targets  
features_pitch.sequential_features  → JSONB LSTM windows
features_pitch.player_context       → Rolling statistics
features_pitch.model_training_set   → Versioned training data
```

**Metadata-Driven Feature Selection:**

```sql
SELECT column_name 
FROM features_pitch.feature_registry 
WHERE 'xgboost' = ANY(model_usage) 
  AND is_active = TRUE;
```

### 5.2 Reproducibility Guarantees

**Data Versioning:**

$$
\text{data\_hash} = SHA256(\text{CONCAT}(\text{pitch\_ids}, \text{features}))
$$

**Training Set Registry:**

Each training set is versioned with:
- `training_set_id`: UUID
- `created_at`: Timestamp
- `data_hash`: SHA-256 of source data
- `feature_list`: Ordered array of feature names
- `row_count`: Number of examples
- `time_range`: [min(game_date), max(game_date)]

---

## 6. Research Findings Alignment

### 6.1 External Research Comparison

| Study | Approach | Accuracy | Our Schema Support |
|-------|----------|----------|-------------------|
| SMU (Gopal et al.) | Feedforward NN | 58% coarse | ✅ `engineered_features.outcome_tier1` |
| CMU Neural Sabermetrics | Llama-3.2 3B | 63.7% pitch type, 76.6% swing IZ | ✅ `sequential_features` for sequences |
| Towards Data Science | LightGBM | 80.5% swing | ✅ `feature_registry` includes swing targets |
| Penn State | ML + Sabermetrics | ~60% | ✅ All physics features present |

### 6.2 Hypotheses to Test

**H1:** Sequential modeling improves accuracy for late-count pitches (2-strike counts)

$$
\Delta_{acc} = \text{Acc}_{LSTM} - \text{Acc}_{XGB} > 0 \quad \text{for } strikes = 2
$$

**H2:** Multi-task learning improves pitch type prediction when location is auxiliary target

$$
\text{Acc}_{MTL}(type) > \text{Acc}_{single}(type)
$$

**H3:** Swing probability calibration is better inside strike zone than outside

$$
ECE_{in-zone} < ECE_{out-zone}
$$

---

## 7. Next Steps

### 7.1 Immediate Actions

1. **Populate base_features:** Migrate 7.66M pitches from `locations`
2. **Build engineered_features:** Create outcome tiers and derived metrics
3. **Train Tier-1 XGBoost:** Establish coarse outcome baseline
4. **Evaluate against research benchmarks:** Validate >58% coarse accuracy

### 7.2 Medium-Term Goals

1. **LSTM sequence model:** 5-pitch sliding windows within PAs
2. **Multi-task network:** Pitch type + location joint prediction
3. **Swing probability model:** Calibrate to 80%+ accuracy
4. **Player context integration:** Rolling 30-day averages

### 7.3 Success Criteria

| Model | Target Accuracy | Target Log Loss | Target ECE |
|-------|-----------------|-----------------|------------|
| Tier-1 XGBoost | >80% coarse | <0.5 | <0.02 |
| Tier-2 XGBoost | >45% fine | <1.6 | <0.03 |
| LSTM Sequential | >82% coarse | <0.45 | <0.02 |
| Multi-Task | >65% type, RMSE<0.5 loc | N/A | <0.03 |
| Swing Prob | >80% | <0.35 | <0.02 |

---

## 8. References

1. Gopal et al. (SMU). "Pitch Outcome Prediction Using Physics and Context." 2024.
2. Lee (2022). "Ensemble Models for Pitch Type and Location Prediction."
3. Yu et al. (2022). "Attention-Based LSTMs for Pitch Sequence Modeling."
4. Ramirez (2024). "pitch_prediction_using_ML: Multi-Task Deep Learning." GitHub.
5. Schilamkur (2024). "Pitch-Outcome-Prediction: Two-Tier Classification." GitHub.
6. Towards Data Science (2024). "Swing Probability with LightGBM."

---

## Appendix A: SQL Query Templates

### A.1 XGBoost Training Query

```sql
SELECT 
    -- Features
    bf.release_speed, bf.plate_x, bf.plate_z,
    bf.pfx_x, bf.pfx_z, bf.release_spin_rate,
    ef.outcome_tier1 as target
FROM features_pitch.base_features bf
JOIN features_pitch.engineered_features ef USING (pitch_id)
WHERE bf.quality_flag = 'normal'
  AND bf.game_year BETWEEN 2015 AND 2022;
```

### A.2 LSTM Sequence Query

```sql
SELECT 
    pitch_id,
    game_pk,
    at_bat_number,
    pitch_number,
    feature_vector,
    outcome
FROM features_pitch.sequential_features
WHERE seq_length >= 3
ORDER BY game_pk, at_bat_number, pitch_number;
```

### A.3 Player Context Query

```sql
SELECT 
    pc.pitcher_id,
    pc.context_type,
    pc.avg_velocity_30d,
    pc.breaking_pct_30d,
    pc.strike_pct_30d
FROM features_pitch.player_context pc
WHERE pc.as_of_date = '2024-06-15'::date
  AND pc.context_type = 'last_30_days';
```

---

## Appendix B: Feature Registry Sample

| column_name | feature_category | is_default | model_usage | data_type |
|-------------|-----------------|------------|-------------|-----------|
| release_speed | physics | TRUE | {xgboost, lstm} | numeric |
| plate_x | location | TRUE | {xgboost, lstm, mtl} | numeric |
| outcome_tier1 | target | TRUE | {xgboost} | categorical |
| swing_decision | target | FALSE | {swing} | boolean |
| seq_5_pitch_types | sequential | FALSE | {lstm} | jsonb |

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-24  
**CRISP-DM Phase:** 3 → 4 Transition  
**Related Issues:** #78, #79, #80, #81, #82, #83
