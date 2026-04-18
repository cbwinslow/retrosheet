# Model Training and Evaluation Training

This guide provides step-by-step instructions for training and evaluating PA outcome distribution models.

## Overview

The model training process uses historical warehouse data to train machine learning models that predict plate appearance outcomes.

## Prerequisites

- Warehouse rebuilt with feature marts
- Python dependencies installed
- Sufficient disk space for model artifacts
- Optional: GPU for accelerated training

## Step-by-Step Process

### Step 1: Choose Model Configuration

Select model parameters based on your goals:

**Model Family Options:**
- `hist_gradient_boosting_multiclass`: Histogram-based gradient boosting (default)
- `random_forest_multiclass`: Random forest classifier
- `logistic_regression_multiclass`: Multinomial logistic regression

**Feature Set Options:**
- `basic`: Core game state features
- `advanced_count`: Advanced features with count context
- `advanced`: Full advanced feature set

**Temporal Policy Options:**
- `full_history`: Train on all historical data (default)
- `window_N`: Use N-year rolling window
- `half_life_N`: Exponential decay with half-life N

### Step 2: Train Model

```bash
python3 scripts/train_pa_outcome_distribution.py \
    --feature-set advanced \
    --model-name hist_gradient_boosting_multiclass \
    --train-years 2000-2022 \
    --validation-years 2023-2025 \
    --temporal-policy full_history
```

**Parameters:**
- `--feature-set`: Feature set to use
- `--model-name`: Model family to train
- `--train-years`: Years for training data
- `--validation-years`: Years for validation data
- `--temporal-policy`: Temporal weighting policy
- `--n-estimators`: Number of trees (for tree-based models)
- `--max-depth`: Maximum tree depth
- `--learning-rate`: Learning rate (for boosting)

**Expected Output:**
- Training progress logs
- Validation metrics (log loss, Brier score, accuracy)
- Model artifact saved to `data/models/`
- Feature importance rankings

### Step 3: Evaluate Model

```bash
python3 scripts/analyze_pa_outcome_calibration.py \
    --model-id <MODEL_ID> \
    --validation-years 2023-2025
```

**Parameters:**
- `--model-id`: Model ID from training output
- `--validation-years`: Years to evaluate on

**Expected Output:**
- Calibration metrics (ECE, confidence gaps)
- Reliability diagram
- Per-class calibration analysis
- Subgroup analysis (count states, base states)

### Step 4: Calibrate Model

```bash
python3 scripts/calibrate_pa_outcome_model.py \
    --model-id <MODEL_ID> \
    --calibration-years 2023-2024 \
    --validation-years 2025 \
    --calibration-type isotonic
```

**Parameters:**
- `--model-id`: Model ID to calibrate
- `--calibration-years`: Years to fit calibration on
- `--validation-years`: Years to evaluate calibration
- `--calibration-type`: Type of calibration (isotonic, sigmoid)

**Expected Output:**
- Calibration metrics before/after
- Calibration artifact saved to `data/models/calibration/`
- Improvement in log loss and ECE

### Step 5: Register Model

```bash
python3 scripts/register_pa_outcome_calibration.py \
    --model-id <MODEL_ID> \
    --calibration-artifact-path <ARTIFACT_PATH> \
    --report-name "calibration_report"
```

**Parameters:**
- `--model-id`: Model ID to register
- `--calibration-artifact-path`: Path to calibration artifact
- `--report-name`: Name for calibration report

**Expected Output:**
- Model registered in `models.model_registry`
- Calibration artifact registered
- Model marked as active if specified

### Step 6: Bootstrap Evaluation (Optional)

```bash
python3 scripts/bootstrap_pa_outcome_evaluation.py \
    --model-id <MODEL_ID> \
    --validation-years 2023-2025 \
    --n-replicates 50
```

**Parameters:**
- `--model-id`: Model ID to evaluate
- `--validation-years`: Years to evaluate on
- `--n-replicates`: Number of bootstrap replicates

**Expected Output:**
- Mean and confidence intervals for metrics
- Bootstrap uncertainty estimates
- Report saved to `predictions.bootstrap_reports`

### Step 7: Persist Reports

```bash
python3 scripts/persist_pa_outcome_reports.py \
    --model-id <MODEL_ID>
```

**Parameters:**
- `--model-id`: Model ID to persist reports for

**Expected Output:**
- Calibration report saved to `predictions.calibration_reports`
- Bootstrap report saved to `predictions.bootstrap_reports`
- Evaluation metrics saved to `predictions.evaluation_metrics`

## Model Selection Guidelines

### When to Use Different Model Families

**Histogram Gradient Boosting:**
- Best overall performance
- Fast training on large datasets
- Handles mixed feature types well
- **Use for:** Production models, large feature sets

**Random Forest:**
- Good interpretability
- Robust to overfitting
- Slower training than HGB
- **Use for:** Baseline models, small datasets

**Logistic Regression:**
- Highly interpretable
- Fast training
- Limited non-linear modeling
- **Use for:** Simple baselines, debugging

### When to Use Different Feature Sets

**Basic:**
- Core game state only
- Fast feature computation
- Lower predictive power
- **Use for:** Quick prototypes, debugging

**Advanced Count:**
- Advanced features with count context
- Good balance of performance/speed
- **Use for:** Most production use cases

**Advanced:**
- Full feature set with priors and history
- Highest predictive power
- Slower feature computation
- **Use for:** Maximum accuracy requirements

### When to Use Different Temporal Policies

**Full History:**
- Uses all historical data
- Best for stable patterns
- May miss recent trends
- **Use for:** Most cases, stable game patterns

**Window:**
- Uses recent N years only
- Adapts to recent trends
- Less training data
- **Use for:** Rapidly changing environments

**Half-Life:**
- Exponential decay weighting
- Balances stability and adaptability
- Tuning required
- **Use for:** Gradual pattern evolution

## Evaluation Metrics

### Primary Metrics

**Log Loss:**
- Measures probability calibration
- Lower is better
- Typical range: 1.4-1.6

**Brier Score:**
- Mean squared error of probabilities
- Lower is better
- Typical range: 0.7-0.75

**Accuracy:**
- Percentage of correct predictions
- Higher is better
- Typical range: 0.40-0.45

### Calibration Metrics

**Expected Calibration Error (ECE):**
- Measures calibration quality
- Lower is better
- Target: < 0.05

**Confidence Gap:**
- Difference between predicted and observed frequency
- Lower is better
- Target: < 0.05 per subgroup

## Troubleshooting

### Issue: Training is very slow

**Solution:** 
- Reduce `--n-estimators`
- Use `--feature-set basic` for testing
- Use GPU if available
- Reduce training year range

### Issue: Out of memory during training

**Solution:**
- Reduce batch size
- Use smaller feature set
- Process fewer years
- Use `max_samples` parameter

### Issue: Model overfits validation data

**Solution:**
- Reduce model complexity (`--max-depth`)
- Add regularization
- Use temporal decay policy
- Increase training data

### Issue: Calibration makes performance worse

**Solution:**
- Check calibration years are separate from validation
- Try different calibration type (sigmoid vs isotonic)
- Ensure sufficient calibration data
- Check for data leakage

## Best Practices

1. **Always use separate calibration and validation years**
2. **Document model parameters in model registry**
3. **Save calibration artifacts with model**
4. **Run bootstrap evaluation for uncertainty estimates**
5. **Persist reports for reproducibility**
6. **Compare against baseline models**
7. **Monitor for drift over time**

## Next Steps

After model training:
1. Register model in model registry
2. Set up prediction serving
3. Monitor model performance
4. Plan for model retraining schedule
