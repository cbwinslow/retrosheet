# Model Selection Guide

**Date:** 2026-04-22
**Purpose:** Research-backed guidance for selecting models by prediction target type

## Quick Reference

| Situation | Recommended | Alternative | Why |
|-----------|-------------|------------|------|
| PA outcome (multi-class) | HGB multiclass | Softmax | Rich features, coherent probabilities |
| Inning runs | Markov uninformed | Empirical baseline | No features needed, fast |
| Next base-out state | Softmax | Markov informed | Discrete state transitions |
| Strikeout rate | HGB | Logistic | Binary, pitcher features |
| No-hit inning | Markov + ML | Informed Markov | State + pitcher quality |
| Win probability | Ensemble | LightGBM | Complex features |
| Hit projection | Softmax | Empirical | Stanford validated |

## Decision Tree

```
START: What are you predicting?
│
├─ "What happens to this batter?"
│   └─ Multi-class distribution?
│       ├─ Yes → HGB multiclass or Softmax
│       └─ No → Binary classification
│           ├─ Strikeout → HGB or Logistic
│           ├─ Walk → HGB or Logistic
│           ├─ Hit → HGB or Logistic
│           └─ Reach base → HGB or Logistic
│
├─ "How many runs this inning?"
│   └─ Markov uninformed (if no features) or
│      Markov informed (if pitcher/batter quality known)
│
├─ "What base-out state next?"
│   └─ Softmax regression (Stanford validated) or
│      Informed Markov (if count context needed)
│
├─ "Who wins this game?"
│   └─ Ensemble (RE24 + ML + Markov) or
│      LightGBM with 165 features
│
├─ " pitcher performance?"
│   ├─ Strikeout rate → HGB + pitcher features
│   ├─ ERA → HGB regression
│   └─ K/BB ratio → HGB + pitch mix features
│
└─ "Specific situation?"
   ├─ "No hits in 3rd" → Markov + ML hybrid
   ├─ "RISP scoring" → Informed Markov
   └─ "Comeback win" → Win probability RE24
```

## Model Family Details

### 1. Empirical Baseline (No Model)
- **What**: Just use historical rate for that stratum
- **Use when**: First baseline, no features, fast
- **Strengths**: No training, no overfitting
- **Weaknesses**: No personalization
- **Example**: P(strikeout) = 23% for all PAs

### 2. Markov Chain (Uninformed)
- **What**: Transition matrix from historical data
- **Use when**: Predicting base-out states, inning runs
- **Strengths**: Interpretable, no features needed
- **Weaknesses**: Assumes stationarity
- **Requirements**: Run expectancy matrix
- **Research**: UT Austin, Stanford CS229

### 3. Markov Chain (Informed)
- **What**: Condition transitions on features
- **Use when**: Need personalization but discrete states
- **Strengths**: Balances simplicity + specificity
- **Weaknesses**: Feature bins must be crafted
- **Requirements**: Feature-enriched RE matrix

### 4. Softmax Regression
- **What**: Multinomial logistic regression
- **Use when**: Multi-class, discrete states
- **Strengths**: Stanford validated, probabilistic
- **Weaknesses**: Linear in features
- **Research**: Stanford CS229 (beat Vegas)
- **Example**: Predict next state from (pitcher, batter, count)

### 5. HistGradientBoosting (HGB)
- **What**: Sklearn's HistGradientBoostingClassifier
- **Use when**: Rich features, complex relationships
- **Strengths**: Handles categoricals, fast, good defaults
- **Weaknesses**: Black box, needs tuning
- **Current best**: PA outcome (log loss 1.5089)

### 6. LightGBM
- **What**: Gradient boosting with leaf-wise growth
- **Use when**: Large data, need speed
- **Strengths**: Fast, good with sparse data
- **Weaknesses**: Less mature than sklearn
- **Research**: mlb-win-probability uses 165 features

### 7. Logistic Regression
- **What**: Binary classification
- **Use when**: Binary targets, interpretability needed
- **Strengths**: Interpretable, calibrated
- **Weaknesses**: Linear boundaries

### 8. Ensemble
- **What**: Combine multiple models
- **Use when**: Production, need robustness
- **Strengths**: Robust, worst-case protected
- **Weaknesses**: Complex, slower
- **Research**: Ensemble Brier 0.1605 (mlb-win-probability)

### 9. Bayesian Hierarchical
- **What**: Hierarchical Bayesian with uncertainty
- **Use when**: Need uncertainty estimates
- **Strengths**: 90% credible intervals
- **Weaknesses**: Slow, complex
- **Research**: mlb-win-probability v4

## Feature Requirements by Model

| Model | Numerical | Categorical | Special |
|-------|-----------|-----------|---------|
| Empirical | none | stratification | none |
| Markov uninformed | none | state encoding | RE matrix |
| Markov informed | features binned | state, count | RE matrix + bins |
| Softmax | standard | one-hot | none |
| HGB | native | native (optional) | none |
| LightGBM | native | native | none |
| Logistic | scaled | one-hot | none |

## Validation Requirements

### All Models
- [ ] Season-stratified train/test split
- [ ] Bootstrap confidence intervals
- [ ] Calibration check (probabilities only)
- [ ] Feature importance

### Multi-class
- [ ] Per-class ECE
- [ ] Top-k accuracy
- [ ] Confusion matrix

### Binary
- [ ] ROC AUC
- [ ] Precision-recall curve
- [ ] Calibration curve

### Distribution
- [ ] Total probability = 1
- [ ] Per-class calibration
- [ ] Brier score

## Research Sources

- Stanford CS229: Softmax for transitions
- UT Austin: Markov for runs/win
- mlb-win-probability: LightGBM + ensemble
- KNOWLEDGE_BASE_MARKOV_CHAIN.md: Full research synthesis
- KNOWLEDGE_BASE_SABERMETRICS.md: Sabermetrics context

## Related Docs

- [docs/KNOWLEDGE_BASE_MARKOV_CHAIN.md](docs/KNOWLEDGE_BASE_MARKOV_CHAIN.md)
- [docs/KNOWLEDGE_BASE_FRAMEWORK.md](docs/KNOWLEDGE_BASE_FRAMEWORK.md)
- [docs/KNOWLEDGE_BASE_SABERMETRICS.md](docs/KNOWLEDGE_BASE_SABERMETRICS.md)