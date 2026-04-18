# Prediction Serving Training

This guide provides step-by-step instructions for serving predictions using trained models.

## Overview

Prediction serving uses registered models to generate probability distributions for plate appearances.

## Prerequisites

- Trained model registered in model registry
- Calibration artifact registered (if using calibration)
- Warehouse with feature data
- Python dependencies installed

## Step-by-Step Process

### Step 1: Verify Model Registration

```bash
psql -d retrosheet -c "SELECT model_id, model_name, model_version, is_active FROM models.model_registry;"
```

**Expected Output:** List of registered models with active flag

### Step 2: Historical Prediction

```bash
python3 scripts/predict_pa_outcome_distribution.py \
    --game-id WAS201910260 \
    --plate-appearance-id 1 \
    --apply-calibration
```

**Parameters:**
- `--game-id`: Game ID from core.games
- `--plate-appearance-id`: Plate appearance ID from core.plate_appearances
- `--apply-calibration`: Apply calibration (default: True)
- `--model-name`: Model name (default: from model registry)
- `--model-version`: Model version (default: active version)

**Expected Output:**
```json
{
  "game_id": "WAS201910260",
  "plate_appearance_id": 1,
  "class_probabilities": {
    "strikeout": 0.25,
    "ground_out": 0.30,
    ...
  },
  "derived_probabilities": {
    "hit": 0.20,
    "out": 0.75,
    ...
  },
  "model_metadata": {
    "model_id": 123,
    "model_name": "hist_gradient_boosting_multiclass",
    ...
  },
  "state_snapshot": {
    "inning": 1,
    "outs_before": 0,
    "start_bases": 0,
    ...
  },
  "missing_features": []
}
```

### Step 3: Live Prediction

```bash
python3 scripts/predict_live_pa_outcome_distribution.py \
    --game-pk 599374 \
    --apply-calibration
```

**Parameters:**
- `--game-pk`: MLB Stats API game PK
- `--apply-calibration`: Apply calibration (default: True)
- `--model-name`: Model name (default: from model registry)

**Expected Output:** Same structure as historical prediction

### Step 4: Batch Predictions

For batch predictions, use a script:

```python
import pandas as pd
from predict_pa_outcome_distribution import predict_pa_outcome_distribution

# Load plate appearances
pas = pd.read_sql("""
    SELECT plate_appearance_id, game_id
    FROM core.plate_appearances
    LIMIT 100
""", engine)

# Make predictions
results = []
for _, row in pas.iterrows():
    result = predict_pa_outcome_distribution(
        game_id=row['game_id'],
        plate_appearance_id=row['plate_appearance_id'],
        apply_calibration=True,
    )
    results.append(result)

# Convert to DataFrame
results_df = pd.DataFrame(results)
```

### Step 5: API Integration (Next.js)

Use the API route for web applications:

```typescript
// baseball-chatbot-ui/app/api/predict/route.ts
const response = await fetch('/api/predict', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    gameId: 'WAS201910260',
    plateAppearanceId: 1,
    applyCalibration: true,
  }),
});

const prediction = await response.json();
```

## Prediction Output Structure

### Class Probabilities

Raw probabilities for each outcome class:
- `strikeout`: Probability of strikeout
- `ground_out`: Probability of ground out
- `fly_out`: Probability of fly out
- `line_out`: Probability of line out
- `pop_out`: Probability of pop out
- `single`: Probability of single
- `double`: Probability of double
- `triple`: Probability of triple
- `home_run`: Probability of home run
- `walk`: Probability of walk
- `hit_by_pitch`: Probability of hit by pitch

### Derived Probabilities

Aggregated probabilities for higher-level categories:
- `hit`: Probability of any hit (single + double + triple + home_run)
- `out`: Probability of any out
- `walk`: Probability of walk or hit by pitch
- `extra_base_hit`: Probability of double, triple, or home_run
- `on_base`: Probability of reaching base (hit + walk)

### Model Metadata

Information about the model used:
- `model_id`: Internal model ID
- `model_name`: Model family name
- `model_version`: Model version
- `feature_set`: Feature set used
- `calibration_applied`: Whether calibration was applied

### State Snapshot

Game state at time of prediction:
- `inning`: Inning number
- `is_bottom_inning`: Bottom of inning flag
- `outs_before`: Outs before the PA
- `start_bases`: Base state (bitmask)
- `balls`: Ball count
- `strikes`: Strike count
- `home_score_diff`: Home team score differential

### Missing Features

List of features that could not be computed:
- Empty if all features available
- Contains feature names if data missing

## Performance Optimization

### Model Caching

Models are cached after first load to avoid repeated disk I/O:

```python
from retrosheet.prediction import load_registered_model

# First call loads from disk
model1 = load_registered_model(model_name="hist_gradient_boosting_multiclass")

# Subsequent calls use cache
model2 = load_registered_model(model_name="hist_gradient_boosting_multiclass")
```

### Batch Processing

For multiple predictions, process in batches to reduce overhead:

```python
# Process 100 PAs at a time
batch_size = 100
for i in range(0, len(pas), batch_size):
    batch = pas.iloc[i:i+batch_size]
    # Process batch
```

### Connection Pooling

Use connection pooling for database queries:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    database_url(),
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
)
```

## Troubleshooting

### Issue: Model not found

**Solution:** Check model is registered:
```bash
psql -d retrosheet -c "SELECT * FROM models.model_registry WHERE is_active = true;"
```

### Issue: Calibration artifact not found

**Solution:** Check calibration is registered:
```bash
psql -d retrosheet -c "SELECT * FROM models.calibration_artifacts;"
```

### Issue: Features missing

**Solution:** Check feature table has data:
```bash
psql -d retrosheet -c "SELECT COUNT(*) FROM features.plate_appearance_advanced_examples;"
```

### Issue: Slow predictions

**Solution:** 
- Use model caching
- Process in batches
- Check database indexes
- Use connection pooling

## Best Practices

1. **Always use calibration for production predictions**
2. **Cache models to avoid repeated loading**
3. **Process predictions in batches for efficiency**
4. **Handle missing features gracefully**
5. **Log prediction requests for debugging**
6. **Monitor prediction latency**
7. **Validate predictions against historical data**

## Monitoring

Monitor prediction serving metrics:

- **Latency:** P50, P95, P99 prediction time
- **Error Rate:** Percentage of failed predictions
- **Feature Null Rate:** Percentage of missing features
- **Calibration Drift:** Monitor calibration quality over time

## Security

- **Authentication:** Require API keys for prediction endpoints
- **Rate Limiting:** Limit requests per user
- **Audit Logging:** Log all prediction requests
- **Input Validation:** Validate input parameters

## Next Steps

After setting up prediction serving:
1. Set up monitoring and alerting
2. Implement prediction logging
3. Create performance dashboards
4. Set up model retraining pipeline
