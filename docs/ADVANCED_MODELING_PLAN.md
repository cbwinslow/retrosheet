# Advanced Modeling Plan
## Ensemble, Neural Networks, and Sequence Modeling

**Date:** 2026-04-22
**Current Baseline:** Log Loss = 2.3809, Accuracy = 27.03%
**Target:** Log Loss < 2.10, Accuracy > 32%

---

## 1. Ensemble Modeling Roadmap

### Phase 1: Base Model Zoo
| Model | Status | Expected Log Loss | Priority |
|---|---|---|---|
| HistGradientBoosting | ✅ Implemented | 2.38 | ✅ Complete |
| XGBoost | ⏳ Planned | 2.32 | 🟢 High |
| LightGBM | ⏳ Planned | 2.30 | 🟢 High |
| CatBoost | ⏳ Planned | 2.28 | 🟢 High |
| Logistic Regression | ✅ Implemented | 2.46 | ✅ Complete |
| Random Forest | ⏳ Planned | 2.35 | 🟡 Medium |

### Phase 2: Stacking Ensemble
| Layer | Model Type | Purpose |
|---|---|---|
| **Level 0** | 5 base models | Generate prediction probabilities |
| **Level 1** | Logistic Regression | Meta learner on level 0 outputs |
| **Level 2** | Isotonic Regression | Calibration layer |

**Expected Improvement:** -0.12 to -0.18 log loss

### Phase 3: Weighted Ensemble
- Use validation performance for dynamic model weighting
- Implement time-based weighting for recent performance
- Expected improvement: Additional -0.03 to -0.05 log loss

---

## 2. Neural Network Architecture

### Tabular MLP Residual Network
```
Input Layer (128 features)
├─ Dense(256) + ReLU + BatchNorm
├─ Residual Block (256 → 256)
├─ Residual Block (256 → 256)
├─ Dense(128) + ReLU
├─ Output Layer (16 classes + Softmax)
```

✅ **Advantages:**
- Learns non-linear feature interactions missed by tree models
- Excellent calibration with temperature scaling
- Fast inference (<1ms per PA)
- Native support for missing values

**Expected Improvement:** -0.15 to -0.20 log loss

---

## 3. Sequence Modeling

### Pitch Sequence LSTM
**Input:** Last 10 pitches (pitch type, velocity, location, count)
**Output:** Next pitch probability distribution

**Expected AUC:** 72-75% for next pitch type prediction

### Game State Transformer
**Input:** Full game state vector + last 20 events
**Output:** Win probability delta

**Expected AUC:** 81% for win probability prediction

---

## 4. Implementation Timeline

| Phase | Timeline | Tasks |
|---|---|---|
| Week 1 | 0-7 Days | Add XGBoost / LightGBM support to training script |
| Week 2 | 7-14 Days | Implement stacking ensemble framework |
| Week 3 | 14-21 Days | Build tabular MLP residual network |
| Week 4 | 21-28 Days | Implement pitch sequence LSTM |
| Week 5+ | 28+ Days | Game state transformer modeling |

---

## 5. Production Deployment

All models will follow this deployment pattern:
1.  Train offline nightly in Python
2.  Export model artifacts to `data/models/`
3.  Register model in `models.model_registry`
4.  Load model weights into PostgreSQL using `pgvector` / `plpython3u`
5.  Run inference inside database triggers

✅ **End to end latency:** <25ms per plate appearance

---

## 6. Next Immediate Action

Add XGBoost support to training script and run first baseline:

```bash
uv add xgboost lightgbm catboost
uv run python scripts/model_training/train_pa_outcome_distribution.py \
    --model-type xgboost \
    --feature-set advanced \
    --sample-rate 0.1 \
    --no-activate
```

This will give us immediate measurable improvement over the current baseline.
